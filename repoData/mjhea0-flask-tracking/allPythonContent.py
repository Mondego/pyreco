__FILENAME__ = bases
from flask.ext.testing import TestCase
from app import app, db


class BaseTestCase(TestCase):
    """A base test case for flask-tracking."""

    def create_app(self):
        app.config.from_object('config.TestConfiguration')
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

########NEW FILE########
__FILENAME__ = constants

########NEW FILE########
__FILENAME__ = mixins
from app import db

class CRUDMixin(object):
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)

    @classmethod
    def get_by_id(cls, id):
        if any(
            (isinstance(id, basestring) and id.isdigit(),
             isinstance(id, (int, float))),
        ):
            return cls.query.get(int(id))
        return None

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        return instance.save()

    def update(self, commit=True, **kwargs):
        for attr, value in kwargs.iteritems():
            setattr(self, attr, value)
        return commit and self.save() or self

    def save(self, commit=True):
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        db.session.delete(self)
        return commit and db.session.commit()

########NEW FILE########
__FILENAME__ = constants

########NEW FILE########
__FILENAME__ = decorators
from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator
########NEW FILE########
__FILENAME__ = forms
from flask.ext.wtf import Form, TextField, PasswordField, BooleanField, RecaptchaField, fields, validators
from flask.ext.wtf import Required, Email, EqualTo
from app.users.models import User
from app import db

class RegisterSiteForm(Form):
    base_url = fields.TextField(validators=[validators.required()])
########NEW FILE########
__FILENAME__ = geodata
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Searches Geolocation of IP addresses using http://freegeoip.net/
It will fetch a csv and return a python dictionary

sample usage:
>>> from freegeoip import get_geodata
>>> get_geodata("189.24.179.76")

{'status': True, 'city': 'Niter\xc3\xb3i', 'countrycode': 'BR', 'ip': '189.24.179.76', 
'zipcode': '', 'longitude': '-43.0944', 'countryname': 'Brazil', 'regioncode': '21', 
'latitude': '-22.8844', 'regionname': 'Rio de Janeiro'}
"""

from urllib import urlopen
from csv import reader
import sys
import re

__author__="Victor Fontes Costa"
__copyright__ = "Copyright (c) 2010, Victor Fontes - victorfontes.com"
__license__ = "GPL"
__version__ = "2.1"
__maintainer__ = __author__
__email__ = "contato [a] victorfontes.com"
__status__ = "Development"

FREE_GEOIP_CSV_URL = "http://freegeoip.net/csv/%s"


def valid_ip(ip):

    pattern = r"\b(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"

    return re.match(pattern, ip)

def __get_geodata_csv(ip):
    if not valid_ip(ip):
        raise Exception('Invalid IP format', 'You must enter a valid ip format: X.X.X.X')

    URL = FREE_GEOIP_CSV_URL % ip
    response_csv = reader(urlopen(URL))
    csv_data = response_csv.next()

    return {
        "status": u"True" == csv_data[0],
        "ip":csv_data[1],
        "countrycode":csv_data[2],
        "countryname":csv_data[3],
        "regioncode":csv_data[4],
        "regionname":csv_data[5],
        "city":csv_data[6],
        "zipcode":csv_data[7],
        "latitude":csv_data[8],
        "longitude":csv_data[9]
    }

def get_geodata(ip):
    return __get_geodata_csv(ip)

if __name__ == "__main__":     #code to execute if called from command-line
    intput_ip = sys.argv[1]
    geodata = get_geodata(intput_ip)
    print "IP: %s" % geodata["ip"]
    print "Country Code: %s" % geodata["countrycode"]
    print "Country Name: %s" % geodata["countryname"]
    print "Region Code: %s" % geodata["regioncode"]
    print "Region Name: %s" % geodata["regionname"]
    print "City: %s" % geodata["city"]
    print "Zip Code: %s" % geodata["zipcode"]
    print "Latitude: %s" % geodata["latitude"]
    print "Longitude: %s" % geodata["longitude"] 
########NEW FILE########
__FILENAME__ = models
from app import db
from app.mixins import CRUDMixin

class Site(CRUDMixin, db.Model):
    __tablename__ = 'tracking_site'
    id = db.Column(db.Integer, primary_key=True)
    visits = db.relationship('Visit', backref='tracking_site',
                                lazy='select')
    base_url = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'))


    def __init__(self, user_id=None, base_url=None):
        self.user_id = user_id
        self.base_url = base_url

    def __repr__(self):
        return '<Site %r>' % (self.base_url)


class Visit(CRUDMixin, db.Model):
    __tablename__ = 'tracking_visit'
    id = db.Column(db.Integer, primary_key=True)
    browser = db.Column(db.Text)
    date = db.Column(db.DateTime)
    event = db.Column(db.Text)
    url = db.Column(db.Text)
    site_id = db.Column(db.Integer, db.ForeignKey('tracking_site.id'))
    ip_address = db.Column(db.Text)
    location = db.Column(db.Text)
    location_full = db.Column(db.Text)

    def __init__(self, browser=None, date=None, event=None, url=None, ip_address=None, location_full=None, location=None):
        self.browser = browser
        self.date = date
        self.event = event
        self.url = url
        self.ip_address = ip_address
        self.location_full = location_full
        self.location = location

    def __repr__(self):
        return '<Visit %r - %r>' % (self.url, self.date)
########NEW FILE########
__FILENAME__ = tests
from flask import url_for
from mock import Mock, patch

from app.bases import BaseTestCase
from app.users.models import User
from app.tracking.models import Site, Visit

import app.tracking.views


class TrackingViewsTests(BaseTestCase):
    def test_visitors_location_is_derived_from_ip(self):
        user = User.create(name="Joe", email="joe@joe.com", password="12345")
        site = Site.create(user_id=user.id)

        mock_geodata = Mock(name="get_geodata")
        mock_geodata.return_value = {
            'city': 'Los Angeles',
            'zipcode': '90001',
            'latitude': '34.05',
            'longitude': '-118.25'
        }

        url = url_for("tracking.register_visit", site_id=site.id)
        wsgi_environment = {"REMOTE_ADDR": "1.2.3.4"}

        with patch.object(app.tracking.views, "get_geodata", mock_geodata):
            with self.client:
                self.client.get(url, environ_overrides=wsgi_environment)

                visits = Visit.query.all()

                mock_geodata.assert_called_once_with("1.2.3.4")
                self.assertEquals(1, len(visits))
                self.assertEquals("Los Angeles, 90001", visits[0].location)
                self.assertEquals("Los Angeles, 90001, 34.05, -118.25",
                                  visits[0].location_full)

########NEW FILE########
__FILENAME__ = views
from flask import Blueprint, Response, render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import current_user, login_required
from app import app, db, login_manager
from app.tracking.models import Site, Visit
from app.tracking.forms import RegisterSiteForm
from datetime import datetime
from app.tracking.geodata import get_geodata
from app.tracking.decorators import crossdomain


mod = Blueprint('tracking', __name__)


@mod.route('/sites/', methods=('GET', 'POST'))
@login_required
def sites_view():
    form = RegisterSiteForm(request.form)
    sites = current_user.sites.all()
    if form.validate_on_submit():
        site = Site()
        form.populate_obj(site)
        site.user_id = current_user.id
        db.session.add(site)
        db.session.commit()
        return redirect('/sites/')
    return render_template('tracking/index.html', form=form, sites=sites)

#http://proj1-6170.herokuapp.com/sites/<%= @current_user.id %>/visited?event='+tracker.settings.event+'&data='+tracker.settings.data+'&visitor='+tracker.settings.visitor
@mod.route('/visit/<int:site_id>/visited', methods=('GET','POST'))
@crossdomain(origin="*", methods=["POST", "GET, OPTIONS"], headers="Content-Type, Origin, Referer, User-Agent", max_age="3600") 
def register_visit(site_id):
    site = Site.get_by_id(site_id)
    if site:
        browser = request.headers.get('User-Agent')
        date = datetime.now()
        event = request.args.get('event')
        url = request.url
        ip_address = request.remote_addr
        geo = get_geodata(ip_address)
        location_full = ", ".join([geo['city'],geo['zipcode'],geo['latitude'],geo['longitude']])
        location = ", ".join([geo['city'],geo['zipcode']])
        visit = Visit(browser, date, event, url, ip_address, location_full, location)
        visit.site_id = site_id
        db.session.add(visit)
        db.session.commit()
    return Response("visit recorded", content_type="text/plain")

# self, browser=None, date=None, event=None, url=None, ip_address=None, location_full=None
########NEW FILE########
__FILENAME__ = constants

########NEW FILE########
__FILENAME__ = decorators

########NEW FILE########
__FILENAME__ = forms
from flask.ext.wtf import Form, fields, validators
from flask.ext.wtf import Required, Email
from app.users.models import User
from app import db


def validate_login(form, field):
    user = form.get_user()

    if user is None:
        raise validators.ValidationError('Invalid user')

    if user.password != form.password.data:
        raise validators.ValidationError('Invalid password')


class LoginForm(Form):
    name = fields.TextField(validators=[Required()])
    password = fields.PasswordField(validators=[Required(), validate_login])

    def get_user(self):
        return db.session.query(User).filter_by(name=self.name.data).first()


class RegistrationForm(Form):
    name = fields.TextField(validators=[Required()])
    email = fields.TextField(validators=[Email()])
    password = fields.PasswordField(validators=[Required()])
    conf_password = fields.PasswordField(validators=[Required()])

    def validate_login(self, field):
        if db.session.query(User).filter_by(username=self.username.data).count() > 0:
            raise validators.ValidationError('Duplicate username')

########NEW FILE########
__FILENAME__ = models
from app import db
from app.mixins import CRUDMixin
from flask.ext.login import UserMixin
from app.tracking.models import Site

class User(UserMixin, CRUDMixin,  db.Model):
    __tablename__ = 'users_user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(120))
    sites = db.relationship('Site', backref='site',
                                lazy='dynamic')

    def __init__(self, name=None, email=None, password=None):
        self.name = name
        self.email = email
        self.password = password

    def __repr__(self):
        return '<User %r>' % (self.name)
########NEW FILE########
__FILENAME__ = tests
from flask import url_for
from flask.ext.login import current_user

from app.bases import BaseTestCase
from app.users.models import User


class UserViewsTests(BaseTestCase):
    def test_users_can_login(self):
        User.create(name="Joe", email="joe@joes.com", password="12345")

        with self.client:
            response = self.client.post("/login/", data={"name": "Joe", "password": "12345"})

            self.assert_redirects(response, url_for("index"))
            self.assertTrue(current_user.name == "Joe")
            self.assertFalse(current_user.is_anonymous())

    def test_users_can_logout(self):
        User.create(name="Joe", email="joe@joes.com", password="12345")

        with self.client:
            self.client.post("/login/", data={"name": "Joe", "password": "12345"})
            self.client.get("/logout/")

            self.assertTrue(current_user.is_anonymous())

    def test_invalid_password_is_rejected(self):
        User.create(name="Joe", email="joe@joes.com", password="12345")

        with self.client:
            self.client.post("/login/", data={"name": "Joe", "password": "****"})

            self.assertTrue(current_user.is_anonymous())

########NEW FILE########
__FILENAME__ = views
from flask import Blueprint, render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from app import app, db, login_manager
from forms import LoginForm, RegistrationForm
from app.users.models import User

mod = Blueprint('users', __name__)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@mod.route('/login/', methods=('GET', 'POST'))
def login_view():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = form.get_user()
        login_user(user)
        flash("Logged in successfully.")
        return redirect(request.args.get("next") or url_for("index"))
    return render_template('users/login.html', form=form)

@mod.route('/register/', methods=('GET', 'POST'))
def register_view():
    form = RegistrationForm(request.form)
    if form.validate_on_submit():
        user = User()
        form.populate_obj(user)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('users/register.html', form=form)

@login_required
@mod.route('/logout/')
def logout_view():
    logout_user()
    return redirect(url_for('index'))
########NEW FILE########
__FILENAME__ = config
import os

_basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfiguration(object):
    DEBUG = False
    TESTING = False

    ADMINS = frozenset(['youremail@yourdomain.com'])
    SECRET_KEY = 'SecretKeyForSessionSigning'

    THREADS_PER_PAGE = 8

    CSRF_ENABLED = True
    CSRF_SESSION_KEY = "somethingimpossibletoguess"

    RECAPTCHA_USE_SSL = False
    RECAPTCHA_PUBLIC_KEY = 'blahblahblahblahblahblahblahblahblah'
    RECAPTCHA_PRIVATE_KEY = 'blahblahblahblahblahblahprivate'
    RECAPTCHA_OPTIONS = {'theme': 'white'}

    DATABASE = 'app.db'

    DATABASE_PATH = os.path.join(_basedir, DATABASE)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DATABASE_PATH


class TestConfiguration(BaseConfiguration):
    TESTING = True

    CSRF_ENABLED = False

    DATABASE = 'tests.db'
    DATABASE_PATH = os.path.join(_basedir, DATABASE)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # + DATABASE_PATH


class DebugConfiguration(BaseConfiguration):
    DEBUG = True

########NEW FILE########
__FILENAME__ = run
from app import app
app.run(debug=True)

########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python
import os
import readline
from pprint import pprint

from flask import *
from app import *

os.environ['PYTHONINSPECT'] = 'True'

########NEW FILE########
