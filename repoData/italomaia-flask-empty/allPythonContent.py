__FILENAME__ = models
# coding:utf-8

from database import db


class Brand(db.Model):
    __tablename__ = 'brand'

    id = db.Column(db.Integer, primary_key=True)
    creation_datetime = db.Column(db.DateTime)
    brand = db.Column(db.String(100))
    website = db.Column(db.String(100))


class SKU(db.Model):
    __tablename__ = 'sku'

    id = db.Column(db.Integer, primary_key=True)
    creation_datetime = db.Column(db.DateTime)

    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'))
    brand = db.relationship('Brand', backref=db.backref('sku_set', lazy='dynamic'))

    model = db.Column(db.String(100))
    teaser = db.Column(db.String(100))
    details = db.Column(db.Text)
    technical_details = db.Column(db.Text)
    mean_score = db.Column(db.SmallInteger)
    #comments


# TODO: this probably should move to another app
class Comment(db.Model):
    __tablename__ = 'comment'

    id = db.Column(db.Integer, primary_key=True)
    creation_datetime = db.Column(db.DateTime)

    sku_id = db.Column(db.Integer, db.ForeignKey('sku.id'))
    sku = db.relationship('SKU', backref=db.backref('comments', lazy='dynamic'))

    score = db.Column(db.SmallInteger)
    comment = db.Column(db.Text)
########NEW FILE########
__FILENAME__ = views
# coding:utf-8

from flask import Blueprint
from flask import render_template, request

from .models import *

app = Blueprint('blueprint', __name__, 
    template_folder='templates')


@app.route("/")
def index_view():
    return render_template("index.html")

########NEW FILE########
__FILENAME__ = models
# -*- coding:utf-8 -*-
from database import db
from datetime import datetime

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pub_date = db.Column(db.DateTime)
    title = db.Column(db.String(120))
    slug = db.Column(db.String(120))
    text = db.Column(db.Text)

    def __init__(self, title, text, pub_date=None, slug=None):
        self.title = title
        self.text = text
        self.slug = (slug or title).replace(' ', '_')
        self.pub_date = (pub_date or datetime.utcnow())

    def __repr__(self):
        return self.title

########NEW FILE########
__FILENAME__ = views
# -*- coding:utf-8 -*-

from flask import Blueprint, render_template, request
from models import Post

app = Blueprint('blog', __name__, template_folder='templates')

@app.route("/")
def index_view():
    posts = Post.query.all()
    return render_template('index.html', posts=posts)

@app.route("/<post_slug>")
def post_view(post_slug):
    post = Post.query.filter_by(slug=post_slug).first()
    return render_template('post.html', post=post)
########NEW FILE########
__FILENAME__ = commands
# -*- coding:utf-8 -*-

from flask.ext.script import Command, Option, prompt_bool

import os
import config


class CreateDB(Command):
    """
    Creates sqlalchemy database
    """

    def run(self):
        from database import create_all

        create_all()


class DropDB(Command):
    """
    Drops sqlalchemy database
    """

    def run(self):
        from database import drop_all

        drop_all()


class Test(Command):
    """
    Run tests
    """

    start_discovery_dir = "tests"

    def get_options(self):
        return [
            Option('--start_discover', '-s', dest='start_discovery',
                   help='Pattern to search for features',
                   default=self.start_discovery_dir),
        ]

    def run(self, start_discovery):
        import unittest

        if os.path.exists(start_discovery):
            argv = [config.project_name, "discover"]
            argv += ["-s", start_discovery]

            unittest.main(argv=argv)
        else:
            print("Directory '%s' was not found in project root." % start_discovery)


########NEW FILE########
__FILENAME__ = config
# -*- config:utf-8 -*-

from datetime import timedelta

project_name = "myblog"


class Config(object):
    DEBUG = False
    TESTING = False
    USE_X_SENDFILE = False

    # DATABASE CONFIGURATION
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/%s_dev.sqlite" % project_name
    SQLALCHEMY_ECHO = False

    CSRF_ENABLED = True
    SECRET_KEY = "secret"  # import os; os.urandom(24)
    LOGGER_NAME = "%s_log" % project_name
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)

    # EMAIL CONFIGURATION
    MAIL_SERVER = "localhost"
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_DEBUG = DEBUG
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    DEFAULT_MAIL_SENDER = "example@%s.com" % project_name

    BLUEPRINTS = [
        'blog' # or ('blog', {'url_prefix':'/blog'})
    ]


class Dev(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class Testing(Config):
    TESTING = True
    CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/%s_test.sqlite" % project_name
    SQLALCHEMY_ECHO = False

########NEW FILE########
__FILENAME__ = database
# -*- coding:utf-8 -*-

#--- SQLALCHEMY SUPPORT

# uncomment for sqlalchemy support
from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

def drop_all():
    db.drop_all()


def create_all():
    db.create_all()


def remove_session():
    db.session.remove()

#--- SQLALCHEMY SUPPORT END

########NEW FILE########
__FILENAME__ = main
# -*- coding:utf-8 -*-

from flask import Flask, render_template


def __import_variable(blueprint_path, module, variable_name):
    path = '.'.join(blueprint_path.split('.') + [module])
    mod = __import__(path, fromlist=[variable_name])
    return getattr(mod, variable_name)


def config_str_to_obj(cfg):
    if isinstance(cfg, basestring):
        module = __import__('config', fromlist=[cfg])
        return getattr(module, cfg)
    return cfg


def app_factory(config, app_name=None, blueprints=None):
    app_name = app_name or __name__
    app = Flask(app_name)

    config = config_str_to_obj(config)
    configure_app(app, config)
    configure_blueprints(app, blueprints or config.BLUEPRINTS)
    configure_error_handlers(app)
    configure_database(app)
    configure_context_processors(app)
    configure_template_filters(app)
    configure_extensions(app)
    configure_before_request(app)
    configure_views(app)

    return app


def configure_app(app, config):
    app.config.from_object(config)
    app.config.from_envvar("APP_CONFIG", silent=True)  # avaiable in the server


def configure_blueprints(app, blueprints):
    for blueprint_config in blueprints:
        blueprint = None
        kw = {}

        if (isinstance(blueprint_config, basestring)):
            blueprint = blueprint_config
        elif (isinstance(blueprint_config, dict)):
            blueprint = blueprint_config[0]
            kw = blueprint_config[1]

        blueprint = __import_variable(blueprint, 'views', 'app')
        app.register_blueprint(blueprint, **kw)


def configure_error_handlers(app):

    @app.errorhandler(403)
    def forbidden_page(error):
        """
        The server understood the request, but is refusing to fulfill it.
        Authorization will not help and the request SHOULD NOT be repeated.
        If the request method was not HEAD and the server wishes to make public
        why the request has not been fulfilled, it SHOULD describe the reason for
        the refusal in the entity. If the server does not wish to make this
        information available to the client, the status code 404 (Not Found)
        can be used instead.
        """
        return render_template("access_forbidden.html"), 403


    @app.errorhandler(404)
    def page_not_found(error):
        """
        The server has not found anything matching the Request-URI. No indication
        is given of whether the condition is temporary or permanent. The 410 (Gone)
        status code SHOULD be used if the server knows, through some internally
        configurable mechanism, that an old resource is permanently unavailable
        and has no forwarding address. This status code is commonly used when the
        server does not wish to reveal exactly why the request has been refused,
        or when no other response is applicable.
        """
        return render_template("page_not_found.html"), 404


    @app.errorhandler(405)
    def method_not_allowed_page(error):
        """
        The method specified in the Request-Line is not allowed for the resource
        identified by the Request-URI. The response MUST include an Allow header
        containing a list of valid methods for the requested resource.
        """
        return render_template("method_not_allowed.html"), 405


    @app.errorhandler(500)
    def server_error_page(error):
        return render_template("server_error.html"), 500


def configure_database(app):
    "Database configuration should be set here"
    # uncomment for sqlalchemy support
    from database import db
    db.app = app
    db.init_app(app)


def configure_context_processors(app):
    "Modify templates context here"
    pass


def configure_template_filters(app):
    "Configure filters and tags for jinja"
    pass


def configure_extensions(app):
    "Configure extensions like mail and login here"
    pass


def configure_before_request(app):
    pass


def configure_views(app):
    "Add some simple views here like index_view"
    @app.route("/")
    def index_view():
        return render_template("index.html")

########NEW FILE########
__FILENAME__ = manage
# -*- coding:utf-8 -*-

from flask.ext import script

import commands

if __name__ == "__main__":
    from main import app_factory
    import config

    manager = script.Manager(app_factory)
    manager.add_option("-c", "--config", dest="config", required=False, default=config.Dev)
    manager.add_command("test", commands.Test())
    manager.add_command("create_db", commands.CreateDB())
    manager.add_command("drop_db", commands.DropDB())
    manager.run()

########NEW FILE########
__FILENAME__ = test_blog
# -*- coding:utf-8 -*-

from tests import BaseTestCase as TestCase
from flask import url_for

class TestBlogViews(TestCase):
    def test_index_view(self):
        url_path = url_for('blog.views.index_view')
        self.client.get(url_path)

########NEW FILE########
__FILENAME__ = commands
# -*- coding:utf-8 -*-

from flask.ext.script import Command, Option, prompt_bool

import os
import config


class CreateDB(Command):
    """
    Creates database using SQLAlchemy
    """

    def run(self):
        from database import create_all

        create_all()


class DropDB(Command):
    """
    Drops database using SQLAlchemy
    """

    def run(self):
        from database import drop_all

        drop_all()


class Test(Command):
    """Run tests."""

    start_discovery_dir = "tests"

    def get_options(self):
        return [
            Option('--start_discover', '-s', dest='start_discovery',
                   help='Pattern to search for features',
                   default=self.start_discovery_dir),
        ]

    def run(self, start_discovery):
        import unittest

        if os.path.exists(start_discovery):
            argv = [config.project_name, "discover"]
            argv += ["-s", start_discovery]

            unittest.main(argv=argv)
        else:
            print("Directory '%s' was not found in project root." % start_discovery)



########NEW FILE########
__FILENAME__ = config
# -*- config:utf-8 -*-

import logging
from datetime import timedelta

project_name = "yourprojectname"


class Config(object):
    # use DEBUG mode?
    DEBUG = False

    # use TESTING mode?
    TESTING = False

    # use server x-sendfile?
    USE_X_SENDFILE = False

    # DATABASE CONFIGURATION
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/%s_dev.sqlite" % project_name
    SQLALCHEMY_ECHO = False

    CSRF_ENABLED = True
    SECRET_KEY = "secret"  # import os; os.urandom(24)

    # LOGGING
    LOGGER_NAME = "%s_log" % project_name
    LOG_FILENAME = "%s.log" % project_name
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = "%(asctime)s %(levelname)s\t: %(message)s" # used by logging.Formatter

    PERMANENT_SESSION_LIFETIME = timedelta(days=1)

    # EMAIL CONFIGURATION
    MAIL_SERVER = "localhost"
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_DEBUG = False
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    DEFAULT_MAIL_SENDER = "example@%s.com" % project_name

    # see example/ for reference
    # ex: BLUEPRINTS = ['blog']  # where app is a Blueprint instance
    # ex: BLUEPRINTS = [('blog', {'url_prefix': '/myblog'})]  # where app is a Blueprint instance
    BLUEPRINTS = []


class Dev(Config):
    DEBUG = True
    MAIL_DEBUG = True
    SQLALCHEMY_ECHO = True


class Testing(Config):
    TESTING = True
    CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/%s_test.sqlite" % project_name
    SQLALCHEMY_ECHO = False

########NEW FILE########
__FILENAME__ = database
# -*- coding:utf-8 -*-

#--- SQLALCHEMY SUPPORT

# uncomment for sqlalchemy support
# from flask.ext.sqlalchemy import SQLAlchemy
# db = SQLAlchemy()

#def drop_all():
#    db.drop_all()


#def create_all():
#    db.create_all()


#def remove_session():
#    db.session.remove()

#--- SQLALCHEMY SUPPORT END

########NEW FILE########
__FILENAME__ = main
# -*- coding:utf-8 -*-

import os
import sys
import logging
from flask import Flask, render_template


# apps is a special folder where you can place your blueprints
PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(PROJECT_PATH, "apps"))


def __import_variable(blueprint_path, module, variable_name):
    path = '.'.join(blueprint_path.split('.') + [module])
    mod = __import__(path, fromlist=[variable_name])
    return getattr(mod, variable_name)


def config_str_to_obj(cfg):
    if isinstance(cfg, basestring):
        module = __import__('config', fromlist=[cfg])
        return getattr(module, cfg)
    return cfg


def app_factory(config, app_name=None, blueprints=None):
    app_name = app_name or __name__
    app = Flask(app_name)

    config = config_str_to_obj(config)
    configure_app(app, config)
    configure_logger(app, config)
    configure_blueprints(app, blueprints or config.BLUEPRINTS)
    configure_error_handlers(app)
    configure_database(app)
    configure_context_processors(app)
    configure_template_filters(app)
    configure_extensions(app)
    configure_before_request(app)
    configure_views(app)

    return app


def configure_app(app, config):
    """Loads configuration class into flask app"""
    app.config.from_object(config)
    app.config.from_envvar("APP_CONFIG", silent=True)  # available in the server


def configure_logger(app, config):
    log_filename = config.LOG_FILENAME

    # Create a file logger since we got a logdir
    log_file = logging.FileHandler(filename=log_filename)
    formatter = logging.Formatter(config.LOG_FORMAT)
    log_file.setFormatter(formatter)
    log_file.setLevel(config.LOG_LEVEL)
    app.logger.addHandler(log_file)
    app.logger.info("Logger started")


def configure_blueprints(app, blueprints):
    """Registers all blueprints set up in config.py"""
    for blueprint_config in blueprints:
        blueprint, kw = None, {}

        if isinstance(blueprint_config, basestring):
            blueprint = blueprint_config
        elif isinstance(blueprint_config, tuple):
            blueprint = blueprint_config[0]
            kw = blueprint_config[1]
        else:
            print "Error in BLUEPRINTS setup in config.py"
            print "Please, verify if each blueprint setup is either a string or a tuple."
            exit(1)

        blueprint = __import_variable(blueprint, 'views', 'app')
        app.register_blueprint(blueprint, **kw)


def configure_error_handlers(app):
    @app.errorhandler(403)
    def forbidden_page(error):
        """
        The server understood the request, but is refusing to fulfill it.
        Authorization will not help and the request SHOULD NOT be repeated.
        If the request method was not HEAD and the server wishes to make public
        why the request has not been fulfilled, it SHOULD describe the reason for
        the refusal in the entity. If the server does not wish to make this
        information available to the client, the status code 404 (Not Found)
        can be used instead.
        """
        return render_template("access_forbidden.html"), 403

    @app.errorhandler(404)
    def page_not_found(error):
        """
        The server has not found anything matching the Request-URI. No indication
        is given of whether the condition is temporary or permanent. The 410 (Gone)
        status code SHOULD be used if the server knows, through some internally
        configurable mechanism, that an old resource is permanently unavailable
        and has no forwarding address. This status code is commonly used when the
        server does not wish to reveal exactly why the request has been refused,
        or when no other response is applicable.
        """
        return render_template("page_not_found.html"), 404

    @app.errorhandler(405)
    def method_not_allowed_page(error):
        """
        The method specified in the Request-Line is not allowed for the resource
        identified by the Request-URI. The response MUST include an Allow header
        containing a list of valid methods for the requested resource.
        """
        return render_template("method_not_allowed.html"), 405

    @app.errorhandler(500)
    def server_error_page(error):
        return render_template("server_error.html"), 500


def configure_database(app):
    """
    Database configuration should be set here
    """
    # uncomment for sqlalchemy support
    # from database import db
    # db.app = app
    # db.init_app(app)


def configure_context_processors(app):
    """Modify templates context here"""
    pass


def configure_template_filters(app):
    """Configure filters and tags for jinja"""
    pass


def configure_extensions(app):
    """Configure extensions like mail and login here"""
    pass


def configure_before_request(app):
    pass


def configure_views(app):
    """Add some simple views here like index_view"""
    pass

########NEW FILE########
__FILENAME__ = manage
# -*- coding:utf-8 -*-

from flask.ext import script

import commands

if __name__ == "__main__":
    from main import app_factory
    import config

    manager = script.Manager(app_factory)
    manager.add_option("-c", "--config", dest="config", required=False, default=config.Dev)
    manager.add_command("test", commands.Test())
    # uncomment for sqlalchemy commands support
    # manager.add_command("create_db", commands.CreateDB())
    # manager.add_command("drop_db", commands.DropDB())
    manager.run()

########NEW FILE########
