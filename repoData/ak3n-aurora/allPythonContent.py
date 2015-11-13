__FILENAME__ = app
import os

from flask import Flask, render_template, url_for, g, request, redirect

# Config
from .config import BaseConfig

# Utils
from .utils import make_dir

# Extensions
from .extensions import db, login_manager, debugtoolbar, gravatar

# Models
from .users.models import User
from .projects.models import Project
from .tasks.models import Task
from .deployments.models import Deployment

# Blueprints
from .users.views import users
from .projects.views import projects
from .stages.views import stages
from .tasks.views import tasks
from .notifications.views import notifications
from .frontend.views import frontend
from .deployments.views import deployments

__all__ = ['create_app']

DEFAULT_BLUEPRINTS = [
    frontend,
    projects,
    stages,
    tasks,
    notifications,
    deployments,
    users,
]


def create_app(config=None, app_name=None, blueprints=None):
    """Create a Flask app."""

    if app_name is None:
        app_name = BaseConfig.PROJECT
    if blueprints is None:
        blueprints = DEFAULT_BLUEPRINTS

    app = Flask(app_name, instance_relative_config=True)

    configure_app(app, config)
    configure_blueprints(app, blueprints)
    configure_extensions(app)
    configure_hook(app)
    configure_logging(app)
    configure_context_processors(app)
    configure_error_handlers(app)

    return app


def configure_app(app, config=None):
    # Default configuration
    app.config.from_object(BaseConfig)

    app.template_folder = BaseConfig.template_folder
    app.static_folder = BaseConfig.static_folder

    if config:
        if isinstance(config, basestring):
            app.config.from_pyfile(config)
        else:
            app.config.from_object(config)
    elif os.path.exists(BaseConfig.AURORA_SETTINGS):
        app.config.from_pyfile(BaseConfig.AURORA_SETTINGS)

    app.template_folder = BaseConfig.template_folder
    app.static_folder = BaseConfig.static_folder

    # Make dirs
    make_dir(app.config['AURORA_PATH'])
    make_dir(app.config['AURORA_PROJECTS_PATH'])
    make_dir(app.config['AURORA_TMP_PATH'])
    make_dir(app.config['AURORA_TMP_DEPLOYMENTS_PATH'])
    make_dir(app.config['LOG_FOLDER'])


def configure_hook(app):
    from flask.ext.login import current_user

    @app.before_request
    def check_login():
        g.user = current_user if current_user.is_authenticated() else None

        if (request.endpoint and request.endpoint != 'static' and
           (not getattr(app.view_functions[request.endpoint],
            'is_public', False)
           and g.user is None)):
            return redirect(url_for('frontend.login', next=request.path))


def configure_blueprints(app, blueprints):
    """Configure blueprints in views."""

    for blueprint in blueprints:
        app.register_blueprint(blueprint)


def configure_extensions(app):
    # flask-sqlalchemy
    db.init_app(app)

    # flask-login
    @login_manager.user_loader
    def load_user(id):
        return User.query.get(id)

    login_manager.init_app(app)

    # flask-debugtoolbar
    debugtoolbar(app)

    # flask-gravatar
    gravatar.init_app(app)


def configure_logging(app):
    """Configure file(info) and email(error) logging."""

    if app.debug or app.testing:
        # Skip debug and test mode. Just check standard output.
        return

    import logging.handlers
    # Set info level on logger, which might be overwritten by handlers.
    # Suppress DEBUG messages.
    app.logger.setLevel(logging.INFO)

    info_log = os.path.join(app.config['LOG_FOLDER'], 'info.log')
    info_file_handler = logging.handlers.RotatingFileHandler(
        info_log, maxBytes=100000, backupCount=10)
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]')
    )
    app.logger.addHandler(info_file_handler)


def configure_context_processors(app):
    """Configure contest processors."""

    @app.context_processor
    def projects():
        """Returns all projects."""
        return {'projects': Project.query.all()}

    @app.context_processor
    def version():
        from . import __version__
        return {'AURORA_VERSION': __version__}

    @app.context_processor
    def recent_deployments():
        def get_recent_deploments(object):
            if object.__tablename__ == 'projects':
                stages_ids = [stage.id for stage in object.stages]
                result = Deployment.query.filter(
                    Deployment.stage_id.in_(stages_ids))
            if object.__tablename__ == 'stages':
                result = Deployment.query.filter_by(stage_id=object.id)
            if object.__tablename__ == 'tasks':
                result = Deployment.query.filter(
                    Deployment.tasks.any(Task.id.in_([object.id])))
            if object.__tablename__ == 'users':
                result = Deployment.query.filter_by(user_id=object.id)
            return result.order_by('started_at desc').limit(3).all()
        return dict(get_recent_deployments=get_recent_deploments)

    # # To exclude caching of static
    @app.context_processor
    def override_url_for():
        return dict(url_for=dated_url_for)

    def dated_url_for(endpoint, **values):
        if endpoint == 'static':
            filename = values.get('filename', None)
            if filename:
                file_path = os.path.join(app.static_folder, filename)
                values['q'] = int(os.stat(file_path).st_mtime)
        return url_for(endpoint, **values)


def configure_error_handlers(app):

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/page_not_found.html"), 404

    @app.errorhandler(500)
    def server_error_page(error):
        return render_template("errors/server_error.html"), 500

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-


class BaseConfig(object):
    import os

    PROJECT = "aurora"

    app_folder = os.path.abspath(os.path.dirname(__file__))
    template_folder = os.path.join(app_folder, 'templates')
    static_folder = os.path.join(app_folder, 'static')

    DEBUG = False
    TESTING = False

    CSRF_ENABLED = True
    # http://flask.pocoo.org/docs/quickstart/#sessions
    SECRET_KEY = 'aurora-secret-key'

    # sqlalchemy settings
    # sqlite
    SQLALCHEMY_DATABASE_URI = 'sqlite:///aurora.db'
    # postgresql
    #SQLALCHEMY_DATABASE_URI = 'postgresql://aurora:aurora@localhost:5432/' + \
    #    'auroradb'

    # Aurora paths
    AURORA_PATH = os.path.join(os.path.expanduser('~'), '.aurora')
    AURORA_SETTINGS = os.path.join(AURORA_PATH, 'settings.py')
    AURORA_PROJECTS_PATH = os.path.join(AURORA_PATH, 'projects')
    AURORA_TMP_PATH = '/tmp/aurora'
    AURORA_TMP_DEPLOYMENTS_PATH = os.path.join(AURORA_TMP_PATH, 'deployments')
    LOG_FOLDER = os.path.join(AURORA_PATH, 'logs')

    # Debug toolbar settings
    DEBUG_TB_INTERCEPT_REDIRECTS = False


class TestConfig(BaseConfig):
    TESTING = True
    CSRF_ENABLED = False

    SQLALCHEMY_ECHO = False
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

########NEW FILE########
__FILENAME__ = decorators
from multiprocessing import Process
from functools import wraps

from flask import g, redirect, request, url_for

from .utils import notify, get_session


def public(location):
    """Makes location public"""
    location.is_public = True
    return location


def must_be_able_to(action):
    """Checks if user can do action, if not notifys him and redirects back."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user.can(action):
                notify(u"You can't do that. You don't have permission.",
                       category='error', action=action)
                return redirect(request.args.get('next')
                                or request.referrer
                                or url_for('frontend.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def notify_result(function):
    """Notifies using result from decorated function."""
    @wraps(function)
    def decorated_function(*args, **kwargs):
        result = function(*args, **kwargs)
        notify(**result)
        return function
    return decorated_function


def task(function):
    """Runs function using multiprocessing."""
    def decorated_function(*args, **kwargs):
        process = Process(target=function, args=args + (get_session(),),
                          kwargs=kwargs)

        if function.__name__ == 'deploy':
            from .deployments.views import current_deployments
            deployment_id = str(args[0])
            current_deployments[deployment_id] = process

        process.start()
    return decorated_function

########NEW FILE########
__FILENAME__ = constants
STATUSES = {
    "READY": 1,
    "RUNNING": 2,
    "COMPLETED": 3,
    "CANCELED": 4,
    "FAILED": 5,
}

BOOTSTRAP_ALERTS = {
    STATUSES['COMPLETED']: 'success',
    STATUSES['FAILED']: 'error',
    STATUSES['READY']: 'info',
    STATUSES['RUNNING']: 'info',
    STATUSES['CANCELED']: 'error'
}

########NEW FILE########
__FILENAME__ = models
import time
import os
from datetime import datetime

from flask import url_for, current_app

from ..extensions import db
from ..tasks.models import Task

from .constants import STATUSES, BOOTSTRAP_ALERTS


deployments_tasks_table = db.Table('deployments_tasks', db.Model.metadata,
                                   db.Column('deployment_id', db.Integer,
                                             db.ForeignKey('deployments.id')),
                                   db.Column('task_id', db.Integer,
                                             db.ForeignKey('tasks.id')))


class Deployment(db.Model):
    __tablename__ = "deployments"
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.SmallInteger, default=STATUSES['READY'])
    branch = db.Column(db.String(32), default='master')
    commit = db.Column(db.String(128))
    started_at = db.Column(db.DateTime(), default=datetime.now)
    finished_at = db.Column(db.DateTime())
    code = db.Column(db.Text())
    log = db.Column(db.Text())
    # Relations
    stage_id = db.Column(db.Integer(),
                         db.ForeignKey('stages.id'), nullable=False)
    user_id = db.Column(db.Integer(),
                        db.ForeignKey('users.id'), nullable=False)
    tasks = db.relationship(Task,
                            secondary=deployments_tasks_table,
                            backref="deployments")

    def get_tmp_path(self):
        return os.path.join(current_app.config['AURORA_TMP_DEPLOYMENTS_PATH'],
                            '{0}'.format(self.id))

    def bootstrap_status(self):
        return BOOTSTRAP_ALERTS[self.status]

    def show_status(self):
        for status, number in STATUSES.iteritems():
            if number == self.status:
                return status

    def is_running(self):
        return self.status == STATUSES['RUNNING']

    def show_tasks_list(self):
        template = '<a href="{0}">{1}</a>'
        return ', '.join([template.format(url_for('tasks.view', id=task.id),
                                          task.name) for task in self.tasks])

    def get_log_path(self):
        return os.path.join(self.get_tmp_path(), 'log')

    def get_log_lines(self):
        if self.log:
            return self.log.split('\n')

        path = os.path.join(self.get_tmp_path(), 'log')
        if os.path.exists(path):
            return open(path).readlines()

        return []

    def show_duration(self):
        delta = self.finished_at - self.started_at
        return time.strftime("%H:%M:%S", time.gmtime(delta.seconds))

    def show_commit(self):
        return "{0}".format(self.commit[:10]) if self.commit else ''

    def __init__(self, *args, **kwargs):
        super(Deployment, self).__init__(*args, **kwargs)

        self.code = [self.stage.project.code, self.stage.code]
        for task in self.stage.tasks:
            self.code.append(task.code)
        self.code = '\n'.join(self.code)

########NEW FILE########
__FILENAME__ = tasks
import os
import imp
import sys
from datetime import datetime

from git import Repo
from fabric.api import execute

from ..decorators import notify_result, task

from .models import Deployment
from .constants import STATUSES


@task
@notify_result
def deploy(deployment_id, session):
    """Runs given deployment."""
    deployment = session.query(Deployment).filter_by(id=deployment_id).first()

    result = {
        'session': session,
        'action': 'create_deployment',
        'category': 'error',
        'user_id': deployment.user_id
    }

    # Create deployment dir
    deployment_tmp_path = deployment.get_tmp_path()
    os.makedirs(deployment_tmp_path)

    deployment_project_tmp_path = os.path.join(
        deployment_tmp_path, deployment.stage.project.get_name_for_path())

    # Copy project's repo if exists, else create an empty folder
    if deployment.stage.project.repository_folder_exists():
        os.system('cp -rf {0} {1}'.format(deployment.stage.project.get_path(),
                                          deployment_project_tmp_path))
    else:
        os.makedirs(deployment_project_tmp_path)

    # Change dir
    os.chdir(deployment_project_tmp_path)

    # Checkout to commit if repo exists
    if deployment.stage.project.repository_folder_exists():
        deployment_repo = Repo.init(deployment_project_tmp_path)
        deployment_repo.git.checkout(deployment.commit)

    # Create module
    module = imp.new_module("deployment_{0}".format(deployment.id))

    # Replace stdout and stderr
    log_path = os.path.join(deployment_tmp_path, 'log')

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = sys.stderr = open(log_path, 'w', 0)

    try:
        print 'Deployment has started.'

        exec deployment.code in module.__dict__

        for task in deployment.tasks:
            # Execute task
            execute(eval('module.' + task.get_function_name()))

        print 'Deployment has finished.'
    except Exception as e:
        deployment.status = STATUSES['FAILED']
        print 'Deployment has failed.'
        print 'Error: {0}'.format(e.message)

        result['message'] = """"{0}" deployment has failed.""" \
            .format(deployment.stage)

    finally:
        # Return stdout and stderr
        sys.stdout.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        log_file = open(log_path)

        # If status has not changed
        if deployment.status == STATUSES['RUNNING']:
            deployment.status = STATUSES['COMPLETED']

    deployment.log = '\n'.join(log_file.readlines())
    deployment.finished_at = datetime.now()
    session.add(deployment)
    session.commit()

    # If deployment is successfull
    if deployment.status == STATUSES['COMPLETED']:
        result['category'] = 'success'
        result['message'] = """"{0}" has been deployed successfully.""" \
            .format(deployment.stage)

    return result

########NEW FILE########
__FILENAME__ = views
import json
from datetime import datetime

from flask import (Blueprint, Response, render_template, request, g, redirect,
                   url_for)

from ..utils import get_or_404, notify, build_log_result
from ..extensions import db
from ..decorators import must_be_able_to
from ..stages.models import Stage
from ..tasks.models import Task

from .tasks import deploy
from .models import Deployment
from .constants import STATUSES

deployments = Blueprint('deployments', __name__, url_prefix='/deployments')

current_deployments = {}


@deployments.route('/create/stage/<int:id>', methods=['POST', 'GET'])
@must_be_able_to('create_deployment')
def create(id):
    stage = get_or_404(Stage, id=id)
    clone_id = request.args.get('clone')

    if request.method == 'POST':
        tasks_ids = request.form.getlist('selected')

        if tasks_ids == []:
            return "You must select tasks for deployment."

        tasks = [get_or_404(Task, id=int(task_id)) for task_id in tasks_ids]
        branch = request.form.get('branch')
        commit = request.form.get('commit')

        if not commit and stage.project.get_repo() is not None:
            commit = stage.project.get_last_commit(branch).hexsha

        deployment = Deployment(stage=stage, tasks=tasks,
                                branch=branch, user=g.user, commit=commit,
                                status=STATUSES['RUNNING'])
        db.session.add(deployment)
        db.session.commit()

        deploy(deployment.id)
        return redirect(url_for('deployments.view', id=deployment.id))

    if stage.project.get_or_create_parameter_value('fetch_before_deploy')\
            == 'True':
        # Fetch
        stage.project.fetch()

    branches = stage.project.get_branches()
    if clone_id:
        clone_deployment = get_or_404(Deployment, id=clone_id)

        if clone_deployment.stage.id != stage.id:
            return "Clone deployment should have the same stage."

        # Select clone deployment's branch
        branch = None
        if branches:
            for branch_item in branches:
                if branch_item.name == clone_deployment.branch:
                    branch = branch_item
    else:
        clone_deployment = None
        branch = branches[0] if branches else None

    return render_template('deployments/create.html', stage=stage,
                           branch=branch, clone_deployment=clone_deployment)


@deployments.route('/view/<int:id>')
def view(id):
    deployment = get_or_404(Deployment, id=id)
    return render_template('deployments/view.html', deployment=deployment)


@deployments.route('/code/<int:id>/fabfile.py')
def raw_code(id):
    deployment = get_or_404(Deployment, id=id)
    return Response(deployment.code, mimetype='text/plain')


@deployments.route('/log/<int:id>')
def log(id):
    """
    Function for getting log for deployment in real time.
    Built on server-sent events.
    """
    deployment = get_or_404(Deployment, id=id)
    last_event_id = request.args.get('lastEventId')

    lines = deployment.get_log_lines()
    # If client just connected return all existing log
    result = ['id: {0}'.format(len(lines))]
    if not last_event_id:
        result.extend(build_log_result(lines))
    # else return new lines.
    else:
        new_lines = lines[int(last_event_id):]
        result.extend(build_log_result(new_lines))

    # len(result) == 1 means that no new lines were added
    # and then deployment's log is not updating.
    if len(result) == 1:
        status = deployment.show_status()
        result = 'data: {"event": "finished", "status": "' + status + '"}\n'
    else:
        result = '\n'.join(result)

    return Response(result + '\n\n', mimetype='text/event-stream')


@deployments.route('/stop', methods=['POST'])
def cancel():
    id = request.form.get('id')
    deployment = get_or_404(Deployment, id=id)
    action = 'cancel_deployment'
    if g.user.can(action) and id:
        try:
            current_deployments[id].terminate()
            current_deployments[id].join()
            current_deployments.pop(id)

            deployment.log = '\n'.join(deployment.get_log_lines())
            deployment.log += "Deployment has canceled."
            deployment.finished_at = datetime.now()
            deployment.status = STATUSES['CANCELED']

            db.session.add(deployment)
            db.session.commit()

            message = "Deployment has canceled successfully."
            category = 'success'
        except Exception, e:
            message = "Can't cancel deployment.\n" + \
                      "Error: {0}".format(e.message)
            category = 'error'

        notify(message, category=category, action=action)
        return json.dumps({'error': True if category == 'error' else False})

    notify("You can't execute this action.", category='error', action=action)
    return json.dumps({'error': True})

########NEW FILE########
__FILENAME__ = extensions
# -*- coding: utf-8 -*-

from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from flask.ext.login import LoginManager
login_manager = LoginManager()

from flask.ext.debugtoolbar import DebugToolbarExtension
debugtoolbar = DebugToolbarExtension

from flask.ext.gravatar import Gravatar
gravatar = Gravatar(default='identicon', rating='g')

########NEW FILE########
__FILENAME__ = forms
from flask.ext.wtf import (Form, Email, Required, TextField, BooleanField,
                           PasswordField)


class LoginForm(Form):
    email = TextField('Email', validators=[Required(), Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Remember me', default=False)

########NEW FILE########
__FILENAME__ = views
from flask import Blueprint, render_template, redirect, g, url_for, request
from flask.ext.login import login_user, logout_user, current_user

from ..decorators import public
from ..users.models import User
from ..deployments.models import Deployment

from .forms import LoginForm

frontend = Blueprint('frontend', __name__)


@frontend.route('/')
def index():
    deployments = Deployment.query.order_by('started_at desc').limit(10).all()
    return render_template('frontend/index.html', deployments=deployments)


@frontend.route('/login', methods=['GET', 'POST'])
@public
def login():
    if g.user is not None:
        return redirect(url_for('frontend.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user, authenticated = User.authenticate(form.email.data,
                                                form.password.data)
        if user and authenticated:
            if login_user(user, remember=form.remember_me.data):
                return redirect(request.args.get('next') or
                                url_for('frontend.index'))

        form.password.errors = [u'Invalid password.']

    return render_template('frontend/login.html', form=form)


@frontend.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('frontend.index'))

########NEW FILE########
__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from alembic.config import Config
from sqlalchemy import engine_from_config, pool
from flask.ext.sqlalchemy import SQLAlchemy
from logging.config import fileConfig
from flask.ext.alembic import FlaskAlembicConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = FlaskAlembicConfig("aurora_app/migrations/alembic.ini")

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from flask import current_app
with current_app.app_context():
    # set the database url
    config.set_main_option('sqlalchemy.url', current_app.config.get('SQLALCHEMY_DATABASE_URI'))
    flask_app = __import__('%s' % ('aurora_app'), fromlist=[current_app.name]).create_app()

db_obj = SQLAlchemy(flask_app)
target_metadata = db_obj.metadata

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
__FILENAME__ = 141ceff13f17_change_commit_size
"""Change commit size.

Revision ID: 141ceff13f17
Revises: None
Create Date: 2013-07-24 00:15:10.951231

"""

# revision identifiers, used by Alembic.
revision = '141ceff13f17'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('deployments', 'commit', type_=sa.String(128),
                    existing_type=sa.String(32))


def downgrade():
    op.alter_column('deployments', 'commit', type_=sa.String(32),
                    existing_type=sa.String(128))

########NEW FILE########
__FILENAME__ = 370b494d9871_
"""empty message

Revision ID: 370b494d9871
Revises: 47195a8a23f3
Create Date: 2013-08-02 05:29:04.130195

"""

# revision identifiers, used by Alembic.
revision = '370b494d9871'
down_revision = '47195a8a23f3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('project_parameters',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('value', sa.String(length=128), nullable=False),
    sa.Column('type', sa.SmallInteger(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('project_parameters')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 47195a8a23f3_
"""empty message

Revision ID: 47195a8a23f3
Revises: 141ceff13f17
Create Date: 2013-08-01 22:42:39.423301

"""

# revision identifiers, used by Alembic.
revision = '47195a8a23f3'
down_revision = '141ceff13f17'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=120),
               nullable=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=120),
               nullable=True)
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from ..extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(), default=datetime.now)
    message = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(32))
    action = db.Column(db.String(32))
    seen = db.Column(db.Boolean(), default=False)
    # Relations
    user_id = db.Column(db.Integer(),
                        db.ForeignKey('users.id'))

    def __init__(self, *args, **kwargs):
        super(Notification, self).__init__(*args, **kwargs)

    def __repr__(self):
        return u"<Notification #{0}>".format(self.id)

########NEW FILE########
__FILENAME__ = views
from flask import Blueprint, render_template, g, Response

from ..extensions import db

from .models import Notification

notifications = Blueprint('notifications', __name__,
                          url_prefix='/notifications')


@notifications.route('/')
def all():
    notifications = Notification.query.order_by("created_at desc").all()
    return render_template('notifications/all.html',
                           notifications=notifications)


@notifications.route('/unseen')
def unseen():
    """Returns unseen notifications and updates them as seen."""
    notifications = Notification.query.filter_by(seen=False, user=g.user) \
                                      .order_by('created_at').all()

    notifications_for_response = []
    # Update notifications
    for notification in notifications:
        notification.seen = True
        category = 'danger' if notification.category == 'error' else \
            notification.category
        notifications_for_response.append({'message': notification.message,
                                           'category': category})
    db.session.commit()

    def generate():
        for notification in notifications_for_response:
            result = 'data: {\n' + \
                     'data: "message": "{0}",\n'.format(
                         notification['message'].replace('\"', '\\\"')) +\
                     'data: "category": "{0}"\n'.format(
                         notification['category']) +\
                     'data: }\n\n'
            yield result

    return Response(generate(), mimetype='text/event-stream')

########NEW FILE########
__FILENAME__ = constants
PARAMETER_TYPES = {
    "INT": 1,
    "STR": 2,
    "BOOL": 3
}

DEFAULT_PARAMETERS = {
    'fetch_before_deploy': {'value': 'True',
                            'type': PARAMETER_TYPES['BOOL']}
}

########NEW FILE########
__FILENAME__ = exceptions
class ParameterValueError(Exception):
    pass

########NEW FILE########
__FILENAME__ = forms
from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.orm import model_form

from ..extensions import db

from .models import Project

ProjectForm = model_form(Project, db.session, Form)

########NEW FILE########
__FILENAME__ = models
import os

from git import Repo
from flask import current_app

from ..extensions import db
from ..stages.models import Stage

from .constants import DEFAULT_PARAMETERS, PARAMETER_TYPES
from .exceptions import ParameterValueError


class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    description = db.Column(db.String(128), default='')
    repository_path = db.Column(db.String(128), default='')
    code = db.Column(db.Text(), default='')
    # Relations
    stages = db.relationship(Stage, backref="project")
    params = db.relationship("ProjectParameter", backref="project")

    def __init__(self, *args, **kwargs):
        super(Project, self).__init__(*args, **kwargs)

    def create_default_params(self):
        for parameter_name in DEFAULT_PARAMETERS.keys():
            self.create_default_parameter(parameter_name)

    def create_default_parameter(self, name):
        parameter_dict = DEFAULT_PARAMETERS[name]
        parameter_dict['name'] = name
        parameter_dict['project_id'] = self.id
        parameter = ProjectParameter(**parameter_dict)
        db.session.add(parameter)
        db.session.commit()
        return parameter

    def get_or_create_parameter_value(self, name):
        for parameter in self.params:
            if parameter.name == name:
                return parameter.value

        return self.create_default_parameter(name).value

    def get_name_for_path(self):
        return self.name.lower().replace(' ', '_')

    def get_path(self):
        """Returns path of project's git repository on local machine."""
        return os.path.join(current_app.config['AURORA_PROJECTS_PATH'],
                            self.get_name_for_path())

    def repository_folder_exists(self):
        return os.path.exists(self.get_path())

    def get_repo(self):
        if self.repository_folder_exists():
            return Repo.init(self.get_path())
        return None

    def get_branches(self):
        repo = self.get_repo()
        if repo:
            return [ref for ref in repo.refs if ref.name != 'origin/HEAD']
        return None

    def get_commits(self, branch, max_count, skip):
        repo = self.get_repo()
        if repo:
            return repo.iter_commits(branch, max_count=max_count,
                                     skip=skip)
        return None

    def get_all_commits(self, branch, skip=None):
        repo = self.get_repo()
        if repo:
            return repo.iter_commits(branch, skip=skip)
        return None

    def get_last_commit(self, branch):
        repo = self.get_repo()
        if repo:
            return repo.iter_commits(branch).next()
        return None

    def get_commits_count(self, branch):
        repo = self.get_repo()
        if repo:
            return reduce(lambda x, _: x + 1, repo.iter_commits(branch), 0)
        return None

    def fetch(self):
        repo = self.get_repo()
        if repo:
            return repo.git.fetch()

    def __repr__(self):
        return self.name


class ProjectParameter(db.Model):
    __tablename__ = "project_parameters"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    value = db.Column(db.String(128), nullable=False)
    type = db.Column(db.SmallInteger, nullable=False)
    # Relations
    project_id = db.Column(db.Integer(), db.ForeignKey('projects.id'),
                           nullable=False)

    def set_value(self, value):
        if self.type == PARAMETER_TYPES['BOOL']:
            values = ['True', 'False']
            if value not in values:
                raise ParameterValueError('Wrong value for bool parameter.')
        elif self.type == PARAMETER_TYPES['INT']:
            try:
                int(value)
            except ValueError:
                raise ParameterValueError('Wrong value for int parameter.')

        self.value = value

    def __init__(self, *args, **kwargs):
        super(ProjectParameter, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = tasks
import os

from ..decorators import task, notify_result


@task
@notify_result
def clone_repository(project, session, user_id=None):
    """Clones project's repository to Aurora folder."""
    result = {
        'session': session,
        'action': 'clone_repository',
        'user_id': user_id,
        'category': 'error'
    }

    if project.repository_path == '':
        result['message'] = """Can't clone "{0}" repository without path.""" \
            .format(project.name)
        return result

    project_path = project.get_path()
    if os.path.exists(project_path):
        result['message'] = """Can't clone "{0}" repository.""" \
            .format(project.name) + \
            """ "{0}" is exists.""".format(project_path)
        return result

    os.system('git clone {0} {1}'.format(project.repository_path, project_path))

    if not os.path.exists(project_path):
        result['message'] = """Can't clone "{0}" repository.\n""" \
            .format(project.name) + "Something gone wrong."
        return result

    result['category'] = 'success'
    result['message'] = 'Cloning "{0}" repository' \
        .format(project.name) + " has finished successfully."

    return result


@task
@notify_result
def remove_repository(project, session, user_id=None):
    """Removes project's repository in Aurora folder."""
    result = {
        'session': session,
        'action': 'remove_repository',
        'category': 'error',
        'user_id': user_id
    }
    project_path = project.get_path()
    if not os.path.exists(project_path):
        result['message'] = """Can't remove "{0}" repository.""" \
            .format(project.name) + " It's not exists."
        return result

    os.system('rm -rf {0}'.format(project_path))

    if os.path.exists(project_path):
        result['message'] = """Can't remove "{0}" repository.""" \
            .format(project.name) + " Something gone wrong."
        return result

    result['category'] = 'success'
    result['message'] = """"{0}" repository has removed successfully.""" \
        .format(project.name, project_path)
    return result

########NEW FILE########
__FILENAME__ = views
import json

from flask import Blueprint, render_template, url_for, redirect, request, g

from ..decorators import must_be_able_to
from ..extensions import db
from ..utils import get_or_404, notify

from .models import Project, ProjectParameter
from .exceptions import ParameterValueError
from .forms import ProjectForm
from .tasks import clone_repository, remove_repository

projects = Blueprint('projects', __name__, url_prefix='/projects')


@projects.route('/create', methods=['GET', 'POST'])
@must_be_able_to('create_project')
def create():
    form = ProjectForm()

    if form.validate_on_submit():
        project = Project()
        form.populate_obj(project)
        db.session.add(project)
        db.session.commit()

        project.create_default_params()

        notify(u'Project "{0}" has been created.'.format(project.name),
               category='success', action='create_project')
        return redirect(url_for('projects.view', id=project.id))

    return render_template('projects/create.html', form=form)


@projects.route('/view/<int:id>')
def view(id):
    project = get_or_404(Project, id=id)
    return render_template('projects/view.html', project=project)


@projects.route('/edit/<int:id>', methods=['GET', 'POST'])
@must_be_able_to('edit_project')
def edit(id):
    project = get_or_404(Project, id=id)
    form = ProjectForm(request.form, project)

    if form.validate_on_submit():
        form.params.data = project.params
        form.populate_obj(project)
        db.session.add(project)
        db.session.commit()

        notify(u'Project "{0}" has been updated.'.format(project.name),
               category='success', action='edit_project')
        return redirect(url_for('projects.view', id=id))

    return render_template('projects/edit.html', project=project, form=form)


@projects.route('/delete/<int:id>')
@must_be_able_to('delete_project')
def delete(id):
    project = get_or_404(Project, id=id)

    # Delete stages
    for stage in project.stages:
        db.session.delete(stage)
    # Delete params
    for param in project.params:
        db.session.delete(param)
    db.session.delete(project)
    db.session.commit()
    
    notify(u'Project "{0}" has been deleted.'.format(project.name),
           category='success', action='delete_project')

    return redirect(request.args.get('next')
                    or url_for('frontend.index'))

TASKS = {
    'clone_repository': clone_repository,
    'remove_repository': remove_repository
}


@projects.route('/execute/<int:id>', methods=['POST'])
def execute(id):
    project = get_or_404(Project, id=id)
    action = request.form.get('action')
    if g.user.can(action):
        if action == 'edit_project':
            name, value = request.form.get('name'), request.form.get('value')
            parameter = ProjectParameter.query.filter_by(name=name).first()

            try:
                parameter.set_value(value)
                db.session.add(parameter)
                db.session.commit()
            except ParameterValueError as e:
                notify(e.message, category='error', action='edit_project')
                return json.dumps({'error': True})
        else:
            TASKS[action](project)
        return json.dumps({'error': False})

    notify(u"""You can't execute "{0}.{1}".""".format(project.name, action),
           category='error', action=action, user_id=g.user.id)
    return json.dumps({'error': True})


@projects.route('/commits/<int:id>')
def commits(id):
    project = get_or_404(Project, id=id)
    branch = request.args.get('branch')
    query = request.args.get('query')
    page_limit = int(request.args.get('page_limit'))
    page = int(request.args.get('page'))

    if query:
        commits = project.get_all_commits(branch,
                                          skip=page_limit * page)
    else:
        commits = project.get_commits(branch, max_count=page_limit,
                                      skip=page_limit * (page - 1))

    result = []
    for commit in commits:
        if query and not (query in commit.hexsha or query in commit.message):
            continue
        else:
            result.append({'id': commit.hexsha,
                           'message': commit.message,
                           'title': "{0} - {1}".format(commit.hexsha[:10],
                                                       commit.message)})

    total = project.get_commits_count(branch)
    if query:
        total = len(result)
        result = result[:page_limit]

    return json.dumps({'total': total,
                       'commits': result})


@projects.route('/commits/one/<int:id>/<string:branch>/<string:commit>')
def get_one_commit(id, branch, commit):
    project = get_or_404(Project, id=id)
    commits = project.get_all_commits(branch)
    for item in commits:
        if commit == item.hexsha:
            return json.dumps({'id': item.hexsha,
                               'message': item.message,
                               'title': "{0} - {1}".format(item.hexsha[:10],
                                                           item.message)})
    return 'error', 500


@projects.route('/')
def all():
    projects = Project.query.all()
    return render_template('projects/all.html', projects=projects)

########NEW FILE########
__FILENAME__ = runner
from flask.ext.script import Manager, Server
from flask.ext.alembic import ManageMigrations

from aurora_app import create_app
from .extensions import db


def create_manager(app):
    manager = Manager(app)
    manager.add_option('-c', '--config',
                       dest="config",
                       required=False,
                       help="config file")

    manager.add_command("runserver", Server())
    manager.add_command("migrate", ManageMigrations(
        config_path='aurora_app/migrations/alembic.ini'))

    def create_superuser_dialog():
        import getpass
        from email.utils import parseaddr

        print "You need to create a superuser!"

        username = raw_input('Username [{0}]: '.format(getpass.getuser()))
        if not username:
            username = getpass.getuser()

        email = None
        while not email:
            email = parseaddr(raw_input('Email: '))[1]

        passwords = lambda: (getpass.getpass(),
                             getpass.getpass('Password (retype): '))

        password, retyped_password = passwords()

        while password == '' or password != retyped_password:
            print 'Passwords do not match or your password is empty!'
            password, retyped_password = passwords()

        return username, email, password

    @manager.command
    def init_config():
        """Creates settings.py in default folder."""
        import inspect
        from .config import BaseConfig
        lines = inspect.getsource(BaseConfig).split('\n')[1:]
        lines = [line[4:] for line in lines]
        open(BaseConfig.AURORA_SETTINGS, 'w').write('\n'.join(lines))
        print 'Configuration was written at: ' + BaseConfig.AURORA_SETTINGS

    @manager.command
    def init_db():
        """Creates aurora database."""
        from .users.models import User
        from .users.constants import ROLES

        db.create_all()

        username, email, password = create_superuser_dialog()

        superuser = User(username=username, password=password, email=email,
                         role=ROLES['ADMIN'])
        db.session.add(superuser)
        db.session.commit()

    return manager


def main():
    import os
    import sys

    if not os.path.exists('aurora.db') and not 'init_db' in sys.argv:
        print 'You need to run "init_db" at first.'
        return

    manager = create_manager(create_app)
    manager.run()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = forms
from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.orm import model_form

from ..extensions import db

from .models import Stage

StageForm = model_form(Stage, db.session, Form)

########NEW FILE########
__FILENAME__ = models
from ..extensions import db
from ..tasks.models import Task
from ..deployments.models import Deployment

stages_tasks_table = db.Table('stages_tasks', db.Model.metadata,
                              db.Column('stage_id', db.Integer,
                                        db.ForeignKey('stages.id')),
                              db.Column('task_id', db.Integer,
                                        db.ForeignKey('tasks.id')))


class Stage(db.Model):
    __tablename__ = "stages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    code = db.Column(db.Text(), default='')
    # Relations
    project_id = db.Column(db.Integer(), db.ForeignKey('projects.id'))
    deployments = db.relationship(Deployment, backref="stage")
    tasks = db.relationship(Task,
                            secondary=stages_tasks_table,
                            backref="stages")

    def __init__(self, *args, **kwargs):
        super(Stage, self).__init__(*args, **kwargs)

    def __repr__(self):
        return u"{0} / {1}".format(self.project.name, self.name) if \
            self.project else self.name
########NEW FILE########
__FILENAME__ = views
from flask import (Blueprint, render_template, request, redirect, url_for,
                   Response)

from ..decorators import must_be_able_to
from ..extensions import db
from ..utils import get_or_404, notify
from ..projects.models import Project
from ..deployments.models import Deployment

from .forms import StageForm
from .models import Stage

stages = Blueprint('stages', __name__, url_prefix='/stages')


@stages.route('/create', methods=['GET', 'POST'])
@must_be_able_to('create_stage')
def create():
    project_id = request.args.get('project_id', None)
    project = get_or_404(Project, id=project_id) if project_id else None
    form = StageForm(project=project)

    if form.validate_on_submit():
        stage = Stage()
        form.populate_obj(stage)
        db.session.add(stage)
        db.session.commit()

        notify(u'Stage "{0}" has been created.'.format(stage),
               category='success', action='create_stage')
        return redirect(url_for('stages.view', id=stage.id))

    return render_template('stages/create.html', form=form, id=project_id)


@stages.route('/view/<int:id>')
def view(id):
    stage = get_or_404(Stage, id=id)
    return render_template('stages/view.html', stage=stage)


@stages.route('/edit/<int:id>', methods=['GET', 'POST'])
@must_be_able_to('edit_stage')
def edit(id):
    stage = get_or_404(Stage, id=id)
    form = StageForm(request.form, stage)

    if form.validate_on_submit():
        # Since we don't show deployments in form, we need to set them here.
        form.deployments.data = stage.deployments
        form.populate_obj(stage)
        db.session.add(stage)
        db.session.commit()

        notify(u'Stage "{0}" has been updated.'.format(stage),
               category='success', action='edit_stage')
        return redirect(url_for('stages.view', id=stage.id))

    return render_template('stages/edit.html', stage=stage, form=form)


@stages.route('/delete/<int:id>')
@must_be_able_to('delete_stage')
def delete(id):
    stage = get_or_404(Stage, id=id)

    project_id = stage.project.id if stage.project else None

    notify(u'Stage "{0}" has been deleted.'.format(stage),
           category='success', action='delete_stage')

    db.session.delete(stage)
    db.session.commit()

    if project_id:
        return redirect(url_for('projects.view', id=project_id))

    return redirect(request.args.get('next')
                    or url_for('frontend.index'))


@stages.route('/')
def all():
    stages = Stage.query.all()
    return render_template('stages/all.html', stages=stages)


@stages.route('/export/<int:id>/fabfile.py')
def export(id):
    stage = get_or_404(Stage, id=id)

    deployment = Deployment(stage=stage, tasks=stage.tasks)
    return Response(deployment.code, mimetype='application/python')

########NEW FILE########
__FILENAME__ = forms
import re

from flask.ext.wtf import Form, ValidationError

from wtforms.ext.sqlalchemy.orm import model_form

from ..extensions import db

from .models import FUNCTION_NAME_REGEXP, Task


def task_code(form, field):
    functions_names_search = re.search(FUNCTION_NAME_REGEXP, field.data)

    if functions_names_search is None:
        raise ValidationError('Function name is not found.')

TaskForm = model_form(Task, db.session, Form, field_args={
    'code': {
        'validators': [task_code]
    }
})

########NEW FILE########
__FILENAME__ = models
import re

from ..extensions import db

FUNCTION_NAME_REGEXP = '^def (\w+)\(.*\):'


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    code = db.Column(db.Text(), default='')

    def __init__(self, *args, **kwargs):
        super(Task, self).__init__(*args, **kwargs)

    def get_function_name(self):
        functions_search = re.search(FUNCTION_NAME_REGEXP, self.code)
        return functions_search.group(1)

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = views
from flask import Blueprint, render_template, request, redirect, url_for

from ..decorators import must_be_able_to
from ..extensions import db
from ..utils import notify, get_or_404
from ..stages.models import Stage

from .models import Task
from .forms import TaskForm

tasks = Blueprint('tasks', __name__, url_prefix='/tasks')


@tasks.route('/create', methods=['GET', 'POST'])
@must_be_able_to('create_task')
def create():
    stage_id = request.args.get('stage_id', None)
    stage = get_or_404(Stage, id=stage_id) if stage_id else None
    form = TaskForm(stages=[stage])

    if form.validate_on_submit():
        task = Task()
        form.populate_obj(task)
        db.session.add(task)
        db.session.commit()

        notify(u'Task "{0}" has been created.'.format(task.name),
               category='success', action='create_task')
        return redirect(url_for('tasks.view', id=task.id))

    return render_template('tasks/create.html', form=form, stage_id=stage_id)


@tasks.route('/view/<int:id>')
def view(id):
    task = get_or_404(Task, id=id)
    return render_template('tasks/view.html', task=task)


@tasks.route('/edit/<int:id>', methods=['GET', 'POST'])
@must_be_able_to('edit_task')
def edit(id):
    task = get_or_404(Task, id=id)
    form = TaskForm(request.form, task)

    if form.validate_on_submit():
        # Since we don't show deployments in form, we need to set them here.
        form.deployments.data = task.deployments
        form.populate_obj(task)
        db.session.add(task)
        db.session.commit()

        notify(u'Task "{0}" has been updated.'.format(task.name),
               category='success', action='edit_task')
        return redirect(url_for('tasks.view', id=task.id))

    return render_template('tasks/edit.html', task=task, form=form)


@tasks.route('/delete/<int:id>')
@must_be_able_to('delete_task')
def delete(id):
    task = get_or_404(Task, id=id)

    notify(u'Task "{0}" has been deleted.'.format(task.name),
           category='success', action='delete_task')

    db.session.delete(task)
    db.session.commit()

    return redirect(request.args.get('next')
                    or url_for('frontend.index'))


@tasks.route('/')
def all():
    tasks = Task.query.all()
    return render_template('tasks/all.html', tasks=tasks)

########NEW FILE########
__FILENAME__ = constants
ROLES = {
    "USER": 1,
    "ADMIN": 2
}

# Permissons
PERMISSIONS = {
    ROLES["ADMIN"]: [
        # Projects
        "create_project", "edit_project", "delete_project",
        # Repositories
        "clone_repository", "remove_repository",
        # Stages
        "create_stage", "edit_stage", "delete_stage",
        # Deploments
        "create_deployment", "cancel_deployment",
        # Tasks
        "create_task", "edit_task", "delete_task",
        # Users
        "create_user", "edit_user", "delete_user"
    ],
    ROLES["USER"]: []
}

########NEW FILE########
__FILENAME__ = forms
from flask.ext.wtf import (Form, Email, Required, TextField, PasswordField,
                           SelectField)

from .constants import ROLES


class EditUserForm(Form):
    username = TextField('Username', validators=[Required()])
    password = PasswordField('Password')
    email = TextField('Email', validators=[Email()])
    role = SelectField(u'Role', coerce=int,
                       choices=[(v, k) for k, v in ROLES.iteritems()])


class CreateUserForm(EditUserForm):
    password = PasswordField('Password', validators=[Required()])

########NEW FILE########
__FILENAME__ = models
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import db

from .constants import ROLES, PERMISSIONS


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.SmallInteger, default=ROLES['USER'])
    # Relations
    deployments = db.relationship("Deployment", backref="user")
    notifications = db.relationship("Notification", backref="user")

    def __init__(self, username=None, password=None, email=None, role=None):
        self.username = username

        if password:
            self.set_password(password)

        self.email = email
        self.role = role

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def can(self, action):
        return action in PERMISSIONS[self.role]

    def show_role(self):
        for role, number in ROLES.iteritems():
            if number == self.role:
                return role

    @classmethod
    def authenticate(self, email, password):
        """
        Returns user and authentication status.
        """
        user = User.query.filter_by(email=email).first()
        if user is not None:
            if user.check_password(password):
                return user, True

        return user, False


    def __repr__(self):
        return u'<User {0}>'.format(self.username)

########NEW FILE########
__FILENAME__ = views
from flask import Blueprint, render_template, redirect, url_for, request, g

from ..decorators import must_be_able_to
from ..extensions import db
from ..utils import notify, get_or_404

from .models import User
from .forms import EditUserForm, CreateUserForm

users = Blueprint('users', __name__, url_prefix='/users')


@users.route('/create', methods=['GET', 'POST'])
@must_be_able_to('create_user')
def create():
    form = CreateUserForm()

    if form.validate_on_submit():
        user = User()
        form.populate_obj(user)
        user.set_password(form.password.data)

        # Check for duplicates
        if User.query.filter_by(username=form.username.data).first() is None:
            db.session.add(user)
            db.session.commit()

            notify(u'User "{0}" has been created.'.format(user.username),
                   category='success', action='create_user')
            return redirect(url_for('users.view', id=user.id))
        form.username.errors = [u'Choose another username, please.']

    return render_template('users/create.html', form=form)


@users.route('/view/<int:id>')
def view(id):
    user = get_or_404(User, id=id)
    return render_template('users/view.html', user=user)


@users.route('/')
def all():
    users = User.query.all()
    return render_template('users/all.html', users=users)


@users.route('/delete/<int:id>')
@must_be_able_to('delete_user')
def delete(id):
    user = get_or_404(User, id=id)

    notify(u'User "{0}" has been deleted.'.format(user.username),
           category='success', action='delete_user')

    db.session.delete(user)
    db.session.commit()

    return redirect(request.args.get('next')
                    or url_for('frontend.index'))


@users.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    user = get_or_404(User, id=id)

    if not (g.user.can('edit_user') or user.id == g.user.id):
        notify(u"You can't do that. You don't have permission.",
               category='error', action='edit_user')

        return redirect(request.args.get('next')
                        or request.referrer
                        or url_for('frontend.index'))

    form = EditUserForm(request.form, user)

    if form.validate_on_submit():
        form.populate_obj(user)

        if form.password.data:
            user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        notify(u'User "{0}" has been updated.'.format(user.username),
               category='success', action='edit_user')
        return redirect(url_for('users.view', id=id))

    return render_template('users/edit.html', user=user, form=form)

########NEW FILE########
__FILENAME__ = utils
import os

from flask import abort, g, current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .notifications.models import Notification
from .extensions import db


def make_dir(dir_path):
    try:
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)
    except Exception, e:
        raise e


def get_or_404(model, **kwargs):
    """Returns an object found with kwargs else aborts with 404 page."""
    obj = model.query.filter_by(**kwargs).first()
    if obj is None:
        abort(404)
    return obj


def notify(message, category=None, action=None, user_id=None,
           session=db.session):
    """Wrapper for creating notifications in database."""
    if user_id is None:
        try:
            user_id = g.user.id
        except:
            pass

    notification = Notification(message=message, category=category,
                                action=action, user_id=user_id)
    session.add(notification)
    session.commit()


def get_session():
    """Creates session for process"""
    engine = create_engine(current_app.config['SQLALCHEMY_DATABASE_URI'])
    Session = scoped_session(sessionmaker(bind=engine,
                                          autoflush=False,
                                          autocommit=False))
    session = Session()
    setattr(session, '_model_changes', dict())
    return session


def build_log_result(lines):
    result = []
    for line in lines:
        result.append('data: {\n' +
                      'data: "message": "{0}"\n'.format(
                          line.replace('\"', '\\\"').replace('\n', '')) +
                      'data: }\n')
    return result
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Aurora documentation build configuration file, created by
# sphinx-quickstart on Sat Aug  3 03:15:02 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Aurora'
copyright = u'2013, Eugene Akentyev'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __import__('pkg_resources').get_distribution('aurora').version
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Auroradoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Aurora.tex', u'Aurora Documentation',
   u'Eugene Akentyev', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'aurora', u'Aurora Documentation',
     [u'Eugene Akentyev'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Aurora', u'Aurora Documentation',
   u'Eugene Akentyev', 'Aurora', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
