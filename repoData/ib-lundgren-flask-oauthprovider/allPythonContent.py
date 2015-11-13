__FILENAME__ = client
"""
A demonstrative OAuth client to use with our provider

This serves as a base, use hmac_client.py, rsa_client.py or
plaintext_client.py depending on which signature type you wish to test.
"""
import requests
from requests.auth import OAuth1
from flask import Flask, redirect, request, session
from urlparse import parse_qsl, urlparse

app = Flask(__name__)
# OBS!: Due to cookie saving issue on localhost client.local is used
# and must be setup in for example /etc/hosts
app.config.update(
    SECRET_KEY="not very secret",
    SERVER_NAME="client.local:5001"
)


@app.route("/start")
def start():
    client = OAuth1(app.config["CLIENT_KEY"],
        callback_uri=u"http://client.local:5001/callback",
        **app.config["OAUTH_CREDENTIALS"])

    r = requests.post(u"http://127.0.0.1:5000/request_token?realm=secret", auth=client)
    print r.content
    data = dict(parse_qsl(r.content))
    resource_owner = data.get(u'oauth_token')
    session["token_secret"] = data.get('oauth_token_secret').decode(u'utf-8')
    url = u"http://127.0.0.1:5000/authorize?oauth_token=" + resource_owner
    return redirect(url)


@app.route("/callback")
def callback():
    # Extract parameters from callback URL
    data = dict(parse_qsl(urlparse(request.url).query))
    resource_owner = data.get(u'oauth_token').decode(u'utf-8')
    verifier = data.get(u'oauth_verifier').decode(u'utf-8')
    token_secret = session["token_secret"]

    # Request the access token
    client = OAuth1(app.config["CLIENT_KEY"],
        resource_owner_key=resource_owner,
        resource_owner_secret=token_secret,
        verifier=verifier,
        **app.config["OAUTH_CREDENTIALS"])
    r = requests.post(u"http://127.0.0.1:5000/access_token", auth=client)

    # Extract the access token from the response
    data = dict(parse_qsl(r.content))
    resource_owner = data.get(u'oauth_token').decode(u'utf-8')
    resource_owner_secret = data.get(u'oauth_token_secret').decode(u'utf-8')
    client = OAuth1(app.config["CLIENT_KEY"],
        resource_owner_key=resource_owner,
        resource_owner_secret=resource_owner_secret,
        **app.config["OAUTH_CREDENTIALS"])
    r = requests.get(u"http://127.0.0.1:5000/protected", auth=client)
    r = requests.get(u"http://127.0.0.1:5000/protected_realm", auth=client)
    return r.content

########NEW FILE########
__FILENAME__ = login
# -*- coding: utf-8 -*-
from demoprovider import app
from models import ResourceOwner as User
from models import db_session
from flask import g, session, render_template, request, redirect, flash
from flask import abort, url_for
from flaskext.openid import OpenID

# setup flask-openid
oid = OpenID(app)


@app.before_request
def before_request():
    g.user = None
    if 'openid' in session:
        g.user = User.query.filter_by(openid=session['openid']).first()


@app.after_request
def after_request(response):
    db_session.remove()
    return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    """Does the login via OpenID.  Has to call into `oid.try_login`
    to start the OpenID machinery.
    """
    # if we are already logged in, go back to were we came from
    if g.user is not None:
        return redirect(oid.get_next_url())
    if request.method == 'POST':
        openid = request.form.get('openid')
        if openid:
            return oid.try_login(openid, ask_for=['email', 'fullname',
                                                  'nickname'])
    return render_template('login.html', next=oid.get_next_url(),
                           error=oid.fetch_error())


@oid.after_login
def create_or_login(resp):
    """This is called when login with OpenID succeeded and it's not
    necessary to figure out if this is the users's first login or not.
    This function has to redirect otherwise the user will be presented
    with a terrible URL which we certainly don't want.
    """
    session['openid'] = resp.identity_url
    user = User.query.filter_by(openid=resp.identity_url).first()
    if user is not None:
        flash(u'Successfully signed in')
        g.user = user
        return redirect(oid.get_next_url())
    return redirect(url_for('create_profile', next=oid.get_next_url(),
                            name=resp.fullname or resp.nickname,
                            email=resp.email))


@app.route('/create-profile', methods=['GET', 'POST'])
def create_profile():
    """If this is the user's first login, the create_or_login function
    will redirect here so that the user can set up his profile.
    """
    if g.user is not None or 'openid' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        if not name:
            flash(u'Error: you have to provide a name')
        elif '@' not in email:
            flash(u'Error: you have to enter a valid email address')
        else:
            flash(u'Profile successfully created')
            db_session.add(User(name, email, session['openid']))
            db_session.commit()
            return redirect(oid.get_next_url())
    return render_template('create_profile.html', next_url=oid.get_next_url())


@app.route('/profile', methods=['GET', 'POST'])
def edit_profile():
    """Updates a profile"""
    if g.user is None:
        abort(401)
    form = dict(name=g.user.name, email=g.user.email)
    if request.method == 'POST':
        if 'delete' in request.form:
            db_session.delete(g.user)
            db_session.commit()
            session['openid'] = None
            flash(u'Profile deleted')
            return redirect(url_for('index'))
        form['name'] = request.form['name']
        form['email'] = request.form['email']
        if not form['name']:
            flash(u'Error: you have to provide a name')
        elif '@' not in form['email']:
            flash(u'Error: you have to enter a valid email address')
        else:
            flash(u'Profile successfully created')
            g.user.name = form['name']
            g.user.email = form['email']
            db_session.commit()
            return redirect(url_for('edit_profile'))
    return render_template('edit_profile.html', form=form)


@app.route('/logout')
def logout():
    session.pop('openid', None)
    flash(u'You have been signed out')
    return redirect(oid.get_next_url())

########NEW FILE########
__FILENAME__ = models
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine("sqlite:///flask-oauthprovider.db")
db_session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    Base.metadata.create_all(bind=engine)


class ResourceOwner(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    openid = Column(String)

    request_tokens = relationship("RequestToken", order_by="RequestToken.id")
    access_tokens = relationship("AccessToken", order_by="AccessToken.id")
    clients = relationship("Client", order_by="Client.id")

    def __init__(self, name, email, openid):
        self.name = name
        self.email = email
        self.openid = openid

    def __repr__(self):
        return "<ResourceOwner (%s, %s)>" % (self.name, self.email)


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    client_key = Column(String)
    name = Column(String)
    description = Column(String)
    secret = Column(String)
    pubkey = Column(String)

    request_tokens = relationship("RequestToken", order_by="RequestToken.id")
    access_tokens = relationship("AccessToken", order_by="AccessToken.id")
    callbacks = relationship("Callback", order_by="Callback.id")

    resource_owner_id = Column(Integer, ForeignKey("users.id"))
    resource_owner = relationship("ResourceOwner", order_by=id)

    def __init__(self, client_key, name, description, secret=None, pubkey=None):
        self.client_key = client_key
        self.name = name
        self.description = description
        self.secret = secret
        self.pubkey = pubkey

    def __repr__(self):
        return "<Client (%s, %s)>" % (self.name, self.id)


class Callback(Base):
    __tablename__ = "callbacks"

    id = Column(Integer, primary_key=True)
    callback = Column(String)

    client_id = Column(Integer, ForeignKey("clients.id"))
    client = relationship("Client", order_by=id)

    def __init__(self, callback):
        self.callback = callback

    def __repr__(self):
        return "<Callback (%s, %s)>" % (self.callback, self.client)


class Nonce(Base):
    __tablename__ = "nonces"

    id = Column(Integer, primary_key=True)
    nonce = Column(String)
    timestamp = Column(Integer)

    # TODO: TTL
    client_id = Column(Integer, ForeignKey("clients.id"))
    client = relationship("Client", backref=backref("nonces", order_by=id))

    request_token_id = Column(Integer, ForeignKey("requestTokens.id"))
    request_token = relationship("RequestToken", backref=backref("nonces", order_by=id))

    access_token_id = Column(Integer, ForeignKey("accessTokens.id"))
    access_token = relationship("AccessToken", backref=backref("nonces", order_by=id))

    def __init__(self, nonce, timestamp):
        self.nonce = nonce
        self.timestamp = timestamp

    def __repr__(self):
        return "<Nonce (%s, %s, %s, %s)>" % (self.nonce, self.timestamp, self.client, self.resource_owner)


class RequestToken(Base):
    __tablename__ = "requestTokens"

    id = Column(Integer, primary_key=True)
    token = Column(String)
    verifier = Column(String)
    realm = Column(String)
    secret = Column(String)
    callback = Column(String)

    # TODO: TTL
    client_id = Column(Integer, ForeignKey("clients.id"))
    client = relationship("Client", backref=backref("requestTokens", order_by=id))

    resource_owner_id = Column(Integer, ForeignKey("users.id"))
    resource_owner = relationship("ResourceOwner", order_by=id)

    def __init__(self, token, callback, secret=None, verifier=None, realm=None):
        self.token = token
        self.secret = secret
        self.verifier = verifier
        self.realm = realm
        self.callback = callback

    def __repr__(self):
        return "<RequestToken (%s, %s, %s)>" % (self.token, self.client, self.resource_owner)


class AccessToken(Base):
    __tablename__ = "accessTokens"

    id = Column(Integer, primary_key=True)
    token = Column(String)
    realm = Column(String)
    secret = Column(String)

    # TODO: TTL
    client_id = Column(Integer, ForeignKey("clients.id"))
    client = relationship("Client", order_by=id)

    resource_owner_id = Column(Integer, ForeignKey("users.id"))
    resource_owner = relationship("ResourceOwner", order_by=id)

    def __init__(self, token, secret=None, verifier=None, realm=None):
        self.token = token
        self.secret = secret
        self.verifier = verifier
        self.realm = realm

    def __repr__(self):
        return "<AccessToken (%s, %s, %s)>" % (self.token, self.client, self.resource_owner)

########NEW FILE########
__FILENAME__ = provider
from flask import request, render_template, g
from flask.ext.oauthprovider import OAuthProvider
from sqlalchemy.orm.exc import NoResultFound
from models import ResourceOwner, Client, Nonce, Callback
from models import RequestToken, AccessToken, db_session
from utils import require_openid


class ExampleProvider(OAuthProvider):

    @property
    def enforce_ssl(self):
        return False

    @property
    def realms(self):
        return [u"secret", u"trolling"]

    @require_openid
    def authorize(self):
        if request.method == u"POST":
            token = request.form.get("oauth_token")
            return self.authorized(token)
        else:
            # TODO: Authenticate client
            token = request.args.get(u"oauth_token")
            return render_template(u"authorize.html", token=token)

    @require_openid
    def register(self):
        if request.method == u'POST':
            client_key = self.generate_client_key()
            secret = self.generate_client_secret()
            # TODO: input sanitisation?
            name = request.form.get(u"name")
            description = request.form.get(u"description")
            callback = request.form.get(u"callback")
            pubkey = request.form.get(u"pubkey")
            # TODO: redirect?
            # TODO: pubkey upload
            # TODO: csrf
            info = {
                u"client_key": client_key,
                u"name": name,
                u"description": description,
                u"secret": secret,
                u"pubkey": pubkey
            }
            client = Client(**info)
            client.callbacks.append(Callback(callback))
            client.resource_owner = g.user
            db_session.add(client)
            db_session.commit()
            return render_template(u"client.html", **info)
        else:
            clients = g.user.clients
            return render_template(u"register.html", clients=clients)

    def validate_timestamp_and_nonce(self, client_key, timestamp, nonce,
            request_token=None, access_token=None):
        filters = [
            Nonce.nonce == nonce,
            Nonce.timestamp == timestamp,
            Client.id == Nonce.client_id,
            Client.client_key == client_key
        ]
        if request_token:
            filters.extend([
                RequestToken.id == Nonce.request_token_id,
                RequestToken.token == request_token
            ])
        if access_token:
            filters.extend([
                AccessToken.id == Nonce.access_token_id,
                AccessToken.token == access_token
            ])
        try:
            db_session.query(Nonce, Client, ResourceOwner).filter(*filters).one()
            return False
        except NoResultFound:
            return True

    def validate_redirect_uri(self, client_key, redirect_uri=None):
        try:
            client = Client.query.filter_by(client_key=client_key).one()
            if redirect_uri in (x.callback for x in client.callbacks):
                return True

            elif len(client.callbacks) == 1 and redirect_uri is None:
                return True

            else:
                return False

        except NoResultFound:
            return False

    def validate_client_key(self, client_key):
        try:
            Client.query.filter_by(client_key=client_key).one()
            return True

        except NoResultFound:
            return False

    def validate_requested_realm(self, client_key, realm):
        return True

    def validate_realm(self, client_key, access_token, uri=None, required_realm=None):

        if not required_realm:
            return True

        # insert other check, ie on uri here

        try:
            token = db_session.query(AccessToken, Client).filter(
                    Client.client_key == client_key,
                    AccessToken.token == access_token).one().AccessToken
            return token.realm in required_realm

        except NoResultFound:
            return False

    @property
    def dummy_client(self):
        return u'dummy_client'

    @property
    def dummy_resource_owner(self):
        return u'dummy_resource_owner'

    def validate_request_token(self, client_key, resource_owner_key):
        # TODO: make client_key optional
        if client_key:
            db_session.query(RequestToken, Client).filter(
                RequestToken.token == resource_owner_key,
                Client.client_key == client_key).one()
        else:
            RequestToken.query.filter_by(token=resource_owner_key).one()
        try:
            return True

        except NoResultFound:
            return False

    def validate_access_token(self, client_key, resource_owner_key):
        try:
            db_session.query(AccessToken, Client).filter(
                Client.client_key == client_key,
                Client.id == AccessToken.client_id,
                AccessToken.token == resource_owner_key
            ).one()
            return True

        except NoResultFound:
            return False

    def validate_verifier(self, client_key, resource_owner_key, verifier):
        try:
            db_session.query(RequestToken, Client).filter(
                Client.client_key == client_key,
                RequestToken.token == resource_owner_key,
                RequestToken.verifier == verifier
            ).one()
            return True
        except NoResultFound:
            return False

    def get_callback(self, request_token):
        return RequestToken.query.filter_by(token=request_token).one().callback

    def get_realm(self, client_key, request_token):
        return db_session.query(RequestToken, Client).filter(
                    Client.client_key == client_key,
                    RequestToken.token == request_token
        ).one().RequestToken.realm

    def get_client_secret(self, client_key):
        try:
            return Client.query.filter_by(client_key=client_key).one().secret

        except NoResultFound:
            return None

    def get_rsa_key(self, client_key):
        try:
            return Client.query.filter_by(client_key=client_key).one().pubkey

        except NoResultFound:
            return None

    def get_request_token_secret(self, client_key, resource_owner_key):
        try:
            query = db_session.query(RequestToken, Client).filter(
                RequestToken.token == resource_owner_key,
                Client.client_key == client_key
            ).one()
            return query.RequestToken.secret

        except NoResultFound:
            return None

    def get_access_token_secret(self, client_key, resource_owner_key):
        try:
            query = db_session.query(AccessToken, Client).filter(
                AccessToken.token == resource_owner_key,
                Client.client_key == client_key
            ).one()
            return query.AccessToken.secret

        except NoResultFound:
            return None

    def save_request_token(self, client_key, request_token, callback,
            realm=None, secret=None):
        token = RequestToken(request_token, callback, secret=secret, realm=realm)
        token.client = Client.query.filter_by(client_key=client_key).one()
        db_session.add(token)
        db_session.commit()

    def save_access_token(self, client_key, access_token, request_token,
            realm=None, secret=None):
        token = AccessToken(access_token, secret=secret, realm=realm)
        token.client = Client.query.filter_by(client_key=client_key).one()
        req_token = RequestToken.query.filter_by(token=request_token).one()
        token.resource_owner = req_token.resource_owner
        token.realm = req_token.realm
        db_session.add(token)
        db_session.commit()

    def save_timestamp_and_nonce(self, client_key, timestamp, nonce,
            request_token=None, access_token=None):
        nonce = Nonce(nonce, timestamp)
        nonce.client = Client.query.filter_by(client_key=client_key).one()

        if request_token:
            nonce.token = RequestToken.query.filter_by(token=request_token).one()

        if access_token:
            nonce.token = AccessToken.query.filter_by(token=access_token).one()

        db_session.add(nonce)
        db_session.commit()

    def save_verifier(self, request_token, verifier):
        token = RequestToken.query.filter_by(token=request_token).one()
        token.verifier = verifier
        token.resource_owner = g.user
        db_session.add(token)
        db_session.commit()

########NEW FILE########
__FILENAME__ = utils
from functools import wraps
from flask import g, url_for, request, redirect


def require_openid(f):
    """Require user to be logged in."""
    @wraps(f)
    def decorator(*args, **kwargs):
        if g.user is None:
            next_url = url_for("login") + "?next=" + request.url
            return redirect(next_url)
        else:
            return f(*args, **kwargs)
    return decorator

########NEW FILE########
__FILENAME__ = hmac_client
from client import app
app.config["OAUTH_CREDENTIALS"] = {
    u"client_secret": u"WgzyivpCPl7WuaxuSBoCCPv5UP9iBV"
}
app.config["CLIENT_KEY"] = u"06NvHxcvImyIBiXPFsQA6GWJXjC8UU"
app.run(debug=True, port=5001)

########NEW FILE########
__FILENAME__ = init_db
from demoprovider.models import init_db
init_db()

########NEW FILE########
__FILENAME__ = login
# -*- coding: utf-8 -*-
from mongo_demoprovider import app
from models import ResourceOwner as User
from flask import g, session, render_template, request, redirect, flash
from flask import abort, url_for
from flask.ext.openid import OpenID

# setup flask-openid
oid = OpenID(app)


@app.before_request
def before_request():
    g.user = None
    if 'openid' in session:
        user_dict = User.find_one({'openid':session['openid']})
        
        if user_dict:
            g.user = User()
            g.user.update(user_dict)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    """Does the login via OpenID.  Has to call into `oid.try_login`
    to start the OpenID machinery.
    """
    # if we are already logged in, go back to were we came from
    if g.user is not None:
        return redirect(oid.get_next_url())
    if request.method == 'POST':
        openid = request.form.get('openid')
        if openid:
            return oid.try_login(openid, ask_for=['email', 'fullname',
                                                  'nickname'])
    return render_template('login.html', next=oid.get_next_url(),
                           error=oid.fetch_error())


@oid.after_login
def create_or_login(resp):
    """This is called when login with OpenID succeeded and it's not
    necessary to figure out if this is the users's first login or not.
    This function has to redirect otherwise the user will be presented
    with a terrible URL which we certainly don't want.
    """
    session['openid'] = resp.identity_url
    user = User.get_collection().find_one({'openid':resp.identity_url})
    if user is not None:
        flash(u'Successfully signed in')
        g.user = user
        return redirect(oid.get_next_url())
    return redirect(url_for('create_profile', next=oid.get_next_url(),
                            name=resp.fullname or resp.nickname,
                            email=resp.email))


@app.route('/create-profile', methods=['GET', 'POST'])
def create_profile():
    """If this is the user's first login, the create_or_login function
    will redirect here so that the user can set up his profile.
    """
    if g.user is not None or 'openid' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        if not name:
            flash(u'Error: you have to provide a name')
        elif '@' not in email:
            flash(u'Error: you have to enter a valid email address')
        else:
            flash(u'Profile successfully created')
            User.get_collection().insert(User(name, email, session['openid']))
            return redirect(oid.get_next_url())
    return render_template('create_profile.html', next_url=oid.get_next_url())


@app.route('/profile', methods=['GET', 'POST'])
def edit_profile():
    """Updates a profile"""
    if g.user is None:
        abort(401)
    form = dict(name=g.user.name, email=g.user.email)
    if request.method == 'POST':
        if 'delete' in request.form:
            User.get_collection().remove(g.user)
            session['openid'] = None
            flash(u'Profile deleted')
            return redirect(url_for('index'))
        form['name'] = request.form['name']
        form['email'] = request.form['email']
        if not form['name']:
            flash(u'Error: you have to provide a name')
        elif '@' not in form['email']:
            flash(u'Error: you have to enter a valid email address')
        else:
            flash(u'Profile successfully created')
            g.user.name = form['name']
            g.user.email = form['email']
            uid = User.get_collection().save(g.user)
            return redirect(url_for('edit_profile'))
    return render_template('edit_profile.html', form=form)


@app.route('/logout')
def logout():
    session.pop('openid', None)
    flash(u'You have been signed out')
    return redirect(oid.get_next_url())

########NEW FILE########
__FILENAME__ = models
import pymongo


def get_connection():
    return pymongo.MongoClient().demo_oauth_provider


class Model(dict):
    @classmethod
    def get_collection(cls):
        conn = get_connection()
        return conn[cls.table]
        
    @classmethod
    def find_one(cls, attrs):
        return cls.get_collection().find_one(attrs)
    
    @classmethod
    def insert(cls, obj):
        return cls.get_collection().insert(obj)
        
    @classmethod
    def save(cls, obj):
        return cls.get_collection().save(obj)

    def __getattr__(self, attr):
        return self[attr]
        
    def __setattr__(self, attr, value):
        self[attr] = value
    
    

class ResourceOwner(Model):
    table = "users"

    def __init__(self, name="", email="", openid=""):
        self.name = name
        self.email = email
        self.openid = openid
        self.request_tokens = []
        self.access_tokens = []
        self.client_ids = []

    def __repr__(self):
        return "<ResourceOwner (%s, %s)>" % (self.name, self.email)


class Client(Model):
    table = "clients"

    def __init__(self, client_key, name, description, secret=None, pubkey=None):
        self.client_key = client_key
        self.name = name
        self.description = description
        self.secret = secret
        self.pubkey = pubkey
        self.request_tokens = []
        self.access_tokens = []
        self.callbacks = []
        self.resource_owner_id = ""

    def __repr__(self):
        return "<Client (%s, %s)>" % (self.name, self.id)


class Nonce(Model):
    table = "nonces"

    def __init__(self, nonce, timestamp):
        self.nonce = nonce
        self.timestamp = timestamp
        self.client_id = ""
        self.request_token_id = ""
        self.access_token_id = ""

    def __repr__(self):
        return "<Nonce (%s, %s, %s, %s)>" % (self.nonce, self.timestamp, self.client, self.resource_owner)


class RequestToken(Model):
    table = "requestTokens"

    def __init__(self, token, callback, secret=None, verifier=None, realm=None):
        self.token = token
        self.secret = secret
        self.verifier = verifier
        self.realm = realm
        self.callback = callback
        self.client_id = ""
        self.resource_owner_id = ""
        

    def __repr__(self):
        return "<RequestToken (%s, %s, %s)>" % (self.token, self.client, self.resource_owner)


class AccessToken(Model):
    table = "accessTokens"

    def __init__(self, token, secret=None, verifier=None, realm=None):
        self.token = token
        self.secret = secret
        self.verifier = verifier
        self.realm = realm
        self.client_id = ""
        self.resource_owner_id = ""

    def __repr__(self):
        return "<AccessToken (%s, %s, %s)>" % (self.token, self.client, self.resource_owner)

########NEW FILE########
__FILENAME__ = provider
from flask import request, render_template, g
from flask.ext.oauthprovider import OAuthProvider
from bson.objectid import ObjectId
from models import ResourceOwner as User, Client, Nonce
from models import RequestToken, AccessToken
from utils import require_openid


class ExampleProvider(OAuthProvider):

    @property
    def enforce_ssl(self):
        return False

    @property
    def realms(self):
        return [u"secret", u"trolling"]
        
    @property
    def nonce_length(self):
        return 20, 40

    @require_openid
    def authorize(self):
        if request.method == u"POST":
            token = request.form.get("oauth_token")
            return self.authorized(token)
        else:
            # TODO: Authenticate client
            token = request.args.get(u"oauth_token")
            return render_template(u"authorize.html", token=token)

    @require_openid
    def register(self):
        if request.method == u'POST':
            client_key = self.generate_client_key()
            secret = self.generate_client_secret()
            # TODO: input sanitisation?
            name = request.form.get(u"name")
            description = request.form.get(u"description")
            callback = request.form.get(u"callback")
            pubkey = request.form.get(u"pubkey")
            # TODO: redirect?
            # TODO: pubkey upload
            # TODO: csrf
            info = {
                u"client_key": client_key,
                u"name": name,
                u"description": description,
                u"secret": secret,
                u"pubkey": pubkey
            }
            client = Client(**info)
            client['callbacks'].append(callback)
            client['resource_owner_id'] = g.user['_id']
            client_id = Client.insert(client)
            g.user.client_ids.append(client_id)
            User.get_collection().save(g.user)
            return render_template(u"client.html", **info)
        else:
            clients = Client.get_collection().find({'_id': {'$in': 
                [ObjectId(oid) for oid in g.user.client_ids]}})
            return render_template(u"register.html", clients=clients)
            
    
    def validate_timestamp_and_nonce(self, client_key, timestamp, nonce,
            request_token=None, access_token=None):
        
        token = True
        req_token = True
        client = Client.find_one({'client_key':client_key})
        
        if client:
            nonce = Nonce.find_one({'nonce':nonce, 'timestamp':timestamp,
                'client_id':client['_id']})
            
            if nonce:
                if request_token:
                    req_token = RequestToken.find_one(
                        {'_id':nonce['request_token_id'], 'token':request_token})
                    
                if access_token:
                    token = RequestToken.find_one(
                        {'_id':nonce['request_token_id'], 'token':access_token})
                
        return token and req_token and nonce != None

    def validate_redirect_uri(self, client_key, redirect_uri=None):
        client = Client.find_one({'client_key':client_key})
        
        return client != None and (
            len(client['callbacks']) == 1 and redirect_uri is None
            or redirect_uri in (x for x in client['callbacks']))
        
        
    def validate_client_key(self, client_key):
        return (
            Client.find_one({'client_key':client_key}) != None)
        

    def validate_requested_realm(self, client_key, realm):
        return True


    def validate_realm(self, client_key, access_token, uri=None, required_realm=None):

        if not required_realm:
            return True

        # insert other check, ie on uri here

        client = Client.find_one({'client_key':client_key})
        
        if client:
            token = AccessToken.find_one(
                {'token':access_token, 'client_id': client['_id']})
            
            if token:
                return token['realm'] in required_realm
        
        return False

    @property
    def dummy_client(self):
        return u'dummy_client'

    @property
    def dummy_resource_owner(self):
        return u'dummy_resource_owner'

    def validate_request_token(self, client_key, resource_owner_key):
        # TODO: make client_key optional
        token = None
        
        if client_key:
            client = Client.find_one({'client_key':client_key})
        
            if client:
                token = RequestToken.find_one(
                    {'token':access_token, 'client_id': client['_id']})
            
        else:
            token = RequestToken.find_one(
                    {'token':resource_owner_key})
        
        return token != None


    def validate_access_token(self, client_key, resource_owner_key):

        token = None
        client = Client.find_one({'client_key':client_key})
    
        if client:
            token = AccessToken.find_one(
                {'token':resource_owner_key, 'client_id': client['_id']})
        
        return token != None
        

    def validate_verifier(self, client_key, resource_owner_key, verifier):
        token = None
        client = Client.find_one({'client_key':client_key})
    
        if client:
            token = RequestToken.find_one(
                {'token':resource_owner_key,
                 'client_id': client['_id'], 
                 'verifier':verifier})
        
        return token != None
        
        
    def get_callback(self, request_token):
        token = RequestToken.find_one(
                {'token':request_token})
                
        if token:
            return token.get('callback')
        else:
            return None


    def get_realm(self, client_key, request_token):
        client = Client.find_one({'client_key':client_key})
        
        if client:
            token = RequestToken.find_one(
                {'token':request_token, 'client_id': client['_id']})
            
            if token:
                return token.get('realm')
                
        return None
        

    def get_client_secret(self, client_key):
            client = Client.find_one({'client_key':client_key})
            
            if client:
                return client.get('secret')
            else:
                return None


    def get_rsa_key(self, client_key):
            client = Client.find_one({'client_key':client_key})
            
            if client:
                return client.get('pubkey')
            else:
                return None

    def get_request_token_secret(self, client_key, resource_owner_key):
        client = Client.find_one({'client_key':client_key})
    
        if client:
            token = RequestToken.find_one(
                {'token':resource_owner_key,
                 'client_id': client['_id']})
                 
            if token:
                return token.get('secret')
                     
        return None
        

    def get_access_token_secret(self, client_key, resource_owner_key):
        client = Client.find_one({'client_key':client_key})
    
        if client:
            token = AccessToken.find_one(
                {'token':resource_owner_key,
                 'client_id': client['_id']})
                 
            if token:
                return token.get('secret')
                     
        return None

    def save_request_token(self, client_key, request_token, callback,
            realm=None, secret=None):
        client = Client.find_one({'client_key':client_key})
        
        if client:
            token = RequestToken(
                request_token, callback, secret=secret, realm=realm)
            token.client_id = client['_id']
        
            RequestToken.insert(token)

    def save_access_token(self, client_key, access_token, request_token,
            realm=None, secret=None):
        client = Client.find_one({'client_key':client_key})
        
        if client:
            token = AccessToken(access_token, secret=secret, realm=realm)
            token.client_id = client['_id']
            
            req_token = RequestToken.find_one({'token':request_token})
            
            if req_token:
                token['resource_owner_id'] = req_token['resource_owner_id']
                token['realm'] = req_token['realm']
            
                AccessToken.insert(token)

    def save_timestamp_and_nonce(self, client_key, timestamp, nonce,
            request_token=None, access_token=None):
        
        client = Client.find_one({'client_key':client_key})
        
        if client:
            nonce = Nonce(nonce, timestamp)
            nonce.client_id = client['_id']

            if request_token:
                req_token = RequestToken.find_one({'token':request_token})
                nonce.request_token_id = req_token['_id']

            if access_token:
                token = AccessToken.find_one({'token':access_token})
                nonce.access_token_id = token['_id']

            Nonce.insert(nonce)

    def save_verifier(self, request_token, verifier):
        token = RequestToken.find_one({'token':request_token})
        token['verifier'] = verifier
        token['resource_owner_id'] = g.user['_id']
        RequestToken.get_collection().save(token)

########NEW FILE########
__FILENAME__ = utils
from functools import wraps
from flask import g, url_for, request, redirect


def require_openid(f):
    """Require user to be logged in."""
    @wraps(f)
    def decorator(*args, **kwargs):
        if g.user is None:
            next_url = url_for("login") + "?next=" + request.url
            return redirect(next_url)
        else:
            return f(*args, **kwargs)
    return decorator

########NEW FILE########
__FILENAME__ = plaintext_client
from client import app
app.config["OAUTH_CREDENTIALS"] = {
    u"client_secret": u"WgzyivpCPl7WuaxuSBoCCPv5UP9iBV",
    u"signature_method": u"PLAINTEXT"
}
app.config["CLIENT_KEY"] = u"06NvHxcvImyIBiXPFsQA6GWJXjC8UU"
app.run(debug=True, port=5001)

########NEW FILE########
__FILENAME__ = rsa_client
from os.path import join, dirname
from client import app


def fread(fn):
    with open(join(dirname(__file__), fn), 'r') as f:
        return f.read().decode("utf-8")

app.config["OAUTH_CREDENTIALS"] = {
    u"rsa_key": fread("mykey.pem"),
    u"signature_method": u"RSA-SHA1",
    "signature_type": "body"
}
app.config["CLIENT_KEY"] = u"5kCCg9t3amq636IsP6PcDGwdJhgdRG"
app.run(debug=True, port=5001)

########NEW FILE########
__FILENAME__ = runserver
from demoprovider import app
app.run(debug=True)

########NEW FILE########
__FILENAME__ = runserver_mongo
from mongo_demoprovider import app
app.run(debug=True)

########NEW FILE########
__FILENAME__ = flask_oauthprovider
# -*- coding: utf-8 -*-
from oauthlib.oauth1.rfc5849 import Server
from oauthlib.oauth1.rfc5849.signature import collect_parameters
from oauthlib.common import add_params_to_uri, encode_params_utf8
from oauthlib.common import generate_token, urlencode
from flask import Response, request, redirect
from werkzeug.exceptions import Unauthorized, BadRequest
from functools import wraps
from urlparse import urlparse


class OAuthProvider(Server):
    """Provide secure services using OAuth 1 RFC 5849.

    OAuthProvider is based on the secure and highly configurable Server
    base class of oauthlib.oauth.rfc5849 for OAuth 1 providers. This flask
    extension adds a number of convenience methods to act as helpers and a base.

    A number of additional methods that will need to be implemented are added
    and documented as to how they fit into the whole OAuth workflow. Detailed
    descriptions of these methods are provided in respective method __doc__.

    Providers will have to implement the following methods:

    * register(self)
    * save_timestamp_and_nonce(self, client_key, timestamp, nonce,
            request_token=None, access_token=None
    * authorize(self)
    * get_callback(self, request_token)
    * save_request_token(self, client_key, request_token, callback, realm=None,
            secret=None)
    * save_verifier(self, client_key, request_token, verifier)
    * save_access_token(self, client_key, request_token, realm=None,
            secret=None)

    Furthermore 4 default URLs are automatically routed using these properties:

    * request_token_url
    * access_token_url
    * register_url
    * authorize_url

    Request tokens and access tokens will automatically be generated and
    returned to clients. They will be saved using the abstract methods outlined
    earlier.

    A successful provider implementation will enable views to be easily and
    securely protected. Providers will also enjoy fine-grained control over
    which clients can access which resources through the use of realms.

    Follows are two view functions, the first under the default non-specified
    realm and the second under the photos realm.

    @app.route("/status_feed")
    @provider.require_oauth()
    def status_feed(self):
        ...

    @app.route("/photos")
    @provider.require_oauth(realm="photos")
    def photos(self):
        ...

    """

    # Properties used to configure the application, can safely be overloaded

    @property
    def request_token_url(self):
        return u'/request_token'

    @property
    def access_token_url(self):
        return u'/access_token'

    @property
    def register_url(self):
        return u'/register'

    @property
    def authorize_url(self):
        return u'/authorize'

    @property
    def secret_length(self):
        return 30

    # Methods that must be overloaded

    def register(self):
        """Client registration.

        Defaults to /register URL.

        A few common actions during client registration includes:

        * Ask the client for an application name and description
        * Ask the client for one or several callback URIs
        * Allow the client to upload a public RSA key if the RSA signature
          method is supported.

        Upon registration each client must be provided with a client key. If
        the HMAC signature method is used a client secret should also be
        be provided.

        For your convenience the following methods are provided:

        * generate_client_key(self) for the client/consumer key
        * generate_client_secret(self) for the client/consumer secret
        """
        raise NotImplementedError("Must be implemented by inheriting classes")

    def save_timestamp_and_nonce(self, client_key, timestamp, nonce,
            request_token=None, access_token=None):
        """All timestamp and nonces must be stored.

        It is recommended that they are also connected to at least the client
        but preferably also the resource owner/user.
        """
        raise NotImplementedError("Must be implemented by inheriting classes")

    def authorize(self):
        """Ask the user to authorize access to the client.

        Defaults to /authorize URL. Invoked by user (redirected by the client).

        This view should only be accessible by authenticated users, redirect
        unauthenticated users to a login.

        Authorization is commonly done through a form asking the user to
        grant or deny access. This form should also include information that
        help the user identify which client it is authorizing access to.
        Usually by displaying application name and description.

        To the authorization URL the client will append the oauth_token parameter
        which corresponds to the previously obtained request token. This token
        should be validated using self.validate_request_token method.

        The request token should be securely kept, preferably in an encrypted
        HTTPOnly secure cookie during form submission as it will be needed to
        complete the authorization.

        Upon user authorization you should use the authorized method to easily
        generate and return a verifier code to the client.

        def authorize(self):
            ...
            return authorized(request_token)

        If the user denied access or if the request token was invalid it is
        important to not redirect the user back to the client.
        """
        raise NotImplementedError("Must be implemented by inheriting classes")


    def get_callback(self, request_token):
        """Return the callback associated with the request token."""
        raise NotImplementedError("Must be implemented by inheriting classes")

    def save_request_token(self, client_key, request_token, callback, realm=None,
            secret=None):
        """Store request tokens.

        This method is invoked by the request_token view and all you need to do
        is to store the token and its associated realm and token secret.
        """
        raise NotImplementedError("Must be implemented by inheriting classes")

    def save_verifier(self, request_token, verifier):
        """Store verifier and user associated with a specific request token.

        This method is invoked automatically by authorized.

        It is VITAL that you relate the user who authorized access with this
        verifier and request token or else you will be unable to provide
        access to the correct resources later.

        Since invocation of this method originates from the user accessing
        the authorize view you should be able to extract their ID easily from
        the request object.
        """
        raise NotImplementedError("Must be implemented by inheriting classes")

    def save_access_token(self, client_key, access_token, request_token,
            secret=None):
        """Store access tokens.

        This method is invoked by the access_token view and there are two
        tasks you will need to carry out in addition to storing the token:

        1. Retrieve the associated user and realm using request_token
        2. Associate the realm and user with the new access token
        """
        raise NotImplementedError("Must be implemented by inheriting classes")

    # There be dragons beyond this point, tread lightly.

    def __init__(self, app):
        """Setup routes and OAuth token methods."""
        self.request_token = self.require_oauth(require_resource_owner=False)(self.request_token)
        self.access_token = self.require_oauth(require_verifier=True)(self.access_token)
        if app is not None:
            self.app = app
            self.init_app(app)
        else:
            self.app = None

    def init_app(self, app):
        """Setup the 4 default routes."""
        app.add_url_rule(self.request_token_url, view_func=self.request_token,
                         methods=[u'POST'])
        app.add_url_rule(self.access_token_url, view_func=self.access_token,
                         methods=[u'POST'])
        app.add_url_rule(self.register_url, view_func=self.register,
                         methods=[u'GET', u'POST'])
        app.add_url_rule(self.authorize_url, view_func=self.authorize,
                         methods=[u'GET', u'POST'])

    def authorized(self, request_token):
        """Create a verifier for an user authorized client"""
        verifier = generate_token(length=self.verifier_length[1])
        self.save_verifier(request_token, verifier)
        response = [
            (u'oauth_token', request_token),
            (u'oauth_verifier', verifier)
        ]
        callback = self.get_callback(request_token)
        return redirect(add_params_to_uri(callback, response))

    def request_token(self):
        """Create an OAuth request token for a valid client request.

        Defaults to /request_token. Invoked by client applications.
        """
        client_key = request.oauth.client_key
        realm = request.oauth.realm
        # TODO: fallback on default realm?
        callback = request.oauth.callback_uri
        request_token = generate_token(length=self.request_token_length[1])
        token_secret = generate_token(length=self.secret_length)
        self.save_request_token(client_key, request_token, callback,
            realm=realm, secret=token_secret)
        return urlencode([(u'oauth_token', request_token),
                          (u'oauth_token_secret', token_secret),
                          (u'oauth_callback_confirmed', u'true')])

    def access_token(self):
        """Create an OAuth access token for an authorized client.

        Defaults to /access_token. Invoked by client applications.
        """
        access_token = generate_token(length=self.access_token_length[1])
        token_secret = generate_token(self.secret_length)
        client_key = request.oauth.client_key
        self.save_access_token(client_key, access_token,
            request.oauth.resource_owner_key, secret=token_secret)
        return urlencode([(u'oauth_token', access_token),
                          (u'oauth_token_secret', token_secret)])

    def generate_client_key(self):
        return generate_token(length=self.client_key_length[1])

    def generate_client_secret(self):
        return generate_token(length=self.secret_length)

    def require_oauth(self, realm=None, require_resource_owner=True,
            require_verifier=False, require_realm=False):
        """Mark the view function f as a protected resource"""

        def decorator(f):
            @wraps(f)
            def verify_request(*args, **kwargs):
                """Verify OAuth params before running view function f"""
                try:
                    if request.form:
                        body = request.form.to_dict()
                    else:
                        body = request.data.decode("utf-8")
                    verify_result = self.verify_request(request.url.decode("utf-8"),
                            http_method=request.method.decode("utf-8"),
                            body=body,
                            headers=request.headers,
                            require_resource_owner=require_resource_owner,
                            require_verifier=require_verifier,
                            require_realm=require_realm or bool(realm),
                            required_realm=realm)
                    valid, oauth_request = verify_result
                    if valid:
                        request.oauth = self.collect_request_parameters(request)

                        # Request tokens are only valid when a verifier is too
                        token = {}
                        if require_verifier:
                            token[u'request_token'] = request.oauth.resource_owner_key
                        else:
                            token[u'access_token'] = request.oauth.resource_owner_key

                        # All nonce/timestamp pairs must be stored to prevent
                        # replay attacks, they may be connected to a specific
                        # client and token to decrease collision probability.
                        self.save_timestamp_and_nonce(request.oauth.client_key,
                                request.oauth.timestamp, request.oauth.nonce,
                                **token)

                        # By this point, the request is fully authorized
                        return f(*args, **kwargs)
                    else:
                        # Unauthorized requests should not diclose their cause
                        raise Unauthorized()

                except ValueError as err:
                    # Caused by missing of or badly formatted parameters
                    raise BadRequest(err.message)

            return verify_request
        return decorator

    def collect_request_parameters(self, request):
        """Collect parameters in an object for convenient access"""

        class OAuthParameters(object):
            """Used as a parameter container since plain object()s can't"""
            pass

        # Collect parameters
        query = urlparse(request.url.decode("utf-8")).query
        content_type = request.headers.get('Content-Type', '')
        if request.form:
            body = request.form.to_dict()
        elif content_type == 'application/x-www-form-urlencoded':
            body = request.data.decode("utf-8")
        else:
            body = ''
        headers = dict(encode_params_utf8(request.headers.items()))
        params = dict(collect_parameters(uri_query=query, body=body, headers=headers))

        # Extract params and store for convenient and predictable access
        oauth_params = OAuthParameters()
        oauth_params.client_key = params.get(u'oauth_consumer_key')
        oauth_params.resource_owner_key = params.get(u'oauth_token', None)
        oauth_params.nonce = params.get(u'oauth_nonce')
        oauth_params.timestamp = params.get(u'oauth_timestamp')
        oauth_params.verifier = params.get(u'oauth_verifier', None)
        oauth_params.callback_uri = params.get(u'oauth_callback', None)
        oauth_params.realm = params.get(u'realm', None)
        return oauth_params

########NEW FILE########
