__FILENAME__ = app
from flask import Flask
from os import environ, path as op

from .config import production


def create_app(config=None, **settings):
    app = Flask(__name__)
    app.config.from_envvar("APP_SETTINGS", silent=True)
    app.config.from_object(config or production)

    # Settings from mode
    mode = environ.get('MODE')
    if mode:
        app.config.from_object('base.config.%s' % mode)

    # Local settings
    app.config.from_pyfile(op.join(op.dirname(production.__file__), 'local.py'), silent=True)

    # Overide settings
    app.config.update(settings)

    with app.test_request_context():

        from .ext import config_extensions
        config_extensions(app)

        from .loader import loader
        loader.register(app)

    return app

########NEW FILE########
__FILENAME__ = admin
from flask_admin.contrib.sqlamodel import ModelView
from flask_wtf import PasswordField, required

from ..core.ext import admin
from .models import User, Role, Key


class UserView(ModelView):
    column_filters = 'username', 'email'
    column_list = 'username', 'email', 'active', 'created_at', 'updated_at'
    form_excluded_columns = 'oauth_token', 'oauth_secret', '_pw_hash'

    def scaffold_form(self):
        form = super(UserView, self).scaffold_form()
        form.pw_hash = PasswordField(validators=[required()])
        form.roles.kwargs['validators'] = []
        return form

admin.add_model(User, UserView)
admin.add_model(Role)
admin.add_model(Key)

########NEW FILE########
__FILENAME__ = forms
from flask import request
from flaskext.babel import lazy_gettext as _
from flask_wtf import Form, TextField, PasswordField, Required, Email, EqualTo, BooleanField, HiddenField, SubmitField


class EmailFormMixin():
    email = TextField(_('Email address'),
                      validators=[Required(message=_("Email not provided")),
                                  Email(message=_("Invalid email address"))])


class PasswordFormMixin():
    password = PasswordField(_("Password"),
                             validators=[Required(message=_("Password not provided"))])


class PasswordConfirmFormMixin():
    password_confirm = PasswordField(_("Retype Password"),
                                     validators=[EqualTo('password', message=_("Passwords do not match"))])


class LoginForm(Form, EmailFormMixin, PasswordFormMixin):
    " The default login form. "

    remember = BooleanField(_("Remember Me"), default=True)
    next = HiddenField()
    submit = SubmitField(_("Login"))

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)

        if request.method == 'GET':
            self.next.data = request.args.get('next', None)


class ForgotPasswordForm(Form, EmailFormMixin):
    "  The default forgot password form. "

    submit = SubmitField(_("Recover Password"))

    def to_dict(self):
        return dict(email=self.email.data)


class RegisterForm(Form, EmailFormMixin, PasswordFormMixin, PasswordConfirmFormMixin):
    "  The default register form. "

    username = TextField(_('UserName'), [Required(message=_('Required'))])
    # submit = SubmitField(_("Register"))

    def to_dict(self):
        return dict(email=self.email.data, password=self.password.data)


class ResetPasswordForm(Form,
                        EmailFormMixin,
                        PasswordFormMixin,
                        PasswordConfirmFormMixin):
    "  The default reset password form. "

    token = HiddenField(validators=[Required()])

    submit = SubmitField(_("Reset Password"))

    def __init__(self, *args, **kwargs):
        super(ResetPasswordForm, self).__init__(*args, **kwargs)

        if request.method == 'GET':
            self.token.data = request.args.get('token', None)
            self.email.data = request.args.get('email', None)

    def to_dict(self):
        return dict(token=self.token.data,
                    email=self.email.data,
                    password=self.password.data)


# pymode:lint_ignore=F0401

########NEW FILE########
__FILENAME__ = manage
"""Flask-Script support.
"""
from flask_script import prompt_pass, Manager


auth_manager = Manager(usage='Authentication operations.')


def loader_meta(manager):
    " Register submanager with loader as manager init. "

    manager.add_command('auth', auth_manager)


@auth_manager.option('username')
@auth_manager.option('email')
@auth_manager.option('-a', '--active', dest='active', action='store_true')
@auth_manager.option('-p', '--password', dest='password', default='')
def create_user(username=None, email=None, active=False, password=''):
    " Create a user. "

    from .models import User
    from ..ext import db

    password = password or prompt_pass("Set password")
    user = User(username=username,
                email=email,
                pw_hash=password,
                active=active)

    db.session.add(user)
    db.session.commit()

    print 'User created successfully.'


@auth_manager.option('name')
def create_role(name):
    " Create a role. "

    from .models import Role
    from ..ext import db

    role = Role(name=name)

    db.session.add(role)
    db.session.commit()

    print 'Role "%s" created successfully.' % name


@auth_manager.option('username')
@auth_manager.option('role')
def add_role(username, role):
    " Add a role to a user. "

    from .models import User, Role
    from ..ext import db

    u = User.query.filter_by(username=username).first()
    r = Role.query.filter_by(name=role).first()
    if u and r:
        u.roles.append(r)
        db.session.add(u)
        db.session.commit()
        print "Role '%s' added to user '%s' successfully" % (
            role, username)


@auth_manager.option('username')
@auth_manager.option('role')
def remove_role(username, role):
    " Remove a role from user. "

    from .models import User, Role
    from ..ext import db

    u = User.query.filter_by(username=username).first()
    r = Role.query.filter_by(name=role).first()
    if r in u.roles:
        u.roles.remove(r)
        db.session.add(u)
        db.session.commit()
    print "Role '%s' removed from user '%s' successfully" % (
        role, username)

# pymode:lint_ignore=F0401

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from flask_login import UserMixin
from flask_principal import RoleNeed, Permission
from flask_squll import _BoundDeclarativeMeta
from random import choice
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug import check_password_hash, generate_password_hash

from ..core.models import BaseMixin
from ..ext import db


PSYMBOLS = 'abcdefghijklmnopqrstuvwxyz123456789'

userroles = db.Table(
    'auth_userroles',
    db.Column('user_id', db.Integer, db.ForeignKey('auth_user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('auth_role.id'))
)


class Role(db.Model, BaseMixin):
    " User roles. "

    __tablename__ = 'auth_role'

    name = db.Column(db.String(19), nullable=False, unique=True)

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return '<Role %r>' % (self.name)


class UserMixinMeta(_BoundDeclarativeMeta):
    " Dynamic mixin from app configuration. "

    def __new__(mcs, name, bases, params):
        from flask import current_app
        from importlib import import_module

        if current_app and current_app.config.get('AUTH_USER_MIXINS'):
            for mixin in current_app.config.get('AUTH_USER_MIXINS'):
                mod, cls = mixin.rsplit('.', 1)
                mod = import_module(mod)
                cls = getattr(mod, cls)
                bases = bases + (cls, )

        return super(UserMixinMeta, mcs).__new__(mcs, name, bases, params)


class User(db.Model, UserMixin, BaseMixin):
    """ Main User database model.

        Extend that uses `AUTH_USER_MIXINS` option.
    """

    __tablename__ = 'auth_user'
    __metaclass__ = UserMixinMeta

    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120))
    active = db.Column(db.Boolean, default=True)
    _pw_hash = db.Column(db.String(199), nullable=False)

    @declared_attr
    def roles(self):
        assert self
        return db.relationship("Role", secondary=userroles, backref="users")

    @hybrid_property
    def pw_hash(self):
        """Simple getter function for the user's password."""
        return self._pw_hash

    @pw_hash.setter
    def pw_hash(self, raw_password):
        """ Password setter, that handles the hashing
            in the database.
        """
        self._pw_hash = generate_password_hash(raw_password)

    @staticmethod
    def permission(role):
        perm = Permission(RoleNeed(role))
        return perm.can()

    def generate_password(self):
        self.pw_hash = ''.join(choice(PSYMBOLS) for c in xrange(8))

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def is_active(self):
        return self.active

    def __unicode__(self):
        return self.username

    def __repr__(self):
        return '<User %r>' % (self.username)


class Key(db.Model, BaseMixin):
    """ OAuth keys store.
    """
    __tablename__ = 'auth_key'
    __table_args__ = db.UniqueConstraint('service_alias', 'service_id'),

    service_alias = db.Column(db.String)
    service_id = db.Column(db.String)

    access_token = db.Column(db.String)
    secret = db.Column(db.String)
    expires = db.Column(db.DateTime)
    refresh_token = db.Column(db.String)

    user_id = db.Column(db.Integer, db.ForeignKey('auth_user.id'))
    user = db.relationship('User', backref=db.backref('keys', lazy='dynamic'))

    def __unicode__(self):
        return self.service_alias

    def __repr__(self):
        return '<Key %s %s>' % (self.service_alias, self.service_id)

    def is_expired(self):
        return self.expires and self.expires < datetime.now()

# pymode:lint_ignore=E0611,E0202

########NEW FILE########
__FILENAME__ = base
from datetime import datetime, timedelta

from flask import url_for, request, flash, redirect
from flask_login import current_user
from flask_rauth import RauthOAuth2, RauthOAuth1
from flaskext.babel import lazy_gettext as _

from ..models import db, Key, User
from ..views import auth


class AbstractRAuth(object):

    client = None

    @property
    def name(self):
        raise NotImplementedError

    @property
    def options(self):
        raise NotImplementedError

    @classmethod
    def get_credentials(cls, response, oauth_token):
        raise NotImplementedError

    @classmethod
    def authorize(cls, response, oauth_token):
        next_url = request.args.get('next') or url_for('urls.index')
        if response is None or 'denied' in request.args:
            flash(_(u'You denied the request to sign in.'))
            return redirect(next_url)

        try:
            credentials = cls.get_credentials(response, oauth_token)
        except Exception:
            return redirect(next_url)

        if credentials.get('expires'):
            expires_in = timedelta(seconds=int(credentials['expires']))
            credentials['expires'] = datetime.now() + expires_in

        key = Key.query.filter(
            Key.service_alias == cls.name,
            Key.service_id == credentials['service_id'],
        ).first()

        user = current_user

        if key:

            if user.is_authenticated():
                key.user = user

            else:
                user = key.user

        else:
            if not user.is_authenticated():
                user = User(username=credentials['username'])
                user.generate_password()
                db.session.add(user)

            key = Key(
                service_alias=cls.name,
                user=user,
                service_id=credentials['service_id'],
                access_token=credentials['access_token'],
                secret=credentials.get('secret'),
                expires=credentials.get('expires'),
            )
            db.session.add(key)

        db.session.commit()
        auth.login(user)
        flash(_('Welcome %(user)s', user=user.username))
        return redirect(next_url)

    @classmethod
    def setup(cls, app):
        options = app.config.get('OAUTH_%s' % cls.name.upper())
        if not options:
            return False

        params = dict()
        if 'params' in options:
            params = options.pop('params')

        app.logger.info('Init OAuth %s' % cls.name)
        cls.options.update(name=cls.name, **options)
        client_cls = RauthOAuth2
        if cls.options.get('request_token_url'):
            client_cls = RauthOAuth1

        cls.client = client_cls(**cls.options)

        login_name = 'oauth_%s_login' % cls.name
        authorize_name = 'oauth_%s_authorize' % cls.name

        @app.route('/%s' % login_name, endpoint=login_name)
        def login():
            return cls.client.authorize(
                callback=(
                    url_for(authorize_name, _external=True,
                            next=request.args.get('next') or request.referrer)
                ), **params)

        cls.client.tokengetter_f = cls.get_token

        app.add_url_rule('/%s' % authorize_name,
                         authorize_name,
                         cls.client.authorized_handler(cls.authorize))

    @classmethod
    def get_token(cls):
        if current_user.is_authenticated():
            for key in current_user.keys:
                if key.service_alias == cls.name:
                    return key.access_token

########NEW FILE########
__FILENAME__ = facebook
from .base import AbstractRAuth


class FacebookOAuth(AbstractRAuth):

    name = 'facebook'
    options = dict(
        base_url='https://graph.facebook.com',
        authorize_url='https://www.facebook.com/dialog/oauth',
        access_token_url='https://graph.facebook.com/oauth/access_token',
    )

    @classmethod
    def get_credentials(cls, response, oauth_token):
        me = cls.client.get('/me', access_token=oauth_token)
        return dict(
            username=me.content['username'],
            access_token=oauth_token,
            expires=response.content['expires'],
            service_id=me.content['id'],
        )

########NEW FILE########
__FILENAME__ = github
from .base import AbstractRAuth


class GithubOAuth(AbstractRAuth):

    name = 'github'
    options = dict(
        base_url='https://api.github.com/',
        authorize_url='https://github.com/login/oauth/authorize',
        access_token_url='https://github.com/login/oauth/access_token',
    )

    @classmethod
    def get_credentials(cls, response, oauth_token):
        me = cls.client.get('/user', access_token=oauth_token)
        return dict(
            username=me.content['login'],
            access_token=oauth_token,
            service_id=me.content['id'],
        )

########NEW FILE########
__FILENAME__ = twitter
from .base import AbstractRAuth


class TwitterOAuth(AbstractRAuth):

    name = 'twitter'
    options = dict(
        base_url='http://api.twitter.com/1/',
        authorize_url='http://api.twitter.com/oauth/authorize',
        access_token_url='http://api.twitter.com/oauth/access_token',
        request_token_url='http://api.twitter.com/oauth/request_token',
    )

    @classmethod
    def get_credentials(cls, response, oauth_token):
        return dict(
            username=response.content['screen_name'],
            service_id=response.content['user_id'],
            access_token=response.content['oauth_token'],
            secret=response.content['oauth_token_secret'],
        )

########NEW FILE########
__FILENAME__ = tests
from flask import url_for

from ..core.tests import FlaskTest
from ..ext import db


class AuthTest(FlaskTest):

    def test_model_mixin(self):
        from .models import User
        self.assertTrue(User.do_true())

    def test_users(self):
        from .models import User

        response = self.client.post('/auth/login/', data=dict())
        self.assertRedirects(response, '/')

        user = User(username='test', pw_hash='test', email='test@test.com')
        db.session.add(user)
        db.session.commit()
        self.assertTrue(user.updated_at)

        response = self.client.post('/auth/login/', data=dict(
            email='test@test.com',
            action_save=True,
            password='test'))
        redirect_url = url_for(self.app.config.get('AUTH_PROFILE_VIEW', 'auth.profile'))
        self.assertRedirects(response, redirect_url)

        response = self.client.get('/auth/logout/')
        self.assertRedirects(response, '/')

        response = self.client.post('/auth/register/', data=dict(
            username='test2',
            email='test2@test.com',
            action_save=True,
            password='test',
            password_confirm='test',
        ))
        redirect_url = url_for(self.app.config.get('AUTH_PROFILE_VIEW', 'auth.profile'))
        self.assertRedirects(response, redirect_url)

        user = User.query.filter(User.username == 'test2').first()
        self.assertEqual(user.email, 'test2@test.com')

    def test_manager(self):
        from .models import Role, User
        from .manage import create_role, create_user, add_role

        create_role('test')
        role = Role.query.filter(Role.name == 'test').first()
        self.assertEqual(role.name, 'test')

        create_user('test', 'test@test.com', active=True, password='12345')
        user = User.query.filter(User.username == 'test').first()

        add_role('test', 'test')
        self.assertTrue(role in user.roles)

    def test_oauth(self):
        from flask import url_for

        if self.app.config.get('OAUTH_TWITTER'):
            self.assertTrue(url_for('oauth_twitter_login'))

        if self.app.config.get('OAUTH_GITHUB'):
            self.assertTrue(url_for('oauth_github_login'))

        if self.app.config.get('OAUTH_FACEBOOK'):
            self.assertTrue(url_for('oauth_facebook_login'))


class TestUserMixin(object):

    @staticmethod
    def do_true():
        return True

########NEW FILE########
__FILENAME__ = utils
from flask import Blueprint
from flask_login import LoginManager, login_required, logout_user, login_user, current_user
from flask_principal import Principal, identity_changed, Identity, AnonymousIdentity, identity_loaded, UserNeed, RoleNeed

from ..ext import db
from .models import User


class UserManager(Blueprint):

    def __init__(self, *args, **kwargs):
        self._login_manager = None
        self._principal = None
        self.app = None
        super(UserManager, self).__init__(*args, **kwargs)

    def register(self, app, *args, **kwargs):
        " Activate loginmanager and principal. "

        if not self._login_manager or self.app != app:
            self._login_manager = LoginManager()
            self._login_manager.user_callback = self.user_loader
            self._login_manager.init_app(app)
            self._login_manager.login_view = app.config.get('AUTH_LOGIN_VIEW', 'code.index')
            self._login_manager.login_message = u'You need to be signed in for this page.'

        self.app = app

        if not self._principal:
            self._principal = Principal(app)
            identity_loaded.connect(self.identity_loaded)

        super(UserManager, self).register(app, *args, **kwargs)

    @staticmethod
    def user_loader(pk):
        return User.query.options(db.joinedload(User.roles)).get(pk)

    @staticmethod
    def login_required(fn):
        return login_required(fn)

    def logout(self):
        identity_changed.send(self.app, identity=AnonymousIdentity())
        return logout_user()

    def login(self, user):
        identity_changed.send(self.app, identity=Identity(user.id))
        return login_user(user)

    @staticmethod
    def identity_loaded(sender, identity):
        identity.user = current_user

        # Add the UserNeed to the identity
        if current_user.is_authenticated():
            identity.provides.add(UserNeed(current_user.id))

            # Assuming the User model has a list of roles, update the
            # identity with the roles that the user provides
            for role in current_user.roles:
                identity.provides.add(RoleNeed(role.name))

########NEW FILE########
__FILENAME__ = views
from flask import request, render_template, flash, redirect, url_for, current_app
from flaskext.babel import lazy_gettext as _

from ..ext import db
from .forms import RegisterForm, LoginForm
from .models import User
from .utils import UserManager


auth = UserManager(
    'auth', __name__, url_prefix='/auth', template_folder='templates')


if not current_app.config.get('AUTH_PROFILE_VIEW'):

    @auth.route('/profile/')
    @auth.login_required
    def profile():
        return render_template("auth/profile.html")


@auth.route('/login/', methods=['POST'])
def login():
    " View function which handles an authentication request. "
    form = LoginForm(request.form)
    # make sure data are valid, but doesn't validate password is right
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # we use werzeug to validate user's password
        if user and user.check_password(form.password.data):
            auth.login(user)
            flash(_('Welcome %(user)s', user=user.username))
            redirect_name = current_app.config.get('AUTH_PROFILE_VIEW', 'auth.profile')
            return redirect(url_for(redirect_name))
        flash(_('Wrong email or password'), 'error-message')
    return redirect(request.referrer or url_for(auth._login_manager.login_view))


@auth.route('/logout/', methods=['GET'])
@auth.login_required
def logout():
    " View function which handles a logout request. "
    auth.logout()
    return redirect(request.referrer or url_for(auth._login_manager.login_view))


@auth.route('/register/', methods=['GET', 'POST'])
def register():
    " Registration Form. "
    form = RegisterForm(request.form)
    if form.validate_on_submit():
        # create an user instance not yet stored in the database
        user = User(
            username=form.username.data,
            email=form.email.data,
            pw_hash=form.password.data)

        # Insert the record in our database and commit it
        db.session.add(user)
        db.session.commit()

        auth.login(user)

        # flash will display a message to the user
        flash(_('Thanks for registering'))

        # redirect user to the 'home' method of the user module.
        redirect_name = current_app.config.get('AUTH_PROFILE_VIEW', 'auth.profile')
        return redirect(url_for(redirect_name))

    return render_template("auth/register.html", form=form)


# pymode:lint_ignore=F0401

########NEW FILE########
__FILENAME__ = core
""" Immutable basic settings.
"""

import logging

from base.config import op, ROOTDIR


# Auth
AUTH_USER_MIXINS = []
AUTH_LOGIN_VIEW = 'core.index'

# Babel
BABEL_LANGUAGES = ['en', 'ru']
BABEL_DEFAULT_LOCALE = 'en'

# Database
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + op.join(ROOTDIR, '.db')

# Cache
CACHE_TYPE = 'simple'

# Mail
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = None
MAIL_PASSWORD = None
DEFAULT_MAIL_SENDER = None

# WTForms
CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    datefmt='%d.%m %H:%M:%S')
logging.info("Core settings loaded.")

########NEW FILE########
__FILENAME__ = develop
""" Development settings.
"""

from .production import *


MODE = 'develop'
DEBUG = True
DEBUG_TB_INTERCEPT_REDIRECTS = False
SQLALCHEMY_ECHO = True

logging.info("Develop settings loaded.")

# pymode:lint_ignore=W0614,W404

########NEW FILE########
__FILENAME__ = production
" Production settings must be here. "

from .core import *
from os import path as op


MODE = 'production'
SECRET_KEY = 'SecretKeyForSessionSigning'
ADMINS = MAIL_USERNAME and [MAIL_USERNAME] or None

# flask.ext.collect
# -----------------
COLLECT_STATIC_ROOT = op.join(op.dirname(ROOTDIR), 'static')

# auth.oauth
# ----------
OAUTH_TWITTER = dict(
    consumer_key='750sRyKzvdGPJjPd96yfgw',
    consumer_secret='UGcyjDCUOb1q44w1nUk8FA7aXxvwwj1BCbiFvYYI',
)

OAUTH_FACEBOOK = dict(
    consumer_key='413457268707622',
    consumer_secret='48e9be9f4e8abccd3fb916a3f646dd3f',
)

OAUTH_GITHUB = dict(
    consumer_key='8bdb217c5df1c20fe632',
    consumer_secret='a3aa972b2e66e3fac488b4544d55eda2aa2768b6',
)

# dealer
DEALER_PARAMS = dict(
    backends=('git', 'mercurial', 'simple', 'null')
)

logging.info("Production settings loaded.")

# pymode:lint_ignore=W0614,W404

########NEW FILE########
__FILENAME__ = test
" Settings for running tests. "

from .production import *


MODE = 'test'
TESTING = True
SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
CSRF_ENABLED = False
CACHE_TYPE = 'simple'

AUTH_USER_MIXINS += ['base.auth.tests.TestUserMixin']

logging.info("Test settings loaded.")

# pymode:lint_ignore=W0614,W404

########NEW FILE########
__FILENAME__ = admin
from .ext import admin, ModelView
from .models import Alembic


class AlembicView(ModelView):
    column_filters = 'version_num',
    column_list = 'version_num',
    form_columns = 'version_num',

admin.add_model(Alembic, AlembicView)

########NEW FILE########
__FILENAME__ = ext
from flask_admin import AdminIndexView, Admin
from flask_admin.contrib.sqlamodel import ModelView
from flask_login import current_user

from ..ext import db


class StaffAdminView(AdminIndexView):
    " Staff admin home page. "

    def is_accessible(self):
        return current_user.is_authenticated() and current_user.permission('staff')


class AuthModelView(ModelView):
    def __init__(self, *args, **kwargs):
        self.role = kwargs.pop('role', None) or 'admin'
        super(AuthModelView, self).__init__(*args, **kwargs)

    def is_accessible(self):
        return current_user.is_authenticated() and current_user.permission(self.role)


class FlaskAdmin(Admin):

    def __init__(self, **kwargs):
        super(FlaskAdmin, self).__init__(index_view=StaffAdminView(), **kwargs)

    def init_app(self, app):
        self.app = None
        super(FlaskAdmin, self).init_app(app)

        from ..loader import loader
        loader.register(submodule='admin')

    def add_model(self, model, view=None, **kwargs):
        view = view or AuthModelView
        self.add_view(view(model, db.session))


admin = FlaskAdmin()

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from sqlalchemy import event
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.session import object_session

from ..ext import db


class UpdateMixin(object):
    """Provides the 'update' convenience function to allow class
    properties to be written via keyword arguments when the object is
    already initialised.

    .. code-block: python

        class Person(Base, UpdateMixin):
            name = db.Column(String(19))

        >>> person = Person(name='foo')
        >>> person.update(**{'name': 'bar'})
        >>> person.update(login='foo')

    """

    def update(self, **kw):
        for k, v in kw.items():
            if hasattr(self, k):
                setattr(self, k, v)


class TimestampMixin(object):
    """Adds automatically updated created_at and updated_at timestamp
    columns to a table, that unsurprisingly are updated on record INSERT and
    UPDATE. UTC time is used in both cases.
    """

    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, onupdate=datetime.utcnow, default=datetime.utcnow)


class BaseMixin(UpdateMixin, TimestampMixin):
    """ Defines an id column to save on boring boilerplate.
    """

    id = db.Column(db.Integer, primary_key=True)

    @declared_attr
    def __tablename__(self):
        """ Set default tablename.
        """
        return self.__name__.lower()

    @property
    def __session__(self):
        return object_session(self)


class Alembic(db.Model):
    __tablename__ = 'alembic_version'
    version_num = db.Column(db.String(32), nullable=False, primary_key=True)


def before_signal(session, *args):
    map(lambda o: hasattr(o, 'before_new') and o.before_new(), session.new)
    map(lambda o: hasattr(o, 'before_delete') and o.before_delete(), session.deleted)

event.listen(db.session.__class__, 'before_flush', before_signal)

########NEW FILE########
__FILENAME__ = tests
from flask import current_app
from flask_testing import TestCase
from flask_mixer import Mixer

from ..ext import db


class QueriesContext():
    """ Test's tool for check database queries.

        >>> with self.assertNumQueries(4):
        >>>     do_something()
    """

    def __init__(self, num, testcase):

        self.num = num
        self.echo = None
        self.testcase = testcase
        self.start = 0

    def __enter__(self):
        from flask_sqlalchemy import get_debug_queries

        self.start = len(get_debug_queries())
        self.echo = db.engine.echo
        db.engine.echo = True

    def __exit__(self, exc_type, exc_value, traceback):
        db.engine.echo = self.echo
        if exc_type is not None:
            return

        from flask_sqlalchemy import get_debug_queries

        executed = len(get_debug_queries()) - self.start
        self.testcase.assertEqual(
            executed, self.num, "%d queries executed, %d expected" % (
                executed, self.num
            )
        )


class FlaskTest(TestCase):
    """ Base flask test class.

        Initialize database.
        Create objects generator.
    """

    def create_app(self):
        return current_app

    def setUp(self):
        db.create_all()
        self.mixer = Mixer(self.app, session_commit=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def assertNumQueries(self, num, func=None):
        " Check number of queries by flask_sqlalchemy. "

        context = QueriesContext(num, self)
        if func is None:
            return context

        with context:
            func()


class CoreTest(FlaskTest):

    def test_home(self):
        response = self.client.get('/')
        self.assert200(response)

    def test_admin(self):
        with self.assertNumQueries(0):
            response = self.client.get('/admin/')
        self.assert404(response)

    def test_cache(self):
        from ..ext import cache

        cache.set('key', 'value')
        testkey = cache.get('key')
        self.assertEqual(testkey, 'value')

    def test_after_change(self):
        from .models import Alembic
        from mock import Mock
        Alembic.before_new = Mock()
        a = Alembic()
        a.version_num = '345'
        db.session.add(a)
        db.session.commit()
        self.assertEqual(Alembic.before_new.call_count, 1)

    def test_mail_handler(self):
        """ Handle errors by mail.
        """
        from . import FlaskMailHandler
        from ..ext import mail

        mail.username = 'test@test.com'
        mail.password = 'test'
        self.app.config['ADMINS'] = ['test@test.com']
        self.app.config['DEFAULT_MAIL_SENDER'] = 'test@test.com'
        self.app.logger.addHandler(FlaskMailHandler(40))
        propagate_exceptions = self.app.config.get('PROPAGATE_EXCEPTIONS')
        self.app.config['PROPAGATE_EXCEPTIONS'] = False

        @self.app.route('/error')
        def error():
            raise Exception('Error content')
        assert error

        with mail.record_messages() as outbox:
            self.app.logger.error('Attention!')
            self.assertTrue(outbox)
            msg = outbox.pop()
            self.assertEqual(msg.subject, 'APP ERROR: http://localhost/')

            self.client.get('/error')
            msg = outbox.pop()
            self.assertTrue('Error content', )

        self.app.config['PROPAGATE_EXCEPTIONS'] = propagate_exceptions

########NEW FILE########
__FILENAME__ = views
from flask import render_template, Blueprint, current_app

from ..auth.forms import LoginForm


core = Blueprint('core', __name__,
                 template_folder='templates',
                 static_url_path='/static/core',
                 static_folder='static')


if current_app and current_app.config.get('AUTH_LOGIN_VIEW') == 'core.index':

    @core.route('/')
    def index():
        """
            Main page.

            Redifine `AUTH_LOGIN_VIEW` for customize index page.
        """

        return render_template('core/index.html', loginform=LoginForm())

########NEW FILE########
__FILENAME__ = ext
from flask import request
from flask_collect import Collect
from flask_debugtoolbar import DebugToolbarExtension
from flask_mail import Mail
from flask_script import Manager
from flask_squll import Squll
from flaskext.babel import Babel
from flask_cache import Cache
from dealer.contrib.flask import Dealer

from .app import create_app


babel = Babel()
cache = Cache()
db = Squll()
dealer = Dealer()
mail = Mail()

manager = Manager(create_app)
manager.add_option("-c", "--config", dest="config", required=False)

collect = Collect()
collect.init_script(manager)


def config_extensions(app):
    " Init application with extensions. "

    cache.init_app(app)
    collect.init_app(app)
    db.init_app(app)
    dealer.init_app(app)
    mail.init_app(app)

    DebugToolbarExtension(app)

    config_babel(app)


def config_babel(app):
    " Init application with babel. "

    babel.init_app(app)

    def get_locale():
        return request.accept_languages.best_match(
            app.config['BABEL_LANGUAGES'])
    babel.localeselector(get_locale)


# pymode:lint_ignore=F0401

########NEW FILE########
__FILENAME__ = loader
from importlib import import_module
from straight.plugin.loaders import ModuleLoader


class AppLoader(ModuleLoader):

    def __init__(self, subtype=None):
        self.subtype = None
        self._cache = []
        super(AppLoader, self).__init__()

    def _fill_cache(self, namespace):
        super(AppLoader, self)._fill_cache(namespace)
        self._cache = filter(self._meta, self._cache)

    def register(self, *args, **kwargs):
        " Load and register modules. "

        result = []

        submodule = kwargs.pop('submodule', None)
        logger = kwargs.pop('logger', None)

        for mod in self:

            if logger:
                logger.info("Register module: %s" % mod.__name__)

            if submodule:
                mod = self.import_module('%s.%s' % (mod.__name__, submodule))

            meta = self._meta(mod)
            meta and meta(*args, **kwargs)

            result.append(mod)

        return result

    def __iter__(self):
        return iter(self._cache)

    @staticmethod
    def _meta(mod):
        return getattr(mod, 'loader_meta', None)

    @staticmethod
    def import_module(path):
        try:
            return import_module(path)
        except ImportError:
            return None


loader = AppLoader()
loader.load(__name__.split('.')[0])


# pymode:lint_ignore=F0401

########NEW FILE########
__FILENAME__ = admin
from wtforms.fields import TextAreaField
from wtforms.widgets import TextArea

from ..core.ext import admin, AuthModelView
from .models import Page


class WysiwygWidget(TextArea):
    def __call__(self, field, **kwargs):
        kwargs['class'] = 'span8 textarea'
        return super(WysiwygWidget, self).__call__(field, **kwargs)


class WysiwygTextAreaField(TextAreaField):
    widget = WysiwygWidget()


class PageView(AuthModelView):
    create_template = 'pages/admin/create.html'
    edit_template = 'pages/admin/edit.html'
    form_overrides = dict(content=WysiwygTextAreaField)
    column_list = 'slug', 'active', 'created_at', 'updated_at'


admin.add_model(Page, PageView)

########NEW FILE########
__FILENAME__ = config
from flask import current_app


ROOT = current_app.config.get('PAGES_ROOT', 'p').strip('/')
TEMPLATE = current_app.config.get('PAGES_TEMPLATE', 'pages/page.html')

########NEW FILE########
__FILENAME__ = models
from flask import render_template

from ..core.models import BaseMixin, db
from ..ext import cache
from .config import TEMPLATE, ROOT


class Page(db.Model, BaseMixin):
    """ Site pages.
    """

    __tablename__ = 'pages_page'

    active = db.Column(db.Boolean, default=True)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    link = db.Column(db.String(256))
    content = db.Column(db.Text)

    parent_id = db.Column(db.Integer, db.ForeignKey('pages_page.id'))
    children = db.relation(
        'Page',
        cascade='all',
        backref=db.backref('parent', remote_side='Page.id'))

    def __unicode__(self):
        return self.slug

    def render(self):
        return render_template(TEMPLATE, page=self)

    @property
    def uri(self):
        cache_key = 'pages.uri.{slug}'.format(slug=self.slug)
        uri = cache.get(cache_key)
        if not uri:
            parent = self.parent_id and self.parent.uri or ('/%s/' % ROOT)
            uri = "{parent}{slug}/".format(parent=parent, slug=self.slug)
            cache.set(cache_key, uri)
        return uri

    @classmethod
    def route(cls, slug):
        page = cls.query.filter_by(slug=slug).first()
        if page is None:
            return page

        return page.uri

########NEW FILE########
__FILENAME__ = tests
from ..core.tests import FlaskTest
from .models import Page


class PageTest(FlaskTest):

    def test_page(self):
        response = self.client.get('/p/unknown_page/')
        self.assert404(response)

        page1 = self.mixer.blend(
            'base.pages.models.Page', content=self.mixer.random)
        self.assertEqual(Page.route(page1.slug), page1.uri)
        response = self.client.get(page1.uri)
        self.assert200(response)
        self.assertTrue(page1.content in response.data)

        page2 = self.mixer.blend(
            'base.pages.models.Page', content=self.mixer.random, parent=page1)
        with self.assertNumQueries(2):
            self.assertEqual(page2.uri, '/p/{slug1}/{slug2}/'.format(
                slug1=page1.slug, slug2=page2.slug))
            self.assertEqual(page1.uri, '/p/{slug}/'.format(slug=page1.slug))

        self.assertEqual(Page.route(page2.slug), page2.uri)
        response = self.client.get(page2.uri)
        self.assertTrue(page2.content in response.data)

        page3 = self.mixer.blend(
            'base.pages.models.Page', link='http://google.com', parent=page1)
        response = self.client.get(page3.uri)
        self.assertEqual(response.status_code, 302)
        self.assertTrue('http://google.com' in response.data)

########NEW FILE########
__FILENAME__ = views
from flask import Blueprint, abort, redirect

from .config import ROOT
from .models import Page


pages = Blueprint('pages', __name__,
                  template_folder='templates',
                  static_url_path='/static/pages',
                  static_folder='static')


@pages.route('/%s/<path:pages>' % ROOT, methods=['GET'])
def page(pages):
    current_page = pages.strip('/').split('/')[-1]
    current_page = Page.query.filter_by(slug=current_page).first()

    if current_page is None:
        return abort(404)

    if current_page.link:
        return redirect(current_page.link)

    return current_page.render()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
# coding: utf-8
from base.ext import db, manager
from base.loader import loader
import sys


# Load app scripts
loader.register(manager, submodule='manage')


@manager.shell
def make_shell_context():
    " Update shell. "

    from flask import current_app
    return dict(app=current_app, db=db)


@manager.command
def alembic():
    " Alembic migration utils. "

    from flask import current_app
    from alembic.config import main
    from os import path as op

    global ARGV

    config = op.join(op.dirname(__file__), 'migrate', 'develop.ini' if current_app.debug else 'production.ini')

    ARGV = ['-c', config] + ARGV

    main(ARGV)


@manager.command
def test(testcase=''):
    " Run unittests. "

    try:
        from unittest2.loader import defaultTestLoader
        from unittest2.runner import TextTestRunner
    except ImportError:
        from unittest.loader import defaultTestLoader
        from unittest.runner import TextTestRunner

    if testcase:
        mod, case = testcase.rsplit('.', 1)
        mod = loader.import_module(mod)
        if not mod or not hasattr(mod, case):
            sys.stdout.write("Load case error: %s\n" % testcase)
            sys.exit(1)

        testcase = getattr(mod, case)
        suite = defaultTestLoader.loadTestsFromTestCase(testcase)
    else:
        cases = loader.register(submodule='tests')
        suites = [defaultTestLoader.loadTestsFromModule(mod) for mod in cases]
        suite = defaultTestLoader.suiteClass(suites)

    TextTestRunner().run(suite)


ARGV = []

if __name__ == '__main__':
    argv = sys.argv[1:]
    if argv and argv[0] == 'alembic':
        ARGV = filter(lambda a: not a in ('-c', 'alembic') and not a.startswith('base.config.'), argv)
        argv = filter(lambda a: not a in ARGV, argv)
        sys.argv = [sys.argv[0] + ' alembic'] + argv

    manager.run()


# pymode:lint_ignore=F0401,W801,W0603

########NEW FILE########
__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(
                config.get_section(config.config_ini_section),
                prefix='sqlalchemy.',
                poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
                connection=connection,
                target_metadata=target_metadata
                )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


########NEW FILE########
__FILENAME__ = 00000001_init_auth_models
"""Init auth models

Create Date: 2012-08-10 17:29:18.996057

"""

# revision identifiers, used by Alembic.
from datetime import datetime

import sqlalchemy as db
from alembic import op


revision = '00000001'
down_revision = None


def upgrade():

    op.create_table(
        'auth_role',
        db.Column('id', db.Integer, primary_key=True),
        db.Column('created_at', db.DateTime,
                  default=datetime.utcnow, nullable=False),
        db.Column('updated_at', db.DateTime,
                  onupdate=datetime.utcnow, default=datetime.utcnow),
        db.Column(
            'name', db.String(19), nullable=False, unique=True),
    )

    op.create_table(
        'auth_user',
        db.Column('id', db.Integer, primary_key=True),
        db.Column('created_at', db.DateTime,
                  default=datetime.utcnow, nullable=False),
        db.Column('updated_at', db.DateTime,
                  onupdate=datetime.utcnow, default=datetime.utcnow),
        db.Column('username', db.String(50), nullable=False, unique=True),
        db.Column('email', db.String(120)),
        db.Column('active', db.Boolean, default=True),
        db.Column('_pw_hash', db.String(199), nullable=False),
        db.Column('oauth_token', db.String(200)),
        db.Column('oauth_secret', db.String(200)),
    )

    op.create_table(
        'auth_userroles',
        db.Column('user_id', db.Integer, db.ForeignKey('auth_user.id')),
        db.Column('role_id', db.Integer, db.ForeignKey('auth_role.id')),
    )


def downgrade():
    op.drop_table('auth_role')
    op.drop_table('auth_user')
    op.drop_table('auth_userroles')

########NEW FILE########
__FILENAME__ = 00000002_fill_admin_recv
"""Fill admin recv

Create Date: 2012-08-11 17:28:35.464047

"""

# revision identifiers, used by Alembic.
from sqlalchemy.ext.declarative import declared_attr
from werkzeug import generate_password_hash

from base.core.models import BaseMixin
from flask_sqlalchemy import SQLAlchemy
from flask import current_app


revision = '00000002'
down_revision = '00000001'

db = SQLAlchemy(current_app)


class MigrateRole(db.Model, BaseMixin):
    __tablename__ = 'auth_role'
    __table_args__ = {'extend_existing': True}
    name = db.Column(db.String(19), nullable=False, unique=True)

userroles = db.Table(
    'auth_userroles',
    db.Column('user_id', db.Integer, db.ForeignKey('auth_user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('auth_role.id')),
    extend_existing=True,
)


class MigrateUser(db.Model, BaseMixin):
    __tablename__ = 'auth_user'
    __table_args__ = {'extend_existing': True}
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(120))
    active = db.Column(db.Boolean, default=True)
    _pw_hash = db.Column(db.String(199), nullable=False)

    @declared_attr
    def roles(self):
        assert self
        return db.relationship(MigrateRole, secondary=userroles, backref="auth")


def upgrade():
    admin = MigrateRole(name='admin')
    staff = MigrateRole(name='staff')
    user = MigrateUser(username='admin',
                       email='admin@admin.com',
                       _pw_hash=generate_password_hash('adminft7'))
    user.roles.append(admin)
    user.roles.append(staff)
    db.session.add(user)
    db.session.commit()


def downgrade():
    pass

# pymode:lint_ignore=E0611,E0202

########NEW FILE########
__FILENAME__ = 00000003_added_key_to_auth
"""Added Key to auth

Revision ID: 00000003
Revises: 00000002
Create Date: 2012-09-29 20:54:46.332465

"""

# revision identifiers, used by Alembic.
revision = '00000003'
down_revision = '00000002'

from alembic import op
import sqlalchemy as db
from datetime import datetime


def upgrade():
    op.create_table(
        'auth_key',

        db.Column('id', db.Integer, primary_key=True),
        db.Column('created_at', db.DateTime,
                  default=datetime.utcnow, nullable=False),
        db.Column('updated_at', db.DateTime,
                  onupdate=datetime.utcnow, default=datetime.utcnow),

        db.Column('service_alias', db.String),
        db.Column('service_id', db.String),
        db.Column('access_token', db.String),
        db.Column('secret', db.String),
        db.Column('expires', db.DateTime),
        db.Column('refresh_token', db.String),
        db.Column('user_id', db.Integer, db.ForeignKey('auth_user.id')),

        db.UniqueConstraint('service_alias', 'service_id'),
    )


def downgrade():
    op.drop_table('auth_key')

########NEW FILE########
__FILENAME__ = 00000004_init_pages
"""init_pages

Revision ID: 00000004
Revises: 00000003
Create Date: 2012-12-12 19:35:23.779969

"""

# revision identifiers, used by Alembic.
revision = '00000004'
down_revision = '00000003'

from alembic import op
import sqlalchemy as db
from datetime import datetime


def upgrade():
    op.create_table(
        'pages_page',

        db.Column('id', db.Integer, primary_key=True),
        db.Column('created_at', db.DateTime,
                  default=datetime.utcnow, nullable=False),
        db.Column('updated_at', db.DateTime,
                  onupdate=datetime.utcnow, default=datetime.utcnow),

        db.Column('active', db.Boolean, default=True),
        db.Column('slug', db.String(100), nullable=False, unique=True),
        db.Column('link', db.String(256)),
        db.Column('content', db.Text),
        db.Column('parent_id', db.Integer, db.ForeignKey('pages_page.id')),
    )


def downgrade():
    op.drop_table('pages_page')

########NEW FILE########
__FILENAME__ = wsgi
import sys
from os import path as op

from base.app import create_app


APPROOT = op.abspath(op.join(op.dirname(__file__), 'base'))
if not APPROOT in sys.path:
    sys.path.insert(0, APPROOT)

application = create_app()

########NEW FILE########
