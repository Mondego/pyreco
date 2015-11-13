__FILENAME__ = forms
from flask.ext.wtf import Form, validators
from wtforms.ext.sqlalchemy.orm import model_form
import models


PostForm = model_form(models.Post, models.db.session, Form, field_args = {
    'name': {'validators': [validators.Required()]},
    'title': {'validators': [validators.Required()]},
    'content': {'validators': [validators.Required()]},
})

CommentForm = model_form(models.Comment, models.db.session, Form, field_args = {
    'commenter': {'validators': [validators.Required()]},
    'body': {'validators': [validators.Required()]},
})

########NEW FILE########
__FILENAME__ = models
from config import db


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    title = db.Column(db.String(200))
    content = db.Column(db.Text)

    def __init__(self, name, title, content):
        self.name = name
        self.title = title
        self.content = content

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commenter = db.Column(db.String(80))
    body = db.Column(db.Text)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    post = db.relationship('Post', backref=db.backref('comments', lazy='dynamic'))

    def __init__(self, commenter, body, post_id):
        self.commenter = commenter
        self.body = body
        self.post_id = post_id

########NEW FILE########
__FILENAME__ = urls
import views

routes = [
    ('/', 'index', views.post_index),
    ('/<int:id>', 'show', views.post_show),
    ('/new', 'new', views.post_new, {'methods': ['GET', 'POST']}),
    ('/<int:id>/edit', 'edit', views.post_edit, {'methods': ['GET', 'POST']}),
    ('/<int:id>/delete', 'delete', views.post_delete, {'methods': ['POST', 'DELETE']}),

    ('/<int:post_id>/comment_new', 'comment_new', views.comment_new, {'methods': ['GET', 'POST']}),
    ('/<int:post_id>/comment_delete/<int:id>', 'comment_delete', views.comment_delete, {'methods': ['GET', 'POST']}),
]

########NEW FILE########
__FILENAME__ = views
from flask import render_template, redirect, url_for, request
from config import db
import models
import forms


def post_index():
    object_list = models.Post.query.all()
    return render_template('post/index.slim', object_list=object_list)

def post_show(id):
    post = models.Post.query.get(id)
    form = forms.CommentForm()
    return render_template('post/show.slim', post=post, form=form)

def post_new():
    form = forms.PostForm()
    if form.validate_on_submit():
        post = models.Post(form.name.data, form.title.data, form.content.data)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('post.index'))
    return render_template('post/new.slim', form=form)

def post_edit(id):
    post = models.Post.query.get(id)
    form = forms.PostForm(request.form, post)
    if form.validate_on_submit():
        post.name = form.name.data
        post.title = form.title.data
        post.content = form.content.data
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('post.show', id=id))
    return render_template('post/edit.slim', form=form, post=post)

def post_delete(id):
    post = models.Post.query.get(id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('post.index'))

def comment_new(post_id):
    post = models.Post.query.get(post_id)
    form = forms.CommentForm()
    if form.validate_on_submit():
        comment = models.Comment(form.commenter.data, form.body.data, post_id)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('.show', id=post_id))
    return render_template('post/show.slim', post=post, form=form)

def comment_delete(post_id, id):
    comment = models.Comment.query.get(id)
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('.show', id=post_id))

########NEW FILE########
__FILENAME__ = blueprints
#: List of blueprints to be registered with the main wsgi app.
BLUEPRINTS = [
    ('blueprints.post', '/posts')
]

########NEW FILE########
__FILENAME__ = dev_settings
#: Dev setup. Enable debugger.
DEBUG = True
#: Enable testing for development.
TESTING = True
#: Database to use for SQLAlchemy.
SQLALCHEMY_DATABASE_URI = 'sqlite:///tmp/dev.db'
SQLALCHEMY_ECHO = True

USE_X_SENDFILE = False
CACHE_TYPE = 'simple'

#: webassets settings.
ASSETS_DEBUG = True
#: Session signing key.
# setting a string key. flask debugtoolbar was concatenating this with strings and failing.
SECRET_KEY = '8095d1aab8d98613102593955e48258eda86d135'

########NEW FILE########
__FILENAME__ = prod_settings
DEBUG = False
TESTING = False

#: If web server supports it, directly send the static files from webserver.
USE_X_SENDFILE = True

#: webassets settings.
ASSETS_DEBUG = False

SQLALCHEMY_DATABASE_URI = 'postgres://redux:reduxpass@localhost/redux'

########NEW FILE########
__FILENAME__ = settings
"""
Default settings supported by Flask. Additional keys can be put
in here which will be accessible in `app.config` dictionary like
object.
"""
import sys
import os
import logging
import importlib
from lib.middlewares import MethodRewriteMiddleware
from flask import render_template

from .blueprints import *

DEBUG = False
TESTING = False
#: Enable CSRF. Might not be needed if WTForms is used.
CSRF_ENABLED = True
#: Key for CSRF.
CSRF_SESSION_KEY = '\x126S{\x94\xbf}o5YE\xac\x17\x8e8^_\x18z\x08\xf3z1\x97'
#: Session signing key.
SECRET_KEY = '\x18[F;(\x99\xbcF\xc8\xe3\xb5\x89R\xb7[\x17H\x85\xd8\xa9,\xbf\x95\xb4;\xe1\x80\x872+\x82\x93'

#: Before request middlewares.
BEFORE_REQUESTS = [
]

#: After request middlewares.
AFTER_REQUESTS = []

#: Middlewares to enable.
#: Middlewares are executed in the order specified.
MIDDLEWARES = [
    #: Emulate RESTFul API for client that dont' directly
    #: support REST.
    # (middleware, *args, **kwargs)
    MethodRewriteMiddleware,
]

stream_logger = logging.StreamHandler()
stream_logger.setFormatter(logging.Formatter('''
                                             Message type:       %(levelname)s
                                             Location:           %(pathname)s:%(lineno)d
                                             Module:             %(module)s
                                             Function:           %(funcName)s
                                             Time:               %(asctime)s

                                             Message:

                                             %(message)s
                                             '''
                                            ))
stream_logger.setLevel(logging.DEBUG)

#: Custom log handlers.
LOG_HANDLERS = [stream_logger]

#: Jinja2 filters.
#TEMPLATE_FILTERS = [('custom_reverse', lambda x: x[::-1])]
TEMPLATE_FILTERS = []

#: Jinja2 context processors.
#CONTEXT_PROCESSORS = {name: val}
CONTEXT_PROCESSORS = {
}

#: Error handlers for http and other arbitrary exceptions.
ERROR_HANDLERS = [(404, lambda error: (render_template('errors/not_found.slim'), 404))]

HTTP_USERNAME = 'admin'
HTTP_PASSWORD = 'password'

# Load appropriate settings.
environ = os.environ.get('FLASK_ENV')
# Set environment specific settings.
if environ:
    _this_module = sys.modules[__name__]
    try:
        _m = importlib.import_module('config.%s_settings' % environ)
    except ImportError, ex:
        pass
    else:
        for _k in dir(_m):
            setattr(_this_module, _k, getattr(_m, _k))
# Dev is the default environment.
else:
    try:
        from dev_settings import *
    except ImportError, ex:
        pass

########NEW FILE########
__FILENAME__ = urls
"""
Sets the mapping between `url_endpoints` and `view functions`.
"""
from lib.utils import set_trace

routes = [
    # Define non-blueprint rotues here. Blueprint routes should be in
    # a separate urls.py inside the blueprint package.
]


def set_urls(app, routes=routes):
    """
    Connects url patterns to actions for the given wsgi `app`.
    """
    for rule in routes:
        # Set url rule.
        url_rule, endpoint, view_func, opts = parse_url_rule(rule)
        app.add_url_rule(url_rule, endpoint=endpoint, view_func=view_func, **opts)

def parse_url_rule(rule):
    """
    Breaks `rule` into `url`, `endpoint`, `view_func` and `opts`
    """
    length = len(rule)
    if length == 4:
        # No processing required.
        return rule
    elif length == 3:
        rule = list(rule)
        endpoint = None
        opts = {}
        if isinstance(rule[2], dict):
            # Options passed.
            opts = rule[2]
            view_func = rule[1]
        else:
            # Endpoint passed.
            endpoint = rule[1]
            view_func = rule[2]
        return (rule[0], endpoint, view_func, opts)
    elif length == 2:
        url_rule, view_func = rule
        return (url_rule, None, view_func, {})
    else:
        raise ValueError('URL rule format not proper %s' % (rule, ))

########NEW FILE########
__FILENAME__ = fabfile
import sys
import os

# Add current directory to path.
sys.path.append(os.path.dirname(__file__))

from fabric.api import local


########NEW FILE########
__FILENAME__ = flask_augment
"""
General purpose decorators and other utilities for contract based programming, for the
flask web framework.
"""
import re, sys, types
from functools import wraps
from collections import defaultdict

from flask import request

class AugmentError(ValueError):
    """
    Default exception raised when a contraint is voilated.
    """
    def __init__(self, errors):
        super(ValueError, self).__init__()
        self.errors = errors

    def __str__(self):
        """
        Dumps the `self.errors` dictionary.
        """
        return repr(self.errors)

def ensure_args(storage=None, error_handler=None, check_blank=True, **rules):
    """
    Ensures the value of `arg_name` satisfies `constraint`
    where `rules` is a collection of `arg_name=constraint`.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            handler = error_handler or _get_error_handler(fn)
            errors = check_args(storage, check_blank, **rules)
            if errors:
                num_errors = len(errors)
                plural = 'errors' if num_errors > 1 else 'error'
                errors['base'].append('%s %s' % (num_errors, plural))
                return _propogate_error(errors, handler)
            else:
                return fn(*args, **kwargs)
        return wrapper
    return decorator

def ensure_presence(storage=None, error_handler=None, **args):
    arg_dict = {}
    for arg_name in args:
        arg_dict[arg_name] = (lambda x: x, '%s is required.' % arg_name)
    return ensure_args(storage=storage, error_handler=error_handler, **arg_dict)

def ensure_one_of(storage=None, error_handler=None, exclusive=False, check_blank=True, **rules):
    """
    `rules` is a dictionary of `arg_name=1` pairs.
    Ensures at least(or at most depending on `exclusive)` one of `arg_name`
    is passed and not null.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            handler = error_handler or _get_error_handler(fn)
            errors = check_args(storage, check_blank, **rules)
            if errors:
                valid_count = len(rules) - len(errors)
                if valid_count < 1:
                    errors['base'].append('One of constraints must validate.')
                    return _propogate_error(errors, handler)
                elif valid_count > 1 and exclusive:
                    errors['base'].append('Only one of constraints should validate.')
                    return _propogate_error(errors, handler)
                else:
                    return fn(*args, **kwargs)
            else:
                if exclusive:
                    errors['base'].append('Only one of constraints should validate.')
                    return _propogate_error(errors, handler)
                else:
                    return fn(*args, **kwargs)
        return wrapper
    return decorator

def check_args(storage=None, check_blank=True, **rules):
    """
    Checks that `arg_val` satisfies `constraint` where `rules` is a
    dicionary of `arg_name=constraint` and `arg_val` is in `kwargs` or `args`
    """
    storage = storage or request.args
    results = []
    for arg_name, constraint in rules.iteritems():
        # Get the argument value.
        arg_val = storage.get(arg_name)
        if check_blank or arg_val:
            message = None
            if isinstance(constraint, list) or isinstance(constraint, tuple):
                if len(constraint) == 2:
                    constraint, message = constraint
                else:
                    raise ValueError('Constraints can either be "(constraint, message)" or "constraint"'
                                    '"%s" is in inproper format' % constraint)
            # `constraint` can either be a regex or a callable.
            validator = constraint
            if not callable(constraint):
                validator = lambda val: re.match(constraint, str(val))
            if message:
                results.append((arg_name, arg_val, validator(arg_val), message))
            else:
                results.append((arg_name, arg_val, validator(arg_val)))
    return _construct_errors(results, rules)

def _construct_errors(results, rules):
    """
    Constructs errors dictionary from the returned results.
    """
    errors = defaultdict(list)
    for res in results:
        message = None
        if len(res) == 4:
            arg_name, arg_val, valid, message = res
        else:
            arg_name, arg_val, valid = res
        if not valid:
            if not message:
                # No user supplied message. Construct a generic message.
                message = '"%s" violates constraint.' % arg_val
            errors[arg_name].append(message)
    return errors

def _propogate_error(errors, handler=None, exception_type=AugmentError):
    """
    Passes the errors to the handler or raises an exception.
    """
    if handler:
        return handler(errors)
    else:
        raise exception_type(errors)

def _get_error_handler(fn):
    error_handler = None
    if getattr(fn, '__name__', None):
        handler_name = '_%s_handler' % fn.__name__
        if isinstance(fn, types.FunctionType):
            mod = sys.modules[fn.__module__]
            error_handler = getattr(mod, handler_name, None)
        elif isinstance(fn, types.MethodType):
            error_handler = getattr(fn.im_class, handler_name, None)
    return error_handler


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = middlewares
from werkzeug import url_decode

class MethodRewriteMiddleware(object):
    """
    Middleware to handle RESTful requests from clients which
    don't support whole of REST (GET, PUT, POST, DELETE).

    The method name is passed as a form field and the request
    is re-written here.
    """

    def __init__(self, app, input_name='_method'):
        self.app = app
        self.input_name = input_name

    def __call__(self, environ, start_response):
        if self.input_name in environ.get('QUERY_STRING', ''):
            args = url_decode(environ['QUERY_STRING'])
            method = args.get(self.input_name).upper()
            if method and method in ['GET', 'POST', 'PUT', 'DELETE']:
                method = method.encode('ascii', 'replace')
                environ['REQUEST_METHOD'] = method
        return self.app(environ, start_response)

########NEW FILE########
__FILENAME__ = utils
# vim: set fileencoding=utf-8 :
"""
Misc. utilities.
"""
def set_trace():
    """
    Wrapper for ``pdb.set_trace``.
    """
    from config import app
    if not app.debug: return
    import pdb
    pdb.set_trace()

def simple_form(form_type, template, success):
    from flask import render_template
    def fn():
        form = form_type()
        if form.validate_on_submit():
            return success()
        return render_template(template, form=form)
    return fn

def http_auth(username, password, include, *endpoints):
    from flask import request, Response
    def protected():
        if request and request.endpoint and not request.endpoint.startswith('_'):
            if include:
                predicate = request.endpoint in endpoints
            else:
                predicate = request.endpoint not in endpoints
            if predicate:
                auth = request.authorization
                if not auth or not (auth.username == username and auth.password == password):
                    return Response('Could not verify your access level for that URL.\n'
                                    'You have to login with proper credentials', 401,
                                    {'WWW-Authenticate': 'Basic realm="Login Required"'})
    return protected

def http_do_auth(username, password, *endpoints):
    return http_auth(username, password, True, *endpoints)

def http_dont_auth(username, password, *endpoints):
    return http_auth(username, password, False, *endpoints)

def row_to_dict(row):
    return dict((col, getattr(row, col)) for col in row.__table__.columns.keys())

def rows_to_dict(rows):
    return map(row_to_dict, rows)

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
"""
Implements the main WSGI app. It instantiates and sets it up. It can
be run stand-alone as a flask application or it can be imported and
the resulting `app` object be used.
"""
import glob

from flask import Flask
from flask import Blueprint
from slimish_jinja import SlimishExtension
from werkzeug import import_string
from flask.ext.bcrypt import Bcrypt
from flask.ext.babel import Babel
from flask.ext.cache import Cache
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.assets import Environment, Bundle
from flask.ext.debugtoolbar import DebugToolbarExtension


import config
import config.urls as urls
import config.settings as settings

def init():
    """
    Sets up flask application object `app` and returns it.
    """
    # Instantiate main app, load configs, register modules, set
    # url patterns and return the `app` object.
    app = Flask(__name__)
    app.config.from_object(settings)
    config.app = app
    # Init SQLAlchemy wrapper.
    config.db = SQLAlchemy(app)
    if app.debug:
        DebugToolbarExtension(app)
    #: Wrap the `app` with `Babel` for i18n.
    Babel(app)

    config.cache = Cache(app)
    app.jinja_env.add_extension(SlimishExtension)
    app.jinja_env.slim_debug = app.debug
    config.bcrypt = Bcrypt(app)
    # Other initializations.
    for fn, values in [(set_middlewares, getattr(settings, 'MIDDLEWARES', None)),
                        (set_context_processors, getattr(settings, 'CONTEXT_PROCESSORS', None)),
                        (set_template_filters, getattr(settings, 'TEMPLATE_FILTERS', None)),
                        (set_before_handlers, getattr(settings, 'BEFORE_REQUESTS', None)),
                        (set_after_handlers, getattr(settings, 'AFTER_REQUESTS', None)),
                        (set_log_handlers, getattr(settings, 'LOG_HANDLERS', None)),
                        (set_error_handlers, getattr(settings, 'ERROR_HANDLERS', None)),
                        (set_blueprints, getattr(settings, 'BLUEPRINTS', None))]:
        if values:
            fn(app, values)

    # Register all js and css files.
    assets = Environment(app)
    register_assets(app, assets)

    # URL rules.
    urls.set_urls(app)
    return app

def register_assets(app, assets):
    """
    Registers all css and js assets with `assets`
    """
    def _get_resource_files(static_folder, resource_folder, resource_ext):
        return [file[len(static_folder) + 1:] for file in
                glob.glob(static_folder + '/%s/*.%s' % (resource_folder, resource_ext))]

    def _get_css_files(static_folder):
        return _get_resource_files(static_folder, 'css', 'css')

    def _get_less_files(static_folder):
        return _get_resource_files(static_folder, 'css', 'less')

    def _get_js_files(static_folder):
        return _get_resource_files(static_folder, 'js', 'js')

    def _get_coffee_files(static_folder):
        return _get_resource_files(static_folder, 'js', 'coffee')

    def _append_blueprint_name(name, files):
        return ['%s/%s' % (name, f) for f in files]

    static_folder = app.static_folder
    css_files = _get_css_files(static_folder)
    less_files = _get_less_files(static_folder)
    js_files = _get_js_files(static_folder)
    coffee_files = _get_coffee_files(static_folder)

    for name, bp in app.blueprints.iteritems():
        if name == 'debugtoolbar':
            continue
        static_folder = bp.static_folder
        if static_folder:
            css_files.extend(_append_blueprint_name(name, _get_css_files(static_folder)))
            less_files.extend(_append_blueprint_name(name, _get_less_files(static_folder)))
            js_files.extend(_append_blueprint_name(name, _get_js_files(static_folder)))
            coffee_files.extend(_append_blueprint_name(name, _get_coffee_files(static_folder)))

    js_contents = []
    if js_files:
        js_contents.append(Bundle(*js_files))
    if coffee_files:
        js_contents.append(Bundle(*coffee_files, filters='coffeescript', output='js/coffee_all.js'))
    if js_contents:
        js_all = Bundle(*js_contents, filters='closure_js', output='js/application.js')
        assets.register('js_all', js_all)
        assets.register('js_all_compressed', js_all, filters='gzip', output='js/application.js.gz')

    css_contents = []
    if css_files:
        css_contents.append(Bundle(*css_files))
    if less_files:
        css_contents.append(Bundle(*less_files, filters='less', output='css/less_all.css'))
    if css_contents:
        css_all = Bundle(*css_contents,
                         filters='cssmin', output='css/application.css')
        assets.register('css_all', css_all)
        assets.register('css_all_compressed', css_all, filters='gzip', output='css/application.css.gz')

def set_middlewares(app, middlewares):
    """
    Adds middlewares to the app.
    """
    # Add middlewares.
    if middlewares:
        for m in middlewares:
            if isinstance(m, list) or isinstance(m, tuple):
                if len(m) == 3:
                    mware, args, kwargs = m
                    new_mware = mware(app.wsgi_app, *args, **kwargs)
                elif len(mware) == 2:
                    mware, args = m
                    if isinstance(args, dict):
                        new_mware = mware(app.wsgi_app, **args)
                    elif isinstance(args, list) or isinstance(args, tuple):
                        new_mware = mware(app.wsgi_app, *args)
                    else:
                        new_mware = mware(app.wsgi_app, args)
            else:
                new_mware = m(app.wsgi_app)
            app.wsgi_app = new_mware

def set_blueprints(app, blueprints):
    """
    Registers blueprints with the app.
    """
    # Register blueprints.
    for blueprint in blueprints:
        url_prefix = None
        if len(blueprint) == 2:
            blueprint, url_prefix = blueprint
        blueprint_object = import_string('%s:BLUEPRINT' % blueprint, silent=True)
        blueprint_name, blueprint_import_name = blueprint.split('.')[-1], blueprint
        if not blueprint_object:
            options = dict(static_folder='static', template_folder='templates')
            blueprint_object = Blueprint(blueprint_name, blueprint_import_name, **options)
        blueprint_routes = import_string('%s.urls:routes' % blueprint_import_name, silent=True)
        if blueprint_routes:
            urls.set_urls(blueprint_object, blueprint_routes)

        # Other initializations.
        for fn, values in [(set_before_handlers, import_string('%s:BEFORE_REQUESTS' % blueprint, silent=True)),
                           (set_before_app_handlers, import_string('%s:BEFORE_APP_REQUESTS' % blueprint, silent=True)),
                           (set_after_handlers, import_string('%s:AFTER_REQUESTS' % blueprint, silent=True)),
                           (set_after_app_handlers, import_string('%s:AFTER_APP_REQUESTS' % blueprint, silent=True)),
                           (set_context_processors, import_string('%s:CONTEXT_PROCESSORS' % blueprint, silent=True)),
                           (set_app_context_processors, import_string('%s:APP_CONTEXT_PROCESSORS' % blueprint, silent=True)),
                           (set_error_handlers, import_string('%s:ERROR_HANDLERS' % blueprint, silent=True)),
                           (set_app_error_handlers, import_string('%s:APP_ERROR_HANDLERS' % blueprint, silent=True))]:
            if values:
                fn(blueprint_object, values)
        # Can be mounted at specific prefix.
        if url_prefix:
            app.register_blueprint(blueprint_object, url_prefix=url_prefix)
        else:
            app.register_blueprint(blueprint_object)

def set_before_handlers(app, before_handlers):
    """
    Sets before handlers.
    """
    # Register before request middlewares.
    for before in before_handlers:
        before = app.before_request(before)

def set_before_app_handlers(app, before_handlers):
    """
    Sets before handlers.
    When called from a blueprint, works on the application level rather than blueprint level.
    """
    # Register before request middlewares.
    for before in before_handlers:
        before = app.before_app_request(before)

def set_after_handlers(app, after_handlers):
    """
    Sets after handlers.
    """
    # Register before request middlewares.
    for after in after_handlers:
        after = app.after_request(after)

def set_after_app_handlers(app, after_handlers):
    """
    Sets after handlers.
    When called from a blueprint, works on the application level rather than blueprint level.
    """
    # Register before request middlewares.
    for after in after_handlers:
        after = app.after_app_request(after)

def set_log_handlers(app, log_handlers):
    """
    Sets log handlers for the app.
    """
    # Set log handlers.
    for handler in log_handlers:
        app.logger.addHandler(handler)

def set_template_filters(app, template_filters):
    """
    Sets jinja2 template filters.
    """
    for filter_name, filter_fn in template_filters:
        app.jinja_env.filters[filter_name] = filter_fn

def set_context_processors(app, context_processors):
    """
    Sets jinja2 context processors.
    """
    app.context_processor(lambda: context_processors)

def set_app_context_processors(app, context_processors):
    """
    Sets jinja2 context processors.
    When called from a blueprint, works on the application level rather than blueprint level.
    """
    app.app_context_processor(lambda: context_processors)

def set_error_handlers(app, error_handlers):
    """
    Sets error handlers.
    """
    for code, fn in error_handlers:
        fn = app.errorhandler(code)(fn)

def set_app_error_handlers(app, error_handlers):
    """
    Sets error handlers.
    When called from a blueprint, works on the application level rather than blueprint level.
    """
    for code, fn in error_handlers:
        fn = app.app_errorhandler(code)(fn)

app = init()
if __name__ == '__main__':
    #: Create the `app` object via :func:`init`. Run the `app`
    #: if called standalone.
    app.run()

########NEW FILE########
__FILENAME__ = manage
import os, signal, sys
import subprocess as sp
import werkzeug.serving
from werkzeug import import_string
from flask.ext.script import Manager
from flask.ext.assets import ManageAssets
import main

app = main.app
manager = Manager(app)

manager.add_command("assets", ManageAssets())

from config import db

@manager.command
def run_tornado(port=5000):
    """
    Runs application under tornado.
    """
    import script.serve_app_tornado as runner
    signal.signal(signal.SIGINT, interrupt_handler)
    _runner(runner, port)

@manager.command
def run_gevent(port=5000):
    """
    Runs gevent server.
    """
    import gevent
    import script.serve_app_gevent as runner
    gevent.signal(signal.SIGINT, interrupt_handler)
    _runner(runner, port)

def _runner(runner, *args, **kwargs):
    environ = os.environ.get('FLASK_ENV')
    if not environ or environ != 'prod':
        # Run with reloading.
        @werkzeug.serving.run_with_reloader
        def run_server():
            runner.run_server(app, *args, **kwargs)
        run_server()
    else:
        runner.run_server(app, *args, **kwargs)

def interrupt_handler(*args, **kwargs):
    sys.exit(1)

@manager.command
def db_createall():
    "Creates database"
    db.create_all()

@manager.command
def db_create_models():
    "Creates database tables."
    # db_createall doesn't work if the models aren't imported
    import_string('models', silent=True)
    for blueprint_name, blueprint in app.blueprints.iteritems():
        import_string('%s.models' % blueprint.import_name, silent=True)
    db.create_all()

@manager.command
def db_dropall():
    "Drops all database tables"
    # db_dropall doesn't work if the models aren't imported
    import_string('models', silent=True)
    for blueprint_name, blueprint in app.blueprints.iteritems():
        import_string('%s.models' % blueprint.import_name, silent=True)
    db.drop_all()


@manager.command
def create_blueprint(name, scaffold=False, fields=''):
    """
    Creates app folder structure. Optionally, scaffolds the app with models, forms, views and templates.
    Eg.
        # Create blueprint with scaffold.
        python manage.py create_blueprint post -s -f 'name:String(80) title:String(200) content:Text

        # Create blueprint with scaffold.
        python manage.py create_blueprint post -f 'name:String(80) title:String(200) content:Text
    """
    print sp.check_output('mkdir -p blueprints/%(name)s/templates/%(name)s' % locals(), shell=True),
    for static_dir in ('css', 'js', 'img'):
        print sp.check_output('mkdir -p blueprints/%(name)s/static/%(static_dir)s' % locals(), shell=True),
    print sp.check_output("touch blueprints/%(name)s/__init__.py" % locals(), shell=True),
    if scaffold:
        create_scaffold('%(name)s/%(name)s' % dict(name=name), fields)

@manager.command
def test():
    """
    Runs unit tests.
    """
    print sp.check_output('nosetests -v', shell=True),

@manager.command
def deps_get():
    """
    Installs dependencies.
    """
    print sp.check_output("pip install -r requirements.txt", shell=True),

@manager.command
def deps_update():
    """
    Updates dependencies.
    """
    print sp.check_output("pip install -r requirements.txt --upgrade", shell=True),

@manager.command
def create_model(name, fields=''):
    """
    Creates model scaffold and the model form.
    Eg:
        # Create top level model.
        python manage.py create_model tag -f 'name:String(80) post_id:Integer'

        # Create model within a blueprint.
        python manage.py create_model post/tag -f 'name:String(80) post_id:Integer'
    """
    if '/' in name:
        blueprint_name, model_name = name.split('/')
        output_file = 'blueprints/%s/models.py' % blueprint_name
    else:
        model_name = name
        output_file = 'models.py'
    model = create_model.model_scaffold % dict(model_name=model_name.capitalize())

    field_declares = []
    field_inits = []
    init_args = []
    for f in fields.split():
        splitted = f.split(':')
        if len(splitted) > 1:
            field_name, field_type = splitted[0], 'db.%s' % splitted[1]
        else:
            field_name, field_type = splitted[0], 'db.Text'
        field_declares.append(create_model.field_declare % dict(field_name=field_name, field_type=field_type))
        field_inits.append(create_model.field_init % dict(field_name=field_name))
        init_args.append(field_name)

    field_declares = '\n'.join(field_declares)

    init_args = (', %s' % ', '.join(init_args)) if init_args else ''
    init_body = '\n'.join(field_inits) if field_inits else '%spass' % (' ' * 8)
    init_method = '    def __init__(self%s):\n%s' % (init_args, init_body)

    file_exists = os.path.exists(output_file)
    with open(output_file, 'a') as out_file:
        model = '%(base)s%(field_declares)s\n\n%(init_method)s' % dict(base=model,
                                                                       field_declares=field_declares,
                                                                       init_method=init_method)
        if not file_exists:
            model = '%(imports)s\n%(rest)s' % dict(imports=create_model.imports,
                                                rest=model)
        out_file.write(model)
    create_model_form(name, fields)

create_model.model_scaffold = '''

class %(model_name)s(db.Model):
    id = db.Column(db.Integer, primary_key=True)
'''
create_model.imports = 'from config import db'
create_model.field_declare = '%s%%(field_name)s = db.Column(%%(field_type)s)' % (' ' * 4)
create_model.field_init = '%sself.%%(field_name)s = %%(field_name)s' % (' ' * 8)
create_model.init_method = '''
    def __init__(self%(args)s):
        %(body)s
'''


@manager.command
def create_routes(name):
    """
    Creates routes scaffold.
    Eg.
        # Top level routes.
        python manage.py create_routes post

        # Blueprint routes.
        python manage.py create_routes post/tag
    """
    if '/' in name:
        blueprint_name, model_name = name.split('/')
        output_file = 'blueprints/%s/urls.py' % blueprint_name
    else:
        model_name = name
        output_file = 'urls.py'
    file_exists = os.path.exists(output_file)
    routes = create_routes.routes_scaffold % dict(model_name=model_name.lower())
    if file_exists:
        routes = create_routes.append_routes % dict(routes=routes)
    else:
        routes = create_routes.new_routes % dict(routes=routes)
    with open(output_file, 'a') as out_file:
        if not file_exists:
            routes = '''%(imports)s\n%(rest)s''' % dict(imports=create_routes.imports,
                                                rest=routes)
        out_file.write(routes)

create_routes.imports = 'import views'
create_routes.routes_scaffold = '''('/', 'index', views.%(model_name)s_index),
    ('/<int:id>', 'show', views.%(model_name)s_show),
    ('/new', 'new', views.%(model_name)s_new, {'methods': ['GET', 'POST']}),
    ('/<int:id>/edit', 'edit', views.%(model_name)s_edit, {'methods': ['GET', 'POST']}),
    ('/<int:id>/delete', 'delete', views.%(model_name)s_delete, {'methods': ['POST']}),'''
create_routes.new_routes = '''
routes = [
    %(routes)s
]
'''
create_routes.append_routes = '''
routes += [
    %(routes)s
]
'''

@manager.command
def create_model_form(name, fields=''):
    """
    Creates model form scaffold.
    Eg:
        python manage.py create_model tag -f 'name:String(80) post_id:Integer'
    """
    if '/' in name:
        blueprint_name, model_name = name.split('/')
        output_file = 'blueprints/%s/forms.py' % blueprint_name
    else:
        model_name = name
        output_file = 'forms.py'
    file_exists = os.path.exists(output_file)
    field_args = []
    for f in fields.split():
        field_name = f.split(':')[0]
        field_args.append(create_model_form.field_args % dict(field_name=field_name))
    form = create_model_form.form_scaffold % dict(model_name=model_name.capitalize(), field_args=''.join(field_args))
    with open(output_file, 'a') as out_file:
        if not file_exists:
            form = '''%(imports)s\n%(rest)s''' % dict(imports=create_model_form.imports,
                                                      rest=form)
        out_file.write(form)

create_model_form.imports = '''import flask.ext.wtf as wtf
from flask.ext.wtf import Form, validators
from wtforms.ext.sqlalchemy.orm import model_form
import models
'''
create_model_form.form_scaffold = '''
%(model_name)sForm = model_form(models.%(model_name)s, models.db.session, Form, field_args = {%(field_args)s
})
'''
create_model_form.field_args = '''
    '%(field_name)s': {'validators': []},'''


@manager.command
def create_view(name, fields=''):
    """
    Creates view scaffold. It also creates the templates.
    Eg.
        # Top level views.
        python manage.py create_view comment -f 'commenter body post_id'

        # Blueprint views.
        python manage.py create_view post/comment -f 'commenter body post_id'
    """
    if '/' in name:
        blueprint_name, model_name = name.split('/')
        output_file = 'blueprints/%s/views.py' % blueprint_name
    else:
        model_name = name
        output_file = 'views.py'
    file_exists = os.path.exists(output_file)
    form_data = []
    for f in fields.split():
        form_data.append('form.%s.data' % f.split(':')[0])
    views = create_view.views_scaffold % dict(name=model_name.lower(),
                                               model_name=model_name.capitalize(),
                                               form_data=', '.join(form_data))
    with open(output_file, 'a') as out_file:
        if not file_exists:
            views = '''%(imports)s\n%(rest)s''' % dict(imports=create_view.imports,
                                                       rest=views)
        out_file.write(views)
    create_templates(name, fields)

create_view.imports = '''from flask import render_template, redirect, url_for, flash, request
from config import db
import models
import forms
'''
create_view.views_scaffold = '''
def %(name)s_index():
    object_list = models.%(model_name)s.query.all()
    return render_template('%(name)s/index.slim', object_list=object_list)

def %(name)s_show(id):
    %(name)s = models.%(model_name)s.query.get(id)
    return render_template('%(name)s/show.slim', %(name)s=%(name)s)

def %(name)s_new():
    form = forms.%(model_name)sForm()
    if form.validate_on_submit():
        %(name)s = models.%(model_name)s(%(form_data)s)
        db.session.add(%(name)s)
        db.session.commit()
        return redirect(url_for('%(name)s.index'))
    return render_template('%(name)s/new.slim', form=form)

def %(name)s_edit(id):
    %(name)s = models.%(model_name)s.query.get(id)
    form = forms.%(model_name)sForm(request.form, %(name)s)
    if form.validate_on_submit():
        form.populate_obj(%(name)s)
        db.session.add(%(name)s)
        db.session.commit()
        return redirect(url_for('%(name)s.show', id=id))
    return render_template('%(name)s/edit.slim', form=form, %(name)s=%(name)s)

def %(name)s_delete(id):
    %(name)s = models.%(model_name)s.query.get(id)
    db.session.delete(%(name)s)
    db.session.commit()
    return redirect(url_for('%(name)s.index'))
'''

@manager.command
def create_templates(name, fields=''):
    """
    Creates templates.
    Eg.
        # Top level templates.
        python manage.py create_templates comment -f 'commenter body post_id'

        # Blueprint templates.
        python manage.py create_templates post/comment -f 'commenter body post_id'
    """
    if '/' in name:
        blueprint_name, name = name.split('/')
        name = name.lower()
        output_dir = 'blueprints/%s/templates/%s' % (blueprint_name, name)
    else:
        name = name.lower()
        output_dir = 'templates/%s' % name
    sp.check_call('mkdir -p %s' % output_dir, shell=True),
    fields = [f.split(':')[0] for f in fields.split()]
    # Create form template.
    with open('%s/_%s_form.slim' % (output_dir, name), 'a') as out_file:
        form_fields = []
        for f in fields:
            form_fields.append(create_templates.form_field % dict(field_name=f))
        form = create_templates.form_scaffold % dict(name=name, fields=''.join(form_fields))
        out_file.write(form)
    # Create index template.
    with open('%s/index.slim' % output_dir, 'a') as out_file:
        index_fields = []
        field_headers = []
        for f in fields:
            index_fields.append(create_templates.index_field % dict(name=name, field_name=f))
            field_headers.append(create_templates.index_field_header % dict(field_header=f.capitalize()))
        index = create_templates.index_scaffold % dict(name=name,
                                                        fields=''.join(index_fields),
                                                        field_headers=''.join(field_headers))
        out_file.write(index)
    # Create show template.
    with open('%s/show.slim' % output_dir, 'a') as out_file:
        show_fields = []
        for f in fields:
            show_fields.append(create_templates.show_field % dict(name=name, field_header=f.capitalize(),
                                                                  field_name=f))
        show = create_templates.show_scaffold % dict(name=name,
                                                     fields=''.join(show_fields))
        out_file.write(show)
    # Create edit and new templates.
    for template_name in ('edit', 'new'):
        with open('%s/%s.slim' % (output_dir, template_name), 'a') as out_file:
            out_file.write(getattr(create_templates, '%s_scaffold' % template_name) % dict(name=name))

create_templates.form_scaffold = '''- from 'helpers.slim' import render_field

form method="POST"
  {{ form.hidden_tag() }}%(fields)s
  .field
    input type="submit"
'''
create_templates.form_field = '''
  {{ render_field(form.%(field_name)s) }}'''
create_templates.index_scaffold = '''- extends 'layout.slim'

- block content
  table
    thead
      tr%(field_headers)s
        %%th
        %%th
        %%th
    tbody
      - for %(name)s in object_list
        tr%(fields)s
          td
            a href="{{ url_for('.show', id=%(name)s.id) }}" Show
          td
            a href="{{ url_for('.edit', id=%(name)s.id) }}" Edit
          td
            a href="{{ url_for('.delete', id=%(name)s.id) }}" data-confirm="Are you sure?" data-method="delete" Delete

  a href="{{ url_for('.new') }}" New %(name)s
'''
create_templates.index_field = '''
          td {{ %(name)s.%(field_name)s }}'''
create_templates.index_field_header = '''
        th %(field_header)s'''
create_templates.show_scaffold = '''- extends 'layout.slim'
- from 'helpers.slim' import flashed

- block content
  {{ flashed() }}%(fields)s
  a href="{{ url_for('.edit', id=%(name)s.id) }}" Edit
  a href="{{ url_for('.index') }}" Back
'''
create_templates.show_field = '''
  p
    strong %(field_header)s:
  p {{ %(name)s.%(field_name)s }}
'''
create_templates.edit_scaffold = '''- extends 'layout.slim'

- block content
    h2 Editing %(name)s
    - include '%(name)s/_%(name)s_form.slim'
    a href="{{ url_for('.show', id=%(name)s.id) }}" Show
    a href="{{ url_for('.index') }}" Back
'''
create_templates.new_scaffold = '''- extends 'layout.slim'

- block content
    h2 Creating new %(name)s
    - include '%(name)s/_%(name)s_form.slim'
    a href="{{ url_for('.index') }}" Back
'''

@manager.command
def create_scaffold(name, fields=''):
    """
    Creates scaffold - model, model form, views, templates and routes.
    """
    create_model(name, fields)
    create_view(name, fields)
    create_routes(name)


if __name__ == '__main__':
    manager.run()

########NEW FILE########
__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

from werkzeug import import_string
import sys, os
sys.path.append(os.path.abspath('%s/..' % os.path.dirname(__file__)))

import main
app = main.app

from config import settings, db

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
import_string('models', silent=True)
for blueprint_name, blueprint in app.blueprints.iteritems():
    import_string('%s.models' % blueprint.import_name, silent=True)
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
    url = settings.SQLALCHEMY_DATABASE_URI
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    core_configs = config.get_section(config.config_ini_section)
    core_configs['sqlalchemy.url'] = settings.SQLALCHEMY_DATABASE_URI
    engine = engine_from_config(
                core_configs,
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
__FILENAME__ = 156299c3cdf7_create_post_table
"""Create post table.

Revision ID: 156299c3cdf7
Revises: None
Create Date: 2013-03-24 22:43:55.314753

"""

# revision identifiers, used by Alembic.
revision = '156299c3cdf7'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('post',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=True),
    sa.Column('title', sa.String(length=200), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('post')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 2dedad1c5f6_create_comment_table
"""Create comment table.

Revision ID: 2dedad1c5f6
Revises: 156299c3cdf7
Create Date: 2013-03-24 23:15:30.406323

"""

# revision identifiers, used by Alembic.
revision = '2dedad1c5f6'
down_revision = '156299c3cdf7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('comment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('commenter', sa.String(length=80), nullable=True),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('post_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('comment')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = serve_app_gevent
from gevent.monkey import patch_all
patch_all()

def run_server(app, port=8080):
    from gevent.pywsgi import WSGIServer
    http_server = WSGIServer(('', port), app)
    http_server.serve_forever()

if __name__ == '__main__':
    import main
    run_server(main.app)

########NEW FILE########
__FILENAME__ = serve_app_tornado

def run_server(app, port=8080):
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    # Initialize app and serve.
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(port)
    IOLoop.instance().start()

if __name__ == '__main__':
    import main
    run_server(main.app)

########NEW FILE########
