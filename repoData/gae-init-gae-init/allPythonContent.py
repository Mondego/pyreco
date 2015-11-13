__FILENAME__ = admin
# coding: utf-8

from flask.ext import wtf
from google.appengine.api import app_identity
import flask

import auth
import config
import model
import util

from main import app


class ConfigUpdateForm(wtf.Form):
  analytics_id = wtf.StringField('Tracking ID', filters=[util.strip_filter])
  announcement_html = wtf.TextAreaField('Announcement HTML', filters=[util.strip_filter])
  announcement_type = wtf.SelectField('Announcement Type', choices=[(t, t.title()) for t in model.Config.announcement_type._choices])
  brand_name = wtf.StringField('Brand Name', [wtf.validators.required()], filters=[util.strip_filter])
  facebook_app_id = wtf.StringField('App ID', filters=[util.strip_filter])
  facebook_app_secret = wtf.StringField('App Secret', filters=[util.strip_filter])
  feedback_email = wtf.StringField('Feedback Email', [wtf.validators.optional(), wtf.validators.email()], filters=[util.email_filter])
  flask_secret_key = wtf.StringField('Secret Key', [wtf.validators.optional()], filters=[util.strip_filter])
  notify_on_new_user = wtf.BooleanField('Send an email notification when a user signs up')
  twitter_consumer_key = wtf.StringField('Consumer Key', filters=[util.strip_filter])
  twitter_consumer_secret = wtf.StringField('Consumer Secret', filters=[util.strip_filter])


@app.route('/_s/admin/config/', endpoint='admin_config_update_service')
@app.route('/admin/config/', methods=['GET', 'POST'])
@auth.admin_required
def admin_config_update():
  config_db = model.Config.get_master_db()
  form = ConfigUpdateForm(obj=config_db)
  if form.validate_on_submit():
    form.populate_obj(config_db)
    if not config_db.flask_secret_key:
      config_db.flask_secret_key = util.uuid()
    config_db.put()
    reload(config)
    app.config.update(CONFIG_DB=config_db)
    return flask.redirect(flask.url_for('welcome'))

  if flask.request.path.startswith('/_s/'):
    return util.jsonify_model_db(config_db)

  instances_url = None
  if config.PRODUCTION:
    instances_url = '%s?app_id=%s&version_id=%s' % (
        'https://appengine.google.com/instances',
        app_identity.get_application_id(),
        config.CURRENT_VERSION_ID,
      )

  return flask.render_template(
      'admin/config_update.html',
      title='Admin Config',
      html_class='admin-config',
      form=form,
      config_db=config_db,
      instances_url=instances_url,
      has_json=True,
    )

########NEW FILE########
__FILENAME__ = appengine_config
# coding: utf-8

import os
import sys

if os.environ.get('SERVER_SOFTWARE', '').startswith('Google App Engine'):
  sys.path.insert(0, 'lib.zip')
else:
  import re
  from google.appengine.tools.devappserver2.python import stubs
  re_ = stubs.FakeFile._skip_files.pattern.replace('|^lib/.*', '')
  re_ = re.compile(re_)
  stubs.FakeFile._skip_files = re_
  sys.path.insert(0, 'lib')
sys.path.insert(0, 'libx')

########NEW FILE########
__FILENAME__ = auth
# coding: utf-8

import functools
import re

from flask.ext import login
from flask.ext import oauth
from google.appengine.api import users
from google.appengine.ext import ndb
import flask

import config
import model
import task
import util

from main import app

_signals = flask.signals.Namespace()

###############################################################################
# Flask Login
###############################################################################
login_manager = login.LoginManager()


class AnonymousUser(login.AnonymousUserMixin):
  id = 0
  admin = False
  name = 'Anonymous'
  user_db = None

  def key(self):
    return None

login_manager.anonymous_user = AnonymousUser


class FlaskUser(AnonymousUser):
  def __init__(self, user_db):
    self.user_db = user_db
    self.id = user_db.key.id()
    self.name = user_db.name
    self.admin = user_db.admin

  def key(self):
    return self.user_db.key.urlsafe()

  def get_id(self):
    return self.user_db.key.urlsafe()

  def is_authenticated(self):
    return True

  def is_active(self):
    return self.user_db.active

  def is_anonymous(self):
    return False


@login_manager.user_loader
def load_user(key):
  user_db = ndb.Key(urlsafe=key).get()
  if user_db:
    return FlaskUser(user_db)
  return None


login_manager.init_app(app)


def current_user_id():
  return login.current_user.id


def current_user_key():
  return login.current_user.user_db.key if login.current_user.user_db else None


def current_user_db():
  return login.current_user.user_db


def is_logged_in():
  return login.current_user.id != 0


###############################################################################
# Decorators
###############################################################################
def login_required(f):
  decorator_order_guard(f, 'auth.login_required')

  @functools.wraps(f)
  def decorated_function(*args, **kws):
    if is_logged_in():
      return f(*args, **kws)
    if flask.request.path.startswith('/_s/'):
      return flask.abort(401)
    return flask.redirect(flask.url_for('signin', next=flask.request.url))
  return decorated_function


def admin_required(f):
  decorator_order_guard(f, 'auth.admin_required')

  @functools.wraps(f)
  def decorated_function(*args, **kws):
    if is_logged_in() and current_user_db().admin:
      return f(*args, **kws)
    if not is_logged_in() and flask.request.path.startswith('/_s/'):
      return flask.abort(401)
    if not is_logged_in():
      return flask.redirect(flask.url_for('signin', next=flask.request.url))
    return flask.abort(403)
  return decorated_function


permission_registered = _signals.signal('permission-registered')


def permission_required(permission=None, methods=None):
  def permission_decorator(f):
    decorator_order_guard(f, 'auth.permission_required')

    # default to decorated function name as permission
    perm = permission or f.func_name
    meths = [m.upper() for m in methods] if methods else None

    permission_registered.send(f, permission=perm)

    @functools.wraps(f)
    def decorated_function(*args, **kws):
      if meths and flask.request.method.upper() not in meths:
        return f(*args, **kws)
      if is_logged_in() and current_user_db().has_permission(perm):
        return f(*args, **kws)
      if not is_logged_in():
        if flask.request.path.startswith('/_s/'):
          return flask.abort(401)
        return flask.redirect(flask.url_for('signin', next=flask.request.url))
      return flask.abort(403)
    return decorated_function
  return permission_decorator


###############################################################################
# Sign in stuff
###############################################################################
@app.route('/login/')
@app.route('/signin/')
def signin():
  next_url = util.get_next_url()
  if flask.url_for('signin') in next_url:
    next_url = flask.url_for('welcome')

  google_signin_url = flask.url_for('signin_google', next=next_url)
  twitter_signin_url = flask.url_for('signin_twitter', next=next_url)
  facebook_signin_url = flask.url_for('signin_facebook', next=next_url)

  return flask.render_template(
      'signin.html',
      title='Please sign in',
      html_class='signin',
      google_signin_url=google_signin_url,
      twitter_signin_url=twitter_signin_url,
      facebook_signin_url=facebook_signin_url,
      next_url=next_url,
    )


@app.route('/signout/')
def signout():
  login.logout_user()
  flask.flash(u'You have been signed out.', category='success')
  return flask.redirect(flask.url_for('welcome'))


###############################################################################
# Google
###############################################################################
@app.route('/signin/google/')
def signin_google():
  save_request_params()
  google_url = users.create_login_url(flask.url_for('google_authorized'))
  return flask.redirect(google_url)


@app.route('/_s/callback/google/authorized/')
def google_authorized():
  google_user = users.get_current_user()
  if google_user is None:
    flask.flash(u'You denied the request to sign in.')
    return flask.redirect(util.get_next_url())

  user_db = retrieve_user_from_google(google_user)
  return signin_user_db(user_db)


def retrieve_user_from_google(google_user):
  auth_id = 'federated_%s' % google_user.user_id()
  user_db = model.User.retrieve_one_by('auth_ids', auth_id)
  if user_db:
    if not user_db.admin and users.is_current_user_admin():
      user_db.admin = True
      user_db.put()
    return user_db

  return create_user_db(
      auth_id,
      re.sub(r'_+|-+|\.+', ' ', google_user.email().split('@')[0]).title(),
      google_user.email(),
      google_user.email(),
      admin=users.is_current_user_admin(),
    )


###############################################################################
# Twitter
###############################################################################
twitter_oauth = oauth.OAuth()


twitter = twitter_oauth.remote_app(
    'twitter',
    base_url='https://api.twitter.com/1.1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authorize',
    consumer_key=config.CONFIG_DB.twitter_consumer_key,
    consumer_secret=config.CONFIG_DB.twitter_consumer_secret,
  )


@app.route('/_s/callback/twitter/oauth-authorized/')
@twitter.authorized_handler
def twitter_authorized(resp):
  if resp is None:
    flask.flash(u'You denied the request to sign in.')
    return flask.redirect(util.get_next_url())

  flask.session['oauth_token'] = (
      resp['oauth_token'],
      resp['oauth_token_secret'],
    )
  user_db = retrieve_user_from_twitter(resp)
  return signin_user_db(user_db)


@twitter.tokengetter
def get_twitter_token():
  return flask.session.get('oauth_token')


@app.route('/signin/twitter/')
def signin_twitter():
  flask.session.pop('oauth_token', None)
  save_request_params()
  try:
    return twitter.authorize(callback=flask.url_for('twitter_authorized'))
  except:
    flask.flash(
        'Something went wrong with Twitter sign in. Please try again.',
        category='danger',
      )
    return flask.redirect(flask.url_for('signin', next=util.get_next_url()))


def retrieve_user_from_twitter(response):
  auth_id = 'twitter_%s' % response['user_id']
  user_db = model.User.retrieve_one_by('auth_ids', auth_id)
  if user_db:
    return user_db

  return create_user_db(
      auth_id,
      response['screen_name'],
      response['screen_name'],
    )


###############################################################################
# Facebook
###############################################################################
facebook_oauth = oauth.OAuth()

facebook = facebook_oauth.remote_app(
    'facebook',
    base_url='https://graph.facebook.com/',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    consumer_key=config.CONFIG_DB.facebook_app_id,
    consumer_secret=config.CONFIG_DB.facebook_app_secret,
    request_token_params={'scope': 'email'},
  )


@app.route('/_s/callback/facebook/oauth-authorized/')
@facebook.authorized_handler
def facebook_authorized(resp):
  if resp is None:
    flask.flash(u'You denied the request to sign in.')
    return flask.redirect(util.get_next_url())

  flask.session['oauth_token'] = (resp['access_token'], '')
  me = facebook.get('/me')
  user_db = retrieve_user_from_facebook(me.data)
  return signin_user_db(user_db)


@facebook.tokengetter
def get_facebook_oauth_token():
  return flask.session.get('oauth_token')


@app.route('/signin/facebook/')
def signin_facebook():
  save_request_params()
  return facebook.authorize(callback=flask.url_for(
      'facebook_authorized', _external=True
    ))


def retrieve_user_from_facebook(response):
  auth_id = 'facebook_%s' % response['id']
  user_db = model.User.retrieve_one_by('auth_ids', auth_id)
  if user_db:
    return user_db
  return create_user_db(
      auth_id,
      response['name'],
      response['username'] if 'username' in response else response['id'],
      response['email'],
    )


###############################################################################
# Helpers
###############################################################################
def decorator_order_guard(f, decorator_name):
  if f in app.view_functions.values():
    raise SyntaxError(
        'Do not use %s above app.route decorators as it would not be checked. '
        'Instead move the line below the app.route lines.' % decorator_name
      )


def create_user_db(auth_id, name, username, email='', **params):
  username = re.sub(r'_+|-+|\s+', '.', username.split('@')[0].lower().strip())
  new_username = username
  n = 1
  while model.User.retrieve_one_by('username', new_username) is not None:
    new_username = '%s%d' % (username, n)
    n += 1

  user_db = model.User(
      name=name,
      email=email.lower(),
      username=new_username,
      auth_ids=[auth_id],
      **params
    )
  user_db.put()
  task.new_user_notification(user_db)
  return user_db


def save_request_params():
  flask.session['auth-params'] = {
      'next': util.get_next_url(),
      'remember': util.param('remember', bool),
    }


@ndb.toplevel
def signin_user_db(user_db):
  if not user_db:
    return flask.redirect(flask.url_for('signin'))
  flask_user_db = FlaskUser(user_db)
  auth_params = flask.session.get('auth-params', {
      'next': flask.url_for('welcome'),
      'remember': False,
    })
  if login.login_user(flask_user_db, remember=auth_params['remember']):
    user_db.put_async()
    flask.flash('Hello %s, welcome to %s.' % (
        user_db.name, config.CONFIG_DB.brand_name,
      ), category='success')
    return flask.redirect(auth_params['next'])
  else:
    flask.flash('Sorry, but you could not sign in.', category='danger')
    return flask.redirect(flask.url_for('signin'))

########NEW FILE########
__FILENAME__ = config
# coding: utf-8

import os

PRODUCTION = os.environ.get('SERVER_SOFTWARE', '').startswith('Google App Eng')
DEVELOPMENT = not PRODUCTION
DEBUG = DEVELOPMENT

try:
  # This part is surrounded in try/except because the config.py file is
  # also used in the run.py script which is used to compile/minify the client
  # side files (*.less, *.coffee, *.js) and is not aware of the GAE
  from datetime import datetime
  from google.appengine.api import app_identity

  CURRENT_VERSION_ID = os.environ.get('CURRENT_VERSION_ID')
  CURRENT_VERSION_NAME = CURRENT_VERSION_ID.split('.')[0]
  CURRENT_VERSION_TIMESTAMP = long(CURRENT_VERSION_ID.split('.')[1]) >> 28
  if DEVELOPMENT:
    import calendar
    CURRENT_VERSION_TIMESTAMP = calendar.timegm(datetime.utcnow().timetuple())
  CURRENT_VERSION_DATE = datetime.utcfromtimestamp(CURRENT_VERSION_TIMESTAMP)
  APPLICATION_ID = app_identity.get_application_id()

  import model

  CONFIG_DB = model.Config.get_master_db()
  SECRET_KEY = CONFIG_DB.flask_secret_key.encode('ascii')
except:
  pass

DEFAULT_DB_LIMIT = 64

###############################################################################
# Client modules, also used by the run.py script.
###############################################################################
STYLES = [
    'src/style/style.less',
  ]

SCRIPTS = [
    ('libs', [
        'ext/js/jquery/jquery.js',
        'ext/js/momentjs/moment.js',
        'ext/js/nprogress/nprogress.js',
        'ext/js/bootstrap/alert.js',
        'ext/js/bootstrap/button.js',
        'ext/js/bootstrap/transition.js',
        'ext/js/bootstrap/collapse.js',
        'ext/js/bootstrap/dropdown.js',
        'ext/js/bootstrap/tooltip.js',
      ]),
    ('scripts', [
        'src/script/common/service.coffee',
        'src/script/common/util.coffee',
        'src/script/site/app.coffee',
        'src/script/site/admin.coffee',
        'src/script/site/profile.coffee',
        'src/script/site/signin.coffee',
        'src/script/site/user.coffee',
      ]),
  ]

########NEW FILE########
__FILENAME__ = main
# coding: utf-8

import logging

from flask.ext import wtf
import flask

import config
import util

app = flask.Flask(__name__)
app.config.from_object(config)
app.jinja_env.line_statement_prefix = '#'
app.jinja_env.line_comment_prefix = '##'
app.jinja_env.globals.update(slugify=util.slugify)
app.jinja_env.globals.update(update_query_argument=util.update_query_argument)


import admin
import auth
import task
import user


if config.DEVELOPMENT:
  from werkzeug import debug
  app.wsgi_app = debug.DebuggedApplication(app.wsgi_app, evalex=True)


###############################################################################
# Main page
###############################################################################
@app.route('/')
def welcome():
  return flask.render_template('welcome.html', html_class='welcome')


###############################################################################
# Sitemap stuff
###############################################################################
@app.route('/sitemap.xml')
def sitemap():
  response = flask.make_response(flask.render_template(
      'sitemap.xml',
      host_url=flask.request.host_url[:-1],
      lastmod=config.CURRENT_VERSION_DATE.strftime('%Y-%m-%d'),
    ))
  response.headers['Content-Type'] = 'application/xml'
  return response


###############################################################################
# Profile stuff
###############################################################################
class ProfileUpdateForm(wtf.Form):
  name = wtf.StringField('Name',
      [wtf.validators.required()], filters=[util.strip_filter],
    )
  email = wtf.StringField('Email',
      [wtf.validators.optional(), wtf.validators.email()],
      filters=[util.email_filter],
    )


@app.route('/_s/profile/', endpoint='profile_service')
@app.route('/profile/', methods=['GET', 'POST'])
@auth.login_required
def profile():
  user_db = auth.current_user_db()
  form = ProfileUpdateForm(obj=user_db)

  if form.validate_on_submit():
    form.populate_obj(user_db)
    user_db.put()
    return flask.redirect(flask.url_for('welcome'))

  if flask.request.path.startswith('/_s/'):
    return util.jsonify_model_db(user_db)

  return flask.render_template(
      'profile.html',
      title=user_db.name,
      html_class='profile',
      form=form,
      user_db=user_db,
      has_json=True,
    )


###############################################################################
# Feedback
###############################################################################
class FeedbackForm(wtf.Form):
  subject = wtf.StringField('Subject',
      [wtf.validators.required()], filters=[util.strip_filter],
    )
  message = wtf.TextAreaField('Message',
      [wtf.validators.required()], filters=[util.strip_filter],
    )
  email = wtf.StringField('Your email (optional)',
      [wtf.validators.optional(), wtf.validators.email()],
      filters=[util.email_filter],
    )


@app.route('/feedback/', methods=['GET', 'POST'])
def feedback():
  if not config.CONFIG_DB.feedback_email:
    return flask.abort(418)

  form = FeedbackForm(obj=auth.current_user_db())
  if form.validate_on_submit():
    body = '%s\n\n%s' % (form.message.data, form.email.data)
    kwargs = {'reply_to': form.email.data} if form.email.data else {}
    task.send_mail_notification(form.subject.data, body, **kwargs)
    flask.flash('Thank you for your feedback!', category='success')
    return flask.redirect(flask.url_for('welcome'))

  return flask.render_template(
      'feedback.html',
      title='Feedback',
      html_class='feedback',
      form=form,
    )


###############################################################################
# Warmup request
###############################################################################
@app.route('/_ah/warmup')
def warmup():
  # TODO: put your warmup code here
  return 'success'


###############################################################################
# Error Handling
###############################################################################
@app.errorhandler(400)  # Bad Request
@app.errorhandler(401)  # Unauthorized
@app.errorhandler(403)  # Forbidden
@app.errorhandler(404)  # Not Found
@app.errorhandler(405)  # Method Not Allowed
@app.errorhandler(410)  # Gone
@app.errorhandler(418)  # I'm a Teapot
@app.errorhandler(500)  # Internal Server Error
def error_handler(e):
  logging.exception(e)
  try:
    e.code
  except AttributeError:
    e.code = 500
    e.name = 'Internal Server Error'

  if flask.request.path.startswith('/_s/'):
    return util.jsonpify({
        'status': 'error',
        'error_code': e.code,
        'error_name': util.slugify(e.name),
        'error_message': e.name,
        'error_class': e.__class__.__name__,
      }), e.code

  return flask.render_template(
      'error.html',
      title='Error %d (%s)!!1' % (e.code, e.name),
      html_class='error-page',
      error=e,
    ), e.code


if config.PRODUCTION:
  @app.errorhandler(Exception)
  def production_error_handler(e):
    return error_handler(e)

########NEW FILE########
__FILENAME__ = model
# coding: utf-8

from google.appengine.ext import ndb

import config
import modelx
import util


class Base(ndb.Model, modelx.BaseX):
  created = ndb.DateTimeProperty(auto_now_add=True)
  modified = ndb.DateTimeProperty(auto_now=True)
  version = ndb.IntegerProperty(default=config.CURRENT_VERSION_TIMESTAMP)

  _PROPERTIES = {
      'key',
      'id',
      'version',
      'created',
      'modified',
    }


class Config(Base, modelx.ConfigX):
  analytics_id = ndb.StringProperty(default='')
  announcement_html = ndb.TextProperty(default='')
  announcement_type = ndb.StringProperty(default='info', choices=[
      'info', 'warning', 'success', 'danger',
    ])
  brand_name = ndb.StringProperty(default=config.APPLICATION_ID)
  facebook_app_id = ndb.StringProperty(default='')
  facebook_app_secret = ndb.StringProperty(default='')
  feedback_email = ndb.StringProperty(default='')
  flask_secret_key = ndb.StringProperty(default=util.uuid())
  notify_on_new_user = ndb.BooleanProperty(default=True)
  twitter_consumer_key = ndb.StringProperty(default='')
  twitter_consumer_secret = ndb.StringProperty(default='')

  _PROPERTIES = Base._PROPERTIES.union({
      'analytics_id',
      'announcement_html',
      'announcement_type',
      'brand_name',
      'facebook_app_id',
      'facebook_app_secret',
      'feedback_email',
      'flask_secret_key',
      'notify_on_new_user',
      'twitter_consumer_key',
      'twitter_consumer_secret',
    })


class User(Base, modelx.UserX):
  name = ndb.StringProperty(required=True)
  username = ndb.StringProperty(required=True)
  email = ndb.StringProperty(default='')
  auth_ids = ndb.StringProperty(repeated=True)
  active = ndb.BooleanProperty(default=True)
  admin = ndb.BooleanProperty(default=False)
  permissions = ndb.StringProperty(repeated=True)

  _PROPERTIES = Base._PROPERTIES.union({
      'active',
      'admin',
      'auth_ids',
      'avatar_url',
      'email',
      'name',
      'username',
      'permissions',
    })

########NEW FILE########
__FILENAME__ = modelx
# coding: utf-8

import hashlib


class BaseX(object):
  @classmethod
  def retrieve_one_by(cls, name, value):
    return cls.query(getattr(cls, name) == value).get()


class ConfigX(object):
  @classmethod
  def get_master_db(cls):
    return cls.get_or_insert('master')

  @property
  def has_facebook(self):
    return bool(self.facebook_app_id and self.facebook_app_secret)

  @property
  def has_twitter(self):
    return bool(self.twitter_consumer_key and self.twitter_consumer_secret)


class UserX(object):
  def has_permission(self, perm):
    return self.admin or perm in self.permissions

  def avatar_url_size(self, size=None):
    return '//gravatar.com/avatar/%(hash)s?d=identicon&r=x%(size)s' % {
        'hash': hashlib.md5(self.email or self.username).hexdigest(),
        'size': '&s=%d' % size if size > 0 else '',
      }
  avatar_url = property(avatar_url_size)

########NEW FILE########
__FILENAME__ = task
# coding: utf-8

import flask
from google.appengine.api import mail
from google.appengine.ext import deferred

import config


###############################################################################
# Helpers
###############################################################################
def send_mail_notification(subject, body, **kwargs):
  if not config.CONFIG_DB.feedback_email:
    return
  brand_name = config.CONFIG_DB.brand_name
  sender = '%s <%s>' % (brand_name, config.CONFIG_DB.feedback_email)
  subject = '[%s] %s' % (brand_name, subject)
  deferred.defer(mail.send_mail, sender, sender, subject, body, **kwargs)


###############################################################################
# User related
###############################################################################
def new_user_notification(user_db):
  if not config.CONFIG_DB.notify_on_new_user:
    return
  body = 'name: %s\nusername: %s\nemail: %s\n%s\n%s' % (
      user_db.name,
      user_db.username,
      user_db.email,
      ''.join([': '.join(('%s\n' % a).split('_')) for a in user_db.auth_ids]),
      flask.url_for('user_update', user_id=user_db.key.id(), _external=True),
    )
  send_mail_notification('New user: %s' % user_db.name, body)

########NEW FILE########
__FILENAME__ = user
# coding: utf-8

import copy

from flask.ext import wtf
from google.appengine.ext import ndb
import flask

import auth
import model
import util

from main import app


###############################################################################
# User List
###############################################################################
@app.route('/_s/user/', endpoint='user_list_service')
@app.route('/user/')
@auth.admin_required
def user_list():
  user_dbs, more_cursor = util.retrieve_dbs(
      model.User.query(),
      limit=util.param('limit', int),
      cursor=util.param('cursor'),
      order=util.param('order') or '-created',
      admin=util.param('admin', bool),
      active=util.param('active', bool),
      permissions=util.param('permissions', list),
    )

  if flask.request.path.startswith('/_s/'):
    return util.jsonify_model_dbs(user_dbs, more_cursor)

  permissions = list(UserUpdateForm._permission_choices)
  permissions += util.param('permissions', list) or []
  return flask.render_template(
      'user/user_list.html',
      html_class='user-list',
      title='User List',
      user_dbs=user_dbs,
      more_url=util.generate_more_url(more_cursor),
      has_json=True,
      permissions=sorted(set(permissions)),
    )


###############################################################################
# User Update
###############################################################################
class UserUpdateForm(wtf.Form):
  username = wtf.StringField('Username',
      [wtf.validators.required(), wtf.validators.length(min=3)],
      filters=[util.email_filter],
    )
  name = wtf.StringField('Name',
      [wtf.validators.required()], filters=[util.strip_filter],
    )
  email = wtf.StringField('Email',
      [wtf.validators.optional(), wtf.validators.email()],
      filters=[util.email_filter],
    )
  admin = wtf.BooleanField('Admin')
  active = wtf.BooleanField('Active')
  permissions = wtf.SelectMultipleField('Permissions',
      filters=[util.sort_filter],
    )

  _permission_choices = set()

  def __init__(self, *args, **kwds):
    super(UserUpdateForm, self).__init__(*args, **kwds)
    self.permissions.choices = [
        (p, p) for p in sorted(UserUpdateForm._permission_choices)
      ]

  @auth.permission_registered.connect
  def _permission_registered_callback(sender, permission):
    UserUpdateForm._permission_choices.add(permission)


@app.route('/user/<int:user_id>/update/', methods=['GET', 'POST'])
@auth.admin_required
def user_update(user_id):
  user_db = model.User.get_by_id(user_id)
  if not user_db:
    flask.abort(404)

  form = UserUpdateForm(obj=user_db)
  for permission in user_db.permissions:
    form.permissions.choices.append((permission, permission))
  form.permissions.choices = sorted(set(form.permissions.choices))
  if form.validate_on_submit():
    if not util.is_valid_username(form.username.data):
      form.username.errors.append('This username is invalid.')
    elif not is_username_available(form.username.data, user_db):
      form.username.errors.append('This username is already taken.')
    else:
      form.populate_obj(user_db)
      if auth.current_user_id() == user_db.key.id():
        user_db.admin = True
        user_db.active = True
      user_db.put()
      return flask.redirect(flask.url_for(
          'user_list', order='-modified', active=user_db.active,
        ))

  if flask.request.path.startswith('/_s/'):
    return util.jsonify_model_db(user_db)

  return flask.render_template(
      'user/user_update.html',
      title=user_db.name,
      html_class='user-update',
      form=form,
      user_db=user_db,
    )


###############################################################################
# User Delete
###############################################################################
@app.route('/_s/user/delete/', methods=['DELETE'])
@auth.admin_required
def user_delete_service():
  user_keys = util.param('user_keys', list)
  user_db_keys = [ndb.Key(urlsafe=k) for k in user_keys]
  delete_user_dbs(user_db_keys)
  return flask.jsonify({
      'result': user_keys,
      'status': 'success',
    })


@ndb.transactional(xg=True)
def delete_user_dbs(user_db_keys):
  ndb.delete_multi(user_db_keys)


###############################################################################
# User Merge
###############################################################################
class UserMergeForm(wtf.Form):
  user_key = wtf.StringField('User Key', [wtf.validators.required()])
  user_keys = wtf.StringField('User Keys', [wtf.validators.required()])
  username = wtf.StringField('Username', [wtf.validators.optional()])
  name = wtf.StringField('Name (merged)',
      [wtf.validators.required()], filters=[util.strip_filter],
    )
  email = wtf.StringField('Email (merged)',
      [wtf.validators.optional(), wtf.validators.email()],
      filters=[util.email_filter],
    )


@app.route('/_s/user/merge/')
@app.route('/user/merge/', methods=['GET', 'POST'])
@auth.admin_required
def user_merge():
  user_keys = util.param('user_keys', list)
  if not user_keys:
    flask.abort(400)

  user_db_keys = [ndb.Key(urlsafe=k) for k in user_keys]
  user_dbs = ndb.get_multi(user_db_keys)
  if len(user_dbs) < 2:
    flask.abort(400)

  if flask.request.path.startswith('/_s/'):
    return util.jsonify_model_dbs(user_dbs)

  user_dbs.sort(key=lambda user_db: user_db.created)
  merged_user_db = user_dbs[0]
  auth_ids = []
  permissions = []
  is_admin = False
  is_active = False
  for user_db in user_dbs:
    auth_ids.extend(user_db.auth_ids)
    permissions.extend(user_db.permissions)
    is_admin = is_admin or user_db.admin
    is_active = is_active or user_db.active
    if user_db.key.urlsafe() == util.param('user_key'):
      merged_user_db = user_db

  auth_ids = sorted(list(set(auth_ids)))
  permissions = sorted(list(set(permissions)))
  merged_user_db.permissions = permissions
  merged_user_db.admin = is_admin
  merged_user_db.active = is_active

  form_obj = copy.deepcopy(merged_user_db)
  form_obj.user_key = merged_user_db.key.urlsafe()
  form_obj.user_keys = ','.join(user_keys)

  form = UserMergeForm(obj=form_obj)
  if form.validate_on_submit():
    form.populate_obj(merged_user_db)
    merged_user_db.auth_ids = auth_ids
    merged_user_db.put()

    deprecated_keys = [key for key in user_db_keys if key != merged_user_db.key]
    merge_user_dbs(merged_user_db, deprecated_keys)
    return flask.redirect(
        flask.url_for('user_update', user_id=merged_user_db.key.id()),
      )

  return flask.render_template(
      'user/user_merge.html',
      title='Merge Users',
      html_class='user-merge',
      user_dbs=user_dbs,
      merged_user_db=merged_user_db,
      form=form,
      auth_ids=auth_ids,
    )


@ndb.transactional(xg=True)
def merge_user_dbs(user_db, deprecated_keys):
  # TODO: Merge possible user data before handling deprecated users
  deprecated_dbs = ndb.get_multi(deprecated_keys)
  for deprecated_db in deprecated_dbs:
    deprecated_db.auth_ids = []
    deprecated_db.active = False
    if not deprecated_db.username.startswith('_'):
      deprecated_db.username = '_%s' % deprecated_db.username
  ndb.put_multi(deprecated_dbs)


###############################################################################
# Helpers
###############################################################################
def is_username_available(username, self_db=None):
  user_dbs, more_cursor = util.retrieve_dbs(
      model.User.query(),
      username=username,
      limit=2,
    )
  c = len(user_dbs)
  return not (c == 2 or c == 1 and self_db and self_db.key != user_dbs[0].key)

########NEW FILE########
__FILENAME__ = util
# coding: utf-8

from datetime import datetime
from datetime import date
from uuid import uuid4
import re
import unicodedata
import urllib

from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import blobstore
from google.appengine.ext import ndb
import flask

import config


###############################################################################
# Request Parameters
###############################################################################
def param(name, cast=None):
  value = None
  if flask.request.json:
    return flask.request.json.get(name, None)

  if value is None:
    value = flask.request.args.get(name, None)
  if value is None and flask.request.form:
    value = flask.request.form.get(name, None)

  if cast and value is not None:
    if cast == bool:
      return value.lower() in ['true', 'yes', '1', '']
    if cast == list:
      return value.split(',') if len(value) > 0 else []
    return cast(value)
  return value


def get_next_url():
  next_url = param('next')
  if next_url:
    return next_url
  referrer = flask.request.referrer
  if referrer and referrer.startswith(flask.request.host_url):
    return referrer
  return flask.url_for('welcome')


###############################################################################
# Model manipulations
###############################################################################
def retrieve_dbs(
    query, order=None, limit=None, cursor=None, keys_only=None, **filters
  ):
  '''Retrieves entities from datastore, by applying cursor pagination
  and equality filters. Returns dbs or keys and more cursor value
  '''
  limit = limit or config.DEFAULT_DB_LIMIT
  cursor = Cursor.from_websafe_string(cursor) if cursor else None
  model_class = ndb.Model._kind_map[query.kind]
  if order:
    for o in order.split(','):
      if o.startswith('-'):
        query = query.order(-model_class._properties[o[1:]])
      else:
        query = query.order(model_class._properties[o])

  for prop in filters:
    if filters.get(prop, None) is None:
      continue
    if isinstance(filters[prop], list):
      for value in filters[prop]:
        query = query.filter(model_class._properties[prop] == value)
    else:
      query = query.filter(model_class._properties[prop] == filters[prop])

  model_dbs, more_cursor, more = query.fetch_page(
      limit, start_cursor=cursor, keys_only=keys_only,
    )
  more_cursor = more_cursor.to_websafe_string() if more else None
  return list(model_dbs), more_cursor


###############################################################################
# JSON Response Helpers
###############################################################################
def jsonify_model_dbs(model_dbs, more_cursor=None):
  '''Return a response of a list of dbs as JSON service result
  '''
  result_objects = []
  for model_db in model_dbs:
    result_objects.append(model_db_to_object(model_db))

  response_object = {
      'status': 'success',
      'count': len(result_objects),
      'now': datetime.utcnow().isoformat(),
      'result': result_objects,
    }
  if more_cursor:
    response_object['more_cursor'] = more_cursor
    response_object['more_url'] = generate_more_url(more_cursor)
  response = jsonpify(response_object)
  return response


def jsonify_model_db(model_db):
  result_object = model_db_to_object(model_db)
  response = jsonpify({
      'status': 'success',
      'now': datetime.utcnow().isoformat(),
      'result': result_object,
    })
  return response


def model_db_to_object(model_db):
  model_db_object = {}
  for prop in model_db._PROPERTIES:
    if prop == 'id':
      try:
        value = json_value(getattr(model_db, 'key', None).id())
      except:
        value = None
    else:
      value = json_value(getattr(model_db, prop, None))
    if value is not None:
      model_db_object[prop] = value
  return model_db_object


def json_value(value):
  if isinstance(value, datetime) or isinstance(value, date):
    return value.isoformat()
  if isinstance(value, ndb.Key):
    return value.urlsafe()
  if isinstance(value, blobstore.BlobKey):
    return urllib.quote(str(value))
  if isinstance(value, ndb.GeoPt):
    return '%s,%s' % (value.lat, value.lon)
  if isinstance(value, list):
    return [json_value(v) for v in value]
  if isinstance(value, long):
    # Big numbers are sent as strings for accuracy in JavaScript
    if value > 9007199254740992 or value < -9007199254740992:
      return str(value)
  if isinstance(value, ndb.Model):
    return model_db_to_object(value)
  return value


def jsonpify(*args, **kwargs):
  if param('callback'):
    content = '%s(%s)' % (
        param('callback'), flask.jsonify(*args, **kwargs).data,
      )
    mimetype = 'application/javascript'
    return flask.current_app.response_class(content, mimetype=mimetype)
  return flask.jsonify(*args, **kwargs)


###############################################################################
# Helpers
###############################################################################
def generate_more_url(more_cursor, base_url=None, cursor_name='cursor'):
  '''Substitutes or alters the current request URL with a new cursor parameter
  for next page of results
  '''
  if not more_cursor:
    return None
  base_url = base_url or flask.request.base_url
  args = flask.request.args.to_dict()
  args[cursor_name] = more_cursor
  return '%s?%s' % (base_url, urllib.urlencode(args))


def uuid():
  return uuid4().hex


_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')


def slugify(text):
  if not isinstance(text, unicode):
    text = unicode(text)
  text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')
  text = unicode(_slugify_strip_re.sub('', text).strip().lower())
  return _slugify_hyphenate_re.sub('-', text)


def is_valid_username(username):
  return True if re.match('^[a-z0-9]+(?:[\.][a-z0-9]+)*$', username) else False


def update_query_argument(name, value=None, ignore='cursor', is_list=False):
  ignore = ignore.split(',') if isinstance(ignore, str) else ignore or []
  arguments = {}
  for key, val in flask.request.args.items():
    if key not in ignore and (is_list and value is not None or key != name):
      arguments[key] = val
  if value is not None:
    if is_list:
      values = []
      if name in arguments:
        values = arguments[name].split(',')
        del arguments[name]
      if value in values:
        values.remove(value)
      else:
        values.append(value)
      if values:
        arguments[name] = ','.join(values)
    else:
      arguments[name] = value
  query = '&'.join('%s=%s' % item for item in sorted(arguments.items()))
  return '%s%s' % (flask.request.path, '?%s' % query if query else '')


###############################################################################
# Lambdas
###############################################################################
strip_filter = lambda x: x.strip() if x else ''
email_filter = lambda x: x.lower().strip() if x else ''
sort_filter = lambda x: sorted(x) if x else []

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
# coding: utf-8

from datetime import datetime
from distutils import spawn
import argparse
import json
import os
import platform
import shutil
import socket
import sys
import time
import urllib
import urllib2

import main
from main import config


###############################################################################
# Options
###############################################################################
PARSER = argparse.ArgumentParser()
PARSER.add_argument(
    '-w', '--watch', dest='watch', action='store_true',
    help='watch files for changes when running the development web server',
  )
PARSER.add_argument(
    '-c', '--clean', dest='clean', action='store_true',
    help='recompiles files when running the development web server',
  )
PARSER.add_argument(
    '-C', '--clean-all', dest='clean_all', action='store_true',
    help='''Cleans all the pip, Node & Bower related tools / libraries and
    updates them to their latest versions''',
  )
PARSER.add_argument(
    '-m', '--minify', dest='minify', action='store_true',
    help='compiles files into minified version before deploying'
  )
PARSER.add_argument(
    '-s', '--start', dest='start', action='store_true',
    help='starts the dev_appserver.py with storage_path pointing to temp',
  )
PARSER.add_argument(
    '-o', '--host', dest='host', action='store', default='127.0.0.1',
    help='the host to start the dev_appserver.py',
  )
PARSER.add_argument(
    '-p', '--port', dest='port', action='store', default='8080',
    help='the port to start the dev_appserver.py',
  )
PARSER.add_argument(
    '-f', '--flush', dest='flush', action='store_true',
    help='clears the datastore, blobstore, etc',
  )
PARSER.add_argument(
    '--appserver-args', dest='args', nargs=argparse.REMAINDER, default=[],
    help='all following args are passed to dev_appserver.py',
  )
ARGS = PARSER.parse_args()


###############################################################################
# Directories
###############################################################################
DIR_BOWER_COMPONENTS = 'bower_components'
DIR_MAIN = 'main'
DIR_NODE_MODULES = 'node_modules'
DIR_STYLE = 'style'
DIR_SCRIPT = 'script'
DIR_TEMP = 'temp'
DIR_VENV = os.path.join(DIR_TEMP, 'venv')

DIR_STATIC = os.path.join(DIR_MAIN, 'static')

DIR_SRC = os.path.join(DIR_STATIC, 'src')
DIR_SRC_SCRIPT = os.path.join(DIR_SRC, DIR_SCRIPT)
DIR_SRC_STYLE = os.path.join(DIR_SRC, DIR_STYLE)

DIR_DST = os.path.join(DIR_STATIC, 'dst')
DIR_DST_STYLE = os.path.join(DIR_DST, DIR_STYLE)
DIR_DST_SCRIPT = os.path.join(DIR_DST, DIR_SCRIPT)

DIR_MIN = os.path.join(DIR_STATIC, 'min')
DIR_MIN_STYLE = os.path.join(DIR_MIN, DIR_STYLE)
DIR_MIN_SCRIPT = os.path.join(DIR_MIN, DIR_SCRIPT)

DIR_LIB = os.path.join(DIR_MAIN, 'lib')
DIR_LIBX = os.path.join(DIR_MAIN, 'libx')
FILE_LIB = '%s.zip' % DIR_LIB
FILE_REQUIREMENTS = 'requirements.txt'
FILE_BOWER = 'bower.json'
FILE_PACKAGE = 'package.json'
FILE_PIP_GUARD = os.path.join(DIR_TEMP, 'pip.guard')
FILE_NPM_GUARD = os.path.join(DIR_TEMP, 'npm.guard')
FILE_BOWER_GUARD = os.path.join(DIR_TEMP, 'bower.guard')

DIR_BIN = os.path.join(DIR_NODE_MODULES, '.bin')
FILE_COFFEE = os.path.join(DIR_BIN, 'coffee')
FILE_GRUNT = os.path.join(DIR_BIN, 'grunt')
FILE_LESS = os.path.join(DIR_BIN, 'lessc')
FILE_UGLIFYJS = os.path.join(DIR_BIN, 'uglifyjs')
FILE_VENV = os.path.join(DIR_VENV, 'Scripts', 'activate.bat') \
    if platform.system() is 'Windows' \
    else os.path.join(DIR_VENV, 'bin', 'activate')

DIR_STORAGE = os.path.join(DIR_TEMP, 'storage')
FILE_UPDATE = os.path.join(DIR_TEMP, 'update.json')


###############################################################################
# Other global variables
###############################################################################
REQUIREMENTS_URL = 'http://docs.gae-init.appspot.com/requirement/'


###############################################################################
# Helpers
###############################################################################
def print_out(script, filename=''):
  timestamp = datetime.now().strftime('%H:%M:%S')
  if not filename:
    filename = '-' * 46
    script = script.rjust(12, '-')
  print '[%s] %12s %s' % (timestamp, script, filename)


def make_dirs(directory):
  if not os.path.exists(directory):
    os.makedirs(directory)


def remove_file_dir(file_dir):
  if os.path.exists(file_dir):
    if os.path.isdir(file_dir):
      shutil.rmtree(file_dir)
    else:
      os.remove(file_dir)


def clean_files():
  bad_endings = ['pyc', 'pyo', '~']
  print_out(
      'CLEAN FILES',
      'Removing files: %s' % ', '.join(['*%s' % e for e in bad_endings]),
    )
  for root, _, files in os.walk('.'):
    for filename in files:
      for bad_ending in bad_endings:
        if filename.endswith(bad_ending):
          remove_file_dir(os.path.join(root, filename))


def merge_files(source, target):
  fout = open(target, 'a')
  for line in open(source):
    fout.write(line)
  fout.close()


def os_execute(executable, args, source, target, append=False):
  operator = '>>' if append else '>'
  os.system('"%s" %s %s %s %s' % (executable, args, source, operator, target))


def compile_script(source, target_dir):
  if not os.path.isfile(source):
    print_out('NOT FOUND', source)
    return

  target = source.replace(DIR_SRC_SCRIPT, target_dir).replace('.coffee', '.js')
  if not is_dirty(source, target):
    return
  make_dirs(os.path.dirname(target))
  if not source.endswith('.coffee'):
    print_out('COPYING', source)
    shutil.copy(source, target)
    return
  print_out('COFFEE', source)
  os_execute(FILE_COFFEE, '-cp', source, target)


def compile_style(source, target_dir, check_modified=False):
  if not os.path.isfile(source):
    print_out('NOT FOUND', source)
    return
  if not source.endswith('.less'):
    return

  target = source.replace(DIR_SRC_STYLE, target_dir).replace('.less', '.css')
  if check_modified and not is_style_modified(target):
    return

  minified = ''
  if target_dir == DIR_MIN_STYLE:
    minified = '-x'
    target = target.replace('.css', '.min.css')
    print_out('LESS MIN', source)
  else:
    print_out('LESS', source)

  make_dirs(os.path.dirname(target))
  os_execute(FILE_LESS, minified, source, target)


def make_lib_zip(force=False):
  if force and os.path.isfile(FILE_LIB):
    remove_file_dir(FILE_LIB)
  if not os.path.isfile(FILE_LIB):
    if os.path.exists(DIR_LIB):
      print_out('ZIP', FILE_LIB)
      shutil.make_archive(DIR_LIB, 'zip', DIR_LIB)
    else:
      print_out('NOT FOUND', DIR_LIB)


def is_dirty(source, target):
  if not os.access(target, os.O_RDONLY):
    return True
  return os.stat(source).st_mtime - os.stat(target).st_mtime > 0


def is_style_modified(target):
  for root, _, files in os.walk(DIR_SRC):
    for filename in files:
      path = os.path.join(root, filename)
      if path.endswith('.less') and is_dirty(path, target):
        return True
  return False


def compile_all_dst():
  for source in config.STYLES:
    compile_style(os.path.join(DIR_STATIC, source), DIR_DST_STYLE, True)
  for _, scripts in config.SCRIPTS:
    for source in scripts:
      compile_script(os.path.join(DIR_STATIC, source), DIR_DST_SCRIPT)


def update_path_separators():
  def fixit(path):
    return path.replace('\\', '/').replace('/', os.sep)

  for idx in xrange(len(config.STYLES)):
    config.STYLES[idx] = fixit(config.STYLES[idx])

  for _, scripts in config.SCRIPTS:
    for idx in xrange(len(scripts)):
      scripts[idx] = fixit(scripts[idx])


def listdir(directory, split_ext=False):
  try:
    if split_ext:
      return [os.path.splitext(dir_)[0] for dir_ in os.listdir(directory)]
    else:
      return os.listdir(directory)
  except OSError:
    return []


def site_packages_path():
  if platform.system() == 'Windows':
    return os.path.join(DIR_VENV, 'Lib', 'site-packages')
  py_version = 'python%s.%s' % sys.version_info[:2]
  return os.path.join(DIR_VENV, 'lib', py_version, 'site-packages')


def create_virtualenv(is_windows):
  if not os.path.exists(FILE_VENV):
    os.system('virtualenv --no-site-packages %s' % DIR_VENV)
    os.system('echo %s >> %s' % (
        'set PYTHONPATH=' if is_windows else 'unset PYTHONPATH', FILE_VENV
      ))
    gae_path = find_gae_path()
    pth_file = os.path.join(site_packages_path(), 'gae.pth')
    echo_to = 'echo %s >> {pth}'.format(pth=pth_file)
    os.system(echo_to % gae_path)
    os.system(echo_to % os.path.abspath(DIR_LIBX))
    fix_path_cmd = 'import dev_appserver; dev_appserver.fix_sys_path()'
    os.system(echo_to % (
        fix_path_cmd if is_windows else '"%s"' % fix_path_cmd
      ))
  return True


def exec_pip_commands(command):
  is_windows = platform.system() == 'Windows'
  script = []
  if create_virtualenv(is_windows):
    activate_cmd = 'call %s' if is_windows else 'source %s'
    activate_cmd %= FILE_VENV
    script.append(activate_cmd)

  script.append('echo %s' % command)
  script.append(command)
  script = '&'.join(script) if is_windows else \
      '/bin/bash -c "%s"' % ';'.join(script)
  os.system(script)


def check_pip_should_run():
  if not os.path.exists(FILE_PIP_GUARD):
    return True
  return os.path.getmtime(FILE_PIP_GUARD) < \
      os.path.getmtime(FILE_REQUIREMENTS)


def check_npm_should_run():
  if not os.path.exists(FILE_NPM_GUARD):
    return True
  return os.path.getmtime(FILE_NPM_GUARD) < os.path.getmtime(FILE_PACKAGE)


def check_bower_should_run():
  if not os.path.exists(FILE_BOWER_GUARD):
    return True
  return os.path.getmtime(FILE_BOWER_GUARD) < os.path.getmtime(FILE_BOWER)


def install_py_libs():
  if not check_pip_should_run():
    return

  exec_pip_commands('pip install -q -r %s' % FILE_REQUIREMENTS)

  exclude_ext = ['.pth', '.pyc', '.egg-info', '.dist-info']
  exclude_prefix = ['setuptools-', 'pip-', 'Pillow-']
  exclude = [
      'test', 'tests', 'pip', 'setuptools', '_markerlib', 'PIL',
      'easy_install.py', 'pkg_resources.py'
    ]

  def _exclude_prefix(pkg):
    for prefix in exclude_prefix:
      if pkg.startswith(prefix):
        return True
    return False

  def _exclude_ext(pkg):
    for ext in exclude_ext:
      if pkg.endswith(ext):
        return True
    return False

  def _get_dest(pkg):
    make_dirs(DIR_LIB)
    return os.path.join(DIR_LIB, pkg)

  site_packages = site_packages_path()
  dir_libs = listdir(DIR_LIB)
  dir_libs.extend(listdir(DIR_LIBX))
  for dir_ in listdir(site_packages):
    if dir_ in dir_libs or dir_ in exclude:
      continue
    if _exclude_prefix(dir_) or _exclude_ext(dir_):
      continue
    src_path = os.path.join(site_packages, dir_)
    copy = shutil.copy if os.path.isfile(src_path) else shutil.copytree
    copy(src_path, _get_dest(dir_))

  with open(FILE_PIP_GUARD, 'w') as pip_guard:
    pip_guard.write('Prevents pip execution if newer than requirements.txt')


def clean_py_libs():
  remove_file_dir(DIR_LIB)
  remove_file_dir(DIR_VENV)


def install_dependencies():
  make_dirs(DIR_TEMP)
  if check_npm_should_run():
    with open(FILE_NPM_GUARD, 'w') as npm_guard:
      npm_guard.write('Prevents npm execution if newer than package.json')
    os.system('npm install')

  if check_bower_should_run():
    with open(FILE_BOWER_GUARD, 'w') as bower_guard:
      bower_guard.write('Prevents bower execution if newer than bower.json')
    os.system('"%s" ext' % FILE_GRUNT)

  install_py_libs()


def check_for_update():
  if os.path.exists(FILE_UPDATE):
    mtime = os.path.getmtime(FILE_UPDATE)
    last = datetime.utcfromtimestamp(mtime).strftime('%Y-%m-%d')
    today = datetime.utcnow().strftime('%Y-%m-%d')
    if last == today:
      return
  try:
    request = urllib2.Request(
        'https://gae-init.appspot.com/_s/version/',
        urllib.urlencode({'version': main.__version__}),
      )
    response = urllib2.urlopen(request)
    with open(FILE_UPDATE, 'w') as update_json:
      update_json.write(response.read())
  except urllib2.HTTPError:
    pass


def print_out_update():
  try:
    with open(FILE_UPDATE, 'r') as update_json:
      data = json.load(update_json)
    if main.__version__ < data['version']:
      print_out('UPDATE')
      print_out(data['version'], 'Latest version of gae-init')
      print_out(main.__version__, 'Your version is a bit behind')
      print_out('CHANGESET', data['changeset'])
  except (ValueError, KeyError):
    os.remove(FILE_UPDATE)
  except IOError:
    pass


def update_missing_args():
  if ARGS.start or ARGS.clean_all:
    ARGS.clean = True


def uniq(seq):
  seen = set()
  return [e for e in seq if e not in seen and not seen.add(e)]


###############################################################################
# Doctor
###############################################################################
def internet_on():
  try:
    urllib2.urlopen('http://74.125.228.100', timeout=2)
    return True
  except (urllib2.URLError, socket.timeout):
    return False


def check_requirement(check_func):
  result, name, help_url_id = check_func()
  if not result:
    print_out('NOT FOUND', name)
    if help_url_id:
      print 'Please see %s%s' % (REQUIREMENTS_URL, help_url_id)
    return False
  return True


def find_gae_path():
  is_windows = platform.system() == 'Windows'
  if is_windows:
    gae_path = None
    for path in os.environ['PATH'].split(os.pathsep):
      if os.path.isfile(os.path.join(path, 'dev_appserver.py')):
        gae_path = path
  else:
    gae_path = spawn.find_executable('dev_appserver.py')
    if gae_path:
      gae_path = os.path.dirname(os.path.realpath(gae_path))
  if not gae_path:
    return ''
  gcloud_exec = 'gcloud.cmd' if is_windows else 'gcloud'
  if not os.path.isfile(os.path.join(gae_path, gcloud_exec)):
    return gae_path
  gae_path = os.path.join(gae_path, '..', 'platform', 'google_appengine')
  if os.path.exists:
    return os.path.realpath(gae_path)
  return ''


def check_internet():
  return internet_on(), 'Internet', ''


def check_gae():
  return bool(find_gae_path()), 'Google App Engine SDK', '#gae'


def check_git():
  return bool(spawn.find_executable('git')), 'Git', '#git'


def check_nodejs():
  return bool(spawn.find_executable('node')), 'Node.js', '#nodejs'


def check_pip():
  return bool(spawn.find_executable('pip')), 'pip', '#pip'


def check_virtualenv():
  return bool(spawn.find_executable('virtualenv')), 'virtualenv', '#virtualenv'


def doctor_says_ok():
  checkers = [check_gae, check_git, check_nodejs, check_pip, check_virtualenv]
  if False in [check_requirement(check) for check in checkers]:
    sys.exit(1)
  return check_requirement(check_internet)


###############################################################################
# Main
###############################################################################
def run_clean():
  print_out('CLEAN')
  clean_files()
  make_lib_zip(force=True)
  remove_file_dir(DIR_DST)
  make_dirs(DIR_DST)
  compile_all_dst()
  print_out('DONE')


def run_clean_all():
  print_out('CLEAN ALL')
  remove_file_dir(DIR_BOWER_COMPONENTS)
  remove_file_dir(DIR_NODE_MODULES)
  clean_py_libs()
  clean_files()
  remove_file_dir(FILE_LIB)
  remove_file_dir(FILE_PIP_GUARD)
  remove_file_dir(FILE_NPM_GUARD)
  remove_file_dir(FILE_BOWER_GUARD)


def run_minify():
  print_out('MINIFY')
  clean_files()
  make_lib_zip(force=True)
  remove_file_dir(DIR_MIN)
  make_dirs(DIR_MIN_SCRIPT)

  for source in config.STYLES:
    compile_style(os.path.join(DIR_STATIC, source), DIR_MIN_STYLE)

  for module, scripts in config.SCRIPTS:
    scripts = uniq(scripts)
    coffees = ' '.join([
        os.path.join(DIR_STATIC, script)
        for script in scripts if script.endswith('.coffee')
      ])

    pretty_js = os.path.join(DIR_MIN_SCRIPT, '%s.js' % module)
    ugly_js = os.path.join(DIR_MIN_SCRIPT, '%s.min.js' % module)
    print_out('COFFEE MIN', ugly_js)

    if len(coffees):
      os_execute(FILE_COFFEE, '--join -cp', coffees, pretty_js, append=True)
    for script in scripts:
      if not script.endswith('.js'):
        continue
      script_file = os.path.join(DIR_STATIC, script)
      merge_files(script_file, pretty_js)
    os_execute(FILE_UGLIFYJS, pretty_js, '-cm', ugly_js)
    remove_file_dir(pretty_js)
  print_out('DONE')


def run_watch():
  print_out('WATCHING')
  make_lib_zip()
  make_dirs(DIR_DST)

  compile_all_dst()
  print_out('DONE', 'and watching for changes (Ctrl+C to stop)')
  while True:
    time.sleep(0.5)
    reload(config)
    update_path_separators()
    compile_all_dst()


def run_flush():
  remove_file_dir(DIR_STORAGE)
  print_out('STORAGE CLEARED')


def run_start():
  make_dirs(DIR_STORAGE)
  clear = 'yes' if ARGS.flush else 'no'
  port = int(ARGS.port)
  run_command = '''
      dev_appserver.py %s
      --host %s
      --port %s
      --admin_port %s
      --storage_path=%s
      --clear_datastore=%s
      --skip_sdk_update_check
      %s
    ''' % (DIR_MAIN, ARGS.host, port, port + 1, DIR_STORAGE, clear,
           " ".join(ARGS.args))
  os.system(run_command.replace('\n', ' '))


def run():
  if len(sys.argv) == 1 or (ARGS.args and not ARGS.start):
    PARSER.print_help()
    sys.exit(1)

  os.chdir(os.path.dirname(os.path.realpath(__file__)))

  update_path_separators()
  update_missing_args()

  if ARGS.clean_all:
    run_clean_all()

  if doctor_says_ok():
    install_dependencies()
    check_for_update()

  print_out_update()

  if ARGS.clean:
    run_clean()

  if ARGS.minify:
    run_minify()

  if ARGS.watch:
    run_watch()

  if ARGS.flush:
    run_flush()

  if ARGS.start:
    run_start()


if __name__ == '__main__':
  run()

########NEW FILE########
