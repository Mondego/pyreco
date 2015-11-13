__FILENAME__ = document.config
import os

class BaseConfig(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY='SECRET_KEY_VALUE'

class ProductionConfig(BaseConfig):
    pass

class DevelopmentConfig(BaseConfig):
    DEBUG = True

class TestingConfig(BaseConfig):
    TESTING = True
    # Tests are simpler if CSRF protection is disabled
    WTF_CSRF_ENABLED = False

# data directories - should be on secure media
STORE_DIR='/var/www/securedrop/store'
GPG_KEY_DIR='/var/www/securedrop/keys'

# fingerprint of the GPG key to encrypt submissions to
JOURNALIST_KEY='APP_GPG_KEY_FINGERPRINT'

SOURCE_TEMPLATES_DIR='/var/www/securedrop/source_templates'
JOURNALIST_TEMPLATES_DIR='/var/www/securedrop/journalist_templates'
WORD_LIST='/var/www/securedrop/wordlist'
NOUNS='/var/www/securedrop/dictionaries/nouns.txt'
ADJECTIVES='/var/www/securedrop/dictionaries/adjectives.txt'
SCRYPT_ID_PEPPER='SCRYPT_ID_PEPPER_VALUE'
SCRYPT_GPG_PEPPER='SCRYPT_GPG_PEPPER_VALUE'
SCRYPT_PARAMS=dict(N=2**14, r=8, p=1)

# Default to the production configuration
FlaskConfig = ProductionConfig
SECUREDROP_ROOT=os.path.abspath('/var/www/securedrop') 

if os.environ.get('SECUREDROP_ENV') == 'test':
    FlaskConfig = TestingConfig
    TEST_DIR='/tmp/securedrop_test'
    STORE_DIR=os.path.join(TEST_DIR, 'store')
    GPG_KEY_DIR=os.path.join(TEST_DIR, 'keys')
    # test_journalist_key.pub
    JOURNALIST_KEY='65A1B5FF195B56353CC63DFFCC40EF1228271441'

# Database Configuration

# Default to using a sqlite database file for development
DATABASE_ENGINE = 'sqlite'
DATABASE_FILE=os.path.join(SECUREDROP_ROOT, 'db.sqlite')

# Uncomment to use mysql (or any other databaes backend supported by
# SQLAlchemy). Make sure you have the necessary dependencies installed, and run
# `python -c "import db; db.init_db()"` to initialize the database

#DATABASE_ENGINE = 'mysql'
#DATABASE_HOST = 'localhost'
#DATABASE_NAME = 'securedrop'
#DATABASE_USERNAME = 'document_mysql'
#DATABASE_PASSWORD = 'MYSQL_USER_PASS'

########NEW FILE########
__FILENAME__ = gen_secret_key
import os, base64

SECRET_KEY_NON=os.urandom(32)
SECRET_KEY=base64.b64encode(SECRET_KEY_NON)

print SECRET_KEY


########NEW FILE########
__FILENAME__ = source.config
import os

class BaseConfig(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY='SECRET_KEY_VALUE'

class ProductionConfig(BaseConfig):
    pass

class DevelopmentConfig(BaseConfig):
    DEBUG = True

class TestingConfig(BaseConfig):
    TESTING = True
    # Tests are simpler if CSRF protection is disabled
    WTF_CSRF_ENABLED = False

# data directories - should be on secure media
STORE_DIR='/var/www/securedrop/store'
GPG_KEY_DIR='/var/www/securedrop/keys'

# fingerprint of the GPG key to encrypt submissions to
JOURNALIST_KEY='APP_GPG_KEY_FINGERPRINT'

SOURCE_TEMPLATES_DIR='/var/www/securedrop/source_templates'
JOURNALIST_TEMPLATES_DIR='/var/www/securedrop/journalist_templates'
WORD_LIST='/var/www/securedrop/wordlist'

NOUNS='/var/www/securedrop/dictionaries/nouns.txt'
ADJECTIVES='/var/www/securedrop/dictionaries/adjectives.txt'
SCRYPT_ID_PEPPER='SCRYPT_ID_PEPPER_VALUE'
SCRYPT_GPG_PEPPER='SCRYPT_GPG_PEPPER_VALUE'
SCRYPT_PARAMS=dict(N=2**14, r=8, p=1)

# Default to the production configuration
FlaskConfig = ProductionConfig

if os.environ.get('SECUREDROP_ENV') == 'test':
    FlaskConfig = TestingConfig
    TEST_DIR='/tmp/securedrop_test'
    STORE_DIR=os.path.join(TEST_DIR, 'store')
    GPG_KEY_DIR=os.path.join(TEST_DIR, 'keys')
    # test_journalist_key.pub
    JOURNALIST_KEY='65A1B5FF195B56353CC63DFFCC40EF1228271441'

# Database Configuration

# Default to using a sqlite database file for development
DATABASE_ENGINE = 'sqlite'
SECUREDROP_ROOT=os.path.abspath('/var/www/securedrop')
DATABASE_FILE=os.path.join(SECUREDROP_ROOT, 'db.sqlite')

# Uncomment to use mysql (or any other databaes backend supported by
# SQLAlchemy). Make sure you have the necessary dependencies installed, and run
# `python -c "import db; db.init_db()"` to initialize the database

#DATABASE_ENGINE = 'mysql'
#DATABASE_HOST = 'localhost'
#DATABASE_NAME = 'securedrop'
#DATABASE_USERNAME = 'securedrop'
#DATABASE_PASSWORD = ''

########NEW FILE########
__FILENAME__ = background
import threading


def execute(func):
    threading.Thread(target=func).start()

########NEW FILE########
__FILENAME__ = crypto_util
# -*- coding: utf-8 -*-
import os
import subprocess
from base64 import b32encode

from Crypto.Random import random
import gnupg
import scrypt

import config
import store

# to fix gpg error #78 on production
os.environ['USERNAME'] = 'www-data'

GPG_KEY_TYPE = "RSA"
if os.environ.get('SECUREDROP_ENV') == 'test':
    # Optiimize crypto to speed up tests (at the expense of security - DO NOT
    # use these settings in production)
    GPG_KEY_LENGTH = 1024
    SCRYPT_PARAMS = dict(N=2**1, r=1, p=1)
else:
    GPG_KEY_LENGTH = 4096
    SCRYPT_PARAMS = config.SCRYPT_PARAMS

SCRYPT_ID_PEPPER = config.SCRYPT_ID_PEPPER
SCRYPT_GPG_PEPPER = config.SCRYPT_GPG_PEPPER

DEFAULT_WORDS_IN_RANDOM_ID = 8

# Make sure these pass before the app can run
# TODO: Add more tests
def do_runtime_tests():
    assert(config.SCRYPT_ID_PEPPER != config.SCRYPT_GPG_PEPPER)
    # crash if we don't have srm:
    try:
        subprocess.check_call(['srm'], stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        pass

do_runtime_tests()

GPG_BINARY = 'gpg2'
try:
    p = subprocess.Popen([GPG_BINARY, '--version'], stdout=subprocess.PIPE)
except OSError:
    GPG_BINARY = 'gpg'
    p = subprocess.Popen([GPG_BINARY, '--version'], stdout=subprocess.PIPE)

assert p.stdout.readline().split()[
    -1].split('.')[0] == '2', "upgrade GPG to 2.0"
del p

gpg = gnupg.GPG(binary=GPG_BINARY, homedir=config.GPG_KEY_DIR)

words = file(config.WORD_LIST).read().split('\n')
nouns = file(config.NOUNS).read().split('\n')
adjectives = file(config.ADJECTIVES).read().split('\n')


class CryptoException(Exception):
    pass


def clean(s, also=''):
    """
    >>> clean("Hello, world!")
    Traceback (most recent call last):
      ...
    CryptoException: invalid input
    >>> clean("Helloworld")
    'Helloworld'
    """
    # safe characters for every possible word in the wordlist includes capital
    # letters because codename hashes are base32-encoded with capital letters
    ok = ' !#%$&)(+*-1032547698;:=?@acbedgfihkjmlonqpsrutwvyxzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    for c in s:
        if c not in ok and c not in also:
            raise CryptoException("invalid input: %s" % s)
    # scrypt.hash requires input of type str. Since the wordlist is all ASCII
    # characters, this conversion is not problematic
    return str(s)


def genrandomid(words_in_random_id=DEFAULT_WORDS_IN_RANDOM_ID):
    return ' '.join(random.choice(words) for x in range(words_in_random_id))


def display_id():
    return ' '.join([random.choice(adjectives), random.choice(nouns)])


def hash_codename(codename, salt=SCRYPT_ID_PEPPER):
    """
    >>> hash_codename('Hello, world!')
    'EQZGCJBRGISGOTC2NZVWG6LILJBHEV3CINNEWSCLLFTUWZLFHBTS6WLCHFHTOLRSGQXUQLRQHFMXKOKKOQ4WQ6SXGZXDAS3Z'
    """
    return b32encode(scrypt.hash(clean(codename), salt, **SCRYPT_PARAMS))


def genkeypair(name, secret):
    """
    >>> if not gpg.list_keys(hash_codename('randomid')):
    ...     genkeypair(hash_codename('randomid'), 'randomid').type
    ... else:
    ...     u'P'
    u'P'
    """
    name = clean(name)
    secret = hash_codename(secret, salt=SCRYPT_GPG_PEPPER)
    return gpg.gen_key(gpg.gen_key_input(
        key_type=GPG_KEY_TYPE, key_length=GPG_KEY_LENGTH,
        passphrase=secret,
        name_email=name
    ))


def delete_reply_keypair(source_id):
    key = getkey(source_id)
    # If this source was never flagged for reivew, they won't have a reply keypair
    if not key: return
    # The private key needs to be deleted before the public key can be deleted
    # http://pythonhosted.org/python-gnupg/#deleting-keys
    gpg.delete_keys(key, True) # private key
    gpg.delete_keys(key)       # public key
    # TODO: srm?


def getkey(name):
    for key in gpg.list_keys():
        for uid in key['uids']:
            if name in uid:
                return key['fingerprint']
    return None


def get_key_by_fingerprint(fingerprint):
    matches = filter(lambda k: k['fingerprint'] == fingerprint, gpg.list_keys())
    return matches[0] if matches else None


def encrypt(fp, s, output=None):
    r"""
    >>> key = genkeypair('randomid', 'randomid')
    >>> encrypt('randomid', "Goodbye, cruel world!")[:45]
    '-----BEGIN PGP MESSAGE-----\nVersion: GnuPG v2'
    """
    if output:
        store.verify(output)
    fp = fp.replace(' ', '')
    if isinstance(s, unicode):
        s = s.encode('utf8')
    if isinstance(s, str):
        out = gpg.encrypt(s, fp, output=output, always_trust=True)
    else:
        out = gpg.encrypt_file(s, fp, output=output, always_trust=True)
    if out.ok:
        return out.data
    else:
        raise CryptoException(out.stderr)


def decrypt(secret, plain_text):
    """
    >>> key = genkeypair('randomid', 'randomid')
    >>> decrypt('randomid', 'randomid',
    ...   encrypt('randomid', 'Goodbye, cruel world!')
    ... )
    'Goodbye, cruel world!'
    """
    hashed_codename = hash_codename(secret, salt=SCRYPT_GPG_PEPPER)
    return gpg.decrypt(plain_text, passphrase=hashed_codename).data


if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = db
import os
import datetime

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm.exc import NoResultFound

import config
import crypto_util
import store

# http://flask.pocoo.org/docs/patterns/sqlalchemy/

if config.DATABASE_ENGINE == "sqlite":
    engine = create_engine(
        config.DATABASE_ENGINE + ":///" +
        config.DATABASE_FILE
    )
else:
    engine = create_engine(
        config.DATABASE_ENGINE + '://' +
        config.DATABASE_USERNAME + ':' +
        config.DATABASE_PASSWORD + '@' +
        config.DATABASE_HOST + '/' +
        config.DATABASE_NAME, echo=False
    )

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class Source(Base):
    __tablename__ = 'sources'
    id = Column(Integer, primary_key=True)
    filesystem_id = Column(String(96), unique=True)
    journalist_designation = Column(String(255), nullable=False)
    flagged = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.datetime.now)
    
    # sources are "pending" and don't get displayed to journalists until they submit something
    pending = Column(Boolean, default=True)

    # keep track of how many interactions have happened, for filenames
    interaction_count = Column(Integer, default=0, nullable=False)

    def __init__(self, filesystem_id=None, journalist_designation=None):
        self.filesystem_id = filesystem_id
        self.journalist_designation = journalist_designation

    def __repr__(self):
        return '<Source %r>' % (self.journalist_designation)

    def journalist_filename(self):
        valid_chars = 'abcdefghijklmnopqrstuvwxyz1234567890-_'
        return ''.join([c for c in self.journalist_designation.lower().replace(' ', '_') if c in valid_chars])

    def documents_messages_count(self):
        try:
            return self.docs_msgs_count
        except AttributeError:
            self.docs_msgs_count = {'messages': 0, 'documents': 0}
            for submission in self.submissions:
                if submission.filename.endswith('msg.gpg'):
                    self.docs_msgs_count['messages'] += 1
                elif submission.filename.endswith('doc.zip.gpg'):
                    self.docs_msgs_count['documents'] += 1
            return self.docs_msgs_count


class Submission(Base):
    __tablename__ = 'submissions'
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('sources.id'))
    source = relationship("Source", backref=backref('submissions', order_by=id))
    filename = Column(String(255), nullable=False)
    size = Column(Integer, nullable=False)
    downloaded = Column(Boolean, default=False)

    def __init__(self, source, filename):
        self.source_id = source.id
        self.filename = filename
        self.size = os.stat(store.path(source.filesystem_id, filename)).st_size

    def __repr__(self):
        return '<Submission %r>' % (self.filename)

class SourceStar(Base):
    __tablename__ = 'source_stars'
    id = Column("id", Integer, primary_key=True)
    source_id = Column("source_id", Integer, ForeignKey('sources.id'))
    starred = Column("starred", Boolean, default=True)

    def __eq__(self, other):
        if isinstance(other, SourceStar):
            return self.source_id == other.source_id and self.id == other.id and self.starred == other.starred
        return NotImplemented

    def __init__(self, source, starred=True):
        self.source_id = source.id
        self.starred = starred

# Declare (or import) models before init_db
def init_db():
    Base.metadata.create_all(bind=engine)


########NEW FILE########
__FILENAME__ = journalist
# -*- coding: utf-8 -*-
import os
from datetime import datetime
import uuid

from flask import (Flask, request, render_template, send_file, redirect,
                   flash, url_for, g)
from flask_wtf.csrf import CsrfProtect

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

import config
import version
import crypto_util
import store
import background
import util
from db import db_session, Source, Submission, SourceStar

app = Flask(__name__, template_folder=config.JOURNALIST_TEMPLATES_DIR)
app.config.from_object(config.FlaskConfig)
CsrfProtect(app)

app.jinja_env.globals['version'] = version.__version__
if getattr(config, 'CUSTOM_HEADER_IMAGE', None):
    app.jinja_env.globals['header_image'] = config.CUSTOM_HEADER_IMAGE
    app.jinja_env.globals['use_custom_header_image'] = True
else:
    app.jinja_env.globals['header_image'] = 'logo.png'
    app.jinja_env.globals['use_custom_header_image'] = False

@app.teardown_appcontext
def shutdown_session(exception=None):
    """Automatically remove database sessions at the end of the request, or
    when the application shuts down"""
    db_session.remove()


def get_source(sid):
    """Return a Source object, representing the database row, for the source
    with id `sid`"""
    source = None

    try:
        source = Source.query.filter(Source.filesystem_id == sid).one()
    except MultipleResultsFound as e:
        app.logger.error("Found multiple Sources when one was expected: %s" % (e,))
        abort(500)
    except NoResultFound as e:
        app.logger.error("Found no Sources when one was expected: %s" % (e,))
        abort(404)

    return source


@app.before_request
def setup_g():
    """Store commonly used values in Flask's special g object"""
    if request.method == 'POST':
        sid = request.form.get('sid')
        if sid:
            g.sid = sid
            g.source = get_source(sid)


def get_docs(sid):
    """Get docs associated with source id `sid`, sorted by submission date"""
    docs = []
    for filename in os.listdir(store.path(sid)):
        os_stat = os.stat(store.path(sid, filename))
        docs.append(dict(
            name=filename,
            date=str(datetime.fromtimestamp(os_stat.st_mtime)),
            size=os_stat.st_size,
        ))
    # sort in chronological order
    docs.sort(key=lambda x: int(x['name'].split('-')[0]))
    return docs


@app.route('/')
def index():
    sources = []
    for source in Source.query.filter_by(pending=False).order_by(Source.last_updated.desc()).all():
        sources.append(source)
        source.num_unread = len(Submission.query.filter(Submission.source_id == source.id, Submission.downloaded == False).all())
    return render_template('index.html', sources=sources)


@app.route('/col/<sid>')
def col(sid):
    source = get_source(sid)
    docs = get_docs(sid)
    haskey = crypto_util.getkey(sid)
    return render_template("col.html", sid=sid,
            codename=source.journalist_designation, docs=docs, haskey=haskey,
            flagged=source.flagged)


def delete_collection(source_id):
    # Delete the source's collection of submissions
    store.delete_source_directory(source_id)

    # Delete the source's reply keypair
    crypto_util.delete_reply_keypair(source_id)

    # Delete their entry in the db
    source = get_source(source_id)
    db_session.delete(source)
    db_session.commit()


@app.route('/col/process', methods=('POST',))
def col_process():
    action = request.form['action']
    if action == 'delete':
        return col_delete()
    elif action == 'star':
        return col_star()
    else:
        return abort(404)


def col_star():

    if 'cols_selected' not in request.form:
        return redirect(url_for('index'))

    cols_selected = request.form.getlist('cols_selected')
    for source_id in cols_selected:
        source = get_source(source_id)
        source_star = SourceStar(source)
        db_session.add(source_star)

    return redirect(url_for('index'))


def col_delete():
    if 'cols_selected' in request.form:
        # deleting multiple collections from the index
        # Note: getlist is cgi.FieldStorage.getlist
        cols_selected = request.form.getlist('cols_selected')
        if len(cols_selected) < 1:
            flash("No collections selected to delete!", "warning")
        else:
            for source_id in cols_selected:
                delete_collection(source_id)
            flash("%s %s deleted" % (
                len(cols_selected),
                "collection" if len(cols_selected) == 1 else "collections"
            ), "notification")
    elif 'col_name' in request.form:
        # deleting a single collection from its /col page
        source_id, col_name = request.form['sid'], request.form['col_name']
        delete_collection(source_id)
        flash("%s's collection deleted" % (col_name,), "notification")

    return redirect(url_for('index'))

@app.route('/col/<sid>/<fn>')
def doc(sid, fn):
    if '..' in fn or fn.startswith('/'):
        abort(404)
    try:
        Submission.query.filter(Submission.filename == fn).one().downloaded = True
    except NoResultFound as e:
        app.logger.error("Could not mark " + fn + " as downloaded: %s" % (e,))
    db_session.commit()
    return send_file(store.path(sid, fn), mimetype="application/pgp-encrypted")


@app.route('/reply', methods=('POST',))
def reply():
    msg = request.form['msg']
    g.source.interaction_count += 1
    filename = "{0}-reply.gpg".format(g.source.interaction_count)

    crypto_util.encrypt(crypto_util.getkey(g.sid), msg, output=
                        store.path(g.sid, filename))

    db_session.commit()
    return render_template('reply.html', sid=g.sid,
            codename=g.source.journalist_designation)


@app.route('/regenerate-code', methods=('POST',))
def generate_code():
    g.source.journalist_designation = crypto_util.display_id()
    db_session.commit()
    return redirect('/col/' + g.sid)

@app.route('/download_unread/<sid>')
def download_unread(sid):
    id = Source.query.filter(Source.filesystem_id == sid).one().id
    docs = [doc.filename for doc in Submission.query.filter(Submission.source_id == id, Submission.downloaded == False).all()]
    return bulk_download(sid, docs)

@app.route('/bulk', methods=('POST',))
def bulk():
    action = request.form['action']

    doc_names_selected = request.form.getlist('doc_names_selected')
    docs_selected = [
        doc for doc in get_docs(g.sid) if doc['name'] in doc_names_selected]
    filenames_selected = [
        doc['name'] for doc in docs_selected]

    if action == 'download':
        return bulk_download(g.sid, filenames_selected)
    elif action == 'delete':
        return bulk_delete(g.sid, docs_selected)
    else:
        abort(400)


def bulk_delete(sid, docs_selected):
    source = get_source(sid)
    confirm_delete = bool(request.form.get('confirm_delete', False))
    if confirm_delete:
        for doc in docs_selected:
            db_session.delete(Submission.query.filter(Submission.filename == doc['name']).one())
            fn = store.path(sid, doc['name'])
            store.secure_unlink(fn)
        db_session.commit()
    return render_template('delete.html', sid=sid,
            codename=source.journalist_designation,
            docs_selected=docs_selected, confirm_delete=confirm_delete)


def bulk_download(sid, docs_selected):
    source = get_source(sid)
    filenames = []
    for doc in docs_selected:
        filenames.append(store.path(sid, doc))
        try:
            Submission.query.filter(Submission.filename == doc).one().downloaded = True
        except NoResultFound as e:
            app.logger.error("Could not mark " + doc + " as downloaded: %s" % (e,))
    db_session.commit()
    zip = store.get_bulk_archive(filenames)
    return send_file(zip.name, mimetype="application/zip",
                     attachment_filename=source.journalist_designation + ".zip",
                     as_attachment=True)


@app.route('/flag', methods=('POST',))
def flag():
    g.source.flagged = True
    db_session.commit()
    return render_template('flag.html', sid=g.sid,
            codename=g.source.journalist_designation)

if __name__ == "__main__":
    # TODO make sure debug=False in production
    app.run(debug=True, host='0.0.0.0', port=8081)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import sys
import os
import shutil
import subprocess

import config
import db

def start():
    subprocess.Popen(['python', 'source.py'])
    subprocess.Popen(['python', 'journalist.py'])
    print "The web application is running, and available on your Vagrant host at the following addresses:"
    print "Source interface:     localhost:8080"
    print "Journalist interface: localhost:8081"

def test():
    """
    Runs the test suite
    """
    # TODO: we could implement test.sh's functionality here, and get rid of
    # test.sh (now it's just clutter, and confusing)
    subprocess.call(["./test.sh"])

def reset():
    """
    Clears the Securedrop development application's state, restoring it to the
    way it was immediately after running `setup_dev.sh`. This command:
    1. Erases the development sqlite database file ($SECUREDROP_ROOT/db.sqlite)
    2. Regenerates the database
    3. Erases stored submissions and replies from $SECUREDROP_ROOT/store
    """
    # Erase the development db file
    assert hasattr(config, 'DATABASE_FILE'), "TODO: ./manage.py doesn't know how to clear the db if the backend is not sqlite"
    os.remove(config.DATABASE_FILE)

    # Regenerate the database
    db.init_db()

    # Clear submission/reply storage
    for source_dir in os.listdir(config.STORE_DIR):
        # Each entry in STORE_DIR is a directory corresponding to a source
        shutil.rmtree(os.path.join(config.STORE_DIR, source_dir))

def main():
    valid_cmds = ["start", "test", "reset"]
    help_str = "./manage.py {{{0}}}".format(','.join(valid_cmds))

    if len(sys.argv) != 2 or sys.argv[1] not in valid_cmds:
        print help_str
        sys.exit(1)

    cmd = sys.argv[1]
    getattr(sys.modules[__name__], cmd)()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = source
# -*- coding: utf-8 -*-
import os
from datetime import datetime
import uuid
from functools import wraps
import zipfile
from cStringIO import StringIO
import subprocess

import logging
# This module's logger is explicitly labeled so the correct logger is used,
# even when this is run from the command line (e.g. during development)
log = logging.getLogger('source')

from flask import (Flask, request, render_template, session, redirect, url_for,
                   flash, abort, g, send_file)
from flask_wtf.csrf import CsrfProtect

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

import config
import version
import crypto_util
import store
import background
import util
from db import db_session, Source, Submission

app = Flask(__name__, template_folder=config.SOURCE_TEMPLATES_DIR)
app.config.from_object(config.FlaskConfig)
CsrfProtect(app)

app.jinja_env.globals['version'] = version.__version__
if getattr(config, 'CUSTOM_HEADER_IMAGE', None):
    app.jinja_env.globals['header_image'] = config.CUSTOM_HEADER_IMAGE
    app.jinja_env.globals['use_custom_header_image'] = True
else:
    app.jinja_env.globals['header_image'] = 'securedrop.png'
    app.jinja_env.globals['use_custom_header_image'] = False


@app.teardown_appcontext
def shutdown_session(exception=None):
    """Automatically remove database sessions at the end of the request, or
    when the application shuts down"""
    db_session.remove()


def logged_in():
    if 'logged_in' in session:
        return True


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not logged_in():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def ignore_static(f):
    """Only executes the wrapped function if we're not loading a static resource."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.path.startswith('/static'):
            return  # don't execute the decorated function
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
@ignore_static
def setup_g():
    """Store commonly used values in Flask's special g object"""
    # ignore_static here because `crypto_util.hash_codename` is scrypt (very
    # time consuming), and we don't need to waste time running if we're just
    # serving a static resource that won't need to access these common values.
    if logged_in():
        g.codename = session['codename']
        g.sid = crypto_util.hash_codename(g.codename)
        try:
            g.source = Source.query.filter(Source.filesystem_id == g.sid).one()
        except MultipleResultsFound as e:
            app.logger.error("Found multiple Sources when one was expected: %s" % (e,))
            abort(500)
        except NoResultFound as e:
            app.logger.error("Found no Sources when one was expected: %s" % (e,))
            del session['logged_in']
            del session['codename']
            return redirect(url_for('index'))
        g.loc = store.path(g.sid)


@app.before_request
@ignore_static
def check_tor2web():
        # ignore_static here so we only flash a single message warning about Tor2Web,
        # corresponding to the intial page load.
    if 'X-tor2web' in request.headers:
        flash('<strong>WARNING:</strong> You appear to be using Tor2Web. '
              'This <strong>does not</strong> provide anonymity. '
              '<a href="/tor2web-warning">Why is this dangerous?</a>',
              "banner-warning")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=('GET', 'POST'))
def generate():
    number_words = 8
    if request.method == 'POST':
        number_words = int(request.form['number-words'])
        if number_words not in range(7, 11):
            abort(403)
    session['codename'] = crypto_util.genrandomid(number_words)
    session.pop('logged_in', None)
    # TODO: make sure this codename isn't a repeat
    return render_template('generate.html', codename=session['codename'])


@app.route('/create', methods=['POST'])
def create():
    sid = crypto_util.hash_codename(session['codename'])

    source = Source(sid, crypto_util.display_id())
    db_session.add(source)
    db_session.commit()

    if os.path.exists(store.path(sid)):
        # if this happens, we're not using very secure crypto
        log.warning("Got a duplicate ID '%s'" % sid)
    else:
        os.mkdir(store.path(sid))

    session['logged_in'] = True
    return redirect(url_for('lookup'))


@app.route('/lookup', methods=('GET',))
@login_required
def lookup():
    replies = []
    for fn in os.listdir(g.loc):
        if fn.endswith('-reply.gpg'):
            try:
                msg = crypto_util.decrypt(g.codename,
                        file(store.path(g.sid, fn)).read()).decode("utf-8")
            except UnicodeDecodeError:
                app.logger.error("Could not decode reply %s" % fn)
            else:
                d = datetime.fromtimestamp(os.stat(store.path(g.sid, fn)).st_mtime)
                date = util.format_time(d)
                replies.append(dict(id=fn, date=date, msg=msg))

    def async_genkey(sid, codename):
        with app.app_context():
            background.execute(lambda: crypto_util.genkeypair(sid, codename))

    # Generate a keypair to encrypt replies from the journalist
    # Only do this if the journalist has flagged the source as one
    # that they would like to reply to. (Issue #140.)
    if not crypto_util.getkey(g.sid) and g.source.flagged:
        async_genkey(g.sid, g.codename)

    # if this was a redirect from the login page, flash a message if there are
    # no replies to clarify "check for replies" flow (#393)
    if request.args.get('from_login') == '1' and len(replies) == 0:
        flash("There are no replies at this time. You can submit more documents from this code name below.", "notification")

    return render_template('lookup.html', codename=g.codename, replies=replies,
            flagged=g.source.flagged, haskey=crypto_util.getkey(g.sid))


def normalize_timestamps(sid):
    """
    Update the timestamps on all of the source's submissions to match that of
    the latest submission. This minimizes metadata that could be useful to
    investigators. See #301.
    """
    sub_paths = [ store.path(sid, submission.filename)
                  for submission in g.source.submissions ]
    if len(sub_paths) > 1:
        args = ["touch"]
        args.extend(sub_paths[:-1])
        rc = subprocess.call(args)
        if rc != 0:
            app.logger.warning("Couldn't normalize submission timestamps (touch exited with %d)" % rc)


@app.route('/submit', methods=('POST',))
@login_required
def submit():
    msg = request.form['msg']
    fh = request.files['fh']
    strip_metadata = True if 'notclean' in request.form else False

    fnames = []
    journalist_filename = g.source.journalist_filename()

    if msg:
        g.source.interaction_count += 1
        fnames.append(store.save_message_submission(g.sid, g.source.interaction_count,
            journalist_filename, msg))
        flash("Thanks! We received your message.", "notification")
    if fh:
        g.source.interaction_count += 1
        fnames.append(store.save_file_submission(g.sid, g.source.interaction_count,
            journalist_filename, fh.filename, fh.stream, fh.content_type, strip_metadata))
        flash("Thanks! We received your document '%s'."
              % fh.filename or '[unnamed]', "notification")

    for fname in fnames:
        submission = Submission(g.source, fname)
        db_session.add(submission)

    if g.source.pending:
        g.source.pending = False

        # Generate a keypair now, if there's enough entropy (issue #303)
        entropy_avail = int(open('/proc/sys/kernel/random/entropy_avail').read())
        if entropy_avail >= 2400:
            crypto_util.genkeypair(g.sid, g.codename)

    g.source.last_updated = datetime.now()
    db_session.commit()
    normalize_timestamps(g.sid)

    return redirect(url_for('lookup'))


@app.route('/delete', methods=('POST',))
@login_required
def delete():
    msgid = request.form['msgid']
    assert '/' not in msgid
    potential_files = os.listdir(g.loc)
    if msgid not in potential_files:
        abort(404)  # TODO are the checks necessary?
    store.secure_unlink(store.path(g.sid, msgid))
    flash("Reply deleted.", "notification")

    return redirect(url_for('lookup'))


def valid_codename(codename):
    return os.path.exists(store.path(crypto_util.hash_codename(codename)))

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        codename = request.form['codename']
        if valid_codename(codename):
            session.update(codename=codename, logged_in=True)
            return redirect(url_for('lookup', from_login='1'))
        else:
            flash("Sorry, that is not a recognized codename.", "error")
    return render_template('login.html')


@app.route('/howto-disable-js')
def howto_disable_js():
    return render_template("howto-disable-js.html")


@app.route('/tor2web-warning')
def tor2web_warning():
    return render_template("tor2web-warning.html")


@app.route('/journalist-key')
def download_journalist_pubkey():
    journalist_pubkey = crypto_util.gpg.export_keys(config.JOURNALIST_KEY)
    return send_file(StringIO(journalist_pubkey),
                     mimetype="application/pgp-keys",
                     attachment_filename=config.JOURNALIST_KEY + ".asc",
                     as_attachment=True)


@app.route('/why-journalist-key')
def why_download_journalist_pubkey():
    return render_template("why-journalist-key.html")


_REDIRECT_URL_WHITELIST = ["http://tor2web.org/",
        "https://www.torproject.org/download.html.en",
        "https://tails.boum.org/",
        "http://www.wired.com/threatlevel/2013/09/freedom-hosting-fbi/",
        "http://www.theguardian.com/world/interactive/2013/oct/04/egotistical-giraffe-nsa-tor-document",
        "https://addons.mozilla.org/en-US/firefox/addon/noscript/",
        "http://noscript.net"]


@app.route('/redirect/<path:redirect_url>')
def redirect_hack(redirect_url):
    # A hack to avoid referer leakage when a user clicks on an external link.
    # TODO: Most likely will want to share this between source.py and
    # journalist.py in the future.
    if redirect_url not in _REDIRECT_URL_WHITELIST:
        return 'Redirect not allowed'
    else:
        return render_template("redirect.html", redirect_url=redirect_url)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('notfound.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html'), 500

if __name__ == "__main__":
    # TODO make sure debug is not on in production
    app.run(debug=True, host='0.0.0.0', port=8080)

########NEW FILE########
__FILENAME__ = store
# -*- coding: utf-8 -*-
import os
import re
import config
import zipfile
import crypto_util
import uuid
import tempfile
import subprocess
from cStringIO import StringIO
from shutil import copyfileobj

from MAT import mat
from MAT import strippers

import logging
log = logging.getLogger(__name__)

from werkzeug import secure_filename

VALIDATE_FILENAME = re.compile(
    "^(reply-)?[a-z0-9-_]+(-msg|-doc\.zip|)\.gpg$").match


class PathException(Exception):

    '''An exception raised by `store.verify` when it encounters a bad path. A path
    can be bad when it is not absolute, not normalized, not within
    `config.STORE_DIR`, or doesn't match the filename format.
    '''
    pass


def verify(p):
    '''Assert that the path is absolute, normalized, inside `config.STORE_DIR`, and
    matches the filename format.
    '''
    if not os.path.isabs(config.STORE_DIR):
        raise PathException("config.STORE_DIR(%s) is not absolute" % (
            config.STORE_DIR, ))

    # os.path.abspath makes the path absolute and normalizes '/foo/../bar' to
    # '/bar', etc. We have to check that the path is normalized before checking
    # that it starts with the `config.STORE_DIR` or else a malicious actor could
    # append a bunch of '../../..' to access files outside of the store.
    if not p == os.path.abspath(p):
        raise PathException("The path is not absolute and/or normalized")

    # Check that the path p is in config.STORE_DIR
    if os.path.relpath(p, config.STORE_DIR).startswith('..'):
        raise PathException("Invalid directory %s" % (p, ))

    if os.path.isfile(p):
        filename = os.path.basename(p)
        ext = os.path.splitext(filename)[-1]
        if filename == '_FLAG':
            return True
        if ext != '.gpg':
            # if there's an extension, verify it's a GPG
            raise PathException("Invalid file extension %s" % (ext, ))
        if not VALIDATE_FILENAME(filename):
            raise PathException("Invalid filename %s" % (filename, ))


def path(*s):
    '''Get the normalized, absolute file path, within `config.STORE_DIR`.'''
    joined = os.path.join(os.path.abspath(config.STORE_DIR), *s)
    absolute = os.path.abspath(joined)
    verify(absolute)
    return absolute


def get_bulk_archive(filenames):
    zip_file = tempfile.NamedTemporaryFile(prefix='tmp_securedrop_bulk_dl_')
    with zipfile.ZipFile(zip_file, 'w') as zip:
        for filename in filenames:
            verify(filename)
            zip.write(filename, arcname=os.path.basename(filename))
    return zip_file


def save_file_submission(sid, count, journalist_filename, filename, stream, content_type, strip_metadata):
    sanitized_filename = secure_filename(filename)
    clean_file = sanitize_metadata(stream, content_type, strip_metadata)

    s = StringIO()
    with zipfile.ZipFile(s, 'w') as zf:
        zf.writestr(sanitized_filename, clean_file.read() if clean_file else stream.read())
    s.reset()

    filename = "{0}-{1}-doc.zip.gpg".format(count, journalist_filename)
    file_loc = path(sid, filename)
    crypto_util.encrypt(config.JOURNALIST_KEY, s, file_loc)
    return filename


def save_message_submission(sid, count, journalist_filename, message):
    filename = "{0}-{1}-msg.gpg".format(count, journalist_filename)
    msg_loc = path(sid, filename)
    crypto_util.encrypt(config.JOURNALIST_KEY, message, msg_loc)
    return filename


def secure_unlink(fn, recursive=False, do_verify = True):
    if do_verify:
        verify(fn)
    command = ['srm']
    if recursive:
        command.append('-r')
    command.append(fn)
    return subprocess.check_call(command)


def delete_source_directory(source_id):
    secure_unlink(path(source_id), recursive=True)

def metadata_handler(f):
    return mat.create_class_file(f, False, add2archive=True)

def sanitize_metadata(stream, content_type, strip_metadata):
    text_plain = content_type == 'text/plain'

    s = None
    t = None
    clean_file = False

    if strip_metadata and not text_plain:
        t = tempfile.NamedTemporaryFile(delete = False)
        copyfileobj(stream, t)
        t.flush()
        file_meta = metadata_handler(t.name)

        if not file_meta.is_clean():
            file_meta.remove_all()
            f = open(t.name)
            s = StringIO()
            s.write(f.read())
            f.close()
            s.reset()
            secure_unlink(t.name, do_verify = False)
            t.close()
        else:
            secure_unlink(t.name, do_verify = False)
            t.close()

    return s


########NEW FILE########
__FILENAME__ = functional_test
import unittest
from selenium import webdriver
from multiprocessing import Process
import socket
import shutil
import os
import gnupg
import urllib2

os.environ['SECUREDROP_ENV'] = 'test'
import config

import source
import journalist
import test_setup
import urllib2

import signal
import traceback

class FunctionalTest():

    def _unused_port(self):
        s = socket.socket()
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def setUp(self):
        signal.signal(signal.SIGUSR1, lambda _, s: traceback.print_stack(s))

        test_setup.create_directories()
        self.gpg = test_setup.init_gpg()
        test_setup.init_db()

        source_port = self._unused_port()
        journalist_port = self._unused_port()

        self.source_location = "http://localhost:%d" % source_port
        self.journalist_location = "http://localhost:%d" % journalist_port

        def start_source_server():
            source.app.run(port=source_port,
                    debug=True,
                    use_reloader=False)

        def start_journalist_server():
            journalist.app.run(port=journalist_port,
                    debug=True,
                    use_reloader=False)

        self.source_process = Process(target = start_source_server)
        self.journalist_process = Process(target = start_journalist_server)

        self.source_process.start()
        self.journalist_process.start()

        self.driver = webdriver.Firefox()
        # Poll the DOM briefly to wait for elements. It appears .click() does
        # not always do a good job waiting for the page to load, or perhaps
        # Firefox takes too long to render it (#399)
        self.driver.implicitly_wait(1)

        self.secret_message = 'blah blah blah'

    def tearDown(self):
        test_setup.clean_root()
        self.driver.quit()
        self.source_process.terminate()
        self.journalist_process.terminate()


########NEW FILE########
__FILENAME__ = journalist_navigation_steps
import urllib2
import tempfile
import zipfile

class JournalistNavigationSteps():

    def _get_submission_content(self, file_url, raw_content):
        if not file_url.endswith(".zip.gpg"):
            return str(raw_content)

        with tempfile.TemporaryFile() as fp:
            fp.write(raw_content.data)
            fp.seek(0)

            zip_file = zipfile.ZipFile(fp)
            content = zip_file.open(zip_file.namelist()[0]).read()

            return content

    def _journalist_checks_messages(self):
        self.driver.get(self.journalist_location)

        code_names = self.driver.find_elements_by_class_name('code-name')
        self.assertEquals(1, len(code_names))

    def _journalist_downloads_message(self):
        self.driver.find_element_by_css_selector('.code-name a').click()

        submissions = self.driver.find_elements_by_css_selector('#submissions a')

        self.assertEqual(1, len(submissions))

        file_url = submissions[0].get_attribute('href')

        raw_content = urllib2.urlopen(file_url).read()

        decrypted_submission = self.gpg.decrypt(raw_content)

        submission = self._get_submission_content(file_url, decrypted_submission)
        self.assertEqual(self.secret_message, submission)

########NEW FILE########
__FILENAME__ = source_navigation_steps

class SourceNavigationSteps():

    def _source_visits_source_homepage(self):
        self.driver.get(self.source_location)

        self.assertEqual("SecureDrop | Protecting Journalists and Sources", self.driver.title)

    def _source_chooses_to_submit_documents(self):
        self.driver.find_element_by_id('submit-documents-button').click()

        codename = self.driver.find_element_by_css_selector('#codename')

        self.assertTrue(len(codename.text) > 0)
        self.source_name = codename.text

    def _source_continues_to_submit_page(self):
        continue_button = self.driver.find_element_by_id('continue-button')

        continue_button.click()
        headline = self.driver.find_element_by_class_name('headline')
        self.assertEqual('You have three options to send data', headline.text)


########NEW FILE########
__FILENAME__ = submit_and_retrieve_file
import unittest
import source_navigation_steps
import journalist_navigation_steps
import functional_test
import tempfile

class SubmitAndRetrieveFile(
        unittest.TestCase,
        functional_test.FunctionalTest,
        source_navigation_steps.SourceNavigationSteps,
        journalist_navigation_steps.JournalistNavigationSteps
        ):

    def setUp(self):
        functional_test.FunctionalTest.setUp(self)

    def tearDown(self):
        functional_test.FunctionalTest.tearDown(self)

    def _source_submits_a_file(self):
        with tempfile.NamedTemporaryFile() as file:
            file.write(self.secret_message)
            file.seek(0)

            filename = file.name
            filebasename = filename.split('/')[-1]

            file_upload_box = self.driver.find_element_by_css_selector('[name=fh]')
            file_upload_box.send_keys(filename)

            submit_button = self.driver.find_element_by_css_selector(
                'button[type=submit]')
            submit_button.click()

            notification = self.driver.find_element_by_css_selector( 'p.notification')
            expected_notification = "Thanks! We received your document '%s'." % filebasename
            self.assertEquals(expected_notification, notification.text)


    def test_submit_and_retrieve_happy_path(self):
        self._source_visits_source_homepage()
        self._source_chooses_to_submit_documents()
        self._source_continues_to_submit_page()
        self._source_submits_a_file()
        self._journalist_checks_messages()
        self._journalist_downloads_message()

########NEW FILE########
__FILENAME__ = submit_and_retrieve_message
import functional_test
import source_navigation_steps
import journalist_navigation_steps
import unittest
import urllib2

class SubmitAndRetrieveMessage(
        unittest.TestCase,
        functional_test.FunctionalTest,
        source_navigation_steps.SourceNavigationSteps,
        journalist_navigation_steps.JournalistNavigationSteps):

    def setUp(self):
        functional_test.FunctionalTest.setUp(self)

    def tearDown(self):
        functional_test.FunctionalTest.tearDown(self)

    def _source_submits_a_message(self):
        text_box = self.driver.find_element_by_css_selector('[name=msg]')

        text_box.send_keys(self.secret_message) # send_keys = type into text box
        submit_button = self.driver.find_element_by_css_selector(
            'button[type=submit]')
        submit_button.click()

        notification = self.driver.find_element_by_css_selector( 'p.notification')
        self.assertEquals('Thanks! We received your message.', notification.text)


    def test_submit_and_retrieve_happy_path(self):
        self._source_visits_source_homepage()
        self._source_chooses_to_submit_documents()
        self._source_continues_to_submit_page()
        self._source_submits_a_message()
        self._journalist_checks_messages()
        self._journalist_downloads_message()

if __name__ == "__main__":
    unittest.main(verbosity=2)

########NEW FILE########
__FILENAME__ = test_journalist
import journalist
import unittest
from db import Source, SourceStar
from mock import patch, ANY, MagicMock


class TestJournalist(unittest.TestCase):
    def setUp(self):
        journalist.request = MagicMock()
        journalist.url_for = MagicMock()
        journalist.redirect = MagicMock()
        journalist.abort = MagicMock()
        journalist.db_session = MagicMock()
        journalist.get_docs = MagicMock()


    @patch("journalist.col_delete")
    def test_col_process_delegates_to_col_delete(self, col_delete):
        journalist.request.form = {"action": "delete"}

        journalist.col_process()

        col_delete.assert_called_with()


    @patch("journalist.col_star")
    def test_col_process_delegates_to_col_star(self, col_star):
        journalist.request.form = {"action": "star"}

        journalist.col_process()

        col_star.assert_called_with()

    @patch("journalist.abort")
    def test_col_process_returns_404_with_bad_action(self, abort):
        journalist.col_process()

        abort.assert_called_with(ANY)

    @patch("journalist.redirect")
    def test_col_star_returns_index_redirect(self, redirect):
        journalist.col_star()

        redirect.assert_called_with(journalist.url_for('index'))

    @patch("journalist.db_session")
    def test_col_star_call_db_(self, db_session):
        source = Source("source_id")
        journalist.get_source = MagicMock(return_value=source)
        journalist.request.form.__contains__.return_value = True
        journalist.request.form.getlist = MagicMock(return_value=['source_id'])
        journalist.col_star()

        db_session.add.assert_called_with(SourceStar(source))


########NEW FILE########
__FILENAME__ = test_unit
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest
import re
from cStringIO import StringIO
import zipfile
from time import sleep
import uuid
from mock import patch, ANY

import gnupg
from flask import session, g, escape
from flask_wtf import CsrfProtect
from bs4 import BeautifulSoup

# Set environment variable so config.py uses a test environment
os.environ['SECUREDROP_ENV'] = 'test'
import config
import crypto_util
import store
import source
import journalist
import test_setup
from db import db_session, Source

def _block_on_reply_keypair_gen(codename):
    sid = crypto_util.hash_codename(codename)
    while not crypto_util.getkey(sid):
        sleep(0.1)

def _logout(test_client):
    # See http://flask.pocoo.org/docs/testing/#accessing-and-modifying-sessions
    # This is necessary because SecureDrop doesn't have a logout button, so a
    # user is logged in until they close the browser, which clears the session.
    # For testing, this function simulates closing the browser at places
    # where a source is likely to do so (for instance, between submitting a
    # document and checking for a journalist reply).
    with test_client.session_transaction() as sess:
        sess.clear()

def shared_setup():
    """Set up the file system, GPG, and database"""
    test_setup.create_directories()
    test_setup.init_gpg()
    test_setup.init_db()

    # Do tests that should always run on app startup
    crypto_util.do_runtime_tests()

def shared_teardown():
    test_setup.clean_root()


class TestSource(unittest.TestCase):

    def setUp(self):
        shared_setup()
        self.app = source.app
        self.client = self.app.test_client()

    def tearDown(self):
        shared_teardown()

    def test_index(self):
        """Test that the landing page loads and looks how we expect"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("Submit documents for the first time", response.data)
        self.assertIn("Already submitted something?", response.data)

    def _find_codename(self, html):
        """Find a source codename (diceware passphrase) in HTML"""
        # Codenames may contain HTML escape characters, and the wordlist
        # contains various symbols.
        codename_re = r'<strong id="codename">(?P<codename>[a-z0-9 &#;?:=@_.*+()\'"$%!-]+)</strong>'
        codename_match = re.search(codename_re, html)
        self.assertIsNotNone(codename_match)
        return codename_match.group('codename')

    def test_generate(self):
        with self.client as c:
            rv = c.get('/generate')
            self.assertEqual(rv.status_code, 200)
            session_codename = session['codename']
        self.assertIn("Remember this code and keep it secret", rv.data)
        self.assertIn(
            "To protect your identity, we're assigning you a unique code name.", rv.data)
        codename = self._find_codename(rv.data)
        # default codename length is 8 words
        self.assertEqual(len(codename.split()), 8)
        # codename is also stored in the session - make sure it matches the
        # codename displayed to the source
        self.assertEqual(codename, escape(session_codename))

    def test_regenerate_valid_lengths(self):
        """Make sure we can regenerate all valid length codenames"""
        for codename_len in xrange(7, 11):
            response = self.client.post('/generate', data={
                'number-words': str(codename_len),
            })
            self.assertEqual(response.status_code, 200)
            codename = self._find_codename(response.data)
            self.assertEquals(len(codename.split()), codename_len)

    def test_regenerate_invalid_lengths(self):
        """If the codename length is invalid, it should return 403 Forbidden"""
        for codename_len in (2, 999):
            response = self.client.post('/generate', data={
                'number-words': str(codename_len),
            })
            self.assertEqual(response.status_code, 403)

    def test_generate_has_login_link(self):
        """The generate page should have a link to remind people to login if they already have a codename, rather than create a new one."""
        rv = self.client.get('/generate')
        self.assertIn("Already have a codename?", rv.data)
        soup = BeautifulSoup(rv.data)
        already_have_codename_link = soup.select('a#already-have-codename')[0]
        self.assertEqual(already_have_codename_link['href'], '/login')

    def test_create(self):
        with self.client as c:
            rv = c.get('/generate')
            codename = session['codename']
            rv = c.post('/create', follow_redirects=True)
            self.assertTrue(session['logged_in'])
            # should be redirected to /lookup
            self.assertIn("You have three options to send data", rv.data)

    def _new_codename(self):
        """Helper function to go through the "generate codename" flow"""
        with self.client as c:
            rv = c.get('/generate')
            codename = session['codename']
            rv = c.post('/create')
        return codename

    def test_lookup(self):
        """Test various elements on the /lookup page"""
        codename = self._new_codename()
        rv = self.client.post('login', data=dict(codename=codename),
                              follow_redirects=True)
        # redirects to /lookup
        self.assertIn("journalist's public key", rv.data)
        # download the public key
        rv = self.client.get('journalist-key')
        self.assertIn("BEGIN PGP PUBLIC KEY BLOCK", rv.data)

    def test_login_and_logout(self):
        rv = self.client.get('/login')
        self.assertEqual(rv.status_code, 200)
        self.assertIn("Login to check for responses", rv.data)

        codename = self._new_codename()
        with self.client as c:
            rv = c.post('/login', data=dict(codename=codename),
                                  follow_redirects=True)
            self.assertEqual(rv.status_code, 200)
            self.assertIn("You have three options to send data", rv.data)
            self.assertTrue(session['logged_in'])
            _logout(c)

        with self.client as c:
            rv = self.client.post('/login', data=dict(codename='invalid'),
                                  follow_redirects=True)
            self.assertEqual(rv.status_code, 200)
            self.assertIn('Sorry, that is not a recognized codename.', rv.data)
            self.assertNotIn('logged_in', session)

    def test_submit_message(self):
        self._new_codename()
        rv = self.client.post('/submit', data=dict(
            msg="This is a test.",
            fh=(StringIO(''), ''),
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn("Thanks! We received your message.", rv.data)

    def test_submit_file(self):
        self._new_codename()
        rv = self.client.post('/submit', data=dict(
            msg="",
            fh=(StringIO('This is a test'), 'test.txt'),
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(escape("Thanks! We received your document 'test.txt'."),
                      rv.data)

    def test_submit_both(self):
        self._new_codename()
        rv = self.client.post('/submit', data=dict(
            msg="This is a test",
            fh=(StringIO('This is a test'), 'test.txt'),
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn("Thanks! We received your message.", rv.data)
        self.assertIn(escape("Thanks! We received your document 'test.txt'."),
                      rv.data)

    def test_submit_dirty_file_to_be_cleaned(self):
        self.gpg = gnupg.GPG(homedir=config.GPG_KEY_DIR)
        img = open(os.getcwd()+'/tests/test_images/dirty.jpg')
        img_metadata = store.metadata_handler(img.name)
        self.assertFalse(img_metadata.is_clean(), "The file is dirty.")
        codename = self._new_codename()
        rv = self.client.post('/submit', data=dict(
            msg="",
            fh=(img, 'dirty.jpg'),
            notclean='True',
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(escape("Thanks! We received your document 'dirty.jpg'."),
                      rv.data)

        store_dirs = [os.path.join(config.STORE_DIR,d) for d in os.listdir(config.STORE_DIR) if os.path.isdir(os.path.join(config.STORE_DIR,d))]
        latest_subdir = max(store_dirs, key=os.path.getmtime)
        zip_gpg_files = [os.path.join(latest_subdir,f) for f in os.listdir(latest_subdir) if os.path.isfile(os.path.join(latest_subdir,f))]
        self.assertEqual(len(zip_gpg_files), 1)
        zip_gpg = zip_gpg_files[0]

        zip_gpg_file = open(zip_gpg)
        decrypted_data = self.gpg.decrypt_file(zip_gpg_file)
        self.assertTrue(decrypted_data.ok, 'Checking the integrity of the data after decryption.')

        s = StringIO(decrypted_data.data)
        zip_file = zipfile.ZipFile(s, 'r')
        clean_file = open(os.path.join(latest_subdir,'dirty.jpg'), 'w+b')
        clean_file.write(zip_file.read('dirty.jpg'))
        clean_file.seek(0)
        zip_file.close()

        # check for the actual file been clean
        clean_file_metadata = store.metadata_handler(clean_file.name)
        self.assertTrue(clean_file_metadata.is_clean(), "the file is now clean.")
        zip_gpg_file.close()
        clean_file.close()
        img.close()

    def test_submit_dirty_file_to_not_clean(self):
        self.gpg = gnupg.GPG(homedir=config.GPG_KEY_DIR)
        img = open(os.getcwd()+'/tests/test_images/dirty.jpg')
        img_metadata = store.metadata_handler(img.name)
        self.assertFalse(img_metadata.is_clean(), "The file is dirty.")
        codename = self._new_codename()
        rv = self.client.post('/submit', data=dict(
            msg="",
            fh=(img, 'dirty.jpg'),
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(escape("Thanks! We received your document 'dirty.jpg'."),
                      rv.data)

        store_dirs = [os.path.join(config.STORE_DIR,d) for d in os.listdir(config.STORE_DIR) if os.path.isdir(os.path.join(config.STORE_DIR,d))]
        latest_subdir = max(store_dirs, key=os.path.getmtime)
        zip_gpg_files = [os.path.join(latest_subdir,f) for f in os.listdir(latest_subdir) if os.path.isfile(os.path.join(latest_subdir,f))]
        self.assertEqual(len(zip_gpg_files), 1)
        zip_gpg = zip_gpg_files[0]

        zip_gpg_file = open(zip_gpg)
        decrypted_data = self.gpg.decrypt_file(zip_gpg_file)
        self.assertTrue(decrypted_data.ok, 'Checking the integrity of the data after decryption.')

        s = StringIO(decrypted_data.data)
        zip_file = zipfile.ZipFile(s, 'r')
        clean_file = open(os.path.join(latest_subdir,'dirty.jpg'), 'w+b')
        clean_file.write(zip_file.read('dirty.jpg'))
        clean_file.seek(0)
        zip_file.close()

        # check for the actual file been clean
        clean_file_metadata = store.metadata_handler(clean_file.name)
        self.assertFalse(clean_file_metadata.is_clean(), "the file is was not cleaned.")
        zip_gpg_file.close()
        clean_file.close()
        img.close()

    def test_submit_clean_file(self):
        img = open(os.getcwd()+'/tests/test_images/clean.jpg')
        codename = self._new_codename()
        rv = self.client.post('/submit', data=dict(
            msg="This is a test",
            fh=(img, 'clean.jpg'),
            notclean='True',
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn("Thanks! We received your message.", rv.data)
        self.assertIn(escape("Thanks! We received your document 'clean.jpg'."),
                      rv.data)
        img.close()

    @patch('zipfile.ZipFile.writestr')
    def test_submit_sanitizes_filename(self, zipfile_write):
        """Test that upload file name is sanitized"""
        insecure_filename = '../../bin/gpg'
        sanitized_filename = 'bin_gpg'

        self._new_codename()
        self.client.post('/submit', data=dict(
            msg="",
            fh=(StringIO('This is a test'), insecure_filename),
        ), follow_redirects=True)
        zipfile_write.assert_called_with(sanitized_filename, ANY)

    def test_tor2web_warning(self):
        rv = self.client.get('/', headers=[('X-tor2web', 'encrypted')])
        self.assertEqual(rv.status_code, 200)
        self.assertIn("You appear to be using Tor2Web.", rv.data)


class TestJournalist(unittest.TestCase):

    def setUp(self):
        shared_setup()
        self.app = journalist.app
        self.client = self.app.test_client()

    def tearDown(self):
        shared_teardown()

    def test_index(self):
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertIn("Sources", rv.data)
        self.assertIn("No documents have been submitted!", rv.data)

    def test_bulk_download(self):
        sid = 'EQZGCJBRGISGOTC2NZVWG6LILJBHEV3CINNEWSCLLFTUWZJPKJFECLS2NZ4G4U3QOZCFKTTPNZMVIWDCJBBHMUDBGFHXCQ3R'
        source = Source(sid, crypto_util.display_id())
        db_session.add(source)
        db_session.commit()
        files = ['1-abc1-msg.gpg', '2-abc2-msg.gpg']
        filenames = test_setup.setup_test_docs(sid, files)

        rv = self.client.post('/bulk', data=dict(
            action='download',
            sid=sid,
            doc_names_selected=files
        ))

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.content_type, 'application/zip')
        self.assertTrue(zipfile.is_zipfile(StringIO(rv.data)))


class TestIntegration(unittest.TestCase):

    def setUp(self):
        shared_setup()
        self.source_app = source.app.test_client()
        self.journalist_app = journalist.app.test_client()
        self.gpg = gnupg.GPG(homedir=config.GPG_KEY_DIR)

    def tearDown(self):
        shared_teardown()

    def test_submit_message(self):
        """When a source creates an account, test that a new entry appears in the journalist interface"""
        test_msg = "This is a test message."

        with self.source_app as source_app:
            rv = source_app.get('/generate')
            rv = source_app.post('/create', follow_redirects=True)
            codename = session['codename']
            sid = g.sid
            # redirected to submission form
            rv = self.source_app.post('/submit', data=dict(
                msg=test_msg,
                fh=(StringIO(''), ''),
            ), follow_redirects=True)
            self.assertEqual(rv.status_code, 200)
            _logout(source_app)

        rv = self.journalist_app.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertIn("Sources", rv.data)
        soup = BeautifulSoup(rv.data)
        col_url = soup.select('ul#cols > li a')[0]['href']

        rv = self.journalist_app.get(col_url)
        self.assertEqual(rv.status_code, 200)
        soup = BeautifulSoup(rv.data)
        submission_url = soup.select('ul#submissions li a')[0]['href']
        self.assertIn("-msg", submission_url)
        li = soup.select('ul#submissions li .doc-info')[0]
        self.assertRegexpMatches(li.contents[-1], "\d+ bytes")

        rv = self.journalist_app.get(submission_url)
        self.assertEqual(rv.status_code, 200)
        decrypted_data = self.gpg.decrypt(rv.data)
        self.assertTrue(decrypted_data.ok)
        self.assertEqual(decrypted_data.data, test_msg)

        # delete submission
        rv = self.journalist_app.get(col_url)
        self.assertEqual(rv.status_code, 200)
        soup = BeautifulSoup(rv.data)
        doc_name = soup.select(
            'ul > li > input[name="doc_names_selected"]')[0]['value']
        rv = self.journalist_app.post('/bulk', data=dict(
            action='delete',
            sid=sid,
            doc_names_selected=doc_name
        ))

        self.assertEqual(rv.status_code, 200)
        soup = BeautifulSoup(rv.data)
        self.assertIn("The following file has been selected for", rv.data)

        # confirm delete submission
        doc_name = soup.select
        doc_name = soup.select(
            'ul > li > input[name="doc_names_selected"]')[0]['value']
        rv = self.journalist_app.post('/bulk', data=dict(
            action='delete',
            sid=sid,
            doc_names_selected=doc_name,
            confirm_delete="1"
        ))
        self.assertEqual(rv.status_code, 200)
        soup = BeautifulSoup(rv.data)
        self.assertIn("File permanently deleted.", rv.data)

        # confirm that submission deleted and absent in list of submissions
        rv = self.journalist_app.get(col_url)
        self.assertEqual(rv.status_code, 200)
        self.assertIn("No documents to display.", rv.data)

    def test_submit_file(self):
        """When a source creates an account, test that a new entry appears in the journalist interface"""
        test_file_contents = "This is a test file."
        test_filename = "test.txt"

        with self.source_app as source_app:
            rv = source_app.get('/generate')
            rv = source_app.post('/create', follow_redirects=True)
            codename = session['codename']
            sid = g.sid
            # redirected to submission form
            rv = self.source_app.post('/submit', data=dict(
                msg="",
                fh=(StringIO(test_file_contents), test_filename),
            ), follow_redirects=True)
            self.assertEqual(rv.status_code, 200)
            _logout(source_app)

        rv = self.journalist_app.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertIn("Sources", rv.data)
        soup = BeautifulSoup(rv.data)
        col_url = soup.select('ul#cols > li a')[0]['href']

        rv = self.journalist_app.get(col_url)
        self.assertEqual(rv.status_code, 200)
        soup = BeautifulSoup(rv.data)
        submission_url = soup.select('ul#submissions li a')[0]['href']
        self.assertIn("-doc", submission_url)
        li = soup.select('ul#submissions li .doc-info')[0]
        self.assertRegexpMatches(li.contents[-1], "\d+ bytes")

        rv = self.journalist_app.get(submission_url)
        self.assertEqual(rv.status_code, 200)
        decrypted_data = self.gpg.decrypt(rv.data)
        self.assertTrue(decrypted_data.ok)

        s = StringIO(decrypted_data.data)
        zip_file = zipfile.ZipFile(s, 'r')
        unzipped_decrypted_data = zip_file.read('test.txt')
        zip_file.close()

        self.assertEqual(unzipped_decrypted_data, test_file_contents)

        # delete submission
        rv = self.journalist_app.get(col_url)
        self.assertEqual(rv.status_code, 200)
        soup = BeautifulSoup(rv.data)
        doc_name = soup.select(
            'ul > li > input[name="doc_names_selected"]')[0]['value']
        rv = self.journalist_app.post('/bulk', data=dict(
            action='delete',
            sid=sid,
            doc_names_selected=doc_name
        ))

        self.assertEqual(rv.status_code, 200)
        soup = BeautifulSoup(rv.data)
        self.assertIn("The following file has been selected for", rv.data)

        # confirm delete submission
        doc_name = soup.select
        doc_name = soup.select(
            'ul > li > input[name="doc_names_selected"]')[0]['value']
        rv = self.journalist_app.post('/bulk', data=dict(
            action='delete',
            sid=sid,
            doc_names_selected=doc_name,
            confirm_delete="1"
        ))
        self.assertEqual(rv.status_code, 200)
        soup = BeautifulSoup(rv.data)
        self.assertIn("File permanently deleted.", rv.data)

        # confirm that submission deleted and absent in list of submissions
        rv = self.journalist_app.get(col_url)
        self.assertEqual(rv.status_code, 200)
        self.assertIn("No documents to display.", rv.data)

    def test_reply_normal(self):
        self.helper_test_reply("This is a test reply.", True)

    def test_reply_unicode(self):
        self.helper_test_reply("Teşekkürler", True)

    def helper_test_reply(self, test_reply, expected_success=True):
        test_msg = "This is a test message."

        with self.source_app as source_app:
            rv = source_app.get('/generate')
            rv = source_app.post('/create', follow_redirects=True)
            codename = session['codename']
            sid = g.sid
            # redirected to submission form
            rv = source_app.post('/submit', data=dict(
                msg=test_msg,
                fh=(StringIO(''), ''),
            ), follow_redirects=True)
            self.assertEqual(rv.status_code, 200)
            self.assertFalse(g.source.flagged)
            _logout(source_app)

        rv = self.journalist_app.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertIn("Sources", rv.data)
        soup = BeautifulSoup(rv.data)
        col_url = soup.select('ul#cols > li a')[0]['href']

        rv = self.journalist_app.get(col_url)
        self.assertEqual(rv.status_code, 200)

        with self.source_app as source_app:
            rv = source_app.post('/login', data=dict(
                codename=codename), follow_redirects=True)
            self.assertEqual(rv.status_code, 200)
            self.assertFalse(g.source.flagged)
            _logout(source_app)

        with self.journalist_app as journalist_app:
            rv = journalist_app.post('/flag', data=dict(
                sid=sid))
            self.assertEqual(rv.status_code, 200)
            _logout(journalist_app)

        with self.source_app as source_app:
            rv = source_app.post('/login', data=dict(
                codename=codename), follow_redirects=True)
            self.assertEqual(rv.status_code, 200)
            self.assertTrue(g.source.flagged)
            source_app.get('/lookup')
            self.assertTrue(g.source.flagged)
            _logout(source_app)

        # Block until the reply keypair has been generated, so we can test
        # sending a reply
        _block_on_reply_keypair_gen(codename)

        rv = self.journalist_app.post('/reply', data=dict(
            sid=sid,
            msg=test_reply
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)

        if not expected_success:
            pass
        else:
            self.assertIn("Thanks! Your reply has been stored.", rv.data)

        with self.journalist_app as journalist_app:
            rv = journalist_app.get(col_url)
            self.assertIn("reply-", rv.data)
            _logout(journalist_app)

        _block_on_reply_keypair_gen(codename)

        with self.source_app as source_app:
            rv = source_app.post('/login', data=dict(codename=codename), follow_redirects=True)
            self.assertEqual(rv.status_code, 200)
            rv = source_app.get('/lookup')
            self.assertEqual(rv.status_code, 200)

            if not expected_success:
                # there should be no reply
                self.assertTrue("You have received a reply." not in rv.data)
            else:
                self.assertIn(
                    "You have received a reply. For your security, please delete all replies when you're done with them.", rv.data)
                self.assertIn(test_reply, rv.data)
                soup = BeautifulSoup(rv.data)
                msgid = soup.select('form.message > input[name="msgid"]')[0]['value']
                rv = source_app.post('/delete', data=dict(
                        sid=sid,
                        msgid=msgid,
                        ), follow_redirects=True)
                self.assertEqual(rv.status_code, 200)
                self.assertIn("Reply deleted", rv.data)
                _logout(source_app)


    def test_delete_collection(self):
        """Test the "delete collection" button on each collection page"""
        # first, add a source
        self.source_app.get('/generate')
        self.source_app.post('/create')
        self.source_app.post('/submit', data=dict(
            msg="This is a test.",
            fh=(StringIO(''), ''),
        ), follow_redirects=True)

        rv = self.journalist_app.get('/')
        # navigate to the collection page
        soup = BeautifulSoup(rv.data)
        first_col_url = soup.select('ul#cols > li a')[0]['href']
        rv = self.journalist_app.get(first_col_url)
        self.assertEqual(rv.status_code, 200)

        # find the delete form and extract the post parameters
        soup = BeautifulSoup(rv.data)
        delete_form_inputs = soup.select('form#delete_collection')[0]('input')
        sid = delete_form_inputs[1]['value']
        col_name = delete_form_inputs[2]['value']
        rv = self.journalist_app.post('/col/process', data=dict(
            action='delete',
            sid=sid,
            col_name=col_name,
        ), follow_redirects=True)
        self.assertEquals(rv.status_code, 200)

        self.assertIn(escape("%s's collection deleted" % (col_name,)), rv.data)
        self.assertIn("No documents have been submitted!", rv.data)


    def test_delete_collections(self):
        """Test the "delete selected" checkboxes on the index page that can be
        used to delete multiple collections"""
        # first, add some sources
        num_sources = 2
        for i in range(num_sources):
            self.source_app.get('/generate')
            self.source_app.post('/create')
            self.source_app.post('/submit', data=dict(
                msg="This is a test "+str(i)+".",
                fh=(StringIO(''), ''),
            ), follow_redirects=True)
            _logout(self.source_app)

        rv = self.journalist_app.get('/')
        # get all the checkbox values
        soup = BeautifulSoup(rv.data)
        checkbox_values = [ checkbox['value'] for checkbox in
                            soup.select('input[name="cols_selected"]') ]
        rv = self.journalist_app.post('/col/process', data=dict(
            action='delete',
            cols_selected=checkbox_values
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn("%s collections deleted" % (num_sources,), rv.data)

        # TODO: functional tests (selenium)
        # This code just tests the underlying API and *does not* test the
        # interactions due to the Javascript in journalist.js. Once we have
        # functional tests, we should add tests for:
        # 1. Warning dialog appearance
        # 2. "Don't show again" checkbox behavior
        # 2. Correct behavior on "yes" and "no" buttons

    def test_filenames(self):
        """Test pretty, sequential filenames when source uploads messages and files"""
        # add a source and submit stuff
        self.source_app.get('/generate')
        self.source_app.post('/create')
        self.helper_filenames_submit()

        # navigate to the collection page
        rv = self.journalist_app.get('/')
        soup = BeautifulSoup(rv.data)
        first_col_url = soup.select('ul#cols > li a')[0]['href']
        rv = self.journalist_app.get(first_col_url)
        self.assertEqual(rv.status_code, 200)

        # test filenames and sort order
        soup = BeautifulSoup(rv.data)
        submission_filename_re = r'^{0}-[a-z0-9-_]+(-msg|-doc\.zip)\.gpg$'
        for i, submission_link in enumerate(soup.select('ul#submissions li a')):
            filename = str(submission_link.contents[0])
            self.assertTrue(re.match(submission_filename_re.format(i+1), filename))


    def test_filenames_delete(self):
        """Test pretty, sequential filenames when journalist deletes files"""
        # add a source and submit stuff
        self.source_app.get('/generate')
        self.source_app.post('/create')
        self.helper_filenames_submit()

        # navigate to the collection page
        rv = self.journalist_app.get('/')
        soup = BeautifulSoup(rv.data)
        first_col_url = soup.select('ul#cols > li a')[0]['href']
        rv = self.journalist_app.get(first_col_url)
        self.assertEqual(rv.status_code, 200)
        soup = BeautifulSoup(rv.data)

        # delete file #2
        self.helper_filenames_delete(soup, 1)
        rv = self.journalist_app.get(first_col_url)
        soup = BeautifulSoup(rv.data)

        # test filenames and sort order
        submission_filename_re = r'^{0}-[a-z0-9-_]+(-msg|-doc\.zip)\.gpg$'
        filename = str(soup.select('ul#submissions li a')[0].contents[0])
        self.assertTrue( re.match(submission_filename_re.format(1), filename) )
        filename = str(soup.select('ul#submissions li a')[1].contents[0])
        self.assertTrue( re.match(submission_filename_re.format(3), filename) )
        filename = str(soup.select('ul#submissions li a')[2].contents[0])
        self.assertTrue( re.match(submission_filename_re.format(4), filename) )


    def helper_filenames_submit(self):
        self.source_app.post('/submit', data=dict(
            msg="This is a test.",
            fh=(StringIO(''), ''),
        ), follow_redirects=True)
        self.source_app.post('/submit', data=dict(
            msg="This is a test.",
            fh=(StringIO('This is a test'), 'test.txt'),
        ), follow_redirects=True)
        self.source_app.post('/submit', data=dict(
            msg="",
            fh=(StringIO('This is a test'), 'test.txt'),
        ), follow_redirects=True)

    def helper_filenames_delete(self, soup, i):
        sid = soup.select('input[name="sid"]')[0]['value']
        checkbox_values = [soup.select('input[name="doc_names_selected"]')[i]['value']]

        # delete
        rv = self.journalist_app.post('/bulk', data=dict(
            sid=sid,
            action='delete',
            doc_names_selected=checkbox_values
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn("The following file has been selected for <strong>permanent deletion</strong>", rv.data)

        # confirm delete
        rv = self.journalist_app.post('/bulk', data=dict(
            sid=sid,
            action='delete',
            confirm_delete=1,
            doc_names_selected=checkbox_values
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn("File permanently deleted.", rv.data)


class TestStore(unittest.TestCase):

    '''The set of tests for store.py.'''
    def setUp(self):
        shared_setup()

    def tearDown(self):
        shared_teardown()

    def test_verify(self):
        with self.assertRaises(store.PathException):
            store.verify(os.path.join(config.STORE_DIR, '..', 'etc', 'passwd'))
        with self.assertRaises(store.PathException):
            store.verify(config.STORE_DIR + "_backup")

    def test_get_zip(self):
        sid = 'EQZGCJBRGISGOTC2NZVWG6LILJBHEV3CINNEWSCLLFTUWZJPKJFECLS2NZ4G4U3QOZCFKTTPNZMVIWDCJBBHMUDBGFHXCQ3R'
        files = ['1-abc1-msg.gpg', '2-abc2-msg.gpg']
        filenames = test_setup.setup_test_docs(sid, files)

        archive = zipfile.ZipFile(store.get_bulk_archive(filenames))

        archivefile_contents = archive.namelist()

        for archived_file, actual_file in zip(archivefile_contents, filenames):
            actual_file_content = open(actual_file).read()
            zipped_file_content = archive.read(archived_file)
            self.assertEquals(zipped_file_content, actual_file_content)


if __name__ == "__main__":
    unittest.main(verbosity=2)

########NEW FILE########
__FILENAME__ = util
import datetime

def format_time(d):
    return d.strftime('%b %d, %Y %I:%M %p')


########NEW FILE########
__FILENAME__ = version
__version__ = '0.2.1'

########NEW FILE########
__FILENAME__ = _genwordlist
"""
Generates `wordlist` from The English Open Word List http://dreamsteep.com/projects/the-english-open-word-list.html
Usage: Unzip the CSV files from the archive with the command `unzip EOWL-v1.1.2.zip EOWL-v1.1.2/CSV\ Format/*.csv`
"""
import re
import string


def just7(x):
    return all(c in string.printable for c in x)

words = set()

for i in map(chr, range(65, 91)):
    words.update(x.strip()
                 for x in file('EOWL-v1.1.2/CSV Format/%s Words.csv' % i) if just7(x))

fh = file('wordlist', 'w')
for word in words:
    if re.search('[^a-z0-9]', word):  # punctuation is right out
        continue
    if re.match(r'^([a-z])\1\1\1*$', word):  # yyyy is not a real word
        continue
    # EOWL contains bigrams xf, xg, xh, etc.
    if re.match(r'^[a-z][a-z]$', word):
        continue
    fh.write('%s\n' % word)

########NEW FILE########
__FILENAME__ = securedrop_init
#!/usr/bin/env python

import os, sys, subprocess

if __name__ == '__main__':
    # check for root
    if not os.geteuid()==0:
        sys.exit('You need to run this as root')

    # paths
    path_torrc_additions = '/home/amnesia/Persistent/.securedrop/torrc_additions'
    path_torrc_backup = '/etc/tor/torrc.bak'
    path_torrc = '/etc/tor/torrc'

    # load torrc_additions
    if os.path.isfile(path_torrc_additions):
        torrc_additions = open(path_torrc_additions).read()
    else:
        sys.exit('Error opening {0} for reading'.format(path_torrc_additions));

    # load torrc
    if os.path.isfile(path_torrc_backup):
        torrc = open(path_torrc_backup).read()
    else:
        if os.path.isfile(path_torrc):
            torrc = open(path_torrc).read()
        else:
            sys.exit('Error opening {0} for reading'.format(path_torrc));

        # save a backup
        open(path_torrc_backup, 'w').write(torrc)

    # append the additions
    open(path_torrc, 'w').write(torrc+torrc_additions)

    # reload tor
    subprocess.call(['/usr/sbin/service', 'tor', 'reload'])

    # success
    subprocess.call(['/usr/bin/sudo', '-u', 'amnesia', '/usr/bin/notify-send', 'Updated torrc', 'You can now connect to your SecureDrop document interface']);


########NEW FILE########
