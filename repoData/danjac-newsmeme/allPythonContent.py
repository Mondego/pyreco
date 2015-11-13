__FILENAME__ = deploy
# UWSGI configuration

import uwsgi
import production_settings

from newsmeme import create_app

application = create_app(production_settings)
uwsgi.applications = {"/":application}


########NEW FILE########
__FILENAME__ = fabfile
import sys

from fabric.api import env, run, cd

"""
Sample fabric file. Assumes the following on production server:

- virtualenv + virtualenvwrapper
- mercurial
- supervisord (running gunicorn/uwsgi etc.)

Copy and modify as required for your own particular setup.

Keep your private settings in a separate module, fab_settings.py, in
the same directory as this file.
"""

try:
    import fab_settings as settings
except ImportError:
    print "You must provide a valid fab_settings.py module in this directory"
    sys.exit(1)


def server():
    env.hosts = settings.SERVER_HOSTS
    env.user = settings.SERVER_USER
    env.password = settings.SERVER_PASSWORD


def deploy():
    """
    Pulls latest code into staging, runs tests, then pulls into live.
    """
    providers = (server,)
    with cd(settings.STAGING_DIR):
        run("hg pull -u")
        run("workon %s;nosetests" % settings.VIRTUALENV)
    with cd(settings.PRODUCTION_DIR):
        run("hg pull -u")


def reload():
    """
    Deploys and then reloads application server.
    """
    deploy()
    run("supervisorctl -c %s restart %s" % (settings.SUPERVISOR_CONF,
                                            settings.SUPERVISOR_CMD))


def upgrade():
    """
    Updates all required packages, runs tests, then updates packages on
    live, then restarts server.
    """

    with cd(settings.PRODUCTION_DIR):
        run("workon %s; python setup.py develop -U" % settings.VIRTUALENV)

    reload()



########NEW FILE########
__FILENAME__ = manage
# -*- coding: utf-8 -*-
"""
    manage.py
    ~~~~~~~~~

    Description of the module goes here...

    :copyright: (c) 2010 by Dan Jacob.
    :license: BSD, see LICENSE for more details.
"""
import sys
import feedparser

from flask import current_app

from flaskext.script import Manager, prompt, prompt_pass, \
    prompt_bool, prompt_choices

from flaskext.mail import Message

from newsmeme import create_app
from newsmeme.extensions import db, mail
from newsmeme.models import Post, User, Comment, Tag

manager = Manager(create_app)

@manager.option("-u", "--url", dest="url", help="Feed URL")
@manager.option("-n", "--username", dest="username", help="Save to user")
def importfeed(url, username):
    """
    Bulk import news from a feed. For testing only !
    """

    user = User.query.filter_by(username=username).first()
    if not user:
        print "User %s does not exist" % username
        sys.exit(1)
    d = feedparser.parse(url)
    for entry in d['entries']:
        post = Post(author=user,
                    title=entry.title[:200],
                    link=entry.link)

        db.session.add(post)
    db.session.commit()

@manager.option('-u', '--username', dest="username", required=False)
@manager.option('-p', '--password', dest="password", required=False)
@manager.option('-e', '--email', dest="email", required=False)
@manager.option('-r', '--role', dest="role", required=False)
def createuser(username=None, password=None, email=None, role=None):
    """
    Create a new user
    """
    
    if username is None:
        while True:
            username = prompt("Username")
            user = User.query.filter(User.username==username).first()
            if user is not None:
                print "Username %s is already taken" % username
            else:
                break

    if email is None:
        while True:
            email = prompt("Email address")
            user = User.query.filter(User.email==email).first()
            if user is not None:
                print "Email %s is already taken" % email
            else:
                break

    if password is None:
        password = prompt_pass("Password")

        while True:
            password_again = prompt_pass("Password again")
            if password != password_again:
                print "Passwords do not match"
            else:
                break
    
    roles = (
        (User.MEMBER, "member"),
        (User.MODERATOR, "moderator"),
        (User.ADMIN, "admin"),
    )

    if role is None:
        role = prompt_choices("Role", roles, resolve=int, default=User.MEMBER)

    user = User(username=username,
                email=email,
                password=password,
                role=role)

    db.session.add(user)
    db.session.commit()

    print "User created with ID", user.id


@manager.command
def createall():
    "Creates database tables"
    
    db.create_all()

@manager.command
def dropall():
    "Drops all database tables"
    
    if prompt_bool("Are you sure ? You will lose all your data !"):
        db.drop_all()

@manager.command
def mailall():
    "Sends an email to all users"
    
    subject = prompt("Subject")
    message = prompt("Message")
    from_address = prompt("From", default="support@thenewsmeme.com")
    if prompt_bool("Are you sure ? Email will be sent to everyone!"):
        with mail.connect() as conn:
            for user in User.query:
                message = Message(subject=subject,
                                  body=message,
                                  sender=from_address,
                                  recipients=[user.email])

                conn.send(message)


@manager.shell
def make_shell_context():
    return dict(app=current_app, 
                db=db,
                Post=Post,
                User=User,
                Tag=Tag,
                Comment=Comment)


manager.add_option('-c', '--config',
                   dest="config",
                   required=False,
                   help="config file")

if __name__ == "__main__":
    manager.run()

########NEW FILE########
__FILENAME__ = application
# -*- coding: utf-8 -*-
"""
    application.py
    ~~~~~~~~~~~

    Application configuration

    :copyright: (c) 2010 by Dan Jacob.
    :license: BSD, see LICENSE for more details.
"""
import os
import logging

from logging.handlers import SMTPHandler, RotatingFileHandler

from flask import Flask, Response, request, g, \
        jsonify, redirect, url_for, flash

from flaskext.babel import Babel, gettext as _
from flaskext.themes import setup_themes
from flaskext.principal import Principal, identity_loaded

from newsmeme import helpers
from newsmeme import views
from newsmeme.config import DefaultConfig
from newsmeme.models import User, Tag
from newsmeme.helpers import render_template
from newsmeme.extensions import db, mail, oid, cache

__all__ = ["create_app"]

DEFAULT_APP_NAME = "newsmeme"

DEFAULT_MODULES = (
    (views.frontend, ""),
    (views.post, "/post"),
    (views.user, "/user"),
    (views.comment, "/comment"),
    (views.account, "/acct"),
    (views.feeds, "/feeds"),
    (views.openid, "/openid"),
    (views.api, "/api"),
)

def create_app(config=None, app_name=None, modules=None):

    if app_name is None:
        app_name = DEFAULT_APP_NAME

    if modules is None:
        modules = DEFAULT_MODULES

    app = Flask(app_name)

    configure_app(app, config)

    configure_logging(app)
    configure_errorhandlers(app)
    configure_extensions(app)
    configure_before_handlers(app)
    configure_template_filters(app)
    configure_context_processors(app)
    # configure_after_handlers(app)
    configure_modules(app, modules)

    return app


def configure_app(app, config):
    
    app.config.from_object(DefaultConfig())

    if config is not None:
        app.config.from_object(config)

    app.config.from_envvar('APP_CONFIG', silent=True)


def configure_modules(app, modules):
    
    for module, url_prefix in modules:
        app.register_module(module, url_prefix=url_prefix)


def configure_template_filters(app):

    @app.template_filter()
    def timesince(value):
        return helpers.timesince(value)


def configure_before_handlers(app):

    @app.before_request
    def authenticate():
        g.user = getattr(g.identity, 'user', None)


def configure_context_processors(app):

    @app.context_processor
    def get_tags():
        tags = cache.get("tags")
        if tags is None:
            tags = Tag.query.order_by(Tag.num_posts.desc()).limit(10).all()
            cache.set("tags", tags)

        return dict(tags=tags)

    @app.context_processor
    def config():
        return dict(config=app.config)


def configure_extensions(app):

    mail.init_app(app)
    db.init_app(app)
    oid.init_app(app)
    cache.init_app(app)

    setup_themes(app)

    # more complicated setups

    configure_identity(app)
    configure_i18n(app)
    

def configure_identity(app):

    Principal(app)

    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):
        g.user = User.query.from_identity(identity)


def configure_i18n(app):

    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        accept_languages = app.config.get('ACCEPT_LANGUAGES', 
                                               ['en_gb'])

        return request.accept_languages.best_match(accept_languages)


def configure_errorhandlers(app):

    if app.testing:
        return

    @app.errorhandler(404)
    def page_not_found(error):
        if request.is_xhr:
            return jsonify(error=_('Sorry, page not found'))
        return render_template("errors/404.html", error=error)

    @app.errorhandler(403)
    def forbidden(error):
        if request.is_xhr:
            return jsonify(error=_('Sorry, not allowed'))
        return render_template("errors/403.html", error=error)

    @app.errorhandler(500)
    def server_error(error):
        if request.is_xhr:
            return jsonify(error=_('Sorry, an error has occurred'))
        return render_template("errors/500.html", error=error)

    @app.errorhandler(401)
    def unauthorized(error):
        if request.is_xhr:
            return jsonfiy(error=_("Login required"))
        flash(_("Please login to see this page"), "error")
        return redirect(url_for("account.login", next=request.path))


def configure_logging(app):
    if app.debug or app.testing:
        return

    mail_handler = \
        SMTPHandler(app.config['MAIL_SERVER'],
                    'error@newsmeme.com',
                    app.config['ADMINS'], 
                    'application error',
                    (
                        app.config['MAIL_USERNAME'],
                        app.config['MAIL_PASSWORD'],
                    ))

    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]')

    debug_log = os.path.join(app.root_path, 
                             app.config['DEBUG_LOG'])

    debug_file_handler = \
        RotatingFileHandler(debug_log,
                            maxBytes=100000,
                            backupCount=10)

    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_handler.setFormatter(formatter)
    app.logger.addHandler(debug_file_handler)

    error_log = os.path.join(app.root_path, 
                             app.config['ERROR_LOG'])

    error_file_handler = \
        RotatingFileHandler(error_log,
                            maxBytes=100000,
                            backupCount=10)

    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    app.logger.addHandler(error_file_handler)




########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
"""
    config.py
    ~~~~~~~~~~~

    Default configuration

    :copyright: (c) 2010 by Dan Jacob.
    :license: BSD, see LICENSE for more details.
"""

from newsmeme import views

class DefaultConfig(object):
    """
    Default configuration for a newsmeme application.
    """

    DEBUG = True

    # change this in your production settings !!!

    SECRET_KEY = "secret"

    # keys for localhost. Change as appropriate.

    RECAPTCHA_PUBLIC_KEY = '6LeYIbsSAAAAACRPIllxA7wvXjIE411PfdB2gt2J'
    RECAPTCHA_PRIVATE_KEY = '6LeYIbsSAAAAAJezaIq3Ft_hSTo0YtyeFG-JgRtu'

    SQLALCHEMY_DATABASE_URI = "sqlite:///newsmeme.db"

    SQLALCHEMY_ECHO = False

    MAIL_DEBUG = DEBUG

    ADMINS = ()

    DEFAULT_MAIL_SENDER = "support@thenewsmeme.com"

    ACCEPT_LANGUAGES = ['en', 'fi']

    DEBUG_LOG = 'logs/debug.log'
    ERROR_LOG = 'logs/error.log'

    THEME = 'newsmeme'

    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 300


class TestConfig(object):

    TESTING = True
    CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ECHO = False





########NEW FILE########
__FILENAME__ = decorators
import functools

from flask import g

def keep_login_url(func):
    """
    Adds attribute g.keep_login_url in order to pass the current
    login URL to login/signup links.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        g.keep_login_url = True
        return func(*args, **kwargs)
    return wrapper


########NEW FILE########
__FILENAME__ = extensions
from flaskext.mail import Mail
from flaskext.openid import OpenID
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.cache import Cache

__all__ = ['oid', 'mail', 'db']

oid = OpenID()
mail = Mail()
db = SQLAlchemy()
cache = Cache()


########NEW FILE########
__FILENAME__ = account
# -*- coding: utf-8 -*-
from flaskext.wtf import Form, HiddenField, BooleanField, TextField, \
        PasswordField, SubmitField, TextField, RecaptchaField, \
        ValidationError, required, email, equal_to, regexp

from flaskext.babel import gettext, lazy_gettext as _ 

from newsmeme.models import User
from newsmeme.extensions import db

from .validators import is_username

class LoginForm(Form):

    next = HiddenField()
    
    remember = BooleanField(_("Remember me"))
    
    login = TextField(_("Username or email address"), validators=[
                      required(message=\
                               _("You must provide an email or username"))])

    password = PasswordField(_("Password"))

    submit = SubmitField(_("Login"))

class SignupForm(Form):

    next = HiddenField()

    username = TextField(_("Username"), validators=[
                         required(message=_("Username required")), 
                         is_username])

    password = PasswordField(_("Password"), validators=[
                             required(message=_("Password required"))])

    password_again = PasswordField(_("Password again"), validators=[
                                   equal_to("password", message=\
                                            _("Passwords don't match"))])

    email = TextField(_("Email address"), validators=[
                      required(message=_("Email address required")), 
                      email(message=_("A valid email address is required"))])

    recaptcha = RecaptchaField(_("Copy the words appearing below"))

    submit = SubmitField(_("Signup"))

    def validate_username(self, field):
        user = User.query.filter(User.username.like(field.data)).first()
        if user:
            raise ValidationError, gettext("This username is taken")

    def validate_email(self, field):
        user = User.query.filter(User.email.like(field.data)).first()
        if user:
            raise ValidationError, gettext("This email is taken")


class EditAccountForm(Form):

    username = TextField("Username", validators=[
                         required(_("Username is required")), is_username])

    email = TextField(_("Your email address"), validators=[
                      required(message=_("Email address required")),
                      email(message=_("A valid email address is required"))])

    receive_email = BooleanField(_("Receive private emails from friends"))
    
    email_alerts = BooleanField(_("Receive an email when somebody replies "
                                  "to your post or comment"))


    submit = SubmitField(_("Save"))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        kwargs['obj'] = self.user
        super(EditAccountForm, self).__init__(*args, **kwargs)
        
    def validate_username(self, field):
        user = User.query.filter(db.and_(
                                 User.username.like(field.data),
                                 db.not_(User.id==self.user.id))).first()

        if user:
            raise ValidationError, gettext("This username is taken")

    def validate_email(self, field):
        user = User.query.filter(db.and_(
                                 User.email.like(field.data),
                                 db.not_(User.id==self.user.id))).first()
        if user:
            raise ValidationError, gettext("This email is taken")


class RecoverPasswordForm(Form):

    email = TextField("Your email address", validators=[
                      email(message=_("A valid email address is required"))])

    submit = SubmitField(_("Find password"))


class ChangePasswordForm(Form):

    activation_key = HiddenField()

    password = PasswordField("Password", validators=[
                             required(message=_("Password is required"))])
    
    password_again = PasswordField(_("Password again"), validators=[
                                   equal_to("password", message=\
                                            _("Passwords don't match"))])

    submit = SubmitField(_("Save"))


class DeleteAccountForm(Form):
    
    recaptcha = RecaptchaField(_("Copy the words appearing below"))

    submit = SubmitField(_("Delete"))



########NEW FILE########
__FILENAME__ = comment
# -*- coding: utf-8 -*-
from flaskext.wtf import Form, TextAreaField, SubmitField, required
from flaskext.babel import lazy_gettext as _

class CommentForm(Form):

    comment = TextAreaField(validators=[
                            required(message=_("Comment is required"))])

    submit = SubmitField(_("Save"))
    cancel = SubmitField(_("Cancel"))

   
class CommentAbuseForm(Form):

    complaint = TextAreaField("Complaint", validators=[
                              required(message=\
                                       _("You must enter the details"
                                         " of the complaint"))])


    submit = SubmitField(_("Send"))

########NEW FILE########
__FILENAME__ = contact
# -*- coding: utf-8 -*-
from flaskext.wtf import Form, TextField, TextAreaField, SubmitField, \
        required, email

from flaskext.babel import lazy_gettext as _

class ContactForm(Form):

    name = TextField(_("Your name"), validators=[
                     required(message=_('Your name is required'))])

    email = TextField(_("Your email address"), validators=[
                      required(message=_("Email address required")),
                      email(message=_("A valid email address is required"))])

    subject = TextField(_("Subject"), validators=[
                        required(message=_("Subject required"))])

    message = TextAreaField(_("Message"), validators=[
                            required(message=_("Message required"))])

    submit = SubmitField(_("Send"))

class MessageForm(Form):

    subject = TextField(_("Subject"), validators=[
                        required(message=_("Subject required"))])

    message = TextAreaField(_("Message"), validators=[
                            required(message=_("Message required"))])

    submit = SubmitField(_("Send"))



########NEW FILE########
__FILENAME__ = openid
from flaskext.wtf import Form, HiddenField, TextField, RecaptchaField, \
        SubmitField, ValidationError, required, email, url

from flaskext.babel import lazy_gettext as _

from newsmeme.models import User

from .validators import is_username

class OpenIdSignupForm(Form):
    
    next = HiddenField()

    username = TextField(_("Username"), validators=[
                         required(_("Username required")), 
                         is_username])
    
    email = TextField(_("Email address"), validators=[
                      required(message=_("Email address required")), 
                      email(message=_("Valid email address required"))])
    
    recaptcha = RecaptchaField(_("Copy the words appearing below"))

    submit = SubmitField(_("Signup"))

    def validate_username(self, field):
        user = User.query.filter(User.username.like(field.data)).first()
        if user:
            raise ValidationError, gettext("This username is taken")

    def validate_email(self, field):
        user = User.query.filter(User.email.like(field.data)).first()
        if user:
            raise ValidationError, gettext("This email is taken")

class OpenIdLoginForm(Form):

    next = HiddenField()

    openid = TextField("OpenID", validators=[
                       required(_("OpenID is required")), 
                       url(_("OpenID must be a valid URL"))])

    submit = SubmitField(_("Login"))
 

########NEW FILE########
__FILENAME__ = post
# -*- coding: utf-8 -*-
from flaskext.wtf import Form, TextField, TextAreaField, RadioField, \
        SubmitField, ValidationError, optional, required, url
       
from flaskext.babel import gettext, lazy_gettext as _

from newsmeme.models import Post
from newsmeme.extensions import db

class PostForm(Form):

    title = TextField(_("Title of your post"), validators=[
                      required(message=_("Title required"))])

    link = TextField(_("Link"), validators=[
                     optional(),
                     url(message=_("This is not a valid URL"))])

    description = TextAreaField(_("Description"))

    tags = TextField(_("Tags"))

    access = RadioField(_("Who can see this post ?"), 
                        default=Post.PUBLIC, 
                        coerce=int,
                        choices=((Post.PUBLIC, _("Everyone")),
                                 (Post.FRIENDS, _("Friends only")),
                                 (Post.PRIVATE, _("Just myself"))))

    submit = SubmitField(_("Save"))

    def __init__(self, *args, **kwargs):
        self.post = kwargs.get('obj', None)
        super(PostForm, self).__init__(*args, **kwargs)

    def validate_link(self, field):
        posts = Post.query.public().filter_by(link=field.data)
        if self.post:
            posts = posts.filter(db.not_(Post.id==self.post.id))
        if posts.count():
            raise ValidationError, gettext("This link has already been posted")



########NEW FILE########
__FILENAME__ = validators
from flaskext.wtf import regexp

from flaskext.babel import lazy_gettext as _

USERNAME_RE = r'^[\w.+-]+$'

is_username = regexp(USERNAME_RE, 
                     message=_("You can only use letters, numbers or dashes"))



########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-
"""
    helpers.py
    ~~~~~~~~

    Helper functions for newsmeme

    :copyright: (c) 2010 by Dan Jacob.
    :license: BSD, see LICENSE for more details.
"""
import markdown
import re
import urlparse
import functools

from datetime import datetime

from flask import current_app, g

from flaskext.babel import gettext, ngettext
from flaskext.themes import static_file_url, render_theme_template 

from newsmeme.extensions import cache

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug. From http://flask.pocoo.org/snippets/5/"""
    result = []
    for word in _punct_re.split(text.lower()):
        #word = word.encode('translit/long')
        if word:
            result.append(word)
    return unicode(delim.join(result))

markdown = functools.partial(markdown.markdown,
                             safe_mode='remove',
                             output_format="html")


cached = functools.partial(cache.cached,
                           unless= lambda: g.user is not None)

def get_theme():
    return current_app.config['THEME']


def render_template(template, **context):
    return render_theme_template(get_theme(), template, **context)


def timesince(dt, default=None):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    """
    
    if default is None:
        default = gettext("just now")

    now = datetime.utcnow()
    diff = now - dt
    
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        
        if not period:
            continue

        singular = u"%%(num)d %s ago" % singular
        plural = u"%%(num)d %s ago" % plural

        return ngettext(singular, plural, num=period)

    return default


def domain(url):
    """
    Returns the domain of a URL e.g. http://reddit.com/ > reddit.com
    """
    rv = urlparse.urlparse(url).netloc
    if rv.startswith("www."):
        rv = rv[4:]
    return rv


########NEW FILE########
__FILENAME__ = comments
from datetime import datetime

from werkzeug import cached_property

from flask import Markup
from flaskext.sqlalchemy import BaseQuery
from flaskext.principal import Permission, UserNeed, Denial

from newsmeme import signals
from newsmeme.extensions import db
from newsmeme.permissions import auth, moderator
from newsmeme.helpers import markdown
from newsmeme.models.posts import Post
from newsmeme.models.users import User
from newsmeme.models.types import DenormalizedText

class CommentQuery(BaseQuery):

    def restricted(self, user):

        if user and user.is_moderator:
            return self
       
        q = self.join(Post)
        criteria = [Post.access==Post.PUBLIC]

        if user:
            criteria.append(Post.author_id==user.id)
            if user.friends:
                criteria.append(db.and_(Post.access==Post.FRIENDS,
                                        Post.author_id.in_(user.friends)))
        
        return q.filter(reduce(db.or_, criteria))

   
class Comment(db.Model):

    __tablename__ = "comments"

    PER_PAGE = 20

    query_class = CommentQuery

    id = db.Column(db.Integer, primary_key=True)
    
    author_id = db.Column(db.Integer, 
                          db.ForeignKey(User.id, ondelete='CASCADE'), 
                          nullable=False)

    post_id = db.Column(db.Integer, 
                        db.ForeignKey(Post.id, ondelete='CASCADE'), 
                        nullable=False)

    parent_id = db.Column(db.Integer, 
                          db.ForeignKey("comments.id", ondelete='CASCADE'))

    comment = db.Column(db.UnicodeText)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer, default=1)
    votes = db.Column(DenormalizedText)

    author = db.relation(User, innerjoin=True, lazy="joined")

    post = db.relation(Post, innerjoin=True, lazy="joined")

    parent = db.relation('Comment', remote_side=[id])

    __mapper_args__ = {'order_by' : id.asc()}
    
    class Permissions(object):

        def __init__(self, obj):
            self.obj = obj

        @cached_property
        def default(self):
            return Permission(UserNeed(self.obj.author_id)) & moderator

        @cached_property
        def edit(self):
            return self.default

        @cached_property
        def delete(self):
            return self.default

        @cached_property
        def vote(self):

            needs = [UserNeed(user_id) for user_id in self.obj.votes]
            needs.append(UserNeed(self.obj.author_id))

            return auth & Denial(*needs)

   
    def __init__(self, *args, **kwargs):
        super(Comment, self).__init__(*args, **kwargs)
        self.votes = self.votes or set()

    @cached_property
    def permissions(self):
        return self.Permissions(self)

    def vote(self, user):
        self.votes.add(user.id)

    def _url(self, _external=False):
        return '%s#comment-%d' % (self.post._url(_external), self.id)

    @cached_property
    def url(self):
        return self._url()

    @cached_property
    def permalink(self):
        return self._url(True)

    @cached_property
    def markdown(self):
        return Markup(markdown(self.comment or ''))

# ------------- SIGNALS ----------------#

def update_num_comments(sender):
    sender.num_comments = \
        Comment.query.filter(Comment.post_id==sender.id).count()
    
    db.session.commit()


signals.comment_added.connect(update_num_comments)
signals.comment_deleted.connect(update_num_comments)


########NEW FILE########
__FILENAME__ = posts
import random

from datetime import datetime

from werkzeug import cached_property

from flask import url_for, Markup
from flaskext.sqlalchemy import BaseQuery
from flaskext.principal import Permission, UserNeed, Denial

from newsmeme.extensions import db
from newsmeme.helpers import slugify, domain, markdown
from newsmeme.permissions import auth, moderator
from newsmeme.models.types import DenormalizedText
from newsmeme.models.users import User

class PostQuery(BaseQuery):

    def jsonify(self):
        for post in self.all():
            yield post.json

    def as_list(self):
        """
        Return restricted list of columns for list queries
        """

        deferred_cols = ("description", 
                         "tags",
                         "author.email",
                         "author.password",
                         "author.activation_key",
                         "author.openid",
                         "author.date_joined",
                         "author.receive_email",
                         "author.email_alerts",
                         "author.followers",
                         "author.following")


        options = [db.defer(col) for col in deferred_cols]
        return self.options(*options)
        
    def deadpooled(self):
        return self.filter(Post.score <= 0)

    def popular(self):
        return self.filter(Post.score > 0)
    
    def hottest(self):
        return self.order_by(Post.num_comments.desc(),
                             Post.score.desc(),
                             Post.id.desc())

    def public(self):
        return self.filter(Post.access==Post.PUBLIC)

    def restricted(self, user=None):
        """
        Returns posts filtered for a) public posts b) posts authored by
        the user or c) posts authored by friends
        """

        if user and user.is_moderator:
            return self

        criteria = [Post.access==Post.PUBLIC]

        if user:
            criteria.append(Post.author_id==user.id)
            if user.friends:
                criteria.append(db.and_(Post.access==Post.FRIENDS,
                                        Post.author_id.in_(user.friends)))
        
        return self.filter(reduce(db.or_, criteria))

    def search(self, keywords):

        criteria = []

        for keyword in keywords.split():

            keyword = '%' + keyword + '%'

            criteria.append(db.or_(Post.title.ilike(keyword),
                                   Post.description.ilike(keyword),
                                   Post.link.ilike(keyword),
                                   Post.tags.ilike(keyword),
                                   User.username.ilike(keyword)))


        q = reduce(db.and_, criteria)
        
        return self.filter(q).join(User).distinct()


class Post(db.Model):

    __tablename__ = "posts"
    
    PUBLIC = 100
    FRIENDS = 200
    PRIVATE = 300

    PER_PAGE = 40

    query_class = PostQuery

    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, 
                          db.ForeignKey(User.id, ondelete='CASCADE'), 
                          nullable=False)
    
    title = db.Column(db.Unicode(200))
    description = db.Column(db.UnicodeText)
    link = db.Column(db.String(250))
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer, default=1)
    num_comments = db.Column(db.Integer, default=0)
    votes = db.Column(DenormalizedText)
    access = db.Column(db.Integer, default=PUBLIC)

    _tags = db.Column("tags", db.UnicodeText)

    author = db.relation(User, innerjoin=True, lazy="joined")
    
    __mapper_args__ = {'order_by' : id.desc()}

    class Permissions(object):

        def __init__(self, obj):
            self.obj = obj

        @cached_property
        def default(self):
            return Permission(UserNeed(self.obj.author_id)) & moderator

        @cached_property
        def view(self):
            if self.obj.access == Post.PUBLIC:
                return Permission()

            if self.obj.access == Post.FRIENDS:
                needs = [UserNeed(user_id) for user_id in \
                            self.obj.author.friends]

                return self.default & Permission(*needs)

            return self.default

        @cached_property
        def edit(self):
            return self.default

        @cached_property
        def delete(self):
            return self.default

        @cached_property
        def vote(self):

            needs = [UserNeed(user_id) for user_id in self.obj.votes]
            needs.append(UserNeed(self.obj.author_id))

            return auth & Denial(*needs)

        @cached_property
        def comment(self):
            return auth

    def __init__(self, *args, **kwargs):
        super(Post, self).__init__(*args, **kwargs)
        self.votes = self.votes or set()
        self.access = self.access or self.PUBLIC

    def __str__(self):
        return self.title

    def __repr__(self):
        return "<%s>" % self

    @cached_property
    def permissions(self):
        return self.Permissions(self)

    def vote(self, user):
        self.votes.add(user.id)

    def _get_tags(self):
        return self._tags 

    def _set_tags(self, tags):
        
        self._tags = tags

        if self.id:
            # ensure existing tag references are removed
            d = db.delete(post_tags, post_tags.c.post_id==self.id)
            db.engine.execute(d)

        for tag in set(self.taglist):

            slug = slugify(tag)

            tag_obj = Tag.query.filter(Tag.slug==slug).first()
            if tag_obj is None:
                tag_obj = Tag(name=tag, slug=slug)
                db.session.add(tag_obj)
            
            if self not in tag_obj.posts:
                tag_obj.posts.append(self)

    tags = db.synonym("_tags", descriptor=property(_get_tags, _set_tags))

    @property
    def taglist(self):
        if self.tags is None:
            return []

        tags = [t.strip() for t in self.tags.split(",")]
        return [t for t in tags if t]

    @cached_property
    def linked_taglist(self):
        """
        Returns the tags in the original order and format, 
        with link to tag page
        """
        return [(tag, url_for('frontend.tag', 
                              slug=slugify(tag))) \
                for tag in self.taglist]

    @cached_property
    def domain(self):
        if not self.link:
            return ''
        return domain(self.link)

    @cached_property
    def json(self):
        """
        Returns dict of safe attributes for passing into 
        a JSON request.
        """
        
        return dict(post_id=self.id,
                    score=self.score,
                    title=self.title,
                    link=self.link,
                    description=self.description,
                    num_comments=self.num_comments,
                    author=self.author.username)

    @cached_property
    def access_name(self):
        return {
                 Post.PUBLIC : "public",
                 Post.FRIENDS : "friends",
                 Post.PRIVATE : "private"
               }.get(self.access, "public")
        
    def can_access(self, user=None):
        if self.access == self.PUBLIC:
            return True

        if user is None:
            return False

        if user.is_moderator or user.id == self.author_id:
            return True

        return self.access == self.FRIENDS and self.author_id in user.friends

    @cached_property
    def comments(self):
        """
        Returns comments in tree. Each parent comment has a "comments" 
        attribute appended and a "depth" attribute.
        """
        from newsmeme.models.comments import Comment

        comments = Comment.query.filter(Comment.post_id==self.id).all()

        def _get_comments(parent, depth):
            
            parent.comments = []
            parent.depth = depth

            for comment in comments:
                if comment.parent_id == parent.id:
                    parent.comments.append(comment)
                    _get_comments(comment, depth + 1)


        parents = [c for c in comments if c.parent_id is None]

        for parent in parents:
            _get_comments(parent, 0)

        return parents
        
    def _url(self, _external=False):
        return url_for('post.view', 
                       post_id=self.id, 
                       slug=self.slug, 
                       _external=_external)

    @cached_property
    def url(self):
        return self._url()

    @cached_property
    def permalink(self):
        return self._url(True)

    @cached_property
    def markdown(self):
        return Markup(markdown(self.description or ''))

    @cached_property
    def slug(self):
        return slugify(self.title or '')[:80]


post_tags = db.Table("post_tags", db.Model.metadata,
    db.Column("post_id", db.Integer, 
              db.ForeignKey('posts.id', ondelete='CASCADE'), 
              primary_key=True),

    db.Column("tag_id", db.Integer, 
              db.ForeignKey('tags.id', ondelete='CASCADE'),
              primary_key=True))


class TagQuery(BaseQuery):

    def cloud(self):

        tags = self.filter(Tag.num_posts > 0).all()

        if not tags:
            return []

        max_posts = max(t.num_posts for t in tags)
        min_posts = min(t.num_posts for t in tags)

        diff = (max_posts - min_posts) / 10.0
        if diff < 0.1:
            diff = 0.1

        for tag in tags:
            tag.size = int(tag.num_posts / diff)
            if tag.size < 1: 
                tag.size = 1

        random.shuffle(tags)

        return tags


class Tag(db.Model):

    __tablename__ = "tags"
    
    query_class = TagQuery

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Unicode(80), unique=True)
    posts = db.dynamic_loader(Post, secondary=post_tags, query_class=PostQuery)

    _name = db.Column("name", db.Unicode(80), unique=True)
    
    def __str__(self):
        return self.name

    def _get_name(self):
        return self._name

    def _set_name(self, name):
        self._name = name.lower().strip()
        self.slug = slugify(name)

    name = db.synonym("_name", descriptor=property(_get_name, _set_name))

    @cached_property
    def url(self):
        return url_for("frontend.tag", slug=self.slug)

    num_posts = db.column_property(
        db.select([db.func.count(post_tags.c.post_id)]).\
            where(db.and_(post_tags.c.tag_id==id,
                          Post.id==post_tags.c.post_id,
                          Post.access==Post.PUBLIC)).as_scalar())



########NEW FILE########
__FILENAME__ = types
from sqlalchemy import types

class DenormalizedText(types.MutableType, types.TypeDecorator):
    """
    Stores denormalized primary keys that can be 
    accessed as a set. 

    :param coerce: coercion function that ensures correct
                   type is returned

    :param separator: separator character
    """

    impl = types.Text

    def __init__(self, coerce=int, separator=" ", **kwargs):

        self.coerce = coerce
        self.separator = separator
        
        super(DenormalizedText, self).__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        if value is not None:
            items = [str(item).strip() for item in value]
            value = self.separator.join(item for item in items if item)
        return value

    def process_result_value(self, value, dialect):
         if not value:
            return set()
         return set(self.coerce(item) \
                   for item in value.split(self.separator))
        
    def copy_value(self, value):
        return set(value)


########NEW FILE########
__FILENAME__ = users
import hashlib

from datetime import datetime

from werkzeug import generate_password_hash, check_password_hash, \
    cached_property

from flaskext.sqlalchemy import BaseQuery
from flaskext.principal import RoleNeed, UserNeed, Permission

from newsmeme.extensions import db
from newsmeme.permissions import null
from newsmeme.models.types import DenormalizedText

class UserQuery(BaseQuery):

    def from_identity(self, identity):
        """
        Loads user from flaskext.principal.Identity instance and
        assigns permissions from user.

        A "user" instance is monkeypatched to the identity instance.

        If no user found then None is returned.
        """

        try:
            user = self.get(int(identity.name))
        except ValueError:
            user = None

        if user:
            identity.provides.update(user.provides)

        identity.user = user

        return user
 
    def authenticate(self, login, password):
        
        user = self.filter(db.or_(User.username==login,
                                  User.email==login)).first()

        if user:
            authenticated = user.check_password(password)
        else:
            authenticated = False

        return user, authenticated

    def authenticate_openid(self, email, openid):

        user = self.filter(User.email==email).first()

        if user:
            authenticated = user.check_openid(openid)
        else:
            authenticated = False

        return user, authenticated


class User(db.Model):
    
    __tablename__ = "users"

    query_class = UserQuery

    # user roles
    MEMBER = 100
    MODERATOR = 200
    ADMIN = 300

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Unicode(60), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    karma = db.Column(db.Integer, default=0)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    activation_key = db.Column(db.String(80), unique=True)
    role = db.Column(db.Integer, default=MEMBER)
    receive_email = db.Column(db.Boolean, default=False)
    email_alerts = db.Column(db.Boolean, default=False)
    followers = db.Column(DenormalizedText)
    following = db.Column(DenormalizedText)

    _password = db.Column("password", db.String(80))
    _openid = db.Column("openid", db.String(80), unique=True)

    class Permissions(object):

        def __init__(self, obj):
            self.obj = obj

        @cached_property
        def send_message(self):
            if not self.obj.receive_email:
                return null

            needs = [UserNeed(user_id) for user_id in self.obj.friends]
            if not needs:
                return null

            return Permission(*needs)

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self.followers = self.followers or set()
        self.following = self.following or set()

    def __str__(self):
        return self.username

    def __repr__(self):
        return "<%s>" % self

    @cached_property
    def permissions(self):
        return self.Permissions(self)

    def _get_password(self):
        return self._password

    def _set_password(self, password):
        self._password = generate_password_hash(password)

    password = db.synonym("_password", 
                          descriptor=property(_get_password,
                                              _set_password))

    def check_password(self, password):
        if self.password is None:
            return False
        return check_password_hash(self.password, password)

    def _get_openid(self):
        return self._openid

    def _set_openid(self, openid):
        self._openid = generate_password_hash(openid)

    openid = db.synonym("_openid", 
                          descriptor=property(_get_openid,
                                              _set_openid))

    def check_openid(self, openid):
        if self.openid is None:
            return False
        return check_password_hash(self.openid, openid)

    @cached_property
    def provides(self):
        needs = [RoleNeed('authenticated'),
                 UserNeed(self.id)]

        if self.is_moderator:
            needs.append(RoleNeed('moderator'))

        if self.is_admin:
            needs.append(RoleNeed('admin'))

        return needs

    @cached_property
    def num_followers(self):
        if self.followers:
            return len(self.followers)
        return 0

    @cached_property
    def num_following(self):
        return len(self.following)

    def is_following(self, user):
        return user.id in self.following

    @property
    def friends(self):
        return self.following.intersection(self.followers)

    def is_friend(self, user):
        return user.id in self.friends

    def get_friends(self):
        return User.query.filter(User.id.in_(self.friends))

    def follow(self, user):
        
        user.followers.add(self.id)
        self.following.add(user.id)

    def unfollow(self, user):
        if self.id in user.followers:
            user.followers.remove(self.id)

        if user.id in self.following:
            self.following.remove(user.id)

    def get_following(self):
        """
        Return following users as query
        """
        return User.query.filter(User.id.in_(self.following or set()))

    def get_followers(self):
        """
        Return followers as query
        """
        return User.query.filter(User.id.in_(self.followers or set()))

    @property
    def is_moderator(self):
        return self.role >= self.MODERATOR

    @property
    def is_admin(self):
        return self.role >= self.ADMIN

    @cached_property
    def gravatar(self):
        if not self.email:
            return ''
        md5 = hashlib.md5()
        md5.update(self.email.strip().lower())
        return md5.hexdigest()

    def gravatar_url(self, size=80):
        if not self.gravatar:
            return ''

        return "http://www.gravatar.com/avatar/%s.jpg?s=%d" % (
            self.gravatar, size)

 

########NEW FILE########
__FILENAME__ = permissions
from flaskext.principal import RoleNeed, Permission

admin = Permission(RoleNeed('admin'))
moderator = Permission(RoleNeed('moderator'))
auth = Permission(RoleNeed('authenticated'))

# this is assigned when you want to block a permission to all
# never assign this role to anyone !
null = Permission(RoleNeed('null'))

########NEW FILE########
__FILENAME__ = signals
from blinker import Namespace

signals = Namespace()

comment_added = signals.signal("comment-added")
comment_deleted = signals.signal("comment-deleted")


########NEW FILE########
__FILENAME__ = account
import uuid

from flask import Module, flash, request, g, current_app, \
    abort, redirect, url_for, session, jsonify

from flaskext.mail import Message
from flaskext.babel import gettext as _
from flaskext.principal import identity_changed, Identity, AnonymousIdentity

from newsmeme.forms import ChangePasswordForm, EditAccountForm, \
    DeleteAccountForm, LoginForm, SignupForm, RecoverPasswordForm

from newsmeme.models import User
from newsmeme.helpers import render_template
from newsmeme.extensions import db, mail
from newsmeme.permissions import auth

account = Module(__name__)

@account.route("/login/", methods=("GET", "POST"))
def login():

    form = LoginForm(login=request.args.get("login", None),
                     next=request.args.get("next", None))

    # TBD: ensure "next" field is passed properly

    if form.validate_on_submit():
        user, authenticated = \
            User.query.authenticate(form.login.data,
                                    form.password.data)

        if user and authenticated:
            session.permanent = form.remember.data
            
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.id))

            # check if openid has been passed in
            openid = session.pop('openid', None)
            if openid:
                user.openid = openid
                db.session.commit()
                
                flash(_("Your OpenID has been attached to your account. "
                      "You can now sign in with your OpenID."), "success")


            else:
                flash(_("Welcome back, %(name)s", name=user.username), "success")

            next_url = form.next.data

            if not next_url or next_url == request.path:
                next_url = url_for('user.posts', username=user.username)

            return redirect(next_url)

        else:

            flash(_("Sorry, invalid login"), "error")

    return render_template("account/login.html", form=form)

@account.route("/signup/", methods=("GET", "POST"))
def signup():

    form = SignupForm(next=request.args.get("next"))

    if form.validate_on_submit():
        
        user = User()
        form.populate_obj(user)

        db.session.add(user)
        db.session.commit()

        identity_changed.send(current_app._get_current_object(),
                              identity=Identity(user.id))

        flash(_("Welcome, %(name)s", name=user.username), "success")

        next_url = form.next.data

        if not next_url or next_url == request.path:
            next_url = url_for('user.posts', username=user.username)

        return redirect(next_url)

    return render_template("account/signup.html", form=form)


@account.route("/logout/")
def logout():

    flash(_("You are now logged out"), "success")
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())

    return redirect(url_for('frontend.index'))


@account.route("/forgotpass/", methods=("GET", "POST"))
def forgot_password():

    form = RecoverPasswordForm()

    if form.validate_on_submit():

        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            flash(_("Please see your email for instructions on "
                  "how to access your account"), "success")
            
            user.activation_key = str(uuid.uuid4())
            db.session.commit()

            body = render_template("emails/recover_password.html",
                                   user=user)

            message = Message(subject=_("Recover your password"),
                              body=body,
                              recipients=[user.email])

            mail.send(message)
            
            return redirect(url_for("frontend.index"))

        else:

            flash(_("Sorry, no user found for that email address"), "error")

    return render_template("account/recover_password.html", form=form)


@account.route("/changepass/", methods=("GET", "POST"))
def change_password():

    user = None

    if g.user:
        user = g.user

    elif 'activation_key' in request.values:
        user = User.query.filter_by(
            activation_key=request.values['activation_key']).first()
    
    if user is None:
        abort(403)

    form = ChangePasswordForm(activation_key=user.activation_key)

    if form.validate_on_submit():

        user.password = form.password.data
        user.activation_key = None

        db.session.commit()

        flash(_("Your password has been changed, "
                "please log in again"), "success")

        return redirect(url_for("account.login"))

    return render_template("account/change_password.html", form=form)
        

@account.route("/edit/", methods=("GET", "POST"))
@auth.require(401)
def edit():
    
    form = EditAccountForm(g.user)

    if form.validate_on_submit():

        form.populate_obj(g.user)
        db.session.commit()

        flash(_("Your account has been updated"), "success")

        return redirect(url_for("frontend.index"))

    return render_template("account/edit_account.html", form=form)


@account.route("/delete/", methods=("GET", "POST"))
@auth.require(401)
def delete():

    # confirm password & recaptcha
    form = DeleteAccountForm()

    if form.validate_on_submit():

        db.session.delete(g.user)
        db.session.commit()
    
        identity_changed.send(current_app._get_current_object(),
                              identity=AnonymousIdentity())

        flash(_("Your account has been deleted"), "success")

        return redirect(url_for("frontend.index"))

    return render_template("account/delete_account.html", form=form)


@account.route("/follow/<int:user_id>/", methods=("POST",))
@auth.require(401)
def follow(user_id):
    
    user = User.query.get_or_404(user_id)
    g.user.follow(user)
    db.session.commit()

    body = render_template("emails/followed.html",
                           user=user)

    mail.send_message(subject=_("%s is now following you" % g.user.username),
                      body=body,
                      recipients=[user.email])

    return jsonify(success=True,
                   reload=True)


@account.route("/unfollow/<int:user_id>/", methods=("POST",))
@auth.require(401)
def unfollow(user_id):
    
    user = User.query.get_or_404(user_id)
    g.user.unfollow(user)
    db.session.commit()

    return jsonify(success=True,
                   reload=True)


########NEW FILE########
__FILENAME__ = api
from flask import Module, jsonify, request

from newsmeme.models import Post, User
from newsmeme.helpers import cached

api = Module(__name__)

@api.route("/post/<int:post_id>/")
@cached()
def post(post_id):

    post = Post.query.public().filter_by(id=post_id).first_or_404()

    return jsonify(**post.json)


@api.route("/search/")
def search():

    keywords = request.args.get("keywords", "")

    if not keywords:
        return jsonify(results=[])

    num_results = int(request.args.get("num_results", 20))

    if num_results > 100:
        num_results = 100

    posts = Post.query.search(keywords).public().limit(num_results)
    
    return jsonify(results=list(posts.jsonify()))


@api.route("/user/<username>/")
@cached()
def user(username):

    user = User.query.filter_by(username=username).first_or_404()
    
    posts = Post.query.filter_by(author_id=user.id).public()

    return jsonify(posts=list(posts.jsonify()))



########NEW FILE########
__FILENAME__ = comment
from flask import Module, redirect, flash, g, jsonify, current_app

from flaskext.mail import Message
from flaskext.babel import gettext as _

from newsmeme import signals
from newsmeme.helpers import render_template
from newsmeme.permissions import auth
from newsmeme.models import Comment
from newsmeme.forms import CommentForm, CommentAbuseForm
from newsmeme.extensions import db, mail

comment = Module(__name__)

@comment.route("/<int:comment_id>/edit/", methods=("GET", "POST"))
@auth.require(401)
def edit(comment_id):

    comment = Comment.query.get_or_404(comment_id)
    comment.permissions.edit.test(403)

    form = CommentForm(obj=comment)

    if form.validate_on_submit():
        
        form.populate_obj(comment)

        db.session.commit()

        flash(_("Your comment has been updated"), "success")

        return redirect(comment.url)
    
    return render_template("comment/edit_comment.html",
                           comment=comment,
                           form=form)

@comment.route("/<int:comment_id>/delete/", methods=("POST",))
@auth.require(401)
def delete(comment_id):

    comment = Comment.query.get_or_404(comment_id)
    comment.permissions.delete.test(403)

    db.session.delete(comment)
    db.session.commit()

    signals.comment_deleted.send(comment.post)

    return jsonify(success=True,
                   comment_id=comment_id)

@comment.route("/<int:comment_id>/abuse/", methods=("GET", "POST",))
@auth.require(401)
def report_abuse(comment_id):

    comment = Comment.query.get_or_404(comment_id)
    form = CommentAbuseForm()
    if form.validate_on_submit():

        admins = current_app.config['ADMINS']

        if admins:

            body = render_template("emails/report_abuse.html",
                               comment=comment,
                               complaint=form.complaint.data)
            
            message = Message(subject="Report Abuse",
                              body=body,
                              sender=g.user.email,
                              recipients=admins)

            mail.send(message)
            
        flash(_("Your report has been sent to the admins"), "success")

        return redirect(comment.url)

    return render_template("comment/report_abuse.html",
                           comment=comment,
                           form=form)

@comment.route("/<int:comment_id>/upvote/", methods=("POST",))
@auth.require(401)
def upvote(comment_id):
    return _vote(comment_id, 1)


@comment.route("/<int:comment_id>/downvote/", methods=("POST",))
@auth.require(401)
def downvote(comment_id):
    return _vote(comment_id, -1)


def _vote(comment_id, score):

    comment = Comment.query.get_or_404(comment_id)
    comment.permissions.vote.test(403)
    
    comment.score += score
    comment.author.karma += score

    if comment.author.karma < 0:
        comment.author.karma = 0

    comment.vote(g.user)

    db.session.commit()

    return jsonify(success=True,
                   comment_id=comment_id,
                   score=comment.score)

########NEW FILE########
__FILENAME__ = feeds

from datetime import datetime

from flask import Module, request, url_for

from werkzeug.contrib.atom import AtomFeed

from newsmeme.models import User, Post, Tag
from newsmeme.helpers import cached

feeds = Module(__name__)

class PostFeed(AtomFeed):

    def add_post(self, post):

        self.add(post.title,
                 unicode(post.markdown),
                 content_type="html",
                 author=post.author.username,
                 url=post.permalink,
                 updated=datetime.utcnow(),
                 published=post.date_created)


@feeds.route("/")
@cached()
def index():
    feed = PostFeed("newsmeme - hot",
                    feed_url=request.url,
                    url=request.url_root)

    posts = Post.query.hottest().public().limit(15)

    for post in posts:
        feed.add_post(post)

    return feed.get_response()


@feeds.route("/latest/")
@cached()
def latest():
    feed = PostFeed("newsmeme - new",
                    feed_url=request.url,
                    url=request.url_root)

    posts = Post.query.public().limit(15)

    for post in posts:
        feed.add_post(post)

    return feed.get_response()


@feeds.route("/deadpool/")
@cached()
def deadpool():
    feed = PostFeed("newsmeme - deadpool",
                    feed_url=request.url,
                    url=request.url_root)

    posts = Post.query.deadpooled().public().limit(15)

    for post in posts:
        feed.add_post(post)

    return feed.get_response()


@feeds.route("/tag/<slug>/")
@cached()
def tag(slug):

    tag = Tag.query.filter_by(slug=slug).first_or_404()

    feed = PostFeed("newsmeme - %s"  % tag,
                    feed_url=request.url,
                    url=request.url_root)

    posts = tag.posts.public().limit(15)

    for post in posts:
        feed.add_post(post)

    return feed.get_response()


@feeds.route("/user/<username>/")
@cached()
def user(username):
    user = User.query.filter_by(username=username).first_or_404()

    feed = PostFeed("newsmeme - %s" % user.username,
                    feed_url=request.url,
                    url=request.url_root)
    
    posts = Post.query.filter_by(author_id=user.id).public().limit(15)
    
    for post in posts:
        feed.add_post(post)

    return feed.get_response()
    

########NEW FILE########
__FILENAME__ = frontend
from flask import Module, url_for, \
    redirect, g, flash, request, current_app

from flaskext.mail import Message
from flaskext.babel import gettext as _

from newsmeme.models import Post, Tag
from newsmeme.extensions import mail, db
from newsmeme.helpers import render_template, cached
from newsmeme.forms import PostForm, ContactForm
from newsmeme.decorators import keep_login_url
from newsmeme.permissions import auth

frontend = Module(__name__)

@frontend.route("/")
@frontend.route("/<int:page>/")
@cached()
@keep_login_url
def index(page=1):
    
    page_obj = Post.query.popular().hottest().restricted(g.user).as_list().\
                          paginate(page, per_page=Post.PER_PAGE)
        
    page_url = lambda page: url_for("frontend.index", page=page)

    return render_template("index.html", 
                           page_obj=page_obj, 
                           page_url=page_url)


@frontend.route("/latest/")
@frontend.route("/latest/<int:page>/")
@cached()
@keep_login_url
def latest(page=1):
    
    page_obj = Post.query.popular().restricted(g.user).as_list().\
                          paginate(page, per_page=Post.PER_PAGE)

    page_url = lambda page: url_for("frontend.latest", page=page)

    return render_template("latest.html", 
                           page_obj=page_obj, 
                           page_url=page_url)


@frontend.route("/deadpool/")
@frontend.route("/deadpool/<int:page>/")
@cached()
@keep_login_url
def deadpool(page=1):

    page_obj = Post.query.deadpooled().restricted(g.user).as_list().\
                          paginate(page, per_page=Post.PER_PAGE)

    page_url = lambda page: url_for("frontend.deadpool", page=page)

    return render_template("deadpool.html", 
                           page_obj=page_obj, 
                           page_url=page_url)


@frontend.route("/submit/", methods=("GET", "POST"))
@auth.require(401)
def submit():

    form = PostForm()
    
    if form.validate_on_submit():

        post = Post(author=g.user)
        form.populate_obj(post)

        db.session.add(post)
        db.session.commit()

        flash(_("Thank you for posting"), "success")

        return redirect(url_for("frontend.latest"))

    return render_template("submit.html", form=form)


@frontend.route("/search/")
@frontend.route("/search/<int:page>/")
@keep_login_url
def search(page=1):

    keywords = request.args.get("keywords", '').strip()

    if not keywords:
        return redirect(url_for("frontend.index"))

    page_obj = Post.query.search(keywords).restricted(g.user).as_list().
                          paginate(page, per_page=Post.PER_PAGE)

    if page_obj.total == 1:

        post = page_obj.items[0]
        return redirect(post.url)
    
    page_url = lambda page: url_for('frontend.search', 
                                    page=page,
                                    keywords=keywords)

    return render_template("search.html",
                           page_obj=page_obj,
                           page_url=page_url,
                           keywords=keywords)



@frontend.route("/contact/", methods=("GET", "POST"))
@keep_login_url
def contact():

    if g.user:
        form = ContactForm(name=g.user.username,
                           email=g.user.email)

    else:
        form = ContactForm()

    if form.validate_on_submit():

        admins = current_app.config.get('ADMINS', [])

        from_address = "%s <%s>" % (form.name.data, 
                                    form.email.data)

        if admins:
            message = Message(subject=form.subject.data,
                              body=form.message.data,
                              recipients=admins,
                              sender=from_address)

            mail.send(message)
        
        flash(_("Thanks, your message has been sent to us"), "success")

        return redirect(url_for('frontend.index'))

    return render_template("contact.html", form=form)


@frontend.route("/tags/")
@cached()
@keep_login_url
def tags():
    tags = Tag.query.cloud()
    return render_template("tags.html", tag_cloud=tags)


@frontend.route("/tags/<slug>/")
@frontend.route("/tags/<slug>/<int:page>/")
@cached()
@keep_login_url
def tag(slug, page=1):
    tag = Tag.query.filter_by(slug=slug).first_or_404()

    page_obj = tag.posts.restricted(g.user).as_list().\
                    paginate(page, per_page=Post.PER_PAGE)

    page_url = lambda page: url_for('frontend.tag',
                                    slug=slug,
                                    page=page)

    return render_template("tag.html", 
                           tag=tag,
                           page_url=page_url,
                           page_obj=page_obj)
    

@frontend.route("/help/")
@keep_login_url
def help():
    return render_template("help.html")


@frontend.route("/rules/")
@keep_login_url
def rules():
    return render_template("rules.html")

########NEW FILE########
__FILENAME__ = openid
from flask import Module, redirect, url_for, session, flash, \
    abort, request, current_app

from flaskext.babel import gettext as _
from flaskext.principal import Identity, identity_changed

from newsmeme.models import User
from newsmeme.helpers import slugify, render_template
from newsmeme.forms import OpenIdSignupForm, OpenIdLoginForm
from newsmeme.extensions import oid, db

openid = Module(__name__)

@oid.after_login
def create_or_login(response):
    
    openid = response.identity_url

    user, authenticated = \
        User.query.authenticate_openid(response.email, openid)

    next_url = session.pop('next', None)
    
    if user is None:
        session['openid'] = openid
        
        username = response.fullname or response.nickname
        if username:
            username = slugify(username.replace("-", "_"))

        return redirect(url_for("openid.signup", 
                                next=next_url,
                                name=username,
                                email=response.email))

    if authenticated:
        
        session.permanent = True

        identity_changed.send(current_app._get_current_object(),
                              identity=Identity(user.id))
        
        flash(_("Welcome back, %%s") % user.username, "success")
        
        if next_url is None:
            next_url = url_for('user.posts', username=user.username)

        return redirect(next_url)
    
    # user already exists, so login and attach openid
    session['openid'] = openid 

    flash(_("You already have an account with us. "
            "Please login with your email address so your "
            "OpenID can be attached to your user account"), "success")

    return redirect(url_for('account.login', 
                            login=response.email))


@openid.route("/login/", methods=("GET", "POST"))
@oid.loginhandler
def login():
    
    form = OpenIdLoginForm(next=request.args.get("next"))

    if form.validate_on_submit():
        session['next'] = form.next.data

        return oid.try_login(form.openid.data,  
                             ask_for=('email', 'fullname', 'nickname'))

    return render_template("openid/login.html", 
                           form=form,
                           error=oid.fetch_error())


@openid.route("/signup/", methods=("GET", "POST"))
def signup():
    
    if 'openid' not in session:
        abort(403)

    form = OpenIdSignupForm(next=request.args.get("next"),
                            username=request.args.get("name"),
                            email=request.args.get("email"))

    if form.validate_on_submit():

        user = User(openid=session.pop('openid'))
        form.populate_obj(user)

        db.session.add(user)
        db.session.commit()

        session.permanent = True

        identity_changed.send(current_app._get_current_object(),
                              identity=Identity(user.id))

        flash(_("Welcome, %%s") % user.username, "success")

        next_url = form.next.data or \
            url_for("user.posts", username=user.username)
    
        return redirect(next_url)

    return render_template("openid/signup.html", form=form)

########NEW FILE########
__FILENAME__ = post
from flask import Module, abort, jsonify, request,  \
    g, url_for, redirect, flash

from flaskext.mail import Message
from flaskext.babel import gettext as _

from newsmeme import signals
from newsmeme.models import Post, Comment
from newsmeme.forms import CommentForm, PostForm
from newsmeme.helpers import render_template
from newsmeme.decorators import keep_login_url
from newsmeme.extensions import db, mail, cache
from newsmeme.permissions import auth

post = Module(__name__)

@post.route("/<int:post_id>/")
@post.route("/<int:post_id>/s/<slug>/")
@cache.cached(unless=lambda: g.user is not None)
@keep_login_url
def view(post_id, slug=None):
    post = Post.query.get_or_404(post_id)
    if not post.permissions.view:
        if not g.user:
            flash(_("You must be logged in to see this post"), "error")
            return redirect(url_for("account.login", next=request.path))
        else:
            flash(_("You must be a friend to see this post"), "error")
            abort(403)

    def edit_comment_form(comment):
        return CommentForm(obj=comment)

    return render_template("post/post.html", 
                           comment_form=CommentForm(),
                           edit_comment_form=edit_comment_form,
                           post=post)


@post.route("/<int:post_id>/upvote/", methods=("POST",))
@auth.require(401)
def upvote(post_id):
    return _vote(post_id, 1)


@post.route("/<int:post_id>/downvote/", methods=("POST",))
@auth.require(401)
def downvote(post_id):
    return _vote(post_id, -1)


@post.route("/<int:post_id>/addcomment/", methods=("GET", "POST"))
@post.route("/<int:post_id>/<int:parent_id>/reply/", methods=("GET", "POST"))
@auth.require(401)
def add_comment(post_id, parent_id=None):
    post = Post.query.get_or_404(post_id)
    post.permissions.view.test(403)

    parent = Comment.query.get_or_404(parent_id) if parent_id else None
    
    form = CommentForm()

    if form.validate_on_submit():
        comment = Comment(post=post,
                          parent=parent,
                          author=g.user)
        
        form.populate_obj(comment)

        db.session.add(comment)
        db.session.commit()

        signals.comment_added.send(post)

        flash(_("Thanks for your comment"), "success")

        author = parent.author if parent else post.author

        if author.email_alerts and author.id != g.user.id:
            
            subject = _("Somebody replied to your comment") if parent else \
                      _("Somebody commented on your post")

            template = "emails/comment_replied.html" if parent else \
                       "emails/post_commented.html"

            body = render_template(template,
                                   author=author,
                                   post=post,
                                   parent=parent,
                                   comment=comment)

            mail.send_message(subject=subject,
                              body=body,
                              recipients=[post.author.email])


        return redirect(comment.url)
    
    return render_template("post/add_comment.html",
                           parent=parent,
                           post=post,
                           form=form)


@post.route("/<int:post_id>/edit/", methods=("GET", "POST"))
@auth.require(401)
def edit(post_id):

    post = Post.query.get_or_404(post_id)
    post.permissions.edit.test(403)
    
    form = PostForm(obj=post)
    if form.validate_on_submit():

        form.populate_obj(post)
        db.session.commit()

        if g.user.id != post.author_id:
            body = render_template("emails/post_edited.html",
                                   post=post)

            message = Message(subject="Your post has been edited",
                              body=body,
                              recipients=[post.author.email])

            mail.send(message)

            flash(_("The post has been updated"), "success")
        
        else:
            flash(_("Your post has been updated"), "success")
        return redirect(url_for("post.view", post_id=post_id))

    return render_template("post/edit_post.html", 
                           post=post, 
                           form=form)


@post.route("/<int:post_id>/delete/", methods=("POST",))
@auth.require(401)
def delete(post_id):

    post = Post.query.get_or_404(post_id)
    post.permissions.delete.test(403)
    
    Comment.query.filter_by(post=post).delete()

    db.session.delete(post)
    db.session.commit()

    if g.user.id != post.author_id:
        body = render_template("emails/post_deleted.html",
                               post=post)

        message = Message(subject="Your post has been deleted",
                          body=body,
                          recipients=[post.author.email])

        mail.send(message)

        flash(_("The post has been deleted"), "success")
    
    else:
        flash(_("Your post has been deleted"), "success")

    return jsonify(success=True,
                   redirect_url=url_for('frontend.index'))

def _vote(post_id, score):

    post = Post.query.get_or_404(post_id)
    post.permissions.vote.test(403)
    
    post.score += score
    post.author.karma += score

    if post.author.karma < 0:
        post.author.karma = 0

    post.vote(g.user)

    db.session.commit()

    return jsonify(success=True,
                   post_id=post_id,
                   score=post.score)


########NEW FILE########
__FILENAME__ = user
from flask import Module, url_for, g, redirect, flash

from flaskext.mail import Message
from flaskext.babel import gettext as _

from newsmeme.helpers import render_template, cached
from newsmeme.models import Post, User, Comment
from newsmeme.decorators import keep_login_url
from newsmeme.forms import MessageForm
from newsmeme.extensions import mail
from newsmeme.permissions import auth

user = Module(__name__)

@user.route("/message/<int:user_id>/", methods=("GET", "POST"))
@auth.require(401)
def send_message(user_id):

    user = User.query.get_or_404(user_id)
    user.permissions.send_message.test(403)

    form = MessageForm()

    if form.validate_on_submit():

        body = render_template("emails/send_message.html",
                               user=user,
                               subject=form.subject.data,
                               message=form.message.data)

        subject = _("You have received a message from %(name)s", 
                    name=g.user.username)

        message = Message(subject=subject,
                          body=body,
                          recipients=[user.email])

        mail.send(message)

        flash(_("Your message has been sent to %(name)s", 
               name=user.username), "success")

        return redirect(url_for("user.posts", username=user.username))

    return render_template("user/send_message.html", user=user, form=form)


@user.route("/<username>/")
@user.route("/<username>/<int:page>/")
@cached()
@keep_login_url
def posts(username, page=1):

    user = User.query.filter_by(username=username).first_or_404()

    page_obj = Post.query.filter_by(author=user).restricted(g.user).\
        as_list().paginate(page, Post.PER_PAGE)
    
    page_url = lambda page: url_for('user.posts',
                                    username=username,
                                    page=page)

    num_comments = Comment.query.filter_by(author_id=user.id).\
        restricted(g.user).count()

    return render_template("user/posts.html",
                           user=user,
                           num_posts=page_obj.total,
                           num_comments=num_comments,
                           page_obj=page_obj,
                           page_url=page_url)


@user.route("/<username>/comments/")
@user.route("/<username>/comments/<int:page>/")
@cached()
@keep_login_url
def comments(username, page=1):

    user = User.query.filter_by(username=username).first_or_404()

    page_obj = Comment.query.filter_by(author=user).\
        order_by(Comment.id.desc()).restricted(g.user).\
        paginate(page, Comment.PER_PAGE)
    
    page_url = lambda page: url_for('user.comments',
                                    username=username,
                                    page=page)

    num_posts = Post.query.filter_by(author_id=user.id).\
        restricted(g.user).count()

    return render_template("user/comments.html",
                           user=user,
                           num_posts=num_posts,
                           num_comments=page_obj.total,
                           page_obj=page_obj,
                           page_url=page_url)



@user.route("/<username>/followers/")
@user.route("/<username>/followers/<int:page>/")
@cached()
@keep_login_url
def followers(username, page=1):

    user = User.query.filter_by(username=username).first_or_404()

    num_posts = Post.query.filter_by(author_id=user.id).\
        restricted(g.user).count()

    num_comments = Comment.query.filter_by(author_id=user.id).\
        restricted(g.user).count()

    followers = user.get_followers().order_by(User.username.asc())

    return render_template("user/followers.html",
                           user=user,
                           num_posts=num_posts,
                           num_comments=num_comments,
                           followers=followers)


@user.route("/<username>/following/")
@user.route("/<username>/following/<int:page>/")
@cached()
@keep_login_url
def following(username, page=1):

    user = User.query.filter_by(username=username).first_or_404()

    num_posts = Post.query.filter_by(author_id=user.id).\
        restricted(g.user).count()

    num_comments = Comment.query.filter_by(author_id=user.id).\
        restricted(g.user).count()
   
    following = user.get_following().order_by(User.username.asc())

    return render_template("user/following.html",
                           user=user,
                           num_posts=num_posts,
                           num_comments=num_comments,
                           following=following)



########NEW FILE########
__FILENAME__ = test_helpers
# -*- coding: utf-8 -*-
"""
    test_helpers.py
    ~~~~~~~~

    NewsMeme tests

    :copyright: (c) 2010 by Dan Jacob.
    :license: BSD, see LICENSE for more details.
"""

from datetime import datetime, timedelta

from newsmeme.helpers import timesince, domain, slugify

from tests import TestCase


class TestSlugify(TestCase):

    def test_slugify(self):

        assert slugify("hello, this is a test") == "hello-this-is-a-test"

class TestDomain(TestCase):

    def test_valid_domain(self):
        
        assert domain("http://reddit.com") == "reddit.com"

    def test_invalid_domain(self):

        assert domain("jkjkjkjkj") == ""
        

class TestTimeSince(TestCase):

    def test_years_ago(self):

        now = datetime.utcnow()
        three_years_ago = now - timedelta(days=365 * 3)
        assert timesince(three_years_ago) == "3 years ago"

    def test_year_ago(self):

        now = datetime.utcnow()
        three_years_ago = now - timedelta(days=365)
        assert timesince(three_years_ago) == "1 year ago"

    def test_months_ago(self):

        now = datetime.utcnow()
        six_months_ago = now - timedelta(days=30 * 6)
        assert timesince(six_months_ago) == "6 months ago"

    def test_minutes_ago(self):

        now = datetime.utcnow()
        five_minutes_ago = now - timedelta(seconds=(60 * 5) + 40)
        assert timesince(five_minutes_ago) == "5 minutes ago"

########NEW FILE########
__FILENAME__ = test_models
# -*- coding: utf-8 -*-
"""
    test_models.py
    ~~~~~~~~

    newsmeme tests

    :copyright: (c) 2010 by Dan Jacob.
    :license: BSD, see LICENSE for more details.
"""

from flaskext.sqlalchemy import get_debug_queries
from flaskext.principal import Identity, AnonymousIdentity

from newsmeme import signals
from newsmeme.models import User, Post, Comment, Tag, post_tags
from newsmeme.extensions import db

from tests import TestCase

class TestTags(TestCase):

    def test_empty_tag_cloud(self):

        tags = Tag.query.cloud()

        assert tags == []

    def test_tag_cloud_with_posts(self):

        user = User(username="tester",
                    email="tester@example.com",
                    password="test")

        db.session.add(user)
        db.session.commit()
        
        for i in xrange(20):
            post = Post(author=user,
                        title="test",
                        tags = "Music, comedy, IT crowd")


            db.session.add(post)
            db.session.commit()

        for i in xrange(10):
            post = Post(author=user,
                        title="test",
                        tags = "Twitter, YouTube, funny")

            db.session.add(post)
            db.session.commit()

        post = Post(author=user,
                    title="test",
                    tags="Beer, parties, kegs")

        db.session.add(post)
        db.session.commit()

        assert Tag.query.count() == 9

        tags = Tag.query.cloud()

        for tag in tags:

            if tag.name in ("it crowd", "music", "comedy"):
                assert tag.size == 10

            elif tag.name in ("twitter", "youtube", "funny"):
                assert tag.size == 5

            elif tag.name in ("beer", "parties", "kegs"):
                assert tag.size == 1


class TestUser(TestCase):

    def test_gravatar(self):

        user = User()

        assert user.gravatar == ''

        user = User(email="tester@example.com")

        assert user.gravatar == "f40aca99b2ca1491dbf6ec55597c4397"

    def test_gravatar_url(self):

        user = User()

        assert user.gravatar_url(80) == ''

        user = User(email="tester@example.com")

        assert user.gravatar_url(80) == \
            "http://www.gravatar.com/avatar/f40aca99b2ca1491dbf6ec55597c4397.jpg?s=80"

    def test_following(self):

        user = User()

        assert user.following == set()

        user.following = set([1])

        assert user.following == set([1])
        

    def test_get_following(self):

        user = User(username="tester",
                    email="tester@example.com")

        db.session.add(user)
        
        assert user.get_following().count() == 0

        user2 = User(username="tester2",
                     email="tester2@example.com")

        db.session.add(user2)

        db.session.commit() 

        user.following = set([user2.id])

        assert user.get_following().count() == 1
        assert user.get_following().first().id == user2.id

        assert user.is_following(user2)

    def test_follow(self):

        user = User(username="tester",
                    email="tester@example.com")

        db.session.add(user)
        
        assert user.get_following().count() == 0

        user2 = User(username="tester2",
                     email="tester2@example.com")

        db.session.add(user2)

        assert user2.get_followers().count() == 0

        db.session.commit() 

        user.follow(user2)
        
        db.session.commit()

        assert user.get_following().count() == 1
        assert user.get_following().first().id == user2.id

        assert user2.get_followers().count() == 1
        assert user2.get_followers().first().id == user.id

    def test_unfollow(self):

        user = User(username="tester",
                    email="tester@example.com")

        db.session.add(user)
        
        assert user.get_following().count() == 0

        user2 = User(username="tester2",
                     email="tester2@example.com")

        db.session.add(user2)

        assert user2.get_followers().count() == 0

        db.session.commit() 

        user.follow(user2)
        
        db.session.commit()

        assert user.get_following().count() == 1
        assert user.get_following().first().id == user2.id

        assert user2.get_followers().count() == 1
        assert user2.get_followers().first().id == user.id

        user.unfollow(user2)

        db.session.commit()

        assert user.get_following().count() == 0
        assert user2.get_followers().count() == 0

    def test_can_receive_mail(self):
        
        user = User(username="tester",
                    email="tester@example.com")

        db.session.add(user)
        
        assert user.get_following().count() == 0

        user2 = User(username="tester2",
                     email="tester2@example.com")

        db.session.add(user2)

        db.session.commit()

        id1 = Identity(user.id)
        id2 = Identity(user2.id)

        id1.provides.update(user.provides)
        id2.provides.update(user2.provides)

        assert not user.permissions.send_message.allows(id2)
        assert not user2.permissions.send_message.allows(id1)

        user.follow(user2)

        db.session.commit()

        del user.permissions
        del user2.permissions

        assert not user.permissions.send_message.allows(id2)
        assert not user2.permissions.send_message.allows(id1)

        user2.follow(user)
        user.receive_email = True

        del user.permissions
        del user2.permissions

        assert user.permissions.send_message.allows(id2)
        assert not user2.permissions.send_message.allows(id1)

        user2.receive_email = True

        del user.permissions
        del user2.permissions

        assert user.permissions.send_message.allows(id2)
        assert user2.permissions.send_message.allows(id1)

        user.unfollow(user2)

        del user.permissions
        del user2.permissions

        assert not user.permissions.send_message.allows(id2)
        assert not user2.permissions.send_message.allows(id1)

    def test_is_friend(self):
        
        user = User(username="tester",
                    email="tester@example.com")

        db.session.add(user)
        
        assert user.get_following().count() == 0

        user2 = User(username="tester2",
                     email="tester2@example.com")

        db.session.add(user2)

        db.session.commit()

        assert not user.is_friend(user2)
        assert not user2.is_friend(user)

        user.follow(user2)

        db.session.commit()

        assert not user.is_friend(user2)
        assert not user2.is_friend(user)


    def test_is_friend(self):
        
        user = User(username="tester",
                    email="tester@example.com")

        db.session.add(user)
        
        assert user.get_following().count() == 0

        user2 = User(username="tester2",
                     email="tester2@example.com")

        db.session.add(user2)

        db.session.commit()

        assert not user.is_friend(user2)
        assert not user2.is_friend(user)

        user.follow(user2)

        db.session.commit()

        assert not user.is_friend(user2)
        assert not user2.is_friend(user)

        user2.follow(user)

        assert user.is_friend(user2)
        assert user2.is_friend(user)


    
    def test_get_friends(self):

        user = User(username="tester",
                    email="tester@example.com")

        db.session.add(user)
        
        assert user.get_friends().count() == 0

        user2 = User(username="tester2",
                     email="tester2@example.com")

        db.session.add(user2)

        assert user2.get_friends().count() == 0

        db.session.commit()

        assert not user.is_friend(user2)
        assert not user2.is_friend(user)

        assert user.get_friends().count() == 0
        assert user2.get_friends().count() == 0

        user.follow(user2)

        db.session.commit()

        assert not user.is_friend(user2)
        assert not user2.is_friend(user)

        assert user.get_friends().count() == 0
        assert user2.get_friends().count() == 0

        user2.follow(user)

        assert user.is_friend(user2)
        assert user2.is_friend(user) 

        assert user.get_friends().count() == 1
        assert user2.get_friends().count() == 1

        assert user.get_friends().first().id == user2.id
        assert user2.get_friends().first().id == user.id

    def test_followers(self):

        user = User()

        assert user.followers == set()

        user.followers = set([1])

        assert user.followers == set([1])

    def test_get_followers(self):

        user = User(username="tester",
                    email="tester@example.com")

        db.session.add(user)
        
        assert user.get_followers().count() == 0

        user2 = User(username="tester2",
                     email="tester2@example.com")

        db.session.add(user2)

        db.session.commit() 

        user.followers = set([user2.id])

        assert user.get_followers().count() == 1
        assert user.get_followers().first().id == user2.id

    def test_check_password_if_password_none(self):

        user = User()

        assert not user.check_password("test")

    def test_check_openid_if_password_none(self):

        user = User()

        assert not user.check_openid("test")

    def test_check_password(self):

        user = User(password="test")
        assert user.password != "test"

        assert not user.check_password("test!")
        assert user.check_password("test")

    def test_check_openid(self):

        user = User(openid="google")
        assert user.openid != "google"

        assert not user.check_openid("test")
        assert user.check_openid("google")

    def test_authenticate_no_user(self):

        user, is_auth = User.query.authenticate("tester@example.com", 
                                                "test")

        assert (user, is_auth) == (None, False)

    def test_authenticate_bad_password(self):

        user = User(username=u"tester",
                    email="tester@example.com",
                    password="test!")

        db.session.add(user)
        db.session.commit()

        auth_user, is_auth = \
            User.query.authenticate("tester@example.com", 
                                    "test")

        assert auth_user.id == user.id
        assert not is_auth

    def test_authenticate_good_username(self):

        user = User(username=u"tester",
                    email="tester@example.com",
                    password="test!")

        db.session.add(user)
        db.session.commit()

        auth_user, is_auth = \
            User.query.authenticate("tester", 
                                    "test!")

        assert auth_user.id == user.id
        assert is_auth

    def test_authenticate_good_email(self):

        user = User(username=u"tester",
                    email="tester@example.com",
                    password="test!")
        
        db.session.add(user)
        db.session.commit()

        auth_user, is_auth = \
            User.query.authenticate("tester@example.com", 
                                    "test!")

        assert auth_user.id == user.id
        assert is_auth


class TestPost(TestCase):

    def setUp(self):
        super(TestPost, self).setUp()

        self.user = User(username="tester",
                         email="tester@example.com",
                         password="testing")
        
        db.session.add(self.user)

        self.post = Post(title="testing",
                         link="http://reddit.com",
                         author=self.user)

        db.session.add(self.post)

        db.session.commit()

    def test_url(self):

        assert self.post.url == "/post/1/s/testing/"

    def test_permanlink(self):

        assert self.post.permalink == "http://localhost/post/1/s/testing/"

    def test_popular(self):

        assert Post.query.popular().count() == 1
        self.post.score = 0
        db.session.commit()
        assert Post.query.popular().count() == 0

    def test_deadpooled(self):

        assert Post.query.deadpooled().count() == 0
        self.post.score = 0
        db.session.commit()
        assert Post.query.deadpooled().count() == 1

    def test_jsonify(self):

        d = self.post.json
        assert d['title'] == self.post.title

        json = list(Post.query.jsonify())

        assert json[0]['title'] == self.post.title

    def test_tags(self):

        assert self.post.taglist == []

        self.post.tags = "Music, comedy, IT crowd"

        db.session.commit()

        assert self.post.taglist == ["Music", "comedy", "IT crowd"]
        
        assert self.post.linked_taglist == [
            ("Music", "/tags/music/"),
            ("comedy", "/tags/comedy/"),
            ("IT crowd", "/tags/it-crowd/"),
        ]


        assert Tag.query.count() == 3

        for tag in Tag.query.all():

            assert tag.num_posts == 1
            assert tag.posts[0].id == self.post.id

        post = Post(title="testing again",
                    link="http://reddit.com/r/programming",
                    author=self.user,
                    tags="comedy, it Crowd, Ubuntu")

        db.session.add(post)
        db.session.commit()

        assert post.taglist == ["comedy", "it Crowd", "Ubuntu"]
        assert Tag.query.count() == 4

        for tag in Tag.query.all():

            if tag.name.lower() in ("comedy", "it crowd"):
                assert tag.num_posts == 2
                assert tag.posts.count() == 2

            else:
                assert tag.num_posts == 1
                assert tag.posts.count() == 1

    def test_restricted(self):

        db.session.delete(self.post)

        user = User(username="testing", email="test@example.com")

        db.session.add(user)

        user2 = User(username="tester2", email="test2@example.com")

        db.session.add(user2)
    
        db.session.commit()
        
        admin = User(username="admin", 
                     email="admin@example.com", 
                     role=User.MODERATOR)

        
        assert user.id

        post = Post(title="test",
                    author=user,
                    access=Post.PRIVATE)

        db.session.add(post)
        db.session.commit()

        posts = Post.query.restricted(user)

        assert Post.query.restricted(user).count() == 1
        assert Post.query.restricted(admin).count() == 1
        assert Post.query.restricted(None).count() == 0
        assert Post.query.restricted(user2).count() == 0

        post.access = Post.PUBLIC
        db.session.commit()
    
        posts = Post.query.restricted(user)

        assert Post.query.restricted(user).count() == 1
        assert Post.query.restricted(admin).count() == 1
        assert Post.query.restricted(None).count() == 1
        assert Post.query.restricted(user2).count() == 1
        
        post.access = Post.FRIENDS

        db.session.commit()
        
        assert Post.query.restricted(user).count() == 1
        assert Post.query.restricted(admin).count() == 1
        assert Post.query.restricted(None).count() == 0
        assert Post.query.restricted(user2).count() == 0
    
        user2.follow(user)
        user.follow(user2)

        db.session.commit()

        assert Post.query.restricted(user2).count() == 1

    def test_can_access(self):

        user = User(username="testing", email="test@example.com")

        db.session.add(user)

        user2 = User(username="tester2", email="test2@example.com")

        db.session.add(user2)
    
        db.session.commit()
        
        admin = User(username="admin", 
                     email="admin@example.com", 
                     role=User.MODERATOR)

        
        post = Post(title="test",
                    author_id=user.id,
                    access=Post.PRIVATE)


        assert post.can_access(user)
        assert post.can_access(admin)

        assert not post.can_access(user2)
        assert not post.can_access(None)

        post.access = Post.PUBLIC

        assert post.can_access(user)
        assert post.can_access(admin)

        assert post.can_access(user2)
        assert post.can_access(None)

        post.access = Post.FRIENDS

        assert post.can_access(user)
        assert post.can_access(admin)

        assert not post.can_access(user2)
        assert not post.can_access(None)

        user.follow(user2)
        user2.follow(user)

        assert post.can_access(user2)

    def test_edit_tags(self):

        self.post.tags = "Music, comedy, IT crowd"

        db.session.commit()

        assert self.post.taglist == ["Music", "comedy", "IT crowd"]
        
        assert self.post.linked_taglist == [
            ("Music", "/tags/music/"),
            ("comedy", "/tags/comedy/"),
            ("IT crowd", "/tags/it-crowd/"),
        ]

        def _count_post_tags():
            s = db.select([db.func.count(post_tags)])
            return db.engine.execute(s).scalar()

        assert _count_post_tags() == 3

        self.post.tags = "music, iPhone, books"
        db.session.commit()

        for t in Tag.query.all():
            if t.name in ("music", "iphone", "books"):
                assert t.num_posts == 1
            
            if t.name in ("comedy", "it crowd"):
                assert t.num_posts == 0

        assert _count_post_tags() == 3
        
        self.post.tags = ""

        assert _count_post_tags() == 0

    def test_update_num_comments(self):

        comment = Comment(post=self.post,
                          author=self.user,
                          comment="test")

        db.session.add(comment)
        db.session.commit()

        signals.comment_added.send(self.post)

        post = Post.query.get(self.post.id)

        assert post.num_comments == 1

        db.session.delete(comment)
        db.session.commit()

        signals.comment_deleted.send(post)

        post = Post.query.get(post.id)

        assert post.num_comments == 0

    def test_votes(self):

        assert self.post.votes == set([])
        user = User(username="tester2",
                    email="tester2@example.com")

        db.session.add(user)
        db.session.commit()
        
        self.post.vote(user)

        assert user.id in self.post.votes

        post = Post.query.get(self.post.id)
        assert user.id in post.votes

    def test_can_vote(self):

        assert not self.post.permissions.vote.allows(AnonymousIdentity())

        identity = Identity(self.user.id)
        identity.provides.update(self.user.provides)
        assert not self.post.permissions.vote.allows(identity)

        user = User(username="tester2",
                    email="tester2@gmail.com")

        db.session.add(user)
        db.session.commit()

        identity = Identity(user.id)
        identity.provides.update(user.provides)

        assert self.post.permissions.vote.allows(identity)

        votes = self.post.votes
        votes.add(user.id)
        self.post.votes = votes

        del self.post.permissions

        assert not self.post.permissions.vote.allows(identity)

    def test_can_edit(self):

        assert not self.post.permissions.edit.allows(AnonymousIdentity())

        identity = Identity(self.user.id)
        identity.provides.update(self.user.provides)
        assert self.post.permissions.edit.allows(identity)

        user = User(username="tester2",
                    email="tester2@gmail.com")

        db.session.add(user)
        db.session.commit()

        identity = Identity(user.id)
        assert not self.post.permissions.edit.allows(identity)

        user.role = User.MODERATOR

        identity.provides.update(user.provides)
        assert self.post.permissions.edit.allows(identity)

        user.role = User.ADMIN
        del user.provides

        identity.provides.update(user.provides)
        assert self.post.permissions.edit.allows(identity)

    def test_can_delete(self):

        assert not self.post.permissions.delete.allows(AnonymousIdentity())

        identity = Identity(self.user.id)
        identity.provides.update(self.user.provides)
        assert self.post.permissions.delete.allows(identity)

        user = User(username="tester2",
                    email="tester2@gmail.com")

        db.session.add(user)
        db.session.commit()

        identity = Identity(user.id)
        assert not self.post.permissions.delete.allows(identity)

        user.role = User.MODERATOR

        identity.provides.update(user.provides)
        assert self.post.permissions.delete.allows(identity)

        user.role = User.ADMIN
        del user.provides

        identity.provides.update(user.provides)
        assert self.post.permissions.delete.allows(identity)

    def test_search(self):

        posts = Post.query.search("testing")
        assert posts.count() == 1

        posts = Post.query.search("reddit")
        assert posts.count() == 1

        posts = Post.query.search("digg")
        assert posts.count() == 0

        posts = Post.query.search("testing reddit")
        assert posts.count() == 1

        posts = Post.query.search("testing digg")
        assert posts.count() == 0
    
        posts = Post.query.search("tester")
        assert posts.count() == 1

    def test_get_comments(self):

        parent = Comment(comment="parent comment",
                         author=self.user,
                         post=self.post)


        child1 = Comment(parent=parent,
                         post=self.post,
                         author=self.user,
                         comment="child1")

        child2 = Comment(parent=parent,
                         post=self.post,
                         author=self.user,
                         comment="child2")

        child3 = Comment(parent=child1,
                         post=self.post, 
                         author=self.user,
                         comment="child3")

        db.session.add_all([parent, child1, child2, child3])
        db.session.commit()

        num_queries = len(get_debug_queries())

        comments = self.post.comments

        assert len(get_debug_queries()) == num_queries + 1

        assert comments[0].id == parent.id
        assert comments[0].depth == 0
        
        comments = comments[0].comments

        assert comments[0].id == child1.id
        assert comments[1].id == child2.id

        assert comments[0].depth == 1

        comments = comments[0].comments

        assert comments[0].id == child3.id

        assert comments[0].depth == 2

class TestComment(TestCase):

    def setUp(self):
        super(TestComment, self).setUp()

        self.user = User(username="tester",
                         email="tester@example.com",
                         password="testing")
        
        db.session.add(self.user)

        self.post = Post(title="testing",
                         link="http://reddit.com",
                         author=self.user)

        db.session.add(self.post)

        self.comment = Comment(post=self.post,
                               author=self.user,
                               comment="a comment")

        db.session.add(self.comment)

        db.session.commit()

    def test_restricted(self):

        db.session.delete(self.post)
        db.session.delete(self.comment)

        user = User(username="testing", email="test@example.com")

        db.session.add(user)

        user2 = User(username="tester2", email="test2@example.com")

        db.session.add(user2)
    
        db.session.commit()
        
        admin = User(username="admin", 
                     email="admin@example.com", 
                     role=User.MODERATOR)

        

        post = Post(title="test",
                    author=user,
                    access=Post.PRIVATE)

        db.session.add(post)
        db.session.commit()


        comment = Comment(author=user,
                          post=post,
                          comment="test")


        db.session.add(comment)
        db.session.commit()

        assert Comment.query.restricted(user).count() == 1
        assert Comment.query.restricted(admin).count() == 1
        assert Comment.query.restricted(None).count() == 0
        assert Comment.query.restricted(user2).count() == 0

        post.access = Post.PUBLIC
        db.session.commit()
    
        posts = Post.query.restricted(user)

        assert Comment.query.restricted(user).count() == 1
        assert Comment.query.restricted(admin).count() == 1
        assert Comment.query.restricted(None).count() == 1
        assert Comment.query.restricted(user2).count() == 1
        
        post.access = Post.FRIENDS

        db.session.commit()
        
        assert Comment.query.restricted(user).count() == 1
        assert Comment.query.restricted(admin).count() == 1
        assert Comment.query.restricted(None).count() == 0
        assert Comment.query.restricted(user2).count() == 0
    
        user2.follow(user)
        user.follow(user2)

        db.session.commit()

        assert Comment.query.restricted(user2).count() == 1


    def test_can_edit(self):

        assert not self.comment.permissions.edit.allows(AnonymousIdentity())

        identity = Identity(self.user.id)
        identity.provides.update(self.user.provides)
        assert self.comment.permissions.edit.allows(identity)

        user = User(username="tester2",
                    email="tester2@gmail.com")

        db.session.add(user)
        db.session.commit()

        identity = Identity(user.id)
        assert not self.comment.permissions.edit.allows(identity)

        user.role = User.MODERATOR

        identity.provides.update(user.provides)
        assert self.comment.permissions.edit.allows(identity)

        user.role = User.ADMIN
        del user.provides

        identity.provides.update(user.provides)
        assert self.comment.permissions.edit.allows(identity)


    def test_can_delete(self):

        assert not self.comment.permissions.delete.allows(AnonymousIdentity())

        identity = Identity(self.user.id)
        identity.provides.update(self.user.provides)
        assert self.comment.permissions.delete.allows(identity)

        user = User(username="tester2",
                    email="tester2@gmail.com")

        db.session.add(user)
        db.session.commit()

        identity = Identity(user.id)
        assert not self.comment.permissions.delete.allows(identity)

        user.role = User.MODERATOR

        identity.provides.update(user.provides)
        assert self.comment.permissions.delete.allows(identity)

        user.role = User.ADMIN
        del user.provides

        identity.provides.update(user.provides)
        assert self.comment.permissions.delete.allows(identity)

    def test_votes(self):

        comment = Comment()
        user = User(username="test", 
                    email="test@example.com")

        db.session.add(user)
        db.session.commit()

        assert comment.votes == set([])

        comment.vote(user)

        assert user.id in comment.votes

    def test_can_vote(self):
        assert not self.comment.permissions.vote.allows(AnonymousIdentity())

        identity = Identity(self.user.id)
        identity.provides.update(self.user.provides)
        assert not self.comment.permissions.vote.allows(identity)

        user = User(username="tester2",
                    email="tester2@gmail.com")

        db.session.add(user)
        db.session.commit()

        identity = Identity(user.id)
        identity.provides.update(user.provides)

        assert self.comment.permissions.vote.allows(identity)

        votes = self.comment.votes
        votes.add(user.id)
        self.comment.votes = votes

        del self.comment.permissions

        assert not self.comment.permissions.vote.allows(identity)


    def test_url(self):

        assert self.comment.url == "/post/1/s/testing/#comment-1"

    def test_permanlink(self):

        assert self.comment.permalink == \
                "http://localhost/post/1/s/testing/#comment-1"


########NEW FILE########
__FILENAME__ = test_views
# -*- coding: utf-8 -*-
"""
    test_views.py
    ~~~~~~~~

    NewsMeme tests

    :copyright: (c) 2010 by Dan Jacob.
    :license: BSD, see LICENSE for more details.
"""

from newsmeme.signals import comment_added
from newsmeme.models import User, Post, Comment
from newsmeme.extensions import db, mail

from tests import TestCase

class TestApi(TestCase):

    def create_user(self):
        user = User(username="tester",
                    email="tester@example.com",
                    password="test")

        db.session.add(user)
        db.session.commit()

        return user

    def create_post(self):
        
        post = Post(author=self.create_user(),
                    title="test")

        db.session.add(post)
        db.session.commit()

        return post

    def test_get_post(self):

        post = self.create_post()

        response = self.client.get("/api/post/%d/" % post.id)
        self.assert_200(response)

        assert response.json['post_id'] == post.id
        assert response.json['title'] == "test"
        assert response.json['author'] == "tester"

    def test_search(self):

        self.create_post()

        response = self.client.get("/api/search/?keywords=test") 

        self.assert_200(response)

        assert len(response.json['results']) == 1

    def test_user(self):

        self.create_post()

        response = self.client.get("/api/user/tester/")
        self.assert_200(response)

        assert len(response.json['posts']) == 1


class TestComment(TestCase):

    def create_comment(self):

        user = User(username="tester",
                    email="tester@example.com",
                    password="test")

        post = Post(author=user,
                    title="test")

        comment = Comment(post=post,
                          author=user,
                          comment="test")

        db.session.add_all([user, post, comment])
        db.session.commit()

        comment_added.send(post)
        return comment

    def test_edit_comment_not_logged_in(self):

        comment = self.create_comment()
        response = self.client.get("/comment/%d/edit/" % comment.id)
        self.assert_401(response)

    def test_edit_comment_not_logged_in_as_author(self):

        comment = self.create_comment()
        user = User(username="tester2",
                    email="tester2@example.com",
                    password="test")

        db.session.add(user)
        db.session.commit()

        self.login(login="tester2", password="test")

        response = self.client.get("/comment/%d/edit/" % comment.id)
        self.assert_403(response)

    def test_edit_comment_logged_in_as_author(self):

        comment = self.create_comment()
        self.login(login="tester", password="test")

        response = self.client.get("/comment/%d/edit/" % comment.id)
        self.assert_200(response)

    def test_update_comment_logged_in_as_author(self):

        comment = self.create_comment()

        self.login(login="tester", password="test")

        response = self.client.post("/comment/%d/edit/" % comment.id,
                                    data={"comment":"test2"})
        
        self.assert_redirects(response, comment.url)
        
        comment = Comment.query.get(comment.id)

        assert comment.comment == "test2"

    def test_delete_comment_not_logged_in(self):

        comment = self.create_comment()
        response = self.client.get("/comment/%d/delete/" % comment.id)
        self.assert_405(response)
       
    def test_delete_comment_not_logged_in_as_author(self):

        comment = self.create_comment()
        response = self.client.post("/comment/%d/delete/" % comment.id)
  
        self.assert_401(response)

        user = User(username="tester2",
                    email="tester2@example.com",
                    password="test")

        db.session.add(user)
        db.session.commit()

        self.login(login="tester2", password="test")

        response = self.client.post("/comment/%d/delete/" % comment.id)
        self.assert_403(response)

    def test_delete_comment_logged_in_as_author(self):

        comment = self.create_comment()
        self.login(login="tester", password="test")

        response = self.client.post("/comment/%d/delete/" % comment.id)
        
        assert Comment.query.count() == 0

        post = Post.query.get(comment.post.id)
        assert post.num_comments == 0

        assert response.json['success']
        assert response.json['comment_id'] == comment.id

    
class TestFrontend(TestCase):

    def test_tags(self):

        user = User(username="tester",
                    email="tester@example.com",
                    password="test")

        db.session.add(user)
        db.session.commit()

        for i in xrange(20):

            post = Post(author=user,
                        tags="IT Crowd, funny, TV",
                        title="test")

            db.session.add(post)
            db.session.commit()
        
        response = self.client.get("/tags/")
        self.assert_200(response)

    def test_rules(self):
        response = self.client.get("/rules/")
        self.assert_200(response)
 
    def test_index(self):
        
        response = self.client.get("/")
        self.assert_200(response)
        
        user = User(username="tester",
                    password="test",
                    email="tester@example.com")

        db.session.add(user)
        
        for i in xrange(100):
            post =  Post(author=user,
                         link="http://reddit.com",
                         title="test post")

            db.session.add(post)

        db.session.commit()

        response = self.client.get("/")
        self.assert_200(response)

    def test_latest(self):

        
        user = User(username="tester",
                    password="test",
                    email="tester@example.com")

        db.session.add(user)
        
        for i in xrange(100):
            post =  Post(author=user,
                         link="http://reddit.com",
                         title="test post")

            db.session.add(post)

        db.session.commit()

    def test_submit_not_logged_in(self):

        response = self.client.get("/submit/")
        self.assert_401(response)

    def test_post_submit_not_logged_in(self):

        data = {
                "title" : "testing",
                "description" : "a test"
                }

        response = self.client.post("/submit/", data=data)
        self.assert_401(response)

    def test_submit_logged_in(self):

        user = User(username="tester",
                    password="test",
                    email="tester@example.com")

        db.session.add(user)
        db.session.commit()

        self.login(login="tester", password="test")
        response = self.client.get("/submit/")
        self.assert_200(response)

    def test_post_submit_logged_in(self):
        
        user = User(username="tester",
                    password="test",
                    email="tester@example.com")

        db.session.add(user)
        db.session.commit()

        self.login(login="tester", password="test")
    
        data = {
                "title" : "testing",
                "description" : "a test"
                }

        response = self.client.post("/submit/", data=data)
        self.assert_redirects(response, "/latest/")

        assert Post.query.count() == 1
        
class TestPost(TestCase):

    def create_user(self, login=False):

        user = User(username="tester",
                    password="test",
                    email="tester@example.com")

        db.session.add(user)
        db.session.commit()

        if login:
            self.login(login="tester", password="test")
        return user

    def test_delete_post_via_get(self):

        response = self.client.get("/post/1/delete/")
        self.assert_405(response)

    def test_delete_non_existing_post_not_logged_in(self):

        response = self.client.post("/post/1/delete/")
        self.assert_401(response)

    def test_delete_non_existing_post_logged_in(self):

        user = self.create_user(True)
        response = self.client.post("/post/1/delete/")
        self.assert_404(response)

    def test_delete_existing_post_not_logged_in(self):

        user = self.create_user(False)
        
        post = Post(author=user,
                    title="test",
                    description="test")

        db.session.add(post)
        db.session.commit()

        response = self.client.post("/post/%d/delete/" % post.id)
        self.assert_401(response)
        
    def test_delete_existing_post_logged_in_as_author(self):

        user = self.create_user(True)
        
        post = Post(author=user,
                    title="test",
                    description="test")

        db.session.add(post)
        db.session.commit()

        response = self.client.post("/post/%d/delete/" % post.id)

        self.assert_200(response)

        assert response.json['success']
        assert Post.query.count() == 0

    def test_delete_post_not_logged_in_as_author(self):

        user = self.create_user(False)
        
        post = Post(author=user,
                    title="test",
                    description="test")

        db.session.add(post)
        db.session.commit()

        user = User(username="tester2",
                    password="test",
                    email="tester2@example.com")

        db.session.add(user)
        db.session.commit()

        self.login(login="tester2", password="test")
 
        response = self.client.post("/post/%d/delete/" % post.id)

        self.assert_403(response)

    def test_delete_post_logged_in_as_admin(self):
    
        user = self.create_user(False)
        
        admin_user = User(username="admin",
                          email="admin@newsmeme.com",
                          password="admin1",
                          role=User.ADMIN)

        db.session.add(admin_user)
        db.session.commit()

        self.login(login="admin", password="admin1")

        post = Post(author=user,
                    title="test",
                    description="test")

        db.session.add(post)
        db.session.commit()

        with mail.record_messages() as outbox:
            response = self.client.post("/post/%d/delete/" % post.id)
        
            assert response.json['success']
            assert Post.query.count() == 0
            assert len(outbox) == 1

    def test_edit_non_existing_post_not_logged_in(self):

        response = self.client.get("/post/1/edit/")
        self.assert_401(response)
        
    def test_edit_non_existing_post_logged_in(self):

        user = self.create_user(True)
        response = self.client.get("/post/1/edit/")
        
        self.assert_404(response)

    def test_edit_existing_post_not_logged_in(self):

        post = Post(author=self.create_user(False),
                    title="test",
                    description="test")

        db.session.add(post)
        db.session.commit()

        response = self.client.get("/post/%d/edit/" % post.id)
        self.assert_401(response)

    def test_edit_existing_post_not_logged_in_as_author(self):

        post = Post(author=self.create_user(False),
                    title="test",
                    description="test")

        db.session.add(post)
        db.session.commit()

        user = User(username="tester2",
                    password="test",
                    email="tester2@example.com")

        db.session.add(user)
        db.session.commit()

        self.login(login="tester2", password="test")
 
        response = self.client.get("/post/%d/edit/" % post.id)
        self.assert_403(response)

    def test_edit_existing_post_logged_in_as_author(self):

        post = Post(author=self.create_user(True),
                    title="test",
                    description="test")

        db.session.add(post)
        db.session.commit()

        response = self.client.get("/post/%d/edit/" % post.id)
        self.assert_200(response)

    def test_update_existing_post_logged_in_as_author(self):

        post = Post(author=self.create_user(True),
                    title="test",
                    description="test")

        db.session.add(post)
        db.session.commit()


        data = {
                "title" : "testing 123",
                "description" : "a test 123"
                }


        response = self.client.post("/post/%d/edit/" % post.id, data=data)
        self.assert_redirects(response, "/post/%d/" % post.id)
        
        post = Post.query.first()

        assert post.title == "testing 123"
        assert post.description == "a test 123"

    def test_update_existing_post_logged_in_as_admin(self):

        post = Post(author=self.create_user(False),
                    title="test",
                    description="test")

        db.session.add(post)
        db.session.commit()

        admin_user = User(username="admin",
                          email="admin@newsmeme.com",
                          password="admin1",
                          role=User.ADMIN)

        db.session.add(admin_user)
        db.session.commit()

        self.login(login="admin", password="admin1")
 
 
        data = {
                "title" : "testing 123",
                "description" : "a test 123"
                }


        with mail.record_messages() as outbox:
            response = self.client.post("/post/%d/edit/" % post.id, data=data)
        
            self.assert_redirects(response, "/post/%d/" % post.id)
            assert len(outbox) == 1

        post = Post.query.first()

        assert post.title == "testing 123"
        assert post.description == "a test 123"
 
    def test_view_post(self):

        response = self.client.get("/post/1/")
        self.assert_404(response)

        user = User(username="tester",
                    password="test",
                    email="tester@example.com")

        db.session.add(user)
        db.session.commit()

        post = Post(author=user,
                    title="test",
                    description="test")

        db.session.add(post)
        db.session.commit()

        response = self.client.get("/post/%d/" % post.id)
        self.assert_200(response)

        for i in xrange(100):
            user = User(username="tester-%d" % i,
                        email="tester=%d.gmail.com" % i,
                        password="test")

            comment = Comment(post=post,
                              author=user,
                              comment="a comment")
            db.session.add(user)
            db.session.add(comment)

        db.session.commit()

        response = self.client.get("/post/%d/" % post.id)
        self.assert_200(response)
    
    def test_add_comment(self):

        response = self.client.get("/post/1/addcomment/")
        self.assert_401(response)

        user = User(username="tester",
                    email="tester@example.com",
                    password="test")

        db.session.add(user)
        db.session.commit()

        self.login(login="tester", password="test")

        response = self.client.get("/post/1/addcomment/")
        self.assert_404(response)

        post = Post(author=user,
                    title="test",
                    link="http://reddit.com")

        db.session.add(post)
        db.session.commit()
        

        response = self.client.get("/post/%d/addcomment/" % post.id)
        self.assert_200(response)

        response = self.client.get("/post/%d/1/reply/" % post.id)

        with mail.record_messages() as outbox:
            response = self.client.post("/post/%d/addcomment/" % post.id,
                data={"comment" : "testing"})
        
            assert len(outbox) == 0

        comment = Comment.query.first()

        self.assert_redirects(response, comment.url)

        # reply to this comment

        response = self.client.get("/post/%d/%d/reply/" % (post.id, comment.id))

        self.assert_200(response)
        
        with mail.record_messages() as outbox:
            response = self.client.post("/post/%d/%d/reply/" % (
                post.id, comment.id), data={'comment':'hello'})

            assert len(outbox) == 0

        assert Comment.query.count() == 2

        reply = Comment.query.filter(
            Comment.parent_id==comment.id).first()

        assert reply.comment == "hello"

        self.assert_redirects(response, reply.url)


        # another user

        user2 = User(username="tester2",
                     email="tester2@example.com",
                     password="test")

        db.session.add(user2)
        db.session.commit()

        self.login(login="tester2", password="test")

        with mail.record_messages() as outbox:
            response = self.client.post("/post/%d/addcomment/" % post.id,
                data={"comment" : "testing"})
        
            assert len(outbox) == 0

        user.email_alerts = True
        db.session.add(user)
        db.session.commit()

        assert User.query.filter(User.email_alerts==True).count() == 1

        with mail.record_messages() as outbox:
            response = self.client.post("/post/%d/addcomment/" % post.id,
                data={"comment" : "testing"})
        
            assert len(outbox) == 1


        with mail.record_messages() as outbox:
            response = self.client.post(
                "/post/%d/%d/reply/" % (post.id, comment.id),
                data={"comment" : "testing"})
        
            assert len(outbox) == 1

        # double check author doesn't receive own emails

        self.login(login="tester", password="test")

        with mail.record_messages() as outbox:
            response = self.client.post("/post/%d/%d/reply/" % (
                post.id, comment.id), data={'comment':'hello'})

            assert len(outbox) == 0


class TestFeeds(TestCase):

    def setUp(self):
        super(TestFeeds, self).setUp()

        user = User(username="tester",
                    email="tester@example.com",
                    password="test")

        db.session.add(user)
        db.session.commit()

        for i in xrange(20):

            post = Post(author=user,
                        tags="programming",
                        title="TESTING",
                        description="test")


            db.session.add(post)
            db.session.commit()

    def test_posts(self):

        response = self.client.get("/feeds/")
        self.assert_200(response)

    def test_latest(self):

        response = self.client.get("/feeds/latest/")
        self.assert_200(response)

    def test_user(self):

        response = self.client.get("/feeds/user/danjac/")
        self.assert_404(response)

        response = self.client.get("/feeds/user/tester/")
        self.assert_200(response)

    def test_tag(self):

        response = self.client.get("/feeds/tag/foo/")
        self.assert_404(response)

        response = self.client.get("/feeds/tag/programming/")
        self.assert_200(response)

class TestAccount(TestCase):

    def test_delete_account(self):

        response = self.client.get("/acct/delete/")
        self.assert_401(response)

        user = User(username="tester",
                    password="test",
                    email="tester@example.com")

        db.session.add(user)
        db.session.commit()

        self.login(login="tester@example.com", password="test")

        response = self.client.get("/acct/delete/")
        self.assert_200(response)

        response = self.client.post("/acct/delete/", 
                                    data={'recaptcha_challenge_field':'test',
                                          'recaptcha_response_field':'test'})
        self.assert_redirects(response, "/")

        assert User.query.count() == 0


    def test_login(self):

        response = self.client.get("/acct/login/")
        self.assert_200(response)

        response = self.client.post("/acct/login/", 
            data={"login" : "tester", "password" : "test"})

        self.assert_200(response)
        assert "invalid login" in response.data

        user = User(username="tester",
                    password="test",
                    email="tester@example.com")

        db.session.add(user)
        db.session.commit()

        response = self.client.post("/acct/login/", 
            data={"login" : "tester", "password" : "test"})

        self.assert_redirects(response, "/user/tester/")

        response = self.client.post("/acct/login/", 
            data={"login" : "tester", "password" : "test",
                  "next" : "/submit/"})

        self.assert_redirects(response, "/submit/")

    def test_logout(self):

        response = self.client.get("/acct/logout/")
        self.assert_redirects(response, "/")


class TestUser(TestCase):

    def setUp(self):
        super(TestUser, self).setUp()

        self.user = User(username="tester", 
                         email="tester@example.com",
                         password="test")

        db.session.add(self.user)

        for i in xrange(10):

            post = Post(author=self.user,
                        title="test")

            db.session.add(post)

            comment = Comment(post=post,
                              author=self.user,
                              comment="test comment")

            db.session.add(comment)

        db.session.commit()

    def test_posts(self):

        response = self.client.get("/user/tester/")
        self.assert_200(response)

    def test_comments(self):

        response = self.client.get("/user/tester/comments/")
        self.assert_200(response)

class TestOpenId(TestCase):

    def test_login(self):

        response = self.client.get("/openid/login/")
        self.assert_200(response)

    def test_signup(self):

        response = self.client.get("/openid/signup/")
        self.assert_403(response)

########NEW FILE########
