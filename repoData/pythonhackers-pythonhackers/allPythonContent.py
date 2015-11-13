__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

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
target_metadata = None

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
__FILENAME__ = 127e0d40f05d_add_flags_to_project
"""add flags to projects

Revision ID: 127e0d40f05d
Revises: b4f4be61aa7
Create Date: 2013-12-22 09:52:38.357986

"""

# revision identifiers, used by Alembic.
revision = '127e0d40f05d'
down_revision = 'b4f4be61aa7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("os_project", sa.Column('hide', sa.Boolean))
    op.add_column("os_project", sa.Column('lang', sa.SmallInteger))


def downgrade():
    op.drop_column("os_project", 'hide')
    op.drop_column("os_project", 'lang')

########NEW FILE########
__FILENAME__ = 1f27928bf1a6_add_parent_field_to_
"""Add parent field to open source projects

Revision ID: 1f27928bf1a6
Revises: 4ee15a6a9f1c
Create Date: 2013-08-12 18:45:10.033955

"""

# revision identifiers, used by Alembic.
revision = '1f27928bf1a6'
down_revision = '4ee15a6a9f1c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('os_project', sa.Column('parent', sa.String(100)))


def downgrade():
    op.drop_column('os_project', 'parent')

########NEW FILE########
__FILENAME__ = 271328db402d_os_project_in_text
"""os_project in text

Revision ID: 271328db402d
Revises: 2d67c6e370bb
Create Date: 2013-11-30 17:24:08.977556

"""

# revision identifiers, used by Alembic.
revision = '271328db402d'
down_revision = '2d67c6e370bb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('os_project', 'description', type_=sa.Text)
    op.alter_column('os_project', 'name', type_=sa.Text)
    op.alter_column('os_project', 'slug', type_=sa.Text)
    op.alter_column('os_project', 'src_url', type_=sa.Text)
    op.alter_column('os_project', 'doc_url', type_=sa.Text)


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 2aa06b3e5853_add_channel_table
"""add channel table

Revision ID: 2aa06b3e5853
Revises: 4e34adcfd51d
Create Date: 2013-12-03 18:25:31.708420

"""

# revision identifiers, used by Alembic.
revision = '2aa06b3e5853'
down_revision = '4e34adcfd51d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'channel',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('name', sa.Text, nullable=False),
        sa.Column('slug', sa.Text, index=True, unique=True),
        sa.Column('created_at', sa.DateTime),
        sa.Column('post_count', sa.Integer),
        sa.Column('disabled', sa.Boolean),
    )


def downgrade():
    op.drop_table('channel')

########NEW FILE########
__FILENAME__ = 2d67c6e370bb_upgrade_for_social_i
"""Upgrade for social information

Revision ID: 2d67c6e370bb
Revises: 1f27928bf1a6
Create Date: 2013-08-18 11:37:33.445584

"""

# revision identifiers, used by Alembic.
revision = '2d67c6e370bb'
down_revision = '1f27928bf1a6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """


    """
    op.add_column('user', sa.Column('password', sa.String(120), nullable=True))
    op.add_column('user', sa.Column('first_name', sa.String(80), nullable=True))
    op.add_column('user', sa.Column('last_name', sa.String(120), nullable=True))
    op.add_column('user', sa.Column('loc', sa.String(50), nullable=True))

    op.add_column('user', sa.Column('follower_count', sa.Integer, nullable=True))
    op.add_column('user', sa.Column('following_count', sa.Integer, nullable=True))

    op.add_column('user', sa.Column('lang', sa.String(5), nullable=True))
    op.add_column('user', sa.Column('pic_url', sa.String(200), nullable=True))

    op.create_table(
        'social_user',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('acc_type', sa.String(2), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.Unicode(200), index=True),
        sa.Column('nick', sa.Unicode(64), index=True,),
        sa.Column('follower_count', sa.Integer),
        sa.Column('following_count', sa.Integer),
        sa.Column('ext_id', sa.String(50)),
        sa.Column('access_token', sa.String(100)),
        sa.Column('hireable', sa.Boolean),
    )


def downgrade():
    op.drop_column('user', 'password')
    op.drop_column('user', 'first_name')
    op.drop_column('user', 'last_name')
    op.drop_column('user', 'loc')

    op.drop_column('user', 'follower_count')
    op.drop_column('user', 'following_count')

    op.drop_column('user', 'lang')
    op.drop_column('user', 'pic_url')

    op.drop_table("social_user")


########NEW FILE########
__FILENAME__ = 32f93e2b03a3_add_pypi_packages
"""add pypi packages

Revision ID: 32f93e2b03a3
Revises: 127e0d40f05d
Create Date: 2013-12-25 13:57:49.200742

"""

# revision identifiers, used by Alembic.
revision = '32f93e2b03a3'
down_revision = '127e0d40f05d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'package',

        sa.Column('name', sa.Text,primary_key=True, nullable=False,index=True),

        sa.Column('author', sa.Text, nullable=True),
        sa.Column('author_email', sa.Text, nullable=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('url', sa.Text, nullable=True),
        sa.Column('mdown', sa.Integer, nullable=True),
        sa.Column('wdown', sa.Integer, nullable=True),
        sa.Column('ddown', sa.Integer, nullable=True),
        sa.Column('data', sa.Text, nullable=True),
        )

def downgrade():
    op.drop_table("package")

########NEW FILE########
__FILENAME__ = 3ec00f83b814_create_tutorial_obje
"""create tutorial object

Revision ID: 3ec00f83b814
Revises: 32f93e2b03a3
Create Date: 2014-01-07 18:16:33.130262

"""

# revision identifiers, used by Alembic.
revision = '3ec00f83b814'
down_revision = '32f93e2b03a3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'tutorial',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, nullable=False, index=True),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('keywords', sa.Text),
        sa.Column('meta_description', sa.Text),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_html', sa.Text),

        sa.Column('slug', sa.Text, index=True, nullable=False),
        sa.Column('upvote_count', sa.Integer),

        sa.Column('created_at', sa.DateTime),
        sa.Column('generated_at', sa.DateTime),

        sa.Column('publish', sa.Boolean, default=True),
        sa.Column('spam', sa.Boolean, default=False),
    )


def downgrade():
    op.drop_table('tutorial')

########NEW FILE########
__FILENAME__ = 43d4e52bb53f_add_category_to_proj
"""add category to projects

Revision ID: 43d4e52bb53f
Revises: 271328db402d
Create Date: 2013-12-01 06:41:46.068494

"""

# revision identifiers, used by Alembic.
revision = '43d4e52bb53f'
down_revision = '271328db402d'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column("os_project", sa.Column('categories', postgresql.ARRAY(sa.String)))


def downgrade():
    op.drop_column("os_project", 'categories')

########NEW FILE########
__FILENAME__ = 4e34adcfd51d_add_message_table
"""add message table

Revision ID: 4e34adcfd51d
Revises: 67ea78b2bbd
Create Date: 2013-12-01 09:44:30.690886

"""

# revision identifiers, used by Alembic.
revision = '4e34adcfd51d'
down_revision = '67ea78b2bbd'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        'message',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('user_id', sa.Integer, nullable=False, index=True),
        sa.Column('user_nick', sa.String(100)),
        sa.Column('reply_to_id', sa.BigInteger),
        sa.Column('reply_to_uid', sa.Integer),
        sa.Column('reply_to_uname', sa.Unicode(200)),
        sa.Column('ext_id', sa.String),
        sa.Column('ext_reply_id', sa.String),
        sa.Column('slug', sa.Text),
        sa.Column('content', sa.Text),
        sa.Column('content_html', sa.Text),
        sa.Column('lang', sa.String(3)),

        sa.Column('mentions', postgresql.ARRAY(sa.String)),
        sa.Column('urls', postgresql.ARRAY(sa.String)),
        sa.Column('tags', postgresql.ARRAY(sa.String)),
        sa.Column('media', postgresql.ARRAY(sa.String)),

        sa.Column('has_url', sa.Boolean),
        sa.Column('has_channel', sa.Boolean),

        sa.Column('karma', sa.Integer),
        sa.Column('up_votes', sa.Integer),
        sa.Column('down_votes', sa.Integer),
        sa.Column('favorites', sa.Integer),
        sa.Column('published_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('channel_id', sa.Integer),
        sa.Column('channels', postgresql.ARRAY(sa.String)),
        sa.Column('spam', sa.Boolean),
        sa.Column('flagged', sa.Boolean),
        sa.Column('deleted', sa.Boolean),
    )


def downgrade():
    op.drop_table('message')

########NEW FILE########
__FILENAME__ = 4ee15a6a9f1c_create_base_tables
"""create user table

Revision ID: 4ee15a6a9f1c
Revises: None
Create Date: 2013-08-08 21:01:38.192523

"""

# revision identifiers, used by Alembic.
revision = '4ee15a6a9f1c'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('nick', sa.String(64), unique=True, index=True, nullable=False),
        sa.Column('email', sa.Unicode(200), index=True, unique=True),
    )

    op.create_table(
        'os_project',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, index=True, nullable=False),
        sa.Column('description', sa.Unicode(500)),
        sa.Column('src_url', sa.Unicode(200)),
        sa.Column('doc_url', sa.Unicode(200)),
        sa.Column('starts', sa.Integer),
        sa.Column('watchers', sa.Integer),
        sa.Column('forks', sa.Integer),
    )


def downgrade():
    op.drop_table('user')
    op.drop_table('os_project')

########NEW FILE########
__FILENAME__ = 57e06acf468_add_actions_table
"""add actions table

Revision ID: 57e06acf468
Revises: 2aa06b3e5853
Create Date: 2013-12-03 18:52:50.010772

"""

# revision identifiers, used by Alembic.
revision = '57e06acf468'
down_revision = '2aa06b3e5853'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'action',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('from_id', sa.BigInteger, nullable=False),
        sa.Column('to_id', sa.BigInteger),
        sa.Column('action', sa.SmallInteger, nullable=False),
        sa.Column('created_at', sa.DateTime),
        sa.Column('deleted',sa.Boolean, default=False),
        sa.Column('deleted_at',sa.DateTime),
    )


def downgrade():
    op.drop_table('action')

########NEW FILE########
__FILENAME__ = 67ea78b2bbd_add_role_to_user_tab
"""add role to User table

Revision ID: 67ea78b2bbd
Revises: 43d4e52bb53f
Create Date: 2013-12-01 06:59:18.813595

"""

# revision identifiers, used by Alembic.
revision = '67ea78b2bbd'
down_revision = '43d4e52bb53f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("user", sa.Column("role", sa.Integer))


def downgrade():
    op.drop_column("user", "role")

########NEW FILE########
__FILENAME__ = b4f4be61aa7_add_buckets_table
"""add buckets table

Revision ID: b4f4be61aa7
Revises: 57e06acf468
Create Date: 2013-12-14 18:22:34.088866

"""

# revision identifiers, used by Alembic.
revision = 'b4f4be61aa7'
down_revision = '57e06acf468'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        'bucket',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, nullable=False, index=True),
        sa.Column('name', sa.Text, nullable=False),
        sa.Column('slug', sa.Text, index=True, nullable=False),
        sa.Column('follower_count', sa.Integer),
        sa.Column('projects', postgresql.ARRAY(sa.String)),
        sa.Column('created_at', sa.DateTime),
    )


def downgrade():
    op.drop_table('bucket')

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import run, sudo, env, task
from fabric.context_managers import cd
import logging
from fabtools import require

# env.hosts = []
setup = {
    'stg': {'dir': '/var/www/stg.pythonhackers.com', 'supervisor': 'staging_pythonhackers'},
    'prd': {'dir': '/var/www/beta.pythonhackers.com', 'supervisor': 'prod_pythonhackers'},
}

env.user = 'root'

PACKAGES = [
    'supervisor', 'vim', 'htop', 'build-essential',
    'postgresql-9.1', 'memcached', 'libpq-dev',
    'git-core', 'tig', 'redis-server',
    'postgresql-contrib-9.1', 'postgresql-client-9.1',
    'python-pip',
]
# 'newrelic-sysmond'
@task
def install_packages():
    require.deb.package(PACKAGES)


@task
def venv():
    run("pip install virtualenv")


@task
def restart_nginx():
    run("service nginx restart")

#"moreutils"

@task
def install_java():
    require.deb.packages(["openjdk-7-jdk", "openjdk-7-jre"], update=True)


@task
def restart_process(setup):
    project = setup['supervisor']
    sudo("supervisorctl restart {}".format(project))


@task
def glog():
    with cd(env.root):
        run("git log -2")


@task
def update_code(settings):
    with cd(settings['dir']):
        run("git pull")


# @task
# def install(*packages):
#     assert packages is not None
#     sudo("apt-get -y install %s" % packages)


@task
def ntp():
    require.deb.packages(["ntp"], update=True)
    sudo("service ntp restart")


@task
def deploy(settings='stg', restart=False):

    setting = setup[settings]

    update_code(setting)
    logging.warn("Should restart? %s %s" % (restart, bool(restart)))

    if bool(restart):
        restart_process(setting)
        log()


@task
def super(mode=""):
    sudo("supervisorctl %s" % mode)


@task
def hostname_check():
    run("hostname")


@task
def disc_status():
    run("df -h")

@task
def log(directory='/var/log/python/stg.pythonhackers/', tail_file='app.log'):
    with cd(directory):
        run("tail -f {}".format(tail_file))


@task
def nlog():
    with cd("/var/log/nginx/stg.pythonhackers.com"):
        run("tail -f access.log")


@task
def rabbitmq():
    require.deb.packages(["rabbitmq-server"], update=True)
    sudo("service rabbitmq-server restart")


@task
def redis():
    require.deb.packages(["redis-server"], update=True)
    sudo("service redis-server restart")


@task
def adduser(username, password, pubkey):
    require.user(username,
                 password=password,
                 ssh_public_keys=pubkey,
                 shell="/bin/bash")
    require.sudoer(username)
########NEW FILE########
__FILENAME__ = admin
import logging
from functools import partial
from flask.ext.login import current_user
from flask.ext.admin import Admin, BaseView, expose, Admin, AdminIndexView
from flask.ext.admin.contrib.sqlamodel import ModelView
from pyhackers.model.bucket import Bucket
from pyhackers.model.user import User, SocialUser
from pyhackers.model.os_project import OpenSourceProject
from pyhackers.model.message import Message
from pyhackers.model.channel import Channel
from pyhackers.model.action import Action
from pyhackers.model.package import Package
from pyhackers.model.tutorial import Tutorial
from jinja2 import Markup


class ProtectedView(BaseView):
    def is_accessible(self):

        if not current_user.is_authenticated():
            return False

        if hasattr(current_user, "role"):
            logging.warn(u"Checking user.. %s-%s" % (current_user.id, current_user.role))

        if not current_user.role == 0:
            return False

        return True


def truncator(field, ctx, model, name):
    original = getattr(model, field).encode('ascii', 'xmlcharrefreplace')

    truncated = original[:10] if len(original) > 10 else original

    return Markup(u"<span title='{1}' data-role='tooltip'>{0}..</span>".format(truncated, original))


def _href(kls, model, name, url=None):
    original = getattr(model, name)
    title = original.replace("http://", "").replace("https://", "").replace("www", "") \
        .replace("github.com", "")

    if url is not None:
        original = "{}/{}".format(url, original)

    return Markup(u'<a href="{0}" target="_blank">{1}</a>'
    .format(original, title))


def _img(field, ctx, model, name):
    original = getattr(model, field)
    return Markup('<img src="{0}" />'.format(original))


def _nick_href(*args):
    return _href(*args, url='https://github.com')


class ProtectedModelView(ModelView, ProtectedView):
    column_display_pk = True


_desc_trunc = partial(truncator, 'description')
_src_href_ = partial(_href, 'src_url')
_img_img = partial(_img, 'pic_url')


class ProjectModelView(ProtectedModelView):
    column_formatters = {'description': _desc_trunc,
                         'src_url': _href}

    column_searchable_list = ('name', 'description')


class UserModelView(ProtectedModelView):
    column_formatters = {'pic_url': _img_img}
    column_searchable_list = ('nick', 'email', 'first_name', 'last_name')


class SocialUserModelView(ProtectedModelView):
    column_formatters = {'nick': _nick_href}


class PackageModelView(ProtectedModelView):
    column_list = ('name','mdown','wdown','ddown', 'summary')
    column_searchable_list = ("name",'summary','description')


class TutorialModelView(ProtectedModelView):
    column_list = ('id', 'title','slug','keywords','meta_description', 'publish', 'spam','upvote_count')

def init(app, db):
    admin = Admin(app)

    admin.add_view(UserModelView(User, db.session, category='User'))
    admin.add_view(SocialUserModelView(SocialUser, db.session, category='User'))
    admin.add_view(ProjectModelView(OpenSourceProject, db.session, name='Project'))
    admin.add_view(ProtectedModelView(Message, db.session))
    admin.add_view(ProtectedModelView(Action, db.session))
    admin.add_view(ProtectedModelView(Bucket, db.session))
    admin.add_view(ProtectedModelView(Channel, db.session))
    admin.add_view(TutorialModelView(Tutorial, db.session))
    admin.add_view(PackageModelView(Package, db.session))
########NEW FILE########
__FILENAME__ = api
import json
import logging
from flask import jsonify, request
import flask.ext.restless
from flask.ext.restless.views import ProcessingException


########NEW FILE########
__FILENAME__ = app
import os
import sys
import logging
from werkzeug.routing import BaseConverter
from flaskext.kvsession import KVSessionExtension
from flask import Flask, request, abort, render_template, redirect, jsonify, session, url_for


current_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.dirname(current_dir)

sys.path.insert(0, source_dir)

from pyhackers.config import config
from pyhackers.setup import setup_application_extensions

current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = config.get("app", "static")
#templates_folder = config.get("app", "templates")
db_conf = config.get("app", "db")

templates_folder = os.path.join(current_dir, 'templates')
statics_folder = os.path.join(current_dir, 'static')
app = Flask(__name__, template_folder=templates_folder, static_folder=statics_folder)
app.secret_key = config.get("app", "flask_secret")
app.debug = bool(config.get("app", "debug"))
app.config['SQLALCHEMY_DATABASE_URI'] = db_conf
app.config['SQLALCHEMY_RECORD_QUERIES'] = True


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


app.url_map.converters['regex'] = RegexConverter

login_manager = None
def start_app(soft=False):
    """
    Well starts the application. But it's a complete mess!
    I seriously need to get better at application start, and import
    statements logic!!
    """
    global login_manager
    from sentry import init as init_sentry
    #init_sentry(app)


    login_manager = setup_application_extensions(app, '/authenticate')

    from flask.ext.sqlalchemy import SQLAlchemy

    from pyhackers.db import set_db, get_db

    set_db(SQLAlchemy(app))
    DB = get_db()
    from pyhackers.model.cassandra.connection import setup,connect
    connect(*setup())

    from pyhackers.model.user import User

    if soft:  # When not in web mode
        return

    from pyhackers.admin import init as admin_init
    from pyhackers.cache import init as cache_init

    #noinspection PyUnusedLocal
    @login_manager.user_loader
    def load_user(user_id):
        logging.warn("[USER]Finding user {}".format(user_id))
        try:
            return User.query.get(user_id)
        except Exception, ex:
            logging.exception(ex)
            try:
                from pyhackers.sentry import sentry_client  # OMG
                sentry_client.captureException()
            finally:
                return None

    cache_init(app)
    admin_init(app, DB)

    from pyhackers.controllers.main import main_app
    from pyhackers.controllers.oauth.ghub import github_bp
    from pyhackers.controllers.discuss import discuss_app
    from pyhackers.controllers.ajax import ajax_app

    app.register_blueprint(github_bp)
    app.register_blueprint(main_app)
    app.register_blueprint(discuss_app)
    app.register_blueprint(ajax_app)

    @app.route("/site-map")
    def site_map():
        links = []
        for rule in app.url_map.iter_rules():
            # Filter out rules we can't navigate to in a browser
            # and rules that require parameters
            if ("GET" in rule.methods or "POST" in rule.methods) and rule is not None and len(rule.defaults or []) >= len(rule.arguments or []):
                url = url_for(rule.endpoint)
                links.append((url, rule.endpoint))
        return jsonify({'links': links})

    # from controllers.oauth.twitter import twitter_bp
    # app.register_blueprint(twitter_bp)


if __name__ == "__main__":
    start_app()
    app.run(use_debugger=True, port=5001)
########NEW FILE########
__FILENAME__ = idgen


from flask import request, jsonify, Blueprint
from pyhackers.idgen import IdGenerator, StatsHandler, idgen_client
from pyhackers.config import config

url_prefix = config.get("idgen", "url_prefix")

idgen_app = Blueprint('idgen_service', __name__, url_prefix=url_prefix)

# idgenerator = IDGen()
stats_handler = StatsHandler()


@idgen_app.route("/new", methods=['GET'])
def generate():
    return str(idgen_client.get())


@idgen_app.route("/flush", methods=['GET'])
def flush():
    return jsonify(stats_handler.get(flush=True))


@idgen_app.route("/stats", methods=['GET'])
def stats():
    return jsonify(stats_handler.get())

########NEW FILE########
__FILENAME__ = cache

from flask.ext.cache import Cache

cache = None


def init(app):
    global cache
    cache = Cache(app, config={'CACHE_TYPE': 'memcached'})
    cache.init_app(app)

########NEW FILE########
__FILENAME__ = cassandra_old
import sys
from datetime import datetime as dt
from functools import wraps
import zlib
import msgpack
import pycassa
from pycassa.pool import ConnectionPool
from pycassa.index import create_index_clause, create_index_expression
from pycassa.cassandra.ttypes import NotFoundException, ConsistencyLevel
from pyhackers.common import unix_time_millisecond, time_with_ms, epoch_to_date, unix_time
from pyhackers.config import config

pool = ConnectionPool("sweetio", [config.cassandra])
status_cf = pycassa.ColumnFamily(pool, "status")
user_timeline_cf = pycassa.ColumnFamily(pool, "user_timeline")
user_cf = pycassa.ColumnFamily(pool, "user2")
channel_timeline_cf = pycassa.ColumnFamily(pool, "channel_timeline")

#create column family user_following_timeline with comparator = IntegerType;
user_following_timeline_cf = pycassa.ColumnFamily(pool, "user_following_timeline")
counters_cf = pycassa.ColumnFamily(pool, "counters")

status_upvotes_cf = pycassa.ColumnFamily(pool, "status_upvotes")
status_downvotes_cf = pycassa.ColumnFamily(pool, "status_downvotes")
status_replies_cf = pycassa.ColumnFamily(pool, "status_replies")
status_resweets_cf = pycassa.ColumnFamily(pool, "status_resweets")
status_favs_cf = pycassa.ColumnFamily(pool, "status_favs")

user_follower_cf = pycassa.ColumnFamily(pool, "user_followers")
user_following_cf = pycassa.ColumnFamily(pool, "user_following")

user_upvotes_cf = pycassa.ColumnFamily(pool, "user_upvotes")
user_downvotes_cf = pycassa.ColumnFamily(pool, "user_downvotes")
user_replies_cf = pycassa.ColumnFamily(pool, "user_replies")
user_favs_cf = pycassa.ColumnFamily(pool, "user_favs")
user_resweets_cf = pycassa.ColumnFamily(pool, "user_resweets")

# user_upvotes
# status_upvotes
# status_retweets { "status_id" : { <status_id> : <user_id> } }
# status_replies
# status_favorites
# status_flags
# conversation =>

not_found_dict = {"error": "Not found"}


class Gateway():
    pass


def notify(message):
    print "New message is here! {}".format(message)


class reporter():
    def captureException(self):
        pass


error_reporter = reporter()


def write(msg):
    sys.stdout.write("[%s] CACHE::%s\n" % (time_with_ms(dt.utcnow()), msg))


class CassandraGateway(Gateway):
    def channel_timeline(self, channel_id_or_name, after_id=""):
        try:
            reverse = not isinstance(after_id, long)

            ch_timeline_items = channel_timeline_cf.get(channel_id_or_name,
                                                        column_reversed=reverse, column_count=20, column_start=after_id)
        except (NotFoundException, Exception):
            return []

        return self.get_statuses(ch_timeline_items, exclude=after_id)

    def timeline(self, user_id, after_id=""):
        try:
            reverse = not isinstance(after_id, long)
            timeline_status_ids = user_following_timeline_cf.get(user_id, column_reversed=reverse, column_count=20,
                                                                 column_start=after_id)
        except NotFoundException:
            return []

        return self.get_statuses(timeline_status_ids, exclude=after_id)

    def user_timeline(self, user_id, after_id=''):
        try:
            reverse = not isinstance(after_id, long)
            timeline_items = user_timeline_cf.get(str(user_id), column_count=20, column_reversed=reverse,
                                                  column_start=after_id)
        except (NotFoundException, Exception):
            return []

        return self.get_statuses(timeline_items, exclude=after_id)

    def get_single_status(self, status_id):
        status = status_cf.get(status_id)
        # write(status)
        data = status.get("data")
        status_post = msgpack.unpackb(zlib.decompress(data))
        status_post["user"] = self.get_user(status_post.get("user_id"))

        try:
            stats = counters_cf.get(status_id)
            write(stats)
            status_post["stats"] = stats
        except NotFoundException:
            pass

        return status_post

    def get_statuses(self, timeline_items, exclude=None):
        status_ids = []

        for ts, id in timeline_items.iteritems():
            if exclude is not None and str(ts) == str(exclude):
                continue
            status_ids.append(id)

        statuses = status_cf.multiget(status_ids)

        status_messages = {}
        status_messages_sorted = []
        user_ids = []

        for key, post in statuses.iteritems():
            status = msgpack.unpackb(zlib.decompress(post.get("data")))
            user_ids.append(status.get("user_id"))
            status_messages[key] = status

        users = user_cf.multiget(user_ids)
        user_dict = {}

        for user_id, columns in users.iteritems():
            for key, val in columns.iteritems():
                if key == "data":
                    # sys.stdout.write("\n%s %s \nZLIB:%r\n" % (user_id,key,val))
                    user_dict[user_id] = msgpack.unpackb(zlib.decompress(val))
                    user_dict[user_id]["stats"] = self.get_user_stats(user_id)

        for ts, id in timeline_items.iteritems():
            message = status_messages.get(id)

            if message is not None:
                message["id"] = str(message['id'])
                message["user"] = user_dict.get(message.get("user_id"))
                message["published_at"] = epoch_to_date(long(message["published_at"]))

                status_messages_sorted.append(status_messages.get(id))

        return status_messages_sorted

    def new_status(self, status_dict, reply_to_id=None, reply_to_user_id=None):

        notify(status_dict)

        if status_dict is None or not isinstance(status_dict, dict):
            return False

        id = long(str(status_dict.get("id")))
        user_id = str(status_dict.get("user_id"))
        channels = status_dict.get("channels")

        status_cf.insert(str(id), {"user_id": user_id, "data": zlib.compress(msgpack.packb(status_dict))})

        ts_id = {id: str(id)}
        #		write("INT: %d vs %s" % (id , str(id)))

        for channel in channels:
            channel_timeline_cf.insert(str(channel), ts_id)

        followers = [f for f in self.get_followers(user_id)]

        for f in followers:
            user_following_timeline_cf.insert(f, ts_id)

        user_timeline_cf.insert(user_id, ts_id)

        #increase status count of the user
        # why there is a user_<id> structure ?
        # well we could submit all our counters to this column family..
        # status ids are registered directly
        # user ids are user_<id> format
        #
        counters_cf.add("user_" + str(user_id), "statuses")

        if reply_to_id is not None:
            counters_cf.add("%s" % reply_to_id, "replies")

    def incr_status_retweet(self, status_id):
        counters_cf.add("%s" % status_id, "resweets")

    def new_channel(self, channel_dict):
        pass

    def new_user(self, id, nick, user_dict):
        user_cf.insert(str(id), {"nick": nick, "data": zlib.compress(msgpack.packb(user_dict))})

    def get_user(self, user_id):
        try:
            #read_consistency_level=ConsistencyLevel.QUORUM
            user = user_cf.get(str(user_id))

            user_dict = msgpack.unpackb(zlib.decompress(user.get("data")))

            if not user_dict.has_key("id"):
                user_dict["id"] = user_id

            return user_dict

        except NotFoundException:
            return None


    def get_user_by_nick(self, user_nick):
        nick_expression = create_index_expression('nick', user_nick)
        clause = create_index_clause([nick_expression], count=1)
        user_dict = None
        for key, user in user_cf.get_indexed_slices(clause):
            user_dict = msgpack.unpackb(zlib.decompress(user.get("data")))

        return user_dict

    def follow_user(self, following_user_id, follower_user_id):
        epoch = int(unix_time(dt.utcnow()))

        user_follower_cf.insert(str(following_user_id), {str(follower_user_id): str(epoch)})
        user_following_cf.insert(str(follower_user_id), {str(following_user_id): str(epoch)})

        counters_cf.add("user_" + str(following_user_id), "followers")
        counters_cf.add("user_" + str(follower_user_id), "following")

    def unfollow_user(self, following_user_id, follower_user_id):
        user_follower_cf.remove(str(following_user_id), columns=[str(follower_user_id)])
        user_following_cf.remove(str(follower_user_id), [str(following_user_id)])

        counters_cf.add("user_" + str(following_user_id), "followers", value=-1)
        counters_cf.add("user_" + str(follower_user_id), "following", value=-1)

    def get_followers(self, user_id):
        try:
            follower_dict = user_follower_cf.get(str(user_id))
        except NotFoundException:
            return

        for key, val in follower_dict.iteritems():
            yield key

    def get_following(self, user_id):
        try:
            following_dict = user_following_cf.get(str(user_id))
        except NotFoundException:
            return None
        return following_dict

    def get_user_stats(self, user_id):

        try:
            return counters_cf.get("user_%s" % str(user_id))
        except NotFoundException:
            return None

    #TODO: Refactor the following methods

    def status_fav(self, status_id, user_id):
        ms = long_now()
        user_favs_cf.insert(str(user_id), {status_id: ""})
        status_favs_cf.insert(str(status_id), {ms: user_id})
        counters_cf.add(str(status_id), "favs")
        counters_cf.add("user_" + str(user_id), "favs")

    def status_upvote(self, status_id, user_id):
        ms = long_now()
        user_upvotes_cf.insert(str(user_id), {status_id: ""})
        status_upvotes_cf.insert(str(status_id), {ms: user_id})
        counters_cf.add(str(status_id), "upvote")
        counters_cf.add("user_" + str(user_id), "upvote")

    def status_downvote(self, status_id, user_id):
        ms = long_now()
        user_downvotes_cf.insert(str(user_id), {status_id: ""})
        status_downvotes_cf.insert(str(status_id), {ms: user_id})
        counters_cf.add(str(status_id), "downvote")
        counters_cf.add("user_" + str(user_id), "downvote")

    def status_reply(self, status_id, user_id):
        pass

    def status_resweet(self, status_id, user_id, new_status_id):
        user_resweets_cf.insert(str(user_id), {status_id: ""})
        status_resweets_cf.insert(str(status_id), {new_status_id: str(user_id)})
        #counters_cf.add("%s"%status_id,"resweets")
        self.incr_status_retweet(status_id)


def long_now():
    return long(unix_time_millisecond(dt.utcnow()))


gateway = CassandraGateway()


class cassandra_cache:
    @classmethod
    def skip_if_possible(cls, proxy_func):
        @wraps(proxy_func)
        def get_data(*args, **kwargs):
            if kwargs.has_key("use_cache") and not kwargs["use_cache"]:
                return proxy_func(*args, **kwargs)

            success, result = cls.call_cache_function(False, proxy_func.__name__, None, *args, **kwargs)
            if not success:
                return proxy_func(*args, **kwargs)
            else:
                return result

        return get_data


    @classmethod
    def after(cls, name=None, condition=None):
        """
        Handles the parameter passing of the decorator.
        If the condition met, call our target function.
        :param cls:
        :param condition:
        :return:
        """

        def after_call(proxy_func):

            @wraps(proxy_func)
            def get_data(*args, **kwargs):

                write("WRAPPER:BEGIN")
                # write(args)
                # write(kwargs)
                # write(dir(proxy_func))
                # write(proxy_func)
                result = proxy_func(*args, **kwargs)

                try:
                    func_name = name or proxy_func.__name__

                    success, cache_result = cls.call_cache_function(True, func_name, result, *args, **kwargs)
                    return cache_result or result
                #					else:
                #						write("Results did not match %r vs %r\n" % (result,condition))
                except:
                    cache_result = None
                    #					error_reporter.captureException()
                    raise

            return get_data

        return after_call

    @classmethod
    def call_cache_function(cls, expect_actual_result, method, actual_call_result, *args, **kwargs):
    #		if hasattr(cls,proxy_func.__name__):
        success, result = False, None

        try:
            fn = getattr(cls, method)

        except:
            write("[%s]Method not found in Cassandra" % method)
            # delay the message capture by somehow.
            #			error_reporter.captureMessage("Method not found in Cassandra: %s" % method)

            return False, None

        try:
            write("BEGIN::%s" % method)
            if not expect_actual_result:
                success, result = fn(*args, **kwargs)
            else:
                success, result = fn(actual_call_result, *args, **kwargs)
        except Exception, ex:
            error_reporter.captureException()
            write("EXCEPTION[%s]:%s" % (method, ex))
        finally:
            write("END::%s" % method)
            return success, result

    @classmethod
    def follow_user(cls, result, *args, **kwargs):
        following_user_id = args[1];
        follower_user_id = args[2]
        if not isinstance(follower_user_id, basestring):
            follower_user_id = str(follower_user_id.id)

        write("Follow USER: %s %s" % (str(following_user_id), str(follower_user_id)))
        try:
            gateway.follow_user(following_user_id, follower_user_id)
        except:
            raise

        return True, True

    @classmethod
    def unfollow_user(cls, result, *args, **kwargs):
        following_user_id = args[1]
        follower_user_id = args[2]
        if not isinstance(follower_user_id, basestring):
            follower_user_id = str(follower_user_id.id)

        write("UNFOLLOW USER: %s %s" % (str(following_user_id), str(follower_user_id)))
        gateway.unfollow_user(following_user_id, follower_user_id)
        return True, True

    @classmethod
    def get_followers(cls, *args, **kwargs):
        following_user_id = args[1]
        follower_ids = [f for f in gateway.get_followers(following_user_id.get("id"))]
        followers = []
        for id in follower_ids:
            user = gateway.get_user(id)
            if user is not None:
                followers.append(user)
        return True, followers


    @classmethod
    def get_following(cls, *args, **kwargs):
        following_user_id = args[1]
        following = []

        for f in gateway.get_following(following_user_id.get("id")):
            user = gateway.get_user(f)
            if user is not None:
                following.append(user)
        return True, following

    @classmethod
    def timeline_cache(cls, *args, **kwargs):
        write("Timeline Cache")
        return False, None

    @classmethod
    def channel_timeline(cls, *args, **kwargs):
        ch_id = args[1]
        after_id = kwargs.get("after_id", "")
        if after_id is None or ( isinstance(after_id, basestring) and not len(after_id)):
            after_id = ""
        else:
            after_id = long(after_id)

        write("CHANNEL after_id: %s" % after_id)

        ch_tm = gateway.channel_timeline(ch_id, after_id=after_id)

        if isinstance(ch_tm, list):
            write("END::Found %d recs" % len(ch_tm))

        return True, (list(reversed(ch_tm)) if not isinstance(after_id, long) else ch_tm)

    @classmethod
    def timeline(cls, *args, **kwargs):
        # write(args)
        # write(kwargs)

        user_id = None
        user = kwargs.get('user', None)

        if user is None:
            return False, []

        if hasattr(user, "id"):
            user_id = str(user.id)
        elif hasattr(user, "get") and "id" in user:
            user_id = str(user.get("id"))

        if user_id is None:
            return False, []

        after_id = kwargs.get("after_id", "")
        if after_id is None or (isinstance(after_id, basestring) and not len(after_id)):
            after_id = ""
        else:
            after_id = long(after_id)

        write("TIMELINE after_id: %s" % after_id)

        timeline = gateway.timeline(user_id, after_id=after_id)

        return True, (list(reversed(timeline)) if not isinstance(after_id, long) else timeline)

    @classmethod
    def get_after_id(cls, **kwargs):
        after_id = kwargs.get("after_id", "")
        if after_id is None or (isinstance(after_id, basestring) and not len(after_id)):
            after_id = ""
        else:
            after_id = long(after_id)
        return after_id

    @classmethod
    def user_timeline(cls, *args, **kwargs):

        user_id = args[1]
        after_id = cls.get_after_id(**kwargs)

        write("BEGIN::User timeline: %s" % user_id)

        id = str(user_id.id) if hasattr(user_id, "id") else str(user_id)
        user_timeline = gateway.user_timeline(id, after_id=after_id)

        if isinstance(user_timeline, list):
            write("END::Found %d recs" % len(user_timeline))

        return True, (list(reversed(user_timeline)) if not isinstance(after_id, long) else user_timeline)

    @classmethod
    def status_insert(cls, new_post, *args, **kwargs):
        write("BEGIN::Status insert")

        if new_post is None:
            return True, None

        write(args)
        replyToId = kwargs.get("reply_to_id", None)
        replyToUserId = kwargs.get("reply_to_user_id", None)

        gateway.new_status(new_post.json(date_converter=unix_time_millisecond), reply_to_id=replyToId,
                           reply_to_user_id=replyToUserId)
        write("END::Status insert")
        return True, new_post

    @classmethod
    def status_resweet(cls, ret_val, *args, **kwargs):
        id = long(args[1])
        user = args[2]

        user_id = str(user.id) if user is not None and hasattr(user, "id") else None

        # status = gateway.get_single_status(id)
        # write(status)
        new_status_id = ret_val.id
        #increate status ReSweet count
        gateway.status_resweet(id, user_id, new_status_id)


        # add history record to notify userA that somebody resweeted their status post.


        return True, ret_val.json()

    actions = ["fav", "upvote", "email", "flag", "resweet", "email", 'downvote', 'info']

    @classmethod
    def status_action_handler(cls, *args, **kwargs):
        status_id = long(args[1])
        action = args[2]
        try:
            user = args[3]
        except IndexError, ie:
            user = kwargs.get("user", None)

        user_id = str(user.id) if user is not None and hasattr(user, "id") else "None"

        write("Id:%s Action:%s User:%s" % (status_id, action, user_id))

        if action == "upvote":
            gateway.status_upvote(status_id, user_id)
        elif action == "fav":
            write("calling fav action")
            gateway.status_fav(status_id, user_id)
        elif action == "downvote":
            gateway.status_downvote(status_id, user_id)
        elif action == "info":
            return True, gateway.get_single_status(str(status_id))

        return True, True

    @classmethod
    def user_profile(cls, *args, **kwargs):
        user_id = args[1]
        write("USER Lookup (%s)" % user_id)

        user = gateway.get_user_by_nick(user_id)

        followers = [f for f in gateway.get_followers(user.get("id"))]

        if user is None:
            return False, not_found_dict

        user["followers"] = followers
        user["stats"] = gateway.get_user_stats(user.get("id"))

        return True, user
########NEW FILE########
__FILENAME__ = dbfield
import base64
from datetime import datetime as dt, timedelta
import logging
import pickle
from sqlalchemy.types import TypeDecorator, CHAR, String, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.
    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value)
            else:
                return "%.32x" % value # hexstring

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(value)


class Choice(TypeDecorator):
    impl = String

    def __init__(self, choices=None, **kw):
        if choices is None:
            choices = {}
        self.choices = dict(choices)
        super(Choice, self).__init__(**kw)

    def process_bind_param(self, value, dialect):
        return [k for k, v in self.choices.iteritems() if v == value][0]

    def process_result_value(self, value, dialect):
        return self.choices[value]


class EpochType(TypeDecorator):
    impl = Integer

    epoch = dt.date(dt(1970, 1, 1))

    def process_bind_param(self, value, dialect):
        return (value - self.epoch).days

    def process_result_value(self, value, dialect):
        return self.epoch + timedelta(days=value)


class GzippedDictField(TypeDecorator):
    """
    Slightly different from a JSONField in the sense that the default
    value is a dictionary.
    """
    impl = Text

    def process_result_value(self, value, dialect):
        if isinstance(value, basestring) and value:
            try:
                value = pickle.loads(base64.b64decode(value).decode('zlib'))
            except Exception, e:
                logging.exception(e)
                return {}
        elif not value:
            return {}
        return value

        pass

    def process_bind_param(self, value, dialect):
        if value is None:
            return
        return base64.b64encode(pickle.dumps(value).encode('zlib'))
########NEW FILE########
__FILENAME__ = http_utils
import logging
import requests
from requests import Timeout
from urlparse import urlparse


html_ctype = 'text/html'
xml_ctype = 'text/xml'
xml_ctype2 = 'application/xml'

rss_ctype = 'application/rss+xml'
atom_ctype = 'application/atom+xml'
rdf_ctype = 'application/rdf+xml'

feed_types = [xml_ctype, rss_ctype, atom_ctype, rdf_ctype, xml_ctype2]


class HttpFetcher():
    def __init__(self):
        self.session = requests.session()
        self.session.config['keep_alive'] = True

    #	@profile
    def download(self, url):
        r = self.session.get(url)

        return r.text

    def download_json(self, url):
        r = self.session.get(url)

        return r.json

    def head(self, url, extended=True):
        try:
            r = self.session.head(url, allow_redirects=True)
            print r.headers
            print r.url

            if extended:
                return HttpResult(r.url, r.headers, r.status_code, True)
            else:
                return r.url
        except Timeout as tout:
            logging.error(tout.message, tout)
            return None
        except Exception:
            logging.error("Finding Actual URL General Exception:", exc_info=True)
            return None


class HttpResult:
    def __init__(self, url='', headers=None, status=None, success=False):
        self.url = url
        self.headers = headers
        self.status_code = status
        self.success = success
        self.__content_type = None
        self.__set_content_type()

    def __set_content_type(self):
        """
        Parse http headers to find out content type
        :return: Nothing
        """
        if self.headers is None:
            return

        content_type = self.headers.get("content-type", None)

        if content_type is None:
            return
        if ";" in content_type:
            content_type_parts = content_type.split(";")

            if len(content_type_parts) == 2:
                self.__content_type = content_type_parts[0]
        else:
            self.__content_type = content_type

    @property
    def content_type(self):
        """
        Return the content-type from header info
        :return: String content-type from header if exists otherwise None
        """
        return self.__content_type

    @property
    def is_html(self):
        """
        Check if the content-type is text/html
        :return: True/False
        """
        return self.__content_type == html_ctype

    @property
    def is_rss(self):
        """
        Check if the HttpResult is a Feed type ( text/xml, application/rss+xml, application/atom+xml )
        :return: True/False
        """
        return self.__content_type in feed_types

    def __reduce__(self):
        return {
            "url": self.url,
            "headers": self.headers,
            "status_code": self.status_code,
            "success": self.success,
            "content_type": self.content_type,
            "is_html": self.is_html,
            "is_rss": self.is_rss
        }


http_fetcher = HttpFetcher()


def is_same_domain(url1, url2):
    """
    Returns true if the two urls should be treated as if they're from the same
    domain (trusted).
    """
    url1 = urlparse(url1)
    url2 = urlparse(url2)
    return url1.netloc == url2.netloc
########NEW FILE########
__FILENAME__ = indexer
import logging
from pyes import *
from pyes.exceptions import ElasticSearchException
from pyhackers.sentry import sentry_client

conn = ES('http://es.pythonhackers.com')


def index_data(data, index='sweet', doc='post', id=None):
    logging.warn("Indexing data %s" % (id if id is not None else ""))
    try:
        res = conn.index(data, index, doc, id=id)
    except ElasticSearchException:
        sentry_client.captureException()
        return False

    id = None

    if res is not None:
        id = res.get("_id", None)

    return id, res
########NEW FILE########
__FILENAME__ = stringutils
# coding=utf-8
import htmlentitydefs
import json
import unicodedata as ud


def leaner_url(s):
    """
    Highly refactoring necessary!
    """
    if s is None or len(s) <= 0:
        return "_"
    s2 = s.replace('http://', '').replace("'", '').replace(u'’', '').replace(' ', '-').replace('www.', ''). \
        replace('?', '').replace('&amp;', '-').replace(';', ''). \
        replace('/', '-').replace('=', '-').replace("#", "").replace(",", '').replace('"', '').replace('&', '').replace(
        "%", '')
    if s2[-1] == '-':
        s2 = s2[0:-1]
    return s2.replace('--', '-')


def safe_str(my_str):
    if my_str is not None:
        if isinstance(my_str, basestring):
            try:
                return my_str.encode('ascii', errors='ignore')
            except:
                return my_str
        else:
            return "%s" % my_str
    else:
        return "None"


def safe_filename(filename):
    return "".join([c for c in filename if c.isalpha() or c.isdigit() or c == ' ']).rstrip()


def safe_obj_str(my_obj):
    return json.dumps(my_obj)


def max_length_field(instance, name, length):
    if hasattr(instance, name):
        original_val = getattr(instance, name)
        if original_val is not None and len(original_val) > length:
            cut_val = original_val[:length]
            setattr(instance, name, cut_val)
            return cut_val
        else:
            return original_val
    return None


def max_length_field2(instance, name, length):
    if hasattr(instance, name):
        original_val = getattr(instance, name)

        if original_val is not None and len(original_val) > length:
            cut_val = original_val[:length]
            setattr(instance, name, cut_val)
            original_field = "original_%s" % name
            if hasattr(instance, original_field):
                setattr(instance, original_field, original_val)


def non_empty_str(str):
    return str is not None and len(str) > 0


def explain_string(str):
    for ch in str:
        charname = ud.name(ch)
        print "%d U%04x %s " % (ord(ch), ord(ch), charname )


def normalize_str(str):
    new_str = []
    for ch in str:

        ordinal = ord(ch)
        if ordinal < 128:
            new_str.append(ch)
        else:
            new_str.append(u'\\u%04x' % ordinal)

    return u''.join(new_str)


def uescape(text):
    escaped_chars = []
    for c in text:
        if (ord(c) < 32) or (ord(c) > 126):
            c = '&{};'.format(htmlentitydefs.codepoint2name[ord(c)])
        escaped_chars.append(c)
    return ''.join(escaped_chars)


if __name__ == '__main__':
    class Test:
        def __init__(self):
            self.name = ''
            self.__surname = ''

        @property
        def surname(self):
            return self.__surname

        @surname.setter
        def surname(self, val):
            self.__surname = val

    test = Test()

    test_name = "1000000000000"
    test.name = test_name
    test.surname = 'cambel'

    max_length_field2(test, 'name', 4)
    max_length_field2(test, 'surname', 2)

    assert hasattr(test, '_original_name')
    print "%s - %s" % (test_name, test._original_name)

    assert test._original_name == test_name
    assert test.name == "1000"

    assert hasattr(test, '_original_surname')
    assert test._original_surname == "cambel"
    assert test.surname == "ca"

    def printer(x):
        print x

    print "{0}{1}{0}".format(("=" * 10), "Keys")
    map(printer, test.__dict__.iterkeys())
    print "{0}{1}{0}".format(("=" * 10), "Keys Values")
    map(printer, test.__dict__.iteritems())
########NEW FILE########
__FILENAME__ = timelimit
import logging
import threading
import sys
import traceback


class TimeoutError(Exception): pass


def timelimit(timeout=30, test=False):
    """borrowed from web.py"""
    timeout_in_seconds = 30

    def _1(function):
        def _2(*args, **kw):
            class Dispatch(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None

                    self.setDaemon(True)
                    self.start()

                def run(self):
                    try:
                        self.result = function(*args, **kw)
                    except:
                        self.error = sys.exc_info()

            if not test:

                c = Dispatch()

                if hasattr(timeout, '__call__'):
                    timeout_in_seconds = timeout()
                else:
                    timeout_in_seconds = timeout

                logging.debug("Timeout is %d" % timeout_in_seconds)
                c.join(timeout_in_seconds)

                if c.isAlive():
                    raise TimeoutError, 'took too long'
                if c.error:
                    tb = ''.join(traceback.format_exception(c.error[0], c.error[1], c.error[2]))
                    logging.debug(tb)
                    raise c.error[0], c.error[1]
                return c.result
            else:
                return function(*args, **kw)

        return _2

    return _1
########NEW FILE########
__FILENAME__ = config
import logging
import ConfigParser
import os

logging.basicConfig(format='[%(asctime)s](%(filename)s#%(lineno)d)%(levelname)-7s %(message)s',
                    level=logging.NOTSET)

config = ConfigParser.RawConfigParser()

configfiles = list()

# load default config file
dev_cfg = os.path.join(os.path.dirname(__file__), 'app.local.cfg')
logging.warn("Dev: %s" % dev_cfg)
configfiles += [dev_cfg]

configfiles += ['/var/`']

logging.warn('Configuration files read: %s' % configfiles)

files_read = config.read(configfiles)

logger = logging.getLogger("")

logger.warn('Configuration files read: %s' % files_read)

logger.setLevel(int(config.get('app', 'log_level')))


APPS_TO_RUN = ['web','idgen']

try:
    SENTRY_DSN = config.get("sentry", "dsn")
except Exception as ex:
    logger.error(ex)
    logger.warn("{0}Sentry client is DUMMY now{0} Config=>[{1}]".format(20 * "=", SENTRY_DSN))
########NEW FILE########
__FILENAME__ = ajax
from flask import request, jsonify, Blueprint
import logging
from flask.ext.login import login_required, current_user
from pyhackers.helpers import current_user_id
from pyhackers.service.channel import follow_channel
from pyhackers.service.discuss import new_discussion_message, discussion_messages, get_user_discussion_by_nick, new_discussion_follower, remove_discussion_follower
from pyhackers.service.post import new_post, upvote_message
from pyhackers.service.project import project_follow
from pyhackers.service.user import follow_user, get_user_timeline_by_nick, get_user_projects_by_nick


ajax_app = Blueprint('ajax', __name__, url_prefix='/ajax/')

@ajax_app.route('message/<regex(".+"):message_id>/upvote', methods=("POST",))
@login_required
def upvote_message_ctrl(message_id):
    upvote_message(message_id, current_user_id())
    return jsonify({'ok': 1})


@ajax_app.route("message/new", methods=("POST",))
@login_required
def new_message():
    logging.warn(request.form)
    message = request.form.get('message')
    code = request.form.get("code")

    new_post(message, code, current_user_id(), nick=current_user.nick)
    return jsonify({'ok': 1})


@ajax_app.route("followchannel", methods=("POST",))
@login_required
def follow_channel_ctrl():
    user_id = request.form.get("id")
    slug = request.form.get("slug")

    result = follow_channel(user_id, current_user)

    return jsonify({'ok': result})


@ajax_app.route("followuser", methods=("POST",))
@login_required
def follow_user_ctrl():
    user_id = request.form.get("id")
    nick = request.form.get("slug")

    result = follow_user(user_id, current_user)

    return jsonify({'ok': result})


@ajax_app.route("follow", methods=("POST",))
@login_required
def follow():
    project_id = request.form.get("id")
    slug = request.form.get("slug")

    logging.warn(u"Liked %s %s [%s-%s]", project_id, slug, current_user.id, current_user.nick)

    project_follow(project_id, current_user)

    return jsonify({'ok': 1})


@ajax_app.route('discuss/message/new', methods=('POST',))
@login_required
def new_discussion_message_ctrl():
    text = request.form.get("text")
    id = request.form.get("id")
    discussion_id = id
    message_id = new_discussion_message(discussion_id, text, current_user_id(), nick=current_user.nick)

    return jsonify({'id': message_id})


@ajax_app.route('discuss/<regex(".+"):discussion_id>/follow', methods=('POST',))
@login_required
def follow_discussion(discussion_id):
    status = request.form.get("status", "follow")
    logging.warn("Discussion User[{}] => {}".format(current_user_id(), status))
    if status == "follow":
        new_discussion_follower(discussion_id, current_user_id(), nick=current_user.nick)
    else:
        remove_discussion_follower(discussion_id, current_user_id())

    return jsonify({'ok': True})

@ajax_app.route('discuss/<regex(".+"):discussion_id>/messages', methods=('GET',))
@login_required
def discussion_messages_ctrl(discussion_id):
    after_id = request.args.get("after_id", -1)
    try:
        after_id = int(after_id)
    except:
        after_id = -1

    _ = discussion_messages(discussion_id, after_message_id=after_id, current_user_id=current_user_id())

    discussion, disc_posts, users, counters = _
    discussion_dict = discussion.to_dict()
    discussion_dict.update(**counters.to_dict())

    return jsonify({'discussion': discussion_dict , 'posts': [p.to_dict() for p in disc_posts]}) #, 'users' : users})


@ajax_app.route('user/<regex(".+"):nick>/projects')
def user_projects(nick):
    _ = get_user_projects_by_nick(nick)
    if _ is None:
        return jsonify({'user': None, 'projects': None})

    user, projects = _
    start = 0

    return jsonify({'user': user.to_dict(), 'projects': [f.to_dict(index=start + i + 1) for i, f in enumerate(projects)]})


@ajax_app.route('user/<regex(".+"):nick>/timeline')
def user_timeline(nick):
    after_id = request.args.get("after_id", -1)
    _ = get_user_timeline_by_nick(nick)
    if _ is None:
        return jsonify({'user': None})

    user, timeline = _

    return jsonify({'user': user.to_dict(), 'timeline': [t.to_dict() for t in timeline]})


@ajax_app.route('user/<regex(".+"):nick>/discussions')
def user_discussion(nick):
    after_id = request.args.get("after_id", -1)

    _ = get_user_discussion_by_nick(nick)
    if _ is None:
        return jsonify({'user': None})

    user, discussions = _

    return jsonify({'user': user.to_dict(), 'discussions': [t.to_dict() for t in discussions]})

########NEW FILE########
__FILENAME__ = discuss
import logging
from flask import request, jsonify, Blueprint, redirect, abort, make_response
from flask.ext.login import login_required, current_user
from pyhackers.cache import cache
from pyhackers.helpers import render_template, render_base_template, current_user_id
from pyhackers.service.discuss import new_discussion, load_discussion, new_discussion_message, load_discussions

discuss_app = Blueprint('discuss', __name__, template_folder='templates', url_prefix='/discuss/')


@discuss_app.route('home')
def index():
    discussions = load_discussions()

    return render_base_template('discuss.html', discussions=discussions)


@discuss_app.route('top')
def top():
    return render_template('discuss.html')


@discuss_app.route('<regex(".+"):slug>/<regex(".+"):id>')
def discussion_ctrl(slug, id):
    discussion_data = load_discussion(slug, id, current_user_id())
    discussion, disc_posts, message, counters, user = discussion_data
    related_discussions = load_discussions()

    return render_base_template("discussion.html", discussion=discussion,
                                message=message,
                                discussion_user=user,
                                posts=[],
                                counters=counters,
                                related_discussions=related_discussions,
                                )

@discuss_app.route('topic/<regex(".+"):slug>')
def discuss_topic_ctrl(slug):
    response = make_response("ok")
    return response

@discuss_app.route('new', methods=('GET', 'POST'))
@login_required
def new():
    if request.method == "POST":
        title = request.form.get("title", '')
        text = request.form.get("text", '')
        logging.warn(request.form)
        logging.warn(u"Text:{} -  Title: {}".format(text, title))
        #raise ValueError("Test")

        discuss_id, slug = new_discussion(title, text, current_user_id())
        return redirect("/discuss/{}/{}".format(slug, discuss_id))
        #return jsonify({'id': str(discuss_id), 'slug': slug})

    return jsonify({'ok': 1})





########NEW FILE########
__FILENAME__ = main
# coding=utf-8
from datetime import datetime as dt
import logging
import random
import time

from pyhackers.model.tutorial import Tutorial
import requests
from pyhackers.model.package import Package
from pyhackers.service.post import new_post
from pyhackers.service.channel import follow_channel, load_channel, get_channel_list
from pyhackers.service.project import project_follow, load_project
from pyhackers.service.user import get_profile, get_profile_by_nick, follow_user, load_user
from flask_wtf import Form
from wtforms import TextField, PasswordField
from wtforms.validators import Required
from flask import request, Blueprint, redirect, jsonify, abort
from flask.ext.login import current_user, logout_user, login_required
from datetime import datetime as dt
from pyhackers.setup import login_manager
from pyhackers.cache import cache
from pyhackers.model.user import User
from pyhackers.model.os_project import OpenSourceProject
from pyhackers.config import config
from pyhackers.sentry import sentry_client
from sqlalchemy import and_
from docutils.core import publish_parts
from pyhackers.helpers import render_template, render_base_template, current_user_id


purge_key = config.get("app", 'purge_key')
debug = config.get("app", "debug")
PRODUCTION = not (debug in ['True', '1', True, 1])
main_app = Blueprint('main', __name__, template_folder='templates')


@main_app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = "pythonhackers.com"
    return response


def current_user_logged_in():
    if hasattr(current_user, "id"):
        return True
    else:
        return False


@main_app.errorhandler(400)
def unauthorized(e):
    return render_template('400.html'), 400


@login_manager.user_loader
def login_load_user(userid):
    logging.warn("Finding user %s" % userid)
    user = User.query.get(userid)
    return user


class LoginForm(Form):
    username = TextField("username", [Required()])
    password = PasswordField("password", [Required()])


def rand_int(maximum=60):
    return int(random.random() * 100) % maximum


def request_force_non_cache():
    purg_arg = request.args.get(purge_key, False)
    logging.warn(u"Purge key:{}".format(purg_arg))

    force_cache = purg_arg in ["True", "1", "ok", True]
    logging.warn(u"Forcing non-cache:{}".format(force_cache))

    if not PRODUCTION:
        return True

    return force_cache


@cache.memoize(timeout=10000, unless=request_force_non_cache)
def get_reddit_top_python_articles(list_type='top'):
    keys = ['top', 'new', 'hot']

    url = "http://www.reddit.com/r/python/%s.json" % list_type
    logging.warn("Fetch REDDIT %s" % url)

    assert list_type in keys

    r = requests.get(url)

    reddit_posts = r.json()
    reddit_python_posts = []

    for red in reddit_posts['data']['children']:
        post = {}
        data = red['data']
        post['url'] = data['url']
        post['popularity'] = data['score']
        post['comment'] = data.get('num_comments', 0)
        post['title'] = data.get('title', '')
        post['domain'] = data.get('domain', '')
        post['ago'] = int((int(time.time()) - data.get('created_utc')) / 3600)
        post['user'] = data.get("author")

        reddit_python_posts.append(post)

    return reddit_python_posts


@main_app.route("/welcome", methods=("GET",))
def welcome():
    return render_base_template("welcome.html")


@main_app.route("/", methods=("GET",))
def main():
    if current_user.is_anonymous():
        return render_base_template("welcome.html")
    else:
        return redirect('/home')


@main_app.route("/home", methods=("GET",))
@main_app.route("/index", methods=("GET",))
@main_app.route("/timeline")
def timeline():
    return render_base_template("timeline.html")


@main_app.route("/links", methods=("GET",))
def index():
    list_type = request.args.get("list", 'top')

    links = get_reddit_top_python_articles(list_type=list_type)
    kwargs = {'links': sorted(links, key=lambda x: x.get("popularity"), reverse=True),
              'btn_hot': 'disabled' if list_type == 'hot' else '',
              'btn_new': 'disabled' if list_type == 'new' else '',
              'btn_top': 'disabled' if list_type == 'top' else '', }

    return render_base_template("index.html", **kwargs)


@main_app.route('/open-source/categories/web-framework')
def project_categories():
    projects = OpenSourceProject.query.filter(OpenSourceProject.categories.contains(["Web Framework"])) \
        .order_by(OpenSourceProject.watchers.desc()).limit(400)

    return render_base_template("os_list.html", projects=projects)


@main_app.route('/os/<regex(".+"):nick>/<regex(".+"):project>')
@main_app.route('/open-source/<regex(".+"):nick>/<regex(".+"):project>')
@cache.memoize(timeout=10000, unless=request_force_non_cache)
def os(nick, project):
    """Display the details of a open source project"""
    project = project[:-1] if project[-1] == "/" else project
    logging.info(u"looking for %s", project)
    slug = u"%s/%s" % (nick, project)
    project_data = load_project(slug, current_user)

    if project_data is None:
        return "Not found", 404

    project, related_projects, followers = project_data

    return render_base_template("os.html",
                                project=project,
                                related_projects=related_projects,
                                followers=followers, )


@cache.memoize(timeout=10000, unless=request_force_non_cache)
def load_projects(start):
    logging.warn(u"Running now with {}".format(start))
    return OpenSourceProject.query.filter(
        and_(OpenSourceProject.lang == 0, OpenSourceProject.hide is not True)).order_by(
        OpenSourceProject.watchers.desc())[start:start + 50]


@main_app.route('/fancy.json')
def fancy_json():
    start = int(request.args.get('start', 0))
    projects = load_projects(start)

    return jsonify({'data': [f.to_dict(index=start + i + 1) for i, f in enumerate(projects)]})


@main_app.route('/fancy/')
def fancy_os_list():
    return render_template('project_frame.html', projects=[])


@main_app.route('/top-python-contributors-developers')
def top_python_dudes():
    return render_template("top-python-developers.html")


@main_app.route('/os')
@main_app.route('/os/')
@main_app.route('/open-source/')
@main_app.route('/top-python-projects/')
@cache.cached(timeout=10000, unless=request_force_non_cache)
def os_list():
    logging.warn("Running OS LIST")
    path = request.path
    if "open-source" in path:
        canonical = None
    else:
        canonical = "http://pythonhackers.com/open-source/"

    projects = OpenSourceProject.query.filter(
        and_(OpenSourceProject.lang == 0,
             OpenSourceProject.hide is not True)
    ).order_by(OpenSourceProject.watchers.desc()).limit(400)

    return render_base_template("os_list.html", projects=projects, canonical=canonical)


@main_app.route('/python-packages/<regex(".+"):package>')
@cache.memoize(timeout=10000, unless=request_force_non_cache)
def package_details(package):
    package_obj = Package.query.get(package)
    if package_obj is None:
        return abort(404)

    try:
        description = publish_parts(package_obj.description, writer_name='html')['html_body']
    except:
        description = package_obj.description
        #description = markdown( package.description, autolink=True)

    return render_base_template("package.html", package=package_obj, description=description)


@main_app.route('/python-packages/')
@cache.cached(timeout=10000, unless=request_force_non_cache)
def package_list():
    packages = Package.query.order_by(Package.mdown.desc()).limit(1000)

    return render_base_template("packages.html", packages=packages)


@main_app.route("/user")
def user():
    """Seems redundant, /profile and /user/<nick takes care of the job"""
    return render_base_template("user.html", user=current_user)


@main_app.route("/new", methods=['GET', 'POST'])
@login_required
def new_message():
    return render_base_template("new_message.html")


@main_app.route("/about")
def about():
    return render_base_template("about.html")


@main_app.route("/coding")
def coding():
    return render_base_template("coding.html")


@main_app.route("/logout")
def logout():
    logout_user()
    return render_base_template("logout.html")


@main_app.route("/profile")
@login_required
def profile():
    """Returns profile of the current logged in user"""
    user_data = load_user(current_user.id, current_user)
    if user_data is not None:
        user, followers, following = user_data

        return render_base_template("profile.html", profile=user, followers=followers,
                                    following=following,
                                    os_projects=[])

    return abort(404)


@main_app.route('/channels/<regex(".+"):name>')
def channel(name):
    channel_name = name
    load_channel(name)
    if name == 'lobby':
        channel_name = "Lobby"
    return render_base_template("channel.html", channel_name=channel_name)


@main_app.route('/user/<regex(".+"):nick>/<regex(".+"):module>')
@main_app.route('/user/<regex(".+"):nick>')
@cache.memoize(timeout=10000, unless=request_force_non_cache)
def user_profile(nick, module=None):
    active_module = 'timeline'

    if module is not None:
        active_module = module if module in ['timeline', 'projects', 'discussions'] else active_module

    _ = get_profile_by_nick(nick)

    if _ is not None:
        user, followers, following = _
    else:
        return abort(404)

    return render_base_template("user_profile.html",
                                profile=user, followers=followers,
                                following=following,
                                module=active_module)


@cache.memoize(timeout=10000, unless=request_force_non_cache)
def find_tutorial(slug):
    return Tutorial.query.filter_by(slug=slug).first()


@main_app.route('/tutorial/<regex(".+"):nick>/<regex(".+"):slug>')
@cache.memoize(timeout=10000, unless=request_force_non_cache)
def tutorial(nick, slug):
    return render_template("tutorial.html", tutorial=find_tutorial("{}/{}".format(nick, slug)))


@main_app.route("/authenticate")
def authenticate():
    return render_base_template('authenticate.html')



########NEW FILE########
__FILENAME__ = ghub
import urllib
from flask.ext.login import login_user
from pyhackers.service.user import create_user_from_github_user
from rauth.service import OAuth2Service
from pyhackers.config import config
from flask import url_for, redirect, request, Blueprint, jsonify
import requests
from pyhackers.model.user import SocialUser, User
from pyhackers.db import DB as db
import logging

github_bp = Blueprint('github', __name__)

github = OAuth2Service(name='github',
                       authorize_url='https://github.com/login/oauth/authorize',
                       access_token_url="https://github.com/login/oauth/access_token",
                       client_id=config.get("github", 'client_id'),
                       client_secret=config.get("github", 'client_secret'))


@github_bp.route('/oauth/github')
def login():
    return redirect(github.get_authorize_url())


@github_bp.route('/oauth/github/authorized')
def authorized():

    redirect_uri = "{}oauth/github/authorized".format(request.host_url)

    logging.warn(redirect_uri)
    r = requests.post('https://github.com/login/oauth/access_token', data={
        'client_id': config.get("github", 'client_id'),
        'client_secret': config.get("github", 'client_secret'),
        'code': request.args['code'],
        'redirect_uri': redirect_uri
    }, headers={"Accept": 'application/json'})

    logging.warn(r.json())
    response_data = r.json()

    access_token = response_data['access_token']

    user_data = requests.get("https://api.github.com/user", params=dict(access_token=access_token))

    user_info = user_data.json()

    user = create_user_from_github_user(access_token, user_info)

    if user is not None:
        login_user(user)
        return redirect("/")
    else:
        return redirect("/")


    # return jsonify(user_info) #, response_data.get("access_token")

########NEW FILE########
__FILENAME__ = google
from json import loads,dumps
import requests
from flask import url_for, request, session, redirect,Blueprint
from flask_oauth import OAuth
from flask.ext.login import login_user
from pyhackers.app import app
from pyhackers.config import config
from pyhackers.models import User

google_bp = Blueprint('register', __name__,template_folder='templates')

oauth = OAuth()

google = oauth.remote_app('google',
                          base_url='https://www.google.com/accounts/',
                          authorize_url='https://accounts.google.com/o/oauth2/auth',
                          request_token_url=None,
                          request_token_params= {'scope': 'https://www.googleapis.com/auth/userinfo.email \
                          https://www.googleapis.com/auth/userinfo.profile',
                                                 'response_type': 'code'},
                          access_token_url='https://accounts.google.com/o/oauth2/token',
                          access_token_method='POST',
                          access_token_params={'grant_type': 'authorization_code'},
                          consumer_key=config.get("google",'client_id'),
                          consumer_secret=config.get("google",'client_secret')
)


@google.tokengetter
def get_access_token():
    return session.get('google_token')



@google_bp.route('/login/google')
def login_google():
    session['next'] = request.args.get('next') or request.referrer or None
    callback=url_for('google_callback', _external=True)
    return google.authorize(callback=callback)


@google_bp.route(app.config['REDIRECT_URI'])
@google.authorized_handler
def google_callback(resp):
    access_token = resp['access_token']
    session['access_token'] = access_token, ''
    if access_token:
        headers={'Authorization': 'OAuth ' + access_token}
        r = requests.get('https://www.googleapis.com/oauth2/v1/userinfo',
                         headers=headers)
        if r.ok:
            data = loads(r.text)
            oauth_id = data['id']
            user = User.load(oauth_id) or User.add(**data)
            login_user(user)
            next_url = session.get('next') or url_for('index')
            return redirect(next_url)
    return redirect(url_for('login'))





########NEW FILE########
__FILENAME__ = twitter
#import urllib
#from flask import url_for, request, session, redirect, Blueprint
#from pyhackers.config import config
#from rauth.service import OAuth1Service
#from rauth.utils import parse_utf8_qsl
#from werkzeug.urls import url_encode
#
#twitter_bp = Blueprint('register', __name__, template_folder='templates')
#
#twitter = OAuth1Service(name='twitter',
#                        request_token_url='https://api.twitter.com/oauth/request_token',
#                        access_token_url='https://api.twitter.com/oauth/access_token',
#                        authorize_url='https://api.twitter.com/oauth/authorize',
#                        base_url='https://api.twitter.com/1/',
#                        consumer_key=config.get("twitter", 'client_id'),
#                        consumer_secret=config.get("twitter", 'client_secret')
#)
#
#
## @twitter.tokengetter
## def get_twitter_token(token=None):
##     return session.get('twitter_token')
#
#
#@twitter_bp.route('/oauth/twitter')
#def login():
#    print config.get("twitter", 'client_id')
#    print config.get("twitter", 'client_secret')
#    oauth_callback = urllib.quote("http://localhost:5001/oauth/twitter/authorized")  #url_for('authorized', _external=True)
#    print oauth_callback
#    params = {'oauth_callback': oauth_callback}
#
#    r = twitter.get_raw_request_token(params=params)
#    data = parse_utf8_qsl(r.content)
#    print data
#
#    session['twitter_oauth'] = (data['oauth_token'],
#                                data['oauth_token_secret'])
#    return redirect(twitter.get_authorize_url(data['oauth_token'], **params))
#
#
#
#
#@twitter_bp.route('/oauth/twitter/authorized')
#def authorized():
#    # next_url = request.args.get('next') or url_for('index')
#    request_token, request_token_secret = session.pop('twitter_oauth')
#
#    # check to make sure the user authorized the request
#    if not 'oauth_token' in request.args:
#        print 'You did not authorize the request'
#        return redirect(url_for('index'))
#
#    try:
#        creds = {'request_token': request_token,
#                'request_token_secret': request_token_secret}
#        params = {'oauth_verifier': request.args['oauth_verifier']}
#        sess = twitter.get_auth_session(params=params, **creds)
#    except Exception, e:
#        print 'There was a problem logging into Twitter: ' + str(e)
#        return redirect(url_for('index'))
#
#    verify = sess.get('account/verify_credentials.json',
#                    params={'format':'json'}).json()
#
#    print verify
#
#    print 'Logged in as ' + verify['name']
#    return redirect(url_for('index'))
#
#    # session['twitter_token'] = (
#    #     resp['oauth_token'],
#    #     resp['oauth_token_secret']
#    # )
#    # session['twitter_user'] = resp['screen_name']
#
#    # flash('You were signed in as %s' % resp['screen_name'])
#    # return redirect(next_url)
########NEW FILE########
__FILENAME__ = user
from flask import request, jsonify, Blueprint, logging
from flask.ext.login import login_required, current_user
from pyhackers.cache import cache



########NEW FILE########
__FILENAME__ = db
DB = None


def set_db(db):
    global DB
    DB = db


def get_db():
    global DB
    return DB

########NEW FILE########
__FILENAME__ = events
from rq import Queue, Connection
from pyhackers.worker.message import new_message_worker
from pyhackers.job_scheduler import worker_queue as q


class Event(object):

    @classmethod
    def new_user(cls, user):
        """A user is registered"""
        pass

    @classmethod
    def follow_user(cls, user, following):
        """A user followed another user"""
        pass

    @classmethod
    def message(cls, user, message, context):
        """A user sent a message"""
        q.enqueue(new_message_worker, args=(user, message, context), result_ttl=0)
        pass

    @classmethod
    def follow_project(cls, user, project):
        """A user started to follow a project"""
        pass

    @classmethod
    def discussion(cls, user, discussion):
        """A User started a discussion"""
        pass

    @classmethod
    def reply(cls, user, context, message, reply_message):
        """A user replied to another user within a context ( e.g in a discussion )"""
        pass

    @classmethod
    def up_vote(cls, user, message):
        """A User up-voted a message(or discussion)"""
        pass

    @classmethod
    def user_view(cls, user, profile):
        """A User viewing another user's profile"""
        pass

    @classmethod
    def user_project_view(cls, user, project):
        """A User viewing a project"""
        pass

    @classmethod
    def click(cls, user, link):
        """A user clicked an external link"""
        pass

    @classmethod
    def mention(cls, user, message, mentioned):
        """ A user mentions somebody"""
        pass

    @classmethod
    def share_link(cls, user, link):
        """A user shared a link"""

    @classmethod
    def discussion_view(cls, current_user_id, discussion_id):
        pass
        #dc = DiscussionCounter.get(id=discussion_id)
        #dc.view_count += 1
        #dc.save()

# { type: FollowUser, user: { id: 3 }, target: { type: user, id : 4 } }
# { type: FollowProject, user: { id: 3 }, target: { type: project, id : 5 } }
# { type: FollowChannel, user: { id: 3 }, target: { type: channel, id : 5 } }
# { type: NewMessage, user: { id: 3 }, target: { type: message, id : 5 } }
# { type: NewChannelMessage, user: { id: 3 }, target: { type: project, id : 5 } }
# { type: NewDiscussion, user: { id: 3 }, target: { type: discussion, id : 5 } }
# { type: DiscussionComment, user: { id: 3 }, discussion: { id: 1020 } target: { type: message, id : 5 } }

########NEW FILE########
__FILENAME__ = twitter
import logging
from tweepy.streaming import StreamListener, json
from tweepy import OAuthHandler, API
from tweepy import Stream
from dateutil import parser as dtparser
from pyhackers.config import config
import redis
#from kafka.client import KafkaClient
#from kafka.producer import SimpleProducer


class StdOutListener(StreamListener):
    """
    A listener handles tweets are the received from the stream.
    This is a basic listener that just prints received tweets to stdout.
    """

    def __init__(self):
        #kafka = KafkaClient("localhost", 9092)
        #self.producer = SimpleProducer(kafka, "pyhackers-rt")
        super(StdOutListener, self).__init__()

    def on_data(self, data):
        obj = json.loads(data)
        #text = obj.get("text") or ""

        if "limit" in obj:
            logging.warn(obj)
            return True

        if "user" not in obj:
            logging.warn(obj)
            return True

        tweet_id = str(obj.get("id_str"))
        self.publish_to_redis(data, tweet_id)
        return True

    @staticmethod
    def publish_to_redis(data, _):
        redis_conn.publish("realtime", data)
        #self.producer.send_messages(data)

    @staticmethod
    def write_to_disk(data, tweet_id):
        with open('.tweets/{}.json'.format(tweet_id), "w") as f:
            f.write(data)

    def on_error(self, status):
        print status


redis_conn = None


def start():
    global redis_conn
    redis_conn = redis.StrictRedis(host="localhost", port=6379, db=0)
    consumer_key = config.get("twitter", "client_id")
    consumer_secret = config.get("twitter", "client_secret")
    access_token = config.get("twitter", "access_token")
    access_token_secret = config.get("twitter", "access_token_secret")

    l = StdOutListener()
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = API(auth)
    friend_ids = api.friends_ids()
    stream = Stream(auth, l)
    logging.warn(friend_ids)
    friend_ids = [str(i) for i in friend_ids]
    #        ,track=['startup','entrepreneurship','marketing','SEO']
    stream.filter(follow=friend_ids, track=['clojure']) #,track=[
    #'entrepreneurship','StartUp','SaaS','github','ycombinator','techstars',
    #'cassandra','mysql','mongodb','quora',
    #'scala','erlang','golang','python','entrepreneur','marketing'])

if __name__ == "__main__":
    start()
########NEW FILE########
__FILENAME__ = realtime
from Queue import Queue
import argparse
import logging
import textwrap
import threading
import time
#from pyhackers.utils import files_in
#from kafka.client import KafkaClient
#from kafka.consumer import SimpleConsumer
from twisted.internet import reactor, task
from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory, listenWS
import simplejson as json
import redis
from os import listdir
from os.path import join, isfile


def files_in(directory):
    for f in listdir(directory):
        if isfile(join(directory, f)):
            yield join(directory, f)
    return


redis_conn = None

logging.basicConfig(format='[%(asctime)s](%(filename)s#%(lineno)d)%(levelname)-7s %(message)s',
                    level=logging.NOTSET)

queue = Queue()


def publish_to_tenants():
    if not len(EchoServerProtocol.tenants):
        return

    msg = queue.get(timeout=None)
    if msg is None:
        return

    msg = str(msg) if msg is not None else ""
    #logging.warn("Queue: {}".format(msg))

    #logging.warn("Deliver tweets")
    for t in EchoServerProtocol.tenants:
        t.sendMessage(msg, False)



class EchoServerProtocol(WebSocketServerProtocol):
    tenants = []

    def onOpen(self):
        logging.warn(u"connection accepted from peer {}".format(self.peerstr))


    def onMessage(self, payload, binary):
        self.tenants.append(self)
        logging.warn(u"connection accepted from peer %s" % self.peerstr)
        logging.warn(u"Message: {}".format(payload))

    def onClose(self, *args):
        self.tenants.remove(self)
        logging.warn("{} - {} - {}".format(*args))

directory = '/Users/bahadircambel/code/learning/pythonhackers/.tweets/'


class PubSubKafkaListener(threading.Thread):
    def __init__(self,consumer):
        threading.Thread.__init__(self)
        self.consumer = consumer

    def iterate(self):
        for message in self.consumer:
            logging.warn(message)
            queue.put(message)

    def run(self):
        self.iterate()
        logging.warn("Exit loop")



class PubSubRedisListener(threading.Thread):
    def __init__(self,r,channels):
        threading.Thread.__init__(self)
        self.redis = r
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe(channels)

    def work(self, data):
        queue.put(data)

    def run(self):
        for item in self.pubsub.listen():
            if item['data'] == "KILL":
                self.pubsub.unsubscribe()
                logging.warn(self, "unsubscribed and finished")
                break
            else:
                self.work(item['data'])

if __name__ == "__main__":
    from twisted.python import log

# Taken from https://twistedmatrix.com/documents/12.0.0/core/howto/logging.html
    log.startLogging(open('console.log', 'w'))
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=textwrap.dedent(''))

    parser.add_argument('--wsport', type=int, default=10001, help="WebSocket Service Port")
    parser.add_argument('--redis', type=str, default='localhost', help="Redis location")

    args = parser.parse_args()





    def listen_redis():
        redis_conn = redis.StrictRedis(host=args.redis, port=6379, db=0)
        redis_listener = PubSubRedisListener(redis_conn,['realtime'])
        redis_listener.daemon = True
        redis_listener.start()

    def listen_kafka():
        kafka = KafkaClient("localhost", 9092)
        consumer = SimpleConsumer(kafka,"socket","pyhackers-rt")
        kafka_listener = PubSubKafkaListener(kafka, consumer)
        kafka_listener.daemon = True
        kafka_listener.start()


    listen_redis()



    l = task.LoopingCall(publish_to_tenants)
    l.start(0.1)

    factory = WebSocketServerFactory("ws://localhost:{}".format(args.wsport), debug=True)
    factory.protocol = EchoServerProtocol
    listenWS(factory)

    reactor.run()
########NEW FILE########
__FILENAME__ = helpers
import logging
import time
from datetime import datetime as dt
from flask import request, render_template as template_render
from flask.ext.login import current_user, AnonymousUserMixin
from json import dumps
import calendar
from pyhackers.config import config
from pyhackers.service.channel import get_channel_list

purge_key = config.get("app", 'purge_key')
debug = config.get("app", "debug")
PRODUCTION = not (debug in ['True', '1', True, 1])
cache_buster = calendar.timegm(time.gmtime())


def render_base_template(*args, **kwargs):
    try:
        logging.warn(current_user.is_anonymous())
        is_logged = not current_user.is_anonymous()
    except Exception as ex:
        logging.exception(ex)
        is_logged = False

    active_user = current_user.jsonable() if not current_user.is_anonymous() else {}
    user_data = dumps(active_user)
    logging.warn(user_data)

    # FIXME: render_template also contains some of the dict-keys.
    kwargs.update(**{'__v__': int(time.time()),
                     'user': active_user,
                     'user_json': user_data,
                     'channels': get_channel_list(),
                     'PROD': PRODUCTION,
                     'logged_in': bool(is_logged),
                     'year': dt.utcnow().year,
    })

    return render_template(*args, **kwargs)


def render_template(*args, **kwargs):
    """
    Render template for anonymous access with cache_buster,PROD settings, used for caching
    """
    params = {'cache_buster': cache_buster, 'user': {}, 'user_json': {}, 'PROD': PRODUCTION,
                     'static_route': 'http://cdn1.pythonhackers.com'}
    params.update(**kwargs)

    return template_render(*args, **params)


def current_user_id():
    if isinstance(current_user, AnonymousUserMixin):
        return None
    else:
        if hasattr(current_user, 'id'):
            return current_user.id
        else:
            return None
########NEW FILE########
__FILENAME__ = idgen
import logging
import requests
from time import time
from pyhackers.config import config, APPS_TO_RUN


class IdGenerator():
    max_time = int(time() * 1000)
    sequence = 0
    worker_id = 1
    epoch = 1356998400000  # 2013-01-01

    def create(self, worker_id=None):
        curr_time = int(time() * 1000)

        if curr_time > IdGenerator.max_time:
            IdGenerator.sequence = 0
            IdGenerator.max_time = curr_time

        IdGenerator.sequence += 1

        if IdGenerator.sequence > 4095:
            # Sequence overflow, bail out
            StatsHandler.errors += 1
            raise ValueError('Clock went backwards! %d < %d' % (curr_time, IdGenerator.max_time))

        IdGenerator.sequence += 1

        if IdGenerator.sequence > 4095:
            StatsHandler.errors += 1
            raise ValueError('Sequence Overflow: %d' % IdGenerator.sequence)

        generated_id = ((curr_time - IdGenerator.epoch) << 23) | ((worker_id or IdGenerator.worker_id) << 10) | IdGenerator.sequence
        StatsHandler.generated_ids += 1
        logging.debug("Created new ID: %s" % generated_id)
        return generated_id


class StatsHandler:
    errors = 0
    generated_ids = 0
    flush_time = time()

    def get(self, flush=False):
        if flush:
            self.flush()

        return {
            'timestamp': time(),
            'generated_ids': StatsHandler.generated_ids,
            'errors': StatsHandler.errors,
            'max_time_ms': IdGenerator.max_time,
            'worker_id': IdGenerator.worker_id,
            'time_since_flush': time() - StatsHandler.flush_time,
        }

    def flush(self):
        StatsHandler.generated_ids = 0
        StatsHandler.errors = 0
        StatsHandler.flush_time = time()


class IDGenClient():
    service_loc = None

    def __init__(self):
        logging.warn("Starting " + self.__class__.__name__)
        self.session = requests.Session()

    def get(self):
        r = self.session.get(self.service_loc)
        return long(r.text.replace("\r\n", ""))


class LocalIDGenClient():
    def __init__(self):
        logging.warn("Starting " + self.__class__.__name__)
        self.idgen = IdGenerator()

    def get(self):
        return self.idgen.create()


idgen_client = None

try:
    IdGenerator.worker_id = int(config.get("idgen", 'worker_id'))
    IDGenClient.service_loc = config.get("app", "idgen_service")

    # if we initialize the IDGen service in this process, lets connect to the internal item..,
    if "idgen" in APPS_TO_RUN:
        idgen_client = LocalIDGenClient()
    else:
        idgen_client = IDGenClient()

except Exception, ex:
    logging.exception(ex)
    pass
########NEW FILE########
__FILENAME__ = job_scheduler
from rq import Queue, Connection

__author__ = 'bahadircambel'


with Connection():
    worker_queue = Queue()

########NEW FILE########
__FILENAME__ = job_worker
import sys
import os
from rq import Queue, Worker, Connection
from rq.contrib.sentry import register_sentry
from rq.logutils import setup_loghandlers

current_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.dirname(current_dir)

sys.path.insert(0, source_dir)

if __name__ == '__main__':
    # Tell rq what Redis connection to use
    from pyhackers.app import start_app
    start_app(soft=True)
    from pyhackers.sentry import sentry_client

    setup_loghandlers("DEBUG")

    with Connection():
        q = Queue()
        w = Worker(q)

        register_sentry(sentry_client, w)
        w.work()
########NEW FILE########
__FILENAME__ = action
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, BigInteger, SmallInteger
from sqlalchemy.dialects import postgresql
from sqlalchemy import event
from pyhackers.db import DB as db
from pyhackers.utils import format_date
from datetime import datetime as dt


class Action(db.Model):
    __tablename__ = "action"

    id = db.Column(db.BigInteger, primary_key=True)
    from_id = db.Column(db.BigInteger, nullable=False)
    to_id = db.Column(db.BigInteger)
    action = db.Column(db.SmallInteger, nullable=False)
    created_at = db.Column(db.DateTime,default=dt.utcnow())
    deleted_at = db.Column(db.DateTime)
    deleted = db.Column(db.Boolean, default=False)

    def jsonable(self):
        return {
            'id': unicode(self.id),
            'from_id': unicode(self.from_id),
            'to_id': unicode(self.to_id),
            'action': unicode(self.action),
            'created_at': unicode(format_date(self.created_at)),
            'deleted_at': unicode(format_date(self.deleted_at)),
            'deleted': unicode(self.deleted),
        }

    def __str__(self):
        return str(self.jsonable())

    def __repr__(self):
        return str(self.jsonable())

from pyhackers.idgen import idgen_client

@event.listens_for(Action, 'before_insert')
def before_inventory_source_insert(mapper, connection, target):
    target.id = idgen_client.get()


class ActionType():

    FollowProject = 1
    UnFollowProject = 2
    FollowUser = 3
    UnFollowUser = 4
########NEW FILE########
__FILENAME__ = bucket
from sqlalchemy.dialects import postgresql
from pyhackers.db import DB as db
from pyhackers.utils import format_date


class Bucket(db.Model):
    __tablename__ = "bucket"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), index=True)
    user = db.relationship("User", )
    name = db.Column(db.Text, nullable=False)
    slug = db.Column(db.Text, nullable=False, index=True)
    created_at = db.Column(db.DateTime)
    follower_count = db.Column(db.Integer)
    projects = db.Column(postgresql.ARRAY(db.String))

    def jsonable(self):
        return {
            'id': unicode(self.id),
            'name': unicode(self.name),
            'slug': unicode(self.slug),
            'created_at': unicode(format_date(self.created_at)),
            'projects': unicode(self.projects),
            'follower_count': unicode(self.follower_count)
        }

    def __repr__(self):
        return str(self.jsonable())

    def __str__(self):
        return str(self.name)

########NEW FILE########
__FILENAME__ = connection
import logging
from cqlengine import connection


def setup(hosts=None, keyspace=None):

    model_keyspace = None
    cassa_hosts = None

    if hosts is None or keyspace is None:
        from pyhackers.config import config
        cassa_hosts = hosts or config.get("cassandra", "host")
        model_keyspace = config.get("cassandra", "keyspace")
    else:
        model_keyspace = keyspace
        cassa_hosts = hosts

    if isinstance(cassa_hosts, basestring):
        cassa_hosts = cassa_hosts.split(",")

    logging.warn("Keyspace: [{}] Hosts: [{}]".format(model_keyspace, cassa_hosts))

    return cassa_hosts, model_keyspace


def connect(cassa_host_list, default_keyspace):
    if cassa_host_list is None:
        pass
        #hosts = ['127.0.0.1:9160']

    connection.setup(cassa_host_list, default_keyspace=default_keyspace)
########NEW FILE########
__FILENAME__ = hierachy
import uuid
from cqlengine import columns
from cqlengine.models import Model
from datetime import datetime as dt
import time
from pyhackers.utils import unix_time, format_date


class MBase(Model):
    __abstract__ = True
    #__keyspace__ = model_keyspace


class PostCounter(MBase):
    id = columns.BigInt(index=True, primary_key=True)
    up_votes = columns.Counter()
    down_votes = columns.Counter()
    views = columns.Counter()
    karma = columns.Counter()
    replies = columns.Counter()


class Post(MBase):
    id = columns.BigInt(index=True, primary_key=True)
    user_id = columns.Integer(required=True, index=True, partition_key=True)
    # TODO: would be a terrible update if the nick is changed ever.
    user_nick = columns.Text()
    text = columns.Text(required=True)
    html = columns.Text(required=False)

    reply_to_id = columns.BigInt()
    reply_to_uid = columns.Integer()
    reply_to_nick = columns.Text()

    ext_id = columns.Text()

    has_url = columns.Boolean()
    has_channel = columns.Boolean()

    # this post is either linked to a DISCUSSION or
    discussion_id = columns.BigInt()
    # CHANNEL or None
    channel_id = columns.Integer()

    spam = columns.Boolean(default=False)
    flagged = columns.Boolean(default=False)
    deleted = columns.Boolean(default=False)

    stats = columns.Map(columns.Ascii, columns.Integer)

    published_at = columns.DateTime(default=dt.utcnow())

    def to_dict(self):
        return {'id': unicode(self.id),
                'text': self.text,
                'html': self.html,
                'user_id': self.user_id,
                'reply_to_id': self.reply_to_id,
                'reply_to_uid': self.reply_to_uid,
                'reply_to_nick': self.reply_to_nick,
                'discussion_id': self.discussion_id,
                'channel_id': self.channel_id,
                'spam': self.spam,
                'flagged': self.flagged,
                'deleted': self.deleted,
                'published_at': self.published_at,
                'ago': self.ago,
                'user': {'id': self.user_id, 'nick': self.user_nick},
                'stats': self.__dict__.get('statistics', {}),
                'upvoted': self.__dict__.get('upvoted', False),
        }

    @property
    def ago(self):
        result = int(int(int(time.time() - unix_time(self.published_at, float=True))) / 60.0)
        abb = "m"

        if result > (60 * 24):
            result /= (60 * 24)
            abb = "d"

        if result > 60:
            result /= 60
            abb = "h"

        return "{}{} ago".format(result, abb)


class Project(MBase):
    id = columns.Integer(primary_key=True)
    name = columns.Text()

    #follower_count = columns.Counter


class TopicCounter(MBase):
    id = columns.Integer(primary_key=True)
    views = columns.Counter()
    discussions = columns.Counter()
    messages = columns.Counter()


class Topic(MBase):
    id = columns.Integer(primary_key=True)
    slug = columns.Text()
    name = columns.Text()
    description = columns.Text()
    last_message_id = columns.BigInt(required=False)
    last_message_time = columns.DateTime(default=dt.utcnow())
    main_topic = columns.Boolean(default=False)
    parent_topic = columns.Integer(required=False)
    subtopics = columns.Set(value_type=columns.Integer)


class TopicDiscussion(MBase):
    topic_id = columns.Integer(primary_key=True, required=False)
    discussion_id = columns.BigInt(primary_key=True, required=False)


class Channel(MBase):
    id = columns.Integer(primary_key=True)
    slug = columns.Text(required=True, index=True)
    name = columns.Text(required=True)


class UserCounter(MBase):
    id = columns.Integer(primary_key=True)
    follower_count = columns.Counter()
    following_count = columns.Counter()
    karma = columns.Counter()
    up_vote_given = columns.Counter()
    up_vote_received = columns.Counter()
    down_vote_given = columns.Counter()
    down_vote_taken = columns.Counter()


class User(MBase):
    id = columns.Integer(primary_key=True)
    nick = columns.Text(required=True, index=True)

    extended = columns.Map(columns.Text, columns.Text)
    registered_at = columns.DateTime(default=dt.utcnow())
    created_at = columns.DateTime(default=dt.utcnow())

    def to_dict(self):
        return {
            'id': self.id,
            'nick': self.nick,
            'properties': self.extended,
        }


class UserDiscussion(MBase):
    user_id = columns.Integer(primary_key=True)
    discussion_id = columns.BigInt(primary_key=True)


class DiscussionCounter(MBase):
    id = columns.BigInt(primary_key=True)
    message_count = columns.Counter()
    user_count = columns.Counter()
    view_count = columns.Counter()
    follower_count = columns.Counter()

    def to_dict(self):
        return {
            'message_count': self.message_count,
            'user_count': self.user_count,
            'view_count': self.view_count,
            'follower_count': self.follower_count,
        }


class Discussion(MBase):
    id = columns.BigInt(primary_key=True)
    title = columns.Text(required=True)
    slug = columns.Text(required=True, index=True)
    user_id = columns.Integer(index=True)
    users = columns.Set(value_type=columns.Integer)
    post_id = columns.BigInt()
    last_message = columns.BigInt()
    published_at = columns.DateTime(default=dt.utcnow())
    topic_id = columns.Integer(required=False)

    def to_dict(self):
        return {
            'id': unicode(self.id),
            'title': self.title,
            'slug': self.slug,
            'user_id': self.user_id,
            'post_id': unicode(self.post_id),
            'last_message': unicode(self.last_message),
            'published_at': format_date(self.published_at),
            'topic_id': unicode(self.topic_id) if self.topic_id is not None else None,
        }

    @property
    def published_date(self):
        return format_date(self.published_at)


class DiscussionPost(MBase):
    disc_id = columns.BigInt(primary_key=True)
    post_id = columns.BigInt(primary_key=True)
    user_id = columns.Integer(primary_key=True)


class DiscussionFollower(MBase):
    """
    Users who follows a discussion
    """
    disc_id = columns.BigInt(primary_key=True)
    user_id = columns.Integer(primary_key=True)
    created_at = columns.DateTime(default=dt.utcnow())


class UserTimeLine(MBase):
    """
    POSTs that user will see in their timeline
    """
    user_id = columns.Integer(primary_key=True)
    post_id = columns.BigInt(primary_key=True)


class UserProject(MBase):
    """
    Projects that user follows
    """
    user_id = columns.Integer(primary_key=True)
    project_id = columns.Integer(primary_key=True)


class UserPost(MBase):
    """
    All the POSTs of a user
    """
    user_id = columns.Integer(primary_key=True)
    post_id = columns.BigInt(primary_key=True)


class UserFollower(MBase):
    """
    Followers of a user
    """
    user_id = columns.Integer(primary_key=True)
    follower_id = columns.Integer(primary_key=True)
    created_at = columns.DateTime(default=dt.utcnow())


class UserFollowing(MBase):
    """
    A user follows another user
    """
    user_id = columns.Integer(primary_key=True)
    following_id = columns.Integer(primary_key=True)
    created_at = columns.DateTime(default=dt.utcnow())


class ProjectFollower(MBase):
    project_id = columns.Integer(primary_key=True)
    user_id = columns.Integer(primary_key=True)
    created_at = columns.DateTime(default=dt.utcnow())


class PostFollower(MBase):
    post_id = columns.TimeUUID(primary_key=True)
    user_id = columns.Integer(primary_key=True)
    created_at = columns.DateTime(default=dt.utcnow())


class ChannelFollower(MBase):
    channel_id = columns.Integer(primary_key=True)
    user_id = columns.Integer(primary_key=True)
    created_at = columns.DateTime(default=dt.utcnow())


class ChannelTimeLine(MBase):
    channel_id = columns.Integer(primary_key=True)
    post_id = columns.BigInt(primary_key=True)


class ProjectTimeLine(MBase):
    project_id = columns.Integer(primary_key=True)
    post_id = columns.BigInt(primary_key=True)


class PostVote(MBase):
    post_id = columns.BigInt(primary_key=True, partition_key=True)
    user_id = columns.Integer(primary_key=True)
    positive = columns.Boolean(default=True)
    created_at = columns.DateTime(default=dt.utcnow())


class PostReply(MBase):
    post_id = columns.BigInt(primary_key=True)
    reply_post_id = columns.BigInt(primary_key=True)


class GithubProject(MBase):
    id = columns.Integer(primary_key=True)
    full_name = columns.Text(index=True)
    description = columns.Text()
    homepage = columns.Text()
    fork = columns.Boolean()
    forks_count = columns.Integer()
    language = columns.Text()
    master_branch = columns.Text()
    name = columns.Text()
    network_count = columns.Integer()
    open_issues = columns.Integer()
    url = columns.Text()
    watchers_count = columns.Integer()
    is_py = columns.Boolean()
    owner = columns.Integer()
    hide = columns.Boolean(default=False)


class GithubUser(MBase):
    nick = columns.Text(primary_key=True)
    id = columns.Integer(index=True)
    email = columns.Text()
    followers = columns.Integer()
    following = columns.Integer()
    image = columns.Text()
    blog = columns.Text()
    bio = columns.Text()
    company = columns.Text()
    location = columns.Text()
    name = columns.Text()
    url = columns.Text()
    utype = columns.Text()
    public_gists = columns.Integer()
    public_repos = columns.Integer()
    # Ref user info does not contain all the information.
    full_profile = columns.Boolean(default=True)


class GithubUserList(MBase):
    user = columns.Text(primary_key=True)
    starred = columns.List(value_type=columns.Text)
    following = columns.List(value_type=columns.Text)
    followers = columns.List(value_type=columns.Text)


class GithubEvent(MBase):
    id = columns.BigInt(primary_key=True)
    type = columns.Text()
    actor = columns.Text()
    org = columns.Text()
    repo = columns.Text()
    created_at = columns.Float()
    payload = columns.Text()
########NEW FILE########
__FILENAME__ = management
import sys
import logging
from cqlengine.management import sync_table, create_keyspace
import argparse
import textwrap


def create(cassa_key_space='pyhackers'):
    assert cassa_key_space != '' or cassa_key_space is not None

    logging.warn("Creating/Synchronizing {}".format(cassa_key_space))

    create_keyspace(cassa_key_space)

    sync_table(User)
    sync_table(Post)
    sync_table(Channel)
    sync_table(Project)

    # User related tables
    sync_table(UserTimeLine)
    sync_table(UserFollower)
    sync_table(UserFollowing)
    sync_table(UserPost)
    sync_table(UserProject)
    sync_table(UserDiscussion)
    sync_table(UserCounter)

    # Post related Tables
    sync_table(PostReply)
    sync_table(PostFollower)
    sync_table(PostCounter)
    sync_table(PostVote)

    # Channel Related Tables
    sync_table(ChannelFollower)
    sync_table(ChannelTimeLine)

    # Topic Related Topics
    sync_table(Topic)
    sync_table(TopicCounter)
    sync_table(TopicDiscussion)

    # Project Related
    sync_table(ProjectFollower)
    sync_table(ProjectTimeLine)

    # Discussions yoo
    sync_table(Discussion)
    sync_table(DiscussionPost)
    sync_table(DiscussionCounter)
    sync_table(DiscussionFollower)

    sync_table(GithubProject)
    sync_table(GithubUser)
    sync_table(GithubUserList)
    sync_table(GithubEvent)


def test_insert():
    from datetime import datetime as dt

    User.create(id=1, nick='bcambel', created_at=dt.utcnow(),
                extended={'test': "test"})

    Post.create(id=1, text="Testing")


def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=textwrap.dedent("""Screen6"""))
    parser.add_argument('hosts', )
    parser.add_argument('keyspace')

    return parser.parse_args()


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}

    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


if __name__ == '__main__':

    args = parse_args()
    from connection import setup, connect

    connect(*setup(args.hosts, args.keyspace))
    from hierachy import *

    if query_yes_no('Are you sure to sync ?', default='no'):
        create(args.keyspace)
        print "Done...."
    else:
        print "No is also a good thing. Bye!"
########NEW FILE########
__FILENAME__ = channel
from pyhackers.db import DB as db
from pyhackers.utils import format_date


class Channel(db.Model):
    __tablename__ = "channel"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    slug = db.Column(db.Text, nullable=False, index=True, unique=True)
    created_at = db.Column(db.DateTime)

    post_count = db.Column(db.BigInteger)

    disabled = db.Column(db.Boolean)

    def jsonable(self):
        return {
            'id': unicode(self.id),
            'name': unicode(self.name),
            'slug': unicode(self.slug),
            'post_count': unicode(self.post_count),
            'disabled': unicode(self.disabled),
            'created_at': unicode(format_date(self.created_at)),
        }

    def __repr__(self):
        return str(self.jsonable())

    def __str__(self):
        return str(self.name)


########NEW FILE########
__FILENAME__ = feed
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text
from pyhackers.common.stringutils import safe_str
from pyhackers.common.dbfield import Choice
from pyhackers.db import DB as db


FeedStatuses = (
    ('done', 'DONE'),
    ('error', 'ERROR'),
    ('scheduled', 'SCHEDULED'),
    ('moved', 'MOVED'),
    ('nf', "NF"),
    ('?', '?'),
)


class Feed(db.Model):
    __tablename__ = 'feed'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(length=100))
    slug = Column(Text())

    description = Column(Text())
    href = Column(Text)
    link = Column(Text)
    rss = Column(Text)
    rss_hash = Column(Text, index=True)
    lang = Column(String(length=3))
    etag = Column(Text)
    updated = Column(DateTime())
    published = Column(DateTime())
    version = Column(Text)
    author = Column(Text)

    status_code = Column(Integer())
    status = Column(Choice(FeedStatuses))

    last_post = Column(DateTime())
    last_check = Column(DateTime())
    next_check = Column(DateTime())
    active = Column(Boolean())
    top = Column(Boolean())
    news = Column(Boolean())

    logo = Column(Text())

    posts = relationship(Post)


class FeedHistory(db.Model):
    __tablename__ = 'feed_history'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime())
    http_status_code = Column(Integer())  # HTTP Status Code [20x,30x,40x,50x]
    post_count = Column(Integer())
    etag = Column(Text)
    feed_id = Column(Integer())


class Post(db.Model):
    __tablename__ = "post"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text())
    author = Column(Text())
    href = Column(Text())
    content_html = Column(Text())
    original_link = Column(Text())
    title_hash = Column(Text, index=True)
    link_hash = Column(Text, index=True)
    post_id = Column(Text())  # most of the time websites publish a URL
    post_id_hash = Column(Text, index=True)
    media = Column(postgresql.ARRAY(String))
    lang = Column(Text)
    tags = Column(postgresql.ARRAY(String))
    published_at = Column(DateTime)
    feed_id = Column(Integer, ForeignKey('feed.id'))

    stats_fb = Column(Integer)
    stats_tw = Column(Integer)

    fetched = Column(Boolean(), default=False)
    indexed = Column(Boolean(), default=False)
    trending = Column(Boolean(), default=False)
    hot = Column(Boolean(), default=False)

    def __repr__(self):
        return "<Post: %s (by %s) %s>" % (safe_str(self.title), self.author, self.href)

    @property
    def original_title(self):
        if hasattr(self, '_original_title'):
            return self._original_title
        else:
            return self.title

    @original_title.setter
    def original_title(self, value):
        self._original_title = value

    @property
    def original_author(self):
        if hasattr(self, '_original_author'):
            return self._original_author
        else:
            return self.author

    @original_author.setter
    def original_author(self, value):
        self._original_author = value
########NEW FILE########
__FILENAME__ = message
from datetime import datetime as dt
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, BigInteger
from sqlalchemy.dialects import postgresql
from sqlalchemy import event
from pyhackers.db import DB as db
from pyhackers.utils import format_date
from pyhackers.model.user import User
from pyhackers.model.channel import Channel


class Message(db.Model):
    __tablename__ = "message"

    id = db.Column(BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship(User)
    user_nick = db.Column(db.String)
    reply_to_id = db.Column(db.String)
    reply_to_uid = db.Column(db.String)
    reply_to_uname = db.Column(db.String)

    ext_id = db.Column(String)
    ext_reply_id = db.Column(String())

    slug = db.Column(Text)
    content = db.Column(Text)
    content_html = db.Column(Text)
    lang = db.Column(String(length=3))

    mentions = db.Column(postgresql.ARRAY(String))
    urls = db.Column(postgresql.ARRAY(String))
    tags = db.Column(postgresql.ARRAY(String))
    media = db.Column(postgresql.ARRAY(String))

    has_url = db.Column(db.Boolean)
    has_channel = db.Column(db.Boolean)

    karma = db.Column(db.Float)
    up_votes = db.Column(db.Integer)
    down_votes = db.Column(db.Integer)
    favorites = db.Column(db.Integer)

    published_at = db.Column(db.DateTime, default=dt.utcnow())

    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), index=True,)
    channel = db.relationship(Channel)
    channels = db.Column(postgresql.ARRAY(String))

    spam = db.Column(db.Boolean, default=False)
    flagged = db.Column(db.Boolean, default=False)

    deleted = db.Column(db.Boolean, default=False)

    def jsonable(self, date_converter=format_date):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'reply_to_id': str(self.reply_to_id),
            'content': self.content,
            'content_html': self.content_html,
            'lang': self.lang,
            'published_at': date_converter(self.published_at),
            'media': self.media,
            'channels': self.channels,
            'mentions': self.mentions,
            "urls": self.urls,
            "tags": self.tags,
        }

    def __str__(self):
        return str(self.jsonable())

from pyhackers.idgen import idgen_client

@event.listens_for(Message, 'before_insert')
def before_inventory_source_insert(mapper, connection, target):
    pass
    #if target.id is None:
    #    target.id = idgen_client.get()
########NEW FILE########
__FILENAME__ = os_project
from sqlalchemy.dialects import postgresql
from pyhackers.db import DB as db


class OpenSourceProject(db.Model):
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column('name', db.String(100), nullable=False)
    slug = db.Column('slug', db.String(100), unique=True, index=True, nullable=False)
    description = db.Column('description', db.Unicode(500))
    src_url = db.Column('src_url', db.Unicode(200))
    doc_url = db.Column('doc_url', db.Unicode(200))
    stars = db.Column('starts', db.Integer)
    watchers = db.Column('watchers', db.Integer)
    forks = db.Column('forks', db.Integer)
    parent = db.Column("parent", db.String(100), nullable=True, index=True )
    categories = db.Column("categories", postgresql.ARRAY(db.String))

    hide = db.Column("hide", db.Boolean, default=False)
    lang = db.Column("lang", db.SmallInteger, default=0)
    __tablename__ = 'os_project'


    def to_dict(self, **kwargs):
        result = {
            'id' : unicode(self.id),
            'slug' : unicode(self.slug),
            'name' : unicode(self.name),
            'src_url' : unicode(self.src_url),
            'description' : unicode(self.description),
            'watchers': self.watchers
        }

        result.update(**kwargs)
        return result
########NEW FILE########
__FILENAME__ = package
__author__ = 'bahadircambel'
from pyhackers.db import DB as db
from pyhackers.utils import nice_number


class Package(db.Model):
    __tablename__ = 'package'

    name = db.Column('name', db.Text, nullable=False,index=True,primary_key=True)
    author = db.Column('author', db.Text, nullable=False)
    author_email = db.Column('author_email', db.Text, nullable=False)
    summary = db.Column('summary', db.Text, nullable=False)
    description = db.Column('description', db.Text, nullable=False)
    url = db.Column('url', db.Text, nullable=False)
    mdown = db.Column('mdown', db.Integer, nullable=False)
    wdown = db.Column('wdown', db.Integer, nullable=False)
    ddown = db.Column('ddown', db.Integer, nullable=False)
    data = db.Column('data', db.Text, nullable=False)

    @property
    def download(self):
        return nice_number(self.mdown)
########NEW FILE########
__FILENAME__ = tutorial
import logging
from datetime import datetime as dt
from pyhackers.db import DB as db
from pyhackers.utils import markdown_to_html, format_date


class Tutorial(db.Model):
    __tablename__ = "tutorial"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), index=True)
    user = db.relationship("User", )

    title = db.Column(db.Text, nullable=False)
    slug = db.Column(db.Text, nullable=False, index=True)

    keywords = db.Column(db.Text, nullable=False)
    meta_description = db.Column(db.Text, nullable=False)

    content = db.Column(db.Text, nullable=False)
    content_html = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime)
    generated_at = db.Column(db.DateTime)

    publish = db.Column(db.Boolean, default=True)
    spam = db.Column(db.Boolean, default=False)

    upvote_count = db.Column(db.Integer, default=1)

    @staticmethod
    def to_dict(obj):
        assert isinstance(obj, Tutorial)

        return {
            'id': unicode(obj.id),
            'title': unicode(obj.name),
            'slug': unicode(obj.slug),
            'created_at': unicode(format_date(obj.created_at)),
            'generated_at': unicode(format_date(obj.generated_at)),
            'keywords': unicode(obj.keywords),
            'content': unicode(obj.content),
            'content_html': unicode(obj.content_html),
            'meta_description': unicode(obj.meta_description),
            'upvote_count': obj.upvote_count or 0,
            'spam': obj.spam
        }

    def __repr__(self):
        return str(Tutorial.to_dict(self))

    def __str__(self):
        return str(self.name)


@db.event.listens_for(Tutorial, 'before_insert')
@db.event.listens_for(Tutorial, 'before_update')
def before_insert(mapper, connection, target):
    logging.warn("Running for before insert")
    target.content_html = markdown_to_html(target.content)
    target.generated_at = dt.utcnow()


#
#def after_insert(mapper, connection, target):
#    logging.warn("Running for after insert")
#    target.content_html  = markdown2.markdown(target.content, extras=['fenced-code-blocks'])
########NEW FILE########
__FILENAME__ = user
from flask.ext.login import UserMixin
from sqlalchemy import Boolean, Column, Integer, String, Float, SmallInteger, DateTime, Text
from sqlalchemy.orm import relationship
from pyhackers.db import DB as db


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nick = Column(db.Text, unique=True, index=True)
    email = Column(db.Text, index=True, unique=True)
    password = Column(db.Text)
    first_name = Column(db.Text, nullable=True)
    last_name = Column(db.Text, nullable=True)

    follower_count = Column(Integer, nullable=True)
    following_count = Column(Integer, nullable=True)

    lang = Column(String(5), nullable=True)
    loc = Column(String(50), nullable=True)

    pic_url = Column(String(200))

    role = Column(db.Integer, default=1, nullable=False)

    social_accounts = relationship('SocialUser', lazy='dynamic')

    def __str__(self):
        return unicode(self.nick)

    def __repr__(self):
        return unicode(self.jsonable())

    def jsonable(self):
        return dict(
            id=self.id,
            nick=self.nick,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            followers=self.follower_count,
            following=self.following_count,
            lang=self.lang,
            loc=self.loc,
            picture=self.pic_url
        )


class SocialUser(db.Model):
    __tablename__ = 'social_user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    email = Column(String(120), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relation(User)
    nick = Column(String(64), index=True)
    acc_type = Column(String(2), nullable=False)
    follower_count = Column(Integer, nullable=True)
    following_count = Column(Integer, nullable=True)
    ext_id = Column(String(50))
    access_token = Column(String(100))
    hireable = Column(Boolean)

    def __repr__(self):
        return '<SocialUser %s-%s->' % (self.acc_type, self.user_id)


def new_user(nick, email):
    u = User()
    u.nick = nick
    u.email = email
    db.session.add(u)
    db.session.commit()
########NEW FILE########
__FILENAME__ = import_packages
from __future__ import print_function
import logging
from pyhackers.utils import files_in
import simplejson
from os import listdir
from os.path import join, isfile
from pyhackers.config import config
from pyhackers.model.package import Package
from pyhackers.db import DB as db
import codecs

package_directory = '/Users/bahadircambel/code/learning/pythonhackers/packages'


def import_package(package_dict):
    inf = package_dict['info']
    p = Package()
    p.name = inf.get('name')
    p.summary = inf.get('summary', "")
    p.description = inf.get('description', "")
    #p.version = inf.get('version')
    p.author = inf.get('author', "")
    p.author_email = inf.get('author_email', "")
    p.url = inf.get("home_page", "")
    downloads = inf.get("downloads")
    p.mdown = downloads.get("last_month")
    p.wdown = downloads.get("last_week")
    p.ddown = downloads.get("last_day")

    p.data = ""
    #p.data = package_dict
    #try:
    #logging.warn(u"{name}-{version}-{mdown},{wdown},{ddown}-{url}-{summary}".format(p.__dict__))
    #except Exception,ex:
     #   logging.exception(ex)
    db.session.add(p)
    try:
        db.session.commit()
    except Exception, ex:
        db.session.rollback()
        logging.exception(ex)


def find_files(directory):

    for file in files_in(directory):
        try:
            lines = codecs.open(file, "r", "utf-8").readlines()
            json_file = u" ".join(lines)
            data = simplejson.loads(json_file)
            import_package(data)
        except Exception,ex:
            logging.warn(u"Exception for {} - {}".format(file, ex))
            logging.exception(ex)
            raise ex



#find_files(package_directory)
# from pyhackers.app import start_app;start_app();from pyhackers.scripts.import_packages import *;find_files(package_directory)
########NEW FILE########
__FILENAME__ = sentry
from pyhackers.config import SENTRY_DSN
from raven.contrib.flask import Sentry
from raven.base import DummyClient
import logging
from pyhackers.app import app

sentry_client = None


def init(app):
    global sentry_client
    logging.warn("Initialization sentry {}".format(SENTRY_DSN))

    if SENTRY_DSN is None:
        sentry_client = DummyClient()
    else:
        try:
            sentry_client = Sentry(app, dsn=SENTRY_DSN)
            #sentry.captureMessage("Configuration is loaded. App is restarted...")
        except Exception, ex:
            logging.exception(ex)
            try:
                sentry_client = DummyClient(SENTRY_DSN)
            except:
                logging.error("""
    ======Failed to initialize Sentry client... The sentry client will run in DummyMode
    ======Restart Application to try to connect to Sentry again
    ======Check the previous error that output
    ======CONFIG: SENTRY_DSN => [%s]
    ======The application will run now...
    """ % SENTRY_DSN)

    return sentry_client


init(app)
########NEW FILE########
__FILENAME__ = channel
import logging
from pyhackers.model.cassandra.hierachy import ChannelFollower, Channel as CsChannel
from pyhackers.model.channel import Channel


def follow_channel(channel_id, current_user):
    ChannelFollower.create(channel_id=channel_id, user_id=current_user.id)


def load_channel(slugish):
    slug = slugish.lower()

    logging.info(u"Loading channel {}".format(slug))
    ch = Channel.query.filter_by(slug=slug).first()
    logging.info(ch)

    cassa_channel = CsChannel.filter(slug=slug).first()

    logging.info(cassa_channel)

    if cassa_channel is None and ch is not None:
        CsChannel.create(id=ch.id, slug=ch.slug, name=ch.name)


def get_channel_list():
    channels = [channel for channel in Channel.query.all()]
    return channels
########NEW FILE########
__FILENAME__ = discuss
import logging
from cqlengine.query import DoesNotExist
from pyhackers.events import Event
from pyhackers.idgen import idgen_client
from pyhackers.model.cassandra.hierachy import Post, Discussion, DiscussionPost, DiscussionCounter, UserDiscussion, \
    User as CsUser, DiscussionFollower
from pyhackers.service.post import new_post, load_posts
from pyhackers.service.user import load_user_profiles
from pyhackers.utils import markdown_to_html

from slugify import slugify

from datetime import datetime as dt


def load_discussions():
    discussions = Discussion.objects.all().limit(50)

    return discussions


def load_discussions_by_id(ids):
    return Discussion.objects.filter(id__in=ids).limit(50)


def load_discussion(slug, discussion_id, current_user_id=None):
    discussion = Discussion.objects.get(id=discussion_id)
    #discussion, disc_posts, users, counters = discussion_messages(discussion_id)

    try:
        message = Post.objects.get(id=discussion.post_id)
    except DoesNotExist:
        message = {}

    followers = [d.user_id for d in DiscussionFollower.objects.filter(disc_id=discussion_id)]
    user = {}

    if current_user_id in followers:
        user = {'id': current_user_id, 'following': True}

    try:
        counters = DiscussionCounter.get(id=discussion_id)
    except DoesNotExist:
        counters = {'message_count': 1, 'user_count': 1, 'view_count': 0}

    # TODO: Utterly we will place this into a background job (more like log processed counter)
    Event.discussion_view(current_user_id, discussion_id)

    return discussion, [], message, counters, user


def discussion_messages(discussion_id, after_message_id=None, limit=100, current_user_id=None):
    logging.warn("Requesting: {} After: {}".format(discussion_id, after_message_id))

    discussion = Discussion.objects.get(id=discussion_id)

    if after_message_id is not None:
        post_filter = DiscussionPost.objects.filter(disc_id=discussion_id,
                                                    post_id__gt=after_message_id)
    else:
        post_filter = DiscussionPost.objects.filter(disc_id=discussion_id)

    #FIXME: Here we only get 100 records right now. No Sorting, paging, nothing. Too bad!
    disc_post_lists = [(p.post_id, p.user_id) for p in post_filter.limit(limit)]
    post_ids = list(set([x[0] for x in disc_post_lists]))
    user_ids = list(set([x[1] for x in disc_post_lists]))
    users = load_user_profiles(user_ids)

    logging.warn("Looking for posts: {}".format(post_ids))
    disc_posts = load_posts(post_ids, current_user_id=current_user_id)
    for post in disc_posts:
        u = filter(lambda x: x.id == post.user_id, users)

        post.user = u[0] if u is not None else None

    try:
        counters = DiscussionCounter.get(id=discussion_id)
    except DoesNotExist:
        counters = {'message_count': 1, 'user_count': 1, 'view_count': 0}

    return discussion, disc_posts, users, counters


def new_discussion(title, text, current_user_id=None):
    disc_id = idgen_client.get()
    post_id = idgen_client.get()

    slug = slugify(title)

    d = Discussion()
    d.id = disc_id
    d.post_id = post_id
    d.message_count = 1
    d.title = title
    d.published_at = dt.utcnow()
    d.user_count = 1
    d.users = {current_user_id}
    d.slug = slug

    d.save()

    disc_counter = DiscussionCounter(id=disc_id)
    disc_counter.message_count = 1
    disc_counter.user_count = 1
    disc_counter.view_count = 1
    disc_counter.save()

    UserDiscussion.create(user_id=current_user_id, discussion_id=d.id)

    new_post(text, code='', current_user_id=current_user_id, post_id=post_id)

    return disc_id, slug


def new_discussion_message(discussion_id, text, current_user_id, nick=''):
    logging.warn("DSCSS:[{}]USER:[{}]".format(discussion_id, current_user_id))
    discussion = Discussion.objects.get(id=discussion_id)

    p = Post()
    p.id = idgen_client.get()
    p.discussion_id = discussion_id
    p.text = text
    p.html = markdown_to_html(text)
    p.user_id = current_user_id
    p.user_nick = nick
    ## Create an entry in the timeline to say that this user
    # has created a post in the given discussion
    # Event.new_post_message

    p.save()

    Event.message(current_user_id, p.id, None)

    # FIXME: Move all this part to the JOB WORKER! Speed my friend.

    discussion.last_message = p.id
    discussion.users.union({current_user_id})
    discussion.save()

    UserDiscussion.create(user_id=current_user_id, discussion_id=discussion_id)

    dp = DiscussionPost.create(disc_id=discussion_id, post_id=p.id, user_id=current_user_id)
    dp.save()

    disc_counter = DiscussionCounter(id=discussion_id)
    disc_counter.message_count += 1
    disc_counter.save()

    return p.id


def get_user_discussion_by_nick(nick):
    try:
        user = CsUser.filter(nick=nick).first()
    except DoesNotExist, dne:
        user = None

    if user is None:
        return

    discussions = list([d.discussion_id for d in UserDiscussion.objects.filter(user_id=user.id)])

    return user, load_discussions_by_id(discussions)


def new_discussion_follower(discussion_id, current_user_id, nick=None):
    dc = DiscussionCounter.get(id=discussion_id)
    dc.follower_count += 1
    dc.save()

    DiscussionFollower.create(disc_id=discussion_id, user_id=current_user_id)


def remove_discussion_follower(discussion_id, current_user_id):
    try:
        follower = DiscussionFollower.objects.filter(disc_id=discussion_id, user_id=current_user_id).first()
        follower.delete()
        dc = DiscussionCounter.get(id=discussion_id)
        dc.follower_count -= 1
        dc.save()
    except DoesNotExist:
        pass

########NEW FILE########
__FILENAME__ = post
import logging
from cqlengine.query import DoesNotExist
from pyhackers.idgen import idgen_client
from pyhackers.model.cassandra.hierachy import Post, PostVote, PostCounter
from pyhackers.events import Event
from pyhackers.utils import markdown_to_html


def load_posts(post_ids, current_user_id=None):
    """
    Select multiple posts from the service.
    We will definitely need to [mem]Cache these records to do a fast lookup batch query.
    Of course also cache invalidation needs to be considered.
    """
    logging.warn("Ids===={}".format(post_ids))

    # If list is not used, or any call that trigger __iter__ will end up with the query syntax
    # rather than the data itself.
    #posts_query = Post.objects.filter(id__in=post_ids).limit(100).allow_filtering()
    #post_counters = list(PostCounter.objects.filter(id__in=post_ids).limit(100).allow_filtering())

    post_objects = []
    # ok ,
    for post_id in post_ids:
        p = Post.objects.get(id=post_id)

        try:
            pc = PostCounter.objects.get(id=post_id) #filter(lambda x: x.id == post.id, post_counters)
            stats = pc._as_dict()
            del stats['id']
            p.__dict__['statistics'] = stats
        except DoesNotExist, dne:
            pass

        if current_user_id is not None:
            try:
                pv = PostVote.objects.get(post_id=post_id, user_id=current_user_id)
                p.__dict__['upvoted'] = True
            except DoesNotExist, dne:
                pass
        post_objects.append(p)

    return post_objects


def new_post(text, code=None, current_user_id=None, post_id=None, nick=None):
    logging.warn("Post is=>{}".format(post_id))

    html = markdown_to_html(text)

    message = Post()
    message.id = post_id or idgen_client.get()
    message.text = text
    message.html = html
    message.user_id = current_user_id
    message.user_nick = nick
    message.save()

    Event.message(current_user_id, message.id, None)


def upvote_message(message_id, current_user_id=None):
    try:
        Post.objects.get(id=message_id)
    except DoesNotExist, dne:
        return

    try:
        already_vote = PostVote.objects.get(post_id=message_id, user_id=current_user_id)
        if already_vote.posivite:
            return
    except DoesNotExist, dne:
        pass

    PostVote.create(post_id=message_id, user_id=current_user_id, positive=True)

    try:
        pc = PostCounter.objects.get(id=message_id)
    except DoesNotExist, dne:
        pc = PostCounter.create(id=message_id)

    if pc is not None:
        pc.up_votes += 1
        pc.save()

    Event.up_vote(current_user_id,message_id)
########NEW FILE########
__FILENAME__ = project
from datetime import datetime as dt
import logging
from pyhackers.db import DB as db
from pyhackers.model.action import Action, ActionType
from pyhackers.model.cassandra.hierachy import ProjectFollower, UserProject
from pyhackers.model.os_project import OpenSourceProject
from pyhackers.service.user import user_list_from_ids
from pyhackers.sentry import sentry_client

#sentry_client = get_sentry_client()

def project_follow(project_id, current_user):
    a = Action()
    a.from_id = current_user.id
    a.to_id = project_id
    a.action = ActionType.FollowProject
    a.created_at = dt.utcnow()

    db.session.add(a)

    success = False
    try:
        db.session.commit()
        success = True
    except Exception, ex:
        db.session.rollback()
        logging.exception(ex)

    if success:
        ProjectFollower.create(project_id=project_id, user_id=current_user.id)
        UserProject.create(project_id=project_id, user_id=current_user.id)


def load_project(slug, current_user):

    project = OpenSourceProject.query.filter_by(slug=slug).first()
    if project is None:
        return

    related_projects = OpenSourceProject.query.filter_by(parent=slug).order_by(
        OpenSourceProject.watchers.desc()).limit(100)

    follower_list = []

    try:
        followers = [f.user_id for f in ProjectFollower.filter(project_id=project.id).limit(20)]
        follower_list = [f for f in user_list_from_ids(followers)]
    except Exception, ex:
        sentry_client.captureException()
        logging.exception(ex)

    return project, related_projects, follower_list
########NEW FILE########
__FILENAME__ = user
import logging
from cqlengine.query import DoesNotExist
from pyhackers.service.post import load_posts
from pyhackers.worker.hipchat import notify_registration
from pyhackers.model.user import SocialUser, User
from pyhackers.model.os_project import OpenSourceProject
from pyhackers.model.action import Action, ActionType
from pyhackers.db import DB as db
from pyhackers.model.cassandra.hierachy import User as CsUser, UserFollower, UserFollowing, UserProject, Project, UserPost, UserDiscussion
from pyhackers.sentry import sentry_client
from pyhackers.job_scheduler import worker_queue


def create_user_from_github_user(access_token, github_user):
    # FIXME: Unacceptable method. Too long, doing a lot of stuff, error prone, etc..
    # FIXME: Refactor me please. Destruct me

    logging.warn("[USER][GITHUB] {}".format(github_user))

    user_login = github_user.get("login")

    social_account = SocialUser.query.filter_by(nick=user_login, acc_type='gh').first()

    user = User.query.filter_by(nick=user_login).first()

    #if user is not None:
    #    return user
    u = user
    email = github_user.get("email", "")
    name = github_user.get("name", "")

    if user is None:
        u = User()
        #u.id = idgen_client.get()
        u.nick = user_login
        u.email = email
        u.pic_url = github_user.get("avatar_url")

        name_parts = name.split(" ")

        if len(name_parts) > 1:
            u.first_name = name_parts[0] or ""
            u.last_name = " ".join(name_parts[1:])
        else:
            u.last_name = name

    if social_account is None:

        su = SocialUser()

        su.user_id = u.id
        su.nick = user_login
        su.acc_type = 'gh'
        su.email = email
        su.follower_count = github_user.get("followers")
        su.following_count = github_user.get("following")
        su.blog = github_user.get("blog")
        su.ext_id = github_user.get("id")
        su.name = github_user.get("name", "")
        su.hireable = github_user.get("hireable", False)
        su.access_token = access_token
        u.social_accounts.append(su)

        db.session.add(u)

        try:
            db.session.commit()
        except Exception, e:
            logging.warn(e)
            db.session.rollback()
            sentry_client.captureException()
        finally:
            CsUser.create(id=u.id, nick=u.nick, extended=dict(pic=u.pic_url))
        try:
            notification = u"Id:{} Nick:[{}] Name:[{}] Email:[{}] Followers:{}".format(u.id, user_login, name,
                                                                                       email,
                                                                                       github_user.get("followers", 0))

            worker_queue.enqueue(notify_registration, args=(notification,), result_ttl=0)
        except Exception, ex:
            logging.exception(ex)
            sentry_client.captureException()

    return u


def follow_user(user_id, current_user):
    if str(user_id) == str(current_user.id):
        logging.warn(u"Don't follow yourself {}".format(user_id))
        return False

    a = Action()
    a.from_id = current_user.id
    a.to_id = user_id
    a.action = ActionType.FollowUser
    db.session.add(a)
    success = False
    try:
        db.session.commit()
        success = True
    except Exception, ex:
        db.session.rollback()

    if success:
        UserFollower.create(user_id=user_id, follower_id=current_user.id)
        UserFollowing.create(user_id=current_user.id, following_id=user_id)

    return success


def user_list_from_ids(ids, dict=True):
    temp_user = CsUser.filter(CsUser.id.in_(set(ids))).limit(50)

    if dict:
        user_list = []
        for u in temp_user:
            d = u._as_dict()
            extras = u.extended
            d.update(**extras)
            user_list.append(d)

        return user_list
    else:
        return temp_user


def load_user_profiles(user_ids):
    return list(CsUser.objects.filter(id__in=user_ids).allow_filtering())


def load_user(user_id, current_user=None):
    """
    Loads all the details about the user including Followers/Following/OpenSource projects list.
    """
    logging.warn("Loading user {}".format(user_id))
    user = User.query.get(user_id)

    user_followers, user_following = [], []

    # FIXME: This try/except block is ugly as hell. Refactor please!
    try:
        followers = [f.follower_id for f in UserFollower.filter(user_id=user_id).limit(20)]
        following = [f.following_id for f in UserFollowing.filter(user_id=user_id).limit(20)]

        cassa_users = user_list_from_ids(set(followers + following), dict=True)

        def expand(o):
            extras = o.extended
            dict_val = o._as_dict()
            dict_val.update(**extras)
            return dict_val

        user_followers = [filter(lambda x: x.get('id') == u, cassa_users)[0] for u in followers]
        user_following = [filter(lambda x: x.get('id') == u, cassa_users)[0] for u in following]

    except Exception, ex:
        logging.warn(ex)
        sentry_client.captureException()

    return user, user_followers, user_following


def get_profile(current_user):
    return load_user(current_user.id)


def get_profile_by_nick(nick):
    user = None
    exception = False

    try:
        user = CsUser.filter(nick=nick).first()
    except Exception, ex:
        exception = True
        logging.exception(ex)
        sentry_client.captureException()

    if user is None and exception:
        # FIXME: backoff to our Postgres. Field Names are different!
        try:
            user = User.query.filter_by(nick=nick)

            return user, [], [], []
        except:
            return None

    if user is None:
        return None

    return load_user(user.id)


def get_user_projects_by_nick(nick):
    try:
        user = CsUser.filter(nick=nick).first()
    except DoesNotExist, dne:
        user = None

    if user is None:
        return

    projects = [p.project_id for p in UserProject.filter(user_id=user.id)]
    os_projects = OpenSourceProject.query.filter(OpenSourceProject.id.in_(projects)).order_by(
            OpenSourceProject.stars.desc()).all()

    return user, os_projects


def get_user_timeline_by_nick(nick):
    try:
        user = CsUser.filter(nick=nick).first()
    except DoesNotExist, dne:
        user = None

    if user is None:
        return

    posts = [p.post_id for p in UserPost.objects.filter(user_id=user.id).order_by('-post_id').limit(5)]

    return user, reversed(load_posts(posts)or [])


def load_github_data():
    return
    access_token, config = None



    user = g.get_user("mitsuhiko")
    #TODO: Create a task to fetch all the other information..



    pub_events = user.get_public_events()

    for e in pub_events:
         print e.id, e.type, e.repo.full_name
########NEW FILE########
__FILENAME__ = project_finder
from pyhackers.config import config
import requests
import logging
import time
from pyhackers.model.os_project import OpenSourceProject
from pyhackers.db import DB as db
from sqlalchemy.exc import IntegrityError

client_id = config.get("github", 'client_id')
client_secret = config.get("github", 'client_secret')

url = 'https://api.github.com'
read_me_url = '/repos/{user}/{repo}/readme'

fields = ['id', 'name', 'full_name', 'description', 'owner', 'html_url', 'git_url', 'watchers_count', 'forks_count',
          'open_issues_count', 'created_at', 'updated_at']

session = requests.Session()


def search_repo(query, page=1):
    qs = 'q=%s&sort=stars&per_page=100&page=%d&order=desc&client_id=%s&client_secret=%s' % (
        query, page, client_id, client_secret)
    data = session.get(url + "/search/repositories",
                       params=qs,
                       # params={'q': query, 'sort': 'stars', 'order': 'desc',
                       #         'client_id': client_id, 'client_secret': client_secret},
                       headers={'Accept': 'application/vnd.github.preview'})

    return data.json().get('items', None)


def importer(query, parent=None, exclude=None):
    for i in range(1, 11):
        popular_projects = search_repo(query, i)
        if popular_projects is None or len(popular_projects) <= 0:
            break

        for i, project in enumerate(popular_projects):
            if project is None:
                break

            logging.warn("%d. %s %s %s" % (i, project[fields[1]], project[fields[7]], project[fields[8]]))
            os_proj = OpenSourceProject()
            os_proj.name = project["name"]
            slug = project.get("full_name", str(int(time.time())))

            if parent is not None and (slug == parent or (exclude is not None and slug in exclude)):
                continue

            os_proj.slug = slug
            os_proj.description = project.get('description', '')
            os_proj.watchers = project['watchers_count']
            os_proj.stars = project['watchers_count']
            os_proj.src_url = project['html_url']
            os_proj.git_url = project['git_url']
            os_proj.parent = parent
            db.session.add(os_proj)

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

                proj = OpenSourceProject.query.filter_by(slug=slug).first()
                proj.watchers = project['watchers_count']
                proj.parent = parent
                proj.stars = project['watchers_count']

                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()


python_search = '+language:python'
django_search = 'django+language:python'
flask_search = 'flask+language:python'


def import_repos():
    try:
        importer(python_search)
    finally:
        pass
    try:
        importer(django_search, 'django/django', ['django/django-old'])
    finally:
        pass
    try:
        importer(flask_search, 'mitsuhiko/flask')
    finally:
        pass




########NEW FILE########
__FILENAME__ = resolve_link

# https://github.com/ianozsvald/twitter-text-python/blob/master/ttp/utils.py


import requests


def follow_shortlinks(shortlinks):
    """Follow redirects in list of shortlinks, return dict of resulting URLs"""
    links_followed = {}
    for shortlink in shortlinks:
        url = shortlink
        request_result = requests.get(url)
        redirect_history = request_result.history
        # history might look like:
        # (<Response [301]>, <Response [301]>)
        # where each response object has a URL
        all_urls = []
        for redirect in redirect_history:
            all_urls.append(redirect.url)
        # append the final URL that we finish with
        all_urls.append(request_result.url)
        links_followed[shortlink] = all_urls
    return links_followed


if __name__ == "__main__":
    shortlinks = ['http://t.co/8o0z9BbEMu', u'http://bbc.in/16dClPF']
    print follow_shortlinks(shortlinks)
########NEW FILE########
__FILENAME__ = textractor
#  This file is part of twitter-text-python.
#
#  twitter-text-python is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  twitter-text-python is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  twitter-text-python. If not, see <http://www.gnu.org/licenses/>.

# Forked by Ian Ozsvald:
# https://github.com/ianozsvald/twitter-text-python
# from:
# https://github.com/BonsaiDen/twitter-text-python

# Modifications by Bahadir Cambel


# Tweet Parser and Formatter ---------------------------------------------------
# ------------------------------------------------------------------------------
import re
import urllib

__version__ = "1.0.1.0"

# Some of this code has been translated from the twitter-text-java library:
# <http://github.com/mzsanford/twitter-text-java>
AT_SIGNS = ur'[@\uff20]'
UTF_CHARS = ur'a-z0-9_\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff'
SPACES = ur'[\u0020\u00A0\u1680\u180E\u2002-\u202F\u205F\u2060\u3000]'

# Lists
LIST_PRE_CHARS = ur'([^a-z0-9_]|^)'
LIST_END_CHARS = ur'([a-z0-9_]{1,20})(/[a-z][a-z0-9\x80-\xFF-]{0,79})?'
LIST_REGEX = re.compile(LIST_PRE_CHARS + '(' + AT_SIGNS + '+)' + LIST_END_CHARS,
                        re.IGNORECASE)

# Users
USERNAME_REGEX = re.compile(ur'\B' + AT_SIGNS + LIST_END_CHARS, re.IGNORECASE)
REPLY_REGEX = re.compile(ur'^(?:' + SPACES + ur')*' + AT_SIGNS
                         + ur'([a-z0-9_]{1,20}).*', re.IGNORECASE)

# Hashtags
HASHTAG_EXP = ur'(^|[^0-9A-Z&/]+)(#|\uff03)([0-9A-Z_]*[A-Z_]+[%s]*)' % UTF_CHARS
HASHTAG_REGEX = re.compile(HASHTAG_EXP, re.IGNORECASE)


# URLs
PRE_CHARS = ur'(?:[^/"\':!=]|^|\:)'
DOMAIN_CHARS = ur'([\.-]|[^\s_\!\.\/])+\.[a-z]{2,}(?::[0-9]+)?'
PATH_CHARS = ur'(?:[\.,]?[%s!\*\'\(\);:=\+\$/%s#\[\]\-_,~@])' % (UTF_CHARS, '%')
QUERY_CHARS = ur'[a-z0-9!\*\'\(\);:&=\+\$/%#\[\]\-_\.,~]'

# Valid end-of-path chracters (so /foo. does not gobble the period).
# 1. Allow ) for Wikipedia URLs.
# 2. Allow =&# for empty URL parameters and other URL-join artifacts
PATH_ENDING_CHARS = r'[%s\)=#/]' % UTF_CHARS
QUERY_ENDING_CHARS = '[a-z0-9_&=#]'

URL_REGEX = re.compile('((%s)((https?://|www\\.)(%s)(\/(%s*%s)?)?(\?%s*%s)?))'
                       % (PRE_CHARS, DOMAIN_CHARS, PATH_CHARS,
                          PATH_ENDING_CHARS, QUERY_CHARS, QUERY_ENDING_CHARS),
                       re.IGNORECASE)

# Registered IANA one letter domains
IANA_ONE_LETTER_DOMAINS = ('x.com', 'x.org', 'z.com', 'q.net', 'q.com', 'i.net')


class ParseResult(object):
    '''A class containing the results of a parsed Tweet.

    Attributes:
    - urls:
        A list containing all the valid urls in the Tweet.

    - users
        A list containing all the valid usernames in the Tweet.

    - reply
        A string containing the username this tweet was a reply to.
        This only matches a username at the beginning of the Tweet,
        it may however be preceeded by whitespace.
        Note: It's generally better to rely on the Tweet JSON/XML in order to
        find out if it's a reply or not.

    - lists
        A list containing all the valid lists in the Tweet.
        Each list item is a tuple in the format (username, listname).

    - tags
        A list containing all the valid tags in theTweet.

    - html
        A string containg formatted HTML.
        To change the formatting sublcass twp.Parser and override the format_*
        methods.

    '''

    def __init__(self, urls, users, reply, lists, tags, html):
        self.urls = urls if urls else []
        self.users = users if users else []
        self.lists = lists if lists else []
        self.reply = reply if reply else None
        self.tags = tags if tags else []
        self.html = html


class Parser(object):
    """A Tweet Parser"""

    def __init__(self, max_url_length=30, include_spans=False, domain='pythonhackers.com'):
        self._max_url_length = max_url_length
        self._include_spans = include_spans
        self.domain = domain

    def parse(self, text, html=True):
        """Parse the text and return a ParseResult instance."""
        self._urls = []
        self._users = []
        self._lists = []
        self._tags = []

        reply = REPLY_REGEX.match(text)
        reply = reply.groups(0)[0] if reply is not None else None

        parsed_html = self._html(text) if html else self._text(text)
        return ParseResult(self._urls, self._users, reply,
                           self._lists, self._tags, parsed_html)

    def _text(self, text):
        """Parse a Tweet without generating HTML."""
        URL_REGEX.sub(self._parse_urls, text)
        USERNAME_REGEX.sub(self._parse_users, text)
        LIST_REGEX.sub(self._parse_lists, text)
        HASHTAG_REGEX.sub(self._parse_tags, text)
        return None

    def _html(self, text):
        """Parse a Tweet and generate HTML."""
        html = URL_REGEX.sub(self._parse_urls, text)
        html = USERNAME_REGEX.sub(self._parse_users, html)
        html = LIST_REGEX.sub(self._parse_lists, html)
        return HASHTAG_REGEX.sub(self._parse_tags, html)

    # Internal parser stuff ----------------------------------------------------
    def _parse_urls(self, match):
        """Parse URLs."""

        mat = match.group(0)

        # Fix a bug in the regex concerning www...com and www.-foo.com domains
        # TODO fix this in the regex instead of working around it here
        domain = match.group(5)
        if domain[0] in '.-':
            return mat

        # Only allow IANA one letter domains that are actually registered
        if len(domain) == 5 \
            and domain[-4:].lower() in ('.com', '.org', '.net') \
            and not domain.lower() in IANA_ONE_LETTER_DOMAINS:
            return mat

        # Check for urls without http(s)
        pos = mat.find('http')
        if pos != -1:
            pre, url = mat[:pos], mat[pos:]
            full_url = url

        # Find the www and force http://
        else:
            pos = mat.lower().find('www')
            pre, url = mat[:pos], mat[pos:]
            full_url = 'http://%s' % url

        if self._include_spans:
            span = match.span(0)
            # add an offset if pre is e.g. ' '
            span = (span[0] + len(pre), span[1])
            self._urls.append((url, span))
        else:
            self._urls.append(url)

        if self._html:
            return '%s%s' % (pre, self.format_url(full_url,
                                                  self._shorten_url(escape(url))))

    def _parse_users(self, match):
        """Parse usernames."""

        # Don't parse lists here
        if match.group(2) is not None:
            return match.group(0)

        mat = match.group(0)
        if self._include_spans:
            self._users.append((mat[1:], match.span(0)))
        else:
            self._users.append(mat[1:])

        if self._html:
            return self.format_username(mat[0:1], mat[1:])

    def _parse_lists(self, match):
        '''Parse lists.'''

        # Don't parse usernames here
        if match.group(4) is None:
            return match.group(0)

        pre, at_char, user, list_name = match.groups()
        list_name = list_name[1:]
        if self._include_spans:
            self._lists.append((user, list_name, match.span(0)))
        else:
            self._lists.append((user, list_name))

        if self._html:
            return '%s%s' % (pre, self.format_list(at_char, user, list_name))

    def _parse_tags(self, match):
        """Parse hashtags."""

        mat = match.group(0)

        # Fix problems with the regex capturing stuff infront of the #
        tag = None
        for i in u'#\uff03':
            pos = mat.rfind(i)
            if pos != -1:
                tag = i
                break

        pre, text = mat[:pos], mat[pos + 1:]
        if self._include_spans:
            span = match.span(0)
            # add an offset if pre is e.g. ' '
            span = (span[0] + len(pre), span[1])
            self._tags.append((text, span))
        else:
            self._tags.append(text)

        if self._html:
            return '%s%s' % (pre, self.format_tag(tag, text))

    def _shorten_url(self, text):
        """Shorten a URL and make sure to not cut of html entities."""

        if len(text) > self._max_url_length != -1:
            text = text[0:self._max_url_length - 3]
            amp = text.rfind('&')
            close = text.rfind(';')
            if amp != -1 and (close == -1 or close < amp):
                text = text[0:amp]

            return text + '...'

        else:
            return text

    # User defined formatters --------------------------------------------------
    def format_tag(self, tag, text):
        """Return formatted HTML for a hashtag."""
        return u'<a href="http://{domain}/hashtag/{tag}" data-tag="{tag}">#{text}</a>'.format(
            **dict(domain=self.domain, tag=urllib.quote(text.encode('utf-8')), text=text))

        #return u'<a href="http://%s/hashtag/%s" data-tag="">%s%s</a>' \
        #    % (self.domain, , tag, text)

    def format_username(self, at_char, user):
        """Return formatted HTML for a username."""
        return u'<a href="http://{domain}/user/{user}" data-user="{user}">{char}{user}</a>'.format(
            **dict(domain=self.domain, user=user, char=at_char, text=user))

        #return u'<a href="http://%s/user/%s" data-user="">%s%s</a>' \
        #       % (self.domain, user, at_char, user)

    def format_list(self, at_char, user, list_name):
        """Return formatted HTML for a list."""
        return u'<a href="http://%s/%s/%s" data-list="">%s%s/%s</a>' \
               % (self.domain, user, list_name, at_char, user, list_name)

    def format_url(self, url, text):
        """Return formatted HTML for a url."""
        return u'<a href="%s">%s</a>' % (escape(url), text)


# Simple URL escaper
def escape(text):
    '''Escape some HTML entities.'''
    return ''.join({'&': '&amp;', '"': '&quot;',
                    '\'': '&apos;', '>': '&gt;',
                    '<': '&lt;'}.get(c, c) for c in text)


if __name__ == "__main__":
    result = Parser().parse("This parsing #python library is neat cc @bcambel")
    print result.html
    print result.users
    print result.tags
    print result.lists
    print result.reply
########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 *-*
import markdown2
from os import listdir
from os.path import join, isfile
from datetime import datetime as dt, timedelta

rules = [(10 ** 9, 'B'), (10 ** 6, 'M'), (10 ** 3, 'K')]


def unix_time(date, float=False):
    epoch = dt.utcfromtimestamp(0)
    delta = date - epoch
    if float:
        return delta.total_seconds()
    else:
        return int(delta.total_seconds())


def unix_time_millisecond(date):
    """
    Uses unix_time function and multiplies with 1000 to get millisecond precision
    Epoch + millisecond precision
    :param date:
    :return:
    """
    return unix_time(date, float=True) * 1e3


def format_date(date):
    return date.strftime('%Y-%m-%d %H:%M:%S') if date is not None else ""


def time_with_ms(date):
    return date.strftime('%H:%M:%S.%f') if date is not None else ""


def epoch_to_date(milliseconds):
    seconds = milliseconds / 1000

    return (dt.utcfromtimestamp(seconds) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")


def nice_number(n):
    numeric = n
    abbreviation = ""

    for number, abbr in rules:
        if n > number:
            abbreviation = abbr
            ident = (n * 10 / number) / 10.0
            break

    ident_int = int(ident)
    if numeric - ident_int == 0:
        numeric = ident_int

    return u"{}{}".format(numeric, abbreviation)


def files_in(directory):
    for f in listdir(directory):
        if isfile(join(directory, f)):
            yield join(directory, f)
    return


def markdown_to_html(txt):
    try:
        html_text = markdown2.markdown(txt, extras=['fenced-code-blocks'])
        return html_text.encode('ascii', 'xmlcharrefreplace').replace("codehilite", "syntax")
    except:
        return txt

if __name__ == "__main__":

    def tests():
        assert "10K" == nice_number(10020)
        assert "102" == nice_number(102)
        assert "1M" == nice_number(1002000)
        assert "1.1B" == nice_number(1102000000)

    tests()
########NEW FILE########
__FILENAME__ = article
import collections
from datetime import datetime as dt
import hashlib
import base64
import logging
import sys
import pprint
from time import mktime
import uuid
import os
import feedparser
from bs4 import BeautifulSoup
from sqlalchemy import or_, and_
from pyhackers.sentry import sentry_client as error_reporter
from pyhackers.common.timelimit import timelimit, TimeoutError
from pyhackers.common.stringutils import safe_str, max_length_field, non_empty_str, safe_filename
from pyhackers.db import DB as session
#from pyhackers.model.feed import Post, Feed, FeedHistory


pp = pprint.PrettyPrinter(indent=6)
default_timeout_limit = 30
current_timeout = default_timeout_limit
content_attributes = ['language', 'value', 'type']
entry_attributes = ['author', 'feedburner_origlink', 'id', 'href', 'published_parsed', 'updated_parsed', 'tags',
                    'title', 'link', 'media_content', 'media_thumbnail']
feed_attributes = ['title', 'language', 'description', 'href', 'updated_parsed', 'version', 'author', 'link']
general_attributes = ['etag', 'status']

code_status_results = {
    0: "?",
    2: "DONE",
    3: "MOVED",
    4: "NF",
    5: "ERROR"
}


def get_feed(rss_url, stats=False):
    post_ids = []

    try:
        for o in download_feed_return_objects(rss_url):
            if o is None:
                continue
            if isinstance(o, Post):
                post_ids.append(o.id)
            session.add(o)
        try:
            if len(post_ids):
                session.commit()
        except Exception, ex:
            session.rollback()
            error_reporter.captureException()
            logging.exception(ex)
            return False

        if len(post_ids) > 0:
            logging.info(u"Saved %d posts for %s" % (len(post_ids), safe_str(rss_url)))
        else:
            logging.info(u"No Posts saved for %s" % safe_str(rss_url))

        for id in post_ids:
            if stats:
                task('get_post_stats', args=(str(id),)).apply_async()
            task('index_post', args=(str(id),)).apply_async()

    except Exception, ex:
        error_dict = {"rss_url": safe_str(rss_url)}

        logging.warn(u"{0}Exception Occured:{1}{0}".format((20 * "="), ex.message))
        try:
            error_reporter.captureException(**error_dict)
        except Exception, error_reporter_exception:
            logging.exception(error_reporter_exception)


def url_hash(url):
    return base64.urlsafe_b64encode(hashlib.md5(safe_str(url)).digest())


def rss_exists(url):
    rss_hash = url_hash(url)
    feed = None

    try:
        feed = session.query(Feed).filter_by(rss_hash=rss_hash).first()
    except:
        error_reporter.captureException()
        try:
            session.rollback()
        except:
            error_reporter.captureException()
        raise

    return feed


def fix_lang_str(lang):
    if len(lang) > 3:
        if '-' in lang:
            lang = lang.split('-')[0]
        else:
            lang = lang[:3]
    return lang


def create_new_feed(feed_parser_results, rss_url):
    feed_obj = Feed()
    feed_obj.id = uuid.uuid1()

    feed_obj.rss = rss_url
    feed_obj.href = feed_parser_results.get("href", "") or ""
    feed_obj.link = feed_parser_results.get("link", "") or ""
    feed_obj.description = feed_parser_results.get("description", "") or ""
    feed_obj.author = feed_parser_results.get("author", "") or ""
    feed_obj.version = feed_parser_results.get("version", "") or ""
    feed_obj.active = True

    max_length_field(feed_obj, "title", 100)

    feed_obj.lang = fix_lang_str(feed_parser_results.get("language", 'en') or 'en')

    feed_obj.rss_hash = url_hash(rss_url)
    return feed_obj


def find_existing_posts(feed_id, post_id_hashes, post_link_hashes):
    try:

        return session.query(Post.post_id_hash, Post.link_hash).filter(
            and_(
                Post.feed_id == feed_id,
                or_(
                    Post.post_id_hash.in_(post_id_hashes),
                    Post.link_hash.in_(post_link_hashes),
                )
            )
        )
    except:
        session.rollback()
        error_reporter.captureException()
        return None


def find_feed_status_from_scode(feed_obj):
    code = int(str(feed_obj.status_code)[0])
    if code_status_results.has_key(code):
        return code_status_results[code]
    else:
        return code_status_results[0]


def cut_clean_etag(etag, max_len=50):
    if etag is not None:
        etag = etag.replace('"', '')
        if len(etag) > max_len:
            etag = etag[:max_len]
        return etag
    else:
        return ""


def download_feed_return_objects(rss_url):
    """
    The piece of code must be removed from this earth, refactored nicely.
    It does everything. Checks if RSS exists, calls RSS fetcher,
    iterates through RSS feed items, creates Post object(s), inserts into FeedHistory.
    """
    try:
        feed_obj = rss_exists(rss_url)
    except:
        yield None
        return

    feed_obj_found = False
    feed_parser_results, success = get_rss(rss_url)

    if feed_parser_results is None:
        error_reporter.captureMessage(u'Feed Parser results is None', **dict(rss_url=rss_url))
        yield None
        return

    if feed_obj is None:
        feed_obj = create_new_feed(feed_parser_results, rss_url)
    else:
        feed_obj_found = True

    feed_id = feed_obj.id
    feed_obj.title = feed_parser_results.get("title", "") or ""
    max_length_field(feed_obj, 'title', 100)

    feed_obj.status_code = feed_parser_results.get("status", "") or 200
    feed_obj.status = find_feed_status_from_scode(feed_obj)

    feed_obj.etag = cut_clean_etag(feed_parser_results.get("etag", ""))

    updated_date = feed_parser_results.get("updated_parsed")
    feed_obj.updated = dt.fromtimestamp(mktime(updated_date)) if updated_date is not None else dt.utcnow()
    #	feed_obj.published =  dt.fromtimestamp(mktime(published_date)) if published_date is not None else None
    feed_obj.last_check = dt.utcnow()

    # We could be creating a new feed, or updating the existing one.
    yield feed_obj
    rss_posts = []

    for feed_article in feed_parser_results.get("entries", []):
        ptime = feed_article.get("published_parsed", None)
        post_date = dt.fromtimestamp(mktime(ptime)) if ptime is not None else dt.utcnow()
        #		print "%r" % post
        p = Post(
            id=uuid.uuid1(),
            title=feed_article.get("title", ""),
            author=feed_article.get("author", ""),
            href=feed_article.get("href", ""),
            post_id=feed_article.get("id", ""),
            published_at=post_date,
            feed_id=feed_id
        )

        p.original_title = max_length_field(p, 'title', 200)
        p.original_author = max_length_field(p, 'author', 200)

        p.content_html = feed_article.get("content", "") or ""

        if feed_article.has_key("media_content"):
            media_contents = feed_article.get("media_content", []) or []
            if media_contents is not None and (not isinstance(media_contents, basestring)) and isinstance(
                    media_contents, collections.Iterable):
                p.media = [media.get("url") for media in media_contents]

        hasHash = False

        if feed_article.has_key("feedburner_origlink"):
            p.original_link = feed_article.get("feedburner_origlink", "")
            if non_empty_str(p.original_link):
                p.link_hash = url_hash(safe_str(p.original_link))
                hasHash = True

        if feed_article.has_key("link"):
            p.href = feed_article.get("link", "")
            if not hasHash and non_empty_str(p.href):
                p.link_hash = url_hash(safe_str(p.href))
                hasHash = True

        if not hasHash:
            print "Post don't have any hash"

        p.title_hash = url_hash(safe_str(p.title)) if non_empty_str(p.title) else ""
        p.post_id_hash = url_hash(safe_str(p.post_id)) if non_empty_str(p.post_id) else ""

        if feed_article.has_key("tags"):
            if isinstance(feed_article['tags'], collections.Iterable):
                p.tags = [pst.get("term") for pst in feed_article['tags']]

        rss_posts.append(p)

    has_posts = len(rss_posts) > 0
    post_id_hashes = [p.post_id_hash for p in rss_posts]
    #	post_title_hashes = [p.title_hash for p in rss_posts]
    post_link_hashes = [p.link_hash for p in rss_posts]

    found_posts_id_hashes = []
    found_posts_link_hashes = []

    if feed_obj_found and has_posts:
        existing_posts = find_existing_posts(feed_id, post_id_hashes, post_link_hashes)

        for ex_post_id_hash, ex_link_hash in existing_posts:
            found_posts_id_hashes.append(ex_post_id_hash)
            found_posts_link_hashes.append(ex_link_hash)

    has_existing_posts = len(found_posts_id_hashes) > 0 or len(found_posts_link_hashes) > 0

    new_post_count = 0
    if has_posts:
        for rss_post in rss_posts:
            should_skip = False

            if has_existing_posts:
                if non_empty_str(rss_post.post_id_hash) and rss_post.post_id_hash in found_posts_id_hashes:
                    should_skip = True
                elif rss_post.link_hash in found_posts_link_hashes:
                    should_skip = True  # "Link Hash found in existing records"

            if not should_skip:
                new_post_count += 1
                yield rss_post

    feed_history = FeedHistory(id=uuid.uuid1(),
                               feed_id=feed_obj.id,
                               timestamp=dt.utcnow(),
                               status=feed_obj.status_code,
                               post_count=new_post_count,
                               etag=feed_obj.etag)
    yield feed_history


def get_object_attr_values(anyobj):

    if not hasattr(anyobj, '__dict__'):
        yield [None, "Object has No __dict__"]
        return
    else:
        pass

    if isinstance(anyobj, dict):
        obj_val_ref = anyobj
    else:
        obj_val_ref = anyobj.__dict__

    for attr, value in obj_val_ref.iteritems():
        yield (attr, value)


def current_dir(file=__file__):
    return os.path.dirname(os.path.abspath(file))


def parent_dir(file=__file__):
    return os.path.dirname(current_dir(file))


def join_path_with_parent_dir(path, file=__file__):
    return os.path.join(os.path.dirname(parent_dir(file)), path)


def get_current_timeout():
    return current_timeout


@timelimit(get_current_timeout)
def download_rss(url):
    return feedparser.parse(url)


def get_rss(url):
    results = None
    success = False
    feed_parser_inst = None

    try:
        feed_parser_inst = download_rss(url)
        success = True
    except TimeoutError:
        pass
    except (UnicodeEncodeError, Exception):
        error_reporter.captureException(**dict(url=url))

    if success:
        results = extract_rss_results(feed_parser_inst, url=url)
    else:
        print "Url not successfull %s " % safe_str(url)

    return results, success


def extract_rss_results(feed, url=''):
    rss_result = dict(entries=[], **dict([(attr, None) for attr in feed_attributes]))

    for attr in general_attributes:
        if hasattr(feed, attr):
            rss_result[attr] = feed[attr]

    for attr in feed_attributes:
        if hasattr(feed.feed, attr):
            rss_result[attr] = feed.feed[attr]

    debug_feed_object(feed, url_downloaded=url)

    for entry in feed.entries:
        feed_entry = {'content': ''}
        content_html = ""
        if hasattr(entry, "content"):
            content = entry.content
            if isinstance(content, collections.Iterable):
                content_html = content[0].value
            elif isinstance(content, basestring):
                content_html = content
            else:
                logging.warn("Content has weird setup")
                content_html = ''

        if hasattr(entry, "description") and not len(content_html):
            if isinstance(entry.description, basestring):
                content_html = entry.description
            elif isinstance(entry.description, list):
                content_html = entry.description[0]  # its a list!
                if isinstance(content_html, dict):
                    content_html = entry.description[0].value  # it's a list contains a dict
                elif isinstance(content_html, basestring):
                    pass
                else:
                    logging.warn("What the fuck is this type? %s " % type(content_html))


        bsoup = BeautifulSoup(content_html)

        html_text = content_html
        if bsoup is not None and len(bsoup.contents) > 0:
            html_text = "".join([unicode(c) for c in bsoup.contents])

        feed_entry['content'] = html_text

        for attr in entry_attributes:
            if hasattr(entry, attr):
                val = entry[attr]
                if val is not None and isinstance(val, basestring):
                    logging.warn(u"{} => {}".format(attr, val))

                    #bsoup2 = BeautifulSoup(val)
                    #val = "".join([unicode(c) for c in bsoup2.contents]) if bsoup2 is not None and len(
                    #    bsoup2.contents) > 0 else val
                    #val = val

                feed_entry[attr] = val

        rss_result["entries"].append(feed_entry)

    return rss_result


def debug_feed_object(feed_obj, url_downloaded):
    file_name = safe_filename(url_downloaded)
    if len(file_name) > 100:
        file_name = file_name[:100]

    debug_file = os.path.join(join_path_with_parent_dir(path='logs', file=__file__), (file_name + ".log"))

    with open(debug_file, "w+") as dobj_file:
        for attr, val in get_object_attr_values(feed_obj):
            pprint.pprint((attr, val, type(val)), stream=dobj_file)


if __name__ == "__main__":
    url = sys.argv[1]

    get_rss(url)
########NEW FILE########
__FILENAME__ = github_worker
import logging
from datetime import datetime as dt
from dateutil import parser as dt_parser
#from cqlengine import BatchQuery
from cqlengine.query import DoesNotExist
from pyhackers.common import unix_time
from pyhackers.config import config
from pyhackers.model.user import User, SocialUser
from pyhackers.model.cassandra.hierachy import (GithubProject,
                                                GithubUserList,
                                                GithubUser,
                                                GithubEvent,
                                                )
from github import Github
import requests
import simplejson

GITHUB_URL = "https://api.github.com/{}?client_id={}&client_secret={}"


class RegistrationGithubWorker():
    """
    Once a user registers via GitHub, we will fetch the stars/watching projects
    following users/followers, events that the user will see their event stream.
    """

    def __init__(self, user_id, social_account_id, config):
        self.user_id = user_id
        self.social_account_id = social_account_id
        self.client_id = config.get("github", 'client_id')
        self.client_secret = config.get("github", 'client_secret')
        self.access_token = None
        self.g = None
        self.github_user = None
        self.github_user_detail = None
        self.users_discovered = set()
        self.previous_link = None

    def get_user_details_from_db(self):
        user = User.query.get(self.user_id)
        social_account = SocialUser.query.get(self.social_account_id)
        self.access_token = social_account.access_token

    def init_github(self):
        self.g = Github(self.access_token,
                        client_id=self.client_id,
                        client_secret=self.client_secret,
                        per_page=100)

        self.github_user = self.g.get_user()
        self.github_user_detail = GithubUserList.create(user=self.github_user.login)

    def get_starred_projects(self):
        starred = self.github_user.get_starred()
        projects = []
        #with BatchQuery() as b:
        for s in starred:
            projects.append(s.full_name)
            self.users_discovered.add(s.owner.login)

            GithubProject.create(
                id=s.id,
                name=s.name,
                full_name=s.full_name,
                watchers_count=s.watchers,
                description=s.description,
                homepage=s.homepage,
                fork=s.fork,
                forks_count=s.forks,
                language=s.language,
                master_branch=s.master_branch,
                network_count=0,
                open_issues=s.open_issues,
                url=s.url,
                is_py=s.language in ['python', 'Python'],
                owner=s.owner.id,
                hide=False,
            )

            #print s.full_name, s.watchers

        self.github_user_detail.starred = projects
        self.github_user_detail.save()

    def get_following_users(self):
        following = self.github_user.get_following()
        following_users = []

        for f in following:
            self.users_discovered.add(f.login)
            following_users.append(f.login)
            print f

        self.github_user_detail.following = following_users
        self.github_user_detail.save()

    def get_follower_users(self):
        followers = self.github_user.get_followers()
        follower_users = []

        for f in followers:
            self.users_discovered.add(f.login)
            follower_users.append(f.login)

        self.github_user_detail.followers = follower_users
        self.github_user_detail.save()

    def save_discovered_users(self):

        found_ids = GithubUser.objects.filter(nick__in=list(self.users_discovered))
        found_id_list = []

        for user in found_ids:
            found_id_list.append(user.nick)

        missing_ids = list(set(self.users_discovered) - set(found_id_list))

        logging.warn(found_id_list)
        logging.warn(self.users_discovered)

        logging.warn(u"[{}] users are found".format(len(self.users_discovered)))
        logging.warn(u"[{}] users are missing".format(len(missing_ids)))

        #return

        for nick in missing_ids:
            user = self.g.get_user(nick)

            logging.warn(u"Creating user [{}]".format(nick))

            GithubUser(nick=user.login,
                       id=user.id,
                       email=user.email,
                       followers=user.followers,
                       following=user.following,
                       image=user.avatar_url,
                       blog=user.blog,
                       bio=user.bio,
                       company=user.company,
                       location=user.location,
                       name=user.name,
                       url=user.url,
                       utype=user.type,
                       public_repos=user.public_repos,
                       public_gists=user.public_gists, ).save()

            logging.warn(u"User[{}]created".format(nick))

    @staticmethod
    def _create_event(json_resp):
        for event in json_resp:
            event_id = int(event.get("id", None))
            event_type = event.get("type", "").replace("Event", "")
            actor = event.get("actor", None)
            actor_str = "{},{}".format(actor.get("id", ""), actor.get("login"))
            repo = event.get("repo", None)
            repo_str = None

            if repo is not None:
                repo_str = "{},{}".format(repo.get("id", ""), repo.get("name"))

            public = event.get("public", None)

            created_at = unix_time(dt_parser.parse(
                event.get("created_at", dt.utcnow())).replace(tzinfo=None),
                float=False)
            org = event.get("org", None)
            org_str = None
            if org is not None:
                org_str = "{},{}".format(org.get("id", ""), org.get("login"))

            payload = event.get("payload", {})

            GithubEvent.create(id=event_id, type=event_type,
                               actor=actor_str, org=org_str,
                               repo=repo_str, created_at=created_at, payload=simplejson.dumps(payload))

    def get_user_timeline(self):
        """
        Fetch events from github
        """
        user = self.github_user.login

        url = GITHUB_URL.format("users/{}/received_events/public".format(user),
                                self.client_id, self.client_secret)
        session = requests.session()

        def paged_json_request(endpoint):
            """
            Recursively fetch the events
            response headers contain ['link'] which is the next or previous page url.
            """
            r = session.get(endpoint)

            json_resp = r.json()
            logging.debug(r.headers)
            next_link = r.headers.get("link")

            logging.debug(next_link)

            if next_link is not None and len(next_link) > 0:
                try:

                    link_parts = next_link.split(";")
                    next_url = link_parts[0]
                    direction = link_parts[1]

                    if "prev" in direction:
                        return

                    next_request_url = next_url.replace("<", "").replace(">", "")

                    if self.previous_link == next_request_url:
                        return

                    self.previous_link = next_request_url

                except Exception, ex:
                    logging.error(ex)
                    next_request_url = None
            else:
                logging.warn(40 * "=")
                logging.warn("No more next link")
                return

            self._create_event(json_resp)

            paged_json_request(next_request_url)

        paged_json_request(url)

    def run(self):
        self.get_user_details_from_db()
        self.init_github()
        self.get_starred_projects()
        self.get_following_users()
        self.get_follower_users()
        self.save_discovered_users()
        self.get_user_timeline()
        # TODO: Generate User Stories


def new_github_registration(user_id, social_account_id):
    logging.warn("[TASK][new_github_registration]: [UserId:{}] [SAcc:{}]".format(user_id, social_account_id))

    RegistrationGithubWorker(user_id, social_account_id, config).run()


if __name__ == "__main__":
    #new_github_registration(12,5)
    new_github_registration(14, 13)
########NEW FILE########
__FILENAME__ = hipchat
import requests
import simplejson as json
from pyhackers.config import config


api_token = config.get("hipchat", "token")


def notify_registration(msg, token=None):
    auth_token = token or api_token
    params = {"message": msg}
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    requests.post("https://api.hipchat.com/v2/room/register/notification?auth_token={}".format(auth_token),
                      data=json.dumps(params),
                      headers=headers)

########NEW FILE########
__FILENAME__ = message
import logging
from pyhackers.model.cassandra.hierachy import (
    User as CsUser, Post as CsPost, UserPost as CsUserPost, UserFollower as CsUserFollower,
    UserTimeLine)

from pyhackers.util.textractor import Parser

parser = Parser()


class MessageWorker():
    def __init__(self, user, message, context):
        self.user_id = user
        self.message_id = message
        self.context = context
        self.user = None
        self.message = None
        self.message_text = ''

    def resolve(self):
        self.user = CsUser.objects.get(id=self.user_id)
        self.message = CsPost.objects.get(id=self.message_id)
        self.message_text = parser.parse(self.message.text)

        logging.warn("Process {}".format(self.message))

    def create_cassa(self):
        logging.warn("Process: Message=>{}".format(self.message.id))


        post_id = self.message_id

        CsUserPost.create(user_id=self.user_id, post_id=post_id)
        user_followers_q = CsUserFollower.objects.filter(user_id=self.user_id).all()
        count = 0
        for follower in user_followers_q:
            UserTimeLine.create(user_id=follower.follower_id, post_id=post_id)
            count += 1

        logging.warn("Message [{}-{}] distributed to {} followers".format(self.message_id, post_id, count))

    def index(self):
        logging.warn("Index...{}".format(self.message))

    def url_rewrite(self):
        logging.warn("URL Rewrite..{}".format(self.message))

    def wait(self):
        logging.warn("Long running thing..")
        logging.warn("=" * 40)

    def run(self):
        self.resolve()
        self.create_cassa()
        self.index()
        self.url_rewrite()
        self.wait()


def new_message_worker(user, message, context):
    logging.warn("[WORKER][FOO] {} - {} - {}".format(user, message, context))
    MessageWorker(user, message, context).run()
########NEW FILE########
__FILENAME__ = wsgi
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.dirname(current_dir)

sys.path.append(source_dir)

from app import app, start_app

start_app()

import newrelic.agent

newrelic.agent.initialize(os.path.join(current_dir, 'newrelic.ini'), 'staging')

application = newrelic.agent.wsgi_application()(app)

########NEW FILE########
__FILENAME__ = startup
from pyhackers.app import start_app;start_app();
from pyhackers.worker.github_worker import *;
#new_github_registration(14,13)
new_github_registration(12,5)

#from pyhackers.tasks.project_finder import *
#importer("python+language:python")
#importer("cassandra+language:python")
#importer("sql+language:python")
########NEW FILE########
