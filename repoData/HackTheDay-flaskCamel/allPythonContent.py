__FILENAME__ = config
import os

DEBUG = 0
CSRF_ENABLED = True
SECRET_KEY = '4740e2b#$%$dsfds55wer#455'

basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'flaskcamel.db')
STATIC_ROOT = None

#EMAIL SETTINGS
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'your_gmail_id@gmail.com'
MAIL_PASSWORD = 'your_gmail_pass'
MAIL_DEBUG = 0

########NEW FILE########
__FILENAME__ = decorators
from threading import Thread


def async(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()
    return wrapper

########NEW FILE########
__FILENAME__ = forms
from flask.ext.wtf import Form
from wtforms import TextField, validators, PasswordField, ValidationError

import models


def validate_user(form, username):
    user_by_name = models.Users.query.filter_by(username=username.data).first()
    if user_by_name:
        raise ValidationError('Username already taken. Choose another')


def validate_email(form, email):
    user_by_email = models.Users.query.filter_by(email=email.data).first()
    if user_by_email:
        raise ValidationError("Email already registered. Login or register \
                               with another Email")


class DetailForm(Form):
    name = TextField('Payee Name:', [validators.Required()])
    street = TextField('Street Address:', [validators.Required()])
    city = TextField('City/Town:', [validators.Required()])
    phone = TextField('Phone:', [validators.Required()])
    website = TextField('My website:', [validators.Required()])


class SignupForm(Form):
    username = TextField('Username', [validators.Required(),
                         validate_user, validators.Length(min=4, max=25)])
    password = PasswordField('Password', [validators.Required(),
                             validators.Length(min=4, max=25),
                             validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm Password', [validators.Required()])
    email = TextField('eMail', [validators.Required(),
                      validators.Email(), validate_email])


class LoginForm(Form):
    username = TextField('Username', [validators.Required()])
    password = PasswordField('Password', [validators.Required()])


class PasswordResetForm(Form):
    username = TextField('Username')
    email = TextField('eMail')


class PasswordChangeForm(Form):
    password = PasswordField('Password', [validators.Required()])

########NEW FILE########
__FILENAME__ = hooks
from flask import url_for
from flaskcamel import app
import urlparse


def static(path):
    root = app.config.get('STATIC_ROOT')
    if root is None:
        return url_for('static', filename=path)
    else:
        return urlparse.urljoin(root, path)


@app.context_processor
def context_processor():
    return dict(static=static)

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from flaskext.bcrypt import Bcrypt
from flask.ext import admin
from flask.ext.login import current_user, UserMixin
from flask.ext.admin.contrib import sqla
from flask.ext.admin.contrib.sqla import filters

from flaskcamel import db, app


ROLE_ADMIN = 0
ROLE_WEB_USER = 1

bcrypt = Bcrypt()


class Users(db.Model, UserMixin):
    __tablename__ = 'users'
    uid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True)
    pwdhash = db.Column(db.String(60))
    email = db.Column(db.String(60), unique=True)
    fb_id = db.Column(db.String(30), unique=True)
    role = db.Column(db.SmallInteger)
    activate = db.Column(db.Boolean)
    created = db.Column(db.DateTime)

    def __init__(self, username, password, email, role):
        self.username = username
        self.pwdhash = bcrypt.generate_password_hash(password)
        self.email = email
        self.role = role
        self.activate = False
        self.created = datetime.utcnow()

    def check_password(self, password):
        return bcrypt.check_password_hash(self.pwdhash, password)

    def get_role(self):
        return unicode(self.role)

    def is_active(self):
        return self.activate

    def is_authenticated(self):
        return True

    def get_id(self):
        return self.uid

    def __unicode__(self):
        return self.username


# Model for User Details
class UserDetail(db.Model):
    __tablename__ = 'userdetail'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    street = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    website = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.uid'))
    user = db.relationship('Users',
                           primaryjoin="Users.uid == UserDetail.uid",
                           backref=db.backref('users', lazy="joined"))

    def __init__(self, name, street, city, phone, website, date, uid):
        self.name = name
        self.street = street
        self.city = city
        self.phone = phone
        self.website = website
        self.date = date
        self.uid = uid

    def is_verified(self):
        return self.appstatus

    def __unicode__(self):
        return self.website


# Customized User model admin
class UsersAdmin(sqla.ModelView):
    column_sortable_list = ('uid', 'username', 'email', 'created', 'role')
    column_labels = dict(title='Comment Title')
    column_searchable_list = ('username', Users.username)
    column_filters = ('uid',
                      'username',
                      'email',
                      'created',
                      'role',
                      filters.FilterLike(Users.username, 'Fixed Title',
                                         options=(('test1', 'Test 1'),
                                                  ('test2', 'Test 2'))))

    form_args = dict(text=dict(label='Big Text', validators=[]))

    def __init__(self, session):
        super(UsersAdmin, self).__init__(Users, session)

    def is_accessible(self):
        if current_user.get_role() == '0':
            return current_user.is_authenticated()


# Customized UserDetail model admin
class UserDetailAdmin(sqla.ModelView):
    column_sortable_list = ('name', 'uid', 'date', 'website')
    column_labels = dict(title='Comment Title')
    column_searchable_list = ('website', UserDetail.website)
    column_filters = ('uid',
                      'website',
                      'date',
                      'name',
                      filters.FilterLike(UserDetail.website, 'Fixed Title',
                                         options=(('test1', 'Test 1'),
                                                  ('test2', 'Test 2'))))
    form_args = dict(text=dict(label='Big Text', validators=[]))

    def __init__(self, session):
        super(UserDetailAdmin, self).__init__(UserDetail, session)

    def is_accessible(self):
        if current_user.get_role() == '0':
            return current_user.is_authenticated()

# Create admin
admin = admin.Admin(app, 'FlaskCamel Admin')

# Add views to admin
admin.add_view(UsersAdmin(db.session))
admin.add_view(UserDetailAdmin(db.session))

########NEW FILE########
__FILENAME__ = views
from datetime import datetime, date

from itsdangerous import URLSafeSerializer

from flask import render_template, url_for, redirect, flash, request, session
from flask.ext.login import (LoginManager, current_user, login_required,
                             login_user, logout_user, AnonymousUser)
from flask.ext.mail import Mail, Message
from flaskext.bcrypt import Bcrypt
from flask_debugtoolbar import DebugToolbarExtension
from flask.ext.oauth import OAuth

from forms import SignupForm, LoginForm, PasswordResetForm, PasswordChangeForm, DetailForm
from flaskcamel import app, db
from models import Users, UserDetail
from decorators import async

oauth = OAuth()
toolbar = DebugToolbarExtension(app)
bcrypt = Bcrypt()
mail = Mail(app)

# Faceboook App Credentials
facebook = oauth.remote_app('facebook',
                            base_url='https://graph.facebook.com/',
                            request_token_url=None,
                            access_token_url='/oauth/access_token',
                            authorize_url='https://www.facebook.com/dialog/oauth',
                            consumer_key='your_consumer_key',
                            consumer_secret='your_secret_key',
                            request_token_params={'scope': 'email'})


class Anonymous(AnonymousUser):
    name = u"Anonymous"

login_manager = LoginManager()
login_manager.anonymous_user = Anonymous
login_manager.login_view = "login"
login_manager.login_message = u"Please log in to access this page."
login_manager.refresh_view = "reauth"
login_manager.init_app(app)


@async
def send_async_email(msg):
    mail.send(msg)


@app.errorhandler(404)
def internal_error404(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error500(error):
    db.session.rollback()
    return render_template('500.html'), 500


@login_manager.user_loader
def load_user(uid):
    return Users.query.filter_by(uid=uid).first()


@app.route('/')
def index():
    if current_user.is_authenticated():
        if current_user.get_role() == '1':
            appslist = UserDetail.query \
                                 .filter_by(uid=current_user.get_id()) \
                                 .order_by(db.desc(UserDetail.website))
            return render_template('index.html', appslist=appslist)

    return render_template('welcome.html')


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('manage_apps.html')


@app.route('/add_detail', methods=['GET', 'POST'])
@login_required
def add_detail():
    if current_user.get_role() == '1':
        form = DetailForm()
        if form.validate_on_submit():
            _detail = UserDetail(
                form.name.data,
                form.street.data,
                form.city.data,
                form.phone.data,
                form.website.data,
                date.today(),
                current_user.get_id()
            )
            _detail.date = datetime.now()
            db.session.add(_detail)
            db.session.commit()
            flash(u'Your details were submitted succsessfully.')
            return redirect(url_for('index'))
        return render_template('add_detail.html', form=form)
    return redirect(url_for('index'))

    
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = SignupForm()
    if form.validate_on_submit():
        user = Users(
            form.username.data,
            form.password.data,
            form.email.data,
            1,)
        db.session.add(user)
        db.session.commit()
        confirm_user(form.username.data, form.email.data)
        flash(u'Check your email to activate your account.')
        return redirect(url_for('index'))

    flash(u'Create your flaskCamel account')
    return render_template('register.html', form=form)


def confirm_user(username, email):
    s = URLSafeSerializer('serliaizer_code')
    key = s.dumps([username, email])

    msg = Message("Account Confirmation", sender="your_id@your_host.com", recipients=[email])
    msg.html = "<b>Welcome to flaskCamel!!!</b></br> Confirmation your\
                account by clicking on this below link </br></br> \
                <a href='http://127.0.0.1:5000/confirmaccount/" + key + "'>\
                http://127.0.0.1:5000/confirmaccount/" + key + "</a>\
                </br></br> Team flaskCamel"
    send_async_email(msg)

    flash(u'Confirmation Email sent to: ' + email)
    return redirect(url_for('index'))


@app.route('/confirmaccount/<secretstring>', methods=['GET', 'POST'])
def confirm_account(secretstring):
    s = URLSafeSerializer('serliaizer_code')
    uname, uemail = s.loads(secretstring)
    user = Users.query.filter_by(username=uname).first()
    user.activate = True
    db.session.add(user)
    db.session.commit()
    flash(u'Your account was confirmed succsessfully!!!')
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated():
        return redirect(url_for('index'))
    else:
        form = LoginForm()
        if form.validate_on_submit():
            admin = Users.query.filter_by(username=form.username.data).first()
            if admin:
                if admin.check_password(form.password.data):
                    login_user(admin)
                    flash(admin.username + ' logged in')
                    return redirect(url_for('index'))
                else:
                    flash('wrong pass')
                    return redirect(url_for('login'))
            else:
                flash('wrong username')
                return redirect(url_for('login'))
    flash(u'Enter your email and password.')
    return render_template('login.html', form=form)


@app.route('/passwordreset', methods=['GET', 'POST'])
def reset_password():
    form = PasswordResetForm()
    if form.validate_on_submit():
        if form.username.data:
            user = Users.query.filter_by(username=form.username.data).first()
        elif form.email.data:
            user = Users.query.filter_by(email=form.email.data).first()
        else:
            flash("Username or password doesn't exists")

        if user:
            if user.email:
                s = URLSafeSerializer('serliaizer_code')
                key = s.dumps([user.username, user.email])

            msg = Message("Password reset", sender="your_id@your_host.com", recipients=[user.email])
            msg.html = "<b>Click on this link to reset your password.</b> \
                        #<a href='http://127.0.0.1:5000/passwordreset/ \
                        " + key + "'>http://127.0.0.1:5000/passwordreset/ \
                        " + key + "</a>"

            send_async_email(msg)
            
            flash('Email sent to: ' + user.email)
            return redirect(url_for('reset_password'))
        else:
            flash('No such user')
            return redirect(url_for('reset_password'))
    flash(u'Enter your email or username')
    return render_template('reset_password.html', form=form)


@app.route('/passwordreset/<secretstring>', methods=['GET', 'POST'])
def change_password(secretstring):
    form = PasswordChangeForm()
    if form.validate_on_submit():
      
        if form.password.data:
            s = URLSafeSerializer('serliaizer_code')
            uname, uemail = s.loads(secretstring)
            user = Users.query.filter_by(username=uname).first()
            db.session.add(user)
            user.pwdhash = bcrypt.generate_password_hash(form.password.data)
            db.session.commit()
            flash(u'succsessful password reset')
            return redirect(url_for('login'))
        else:
            flash('Try again!')
            return redirect(url_for('reset_password'))

    return render_template('change_password.html', form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.")
    return redirect(url_for("index"))


#Facebook OAuth integration

@app.route('/fblogin')
def facebook_login():
    return facebook.authorize(callback=url_for('facebook_authorized',
                              next=request.args.get('next') or request.referrer or None,
                              _external=True))


@app.route('/login/authorized')
@facebook.authorized_handler
def facebook_authorized(resp):
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        flash('You denied the facebook login')
        return redirect(next_url)

    session['fb_access_token'] = (resp['access_token'], '')

    me = facebook.get('/me')
    user = Users.query.filter_by(fb_id=me.data['id']).first()
    
    if user:
        if me.data['username']:
            fb_username = me.data['username']
        else:
            fb_username = me.data['name']

        fb_email = me.data['email']

        role = 1
        user = Users(fb_username, 'temp', fb_email, role)
        user.fb_id = me.data['id']
        user.activate = True
        user.created = datetime.utcnow()
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.uid

        flash('You are now logged in as %s' % user.username)
        return redirect(url_for('index'))


@facebook.tokengetter
def get_facebook_oauth_token():
    return session.get('fb_access_token')

########NEW FILE########
__FILENAME__ = manage
from flaskcamel import app, db

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
    #app.run(host='0.0.0.0')

########NEW FILE########
