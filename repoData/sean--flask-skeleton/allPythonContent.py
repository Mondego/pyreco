__FILENAME__ = default_settings
# Global configuration
BROWSER_SECRET_KEY = ''

# Flask-Cache settings
CACHE_TYPE = 'memcached'
CACHE_MEMCACHED_SERVERS = ['127.0.0.1:11211']

# When behind a load balancer, set CANONICAL_NAME to the value contained in
# Host headers (e.g. 'www.example.org')
CANONICAL_NAME = '127.0.0.1'

# When behind a load balancer, set CANONICAL_PORT to the value contained in
# Host headers (normally it will be '80' in production)
CANONICAL_PORT = '5000'

DATABASE_URI_FMT = 'postgresql+psycopg2://{username}:{password}@{hostname}:{port}/{dbname}'
DB_HOST = '127.0.0.1'
DB_NAME = 'skeleton'
# Setup a password database. Generate a random pass via:
# import M2Crypto
# M2Crypto.m2.rand_bytes(24).encode('base64').rstrip()
DB_PASS = ''
DB_PORT = '5432'
DB_SCHEMA = 'skeleton_schema'
DB_ADMIN = 'skeleton_dba'
DB_USER = 'skeleton_www'
DEBUG = False
DEBUG_TOOLBAR = False
LISTEN_HOST = '127.0.0.1'
PASSWORD_HASH = ''
SECRET_KEY = ''
SESSION_BYTES = 25
SESSION_COOKIE_NAME = 'skeleton_session'
SSL_CERT_FILENAME = ''
SSL_PRIVATE_KEY_FILENAME = ''
TESTING = False
USE_SSL = True

# Logs SQL queries to stderr
SQLALCHEMY_ECHO = False

# If users want to pass specific werkzeug options
WERKZEUG_OPTS = {'host': LISTEN_HOST, 'port' : 5000}

# Import user-provided values
try:
    from local_settings import *
except ImportError:
    pass


# Add a small amount of anti-footshooting and check to make sure a browser
# key is set.
if len(BROWSER_SECRET_KEY) < 16:
    # Generate a a good key
    import M2Crypto, os, re
    randpw = re.sub(os.linesep, '', M2Crypto.m2.rand_bytes(24).encode('base64').rstrip())
    print "Generating a random password for BROWSER_SECRET_KEY. Copy/paste the following commands to setup a random non-fail password."
    print '\n\techo "BROWSER_SECRET_KEY = \'%s\'" >> local_settings.py\n' % randpw
    raise ValueError('BROWSER_SECRET_KEY needs to be set and longer than 8 characters (len(BROWSER_SECRET_KEY) >= 16 recommended)!')


# Add a small amount of anti-footshooting and check to make sure a password
# is set. Idiots use passwords less than 16char. Just sayin'.
if len(DB_PASS) < 8:
    # Generate a 29char random password. Good enough.
    import M2Crypto, os, re
    randpw = re.sub(os.linesep, '', M2Crypto.m2.rand_bytes(24).encode('base64').rstrip())
    print "Generating a random password for DB_PASS. Copy/paste the following commands to setup a random non-fail password."
    print '\n\techo "DB_PASS = \'%s\'" >> local_settings.py\n' % randpw
    raise ValueError('DB_PASS needs to be set and longer than 8 characters (len(DB_PASS) >= 16 recommended)!')


# Add a small amount of anti-footshooting and check to make sure a password
# hash is set of modest strength.
if len(PASSWORD_HASH) < 32:
    # Generate a decently long random secret.
    import M2Crypto, os, re
    randsec = re.sub(os.linesep, '', M2Crypto.m2.rand_bytes(256).encode('base64').rstrip())
    print "Generating a random secret for PASSWORD_HASH. Copy/paste the following commands to setup a random non-fail secret.\n"
    print '\techo "PASSWORD_HASH = \'%s\'.decode(\'base64\')" >> local_settings.py\n' % randsec
    print "DO NOT LOOSE PASSWORD_HASH! If you loose PASSWORD_HASH no users will be able to log in and every user will have to reset their password!!!\n"
    raise ValueError('PASSWORD_HASH needs to be set and longer than 32 characters (len(PASSWORD_HASH) >= 32 recommended)!')


# Add a small amount of anti-footshooting and check to make sure a secret key
# is set of modest strength.
if len(SECRET_KEY) < 32:
    # Generate a decently long random secret.
    import M2Crypto, os, re
    randsec = re.sub(os.linesep, '', M2Crypto.m2.rand_bytes(256).encode('base64').rstrip())
    print "Generating a random secret for SECRET_KEY. Copy/paste the following commands to setup a random non-fail secret.\n"
    print '\techo "SECRET_KEY = \'%s\'.decode(\'base64\')" >> local_settings.py\n' % randsec
    raise ValueError('SECRET_KEY needs to be set and longer than 32 characters (len(SECRET_KEY) >= 64 recommended)!')


# If we're running in SSL mode, check for the files or give users a hint on
# how to generate the keys.
if USE_SSL:
    import os
    key_file = SSL_PRIVATE_KEY_FILENAME if SSL_PRIVATE_KEY_FILENAME else 'ssl.key'
    cert_file = SSL_CERT_FILENAME if SSL_CERT_FILENAME else 'ssl.cert'
    if not os.access(key_file, os.R_OK) and not os.access(cert_file, os.R_OK):
        print "HINT: To generate a key and cert without it prompting for information (spaces are escaped with a \\):\n"
        print "\topenssl req -x509 -nodes -days 365 -subj '/C=US/ST=MyState/L=MyCity/CN=127.0.0.1/O=MyCompany\ Inc/OU=MyOU/emailAddress=user@example.com' -newkey rsa:1024 -keyout %s -out %s\n" % (key_file, cert_file)
        raise ValueError('SSL_PRIVATE_KEY_FILENAME file missing (possibly needs to be generated?)')

    else:
        if not os.access(key_file, os.R_OK):
            print "HINT: To generate a private key:\n"
            print "\topenssl genrsa 1024 > %s\n" % key_file
            raise ValueError('SSL_PRIVATE_KEY_FILENAME file missing (possibly needs to be generated?)')

        if not os.access(cert_file, os.R_OK):
            print "HINT: To generate a private key:\n"
            print "\topenssl req -new -x509 -nodes -sha1 -days 365 -key %s > %s\n" % (key_file, cert_file)
            raise ValueError('SSL_CERT_FILENAME file missing (possibly needs to be generated?)')

    from OpenSSL import SSL
    ctx = SSL.Context(SSL.TLSv1_METHOD)
    ctx.use_privatekey_file(key_file)
    ctx.use_certificate_file(cert_file)
    WERKZEUG_OPTS['ssl_context'] = ctx

    ### WARNING: Ugh. Monkey pach in a fix to correct pyOpenSSL's
    ### incompatible ServerSocket implementation that accepts zero arguments
    ### for shutdown() instead of one. Fix up
    ### lib/python2.7/SocketServer.py:459's shutdown() call because that
    ### appears to be easier to quickly hack in versus patching
    ### pyOpenSSL. Again, don't use this for production, but it's great for
    ### testing.
    def monkeyp_ssl_shutdown_request(self, request):
        try:
            request.shutdown()
        except socket.error:
            pass #some platforms may raise ENOTCONN here
        self.close_request(request)
    from SocketServer import TCPServer
    TCPServer.shutdown_request = monkeyp_ssl_shutdown_request



# Derived values
SQLALCHEMY_DATABASE_URI = DATABASE_URI_FMT.format(**
    {   'username': DB_USER,
        'password': DB_PASS,
        'hostname': DB_HOST,
        'port':     DB_PORT,
        'dbname':   DB_NAME,
        'schema':   DB_SCHEMA,
    })

# Explicitly specify what's a local request
scheme = 'https' if USE_SSL else 'http'
LOCAL_REQUEST = '%s://%s:%s/' % (scheme, CANONICAL_NAME, CANONICAL_PORT)

########NEW FILE########
__FILENAME__ = runserver
from skeleton import create_app


app = create_app(__name__)

if app.config['DEBUG']:
    app.debug = True

app.run(**app.config['WERKZEUG_OPTS'])

########NEW FILE########
__FILENAME__ = shell
from skeleton import create_app
app = create_app()
ctx = app.test_request_context()
ctx.push()
from skeleton import db
ses = db.session

########NEW FILE########
__FILENAME__ = strftime
# Trivial example

def strftime(value, format='%c'):
    """ Formats a time value in the specified format """
    return value.strftime(format)

########NEW FILE########
__FILENAME__ = lib
from flask import current_app, request, session

from aaa import LOGIN_SUFFIX_BLACKLIST

def fixup_destination_url(src_param_name, dst_param_name):
    """ Saves the destination URL tagged as a URL parameter or in the session and
    moves it over to a local session variable. Useful when you want to
    capture the last value of something, but a user could possibly walk
    off. """
    local_dsturl = None
    if src_param_name in session:
        # SecureCookie sessions are tamper proof, supposedly. Don't need to
        # check if its a trusted parameter.
        local_dsturl = session.pop(src_param_name)
    elif src_param_name in request.args and local_request(request.args[src_param_name]):
        # Request parameters are spoofable, always check and only accept
        # trusted arguments.
        local_dsturl = request.args[src_param_name]

    # Return if nothing was found in the arguments
    if not local_dsturl:
        return False
    else:
        # If something was found, remove our destination
        session.pop(dst_param_name, None)

    for suffix in LOGIN_SUFFIX_BLACKLIST:
        # XXX: This should be a bit more sophisticated and use a
        # regex that ignores query parameters.
        if local_dsturl.endswith(suffix) and LOGIN_SUFFIX_BLACKLIST[suffix]:
            local_dsturl = None
            break

    if local_dsturl:
        session[dst_param_name] = local_dsturl
    return True


def local_request(url = None):
    """ Determines whether or not a request is local or not """
    if url is not None:
        pass
    elif request.referrer:
        url = request.referrer
    else:
        raise ValueError('Unable to determine if the request is local or not')

    # Perform basic referrer checking
    if not url.startswith(current_app.config['LOCAL_REQUEST']):
        return False

    # Return true last that way we can easily add additional checks.
    return True

########NEW FILE########
__FILENAME__ = timezone
from skeleton import db

class Timezone(db.Model):
    __table__ = db.Table(
        'timezone', db.metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('name', db.String),
        schema='public')

########NEW FILE########
__FILENAME__ = forms
from flaskext.wtf import BooleanField, Email, EqualTo, Form, IntegerField, \
    Length, NumberRange, Optional, Required, PasswordField, QuerySelectField, \
    RadioField, SubmitField, TextField, ValidationError

class LoginForm(Form):
    email = TextField('Email', validators=[Required(), Email()])
    password = PasswordField('Password', validators=[Required()])
    idle_ttl = RadioField('Idle Session Timeout', default='tmp', choices=[
            ('tmp',  '20 minutes'),
            ('day',  '8 hours (a normal business day)'),
            ('week', '8 days (Monday to Monday)'),
            ])
    submit = SubmitField('Login')
    # Tempted to add a Field that would provide a mask for a user's IP
    # address. Defaults to /32, but could be set down to /24 if they're stuck
    # in a totally broken corporate environment.


class ProfileForm(Form):
    password = PasswordField('New Password', validators=[
            Optional(),
            Length(min=8, max=80),
            EqualTo('confirm', message='Passwords must match')
            ])
    confirm = PasswordField('Repeat Password')
    default_ipv4_mask = IntegerField(label='IPv4 Mask', validators=[
            Optional(),
            NumberRange(min=0, max=32, message='IPv4 Mask must between %(min)s and %(max)s'),
            ])
    default_ipv6_mask = IntegerField(label='IPv6 Mask', validators=[
            Optional(),
            NumberRange(min=0, max=128, message='IPv6 Mask must between %(min)s and %(max)s'),
            ])
    timezone = QuerySelectField(get_label='name', allow_blank=True)
    submit = SubmitField('Update Profile')


class RegisterForm(Form):
    email = TextField('Email Address', validators = [Email()])
    password = PasswordField('New Password', validators=[
            Required(),
            Length(min=8, max=80),
            EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    accept_tos = BooleanField('I accept the TOS', validators = [Required()])
    timezone = QuerySelectField(get_label='name', allow_blank=True)
    submit = SubmitField('Register')

########NEW FILE########
__FILENAME__ = email
from skeleton import db

class Email(db.Model):
    __table__ = db.Table(
        'email', db.metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('email', db.String),
        db.Column('user_id', db.Integer),
        schema='email')

########NEW FILE########
__FILENAME__ = user
from skeleton import db

class User(db.Model):
    active = db.Column(db.Boolean)
    default_ipv4_mask = db.Column(db.Integer)
    default_ipv6_mask = db.Column(db.Integer)
    max_concurrent_sessions = db.Column(db.Integer)
    registration_utc = db.Column(db.DateTime(timezone=True))
    timezone_id = db.Column(db.Integer, db.ForeignKey('public.timezone.id'))
    timezone = db.relationship('Timezone', primaryjoin='Timezone.id==User.timezone_id')
    user_id = db.Column(db.Integer, primary_key=True)

    __tablename__ = 'user'
    __table_args__ = {'schema':'aaa'}

########NEW FILE########
__FILENAME__ = user_emails
from skeleton import db

class UserEmails(db.Model):
    __table__ = db.Table(
        'user_emails', db.metadata,
        db.Column('user_id', db.Integer, primary_key=True),
        db.Column('email_id', db.Integer),
        db.Column('email', db.String),
        db.Column('user_primary_email_id', db.Integer),
        schema='email')

########NEW FILE########
__FILENAME__ = user_info
from skeleton import db

class UserInfo(db.Model):
    timezone_id = db.Column(db.Integer, db.ForeignKey('public.timezone.id'))
    timezone = db.relationship('Timezone', primaryjoin='Timezone.id==UserInfo.timezone_id')

    user_id = db.Column(db.Integer, primary_key=True)

    __tablename__ = 'user_info'
    __table_args__ = {'schema':'aaa'}

########NEW FILE########
__FILENAME__ = user
from flask import request
from sqlalchemy.sql.expression import bindparam, text

from skeleton import cache, db
from .models.user_info import UserInfo

@cache.memoize()
def get_user_id(email = None, session_id = None):
    """ Helper function that returns the user_id for a given email address """
    if email is not None:
        result = db.session.execute(
            text("SELECT aaa.get_user_id_by_email(:email)",
                 bindparams=[bindparam('email', email)]))
        return result.first()[0]

    if session_id is not None:
        result = db.session.execute(
            text("SELECT aaa.get_user_id_by_session_id(:session)",
                 bindparams=[bindparam('session', session_id)]))
        return result.first()[0]
    return None


@cache.memoize()
def get_user_timezone(user_id = None, email = None, session_id = None):
    """ Helper function that returns the user's timezone """
    if session_id is not None:
        user_id = get_user_id(session_id=session_id)

    if email is not None:
        user_id = get_user_id(email)

    if user_id is not None:
        return UserInfo.query.filter_by(user_id=user_id).first().timezone.name

    return None

########NEW FILE########
__FILENAME__ = views
import hashlib

from flask import current_app, flash, g, redirect, render_template, \
    request, session, url_for
from sqlalchemy.sql.expression import bindparam, text
from sqlalchemy.types import LargeBinary

from skeleton import db
from skeleton.lib import fixup_destination_url, local_request
from .forms import LoginForm, ProfileForm, RegisterForm
from . import fresh_login_required, gen_session_id, module
from skeleton.models import Timezone
from aaa.models.user import User
from .user import get_user_id


@module.route('/login', methods=('GET','POST'))
def login():
    form = LoginForm()
    # Generate a session ID for them if they don't have one
    if 'i' not in session:
        session['i'] = gen_session_id()

    fixup_destination_url('dsturl','post_login_url')

    if form.validate_on_submit():
        remote_addr = request.environ['REMOTE_ADDR']

        # Hash the password once here:
        h = hashlib.new('sha256')
        h.update(current_app.config['PASSWORD_HASH'])
        h.update(form.password.data)
        shapass = h.digest()

        # Change out the values of the session ttl
        idle = '1 second'
        if form.idle_ttl.data == 'tmp':
            idle = '20 minutes'
        elif form.idle_ttl.data == 'day':
            idle = '1 day'
        elif form.idle_ttl.data == 'week':
            idle = '1 week'
        else:
            flask.abort(500)

        # Generate a new session ID upon login. If someone steals my session
        # id, I want to explicitly prevent its use as a way of inject
        # unauthenticated session information in to an authenticated
        # session. In the future once pgmemcache has been hooked up to the
        # database, the old session id will be expired from memcache
        # automatically.
        new_sess_id = gen_session_id()

        ses = db.session
        result = ses.execute(
            text("SELECT ret, col, msg FROM aaa.login(:email, :pw, :ip, :sid, :idle, :secure) AS (ret BOOL, col TEXT, msg TEXT)",
                 bindparams=[
                    bindparam('email', form.email.data),
                    bindparam('pw', shapass, type_=LargeBinary),
                    bindparam('ip', remote_addr),
                    bindparam('sid', new_sess_id),
                    bindparam('idle',idle),
                    bindparam('secure', request.is_secure)]))

        # Explicitly commit regardless of the remaining logic. The database
        # did the right thing behind the closed doors of aaa.login() and we
        # need to make sure that the logging to shadow.aaa_login_attempts is
        # COMMIT'ed so that customer support can help the poor, frustrated
        # (stupid?) users.
        ses.commit()
        row = result.first()
        if row[0] == True:
            session['i'] = new_sess_id
            session['li'] = True
            flash('Successfully logged in as %s' % (form.email.data))
            if 'post_login_url' in session:
                return redirect(session.pop('post_login_url'))
            else:
                return redirect(url_for('home.index'))
        else:
            session.pop('li', None)
            # Return a useful error message from the database
            try:
                # If the database says be vague, we'll be vague in our error
                # messages. When the database commands it we obey, got it?
                if row[1] == 'vague':
                    # Set bogus data so that 'form.errors == True'. If brute
                    # force weren't such an issue, we'd just append a field
                    # error like below. If you want to get the specifics of
                    # why the database rejected a user, temporarily change
                    # the above 'vague' to something that the database
                    # doesn't return, such as 'EDRAT' or something equally
                    # POSIXly funny.
                    form.errors['EPERM'] = 'There is no intro(2) error code for web errors'
                    pass
                else:
                    field = form.__getattribute__(row[1])
                    field.errors.append(row[2])
            except AttributeError as e:
                pass
    return render_template('aaa/login.html', form=form)


@module.route('/logout')
def logout():
    # Is there a destination post-logout?
    dsturl = None
    if request.referrer and local_request(request.referrer):
        dsturl = request.referrer
    else:
        dsturl = None

    # End the session in the database
    already_logged_out = False
    if 'li' in session:
        ses = db.session
        result = ses.execute(
            text("SELECT ret, col, msg FROM aaa.logout(:sid) AS (ret BOOL, col TEXT, msg TEXT)",
                 bindparams=[bindparam('sid', session['i'])]))
        ses.commit()
        # For now, don't test the result of the logout call. Regardless of
        # whether or not a user provides us with a valid session ID from the
        # wrong IP address, terminate the session. Shoot first, ask questions
        # later (i.e. why was a BadUser in posession of GoodUser's session
        # ID?!)
    else:
        already_logged_out = True

    # Nuke every key in the session
    for k in session.keys():
        session.pop(k)

    # Set a flash message after we nuke the keys in session
    if already_logged_out:
        flash('Session cleared for logged out user')
    else:
        flash('You were logged out')

    return render_template('aaa/logout.html', dsturl=dsturl)


@module.route('/profile', methods=('GET','POST'))
@fresh_login_required
def profile():
    user_id = get_user_id(session_id = session['i'])
    user = User.query.filter_by(user_id=user_id).first_or_404()
    form = ProfileForm(obj=user)
    form.timezone.query = Timezone.query.order_by(Timezone.name)

    if form.validate_on_submit():
        shapass = None
        if form.password:
            # Hash the password once here:
            h = hashlib.new('sha256')
            h.update(current_app.config['PASSWORD_HASH'])
            h.update(form.password.data)
            shapass = h.digest()

        form.populate_obj(user)
        user.password = shapass
        db.session.add(user)
        db.session.commit()
    return render_template('aaa/profile.html', form=form)


@module.route('/register', methods=('GET','POST'))
def register():
    form = RegisterForm()
    if 'i' not in session:
        session['i'] = gen_session_id()

    form.timezone.query = Timezone.query.order_by(Timezone.name)
    if form.validate_on_submit():
        # Form validates, execute the registration pl function

        remote_addr = request.environ['REMOTE_ADDR']

        # Hash the password once here:
        h = hashlib.new('sha256')
        h.update(current_app.config['PASSWORD_HASH'])
        h.update(form.password.data)
        shapass = h.digest()

        ses = db.session
        result = ses.execute(
            text("SELECT ret, col, msg FROM aaa.register(:email, :pw, :ip) AS (ret BOOL, col TEXT, msg TEXT)",
                 bindparams=[
                    bindparam('email', form.email.data),
                    bindparam('pw', shapass, type_=LargeBinary),
                    bindparam('ip', remote_addr)]))
        row = result.first()
        if row[0] == True:
            # Update the user's timezone if they submitted a timezone
            if form.timezone.data:
                res = ses.execute(
                    text("INSERT INTO aaa.user_info (user_id, timezone_id) VALUES (get_user_id_by_email(:email), :tz)",
                         bindparams=[bindparam('email', form.email.data),
                                     bindparam('tz', form.timezone.data.id),]))
            ses.commit()
            flash('Thanks for registering! Please check your %s email account to confirm your email address.' % (form.email.data))
            return redirect(url_for('aaa.login'))
        else:
            # Return a useful error message from the database
            try:
                field = form.__getattribute__(row[1])
                field.errors.append(row[2])
            except AttributeError as e:
                pass
    return render_template('aaa/register.html', form=form)

########NEW FILE########
__FILENAME__ = h1
from skeleton import db

class H1(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    val = db.Column(db.String)
    __table_args__ = {'schema':'public'}

########NEW FILE########
__FILENAME__ = h3
from skeleton import db

class H3(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    val2 = db.Column(db.String)
    __table_args__ = {'schema':'public'}

########NEW FILE########
__FILENAME__ = views
from flask import render_template, request

from home import module

@module.route('/')
def index():
    remote_addr = request.environ['REMOTE_ADDR']
    return render_template('home/index.html', remote_addr=remote_addr)

########NEW FILE########
__FILENAME__ = h2
from skeleton import db

# Note the conflicting variable and table name.
class H2(db.Model):
    __table__ = db.Table(
        'h2', db.metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('val2', db.String),
        schema='mod1')

########NEW FILE########
__FILENAME__ = views
import random

from flask import render_template, request

from skeleton import cache

from . import module
from .models import H2

@cache.memoize(timeout=10)
def random_func(useless_parameter):
    """ Cache a random number for 10 seconds """
    # Ignore the useless_parameter for this example
    return random.randrange(0, 100000)

@module.route('/mod1_view')
def index(name = None):
    # Call random_func() 10x times, twice.
    cached_values = []
    for i in range(0,10):
        cached_values.append(random_func(i))
    for i in range(0,10):
        cached_values.append(random_func(i))

    # There should be 10 unique values even though we appended twice to the
    # list.
    cached_values = list(set(cached_values))
    unique_values = len(cached_values)
    return render_template('mod1/mod1_view.html', name=name, cached_values=cached_values, unique_values=unique_values)

@module.route('/list_all')
def list_all():
    entries = H2.query.all()
    return render_template('mod1/list_all.html', entries=entries)

@module.route('/list_one')
def list_one():
    id = request.args.get('id', 1)
    entry = H2.query.filter_by(id=id).first_or_404()
    return render_template('mod1/list_one.html', entry=entry)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime, timedelta

from flask import render_template, redirect, session, url_for

from skeleton import cache

from . import module

def user_logged_in():
    """ Returns true if the user is logged in """
    return True if 'li' in session else False

@module.route('/cache_logged_out')
@cache.cached(timeout=60, unless=user_logged_in)
def cache_logged_out():
    # Set a simple counter. A logged out user won't see this incrementing,
    # but a logged in user will.
    mc_key = 'user_page_count'
    count = cache.get(mc_key)
    if not count:
        count = 0
    cache.set(mc_key, count + 1)

    now = datetime.today()
    expires = now + timedelta(seconds = 60)

    return render_template('mod2/cache_logged_out.html', time=datetime.today(), expires=expires, count=count)

@module.route('/cached_always')
@cache.cached(timeout=15)
def cached_always():
    now = datetime.today()
    expires = now + timedelta(seconds = 15)
    return render_template('mod2/cached_always.html', time=now, expires=expires)

@module.route('/')
def index():
    return render_template('mod2/index.html')

# Create a view that redirects to mod2's index: http://127.0.0.1:5000/mod2/redirect_here
@module.route('/redirect_here')
def redir_index():
    return redirect(url_for('index'))

# Create a view that redirects to home's index: http://127.0.0.1:5000/mod2/redirect_home
@module.route('/redirect_home')
def redir_index2():
    return redirect(url_for('home.index'))

########NEW FILE########
__FILENAME__ = forms
import re

from flaskext.wtf import Form, Regexp, Required, SubmitField, TextField, URL

class PageAddTagForm(Form):
    tag = TextField('Tag', validators=[
            Required(),
            Regexp(regex=r'[a-z0-9]{1,80}', flags=re.IGNORECASE, message='Invalid Tag. Only able to use a-z and 0-9'),
            ])
    submit = SubmitField('Submit')


class PageSubmitForm(Form):
    url = TextField('URL', validators=[Required(), URL()])
    submit = SubmitField('Submit')

########NEW FILE########
__FILENAME__ = page
from skeleton import db

from .page_tags import PageTags

class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String)
    tags = db.relationship(
        'Tag', secondary=PageTags,
        backref=db.backref('pages', lazy='dynamic'))
    __tablename__ = 'page'
    __table_args__ = {'schema':'public'}

    def __init__(self, url = url):
        self.url = url

########NEW FILE########
__FILENAME__ = page_tags
from skeleton import db

PageTags = db.Table('page_tags', db.metadata,
    db.Column('page_id', db.Integer, db.ForeignKey('public.page.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('public.tag.id')),
    schema='public'
)

########NEW FILE########
__FILENAME__ = tag
from skeleton import db

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    # Placeholders:
    # pages is created automatically via the Page model
    __tablename__ = 'tag'
    __table_args__ = {'schema':'public'}

########NEW FILE########
__FILENAME__ = views
from datetime import datetime

from flask import current_app, flash, redirect, render_template, \
    session, url_for
from flaskext.babel import to_user_timezone

from skeleton import babel, db
from aaa import login_required
from aaa.user import get_user_timezone

from . import module
from .forms import PageAddTagForm, PageSubmitForm
from .models import Page, PageTags, Tag


@babel.timezoneselector
def get_timezone():
    if 'li' in session:
        return get_user_timezone(session_id=session['i'])


@module.route('/')
def some_random_view():
    t = datetime.utcnow()
    return render_template('mod3/root.html', time=to_user_timezone(t))


@module.route('/pages')
def page_list():
    entries = Page.query.order_by(Page.url).all()
    return render_template('mod3/pages.html', pages=entries)

@module.route('/page/submit', methods=('GET','POST'))
@login_required
def page_submit():
    form = PageSubmitForm()
    if form.validate_on_submit():
        ses = db.session
        page = Page.query.filter_by(url = form.url.data.lower()).first()
        # Only add non-duplicate pages
        if page is None:
            page = Page(form.url.data)
            ses.add(page)
        ses.commit()
        return redirect(url_for('page_tags', page_id = page.id))
    return render_template('mod3/page_submit.html', form=form)


@module.route('/page/tags/<int:page_id>')
def page_tags(page_id):
    page = Page.query.filter_by(id = page_id).first_or_404()
    # Get a list of all of the tags that are on a given page. Note how we
    # created the join from the origin table, Tag, all the way over to the
    # Page table through the mapping table.
    tags = Tag.query.join(PageTags, Page).filter(Page.id == page.id).order_by('name').all()
    return render_template('mod3/page_tags.html', page=page, tags=tags)


@module.route('/tag/page/<int:page_id>/add', methods=('GET','POST'))
@login_required
def tag_add(page_id):
    page = Page.query.filter_by(id = page_id).first_or_404()
    form = PageAddTagForm()
    ses = db.session
    if form.validate_on_submit():
        # See if the tag already exists
        tag = Tag.query.filter_by(name = form.tag.data.lower()).first()
        if tag is None:
            # Create the tag
            tag = Tag(name = form.tag.data)
            ses.add(tag)
            flash('Adding tag %s' % tag.name)
        else:
            flash('Tag %s already exists with id %s, not adding' % (tag.name, tag.id))
        # See if there's a mapping row exists or not. If not, add one.
        if tag.pages.filter(Page.id == page.id).first() is None:
            tag.pages.append(page)
            flash('Adding tag %s to page %s' % (tag.name, page.url))
        else:
            flash('tag.id %s already exists for page %s' % (tag.id, page.id))
        ses.commit()
        return redirect(url_for('page_tags', page_id = page.id))
    return render_template('mod3/tag_add.html', form=form, page=page)


@module.route('/tag/pages/<int:tag_id>')
def tag_pages(tag_id):
    tag = Tag.query.filter_by(id = tag_id).first_or_404()
    return render_template('mod3/tag_pages.html', tag=tag)


@module.route('/tags')
def tag_list():
    tags = Tag.query.order_by('name').all()
    return render_template('mod3/tags.html', tags=tags)

########NEW FILE########
