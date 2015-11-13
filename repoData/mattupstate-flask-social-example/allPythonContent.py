__FILENAME__ = assets

from flask.ext.assets import Bundle

from . import app, webassets

js_libs = Bundle("js/libs/jquery-1.7.1.min.js",
                 "js/libs/bootstrap.min.js",
                 filters="jsmin",
                 output="js/libs.js")

js_main = Bundle("js/src/main.js",
                 filters="jsmin",
                 output="js/main.js")

css_less = Bundle("css/src/styles.less",
                  filters="less",
                  output="css/styles.css",
                  debug=False)

css_main = Bundle(Bundle("css/bootstrap.min.css"),
                  css_less,
                  filters="cssmin",
                  output="css/main.css")


webassets.manifest = 'cache' if not app.debug else False
webassets.cache = not app.debug
webassets.debug = app.debug

webassets.register('js_libs', js_libs)
webassets.register('js_main', js_main)
webassets.register('css_main', css_main)

########NEW FILE########
__FILENAME__ = forms

from flask import current_app
from flask.ext.wtf import Form
from wtforms import TextField, PasswordField, ValidationError
from wtforms.validators import Required, Email, Length, Regexp, EqualTo

class UniqueUser(object):
    def __init__(self, message="User exists"):
        self.message = message

    def __call__(self, form, field):
        if current_app.security.datastore.find_user(email=field.data):
            raise ValidationError(self.message)


validators = {
    'email': [
        Required(),
        Email(),
        UniqueUser(message='Email address is associated with '
                           'an existing account')
    ],
    'password': [
        Required(),
        Length(min=6, max=50),
        EqualTo('confirm', message='Passwords must match'),
        Regexp(r'[A-Za-z0-9@#$%^&+=]',
               message='Password contains invalid characters')
    ]
}


class RegisterForm(Form):
    email = TextField('Email', validators['email'])
    password = PasswordField('Password', validators['password'], )
    confirm = PasswordField('Confirm Password')

########NEW FILE########
__FILENAME__ = github


import github3

config = {
    'id': 'github',
    'name': 'GitHub',
    'install': 'pip install github3.py',
    'module': 'app.github',
    'base_url': 'https://api.github.com/',
    'request_token_url': None,
    'access_token_url': 'https://github.com/login/oauth/access_token',
    'authorize_url': 'https://github.com/login/oauth/authorize',
    'request_token_params': {
        'scope': 'user'
    }
}


def get_api(connection, **kwargs):
    return github3.login(token=getattr(connection, 'access_token'))


def get_provider_user_id(response, **kwargs):
    print 'get_provider_user_id:'
    if response:
        gh = github3.login(token=response['access_token'])
        return str(gh.user().to_json()['id'])
    return None


def get_connection_values(response, **kwargs):
    if not response:
        return None

    access_token = response['access_token']
    gh = github3.login(token=access_token)
    user = gh.user().to_json()

    return dict(
        provider_id=config['id'],
        provider_user_id=str(user['id']),
        access_token=access_token,
        secret=None,
        display_name=user['login'],
        profile_url=user['html_url'],
        image_url=user['avatar_url']
    )

########NEW FILE########
__FILENAME__ = helpers
import os
import yaml

from flask import Flask as BaseFlask, Config as BaseConfig


class Config(BaseConfig):

    def from_heroku(self):
        # Register database schemes in URLs.
        for key in ['DATABASE_URL']:
            if key in os.environ:
                self['SQLALCHEMY_DATABASE_URI'] = os.environ[key]
                break

        for key in ['SECRET_KEY', 'GOOGLE_ANALYTICS_ID', 'ADMIN_CREDENTIALS', 'SECURITY_PASSWORD_SALT']:
            if key in os.environ:
                self[key] = os.environ[key]

        for key_prefix in ['TWITTER', 'FACEBOOK', 'GITHUB']:
            for key_suffix in ['key', 'secret']:
                ev = '%s_CONSUMER_%s' % (key_prefix, key_suffix.upper())
                if ev in os.environ:
                    social_key = 'SOCIAL_' + key_prefix
                    oauth_key = 'consumer_' + key_suffix
                    self[social_key][oauth_key] = os.environ[ev]

    def from_yaml(self, root_path):
        env = os.environ.get('FLASK_ENV', 'development').upper()
        self['ENVIRONMENT'] = env.lower()

        for fn in ('app', 'credentials'):
            config_file = os.path.join(root_path, 'config', '%s.yml' % fn)

            try:
                with open(config_file) as f:
                    c = yaml.load(f)

                c = c.get(env, c)

                for key in c.iterkeys():
                    if key.isupper():
                        self[key] = c[key]
            except:
                pass


class Flask(BaseFlask):
    """Extended version of `Flask` that implements custom config class
    and adds `register_middleware` method"""

    def make_config(self, instance_relative=False):
        root_path = self.root_path
        if instance_relative:
            root_path = self.instance_path
        return Config(root_path, self.default_config)

    def register_middleware(self, middleware_class):
        """Register a WSGI middleware on the application
        :param middleware_class: A WSGI middleware implementation
        """
        self.wsgi_app = middleware_class(self.wsgi_app)

########NEW FILE########
__FILENAME__ = middleware
from werkzeug import url_decode


class MethodRewriteMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if 'METHOD_OVERRIDE' in environ.get('QUERY_STRING', ''):
            args = url_decode(environ['QUERY_STRING'])
            method = args.get('__METHOD_OVERRIDE__')
            if method:
                method = method.encode('ascii', 'replace')
                environ['REQUEST_METHOD'] = method
        return self.app(environ, start_response)

########NEW FILE########
__FILENAME__ = models

from flask.ext.security import UserMixin, RoleMixin

from . import db


roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('roles.id')))


class Role(db.Model, RoleMixin):

    __tablename__ = "roles"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(120))
    active = db.Column(db.Boolean())
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)
    roles = db.relationship('Role', secondary=roles_users,
            backref=db.backref('users', lazy='dynamic'))
    connections = db.relationship('Connection',
            backref=db.backref('user', lazy='joined'), cascade="all")


class Connection(db.Model):

    __tablename__ = "connections"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    provider_id = db.Column(db.String(255))
    provider_user_id = db.Column(db.String(255))
    access_token = db.Column(db.String(255))
    secret = db.Column(db.String(255))
    display_name = db.Column(db.String(255))
    full_name = db.Column(db.String(255))
    profile_url = db.Column(db.String(512))
    image_url = db.Column(db.String(512))
    rank = db.Column(db.Integer)

########NEW FILE########
__FILENAME__ = tools

from functools import wraps

from flask import Response, current_app, request


def check_auth(username, password):
    creds = current_app.config['ADMIN_CREDENTIALS'].split(',')
    return username == creds[0] and password == creds[1]


def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

########NEW FILE########
__FILENAME__ = views
from flask import render_template, redirect, request, current_app, session, \
    flash, url_for
from flask.ext.security import LoginForm, current_user, login_required, \
    login_user
from flask.ext.social.utils import get_provider_or_404
from flask.ext.social.views import connect_handler

from . import app, db
from .forms import RegisterForm
from .models import User
from .tools import requires_auth


@app.route('/')
def index():
    return render_template('index.html', total_users=User.query.count())


@app.route('/login')
def login():
    if current_user.is_authenticated():
        return redirect(request.referrer or '/')

    return render_template('login.html', form=LoginForm())


@app.route('/register', methods=['GET', 'POST'])
@app.route('/register/<provider_id>', methods=['GET', 'POST'])
def register(provider_id=None):
    if current_user.is_authenticated():
        return redirect(request.referrer or '/')

    form = RegisterForm()

    if provider_id:
        provider = get_provider_or_404(provider_id)
        connection_values = session.get('failed_login_connection', None)
    else:
        provider = None
        connection_values = None

    if form.validate_on_submit():
        ds = current_app.security.datastore
        user = ds.create_user(email=form.email.data, password=form.password.data)
        ds.commit()

        # See if there was an attempted social login prior to registering
        # and if so use the provider connect_handler to save a connection
        connection_values = session.pop('failed_login_connection', None)

        if connection_values:
            connection_values['user_id'] = user.id
            connect_handler(connection_values, provider)

        if login_user(user):
            ds.commit()
            flash('Account created successfully', 'info')
            return redirect(url_for('profile'))

        return render_template('thanks.html', user=user)

    login_failed = int(request.args.get('login_failed', 0))

    return render_template('register.html',
                           form=form,
                           provider=provider,
                           login_failed=login_failed,
                           connection_values=connection_values)


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html',
        twitter_conn=current_app.social.twitter.get_connection(),
        facebook_conn=current_app.social.facebook.get_connection(),
        github_conn=current_app.social.github.get_connection())


@app.route('/profile/<provider_id>/post', methods=['POST'])
@login_required
def social_post(provider_id):
    message = request.form.get('message', None)

    if message:
        provider = get_provider_or_404(provider_id)
        api = provider.get_api()

        if provider_id == 'twitter':
            display_name = 'Twitter'
            api.PostUpdate(message)
        if provider_id == 'facebook':
            display_name = 'Facebook'
            api.put_object("me", "feed", message=message)

        flash('Message posted to %s: %s' % (display_name, message), 'info')

    return redirect(url_for('profile'))


@app.route('/admin')
@requires_auth
def admin():
    users = User.query.all()
    return render_template('admin.html', users=users)


@app.route('/admin/users/<user_id>', methods=['DELETE'])
@requires_auth
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully', 'info')
    return redirect(url_for('admin'))

########NEW FILE########
__FILENAME__ = manage
from flask.ext.assets import ManageAssets
from flask.ext.script import Manager
from flask.ext.security.script import CreateUserCommand

from app import create_app

manager = Manager(create_app())
manager.add_command("assets", ManageAssets())
manager.add_command('create_user', CreateUserCommand())

if __name__ == "__main__":
    manager.run()
########NEW FILE########
__FILENAME__ = wsgi

import os

from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

########NEW FILE########
