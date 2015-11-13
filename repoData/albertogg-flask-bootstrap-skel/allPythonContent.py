__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

import sys
import os.path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
    
from application import app, db


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Overwrite the sqlalchemy.url in the alembic.ini file.
config.set_main_option('sqlalchemy.url', app.config['SQLALCHEMY_DATABASE_URI'])

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = db.metadata

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
__FILENAME__ = default_settings
import os

# Get application base dir.
_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
RELOAD = True
SECRET_KEY = 'mysecretkeyvalue'
SQLALCHEMY_DATABASE_URI = 'sqlite:////' + os.path.join(_basedir, 'db/app_dev.db')

########NEW FILE########
__FILENAME__ = manager
from application import app
from flask import render_template
from application.models import *


@app.route('/')
@app.route('/index/')
def index():
    return render_template('info/index.html', title='Flask-Bootstrap')


@app.route('/hello/<username>/')
def hello_username(username):
    return render_template('info/hello.html', title="Flask-Bootstrap, Hi %s"
                            % (username), username=username)

########NEW FILE########
__FILENAME__ = models
from application import db

##
# Create your own models here and they will be imported automaticaly. or
# use a model per blueprint.

##
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True)
#     email = db.Column(db.String(80), unique=True)
#     password = db.Column(db.String(80))

#     def __init__(self, username, email, password):
#         self.username = username
#         self.email = email
#         self.password = password

#     def __repr__(self):
#         return '<User %r>' % (self.username)

##
# class Log(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     time = db.Column(db.DateTime)
#     hostname = db.Column(db.String(20))
#     flagger = db.Column(db.Boolean)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
#     user = db.relationship('User', backref='log', lazy='dynamic')

#     def __init__(self, time, uptime, hostname, flagger, user_id):
#         self.returns = 0
#         self.errors = 0
#         self.time = time
#         self.hostname = hostname
#         self.flagger = flagger
#         self.user_id = user_id

#     def __repr__(self):
#         return '<Log %r>' % (self.hostname)

########NEW FILE########
__FILENAME__ = production
import os

DEBUG = False
RELOAD = False
CSRF_ENABLED = True
SECRET_KEY = 'notmysecretkey'
SQLALCHEMY_DATABASE_URI = str(os.environ.get('DATABASE_URL', 'postgresql://localhost/myproddatabase'))

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import *


# start with the default server
def run():
    """ Start with the default server """
    local('python runserver.py')


# start with unicorn server.
def grun():
    """ Start with gunicorn server """
    local('gunicorn -c gunicorn.conf runserver:app')


# run tests
def tests():
    """ Run unittests """
    local('python runtests.py --verbose')


# start iteractive shell within the flask environment
def shell():
    """ Start interactive shell within flask environment """
    local('python shell.py')

########NEW FILE########
__FILENAME__ = runserver
import os
from application import app

# run the application!
if __name__ == '__main__':
     # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

########NEW FILE########
__FILENAME__ = runtests
from tests.manage_tests import *

# Run unittest
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python

import os
import readline
from pprint import pprint

from flask import *
from application import *
from application.default_settings import _basedir


os.environ['PYTHONINSPECT'] = 'True'

# Create database directory if not exists.
create_db_dir = _basedir + '/db'
if not os.path.exists(create_db_dir):
    os.mkdir(create_db_dir, 0755)

########NEW FILE########
__FILENAME__ = manage_tests
import os
import unittest
from application.default_settings import _basedir
from application import app, db


class ManagerTestCase(unittest.TestCase):
    """ setup and teardown for the testing database """

    def setUp(self):
        create_db_dir = _basedir + '/db'
        if not os.path.exists(create_db_dir):
            os.mkdir(create_db_dir, 0755)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = ('sqlite:///'
                                    + os.path.join(_basedir, 'db/tests.db'))
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()


class OriginalRoutes(ManagerTestCase):
    """ test suite for the original in app routes """

    def route_username(self, username):
        return self.app.get('/hello/%s' % (username), follow_redirects=True)

    def test_username(self):
        rv = self.route_username('alberto')
        assert "Hello, alberto" in rv.data

    def test_index(self):
        rv = self.app.get('/')
        assert 'Flask bootstrap project' in rv.data
        assert 'Flask-bootstrap' in rv.data
        assert 'Read the wiki' in rv.data

########NEW FILE########
