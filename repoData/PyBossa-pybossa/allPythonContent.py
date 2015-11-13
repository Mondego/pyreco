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
__FILENAME__ = 1eb5febf4842_create_blogpost_table
"""Create blogpost table

Revision ID: 1eb5febf4842
Revises: 3da51a88205a
Create Date: 2014-04-07 15:18:09.024341

"""

# revision identifiers, used by Alembic.
revision = '1eb5febf4842'
down_revision = '3da51a88205a'

from alembic import op
import sqlalchemy as sa
import datetime


def make_timestamp():
    now = datetime.datetime.utcnow()
    return now.isoformat()


def upgrade():
    op.create_table(
    'blogpost',
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('title', sa.Unicode(length=255), nullable=False),
    sa.Column('body', sa.UnicodeText, nullable=False),
    sa.Column('app_id', sa.Integer, sa.ForeignKey('app.id', ondelete='CASCADE'), nullable=False),
    sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id')),
    sa.Column('created', sa.Text, default=make_timestamp),
    )


def downgrade():
   op.drop_table('blogpost')

########NEW FILE########
__FILENAME__ = 25e478de8a63_big_int_for_oauth_id
"""big int for oauth id

Revision ID: 25e478de8a63
Revises: 51d3131cf450
Create Date: 2012-08-13 13:46:01.748992

"""

# revision identifiers, used by Alembic.
revision = '25e478de8a63'
down_revision = '51d3131cf450'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('user', 'facebook_user_id', type_=sa.BigInteger)
    op.alter_column('user', 'twitter_user_id', type_=sa.BigInteger)


def downgrade():
    op.alter_column('user', 'facebook_user_id', type_=sa.Integer)
    op.alter_column('user', 'twitter_user_id', type_=sa.Integer)

########NEW FILE########
__FILENAME__ = 27bf0aefa49d_add_colum_ckan_api_k
"""add colum ckan_api key field to user

Revision ID: 27bf0aefa49d
Revises: 9f0b1e842d8
Create Date: 2013-04-11 12:03:51.348130

"""

# revision identifiers, used by Alembic.
revision = '27bf0aefa49d'
down_revision = '9f0b1e842d8'

from alembic import op
import sqlalchemy as sa


field = 'ckan_api'


def upgrade():
    op.add_column('user', sa.Column(field, sa.String))


def downgrade():
    op.drop_column('user', field)

########NEW FILE########
__FILENAME__ = 2a9a0ccb45fc_add_google_user_id
"""add google user id

Revision ID: 2a9a0ccb45fc
Revises: 4f04ded45835
Create Date: 2012-10-08 13:10:20.994389

"""

# revision identifiers, used by Alembic.
revision = '2a9a0ccb45fc'
down_revision = '4f04ded45835'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user', sa.Column('google_user_id', sa.String, unique=True))


def downgrade():
    op.drop_column('user', 'google_user_id')

########NEW FILE########
__FILENAME__ = 2fb54e27efed_add_twitter_user_id_
"""Add twitter_user_id to the Column:User

Revision ID: 2fb54e27efed
Revises: None
Create Date: 2012-05-16 08:43:18.768728

"""

# revision identifiers, used by Alembic.
revision = '2fb54e27efed'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user', sa.Column('twitter_user_id', sa.Integer, unique=True))

def downgrade():
    op.drop_column('user', 'twitter_user_id')

########NEW FILE########
__FILENAME__ = 35242069df8c_app_long_description
"""app long description field

Revision ID: 35242069df8c
Revises: 2fb54e27efed
Create Date: 2012-06-25 09:07:25.155464

"""

# revision identifiers, used by Alembic.
revision = '35242069df8c'
down_revision = '2fb54e27efed'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('app', sa.Column('long_description', sa.Unicode))

def downgrade():
    op.drop_column('app', 'long_description')

########NEW FILE########
__FILENAME__ = 3620d7cac37b_table_constrains
"""table_constrains

Revision ID: 3620d7cac37b
Revises: 3f113ca6c186
Create Date: 2014-01-09 13:20:30.954637

"""

# revision identifiers, used by Alembic.
revision = '3620d7cac37b'
down_revision = '3f113ca6c186'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # App table
    op.alter_column('app', 'name', nullable=False)
    op.alter_column('app', 'short_name', nullable=False)
    op.alter_column('app', 'description', nullable=False)
    op.alter_column('app', 'owner_id', nullable=False)
    # Task
    op.alter_column('task', 'app_id', nullable=False)

    # TaskRun
    op.alter_column('task_run', 'app_id', nullable=False)
    op.alter_column('task_run', 'task_id', nullable=False)


def downgrade():
    op.alter_column('app', 'name', nullable=True)
    op.alter_column('app', 'short_name', nullable=True)
    op.alter_column('app', 'description', nullable=True)
    op.alter_column('app', 'owner_id', nullable=True)
    # Task
    op.alter_column('task', 'app_id', nullable=True)

    # TaskRun
    op.alter_column('task_run', 'app_id', nullable=True)
    op.alter_column('task_run', 'task_id', nullable=True)

########NEW FILE########
__FILENAME__ = 3da51a88205a_ckan_api_key_constraint
"""ckan api key constraint

Revision ID: 3da51a88205a
Revises: 46c3f68e950a
Create Date: 2014-04-01 11:33:01.394220

"""

# revision identifiers, used by Alembic.
revision = '3da51a88205a'
down_revision = '46c3f68e950a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    query = '''UPDATE "user"
                 SET ckan_api=null
                 WHERE id IN (SELECT id 
                    FROM (SELECT id, row_number() over (partition BY ckan_api ORDER BY id) AS rnum
                          FROM "user") t
               WHERE t.rnum > 1);
            '''
    op.execute(query)
    op.create_unique_constraint('ckan_api_uq', 'user', ['ckan_api'])


def downgrade():
    op.drop_constraint('ckan_api_uq', 'user')

########NEW FILE########
__FILENAME__ = 3ee23961633_n_answers_into_task
"""n_answers into task

Revision ID: 3ee23961633
Revises: 25e478de8a63
Create Date: 2012-09-13 10:40:22.345634

"""

# revision identifiers, used by Alembic.
revision = '3ee23961633'
down_revision = '25e478de8a63'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('task', sa.Column('n_answers', sa.Integer, default=30))


def downgrade():
    op.drop_column('task', 'n_answers')

########NEW FILE########
__FILENAME__ = 3f113ca6c186_add_app_category_fie
"""add app category field

Revision ID: 3f113ca6c186
Revises: 47dd43c1491
Create Date: 2013-05-21 14:07:25.855929

"""

# revision identifiers, used by Alembic.
revision = '3f113ca6c186'
down_revision = '47dd43c1491'

from alembic import op
import sqlalchemy as sa


field = 'category_id'


def upgrade():
    op.add_column('app', sa.Column(field, sa.Integer, sa.ForeignKey('category.id')))
    # Assign First Category to Published Apps but not draft
    query = 'UPDATE app SET category_id=1 FROM task WHERE app.info LIKE(\'%task_presenter%\') AND task.app_id=app.id AND app.hidden=0'
    op.execute(query)


def downgrade():
    op.drop_column('app', field)

########NEW FILE########
__FILENAME__ = 46c3f68e950a_add_table_constraints_to_user_locale_
"""add table constraints to user locale and privacy mode

Revision ID: 46c3f68e950a
Revises: 4ad4fddc76f8
Create Date: 2014-03-08 09:53:09.049736

"""

# revision identifiers, used by Alembic.
revision = '46c3f68e950a'
down_revision = '4ad4fddc76f8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    query = 'UPDATE "user" SET locale=\'en\';'
    op.execute(query)
    op.alter_column('user', 'locale', nullable=False)
    op.alter_column('user', 'privacy_mode', nullable=False)



def downgrade():
    op.alter_column('user', 'locale', nullable=True)
    op.alter_column('user', 'privacy_mode', nullable=True)

########NEW FILE########
__FILENAME__ = 47dd43c1491_create_category_tabl
"""create category table

Revision ID: 47dd43c1491
Revises: 27bf0aefa49d
Create Date: 2013-05-21 10:41:43.548449

"""

# revision identifiers, used by Alembic.
revision = '47dd43c1491'
down_revision = '27bf0aefa49d'

from alembic import op
import sqlalchemy as sa
import datetime


def make_timestamp():
    now = datetime.datetime.utcnow()
    return now.isoformat()


def upgrade():
    op.create_table(
        'category',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.Text, nullable=False, unique=True),
        sa.Column('short_name', sa.Text, nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('created', sa.Text, default=make_timestamp),
    )

    # Add two categories
    query = 'INSERT INTO category (name, short_name, description) VALUES (\'Thinking\', \'thinking\', \'Applications where you can help using your skills\')'
    op.execute(query)
    query = 'INSERT INTO category  (name, short_name, description) VALUES (\'Sensing\', \'sensing\', \'Applications where you can help gathering data\')'
    op.execute(query)


def downgrade():
    op.drop_table('category')

########NEW FILE########
__FILENAME__ = 4ad4fddc76f8_add_privacy_mode_to_user
"""add privacy mode to user

Revision ID: 4ad4fddc76f8
Revises: 3620d7cac37b
Create Date: 2014-02-26 16:48:19.575577

"""

# revision identifiers, used by Alembic.
revision = '4ad4fddc76f8'
down_revision = '3620d7cac37b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user', sa.Column('privacy_mode', sa.Boolean, default=True))
    query = 'UPDATE "user" SET privacy_mode=true;'
    op.execute(query)



def downgrade():
    op.drop_column('user', 'privacy_mode')

########NEW FILE########
__FILENAME__ = 4f04ded45835_change_long_descript
"""Change long_description to UnicodeText

Revision ID: 4f04ded45835
Revises: 3ee23961633
Create Date: 2012-10-04 13:34:16.345403

"""

# revision identifiers, used by Alembic.
revision = '4f04ded45835'
down_revision = '3ee23961633'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('app', 'long_description', type_=sa.UnicodeText)
    pass


def downgrade():
    op.alter_column('app', 'long_description', type_=sa.Unicode)
    pass

########NEW FILE########
__FILENAME__ = 50a846b021ae_add_a_column_to_app_
"""Add a column to App for user access control

Revision ID: 50a846b021ae
Revises: 2a9a0ccb45fc
Create Date: 2013-03-21 12:21:44.199808

"""

# revision identifiers, used by Alembic.
revision = '50a846b021ae'
down_revision = '2a9a0ccb45fc'

from alembic import op
import sqlalchemy as sa


field = 'allow_anonymous_contributors'


def upgrade():
    op.add_column('app', sa.Column(field, sa.BOOLEAN, default=True))
    query = 'UPDATE app SET %s = True;' % field
    op.execute(query)


def downgrade():
    op.drop_column('app', field)

########NEW FILE########
__FILENAME__ = 51d3131cf450_add_featured_table
"""add featured table

Revision ID: 51d3131cf450
Revises: 9341dfd1b21
Create Date: 2012-07-31 17:15:38.969627

"""


# revision identifiers, used by Alembic.
revision = '51d3131cf450'
down_revision = '9341dfd1b21'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import ForeignKey


def make_timestamp():
    now = datetime.datetime.now()
    return now.isoformat()


def upgrade():
    op.create_table(
        'featured',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('created', sa.Text, default=make_timestamp),
        sa.Column('app_id', sa.Integer, ForeignKey('app.id'), unique=True)
    )


def downgrade():
    op.drop_table('featured')

########NEW FILE########
__FILENAME__ = 9341dfd1b21_admin_field_for_user
"""admin field for users

Revision ID: 9341dfd1b21
Revises: a0d7c1872e
Create Date: 2012-07-31 17:12:24.229677

"""

# revision identifiers, used by Alembic.
revision = '9341dfd1b21'
down_revision = 'a0d7c1872e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user', sa.Column('admin', sa.Boolean, default=False))


def downgrade():
    op.drop_column('user', 'admin')

########NEW FILE########
__FILENAME__ = 9f0b1e842d8_add_locale_to_user_t
"""add locale to user table

Revision ID: 9f0b1e842d8
Revises: 50a846b021ae
Create Date: 2013-03-26 13:55:36.669733

"""

# revision identifiers, used by Alembic.
revision = '9f0b1e842d8'
down_revision = '50a846b021ae'

from alembic import op
import sqlalchemy as sa


field = 'locale'


def upgrade():
    op.add_column('user', sa.Column(field, sa.String, default="en"))
    query = 'UPDATE "user" SET %s=\'en\';' % field
    op.execute(query)


def downgrade():
    op.drop_column('user', field)

########NEW FILE########
__FILENAME__ = a0d7c1872e_add_facebook_user_id
"""add facebook user id

Revision ID: a0d7c1872e
Revises: 35242069df8c
Create Date: 2012-06-29 12:18:38.475096

"""

# revision identifiers, used by Alembic.
revision = 'a0d7c1872e'
down_revision = '35242069df8c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user', sa.Column('facebook_user_id', sa.Integer, unique=True))

def downgrade():
    op.drop_column('user', 'facebook_user_id')

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
import os
import sys
import optparse
import inspect

#import pybossa.model as model
from pybossa.core import db, create_app
from pybossa.model.app import App
from pybossa.model.user import User
from pybossa.model.category import Category

from alembic.config import Config
from alembic import command
from html2text import html2text
from sqlalchemy.sql import text

app = create_app()

def setup_alembic_config():
    if "DATABASE_URL" not in os.environ:
        alembic_cfg = Config("alembic.ini")
    else:
        dynamic_filename = "alembic-heroku.ini"
        with file("alembic.ini.template") as f:
            with file(dynamic_filename, "w") as conf:
                for line in f.readlines():
                    if line.startswith("sqlalchemy.url"):
                        conf.write("sqlalchemy.url = %s\n" %
                                   os.environ['DATABASE_URL'])
                    else:
                        conf.write(line)
        alembic_cfg = Config(dynamic_filename)

    command.stamp(alembic_cfg, "head")

def db_create():
    '''Create the db'''
    with app.app_context():
        db.create_all()
        # then, load the Alembic configuration and generate the
        # version table, "stamping" it with the most recent rev:
        setup_alembic_config()
        # finally, add a minimum set of categories: Volunteer Thinking, Volunteer Sensing, Published and Draft
        categories = []
        categories.append(Category(name="Thinking",
                          short_name='thinking',
                          description='Volunteer Thinking apps'))
        categories.append(Category(name="Volunteer Sensing",
                          short_name='sensing',
                          description='Volunteer Sensing apps'))
        db.session.add_all(categories)
        db.session.commit()

def db_rebuild():
    '''Rebuild the db'''
    with app.app_context():
        db.drop_all()
        db.create_all()
        # then, load the Alembic configuration and generate the
        # version table, "stamping" it with the most recent rev:
        setup_alembic_config()

def fixtures():
    '''Create some fixtures!'''
    with app.app_context():
        user = User(
            name=u'tester',
            email_addr=u'tester@tester.org',
            api_key='tester'
            )
        user.set_password(u'tester')
        db.session.add(user)
        db.session.commit()

def markdown_db_migrate():
    '''Perform a migration of the app long descriptions from HTML to
    Markdown for existing database records'''
    with app.app_context():
        query = 'SELECT id, long_description FROM "app";'
        query_result = db.engine.execute(query)
        old_descriptions = query_result.fetchall()
        for old_desc in old_descriptions:
            if old_desc.long_description:
                new_description = html2text(old_desc.long_description)
                query = text('''
                           UPDATE app SET long_description=:long_description
                           WHERE id=:id''')
                db.engine.execute(query, long_description = new_description, id = old_desc.id)


def bootstrap_avatars():
    """Download current links from user avatar and apps to real images hosted in the
    PyBossa server."""
    import requests
    import os
    import time
    from urlparse import urlparse
    from PIL import Image

    def get_gravatar_url(email, size):
        # import code for encoding urls and generating md5 hashes
        import urllib, hashlib

        # construct the url
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
        gravatar_url += urllib.urlencode({'d':404, 's':str(size)})
        return gravatar_url

    with app.app_context():
        if app.config['UPLOAD_METHOD'] == 'local':
            users = User.query.order_by('id').all()
            print "Downloading avatars for %s users" % len(users)
            for u in users[0:10]:
                print "Downloading avatar for %s ..." % u.name
                container = "user_%s" % u.id
                path = os.path.join(app.config.get('UPLOAD_FOLDER'), container)
                try:
                    print get_gravatar_url(u.email_addr, 100)
                    r = requests.get(get_gravatar_url(u.email_addr, 100), stream=True)
                    if r.status_code == 200:
                        if not os.path.isdir(path):
                            os.makedirs(path)
                        prefix = time.time()
                        filename = "%s_avatar.png" % prefix
                        with open(os.path.join(path, filename), 'wb') as f:
                            for chunk in r.iter_content(1024):
                                f.write(chunk)
                        u.info['avatar'] = filename
                        u.info['container'] = container
                        db.session.commit()
                        print "Done!"
                    else:
                        print "No Gravatar, this user will use the placeholder."
                except:
                    raise
                    print "No gravatar, this user will use the placehoder."


            apps = App.query.all()
            print "Downloading avatars for %s apps" % len(apps)
            for a in apps[0:1]:
                if a.info.get('thumbnail') and not a.info.get('container'):
                    print "Working on app: %s ..." % a.short_name
                    print "Saving avatar: %s ..." % a.info.get('thumbnail')
                    url = urlparse(a.info.get('thumbnail'))
                    if url.scheme and url.netloc:
                        container = "user_%s" % a.owner_id
                        path = os.path.join(app.config.get('UPLOAD_FOLDER'), container)
                        try:
                            r = requests.get(a.info.get('thumbnail'), stream=True)
                            if r.status_code == 200:
                                prefix = time.time()
                                filename = "app_%s_thumbnail_%i.png" % (a.id, prefix)
                                if not os.path.isdir(path):
                                    os.makedirs(path)
                                with open(os.path.join(path, filename), 'wb') as f:
                                    for chunk in r.iter_content(1024):
                                        f.write(chunk)
                                a.info['thumbnail'] = filename
                                a.info['container'] = container
                                db.session.commit()
                                print "Done!"
                        except:
                            print "Something failed, this app will use the placehoder."
        if app.config['UPLOAD_METHOD'] == 'rackspace':
            import pyrax
            import tempfile
            pyrax.set_setting("identity_type", "rackspace")
            pyrax.set_credentials(username=app.config['RACKSPACE_USERNAME'],
                                  api_key=app.config['RACKSPACE_API_KEY'],
                                  region=app.config['RACKSPACE_REGION'])

            cf = pyrax.cloudfiles
            users = User.query.all()
            print "Downloading avatars for %s users" % len(users)
            dirpath = tempfile.mkdtemp()
            for u in users:
                try:
                    r = requests.get(get_gravatar_url(u.email_addr, 100), stream=True)
                    if r.status_code == 200:
                        print "Downloading avatar for %s ..." % u.name
                        container = "user_%s" % u.id
                        try:
                            cf.get_container(container)
                        except pyrax.exceptions.NoSuchContainer:
                            cf.create_container(container)
                            cf.make_container_public(container)
                        prefix = time.time()
                        filename = "%s_avatar.png" % prefix
                        with open(os.path.join(dirpath, filename), 'wb') as f:
                            for chunk in r.iter_content(1024):
                                f.write(chunk)
                        chksum = pyrax.utils.get_checksum(os.path.join(dirpath,
                                                                       filename))
                        cf.upload_file(container,
                                       os.path.join(dirpath, filename),
                                       obj_name=filename,
                                       etag=chksum)
                        u.info['avatar'] = filename
                        u.info['container'] = container
                        db.session.commit()
                        print "Done!"
                    else:
                        print "No Gravatar, this user will use the placeholder."
                except:
                    print "No gravatar, this user will use the placehoder."


            apps = App.query.all()
            print "Downloading avatars for %s apps" % len(apps)
            for a in apps:
                if a.info.get('thumbnail') and not a.info.get('container'):
                    print "Working on app: %s ..." % a.short_name
                    print "Saving avatar: %s ..." % a.info.get('thumbnail')
                    url = urlparse(a.info.get('thumbnail'))
                    if url.scheme and url.netloc:
                        container = "user_%s" % a.owner_id
                        try:
                            cf.get_container(container)
                        except pyrax.exceptions.NoSuchContainer:
                            cf.create_container(container)
                            cf.make_container_public(container)

                        try:
                            r = requests.get(a.info.get('thumbnail'), stream=True)
                            if r.status_code == 200:
                                prefix = time.time()
                                filename = "app_%s_thumbnail_%i.png" % (a.id, prefix)
                                with open(os.path.join(dirpath, filename), 'wb') as f:
                                    for chunk in r.iter_content(1024):
                                        f.write(chunk)
                                chksum = pyrax.utils.get_checksum(os.path.join(dirpath,
                                                                               filename))
                                cf.upload_file(container,
                                               os.path.join(dirpath, filename),
                                               obj_name=filename,
                                               etag=chksum)
                                a.info['thumbnail'] = filename
                                a.info['container'] = container
                                db.session.commit()
                                print "Done!"
                        except:
                            print "Something failed, this app will use the placehoder."




## ==================================================
## Misc stuff for setting up a command line interface

def _module_functions(functions):
    local_functions = dict(functions)
    for k,v in local_functions.items():
        if not inspect.isfunction(v) or k.startswith('_'):
            del local_functions[k]
    return local_functions

def _main(functions_or_object):
    isobject = inspect.isclass(functions_or_object)
    if isobject:
        _methods = _object_methods(functions_or_object)
    else:
        _methods = _module_functions(functions_or_object)

    usage = '''%prog {action}

Actions:
    '''
    usage += '\n    '.join(
        [ '%s: %s' % (name, m.__doc__.split('\n')[0] if m.__doc__ else '') for (name,m)
        in sorted(_methods.items()) ])
    parser = optparse.OptionParser(usage)
    # Optional: for a config file
    # parser.add_option('-c', '--config', dest='config',
    #         help='Config file to use.')
    options, args = parser.parse_args()

    if not args or not args[0] in _methods:
        parser.print_help()
        sys.exit(1)

    method = args[0]
    if isobject:
        getattr(functions_or_object(), method)(*args[1:])
    else:
        _methods[method](*args[1:])

__all__ = [ '_main' ]

if __name__ == '__main__':
    _main(locals())



########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# PyBossa documentation build configuration file, created by
# sphinx-quickstart on Sat Dec  3 21:41:13 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
import datetime

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Read the docs theme
#on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
#if on_rtd:
#    html_theme = 'default'
#else:
    #html_theme = 'nature'
sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'sphinx-theme-pybossa'
html_theme_options = {
        'logo_icon': 'logo.png',
        'show_okfn_logo': False,
        'show_version': False,
        #'google_analytics_id': ...
    }
html_sidebars = {
    '**': ['globaltoc.html', 'localtoc.html', 'relations.html']
}

# Year for copyright
year = datetime.datetime.now().year

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'PyBossa'
copyright = u'%s, SF Isle of Man' %\
        (year)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = 'v0.2.1'
# The full version, including alpha/beta/rc tags.
release = 'v0.2.1'

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
pygments_style = 'fruity'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = 'nature'

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
htmlhelp_basename = 'PyBossadoc'


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
  ('index', 'PyBossa.tex', u'PyBossa Documentation',
   u'Citizen Cyberscience Centre and Open Knowledge Foundation', 'manual'),
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
    ('index', 'pybossa', u'PyBossa Documentation',
     [u'Citizen Cyberscience Centre and Open Knowledge Foundation'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'PyBossa', u'PyBossa Documentation',
   u'Citizen Cyberscience Centre and Open Knowledge Foundation', 'PyBossa', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = fabfile
from __future__ import with_statement
from fabric.api import *
from fabric.contrib.files import exists, append
from StringIO import StringIO

@task
def deploy(service_name, port=2090):
    '''Deploy (or upgrade) PyBossa service named `service_name` on optional
    `port` (default 2090)'''
    basedir = '/home/okfn/var/srvc' 
    app_dir = basedir + '/' + service_name
    src_dir = app_dir + '/' + 'src'
    code_dir = src_dir + '/' + 'pybossa'
    pip_path = app_dir + '/bin/pip'
    if not exists(src_dir):
        run('virtualenv %s' % app_dir)
        run('mkdir -p %s' % src_dir)
    run('%s install gunicorn' % pip_path)
    run('%s install -e git+https://github.com/PyBossa/pybossa#egg=pybossa' % pip_path)
    with cd(code_dir):
        run('git submodule init')
        run('git submodule update')

    supervisor_path = '/etc/supervisor/conf.d/%s.conf' % service_name
    if not exists(supervisor_path):
        log_path = app_dir + '/log'
        run('mkdir -p %s' % log_path)
        templated = supervisor_config % {
                'service_name': service_name,
                'app_dir': app_dir,
                'log_path': log_path,
                'port': port
                }
        put(StringIO(templated), supervisor_path, use_sudo=True) 
        sudo('/etc/init.d/supervisor status')
        sudo('/etc/init.d/supervisor force-reload')
    print('Restarting supervised process for %s' % service_name)
    sudo('supervisorctl restart %s' % service_name)
    print('You will now need to have your web server proxy to port: %s' % port)


supervisor_config = '''[program:%(service_name)s]
command=%(app_dir)s/bin/gunicorn "pybossa.web:app" --bind=127.0.0.1:%(port)s --workers=2 --max-requests=500 --name=%(service_name)s --error-logfile=%(log_path)s/%(service_name)s.gunicorn.error.log

; user that owns virtual environment.
user=okfn
 
stdout_logfile=%(log_path)s/%(service_name)s.log
stderr_logfile=%(log_path)s/%(service_name)s.error.log
autostart=true
'''


########NEW FILE########
__FILENAME__ = api_base
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa api module for exposing domain objects via an API.

This package adds GET, POST, PUT and DELETE methods for any class:
    * applications,
    * tasks,
    * task_runs,
    * users,
    * etc.

"""
import json
from flask import request, abort, Response
from flask.views import MethodView
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError
from pybossa.util import jsonpify, crossdomain
from pybossa.core import db
from pybossa.auth import require
from pybossa.hateoas import Hateoas
from pybossa.ratelimit import ratelimit
from pybossa.error import ErrorStatus


cors_headers = ['Content-Type', 'Authorization']

error = ErrorStatus()


class APIBase(MethodView):

    """Class to create CRUD methods."""

    hateoas = Hateoas()

    def valid_args(self):
        """Check if the domain object args are valid."""
        for k in request.args.keys():
            if k not in ['api_key']:
                getattr(self.__class__, k)

    @crossdomain(origin='*', headers=cors_headers)
    def options(self):  # pragma: no cover
        """Return '' for Options method."""
        return ''

    @jsonpify
    @crossdomain(origin='*', headers=cors_headers)
    @ratelimit(limit=300, per=15 * 60)
    def get(self, id):
        """Get an object.

        Returns an item from the DB with the request.data JSON object or all
        the items if id == None

        :arg self: The class of the object to be retrieved
        :arg integer id: the ID of the object in the DB
        :returns: The JSON item/s stored in the DB

        """
        try:
            getattr(require, self.__class__.__name__.lower()).read()
            query = self._db_query(self.__class__, id)
            json_response = self._create_json_response(query, id)
            return Response(json_response, mimetype='application/json')
        except Exception as e:
            return error.format_exception(
                e,
                target=self.__class__.__name__.lower(),
                action='GET')

    def _create_json_response(self, query_result, id):
        if len (query_result) == 1 and query_result[0] is None:
            raise abort(404)
        items = list(self._create_dict_from_model(item) for item in query_result)
        if id:
            getattr(require, self.__class__.__name__.lower()).read(query_result[0])
            items = items[0]
        return json.dumps(items)

    def _create_dict_from_model(self, model):
        return self._select_attributes(self._add_hateoas_links(model))

    def _add_hateoas_links(self, item):
        obj = item.dictize()
        links, link = self.hateoas.create_links(item)
        if links:
            obj['links'] = links
        if link:
            obj['link'] = link
        return obj

    def _db_query(self, cls, id):
        """ Returns a list with the results of the query"""
        query = db.session.query(self.__class__)
        if not id:
            limit, offset = self._set_limit_and_offset()
            query = self._filter_query(query, limit, offset)
        else:
            query = [query.get(id)]
        return query

    def _filter_query(self, query, limit, offset):
        for k in request.args.keys():
            if k not in ['limit', 'offset', 'api_key']:
                # Raise an error if the k arg is not a column
                getattr(self.__class__, k)
                query = query.filter(
                    getattr(self.__class__, k) == request.args[k])
        query = self._custom_filter(query)
        return self._format_query_result(query, limit, offset)

    def _format_query_result(self, query, limit, offset):
        query = query.order_by(self.__class__.id)
        query = query.limit(limit)
        query = query.offset(offset)
        return query.all()

    def _set_limit_and_offset(self):
        try:
            limit = min(10000, int(request.args.get('limit')))
        except (ValueError, TypeError):
            limit = 20
        try:
            offset = int(request.args.get('offset'))
        except (ValueError, TypeError):
            offset = 0
        return limit, offset

    @jsonpify
    @crossdomain(origin='*', headers=cors_headers)
    @ratelimit(limit=300, per=15 * 60)
    def post(self):
        """Post an item to the DB with the request.data JSON object.

        :arg self: The class of the object to be inserted
        :returns: The JSON item stored in the DB

        """
        try:
            self.valid_args()
            data = json.loads(request.data)
            # Clean HATEOAS args
            data = self.hateoas.remove_links(data)
            inst = self.__class__(**data)
            self._update_object(inst)
            getattr(require, self.__class__.__name__.lower()).create(inst)
            db.session.add(inst)
            db.session.commit()
            return json.dumps(inst.dictize())
        except IntegrityError:
            db.session.rollback()
            raise
        except Exception as e:
            return error.format_exception(
                e,
                target=self.__class__.__name__.lower(),
                action='POST')

    @jsonpify
    @crossdomain(origin='*', headers=cors_headers)
    @ratelimit(limit=300, per=15 * 60)
    def delete(self, id):
        """Delete a single item from the DB.

        :arg self: The class of the object to be deleted
        :arg integer id: the ID of the object in the DB
        :returns: An HTTP status code based on the output of the action.

        More info about HTTP status codes for this action `here
        <http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.7>`_.

        """
        try:
            self.valid_args()
            inst = db.session.query(self.__class__).get(id)
            if inst is None:
                raise NotFound
            getattr(require, self.__class__.__name__.lower()).delete(inst)
            db.session.delete(inst)
            db.session.commit()
            self._refresh_cache(inst)
            return '', 204
        except Exception as e:
            return error.format_exception(
                e,
                target=self.__class__.__name__.lower(),
                action='DELETE')

    @jsonpify
    @crossdomain(origin='*', headers=cors_headers)
    @ratelimit(limit=300, per=15 * 60)
    def put(self, id):
        """Update a single item in the DB.

        :arg self: The class of the object to be updated
        :arg integer id: the ID of the object in the DB
        :returns: An HTTP status code based on the output of the action.

        More info about HTTP status codes for this action `here
        <http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.6>`_.

        """
        try:
            self.valid_args()
            existing = db.session.query(self.__class__).get(id)
            if existing is None:
                raise NotFound
            getattr(require, self.__class__.__name__.lower()).update(existing)
            data = json.loads(request.data)
            # may be missing the id as we allow partial updates
            data['id'] = id
            # Clean HATEOAS args
            data = self.hateoas.remove_links(data)
            inst = self.__class__(**data)
            db.session.merge(inst)
            db.session.commit()
            self._refresh_cache(inst)
            return Response(json.dumps(inst.dictize()), 200,
                            mimetype='application/json')
        except IntegrityError:
            db.session.rollback()
            raise
        except Exception as e:
            return error.format_exception(
                e,
                target=self.__class__.__name__.lower(),
                action='PUT')


    def _update_object(self, data_dict):
        """Update object.

        Method to be overriden in inheriting classes which wish to update
        data dict.

        """
        pass


    def _refresh_cache(self, data_dict):
        """Refresh cache.

        Method to be overriden in inheriting classes which wish to refresh
        cache for given object.

        """
        pass


    def _select_attributes(self, item_data):
        """Method to be overriden in inheriting classes in case it is not
        desired that every object attribute is returned by the API
        """
        return item_data


    def _custom_filter(self, query):
        """Method to be overriden in inheriting classes which wish to consider
        specific filtering criteria
        """
        return query

########NEW FILE########
__FILENAME__ = app
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa api module for domain object APP via an API.

This package adds GET, POST, PUT and DELETE methods for:
    * applications,

"""
from flask.ext.login import current_user
from api_base import APIBase
from pybossa.model.app import App
import pybossa.cache.apps as cached_apps


class AppAPI(APIBase):

    """
    Class for the domain object App.

    It refreshes automatically the cache, and updates the app properly.

    """

    __class__ = App

    def _refresh_cache(self, obj):
        cached_apps.delete_app(obj.short_name)

    def _update_object(self, obj):
        if not current_user.is_anonymous():
            obj.owner = current_user

########NEW FILE########
__FILENAME__ = category
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa api module for domain object Category via an API.

This package adds GET, POST, PUT and DELETE methods for:
    * categories

"""
from api_base import APIBase
from pybossa.model.category import Category


class CategoryAPI(APIBase):

    """Class API for domain object Category."""

    __class__ = Category

########NEW FILE########
__FILENAME__ = global_stats
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa api module for exposing Global Stats via an API.

This package adds GET method for Global Stats.

"""
import json
from api_base import APIBase, cors_headers
from flask import Response
import pybossa.view.stats as stats
import pybossa.cache.apps as cached_apps
import pybossa.cache.categories as cached_categories
from pybossa.util import jsonpify, crossdomain
from pybossa.ratelimit import ratelimit
from werkzeug.exceptions import MethodNotAllowed


class GlobalStatsAPI(APIBase):

    """
    Class for Global Stats of PyBossa server.

    Returns global stats as a JSON object.

    """

    @jsonpify
    @crossdomain(origin='*', headers=cors_headers)
    @ratelimit(limit=300, per=15 * 60)
    def get(self, id):
        """Return global stats."""
        n_pending_tasks = stats.n_total_tasks_site() - stats.n_task_runs_site()
        n_users = stats.n_auth_users() + stats.n_anon_users()
        n_projects = cached_apps.n_published() + cached_apps.n_draft()
        data = dict(n_projects=n_projects,
                    n_users=n_users,
                    n_task_runs=stats.n_task_runs_site(),
                    n_pending_tasks=n_pending_tasks,
                    categories=[])
        # Add Categories
        categories = cached_categories.get_used()
        for c in categories:
            datum = dict()
            datum[c['short_name']] = cached_apps.n_count(c['short_name'])
            data['categories'].append(datum)
        # Add Featured
        datum = dict()
        datum['featured'] = cached_apps.n_featured()
        data['categories'].append(datum)
        # Add Draft
        datum = dict()
        datum['draft'] = cached_apps.n_draft()
        data['categories'].append(datum)
        return Response(json.dumps(data), 200, mimetype='application/json')

    def post(self):
        raise MethodNotAllowed

########NEW FILE########
__FILENAME__ = task
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa api module for exposing domain object Task via an API.

This package adds GET, POST, PUT and DELETE methods for:
    * tasks

"""
from pybossa.model.task import Task
from api_base import APIBase


class TaskAPI(APIBase):

    """Class for domain object Task."""

    __class__ = Task

########NEW FILE########
__FILENAME__ = task_run
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa api module for exposing domain object TaskRun via an API.

This package adds GET, POST, PUT and DELETE methods for:
    * task_runs

"""
from flask import request
from flask.ext.login import current_user
from api_base import APIBase
from pybossa.model import db
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun
from werkzeug.exceptions import Forbidden


class TaskRunAPI(APIBase):

    """Class API for domain object TaskRun."""

    __class__ = TaskRun

    def _update_object(self, taskrun):
        """Update task_run object with user id or ip."""
        # validate the task and app for that taskrun are ok
        task = Task.query.get(taskrun.task_id)
        if task is None:  # pragma: no cover
            raise Forbidden('Invalid task_id')
        if (task.app_id != taskrun.app_id):
            raise Forbidden('Invalid app_id')

        # Add the user info so it cannot post again the same taskrun
        if current_user.is_anonymous():
            taskrun.user_ip = request.remote_addr
        else:
            taskrun.user = current_user

########NEW FILE########
__FILENAME__ = token
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa api module for user oauth tokens via an API.

This package adds GET method for:
    * user oauth tokens

"""
import json
from api_base import APIBase, error, require
from pybossa.model.user import User
import pybossa.cache.users as cached_users
from werkzeug.exceptions import MethodNotAllowed, NotFound
from flask import request, Response
from flask.ext.login import current_user
from pybossa.util import jsonpify
from pybossa.ratelimit import ratelimit


class TokenAPI(APIBase):

    """
    Class for user oauth tokens

    """

    _resource_name = 'token'
    oauth_providers = ('twitter', 'facebook', 'google')

    @jsonpify
    @ratelimit(limit=300, per=15 * 60)
    def get(self, token):
        try:
            getattr(require, self._resource_name).read()
            user_tokens = self._get_all_tokens()
            if token:
                response = self._get_token(token, user_tokens)
            else:
                response = user_tokens
            return Response(json.dumps(response), mimetype='application/json')
        except Exception as e:
            return error.format_exception(
                e,
                target=self._resource_name,
                action='GET')


    def _get_token(self, token, user_tokens):
        token = '%s_token' % token
        if token in user_tokens:
            return {token: user_tokens[token]}
        raise NotFound


    def _get_all_tokens(self):
        tokens = {}
        for provider in self.oauth_providers:
            token = self._create_token_for('%s_token' % provider)
            if token:
                tokens['%s_token' % provider] = token
        return tokens


    def _create_token_for(self, provider):
        token_value = dict(current_user.info).get(provider)
        if token_value:
            token = dict(oauth_token=token_value['oauth_token'])
            if token_value.get('oauth_token_secret'):
                token['oauth_token_secret'] = token_value['oauth_token_secret']
            return token
        return None



    def post(self):
        raise MethodNotAllowed(valid_methods=['GET'])

    def delete(self):
        raise MethodNotAllowed(valid_methods=['GET'])

    def put(self):
        raise MethodNotAllowed(valid_methods=['GET'])

########NEW FILE########
__FILENAME__ = user
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa api module for domain object USER via an API.

This package adds GET method for:
    * users

"""
from api_base import APIBase
from pybossa.model.user import User
import pybossa.cache.users as cached_users
from werkzeug.exceptions import MethodNotAllowed
from flask import request
from flask.ext.login import current_user


class UserAPI(APIBase):

    """
    Class for the domain object User.

    """

    __class__ = User

    # Define private and public fields available through the API
    # (maybe should be defined in the model?) There are fields like password hash
    # that shouldn't be visible even for admins

    # Attributes that are always visible from everyone
    public_attributes = ('locale', 'name')

    # Attributes that are visible only for admins or everyone if the user
    # has privacy_mode disabled
    allowed_attributes = ('name', 'locale', 'fullname', 'created')


    def _select_attributes(self, user_data):
        privacy = self._is_user_private(user_data)
        for attribute in user_data.keys():
            self._remove_attribute_if_private(attribute, user_data, privacy)
        return user_data

    def _remove_attribute_if_private(self, attribute, user_data, privacy):
        if self._is_attribute_private(attribute, privacy):
            del user_data[attribute]

    def _is_attribute_private(self, attribute, privacy):
        return (attribute not in self.allowed_attributes or
                privacy and attribute not in self.public_attributes)

    def _is_user_private(self, user):
        return not self._is_requester_admin() and user['privacy_mode']

    def _is_requester_admin(self):
        return current_user.is_authenticated() and current_user.admin

    def _custom_filter(self, query):
        if self._private_attributes_in_request() and not self._is_requester_admin():
            query = query.filter(getattr(User, 'privacy_mode') == False)
        return query

    def _private_attributes_in_request(self):
        for attribute in request.args.keys():
            if (attribute in self.allowed_attributes and
                attribute not in self.public_attributes):
                return True
        return False

    def post(self):
        raise MethodNotAllowed(valid_methods=['GET'])

    def delete(self):
        raise MethodNotAllowed(valid_methods=['GET'])

    def put(self):
        raise MethodNotAllowed(valid_methods=['GET'])

########NEW FILE########
__FILENAME__ = vmcp
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa api module for exposing VMCP via an API.

This package signs via API a request from CernVM plugin.

"""
import os
import json
import pybossa.vmcp
from flask import Response, request, current_app
from api_base import APIBase, cors_headers
from werkzeug.exceptions import MethodNotAllowed
from pybossa.util import jsonpify, crossdomain
from pybossa.ratelimit import ratelimit


class VmcpAPI(APIBase):

    """Class for CernVM plugin api.

    Returns signed object to start a CernVM instance.

    """

    @jsonpify
    @crossdomain(origin='*', headers=cors_headers)
    @ratelimit(limit=300, per=15 * 60)
    def get(self, id):
        """Return signed VMCP for CernVM requests."""
        error = dict(action=request.method,
                     status="failed",
                     status_code=None,
                     target='vmcp',
                     exception_cls='vmcp',
                     exception_msg=None)
        try:
            if current_app.config.get('VMCP_KEY'):
                pkey = (current_app.root_path + '/../keys/' +
                        current_app.config.get('VMCP_KEY'))
                if not os.path.exists(pkey):
                    raise IOError
            else:
                raise KeyError
            if request.args.get('cvm_salt'):
                salt = request.args.get('cvm_salt')
            else:
                raise AttributeError
            data = request.args.copy()
            signed_data = pybossa.vmcp.sign(data, salt, pkey)
            return Response(json.dumps(signed_data),
                            200,
                            mimetype='application/json')

        except KeyError:
            error['status_code'] = 501
            error['exception_msg'] = ("The server is not configured properly, \
                                      contact the admins")
            return Response(json.dumps(error), status=error['status_code'],
                            mimetype='application/json')
        except IOError:
            error['status_code'] = 501
            error['exception_msg'] = ("The server is not configured properly \
                                      (private key is missing), contact the \
                                      admins")
            return Response(json.dumps(error), status=error['status_code'],
                            mimetype='application/json')

        except AttributeError:
            error['status_code'] = 415
            error['exception_msg'] = "cvm_salt parameter is missing"
            return Response(json.dumps(error), status=error['status_code'],
                            mimetype='application/json')

    def post(self):
        raise MethodNotAllowed

########NEW FILE########
__FILENAME__ = app
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask.ext.login import current_user


def create(app=None):
    return not current_user.is_anonymous()


def read(app=None):
    if app is None:
        return True
    elif app.hidden:
        if current_user.is_authenticated():
            if current_user.admin:
                return True
            elif current_user.id == app.owner_id:
                return True
            else:
                return False
        else:
            return False
    else:
        return True


def update(app):
    if not current_user.is_anonymous() and (app.owner_id == current_user.id
                                            or current_user.admin is True):
        return True
    else:
        return False


def delete(app):
    return update(app)

########NEW FILE########
__FILENAME__ = blogpost
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask.ext.login import current_user
import pybossa.model as model
from pybossa.core import db

def create(blogpost=None, app_id=None):
    if current_user.is_anonymous() or (blogpost is None and app_id is None):
        return False
    app = _get_app(blogpost, app_id)
    if blogpost is None:
        return app.owner_id == current_user.id
    return blogpost.user_id == app.owner_id == current_user.id


def read(blogpost=None, app_id=None):
    app = _get_app(blogpost, app_id)
    if app and not app.hidden:
        return True
    if current_user.is_anonymous() or (blogpost is None and app_id is None):
        return False
    return current_user.admin or current_user.id == app.owner_id


def update(blogpost):
    if current_user.is_anonymous():
        return False
    return blogpost.user_id == current_user.id


def delete(blogpost):
    if current_user.is_anonymous():
        return False
    else:
        return current_user.admin or blogpost.user_id == current_user.id


def _get_app(blogpost, app_id):
    if blogpost is not None:
        return db.session.query(model.app.App).get(blogpost.app_id)
    else:
        return db.session.query(model.app.App).get(app_id)





########NEW FILE########
__FILENAME__ = category
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask.ext.login import current_user


def create(category=None):
    if current_user.is_authenticated():
        if current_user.admin is True:
            return True
        else:
            return False
    else:
        return False


def read(category=None):
    return True


def update(category):
    return create(category)


def delete(category):
    return create(category)

########NEW FILE########
__FILENAME__ = task
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask.ext.login import current_user
import pybossa.model as model
from pybossa.core import db


def create(task=None):
    if not current_user.is_anonymous():
        app = db.session.query(model.app.App).filter_by(id=task.app_id).one()
        if app.owner_id == current_user.id or current_user.admin is True:
            return True
        else:
            return False
    else:
        return False


def read(task=None):
    return True


def update(task):
    if not current_user.is_anonymous():
        app = db.session.query(model.app.App).filter_by(id=task.app_id).one()
        if app.owner_id == current_user.id or current_user.admin is True:
            return True
        else:
            return False
    else:
        return False


def delete(task):
    return update(task)

########NEW FILE########
__FILENAME__ = taskrun
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask.ext.login import current_user
from pybossa.model.task_run import TaskRun
from werkzeug.exceptions import Forbidden


def create(taskrun=None):
    authorized = (TaskRun.query.filter_by(app_id=taskrun.app_id)
                    .filter_by(task_id=taskrun.task_id)
                    .filter_by(user=taskrun.user)
                    .filter_by(user_ip=taskrun.user_ip)
                    .first()) is None
    if not authorized:
        raise Forbidden
    return authorized


def read(taskrun=None):
    return True


def update(taskrun):
    return False


def delete(taskrun):
    if current_user.is_anonymous():
        return False
    if taskrun.user_id is None:
        return current_user.admin
    else:
        return current_user.admin or taskrun.user_id == current_user.id


########NEW FILE########
__FILENAME__ = token
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask.ext.login import current_user


def create(token=None):
    return False


def read(token=None):
    return not current_user.is_anonymous()


def update(token=None):
    return False


def delete(token=None):
    return False

########NEW FILE########
__FILENAME__ = user
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask.ext.login import current_user


def create(user=None): # pragma: no cover
    if current_user.is_authenticated():
        if current_user.admin:
            return True
        else:
            return False
    else:
        return False


def read(user=None): # pragma: no cover
    return True


def update(user): # pragma: no cover
    return create(user)


def delete(user): # pragma: no cover
    return update(user)

########NEW FILE########
__FILENAME__ = apps
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy.sql import func, text
from pybossa.core import db, timeouts
from pybossa.model.featured import Featured
from pybossa.model.app import App
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun
from pybossa.util import pretty_date
from pybossa.cache import memoize, cache, delete_memoized, delete_cached

import json
import string
import operator
import datetime
import time
from datetime import timedelta


@memoize(timeout=timeouts.get('APP_TIMEOUT'))
def get_app(short_name):
    sql = text('''SELECT * FROM
                  app WHERE app.short_name=:short_name''')
    results = db.engine.execute(sql, short_name=short_name)
    app = App()
    for row in results:
        app = App(id=row.id, name=row.name, short_name=row.short_name,
                  created=row.created,
                  description=row.description,
                  long_description=row.long_description,
                  owner_id=row.owner_id,
                  hidden=row.hidden,
                  info=json.loads(row.info),
                  allow_anonymous_contributors=row.allow_anonymous_contributors)
    return app


@cache(timeout=timeouts.get('STATS_FRONTPAGE_TIMEOUT'),
       key_prefix="front_page_featured_apps")
def get_featured_front_page():
    """Return featured apps"""
    sql = text('''SELECT app.id, app.name, app.short_name, app.info FROM
               app, featured where app.id=featured.app_id and app.hidden=0''')
    results = db.engine.execute(sql)
    featured = []
    for row in results:
        app = dict(id=row.id, name=row.name, short_name=row.short_name,
                   info=dict(json.loads(row.info)),
                   n_volunteers=n_volunteers(row.id),
                   n_completed_tasks=n_completed_tasks(row.id))
        featured.append(app)
    return featured


@cache(timeout=timeouts.get('STATS_FRONTPAGE_TIMEOUT'),
       key_prefix="front_page_top_apps")
def get_top(n=4):
    """Return top n=4 apps"""
    sql = text('''SELECT app.id, app.name, app.short_name, app.description, app.info,
              COUNT(app_id) AS total FROM task_run, app
              WHERE app_id IS NOT NULL AND app.id=app_id AND app.hidden=0
              GROUP BY app.id ORDER BY total DESC LIMIT :limit;''')
    results = db.engine.execute(sql, limit=n)
    top_apps = []
    for row in results:
        app = dict(id=row.id, name=row.name, short_name=row.short_name,
                   description=row.description,
                   info=json.loads(row.info),
                   n_volunteers=n_volunteers(row.id),
                   n_completed_tasks=n_completed_tasks(row.id))
        top_apps.append(app)
    return top_apps


@memoize(timeout=timeouts.get('APP_TIMEOUT'))
def n_tasks(app_id):
    sql = text('''SELECT COUNT(task.id) AS n_tasks FROM task
                  WHERE task.app_id=:app_id''')
    results = db.engine.execute(sql, app_id=app_id)
    n_tasks = 0
    for row in results:
        n_tasks = row.n_tasks
    return n_tasks


@memoize(timeout=timeouts.get('APP_TIMEOUT'))
def n_completed_tasks(app_id):
    sql = text('''SELECT COUNT(task.id) AS n_completed_tasks FROM task
                WHERE task.app_id=:app_id AND task.state=\'completed\';''')
    results = db.engine.execute(sql, app_id=app_id)
    n_completed_tasks = 0
    for row in results:
        n_completed_tasks = row.n_completed_tasks
    return n_completed_tasks


@memoize(timeout=timeouts.get('REGISTERED_USERS_TIMEOUT'))
def n_registered_volunteers(app_id):
    sql = text('''SELECT COUNT(DISTINCT(task_run.user_id)) AS n_registered_volunteers FROM task_run
           WHERE task_run.user_id IS NOT NULL AND
           task_run.user_ip IS NULL AND
           task_run.app_id=:app_id;''')
    results = db.engine.execute(sql, app_id=app_id)
    n_registered_volunteers = 0
    for row in results:
        n_registered_volunteers = row.n_registered_volunteers
    return n_registered_volunteers


@memoize(timeout=timeouts.get('ANON_USERS_TIMEOUT'))
def n_anonymous_volunteers(app_id):
    sql = text('''SELECT COUNT(DISTINCT(task_run.user_ip)) AS n_anonymous_volunteers FROM task_run
           WHERE task_run.user_ip IS NOT NULL AND
           task_run.user_id IS NULL AND
           task_run.app_id=:app_id;''')
    results = db.engine.execute(sql, app_id=app_id)
    n_anonymous_volunteers = 0
    for row in results:
        n_anonymous_volunteers = row.n_anonymous_volunteers
    return n_anonymous_volunteers


@memoize()
def n_volunteers(app_id):
    return n_anonymous_volunteers(app_id) + n_registered_volunteers(app_id)


@memoize(timeout=timeouts.get('APP_TIMEOUT'))
def n_task_runs(app_id):
    sql = text('''SELECT COUNT(task_run.id) AS n_task_runs FROM task_run
                  WHERE task_run.app_id=:app_id''')
    results = db.engine.execute(sql, app_id=app_id)
    n_task_runs = 0
    for row in results:
        n_task_runs = row.n_task_runs
    return n_task_runs


@memoize(timeout=timeouts.get('APP_TIMEOUT'))
def overall_progress(app_id):
    """Returns the percentage of submitted Tasks Runs done when a task is
    completed"""
    sql = text('''SELECT task.id, n_answers,
               COUNT(task_run.task_id) AS n_task_runs
               FROM task LEFT OUTER JOIN task_run ON task.id=task_run.task_id
               WHERE task.app_id=:app_id GROUP BY task.id''')
    results = db.engine.execute(sql, app_id=app_id)
    n_expected_task_runs = 0
    n_task_runs = 0
    for row in results:
        tmp = row[2]
        if row[2] > row[1]:
            tmp = row[1]
        n_expected_task_runs += row[1]
        n_task_runs += tmp
    pct = float(0)
    if n_expected_task_runs != 0:
        pct = float(n_task_runs) / float(n_expected_task_runs)
    return (pct * 100)


@memoize(timeout=timeouts.get('APP_TIMEOUT'))
def last_activity(app_id):
    sql = text('''SELECT finish_time FROM task_run WHERE app_id=:app_id
               ORDER BY finish_time DESC LIMIT 1''')
    results = db.engine.execute(sql, app_id=app_id)
    for row in results:
        if row is not None:
            return row[0]
        else:  # pragma: no cover
            return None


# This function does not change too much, so cache it for a longer time
@cache(timeout=timeouts.get('STATS_FRONTPAGE_TIMEOUT'),
       key_prefix="number_featured_apps")
def n_featured():
    """Return number of featured apps"""
    sql = text('''select count(*) from featured;''')
    results = db.engine.execute(sql)
    for row in results:
        count = row[0]
    return count


# This function does not change too much, so cache it for a longer time
@memoize(timeout=timeouts.get('STATS_FRONTPAGE_TIMEOUT'))
def get_featured(category, page=1, per_page=5):
    """Return a list of featured apps with a pagination"""

    count = n_featured()

    sql = text('''SELECT app.id, app.name, app.short_name, app.info, app.created,
               app.description,
               "user".fullname AS owner FROM app, featured, "user"
               WHERE app.id=featured.app_id AND app.hidden=0
               AND "user".id=app.owner_id GROUP BY app.id, "user".id
               OFFSET(:offset) LIMIT(:limit);
               ''')
    offset = (page - 1) * per_page
    results = db.engine.execute(sql, limit=per_page, offset=offset)
    apps = []
    for row in results:
        app = dict(id=row.id, name=row.name, short_name=row.short_name,
                   created=row.created, description=row.description,
                   overall_progress=overall_progress(row.id),
                   last_activity=pretty_date(last_activity(row.id)),
                   last_activity_raw=last_activity(row.id),
                   owner=row.owner,
                   featured=row.id,
                   info=dict(json.loads(row.info)))
        apps.append(app)
    return apps, count


@cache(key_prefix="number_published_apps",
       timeout=timeouts.get('STATS_APP_TIMEOUT'))
def n_published():
    """Return number of published apps"""
    sql = text('''
               WITH published_apps as
               (SELECT app.id FROM app, task WHERE
               app.id=task.app_id AND app.hidden=0 AND app.info
               LIKE('%task_presenter%') GROUP BY app.id)
               SELECT COUNT(id) FROM published_apps;
               ''')
    results = db.engine.execute(sql)
    for row in results:
        count = row[0]
    return count


# Cache it for longer times, as this is only shown to admin users
@cache(timeout=timeouts.get('STATS_DRAFT_TIMEOUT'),
       key_prefix="number_draft_apps")
def n_draft():
    """Return number of draft applications"""
    sql = text('''SELECT COUNT(app.id) FROM app
               LEFT JOIN task on app.id=task.app_id
               WHERE task.app_id IS NULL AND app.info NOT LIKE('%task_presenter%')
               AND app.hidden=0;''')

    results = db.engine.execute(sql)
    for row in results:
        count = row[0]
    return 1


@memoize(timeout=timeouts.get('STATS_FRONTPAGE_TIMEOUT'))
def get_draft(category, page=1, per_page=5):
    """Return list of draft applications"""

    count = n_draft()

    sql = text('''SELECT app.id, app.name, app.short_name, app.created,
               app.description, app.info, "user".fullname as owner
               FROM "user", app LEFT JOIN task ON app.id=task.app_id
               WHERE task.app_id IS NULL AND app.info NOT LIKE('%task_presenter%')
               AND app.hidden=0
               AND app.owner_id="user".id
               OFFSET :offset
               LIMIT :limit;''')

    offset = (page - 1) * per_page
    results = db.engine.execute(sql, limit=per_page, offset=offset)
    apps = []
    for row in results:
        app = dict(id=row.id, name=row.name, short_name=row.short_name,
                   created=row.created,
                   description=row.description,
                   owner=row.owner,
                   last_activity=pretty_date(last_activity(row.id)),
                   last_activity_raw=last_activity(row.id),
                   overall_progress=overall_progress(row.id),
                   info=dict(json.loads(row.info)))
        apps.append(app)
    return apps, count


@memoize(timeout=timeouts.get('N_APPS_PER_CATEGORY_TIMEOUT'))
def n_count(category):
    """Count the number of apps in a given category"""
    sql = text('''
               WITH uniq AS (
               SELECT COUNT(app.id) FROM task, app
               LEFT OUTER JOIN category ON app.category_id=category.id
               WHERE
               category.short_name=:category
               AND app.hidden=0
               AND app.info LIKE('%task_presenter%')
               AND task.app_id=app.id
               GROUP BY app.id)
               SELECT COUNT(*) FROM uniq
               ''')

    results = db.engine.execute(sql, category=category)
    count = 0
    for row in results:
        count = row[0]
    return count


@memoize(timeout=timeouts.get('APP_TIMEOUT'))
def get(category, page=1, per_page=5):
    """Return a list of apps with at least one task and a task_presenter
       with a pagination for a given category"""

    count = n_count(category)

    sql = text('''SELECT app.id, app.name, app.short_name, app.description,
               app.info, app.created, app.category_id, "user".fullname AS owner,
               featured.app_id as featured
               FROM "user", task, app
               LEFT OUTER JOIN category ON app.category_id=category.id
               LEFT OUTER JOIN featured ON app.id=featured.app_id
               WHERE
               category.short_name=:category
               AND app.hidden=0
               AND "user".id=app.owner_id
               AND app.info LIKE('%task_presenter%')
               AND task.app_id=app.id
               GROUP BY app.id, "user".id, featured.app_id ORDER BY app.name
               OFFSET :offset
               LIMIT :limit;''')

    offset = (page - 1) * per_page
    results = db.engine.execute(sql, category=category, limit=per_page, offset=offset)
    apps = []
    for row in results:
        app = dict(id=row.id,
                   name=row.name, short_name=row.short_name,
                   created=row.created,
                   description=row.description,
                   owner=row.owner,
                   featured=row.featured,
                   last_activity=pretty_date(last_activity(row.id)),
                   last_activity_raw=last_activity(row.id),
                   overall_progress=overall_progress(row.id),
                   info=dict(json.loads(row.info)))
        apps.append(app)
    return apps, count


def reset():
    """Clean the cache"""
    delete_cached("index_front_page")
    delete_cached('front_page_featured_apps')
    delete_cached('front_page_top_apps')
    delete_cached('number_featured_apps')
    delete_cached('number_published_apps')
    delete_cached('number_draft_apps')
    delete_memoized(get_featured)
    delete_memoized(get_draft)
    delete_memoized(n_count)
    delete_memoized(get)


def delete_app(short_name):
    """Reset app values in cache"""
    delete_memoized(get_app, short_name)


def delete_n_tasks(app_id):
    """Reset n_tasks value in cache"""
    delete_memoized(n_tasks, app_id)


def delete_n_completed_tasks(app_id):
    """Reset n_completed_tasks value in cache"""
    delete_memoized(n_completed_tasks, app_id)


def delete_n_task_runs(app_id):
    """Reset n_tasks value in cache"""
    delete_memoized(n_task_runs, app_id)


def delete_overall_progress(app_id):
    """Reset overall_progress value in cache"""
    delete_memoized(overall_progress, app_id)


def delete_last_activity(app_id):
    """Reset last_activity value in cache"""
    delete_memoized(last_activity, app_id)


def delete_n_registered_volunteers(app_id):
    """Reset n_registered_volunteers value in cache"""
    delete_memoized(n_registered_volunteers, app_id)


def delete_n_anonymous_volunteers(app_id):
    """Reset n_anonymous_volunteers value in cache"""
    delete_memoized(n_anonymous_volunteers, app_id)


def delete_n_volunteers(app_id):
    """Reset n_volunteers value in cache"""
    delete_memoized(n_volunteers, app_id)


def clean(app_id):
    """Clean all items in cache"""
    reset()
    delete_n_tasks(app_id)
    delete_n_completed_tasks(app_id)
    delete_n_task_runs(app_id)
    delete_overall_progress(app_id)
    delete_last_activity(app_id)
    delete_n_registered_volunteers(app_id)
    delete_n_anonymous_volunteers(app_id)
    delete_n_volunteers(app_id)

########NEW FILE########
__FILENAME__ = categories
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy.sql import text
from pybossa.cache import cache, delete_cached
from pybossa.core import db, timeouts
import pybossa.model as model


@cache(key_prefix="categories_all",
       timeout=timeouts.get('CATEGORY_TIMEOUT'))
def get_all():
    """Return all categories"""
    return db.session.query(model.category.Category).all()


@cache(key_prefix="categories_used",
       timeout=timeouts.get('CATEGORY_TIMEOUT'))
def get_used():
    """Return categories only used by apps"""
    sql = text('''
               SELECT category.* FROM category, app
               WHERE app.category_id=category.id GROUP BY category.id
               ''')
    results = db.engine.execute(sql)
    categories = []
    for row in results:
        category = dict(id=row.id, name=row.name, short_name=row.short_name,
                        description=row.description)
        categories.append(category)
    return categories


def reset():
    """Clean the cache"""
    delete_cached('categories_all')
    delete_cached('categories_used')

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy.sql import text
from pybossa.core import db, timeouts
from pybossa.cache import memoize
from pybossa.cache.apps import overall_progress



@memoize(timeout=60)
def n_available_tasks(app_id, user_id=None, user_ip=None):
    """Returns the number of tasks for a given app a user can contribute to,
    based on the completion of the app tasks, and previous task_runs submitted
    by the user"""

    if user_id and not user_ip:
        query = text('''SELECT COUNT(id) AS n_tasks FROM task WHERE NOT EXISTS
                       (SELECT task_id FROM task_run WHERE
                       app_id=:app_id AND user_id=:user_id AND task_id=task.id)
                       AND app_id=:app_id AND state !='completed';''')
        result = db.engine.execute(query, app_id=app_id, user_id=user_id)
    else:
        if not user_ip:
            user_ip = '127.0.0.1'
        query = text('''SELECT COUNT(id) AS n_tasks FROM task WHERE NOT EXISTS
                       (SELECT task_id FROM task_run WHERE
                       app_id=:app_id AND user_ip=:user_ip AND task_id=task.id)
                       AND app_id=:app_id AND state !='completed';''')
        result = db.engine.execute(query, app_id=app_id, user_ip=user_ip)
    n_tasks = 0
    for row in result:
        n_tasks = row.n_tasks
    return n_tasks


def check_contributing_state(app_id, user_id=None, user_ip=None):
    """Returns the state of a given app for a given user, depending on whether
    the app is completed or not and the user can contribute more to it or not"""

    states = ('completed', 'can_contribute', 'cannot_contribute')
    if overall_progress(app_id) >= 100:
        return states[0]
    if n_available_tasks(app_id, user_id=user_id, user_ip=user_ip) > 0:
        return states[1]
    return states[2]


def add_custom_contrib_button_to(app, user_id_ip):
    if type(app) == dict:
        app_id = app['id']
    else:
        app_id = app.id
        app = app.dictize()
    app['contrib_button'] = check_contributing_state(app_id, **user_id_ip)
    print app['contrib_button']
    return app

########NEW FILE########
__FILENAME__ = users
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
from sqlalchemy.sql import text
from pybossa.core import db, timeouts
from pybossa.cache import cache, memoize, delete_memoized
from pybossa.util import pretty_date
from pybossa.model.user import User
import json


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_leaderboard(n, user_id):
    """Return the top n users with their rank."""
    sql = text('''
               WITH global_rank AS (
                    WITH scores AS (
                        SELECT user_id, COUNT(*) AS score FROM task_run
                        WHERE user_id IS NOT NULL GROUP BY user_id)
                    SELECT user_id, score, rank() OVER (ORDER BY score desc)
                    FROM scores)
               SELECT rank, id, name, fullname, email_addr, info, score FROM global_rank
               JOIN public."user" on (user_id=public."user".id) ORDER BY rank
               LIMIT :limit;
               ''')

    results = db.engine.execute(sql, limit=n)

    top_users = []
    user_in_top = False
    for row in results:
        if (row.id == user_id):
            user_in_top = True
        user=dict(
            rank=row.rank,
            id=row.id,
            name=row.name,
            fullname=row.fullname,
            email_addr=row.email_addr,
            info=dict(json.loads(row.info)),
            score=row.score)
        top_users.append(user)
    if (user_id != 'anonymous'):
        if not user_in_top:
            sql = text('''
                       WITH global_rank AS (
                            WITH scores AS (
                                SELECT user_id, COUNT(*) AS score FROM task_run
                                WHERE user_id IS NOT NULL GROUP BY user_id)
                            SELECT user_id, score, rank() OVER (ORDER BY score desc)
                            FROM scores)
                       SELECT rank, id, name, fullname, email_addr, info, score FROM global_rank
                       JOIN public."user" on (user_id=public."user".id)
                       WHERE user_id=:user_id ORDER BY rank;
                       ''')
            user_rank = db.engine.execute(sql, user_id=user_id)
            u = User.query.get(user_id)
            # Load by default user data with no rank
            user=dict(
                rank=-1,
                id=u.id,
                name=u.name,
                fullname=u.fullname,
                email_addr=u.email_addr,
                info=u.info,
                score=-1)
            for row in user_rank: # pragma: no cover
                user=dict(
                    rank=row.rank,
                    id=row.id,
                    name=row.name,
                    fullname=row.fullname,
                    email_addr=row.email_addr,
                    info=dict(json.loads(row.info)),
                    score=row.score)
            top_users.append(user)

    return top_users


@cache(key_prefix="front_page_top_users",
       timeout=timeouts.get('USER_TOP_TIMEOUT'))
def get_top(n=10):
    """Return the n=10 top users"""
    sql = text('''SELECT "user".id, "user".name, "user".fullname, "user".email_addr,
               "user".created, "user".info, COUNT(task_run.id) AS task_runs FROM task_run, "user"
               WHERE "user".id=task_run.user_id GROUP BY "user".id
               ORDER BY task_runs DESC LIMIT :limit''')
    results = db.engine.execute(sql, limit=n)
    top_users = []
    for row in results:
        user = dict(id=row.id, name=row.name, fullname=row.fullname,
                    email_addr=row.email_addr,
                    created=row.created,
                    task_runs=row.task_runs,
                    info=dict(json.loads(row.info)))
        top_users.append(user)
    return top_users


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_user_summary(name):
    # Get USER
    sql = text('''
               SELECT "user".id, "user".name, "user".fullname, "user".created,
               "user".api_key, "user".twitter_user_id, "user".facebook_user_id,
               "user".google_user_id, "user".info,
               "user".email_addr, COUNT(task_run.user_id) AS n_answers
               FROM "user" LEFT OUTER JOIN task_run ON "user".id=task_run.user_id
               WHERE "user".name=:name
               GROUP BY "user".id;
               ''')
    results = db.engine.execute(sql, name=name)
    user = dict()
    for row in results:
        user = dict(id=row.id, name=row.name, fullname=row.fullname,
                    created=row.created, api_key=row.api_key,
                    twitter_user_id=row.twitter_user_id,
                    google_user_id=row.google_user_id,
                    facebook_user_id=row.facebook_user_id,
                    info=dict(json.loads(row.info)),
                    email_addr=row.email_addr, n_answers=row.n_answers,
                    registered_ago=pretty_date(row.created))

    # Rank
    # See: https://gist.github.com/tokumine/1583695
    sql = text('''
               WITH global_rank AS (
                    WITH scores AS (
                        SELECT user_id, COUNT(*) AS score FROM task_run
                        WHERE user_id IS NOT NULL GROUP BY user_id)
                    SELECT user_id, score, rank() OVER (ORDER BY score desc)
                    FROM scores)
               SELECT * from global_rank WHERE user_id=:user_id;
               ''')

    if user:
        results = db.engine.execute(sql, user_id=user['id'])
        for row in results:
            user['rank'] = row.rank
            user['score'] = row.score

        # Get the APPs where the USER has participated
        sql = text('''
                   SELECT app.id, app.name, app.short_name, app.info,
                   COUNT(task_run.app_id) AS n_answers FROM app, task_run
                   WHERE app.id=task_run.app_id AND
                   task_run.user_id=:user_id GROUP BY app.id
                   ORDER BY n_answers DESC;
                   ''')
        results = db.engine.execute(sql, user_id=user['id'])
        apps_contributed = []
        for row in results:
            app = dict(id=row.id, name=row.name, info=dict(json.loads(row.info)),
                       short_name=row.short_name,
                       n_answers=row.n_answers)
            apps_contributed.append(app)

        # Get the CREATED APPS by the USER
        sql = text('''
                   SELECT app.id, app.name, app.short_name, app.info, app.created
                   FROM app
                   WHERE app.owner_id=:user_id
                   ORDER BY app.created DESC;
                   ''')
        results = db.engine.execute(sql, user_id=user['id'])
        apps_created = []
        for row in results:
            app = dict(id=row.id, name=row.name,
                       short_name=row.short_name,
                       info=dict(json.loads(row.info)))
            apps_created.append(app)

        return user, apps_contributed, apps_created
    else: # pragma: no cover
        return None, None, None


@cache(timeout=timeouts.get('USER_TOTAL_TIMEOUT'),
       key_prefix="site_total_users")
def get_total_users():
    count = User.query.count()
    return count


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_users_page(page, per_page=24):
    offset = (page - 1) * per_page
    sql = text('''SELECT "user".id, "user".name, "user".fullname, "user".email_addr,
               "user".created, "user".info, COUNT(task_run.id) AS task_runs
               FROM task_run, "user"
               WHERE "user".id=task_run.user_id GROUP BY "user".id
               ORDER BY "user".created DESC LIMIT :limit OFFSET :offset''')
    results = db.engine.execute(sql, limit=per_page, offset=offset)
    accounts = []
    for row in results:
        user = dict(id=row.id, name=row.name, fullname=row.fullname,
                    email_addr=row.email_addr, created=row.created,
                    task_runs=row.task_runs, info=dict(json.loads(row.info)),
                    registered_ago=pretty_date(row.created))
        accounts.append(user)
    return accounts


def delete_user_summary(name):
    """Delete from cache the user summary."""
    delete_memoized(get_user_summary, name)

########NEW FILE########
__FILENAME__ = ckan
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import requests
import json

from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun


class Ckan(object):
    def _field_setup(self, obj):
        int_fields = ['id', 'app_id', 'task_id', 'user_id', 'n_answers', 'timeout',
                      'calibration', 'quorum']
        text_fields = ['state', 'user_ip']
        float_fields = ['priority_0']
        timestamp_fields = ['created', 'finish_time']
        json_fields = ['info']
        # Backrefs and functions
        sqlalchemy_refs = ['app', 'task_runs', 'pct_status']
        fields = []
        for attr in obj.__dict__.keys():
            if ("__" not in attr[0:2] and "_" not in attr[0:1] and
                    attr not in sqlalchemy_refs):
                if attr in json_fields:
                    fields.append({'id': attr, 'type': 'json'})
                elif attr in timestamp_fields:
                    fields.append({'id': attr, 'type': 'timestamp'})
                elif attr in int_fields:
                    fields.append({'id': attr, 'type': 'int'})
                elif attr in text_fields:
                    fields.append({'id': attr, 'type': 'text'})
                elif attr in float_fields:
                    fields.append({'id': attr, 'type': 'float'})
                else:
                    fields.append({'id': "%s_%s" % (obj.__name__, attr), 'type': 'int'})
        return fields

    def __init__(self, url, api_key=None):
        self.url = url + "/api/3"
        self.headers = {'Authorization': api_key,
                        'Content-type': 'application/json'}
        self.package = None
        self.aliases = dict(task="task", task_run="task_run, answer")
        self.fields = dict(task=self._field_setup(Task), task_run=self._field_setup(TaskRun))
        self.primary_key = dict(task='id', task_run='id')
        self.indexes = dict(task='id', task_run='id')

    def get_resource_id(self, name):
        for r in self.package['resources']:
            if r['name'] == name:
                return r['id']
        return False

    def package_exists(self, name):
        pkg = {'id': name}
        r = requests.get(self.url + "/action/package_show",
                         headers=self.headers,
                         params=pkg)
        if r.status_code == 200 or r.status_code == 404 or r.status_code == 403:
            try:
                output = json.loads(r.text)
                if output.get('success'):
                    self.package = output['result']
                    return output['result'], None
                else:
                    return False, None
            except ValueError:
                return False, Exception("CKAN: JSON not valid", r.text,
                                        r.status_code)
        else:
            raise Exception("CKAN: the remote site failed! package_show failed",
                            r.text,
                            r.status_code)

    def package_create(self, app, user, url):
        pkg = {'name': app.short_name,
               'title': app.name,
               'author': user.fullname,
               'author_email': user.email_addr,
               'notes': app.description,
               'type': 'pybossa',
               'url': url}
        r = requests.post(self.url + "/action/package_create",
                          headers=self.headers,
                          data=json.dumps(pkg))
        if r.status_code == 200:
            output = json.loads(r.text)
            self.package = output['result']
            return self.package
        else:
            raise Exception("CKAN: the remote site failed! package_create failed",
                            r.text,
                            r.status_code)

    def package_update(self, app, user, url, resources):
        pkg = {'id': app.short_name,
               'name': app.short_name,
               'title': app.name,
               'author': user.fullname,
               'author_email': user.email_addr,
               'notes': app.description,
               'type': 'pybossa',
               'resources': resources,
               'url': url}
        r = requests.post(self.url + "/action/package_update",
                          headers=self.headers,
                          data=json.dumps(pkg))
        if r.status_code == 200:
            output = json.loads(r.text)
            self.package = output['result']
            return self.package
        else:
            raise Exception("CKAN: the remote site failed! package_update failed",
                            r.text,
                            r.status_code)

    def resource_create(self, name, package_id=None):
        if package_id is None:
            package_id = self.package['id']
        rsrc = {'package_id': package_id,
                'name': name,
                'url': self.package['url'],
                'description': "%ss" % name}
        r = requests.post(self.url + "/action/resource_create",
                          headers=self.headers,
                          data=json.dumps(rsrc))
        if r.status_code == 200:
            return json.loads(r.text)
        else:
            raise Exception("CKAN: the remote site failed! resource_create failed",
                            r.text,
                            r.status_code)

    def datastore_create(self, name, resource_id=None):
        if resource_id is None:
            resource_id = self.get_resource_id(name)
        datastore = {'resource_id': resource_id,
                     'fields': self.fields[name],
                     'indexes': self.indexes[name],
                     'primary_key': self.primary_key[name]}
        r = requests.post(self.url + "/action/datastore_create",
                          headers=self.headers,
                          data=json.dumps(datastore))
        if r.status_code == 200:
            output = json.loads(r.text)
            if output['success']:
                return output['result']
            else:  # pragma: no cover
                return output
        else:
            raise Exception("CKAN: the remote site failed! datastore_create failed",
                            r.text,
                            r.status_code)

    def datastore_upsert(self, name, records, resource_id=None):
        if resource_id is None:
            resource_id = self.get_resource_id(name)
        _records = ''
        for text in records:
            _records += text
        _records = json.loads(_records)
        for i in range(0, len(_records), 20):
            chunk = _records[i:i + 20]
            payload = {'resource_id': resource_id,
                       'records': chunk,
                       'method': 'insert'}
            r = requests.post(self.url + "/action/datastore_upsert",
                              headers=self.headers,
                              data=json.dumps(payload))
            if r.status_code != 200:
                raise Exception("CKAN: the remote site failed! datastore_upsert failed",
                                r.text,
                                r.status_code)
        return True

    def datastore_delete(self, name, resource_id=None):
        #if resource_id is None:
        #    resource_id = self.get_resource_id(name)
        payload = {'resource_id': resource_id}
        r = requests.post(self.url + "/action/datastore_delete",
                          headers=self.headers,
                          data=json.dumps(payload))
        if r.status_code == 404 or r.status_code == 200:
            return True
        else:
            raise Exception("CKAN: the remote site failed! datastore_delete failed",
                            r.text,
                            r.status_code)

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging
from flask import Flask, url_for, session, request, render_template, flash
from flask.ext.login import current_user
from flask.ext.heroku import Heroku
from flask.ext.babel import lazy_gettext

from pybossa import default_settings as settings
from pybossa.extensions import *
from pybossa.ratelimit import get_view_rate_limit

from raven.contrib.flask import Sentry
from pybossa.model import db
from pybossa import model


def create_app():
    app = Flask(__name__)
    if 'DATABASE_URL' in os.environ:  # pragma: no cover
        heroku = Heroku(app)
    configure_app(app)
    setup_cache_timeouts(app)
    setup_theme(app)
    setup_uploader(app)
    setup_error_email(app)
    setup_logging(app)
    setup_login_manager(app)
    login_manager.setup_app(app)
    setup_babel(app)
    setup_markdown(app)
    # Set up Gravatar for users
    setup_gravatar(app)
    #gravatar = Gravatar(app, size=100, rating='g', default='mm',
                        #force_default=False, force_lower=False)
    setup_db(app)
    mail.init_app(app)
    sentinel.init_app(app)
    signer.init_app(app)
    if app.config.get('SENTRY_DSN'): # pragma: no cover
        sentr = Sentry(app)
    setup_blueprints(app)
    setup_hooks(app)
    setup_error_handlers(app)
    setup_social_networks(app)
    setup_jinja(app)
    setup_geocoding(app)
    setup_csrf_protection(app)
    setup_debug_toolbar(app)
    return app


def configure_app(app):
    app.config.from_object(settings)
    app.config.from_envvar('PYBOSSA_SETTINGS', silent=True)
    # parent directory
    if not os.environ.get('PYBOSSA_SETTINGS'): # pragma: no cover
        here = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(here), 'settings_local.py')
        if os.path.exists(config_path): # pragma: no cover
            app.config.from_pyfile(config_path)
    # Override DB in case of testing
    if app.config.get('SQLALCHEMY_DATABASE_TEST_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_TEST_URI']


def setup_theme(app):
    """Configure theme for PyBossa app."""
    theme = app.config['THEME']
    app.template_folder = os.path.join('themes', theme, 'templates')
    app.static_folder = os.path.join('themes', theme, 'static')


def setup_uploader(app):
    global uploader
    if app.config.get('UPLOAD_METHOD') == 'local':
        from pybossa.uploader.local import LocalUploader
        uploader = LocalUploader()
        uploader.init_app(app)
    if app.config.get('UPLOAD_METHOD') == 'rackspace': # pragma: no cover
        from pybossa.uploader.rackspace import RackspaceUploader
        uploader = RackspaceUploader()
        app.url_build_error_handlers.append(uploader.external_url_handler)
        uploader.init_app(app)

def setup_markdown(app):
    misaka.init_app(app)


def setup_db(app):
    db.app = app
    db.init_app(app)


def setup_gravatar(app):
    gravatar.init_app(app)

from logging.handlers import SMTPHandler
def setup_error_email(app):
    ADMINS = app.config.get('ADMINS', '')
    if not app.debug and ADMINS: # pragma: no cover
        mail_handler = SMTPHandler('127.0.0.1',
                                   'server-error@no-reply.com',
                                   ADMINS, 'error')
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

from logging.handlers import RotatingFileHandler
from logging import Formatter
def setup_logging(app):
    log_file_path = app.config.get('LOG_FILE')
    log_level = app.config.get('LOG_LEVEL', logging.WARN)
    if log_file_path: # pragma: no cover
        file_handler = RotatingFileHandler(log_file_path)
        file_handler.setFormatter(Formatter(
            '%(name)s:%(levelname)s:[%(asctime)s] %(message)s '
            '[in %(pathname)s:%(lineno)d]'
            ))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
        logger = logging.getLogger('pybossa')
        logger.setLevel(log_level)
        logger.addHandler(file_handler)

def setup_login_manager(app):
    login_manager.login_view = 'account.signin'
    login_manager.login_message = u"Please sign in to access this page."
    @login_manager.user_loader
    def load_user(username):
        return db.session.query(model.user.User).filter_by(name=username).first()


def setup_babel(app):
    """Return babel handler."""
    babel.init_app(app)

    @babel.localeselector
    def get_locale():
        if current_user.is_authenticated():
            lang = current_user.locale
        else:
            lang = session.get('lang',
                               request.accept_languages.best_match(app.config['LOCALES']))
        if lang is None:
            lang = 'en'
        return lang
    return babel

def setup_blueprints(app):
    """Configure blueprints."""
    from pybossa.api import blueprint as api
    from pybossa.view.account import blueprint as account
    from pybossa.view.applications import blueprint as applications
    from pybossa.view.admin import blueprint as admin
    from pybossa.view.leaderboard import blueprint as leaderboard
    from pybossa.view.stats import blueprint as stats
    from pybossa.view.help import blueprint as help
    from pybossa.view.home import blueprint as home
    from pybossa.view.uploads import blueprint as uploads

    blueprints = [{'handler': home, 'url_prefix': '/'},
                  {'handler': api,  'url_prefix': '/api'},
                  {'handler': account, 'url_prefix': '/account'},
                  {'handler': applications, 'url_prefix': '/app'},
                  {'handler': admin, 'url_prefix': '/admin'},
                  {'handler': leaderboard, 'url_prefix': '/leaderboard'},
                  {'handler': help, 'url_prefix': '/help'},
                  {'handler': stats, 'url_prefix': '/stats'},
                  {'handler': uploads, 'url_prefix': '/uploads'},
                  ]

    for bp in blueprints:
        app.register_blueprint(bp['handler'], url_prefix=bp['url_prefix'])


def setup_social_networks(app):
    try:  # pragma: no cover
        if (app.config['TWITTER_CONSUMER_KEY'] and
                app.config['TWITTER_CONSUMER_SECRET']):
            twitter.init_app(app)
            from pybossa.view.twitter import blueprint as twitter_bp
            app.register_blueprint(twitter_bp, url_prefix='/twitter')
    except Exception as inst:  # pragma: no cover
        print type(inst)
        print inst.args
        print inst
        print "Twitter signin disabled"

    # Enable Facebook if available
    try:  # pragma: no cover
        if (app.config['FACEBOOK_APP_ID'] and app.config['FACEBOOK_APP_SECRET']):
            facebook.init_app(app)
            from pybossa.view.facebook import blueprint as facebook_bp
            app.register_blueprint(facebook_bp, url_prefix='/facebook')
    except Exception as inst: # pragma: no cover
        print type(inst)
        print inst.args
        print inst
        print "Facebook signin disabled"

    # Enable Google if available
    try:  # pragma: no cover
        if (app.config['GOOGLE_CLIENT_ID'] and app.config['GOOGLE_CLIENT_SECRET']):
            google.init_app(app)
            from pybossa.view.google import blueprint as google_bp
            app.register_blueprint(google_bp, url_prefix='/google')
    except Exception as inst:  # pragma: no cover
        print type(inst)
        print inst.args
        print inst
        print "Google signin disabled"


def setup_geocoding(app):
    # Check if app stats page can generate the map
    geolite = app.root_path + '/../dat/GeoLiteCity.dat'
    if not os.path.exists(geolite):  # pragma: no cover
        app.config['GEO'] = False
        print("GeoLiteCity.dat file not found")
        print("App page stats web map disabled")
    else:  # pragma: no cover
        app.config['GEO'] = True


def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)

def setup_jinja(app):
    app.jinja_env.globals['url_for_other_page'] = url_for_other_page


def setup_error_handlers(app):
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404


    @app.errorhandler(500)
    def server_error(e):  # pragma: no cover
        return render_template('500.html'), 500


    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403


    @app.errorhandler(401)
    def unauthorized(e):
        return render_template('401.html'), 401


def setup_hooks(app):
    @app.after_request
    def inject_x_rate_headers(response):
        limit = get_view_rate_limit()
        if limit and limit.send_x_headers:
            h = response.headers
            h.add('X-RateLimit-Remaining', str(limit.remaining))
            h.add('X-RateLimit-Limit', str(limit.limit))
            h.add('X-RateLimit-Reset', str(limit.reset))
        return response

    @app.before_request
    def api_authentication():
        """ Attempt API authentication on a per-request basis."""
        apikey = request.args.get('api_key', None)
        from flask import _request_ctx_stack
        if 'Authorization' in request.headers:
            apikey = request.headers.get('Authorization')
        if apikey:
            user = db.session.query(model.user.User).filter_by(api_key=apikey).first()
            ## HACK:
            # login_user sets a session cookie which we really don't want.
            # login_user(user)
            if user:
                _request_ctx_stack.top.user = user

    @app.context_processor
    def global_template_context():
        if current_user.is_authenticated():
            if (current_user.email_addr == current_user.name or
                    current_user.email_addr == "None"):
                flash(lazy_gettext("Please update your e-mail address in your profile page,"
                      " right now it is empty!"), 'error')

        # Cookies warning
        cookie_name = app.config['BRAND'] + "_accept_cookies"
        show_cookies_warning = False
        if not request.cookies.get(cookie_name):
            show_cookies_warning = True

        # Announcement sections
        if app.config.get('ANNOUNCEMENT'):
            announcement = app.config['ANNOUNCEMENT']
            if current_user.is_authenticated():
                for key in announcement.keys():
                    if key == 'admin' and current_user.admin:
                        flash(announcement[key], 'info')
                    if key == 'owner' and len(current_user.apps) != 0:
                        flash(announcement[key], 'info')
                    if key == 'user':
                        flash(announcement[key], 'info')

        if app.config.get('CONTACT_EMAIL'):  # pragma: no cover
            contact_email = app.config.get('CONTACT_EMAIL')
        else:
            contact_email = 'info@pybossa.com'

        if app.config.get('CONTACT_TWITTER'):  # pragma: no cover
            contact_twitter = app.config.get('CONTACT_TWITTER')
        else:
            contact_twitter = 'PyBossa'

        return dict(
            brand=app.config['BRAND'],
            title=app.config['TITLE'],
            logo=app.config['LOGO'],
            copyright=app.config['COPYRIGHT'],
            description=app.config['DESCRIPTION'],
            terms_of_use=app.config['TERMSOFUSE'],
            data_use=app.config['DATAUSE'],
            enforce_privacy=app.config['ENFORCE_PRIVACY'],
            #version=pybossa.__version__,
            current_user=current_user,
            show_cookies_warning=show_cookies_warning,
            contact_email=contact_email,
            contact_twitter=contact_twitter,
            upload_method=app.config['UPLOAD_METHOD'])


def setup_csrf_protection(app):
    csrf.init_app(app)


def setup_debug_toolbar(app): # pragma: no cover
    if app.config['ENABLE_DEBUG_TOOLBAR']:
        debug_toolbar.init_app(app)


def setup_cache_timeouts(app):
    global timeouts
    # Apps
    timeouts['APP_TIMEOUT'] = app.config['APP_TIMEOUT']
    timeouts['REGISTERED_USERS_TIMEOUT'] = app.config['REGISTERED_USERS_TIMEOUT']
    timeouts['ANON_USERS_TIMEOUT'] = app.config['ANON_USERS_TIMEOUT']
    timeouts['STATS_FRONTPAGE_TIMEOUT'] = app.config['STATS_FRONTPAGE_TIMEOUT']
    timeouts['STATS_APP_TIMEOUT'] = app.config['STATS_APP_TIMEOUT']
    timeouts['STATS_DRAFT_TIMEOUT'] = app.config['STATS_DRAFT_TIMEOUT']
    timeouts['N_APPS_PER_CATEGORY_TIMEOUT'] = app.config['N_APPS_PER_CATEGORY_TIMEOUT']
    # Categories
    timeouts['CATEGORY_TIMEOUT'] = app.config['CATEGORY_TIMEOUT']
    # Users
    timeouts['USER_TIMEOUT'] = app.config['USER_TIMEOUT']
    timeouts['USER_TOP_TIMEOUT'] = app.config['USER_TOP_TIMEOUT']
    timeouts['USER_TOTAL_TIMEOUT'] = app.config['USER_TOTAL_TIMEOUT']

########NEW FILE########
__FILENAME__ = default_settings
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

DEBUG = False

# webserver host and port
HOST = '0.0.0.0'
PORT = 5000

SECRET = 'foobar'
SECRET_KEY = 'my-session-secret'

ITSDANGEROUSKEY = 'its-dangerous-key'

## project configuration
BRAND = 'PyBossa'
TITLE = 'PyBossa'
COPYRIGHT = 'Set Your Institution'
DESCRIPTION = 'Set the description in your config'
TERMSOFUSE = 'http://okfn.org/terms-of-use/'
DATAUSE = 'http://opendatacommons.org/licenses/by/'
LOGO = ''
LOCALES = ['en', 'es']

## Default THEME
THEME = 'default'

## Default number of apps per page
APPS_PER_PAGE = 20

## Default allowed extensions
ALLOWED_EXTENSIONS = ['js', 'css', 'png', 'jpg', 'jpeg', 'gif']
UPLOAD_METHOD = 'local'

## Default number of users shown in the leaderboard
LEADERBOARD = 20

## Default configuration for debug toolbar
ENABLE_DEBUG_TOOLBAR = False

# Cache default key prefix
REDIS_CACHE_ENABLED = False
REDIS_SENTINEL = [('localhost', 26379)]
REDIS_MASTER = 'mymaster'

REDIS_KEYPREFIX = 'pybossa_cache'

## Default cache timeouts
# App cache
APP_TIMEOUT = 15 * 60
REGISTERED_USERS_TIMEOUT = 15 * 60
ANON_USERS_TIMEOUT = 5 * 60 * 60
STATS_FRONTPAGE_TIMEOUT = 12 * 60 * 60
STATS_APP_TIMEOUT = 12 * 60 * 60
STATS_DRAFT_TIMEOUT = 24 * 60 * 60
N_APPS_PER_CATEGORY_TIMEOUT = 60 * 60
# Category cache
CATEGORY_TIMEOUT = 24 * 60 * 60
# User cache
USER_TIMEOUT = 15 * 60
USER_TOP_TIMEOUT = 24 * 60 * 60
USER_TOTAL_TIMEOUT = 24 * 60 * 60

########NEW FILE########
__FILENAME__ = extensions
"""
This module exports all the extensions used by PyBossa.

The objects are:
    * sentinel: for caching data, ratelimiting, etc.
    * signer: for signing emails, cookies, etc.
    * mail: for sending emails,
    * login_manager: to handle account sigin/signout
    * facebook: for Facebook signin
    * twitter: for Twitter signin
    * google: for Google signin
    * misaka: for app.long_description markdown support,
    * babel: for i18n support,
    * gravatar: for Gravatar support,
    * uploader: for file uploads support,
    * csrf: for CSRF protection

"""
__all__ = ['sentinel', 'signer', 'mail', 'login_manager', 'facebook',
           'twitter', 'google', 'misaka', 'babel', 'gravatar',
           'uploader', 'csrf', 'timeouts', 'debug_toolbar']
# CACHE
from pybossa.sentinel import Sentinel
sentinel = Sentinel()

# Signer
from pybossa.signer import Signer
signer = Signer()

# Mail
from flask.ext.mail import Mail
mail = Mail()

# Login Manager
from flask.ext.login import LoginManager
login_manager = LoginManager()

# Debug Toolbar
from flask.ext.debugtoolbar import DebugToolbarExtension
debug_toolbar = DebugToolbarExtension()

# Social Networks
from pybossa.util import Facebook
facebook = Facebook()

from pybossa.util import Twitter
twitter = Twitter()

from pybossa.util import Google
google = Google()

# Markdown support
from flask.ext.misaka import Misaka
misaka = Misaka()

# Babel
from flask.ext.babel import Babel
babel = Babel()

# Gravatar
from flask.ext.gravatar import Gravatar
gravatar = Gravatar(size=100, rating='g', default='mm',
                    force_default=False, force_lower=False)

# Uploader
uploader = None

# CSRF protection
from flask_wtf.csrf import CsrfProtect
csrf = CsrfProtect()

# Timeouts
timeouts = dict()

########NEW FILE########
__FILENAME__ = hateoas
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask import url_for


class Hateoas(object):
    def link(self, rel, title, href):
        return "<link rel='%s' title='%s' href='%s'/>" % (rel, title, href)

    def create_link(self, item, rel='self'):
        title = item.__class__.__name__.lower()
        method = ".api_%s" % title
        href = url_for(method, id=item.id, _external=True)
        return self.link(rel, title, href)

    def create_links(self, item):
        cls = item.__class__.__name__.lower()
        links = []
        if cls == 'taskrun':
            link = self.create_link(item)
            if item.app_id is not None:
                links.append(self.create_link(item.app, rel='parent'))
            if item.task_id is not None:
                links.append(self.create_link(item.task, rel='parent'))
            return links, link
        elif cls == 'task':
            link = self.create_link(item)
            if item.app_id is not None:
                links = [self.create_link(item.app, rel='parent')]
            return links, link
        elif cls == 'category':
            return None, self.create_link(item)
        elif cls == 'app':
            link = self.create_link(item)
            if item.category_id is not None:
                links.append(self.create_link(item.category, rel='category'))
            return links, link
        elif cls == 'user':
            link = self.create_link(item)
            # TODO: add the apps created by the user as the links with rel=? (maybe 'app'??)
            return None, link
        else: # pragma: no cover
            return False

    def remove_links(self, item):
        """Remove HATEOAS link and links from item"""
        if item.get('link'):
            item.pop('link')
        if item.get('links'):
            item.pop('links')
        return item

########NEW FILE########
__FILENAME__ = app
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy import Integer, Boolean, Unicode, Float, UnicodeText, Text
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy import event


from pybossa.core import db
from pybossa.model import DomainObject, JSONType, make_timestamp
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun
from pybossa.model.featured import Featured
from pybossa.model.category import Category
from pybossa.model.blogpost import Blogpost



class App(db.Model, DomainObject):
    '''A microtasking Application to which Tasks are associated.
    '''

    __tablename__ = 'app'

    id = Column(Integer, primary_key=True)
    created = Column(Text, default=make_timestamp)
    name = Column(Unicode(length=255), unique=True, nullable=False)
    short_name = Column(Unicode(length=255), unique=True, nullable=False)
    description = Column(Unicode(length=255), nullable=False)
    long_description = Column(UnicodeText)
    allow_anonymous_contributors = Column(Boolean, default=True)
    long_tasks = Column(Integer, default=0)
    hidden = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    time_estimate = Column(Integer, default=0)
    time_limit = Column(Integer, default=0)
    calibration_frac = Column(Float, default=0)
    bolt_course_id = Column(Integer, default=0)
    category_id = Column(Integer, ForeignKey('category.id'))
    info = Column(JSONType, default=dict)


    tasks = relationship(Task, cascade='all, delete, delete-orphan', backref='app')
    task_runs = relationship(TaskRun, backref='app',
                             cascade='all, delete-orphan',
                             order_by='TaskRun.finish_time.desc()')
    featured = relationship(Featured, cascade='all, delete, delete-orphan', backref='app')
    category = relationship(Category)
    blogposts = relationship(Blogpost, cascade='all, delete-orphan', backref='app')


@event.listens_for(App, 'before_update')
@event.listens_for(App, 'before_insert')
def empty_string_to_none(mapper, conn, target):
    if target.name == '':
        target.name = None
    if target.short_name == '':
        target.short_name = None
    if target.description == '':
        target.description = None

########NEW FILE########
__FILENAME__ = blogpost
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy import Integer, Unicode, UnicodeText, Text
from sqlalchemy.schema import Column, ForeignKey

from pybossa.core import db
from pybossa.model import DomainObject, make_timestamp



class Blogpost(db.Model, DomainObject):
    """A blog post associated to a given app"""

    __tablename__ = 'blogpost'

    id = Column(Integer, primary_key=True)
    created = Column(Text, default=make_timestamp)
    app_id = Column(Integer, ForeignKey('app.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    title = Column(Unicode(length=255), nullable=False)
    body = Column(UnicodeText, nullable=False)

########NEW FILE########
__FILENAME__ = category
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy import Integer, Text
from sqlalchemy.schema import Column, ForeignKey

from pybossa.core import db
from pybossa.model import DomainObject, make_timestamp



class Category(db.Model, DomainObject):
    '''A Table with Categories for Applications.'''

    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    short_name = Column(Text, nullable=False, unique=True)
    description = Column(Text, nullable=False)
    created = Column(Text, default=make_timestamp)

########NEW FILE########
__FILENAME__ = featured
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy import Integer, Text
from sqlalchemy.schema import Column, ForeignKey

from pybossa.core import db
from pybossa.model import DomainObject, make_timestamp



class Featured(db.Model, DomainObject):
    '''A Table with Featured Apps.'''

    __tablename__ = 'featured'

    id = Column(Integer, primary_key=True)
    created = Column(Text, default=make_timestamp)
    app_id = Column(Integer, ForeignKey('app.id'))

########NEW FILE########
__FILENAME__ = task
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy import Integer, Boolean, Float, UnicodeText, Text
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.orm import relationship, backref

from pybossa.core import db
from pybossa.model import DomainObject, JSONType, make_timestamp
from pybossa.model.task_run import TaskRun




class Task(db.Model, DomainObject):
    '''An individual Task which can be performed by a user. A Task is
    associated to an App.
    '''
    __tablename__ = 'task'


    id = Column(Integer, primary_key=True)
    created = Column(Text, default=make_timestamp)
    app_id = Column(Integer, ForeignKey('app.id', ondelete='CASCADE'), nullable=False)
    state = Column(UnicodeText, default=u'ongoing')
    quorum = Column(Integer, default=0)
    calibration = Column(Integer, default=0)
    priority_0 = Column(Float, default=0)
    info = Column(JSONType, default=dict)
    n_answers = Column(Integer, default=30)

    task_runs = relationship(TaskRun, cascade='all, delete, delete-orphan', backref='task')


    def pct_status(self):
        """Returns the percentage of Tasks that are completed"""
        # DEPRECATED: self.info.n_answers will be removed
        # DEPRECATED: use self.t.n_answers instead
        if (self.info.get('n_answers')):
            self.n_answers = int(self.info['n_answers'])
        if self.n_answers != 0 and self.n_answers != None:
            return float(len(self.task_runs)) / self.n_answers
        else:  # pragma: no cover
            return float(0)

########NEW FILE########
__FILENAME__ = task_run
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy import Integer, Text
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy import event

from pybossa.core import db
from pybossa.model import DomainObject, JSONType, make_timestamp




class TaskRun(db.Model, DomainObject):
    '''A run of a given task by a specific user.
    '''
    __tablename__ = 'task_run'

    id = Column(Integer, primary_key=True)
    created = Column(Text, default=make_timestamp)
    app_id = Column(Integer, ForeignKey('app.id'), nullable=False)
    task_id = Column(Integer, ForeignKey('task.id', ondelete='CASCADE'),
                     nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user_ip = Column(Text)
    finish_time = Column(Text, default=make_timestamp)
    timeout = Column(Integer)
    calibration = Column(Integer)
    info = Column(JSONType, default=dict)
    '''General writable field that should be used by clients to record results\
    of a TaskRun. Usually a template for this will be provided by Task
    For example::
        result: {
            whatever information shoudl be recorded -- up to task presenter
        }
    '''


@event.listens_for(TaskRun, 'after_insert')
def update_task_state(mapper, conn, target):
    """Update the task.state when n_answers condition is met."""
    sql_query = ('select count(id) from task_run \
                 where task_run.task_id=%s') % target.task_id
    n_answers = conn.scalar(sql_query)
    sql_query = ('select n_answers from task \
                 where task.id=%s') % target.task_id
    task_n_answers = conn.scalar(sql_query)
    if (n_answers) >= task_n_answers:
        sql_query = ("UPDATE task SET state=\'completed\' \
                     where id=%s") % target.task_id
        conn.execute(sql_query)

########NEW FILE########
__FILENAME__ = user
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy import Integer, Boolean, Unicode, Text, String, BigInteger
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy import event
from werkzeug import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin

from pybossa.core import db
from pybossa.model import DomainObject, make_timestamp, JSONType, make_uuid
from pybossa.model.app import App
from pybossa.model.task_run import TaskRun
from pybossa.model.blogpost import Blogpost




class User(db.Model, DomainObject, UserMixin):
    '''A registered user of the PyBossa system'''

    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    created = Column(Text, default=make_timestamp)
    email_addr = Column(Unicode(length=254), unique=True, nullable=False)
    name = Column(Unicode(length=254), unique=True, nullable=False)
    fullname = Column(Unicode(length=500), nullable=False)
    locale = Column(Unicode(length=254), default=u'en', nullable=False)
    api_key = Column(String(length=36), default=make_uuid, unique=True)
    passwd_hash = Column(Unicode(length=254), unique=True)
    admin = Column(Boolean, default=False)
    privacy_mode = Column(Boolean, default=True, nullable=False)
    category = Column(Integer)
    flags = Column(Integer)
    twitter_user_id = Column(BigInteger, unique=True)
    facebook_user_id = Column(BigInteger, unique=True)
    google_user_id = Column(String, unique=True)
    ckan_api = Column(String, unique=True)
    info = Column(JSONType, default=dict)

    ## Relationships
    task_runs = relationship(TaskRun, backref='user')
    apps = relationship(App, backref='owner')
    blogposts = relationship(Blogpost, backref='owner')


    def get_id(self):
        '''id for login system. equates to name'''
        return self.name


    def set_password(self, password):
        self.passwd_hash = generate_password_hash(password)


    def check_password(self, password):
        # OAuth users do not have a password
        if self.passwd_hash:
            return check_password_hash(self.passwd_hash, password)
        else:
            return False


    @classmethod
    def by_name(cls, name):
        '''Lookup user by (user)name.'''
        return db.session.query(User).filter_by(name=name).first()


@event.listens_for(User, 'before_insert')
def make_admin(mapper, conn, target):
    users = conn.scalar('select count(*) from "user"')
    if users == 0:
        target.admin = True

########NEW FILE########
__FILENAME__ = sched
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

#import json
#from flask import Blueprint, request, url_for, flash, redirect, abort
#from flask import abort, request, make_response, current_app
from sqlalchemy.sql import text
import pybossa.model as model
from pybossa.core import db
import random


def new_task(app_id, user_id=None, user_ip=None, offset=0):
    '''Get a new task by calling the appropriate scheduler function.
    '''
    app = db.session.query(model.app.App).get(app_id)
    if not app.allow_anonymous_contributors and user_id is None:
        error = model.task.Task(info=dict(error="This application does not allow anonymous contributors"))
        return error
    else:
        sched_map = {
            'default': get_depth_first_task,
            'breadth_first': get_breadth_first_task,
            'depth_first': get_depth_first_task,
            'random': get_random_task,
            'incremental': get_incremental_task}
        sched = sched_map.get(app.info.get('sched'), sched_map['default'])
        return sched(app_id, user_id, user_ip, offset=offset)


def get_breadth_first_task(app_id, user_id=None, user_ip=None, n_answers=30, offset=0):
    """Gets a new task which have the least number of task runs (excluding the
    current user).

    Note that it **ignores** the number of answers limit for efficiency reasons
    (this is not a big issue as all it means is that you may end up with some
    tasks run more than is strictly needed!)
    """
    # Uncomment the next three lines to profile the sched function
    #import timeit
    #T = timeit.Timer(lambda: get_candidate_tasks(app_id, user_id,
    #                  user_ip, n_answers))
    #print "First algorithm: %s" % T.timeit(number=1)

    if user_id and not user_ip:
        sql = text('''
                   SELECT task.id, COUNT(task_run.task_id) AS taskcount FROM task
                   LEFT JOIN task_run ON (task.id = task_run.task_id) WHERE NOT EXISTS
                   (SELECT 1 FROM task_run WHERE app_id=:app_id AND
                   user_id=:user_id AND task_id=task.id)
                   AND task.app_id=:app_id AND task.state !='completed'
                   group by task.id ORDER BY taskcount, id ASC LIMIT 10;
                   ''')
        tasks = db.engine.execute(sql, app_id=app_id, user_id=user_id)
    else:
        if not user_ip: # pragma: no cover
            user_ip = '127.0.0.1'
        sql = text('''
                   SELECT task.id, COUNT(task_run.task_id) AS taskcount FROM task
                   LEFT JOIN task_run ON (task.id = task_run.task_id) WHERE NOT EXISTS
                   (SELECT 1 FROM task_run WHERE app_id=:app_id AND
                   user_ip=:user_ip AND task_id=task.id)
                   AND task.app_id=:app_id AND task.state !='completed'
                   group by task.id ORDER BY taskcount, id ASC LIMIT 10;
                   ''')

        # results will be list of (taskid, count)
        tasks = db.engine.execute(sql, app_id=app_id, user_ip=user_ip)
    # ignore n_answers for the present - we will just keep going once we've
    # done as many as we need
    tasks = [x[0] for x in tasks]
    if tasks:
        if (offset == 0):
            return db.session.query(model.task.Task).get(tasks[0])
        else:
            if (offset < len(tasks)):
                return db.session.query(model.task.Task).get(tasks[offset])
            else:
                return None
    else: # pragma: no cover
        return None


def get_depth_first_task(app_id, user_id=None, user_ip=None, n_answers=30, offset=0):
    """Gets a new task for a given application"""
    # Uncomment the next three lines to profile the sched function
    #import timeit
    #T = timeit.Timer(lambda: get_candidate_tasks(app_id, user_id,
    #                  user_ip, n_answers))
    #print "First algorithm: %s" % T.timeit(number=1)
    candidate_tasks = get_candidate_tasks(app_id, user_id, user_ip, n_answers, offset=offset)
    total_remaining = len(candidate_tasks)
    #print "Available tasks %s " % total_remaining
    if total_remaining == 0:
        return None
    if (offset == 0):
        return candidate_tasks[0]
    else:
        if (offset < len(candidate_tasks)):
            return candidate_tasks[offset]
        else:
            return None


def get_random_task(app_id, user_id=None, user_ip=None, n_answers=30, offset=0):
    """Returns a random task for the user"""
    app = db.session.query(model.app.App).get(app_id)
    from random import choice
    if len(app.tasks) > 0:
        return choice(app.tasks)
    else:
        return None


def get_incremental_task(app_id, user_id=None, user_ip=None, n_answers=30, offset=0):
    """Get a new task for a given application with its last given answer.
       It is an important strategy when dealing with large tasks, as
       transcriptions"""
    candidate_tasks = get_candidate_tasks(app_id, user_id, user_ip, n_answers, offset=0)
    total_remaining = len(candidate_tasks)
    if total_remaining == 0:
        return None
    rand = random.randrange(0, total_remaining)
    task = candidate_tasks[rand]
    #Find last answer for the task
    q = db.session.query(model.task_run.TaskRun)\
          .filter(model.task_run.TaskRun.task_id == task.id)\
          .order_by(model.task_run.TaskRun.finish_time.desc())
    last_task_run = q.first()
    if last_task_run:
        task.info['last_answer'] = last_task_run.info
        #TODO: As discussed in GitHub #53
        # it is necessary to create a lock in the task!
    return task


def get_candidate_tasks(app_id, user_id=None, user_ip=None, n_answers=30, offset=0):
    """Gets all available tasks for a given application and user"""
    rows = None
    if user_id and not user_ip:
        query = text('''
                     SELECT id FROM task WHERE NOT EXISTS
                     (SELECT task_id FROM task_run WHERE
                     app_id=:app_id AND user_id=:user_id AND task_id=task.id)
                     AND app_id=:app_id AND state !='completed'
                     ORDER BY priority_0 DESC, id ASC LIMIT 10''')
        rows = db.engine.execute(query, app_id=app_id, user_id=user_id)
    else:
        if not user_ip:
            user_ip = '127.0.0.1'
        query = text('''
                     SELECT id FROM task WHERE NOT EXISTS
                     (SELECT task_id FROM task_run WHERE
                     app_id=:app_id AND user_ip=:user_ip AND task_id=task.id)
                     AND app_id=:app_id AND state !='completed'
                     ORDER BY priority_0 DESC, id ASC LIMIT 10''')
        rows = db.engine.execute(query, app_id=app_id, user_ip=user_ip)

    tasks = []
    for t in rows:
        tasks.append(db.session.query(model.task.Task).get(t.id))
    return tasks

########NEW FILE########
__FILENAME__ = stats
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask import current_app
from sqlalchemy.sql import text
from pybossa.core import db
from pybossa.cache import cache, memoize, ONE_DAY
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun
from pybossa.cache import FIVE_MINUTES, memoize

import string
import pygeoip
import operator
import datetime
import time
from datetime import timedelta


@memoize(timeout=ONE_DAY)
def get_task_runs(app_id):
    """Return all the Task Runs for a given app_id"""
    task_runs = db.session.query(TaskRun).filter_by(app_id=app_id).all()
    return task_runs


#@memoize(timeout=ONE_DAY)
#def get_tasks(app_id):
#    """Return all the tasks for a given app_id"""
#    tasks = db.session.query(Task).filter_by(app_id=app_id).all()
#    return tasks


@memoize(timeout=ONE_DAY)
def get_avg_n_tasks(app_id):
    """Return the average number of answers expected per task,
    and the number of tasks"""
    sql = text('''SELECT COUNT(task.id) as n_tasks,
               AVG(task.n_answers) AS "avg" FROM task
               WHERE task.app_id=:app_id;''')

    results = db.engine.execute(sql, app_id=app_id)
    for row in results:
        avg = float(row.avg)
        total_n_tasks = row.n_tasks
    return avg, total_n_tasks


@memoize(timeout=ONE_DAY)
def stats_users(app_id):
    """Return users's stats for a given app_id"""
    users = {}
    auth_users = []
    anon_users = []

    # Get Authenticated Users
    sql = text('''SELECT task_run.user_id AS user_id,
               COUNT(task_run.id) as n_tasks FROM task_run
               WHERE task_run.user_id IS NOT NULL AND
               task_run.user_ip IS NULL AND
               task_run.app_id=:app_id
               GROUP BY task_run.user_id ORDER BY n_tasks DESC
               LIMIT 5;''')
    results = db.engine.execute(sql, app_id=app_id)

    for row in results:
        auth_users.append([row.user_id, row.n_tasks])

    sql = text('''SELECT count(distinct(task_run.user_id)) AS user_id FROM task_run
               WHERE task_run.user_id IS NOT NULL AND
               task_run.user_ip IS NULL AND
               task_run.app_id=:app_id;''')
    results = db.engine.execute(sql, app_id=app_id)
    for row in results:
        users['n_auth'] = row[0]

    # Get all Anonymous Users
    sql = text('''SELECT task_run.user_ip AS user_ip,
               COUNT(task_run.id) as n_tasks FROM task_run
               WHERE task_run.user_ip IS NOT NULL AND
               task_run.user_id IS NULL AND
               task_run.app_id=:app_id
               GROUP BY task_run.user_ip ORDER BY n_tasks DESC;''')
    results = db.engine.execute(sql, app_id=app_id)

    for row in results:
        anon_users.append([row.user_ip, row.n_tasks])

    sql = text('''SELECT COUNT(DISTINCT(task_run.user_ip)) AS user_ip FROM task_run
               WHERE task_run.user_ip IS NOT NULL AND
               task_run.user_id IS NULL AND
               task_run.app_id=:app_id;''')
    results = db.engine.execute(sql, app_id=app_id)

    for row in results:
        users['n_anon'] = row[0]

    return users, anon_users, auth_users


@memoize(timeout=ONE_DAY)
def stats_dates(app_id):
    dates = {}
    dates_anon = {}
    dates_auth = {}
    dates_n_tasks = {}

    task_runs = get_task_runs(app_id)

    avg, total_n_tasks = get_avg_n_tasks(app_id)

    for tr in task_runs:
        # Data for dates
        date, hour = string.split(tr.finish_time, "T")
        tr.finish_time = string.split(tr.finish_time, '.')[0]
        hour = string.split(hour, ":")[0]

        # Dates
        if date in dates.keys():
            dates[date] += 1
        else:
            dates[date] = 1

        if date in dates_n_tasks.keys():
            dates_n_tasks[date] = total_n_tasks * avg
        else:
            dates_n_tasks[date] = total_n_tasks * avg

        if tr.user_id is None:
            if date in dates_anon.keys():
                dates_anon[date] += 1
            else:
                dates_anon[date] = 1
        else:
            if date in dates_auth.keys():
                dates_auth[date] += 1
            else:
                dates_auth[date] = 1
    return dates, dates_n_tasks, dates_anon, dates_auth


@memoize(timeout=ONE_DAY)
def stats_hours(app_id):
    hours = {}
    hours_anon = {}
    hours_auth = {}
    max_hours = 0
    max_hours_anon = 0
    max_hours_auth = 0

    task_runs = get_task_runs(app_id)

    # initialize hours keys
    for i in range(0, 24):
        hours[str(i).zfill(2)] = 0
        hours_anon[str(i).zfill(2)] = 0
        hours_auth[str(i).zfill(2)] = 0

    for tr in task_runs:
        # Hours
        date, hour = string.split(tr.finish_time, "T")
        tr.finish_time = string.split(tr.finish_time, '.')[0]
        hour = string.split(hour, ":")[0]

        if hour in hours.keys():
            hours[hour] += 1
            if (hours[hour] > max_hours):
                max_hours = hours[hour]

        if tr.user_id is None:
            if hour in hours_anon.keys():
                hours_anon[hour] += 1
                if (hours_anon[hour] > max_hours_anon):
                    max_hours_anon = hours_anon[hour]

        else:
            if hour in hours_auth.keys():
                hours_auth[hour] += 1
                if (hours_auth[hour] > max_hours_auth):
                    max_hours_auth = hours_auth[hour]
    return hours, hours_anon, hours_auth, max_hours, max_hours_anon, max_hours_auth


@memoize(timeout=ONE_DAY)
def stats_format_dates(app_id, dates, dates_n_tasks, dates_estimate,
                       dates_anon, dates_auth):
    """Format dates stats into a JSON format"""
    dayNewStats = dict(label="Anon + Auth",   values=[])
    dayAvgAnswers = dict(label="Expected Answers",   values=[])
    dayEstimates = dict(label="Estimation",   values=[])
    dayTotalStats = dict(label="Total", disabled="True", values=[])
    dayNewAnonStats = dict(label="Anonymous", values=[])
    dayNewAuthStats = dict(label="Authenticated", values=[])

    total = 0
    for d in sorted(dates.keys()):
        # JavaScript expects miliseconds since EPOCH
        # New answers per day
        dayNewStats['values'].append(
            [int(time.mktime(time.strptime(d, "%Y-%m-%d")) * 1000), dates[d]])

        dayAvgAnswers['values'].append(
            [int(time.mktime(time.strptime(d, "%Y-%m-%d")) * 1000),
             dates_n_tasks[d]])

        # Total answers per day
        total = total + dates[d]
        dayTotalStats['values'].append(
            [int(time.mktime(time.strptime(d, "%Y-%m-%d")) * 1000), total])

        # Anonymous answers per day
        if d in (dates_anon.keys()):
            dayNewAnonStats['values'].append(
                [int(time.mktime(time.strptime(d, "%Y-%m-%d")) * 1000),
                 dates_anon[d]])
        else: # pragma: no cover
            dayNewAnonStats['values'].append(
                [int(time.mktime(time.strptime(d, "%Y-%m-%d")) * 1000), 0])

        # Authenticated answers per day
        if d in (dates_auth.keys()):
            dayNewAuthStats['values'].append(
                [int(time.mktime(time.strptime(d, "%Y-%m-%d")) * 1000),
                 dates_auth[d]])
        else: # pragma: no cover
            dayNewAuthStats['values'].append(
                [int(time.mktime(time.strptime(d, "%Y-%m-%d")) * 1000), 0])

    for d in sorted(dates_estimate.keys()):
        dayEstimates['values'].append(
            [int(time.mktime(time.strptime(d, "%Y-%m-%d")) * 1000),
             dates_estimate[d]])

        dayAvgAnswers['values'].append(
            [int(time.mktime(time.strptime(d, "%Y-%m-%d")) * 1000),
             dates_n_tasks.values()[0]])

    return dayNewStats, dayNewAnonStats, dayNewAuthStats, \
        dayTotalStats, dayAvgAnswers, dayEstimates


@memoize(timeout=ONE_DAY)
def stats_format_hours(app_id, hours, hours_anon, hours_auth,
                       max_hours, max_hours_anon, max_hours_auth):
    """Format hours stats into a JSON format"""
    hourNewStats = dict(label="Anon + Auth", disabled="True", values=[], max=0)
    hourNewAnonStats = dict(label="Anonymous", values=[], max=0)
    hourNewAuthStats = dict(label="Authenticated", values=[], max=0)

    hourNewStats['max'] = max_hours
    hourNewAnonStats['max'] = max_hours_anon
    hourNewAuthStats['max'] = max_hours_auth

    for h in sorted(hours.keys()):
        # New answers per hour
        #hourNewStats['values'].append(dict(x=int(h), y=hours[h], size=hours[h]*10))
        if (hours[h] != 0):
            hourNewStats['values'].append([int(h), hours[h],
                                           (hours[h] * 5) / max_hours])
        else:
            hourNewStats['values'].append([int(h), hours[h], 0])

        # New Anonymous answers per hour
        if h in hours_anon.keys():
            #hourNewAnonStats['values'].append(dict(x=int(h), y=hours[h], size=hours_anon[h]*10))
            if (hours_anon[h] != 0):
                hourNewAnonStats['values'].append([int(h), hours_anon[h],
                                                   (hours_anon[h] * 5) / max_hours])
            else:
                hourNewAnonStats['values'].append([int(h), hours_anon[h], 0])

        # New Authenticated answers per hour
        if h in hours_auth.keys():
            #hourNewAuthStats['values'].append(dict(x=int(h), y=hours[h], size=hours_auth[h]*10))
            if (hours_auth[h] != 0):
                hourNewAuthStats['values'].append([int(h), hours_auth[h],
                                                   (hours_auth[h] * 5) / max_hours])
            else:
                hourNewAuthStats['values'].append([int(h), hours_auth[h], 0])
    return hourNewStats, hourNewAnonStats, hourNewAuthStats


@memoize(timeout=ONE_DAY)
def stats_format_users(app_id, users, anon_users, auth_users, geo=False):
    """Format User Stats into JSON"""
    userStats = dict(label="User Statistics", values=[])
    userAnonStats = dict(label="Anonymous Users", values=[], top5=[], locs=[])
    userAuthStats = dict(label="Authenticated Users", values=[], top5=[])

    userStats['values'].append(dict(label="Anonymous", value=[0, users['n_anon']]))
    userStats['values'].append(dict(label="Authenticated", value=[0, users['n_auth']]))

    for u in anon_users:
        userAnonStats['values'].append(dict(label=u[0], value=[u[1]]))

    for u in auth_users:
        userAuthStats['values'].append(dict(label=u[0], value=[u[1]]))

    # Get location for Anonymous users
    top5_anon = []
    top5_auth = []
    loc_anon = []
    # Check if the GeoLiteCity.dat exists
    geolite = current_app.root_path + '/../dat/GeoLiteCity.dat'
    if geo: # pragma: no cover
        gic = pygeoip.GeoIP(geolite)
    for u in anon_users:
        if geo: # pragma: no cover
            loc = gic.record_by_addr(u[0])
        else:
            loc = {}
        if loc is None: # pragma: no cover
            loc = {}
        if (len(loc.keys()) == 0):
            loc['latitude'] = 0
            loc['longitude'] = 0
        top5_anon.append(dict(ip=u[0], loc=loc, tasks=u[1]))

    for u in anon_users:
        if geo: # pragma: no cover
            loc = gic.record_by_addr(u[0])
        else:
            loc = {}
        if loc is None: # pragma: no cover
            loc = {}
        if (len(loc.keys()) == 0):
            loc['latitude'] = 0
            loc['longitude'] = 0
        loc_anon.append(dict(ip=u[0], loc=loc, tasks=u[1]))

    for u in auth_users:
        sql = text('''SELECT name, fullname from "user" where id=:id;''')
        results = db.engine.execute(sql, id=u[0])
        for row in results:
            fullname = row.fullname
            name = row.name
        top5_auth.append(dict(name=name, fullname=fullname, tasks=u[1]))

    userAnonStats['top5'] = top5_anon[0:5]
    userAnonStats['locs'] = loc_anon
    userAuthStats['top5'] = top5_auth

    return dict(users=userStats, anon=userAnonStats, auth=userAuthStats,
                n_anon=users['n_anon'], n_auth=users['n_auth'])


@memoize(timeout=ONE_DAY)
def get_stats(app_id, geo=False):
    """Return the stats a given app"""
    hours, hours_anon, hours_auth, max_hours, \
        max_hours_anon, max_hours_auth = stats_hours(app_id)
    users, anon_users, auth_users = stats_users(app_id)
    dates, dates_n_tasks, dates_anon, dates_auth = stats_dates(app_id)

    avg, total_n_tasks = get_avg_n_tasks(app_id)

    sorted_answers = sorted(dates.iteritems(), key=operator.itemgetter(0))
    if len(sorted_answers) > 0:
        last_day = datetime.datetime.strptime(sorted_answers[-1][0], "%Y-%m-%d")
    total_answers = sum(dates.values())
    if len(dates) > 0:
        avg_answers_per_day = total_answers / len(dates)
    required_days_to_finish = ((avg * total_n_tasks) - total_answers) / avg_answers_per_day

    pace = total_answers

    dates_estimate = {}
    for i in range(0, int(required_days_to_finish) + 2):
        tmp = last_day + timedelta(days=(i))
        tmp_str = tmp.date().strftime('%Y-%m-%d')
        dates_estimate[tmp_str] = pace
        pace = pace + avg_answers_per_day

    dates_stats = stats_format_dates(app_id, dates, dates_n_tasks, dates_estimate,
                                     dates_anon, dates_auth)

    hours_stats = stats_format_hours(app_id, hours, hours_anon, hours_auth,
                                     max_hours, max_hours_anon, max_hours_auth)

    users_stats = stats_format_users(app_id, users, anon_users, auth_users, geo)

    return dates_stats, hours_stats, users_stats

########NEW FILE########
__FILENAME__ = local
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
# Cache global variables for timeouts
"""
Local module for uploading files to a PyBossa local filesystem.

This module exports:
    * Local class: for uploading files to a local filesystem.

"""
from pybossa.uploader import Uploader
import os
from werkzeug import secure_filename


class LocalUploader(Uploader):

    """Local filesystem uploader class."""

    upload_folder = 'uploads'

    def init_app(self, app):
        """Config upload folder."""
        super(self.__class__, self).init_app(app)
        if app.config.get('UPLOAD_FOLDER'):
            self.upload_folder = app.config['UPLOAD_FOLDER']

    def _upload_file(self, file, container):
        """Upload a file into a container/folder."""
        try:
            filename = secure_filename(file.filename)
            if not os.path.isdir(os.path.join(self.upload_folder, container)):
                os.makedirs(os.path.join(self.upload_folder, container))
            file.save(os.path.join(self.upload_folder, container, filename))
            return True
        except:
            return False

    def delete_file(self, name, container):
        """Delete file from filesystem."""
        try:
            path = os.path.join(self.upload_folder, container, name)
            os.remove(path)
            return True
        except:
            return False

########NEW FILE########
__FILENAME__ = rackspace
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
# Cache global variables for timeouts
"""
Local module for uploading files to a PyBossa local filesystem.

This module exports:
    * Local class: for uploading files to a local filesystem.

"""
import pyrax
from pybossa.uploader import Uploader
from werkzeug import secure_filename


class RackspaceUploader(Uploader):

    """Rackspace Cloud Files uploader class."""

    cf = None
    cont_name = 'pybossa'

    def init_app(self, app, cont_name=None):
        """Init method to create a generic uploader."""
        super(self.__class__, self).init_app(app)
        try:
            pyrax.set_setting("identity_type", "rackspace")
            pyrax.set_credentials(username=app.config['RACKSPACE_USERNAME'],
                                  api_key=app.config['RACKSPACE_API_KEY'],
                                  region=app.config['RACKSPACE_REGION'])
            self.cf = pyrax.cloudfiles
            if cont_name:
                self.cont_name = cont_name
            return self.cf.get_container(self.cont_name)
        except pyrax.exceptions.NoSuchContainer:
            c = self.cf.create_container(self.cont_name)
            self.cf.make_container_public(self.cont_name)
            return c

    def get_container(self, name):
        """Create a container for the given asset."""
        try:
            return self.cf.get_container(name)
        except pyrax.exceptions.NoSuchContainer:
            c = self.cf.create_container(name)
            self.cf.make_container_public(name)
            return c

    def _upload_file_to_rackspace(self, file, container):
        """Upload file to rackspace."""
        chksum = pyrax.utils.get_checksum(file)
        self.cf.upload_file(container,
                            file,
                            obj_name=secure_filename(file.filename),
                            etag=chksum)
        return True

    def _upload_file(self, file, container):
        """Upload a file into a container."""
        try:
            cnt = self.get_container(container)
            obj = cnt.get_object(file.filename)
            obj.delete()
            return self._upload_file_to_rackspace(file, container)
        except pyrax.exceptions.NoSuchObject:
            return self._upload_file_to_rackspace(file, container)
        except pyrax.exceptions.UploadFailed:
            return False

    def _lookup_url(self, endpoint, values):
        """Return Rackspace URL for object."""
        try:
            cont = self.get_container(values['container'])
            if cont.cdn_enabled:
                return "%s/%s" % (cont.cdn_uri, values['filename'])
            else:
                return None
        except: # pragma: no cover
            return None

    def delete_file(self, name, container):
        """Delete file from container."""
        try:
            cnt = self.get_container(container)
            obj = cnt.get_object(name)
            obj.delete()
            return True
        except:
            return False

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from datetime import timedelta
from functools import update_wrapper
import csv
import codecs
import cStringIO
from flask import abort, request, make_response, current_app
from functools import wraps
from flask_oauth import OAuth
from flask.ext.login import current_user
from math import ceil
import json


def jsonpify(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f(*args, **kwargs).data) + ')'
            return current_app.response_class(content,
                                              mimetype='application/javascript')
        else:
            return f(*args, **kwargs)
    return decorated_function


def admin_required(f):  # pragma: no cover
    """Checks if the user is and admin or not"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.admin:
            return f(*args, **kwargs)
        else:
            return abort(403)
    return decorated_function


# from http://flask.pocoo.org/snippets/56/
def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:  # pragma: no cover
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):  # pragma: no cover
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):  # pragma: no cover
        max_age = max_age.total_seconds()

    def get_methods():  # pragma: no cover
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):

        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':  # pragma: no cover
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':  # pragma: no cover
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


# Fromhttp://stackoverflow.com/q/1551382
def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    import dateutil.parser
    now = datetime.now()
    if type(time) is str or type(time) is unicode:
        time = dateutil.parser.parse(time)
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return ' '.join([str(second_diff / 60), "minutes ago"])
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return ' '.join([str(second_diff / 3600), "hours ago"])
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return ' '.join([str(day_diff), "days ago"])
    if day_diff < 31:
        return ' '.join([str(day_diff / 7), "weeks ago"])
    if day_diff < 60:
        return ' '.join([str(day_diff / 30), "month ago"])
    if day_diff < 365:
        return ' '.join([str(day_diff / 30), "months ago"])
    if day_diff < (365 * 2):
        return ' '.join([str(day_diff / 365), "year ago"])
    return ' '.join([str(day_diff / 365), "years ago"])


class Pagination(object):

    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=0, left_current=2, right_current=3,
                   right_edge=0):
        last = 0
        for num in xrange(1, self.pages + 1):
            if (num <= left_edge or
                    (num > self.page - left_current - 1 and
                     num < self.page + right_current) or
                    num > self.pages - right_edge):
                if last + 1 != num:  # pragma: no cover
                    yield None
                yield num
                last = num


class Twitter(object):
    oauth = OAuth()

    def __init__(self, app=None):
        self.app = app
        if app is not None: # pragma: no cover
            self.init_app(app)

    def init_app(self, app):
        self.oauth = self.oauth.remote_app(
            'twitter',
            base_url='https://api.twitter.com/1/',
            request_token_url='https://api.twitter.com/oauth/request_token',
            access_token_url='https://api.twitter.com/oauth/access_token',
            authorize_url='https://api.twitter.com/oauth/authenticate',
            consumer_key=app.config['TWITTER_CONSUMER_KEY'],
            consumer_secret=app.config['TWITTER_CONSUMER_SECRET'])


class Facebook(object):
    oauth = OAuth()

    def __init__(self, app=None):
        self.app = app
        if app is not None: # pragma: no cover
            self.init_app(app)

    def init_app(self, app):
        self.oauth = self.oauth.remote_app(
            'facebook',
            base_url='https://graph.facebook.com/',
            request_token_url=None,
            access_token_url='/oauth/access_token',
            authorize_url='https://www.facebook.com/dialog/oauth',
            consumer_key=app.config['FACEBOOK_APP_ID'],
            consumer_secret=app.config['FACEBOOK_APP_SECRET'],
            request_token_params={'scope': 'email'})


def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # This code is taken from http://docs.python.org/library/csv.html#examples
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]


def utf_8_encoder(unicode_csv_data):
    # This code is taken from http://docs.python.org/library/csv.html#examples
    for line in unicode_csv_data:
        yield line.encode('utf-8')


class Google(object):
    oauth = OAuth()

    def __init__(self, app=None):
        self.app = app
        if app is not None: # pragma: no cover
            self.init_app(app)

    def init_app(self, app):
        self.oauth = self.oauth.remote_app(
            'google',
            base_url='https://www.google.com/accounts/',
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            request_token_url=None,
            request_token_params={'scope': 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email',
                                  'response_type': 'code'},
            access_token_url='https://accounts.google.com/o/oauth2/token',
            access_token_method='POST',
            access_token_params={'grant_type': 'authorization_code'},
            consumer_key=app.config['GOOGLE_CLIENT_ID'],
            consumer_secret=app.config['GOOGLE_CLIENT_SECRET'])


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        line = []
        for s in row:
            if (type(s) == dict):
                line.append(json.dumps(s))
            else:
                line.append(unicode(s).encode("utf-8"))
        self.writer.writerow(line)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):  # pragma: no cover
        for row in rows:
            self.writerow(row)


def get_user_signup_method(user):
    """Return which OAuth sign up method the user used"""
    msg = u'Sorry, there is already an account with the same e-mail.'
    # Google
    if user.info.get('google_token'):
        msg += " <strong>It seems like you signed up with your Google account.</strong>"
        msg += "<br/>You can try and sign in by clicking in the Google button."
        return (msg, 'google')
    # Facebook
    elif user.info.get('facebook_token'):
        msg += " <strong>It seems like you signed up with your Facebook account.</strong>"
        msg += "<br/>You can try and sign in by clicking in the Facebook button."
        return (msg, 'facebook')
    # Twitter
    elif user.info.get('twitter_token'):
        msg += " <strong>It seems like you signed up with your Twitter account.</strong>"
        msg += "<br/>You can try and sign in by clicking in the Twitter button."
        return (msg, 'twitter')
    # Local account
    else:
        msg += " <strong>It seems that you created an account locally.</strong>"
        msg += " <br/>You can reset your password if you don't remember it."
        return (msg, 'local')

def get_port():
    import os
    port = os.environ.get('PORT', '')
    if port.isdigit():
        return int(port)
    else:
        return current_app.config['PORT']


def get_user_id_or_ip():
    """Returns the id of the current user if is authenticated. Otherwise
    returns its IP address (defaults to 127.0.0.1)"""
    user_id = current_user.id if current_user.is_authenticated() else None
    user_ip = request.remote_addr or "127.0.0.1" if current_user.is_anonymous() else None
    return dict(user_id=user_id, user_ip=user_ip)

########NEW FILE########
__FILENAME__ = validator
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask.ext.babel import lazy_gettext
from wtforms.validators import ValidationError
import re


class Unique(object):

    """Validator that checks field uniqueness."""

    def __init__(self, session, model, field, message=None):
        self.session = session
        self.model = model
        self.field = field
        if not message:  # pragma: no cover
            message = lazy_gettext(u'This item already exists')
        self.message = message

    def __call__(self, form, field):
        check = self.session.query(self.model)\
                    .filter(self.field == field.data)\
                    .first()
        if 'id' in form:
            id = form.id.data
        else:
            id = None
        if check and (id is None or id != check.id):
            raise ValidationError(self.message)


class NotAllowedChars(object):
    """Validator that checks field not allowed chars"""
    not_valid_chars = '$#&\/| '

    def __init__(self, message=None):
        if not message:
            self.message = lazy_gettext(u'%sand space symbols are forbidden'
                                        % self.not_valid_chars)
        else:  # pragma: no cover
            self.message = message

    def __call__(self, form, field):
        if any(c in field.data for c in self.not_valid_chars):
            raise ValidationError(self.message)


class CommaSeparatedIntegers(object):
    """Validator that validates input fields that have comma separated values"""
    not_valid_chars = '$#&\/| '

    def __init__(self, message=None):
        if not message:
            self.message = lazy_gettext(u'Only comma separated values are allowed, no spaces')

        else:  # pragma: no cover
            self.message = message

    def __call__(self, form, field):
        pattern = re.compile('^[\d,]+$')
        if pattern.match(field.data) is None:
            raise ValidationError(self.message)

########NEW FILE########
__FILENAME__ = account
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa Account view for web application.

This module exports the following endpoints:
    * Accounts index: list of all registered users in PyBossa
    * Signin: method for signin into PyBossa
    * Signout: method for signout from PyBossa
    * Register: method for creating a new PyBossa account
    * Profile: method to manage user's profile (update data, reset password...)

"""
from itsdangerous import BadData
from markdown import markdown
import json
import time

from flask import Blueprint, request, url_for, flash, redirect, abort
from flask import render_template, current_app
from flask.ext.login import login_required, login_user, logout_user, \
    current_user
from flask.ext.mail import Message
from flask_wtf import Form
from flask_wtf.file import FileField, FileRequired
from wtforms import TextField, PasswordField, validators, \
    IntegerField, SelectField, BooleanField
from wtforms.widgets import HiddenInput

import pybossa.validator as pb_validator
import pybossa.model as model
from flask.ext.babel import lazy_gettext, gettext
from sqlalchemy.sql import text
from pybossa.model.user import User
from pybossa.core import db, signer, mail, uploader
from pybossa.util import Pagination, get_user_id_or_ip
from pybossa.util import get_user_signup_method
from pybossa.cache import users as cached_users


blueprint = Blueprint('account', __name__)


@blueprint.route('/', defaults={'page': 1})
@blueprint.route('/page/<int:page>')
def index(page):
    """
    Index page for all PyBossa registered users.

    Returns a Jinja2 rendered template with the users.

    """
    per_page = 24
    count = cached_users.get_total_users()
    accounts = cached_users.get_users_page(page, per_page)
    if not accounts and page != 1:
        abort(404)
    pagination = Pagination(page, per_page, count)
    if current_user.is_authenticated():
        user_id = current_user.id
    else:
        user_id = 'anonymous'
    top_users = cached_users.get_leaderboard(current_app.config['LEADERBOARD'],
                                             user_id)
    return render_template('account/index.html', accounts=accounts,
                           total=count,
                           top_users=top_users,
                           title="Community", pagination=pagination)


class LoginForm(Form):

    """Login Form class for signin into PyBossa."""

    email = TextField(lazy_gettext('E-mail'),
                      [validators.Required(
                          message=lazy_gettext("The e-mail is required"))])

    password = PasswordField(lazy_gettext('Password'),
                             [validators.Required(
                                 message=lazy_gettext(
                                     "You must provide a password"))])


@blueprint.route('/signin', methods=['GET', 'POST'])
def signin():
    """
    Signin method for PyBossa users.

    Returns a Jinja2 template with the result of signing process.

    """
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        password = form.password.data
        email = form.email.data
        user = model.user.User.query.filter_by(email_addr=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            msg_1 = gettext("Welcome back") + " " + user.fullname
            flash(msg_1, 'success')
            return redirect(request.args.get("next") or url_for("home.home"))
        elif user:
            msg, method = get_user_signup_method(user)
            if method == 'local':
                msg = gettext("Ooops, Incorrect email/password")
                flash(msg, 'error')
            else:
                flash(msg, 'info')
        else:
            msg = gettext("Ooops, we didn't find you in the system, \
                          did you sign in?")
            flash(msg, 'info')

    if request.method == 'POST' and not form.validate():
        flash(gettext('Please correct the errors'), 'error')
    auth = {'twitter': False, 'facebook': False, 'google': False}
    if current_user.is_anonymous():
        # If Twitter is enabled in config, show the Twitter Sign in button
        if ('twitter' in current_app.blueprints): # pragma: no cover
            auth['twitter'] = True
        if ('facebook' in current_app.blueprints): # pragma: no cover
            auth['facebook'] = True
        if ('google' in current_app.blueprints): # pragma: no cover
            auth['google'] = True
        return render_template('account/signin.html',
                               title="Sign in",
                               form=form, auth=auth,
                               next=request.args.get('next'))
    else:
        # User already signed in, so redirect to home page
        return redirect(url_for("home.home"))


@blueprint.route('/signout')
def signout():
    """
    Signout PyBossa users.

    Returns a redirection to PyBossa home page.

    """
    logout_user()
    flash(gettext('You are now signed out'), 'success')
    return redirect(url_for('home.home'))


class RegisterForm(Form):

    """Register Form Class for creating an account in PyBossa."""

    err_msg = lazy_gettext("Full name must be between 3 and 35 "
                           "characters long")
    fullname = TextField(lazy_gettext('Full name'),
                         [validators.Length(min=3, max=35, message=err_msg)])

    err_msg = lazy_gettext("User name must be between 3 and 35 "
                           "characters long")
    err_msg_2 = lazy_gettext("The user name is already taken")
    name = TextField(lazy_gettext('User name'),
                         [validators.Length(min=3, max=35, message=err_msg),
                          pb_validator.NotAllowedChars(),
                          pb_validator.Unique(db.session, model.user.User,
                                              model.user.User.name, err_msg_2)])

    err_msg = lazy_gettext("Email must be between 3 and 35 characters long")
    err_msg_2 = lazy_gettext("Email is already taken")
    email_addr = TextField(lazy_gettext('Email Address'),
                           [validators.Length(min=3, max=35, message=err_msg),
                            validators.Email(),
                            pb_validator.Unique(
                                db.session, model.user.User,
                                model.user.User.email_addr, err_msg_2)])

    err_msg = lazy_gettext("Password cannot be empty")
    err_msg_2 = lazy_gettext("Passwords must match")
    password = PasswordField(lazy_gettext('New Password'),
                             [validators.Required(err_msg),
                              validators.EqualTo('confirm', err_msg_2)])

    confirm = PasswordField(lazy_gettext('Repeat Password'))


class UpdateProfileForm(Form):

    """Form Class for updating PyBossa's user Profile."""

    id = IntegerField(label=None, widget=HiddenInput())

    err_msg = lazy_gettext("Full name must be between 3 and 35 "
                           "characters long")
    fullname = TextField(lazy_gettext('Full name'),
                         [validators.Length(min=3, max=35, message=err_msg)])

    err_msg = lazy_gettext("User name must be between 3 and 35 "
                           "characters long")
    err_msg_2 = lazy_gettext("The user name is already taken")
    name = TextField(lazy_gettext('Username'),
                     [validators.Length(min=3, max=35, message=err_msg),
                      pb_validator.NotAllowedChars(),
                      pb_validator.Unique(
                          db.session, model.user.User, model.user.User.name, err_msg_2)])

    err_msg = lazy_gettext("Email must be between 3 and 35 characters long")
    err_msg_2 = lazy_gettext("Email is already taken")
    email_addr = TextField(lazy_gettext('Email Address'),
                           [validators.Length(min=3, max=35, message=err_msg),
                            validators.Email(),
                            pb_validator.Unique(
                                db.session, model.user.User,
                                model.user.User.email_addr, err_msg_2)])

    locale = SelectField(lazy_gettext('Language'))
    ckan_api = TextField(lazy_gettext('CKAN API Key'))
    privacy_mode = BooleanField(lazy_gettext('Privacy Mode'))

    def set_locales(self, locales):
        """Fill the locale.choices."""
        choices = []
        for locale in locales:
            if locale == 'en':
                lang = gettext("English")
            if locale == 'es':
                lang = gettext("Spanish")
            if locale == 'fr':
                lang = gettext("French")
            choices.append((locale, lang))
        self.locale.choices = choices


class AvatarUploadForm(Form):
    avatar = FileField(lazy_gettext('Avatar'), validators=[FileRequired()])
    x1 = IntegerField(label=None, widget=HiddenInput())
    y1 = IntegerField(label=None, widget=HiddenInput())
    x2 = IntegerField(label=None, widget=HiddenInput())
    y2 = IntegerField(label=None, widget=HiddenInput())



@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    """
    Register method for creating a PyBossa account.

    Returns a Jinja2 template

    """
    # TODO: re-enable csrf
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        account = model.user.User(fullname=form.fullname.data,
                             name=form.name.data,
                             email_addr=form.email_addr.data)
        account.set_password(form.password.data)
        # account.locale = get_locale()
        db.session.add(account)
        db.session.commit()
        login_user(account, remember=True)
        flash(gettext('Thanks for signing-up'), 'success')
        return redirect(url_for('home.home'))
    if request.method == 'POST' and not form.validate():
        flash(gettext('Please correct the errors'), 'error')
    return render_template('account/register.html',
                           title=gettext("Register"), form=form)


@blueprint.route('/profile', methods=['GET'])
def redirect_profile():
    if current_user.is_anonymous(): # pragma: no cover
        return redirect(url_for('.signin'))
    else:
        return redirect(url_for('.profile', name=current_user.name), 302)

@blueprint.route('/<name>/', methods=['GET'])
def profile(name):
    """
    Get user profile.

    Returns a Jinja2 template with the user information.

    """
    user = db.session.query(model.user.User).filter_by(name=name).first()

    if user is None:
        return abort(404)

    # Show public profile from another user
    if current_user.is_anonymous() or (user.id != current_user.id):
        user, apps_contributed, _ = cached_users.get_user_summary(name)
        apps_created, apps_draft = _get_user_apps(user['id'])
        if user:
            title = "%s &middot; User Profile" % user['fullname']
            return render_template('/account/public_profile.html',
                                   title=title,
                                   user=user,
                                   apps=apps_contributed,
                                   apps_created=apps_created)

    # Show user profile page with admin, as it is the same user
    if user.id == current_user.id and current_user.is_authenticated():
        sql = text('''
                   SELECT app.name, app.short_name, app.info,
                   COUNT(*) as n_task_runs
                   FROM task_run JOIN app ON
                   (task_run.app_id=app.id) WHERE task_run.user_id=:user_id
                   GROUP BY app.name, app.short_name, app.info
                   ORDER BY n_task_runs DESC;''')

        # results will have the following format
        # (app.name, app.short_name, n_task_runs)
        results = db.engine.execute(sql, user_id=current_user.id)

        apps_contrib = []
        for row in results:
            app = dict(name=row.name, short_name=row.short_name,
                       info=json.loads(row.info), n_task_runs=row.n_task_runs)
            apps_contrib.append(app)

        # Rank
        # See: https://gist.github.com/tokumine/1583695
        sql = text('''
                   WITH global_rank AS (
                        WITH scores AS (
                            SELECT user_id, COUNT(*) AS score FROM task_run
                            WHERE user_id IS NOT NULL GROUP BY user_id)
                        SELECT user_id, score, rank() OVER (ORDER BY score desc)
                        FROM scores)
                   SELECT * from global_rank WHERE user_id=:user_id;
                   ''')

        results = db.engine.execute(sql, user_id=current_user.id)
        for row in results:
            user.rank = row.rank
            user.score = row.score

        user.total = db.session.query(model.user.User).count()

        apps_published, apps_draft = _get_user_apps(current_user.id)

        return render_template('account/profile.html', title=gettext("Profile"),
                              apps_contrib=apps_contrib,
                              apps_published=apps_published,
                              apps_draft=apps_draft,
                              user=user)


@blueprint.route('/<name>/applications')
@login_required
def applications(name):
    """
    List user's application list.

    Returns a Jinja2 template with the list of applications of the user.

    """
    user = User.query.filter_by(name=name).first()
    if not user:
        return abort(404)
    if current_user.name != name:
        return abort(403)

    user = db.session.query(model.user.User).get(current_user.id)
    apps_published, apps_draft = _get_user_apps(user.id)

    return render_template('account/applications.html',
                           title=gettext("Applications"),
                           apps_published=apps_published,
                           apps_draft=apps_draft)


def _get_user_apps(user_id):
    apps_published = []
    apps_draft = []
    sql = text('''
               SELECT app.id, app.name, app.short_name, app.description,
               app.info
               FROM app, task
               WHERE app.id=task.app_id AND app.owner_id=:user_id AND
               app.hidden=0 AND app.info LIKE('%task_presenter%')
               GROUP BY app.id, app.name, app.short_name,
               app.description,
               app.info;''')

    results = db.engine.execute(sql, user_id=user_id)
    for row in results:
        app = dict(id=row.id, name=row.name, short_name=row.short_name,
                   description=row.description,
                   info=json.loads(row.info))
        apps_published.append(app)

    sql = text('''
               SELECT app.id, app.name, app.short_name, app.description,
               app.info
               FROM app
               WHERE app.owner_id=:user_id
               AND app.info NOT LIKE('%task_presenter%')
               GROUP BY app.id, app.name, app.short_name,
               app.description,
               app.info;''')
    results = db.engine.execute(sql, user_id=user_id)
    for row in results:
        app = dict(id=row.id, name=row.name, short_name=row.short_name,
                   description=row.description,
                   info=json.loads(row.info))
        apps_draft.append(app)
    return apps_published, apps_draft


@blueprint.route('/<name>/update', methods=['GET', 'POST'])
@login_required
def update_profile(name):
    """
    Update user's profile.

    Returns Jinja2 template.

    """
    user = User.query.filter_by(name=name).first()
    if not user:
        return abort(404)
    if current_user.id != user.id:
        return abort(403)
    show_passwd_form = True
    if user.twitter_user_id or user.google_user_id or user.facebook_user_id:
        show_passwd_form = False
    usr, apps, apps_created = cached_users.get_user_summary(name)
    # Extend the values
    current_user.rank = usr.get('rank')
    current_user.score = usr.get('score')
    # Title page
    title_msg = "Update your profile: %s" % current_user.fullname
    # Creation of forms
    update_form = UpdateProfileForm(obj=user)
    update_form.set_locales(current_app.config['LOCALES'])
    avatar_form = AvatarUploadForm()
    password_form = ChangePasswordForm()
    external_form = update_form


    if request.method == 'GET':
        return render_template('account/update.html',
                               title=title_msg,
                               user=usr,
                               form=update_form,
                               upload_form=avatar_form,
                               password_form=password_form,
                               external_form=external_form,
                               show_passwd_form=show_passwd_form)
    else:
        # Update user avatar
        if request.form.get('btn') == 'Upload':
            avatar_form = AvatarUploadForm()
            if avatar_form.validate_on_submit():
                file = request.files['avatar']
                coordinates = (avatar_form.x1.data, avatar_form.y1.data,
                               avatar_form.x2.data, avatar_form.y2.data)
                prefix = time.time()
                file.filename = "%s_avatar.png" % prefix
                container = "user_%s" % current_user.id
                uploader.upload_file(file,
                                     container=container,
                                     coordinates=coordinates)
                # Delete previous avatar from storage
                if current_user.info.get('avatar'):
                    uploader.delete_file(current_user.info['avatar'], container)
                current_user.info = {'avatar': file.filename,
                                     'container': container}
                db.session.commit()
                cached_users.delete_user_summary(current_user.name)
                flash(gettext('Your avatar has been updated! It may \
                              take some minutes to refresh...'), 'success')
                return redirect(url_for('.update_profile', name=current_user.name))
            else:
                flash("You have to provide an image file to update your avatar",
                      "error")
                return render_template('/account/update.html',
                                       form=update_form,
                                       upload_form=avatar_form,
                                       password_form=password_form,
                                       external_form=external_form,
                                       title=title_msg,
                                       show_passwd_form=show_passwd_form)
        # Update user profile
        elif request.form.get('btn') == 'Profile':
            update_form = UpdateProfileForm()
            update_form.set_locales(current_app.config['LOCALES'])
            if update_form.validate():
                current_user.id = update_form.id.data
                current_user.fullname = update_form.fullname.data
                current_user.name = update_form.name.data
                current_user.email_addr = update_form.email_addr.data
                current_user.privacy_mode = update_form.privacy_mode.data
                current_user.locale = update_form.locale.data
                db.session.commit()
                cached_users.delete_user_summary(current_user.name)
                flash(gettext('Your profile has been updated!'), 'success')
                return redirect(url_for('.update_profile', name=current_user.name))
            else:
                flash(gettext('Please correct the errors'), 'error')
                title_msg = 'Update your profile: %s' % current_user.fullname
                return render_template('/account/update.html',
                                       form=update_form,
                                       upload_form=avatar_form,
                                       password_form=password_form,
                                       external_form=external_form,
                                       title=title_msg,
                                       show_passwd_form=show_passwd_form)

        # Update user password
        elif request.form.get('btn') == 'Password':
            # Update the data because passing it in the constructor does not work
            update_form.name.data = user.name
            update_form.fullname.data = user.fullname
            update_form.email_addr.data = user.email_addr
            update_form.ckan_api.data = user.ckan_api
            external_form = update_form
            if password_form.validate_on_submit():
                user = db.session.query(model.user.User).get(current_user.id)
                if user.check_password(password_form.current_password.data):
                    user.set_password(password_form.new_password.data)
                    db.session.add(user)
                    db.session.commit()
                    flash(gettext('Yay, you changed your password succesfully!'),
                          'success')
                    return redirect(url_for('.update_profile', name=name))
                else:
                    msg = gettext("Your current password doesn't match the "
                                  "one in our records")
                    flash(msg, 'error')
                    return render_template('/account/update.html',
                                           form=update_form,
                                           upload_form=avatar_form,
                                           password_form=password_form,
                                           external_form=external_form,
                                           title=title_msg,
                                           show_passwd_form=show_passwd_form)
            else:
                flash(gettext('Please correct the errors'), 'error')
                return render_template('/account/update.html',
                                       form=update_form,
                                       upload_form=avatar_form,
                                       password_form=password_form,
                                       external_form=external_form,
                                       title=title_msg,
                                       show_passwd_form=show_passwd_form)
        # Update user external services
        elif request.form.get('btn') == 'External':
            del external_form.locale
            del external_form.email_addr
            del external_form.fullname
            del external_form.name
            if external_form.validate():
                current_user.ckan_api = external_form.ckan_api.data or None
                db.session.commit()
                cached_users.delete_user_summary(current_user.name)
                flash(gettext('Your profile has been updated!'), 'success')
                return redirect(url_for('.update_profile', name=current_user.name))
            else:
                flash(gettext('Please correct the errors'), 'error')
                title_msg = 'Update your profile: %s' % current_user.fullname
                return render_template('/account/update.html',
                                       form=update_form,
                                       upload_form=avatar_form,
                                       password_form=password_form,
                                       external_form=external_form,
                                       title=title_msg,
                                       show_passwd_form=show_passwd_form)
        # Otherwise return 415
        else:
            return abort(415)


class ChangePasswordForm(Form):

    """Form for changing user's password."""

    current_password = PasswordField(lazy_gettext('Current password'))

    err_msg = lazy_gettext("Password cannot be empty")
    err_msg_2 = lazy_gettext("Passwords must match")
    new_password = PasswordField(lazy_gettext('New password'),
                                 [validators.Required(err_msg),
                                  validators.EqualTo('confirm', err_msg_2)])
    confirm = PasswordField(lazy_gettext('Repeat password'))


class ResetPasswordForm(Form):

    """Class for resetting user's password."""

    err_msg = lazy_gettext("Password cannot be empty")
    err_msg_2 = lazy_gettext("Passwords must match")
    new_password = PasswordField(lazy_gettext('New Password'),
                                 [validators.Required(err_msg),
                                  validators.EqualTo('confirm', err_msg_2)])
    confirm = PasswordField(lazy_gettext('Repeat Password'))


@blueprint.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """
    Reset password method.

    Returns a Jinja2 template.

    """
    key = request.args.get('key')
    if key is None:
        abort(403)
    userdict = {}
    try:
        userdict = signer.signer.loads(key, max_age=3600, salt='password-reset')
    except BadData:
        abort(403)
    username = userdict.get('user')
    if not username or not userdict.get('password'):
        abort(403)
    user = model.user.User.query.filter_by(name=username).first_or_404()
    if user.passwd_hash != userdict.get('password'):
        abort(403)
    form = ChangePasswordForm(request.form)
    if form.validate_on_submit():
        user.set_password(form.new_password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(gettext('You reset your password successfully!'), 'success')
        return redirect(url_for('.signin'))
    if request.method == 'POST' and not form.validate():
        flash(gettext('Please correct the errors'), 'error')
    return render_template('/account/password_reset.html', form=form)


class ForgotPasswordForm(Form):

    """Form Class for forgotten password."""

    err_msg = lazy_gettext("Email must be between 3 and 35 characters long")
    email_addr = TextField(lazy_gettext('Email Address'),
                           [validators.Length(min=3, max=35, message=err_msg),
                            validators.Email()])


@blueprint.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Request a forgotten password for a user.

    Returns a Jinja2 template.

    """
    form = ForgotPasswordForm(request.form)
    if form.validate_on_submit():
        user = model.user.User.query\
                    .filter_by(email_addr=form.email_addr.data)\
                    .first()
        if user and user.email_addr:
            msg = Message(subject='Account Recovery',
                          recipients=[user.email_addr])
            if user.twitter_user_id:
                msg.body = render_template(
                    '/account/email/forgot_password_openid.md',
                    user=user, account_name='Twitter')
            elif user.facebook_user_id:
                msg.body = render_template(
                    '/account/email/forgot_password_openid.md',
                    user=user, account_name='Facebook')
            elif user.google_user_id:
                msg.body = render_template(
                    '/account/email/forgot_password_openid.md',
                    user=user, account_name='Google')
            else:
                userdict = {'user': user.name, 'password': user.passwd_hash}
                key = signer.signer.dumps(userdict, salt='password-reset')
                recovery_url = url_for('.reset_password',
                                       key=key, _external=True)
                msg.body = render_template(
                    '/account/email/forgot_password.md',
                    user=user, recovery_url=recovery_url)
            msg.html = markdown(msg.body)
            mail.send(msg)
            flash(gettext("We've send you email with account "
                          "recovery instructions!"),
                  'success')
        else:
            flash(gettext("We don't have this email in our records. "
                          "You may have signed up with a different "
                          "email or used Twitter, Facebook, or "
                          "Google to sign-in"), 'error')
    if request.method == 'POST' and not form.validate():
        flash(gettext('Something went wrong, please correct the errors on the '
              'form'), 'error')
    return render_template('/account/password_forgot.html', form=form)


@blueprint.route('/<name>/resetapikey', methods=['POST'])
@login_required
def reset_api_key(name):
    """
    Reset API-KEY for user.

    Returns a Jinja2 template.

    """
    user = User.query.filter_by(name=name).first()
    if not user:
        return abort(404)
    if current_user.name != user.name:
        return abort(403)

    title = ("User: %s &middot; Settings"
             "- Reset API KEY") % current_user.fullname
    user = db.session.query(model.user.User).get(current_user.id)
    user.api_key = model.make_uuid()
    db.session.commit()
    cached_users.delete_user_summary(user.name)
    msg = gettext('New API-KEY generated')
    flash(msg, 'success')
    return redirect(url_for('account.profile', name=name))

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask import Blueprint
from flask import render_template
from flask import request
from flask import abort
from flask import flash
from flask import redirect
from flask import url_for
from flask import current_app
from flask import Response
from flask.ext.login import login_required, current_user
from flask_wtf import Form
from wtforms import TextField, IntegerField, validators
from wtforms.widgets import HiddenInput
from flask.ext.babel import lazy_gettext, gettext
from werkzeug.exceptions import HTTPException

import pybossa.model as model
from pybossa.core import db
from pybossa.util import admin_required, UnicodeWriter
from pybossa.cache import apps as cached_apps
from pybossa.cache import categories as cached_cat
from pybossa.auth import require
import pybossa.validator as pb_validator
from sqlalchemy import or_, func
import json
from StringIO import StringIO


blueprint = Blueprint('admin', __name__)


def format_error(msg, status_code):
    error = dict(error=msg,
                 status_code=status_code)
    return Response(json.dumps(error), status=status_code,
                    mimetype='application/json')


@blueprint.route('/')
@login_required
@admin_required
def index():
    """List admin actions"""
    return render_template('/admin/index.html')


@blueprint.route('/featured')
@blueprint.route('/featured/<int:app_id>', methods=['POST', 'DELETE'])
@login_required
@admin_required
def featured(app_id=None):
    """List featured apps of PyBossa"""
    try:
        categories = cached_cat.get_all()

        if request.method == 'GET':
            apps = {}
            for c in categories:
                n_apps = cached_apps.n_count(category=c.short_name)
                apps[c.short_name], n_apps = cached_apps.get(category=c.short_name,
                                                             page=1,
                                                             per_page=n_apps)
            return render_template('/admin/applications.html', apps=apps,
                                   categories=categories)
        else:
            app = db.session.query(model.app.App).get(app_id)
            if app:
                if request.method == 'POST':
                    cached_apps.reset()
                    f = model.featured.Featured()
                    f.app_id = app_id
                    require.app.update(app)
                    # Check if the app is already in this table
                    tmp = db.session.query(model.featured.Featured)\
                            .filter(model.featured.Featured.app_id == app_id)\
                            .first()
                    if (tmp is None):
                        db.session.add(f)
                        db.session.commit()
                        return json.dumps(f.dictize())
                    else:
                        msg = "App.id %s alreay in Featured table" % app_id
                        return format_error(msg, 415)
                if request.method == 'DELETE':
                    cached_apps.reset()
                    f = db.session.query(model.featured.Featured)\
                          .filter(model.featured.Featured.app_id == app_id)\
                          .first()
                    if (f):
                        db.session.delete(f)
                        db.session.commit()
                        return "", 204
                    else:
                        msg = 'App.id %s is not in Featured table' % app_id
                        return format_error(msg, 404)
            else:
                msg = 'App.id %s not found' % app_id
                return format_error(msg, 404)
    except Exception as e: # pragma: no cover
        current_app.logger.error(e)
        return abort(500)


class SearchForm(Form):
    user = TextField(lazy_gettext('User'))


@blueprint.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def users(user_id=None):
    """Manage users of PyBossa"""
    try:
        form = SearchForm(request.form)
        users = db.session.query(model.user.User)\
                  .filter(model.user.User.admin == True)\
                  .filter(model.user.User.id != current_user.id)\
                  .all()

        if request.method == 'POST' and form.user.data:
            query = '%' + form.user.data.lower() + '%'
            found = db.session.query(model.user.User)\
                      .filter(or_(func.lower(model.user.User.name).like(query),
                                  func.lower(model.user.User.fullname).like(query)))\
                      .filter(model.user.User.id != current_user.id)\
                      .all()
            require.user.update(found)
            if not found:
                flash("<strong>Ooops!</strong> We didn't find a user "
                      "matching your query: <strong>%s</strong>" % form.user.data)
            return render_template('/admin/users.html', found=found, users=users,
                                   title=gettext("Manage Admin Users"),
                                   form=form)

        return render_template('/admin/users.html', found=[], users=users,
                               title=gettext("Manage Admin Users"), form=form)
    except Exception as e:  # pragma: no cover
        current_app.logger.error(e)
        return abort(500)


@blueprint.route('/users/export')
@login_required
@admin_required
def export_users():
    """Export Users list in the given format, only for admins"""

    exportable_attributes = ('id', 'name', 'fullname', 'email_addr',
                             'created', 'locale', 'admin')

    def respond_json():
        return Response(gen_json(), mimetype='application/json')

    def gen_json():
        users = db.session.query(model.user.User).all()
        json_users = []
        for user in users:
            json_users.append(dictize_with_exportable_attributes(user))
        return json.dumps(json_users)

    def dictize_with_exportable_attributes(user):
        dict_user = {}
        for attr in exportable_attributes:
            dict_user[attr] = getattr(user, attr)
        return dict_user

    def respond_csv():
        out = StringIO()
        writer = UnicodeWriter(out)
        return Response(gen_csv(out, writer, write_user), mimetype='text/csv')

    def gen_csv(out, writer, write_user):
        add_headers(writer)
        for user in db.session.query(model.user.User).yield_per(1):
            write_user(writer, user)
        yield out.getvalue()

    def write_user(writer, user):
        values = [getattr(user, attr) for attr in sorted(exportable_attributes)]
        writer.writerow(values)

    def add_headers(writer):
        writer.writerow(sorted(exportable_attributes))

    export_formats = ["json", "csv"]

    fmt = request.args.get('format')
    if not fmt:
        return redirect(url_for('.index'))
    if fmt not in export_formats:
        abort(415)
    return {"json": respond_json, "csv": respond_csv}[fmt]()


@blueprint.route('/users/add/<int:user_id>')
@login_required
@admin_required
def add_admin(user_id=None):
    """Add admin flag for user_id"""
    try:
        if user_id:
            user = db.session.query(model.user.User)\
                     .get(user_id)
            require.user.update(user)
            if user:
                user.admin = True
                db.session.commit()
                return redirect(url_for(".users"))
            else:
                msg = "User not found"
                return format_error(msg, 404)
    except Exception as e: # pragma: no cover
        current_app.logger.error(e)
        return abort(500)


@blueprint.route('/users/del/<int:user_id>')
@login_required
@admin_required
def del_admin(user_id=None):
    """Del admin flag for user_id"""
    try:
        if user_id:
            user = db.session.query(model.user.User)\
                     .get(user_id)
            require.user.update(user)
            if user:
                user.admin = False
                db.session.commit()
                return redirect(url_for('.users'))
            else:
                msg = "User.id not found"
                return format_error(msg, 404)
        else:  # pragma: no cover
            msg = "User.id is missing for method del_admin"
            return format_error(msg, 415)
    except Exception as e:  # pragma: no cover
        current_app.logger.error(e)
        return abort(500)


class CategoryForm(Form):
    id = IntegerField(label=None, widget=HiddenInput())
    name = TextField(lazy_gettext('Name'),
                     [validators.Required(),
                      pb_validator.Unique(db.session, model.category.Category, model.category.Category.name,
                                          message="Name is already taken.")])
    description = TextField(lazy_gettext('Description'),
                            [validators.Required()])


@blueprint.route('/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def categories():
    """List Categories"""
    try:
        if request.method == 'GET':
            require.category.read()
            form = CategoryForm()
        if request.method == 'POST':
            require.category.create()
            form = CategoryForm(request.form)
            if form.validate():
                slug = form.name.data.lower().replace(" ", "")
                category = model.category.Category(name=form.name.data,
                                          short_name=slug,
                                          description=form.description.data)
                db.session.add(category)
                db.session.commit()
                cached_cat.reset()
                msg = gettext("Category added")
                flash(msg, 'success')
            else:
                flash(gettext('Please correct the errors'), 'error')
        categories = cached_cat.get_all()
        n_apps_per_category = dict()
        for c in categories:
            n_apps_per_category[c.short_name] = cached_apps.n_count(c.short_name)

        return render_template('admin/categories.html',
                               title=gettext('Categories'),
                               categories=categories,
                               n_apps_per_category=n_apps_per_category,
                               form=form)
    except Exception as e:  # pragma: no cover
        current_app.logger.error(e)
        return abort(500)


@blueprint.route('/categories/del/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def del_category(id):
    """Deletes a category"""
    try:
        category = db.session.query(model.category.Category).get(id)
        if category:
            if len(cached_cat.get_all()) > 1:
                require.category.delete(category)
                if request.method == 'GET':
                    return render_template('admin/del_category.html',
                                           title=gettext('Delete Category'),
                                           category=category)
                if request.method == 'POST':
                    db.session.delete(category)
                    db.session.commit()
                    msg = gettext("Category deleted")
                    flash(msg, 'success')
                    cached_cat.reset()
                    return redirect(url_for(".categories"))
            else:
                msg = gettext('Sorry, it is not possible to delete the only \
                                   available category. You can modify it, click the \
                                   edit button')
                flash(msg, 'warning')
                return redirect(url_for('.categories'))
        else:
            abort(404)
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        current_app.logger.error(e)
        return abort(500)


@blueprint.route('/categories/update/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def update_category(id):
    """Updates a category"""
    try:
        category = db.session.query(model.category.Category).get(id)
        if category:
            require.category.update(category)
            form = CategoryForm(obj=category)
            form.populate_obj(category)
            if request.method == 'GET':
                return render_template('admin/update_category.html',
                                       title=gettext('Update Category'),
                                       category=category,
                                       form=form)
            if request.method == 'POST':
                form = CategoryForm(request.form)
                if form.validate():
                    slug = form.name.data.lower().replace(" ", "")
                    new_category = model.category.Category(id=form.id.data,
                                                  name=form.name.data,
                                                  short_name=slug)
                    # print new_category.id
                    db.session.merge(new_category)
                    db.session.commit()
                    cached_cat.reset()
                    msg = gettext("Category updated")
                    flash(msg, 'success')
                    return redirect(url_for(".categories"))
                else:
                    msg = gettext("Please correct the errors")
                    flash(msg, 'success')
                    return render_template('admin/update_category.html',
                                           title=gettext('Update Category'),
                                           category=category,
                                           form=form)
        else:
            abort(404)
    except HTTPException:
        raise
    except Exception as e: # pragma: no cover
        current_app.logger.error(e)
        return abort(500)

########NEW FILE########
__FILENAME__ = applications
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import time
from StringIO import StringIO
from flask import Blueprint, request, url_for, flash, redirect, abort, Response, current_app
from flask import render_template, make_response
from flask_wtf import Form
from flask_wtf.file import FileField, FileRequired
from wtforms import IntegerField, DecimalField, TextField, BooleanField, \
    SelectField, validators, TextAreaField
from wtforms.widgets import HiddenInput
from flask.ext.login import login_required, current_user
from flask.ext.babel import lazy_gettext, gettext
from werkzeug.exceptions import HTTPException
from sqlalchemy.sql import text

import pybossa.model as model
import pybossa.stats as stats
import pybossa.validator as pb_validator
import pybossa.sched as sched

from pybossa.core import db, uploader
from pybossa.cache import ONE_DAY, ONE_HOUR
from pybossa.model.app import App
from pybossa.model.task import Task
from pybossa.model.user import User
from pybossa.util import Pagination, UnicodeWriter, admin_required, get_user_id_or_ip
from pybossa.auth import require
from pybossa.cache import apps as cached_apps
from pybossa.cache import categories as cached_cat
from pybossa.cache.helpers import add_custom_contrib_button_to
from pybossa.ckan import Ckan
from pybossa.extensions import misaka

import re
import json
import importer
import presenter as presenter_module
import operator
import math
import requests

blueprint = Blueprint('app', __name__)

class AvatarUploadForm(Form):
    id = IntegerField(label=None, widget=HiddenInput())
    avatar = FileField(lazy_gettext('Avatar'), validators=[FileRequired()])
    x1 = IntegerField(label=None, widget=HiddenInput(), default=0)
    y1 = IntegerField(label=None, widget=HiddenInput(), default=0)
    x2 = IntegerField(label=None, widget=HiddenInput(), default=0)
    y2 = IntegerField(label=None, widget=HiddenInput(), default=0)


class AppForm(Form):
    name = TextField(lazy_gettext('Name'),
                     [validators.Required(),
                      pb_validator.Unique(db.session, model.app.App, model.app.App.name,
                                          message=lazy_gettext("Name is already taken."))])
    short_name = TextField(lazy_gettext('Short Name'),
                           [validators.Required(),
                            pb_validator.NotAllowedChars(),
                            pb_validator.Unique(
                                db.session, model.app.App, model.app.App.short_name,
                                message=lazy_gettext(
                                    "Short Name is already taken."))])
    long_description = TextAreaField(lazy_gettext('Long Description'),
                                     [validators.Required()])


class AppUpdateForm(AppForm):
    id = IntegerField(label=None, widget=HiddenInput())
    description = TextAreaField(lazy_gettext('Description'),
                            [validators.Required(
                                message=lazy_gettext(
                                    "You must provide a description.")),
                             validators.Length(max=255)])
    long_description = TextAreaField(lazy_gettext('Long Description'))
    allow_anonymous_contributors = SelectField(
        lazy_gettext('Allow Anonymous Contributors'),
        choices=[('True', lazy_gettext('Yes')),
                 ('False', lazy_gettext('No'))])
    category_id = SelectField(lazy_gettext('Category'), coerce=int)
    hidden = BooleanField(lazy_gettext('Hide?'))


class TaskPresenterForm(Form):
    id = IntegerField(label=None, widget=HiddenInput())
    editor = TextAreaField('')


class TaskRedundancyForm(Form):
    n_answers = IntegerField(lazy_gettext('Redundancy'),
                             [validators.Required(),
                              validators.NumberRange(
                                  min=1, max=1000,
                                  message=lazy_gettext('Number of answers should be a \
                                                       value between 1 and 1,000'))])


class TaskPriorityForm(Form):
    task_ids = TextField(lazy_gettext('Task IDs'),
                         [validators.Required(),
                          pb_validator.CommaSeparatedIntegers()])

    priority_0 = DecimalField(lazy_gettext('Priority'),
                              [validators.NumberRange(
                                  min=0, max=1,
                                  message=lazy_gettext('Priority should be a \
                                                       value between 0.0 and 1.0'))])


class TaskSchedulerForm(Form):
    sched = SelectField(lazy_gettext('Task Scheduler'),
                        choices=[('default', lazy_gettext('Default')),
                                 ('breadth_first', lazy_gettext('Breadth First')),
                                 ('depth_first', lazy_gettext('Depth First')),
                                 ('random', lazy_gettext('Random'))])


class BlogpostForm(Form):
    id = IntegerField(label=None, widget=HiddenInput())
    title = TextField(lazy_gettext('Title'),
                     [validators.Required(message=lazy_gettext(
                                    "You must enter a title for the post."))])
    body = TextAreaField(lazy_gettext('Body'),
                           [validators.Required(message=lazy_gettext(
                                    "You must enter some text for the post."))])


def app_title(app, page_name):
    if not app:  # pragma: no cover
        return "Application not found"
    if page_name is None:
        return "Application: %s" % (app.name)
    return "Application: %s &middot; %s" % (app.name, page_name)


def app_by_shortname(short_name):
    app = cached_apps.get_app(short_name)
    if app.id:
        # Get owner
        owner = User.query.get(app.owner_id)
        # Populate CACHE with the data of the app
        return (app,
                owner,
                cached_apps.n_tasks(app.id),
                cached_apps.n_task_runs(app.id),
                cached_apps.overall_progress(app.id),
                cached_apps.last_activity(app.id))

    else:
        cached_apps.delete_app(short_name)
        return abort(404)


@blueprint.route('/', defaults={'page': 1})
@blueprint.route('/page/<int:page>/', defaults={'page': 1})
def redirect_old_featured(page):
    """DEPRECATED only to redirect old links"""
    return redirect(url_for('.index', page=page), 301)


@blueprint.route('/published/', defaults={'page': 1})
@blueprint.route('/published/<int:page>/', defaults={'page': 1})
def redirect_old_published(page):  # pragma: no cover
    """DEPRECATED only to redirect old links"""
    category = db.session.query(model.category.Category).first()
    return redirect(url_for('.app_cat_index', category=category.short_name, page=page), 301)


@blueprint.route('/draft/', defaults={'page': 1})
@blueprint.route('/draft/<int:page>/', defaults={'page': 1})
def redirect_old_draft(page):
    """DEPRECATED only to redirect old links"""
    return redirect(url_for('.draft', page=page), 301)


@blueprint.route('/category/featured/', defaults={'page': 1})
@blueprint.route('/category/featured/page/<int:page>/')
def index(page):
    """List apps in the system"""
    if cached_apps.n_featured() > 0:
        return app_index(page, cached_apps.get_featured, 'featured',
                         True, False)
    else:
        categories = cached_cat.get_all()
        cat_short_name = categories[0].short_name
        return redirect(url_for('.app_cat_index', category=cat_short_name))


def app_index(page, lookup, category, fallback, use_count):
    """Show apps of app_type"""

    per_page = current_app.config['APPS_PER_PAGE']

    apps, count = lookup(category, page, per_page)

    data = []
    for app in apps:
        data.append(dict(app=app, n_tasks=cached_apps.n_tasks(app['id']),
                         overall_progress=cached_apps.overall_progress(app['id']),
                         last_activity=app['last_activity'],
                         last_activity_raw=app['last_activity_raw'],
                         n_completed_tasks=cached_apps.n_completed_tasks(app['id']),
                         n_volunteers=cached_apps.n_volunteers(app['id'])))


    if fallback and not apps:  # pragma: no cover
        return redirect(url_for('.index'))

    pagination = Pagination(page, per_page, count)
    categories = cached_cat.get_all()
    # Check for pre-defined categories featured and draft
    featured_cat = model.category.Category(name='Featured',
                                  short_name='featured',
                                  description='Featured applications')
    if category == 'featured':
        active_cat = featured_cat
    elif category == 'draft':
        active_cat = model.category.Category(name='Draft',
                                    short_name='draft',
                                    description='Draft applications')
    else:
        active_cat = db.session.query(model.category.Category)\
                       .filter_by(short_name=category).first()

    # Check if we have to add the section Featured to local nav
    if cached_apps.n_featured() > 0:
        categories.insert(0, featured_cat)
    template_args = {
        "apps": data,
        "title": gettext("Applications"),
        "pagination": pagination,
        "active_cat": active_cat,
        "categories": categories}

    if use_count:
        template_args.update({"count": count})
    return render_template('/applications/index.html', **template_args)


@blueprint.route('/category/draft/', defaults={'page': 1})
@blueprint.route('/category/draft/page/<int:page>/')
@login_required
@admin_required
def draft(page):
    """Show the Draft apps"""
    return app_index(page, cached_apps.get_draft, 'draft',
                     False, True)


@blueprint.route('/category/<string:category>/', defaults={'page': 1})
@blueprint.route('/category/<string:category>/page/<int:page>/')
def app_cat_index(category, page):
    """Show Apps that belong to a given category"""
    return app_index(page, cached_apps.get, category, False, True)


@blueprint.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    require.app.create()
    form = AppForm(request.form)

    def respond(errors):
        return render_template('applications/new.html',
                               title=gettext("Create an Application"),
                               form=form, errors=errors)

    def _description_from_long_description():
        long_desc = form.long_description.data
        html_long_desc = misaka.render(long_desc)[:-1]
        remove_html_tags_regex = re.compile('<[^>]*>')
        blank_space_regex = re.compile('\n')
        text_desc = remove_html_tags_regex.sub("", html_long_desc)[:255]
        if len(text_desc) >= 252:
            text_desc = text_desc[:-3]
            text_desc += "..."
        return blank_space_regex.sub(" ", text_desc)

    if request.method != 'POST':
        return respond(False)

    if not form.validate():
        flash(gettext('Please correct the errors'), 'error')
        return respond(True)

    info = {}

    app = model.app.App(name=form.name.data,
                    short_name=form.short_name.data,
                    description=_description_from_long_description(),
                    long_description=form.long_description.data,
                    owner_id=current_user.id,
                    info=info)

    db.session.add(app)
    db.session.commit()

    msg_1 = gettext('Application created!')
    flash('<i class="icon-ok"></i> ' + msg_1, 'success')
    flash('<i class="icon-bullhorn"></i> ' +
          gettext('You can check the ') +
          '<strong><a href="https://docs.pybossa.com">' +
          gettext('Guide and Documentation') +
          '</a></strong> ' +
          gettext('for adding tasks, a thumbnail, using PyBossa.JS, etc.'),
          'info')
    return redirect(url_for('.update', short_name=app.short_name))


@blueprint.route('/<short_name>/tasks/taskpresentereditor', methods=['GET', 'POST'])
@login_required
def task_presenter_editor(short_name):
    try:
        errors = False
        (app, owner, n_tasks,
        n_task_runs, overall_progress, last_activty) = app_by_shortname(short_name)

        title = app_title(app, "Task Presenter Editor")
        require.app.read(app)
        require.app.update(app)

        form = TaskPresenterForm(request.form)
        form.id.data = app.id
        if request.method == 'POST' and form.validate():
            db_app = db.session.query(model.app.App).filter_by(id=app.id).first()
            db_app.info['task_presenter'] = form.editor.data
            db.session.add(db_app)
            db.session.commit()
            cached_apps.delete_app(app.short_name)
            msg_1 = gettext('Task presenter added!')
            flash('<i class="icon-ok"></i> ' + msg_1, 'success')
            return redirect(url_for('.tasks', short_name=app.short_name))

        # It does not have a validation
        if request.method == 'POST' and not form.validate():  # pragma: no cover
            flash(gettext('Please correct the errors'), 'error')
            errors = True

        if app.info.get('task_presenter'):
            form.editor.data = app.info['task_presenter']
        else:
            if not request.args.get('template'):
                msg_1 = gettext('<strong>Note</strong> You will need to upload the'
                                ' tasks using the')
                msg_2 = gettext('CSV importer')
                msg_3 = gettext(' or download the app bundle and run the'
                                ' <strong>createTasks.py</strong> script in your'
                                ' computer')
                url = '<a href="%s"> %s</a>' % (url_for('app.import_task',
                                                        short_name=app.short_name), msg_2)
                msg = msg_1 + url + msg_3
                flash(msg, 'info')

                wrap = lambda i: "applications/presenters/%s.html" % i
                pres_tmpls = map(wrap, presenter_module.presenters)

                return render_template(
                    'applications/task_presenter_options.html',
                    title=title,
                    app=app,
                    presenters=pres_tmpls)

            tmpl_uri = "applications/snippets/%s.html" \
                % request.args.get('template')
            tmpl = render_template(tmpl_uri, app=app)
            form.editor.data = tmpl
            msg = 'Your code will be <em>automagically</em> rendered in \
                          the <strong>preview section</strong>. Click in the \
                          preview button!'
            flash(gettext(msg), 'info')
        return render_template('applications/task_presenter_editor.html',
                               title=title,
                               form=form,
                               app=app,
                               errors=errors)
    except HTTPException as e:
        if app.hidden:
            raise abort(403)
        else:  # pragma: no cover
            raise e


@blueprint.route('/<short_name>/delete', methods=['GET', 'POST'])
@login_required
def delete(short_name):
    (app, owner, n_tasks,
    n_task_runs, overall_progress, last_activity) = app_by_shortname(short_name)
    try:
        title = app_title(app, "Delete")
        require.app.read(app)
        require.app.delete(app)
        if request.method == 'GET':
            return render_template('/applications/delete.html',
                                   title=title,
                                   app=app,
                                   owner=owner,
                                   n_tasks=n_tasks,
                                   overall_progress=overall_progress,
                                   last_activity=last_activity)
        # Clean cache
        cached_apps.delete_app(app.short_name)
        cached_apps.clean(app.id)
        app = App.query.get(app.id)
        db.session.delete(app)
        db.session.commit()
        flash(gettext('Application deleted!'), 'success')
        return redirect(url_for('account.profile', name=current_user.name))
    except HTTPException:  # pragma: no cover
        if app.hidden:
            raise abort(403)
        else:
            raise


@blueprint.route('/<short_name>/update', methods=['GET', 'POST'])
@login_required
def update(short_name):
    (app, owner, n_tasks,
     n_task_runs, overall_progress, last_activity) = app_by_shortname(short_name)

    def handle_valid_form(form):
        hidden = int(form.hidden.data)

        new_info = {}
        # Add the info items
        (app, owner, n_tasks, n_task_runs,
         overall_progress, last_activity) = app_by_shortname(short_name)

        # Merge info object
        info = dict(app.info.items() + new_info.items())

        new_application = model.app.App(
            id=form.id.data,
            name=form.name.data,
            short_name=form.short_name.data,
            description=form.description.data,
            long_description=form.long_description.data,
            hidden=hidden,
            info=info,
            owner_id=app.owner_id,
            allow_anonymous_contributors=form.allow_anonymous_contributors.data,
            category_id=form.category_id.data)

        (app, owner, n_tasks,
         n_task_runs, overall_progress, last_activity) = app_by_shortname(short_name)
        db.session.merge(new_application)
        db.session.commit()
        cached_apps.delete_app(short_name)
        cached_apps.reset()
        cached_cat.reset()
        cached_apps.get_app(new_application.short_name)
        flash(gettext('Application updated!'), 'success')
        return redirect(url_for('.details',
                                short_name=new_application.short_name))

    try:
        require.app.read(app)
        require.app.update(app)

        title = app_title(app, "Update")
        if request.method == 'GET':
            form = AppUpdateForm(obj=app)
            upload_form = AvatarUploadForm()
            categories = db.session.query(model.category.Category).all()
            form.category_id.choices = [(c.id, c.name) for c in categories]
            if app.category_id is None:
                app.category_id = categories[0].id
            form.populate_obj(app)

        if request.method == 'POST':
            upload_form = AvatarUploadForm()
            form = AppUpdateForm(request.form)
            categories = cached_cat.get_all()
            form.category_id.choices = [(c.id, c.name) for c in categories]

            if request.form.get('btn') != 'Upload':
                if form.validate():
                    return handle_valid_form(form)
                flash(gettext('Please correct the errors'), 'error')
            else:
                if upload_form.validate_on_submit():
                    app = App.query.get(app.id)
                    file = request.files['avatar']
                    coordinates = (upload_form.x1.data, upload_form.y1.data,
                                   upload_form.x2.data, upload_form.y2.data)
                    prefix = time.time()
                    file.filename = "app_%s_thumbnail_%i.png" % (app.id, prefix)
                    container = "user_%s" % current_user.id
                    uploader.upload_file(file,
                                         container=container,
                                         coordinates=coordinates)
                    # Delete previous avatar from storage
                    if app.info.get('thumbnail'):
                        uploader.delete_file(app.info['thumbnail'], container)
                    app.info['thumbnail'] = file.filename
                    app.info['container'] = container
                    db.session.commit()
                    cached_apps.delete_app(app.short_name)
                    flash(gettext('Your application thumbnail has been updated! It may \
                                  take some minutes to refresh...'), 'success')
                else:
                    flash(gettext('You must provide a file to change the avatar'),
                          'error')
                return redirect(url_for('.update', short_name=short_name))

        return render_template('/applications/update.html',
                               form=form,
                               upload_form=upload_form,
                               title=title,
                               app=app, owner=owner)
    except HTTPException:
        if app.hidden:  # pragma: no cover
            raise abort(403)
        else:  # pragma: no cover
            raise


@blueprint.route('/<short_name>/')
def details(short_name):
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)

    try:
        require.app.read(app)
        template = '/applications/app.html'
    except HTTPException:  # pragma: no cover
        if app.hidden:
            raise abort(403)
        else:
            raise

    title = app_title(app, None)

    app = add_custom_contrib_button_to(app, get_user_id_or_ip())

    template_args = {"app": app, "title": title,
                     "owner": owner,
                     "n_tasks": n_tasks,
                     "overall_progress": overall_progress,
                     "last_activity": last_activity,
                     "n_completed_tasks": cached_apps.n_completed_tasks(app.get('id')),
                     "n_volunteers": cached_apps.n_volunteers(app.get('id'))}
    if current_app.config.get('CKAN_URL'):
        template_args['ckan_name'] = current_app.config.get('CKAN_NAME')
        template_args['ckan_url'] = current_app.config.get('CKAN_URL')
        template_args['ckan_pkg_name'] = short_name
    return render_template(template, **template_args)


@blueprint.route('/<short_name>/settings')
@login_required
def settings(short_name):
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)

    title = app_title(app, "Settings")
    try:
        require.app.read(app)
        require.app.update(app)
        app = add_custom_contrib_button_to(app, get_user_id_or_ip())
        return render_template('/applications/settings.html',

                               app=app,
                               owner=owner,
                               n_tasks=n_tasks,
                               overall_progress=overall_progress,
                               last_activity=last_activity,
                               title=title)
    except HTTPException:
        if app.hidden:  # pragma: no cover
            raise abort(403)
        else:
            raise


def compute_importer_variant_pairs(forms):
    """Return a list of pairs of importer variants. The pair-wise enumeration
    is due to UI design.
    """
    variants = reduce(operator.__add__,
                      [i.variants for i in forms.itervalues()],
                      [])
    if len(variants) % 2: # pragma: no cover
        variants.append("empty")

    prefix = "applications/tasks/"

    importer_variants = map(lambda i: "%s%s.html" % (prefix, i), variants)
    return [
        (importer_variants[i * 2], importer_variants[i * 2 + 1])
        for i in xrange(0, int(math.ceil(len(variants) / 2.0)))]


@blueprint.route('/<short_name>/tasks/import', methods=['GET', 'POST'])
@login_required
def import_task(short_name):
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    title = app_title(app, "Import Tasks")
    loading_text = gettext("Importing tasks, this may take a while, wait...")
    template_args = {"title": title, "app": app, "loading_text": loading_text,
                     "owner": owner}
    try:
        require.app.read(app)
        require.app.update(app)
    except HTTPException:
        if app.hidden:  # pragma: no cover
            raise abort(403)
        else:
            raise

    data_handlers = dict([
        (i.template_id, (i.form_detector, i(request.form), i.form_id))
        for i in importer.importers])
    forms = [
        (i.form_id, i(request.form))
        for i in importer.importers]
    forms = dict(forms)
    template_args.update(forms)

    template_args["importer_variants"] = compute_importer_variant_pairs(forms)

    template = request.args.get('template')

    if not (template or request.method == 'POST'):
        return render_template('/applications/import_options.html',
                               **template_args)

    if template == 'gdocs':  # pragma: no cover
        mode = request.args.get('mode')
        if mode is not None:
            template_args["gdform"].googledocs_url.data = importer.googledocs_urls[mode]

    # in future, we shall pass an identifier of the form/template used,
    # which we can receive here, and use for a dictionary lookup, rather than
    # this search mechanism
    form = None
    handler = None
    for k, v in data_handlers.iteritems():
        field_id, handler, form_name = v
        if field_id in request.form:
            form = template_args[form_name]
            template = k
            break

    def render_forms():
        tmpl = '/applications/importers/%s.html' % template
        return render_template(tmpl, **template_args)

    if not (form and form.validate_on_submit()):  # pragma: no cover
        return render_forms()

    return _import_task(app, handler, form, render_forms)


def _import_task(app, handler, form, render_forms):
    try:
        empty = True
        n = 0
        n_data = 0
        for task_data in handler.tasks(form):
            n_data += 1
            task = model.task.Task(app_id=app.id)
            [setattr(task, k, v) for k, v in task_data.iteritems()]
            data = db.session.query(model.task.Task).filter_by(app_id=app.id).filter_by(info=task.info).first()
            if data is None:
                db.session.add(task)
                db.session.commit()
                n += 1
                empty = False
        if empty and n_data == 0:
            raise importer.BulkImportException(
                gettext('Oops! It looks like the file is empty.'))
        if empty and n_data > 0:
            flash(gettext('Oops! It looks like there are no new records to import.'), 'warning')

        msg = str(n) + " " + gettext('Tasks imported successfully!')
        if n == 1:
            msg = str(n) + " " + gettext('Task imported successfully!')
        flash(msg, 'success')
        cached_apps.delete_n_tasks(app.id)
        cached_apps.delete_n_task_runs(app.id)
        cached_apps.delete_overall_progress(app.id)
        cached_apps.delete_last_activity(app.id)
        return redirect(url_for('.tasks', short_name=app.short_name))
    except importer.BulkImportException, err_msg:
        flash(err_msg, 'error')
    except Exception as inst:  # pragma: no cover
        current_app.logger.error(inst)
        msg = 'Oops! Looks like there was an error with processing that file!'
        flash(gettext(msg), 'error')
    return render_forms()


@blueprint.route('/<short_name>/task/<int:task_id>')
def task_presenter(short_name, task_id):
    (app, owner,
     n_tasks, n_task_runs, overall_progress, last_activity) = app_by_shortname(short_name)
    task = Task.query.filter_by(id=task_id).first_or_404()
    try:
        require.app.read(app)
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else:  # pragma: no cover
            raise

    if current_user.is_anonymous():
        if not app.allow_anonymous_contributors:
            msg = ("Oops! You have to sign in to participate in "
                   "<strong>%s</strong>"
                   "application" % app.name)
            flash(gettext(msg), 'warning')
            return redirect(url_for('account.signin',
                                    next=url_for('.presenter',
                                                 short_name=app.short_name)))
        else:
            msg_1 = gettext(
                "Ooops! You are an anonymous user and will not "
                "get any credit"
                " for your contributions.")
            next_url = url_for(
                'app.task_presenter',
                short_name=short_name,
                task_id=task_id)
            url = url_for(
                'account.signin',
                next=next_url)
            flash(msg_1 + "<a href=\"" + url + "\">Sign in now!</a>", "warning")

    title = app_title(app, "Contribute")
    template_args = {"app": app, "title": title, "owner": owner}

    def respond(tmpl):
        return render_template(tmpl, **template_args)

    if not (task.app_id == app.id):
        return respond('/applications/task/wrong.html')

    #return render_template('/applications/presenter.html', app = app)
    # Check if the user has submitted a task before

    tr_search = db.session.query(model.task_run.TaskRun)\
                  .filter(model.task_run.TaskRun.task_id == task_id)\
                  .filter(model.task_run.TaskRun.app_id == app.id)

    if current_user.is_anonymous():
        remote_addr = request.remote_addr or "127.0.0.1"
        tr = tr_search.filter(model.task_run.TaskRun.user_ip == remote_addr)
    else:
        tr = tr_search.filter(model.task_run.TaskRun.user_id == current_user.id)

    tr_first = tr.first()
    if tr_first is None:
        return respond('/applications/presenter.html')
    else:
        return respond('/applications/task/done.html')


@blueprint.route('/<short_name>/presenter')
@blueprint.route('/<short_name>/newtask')
def presenter(short_name):

    def invite_new_volunteers():
        user_id = None if current_user.is_anonymous() else current_user.id
        user_ip = request.remote_addr if current_user.is_anonymous() else None
        task = sched.new_task(app.id, user_id, user_ip, 0)
        return task is None and overall_progress < 100.0

    def respond(tmpl):
        if (current_user.is_anonymous()):
            msg_1 = gettext(msg)
            flash(msg_1, "warning")
        resp = make_response(render_template(tmpl, **template_args))
        return resp

    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    title = app_title(app, "Contribute")
    template_args = {"app": app, "title": title, "owner": owner,
                     "invite_new_volunteers": invite_new_volunteers()}
    try:
        require.app.read(app)
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else:  # pragma: no cover
            raise

    if not app.allow_anonymous_contributors and current_user.is_anonymous():
        msg = "Oops! You have to sign in to participate in <strong>%s</strong> \
               application" % app.name
        flash(gettext(msg), 'warning')
        return redirect(url_for('account.signin',
                        next=url_for('.presenter', short_name=app.short_name)))

    msg = "Ooops! You are an anonymous user and will not \
           get any credit for your contributions. Sign in \
           now!"

    if app.info.get("tutorial") and \
            request.cookies.get(app.short_name + "tutorial") is None:
        resp = respond('/applications/tutorial.html')
        resp.set_cookie(app.short_name + 'tutorial', 'seen')
        return resp
    else:
        return respond('/applications/presenter.html')


@blueprint.route('/<short_name>/tutorial')
def tutorial(short_name):
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    title = app_title(app, "Tutorial")
    try:
        require.app.read(app)
    except HTTPException:
        if app.hidden:
            return abort(403)
        else: # pragma: no cover
            raise
    return render_template('/applications/tutorial.html', title=title,
                           app=app, owner=owner)


@blueprint.route('/<short_name>/<int:task_id>/results.json')
def export(short_name, task_id):
    """Return a file with all the TaskRuns for a give Task"""
    # Check if the app exists
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    try:
        require.app.read(app)
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else: # pragma: no cover
            raise

    # Check if the task belongs to the app and exists
    task = db.session.query(model.task.Task).filter_by(app_id=app.id)\
                                       .filter_by(id=task_id).first()
    if task:
        taskruns = db.session.query(model.task_run.TaskRun).filter_by(task_id=task_id)\
                             .filter_by(app_id=app.id).all()
        results = [tr.dictize() for tr in taskruns]
        return Response(json.dumps(results), mimetype='application/json')
    else:
        return abort(404)


@blueprint.route('/<short_name>/tasks/')
def tasks(short_name):
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    title = app_title(app, "Tasks")
    try:
        require.app.read(app)
        return render_template('/applications/tasks.html',
                               title=title,
                               app=app,
                               owner=owner,
                               n_tasks=n_tasks,
                               overall_progress=overall_progress,
                               last_activity=last_activity,
                               n_completed_tasks=cached_apps.n_completed_tasks(app.id),
                               n_volunteers=cached_apps.n_volunteers(app.id))
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else: # pragma: no cover
            raise


@blueprint.route('/<short_name>/tasks/browse', defaults={'page': 1})
@blueprint.route('/<short_name>/tasks/browse/<int:page>')
def tasks_browse(short_name, page):
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    title = app_title(app, "Tasks")

    def respond():
        per_page = 10
        count = db.session.query(model.task.Task)\
            .filter_by(app_id=app.id)\
            .count()
        app_tasks = db.session.query(model.task.Task)\
            .filter_by(app_id=app.id)\
            .order_by(model.task.Task.id)\
            .limit(per_page)\
            .offset((page - 1) * per_page)\
            .all()

        if not app_tasks and page != 1:
            abort(404)

        pagination = Pagination(page, per_page, count)
        return render_template('/applications/tasks_browse.html',
                               app=app,
                               owner=owner,
                               tasks=app_tasks,
                               title=title,
                               pagination=pagination)

    try:
        require.app.read(app)
        return respond()
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else: # pragma: no cover
            raise


@blueprint.route('/<short_name>/tasks/delete', methods=['GET', 'POST'])
@login_required
def delete_tasks(short_name):
    """Delete ALL the tasks for a given application"""
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    try:
        require.app.read(app)
        require.app.update(app)
        if request.method == 'GET':
            title = app_title(app, "Delete")
            return render_template('applications/tasks/delete.html',
                                   app=app,
                                   owner=owner,
                                   n_tasks=n_tasks,
                                   overall_progress=overall_progress,
                                   last_activity=last_activity,
                                   title=title)
        else:
            tasks = db.session.query(model.task.Task).filter_by(app_id=app.id).all()
            for t in tasks:
                db.session.delete(t)
            db.session.commit()
            msg = gettext("All the tasks and associated task runs have been deleted")
            flash(msg, 'success')
            cached_apps.delete_last_activity(app.id)
            cached_apps.delete_n_tasks(app.id)
            cached_apps.delete_n_task_runs(app.id)
            cached_apps.delete_overall_progress(app.id)
            return redirect(url_for('.tasks', short_name=app.short_name))
    except HTTPException:
        return abort(403)


@blueprint.route('/<short_name>/tasks/export')
def export_to(short_name):
    """Export Tasks and TaskRuns in the given format"""
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    title = app_title(app, gettext("Export"))
    loading_text = gettext("Exporting data..., this may take a while")

    try:
        require.app.read(app)
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else: # pragma: no cover
            raise

    def respond():
        return render_template('/applications/export.html',
                               title=title,
                               loading_text=loading_text,
                               app=app,
                               owner=owner)

    def gen_json(table):
        n = db.session.query(table)\
            .filter_by(app_id=app.id).count()
        sep = ", "
        yield "["
        for i, tr in enumerate(db.session.query(table)
                                 .filter_by(app_id=app.id).yield_per(1), 1):
            item = json.dumps(tr.dictize())
            if (i == n):
                sep = ""
            yield item + sep
        yield "]"

    def format_csv_properly(row):
        keys = sorted(row.keys())
        values = []
        for k in keys:
            values.append(row[k])
        return values


    def handle_task(writer, t):
        if (type(t.info) == dict):
            values = format_csv_properly(t.info)
            writer.writerow(values)
        else: # pragma: no cover
            writer.writerow([t.info])

    def handle_task_run(writer, t):
        if (type(t.info) == dict):
            values = format_csv_properly(t.info)
            writer.writerow(values)
        else: # pragma: no cover
            writer.writerow([t.info])

    def get_csv(out, writer, table, handle_row):
        for tr in db.session.query(table)\
                .filter_by(app_id=app.id)\
                .yield_per(1):
            handle_row(writer, tr)
        yield out.getvalue()

    def respond_json(ty):
        tables = {"task": model.task.Task, "task_run": model.task_run.TaskRun}
        try:
            table = tables[ty]
        except KeyError:
            return abort(404)
        return Response(gen_json(table), mimetype='application/json')

    def create_ckan_datastore(ckan, table, package_id):
        tables = {"task": model.task.Task, "task_run": model.task_run.TaskRun}
        new_resource = ckan.resource_create(name=table,
                                            package_id=package_id)
        ckan.datastore_create(name=table,
                              resource_id=new_resource['result']['id'])
        ckan.datastore_upsert(name=table,
                              records=gen_json(tables[table]),
                              resource_id=new_resource['result']['id'])

    def respond_ckan(ty):
        # First check if there is a package (dataset) in CKAN
        tables = {"task": model.task.Task, "task_run": model.task_run.TaskRun}
        msg_1 = gettext("Data exported to ")
        msg = msg_1 + "%s ..." % current_app.config['CKAN_URL']
        ckan = Ckan(url=current_app.config['CKAN_URL'],
                    api_key=current_user.ckan_api)
        app_url = url_for('.details', short_name=app.short_name, _external=True)

        try:
            package, e = ckan.package_exists(name=app.short_name)
            if e:
                raise e
            if package:
                # Update the package
                owner = User.query.get(app.owner_id)
                package = ckan.package_update(app=app, user=owner, url=app_url,
                                              resources=package['resources'])

                ckan.package = package
                resource_found = False
                for r in package['resources']:
                    if r['name'] == ty:
                        ckan.datastore_delete(name=ty, resource_id=r['id'])
                        ckan.datastore_create(name=ty, resource_id=r['id'])
                        ckan.datastore_upsert(name=ty,
                                              records=gen_json(tables[ty]),
                                              resource_id=r['id'])
                        resource_found = True
                        break
                if not resource_found:
                    create_ckan_datastore(ckan, ty, package['id'])
            else:
                owner = User.query.get(app.owner_id)
                package = ckan.package_create(app=app, user=owner, url=app_url)
                create_ckan_datastore(ckan, ty, package['id'])
                #new_resource = ckan.resource_create(name=ty,
                #                                    package_id=package['id'])
                #ckan.datastore_create(name=ty,
                #                      resource_id=new_resource['result']['id'])
                #ckan.datastore_upsert(name=ty,
                #                     records=gen_json(tables[ty]),
                #                     resource_id=new_resource['result']['id'])
            flash(msg, 'success')
            return respond()
        except requests.exceptions.ConnectionError:
                msg = "CKAN server seems to be down, try again layer or contact the CKAN admins"
                current_app.logger.error(msg)
                flash(msg, 'danger')
        except Exception as inst:
            if len(inst.args) == 3:
                t, msg, status_code = inst.args
                msg = ("Error: %s with status code: %s" % (t, status_code))
            else: # pragma: no cover
                msg = ("Error: %s" % inst.args[0])
            current_app.logger.error(msg)
            flash(msg, 'danger')
        finally:
            return respond()

    def respond_csv(ty):
        # Export Task(/Runs) to CSV
        types = {
            "task": (
                model.task.Task, handle_task,
                (lambda x: True),
                gettext(
                    "Oops, the application does not have tasks to \
                    export, if you are the owner add some tasks")),
            "task_run": (
                model.task_run.TaskRun, handle_task_run,
                (lambda x: type(x.info) == dict),
                gettext(
                    "Oops, there are no Task Runs yet to export, invite \
                     some users to participate"))}
        try:
            table, handle_row, test, msg = types[ty]
        except KeyError:
            return abort(404)

        out = StringIO()
        writer = UnicodeWriter(out)
        t = db.session.query(table)\
            .filter_by(app_id=app.id)\
            .first()
        if t is not None:
            if test(t):
                writer.writerow(sorted(t.info.keys()))

            return Response(get_csv(out, writer, table, handle_row),
                            mimetype='text/csv')
        else:
            flash(msg, 'info')
            return respond()

    export_formats = ["json", "csv"]
    if current_user.is_authenticated():
        if current_user.ckan_api:
            export_formats.append('ckan')

    ty = request.args.get('type')
    fmt = request.args.get('format')
    if not (fmt and ty):
        if len(request.args) >= 1:
            abort(404)
        return render_template('/applications/export.html',
                               title=title,
                               loading_text=loading_text,
                               ckan_name=current_app.config.get('CKAN_NAME'),
                               app=app,
                               owner=owner)
    if fmt not in export_formats:
        abort(415)
    return {"json": respond_json, "csv": respond_csv, 'ckan': respond_ckan}[fmt](ty)


@blueprint.route('/<short_name>/stats')
def show_stats(short_name):
    """Returns App Stats"""
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    n_volunteers = cached_apps.n_volunteers(app.id)
    n_completed_tasks = cached_apps.n_completed_tasks(app.id)
    title = app_title(app, "Statistics")

    try:
        require.app.read(app)
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else: # pragma: no cover
            raise

    if not ((n_tasks > 0) and (n_task_runs > 0)):
        return render_template('/applications/non_stats.html',
                               title=title,
                               app=app,
                               owner=owner)

    dates_stats, hours_stats, users_stats = stats.get_stats(
        app.id,
        current_app.config['GEO'])
    anon_pct_taskruns = int((users_stats['n_anon'] * 100) /
                            (users_stats['n_anon'] + users_stats['n_auth']))
    userStats = dict(
        geo=current_app.config['GEO'],
        anonymous=dict(
            users=users_stats['n_anon'],
            taskruns=users_stats['n_anon'],
            pct_taskruns=anon_pct_taskruns,
            top5=users_stats['anon']['top5']),
        authenticated=dict(
            users=users_stats['n_auth'],
            taskruns=users_stats['n_auth'],
            pct_taskruns=100 - anon_pct_taskruns,
            top5=users_stats['auth']['top5']))

    tmp = dict(userStats=users_stats['users'],
               userAnonStats=users_stats['anon'],
               userAuthStats=users_stats['auth'],
               dayStats=dates_stats,
               hourStats=hours_stats)

    return render_template('/applications/stats.html',
                           title=title,
                           appStats=json.dumps(tmp),
                           userStats=userStats,
                           app=app,
                           owner=owner,
                           n_tasks=n_tasks,
                           overall_progress=overall_progress,
                           n_volunteers=n_volunteers,
                           n_completed_tasks=n_completed_tasks)


@blueprint.route('/<short_name>/tasks/settings')
@login_required
def task_settings(short_name):
    """Settings page for tasks of the application"""
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    try:
        require.app.read(app)
        require.app.update(app)
        return render_template('applications/task_settings.html',
                               app=app,
                               owner=owner)
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else:
            raise


@blueprint.route('/<short_name>/tasks/redundancy', methods=['GET', 'POST'])
@login_required
def task_n_answers(short_name):
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    title = app_title(app, gettext('Redundancy'))
    form = TaskRedundancyForm()
    try:
        require.app.read(app)
        require.app.update(app)
        if request.method == 'GET':
            return render_template('/applications/task_n_answers.html',
                                   title=title,
                                   form=form,
                                   app=app,
                                   owner=owner)
        elif request.method == 'POST' and form.validate():
            sql = text('''
                       UPDATE task SET n_answers=:n_answers,
                       state='ongoing' WHERE app_id=:app_id''')
            db.engine.execute(sql, n_answers=form.n_answers.data, app_id=app.id)
            msg = gettext('Redundancy of Tasks updated!')
            flash(msg, 'success')
            return redirect(url_for('.tasks', short_name=app.short_name))
        else:
            flash(gettext('Please correct the errors'), 'error')
            return render_template('/applications/task_n_answers.html',
                                   title=title,
                                   form=form,
                                   app=app,
                                   owner=owner)
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else: # pragma: no cover
            raise


@blueprint.route('/<short_name>/tasks/scheduler', methods=['GET', 'POST'])
@login_required
def task_scheduler(short_name):
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    title = app_title(app, gettext('Task Scheduler'))
    form = TaskSchedulerForm()

    def respond():
        return render_template('/applications/task_scheduler.html',
                               title=title,
                               form=form,
                               app=app,
                               owner=owner)
    try:
        require.app.read(app)
        require.app.update(app)
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else: # pragma: no cover
            raise

    if request.method == 'GET':
        if app.info.get('sched'):
            for s in form.sched.choices:
                if app.info['sched'] == s[0]:
                    form.sched.data = s[0]
                    break
        return respond()

    if request.method == 'POST' and form.validate():
        app = App.query.filter_by(short_name=app.short_name).first()
        if form.sched.data:
            app.info['sched'] = form.sched.data
        db.session.add(app)
        db.session.commit()
        cached_apps.delete_app(app.short_name)
        msg = gettext("Application Task Scheduler updated!")
        flash(msg, 'success')
        return redirect(url_for('.tasks', short_name=app.short_name))
    else: # pragma: no cover
        flash(gettext('Please correct the errors'), 'error')
        return respond()


@blueprint.route('/<short_name>/tasks/priority', methods=['GET', 'POST'])
@login_required
def task_priority(short_name):
    (app, owner, n_tasks, n_task_runs,
     overall_progress, last_activity) = app_by_shortname(short_name)
    title = app_title(app, gettext('Task Priority'))
    form = TaskPriorityForm()

    def respond():
        return render_template('/applications/task_priority.html',
                               title=title,
                               form=form,
                               app=app,
                               owner=owner)
    try:
        require.app.read(app)
        require.app.update(app)
    except HTTPException:
        if app.hidden:
            raise abort(403)
        else:
            raise

    if request.method == 'GET':
        return respond()
    if request.method == 'POST' and form.validate():
        tasks = []
        for task_id in form.task_ids.data.split(","):
            if task_id != '':
                t = db.session.query(model.task.Task).filter_by(app_id=app.id)\
                              .filter_by(id=int(task_id)).first()
                if t:
                    t.priority_0 = form.priority_0.data
                    tasks.append(t)
                else:  # pragma: no cover
                    flash(gettext(("Ooops, Task.id=%s does not belong to the app" % task_id)), 'danger')
        db.session.add_all(tasks)
        db.session.commit()
        cached_apps.delete_app(app.short_name)
        flash(gettext("Task priority has been changed"), 'success')
        return respond()
    else:
        flash(gettext('Please correct the errors'), 'error')
        return respond()


@blueprint.route('/<short_name>/blog')
def show_blogposts(short_name):
    app, owner, _, _, _, _ = app_by_shortname(short_name)
    blogposts = db.session.query(model.blogpost.Blogpost).filter_by(app_id=app.id).all()
    require.blogpost.read(app_id=app.id)
    return render_template('applications/blog.html', app=app,
                           owner=owner, blogposts=blogposts)


@blueprint.route('/<short_name>/<int:id>')
def show_blogpost(short_name, id):
    app, owner, _, _, _, _ = app_by_shortname(short_name)
    blogpost = db.session.query(model.blogpost.Blogpost).filter_by(id=id,
                                                        app_id=app.id).first()
    if blogpost is None:
        raise abort(404)
    require.blogpost.read(blogpost)
    return render_template('applications/blog_post.html',
                            app=app,
                            owner=owner,
                            blogpost=blogpost)


@blueprint.route('/<short_name>/new-blogpost', methods=['GET', 'POST'])
@login_required
def new_blogpost(short_name):

    def respond():
        return render_template('applications/new_blogpost.html',
                               title=gettext("Write a new post"),
                               form=form, app=app, owner=owner)

    app, owner, _, _, _, _ = app_by_shortname(short_name)

    form = BlogpostForm(request.form)
    del form.id

    if request.method != 'POST':
        require.blogpost.create(app_id=app.id)
        return respond()

    if not form.validate():
        flash(gettext('Please correct the errors'), 'error')
        return respond()

    blogpost = model.blogpost.Blogpost(title=form.title.data,
                                body=form.body.data,
                                user_id=current_user.id,
                                app_id=app.id)
    require.blogpost.create(blogpost)
    db.session.add(blogpost)
    db.session.commit()
    cached_apps.delete_app(short_name)

    msg_1 = gettext('Blog post created!')
    flash('<i class="icon-ok"></i> ' + msg_1, 'success')

    return redirect(url_for('.show_blogposts', short_name=short_name))


@blueprint.route('/<short_name>/<int:id>/update', methods=['GET', 'POST'])
@login_required
def update_blogpost(short_name, id):
    app, owner, _, _, _, _ = app_by_shortname(short_name)

    blogpost = db.session.query(model.blogpost.Blogpost).filter_by(id=id,
                                                        app_id=app.id).first()
    if blogpost is None:
        raise abort(404)

    def respond():
        return render_template('applications/update_blogpost.html',
                               title=gettext("Edit a post"),
                               form=form, app=app, owner=owner,
                               blogpost=blogpost)
    form = BlogpostForm()

    if request.method != 'POST':
        require.blogpost.update(blogpost)
        form = BlogpostForm(obj=blogpost)
        return respond()

    if not form.validate():
        flash(gettext('Please correct the errors'), 'error')
        return respond()

    require.blogpost.update(blogpost)
    blogpost = model.blogpost.Blogpost(id=form.id.data,
                                title=form.title.data,
                                body=form.body.data,
                                user_id=current_user.id,
                                app_id=app.id)
    db.session.merge(blogpost)
    db.session.commit()
    cached_apps.delete_app(short_name)

    msg_1 = gettext('Blog post updated!')
    flash('<i class="icon-ok"></i> ' + msg_1, 'success')

    return redirect(url_for('.show_blogposts', short_name=short_name))


@blueprint.route('/<short_name>/<int:id>/delete', methods=['POST'])
@login_required
def delete_blogpost(short_name, id):
    app = app_by_shortname(short_name)[0]
    blogpost = db.session.query(model.blogpost.Blogpost).filter_by(id=id,
                                                        app_id=app.id).first()
    if blogpost is None:
        raise abort(404)

    require.blogpost.delete(blogpost)
    db.session.delete(blogpost)
    db.session.commit()
    cached_apps.delete_app(short_name)
    flash('<i class="icon-ok"></i> ' + 'Blog post deleted!', 'success')
    return redirect(url_for('.show_blogposts', short_name=short_name))





########NEW FILE########
__FILENAME__ = facebook
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask import Blueprint, request, url_for, flash, redirect, session
from flask.ext.login import login_user, current_user

from pybossa.core import db, facebook
from pybossa.model.user import User
#from pybossa.util import Facebook, get_user_signup_method
from pybossa.util import get_user_signup_method
# Required to access the config parameters outside a context as we are using
# Flask 0.8
# See http://goo.gl/tbhgF for more info
#from pybossa.core import app

# This blueprint will be activated in web.py if the FACEBOOK APP ID and SECRET
# are available
blueprint = Blueprint('facebook', __name__)


@blueprint.route('/', methods=['GET', 'POST'])
def login():  # pragma: no cover
    return facebook.oauth.authorize(callback=url_for('.oauth_authorized',
                                                     next=request.args.get("next"),
                                                     _external=True))


@facebook.oauth.tokengetter
def get_facebook_token():  # pragma: no cover
    if current_user.is_anonymous():
        return session.get('oauth_token')
    else:
        return (current_user.info['facebook_token']['oauth_token'], '')


@blueprint.route('/oauth-authorized')
@facebook.oauth.authorized_handler
def oauth_authorized(resp):  # pragma: no cover
    next_url = request.args.get('next') or url_for('home.home')
    if resp is None:
        flash(u'You denied the request to sign in.', 'error')
        flash(u'Reason: ' + request.args['error_reason'] +
              ' ' + request.args['error_description'], 'error')
        return redirect(next_url)

    # We have to store the oauth_token in the session to get the USER fields
    access_token = resp['access_token']
    session['oauth_token'] = (resp['access_token'], '')
    user_data = facebook.oauth.get('/me').data

    user = manage_user(access_token, user_data, next_url)
    if user is None:
        # Give a hint for the user
        user = db.session.query(User)\
                 .filter_by(email_addr=user_data['email'])\
                 .first()
        if user is not None:
            msg, method = get_user_signup_method(user)
            flash(msg, 'info')
            if method == 'local':
                return redirect(url_for('account.forgot_password'))
            else:
                return redirect(url_for('account.signin'))
        else:
            return redirect(url_for('account.signin'))
    else:
        first_login = False
        login_user(user, remember=True)
        flash("Welcome back %s" % user.fullname, 'success')
        request_email = False
        if (user.email_addr == "None"):
            request_email = True
        if request_email:
            if first_login:
                flash("This is your first login, please add a valid e-mail")
            else:
                flash("Please update your e-mail address in your profile page")
            return redirect(url_for('account.update_profile'))
        return redirect(next_url)


def manage_user(access_token, user_data, next_url):
    """Manage the user after signin"""
    user = db.session.query(User)\
             .filter_by(facebook_user_id=user_data['id']).first()

    if user is None:
        facebook_token = dict(oauth_token=access_token)
        info = dict(facebook_token=facebook_token)
        user = db.session.query(User)\
                 .filter_by(name=user_data['username']).first()
        # NOTE: Sometimes users at Facebook validate their accounts without
        # registering an e-mail (see this http://stackoverflow.com/a/17809808)
        email = None
        if user_data.get('email'):
            email = db.session.query(User)\
                      .filter_by(email_addr=user_data['email']).first()

        if user is None and email is None:
            if not user_data.get('email'):
                user_data['email'] = "None"
            user = User(fullname=user_data['name'],
                   name=user_data['username'],
                   email_addr=user_data['email'],
                   facebook_user_id=user_data['id'],
                   info=info)
            db.session.add(user)
            db.session.commit()
            return user
        else:
            return None
    else:
        return user

########NEW FILE########
__FILENAME__ = google
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask import Blueprint, request, url_for, flash, redirect, session
from flask.ext.login import login_user, current_user

from pybossa.core import db, google
from pybossa.model.user import User
from pybossa.util import get_user_signup_method
# Required to access the config parameters outside a context as we are using
# Flask 0.8
# See http://goo.gl/tbhgF for more info
import requests

# This blueprint will be activated in web.py if the FACEBOOK APP ID and SECRET
# are available
blueprint = Blueprint('google', __name__)

@blueprint.route('/', methods=['GET', 'POST'])
def login():  # pragma: no cover
    if request.args.get("next"):
        request_token_params = {
            'scope': 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email',
            'response_type': 'code'}
        google.oauth.request_token_params = request_token_params
    return google.oauth.authorize(callback=url_for('.oauth_authorized',
                                  _external=True))


@google.oauth.tokengetter
def get_google_token():  # pragma: no cover
    if current_user.is_anonymous():
        return session.get('oauth_token')
    else:
        return (current_user.info['google_token']['oauth_token'], '')


def manage_user(access_token, user_data, next_url):
    """Manage the user after signin"""
    # We have to store the oauth_token in the session to get the USER fields

    user = db.session.query(User)\
             .filter_by(google_user_id=user_data['id'])\
             .first()

    # user never signed on
    if user is None:
        google_token = dict(oauth_token=access_token)
        info = dict(google_token=google_token)
        user = db.session.query(User)\
                 .filter_by(name=user_data['name'].encode('ascii', 'ignore')
                                                  .lower().replace(" ", ""))\
                 .first()

        email = db.session.query(User)\
                  .filter_by(email_addr=user_data['email'])\
                  .first()

        if ((user is None) and (email is None)):
            user = User(fullname=user_data['name'],
                   name=user_data['name'].encode('ascii', 'ignore')
                                         .lower().replace(" ", ""),
                   email_addr=user_data['email'],
                   google_user_id=user_data['id'],
                   info=info)
            db.session.add(user)
            db.session.commit()
            return user
        else:
            return None
    else:
        # Update the name to fit with new paradigm to avoid UTF8 problems
        if type(user.name) == unicode or ' ' in user.name:
            user.name = user.name.encode('ascii', 'ignore').lower().replace(" ", "")
            db.session.add(user)
            db.session.commit()
        return user


@blueprint.route('/oauth_authorized')
@google.oauth.authorized_handler
def oauth_authorized(resp):  # pragma: no cover
    #print "OAUTH authorized method called"
    next_url = url_for('home.home')

    if resp is None or request.args.get('error'):
        flash(u'You denied the request to sign in.', 'error')
        flash(u'Reason: ' + request.args['error'], 'error')
        if request.args.get('error'):
                return redirect(url_for('account.signin'))
        return redirect(next_url)

    headers = {'Authorization': ' '.join(['OAuth', resp['access_token']])}
    url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    try:
        r = requests.get(url, headers=headers)
    except requests.exceptions.http_error:
        # Unauthorized - bad token
        if r.status_code == 401:
            return redirect(url_for('account.signin'))
        return r.content

    access_token = resp['access_token']
    session['oauth_token'] = access_token
    import json
    user_data = json.loads(r.content)
    user = manage_user(access_token, user_data, next_url)
    if user is None:
        # Give a hint for the user
        user = db.session.query(User)\
                 .filter_by(email_addr=user_data['email'])\
                 .first()
        if user is None:
            user = db.session.query(User)\
                     .filter_by(name=user_data['name'].encode('ascii', 'ignore')
                                                      .lower().replace(' ', ''))\
                     .first()

        msg, method = get_user_signup_method(user)
        flash(msg, 'info')
        if method == 'local':
            return redirect(url_for('account.forgot_password'))
        else:
            return redirect(url_for('account.signin'))
    else:
        login_user(user, remember=True)
        flash("Welcome back %s" % user.fullname, 'success')
        return redirect(next_url)

########NEW FILE########
__FILENAME__ = help
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask import Blueprint
from flask import render_template
from pybossa.cache import apps as cached_apps
from pybossa.cache import categories as cached_cat
from random import choice

blueprint = Blueprint('help', __name__)


@blueprint.route('/api')
def api():
    """Render help/api page"""
    categories = cached_cat.get_used()
    apps, count = cached_apps.get(categories[0]['short_name'])
    if len(apps) > 0:
        app_id = choice(apps)['id']
    else:  # pragma: no cover
        app_id = None
    return render_template('help/api.html', title="Help: API",
                           app_id=app_id)


@blueprint.route('/license')
def license():
    """Render help/license page"""
    return render_template('help/license.html', title='Help: Licenses')


@blueprint.route('/terms-of-use')
def tos():
    """Render help/terms-of-use page"""
    return render_template('help/tos.html', title='Help: Terms of Use')


@blueprint.route('/cookies-policy')
def cookies_policy():
    """Render help/cookies-policy page"""
    return render_template('help/cookies_policy.html', title='Help: Cookies Policy')

########NEW FILE########
__FILENAME__ = home
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask import current_app, request
from flask.ext.login import current_user
import pybossa.model as model
from pybossa.util import Pagination, get_user_id_or_ip
from flask import Blueprint
from flask import render_template
from pybossa.cache import apps as cached_apps
from pybossa.cache import users as cached_users
from pybossa.cache import categories as cached_cat


blueprint = Blueprint('home', __name__)

@blueprint.route('/')
def home():
    """ Render home page with the cached apps and users"""

    page = 1
    per_page = current_app.config.get('APPS_PER_PAGE')
    if per_page is None: # pragma: no cover
        per_page = 5
    d = {'featured': cached_apps.get_featured_front_page(),
         'top_apps': cached_apps.get_top(),
         'top_users': None}

    # Get all the categories with apps
    categories = cached_cat.get_used()
    d['categories'] = categories
    d['categories_apps'] = {}
    for c in categories:
        tmp_apps, count = cached_apps.get(c['short_name'], page, per_page)
        d['categories_apps'][str(c['short_name'])] = tmp_apps

    # Add featured
    tmp_apps, count = cached_apps.get_featured('featured', page, per_page)
    if count > 0:
        featured = model.category.Category(name='Featured', short_name='featured')
        d['categories'].insert(0,featured)
        d['categories_apps']['featured'] = tmp_apps

    if current_app.config['ENFORCE_PRIVACY'] and current_user.is_authenticated():
        if current_user.admin:
            d['top_users'] = cached_users.get_top()
    if not current_app.config['ENFORCE_PRIVACY']:
        d['top_users'] = cached_users.get_top()
    return render_template('/home/index.html', **d)



@blueprint.route("about")
def about():
    """Render the about template"""
    return render_template("/home/about.html")

@blueprint.route("search")
def search():
    """Render search results page"""
    return render_template("/home/search.html")

########NEW FILE########
__FILENAME__ = importer
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from StringIO import StringIO
from flask_wtf import Form
from wtforms import TextField, validators
from flask.ext.babel import lazy_gettext, gettext
from pybossa.util import unicode_csv_reader
import json
import requests


importers = []


def register_importer(cls):
    importers.append(cls)
    return cls


# def enabled_importers(enabled_importer_names=None):
#     if enabled_importer_names is None:
#         return importers
#     check = lambda i: i.template_id in enabled_importer_names
#     return filter(check, importers)


class BulkImportException(Exception):
    pass


googledocs_urls = {
    'spreadsheet': None,
    'image': "https://docs.google.com/spreadsheet/ccc"
             "?key=0AsNlt0WgPAHwdHFEN29mZUF0czJWMUhIejF6dWZXdkE"
             "&usp=sharing",
    'sound': "https://docs.google.com/spreadsheet/ccc"
             "?key=0AsNlt0WgPAHwdEczcWduOXRUb1JUc1VGMmJtc2xXaXc"
             "&usp=sharing",
    'video': "https://docs.google.com/spreadsheet/ccc"
             "?key=0AsNlt0WgPAHwdGZ2UGhxSTJjQl9YNVhfUVhGRUdoRWc"
             "&usp=sharing",
    'map': "https://docs.google.com/spreadsheet/ccc"
           "?key=0AsNlt0WgPAHwdGZnbjdwcnhKRVNlN1dGXy0tTnNWWXc"
           "&usp=sharing",
    'pdf': "https://docs.google.com/spreadsheet/ccc"
           "?key=0AsNlt0WgPAHwdEVVamc0R0hrcjlGdXRaUXlqRXlJMEE"
           "&usp=sharing"}


class BulkTaskImportForm(Form):
    template_id = None
    form_id = None
    form_detector = None
    tasks = None
    get_data_url = None

    def __init__(self, *args, **kwargs):
        super(BulkTaskImportForm, self).__init__(*args, **kwargs)

    def import_csv_tasks(self, csvreader):
        headers = []
        fields = set(['state', 'quorum', 'calibration', 'priority_0',
                      'n_answers'])
        field_header_index = []

        for row in csvreader:
            if not headers:
                headers = row
                if len(headers) != len(set(headers)):
                    msg = gettext('The file you uploaded has '
                                  'two headers with the same name.')
                    raise BulkImportException(msg)
                field_headers = set(headers) & fields
                for field in field_headers:
                    field_header_index.append(headers.index(field))
            else:
                task_data = {"info": {}}
                for idx, cell in enumerate(row):
                    if idx in field_header_index:
                        task_data[headers[idx]] = cell
                    else:
                        task_data["info"][headers[idx]] = cell
                yield task_data

    def get_csv_data_from_request(self, r):
        if r.status_code == 403:
            msg = "Oops! It looks like you don't have permission to access" \
                " that file"
            raise BulkImportException(gettext(msg), 'error')
        if ((not 'text/plain' in r.headers['content-type']) and
                (not 'text/csv' in r.headers['content-type'])):
            msg = gettext("Oops! That file doesn't look like the right file.")
            raise BulkImportException(msg, 'error')

        csvcontent = StringIO(r.text)
        csvreader = unicode_csv_reader(csvcontent)
        return self.import_csv_tasks(csvreader)

    @property
    def variants(self):
        return [self.template_id]


@register_importer
class BulkTaskCSVImportForm(BulkTaskImportForm):
    msg_required = lazy_gettext("You must provide a URL")
    msg_url = lazy_gettext("Oops! That's not a valid URL. "
                           "You must provide a valid URL")
    csv_url = TextField(lazy_gettext('URL'),
                        [validators.Required(message=msg_required),
                         validators.URL(message=msg_url)])
    template_id = "csv"
    form_id = "csvform"
    form_detector = "csv_url"

    def get_data_url(self, form):
        return form.csv_url.data

    def tasks(self, form):
        dataurl = self.get_data_url(form)
        r = requests.get(dataurl)
        return self.get_csv_data_from_request(r)


@register_importer
class BulkTaskGDImportForm(BulkTaskImportForm):
    msg_required = lazy_gettext("You must provide a URL")
    msg_url = lazy_gettext("Oops! That's not a valid URL. "
                           "You must provide a valid URL")
    googledocs_url = TextField(lazy_gettext('URL'),
                               [validators.Required(message=msg_required),
                                   validators.URL(message=msg_url)])
    template_id = "gdocs"
    form_id = "gdform"
    form_detector = "googledocs_url"

    def get_data_url(self, form):
        return ''.join([form.googledocs_url.data, '&output=csv'])

    def tasks(self, form):
        dataurl = self.get_data_url(form)
        r = requests.get(dataurl)
        return self.get_csv_data_from_request(r)

    @property
    def variants(self):
        return [("-".join([self.template_id, mode]))
                for mode in googledocs_urls.keys()]


@register_importer
class BulkTaskEpiCollectPlusImportForm(BulkTaskImportForm):
    msg_required = lazy_gettext("You must provide an EpiCollect Plus "
                                "project name")
    msg_form_required = lazy_gettext("You must provide a Form name "
                                     "for the project")
    epicollect_project = TextField(lazy_gettext('Project Name'),
                                   [validators.Required(message=msg_required)])
    epicollect_form = TextField(lazy_gettext('Form name'),
                                [validators.Required(message=msg_required)])
    template_id = "epicollect"
    form_id = "epiform"
    form_detector = "epicollect_project"

    def import_epicollect_tasks(self, data):
        for d in data:
            yield {"info": d}

    def get_data_url(self, form):
        return 'http://plus.epicollect.net/%s/%s.json' % \
            (form.epicollect_project.data, form.epicollect_form.data)

    def get_epicollect_data_from_request(self, r):
        if r.status_code == 403:
            msg = "Oops! It looks like you don't have permission to access" \
                " the EpiCollect Plus project"
            raise BulkImportException(gettext(msg), 'error')
        if not 'application/json' in r.headers['content-type']:
            msg = "Oops! That project and form do not look like the right one."
            raise BulkImportException(gettext(msg), 'error')
        return self.import_epicollect_tasks(json.loads(r.text))

    def tasks(self, form):
        dataurl = self.get_data_url(form)
        r = requests.get(dataurl)
        return self.get_epicollect_data_from_request(r)

########NEW FILE########
__FILENAME__ = leaderboard
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from flask import Blueprint, request, url_for, flash, redirect, abort, current_app
from flask import render_template
#from flaskext.wtf import Form, IntegerField, TextField, BooleanField, validators, HiddenInput
from flask.ext.login import login_required, current_user
from sqlalchemy.exc import UnboundExecutionError
from sqlalchemy.sql import func, text
from sqlalchemy import func

import pybossa.model as model
from pybossa.core import db
from pybossa.auth import require
from pybossa.cache import users as cached_users

blueprint = Blueprint('leaderboard', __name__)


@blueprint.route('/')
def index():
    """Get the last activity from users and apps"""
    if current_user.is_authenticated():
        user_id = current_user.id
    else:
        user_id = 'anonymous'
    top_users = cached_users.get_leaderboard(current_app.config['LEADERBOARD'],
                                             user_id=user_id)

    return render_template('/stats/index.html', title="Community Leaderboard",
                           top_users=top_users)

########NEW FILE########
__FILENAME__ = presenter
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
presenters = ["basic", "image", "sound", "video", "map", "pdf"]

########NEW FILE########
__FILENAME__ = stats
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import json
import pygeoip
from flask import Blueprint, current_app
from flask import render_template
from sqlalchemy.sql import text

from pybossa.core import db
from pybossa.cache import cache, ONE_DAY
from pybossa.cache import apps as cached_apps

blueprint = Blueprint('stats', __name__)


@cache(timeout=ONE_DAY, key_prefix="site_n_auth_users")
def n_auth_users():
    sql = text('''SELECT COUNT("user".id) AS n_auth FROM "user";''')
    results = db.engine.execute(sql)
    for row in results:
        n_auth = row.n_auth
    return n_auth or 0

@cache(timeout=ONE_DAY, key_prefix="site_n_anon_users")
def n_anon_users():
    sql = text('''SELECT COUNT(DISTINCT(task_run.user_ip))
               AS n_anon FROM task_run;''')

    results = db.engine.execute(sql)
    for row in results:
        n_anon = row.n_anon
    return n_anon or 0


@cache(timeout=ONE_DAY, key_prefix="site_n_tasks")
def n_tasks_site():
    sql = text('''SELECT COUNT(task.id) AS n_tasks FROM task''')
    results = db.engine.execute(sql)
    for row in results:
        n_tasks = row.n_tasks
    return n_tasks or 0


@cache(timeout=ONE_DAY, key_prefix="site_n_total_tasks")
def n_total_tasks_site():
    sql = text('''SELECT SUM(n_answers) AS n_tasks FROM task''')
    results = db.engine.execute(sql)
    for row in results:
        total = row.n_tasks
    return total or 0


@cache(timeout=ONE_DAY, key_prefix="site_n_task_runs")
def n_task_runs_site():
    sql = text('''SELECT COUNT(task_run.id) AS n_task_runs FROM task_run''')
    results = db.engine.execute(sql)
    for row in results:
        n_task_runs = row.n_task_runs
    return n_task_runs or 0


@cache(timeout=ONE_DAY, key_prefix="site_top5_apps_24_hours")
def get_top5_apps_24_hours():
    # Top 5 Most active apps in last 24 hours
    sql = text('''SELECT app.id, app.name, app.short_name, app.info,
               COUNT(task_run.app_id) AS n_answers FROM app, task_run
               WHERE app.id=task_run.app_id
               AND app.hidden=0
               AND DATE(task_run.finish_time) > NOW() - INTERVAL '24 hour'
               AND DATE(task_run.finish_time) <= NOW()
               GROUP BY app.id
               ORDER BY n_answers DESC LIMIT 5;''')

    results = db.engine.execute(sql, limit=5)
    top5_apps_24_hours = []
    for row in results:
        tmp = dict(id=row.id, name=row.name, short_name=row.short_name,
                   info=dict(json.loads(row.info)), n_answers=row.n_answers)
        top5_apps_24_hours.append(tmp)
    return top5_apps_24_hours


@cache(timeout=ONE_DAY, key_prefix="site_top5_users_24_hours")
def get_top5_users_24_hours():
    # Top 5 Most active users in last 24 hours
    sql = text('''SELECT "user".id, "user".fullname, "user".name,
               COUNT(task_run.app_id) AS n_answers FROM "user", task_run
               WHERE "user".id=task_run.user_id
               AND DATE(task_run.finish_time) > NOW() - INTERVAL '24 hour'
               AND DATE(task_run.finish_time) <= NOW()
               GROUP BY "user".id
               ORDER BY n_answers DESC LIMIT 5;''')

    results = db.engine.execute(sql, limit=5)
    top5_users_24_hours = []
    for row in results:
        user = dict(id=row.id, fullname=row.fullname,
                    name=row.name,
                    n_answers=row.n_answers)
        top5_users_24_hours.append(user)
    return top5_users_24_hours


@cache(timeout=ONE_DAY, key_prefix="site_locs")
def get_locs(): # pragma: no cover
    # All IP addresses from anonymous users to create a map
    locs = []
    if current_app.config['GEO']:
        sql = '''SELECT DISTINCT(user_ip) from task_run WHERE user_ip IS NOT NULL;'''
        results = db.engine.execute(sql)

        geolite = current_app.root_path + '/../dat/GeoLiteCity.dat'
        gic = pygeoip.GeoIP(geolite)
        for row in results:
            loc = gic.record_by_addr(row.user_ip)
            if loc is None:
                loc = {}
            if (len(loc.keys()) == 0):
                loc['latitude'] = 0
                loc['longitude'] = 0
            locs.append(dict(loc=loc))
    return locs


@blueprint.route('/')
def index():
    """Return Global Statistics for the site"""

    title = "Global Statistics"

    n_auth = n_auth_users()

    n_anon = n_anon_users()

    n_total_users = n_anon + n_auth

    n_published_apps = cached_apps.n_published()
    n_draft_apps = cached_apps.n_draft()
    n_total_apps = n_published_apps + n_draft_apps

    n_tasks = n_tasks_site()

    n_task_runs = n_task_runs_site()

    top5_apps_24_hours = get_top5_apps_24_hours()

    top5_users_24_hours = get_top5_users_24_hours()

    locs = get_locs()

    show_locs = False
    if len(locs) > 0:
        show_locs = True

    stats = dict(n_total_users=n_total_users, n_auth=n_auth, n_anon=n_anon,
                 n_published_apps=n_published_apps,
                 n_draft_apps=n_draft_apps,
                 n_total_apps=n_total_apps,
                 n_tasks=n_tasks,
                 n_task_runs=n_task_runs)

    users = dict(label="User Statistics",
                 values=[
                     dict(label='Anonymous', value=[0, n_anon]),
                     dict(label='Authenticated', value=[0, n_auth])])

    apps = dict(label="Apps Statistics",
                values=[
                    dict(label='Published', value=[0, n_published_apps]),
                    dict(label='Draft', value=[0, n_draft_apps])])

    tasks = dict(label="Task and Task Run Statistics",
                 values=[
                     dict(label='Tasks', value=[0, n_tasks]),
                     dict(label='Answers', value=[1, n_task_runs])])

    return render_template('/stats/global.html', title=title,
                           users=json.dumps(users),
                           apps=json.dumps(apps),
                           tasks=json.dumps(tasks),
                           locs=json.dumps(locs),
                           show_locs=show_locs,
                           top5_users_24_hours=top5_users_24_hours,
                           top5_apps_24_hours=top5_apps_24_hours,
                           stats=stats)

########NEW FILE########
__FILENAME__ = twitter
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
from flask import Blueprint, request, url_for, flash, redirect
from flask.ext.login import login_user, current_user

from pybossa.core import db, twitter
from pybossa.model.user import User
from pybossa.util import get_user_signup_method
# Required to access the config parameters outside a
# context as we are using Flask 0.8
# See http://goo.gl/tbhgF for more info

# This blueprint will be activated in web.py
# if the TWITTER CONSUMER KEY and SECRET
# are available
blueprint = Blueprint('twitter', __name__)


@blueprint.route('/', methods=['GET', 'POST'])
def login():  # pragma: no cover
    return twitter.oauth.authorize(callback=url_for('.oauth_authorized',
                                                    next=request.args.get("next")))


@twitter.oauth.tokengetter
def get_twitter_token():  # pragma: no cover
    if current_user.is_anonymous():
        return None

    return((current_user.info['twitter_token']['oauth_token'],
            current_user.info['twitter_token']['oauth_token_secret']))


def manage_user(access_token, user_data, next_url):
    """Manage the user after signin"""
    # Twitter API does not provide a way
    # to get the e-mail so we will ask for it
    # only the first time
    user = db.session.query(User)\
             .filter_by(twitter_user_id=user_data['user_id'])\
             .first()

    if user is not None:
        return user

    twitter_token = dict(oauth_token=access_token['oauth_token'],
                         oauth_token_secret=access_token['oauth_token_secret'])
    info = dict(twitter_token=twitter_token)
    user = db.session.query(User)\
        .filter_by(name=user_data['screen_name'])\
        .first()

    if user is not None:
        return None

    user = User(fullname=user_data['screen_name'],
           name=user_data['screen_name'],
           email_addr=user_data['screen_name'],
           twitter_user_id=user_data['user_id'],
           info=info)
    db.session.add(user)
    db.session.commit()
    return user


@blueprint.route('/oauth-authorized')
@twitter.oauth.authorized_handler
def oauth_authorized(resp):  # pragma: no cover
    """Called after authorization. After this function finished handling,
    the OAuth information is removed from the session again. When this
    happened, the tokengetter from above is used to retrieve the oauth
    token and secret.

    Because the remote application could have re-authorized the application
    it is necessary to update the values in the database.

    If the application redirected back after denying, the response passed
    to the function will be `None`. Otherwise a dictionary with the values
    the application submitted. Note that Twitter itself does not really
    redirect back unless the user clicks on the application name.
    """
    next_url = request.args.get('next') or url_for('home.home')
    if resp is None:
        flash(u'You denied the request to sign in.', 'error')
        return redirect(next_url)

    access_token = dict(oauth_token=resp['oauth_token'],
                        oauth_token_secret=resp['oauth_token_secret'])

    user_data = dict(screen_name=resp['screen_name'],
                     user_id=resp['user_id'])

    user = manage_user(access_token, user_data, next_url)

    if user is None:
        user = db.session.query(User)\
                 .filter_by(name=user_data['screen_name'])\
                 .first()
        msg, method = get_user_signup_method(user)
        flash(msg, 'info')
        if method == 'local':
            return redirect(url_for('account.forgot_password'))
        else:
            return redirect(url_for('account.signin'))

    first_login = False
    login_user(user, remember=True)
    flash("Welcome back %s" % user.fullname, 'success')
    if user.email_addr != user.name:
        return redirect(next_url)
    if first_login:
        flash("This is your first login, please add a valid e-mail")
    else:
        flash("Please update your e-mail address in your profile page")
    return redirect(url_for('account.update_profile'))


########NEW FILE########
__FILENAME__ = uploads
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
PyBossa Uploads view for LocalUploader application.

This module serves uploaded content like avatars.

"""
from flask import Blueprint, send_from_directory
from pybossa.core import uploader


blueprint = Blueprint('uploads', __name__)

@blueprint.route('/<path:filename>')
def uploaded_file(filename): # pragma: no cover
    return send_from_directory(uploader.upload_folder, filename)

########NEW FILE########
__FILENAME__ = vmcp
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import M2Crypto
import hashlib
import base64

"""
Sign the data in the given dictionary and return a new hash
that includes the signature.

@param $data Is a dictionary that contains the values to be signed
@param $salt Is the salt parameter passed via the cvm_salt GET parameter
@param $pkey Is the path to the private key file that will be used to calculate the signature
"""


def myquote(line):
    valid = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    escaped = ""
    for c in line:
        if c not in valid:
            escaped += "%%%.2X" % ord(c)
        else:
            escaped += c
    return escaped


def calculate_buffer(data, salt):
    strBuffer = ""
    for k in sorted(data.iterkeys()):

        # Handle the BOOL special case
        v = data[k]
        if type(v) == bool:  # pragma: no cover
            if v:
                v = 1
            else:
                v = 0
            data[k] = v

        # Update buffer
        strBuffer += "%s=%s\n" % (str(k).lower(), myquote(str(v)))

    # Append salt
    strBuffer += salt
    return strBuffer


def sign(data, salt, pkey):
    strBuffer = calculate_buffer(data, salt)
    # Sign data
    rsa = M2Crypto.RSA.load_key(pkey)
    digest = hashlib.new('sha512', strBuffer).digest()

    # Append signature
    data['signature'] = base64.b64encode(rsa.sign(digest, "sha512"))
    data['digest'] = digest
    data['strBuffer'] = strBuffer

    # Return new data dictionary
    return data

########NEW FILE########
__FILENAME__ = run
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 Daniel Lombraña González
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa. If not, see <http://www.gnu.org/licenses/>.
from pybossa.core import create_app

if __name__ == "__main__":  # pragma: no cover
    app = create_app()
    #logging.basicConfig(level=logging.NOTSET)
    app.run(host=app.config['HOST'], port=app.config['PORT'],
            debug=app.config.get('DEBUG', True))
else:
    app = create_app()

########NEW FILE########
__FILENAME__ = settings_test
SECRET = 'foobar'
SECRET_KEY = 'my-session-secret'
SQLALCHEMY_DATABASE_TEST_URI = 'postgresql://rtester:rtester@localhost/pybossa_test'
GOOGLE_CLIENT_ID = 'id'
GOOGLE_CLIENT_SECRET = 'secret'
TWITTER_CONSUMER_KEY='key'
TWITTER_CONSUMER_SECRET='secret'
FACEBOOK_APP_ID='id'
FACEBOOK_APP_SECRET='secret'
TERMSOFUSE = 'http://okfn.org/terms-of-use/'
DATAUSE = 'http://opendatacommons.org/licenses/by/'
ITSDANGEROUSKEY = 'its-dangerous-key'
LOGO = 'logo.png'
PORT=5001
MAIL_SERVER = 'localhost'
MAIL_USERNAME = None
MAIL_PASSWORD = None
MAIL_PORT = 25
MAIL_FAIL_SILENTLY = False
MAIL_DEFAULT_SENDER = 'PyBossa Support <info@pybossa.com>'
ANNOUNCEMENT = {'admin': 'Root Message', 'user': 'User Message', 'owner': 'Owner Message'}
LOCALES = ['en', 'es', 'fr']
ENFORCE_PRIVACY = False
REDIS_CACHE_ENABLED = False
REDIS_SENTINEL = [('localhost', 26379)]
REDIS_KEYPREFIX = 'pybossa_cache'
LOCALES = ['en', 'es', 'fr']
WTF_CSRF_ENABLED = False
TESTING = True
CSRF_ENABLED = False
MAIL_SERVER = 'localhost'
MAIL_USERNAME = None
MAIL_PASSWORD = None
MAIL_PORT = 25
MAIL_FAIL_SILENTLY = False
MAIL_DEFAULT_SENDER = 'PyBossa Support <info@pybossa.com>'
ALLOWED_EXTENSIONS = ['js', 'css', 'png', 'jpg', 'jpeg', 'gif']
UPLOAD_FOLDER = '/tmp/'
UPLOAD_METHOD = 'local'
RACKSPACE_USERNAME = 'username'
RACKSPACE_API_KEY = 'apikey'
RACKSPACE_REGION = 'ORD'

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from pybossa.model import db, rebuild_db
from pybossa.core import create_app, sentinel
from functools import wraps

flask_app = create_app()

def with_context(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        with flask_app.app_context():
            return f(*args, **kwargs)
    return decorated_function


def redis_flushall():
    sentinel.connection.master_for('mymaster').flushall()


def assert_not_raises(exception, call, *args, **kwargs):
    try:
        call(*args, **kwargs)
        assert True
    except exception as ex:
        assert False, str(ex)



class Test(object):

    def setUp(self):
        self.flask_app = flask_app
        self.app = flask_app.test_client()
        with self.flask_app.app_context():
            rebuild_db()


    def tearDown(self):
        with self.flask_app.app_context():
            db.session.remove()
            redis_flushall()

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from pybossa.model import db, rebuild_db
from pybossa.core import create_app, sentinel
from pybossa.model.app import App
from pybossa.model.category import Category
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun
from pybossa.model.user import User
import pybossa.model as model
from functools import wraps
import random

flask_app = create_app()

def with_context(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        with flask_app.app_context():
            return f(*args, **kwargs)
    return decorated_function


class Test(object):
    def setUp(self):
        self.flask_app = flask_app
        self.app = flask_app.test_client()
        with self.flask_app.app_context():
            rebuild_db()

    def tearDown(self):
        with self.flask_app.app_context():
            db.session.remove()
            self.redis_flushall()

    fullname = u'T Tester'
    fullname2 = u'T Tester 2'
    email_addr = u'tester@tester.com'
    email_addr2 = u'tester-2@tester.com'
    root_addr = u'root@root.com'
    name = u'tester'
    name2 = u'tester-2'
    root_name = u'root'
    api_key = 'tester'
    api_key_2 = 'tester-2'
    root_api_key = 'root'
    app_name = u'My New App'
    app_short_name = u'test-app'
    password = u'tester'
    root_password = password + 'root'
    cat_1 = 'thinking'
    cat_2 = 'sensing'

    def create(self,sched='default'):
        root, user,user2 = self.create_users()
        info = {
            'total': 150,
            'long_description': 'hello world',
            'task_presenter': 'TaskPresenter',
            'sched': sched
            }

        app = self.create_app(info)
        app.owner = user

        db.session.add(root)
        db.session.commit()
        db.session.add(user)
        db.session.commit()
        db.session.add(user2)
        db.session.commit()
        db.session.add(app)


        task_info = {
            'question': 'My random question',
            'url': 'my url'
            }
        task_run_info = {
            'answer': u'annakarenina'
            }

        # Create the task and taskruns for the first app
        for i in range (0,10):
             task, task_run = self.create_task_and_run(task_info, task_run_info, app, user,i)
             db.session.add_all([task, task_run])
        db.session.commit()
        db.session.remove()

    def create_2(self,sched='default'):
        root, user,user2 = self.create_users()

        info = {
            'total': 150,
            'long_description': 'hello world',
            'task_presenter': 'TaskPresenter',
            'sched': sched
            }

        app = self.create_app(info)
        app.owner = user

        db.session.add_all([root, user, user2, app])

        task_info = {
            'question': 'My random question',
            'url': 'my url'
            }
        task_run_info = {
            'answer': u'annakarenina'
            }

        # Create the task and taskruns for the first app
        task, task_run = self.create_task_and_run(task_info, task_run_info, app, user,1)
        db.session.add_all([task, task_run])

        db.session.commit()
        db.session.remove()


    def create_users(self):
        root = User(
                email_addr = self.root_addr,
                name = self.root_name,
                passwd_hash = self.root_password,
                fullname = self.fullname,
                api_key = self.root_api_key)
        root.set_password(self.root_password)

        user = User(
                email_addr = self.email_addr,
                name = self.name,
                passwd_hash = self.password,
                fullname = self.fullname,
                api_key = self.api_key
                )

        user.set_password(self.password)

        user2 = User(
                email_addr = self.email_addr2,
                name = self.name2,
                passwd_hash = self.password + "2",
                fullname = self.fullname2,
                api_key=self.api_key_2)

        user2.set_password(self.password)

        return root, user, user2

    def create_app(self,info):
        with self.flask_app.app_context():
            category = db.session.query(Category).first()
            if category is None:
                self._create_categories()
                category = db.session.query(Category).first()
            app = App(
                    name=self.app_name,
                    short_name=self.app_short_name,
                    description=u'description',
                    hidden=0,
                    category_id=category.id,
                    info=info
                )
            return app

    def create_task_and_run(self,task_info, task_run_info, app, user, order):
        task = Task(app_id = 1, state = '0', info = task_info, n_answers=10)
        task.app = app
        # Taskruns will be assigned randomly to a signed user or an anonymous one
        if random.randint(0,1) == 1:
            task_run = TaskRun(
                    app_id = 1,
                    task_id = 1,
                    user_id = 1,
                    info = task_run_info)
            task_run.user = user
        else:
            task_run = TaskRun(
                    app_id = 1,
                    task_id = 1,
                    user_ip = '127.0.0.%s' % order,
                    info = task_run_info)
        task_run.task = task
        return task, task_run

    def _create_categories(self):
        names = [self.cat_1, self.cat_2]
        db.session.add_all([Category(name=c_name,
                                           short_name=c_name.lower().replace(" ",""),
                                           description=c_name)
                            for c_name in names])
        db.session.commit()

    def redis_flushall(self):
        sentinel.connection.master_for('mymaster').flushall()

class Fixtures:
    fullname = u'T Tester'
    fullname2 = u'T Tester 2'
    email_addr = u'tester@tester.com'
    email_addr2 = u'tester-2@tester.com'
    root_addr = u'root@root.com'
    name = u'tester'
    name2 = u'tester-2'
    root_name = u'root'
    api_key = 'tester'
    api_key_2 = 'tester-2'
    root_api_key = 'root'
    app_name = u'My New App'
    app_short_name = u'test-app'
    password = u'tester'
    root_password = password + 'root'
    cat_1 = 'thinking'
    cat_2 = 'sensing'

    @classmethod
    def create(cls,sched='default'):
        root, user,user2 = Fixtures.create_users()
        info = {
            'total': 150,
            'long_description': 'hello world',
            'task_presenter': 'TaskPresenter',
            'sched': sched
            }

        app = Fixtures.create_app(info)
        app.owner = user

        db.session.add(root)
        db.session.commit()
        db.session.add(user)
        db.session.commit()
        db.session.add(user2)
        db.session.commit()
        db.session.add(app)


        task_info = {
            'question': 'My random question',
            'url': 'my url'
            }
        task_run_info = {
            'answer': u'annakarenina'
            }

        # Create the task and taskruns for the first app
        for i in range (0,10):
             task, task_run = Fixtures.create_task_and_run(task_info, task_run_info, app, user,i)
             db.session.add_all([task, task_run])
        db.session.commit()
        db.session.remove()

    @classmethod
    def create_2(cls,sched='default'):
        root, user,user2 = Fixtures.create_users()

        info = {
            'total': 150,
            'long_description': 'hello world',
            'task_presenter': 'TaskPresenter',
            'sched': sched
            }

        app = Fixtures.create_app(info)
        app.owner = user

        db.session.add_all([root, user, user2, app])

        task_info = {
            'question': 'My random question',
            'url': 'my url'
            }
        task_run_info = {
            'answer': u'annakarenina'
            }

        # Create the task and taskruns for the first app
        task, task_run = Fixtures.create_task_and_run(task_info, task_run_info, app, user,1)
        db.session.add_all([task, task_run])

        db.session.commit()
        db.session.remove()


    @classmethod
    def create_users(cls):
        root = User(
                email_addr = cls.root_addr,
                name = cls.root_name,
                passwd_hash = cls.root_password,
                fullname = cls.fullname,
                api_key = cls.root_api_key)
        root.set_password(cls.root_password)

        user = User(
                email_addr = cls.email_addr,
                name = cls.name,
                passwd_hash = cls.password,
                fullname = cls.fullname,
                api_key = cls.api_key)

        user.set_password(cls.password)

        user2 = User(
                email_addr = cls.email_addr2,
                name = cls.name2,
                passwd_hash = cls.password + "2",
                fullname = cls.fullname2,
                api_key=cls.api_key_2)

        user2.set_password(cls.password)

        return root, user, user2

    @classmethod
    def create_app(cls,info):
        category = db.session.query(Category).first()
        if category is None:
            cls.create_categories()
            category = db.session.query(Category).first()
        app = App(
                name=cls.app_name,
                short_name=cls.app_short_name,
                description=u'description',
                hidden=0,
                category_id=category.id,
                info=info
            )
        return app

    @classmethod
    def create_task_and_run(cls,task_info, task_run_info, app, user, order):
        task = Task(app_id = 1, state = '0', info = task_info, n_answers=10)
        task.app = app
        # Taskruns will be assigned randomly to a signed user or an anonymous one
        if random.randint(0,1) == 1:
            task_run = TaskRun(
                    app_id = 1,
                    task_id = 1,
                    user_id = 1,
                    info = task_run_info)
            task_run.user = user
        else:
            task_run = TaskRun(
                    app_id = 1,
                    task_id = 1,
                    user_ip = '127.0.0.%s' % order,
                    info = task_run_info)
        task_run.task = task
        return task, task_run

    @classmethod
    def create_categories(cls):
        names = [cls.cat_1, cls.cat_2]
        db.session.add_all([Category(name=c_name,
                                           short_name=c_name.lower().replace(" ",""),
                                           description=c_name)
                            for c_name in names])
        db.session.commit()

    @classmethod
    def redis_flushall(cls):
        sentinel.connection.master_for('mymaster').flushall()

def assert_not_raises(exception, call, *args, **kwargs):
    try:
        call(*args, **kwargs)
        assert True
    except exception as ex:
        assert False, str(ex)

########NEW FILE########
__FILENAME__ = app_factory
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from pybossa.model import db
from pybossa.model.app import App
from . import BaseFactory, factory


class AppFactory(BaseFactory):
    FACTORY_FOR = App

    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: u'My App number %d' % n)
    short_name = factory.Sequence(lambda n: u'app%d' % n)
    description = u'App description'
    allow_anonymous_contributors = True
    long_tasks = 0
    hidden = 0
    owner = factory.SubFactory('factories.UserFactory')
    owner_id = factory.LazyAttribute(lambda app: app.owner.id)
    category = factory.SubFactory('factories.CategoryFactory')
    category_id = factory.LazyAttribute(lambda app: app.category.id)

########NEW FILE########
__FILENAME__ = blogpost_factory
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from pybossa.model import db
from pybossa.model.blogpost import Blogpost
from . import BaseFactory, factory


class BlogpostFactory(BaseFactory):
    FACTORY_FOR = Blogpost

    id = factory.Sequence(lambda n: n)
    title = u'Blogpost title'
    body = u'Blogpost body text'
    app = factory.SubFactory('factories.AppFactory')
    app_id = factory.LazyAttribute(lambda blogpost: blogpost.app.id)
    owner = factory.SelfAttribute('app.owner')
    user_id = factory.LazyAttribute(
        lambda blogpost: blogpost.owner.id if blogpost.owner else None)

########NEW FILE########
__FILENAME__ = category_factory
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from pybossa.model import db
from pybossa.model.category import Category
from . import BaseFactory, factory


class CategoryFactory(BaseFactory):
    FACTORY_FOR = Category

    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: 'category_name_%d' % n)
    short_name = factory.Sequence(lambda n: 'category_short_name_%d' % n)
    description = 'Category description for testing purposes'

########NEW FILE########
__FILENAME__ = featured_factory
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from pybossa.model import db
from pybossa.model.featured import Featured
from . import BaseFactory, factory


class FeaturedFactory(BaseFactory):
    FACTORY_FOR = Featured

    id = factory.Sequence(lambda n: n)
    app = factory.SubFactory('factories.AppFactory')
    app_id = factory.LazyAttribute(lambda featured: featured.app.id)

########NEW FILE########
__FILENAME__ = taskrun_factory
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from pybossa.model import db
from pybossa.model.task_run import TaskRun
from . import BaseFactory, factory


class TaskRunFactory(BaseFactory):
    FACTORY_FOR = TaskRun

    id = factory.Sequence(lambda n: n)
    task = factory.SubFactory('factories.TaskFactory')
    task_id = factory.LazyAttribute(lambda task_run: task_run.task.id)
    app = factory.SelfAttribute('task.app')
    app_id = factory.LazyAttribute(lambda task_run: task_run.app.id)
    user = factory.SubFactory('factories.UserFactory')
    user_id = factory.LazyAttribute(lambda task_run: task_run.user.id)


class AnonymousTaskRunFactory(TaskRunFactory):
    user = None
    user_id = None
    user_ip = '127.0.0.1'

########NEW FILE########
__FILENAME__ = task_factory
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from pybossa.model import db
from pybossa.model.task import Task
from . import BaseFactory, factory


class TaskFactory(BaseFactory):
    FACTORY_FOR = Task

    id = factory.Sequence(lambda n: n)
    app = factory.SubFactory('factories.AppFactory')
    app_id = factory.LazyAttribute(lambda task: task.app.id)
    state = u'ongoing'
    quorum = 0
    calibration = 0
    priority_0 = 0.0
    n_answers = 30

########NEW FILE########
__FILENAME__ = user_factory
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from pybossa.model import db
from pybossa.model.user import User
from . import BaseFactory, factory


class UserFactory(BaseFactory):
    FACTORY_FOR = User

    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: u'user%d' % n)
    fullname = factory.Sequence(lambda n: u'User %d' % n)
    email_addr = factory.LazyAttribute(lambda usr: u'%s@test.com' % usr.name)
    locale = u'en'
    admin = False
    privacy_mode = True
    api_key =  factory.Sequence(lambda n: u'api-key%d' % n)

########NEW FILE########
__FILENAME__ = sched
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
from helper import web
from default import model, db


class Helper(web.Helper):
    """Class to help testing the scheduler"""
    def is_task(self, task_id, tasks):
        """Returns True if the task_id is in tasks list"""
        for t in tasks:
            if t.id == task_id:
                return True
        return False

    def is_unique(self, id, items):
        """Returns True if the id is not Unique"""
        copies = 0
        for i in items:
            if type(i) is dict:
                if i['id'] == id:
                    copies = copies + 1
            else:
                if i.id == id:
                    copies = copies + 1
        if copies >= 2:
            return False
        else:
            return True

    def del_task_runs(self, app_id=1):
        """Deletes all TaskRuns for a given app_id"""
        db.session.query(model.task_run.TaskRun).filter_by(app_id=app_id).delete()
        db.session.commit()
        # Update task.state
        db.session.query(model.task.Task).filter_by(app_id=app_id)\
                  .update({"state": "ongoing"})
        db.session.commit()
        db.session.remove()

########NEW FILE########
__FILENAME__ = user
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

class User(object):
    """Class to help testing PyBossa"""
    def __init__(self, **kwargs):
        self.fullname = "John Doe"
        self.username = self.fullname.replace(" ", "").lower()
        self.password = "p4ssw0rd"
        self.email_addr = self.username + "@example.com"

########NEW FILE########
__FILENAME__ = web
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from default import Test, db, Fixtures, with_context
from helper.user import User
from pybossa.model.app import App
from pybossa.model.category import Category
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun


class Helper(Test):
    """Class to help testing the web interface"""

    user = User()

    def html_title(self, title=None):
        """Helper function to create an HTML title"""
        if title is None:
            return "<title>PyBossa</title>"
        else:
            return "<title>PyBossa &middot; %s</title>" % title

    def register(self, method="POST", fullname="John Doe", name="johndoe",
                 password="p4ssw0rd", password2=None, email=None):
        """Helper function to register and sign in a user"""
        if password2 is None:
            password2 = password
        if email is None:
            email = name + '@example.com'
        if method == "POST":
            return self.app.post('/account/register',
                                 data={
                                     'fullname': fullname,
                                     'name': name,
                                     'email_addr': email,
                                     'password': password,
                                     'confirm': password2},
                                 follow_redirects=True)
        else:
            return self.app.get('/account/register', follow_redirects=True)

    def signin(self, method="POST", email="johndoe@example.com", password="p4ssw0rd",
               next=None):
        """Helper function to sign in current user"""
        url = '/account/signin'
        if next is not None:
            url = url + '?next=' + next
        if method == "POST":
            return self.app.post(url, data={'email': email,
                                            'password': password},
                                 follow_redirects=True)
        else:
            return self.app.get(url, follow_redirects=True)

    def profile(self, name="johndoe"):
        """Helper function to check profile of signed in user"""
        url = "/account/%s" % name
        return self.app.get(url, follow_redirects=True)

    def update_profile(self, method="POST", id=1, fullname="John Doe",
                       name="johndoe", locale="es",
                       email_addr="johndoe@example.com",
                       new_name=None,
                       btn='Profile'):
        """Helper function to update the profile of users"""
        url = "/account/%s/update" % name
        if new_name:
            name = new_name
        if (method == "POST"):
            return self.app.post(url,
                                 data={'id': id,
                                       'fullname': fullname,
                                       'name': name,
                                       'locale': locale,
                                       'email_addr': email_addr,
                                       'btn': btn},
                                 follow_redirects=True)
        else:
            return self.app.get(url,
                                follow_redirects=True)

    def signout(self):
        """Helper function to sign out current user"""
        return self.app.get('/account/signout', follow_redirects=True)

    def create_categories(self):
        with self.flask_app.app_context():
            categories = db.session.query(Category).all()
            if len(categories) == 0:
                print "Categories 0"
                print "Creating default ones"
                self._create_categories()


    def new_application(self, method="POST", name="Sample App",
                        short_name="sampleapp", description="Description",
                        long_description=u'Long Description\n================'):
        """Helper function to create an application"""
        if method == "POST":
            self.create_categories()
            return self.app.post("/app/new", data={
                'name': name,
                'short_name': short_name,
                'description': description,
                'long_description': long_description,
            }, follow_redirects=True)
        else:
            return self.app.get("/app/new", follow_redirects=True)

    def new_task(self, appid):
        """Helper function to create tasks for an app"""
        tasks = []
        for i in range(0, 10):
            tasks.append(Task(app_id=appid, state='0', info={}))
        db.session.add_all(tasks)
        db.session.commit()

    def delete_task_runs(self, app_id=1):
        """Deletes all TaskRuns for a given app_id"""
        db.session.query(TaskRun).filter_by(app_id=1).delete()
        db.session.commit()

    def task_settings_scheduler(self, method="POST", short_name='sampleapp',
                                sched="default"):
        """Helper function to modify task scheduler"""
        url = "/app/%s/tasks/scheduler" % short_name
        if method == "POST":
            return self.app.post(url, data={
                'sched': sched,
            }, follow_redirects=True)
        else:
            return self.app.get(url, follow_redirects=True)

    def task_settings_redundancy(self, method="POST", short_name='sampleapp',
                                 n_answers=30):
        """Helper function to modify task redundancy"""
        url = "/app/%s/tasks/redundancy" % short_name
        if method == "POST":
            return self.app.post(url, data={
                'n_answers': n_answers,
            }, follow_redirects=True)
        else:
            return self.app.get(url, follow_redirects=True)

    def task_settings_priority(self, method="POST", short_name='sampleapp',
                                 task_ids="1", priority_0=0.0):
        """Helper function to modify task redundancy"""
        url = "/app/%s/tasks/priority" % short_name
        if method == "POST":
            return self.app.post(url, data={
                'task_ids': task_ids,
                'priority_0': priority_0
            }, follow_redirects=True)
        else:
            return self.app.get(url, follow_redirects=True)

    def delete_application(self, method="POST", short_name="sampleapp"):
        """Helper function to delete an application"""
        if method == "POST":
            return self.app.post("/app/%s/delete" % short_name,
                                 follow_redirects=True)
        else:
            return self.app.get("/app/%s/delete" % short_name,
                                follow_redirects=True)

    def update_application(self, method="POST", short_name="sampleapp", id=1,
                           new_name="Sample App", new_short_name="sampleapp",
                           new_description="Description",
                           new_allow_anonymous_contributors="False",
                           new_category_id="2",
                           new_long_description="Long desc",
                           new_sched="random",
                           new_hidden=False):
        """Helper function to update an application"""
        if method == "POST":
            if new_hidden:
                return self.app.post("/app/%s/update" % short_name,
                                     data={
                                         'id': id,
                                         'name': new_name,
                                         'short_name': new_short_name,
                                         'description': new_description,
                                         'allow_anonymous_contributors': new_allow_anonymous_contributors,
                                         'category_id': new_category_id,
                                         'long_description': new_long_description,
                                         'sched': new_sched,
                                         'hidden': new_hidden,
                                         'btn': 'Save'},
                                     follow_redirects=True)
            else:
                return self.app.post("/app/%s/update" % short_name,
                                     data={'id': id, 'name': new_name,
                                           'short_name': new_short_name,
                                           'allow_anonymous_contributors': new_allow_anonymous_contributors,
                                           'category_id': new_category_id,
                                           'long_description': new_long_description,
                                           'sched': new_sched,
                                           'description': new_description,
                                           'btn': 'Save'
                                           },
                                     follow_redirects=True)
        else:
            return self.app.get("/app/%s/update" % short_name,
                                follow_redirects=True)

########NEW FILE########
__FILENAME__ = test_admin
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import json
from helper import web
from default import db, with_context
from mock import patch
from collections import namedtuple
from bs4 import BeautifulSoup
from pybossa.model.user import User
from pybossa.model.app import App
from pybossa.model.task import Task
from pybossa.model.category import Category


FakeRequest = namedtuple('FakeRequest', ['text', 'status_code', 'headers'])


class TestAdmin(web.Helper):
    pkg_json_not_found = {
        "help": "Return ...",
        "success": False,
        "error": {
            "message": "Not found",
            "__type": "Not Found Error"}}
    # Tests

    @with_context
    def test_00_first_user_is_admin(self):
        """Test ADMIN First Created user is admin works"""
        self.register()
        user = db.session.query(User).get(1)
        assert user.admin == 1, "User ID:1 should be admin, but it is not"

    @with_context
    def test_01_admin_index(self):
        """Test ADMIN index page works"""
        self.register()
        res = self.app.get("/admin", follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "There should be an index page for admin users and apps"
        assert "Settings" in res.data, err_msg
        divs = ['featured-apps', 'users', 'categories', 'users-list']
        for div in divs:
            err_msg = "There should be a button for managing %s" % div
            assert dom.find(id=div) is not None, err_msg

    @with_context
    def test_01_admin_index_anonymous(self):
        """Test ADMIN index page works as anonymous user"""
        res = self.app.get("/admin", follow_redirects=True)
        err_msg = ("The user should not be able to access this page"
                   " but the returned status is %s" % res.data)
        assert "Please sign in to access this page" in res.data, err_msg

    @with_context
    def test_01_admin_index_authenticated(self):
        """Test ADMIN index page works as signed in user"""
        self.register()
        self.signout()
        self.register(name="tester2", email="tester2@tester.com",
                      password="tester")
        res = self.app.get("/admin", follow_redirects=True)
        err_msg = ("The user should not be able to access this page"
                   " but the returned status is %s" % res.status)
        assert "403 FORBIDDEN" in res.status, err_msg

    @with_context
    def test_02_second_user_is_not_admin(self):
        """Test ADMIN Second Created user is NOT admin works"""
        self.register()
        self.signout()
        self.register(name="tester2", email="tester2@tester.com",
                      password="tester")
        self.signout()
        user = db.session.query(User).get(2)
        assert user.admin == 0, "User ID: 2 should not be admin, but it is"

    @with_context
    def test_03_admin_featured_apps_as_admin(self):
        """Test ADMIN featured apps works as an admin user"""
        self.register()
        self.signin()
        res = self.app.get('/admin/featured', follow_redirects=True)
        assert "Manage featured applications" in res.data, res.data

    @with_context
    def test_04_admin_featured_apps_as_anonymous(self):
        """Test ADMIN featured apps works as an anonymous user"""
        res = self.app.get('/admin/featured', follow_redirects=True)
        assert "Please sign in to access this page" in res.data, res.data

    @with_context
    def test_05_admin_featured_apps_as_user(self):
        """Test ADMIN featured apps works as a signed in user"""
        self.register()
        self.signout()
        self.register()
        self.register(name="tester2", email="tester2@tester.com",
                      password="tester")
        res = self.app.get('/admin/featured', follow_redirects=True)
        assert res.status == "403 FORBIDDEN", res.status

    @with_context
    @patch('pybossa.core.uploader.upload_file', return_value=True)
    def test_06_admin_featured_apps_add_remove_app(self, mock):
        """Test ADMIN featured apps add-remove works as an admin user"""
        self.register()
        self.new_application()
        self.update_application()
        # The application is in the system but not in the front page
        res = self.app.get('/', follow_redirects=True)
        assert "Create an App" in res.data,\
            "The application should not be listed in the front page"\
            " as it is not featured"
        # Only apps that have been published can be featured
        self.new_task(1)
        app = db.session.query(App).get(1)
        app.info = dict(task_presenter="something")
        db.session.add(app)
        db.session.commit()
        res = self.app.get('/admin/featured', follow_redirects=True)
        assert "Featured" in res.data, res.data
        assert "Sample App" in res.data, res.data
        # Add it to the Featured list
        res = self.app.post('/admin/featured/1')
        f = json.loads(res.data)
        assert f['id'] == 1, f
        assert f['app_id'] == 1, f
        # Check that it is listed in the front page
        res = self.app.get('/', follow_redirects=True)
        assert "Sample App" in res.data,\
            "The application should be listed in the front page"\
            " as it is featured"
        # A retry should fail
        res = self.app.post('/admin/featured/1')
        err = json.loads(res.data)
        err_msg = "App.id 1 alreay in Featured table"
        assert err['error'] == err_msg, err_msg
        assert err['status_code'] == 415, "Status code should be 415"

        # Remove it again from the Featured list
        res = self.app.delete('/admin/featured/1')
        assert res.status == "204 NO CONTENT", res.status
        # Check that it is not listed in the front page
        res = self.app.get('/', follow_redirects=True)
        assert "Sample App" not in res.data,\
            "The application should not be listed in the front page"\
            " as it is not featured"
        # If we try to delete again, it should return an error
        res = self.app.delete('/admin/featured/1')
        err = json.loads(res.data)
        assert err['status_code'] == 404, "App should not be found"
        err_msg = 'App.id 1 is not in Featured table'
        assert err['error'] == err_msg, err_msg

        # Try with an id that does not exist
        res = self.app.delete('/admin/featured/999')
        err = json.loads(res.data)
        assert err['status_code'] == 404, "App should not be found"
        err_msg = 'App.id 999 not found'
        assert err['error'] == err_msg, err_msg

    @with_context
    @patch('pybossa.core.uploader.upload_file', return_value=True)
    def test_07_admin_featured_apps_add_remove_app_non_admin(self, mock):
        """Test ADMIN featured apps add-remove works as an non-admin user"""
        self.register()
        self.signout()
        self.register(name="John2", email="john2@john.com",
                      password="passwd")
        self.new_application()
        # The application is in the system but not in the front page
        res = self.app.get('/', follow_redirects=True)
        err_msg = ("The application should not be listed in the front page"
                   "as it is not featured")
        assert "Create an App" in res.data, err_msg
        res = self.app.get('/admin/featured', follow_redirects=True)
        err_msg = ("The user should not be able to access this page"
                   " but the returned status is %s" % res.status)
        assert "403 FORBIDDEN" in res.status, err_msg
        # Try to add the app to the featured list
        res = self.app.post('/admin/featured/1')
        err_msg = ("The user should not be able to POST to this page"
                   " but the returned status is %s" % res.status)
        assert "403 FORBIDDEN" in res.status, err_msg
        # Try to remove it again from the Featured list
        res = self.app.delete('/admin/featured/1')
        err_msg = ("The user should not be able to DELETE to this page"
                   " but the returned status is %s" % res.status)
        assert "403 FORBIDDEN" in res.status, err_msg

    @with_context
    @patch('pybossa.core.uploader.upload_file', return_value=True)
    def test_08_admin_featured_apps_add_remove_app_anonymous(self, mock):
        """Test ADMIN featured apps add-remove works as an anonymous user"""
        self.register()
        self.new_application()
        self.signout()
        # The application is in the system but not in the front page
        res = self.app.get('/', follow_redirects=True)
        assert "Create an App" in res.data,\
            "The application should not be listed in the front page"\
            " as it is not featured"
        res = self.app.get('/admin/featured', follow_redirects=True)
        err_msg = ("The user should not be able to access this page"
                   " but the returned status is %s" % res.data)
        assert "Please sign in to access this page" in res.data, err_msg

        # Try to add the app to the featured list
        res = self.app.post('/admin/featured/1', follow_redirects=True)
        err_msg = ("The user should not be able to POST to this page"
                   " but the returned status is %s" % res.data)
        assert "Please sign in to access this page" in res.data, err_msg

        # Try to remove it again from the Featured list
        res = self.app.delete('/admin/featured/1', follow_redirects=True)
        err_msg = ("The user should not be able to DELETE to this page"
                   " but the returned status is %s" % res.data)
        assert "Please sign in to access this page" in res.data, err_msg

    @with_context
    def test_09_admin_users_as_admin(self):
        """Test ADMIN users works as an admin user"""
        self.register()
        res = self.app.get('/admin/users', follow_redirects=True)
        assert "Manage Admin Users" in res.data, res.data

    @with_context
    def test_10_admin_user_not_listed(self):
        """Test ADMIN users does not list himself works"""
        self.register()
        res = self.app.get('/admin/users', follow_redirects=True)
        assert "Manage Admin Users" in res.data, res.data
        assert "Current Users with Admin privileges" not in res.data, res.data
        assert "John" not in res.data, res.data

    @with_context
    def test_11_admin_user_not_listed_in_search(self):
        """Test ADMIN users does not list himself in the search works"""
        self.register()
        data = {'user': 'john'}
        res = self.app.post('/admin/users', data=data, follow_redirects=True)
        assert "Manage Admin Users" in res.data, res.data
        assert "Current Users with Admin privileges" not in res.data, res.data
        assert "John" not in res.data, res.data

    @with_context
    def test_12_admin_user_search(self):
        """Test ADMIN users search works"""
        # Create two users
        self.register()
        self.signout()
        self.register(fullname="Juan Jose", name="juan",
                      email="juan@juan.com", password="juan")
        self.signout()
        # Signin with admin user
        self.signin()
        data = {'user': 'juan'}
        res = self.app.post('/admin/users', data=data, follow_redirects=True)
        assert "Juan Jose" in res.data, "username should be searchable"
        # Check with uppercase
        data = {'user': 'JUAN'}
        res = self.app.post('/admin/users', data=data, follow_redirects=True)
        err_msg = "username search should be case insensitive"
        assert "Juan Jose" in res.data, err_msg
        # Search fullname
        data = {'user': 'Jose'}
        res = self.app.post('/admin/users', data=data, follow_redirects=True)
        assert "Juan Jose" in res.data, "fullname should be searchable"
        # Check with uppercase
        data = {'user': 'JOsE'}
        res = self.app.post('/admin/users', data=data, follow_redirects=True)
        err_msg = "fullname search should be case insensitive"
        assert "Juan Jose" in res.data, err_msg
        # Warning should be issued for non-found users
        data = {'user': 'nothingExists'}
        res = self.app.post('/admin/users', data=data, follow_redirects=True)
        warning = ("We didn't find a user matching your query: <strong>%s</strong>" %
                   data['user'])
        err_msg = "A flash message should be returned for non-found users"
        assert warning in res.data, err_msg

    @with_context
    def test_13_admin_user_add_del(self):
        """Test ADMIN add/del user to admin group works"""
        self.register()
        self.signout()
        self.register(fullname="Juan Jose", name="juan",
                      email="juan@juan.com", password="juan")
        self.signout()
        # Signin with admin user
        self.signin()
        # Add user.id=1000 (it does not exist)
        res = self.app.get("/admin/users/add/1000", follow_redirects=True)
        err = json.loads(res.data)
        assert res.status_code == 404, res.status_code
        assert err['error'] == "User not found", err
        assert err['status_code'] == 404, err


        # Add user.id=2 to admin group
        res = self.app.get("/admin/users/add/2", follow_redirects=True)
        assert "Current Users with Admin privileges" in res.data
        err_msg = "User.id=2 should be listed as an admin"
        assert "Juan Jose" in res.data, err_msg
        # Remove user.id=2 from admin group
        res = self.app.get("/admin/users/del/2", follow_redirects=True)
        assert "Current Users with Admin privileges" not in res.data
        err_msg = "User.id=2 should be listed as an admin"
        assert "Juan Jose" not in res.data, err_msg
        # Delete a non existant user should return an error
        res = self.app.get("/admin/users/del/5000", follow_redirects=True)
        err = json.loads(res.data)
        assert res.status_code == 404, res.status_code
        assert err['error'] == "User.id not found", err
        assert err['status_code'] == 404, err

    @with_context
    def test_14_admin_user_add_del_anonymous(self):
        """Test ADMIN add/del user to admin group works as anonymous"""
        self.register()
        self.signout()
        self.register(fullname="Juan Jose", name="juan",
                      email="juan@juan.com", password="juan")
        self.signout()
        # Add user.id=2 to admin group
        res = self.app.get("/admin/users/add/2", follow_redirects=True)
        err_msg = "User should be redirected to signin"
        assert "Please sign in to access this page" in res.data, err_msg
        # Remove user.id=2 from admin group
        res = self.app.get("/admin/users/del/2", follow_redirects=True)
        err_msg = "User should be redirected to signin"
        assert "Please sign in to access this page" in res.data, err_msg

    @with_context
    def test_15_admin_user_add_del_authenticated(self):
        """Test ADMIN add/del user to admin group works as authenticated"""
        self.register()
        self.signout()
        self.register(fullname="Juan Jose", name="juan",
                      email="juan@juan.com", password="juan")
        self.signout()
        self.register(fullname="Juan Jose2", name="juan2",
                      email="juan2@juan.com", password="juan2")
        self.signout()
        self.signin(email="juan2@juan.com", password="juan2")
        # Add user.id=2 to admin group
        res = self.app.get("/admin/users/add/2", follow_redirects=True)
        assert res.status == "403 FORBIDDEN",\
            "This action should be forbidden, not enought privileges"
        # Remove user.id=2 from admin group
        res = self.app.get("/admin/users/del/2", follow_redirects=True)
        assert res.status == "403 FORBIDDEN",\
            "This action should be forbidden, not enought privileges"

    @with_context
    def test_16_admin_user_export(self):
        """Test ADMIN user list export works as admin"""
        self.register()
        self.signout()
        self.register(fullname="Juan Jose", name="juan",
                      email="juan@juan.com", password="juan")
        self.signout()
        self.register(fullname="Juan Jose2", name="juan2",
                      email="juan2@juan.com", password="juan2")
        self.signin()
        # The user is redirected to '/admin/' if no format is specified
        res = self.app.get('/admin/users/export', follow_redirects=True)
        assert 'Featured Applications' in res.data, res.data
        assert 'Administrators' in res.data, res.data
        res = self.app.get('/admin/users/export?firmit=', follow_redirects=True)
        assert 'Featured Applications' in res.data, res.data
        assert 'Administrators' in res.data, res.data
        # A 415 error is raised if the format is not supported (is not either json or csv)
        res = self.app.get('/admin/users/export?format=bad',
                            follow_redirects=True)
        assert res.status_code == 415, res.status_code
        # JSON is a valid format for exports
        res = self.app.get('/admin/users/export?format=json',
                            follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert res.mimetype == 'application/json', res.mimetype
        #CSV is a valid format for exports
        res = self.app.get('/admin/users/export?format=csv',
                            follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert res.mimetype == 'text/csv', res.mimetype

    @with_context
    def test_17_admin_user_export_anonymous(self):
        """Test ADMIN user list export works as anonymous user"""
        self.register()
        self.signout()

        # Whichever the args of the request are, the user is redirected to login
        res = self.app.get('/admin/users/export', follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Anonymous users should be redirected to sign in"
        assert dom.find(id='signin') is not None, err_msg
        res = self.app.get('/admin/users/export?firmit=', follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Anonymous users should be redirected to sign in"
        assert dom.find(id='signin') is not None, err_msg
        res = self.app.get('/admin/users/export?format=bad',
                            follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Anonymous users should be redirected to sign in"
        assert dom.find(id='signin') is not None, err_msg
        res = self.app.get('/admin/users/export?format=json',
                            follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Anonymous users should be redirected to sign in"
        assert dom.find(id='signin') is not None, err_msg

    @with_context
    def test_18_admin_user_export_authenticated(self):
        """Test ADMIN user list export works as authenticated non-admin user"""
        self.register()
        self.signout()
        self.register(fullname="Juan Jose", name="juan",
                      email="juan@juan.com", password="juan")

        # No matter what params in the request, Forbidden is raised
        res = self.app.get('/admin/users/export', follow_redirects=True)
        assert res.status_code == 403, res.status_code
        res = self.app.get('/admin/users/export?firmit=', follow_redirects=True)
        assert res.status_code == 403, res.status_code
        res = self.app.get('/admin/users/export?format=bad',
                            follow_redirects=True)
        assert res.status_code == 403, res.status_code
        res = self.app.get('/admin/users/export?format=json',
                            follow_redirects=True)
        assert res.status_code == 403, res.status_code

    @with_context
    @patch('pybossa.ckan.requests.get')
    @patch('pybossa.core.uploader.upload_file', return_value=True)
    def test_19_admin_update_app(self, Mock, Mock2):
        """Test ADMIN can update an app that belongs to another user"""
        html_request = FakeRequest(json.dumps(self.pkg_json_not_found), 200,
                                   {'content-type': 'application/json'})
        Mock.return_value = html_request
        self.register()
        self.signout()
        self.register(fullname="Juan Jose", name="juan",
                      email="juan@juan.com", password="juan")
        self.new_application()
        self.signout()
        # Sign in with the root user
        self.signin()
        res = self.app.get('/app/sampleapp/settings')
        err_msg = "Admin users should be able to get the settings page for any app"
        assert res.status == "200 OK", err_msg
        res = self.update_application(method="GET")
        assert "Update the application" in res.data,\
            "The app should be updated by admin users"
        res = self.update_application(new_name="Root",
                                      new_short_name="rootsampleapp")
        res = self.app.get('/app/rootsampleapp', follow_redirects=True)
        assert "Root" in res.data, "The app should be updated by admin users"

        app = db.session.query(App)\
                .filter_by(short_name="rootsampleapp").first()
        juan = db.session.query(User).filter_by(name="juan").first()
        assert app.owner_id == juan.id, "Owner_id should be: %s" % juan.id
        assert app.owner_id != 1, "The owner should be not updated"
        res = self.update_application(short_name="rootsampleapp",
                                      new_short_name="sampleapp",
                                      new_long_description="New Long Desc")
        res = self.app.get('/app/sampleapp', follow_redirects=True)
        err_msg = "The long description should have been updated"
        assert "New Long Desc" in res.data, err_msg

    @with_context
    @patch('pybossa.core.uploader.upload_file', return_value=True)
    def test_20_admin_delete_app(self, mock):
        """Test ADMIN can delete an app that belongs to another user"""
        self.register()
        self.signout()
        self.register(fullname="Juan Jose", name="juan",
                      email="juan@juan.com", password="juan")
        self.new_application()
        self.signout()
        # Sign in with the root user
        self.signin()
        res = self.delete_application(method="GET")
        assert "Yes, delete it" in res.data,\
            "The app should be deleted by admin users"
        res = self.delete_application()
        err_msg = "The app should be deleted by admin users"
        assert "Application deleted!" in res.data, err_msg

    @with_context
    def test_21_admin_delete_tasks(self):
        """Test ADMIN can delete an app's tasks that belongs to another user"""
        # Admin
        self.create()
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        assert len(tasks) > 0, "len(app.tasks) > 0"
        res = self.signin(email=u'root@root.com', password=u'tester' + 'root')
        res = self.app.get('/app/test-app/tasks/delete', follow_redirects=True)
        err_msg = "Admin user should get 200 in GET"
        assert res.status_code == 200, err_msg
        res = self.app.post('/app/test-app/tasks/delete', follow_redirects=True)
        err_msg = "Admin should get 200 in POST"
        assert res.status_code == 200, err_msg
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        assert len(tasks) == 0, "len(app.tasks) != 0"

    @with_context
    def test_22_admin_list_categories(self):
        """Test ADMIN list categories works"""
        self.create()
        # Anonymous user
        url = '/admin/categories'
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Anonymous users should be redirected to sign in"
        assert dom.find(id='signin') is not None, err_msg

        # Authenticated user but not admin
        self.signin(email=self.email_addr2, password=self.password)
        res = self.app.get(url, follow_redirects=True)
        err_msg = "Non-Admin users should get 403"
        assert res.status_code == 403, err_msg
        self.signout()

        # Admin user
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Admin users should be get a list of Categories"
        assert dom.find(id='categories') is not None, err_msg

    @with_context
    def test_23_admin_add_category(self):
        """Test ADMIN add category works"""
        self.create()
        category = {'name': 'cat', 'short_name': 'cat',
                    'description': 'description'}
        # Anonymous user
        url = '/admin/categories'
        res = self.app.post(url, data=category, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Anonymous users should be redirected to sign in"
        assert dom.find(id='signin') is not None, err_msg

        # Authenticated user but not admin
        self.signin(email=self.email_addr2, password=self.password)
        res = self.app.post(url, data=category, follow_redirects=True)
        err_msg = "Non-Admin users should get 403"
        assert res.status_code == 403, err_msg
        self.signout()

        # Admin
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.post(url, data=category, follow_redirects=True)
        err_msg = "Category should be added"
        assert "Category added" in res.data, err_msg
        assert category['name'] in res.data, err_msg

        category = {'name': 'cat', 'short_name': 'cat',
                    'description': 'description'}

        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.post(url, data=category, follow_redirects=True)
        err_msg = "Category form validation should work"
        assert "Please correct the errors" in res.data, err_msg


    @with_context
    def test_24_admin_update_category(self):
        """Test ADMIN update category works"""
        self.create()
        obj = db.session.query(Category).get(1)
        _name = obj.name
        category = obj.dictize()

        # Anonymous user GET
        url = '/admin/categories/update/%s' % obj.id
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Anonymous users should be redirected to sign in"
        assert dom.find(id='signin') is not None, err_msg
        # Anonymous user POST
        res = self.app.post(url, data=category, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Anonymous users should be redirected to sign in"
        assert dom.find(id='signin') is not None, err_msg

        # Authenticated user but not admin GET
        self.signin(email=self.email_addr2, password=self.password)
        res = self.app.post(url, follow_redirects=True)
        err_msg = "Non-Admin users should get 403"
        assert res.status_code == 403, err_msg
        # Authenticated user but not admin POST
        res = self.app.post(url, data=category, follow_redirects=True)
        err_msg = "Non-Admin users should get 403"
        assert res.status_code == 403, err_msg
        self.signout()

        # Admin GET
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        err_msg = "Category should be listed for admin user"
        assert _name in res.data, err_msg
        # Check 404
        url_404 = '/admin/categories/update/5000'
        res = self.app.get(url_404, follow_redirects=True)
        assert res.status_code == 404, res.status_code
        # Admin POST
        res = self.app.post(url, data=category, follow_redirects=True)
        err_msg = "Category should be updated"
        assert "Category updated" in res.data, err_msg
        assert category['name'] in res.data, err_msg
        updated_category = db.session.query(Category).get(obj.id)
        assert updated_category.name == obj.name, err_msg
        # With not valid form
        category['name'] = None
        res = self.app.post(url, data=category, follow_redirects=True)
        assert "Please correct the errors" in res.data, err_msg

    @with_context
    def test_25_admin_delete_category(self):
        """Test ADMIN delete category works"""
        self.create()
        obj = db.session.query(Category).get(2)
        category = obj.dictize()

        # Anonymous user GET
        url = '/admin/categories/del/%s' % obj.id
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Anonymous users should be redirected to sign in"
        assert dom.find(id='signin') is not None, err_msg
        # Anonymous user POST
        res = self.app.post(url, data=category, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Anonymous users should be redirected to sign in"
        assert dom.find(id='signin') is not None, err_msg

        # Authenticated user but not admin GET
        self.signin(email=self.email_addr2, password=self.password)
        res = self.app.post(url, follow_redirects=True)
        err_msg = "Non-Admin users should get 403"
        assert res.status_code == 403, err_msg
        # Authenticated user but not admin POST
        res = self.app.post(url, data=category, follow_redirects=True)
        err_msg = "Non-Admin users should get 403"
        assert res.status_code == 403, err_msg
        self.signout()

        # Admin GET
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        err_msg = "Category should be listed for admin user"
        assert category['name'] in res.data, err_msg
        # Admin POST
        res = self.app.post(url, data=category, follow_redirects=True)
        err_msg = "Category should be deleted"
        assert "Category deleted" in res.data, err_msg
        assert category['name'] not in res.data, err_msg
        output = db.session.query(Category).get(obj.id)
        assert output is None, err_msg
        # Non existant category
        category['id'] = 5000
        url = '/admin/categories/del/5000'
        res = self.app.post(url, data=category, follow_redirects=True)
        assert res.status_code == 404, res.status_code

        # Now try to delete the only available Category
        obj = db.session.query(Category).first()
        url = '/admin/categories/del/%s' % obj.id
        category = obj.dictize()
        res = self.app.post(url, data=category, follow_redirects=True)
        print res.data
        err_msg = "Category should not be deleted"
        assert "Category deleted" not in res.data, err_msg
        assert category['name'] in res.data, err_msg
        output = db.session.query(Category).get(obj.id)
        assert output.id == category['id'], err_msg

########NEW FILE########
__FILENAME__ = test_admin_export_users
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import json
import StringIO
from default import with_context
from pybossa.util import unicode_csv_reader
from helper import web



class TestExportUsers(web.Helper):

    exportable_attributes = ('id', 'name', 'fullname', 'email_addr',
                             'created', 'locale', 'admin')

    @with_context
    def test_json_contains_all_attributes(self):
        self.register()

        res = self.app.get('/admin/users/export?format=json',
                            follow_redirects=True)
        data = json.loads(res.data)

        for attribute in self.exportable_attributes:
            assert attribute in data[0], data

    @with_context
    def test_json_returns_all_users(self):
        self.register(fullname="Manolita")
        self.signout()
        self.register(fullname="Juan Jose", name="juan",
                      email="juan@juan.com", password="juan")
        self.signout()
        self.register(fullname="Juan Jose2", name="juan2",
                      email="juan2@juan.com", password="juan2")
        self.signin()

        res = self.app.get('/admin/users/export?format=json',
                            follow_redirects=True)
        data = res.data
        json_data = json.loads(data)

        assert "Juan Jose" in data, data
        assert "Manolita" in data, data
        assert "Juan Jose2" in data, data
        assert len(json_data) == 3

    @with_context
    def test_csv_contains_all_attributes(self):
        self.register()

        res = self.app.get('/admin/users/export?format=csv',
                            follow_redirects=True)
        data = res.data

        for attribute in self.exportable_attributes:
            assert attribute in data, data

    @with_context
    def test_csv_returns_all_users(self):
        self.register(fullname="Manolita")
        self.signout()
        self.register(fullname="Juan Jose", name="juan",
                      email="juan@juan.com", password="juan")
        self.signout()
        self.register(fullname="Juan Jose2", name="juan2",
                      email="juan2@juan.com", password="juan2")
        self.signin()

        res = self.app.get('/admin/users/export?format=csv',
                            follow_redirects=True)
        data = res.data
        csv_content = StringIO.StringIO(data)
        csvreader = unicode_csv_reader(csv_content)

        # number of users is -1 because the first row in csv are the headers
        number_of_users = -1
        for row in csvreader:
            number_of_users += 1

        assert number_of_users == 3, number_of_users





########NEW FILE########
__FILENAME__ = test_api_common
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import json
from base import with_context
from nose.tools import assert_equal, assert_raises
from test_api import TestAPI

from factories import AppFactory, TaskFactory, TaskRunFactory, UserFactory



class TestApiCommon(TestAPI):


    @with_context
    def test_limits_query(self):
        """Test API GET limits works"""
        owner = UserFactory.create()
        for i in range(30):
            app = AppFactory.create(owner=owner)
            task = TaskFactory(app=app)
            taskrun = TaskRunFactory(task=task)

        res = self.app.get('/api/app')
        data = json.loads(res.data)
        assert len(data) == 20, len(data)

        res = self.app.get('/api/app?limit=10')
        data = json.loads(res.data)
        assert len(data) == 10, len(data)

        res = self.app.get('/api/app?limit=10&offset=10')
        data = json.loads(res.data)
        assert len(data) == 10, len(data)
        assert data[0].get('name') == 'My App number 11', data[0]

        res = self.app.get('/api/task')
        data = json.loads(res.data)
        assert len(data) == 20, len(data)

        res = self.app.get('/api/taskrun')
        data = json.loads(res.data)
        assert len(data) == 20, len(data)

        UserFactory.create_batch(30)

        res = self.app.get('/api/user')
        data = json.loads(res.data)
        assert len(data) == 20, len(data)

        res = self.app.get('/api/user?limit=10')
        data = json.loads(res.data)
        print data
        assert len(data) == 10, len(data)

        res = self.app.get('/api/user?limit=10&offset=10')
        data = json.loads(res.data)
        assert len(data) == 10, len(data)
        assert data[0].get('name') == 'user11', data


    @with_context
    def test_get_query_with_api_key(self):
        """ Test API GET query with an API-KEY"""
        users = UserFactory.create_batch(3)
        app = AppFactory.create(owner=users[0], info={'total': 150})
        task = TaskFactory.create(app=app, info={'url': 'my url'})
        taskrun = TaskRunFactory.create(task=task, user=users[0],
                                        info={'answer': 'annakarenina'})
        for endpoint in self.endpoints:
            url = '/api/' + endpoint + '?api_key=' + users[1].api_key
            res = self.app.get(url)
            data = json.loads(res.data)

            if endpoint == 'app':
                assert len(data) == 1, data
                app = data[0]
                assert app['info']['total'] == 150, data
                assert res.mimetype == 'application/json', res

            if endpoint == 'task':
                assert len(data) == 1, data
                task = data[0]
                assert task['info']['url'] == 'my url', data
                assert res.mimetype == 'application/json', res

            if endpoint == 'taskrun':
                assert len(data) == 1, data
                taskrun = data[0]
                assert taskrun['info']['answer'] == 'annakarenina', data
                assert res.mimetype == 'application/json', res

            if endpoint == 'user':
                assert len(data) == 3, data
                user = data[0]
                assert user['name'] == 'user1', data
                assert res.mimetype == 'application/json', res


    @with_context
    def test_query_search_wrongfield(self):
        """ Test API query search works"""
        # Test first a non-existant field for all end-points
        for endpoint in self.endpoints:
            res = self.app.get("/api/%s?wrongfield=value" % endpoint)
            err = json.loads(res.data)
            assert res.status_code == 415, err
            assert err['status'] == 'failed', err
            assert err['action'] == 'GET', err
            assert err['exception_cls'] == 'AttributeError', err


    @with_context
    def test_query_sql_injection(self):
        """Test API SQL Injection is not allowed works"""

        q = '1%3D1;SELECT%20*%20FROM%20task%20WHERE%201=1'
        res = self.app.get('/api/task?' + q)
        error = json.loads(res.data)
        assert res.status_code == 415, error
        assert error['action'] == 'GET', error
        assert error['status'] == 'failed', error
        assert error['target'] == 'task', error

        q = 'app_id=1%3D1;SELECT%20*%20FROM%20task%20WHERE%201'
        res = self.app.get('/api/apappp?' + q)
        assert res.status_code == 404, res.data

        q = 'app_id=1%3D1;SELECT%20*%20FROM%20task%20WHERE%201'
        res = self.app.get('/api/' + q)
        assert res.status_code == 404, res.data

        q = 'app_id=1%3D1;SELECT%20*%20FROM%20task%20WHERE%201'
        res = self.app.get('/api' + q)
        assert res.status_code == 404, res.data

########NEW FILE########
__FILENAME__ = test_app_api
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import json
from mock import patch
from base import db, with_context
from nose.tools import assert_equal, assert_raises
from test_api import TestAPI
from pybossa.model.app import App
from pybossa.model.user import User
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun

from factories import AppFactory, TaskFactory, TaskRunFactory, UserFactory


class TestAppAPI(TestAPI):

    @with_context
    def test_app_query(self):
        """ Test API App query"""
        AppFactory.create(info={'total': 150})
        res = self.app.get('/api/app')
        data = json.loads(res.data)
        assert len(data) == 1, data
        app = data[0]
        assert app['info']['total'] == 150, data

        # The output should have a mime-type: application/json
        assert res.mimetype == 'application/json', res

        # Test a non-existant ID
        res = self.app.get('/api/app/3434209')
        err = json.loads(res.data)
        assert res.status_code == 404, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'app', err
        assert err['exception_cls'] == 'NotFound', err
        assert err['action'] == 'GET', err

    @with_context
    def test_query_app(self):
        """Test API query for app endpoint works"""
        AppFactory.create(short_name='test-app', name='My New App')
        # Test for real field
        res = self.app.get("/api/app?short_name=test-app")
        data = json.loads(res.data)
        # Should return one result
        assert len(data) == 1, data
        # Correct result
        assert data[0]['short_name'] == 'test-app', data

        # Valid field but wrong value
        res = self.app.get("/api/app?short_name=wrongvalue")
        data = json.loads(res.data)
        assert len(data) == 0, data

        # Multiple fields
        res = self.app.get('/api/app?short_name=test-app&name=My New App')
        data = json.loads(res.data)
        # One result
        assert len(data) == 1, data
        # Correct result
        assert data[0]['short_name'] == 'test-app', data
        assert data[0]['name'] == 'My New App', data


    @with_context
    def test_app_post(self):
        """Test API App creation and auth"""
        users = UserFactory.create_batch(2)
        name = u'XXXX Project'
        data = dict(
            name=name,
            short_name='xxxx-project',
            description='description',
            owner_id=1,
            long_description=u'Long Description\n================')
        data = json.dumps(data)
        # no api-key
        res = self.app.post('/api/app', data=data)
        assert_equal(res.status, '401 UNAUTHORIZED',
                     'Should not be allowed to create')
        # now a real user
        res = self.app.post('/api/app?api_key=' + users[1].api_key,
                            data=data)
        out = db.session.query(App).filter_by(name=name).one()
        assert out, out
        assert_equal(out.short_name, 'xxxx-project'), out
        assert_equal(out.owner.name, 'user2')
        id_ = out.id
        db.session.remove()

        # now a real user with headers auth
        headers = [('Authorization', users[1].api_key)]
        new_app = dict(
            name=name + '2',
            short_name='xxxx-project2',
            description='description2',
            owner_id=1,
            long_description=u'Long Description\n================')
        new_app = json.dumps(new_app)
        res = self.app.post('/api/app', headers=headers,
                            data=new_app)
        out = db.session.query(App).filter_by(name=name + '2').one()
        assert out, out
        assert_equal(out.short_name, 'xxxx-project2'), out
        assert_equal(out.owner.name, 'user2')
        id_ = out.id
        db.session.remove()

        # test re-create should fail
        res = self.app.post('/api/app?api_key=' + users[1].api_key,
                            data=data)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'POST', err
        assert err['exception_cls'] == "IntegrityError", err

        # test create with non-allowed fields should fail
        data = dict(name='fail', short_name='fail', link='hateoas', wrong=15)
        res = self.app.post('/api/app?api_key=' + users[1].api_key,
                            data=data)
        err = json.loads(res.data)
        err_msg = "ValueError exception should be raised"
        assert res.status_code == 415, err
        assert err['action'] == 'POST', err
        assert err['status'] == 'failed', err
        assert err['exception_cls'] == "ValueError", err_msg
        # Now with a JSON object but not valid
        data = json.dumps(data)
        res = self.app.post('/api/app?api_key=' + users[1].api_key,
                            data=data)
        err = json.loads(res.data)
        err_msg = "TypeError exception should be raised"
        assert err['action'] == 'POST', err_msg
        assert err['status'] == 'failed', err_msg
        assert err['exception_cls'] == "TypeError", err_msg
        assert res.status_code == 415, err_msg

        # test update
        data = {'name': 'My New Title'}
        datajson = json.dumps(data)
        ## anonymous
        res = self.app.put('/api/app/%s' % id_, data=data)
        error_msg = 'Anonymous should not be allowed to update'
        assert_equal(res.status, '401 UNAUTHORIZED', error_msg)
        error = json.loads(res.data)
        assert error['status'] == 'failed', error
        assert error['action'] == 'PUT', error
        assert error['exception_cls'] == 'Unauthorized', error

        ### real user but not allowed as not owner!
        non_owner = UserFactory.create()
        url = '/api/app/%s?api_key=%s' % (id_, non_owner.api_key)
        res = self.app.put(url, data=datajson)
        error_msg = 'Should not be able to update apps of others'
        assert_equal(res.status, '403 FORBIDDEN', error_msg)
        error = json.loads(res.data)
        assert error['status'] == 'failed', error
        assert error['action'] == 'PUT', error
        assert error['exception_cls'] == 'Forbidden', error

        res = self.app.put('/api/app/%s?api_key=%s' % (id_, users[1].api_key),
                           data=datajson)

        assert_equal(res.status, '200 OK', res.data)
        out2 = db.session.query(App).get(id_)
        assert_equal(out2.name, data['name'])
        out = json.loads(res.data)
        assert out.get('status') is None, error
        assert out.get('id') == id_, error

        # With wrong id
        res = self.app.put('/api/app/5000?api_key=%s' % users[1].api_key,
                           data=datajson)
        assert_equal(res.status, '404 NOT FOUND', res.data)
        error = json.loads(res.data)
        assert error['status'] == 'failed', error
        assert error['action'] == 'PUT', error
        assert error['exception_cls'] == 'NotFound', error

        # With fake data
        data['algo'] = 13
        datajson = json.dumps(data)
        res = self.app.put('/api/app/%s?api_key=%s' % (id_, users[1].api_key),
                           data=datajson)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'TypeError', err

        # With empty fields
        data.pop('algo')
        data['name'] = None
        datajson = json.dumps(data)
        res = self.app.put('/api/app/%s?api_key=%s' % (id_, users[1].api_key),
                           data=datajson)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'IntegrityError', err

        data['name'] = ''
        datajson = json.dumps(data)
        res = self.app.put('/api/app/%s?api_key=%s' % (id_, users[1].api_key),
                           data=datajson)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'IntegrityError', err

        data['name'] = 'something'
        data['short_name'] = ''
        datajson = json.dumps(data)
        res = self.app.put('/api/app/%s?api_key=%s' % (id_, users[1].api_key),
                           data=datajson)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'IntegrityError', err


        # With not JSON data
        datajson = data
        res = self.app.put('/api/app/%s?api_key=%s' % (id_, users[1].api_key),
                           data=datajson)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'ValueError', err

        # With wrong args in the URL
        data = dict(
            name=name,
            short_name='xxxx-project',
            long_description=u'Long Description\n================')

        datajson = json.dumps(data)
        res = self.app.put('/api/app/%s?api_key=%s&search=select1' % (id_, users[1].api_key),
                           data=datajson)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'AttributeError', err

        # test delete
        ## anonymous
        res = self.app.delete('/api/app/%s' % id_, data=data)
        error_msg = 'Anonymous should not be allowed to delete'
        assert_equal(res.status, '401 UNAUTHORIZED', error_msg)
        error = json.loads(res.data)
        assert error['status'] == 'failed', error
        assert error['action'] == 'DELETE', error
        assert error['target'] == 'app', error
        ### real user but not allowed as not owner!
        url = '/api/app/%s?api_key=%s' % (id_, non_owner.api_key)
        res = self.app.delete(url, data=datajson)
        error_msg = 'Should not be able to delete apps of others'
        assert_equal(res.status, '403 FORBIDDEN', error_msg)
        error = json.loads(res.data)
        assert error['status'] == 'failed', error
        assert error['action'] == 'DELETE', error
        assert error['target'] == 'app', error

        url = '/api/app/%s?api_key=%s' % (id_, users[1].api_key)
        res = self.app.delete(url, data=datajson)

        assert_equal(res.status, '204 NO CONTENT', res.data)

        # delete an app that does not exist
        url = '/api/app/5000?api_key=%s' % users[1].api_key
        res = self.app.delete(url, data=datajson)
        error = json.loads(res.data)
        assert res.status_code == 404, error
        assert error['status'] == 'failed', error
        assert error['action'] == 'DELETE', error
        assert error['target'] == 'app', error
        assert error['exception_cls'] == 'NotFound', error

        # delete an app that does not exist
        url = '/api/app/?api_key=%s' % users[1].api_key
        res = self.app.delete(url, data=datajson)
        assert res.status_code == 404, error

    @with_context
    def test_admin_app_post(self):
        """Test API App update/delete for ADMIN users"""
        admin = UserFactory.create()
        assert admin.admin
        user = UserFactory.create()
        app = AppFactory.create(owner=user, short_name='xxxx-project')

        # test update
        data = {'name': 'My New Title'}
        datajson = json.dumps(data)
        ### admin user but not owner!
        url = '/api/app/%s?api_key=%s' % (app.id, admin.api_key)
        res = self.app.put(url, data=datajson)

        assert_equal(res.status, '200 OK', res.data)
        out2 = db.session.query(App).get(app.id)
        assert_equal(out2.name, data['name'])

        # PUT with not JSON data
        res = self.app.put(url, data=data)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'app', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'ValueError', err

        # PUT with not allowed args
        res = self.app.put(url + "&foo=bar", data=json.dumps(data))
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'app', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'AttributeError', err

        # PUT with fake data
        data['wrongfield'] = 13
        res = self.app.put(url, data=json.dumps(data))
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'app', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'TypeError', err
        data.pop('wrongfield')

        # test delete
        url = '/api/app/%s?api_key=%s' % (app.id, admin.api_key)
        # DELETE with not allowed args
        res = self.app.delete(url + "&foo=bar", data=json.dumps(data))
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'app', err
        assert err['action'] == 'DELETE', err
        assert err['exception_cls'] == 'AttributeError', err

        ### DELETE success real user  not owner!
        res = self.app.delete(url, data=json.dumps(data))
        assert_equal(res.status, '204 NO CONTENT', res.data)

    @with_context
    def test_user_progress_anonymous(self):
        """Test API userprogress as anonymous works"""
        user = UserFactory.create()
        app = AppFactory.create(owner=user)
        tasks = TaskFactory.create_batch(2, app=app)
        for task in tasks:
            taskruns = TaskRunFactory.create_batch(2, task=task, user=user)
        taskruns = db.session.query(TaskRun)\
                     .filter(TaskRun.app_id == app.id)\
                     .filter(TaskRun.user_id == user.id)\
                     .all()

        res = self.app.get('/api/app/1/userprogress', follow_redirects=True)
        data = json.loads(res.data)

        error_msg = "The reported total number of tasks is wrong"
        assert len(tasks) == data['total'], error_msg

        error_msg = "The reported number of done tasks is wrong"
        assert len(taskruns) == data['done'], data

        # Add a new TaskRun and check again
        taskrun = TaskRunFactory.create(task=tasks[0], info={'answer': u'hello'})

        res = self.app.get('/api/app/1/userprogress', follow_redirects=True)
        data = json.loads(res.data)
        error_msg = "The reported total number of tasks is wrong"
        assert len(tasks) == data['total'], error_msg

        error_msg = "Number of done tasks is wrong: %s" % len(taskruns)
        assert len(taskruns) + 1 == data['done'], error_msg

    @with_context
    def test_user_progress_authenticated_user(self):
        """Test API userprogress as an authenticated user works"""
        user = UserFactory.create()
        app = AppFactory.create(owner=user)
        tasks = TaskFactory.create_batch(2, app=app)
        for task in tasks:
            taskruns = TaskRunFactory.create_batch(2, task=task, user=user)
        taskruns = db.session.query(TaskRun)\
                     .filter(TaskRun.app_id == app.id)\
                     .filter(TaskRun.user_id == user.id)\
                     .all()

        url = '/api/app/1/userprogress?api_key=%s' % user.api_key
        res = self.app.get(url, follow_redirects=True)
        data = json.loads(res.data)
        error_msg = "The reported total number of tasks is wrong"
        assert len(tasks) == data['total'], error_msg

        url = '/api/app/%s/userprogress?api_key=%s' % (app.short_name, user.api_key)
        res = self.app.get(url, follow_redirects=True)
        data = json.loads(res.data)
        error_msg = "The reported total number of tasks is wrong"
        assert len(tasks) == data['total'], error_msg

        url = '/api/app/5000/userprogress?api_key=%s' % user.api_key
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code

        url = '/api/app/userprogress?api_key=%s' % user.api_key
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code

        error_msg = "The reported number of done tasks is wrong"
        assert len(taskruns) == data['done'], error_msg

        # Add a new TaskRun and check again
        taskrun = TaskRunFactory.create(task=tasks[0], info={'answer': u'hello'})

        res = self.app.get('/api/app/1/userprogress', follow_redirects=True)
        data = json.loads(res.data)
        error_msg = "The reported total number of tasks is wrong"
        assert len(tasks) == data['total'], error_msg

        error_msg = "Number of done tasks is wrong: %s" % len(taskruns)
        assert len(taskruns) + 1 == data['done'], error_msg


    @with_context
    def test_delete_app_cascade(self):
        """Test API delete app deletes associated tasks and taskruns"""
        app = AppFactory.create()
        tasks = TaskFactory.create_batch(2, app=app)
        task_runs = TaskRunFactory.create_batch(2, app=app)
        url = '/api/app/%s?api_key=%s' % (1, app.owner.api_key)
        self.app.delete(url)

        tasks = db.session.query(Task)\
                  .filter_by(app_id=1)\
                  .all()
        assert len(tasks) == 0, "There should not be any task"

        task_runs = db.session.query(TaskRun)\
                      .filter_by(app_id=1)\
                      .all()
        assert len(task_runs) == 0, "There should not be any task run"


    @with_context
    def test_newtask_allow_anonymous_contributors(self):
        """Test API get a newtask - allow anonymous contributors"""
        app = AppFactory.create()
        user = UserFactory.create()
        tasks = TaskFactory.create_batch(2, app=app, info={'question': 'answer'})

        # All users are allowed to participate by default
        # As Anonymous user
        url = '/api/app/%s/newtask' % app.id
        res = self.app.get(url, follow_redirects=True)
        task = json.loads(res.data)
        err_msg = "The task.app_id is different from the app.id"
        assert task['app_id'] == app.id, err_msg
        err_msg = "There should not be an error message"
        assert task['info'].get('error') is None, err_msg
        err_msg = "There should be a question"
        assert task['info'].get('question') == 'answer', err_msg

        # As registered user
        url = '/api/app/%s/newtask?api_key=%s' % (app.id, user.api_key)
        res = self.app.get(url, follow_redirects=True)
        task = json.loads(res.data)
        err_msg = "The task.app_id is different from the app.id"
        assert task['app_id'] == app.id, err_msg
        err_msg = "There should not be an error message"
        assert task['info'].get('error') is None, err_msg
        err_msg = "There should be a question"
        assert task['info'].get('question') == 'answer', err_msg

        # Now only allow authenticated users
        app.allow_anonymous_contributors = False

        # As Anonymous user
        url = '/api/app/%s/newtask' % app.id
        res = self.app.get(url, follow_redirects=True)
        task = json.loads(res.data)
        err_msg = "The task.app_id should be null"
        assert task['app_id'] is None, err_msg
        err_msg = "There should be an error message"
        err = "This application does not allow anonymous contributors"
        assert task['info'].get('error') == err, err_msg
        err_msg = "There should not be a question"
        assert task['info'].get('question') is None, err_msg

        # As registered user
        url = '/api/app/%s/newtask?api_key=%s' % (app.id, user.api_key)
        res = self.app.get(url, follow_redirects=True)
        task = json.loads(res.data)
        err_msg = "The task.app_id is different from the app.id"
        assert task['app_id'] == app.id, err_msg
        err_msg = "There should not be an error message"
        assert task['info'].get('error') is None, err_msg
        err_msg = "There should be a question"
        assert task['info'].get('question') == 'answer', err_msg


    @with_context
    def test_newtask(self):
        """Test API App.new_task method and authentication"""
        app = AppFactory.create()
        TaskFactory.create_batch(2, app=app)
        user = UserFactory.create()

        # anonymous
        # test getting a new task
        res = self.app.get('/api/app/%s/newtask' % app.id)
        assert res, res
        task = json.loads(res.data)
        assert_equal(task['app_id'], app.id)

        # The output should have a mime-type: application/json
        assert res.mimetype == 'application/json', res

        # as a real user
        url = '/api/app/%s/newtask?api_key=%s' % (app.id, user.api_key)
        res = self.app.get(url)
        assert res, res
        task = json.loads(res.data)
        assert_equal(task['app_id'], app.id)

        # Get NotFound for an non-existing app
        url = '/api/app/5000/newtask'
        res = self.app.get(url)
        err = json.loads(res.data)
        err_msg = "The app does not exist"
        assert err['status'] == 'failed', err_msg
        assert err['status_code'] == 404, err_msg
        assert err['exception_cls'] == 'NotFound', err_msg
        assert err['target'] == 'app', err_msg

        # Get an empty task
        url = '/api/app/%s/newtask?offset=1000' % app.id
        res = self.app.get(url)
        assert res.data == '{}', res.data

########NEW FILE########
__FILENAME__ = test_category_api
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import json
from base import db, with_context
from nose.tools import assert_equal
from test_api import TestAPI
from pybossa.model.category import Category

from factories import UserFactory, CategoryFactory


class TestCategoryAPI(TestAPI):

    @with_context
    def test_query_category(self):
        """Test API query for category endpoint works"""
        CategoryFactory.create(name='thinking', short_name='thinking')
        # Test for real field
        url = "/api/category"
        res = self.app.get(url + "?short_name=thinking")
        data = json.loads(res.data)
        # Should return one result
        assert len(data) == 1, data
        # Correct result
        assert data[0]['short_name'] == 'thinking', data

        # Valid field but wrong value
        res = self.app.get(url + "?short_name=wrongvalue")
        data = json.loads(res.data)
        assert len(data) == 0, data

        # Multiple fields
        res = self.app.get(url + '?short_name=thinking&name=thinking')
        data = json.loads(res.data)
        # One result
        assert len(data) == 1, data
        # Correct result
        assert data[0]['short_name'] == 'thinking', data
        assert data[0]['name'] == 'thinking', data

        # Limits
        res = self.app.get(url + "?limit=1")
        data = json.loads(res.data)
        for item in data:
            assert item['short_name'] == 'thinking', item
        assert len(data) == 1, data

        # Errors
        res = self.app.get(url + "?something")
        err = json.loads(res.data)
        err_msg = "AttributeError exception should be raised"
        res.status_code == 415, err_msg
        assert res.status_code == 415, err_msg
        assert err['action'] == 'GET', err_msg
        assert err['status'] == 'failed', err_msg
        assert err['exception_cls'] == 'AttributeError', err_msg

    @with_context
    def test_category_post(self):
        """Test API Category creation and auth"""
        admin = UserFactory.create()
        user = UserFactory.create()
        name = u'Category'
        category = dict(
            name=name,
            short_name='category',
            description=u'description')
        data = json.dumps(category)
        # no api-key
        url = '/api/category'
        res = self.app.post(url, data=data)
        err = json.loads(res.data)
        err_msg = 'Should not be allowed to create'
        assert res.status_code == 401, err_msg
        assert err['action'] == 'POST', err_msg
        assert err['exception_cls'] == 'Unauthorized', err_msg

        # now a real user but not admin
        res = self.app.post(url + '?api_key=' + user.api_key, data=data)
        err = json.loads(res.data)
        err_msg = 'Should not be allowed to create'
        assert res.status_code == 403, err_msg
        assert err['action'] == 'POST', err_msg
        assert err['exception_cls'] == 'Forbidden', err_msg

        # now as an admin
        res = self.app.post(url + '?api_key=' + admin.api_key,
                            data=data)
        err = json.loads(res.data)
        err_msg = 'Admin should be able to create a Category'
        assert res.status_code == 200, err_msg
        cat = db.session.query(Category)\
                .filter_by(short_name=category['short_name']).first()
        assert err['id'] == cat.id, err_msg
        assert err['name'] == category['name'], err_msg
        assert err['short_name'] == category['short_name'], err_msg
        assert err['description'] == category['description'], err_msg

        # test re-create should fail
        res = self.app.post(url + '?api_key=' + admin.api_key,
                            data=data)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'POST', err
        assert err['exception_cls'] == "IntegrityError", err

        # test create with non-allowed fields should fail
        data = dict(name='fail', short_name='fail', wrong=15)
        res = self.app.post(url + '?api_key=' + admin.api_key,
                            data=data)
        err = json.loads(res.data)
        err_msg = "ValueError exception should be raised"
        assert res.status_code == 415, err
        assert err['action'] == 'POST', err
        assert err['status'] == 'failed', err
        assert err['exception_cls'] == "ValueError", err_msg
        # Now with a JSON object but not valid
        data = json.dumps(data)
        res = self.app.post(url + '?api_key=' + user.api_key,
                            data=data)
        err = json.loads(res.data)
        err_msg = "TypeError exception should be raised"
        assert err['action'] == 'POST', err_msg
        assert err['status'] == 'failed', err_msg
        assert err['exception_cls'] == "TypeError", err_msg
        assert res.status_code == 415, err_msg

        # test update
        data = {'name': 'My New Title'}
        datajson = json.dumps(data)
        ## anonymous
        res = self.app.put(url + '/%s' % cat.id,
                           data=data)
        error_msg = 'Anonymous should not be allowed to update'
        assert_equal(res.status, '401 UNAUTHORIZED', error_msg)
        error = json.loads(res.data)
        assert error['status'] == 'failed', error
        assert error['action'] == 'PUT', error
        assert error['exception_cls'] == 'Unauthorized', error

        ### real user but not allowed as not admin!
        url = '/api/category/%s?api_key=%s' % (cat.id, user.api_key)
        res = self.app.put(url, data=datajson)
        error_msg = 'Should not be able to update apps of others'
        assert_equal(res.status, '403 FORBIDDEN', error_msg)
        error = json.loads(res.data)
        assert error['status'] == 'failed', error
        assert error['action'] == 'PUT', error
        assert error['exception_cls'] == 'Forbidden', error

        # Now as an admin
        res = self.app.put('/api/category/%s?api_key=%s' % (cat.id, admin.api_key),
                           data=datajson)
        assert_equal(res.status, '200 OK', res.data)
        out2 = db.session.query(Category).get(cat.id)
        assert_equal(out2.name, data['name'])
        out = json.loads(res.data)
        assert out.get('status') is None, error
        assert out.get('id') == cat.id, error

        # With fake data
        data['algo'] = 13
        datajson = json.dumps(data)
        res = self.app.put('/api/category/%s?api_key=%s' % (cat.id, admin.api_key),
                           data=datajson)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'TypeError', err

        # With not JSON data
        datajson = data
        res = self.app.put('/api/category/%s?api_key=%s' % (cat.id, admin.api_key),
                           data=datajson)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'ValueError', err

        # With wrong args in the URL
        data = dict(
            name='Category3',
            short_name='category3',
            description=u'description3')

        datajson = json.dumps(data)
        res = self.app.put('/api/category/%s?api_key=%s&search=select1' % (cat.id, admin.api_key),
                           data=datajson)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'AttributeError', err

        # test delete
        ## anonymous
        res = self.app.delete(url + '/%s' % cat.id, data=data)
        error_msg = 'Anonymous should not be allowed to delete'
        assert_equal(res.status, '401 UNAUTHORIZED', error_msg)
        error = json.loads(res.data)
        assert error['status'] == 'failed', error
        assert error['action'] == 'DELETE', error
        assert error['target'] == 'category', error
        ### real user but not admin
        url = '/api/category/%s?api_key=%s' % (cat.id, user.api_key)
        res = self.app.delete(url, data=datajson)
        error_msg = 'Should not be able to delete apps of others'
        assert_equal(res.status, '403 FORBIDDEN', error_msg)
        error = json.loads(res.data)
        assert error['status'] == 'failed', error
        assert error['action'] == 'DELETE', error
        assert error['target'] == 'category', error

        # As admin
        url = '/api/category/%s?api_key=%s' % (cat.id, admin.api_key)
        res = self.app.delete(url, data=datajson)

        assert_equal(res.status, '204 NO CONTENT', res.data)

        # delete a category that does not exist
        url = '/api/category/5000?api_key=%s' % admin.api_key
        res = self.app.delete(url, data=datajson)
        error = json.loads(res.data)
        assert res.status_code == 404, error
        assert error['status'] == 'failed', error
        assert error['action'] == 'DELETE', error
        assert error['target'] == 'category', error
        assert error['exception_cls'] == 'NotFound', error

        # delete a category that does not exist
        url = '/api/category/?api_key=%s' % admin.api_key
        res = self.app.delete(url, data=datajson)
        assert res.status_code == 404, error

########NEW FILE########
__FILENAME__ = test_global_stats_api
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import json
from test_api import TestAPI
from factories import AppFactory



class TestGlobalStatsAPI(TestAPI):

    def test_global_stats(self):
        """Test Global Stats works."""
        AppFactory()
        res = self.app.get('api/globalstats')
        stats = json.loads(res.data)
        assert res.status_code == 200, res.status_code
        keys = ['n_projects', 'n_pending_tasks',
                'n_users', 'n_task_runs', 'categories']
        for k in keys:
            err_msg = "%s should be in stats JSON object" % k
            assert k in stats.keys(), err_msg

    def test_post_global_stats(self):
        """Test Global Stats Post works."""
        res = self.app.post('api/globalstats')
        assert res.status_code == 405, res.status_code

########NEW FILE########
__FILENAME__ = test_taskrun_api
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import json
from base import with_context
from nose.tools import assert_equal
from test_api import TestAPI

from factories import (AppFactory, TaskFactory, TaskRunFactory,
                        AnonymousTaskRunFactory, UserFactory)



class TestTaskrunAPI(TestAPI):


    @with_context
    def test_taskrun_query_without_params(self):
        """Test API TaskRun query"""
        TaskRunFactory.create_batch(10, info={'answer': 'annakarenina'})
        res = self.app.get('/api/taskrun')
        taskruns = json.loads(res.data)
        assert len(taskruns) == 10, taskruns
        taskrun = taskruns[0]
        assert taskrun['info']['answer'] == 'annakarenina', taskrun

        # The output should have a mime-type: application/json
        assert res.mimetype == 'application/json', res


    @with_context
    def test_query_taskrun(self):
        """Test API query for taskrun with params works"""
        app = AppFactory.create()
        TaskRunFactory.create_batch(10, app=app)
        # Test for real field
        res = self.app.get("/api/taskrun?app_id=1")
        data = json.loads(res.data)
        # Should return one result
        assert len(data) == 10, data
        # Correct result
        assert data[0]['app_id'] == 1, data

        # Valid field but wrong value
        res = self.app.get("/api/taskrun?app_id=99999999")
        data = json.loads(res.data)
        assert len(data) == 0, data

        # Multiple fields
        res = self.app.get('/api/taskrun?app_id=1&task_id=1')
        data = json.loads(res.data)
        # One result
        assert len(data) == 1, data
        # Correct result
        assert data[0]['app_id'] == 1, data
        assert data[0]['task_id'] == 1, data

        # Limits
        res = self.app.get("/api/taskrun?app_id=1&limit=5")
        data = json.loads(res.data)
        for item in data:
            assert item['app_id'] == 1, item
        assert len(data) == 5, data


    @with_context
    def test_taskrun_anonymous_post(self):
        """Test API TaskRun creation and auth for anonymous users"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app)
        data = dict(
            app_id=app.id,
            task_id=task.id,
            info='my task result')

        # With wrong app_id
        data['app_id'] = 100000000000000000
        datajson = json.dumps(data)
        tmp = self.app.post('/api/taskrun', data=datajson)
        err_msg = "This post should fail as the app_id is wrong"
        err = json.loads(tmp.data)
        assert tmp.status_code == 403, tmp.data
        assert err['status'] == 'failed', err_msg
        assert err['status_code'] == 403, err_msg
        assert err['exception_msg'] == 'Invalid app_id', err_msg
        assert err['exception_cls'] == 'Forbidden', err_msg
        assert err['target'] == 'taskrun', err_msg

        # With wrong task_id
        data['app_id'] = task.app_id
        data['task_id'] = 100000000000000000000
        datajson = json.dumps(data)
        tmp = self.app.post('/api/taskrun', data=datajson)
        err = json.loads(tmp.data)
        assert tmp.status_code == 403, err_msg
        assert err['status'] == 'failed', err_msg
        assert err['status_code'] == 403, err_msg
        assert err['exception_msg'] == 'Invalid task_id', err_msg
        assert err['exception_cls'] == 'Forbidden', err_msg
        assert err['target'] == 'taskrun', err_msg

        # Now with everything fine
        data = dict(
            app_id=task.app_id,
            task_id=task.id,
            info='my task result')
        datajson = json.dumps(data)
        tmp = self.app.post('/api/taskrun', data=datajson)
        r_taskrun = json.loads(tmp.data)
        assert tmp.status_code == 200, r_taskrun

        # If the anonymous tries again it should be forbidden
        tmp = self.app.post('/api/taskrun', data=datajson)
        err_msg = ("Anonymous users should be only allowed to post \
                    one task_run per task")
        assert tmp.status_code == 403, err_msg

    @with_context
    def test_taskrun_authenticated_post(self):
        """Test API TaskRun creation and auth for authenticated users"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app)
        data = dict(
            app_id=app.id,
            task_id=task.id,
            info='my task result')

        # With wrong app_id
        data['app_id'] = 100000000000000000
        datajson = json.dumps(data)
        url = '/api/taskrun?api_key=%s' % app.owner.api_key
        tmp = self.app.post(url, data=datajson)
        err_msg = "This post should fail as the app_id is wrong"
        err = json.loads(tmp.data)
        assert tmp.status_code == 403, err_msg
        assert err['status'] == 'failed', err_msg
        assert err['status_code'] == 403, err_msg
        assert err['exception_msg'] == 'Invalid app_id', err_msg
        assert err['exception_cls'] == 'Forbidden', err_msg
        assert err['target'] == 'taskrun', err_msg

        # With wrong task_id
        data['app_id'] = task.app_id
        data['task_id'] = 100000000000000000000
        datajson = json.dumps(data)
        tmp = self.app.post(url, data=datajson)
        err_msg = "This post should fail as the task_id is wrong"
        err = json.loads(tmp.data)
        assert tmp.status_code == 403, err_msg
        assert err['status'] == 'failed', err_msg
        assert err['status_code'] == 403, err_msg
        assert err['exception_msg'] == 'Invalid task_id', err_msg
        assert err['exception_cls'] == 'Forbidden', err_msg
        assert err['target'] == 'taskrun', err_msg

        # Now with everything fine
        data = dict(
            app_id=task.app_id,
            task_id=task.id,
            info='my task result')
        datajson = json.dumps(data)
        tmp = self.app.post(url, data=datajson)
        r_taskrun = json.loads(tmp.data)
        assert tmp.status_code == 200, r_taskrun

        # If the user tries again it should be forbidden
        tmp = self.app.post(url, data=datajson)
        err_msg = ("Authorized users should be only allowed to post \
                    one task_run per task")
        task_runs = self.app.get('/api/taskrun')
        assert tmp.status_code == 403, tmp.data


    @with_context
    def test_taskrun_post_with_bad_data(self):
        """Test API TaskRun error messages."""
        app = AppFactory.create()
        task = TaskFactory.create(app=app)
        app_id = app.id
        task_run = dict(app_id=app.id, task_id=task.id, info='my task result')
        url = '/api/taskrun?api_key=%s' % app.owner.api_key

        # POST with not JSON data
        res = self.app.post(url, data=task_run)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'taskrun', err
        assert err['action'] == 'POST', err
        assert err['exception_cls'] == 'ValueError', err

        # POST with not allowed args
        res = self.app.post(url + '&foo=bar', data=task_run)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'taskrun', err
        assert err['action'] == 'POST', err
        assert err['exception_cls'] == 'AttributeError', err

        # POST with fake data
        task_run['wrongfield'] = 13
        res = self.app.post(url, data=json.dumps(task_run))
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'taskrun', err
        assert err['action'] == 'POST', err
        assert err['exception_cls'] == 'TypeError', err


    @with_context
    def test_taskrun_update(self):
        """Test TaskRun API update works"""
        admin = UserFactory.create()
        owner = UserFactory.create()
        non_owner = UserFactory.create()
        app = AppFactory.create(owner=owner)
        task = TaskFactory.create(app=app)
        anonymous_taskrun = AnonymousTaskRunFactory.create(task=task, info='my task result')
        user_taskrun = TaskRunFactory.create(task=task, user=owner, info='my task result')

        task_run = dict(app_id=app.id, task_id=task.id, info='another result')
        datajson = json.dumps(task_run)

        # anonymous user
        # No one can update anonymous TaskRuns
        url = '/api/taskrun/%s' % anonymous_taskrun.id
        res = self.app.put(url, data=datajson)
        assert anonymous_taskrun, anonymous_taskrun
        assert_equal(anonymous_taskrun.user, None)
        error_msg = 'Should not be allowed to update'
        assert_equal(res.status, '401 UNAUTHORIZED', error_msg)

        # real user but not allowed as not owner!
        url = '/api/taskrun/%s?api_key=%s' % (user_taskrun.id, non_owner.api_key)
        res = self.app.put(url, data=datajson)
        error_msg = 'Should not be able to update TaskRuns of others'
        assert_equal(res.status, '403 FORBIDDEN', error_msg)

        # real user
        url = '/api/taskrun/%s?api_key=%s' % (user_taskrun.id, owner.api_key)
        out = self.app.get(url, follow_redirects=True)
        task = json.loads(out.data)
        datajson = json.loads(datajson)
        datajson['link'] = task['link']
        datajson['links'] = task['links']
        datajson = json.dumps(datajson)
        url = '/api/taskrun/%s?api_key=%s' % (user_taskrun.id, owner.api_key)
        res = self.app.put(url, data=datajson)
        out = json.loads(res.data)
        assert_equal(res.status, '403 FORBIDDEN', res.data)

        # PUT with not JSON data
        res = self.app.put(url, data=task_run)
        err = json.loads(res.data)
        assert res.status_code == 403, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'taskrun', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'Forbidden', err

        # PUT with not allowed args
        res = self.app.put(url + "&foo=bar", data=json.dumps(task_run))
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'taskrun', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'AttributeError', err

        # PUT with fake data
        task_run['wrongfield'] = 13
        res = self.app.put(url, data=json.dumps(task_run))
        err = json.loads(res.data)
        assert res.status_code == 403, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'taskrun', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'Forbidden', err
        task_run.pop('wrongfield')

        # root user
        url = '/api/taskrun/%s?api_key=%s' % (user_taskrun.id, admin.api_key)
        res = self.app.put(url, data=datajson)
        assert_equal(res.status, '403 FORBIDDEN', res.data)


    @with_context
    def test_taskrun_delete(self):
        """Test TaskRun API delete works"""
        admin = UserFactory.create()
        owner = UserFactory.create()
        non_owner = UserFactory.create()
        app = AppFactory.create(owner=owner)
        task = TaskFactory.create(app=app)
        anonymous_taskrun = AnonymousTaskRunFactory.create(task=task, info='my task result')
        user_taskrun = TaskRunFactory.create(task=task, user=owner, info='my task result')

        ## anonymous
        res = self.app.delete('/api/taskrun/%s' % user_taskrun.id)
        error_msg = 'Anonymous should not be allowed to delete'
        assert_equal(res.status, '401 UNAUTHORIZED', error_msg)

        ### real user but not allowed to delete anonymous TaskRuns
        url = '/api/taskrun/%s?api_key=%s' % (anonymous_taskrun.id, owner.api_key)
        res = self.app.delete(url)
        error_msg = 'Authenticated user should not be allowed ' \
                    'to delete anonymous TaskRuns'
        assert_equal(res.status, '403 FORBIDDEN', error_msg)

        ### real user but not allowed as not owner!
        url = '/api/taskrun/%s?api_key=%s' % (user_taskrun.id, non_owner.api_key)
        res = self.app.delete(url)
        error_msg = 'Should not be able to delete TaskRuns of others'
        assert_equal(res.status, '403 FORBIDDEN', error_msg)

        #### real user
        # DELETE with not allowed args
        url = '/api/taskrun/%s?api_key=%s' % (user_taskrun.id, owner.api_key)
        res = self.app.delete(url + "&foo=bar")
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'taskrun', err
        assert err['action'] == 'DELETE', err
        assert err['exception_cls'] == 'AttributeError', err

        # Owner with valid args can delete
        res = self.app.delete(url)
        assert_equal(res.status, '204 NO CONTENT', res.data)

        ### root
        url = '/api/taskrun/%s?api_key=%s' % (anonymous_taskrun.id, admin.api_key)
        res = self.app.delete(url)
        error_msg = 'Admin should be able to delete TaskRuns of others'
        assert_equal(res.status, '204 NO CONTENT', error_msg)


    @with_context
    def test_taskrun_updates_task_state(self):
        """Test API TaskRun POST updates task state"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app, n_answers=2)
        url = '/api/taskrun?api_key=%s' % app.owner.api_key

        # Post first taskrun
        data = dict(
            app_id=task.app_id,
            task_id=task.id,
            info='my task result')
        datajson = json.dumps(data)
        tmp = self.app.post(url, data=datajson)
        r_taskrun = json.loads(tmp.data)

        assert tmp.status_code == 200, r_taskrun
        err_msg = "Task state should be different from completed"
        assert task.state == 'ongoing', err_msg

        # Post second taskrun
        url = '/api/taskrun'
        data = dict(
            app_id=task.app_id,
            task_id=task.id,
            info='my task result anon')
        datajson = json.dumps(data)
        tmp = self.app.post(url, data=datajson)
        r_taskrun = json.loads(tmp.data)

        assert tmp.status_code == 200, r_taskrun
        err_msg = "Task state should be equal to completed"
        assert task.state == 'completed', err_msg

########NEW FILE########
__FILENAME__ = test_task_api
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import json
from base import db, with_context
from nose.tools import assert_equal
from test_api import TestAPI
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun

from factories import AppFactory, TaskFactory, TaskRunFactory, UserFactory



class TestTaskAPI(TestAPI):


    @with_context
    def test_task_query_without_params(self):
        """ Test API Task query"""
        app = AppFactory.create()
        TaskFactory.create_batch(10, app=app, info={'question': 'answer'})
        res = self.app.get('/api/task')
        tasks = json.loads(res.data)
        assert len(tasks) == 10, tasks
        task = tasks[0]
        assert task['info']['question'] == 'answer', task

        # The output should have a mime-type: application/json
        assert res.mimetype == 'application/json', res


    @with_context
    def test_task_query_with_params(self):
        """Test API query for task with params works"""
        app = AppFactory.create()
        TaskFactory.create_batch(10, app=app)
        # Test for real field
        res = self.app.get("/api/task?app_id=1")
        data = json.loads(res.data)
        # Should return one result
        assert len(data) == 10, data
        # Correct result
        assert data[0]['app_id'] == 1, data

        # Valid field but wrong value
        res = self.app.get("/api/task?app_id=99999999")
        data = json.loads(res.data)
        assert len(data) == 0, data

        # Multiple fields
        res = self.app.get('/api/task?app_id=1&state=ongoing')
        data = json.loads(res.data)
        # One result
        assert len(data) == 10, data
        # Correct result
        assert data[0]['app_id'] == 1, data
        assert data[0]['state'] == u'ongoing', data

        # Limits
        res = self.app.get("/api/task?app_id=1&limit=5")
        data = json.loads(res.data)
        for item in data:
            assert item['app_id'] == 1, item
        assert len(data) == 5, data


    @with_context
    def test_task_post(self):
        """Test API Task creation"""
        admin = UserFactory.create()
        user = UserFactory.create()
        non_owner = UserFactory.create()
        app = AppFactory.create(owner=user)
        data = dict(app_id=app.id, state='0', info='my task data')
        root_data = dict(app_id=app.id, state='0', info='my root task data')

        # anonymous user
        # no api-key
        res = self.app.post('/api/task', data=json.dumps(data))
        error_msg = 'Should not be allowed to create'
        assert_equal(res.status, '401 UNAUTHORIZED', error_msg)

        ### real user but not allowed as not owner!
        res = self.app.post('/api/task?api_key=' + non_owner.api_key,
                            data=json.dumps(data))

        error_msg = 'Should not be able to post tasks for apps of others'
        assert_equal(res.status, '403 FORBIDDEN', error_msg)

        # now a real user
        res = self.app.post('/api/task?api_key=' + user.api_key,
                            data=json.dumps(data))
        assert res.data, res
        datajson = json.loads(res.data)
        out = db.session.query(Task)\
                .filter_by(id=datajson['id'])\
                .one()
        assert out, out
        assert_equal(out.info, 'my task data'), out
        assert_equal(out.app_id, app.id)

        # now the root user
        res = self.app.post('/api/task?api_key=' + admin.api_key,
                            data=json.dumps(root_data))
        assert res.data, res
        datajson = json.loads(res.data)
        out = db.session.query(Task)\
                .filter_by(id=datajson['id'])\
                .one()
        assert out, out
        assert_equal(out.info, 'my root task data'), out
        assert_equal(out.app_id, app.id)

        # POST with not JSON data
        url = '/api/task?api_key=%s' % user.api_key
        res = self.app.post(url, data=data)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'task', err
        assert err['action'] == 'POST', err
        assert err['exception_cls'] == 'ValueError', err

        # POST with not allowed args
        res = self.app.post(url + '&foo=bar', data=json.dumps(data))
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'task', err
        assert err['action'] == 'POST', err
        assert err['exception_cls'] == 'AttributeError', err

        # POST with fake data
        data['wrongfield'] = 13
        res = self.app.post(url, data=json.dumps(data))
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'task', err
        assert err['action'] == 'POST', err
        assert err['exception_cls'] == 'TypeError', err


    @with_context
    def test_task_update(self):
        """Test API task update"""
        admin = UserFactory.create()
        user = UserFactory.create()
        non_owner = UserFactory.create()
        app = AppFactory.create(owner=user)
        task = TaskFactory.create(app=app)
        root_task = TaskFactory.create(app=app)
        data = {'state': '1'}
        datajson = json.dumps(data)
        root_data = {'state': '4'}
        root_datajson = json.dumps(root_data)

        ## anonymous
        res = self.app.put('/api/task/%s' % task.id, data=data)
        assert_equal(res.status, '401 UNAUTHORIZED', res.status)
        ### real user but not allowed as not owner!
        url = '/api/task/%s?api_key=%s' % (task.id, non_owner.api_key)
        res = self.app.put(url, data=datajson)
        assert_equal(res.status, '403 FORBIDDEN', res.status)

        ### real user
        url = '/api/task/%s?api_key=%s' % (task.id, user.api_key)
        res = self.app.put(url, data=datajson)
        out = json.loads(res.data)
        assert_equal(res.status, '200 OK', res.data)
        assert_equal(task.state, data['state'])
        assert task.id == out['id'], out

        ### root
        res = self.app.put('/api/task/%s?api_key=%s' % (root_task.id, admin.api_key),
                           data=root_datajson)
        assert_equal(res.status, '200 OK', res.data)
        assert_equal(root_task.state, root_data['state'])

        # PUT with not JSON data
        res = self.app.put(url, data=data)
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'task', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'ValueError', err

        # PUT with not allowed args
        res = self.app.put(url + "&foo=bar", data=json.dumps(data))
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'task', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'AttributeError', err

        # PUT with fake data
        data['wrongfield'] = 13
        res = self.app.put(url, data=json.dumps(data))
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'task', err
        assert err['action'] == 'PUT', err
        assert err['exception_cls'] == 'TypeError', err


    @with_context
    def test_task_delete(self):
        """Test API task delete"""
        admin = UserFactory.create()
        user = UserFactory.create()
        non_owner = UserFactory.create()
        app = AppFactory.create(owner=user)
        task = TaskFactory.create(app=app)
        root_task = TaskFactory.create(app=app)

        ## anonymous
        res = self.app.delete('/api/task/%s' % task.id)
        error_msg = 'Anonymous should not be allowed to update'
        assert_equal(res.status, '401 UNAUTHORIZED', error_msg)

        ### real user but not allowed as not owner!
        url = '/api/task/%s?api_key=%s' % (task.id, non_owner.api_key)
        res = self.app.delete(url)
        error_msg = 'Should not be able to update tasks of others'
        assert_equal(res.status, '403 FORBIDDEN', error_msg)

        #### real user
        # DELETE with not allowed args
        res = self.app.delete(url + "&foo=bar")
        err = json.loads(res.data)
        assert res.status_code == 415, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'task', err
        assert err['action'] == 'DELETE', err
        assert err['exception_cls'] == 'AttributeError', err

        # DELETE returns 204
        url = '/api/task/%s?api_key=%s' % (task.id, user.api_key)
        res = self.app.delete(url)
        assert_equal(res.status, '204 NO CONTENT', res.data)
        assert res.data == '', res.data

        #### root user
        url = '/api/task/%s?api_key=%s' % (root_task.id, admin.api_key)
        res = self.app.delete(url)
        assert_equal(res.status, '204 NO CONTENT', res.data)

        tasks = db.session.query(Task)\
                  .filter_by(app_id=app.id)\
                  .all()
        assert task not in tasks, tasks
        assert root_task not in tasks, tasks


    @with_context
    def test_delete_task_cascade(self):
        """Test API delete task deletes associated taskruns"""
        task = TaskFactory.create()
        task_runs = TaskRunFactory.create_batch(3, task=task)
        url = '/api/task/%s?api_key=%s' % (task.id, task.app.owner.api_key)
        res = self.app.delete(url)

        assert_equal(res.status, '204 NO CONTENT', res.data)
        task_runs = db.session.query(TaskRun)\
                      .filter_by(task_id=task.id)\
                      .all()
        assert len(task_runs) == 0, "There should not be any task run for task"

########NEW FILE########
__FILENAME__ = test_token_api
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import json
from base import with_context
from nose.tools import assert_equal, assert_raises
from test_api import TestAPI
from pybossa.api.token import TokenAPI
from werkzeug.exceptions import MethodNotAllowed

from factories import UserFactory



class TestTokenAPI(TestAPI):

    @with_context
    def test_not_allowed_methods(self):
        """Test POST, DELETE, PUT methods are not allowed for resource token"""
        token_api_instance = TokenAPI()

        post_response = self.app.post('/api/token')
        assert post_response.status_code == 405, post_response.status_code
        assert_raises(MethodNotAllowed, token_api_instance.post)
        delete_response = self.app.delete('/api/token')
        assert delete_response.status_code == 405, delete_response.status_code
        assert_raises(MethodNotAllowed, token_api_instance.delete)
        put_response = self.app.put('/api/token')
        assert put_response.status_code == 405, put_response.status_code
        assert_raises(MethodNotAllowed, token_api_instance.put)


    @with_context
    def test_get_all_tokens_anonymous_user(self):
        """Test anonymous users are unauthorized to request their tokens"""

        # Anonymoues users should be unauthorized, no matter which kind of token are requesting
        res = self.app.get('/api/token')
        err = json.loads(res.data)

        assert res.status_code == 401, err
        assert err['status'] == 'failed', err
        assert err['status_code'] == 401, err
        assert err['exception_cls'] == 'Unauthorized', err
        assert err['target'] == 'token', err


    @with_context
    def test_get_specific_token_anonymous_user(self):
        """Test anonymous users are unauthorized to request any of their tokens"""

        res = self.app.get('/api/token/twitter')
        err = json.loads(res.data)

        assert res.status_code == 401, err
        assert err['status'] == 'failed', err
        assert err['status_code'] == 401, err
        assert err['exception_cls'] == 'Unauthorized', err
        assert err['target'] == 'token', err


    @with_context
    def test_get_all_tokens_authenticated_user(self):
        """Test authenticated user is able to retrieve all his tokens"""

        user = UserFactory.create_batch(2)[1]
        user.info = create_tokens_for(user)

        res = self.app.get('api/token?api_key=' + user.api_key)
        data = json.loads(res.data)

        for provider in TokenAPI.oauth_providers:
            token_name = '%s_token' % provider
            assert data.get(token_name) is not None, data


    @with_context
    def test_get_all_existing_tokens_authenticated_user(self):
        """Test if a user lacks one of the valid tokens, it won't be retrieved"""

        user = UserFactory.create_batch(2)[1]
        user.info = create_tokens_for(user)
        del user.info['google_token']

        res = self.app.get('api/token?api_key=' + user.api_key)
        data = json.loads(res.data)

        assert data.get('twitter_token') is not None, data
        assert data.get('facebook_token') is not None, data
        assert data.get('google_token') is None, data


    @with_context
    def test_get_existing_token_authenticated_user(self):
        """Test authenticated user retrieves a given existing token"""

        user = UserFactory.create_batch(2)[1]
        user.info = create_tokens_for(user)

        # If the token exists, it should be retrieved
        res = self.app.get('/api/token/twitter?api_key=' + user.api_key)
        data = json.loads(res.data)

        assert data.get('twitter_token') is not None, data
        assert data.get('twitter_token')['oauth_token'] == 'token-for-%s' % user.name
        assert data.get('twitter_token')['oauth_token_secret'] == 'secret-for-%s' % user.name
        # And no other tokens should
        assert data.get('facebook_token') is None, data


    @with_context
    def test_get_non_existing_token_authenticated_user(self):
        """Test authenticated user cannot get non-existing tokens"""

        user_no_tokens = UserFactory.create_batch(2)[1]

        res = self.app.get('/api/token/twitter?api_key=' + user_no_tokens.api_key)
        error = json.loads(res.data)

        assert res.status_code == 404, error
        assert error['status'] == 'failed', error
        assert error['action'] == 'GET', error
        assert error['target'] == 'token', error
        assert error['exception_cls'] == 'NotFound', error


    @with_context
    def test_get_non_valid_token(self):
        """Test authenticated user cannot get non-valid tokens"""

        user = UserFactory.create_batch(2)[1]
        res = self.app.get('/api/token/non-valid?api_key=' + user.api_key)
        error = json.loads(res.data)

        assert res.status_code == 404, error
        assert error['status'] == 'failed', error
        assert error['action'] == 'GET', error
        assert error['target'] == 'token', error
        assert error['exception_cls'] == 'NotFound', error



def create_tokens_for(user):
    info = {}
    twitter_token = {'oauth_token': 'token-for-%s' % user.name,
                     'oauth_token_secret': 'secret-for-%s' % user.name}
    facebook_token = {'oauth_token': 'facebook_token'}
    google_token = {'oauth_token': 'google_token'}
    info['twitter_token'] = twitter_token
    info['facebook_token'] = facebook_token
    info['google_token'] = google_token
    return info




########NEW FILE########
__FILENAME__ = test_user_api
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import json
from base import with_context
from nose.tools import assert_raises
from werkzeug.exceptions import MethodNotAllowed
from pybossa.api.user import UserAPI
from test_api import TestAPI

from factories import UserFactory



class TestUserAPI(TestAPI):

    @with_context
    def test_user_get(self):
        """Test API User GET"""
        expected_user = UserFactory.create()
        # Test GET all users
        res = self.app.get('/api/user')
        data = json.loads(res.data)
        user = data[0]
        assert len(data) == 1, data
        assert user['name'] == expected_user.name, data

        # The output should have a mime-type: application/json
        assert res.mimetype == 'application/json', res

        # Test GETting a specific user by ID
        res = self.app.get('/api/user/1')
        data = json.loads(res.data)
        user = data
        assert user['name'] == expected_user.name, data

        # Test a non-existant ID
        res = self.app.get('/api/user/3434209')
        err = json.loads(res.data)
        assert res.status_code == 404, err
        assert err['status'] == 'failed', err
        assert err['target'] == 'user', err
        assert err['exception_cls'] == 'NotFound', err
        assert err['action'] == 'GET', err


    @with_context
    def test_query_user(self):
        """Test API query for user endpoint works"""
        expected_user = UserFactory.create_batch(2)[0]
        # When querying with a valid existing field which is unique
        # It should return one correct result if exists
        res = self.app.get('/api/user?name=%s' % expected_user.name)
        data = json.loads(res.data)
        assert len(data) == 1, data
        assert data[0]['name'] == expected_user.name, data
        # And it should return no results if there are no matches
        res = self.app.get('/api/user?name=Godzilla')
        data = json.loads(res.data)
        assert len(data) == 0, data

        # When querying with a valid existing non-unique field
        res = self.app.get("/api/user?locale=en")
        data = json.loads(res.data)
        # It should return 3 results, as every registered user has locale=en by default
        assert len(data) == 2, data
        # And they should be the correct ones
        assert (data[0]['locale'] == data[1]['locale'] == 'en'
               and data[0] != data[1]), data

        # When querying with multiple valid fields
        res = self.app.get('/api/user?name=%s&locale=en' % expected_user.name)
        data = json.loads(res.data)
        # It should find and return one correct result
        assert len(data) == 1, data
        assert data[0]['name'] == expected_user.name, data
        assert data[0]['locale'] == 'en', data

        # When querying with non-valid fields -- Errors
        res = self.app.get('/api/user?something_invalid=whatever')
        err = json.loads(res.data)
        err_msg = "AttributeError exception should be raised"
        assert res.status_code == 415, err_msg
        assert err['action'] == 'GET', err_msg
        assert err['status'] == 'failed', err_msg
        assert err['exception_cls'] == 'AttributeError', err_msg


    @with_context
    def test_user_not_allowed_actions(self):
        """Test POST, PUT and DELETE actions are not allowed for user
        in the API"""

        user_api_instance = UserAPI()
        post_response = self.app.post('/api/user')
        assert post_response.status_code == 405, post_response.status_code
        assert_raises(MethodNotAllowed, user_api_instance.post)
        delete_response = self.app.delete('/api/user')
        assert delete_response.status_code == 405, delete_response.status_code
        assert_raises(MethodNotAllowed, user_api_instance.delete)
        put_response = self.app.put('/api/user')
        assert put_response.status_code == 405, put_response.status_code
        assert_raises(MethodNotAllowed, user_api_instance.put)


    @with_context
    def test_privacy_mode_user_get(self):
        """Test API user queries for privacy mode"""
        admin = UserFactory.create()
        user = UserFactory.create()
        # Add user with fullname 'Public user', privacy mode disabled
        user_with_privacy_disabled = UserFactory.create(email_addr='public@user.com',
                                    name='publicUser', fullname='Public user',
                                    privacy_mode=False)
        # Add user with fullname 'Private user', privacy mode enabled
        user_with_privacy_enabled = UserFactory.create(email_addr='private@user.com',
                                    name='privateUser', fullname='Private user',
                                    privacy_mode=True)

        # With no API-KEY
        # User with privacy disabled
        res = self.app.get('/api/user/3')
        data = json.loads(res.data)
        user_with_privacy_disabled = data
        # When checking a public field it should be returned
        assert user_with_privacy_disabled['locale'] == 'en', data
        # When checking a private field it should be returned too
        assert user_with_privacy_disabled['fullname'] == 'Public user', data
        # User with privacy enabled
        res = self.app.get('/api/user/4')
        data = json.loads(res.data)
        user_with_privacy_enabled = data
        # When checking a public field it should be returned
        assert user_with_privacy_enabled['locale'] == 'en', data
        # When checking a private field it should not be returned
        assert 'fullname' not in user_with_privacy_enabled, data
        # Users with privacy enabled and disabled, mixed together
        res = self.app.get('/api/user')
        data = json.loads(res.data)
        user_with_privacy_disabled = data[2]
        user_with_privacy_enabled = data[3]
        assert user_with_privacy_disabled['locale'] == 'en', data
        assert user_with_privacy_disabled['fullname'] == 'Public user', data
        assert user_with_privacy_enabled['locale'] == 'en', data
        assert 'fullname' not in user_with_privacy_enabled, data

        # With a non-admin API-KEY
        # User with privacy disabled
        res = self.app.get('/api/user/3?api_key=' + user.api_key)
        data = json.loads(res.data)
        user_with_privacy_disabled = data
        # When checking a public field it should be returned
        assert user_with_privacy_disabled['locale'] == 'en', data
        # When checking a private field it should be returned too
        assert user_with_privacy_disabled['fullname'] == 'Public user', data
        # User with privacy enabled
        res = self.app.get('/api/user/4?api_key=' + user.api_key)
        data = json.loads(res.data)
        user_with_privacy_enabled = data
        # When checking a public field it should be returned
        assert user_with_privacy_enabled['locale'] == 'en', data
        # When checking a private field it should not be returned
        assert 'fullname' not in user_with_privacy_enabled, data
        # Users with privacy enabled and disabled, mixed together
        res = self.app.get('/api/user?api_key=' + user.api_key)
        data = json.loads(res.data)
        user_with_privacy_disabled = data[2]
        user_with_privacy_enabled = data[3]
        assert user_with_privacy_disabled['locale'] == 'en', data
        assert user_with_privacy_disabled['fullname'] == 'Public user', data
        assert user_with_privacy_enabled['locale'] == 'en', data
        assert 'fullname' not in user_with_privacy_enabled, data

        # Admin API-KEY should be able to retrieve every field in user
        res = self.app.get('/api/user/3?api_key=' + admin.api_key)
        data = json.loads(res.data)
        user_with_privacy_disabled = data
        # When checking a public field it should be returned
        assert user_with_privacy_disabled['locale'] == 'en', data
        # When checking a private field it should be returned too
        assert user_with_privacy_disabled['fullname'] == 'Public user', data
        # User with privacy enabled
        res = self.app.get('/api/user/4?api_key=' + admin.api_key)
        data = json.loads(res.data)
        user_with_privacy_enabled = data
        # When checking a public field it should be returned
        assert user_with_privacy_enabled['locale'] == 'en', data
        # When checking a private field it should be returned too
        assert user_with_privacy_enabled['fullname'] == 'Private user', data
        # Users with privacy enabled and disabled, mixed together
        res = self.app.get('/api/user?api_key=' + admin.api_key)
        data = json.loads(res.data)
        user_with_privacy_disabled = data[2]
        user_with_privacy_enabled = data[3]
        assert user_with_privacy_disabled['locale'] == 'en', data
        assert user_with_privacy_disabled['fullname'] == 'Public user', data
        assert user_with_privacy_enabled['locale'] == 'en', data
        assert user_with_privacy_enabled['fullname'] == 'Private user', data


    @with_context
    def test_privacy_mode_user_queries(self):
        """Test API user queries for privacy mode with private fields in query
        """
        admin = UserFactory.create()
        user = UserFactory.create()
        # Add user with fullname 'Public user', privacy mode disabled
        user_with_privacy_disabled = UserFactory(email_addr='public@user.com',
                                    name='publicUser', fullname='User',
                                    privacy_mode=False)
        # Add user with fullname 'Private user', privacy mode enabled
        user_with_privacy_enabled = UserFactory(email_addr='private@user.com',
                                    name='privateUser', fullname='User',
                                    privacy_mode=True)

        # When querying with private fields
        query = 'api/user?fullname=User'
        # with no API-KEY, no user with privacy enabled should be returned,
        # even if it matches the query
        res = self.app.get(query)
        data = json.loads(res.data)
        assert len(data) == 1, data
        public_user = data[0]
        assert public_user['name'] == 'publicUser', public_user

        # with a non-admin API-KEY, the result should be the same
        res = self.app.get(query + '&api_key=' + user.api_key)
        data = json.loads(res.data)
        assert len(data) == 1, data
        public_user = data[0]
        assert public_user['name'] == 'publicUser', public_user

        # with an admin API-KEY, all the matching results should be returned
        res = self.app.get(query + '&api_key=' + admin.api_key)
        data = json.loads(res.data)
        assert len(data) == 2, data
        public_user = data[0]
        assert public_user['name'] == 'publicUser', public_user
        private_user = data[1]
        assert private_user['name'] == 'privateUser', private_user

########NEW FILE########
__FILENAME__ = test_vmcp_api
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import json
from base import flask_app, with_context
from mock import patch
from test_api import TestAPI



class TestVmcpAPI(TestAPI):

    @with_context
    def test_vcmp(self):
        """Test VCMP without key fail works."""
        if self.flask_app.config.get('VMCP_KEY'):
            self.flask_app.config.pop('VMCP_KEY')
        res = self.app.get('api/vmcp', follow_redirects=True)
        err = json.loads(res.data)
        assert res.status_code == 501, err
        assert err['status_code'] == 501, err
        assert err['status'] == "failed", err
        assert err['target'] == "vmcp", err
        assert err['action'] == "GET", err

    @with_context
    @patch.dict(flask_app.config, {'VMCP_KEY': 'invalid.key'})
    def test_vmcp_file_not_found(self):
        """Test VMCP with invalid file key works."""
        res = self.app.get('api/vmcp', follow_redirects=True)
        err = json.loads(res.data)
        assert res.status_code == 501, err
        assert err['status_code'] == 501, err
        assert err['status'] == "failed", err
        assert err['target'] == "vmcp", err
        assert err['action'] == "GET", err

    @with_context
    @patch.dict(flask_app.config, {'VMCP_KEY': 'invalid.key'})
    def test_vmcp_01(self):
        """Test VMCP errors works"""
        # Even though the key does not exists, let's patch it to test
        # all the errors
        with patch('os.path.exists', return_value=True):
            res = self.app.get('api/vmcp', follow_redirects=True)
            err = json.loads(res.data)
            assert res.status_code == 415, err
            assert err['status_code'] == 415, err
            assert err['status'] == "failed", err
            assert err['target'] == "vmcp", err
            assert err['action'] == "GET", err
            assert err['exception_msg'] == 'cvm_salt parameter is missing'

    @with_context
    @patch.dict(flask_app.config, {'VMCP_KEY': 'invalid.key'})
    def test_vmcp_02(self):
        """Test VMCP signing works."""
        signature = dict(signature='XX')
        with patch('os.path.exists', return_value=True):
            with patch('pybossa.vmcp.sign', return_value=signature):
                res = self.app.get('api/vmcp?cvm_salt=testsalt',
                                   follow_redirects=True)
                out = json.loads(res.data)
                assert res.status_code == 200, out
                assert out['signature'] == signature['signature'], out

                # Now with a post
                res = self.app.post('api/vmcp?cvm_salt=testsalt',
                                   follow_redirects=True)
                assert res.status_code == 405, res.status_code

########NEW FILE########
__FILENAME__ = test_authentication
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from default import Test, with_context


class TestAuthentication(Test):
    @with_context
    def test_api_authenticate(self):
        """Test AUTHENTICATION works"""
        self.create()
        res = self.app.get('/?api_key=%s' % self.api_key)
        assert 'checkpoint::logged-in::tester' in res.data, res.data

########NEW FILE########
__FILENAME__ = test_blogpost_auth
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from base import Test, db, assert_not_raises
from pybossa.auth import require
from nose.tools import assert_raises
from werkzeug.exceptions import Forbidden, Unauthorized
from mock import patch
from test_authorization import mock_current_user
from factories import AppFactory, BlogpostFactory, UserFactory
from factories import reset_all_pk_sequences



class TestBlogpostAuthorization(Test):

    def setUp(self):
        super(TestBlogpostAuthorization, self).setUp()
        reset_all_pk_sequences()

    mock_anonymous = mock_current_user()
    mock_authenticated = mock_current_user(anonymous=False, admin=False, id=2)
    mock_admin = mock_current_user(anonymous=False, admin=True, id=1)



    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.blogpost.current_user', new=mock_anonymous)
    def test_anonymous_user_create_given_blogpost(self):
        """Test anonymous users cannot create a given blogpost"""

        with self.flask_app.test_request_context('/'):
            app = AppFactory.create()
            blogpost = BlogpostFactory.build(app=app, owner=None)

            assert_raises(Unauthorized, getattr(require, 'blogpost').create, blogpost)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.blogpost.current_user', new=mock_anonymous)
    def test_anonymous_user_create_blogposts_for_given_app(self):
        """Test anonymous users cannot create blogposts for a given app"""

        with self.flask_app.test_request_context('/'):
            app = AppFactory.create()

            assert_raises(Unauthorized, getattr(require, 'blogpost').create, app_id=app.id)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.blogpost.current_user', new=mock_anonymous)
    def test_anonymous_user_create_blogposts(self):
        """Test anonymous users cannot create any blogposts"""

        with self.flask_app.test_request_context('/'):

            assert_raises(Unauthorized, getattr(require, 'blogpost').create)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.blogpost.current_user', new=mock_admin)
    def test_non_owner_authenticated_user_create_given_blogpost(self):
        """Test authenticated user cannot create a given blogpost if is not the
        app owner, even if is admin"""

        with self.flask_app.app_context():
            admin = UserFactory.create()
            app = AppFactory.create()
            blogpost = BlogpostFactory.build(app=app, owner=admin)

            assert self.mock_admin.id != app.owner.id
            assert_raises(Forbidden, getattr(require, 'blogpost').create, blogpost)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.blogpost.current_user', new=mock_admin)
    def test_non_owner_authenticated_user_create_blogpost_for_given_app(self):
        """Test authenticated user cannot create blogposts for a given app
        if is not the app owner, even if is admin"""

        with self.flask_app.app_context():
            owner = UserFactory.create_batch(2)[1]
            app = AppFactory.create(owner=owner)

            assert self.mock_admin.id != app.owner.id
            assert_raises(Forbidden, getattr(require, 'blogpost').create, app_id=app.id)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_owner_create_given_blogpost(self):
        """Test authenticated user can create a given blogpost if is app owner"""

        with self.flask_app.test_request_context('/'):
            owner = UserFactory.create_batch(2)[1]
            app = AppFactory.create(owner=owner)
            blogpost = BlogpostFactory.build(app=app, owner=owner)

            assert self.mock_authenticated.id == app.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').create, blogpost)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_owner_create_blogpost_for_given_app(self):
        """Test authenticated user can create blogposts for a given app
        if is app owner"""

        with self.flask_app.test_request_context('/'):
            owner = UserFactory.create_batch(2)[1]
            app = AppFactory.create(owner=owner)

            assert self.mock_authenticated.id == app.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').create, app_id=app.id)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_owner_create_blogpost_as_other_user(self):
        """Test authenticated user cannot create blogpost if is app owner but
        sets another person as the author of the blogpost"""

        with self.flask_app.test_request_context('/'):
            another_user = UserFactory.create()
            app = AppFactory.create()
            blogpost = BlogpostFactory.build(app_id=app.id,
                                              owner=another_user)

            assert self.mock_authenticated.id == app.owner.id
            assert_raises(Forbidden, getattr(require, 'blogpost').create, blogpost)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.blogpost.current_user', new=mock_anonymous)
    def test_anonymous_user_read_given_blogpost(self):
        """Test anonymous users can read a given blogpost"""

        with self.flask_app.test_request_context('/'):
            app = AppFactory.create()
            blogpost = BlogpostFactory.create(app=app)

            assert_not_raises(Exception, getattr(require, 'blogpost').read, blogpost)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.blogpost.current_user', new=mock_anonymous)
    def test_anonymous_user_read_blogposts_for_given_app(self):
        """Test anonymous users can read blogposts of a given app"""

        with self.flask_app.test_request_context('/'):
            app = AppFactory.create()
            assert_not_raises(Exception, getattr(require, 'blogpost').read, app_id=app.id)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.blogpost.current_user', new=mock_anonymous)
    def test_anonymous_user_read_given_blogpost_hidden_app(self):
        """Test anonymous users cannot read a given blogpost of a hidden app"""

        with self.flask_app.test_request_context('/'):
            app = AppFactory.create(hidden=1)
            blogpost = BlogpostFactory.create(app=app)

            assert_raises(Unauthorized, getattr(require, 'blogpost').read, blogpost)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.blogpost.current_user', new=mock_anonymous)
    def test_anonymous_user_read_blogposts_for_given_hidden_app(self):
        """Test anonymous users cannot read blogposts of a given app if is hidden"""

        with self.flask_app.test_request_context('/'):
            app = AppFactory.create(hidden=1)

            assert_raises(Unauthorized, getattr(require, 'blogpost').read, app_id=app.id)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_non_owner_authenticated_user_read_given_blogpost(self):
        """Test authenticated user can read a given blogpost if is not the app owner"""

        with self.flask_app.test_request_context('/'):
            app = AppFactory.create()
            user = UserFactory.create()
            blogpost = BlogpostFactory.create(app=app)

            assert self.mock_authenticated.id != app.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').read, blogpost)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_non_owner_authenticated_user_read_blogposts_for_given_app(self):
        """Test authenticated user can read blogposts of a given app if
        is not the app owner"""

        with self.flask_app.test_request_context('/'):
            app = AppFactory.create()
            user = UserFactory.create()

            assert self.mock_authenticated.id != app.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').read, app_id=app.id)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_non_owner_authenticated_user_read_given_blogpost_hidden_app(self):
        """Test authenticated user cannot read a given blogpost of a hidden app
        if is not the app owner"""

        with self.flask_app.test_request_context('/'):
            app = AppFactory.create(hidden=1)
            user = UserFactory.create()
            blogpost = BlogpostFactory.create(app=app)

            assert self.mock_authenticated.id != app.owner.id
            assert_raises(Forbidden, getattr(require, 'blogpost').read, blogpost)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_non_owner_authenticated_user_read_blogposts_for_given_hidden_app(self):
        """Test authenticated user cannot read blogposts of a given app if is
        hidden and is not the app owner"""

        with self.flask_app.test_request_context('/'):
            app = AppFactory.create(hidden=1)
            user = UserFactory.create()

            assert self.mock_authenticated.id != app.owner.id
            assert_raises(Forbidden, getattr(require, 'blogpost').read, app_id=app.id)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_owner_read_given_blogpost(self):
        """Test authenticated user can read a given blogpost if is the app owner"""

        with self.flask_app.test_request_context('/'):
            owner = UserFactory.create_batch(2)[1]
            app = AppFactory.create(owner=owner)
            blogpost = BlogpostFactory.create(app=app)

            assert self.mock_authenticated.id == app.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').read, blogpost)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_owner_read_blogposts_for_given_app(self):
        """Test authenticated user can read blogposts of a given app if is the
        app owner"""

        with self.flask_app.test_request_context('/'):
            owner = UserFactory.create_batch(2)[1]
            app = AppFactory.create(owner=owner)

            assert self.mock_authenticated.id == app.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').read, app_id=app.id)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_owner_read_given_blogpost_hidden_app(self):
        """Test authenticated user can read a given blogpost of a hidden app if
        is the app owner"""

        with self.flask_app.test_request_context('/'):
            owner = UserFactory.create_batch(2)[1]
            app = AppFactory.create(owner=owner, hidden=1)
            blogpost = BlogpostFactory.create(app=app)

            assert self.mock_authenticated.id == app.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').read, blogpost)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_owner_read_blogposts_for_given_hidden_app(self):
        """Test authenticated user can read blogposts of a given hidden app if
        is the app owner"""

        with self.flask_app.test_request_context('/'):
            owner = UserFactory.create_batch(2)[1]
            app = AppFactory.create(owner=owner, hidden=1)

            assert self.mock_authenticated.id == app.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').read, app_id=app.id)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.blogpost.current_user', new=mock_admin)
    def test_admin_read_given_blogpost_hidden_app(self):
        """Test admin can read a given blogpost of a hidden app"""

        with self.flask_app.test_request_context('/'):
            admin = UserFactory.create()
            app = AppFactory.create(hidden=1)
            blogpost = BlogpostFactory.create(app=app)

            assert self.mock_admin.id != app.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').read, blogpost)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.blogpost.current_user', new=mock_admin)
    def test_admin_read_blogposts_for_given_hidden_app(self):
        """Test admin can read blogposts of a given hidden app"""

        with self.flask_app.test_request_context('/'):
            admin = UserFactory.create()
            app = AppFactory.create(hidden=1)

            assert self.mock_admin.id != app.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').read, app_id=app.id)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.blogpost.current_user', new=mock_anonymous)
    def test_anonymous_user_update_blogpost(self):
        """Test anonymous users cannot update blogposts"""

        with self.flask_app.test_request_context('/'):
            blogpost = BlogpostFactory.create()

            assert_raises(Unauthorized, getattr(require, 'blogpost').update, blogpost)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.blogpost.current_user', new=mock_admin)
    def test_non_owner_authenticated_user_update_blogpost(self):
        """Test authenticated user cannot update a blogpost if is not the post
        owner, even if is admin"""

        with self.flask_app.test_request_context('/'):
            admin = UserFactory.create()
            app = AppFactory.create()
            blogpost = BlogpostFactory.create(app=app)

            assert self.mock_admin.id != blogpost.owner.id
            assert_raises(Forbidden, getattr(require, 'blogpost').update, blogpost)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_owner_update_blogpost(self):
        """Test authenticated user can update blogpost if is the post owner"""

        with self.flask_app.test_request_context('/'):
            owner = UserFactory.create_batch(2)[1]
            app = AppFactory.create()
            blogpost = BlogpostFactory.create(app=app, owner=owner)

            assert self.mock_authenticated.id == blogpost.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').update, blogpost)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.blogpost.current_user', new=mock_anonymous)
    def test_anonymous_user_delete_blogpost(self):
        """Test anonymous users cannot delete blogposts"""

        with self.flask_app.test_request_context('/'):
            blogpost = BlogpostFactory.create()

            assert_raises(Unauthorized, getattr(require, 'blogpost').delete, blogpost)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_non_owner_authenticated_user_delete_blogpost(self):
        """Test authenticated user cannot delete a blogpost if is not the post
        owner and is not admin"""

        with self.flask_app.test_request_context('/'):
            blogpost = BlogpostFactory.create()

            assert self.mock_authenticated.id != blogpost.owner.id
            assert not self.mock_authenticated.admin
            assert_raises(Forbidden, getattr(require, 'blogpost').delete, blogpost)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.blogpost.current_user', new=mock_authenticated)
    def test_owner_delete_blogpost(self):
        """Test authenticated user can delete a blogpost if is the post owner"""

        with self.flask_app.test_request_context('/'):
            owner = UserFactory.create_batch(2)[1]
            app = AppFactory.create()
            blogpost = BlogpostFactory.create(app=app, owner=owner)

            assert self.mock_authenticated.id == blogpost.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').delete, blogpost)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.blogpost.current_user', new=mock_admin)
    def test_admin_authenticated_user_delete_blogpost(self):
        """Test authenticated user can delete any blogpost if is admin"""

        with self.flask_app.test_request_context('/'):
            admin = UserFactory.create()
            blogpost = BlogpostFactory.create()

            assert self.mock_admin.id != blogpost.owner.id
            assert_not_raises(Exception, getattr(require, 'blogpost').delete, blogpost)

########NEW FILE########
__FILENAME__ = test_taskrun_auth
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from base import Test, db, assert_not_raises
from pybossa.auth import require
from nose.tools import assert_raises
from werkzeug.exceptions import Forbidden, Unauthorized
from mock import patch
from test_authorization import mock_current_user
from factories import (AppFactory, AnonymousTaskRunFactory,
                       TaskFactory, TaskRunFactory, UserFactory)
from factories import reset_all_pk_sequences



class TestTaskrunAuthorization(Test):

    def setUp(self):
        super(TestTaskrunAuthorization, self).setUp()
        reset_all_pk_sequences()


    mock_anonymous = mock_current_user()
    mock_authenticated = mock_current_user(anonymous=False, admin=False, id=2)
    mock_admin = mock_current_user(anonymous=False, admin=True, id=1)


    def configure_fixtures(self):
        self.app = db.session.query(App).first()
        self.root = db.session.query(User).first()
        self.user1 = db.session.query(User).get(2)
        self.user2 = db.session.query(User).get(3)
        self.task = Task(app_id=self.app.id, state='0', n_answers=10)
        self.task.app = self.app
        db.session.add(self.task)
        db.session.commit()


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_create_first_taskrun(self):
        """Test anonymous user can create a taskrun for a given task if he
        hasn't already done it"""

        with self.flask_app.test_request_context('/'):
            taskrun = AnonymousTaskRunFactory.build()

            assert_not_raises(Exception,
                          getattr(require, 'taskrun').create,
                          taskrun)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_create_repeated_taskrun(self):
        """Test anonymous user cannot create a taskrun for a task to which
        he has previously posted a taskrun"""

        with self.flask_app.test_request_context('/'):
            task = TaskFactory.create()
            taskrun1 = AnonymousTaskRunFactory.create(task=task)
            taskrun2 = AnonymousTaskRunFactory.build(task=task)
            assert_raises(Forbidden,
                        getattr(require, 'taskrun').create,
                        taskrun2)

            # But the user can still create taskruns for different tasks
            task2 = TaskFactory.create(app=task.app)
            taskrun3 = AnonymousTaskRunFactory.build(task=task2)
            assert_not_raises(Exception,
                          getattr(require, 'taskrun').create,
                          taskrun3)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_create_first_taskrun(self):
        """Test authenticated user can create a taskrun for a given task if he
        hasn't already done it"""

        with self.flask_app.test_request_context('/'):
            taskrun = TaskRunFactory.build()

            assert self.mock_authenticated.id == taskrun.user.id
            assert_not_raises(Exception,
                          getattr(require, 'taskrun').create,
                          taskrun)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_create_repeated_taskrun(self):
        """Test authenticated user cannot create a taskrun for a task to which
        he has previously posted a taskrun"""

        with self.flask_app.test_request_context('/'):
            task = TaskFactory.create()
            taskrun1 = TaskRunFactory.create(task=task)
            taskrun2 = TaskRunFactory.build(task=task, user=taskrun1.user)

            assert self.mock_authenticated.id == taskrun1.user.id
            assert_raises(Forbidden, getattr(require, 'taskrun').create, taskrun2)

            # But the user can still create taskruns for different tasks
            task2 = TaskFactory.create(app=task.app)
            taskrun3 = TaskRunFactory.build(task=task2, user=taskrun1.user)

            assert self.mock_authenticated.id == taskrun3.user.id
            assert_not_raises(Exception,
                          getattr(require, 'taskrun').create,
                          taskrun3)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_read(self):
        """Test anonymous user can read any taskrun"""

        with self.flask_app.test_request_context('/'):
            anonymous_taskrun = AnonymousTaskRunFactory.create()
            user_taskrun = TaskRunFactory.create()

            assert_not_raises(Exception,
                          getattr(require, 'taskrun').read,
                          anonymous_taskrun)
            assert_not_raises(Exception,
                          getattr(require, 'taskrun').read,
                          user_taskrun)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_read(self):
        """Test authenticated user can read any taskrun"""

        with self.flask_app.test_request_context('/'):
            own_taskrun = TaskRunFactory.create()
            anonymous_taskrun = AnonymousTaskRunFactory.create()
            other_users_taskrun = TaskRunFactory.create()

            assert self.mock_authenticated.id == own_taskrun.user.id
            assert self.mock_authenticated.id != other_users_taskrun.user.id
            assert_not_raises(Exception,
                          getattr(require, 'taskrun').read,
                          anonymous_taskrun)
            assert_not_raises(Exception,
                          getattr(require, 'taskrun').read,
                          other_users_taskrun)
            assert_not_raises(Exception,
                          getattr(require, 'taskrun').read,
                          own_taskrun)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_update_anoymous_taskrun(self):
        """Test anonymous users cannot update an anonymously posted taskrun"""

        with self.flask_app.test_request_context('/'):
            anonymous_taskrun = AnonymousTaskRunFactory.create()

            assert_raises(Unauthorized,
                          getattr(require, 'taskrun').update,
                          anonymous_taskrun)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_update_anonymous_taskrun(self):
        """Test authenticated users cannot update an anonymously posted taskrun"""

        with self.flask_app.test_request_context('/'):
            anonymous_taskrun = AnonymousTaskRunFactory.create()

            assert_raises(Forbidden,
                          getattr(require, 'taskrun').update,
                          anonymous_taskrun)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.taskrun.current_user', new=mock_admin)
    def test_admin_update_anonymous_taskrun(self):
        """Test admins cannot update anonymously posted taskruns"""

        with self.flask_app.test_request_context('/'):
            anonymous_taskrun = AnonymousTaskRunFactory.create()

            assert_raises(Forbidden,
                          getattr(require, 'taskrun').update,
                          anonymous_taskrun)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_update_user_taskrun(self):
        """Test anonymous user cannot update taskruns posted by authenticated users"""
        with self.flask_app.test_request_context('/'):
            user_taskrun = TaskRunFactory.create()

            assert_raises(Unauthorized,
                          getattr(require, 'taskrun').update,
                          user_taskrun)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_update_other_users_taskrun(self):
        """Test authenticated user cannot update any user taskrun"""

        with self.flask_app.test_request_context('/'):
            own_taskrun = TaskRunFactory.create()
            other_users_taskrun = TaskRunFactory.create()

            assert self.mock_authenticated.id == own_taskrun.user.id
            assert self.mock_authenticated.id != other_users_taskrun.user.id
            assert_raises(Forbidden,
                          getattr(require, 'taskrun').update,
                          own_taskrun)
            assert_raises(Forbidden,
                          getattr(require, 'taskrun').update,
                          other_users_taskrun)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.taskrun.current_user', new=mock_admin)
    def test_admin_update_user_taskrun(self):
        """Test admins cannot update taskruns posted by authenticated users"""

        with self.flask_app.test_request_context('/'):
            user_taskrun = TaskRunFactory.create()

            assert self.mock_admin.id != user_taskrun.user.id
            assert_raises(Forbidden,
                          getattr(require, 'taskrun').update,
                          user_taskrun)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_delete_anonymous_taskrun(self):
        """Test anonymous users cannot delete an anonymously posted taskrun"""

        with self.flask_app.test_request_context('/'):
            anonymous_taskrun = AnonymousTaskRunFactory.create()

            assert_raises(Unauthorized,
                          getattr(require, 'taskrun').delete,
                          anonymous_taskrun)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_delete_anonymous_taskrun(self):
        """Test authenticated users cannot delete an anonymously posted taskrun"""

        with self.flask_app.test_request_context('/'):
            anonymous_taskrun = AnonymousTaskRunFactory.create()

            assert_raises(Forbidden,
                          getattr(require, 'taskrun').delete,
                          anonymous_taskrun)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.taskrun.current_user', new=mock_admin)
    def test_admin_delete_anonymous_taskrun(self):
        """Test admins can delete anonymously posted taskruns"""

        with self.flask_app.test_request_context('/'):
            anonymous_taskrun = AnonymousTaskRunFactory.create()

            assert_not_raises(Exception,
                          getattr(require, 'taskrun').delete,
                          anonymous_taskrun)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_delete_user_taskrun(self):
        """Test anonymous user cannot delete taskruns posted by authenticated users"""

        with self.flask_app.test_request_context('/'):
            user_taskrun = TaskRunFactory.create()

            assert_raises(Unauthorized,
                      getattr(require, 'taskrun').delete,
                      user_taskrun)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_delete_other_users_taskrun(self):
        """Test authenticated user cannot delete a taskrun if it was created
        by another authenticated user, but can delete his own taskruns"""

        with self.flask_app.test_request_context('/'):
            own_taskrun = TaskRunFactory.create()
            other_users_taskrun = TaskRunFactory.create()

            assert self.mock_authenticated.id == own_taskrun.user.id
            assert self.mock_authenticated.id != other_users_taskrun.user.id
            assert_not_raises(Exception,
                      getattr(require, 'taskrun').delete,
                      own_taskrun)
            assert_raises(Forbidden,
                      getattr(require, 'taskrun').delete,
                      other_users_taskrun)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.taskrun.current_user', new=mock_admin)
    def test_admin_delete_user_taskrun(self):
        """Test admins can delete taskruns posted by authenticated users"""

        with self.flask_app.test_request_context('/'):
            user_taskrun = TaskRunFactory.create()

            assert self.mock_admin.id != user_taskrun.user.id
            assert_not_raises(Exception,
                      getattr(require, 'taskrun').delete,
                      user_taskrun)

########NEW FILE########
__FILENAME__ = test_token_auth
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from base import Test
from pybossa.auth import require
from nose.tools import assert_raises
from werkzeug.exceptions import Forbidden, Unauthorized
from mock import patch
from test_authorization import mock_current_user



class TestTokenAuthorization(Test):

    auth_providers = ('twitter', 'facebook', 'google')
    mock_anonymous = mock_current_user()
    mock_authenticated = mock_current_user(anonymous=False, admin=False, id=2)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_delete(self):
        """Test anonymous user is not allowed to delete an oauth token"""
        with self.flask_app.test_request_context('/'):
            for token in self.auth_providers:
                assert_raises(Unauthorized,
                          getattr(require, 'token').delete,
                          token)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_delete(self):
        """Test authenticated user is not allowed to delete an oauth token"""
        with self.flask_app.test_request_context('/'):
            for token in self.auth_providers:
                assert_raises(Forbidden,
                          getattr(require, 'token').delete,
                          token)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_create(self):
        """Test anonymous user is not allowed to create an oauth token"""
        with self.flask_app.test_request_context('/'):
            for token in self.auth_providers:
                assert_raises(Unauthorized,
                          getattr(require, 'token').create,
                          token)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_create(self):
        """Test authenticated user is not allowed to create an oauth token"""
        with self.flask_app.test_request_context('/'):
            for token in self.auth_providers:
                assert_raises(Forbidden,
                          getattr(require, 'token').create,
                          token)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_update(self):
        """Test anonymous user is not allowed to update an oauth token"""
        with self.flask_app.test_request_context('/'):
            for token in self.auth_providers:
                assert_raises(Unauthorized,
                          getattr(require, 'token').update,
                          token)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_update(self):
        """Test authenticated user is not allowed to update an oauth token"""
        with self.flask_app.test_request_context('/'):
            for token in self.auth_providers:
                assert_raises(Forbidden,
                          getattr(require, 'token').update,
                          token)


    @patch('pybossa.auth.current_user', new=mock_anonymous)
    @patch('pybossa.auth.taskrun.current_user', new=mock_anonymous)
    def test_anonymous_user_read(self):
        """Test anonymous user is not allowed to read an oauth token"""
        with self.flask_app.test_request_context('/'):
            for token in self.auth_providers:
                assert_raises(Unauthorized,
                          getattr(require, 'token').read,
                          token)


    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_read(self):
        """Test authenticated user is allowed to read his own oauth tokens"""
        with self.flask_app.test_request_context('/'):
            for token in self.auth_providers:
                assert_raises(Forbidden,
                          getattr(require, 'token').read,
                          token)

########NEW FILE########
__FILENAME__ = test_cache_apps
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from default import Test, db, with_context
from pybossa.model.app import App
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun
from pybossa.model.user import User
from pybossa.model.featured import Featured
from pybossa.cache import apps as cached_apps


class TestAppsCache(Test):

    @with_context
    def setUp(self):
        super(TestAppsCache, self).setUp()
        self.user = self.create_users()[0]
        db.session.add(self.user)
        db.session.commit()


    def create_app_with_tasks(self, completed_tasks, ongoing_tasks):
        app = App(name='my_app',
                  short_name='my_app_shortname',
                  description=u'description')
        app.owner = self.user
        db.session.add(app)
        for i in range(completed_tasks):
            task = Task(app_id = 1, state = 'completed', n_answers=3)
            db.session.add(task)
        for i in range(ongoing_tasks):
            task = Task(app_id = 1, state = 'ongoing', n_answers=3)
            db.session.add(task)
        db.session.commit()
        return app

    def create_app_with_contributors(self, anonymous, registered, two_tasks=False, name='my_app'):
        app = App(name=name,
                  short_name='%s_shortname' % name,
                  description=u'description')
        app.owner = self.user
        db.session.add(app)
        task = Task(app=app)
        db.session.add(task)
        if two_tasks:
            task2 = Task(app=app)
            db.session.add(task2)
        db.session.commit()
        for i in range(anonymous):
            task_run = TaskRun(app_id = app.id,
                               task_id = 1,
                               user_ip = '127.0.0.%s' % i)
            db.session.add(task_run)
            if two_tasks:
                task_run2 = TaskRun(app_id = app.id,
                               task_id = 2,
                               user_ip = '127.0.0.%s' % i)
                db.session.add(task_run2)
        for i in range(registered):
            user = User(email_addr = "%s@a.com" % i,
                        name = "user%s" % i,
                        passwd_hash = "1234%s" % i,
                        fullname = "user_fullname%s" % i)
            db.session.add(user)
            task_run = TaskRun(app_id = app.id,
                               task_id = 1,
                               user = user)
            db.session.add(task_run)
            if two_tasks:
                task_run2 = TaskRun(app_id = app.id,
                               task_id = 2,
                               user = user)
                db.session.add(task_run2)
        db.session.commit()
        return app


    @with_context
    def test_get_featured_front_page(self):
        """Test CACHE APPS get_featured_front_page returns featured apps"""

        app = self.create_app(None)
        app.owner = self.user
        db.session.add(app)
        featured = Featured(app=app)
        db.session.add(featured)
        db.session.commit()

        featured = cached_apps.get_featured_front_page()

        assert len(featured) is 1, featured


    @with_context
    def test_get_featured_front_page_only_returns_featured(self):
        """Test CACHE APPS get_featured_front_page returns only featured apps"""

        featured_app = self.create_app(None)
        non_featured_app = self.create_app(None)
        non_featured_app.name = 'other_app'
        non_featured_app.short_name = 'other_app'
        featured_app.owner = self.user
        non_featured_app.owner = self.user
        db.session.add(featured_app)
        db.session.add(non_featured_app)
        featured = Featured(app=featured_app)
        db.session.add(featured)
        db.session.commit()

        featured = cached_apps.get_featured_front_page()

        assert len(featured) is 1, featured


    @with_context
    def test_get_featured_front_page_not_returns_hidden_apps(self):
        """Test CACHE APPS get_featured_front_page does not return hidden apps"""

        featured_app = self.create_app(None)
        featured_app.owner = self.user
        featured_app.hidden = 1
        db.session.add(featured_app)
        featured = Featured(app=featured_app)
        db.session.add(featured)
        db.session.commit()

        featured = cached_apps.get_featured_front_page()

        assert len(featured) is 0, featured


    @with_context
    def test_get_featured_front_page_returns_required_fields(self):
        """Test CACHE APPS get_featured_front_page returns the required info
        about each featured app"""

        app = self.create_app(None)
        app.owner = self.user
        db.session.add(app)
        featured = Featured(app=app)
        db.session.add(featured)
        db.session.commit()
        fields = ('id', 'name', 'short_name', 'info', 'n_volunteers', 'n_completed_tasks')

        featured = cached_apps.get_featured_front_page()[0]

        for field in fields:
            assert featured.has_key(field), "%s not in app info" % field


    @with_context
    def test_get_top_returns_apps_with_most_taskruns(self):
        """Test CACHE APPS get_top returns the apps with most taskruns in order"""

        ranked_3_app = self.create_app_with_contributors(8, 0, name='three')
        ranked_2_app = self.create_app_with_contributors(9, 0, name='two')
        ranked_1_app = self.create_app_with_contributors(10, 0, name='one')
        ranked_4_app = self.create_app_with_contributors(7, 0, name='four')

        top_apps = cached_apps.get_top()

        assert top_apps[0]['name'] == 'one', top_apps
        assert top_apps[1]['name'] == 'two', top_apps
        assert top_apps[2]['name'] == 'three', top_apps
        assert top_apps[3]['name'] == 'four', top_apps


    @with_context
    def test_get_top_respects_limit(self):
        """Test CACHE APPS get_top returns only the top n apps"""

        ranked_3_app = self.create_app_with_contributors(8, 0, name='three')
        ranked_2_app = self.create_app_with_contributors(9, 0, name='two')
        ranked_1_app = self.create_app_with_contributors(10, 0, name='one')
        ranked_4_app = self.create_app_with_contributors(7, 0, name='four')

        top_apps = cached_apps.get_top(n=2)

        assert len(top_apps) is 2, len(top_apps)


    @with_context
    def test_get_top_returns_four_apps_by_default(self):
        """Test CACHE APPS get_top returns the top 4 apps by default"""

        ranked_3_app = self.create_app_with_contributors(8, 0, name='three')
        ranked_2_app = self.create_app_with_contributors(9, 0, name='two')
        ranked_1_app = self.create_app_with_contributors(10, 0, name='one')
        ranked_4_app = self.create_app_with_contributors(7, 0, name='four')
        ranked_5_app = self.create_app_with_contributors(7, 0, name='five')

        top_apps = cached_apps.get_top()

        assert len(top_apps) is 4, len(top_apps)


    @with_context
    def test_get_top_doesnt_return_hidden_apps(self):
        """Test CACHE APPS get_top does not return apps that are hidden"""

        ranked_3_app = self.create_app_with_contributors(8, 0, name='three')
        ranked_2_app = self.create_app_with_contributors(9, 0, name='two')
        ranked_1_app = self.create_app_with_contributors(10, 0, name='one')
        hidden_app = self.create_app_with_contributors(11, 0, name='hidden')
        hidden_app.hidden = 1
        db.session.add(hidden_app)
        db.session.commit()

        top_apps = cached_apps.get_top()

        assert len(top_apps) is 3, len(top_apps)
        for app in top_apps:
            assert app['name'] != 'hidden', app['name']

    @with_context
    def test_n_completed_tasks_no_completed_tasks(self):
        """Test CACHE APPS n_completed_tasks returns 0 if no completed tasks"""

        app = self.create_app_with_tasks(completed_tasks=0, ongoing_tasks=5)
        completed_tasks = cached_apps.n_completed_tasks(app.id)

        err_msg = "Completed tasks is %s, it should be 0" % completed_tasks
        assert completed_tasks == 0, err_msg


    @with_context
    def test_n_completed_tasks_with_completed_tasks(self):
        """Test CACHE APPS n_completed_tasks returns number of completed tasks
        if there are any"""

        app = self.create_app_with_tasks(completed_tasks=5, ongoing_tasks=5)
        completed_tasks = cached_apps.n_completed_tasks(app.id)

        err_msg = "Completed tasks is %s, it should be 5" % completed_tasks
        assert completed_tasks == 5, err_msg


    @with_context
    def test_n_completed_tasks_with_all_tasks_completed(self):
        """Test CACHE APPS n_completed_tasks returns number of tasks if all
        tasks are completed"""

        app = self.create_app_with_tasks(completed_tasks=4, ongoing_tasks=0)
        completed_tasks = cached_apps.n_completed_tasks(app.id)

        err_msg = "Completed tasks is %s, it should be 4" % completed_tasks
        assert completed_tasks == 4, err_msg


    @with_context
    def test_n_registered_volunteers(self):
        """Test CACHE APPS n_registered_volunteers returns number of volunteers
        that contributed to an app when each only submited one task run"""

        app = self.create_app_with_contributors(anonymous=0, registered=3)
        registered_volunteers = cached_apps.n_registered_volunteers(app.id)

        err_msg = "Volunteers is %s, it should be 3" % registered_volunteers
        assert registered_volunteers == 3, err_msg


    @with_context
    def test_n_registered_volunteers_with_more_than_one_taskrun(self):
        """Test CACHE APPS n_registered_volunteers returns number of volunteers
        that contributed to an app when any submited more than one task run"""

        app = self.create_app_with_contributors(anonymous=0, registered=2, two_tasks=True)
        registered_volunteers = cached_apps.n_registered_volunteers(app.id)

        err_msg = "Volunteers is %s, it should be 2" % registered_volunteers
        assert registered_volunteers == 2, err_msg


    @with_context
    def test_n_anonymous_volunteers(self):
        """Test CACHE APPS n_anonymous_volunteers returns number of volunteers
        that contributed to an app when each only submited one task run"""

        app = self.create_app_with_contributors(anonymous=3, registered=0)
        anonymous_volunteers = cached_apps.n_anonymous_volunteers(app.id)

        err_msg = "Volunteers is %s, it should be 3" % anonymous_volunteers
        assert anonymous_volunteers == 3, err_msg


    @with_context
    def test_n_anonymous_volunteers_with_more_than_one_taskrun(self):
        """Test CACHE APPS n_anonymous_volunteers returns number of volunteers
        that contributed to an app when any submited more than one task run"""

        app = self.create_app_with_contributors(anonymous=2, registered=0, two_tasks=True)
        anonymous_volunteers = cached_apps.n_anonymous_volunteers(app.id)

        err_msg = "Volunteers is %s, it should be 2" % anonymous_volunteers
        assert anonymous_volunteers == 2, err_msg


    @with_context
    def test_n_volunteers(self):
        """Test CACHE APPS n_volunteers returns the sum of the anonymous 
        plus registered volunteers that contributed to an app"""

        app = self.create_app_with_contributors(anonymous=2, registered=3, two_tasks=True)
        total_volunteers = cached_apps.n_volunteers(app.id)

        err_msg = "Volunteers is %s, it should be 5" % total_volunteers
        assert total_volunteers == 5, err_msg

########NEW FILE########
__FILENAME__ = test_cache_helpers
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from default import Test, db, with_context
from factories import (AppFactory, TaskFactory, TaskRunFactory,
                      AnonymousTaskRunFactory, UserFactory)
from pybossa.cache import helpers


class TestHelpersCache(Test):

    def test_n_available_tasks_no_tasks_authenticated_user(self):
        """Test n_available_tasks returns 0 for authenticated user if the app
        has no tasks"""
        app = AppFactory.create()

        n_available_tasks = helpers.n_available_tasks(app.id, user_id=1)

        assert n_available_tasks == 0, n_available_tasks


    def test_n_available_tasks_no_tasks_anonymous_user(self):
        """Test n_available_tasks returns 0 for anonymous user if the app
        has no tasks"""
        app = AppFactory.create()

        n_available_tasks = helpers.n_available_tasks(app.id, user_ip='127.0.0.1')

        assert n_available_tasks == 0, n_available_tasks


    def test_n_available_tasks_no_taskruns_authenticated_user(self):
        """Test n_available_tasks returns 1 for authenticated user
        if there are no taskruns"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app)

        n_available_tasks = helpers.n_available_tasks(app.id, user_id=1)

        assert n_available_tasks == 1, n_available_tasks


    def test_n_available_tasks_no_taskruns_anonymous_user(self):
        """Test n_available_tasks returns 1 for anonymous user
        if there are no taskruns"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app)

        n_available_tasks = helpers.n_available_tasks(app.id, user_ip='127.0.0.1')

        assert n_available_tasks == 1, n_available_tasks


    def test_n_available_tasks_all_tasks_completed_authenticated_user(self):
        """Test n_available_tasks returns 0 for authenticated user if all the
        tasks are completed"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app, state='completed')

        n_available_tasks = helpers.n_available_tasks(app.id, user_id=1)

        assert n_available_tasks == 0, n_available_tasks


    def test_n_available_tasks_all_tasks_completed_anonymous_user(self):
        """Test n_available_tasks returns 0 for anonymous user if all the
        tasks are completed"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app, state='completed')

        n_available_tasks = helpers.n_available_tasks(app.id, user_ip='127.0.0.1')

        assert n_available_tasks == 0, n_available_tasks


    def test_n_available_tasks_all_tasks_answered_by_authenticated_user(self):
        """Test n_available_tasks returns 0 for authenticated user if he has
        submitted taskruns for all the tasks"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app, n_answers=2)
        user = UserFactory.create()
        taskrun = TaskRunFactory.create(task=task, user=user)

        n_available_tasks = helpers.n_available_tasks(app.id, user_id=user.id)

        assert task.state != 'completed', task.state
        assert n_available_tasks == 0, n_available_tasks


    def test_n_available_tasks_all_tasks_answered_by_anonymous_user(self):
        """Test n_available_tasks returns 0 for anonymous user if he has
        submitted taskruns for all the tasks"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app, n_answers=2)
        taskrun = AnonymousTaskRunFactory.create(task=task)

        n_available_tasks = helpers.n_available_tasks(app.id, user_ip=taskrun.user_ip)

        assert task.state != 'completed', task.state
        assert n_available_tasks == 0, n_available_tasks


    def test_n_available_tasks_some_tasks_answered_by_authenticated_user(self):
        """Test n_available_tasks returns 1 for authenticated user if he has
        submitted taskruns for one of the tasks but there is still another task"""
        app = AppFactory.create()
        answered_task = TaskFactory.create(app=app)
        available_task = TaskFactory.create(app=app)
        user = UserFactory.create()
        taskrun = TaskRunFactory.create(task=answered_task, user=user)

        n_available_tasks = helpers.n_available_tasks(app.id, user_id=user.id)
        assert n_available_tasks == 1, n_available_tasks


    def test_n_available_some_all_tasks_answered_by_anonymous_user(self):
        """Test n_available_tasks returns 1 for anonymous user if he has
        submitted taskruns for one of the tasks but there is still another task"""
        app = AppFactory.create()
        answered_task = TaskFactory.create(app=app)
        available_task = TaskFactory.create(app=app)
        taskrun = AnonymousTaskRunFactory.create(task=answered_task)

        n_available_tasks = helpers.n_available_tasks(app.id, user_ip=taskrun.user_ip)

        assert n_available_tasks == 1, n_available_tasks


    def test_n_available_tasks_task_answered_by_another_user(self):
        """Test n_available_tasks returns 1 for a user if another
        user has submitted taskruns for the task but he hasn't"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app)
        user = UserFactory.create()
        taskrun = TaskRunFactory.create(task=task)

        n_available_tasks = helpers.n_available_tasks(app.id, user_id=user.id)
        assert n_available_tasks == 1, n_available_tasks


    def test_check_contributing_state_completed(self):
        """Test check_contributing_state returns 'completed' for an app with all
        tasks completed and user that has contributed to it"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app, n_answers=1)
        user = UserFactory.create()
        TaskRunFactory.create_batch(1, task=task, user=user)

        contributing_state = helpers.check_contributing_state(app_id=app.id,
                                                              user_id=user.id)

        assert task.state == 'completed', task.state
        assert contributing_state == 'completed', contributing_state


    def test_check_contributing_state_completed_user_not_contributed(self):
        """Test check_contributing_state returns 'completed' for an app with all
        tasks completed even if the user has not contributed to it"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app, n_answers=2)
        TaskRunFactory.create_batch(2, task=task)
        user = UserFactory.create()

        contributing_state = helpers.check_contributing_state(app_id=app.id,
                                                              user_id=user.id)

        assert task.state == 'completed', task.state
        assert contributing_state == 'completed', contributing_state


    def test_check_contributing_state_ongoing_tasks_not_contributed(self):
        """Test check_contributing_state returns 'can_contribute' for an app
        with ongoing tasks a user has not contributed to"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app)
        user = UserFactory.create()

        contributing_state = helpers.check_contributing_state(app_id=app.id,
                                                              user_id=user.id)

        assert contributing_state == 'can_contribute', contributing_state


    def test_check_contributing_state_ongoing_tasks_contributed(self):
        """Test check_contributing_state returns 'cannot_contribute' for an app
        with ongoing tasks to which the user has already contributed"""
        app = AppFactory.create()
        task = TaskFactory.create(app=app, n_answers=3)
        user = UserFactory.create()
        TaskRunFactory.create(task=task, user=user)
        contributing_state = helpers.check_contributing_state(app_id=app.id,
                                                              user_id=user.id)

        assert contributing_state == 'cannot_contribute', contributing_state

########NEW FILE########
__FILENAME__ = test_ckan
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import json
from mock import patch
from collections import namedtuple
from bs4 import BeautifulSoup

from default import Test, db, with_context
from pybossa.model.user import User
from pybossa.model.app import App
from helper import web as web_helper
from pybossa.ckan import Ckan


FakeRequest = namedtuple('FakeRequest', ['text', 'status_code', 'headers'])


class TestCkanWeb(web_helper.Helper):
    url = "/app/test-app/tasks/export"

    def setUp(self):
        super(TestCkanWeb, self).setUp()
        with self.flask_app.app_context():
            self.create()

    # Tests

    def test_00_anonymous(self):
        """Test CKAN anonymous cannot export data via CKAN"""
        res = self.app.get(self.url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "The CKAN exporter should not be available for anon users"
        assert dom.find(id="ckan") is None, err_msg

    def test_01_authenticated(self):
        """Test CKAN authenticated app owners can export data via CKAN"""
        res = self.signin(email=self.email_addr, password=self.password)
        res = self.app.get(self.url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "The CKAN exporter should be available for the owner of the app"
        assert dom.find(id="ckan") is not None, err_msg

        self.signout()

        self.signin(email=self.email_addr2, password=self.password)
        res = self.app.get(self.url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "The CKAN exporter should be ONLY available for the owner of the app"
        assert dom.find(id="ckan") is None, err_msg

    @with_context
    def test_02_export_links(self):
        """Test CKAN export links task and task run are available"""
        self.signin(email=self.email_addr, password=self.password)
        res = self.app.get(self.url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "There should be a warning about adding a CKAN api Key"
        assert dom.find(id="ckan_warning") is not None, err_msg
        # Add a CKAN API key to the user
        u = db.session.query(User).filter_by(name=self.name).first()
        u.ckan_api = "ckan-api-key"
        db.session.add(u)
        db.session.commit()
        # Request again the page
        res = self.app.get(self.url, follow_redirects=True)
        err_msg = "There should be two buttons to export Task and Task Runs"
        dom = BeautifulSoup(res.data)
        assert dom.find(id="ckan_task") is not None, err_msg
        assert dom.find(id="ckan_task_run") is not None, err_msg


class TestCkanModule(Test, object):

    ckan = Ckan(url="http://datahub.io", api_key="fake-api-key")
    task_resource_id = "0dde48c7-a0e9-445f-bc84-6365ec057450"
    task_run_resource_id = "a49448dc-228a-4d54-a697-ba02c50e0143"
    package_id = "4bcf844c-3ad0-4203-8418-32e7d7c4ce96"
    pkg_json_not_found = {
        "help": "Return ...",
        "success": False,
        "error": {
            "message": "Not found",
            "__type": "Not Found Error"}}

    pkg_json_found = {
        "help": "Return the metadata of a dataset ...",
        "success": True,
        "result": {
            "license_title": "",
            "maintainer": "",
            "relationships_as_object": [],
            "maintainer_email": "",
            "revision_timestamp": "2013-04-11T11:45:52.689160",
            "id": package_id,
            "metadata_created": "2013-04-11T11:39:56.003541",
            "metadata_modified": "2013-04-12T10:50:45.132825",
            "author": "Daniel Lombrana Gonzalez",
            "author_email": "",
            "state": "deleted",
            "version": "",
            "license_id": "",
            "type": None,
            "resources": [
                {
                    "resource_group_id": "f45c29ce-97f3-4b1f-b060-3306ffedb64b",
                    "cache_last_updated": None,
                    "revision_timestamp": "2013-04-12T10:50:41.635556",
                    "webstore_last_updated": None,
                    "id": task_resource_id,
                    "size": None,
                    "state": "active",
                    "last_modified": None,
                    "hash": "",
                    "description": "tasks",
                    "format": "",
                    "tracking_summary": {
                        "total": 0,
                        "recent": 0
                    },
                    "mimetype_inner": None,
                    "mimetype": None,
                    "cache_url": None,
                    "name": "task",
                    "created": "2013-04-12T05:50:41.776512",
                    "url": "http://localhost:5000/app/urbanpark/",
                    "webstore_url": None,
                    "position": 0,
                    "revision_id": "85027e11-fcbd-4362-9298-9755c99729b0",
                    "resource_type": None
                },
                {
                    "resource_group_id": "f45c29ce-97f3-4b1f-b060-3306ffedb64b",
                    "cache_last_updated": None,
                    "revision_timestamp": "2013-04-12T10:50:45.132825",
                    "webstore_last_updated": None,
                    "id": task_run_resource_id,
                    "size": None,
                    "state": "active",
                    "last_modified": None,
                    "hash": "",
                    "description": "task_runs",
                    "format": "",
                    "tracking_summary": {
                        "total": 0,
                        "recent": 0
                    },
                    "mimetype_inner": None,
                    "mimetype": None,
                    "cache_url": None,
                    "name": "task_run",
                    "created": "2013-04-12T05:50:45.193953",
                    "url": "http://localhost:5000/app/urbanpark/",
                    "webstore_url": None,
                    "position": 1,
                    "revision_id": "a1c52da7-5f2a-4bd4-8e58-b58e3caa11b5",
                    "resource_type": None
                }
            ],
            "tags": [],
            "tracking_summary": {
                "total": 0,
                "recent": 0
            },
            "groups": [],
            "relationships_as_subject": [],
            "name": "urbanpark",
            "isopen": False,
            "url": "http://localhost:5000/app/urbanpark/",
            "notes": "",
            "title": "Urban Parks",
            "extras": [],
            "revision_id": "b74c202a-1ad6-42a9-a878-012827d86c54"
        }
    }

    task_datastore = {
        u'help': u'Adds a ...',
        u'success': True,
        u'result': {
            u'fields': [{u'type': u'json', u'id': u'info'},
                        {u'type': u'int', u'id': u'user_id'},
                        {u'type': u'int', u'id': u'task_id'},
                        {u'type': u'timestamp', u'id': u'created'},
                        {u'type': u'timestamp', u'id': u'finish_time'},
                        {u'type': u'int', u'id': u'calibration'},
                        {u'type': u'int', u'id': u'app_id'},
                        {u'type': u'text', u'id': u'user_ip'},
                        {u'type': u'int', u'id': u'TaskRun_task'},
                        {u'type': u'int', u'id': u'TaskRun_user'},
                        {u'type': u'int', u'id': u'timeout'},
                        {u'type': u'int', u'id': u'id'}],
            u'method': u'insert',
            u'indexes': u'id',
            u'primary_key': u'id',
            u'resource_id': task_resource_id}}

    task_upsert = {"help": "Updates",
                   "success": True,
                   "result": {
                       "records": [
                           {"info": {"foo": "bar"},
                            "n_answers": 1000,
                            "quorum": 0,
                            "created": "2012-07-29T17:12:10.519270",
                            "calibration": 0,
                            "app_id": 120,
                            "state": "0",
                            "id": 6345,
                            "priority_0": 0.0}],
                       "method": "insert",
                       "resource_id": task_resource_id}}

    server_error = FakeRequest("Server Error", 500, {'content-type': 'text/html'})

    # Tests

    @patch('pybossa.ckan.requests.get')
    def test_00_package_exists_returns_false(self, Mock):
        """Test CKAN get_resource_id works"""
        html_request = FakeRequest(json.dumps(self.pkg_json_not_found), 200,
                                   {'content-type': 'application/json'})
        Mock.return_value = html_request
        with self.flask_app.test_request_context('/'):
            # Resource that exists
            out, e = self.ckan.package_exists(name='not-found')
            assert out is False, "It should return False as pkg does not exist"
            # Handle error in CKAN server
            Mock.return_value = self.server_error
            try:
                pkg, e = self.ckan.package_exists(name="something-goes-wrong")
                if e:
                    raise e
            except Exception as out:
                type, msg, status_code = out.args
                assert "Server Error" in msg, msg
                assert status_code == 500, "status_code should be 500"
                assert type == "CKAN: the remote site failed! package_show failed"
            # Now with a broken JSON item
            Mock.return_value = FakeRequest("simpletext", 200,
                                            {'content-type': 'text/html'})
            out, e = self.ckan.package_exists(name='not-found')
            assert out is False, "It should return False as pkg does not exist"
            # Handle error in CKAN server
            try:
                pkg, e = self.ckan.package_exists(name="something-goes-wrong")
                if e:
                    raise e
            except Exception as out:
                type, msg, status_code = out.args
                assert status_code == 200, "status_code should be 200"
                assert type == "CKAN: JSON not valid"

    @patch('pybossa.ckan.requests.get')
    def test_01_package_exists_returns_pkg(self, Mock):
        """Test CKAN get_resource_id works"""
        html_request = FakeRequest(json.dumps(self.pkg_json_found), 200,
                                   {'content-type': 'application/json'})
        Mock.return_value = html_request
        with self.flask_app.test_request_context('/'):
            # Resource that exists
            out, e = self.ckan.package_exists(name='urbanpark')
            assert out is not False, "It should return a pkg"
            err_msg = "The pkg id should be the same"
            assert out['id'] == self.pkg_json_found['result']['id'], err_msg

    @patch('pybossa.ckan.requests.get')
    def test_02_get_resource_id(self, Mock):
        """Test CKAN get_resource_id works"""
        html_request = FakeRequest(json.dumps(self.pkg_json_found), 200,
                                   {'content-type': 'application/json'})
        Mock.return_value = html_request
        with self.flask_app.test_request_context('/'):
            # Resource that exists
            # Get the package
            out, e = self.ckan.package_exists(name='urbanpark')
            # Get the resource id for Task
            out = self.ckan.get_resource_id(name='task')
            err_msg = "It should return the task resource ID"
            assert out == self.task_resource_id, err_msg
            # Get the resource id for TaskRun
            out = self.ckan.get_resource_id(name='task_run')
            err_msg = "It should return the task_run resource ID"
            assert out == self.task_run_resource_id, err_msg
            # Get the resource id for a non existant resource
            err_msg = "It should return false"
            out = self.ckan.get_resource_id(name='non-existant')
            assert out is False, err_msg

    @patch('pybossa.ckan.requests.post')
    def test_03_package_create(self, Mock):
        """Test CKAN package_create works"""
        # It should return self.pkg_json_found with an empty Resources list
        html_request = FakeRequest(json.dumps(self.pkg_json_found), 200,
                                   {'content-type': 'application/json'})
        Mock.return_value = html_request
        with self.flask_app.test_request_context('/'):
            # Resource that exists
            app = App(short_name='urbanpark', name='Urban Parks')
            user = User(fullname='Daniel Lombrana Gonzalez')
            out = self.ckan.package_create(app=app, user=user, url="http://something.com")
            err_msg = "The package ID should be the same"
            assert out['id'] == self.package_id, err_msg

            # Check the exception
            Mock.return_value = self.server_error
            try:
                self.ckan.package_create(app=app, user=user, url="http://something.com")
            except Exception as out:
                type, msg, status_code = out.args
                assert "Server Error" in msg, msg
                assert 500 == status_code, status_code
                assert "CKAN: the remote site failed! package_create failed" == type, type

    @patch('pybossa.ckan.requests.post')
    def test_05_resource_create(self, Mock):
        """Test CKAN resource_create works"""
        pkg_request = FakeRequest(json.dumps(self.pkg_json_found), 200,
                                  {'content-type': 'application/json'})

        rsrc_request = FakeRequest(json.dumps(
            self.pkg_json_found['result']['resources'][0]),
            200,
            {'content-type': 'text/html'})
        Mock.return_value = pkg_request
        with self.flask_app.test_request_context('/'):
            # Resource that exists
            app = App(short_name='urbanpark', name='Urban Parks')
            user = User(fullname='Daniel Lombrana Gonzalez')
            self.ckan.package_create(app=app, user=user, url="http://something.com")
            Mock.return_value = rsrc_request
            out = self.ckan.resource_create(name='task')
            err_msg = "It should create the task resource"
            assert out["id"] == self.task_resource_id, err_msg
            Mock.return_value = self.server_error
            try:
                self.ckan.resource_create(name='something-goes-wrong')
            except Exception as out:
                type, msg, status_code = out.args
                assert "Server Error" in msg, msg
                assert 500 == status_code, status_code
                assert "CKAN: the remote site failed! resource_create failed" == type, type

    @patch('pybossa.ckan.requests.post')
    def test_05_datastore_create_without_resource_id(self, Mock):
        """Test CKAN datastore_create without resource_id works"""
        html_request = FakeRequest(json.dumps(self.task_datastore), 200,
                                   {'content-type': 'application/json'})

        Mock.return_value = html_request
        with self.flask_app.test_request_context('/'):
            out = self.ckan.datastore_create(name='task',
                                             resource_id=None)
            err_msg = "It should ref the task resource ID"
            assert out['resource_id'] == self.task_resource_id, err_msg
            # Check the error
            Mock.return_value = self.server_error
            try:
                self.ckan.datastore_create(name='task',
                                           resource_id=self.task_resource_id)
            except Exception as out:
                type, msg, status_code = out.args
                assert "Server Error" in msg, err_msg
                assert 500 == status_code, status_code
                assert "CKAN: the remote site failed! datastore_create failed" == type, type

    @patch('pybossa.ckan.requests.post')
    def test_05_datastore_create(self, Mock):
        """Test CKAN datastore_create works"""
        html_request = FakeRequest(json.dumps(self.task_datastore), 200,
                                   {'content-type': 'application/json'})

        Mock.return_value = html_request
        with self.flask_app.test_request_context('/'):
            out = self.ckan.datastore_create(name='task',
                                             resource_id=self.task_resource_id)
            err_msg = "It should ref the task resource ID"
            assert out['resource_id'] == self.task_resource_id, err_msg
            # Check the error
            Mock.return_value = self.server_error
            try:
                self.ckan.datastore_create(name='task',
                                           resource_id=self.task_resource_id)
            except Exception as out:
                type, msg, status_code = out.args
                assert "Server Error" in msg, err_msg
                assert 500 == status_code, status_code
                assert "CKAN: the remote site failed! datastore_create failed" == type, type

    @patch('pybossa.ckan.requests.post')
    def test_06_datastore_upsert_without_resource_id(self, Mock):
        """Test CKAN datastore_upsert without resourece_id works"""
        html_request = FakeRequest(json.dumps(self.task_upsert), 200,
                                   {'content-type': 'application/json'})

        record = dict(info=dict(foo="bar"))
        Mock.return_value = html_request
        with self.flask_app.test_request_context('/'):
            out = self.ckan.datastore_upsert(name='task',
                                             records=json.dumps([record]),
                                             resource_id=None)
            err_msg = "It should return True"
            assert out is True, err_msg
            # Check the error
            Mock.return_value = self.server_error
            try:
                self.ckan.datastore_upsert(name='task',
                                           records=json.dumps([record]),
                                           resource_id=self.task_resource_id)
            except Exception as out:
                type, msg, status_code = out.args
                assert "Server Error" in msg, msg
                assert 500 == status_code, status_code
                assert "CKAN: the remote site failed! datastore_upsert failed" == type, type


    @patch('pybossa.ckan.requests.post')
    def test_06_datastore_upsert(self, Mock):
        """Test CKAN datastore_upsert works"""
        html_request = FakeRequest(json.dumps(self.task_upsert), 200,
                                   {'content-type': 'application/json'})

        record = dict(info=dict(foo="bar"))
        Mock.return_value = html_request
        with self.flask_app.test_request_context('/'):
            out = self.ckan.datastore_upsert(name='task',
                                             records=json.dumps([record]),
                                             resource_id=self.task_resource_id)
            err_msg = "It should return True"
            assert out is True, err_msg
            # Check the error
            Mock.return_value = self.server_error
            try:
                self.ckan.datastore_upsert(name='task',
                                           records=json.dumps([record]),
                                           resource_id=self.task_resource_id)
            except Exception as out:
                type, msg, status_code = out.args
                assert "Server Error" in msg, msg
                assert 500 == status_code, status_code
                assert "CKAN: the remote site failed! datastore_upsert failed" == type, type

    @patch('pybossa.ckan.requests.post')
    def test_07_datastore_delete(self, Mock):
        """Test CKAN datastore_delete works"""
        html_request = FakeRequest(json.dumps({}), 200,
                                   {'content-type': 'application/json'})

        Mock.return_value = html_request
        with self.flask_app.test_request_context('/'):
            out = self.ckan.datastore_delete(name='task',
                                             resource_id=self.task_resource_id)
            err_msg = "It should return True"
            assert out is True, err_msg
            # Check the error
            Mock.return_value = self.server_error
            try:
                self.ckan.datastore_delete(name='task',
                                           resource_id=self.task_resource_id)
            except Exception as out:
                type, msg, status_code = out.args
                assert "Server Error" in msg, msg
                assert 500 == status_code, status_code
                assert "CKAN: the remote site failed! datastore_delete failed" == type, type

    @patch('pybossa.ckan.requests.post')
    def test_08_package_update(self, Mock):
        """Test CKAN package_update works"""
        html_request = FakeRequest(json.dumps(self.pkg_json_found), 200,
                                   {'content-type': 'application/json'})
        Mock.return_value = html_request
        with self.flask_app.test_request_context('/'):
            # Resource that exists
            app = App(short_name='urbanpark', name='Urban Parks')
            user = User(fullname='Daniel Lombrana Gonzalez')
            out = self.ckan.package_update(app=app, user=user,
                                           url="http://something.com",
                                           resources=self.pkg_json_found['result']['resources'])
            err_msg = "The package ID should be the same"
            assert out['id'] == self.package_id, err_msg

            # Check the exception
            Mock.return_value = self.server_error
            try:
                self.ckan.package_update(app=app, user=user,
                                         url="http://something.com",
                                         resources=self.pkg_json_found['result']['resources'])
            except Exception as out:
                type, msg, status_code = out.args
                assert "Server Error" in msg, msg
                assert 500 == status_code, status_code
                assert "CKAN: the remote site failed! package_update failed" == type, type

########NEW FILE########
__FILENAME__ = test_facebook
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
from default import Test, with_context
from pybossa.view.facebook import manage_user


class TestFacebook(Test):
    @with_context
    def test_manage_user_with_email(self):
        """Test FACEBOOK manage_user works."""
        # First with a new user
        user_data = dict(id=1, username='facebook',
                         email='f@f.com', name='name')
        token = 't'
        user = manage_user(token, user_data, None)
        assert user.email_addr == user_data['email'], user
        assert user.name == user_data['username'], user
        assert user.fullname == user_data['name'], user
        assert user.facebook_user_id == user_data['id'], user

        # Second with the same user
        user = manage_user(token, user_data, None)
        assert user.email_addr == user_data['email'], user
        assert user.name == user_data['username'], user
        assert user.fullname == user_data['name'], user
        assert user.facebook_user_id == user_data['id'], user

        # Finally with a user that already is in the system
        user_data = dict(id=10, username=self.name,
                         email=self.email_addr, name=self.fullname)
        token = 'tA'
        user = manage_user(token, user_data, None)
        err_msg = "It should return the same user"
        assert user.facebook_user_id == 10, err_msg

    @with_context
    def test_manage_user_without_email(self):
        """Test FACEBOOK manage_user without e-mail works."""
        # First with a new user
        user_data = dict(id=1, username='facebook', name='name')
        token = 't'
        user = manage_user(token, user_data, None)
        assert user.email_addr == user_data['email'], user
        assert user.name == user_data['username'], user
        assert user.fullname == user_data['name'], user
        assert user.facebook_user_id == user_data['id'], user

        # Second with the same user
        user = manage_user(token, user_data, None)
        assert user.email_addr == user_data['email'], user
        assert user.name == user_data['username'], user
        assert user.fullname == user_data['name'], user
        assert user.facebook_user_id == user_data['id'], user

        # Finally with a user that already is in the system
        user_data = dict(id=10, username=self.name,
                         email=self.email_addr, name=self.fullname)
        token = 'tA'
        user = manage_user(token, user_data, None)
        err_msg = "It should return the same user"
        assert user.facebook_user_id == 10, err_msg

########NEW FILE########
__FILENAME__ = test_google
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
from default import Test, with_context
from pybossa.view.google import manage_user


class TestGoogle(Test):
    @with_context
    def test_manage_user(self):
        """Test GOOGLE manage_user works."""
        # First with a new user
        user_data = dict(id='1', name='google',
                         email='g@g.com')
        token = 't'
        user = manage_user(token, user_data, None)
        assert user.email_addr == user_data['email'], user
        assert user.name == user_data['name'], user
        assert user.fullname == user_data['name'], user
        assert user.google_user_id == user_data['id'], user

        # Second with the same user
        user = manage_user(token, user_data, None)
        assert user.email_addr == user_data['email'], user
        assert user.name == user_data['name'], user
        assert user.fullname == user_data['name'], user
        assert user.google_user_id == user_data['id'], user

        # Finally with a user that already is in the system
        user_data = dict(id='10', name=self.name,
                         email=self.email_addr)
        token = 'tA'
        user = manage_user(token, user_data, None)
        err_msg = "User should be the same"
        print user.google_user_id
        assert user.google_user_id == '10', err_msg

########NEW FILE########
__FILENAME__ = test_hateoas
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import json

from default import db, with_context
from helper import web as web_helper
from pybossa.hateoas import Hateoas


class TestHateoas(web_helper.Helper):

    hateoas = Hateoas()

    def setUp(self):
        super(TestHateoas, self).setUp()
        with self.flask_app.app_context():
            self.create()

    # Tests
    @with_context
    def test_00_link_object(self):
        """Test HATEOAS object link is created"""
        # For app
        res = self.app.get("/api/app/1", follow_redirects=True)
        output = json.loads(res.data)
        err_msg = "There should be a Link with the object URI"
        assert output['link'] is not None, err_msg

        err_msg = "There should be a Links list with the category URI"
        assert output['links'] is not None, err_msg
        assert len(output['links']) == 1, err_msg
        app_link = self.hateoas.link(rel='category', title='category',
                                     href='http://localhost/api/category/1')
        assert app_link == output['links'][0], err_msg

        app_link = self.hateoas.link(rel='self', title='app',
                                     href='http://localhost/api/app/1')
        err_msg = "The object link is wrong: %s" % output['link']
        assert app_link == output['link'], err_msg

        # For task
        res = self.app.get("/api/task/1", follow_redirects=True)
        output = json.loads(res.data)
        err_msg = "There should be a Link with the object URI"
        assert output['link'] is not None, err_msg
        task_link = self.hateoas.link(rel='self', title='task',
                                      href='http://localhost/api/task/1')
        err_msg = "The object link is wrong: %s" % output['link']
        assert task_link == output['link'], err_msg
        err_msg = "There should be one parent link: app"
        assert output.get('links') is not None, err_msg
        assert len(output.get('links')) == 1, err_msg
        err_msg = "The parent link is wrong"
        app_link = self.hateoas.link(rel='parent', title='app',
                                     href='http://localhost/api/app/1')
        assert output.get('links')[0] == app_link, err_msg

        # For taskrun
        res = self.app.get("/api/taskrun/1", follow_redirects=True)
        output = json.loads(res.data)
        err_msg = "There should be a Link with the object URI"
        assert output['link'] is not None, err_msg
        task_link = self.hateoas.link(rel='self', title='taskrun',
                                      href='http://localhost/api/taskrun/1')
        err_msg = "The object link is wrong: %s" % output['link']
        assert task_link == output['link'], err_msg
        err_msg = "There should be two parent links: app and task"
        assert output.get('links') is not None, err_msg
        assert len(output.get('links')) == 2, err_msg
        err_msg = "The parent app link is wrong"
        app_link = self.hateoas.link(rel='parent', title='app',
                                     href='http://localhost/api/app/1')
        assert output.get('links')[0] == app_link, err_msg

        err_msg = "The parent task link is wrong"
        app_link = self.hateoas.link(rel='parent', title='task',
                                     href='http://localhost/api/task/1')
        assert output.get('links')[1] == app_link, err_msg
        res = self.app.post("/api/taskrun")

        # For category
        res = self.app.get("/api/category/1", follow_redirects=True)
        output = json.loads(res.data)
        err_msg = "There should be a Link with the object URI"
        assert output['link'] is not None, err_msg
        category_link = self.hateoas.link(rel='self', title='category',
                                          href='http://localhost/api/category/1')
        err_msg = "The object link is wrong: %s" % output['link']
        assert category_link == output['link'], err_msg
        err_msg = "There should be no other links"
        assert output.get('links') is None, err_msg
        err_msg = "The object links should are wrong"

        # For user
        # Pending define what user fields will be visible through the API
        # Issue #626. For now let's suppose link and links are not visible
        # res = self.app.get("/api/user/1?api_key=" + self.root_api_key, follow_redirects=True)
        # output = json.loads(res.data)
        # err_msg = "There should be a Link with the object URI"
        # assert output['link'] is not None, err_msg
        # user_link = self.hateoas.link(rel='self', title='user',
        #                               href='http://localhost/api/user/1')
        # err_msg = "The object link ir wrong: %s" % output['link']
        # assert user_link == output['link'], err_msg
        # # when the links specification of a user will be set, modify the following
        # err_msg = "The list of links should be empty for now"
        # assert output.get('links') == None, err_msg


    @with_context
    def test_01_link_object(self):
        """Test HATEOAS object link is created"""
        # For app
        res = self.app.get("/api/app", follow_redirects=True)
        output = json.loads(res.data)[0]
        err_msg = "There should be a Link with the object URI"
        assert output['link'] is not None, err_msg
        app_link = self.hateoas.link(rel='self', title='app',
                                     href='http://localhost/api/app/1')

        err_msg = "The object link is wrong: %s" % output['link']
        assert app_link == output['link'], err_msg

        err_msg = "There should be a Links list with the category URI"
        assert output['links'] is not None, err_msg
        assert len(output['links']) == 1, err_msg
        app_link = self.hateoas.link(rel='category', title='category',
                                     href='http://localhost/api/category/1')
        assert app_link == output['links'][0], err_msg

        # For task
        res = self.app.get("/api/task", follow_redirects=True)
        output = json.loads(res.data)[0]
        err_msg = "There should be a Link with the object URI"
        assert output['link'] is not None, err_msg
        task_link = self.hateoas.link(rel='self', title='task',
                                      href='http://localhost/api/task/1')
        err_msg = "The object link is wrong: %s" % output['link']
        assert task_link == output['link'], err_msg
        err_msg = "There should be one parent link: app"
        assert output.get('links') is not None, err_msg
        assert len(output.get('links')) == 1, err_msg
        err_msg = "The parent link is wrong"
        app_link = self.hateoas.link(rel='parent', title='app',
                                     href='http://localhost/api/app/1')
        assert output.get('links')[0] == app_link, err_msg

        # For taskrun
        res = self.app.get("/api/taskrun", follow_redirects=True)
        output = json.loads(res.data)[0]
        err_msg = "There should be a Link with the object URI"
        assert output['link'] is not None, err_msg
        task_link = self.hateoas.link(rel='self', title='taskrun',
                                      href='http://localhost/api/taskrun/1')
        err_msg = "The object link is wrong: %s" % output['link']
        assert task_link == output['link'], err_msg
        err_msg = "There should be two parent links: app and task"
        assert output.get('links') is not None, err_msg
        assert len(output.get('links')) == 2, err_msg
        err_msg = "The parent app link is wrong"
        app_link = self.hateoas.link(rel='parent', title='app',
                                     href='http://localhost/api/app/1')
        assert output.get('links')[0] == app_link, err_msg

        err_msg = "The parent task link is wrong"
        app_link = self.hateoas.link(rel='parent', title='task',
                                     href='http://localhost/api/task/1')
        assert output.get('links')[1] == app_link, err_msg

        # Check that hateoas removes all link and links from item
        without_links = self.hateoas.remove_links(output)
        err_msg = "There should not be any link or links keys"
        assert without_links.get('link') is None, err_msg
        assert without_links.get('links') is None, err_msg

        # For category
        res = self.app.get("/api/category", follow_redirects=True)
        output = json.loads(res.data)[0]
        err_msg = "There should be a Link with the object URI"
        assert output['link'] is not None, err_msg
        category_link = self.hateoas.link(rel='self', title='category',
                                      href='http://localhost/api/category/1')
        err_msg = "The object link is wrong: %s" % output['link']
        assert category_link == output['link'], err_msg
        err_msg = "There should be no other links"
        assert output.get('links') is None, err_msg
        err_msg = "The object links should are wrong"

        # For user
        # Pending define what user fields will be visible through the API
        # Issue #626. For now let's suppose link and links are not visible
        # res = self.app.get("/api/user?api_key=" + self.root_api_key, follow_redirects=True)
        # output = json.loads(res.data)[0]
        # err_msg = "There should be a Link with the object URI"
        # assert output['link'] is not None, err_msg
        # user_link = self.hateoas.link(rel='self', title='user',
        #                               href='http://localhost/api/user/1')
        # err_msg = "The object link ir wrong: %s" % output['link']
        # assert user_link == output['link'], err_msg
        # # when the links specification of a user will be set, modify the following
        # err_msg = "The list of links should be empty for now"
        # assert output.get('links') == None, err_msg

########NEW FILE########
__FILENAME__ = test_i18n
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from helper import web
from default import db, with_context
from pybossa.model.user import User


class TestI18n(web.Helper):
    def setUp(self):
        super(TestI18n, self).setUp()
        with self.flask_app.app_context():
            self.create()

    # Tests
    @with_context
    def test_00_i18n_anonymous(self):
        """Test i18n anonymous works"""
        # First default 'en' locale
        with self.app as c:
            err_msg = "The page should be in English"
            res = c.get('/', headers=[('Accept-Language', 'en')])
            assert "Community" in res.data, err_msg
        # Second with 'es' locale
        with self.app as c:
            err_msg = "The page should be in Spanish"
            res = c.get('/', headers=[('Accept-Language', 'es')])
            assert "Comunidad" in res.data, err_msg

    @with_context
    def test_01_i18n_authenticated(self):
        """Test i18n as an authenticated user works"""
        with self.app as c:
            # First default 'en' locale
            err_msg = "The page should be in English"
            res = c.get('/', follow_redirects=True)
            assert "Community" in res.data, err_msg
            self.register()
            self.signin()
            # After signing in it should be in English
            err_msg = "The page should be in English"
            res = c.get('/', follow_redirects=True)
            assert "Community" in res.data, err_msg

            # Change it to Spanish
            user = db.session.query(User).filter_by(name='johndoe').first()
            user.locale = 'es'
            db.session.add(user)
            db.session.commit()

            res = c.get('/', follow_redirects=True)
            err_msg = "The page should be in Spanish"
            assert "Comunidad" in res.data, err_msg
            # Sign out should revert it to English
            self.signout()
            err_msg = "The page should be in English"
            res = c.get('/', follow_redirects=True)
            assert "Community" in res.data, err_msg

########NEW FILE########
__FILENAME__ = test_model_app
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from default import Test, db, with_context
from nose.tools import assert_raises
from pybossa.model.app import App
from pybossa.model.user import User
from sqlalchemy.exc import IntegrityError


class TestModelApp(Test):

    @with_context
    def test_app_errors(self):
        """Test APP model errors."""
        app = App(name='Application',
                  short_name='app',
                  description='desc',
                  owner_id=None)

        # App.owner_id shoult not be nullable
        db.session.add(app)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

        # App.name shoult not be nullable
        user = User(email_addr="john.doe@example.com",
                    name="johndoe",
                    fullname="John Doe",
                    locale="en")
        db.session.add(user)
        db.session.commit()
        user = db.session.query(User).first()
        app.owner_id = user.id
        app.name = None
        db.session.add(app)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

        app.name = ''
        db.session.add(app)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

        # App.short_name shoult not be nullable
        app.name = "Application"
        app.short_name = None
        db.session.add(app)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

        app.short_name = ''
        db.session.add(app)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

        # App.description shoult not be nullable
        db.session.add(app)
        app.short_name = "app"
        app.description = None
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

        app.description = ''
        db.session.add(app)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

########NEW FILE########
__FILENAME__ = test_model_base
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from default import Test, db, with_context
from nose.tools import raises
from pybossa.model.user import User
from pybossa.model.app import App
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun


"""Tests for inter-model relations and base classes and helper functions
of model package."""



class TestModelBase(Test):

    @raises(NotImplementedError)
    @with_context
    def test_domain_object_error(self):
        """Test DomainObject errors work."""
        user = User()
        user.name = "John"
        d = user.dictize()
        user.undictize(d)


    @with_context
    def test_all(self):
        """Test MODEL works"""
        username = u'test-user-1'
        user = User(name=username, fullname=username, email_addr=username)
        info = {
            'total': 150,
            'long_description': 'hello world'}
        app = App(
            name=u'My New App',
            short_name=u'my-new-app',
            description=u'description',
            info=info)
        app.owner = user
        task_info = {
            'question': 'My random question',
            'url': 'my url'}
        task = Task(info=task_info)
        task_run_info = {'answer': u'annakarenina'}
        task_run = TaskRun(info=task_run_info)
        task.app = app
        task_run.task = task
        task_run.app = app
        task_run.user = user
        db.session.add_all([user, app, task, task_run])
        db.session.commit()
        app_id = app.id

        db.session.remove()

        app = db.session.query(App).get(app_id)
        assert app.name == u'My New App', app
        # year would start with 201...
        assert app.created.startswith('201'), app.created
        assert app.long_tasks == 0, app.long_tasks
        assert app.hidden == 0, app.hidden
        assert app.time_estimate == 0, app
        assert app.time_limit == 0, app
        assert app.calibration_frac == 0, app
        assert app.bolt_course_id == 0
        assert len(app.tasks) == 1, app
        assert app.owner.name == username, app
        out_task = app.tasks[0]
        assert out_task.info['question'] == task_info['question'], out_task
        assert out_task.quorum == 0, out_task
        assert out_task.state == "ongoing", out_task
        assert out_task.calibration == 0, out_task
        assert out_task.priority_0 == 0, out_task
        assert len(out_task.task_runs) == 1, out_task
        outrun = out_task.task_runs[0]
        assert outrun.info['answer'] == task_run_info['answer'], outrun
        assert outrun.user.name == username, outrun

        user = User.by_name(username)
        assert user.apps[0].id == app_id, user


########NEW FILE########
__FILENAME__ = test_model_blogpost
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from default import Test, db, with_context, assert_not_raises
from nose.tools import raises, assert_raises
from sqlalchemy.exc import IntegrityError, DataError
from pybossa.model.app import App
from pybossa.model.user import User
from pybossa.model.blogpost import Blogpost


class TestBlogpostModel(Test):

    def setUp(self):
        super(TestBlogpostModel, self).setUp()
        with self.flask_app.app_context():
            user = User(email_addr="john.doe@example.com",
                        name="johndoe",
                        fullname="John Doe",
                        locale="en")
            app = App(
                name='Application',
                short_name='app',
                description='desc',
                owner=user)
            db.session.add(user)
            db.session.add(app)
            db.session.commit()

    def configure_fixtures(self):
        self.app = db.session.query(App).first()
        self.user = db.session.query(User).first()


    @with_context
    def test_blogpost_title_length(self):
        """Test BLOGPOST model title length has a limit"""
        self.configure_fixtures()
        valid_title = 'a' * 255
        invalid_title = 'a' * 256
        blogpost = Blogpost(title=valid_title, body="body", app=self.app)
        db.session.add(blogpost)

        assert_not_raises(DataError, db.session.commit)

        blogpost.title = invalid_title
        assert_raises(DataError, db.session.commit)

    @with_context
    def test_blogpost_title_presence(self):
        """Test BLOGPOST a blogpost must have a title"""
        self.configure_fixtures()
        blogpost = Blogpost(title=None, body="body", app=self.app)
        db.session.add(blogpost)

        assert_raises(IntegrityError, db.session.commit)

    @with_context
    def test_blogpost_body_presence(self):
        """Test BLOGPOST a blogpost must have a body"""
        self.configure_fixtures()
        blogpost = Blogpost(title='title', body=None, app=self.app)
        db.session.add(blogpost)

        assert_raises(IntegrityError, db.session.commit)

    @with_context
    def test_blogpost_belongs_to_app(self):
        """Test BLOGPOSTS must belong to an app"""
        self.configure_fixtures()
        blogpost = Blogpost(title='title', body="body", app=None)

    @with_context
    def test_blogpost_belongs_to_app(self):
        """Test BLOGPOSTS must belong to an app"""
        self.configure_fixtures()
        blogpost = Blogpost(title='title', app = None)
        db.session.add(blogpost)

        assert_raises(IntegrityError, db.session.commit)

    @with_context
    def test_blogpost_is_deleted_after_app_deletion(self):
        """Test BLOGPOST no blogposts can exist after it's app has been removed"""
        self.configure_fixtures()
        blogpost = Blogpost(title='title', body="body", app=self.app)
        db.session.add(blogpost)
        db.session.commit()

        assert self.app in db.session
        assert blogpost in db.session

        db.session.delete(self.app)
        db.session.commit()
        assert self.app not in db.session
        assert blogpost not in db.session

    @with_context
    def test_blogpost_deletion_doesnt_delete_app(self):
        """Test BLOGPOST when deleting a blogpost it's parent app is not affected"""
        self.configure_fixtures()
        blogpost = Blogpost(title='title', body="body", app=self.app)
        db.session.add(blogpost)
        db.session.commit()

        assert self.app in db.session
        assert blogpost in db.session

        db.session.delete(blogpost)
        db.session.commit()
        assert self.app in db.session
        assert blogpost not in db.session

    @with_context
    def test_blogpost_owner_is_nullable(self):
        """Test BLOGPOST a blogpost owner can be none
        (if the user is removed from the system)"""
        self.configure_fixtures()
        blogpost = Blogpost(title='title', body="body", app=self.app, owner=None)
        db.session.add(blogpost)

        assert_not_raises(IntegrityError, db.session.commit)

    @with_context
    def test_blogpost_is_not_deleted_after_owner_deletion(self):
        """Test BLOGPOST a blogpost remains when it's owner user is removed
        from the system"""
        self.configure_fixtures()
        owner = User(
            email_addr="john.doe2@example.com",
            name="johndoe2",
            fullname="John Doe2",
            locale="en")
        blogpost = Blogpost(title='title', body="body", app=self.app, owner=owner)
        db.session.add(blogpost)
        db.session.commit()

        assert owner in db.session
        assert blogpost in db.session

        db.session.delete(owner)
        db.session.commit()
        assert owner not in db.session
        assert blogpost in db.session
        assert blogpost.owner == None, blogpost.owner

########NEW FILE########
__FILENAME__ = test_model_task
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from default import Test, db, with_context
from nose.tools import assert_raises
from sqlalchemy.exc import IntegrityError
from pybossa.model.user import User
from pybossa.model.app import App
from pybossa.model.task import Task


class TestModelTask(Test):


    @with_context
    def test_task_errors(self):
        """Test TASK model errors."""
        user = User(
            email_addr="john.doe@example.com",
            name="johndoe",
            fullname="John Doe",
            locale="en")
        db.session.add(user)
        db.session.commit()
        user = db.session.query(User).first()
        app = App(
            name='Application',
            short_name='app',
            description='desc',
            owner_id=user.id)
        db.session.add(app)
        db.session.commit()

        task = Task(app_id=None)
        db.session.add(task)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

########NEW FILE########
__FILENAME__ = test_model_taskrun
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from default import Test, db, with_context
from nose.tools import assert_raises
from sqlalchemy.exc import IntegrityError
from pybossa.model.user import User
from pybossa.model.app import App
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun


class TestModelTaskRun(Test):

    @with_context
    def test_task_run_errors(self):
        """Test TASK_RUN model errors."""
        user = User(
            email_addr="john.doe@example.com",
            name="johndoe",
            fullname="John Doe",
            locale="en")
        db.session.add(user)
        db.session.commit()

        user = db.session.query(User).first()
        app = App(
            name='Application',
            short_name='app',
            description='desc',
            owner_id=user.id)
        db.session.add(app)
        db.session.commit()

        task = Task(app_id=app.id)
        db.session.add(task)
        db.session.commit()

        task_run = TaskRun(app_id=None, task_id=task.id)
        db.session.add(task_run)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

        task_run = TaskRun(app_id=app.id, task_id=None)
        db.session.add(task_run)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

########NEW FILE########
__FILENAME__ = test_model_user
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from default import Test, db, with_context
from nose.tools import assert_raises
from sqlalchemy.exc import IntegrityError
from pybossa.model.user import User


class TestModelUser(Test):

    @with_context
    def test_user(self):
        """Test USER model."""
        # First user
        user = User(
            email_addr="john.doe@example.com",
            name="johndoe",
            fullname="John Doe",
            locale="en")

        user2 = User(
            email_addr="john.doe2@example.com",
            name="johndoe2",
            fullname="John Doe2",
            locale="en",)

        db.session.add(user)
        db.session.commit()
        tmp = db.session.query(User).get(1)
        assert tmp.email_addr == user.email_addr, tmp
        assert tmp.name == user.name, tmp
        assert tmp.fullname == user.fullname, tmp
        assert tmp.locale == user.locale, tmp
        assert tmp.api_key is not None, tmp
        assert tmp.created is not None, tmp
        err_msg = "First user should be admin"
        assert tmp.admin is True, err_msg
        err_msg = "check_password method should return False"
        assert tmp.check_password(password="nothing") is False, err_msg

        db.session.add(user2)
        db.session.commit()
        tmp = db.session.query(User).get(2)
        assert tmp.email_addr == user2.email_addr, tmp
        assert tmp.name == user2.name, tmp
        assert tmp.fullname == user2.fullname, tmp
        assert tmp.locale == user2.locale, tmp
        assert tmp.api_key is not None, tmp
        assert tmp.created is not None, tmp
        err_msg = "Second user should be not an admin"
        assert tmp.admin is False, err_msg

    @with_context
    def test_user_errors(self):
        """Test USER model errors."""
        user = User(
            email_addr="john.doe@example.com",
            name="johndoe",
            fullname="John Doe",
            locale="en")

        # User.name should not be nullable
        user.name = None
        db.session.add(user)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

        # User.fullname should not be nullable
        user.name = "johndoe"
        user.fullname = None
        db.session.add(user)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

        # User.email_addr should not be nullable
        user.name = "johndoe"
        user.fullname = "John Doe"
        user.email_addr = None
        db.session.add(user)
        assert_raises(IntegrityError, db.session.commit)
        db.session.rollback()

########NEW FILE########
__FILENAME__ = test_privacy
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from bs4 import BeautifulSoup

from helper import web as web_helper
from default import flask_app, with_context
from mock import patch


class TestPrivacyWebPublic(web_helper.Helper):

    def setUp(self):
        super(TestPrivacyWebPublic, self).setUp()
        with self.flask_app.app_context():
            self.create()

    # Tests
    @with_context
    def test_00_footer(self):
        """Test PRIVACY footer privacy is respected"""
        url = '/'
        # As Anonymou user
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Footer links should be shown to anonymous users"
        assert dom.find(id='footer_links') is not None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Footer links should be shown to authenticated users"
        assert dom.find(id='footer_links') is not None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Footer links should be shown to admin users"
        assert dom.find(id='footer_links') is not None, err_msg
        self.signout()

    @with_context
    def test_01_front_page(self):
        """Test PRIVACY footer privacy is respected"""
        url = '/'
        # As Anonymou user
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Top users should be shown to anonymous users"
        assert dom.find(id='top_users') is not None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Top users should be shown to authenticated users"
        assert dom.find(id='top_users') is not None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Top users should be shown to admin"
        assert dom.find(id='top_users') is not None, err_msg
        self.signout()

    @with_context
    def test_02_account_index(self):
        """Test PRIVACY account privacy is respected"""
        # As Anonymou user
        url = "/account"
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Community page should be shown to anonymous users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Community page should be shown to authenticated users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Community page should be shown to admin users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout()

    @with_context
    def test_03_leaderboard(self):
        """Test PRIVACY leaderboard privacy is respected"""
        # As Anonymou user
        url = "/leaderboard"
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Leaderboard page should be shown to anonymous users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Leaderboard page should be shown to authenticated users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Leaderboard page should be shown to admin users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout()

    @with_context
    def test_04_global_stats_index(self):
        """Test PRIVACY global stats privacy is respected"""
        # As Anonymou user
        url = "/stats"
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Stats page should be shown to anonymous users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Stats page should be shown to authenticated users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Stats page should be shown to admin users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout()

    @with_context
    def test_05_app_stats_index(self):
        """Test PRIVACY app stats privacy is respected"""
        # As Anonymou user
        url = "/app/%s/stats" % self.app_short_name
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "App Stats page should be shown to anonymous users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "App Stats page should be shown to authenticated users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "App Stats page should be shown to admin users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout()

    @with_context
    def test_06_user_public_profile(self):
        """Test PRIVACY user public profile privacy is respected"""
        # As Anonymou user
        url = "/account/%s" % self.name
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Public User Profile page should be shown to anonymous users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Public User Profile page should be shown to authenticated users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Public User Profile page should be shown to admin users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout()


class TestPrivacyWebPrivacy(web_helper.Helper):

    def setUp(self):
        super(TestPrivacyWebPrivacy, self).setUp()
        with self.flask_app.app_context():
            self.create()

    # Tests
    @patch.dict(flask_app.config, {'ENFORCE_PRIVACY': True})
    @with_context
    def test_00_footer(self):
        """Test PRIVACY footer privacy is respected"""
        url = '/'
        # As Anonymou user
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Footer links should not be shown to anonymous users"
        assert dom.find(id='footer_links') is None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Footer links should not be shown to authenticated users"
        assert dom.find(id='footer_links') is None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Footer links should not be shown to admin users"
        assert dom.find(id='footer_links') is None, err_msg
        self.signout()

    @patch.dict(flask_app.config, {'ENFORCE_PRIVACY': True})
    @with_context
    def test_01_front_page(self):
         """Test PRIVACY front page top users privacy is respected"""
         url = '/'
         # As Anonymou user
         res = self.app.get(url, follow_redirects=True)
         dom = BeautifulSoup(res.data)
         err_msg = "Top users should not be shown to anonymous users"
         assert dom.find(id='top_users') is None, err_msg
         # As Authenticated user but NOT ADMIN
         self.signin()
         res = self.app.get(url, follow_redirects=True)
         dom = BeautifulSoup(res.data)
         err_msg = "Top users should not be shown to authenticated users"
         assert dom.find(id='top_users') is None, err_msg
         self.signout
         # As Authenticated user but ADMIN
         res = self.signin(email=self.root_addr, password=self.root_password)
         print res.data
         res = self.app.get(url, follow_redirects=True)
         dom = BeautifulSoup(res.data)
         err_msg = "Top users should be shown to admin"
         assert dom.find(id='top_users') is not None, err_msg
         self.signout()

    @patch.dict(flask_app.config, {'ENFORCE_PRIVACY': True})
    @with_context
    def test_02_account_index(self):
        """Test PRIVACY account privacy is respected"""
        # As Anonymou user
        url = "/account"
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Community page should not be shown to anonymous users"
        assert dom.find(id='enforce_privacy') is not None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Community page should not be shown to authenticated users"
        assert dom.find(id='enforce_privacy') is not None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Community page should be shown to admin users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout()

    @patch.dict(flask_app.config, {'ENFORCE_PRIVACY': True})
    @with_context
    def test_03_leaderboard(self):
        """Test PRIVACY leaderboard privacy is respected"""
        # As Anonymou user
        url = "/leaderboard"
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Leaderboard page should not be shown to anonymous users"
        assert dom.find(id='enforce_privacy') is not None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Leaderboard page should not be shown to authenticated users"
        assert dom.find(id='enforce_privacy') is not None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Leaderboard page should be shown to admin users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout()

    @patch.dict(flask_app.config, {'ENFORCE_PRIVACY': True})
    @with_context
    def test_04_global_stats_index(self):
        """Test PRIVACY global stats privacy is respected"""
        # As Anonymou user
        url = "/stats"
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Stats page should not be shown to anonymous users"
        assert dom.find(id='enforce_privacy') is not None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Stats page should not be shown to authenticated users"
        assert dom.find(id='enforce_privacy') is not None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Stats page should be shown to admin users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout()

    @patch.dict(flask_app.config, {'ENFORCE_PRIVACY': True})
    @with_context
    def test_05_app_stats_index(self):
        """Test PRIVACY app stats privacy is respected"""
        # As Anonymou user
        url = "/app/%s/stats" % self.app_short_name
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "App Stats page should not be shown to anonymous users"
        assert dom.find(id='enforce_privacy') is not None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "App Stats page should not be shown to authenticated users"
        assert dom.find(id='enforce_privacy') is not None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "App Stats page should be shown to admin users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout()

    @patch.dict(flask_app.config, {'ENFORCE_PRIVACY': True})
    @with_context
    def test_06_user_public_profile(self):
        """Test PRIVACY user public profile privacy is respected"""
        # As Anonymou user
        url = "/account/%s" % self.name
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Public User Profile page should not be shown to anonymous users"
        assert dom.find(id='enforce_privacy') is not None, err_msg
        # As Authenticated user but NOT ADMIN
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Public User Profile page should not be shown to authenticated users"
        assert dom.find(id='enforce_privacy') is not None, err_msg
        self.signout
        # As Authenticated user but ADMIN
        self.signin(email=self.root_addr, password=self.root_password)
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "Public User Profile page should be shown to admin users"
        assert dom.find(id='enforce_privacy') is None, err_msg
        self.signout()

########NEW FILE########
__FILENAME__ = test_ratelimit
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
This module tests the RateLimit class and decorator for the API.

It tests all the actions: GET, POST, DEL and PUT, as well as the specific
API endpoints like userprogress or vmcp.

"""
import json

from default import Test, db, with_context
from pybossa.model.app import App


class TestAPI(Test):
    def setUp(self):
        super(TestAPI, self).setUp()
        with self.flask_app.app_context():
            self.create()
            self.redis_flushall()


    @with_context
    def check_limit(self, url, action, obj, data=None):
        # Set the limit
        limit = 299
        # Start check
        for i in range(limit, -1, -1):
            if action == 'get':
                res = self.app.get(url)
            elif action == 'post':
                if obj == 'app':
                    data = dict(name=i,
                                short_name=i,
                                long_description=u'something')
                data = json.dumps(data)
                res = self.app.post(url, data=data)
            elif action == 'put':
                _url = '/api/%s/%s' % (obj, i)

                if obj == 'app':
                    data = dict(name=i,
                                short_name=i,
                                long_description=u'something')
                data = json.dumps(data)

                res = self.app.put(_url + url, data)
            elif action == 'delete':
                _url = '/api/%s/%s' % (obj, i)
                res = self.app.delete(_url + url)
            else:
                raise Exception("action not found")
            # Error message
            err_msg = "GET X-RateLimit-Remaining not working"
            # Tests
            print "X-RateLimit-Remaining: %s" % res.headers['X-RateLimit-Remaining']
            print "Expected value: %s" % i
            assert int(res.headers['X-RateLimit-Remaining']) == i, err_msg
            if res.headers['X-RateLimit-Remaining'] == 0:
                error = json.loads(res.data)
                err_msg = "The status_code should be 429"
                assert error['status_code'] == 429, err_msg
                err_msg = "The status should be failed"
                assert error['status'] == 'failed', err_msg
                err_msg = "The exception_cls should be TooManyRequests"
                assert error['exception_cls'] == 'TooManyRequests', err_msg

    @with_context
    def test_00_api_get(self):
        """Test API GET rate limit."""
        # GET as Anonymous
        url = '/api/'
        action = 'get'
        self.check_limit(url, action, 'app')

    @with_context
    def test_00_app_get(self):
        """Test API.app GET rate limit."""
        # GET as Anonymous
        url = '/api/app'
        action = 'get'
        self.check_limit(url, action, 'app')

    @with_context
    def test_01_app_post(self):
        """Test API.app POST rate limit."""
        url = '/api/app?api_key=' + self.api_key
        self.check_limit(url, 'post', 'app')

    @with_context
    def test_02_app_delete(self):
        """Test API.app DELETE rate limit."""
        for i in range(300):
            app = App(name=str(i), short_name=str(i),
                      description=str(i), owner_id=1)
            db.session.add(app)
            db.session.commit()

        url = '?api_key=%s' % (self.api_key)
        self.check_limit(url, 'delete', 'app')

    @with_context
    def test_03_app_put(self):
        """Test API.app PUT rate limit."""
        for i in range(300):
            app = App(name=str(i), short_name=str(i),
                      description=str(i), owner_id=1)
            db.session.add(app)
        db.session.commit()

        url = '?api_key=%s' % (self.api_key)
        self.check_limit(url, 'put', 'app')

    @with_context
    def test_04_new_task(self):
        """Test API.new_task(app_id) GET rate limit."""
        url = '/api/app/1/newtask'
        self.check_limit(url, 'get', 'app')

    @with_context
    def test_05_vmcp(self):
        """Test API.vmcp GET rate limit."""
        url = '/api/vmcp'
        self.check_limit(url, 'get', 'app')

    @with_context
    def test_05_user_progress(self):
        """Test API.user_progress GET rate limit."""
        url = '/api/app/1/userprogress'
        self.check_limit(url, 'get', 'app')

########NEW FILE########
__FILENAME__ = test_sched
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import json
import random

from helper import sched
from default import Test, db, with_context
from pybossa.model.task import Task
from pybossa.model.app import App
from pybossa.model.user import User
from pybossa.model.task_run import TaskRun
import pybossa


class TestSched(sched.Helper):
    def setUp(self):
        super(TestSched, self).setUp()
        self.endpoints = ['app', 'task', 'taskrun']

    # Tests
    @with_context
    def test_anonymous_01_newtask(self):
        """ Test SCHED newtask returns a Task for the Anonymous User"""
        # Del previous TaskRuns
        self.create()
        self.del_task_runs()

        res = self.app.get('api/app/1/newtask')
        print res.data
        data = json.loads(res.data)
        assert data['info'], data

    @with_context
    def test_anonymous_02_gets_different_tasks(self):
        """ Test SCHED newtask returns N different Tasks for the Anonymous User"""
        # Del previous TaskRuns
        self.del_task_runs()

        assigned_tasks = []
        # Get a Task until scheduler returns None
        res = self.app.get('api/app/1/newtask')
        data = json.loads(res.data)
        while data.get('info') is not None:
            # Check that we have received a Task
            assert data.get('info'),  data

            # Save the assigned task
            assigned_tasks.append(data)

            # Submit an Answer for the assigned task
            tr = TaskRun(app_id=data['app_id'], task_id=data['id'],
                         user_ip="127.0.0.1",
                         info={'answer': 'Yes'})
            db.session.add(tr)
            db.session.commit()
            res = self.app.get('api/app/1/newtask')
            data = json.loads(res.data)

        # Check if we received the same number of tasks that the available ones
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        assert len(assigned_tasks) == len(tasks), len(assigned_tasks)
        # Check if all the assigned Task.id are equal to the available ones
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        err_msg = "Assigned Task not found in DB Tasks"
        for at in assigned_tasks:
            assert self.is_task(at['id'], tasks), err_msg
        # Check that there are no duplicated tasks
        err_msg = "One Assigned Task is duplicated"
        for at in assigned_tasks:
            assert self.is_unique(at['id'], assigned_tasks), err_msg

    @with_context
    def test_anonymous_03_respects_limit_tasks(self):
        """ Test SCHED newtask respects the limit of 30 TaskRuns per Task"""
        # Del previous TaskRuns
        self.del_task_runs()

        assigned_tasks = []
        # Get Task until scheduler returns None
        for i in range(10):
            res = self.app.get('api/app/1/newtask')
            data = json.loads(res.data)

            while data.get('info') is not None:
                # Check that we received a Task
                assert data.get('info'),  data

                # Save the assigned task
                assigned_tasks.append(data)

                # Submit an Answer for the assigned task
                tr = TaskRun(app_id=data['app_id'], task_id=data['id'],
                             user_ip="127.0.0." + str(i),
                             info={'answer': 'Yes'})
                db.session.add(tr)
                db.session.commit()
                res = self.app.get('api/app/1/newtask')
                data = json.loads(res.data)

        # Check if there are 30 TaskRuns per Task
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        for t in tasks:
            assert len(t.task_runs) == 10, len(t.task_runs)
        # Check that all the answers are from different IPs
        err_msg = "There are two or more Answers from same IP"
        for t in tasks:
            for tr in t.task_runs:
                assert self.is_unique(tr.user_ip, t.task_runs), err_msg

    @with_context
    def test_user_01_newtask(self):
        """ Test SCHED newtask returns a Task for John Doe User"""
        # Del previous TaskRuns
        self.create()
        self.del_task_runs()

        # Register
        self.register()
        self.signin()
        res = self.app.get('api/app/1/newtask')
        data = json.loads(res.data)
        assert data['info'], data
        self.signout()

    @with_context
    def test_user_02_gets_different_tasks(self):
        """ Test SCHED newtask returns N different Tasks for John Doe User"""
        # Del previous TaskRuns
        self.create()
        self.del_task_runs()

        # Register
        self.register()
        self.signin()

        assigned_tasks = []
        # Get Task until scheduler returns None
        res = self.app.get('api/app/1/newtask')
        data = json.loads(res.data)
        while data.get('info') is not None:
            # Check that we received a Task
            assert data.get('info'),  data

            # Save the assigned task
            assigned_tasks.append(data)

            # Submit an Answer for the assigned task
            tr = dict(app_id=data['app_id'], task_id=data['id'],
                      info={'answer': 'No'})
            tr = json.dumps(tr)

            self.app.post('/api/taskrun', data=tr)
            res = self.app.get('api/app/1/newtask')
            data = json.loads(res.data)

        # Check if we received the same number of tasks that the available ones
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        assert len(assigned_tasks) == len(tasks), assigned_tasks
        # Check if all the assigned Task.id are equal to the available ones
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        err_msg = "Assigned Task not found in DB Tasks"
        for at in assigned_tasks:
            assert self.is_task(at['id'], tasks), err_msg
        # Check that there are no duplicated tasks
        err_msg = "One Assigned Task is duplicated"
        for at in assigned_tasks:
            assert self.is_unique(at['id'], assigned_tasks), err_msg

    @with_context
    def test_user_03_respects_limit_tasks(self):
        """ Test SCHED newtask respects the limit of 30 TaskRuns per Task"""
        # Del previous TaskRuns
        self.create()
        self.del_task_runs()

        assigned_tasks = []
        # We need one extra loop to allow the scheduler to mark a task as completed
        for i in range(11):
            self.register(fullname=self.user.username + str(i),
                          name=self.user.username + str(i),
                          password=self.user.username + str(i))
            self.signin()
            # Get Task until scheduler returns None
            res = self.app.get('api/app/1/newtask')
            data = json.loads(res.data)

            while data.get('info') is not None:
                # Check that we received a Task
                assert data.get('info'),  data

                # Save the assigned task
                assigned_tasks.append(data)

                # Submit an Answer for the assigned task
                tr = dict(app_id=data['app_id'], task_id=data['id'],
                          info={'answer': 'No'})
                tr = json.dumps(tr)
                self.app.post('/api/taskrun', data=tr)

                res = self.app.get('api/app/1/newtask')
                data = json.loads(res.data)
            self.signout()

        # Check if there are 30 TaskRuns per Task
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        for t in tasks:
            assert len(t.task_runs) == 10, t.task_runs
        # Check that all the answers are from different IPs
        err_msg = "There are two or more Answers from same User"
        for t in tasks:
            for tr in t.task_runs:
                assert self.is_unique(tr.user_id, t.task_runs), err_msg
        # Check that task.state is updated to completed
        for t in tasks:
            assert t.state == "completed", t.state

    @with_context
    def test_tasks_for_user_ip_id(self):
        """ Test SCHED newtask to see if sends the same ammount of Task to
            user_id and user_ip
        """
        # Del Fixture Task
        self.create()
        self.del_task_runs()

        assigned_tasks = []
        for i in range(10):
            signin = False
            if random.random >= 0.5:
                signin = True
                self.register(fullname=self.user.username + str(i),
                              name=self.user.username + str(i),
                              password=self.user.username + str(i))

            if signin:
                self.signin()
            # Get Task until scheduler returns None
            res = self.app.get('api/app/1/newtask')
            data = json.loads(res.data)

            while data.get('info') is not None:
                # Check that we received a Task
                assert data.get('info'),  data

                # Save the assigned task
                assigned_tasks.append(data)

                # Submit an Answer for the assigned task
                if signin:
                    tr = dict(app_id=data['app_id'], task_id=data['id'],
                              info={'answer': 'No'})
                    tr = json.dumps(tr)
                    self.app.post('/api/taskrun', data=tr)
                else:
                    tr = TaskRun(app_id=data['app_id'], task_id=data['id'],
                                 user_ip="127.0.0." + str(i),
                                 info={'answer': 'Yes'})
                    db.session.add(tr)
                    db.session.commit()

                res = self.app.get('api/app/1/newtask')
                data = json.loads(res.data)
            if signin:
                self.signout()

        # Check if there are 30 TaskRuns per Task
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        for t in tasks:
            assert len(t.task_runs) == 10, t.task_runs
        # Check that all the answers are from different IPs and IDs
        err_msg1 = "There are two or more Answers from same User ID"
        err_msg2 = "There are two or more Answers from same User IP"
        for t in tasks:
            for tr in t.task_runs:
                if tr.user_id:
                    assert self.is_unique(tr.user_id, t.task_runs), err_msg1
                else:
                    assert self.is_unique(tr.user_ip, t.task_runs), err_msg2

    @with_context
    def test_task_preloading(self):
        """Test TASK Pre-loading works"""
        # Del previous TaskRuns
        self.create()
        self.del_task_runs()

        # Register
        self.register()
        self.signin()

        assigned_tasks = []
        # Get Task until scheduler returns None
        res = self.app.get('api/app/1/newtask')
        task1 = json.loads(res.data)
        # Check that we received a Task
        assert task1.get('info'),  task1
        # Pre-load the next task for the user
        res = self.app.get('api/app/1/newtask?offset=1')
        task2 = json.loads(res.data)
        # Check that we received a Task
        assert task2.get('info'),  task2
        # Check that both tasks are different
        assert task1.get('id') != task2.get('id'), "Tasks should be different"
        ## Save the assigned task
        assigned_tasks.append(task1)
        assigned_tasks.append(task2)

        # Submit an Answer for the assigned and pre-loaded task
        for t in assigned_tasks:
            tr = dict(app_id=t['app_id'], task_id=t['id'], info={'answer': 'No'})
            tr = json.dumps(tr)

            self.app.post('/api/taskrun', data=tr)
        # Get two tasks again
        res = self.app.get('api/app/1/newtask')
        task3 = json.loads(res.data)
        # Check that we received a Task
        assert task3.get('info'),  task1
        # Pre-load the next task for the user
        res = self.app.get('api/app/1/newtask?offset=1')
        task4 = json.loads(res.data)
        # Check that we received a Task
        assert task4.get('info'),  task2
        # Check that both tasks are different
        assert task3.get('id') != task4.get('id'), "Tasks should be different"
        assert task1.get('id') != task3.get('id'), "Tasks should be different"
        assert task2.get('id') != task4.get('id'), "Tasks should be different"
        # Check that a big offset returns None
        res = self.app.get('api/app/1/newtask?offset=11')
        assert json.loads(res.data) == {}, res.data

    @with_context
    def test_task_priority(self):
        """Test SCHED respects priority_0 field"""
        # Del previous TaskRuns
        self.create()
        self.del_task_runs()

        # Register
        self.register()
        self.signin()

        # By default, tasks without priority should be ordered by task.id (FIFO)
        tasks = db.session.query(Task).filter_by(app_id=1).order_by('id').all()
        res = self.app.get('api/app/1/newtask')
        task1 = json.loads(res.data)
        # Check that we received a Task
        err_msg = "Task.id should be the same"
        assert task1.get('id') == tasks[0].id, err_msg

        # Now let's change the priority to a random task
        import random
        t = random.choice(tasks)
        # Increase priority to maximum
        t.priority_0 = 1
        db.session.add(t)
        db.session.commit()
        # Request again a new task
        res = self.app.get('api/app/1/newtask')
        task1 = json.loads(res.data)
        # Check that we received a Task
        err_msg = "Task.id should be the same"
        assert task1.get('id') == t.id, err_msg
        err_msg = "Task.priority_0 should be the 1"
        assert task1.get('priority_0') == 1, err_msg

    def _add_task_run(self, app, task, user=None):
        tr = TaskRun(app=app, task=task, user=user)
        db.session.add(tr)
        db.session.commit()

    @with_context
    def test_no_more_tasks(self):
        """Test that a users gets always tasks"""
        self.create()
        app = App(short_name='egil', name='egil',
                  description='egil')
        owner = db.session.query(User).get(1)
        app.owner_id = owner.id
        db.session.add(app)
        db.session.commit()

        app_id = app.id

        for i in range(20):
            task = Task(app=app, info={'i': i}, n_answers=10)
            db.session.add(task)
            db.session.commit()

        tasks = db.session.query(Task).filter_by(app_id=app.id).limit(11).all()
        for t in tasks[0:10]:
            for x in range(10):
                self._add_task_run(app, t)

        assert tasks[0].n_answers == 10

        url = 'api/app/%s/newtask' % app_id
        res = self.app.get(url)
        data = json.loads(res.data)

        err_msg = "User should get a task"
        assert 'app_id' in data.keys(), err_msg
        assert data['app_id'] == app_id, err_msg
        assert data['id'] == tasks[10].id, err_msg


class TestGetBreadthFirst(Test):
    def setUp(self):
        super(TestGetBreadthFirst, self).setUp()
        with self.flask_app.app_context():
            self.create()


    def del_task_runs(self, app_id=1):
        """Deletes all TaskRuns for a given app_id"""
        db.session.query(TaskRun).filter_by(app_id=1).delete()
        db.session.commit()
        db.session.remove()

    @with_context
    def test_get_default_task_anonymous(self):
        self._test_get_breadth_first_task()

    @with_context
    def test_get_breadth_first_task_user(self):
        user = self.create_users()[0]
        self._test_get_breadth_first_task(user)

    @with_context
    def test_get_random_task(self):
        self._test_get_random_task()

    def _test_get_random_task(self, user=None):
        task = pybossa.sched.get_random_task(app_id=1)
        assert task is not None, task

        tasks = db.session.query(Task).all()
        for t in tasks:
            db.session.delete(t)
        db.session.commit()
        task = pybossa.sched.get_random_task(app_id=1)
        assert task is None, task


    def _test_get_breadth_first_task(self, user=None):
        self.del_task_runs()
        if user:
            short_name = 'xyzuser'
        else:
            short_name = 'xyznouser'

        app = App(short_name=short_name, name=short_name,
              description=short_name)
        owner = db.session.query(User).get(1)

        app.owner = owner
        task = Task(app=app, state='0', info={})
        task2 = Task(app=app, state='0', info={})
        task.app = app
        task2.app = app
        db.session.add(app)
        db.session.add(task)
        db.session.add(task2)
        db.session.commit()
        taskid = task.id
        appid = app.id
        # give task2 a bunch of runs
        for idx in range(2):
            self._add_task_run(app, task2)

        # now check we get task without task runs as anonymous user
        out = pybossa.sched.get_breadth_first_task(appid)
        assert out.id == taskid, out

        # now check we get task without task runs as a user
        owner = db.session.query(User).get(1)
        out = pybossa.sched.get_breadth_first_task(appid, owner.id)
        assert out.id == taskid, out


        # now check that offset works
        out1 = pybossa.sched.get_breadth_first_task(appid)
        out2 = pybossa.sched.get_breadth_first_task(appid, offset=1)
        assert out1.id != out2.id, out

        # asking for a bigger offset (max 10)
        out2 = pybossa.sched.get_breadth_first_task(appid, offset=11)
        assert out2 is None, out

        self._add_task_run(app, task)
        out = pybossa.sched.get_breadth_first_task(appid)
        assert out.id == taskid, out

        # now add 2 more taskruns. We now have 3 and 2 task runs per task
        self._add_task_run(app, task)
        self._add_task_run(app, task)
        out = pybossa.sched.get_breadth_first_task(appid)
        assert out.id == task2.id, out

    def _add_task_run(self, app, task, user=None):
        tr = TaskRun(app=app, task=task, user=user)
        db.session.add(tr)
        db.session.commit()

########NEW FILE########
__FILENAME__ = test_sched_2
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from helper import sched
from default import with_context
import json


class TestSched(sched.Helper):
    def setUp(self):
        super(TestSched, self).setUp()
        self.endpoints = ['app', 'task', 'taskrun']

    # Tests
    @with_context
    def test_incremental_tasks(self):
        """ Test incremental SCHED strategy - second TaskRun receives first gaven answer"""
        self.create_2(sched='incremental')

        # Del previous TaskRuns
        self.del_task_runs()

        # Register
        self.register(fullname=self.user.fullname, name=self.user.username,
                      password=self.user.password)
        self.register(fullname="Marie Doe", name="mariedoe", password="dr0wss4p")
        self.signin()

        # Get the only task with no runs!
        res = self.app.get('api/app/1/newtask')
        data = json.loads(res.data)
        # Check that we received a clean Task
        assert data.get('info'), data
        assert not data.get('info').get('last_answer')

        # Submit an Answer for the assigned task
        tr = dict(app_id=data['app_id'], task_id=data['id'], info={'answer': 'No'})
        tr = json.dumps(tr)

        self.app.post('/api/taskrun', data=tr)
        # No more tasks available for this user!
        res = self.app.get('api/app/1/newtask')
        data = json.loads(res.data)
        assert not data

        #### Get the only task now with an answer as Anonimous!
        self.signout()
        res = self.app.get('api/app/1/newtask')
        data = json.loads(res.data)

        # Check that we received a Task with answer
        assert data.get('info'), data
        assert data.get('info').get('last_answer').get('answer') == 'No'

        # Submit a second Answer as Anonimous
        tr = dict(app_id=data['app_id'], task_id=data['id'],
                  info={'answer': 'No No'})
        tr = json.dumps(tr)

        self.app.post('/api/taskrun', data=tr)

        #### Get the only task now with an answer as User2!
        self.signin(email="mariedoe@example.com", password="dr0wss4p")
        res = self.app.get('api/app/1/newtask')
        data = json.loads(res.data)

        # Check that we received a Task with answer
        assert data.get('info'), data
        assert data.get('info').get('last_answer').get('answer') == 'No No'

########NEW FILE########
__FILENAME__ = test_stats
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import time
from default import Test, db, with_context
from pybossa.model.task_run import TaskRun
import pybossa.stats as stats


class TestStats(Test):
    def setUp(self):
        super(TestStats, self).setUp()
        with self.flask_app.app_context():
            self.create()

    # Tests
    # Fixtures will create 10 tasks and will need 10 answers per task, so
    # the app will be completed when 100 tasks have been submitted
    # Only 10 task_runs are saved in the DB

    def test_00_avg_n_tasks(self):
        """Test STATS avg and n of tasks method works"""
        with self.flask_app.test_request_context('/'):
            avg, n_tasks = stats.get_avg_n_tasks(1)
            err_msg = "The average number of answer per task is wrong"
            assert avg == 10, err_msg
            err_msg = "The n of tasks is wrong"
            assert n_tasks == 10, err_msg

    def test_01_stats_dates(self):
        """Test STATS dates method works"""
        today = unicode(datetime.date.today())
        with self.flask_app.test_request_context('/'):
            dates, dates_n_tasks, dates_anon, dates_auth = stats.stats_dates(1)
            err_msg = "There should be 10 answers today"
            assert dates[today] == 10, err_msg
            err_msg = "There should be 100 answers per day"
            assert dates_n_tasks[today] == 100, err_msg
            err_msg = "The SUM of answers from anon and auth users should be 10"
            assert (dates_anon[today] + dates_auth[today]) == 10, err_msg

    def test_02_stats_hours(self):
        """Test STATS hours method works"""
        hour = unicode(datetime.datetime.utcnow().strftime('%H'))
        with self.flask_app.test_request_context('/'):
            hours, hours_anon, hours_auth, max_hours,\
                max_hours_anon, max_hours_auth = stats.stats_hours(1)
            print hours
            for i in range(0, 24):
                # There should be only 10 answers at current hour
                if str(i).zfill(2) == hour:
                    err_msg = "At time %s there should be 10 answers" \
                              "but there are %s" % (str(i).zfill(2),
                                                    hours[str(i).zfill(2)])
                    assert hours[str(i).zfill(2)] == 10, "There should be 10 answers"
                else:
                    err_msg = "At time %s there should be 0 answers" \
                              "but there are %s" % (str(i).zfill(2),
                                                    hours[str(i).zfill(2)])
                    assert hours[str(i).zfill(2)] == 0, err_msg

                if str(i).zfill(2) == hour:
                    tmp = (hours_anon[hour] + hours_auth[hour])
                    assert tmp == 10, "There should be 10 answers"
                else:
                    tmp = (hours_anon[str(i).zfill(2)] + hours_auth[str(i).zfill(2)])
                    assert tmp == 0, "There should be 0 answers"
            err_msg = "It should be 10, as all answers are submitted in the same hour"
            tr = db.session.query(TaskRun).all()
            for t in tr:
                print t.finish_time
            assert max_hours == 10, err_msg
            assert (max_hours_anon + max_hours_auth) == 10, err_msg

    def test_03_stats(self):
        """Test STATS stats method works"""
        today = unicode(datetime.date.today())
        hour = int(datetime.datetime.utcnow().strftime('%H'))
        date_ms = time.mktime(time.strptime(today, "%Y-%m-%d")) * 1000
        anon = 0
        auth = 0
        with self.flask_app.test_request_context('/'):
            dates_stats, hours_stats, user_stats = stats.get_stats(1)
            for item in dates_stats:
                if item['label'] == 'Anon + Auth':
                    assert item['values'][0][0] == date_ms, item['values'][0][0]
                    assert item['values'][0][1] == 10, "There should be 10 answers"
                if item['label'] == 'Anonymous':
                    assert item['values'][0][0] == date_ms, item['values'][0][0]
                    anon = item['values'][0][1]
                if item['label'] == 'Authenticated':
                    assert item['values'][0][0] == date_ms, item['values'][0][0]
                    auth = item['values'][0][1]
                if item['label'] == 'Total':
                    assert item['values'][0][0] == date_ms, item['values'][0][0]
                    assert item['values'][0][1] == 10, "There should be 10 answers"
                if item['label'] == 'Expected Answers':
                    assert item['values'][0][0] == date_ms, item['values'][0][0]
                    for i in item['values']:
                        assert i[1] == 100, "Each date should have 100 answers"
                    assert item['values'][0][1] == 100, "There should be 10 answers"
                if item['label'] == 'Estimation':
                    assert item['values'][0][0] == date_ms, item['values'][0][0]
                    v = 10
                    for i in item['values']:
                        assert i[1] == v, "Each date should have 10 extra answers"
                        v = v + 10
            assert auth + anon == 10, "date stats sum of auth and anon should be 10"

            max_hours = 0
            for item in hours_stats:
                if item['label'] == 'Anon + Auth':
                    max_hours = item['max']
                    print item
                    assert item['max'] == 10, item['max']
                    assert item['max'] == 10, "Max hours value should be 10"
                    for i in item['values']:
                        if i[0] == hour:
                            assert i[1] == 10, "There should be 10 answers"
                            assert i[2] == 5, "The size of the bubble should be 5"
                        else:
                            assert i[1] == 0, "There should be 0 answers"
                            assert i[2] == 0, "The size of the buggle should be 0"
                if item['label'] == 'Anonymous':
                    anon = item['max']
                    for i in item['values']:
                        if i[0] == hour:
                            assert i[1] == anon, "There should be anon answers"
                            assert i[2] == (anon * 5) / max_hours, "The size of the bubble should be 5"
                        else:
                            assert i[1] == 0, "There should be 0 answers"
                            assert i[2] == 0, "The size of the buggle should be 0"
                if item['label'] == 'Authenticated':
                    auth = item['max']
                    for i in item['values']:
                        if i[0] == hour:
                            assert i[1] == auth, "There should be anon answers"
                            assert i[2] == (auth * 5) / max_hours, "The size of the bubble should be 5"
                        else:
                            assert i[1] == 0, "There should be 0 answers"
                            assert i[2] == 0, "The size of the buggle should be 0"
            assert auth + anon == 10, "date stats sum of auth and anon should be 10"

            err_msg = "date stats sum of auth and anon should be 10"
            assert user_stats['n_anon'] + user_stats['n_auth'], err_msg

########NEW FILE########
__FILENAME__ = test_twitter
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
from default import Test, db, with_context
from pybossa.view.twitter import manage_user


class TestTwitter(Test):
    @with_context
    def test_manage_user(self):
        """Test TWITTER manage_user works."""
        # First with a new user
        user_data = dict(user_id=1, screen_name='twitter')
        token = dict(oauth_token='token', oauth_token_secret='secret')
        user = manage_user(token, user_data, None)
        assert user.email_addr == user_data['screen_name'], user
        assert user.name == user_data['screen_name'], user
        assert user.fullname == user_data['screen_name'], user
        assert user.twitter_user_id == user_data['user_id'], user

        # Second with the same user
        user = manage_user(token, user_data, None)
        assert user.email_addr == user_data['screen_name'], user
        assert user.name == user_data['screen_name'], user
        assert user.fullname == user_data['screen_name'], user
        assert user.twitter_user_id == user_data['user_id'], user

        # Finally with a user that already is in the system
        user_data = dict(user_id=10, screen_name=self.name)
        token = dict(oauth_token='token2', oauth_token_secret='secret2')
        user = manage_user(token, user_data, None)
        err_msg = "It should return the same user"
        assert user.twitter_user_id == 10, err_msg

########NEW FILE########
__FILENAME__ = test_generic_uploader
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""This module tests the Uploader class."""

from default import Test, with_context
from pybossa.uploader import Uploader
from werkzeug.datastructures import FileStorage
from mock import patch
from PIL import Image
import tempfile
import os
from nose.tools import assert_raises


class TestUploader(Test):

    """Test PyBossa Uploader module."""

    def setUp(self):
        """SetUp method."""
        super(TestUploader, self).setUp()
        with self.flask_app.app_context():
            self.create()

    @with_context
    def test_uploader_init(self):
        """Test UPLOADER init method works."""
        u = Uploader()
        new_extensions = ['pdf', 'doe']
        new_uploader = Uploader()
        with patch.dict(self.flask_app.config,
                        {'ALLOWED_EXTENSIONS': new_extensions}):
            new_uploader.init_app(self.flask_app)
            expected_extensions = set.union(u.allowed_extensions, new_extensions)
            err_msg = "The new uploader should support two extra extensions"
            assert expected_extensions == new_uploader.allowed_extensions, err_msg

    @with_context
    def test_allowed_file(self):
        """Test UPLOADER allowed_file method works."""
        u = Uploader()
        for ext in u.allowed_extensions:
            # Change extension to uppercase to check that it works too
            filename = 'test.%s' % ext.upper()
            err_msg = ("This file: %s should be allowed, but it failed"
                       % filename)
            assert u.allowed_file(filename) is True, err_msg

        err_msg = "Non allowed extensions should return false"
        assert u.allowed_file('wrong.pdf') is False, err_msg

    @with_context
    def test_get_filename_extension(self):
        """Test UPLOADER get_filename_extension works."""
        u = Uploader()
        filename = "image.png"
        err_msg = "The extension should be PNG"
        assert u.get_filename_extension(filename) == 'png', err_msg
        filename = "image.jpg"
        err_msg = "The extension should be JPEG"
        assert u.get_filename_extension(filename) == 'jpeg', err_msg
        filename = "imagenoextension"
        err_msg = "The extension should be None"
        assert u.get_filename_extension(filename) == None, err_msg

    @with_context
    def test_crop(self):
        """Test UPLOADER crop works."""
        u = Uploader()
        size = (100, 100)
        im = Image.new('RGB', size)
        folder = tempfile.mkdtemp()
        u.upload_folder = folder
        im.save(os.path.join(folder, 'image.png'))
        coordinates = (0, 0, 50, 50)
        file = FileStorage(filename=os.path.join(folder, 'image.png'))
        with patch('pybossa.uploader.Image', return_value=True):
            err_msg = "It should crop the image"
            assert u.crop(file, coordinates) is True, err_msg

        with patch('pybossa.uploader.Image.open', side_effect=IOError):
            err_msg = "It should return false"
            assert u.crop(file, coordinates) is False, err_msg

    @with_context
    def test_external_url_handler(self):
        """Test UPLOADER external_url_handler works."""
        u = Uploader()
        with patch.object(u, '_lookup_url', return_value='url'):
            assert u.external_url_handler(BaseException, 'endpoint', 'values') == 'url'

    @with_context
    def test_external_url_handler_fails(self):
        """Test UPLOADER external_url_handler fails works."""
        u = Uploader()
        with patch.object(u, '_lookup_url', return_value=None):
            with patch('pybossa.uploader.sys') as mysys:
                mysys.exc_info.return_value=(BaseException, BaseException, None)
                assert_raises(BaseException,
                              u.external_url_handler,
                              BaseException,
                              'endpoint',
                              'values')

    @with_context
    def test_external_url_handler_fails_2(self):
        """Test UPLOADER external_url_handler fails works."""
        u = Uploader()
        with patch.object(u, '_lookup_url', return_value=None):
            with patch('pybossa.uploader.sys') as mysys:
                mysys.exc_info.return_value=(BaseException, BaseException, None)
                assert_raises(IOError,
                              u.external_url_handler,
                              IOError,
                              'endpoint',
                              'values')

########NEW FILE########
__FILENAME__ = test_local_uploader
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""This module tests the Uploader class."""

import os
import tempfile
from default import Test, with_context
from pybossa.uploader.local import LocalUploader
from mock import patch
from werkzeug.datastructures import FileStorage


class TestLocalUploader(Test):

    """Test PyBossa Uploader module."""

    @with_context
    def test_local_uploader_init(self):
        """Test LOCAL UPLOADER init works."""
        u = LocalUploader()
        u.init_app(self.flask_app)
        new_extensions = ['pdf', 'doe']
        new_upload_folder = '/tmp/'
        new_config_ext = {'ALLOWED_EXTENSIONS': new_extensions}
        new_config_uf = {'UPLOAD_FOLDER': new_upload_folder}
        with patch.dict(self.flask_app.config, new_config_ext):
            with patch.dict(self.flask_app.config, new_config_uf):
                new_uploader = LocalUploader()
                new_uploader.init_app(self.flask_app)
                expected_extensions = set.union(u.allowed_extensions,
                                                new_extensions)
                err_msg = "The new uploader should support two extra extensions"
                assert expected_extensions == new_uploader.allowed_extensions, err_msg
                err_msg = "Upload folder by default is /tmp/"
                assert new_uploader.upload_folder == '/tmp/', err_msg

    @with_context
    @patch('werkzeug.datastructures.FileStorage.save', side_effect=IOError)
    def test_local_uploader_upload_fails(self, mock):
        """Test LOCAL UPLOADER upload fails."""
        u = LocalUploader()
        file = FileStorage(filename='test.jpg')
        res = u.upload_file(file, container='user_3')
        err_msg = ("Upload file should return False, \
                   as there is an exception")
        assert res is False, err_msg


    @with_context
    @patch('werkzeug.datastructures.FileStorage.save', return_value=None)
    def test_local_uploader_upload_correct_file(self, mock):
        """Test LOCAL UPLOADER upload works."""
        mock.save.return_value = None
        u = LocalUploader()
        file = FileStorage(filename='test.jpg')
        res = u.upload_file(file, container='user_3')
        err_msg = ("Upload file should return True, \
                   as this extension is allowed")
        assert res is True, err_msg

    @with_context
    @patch('werkzeug.datastructures.FileStorage.save', return_value=None)
    def test_local_uploader_upload_wrong_file(self, mock):
        """Test LOCAL UPLOADER upload works with wrong extension."""
        mock.save.return_value = None
        u = LocalUploader()
        file = FileStorage(filename='test.txt')
        res = u.upload_file(file, container='user_3')
        err_msg = ("Upload file should return False, \
                   as this extension is not allowed")
        assert res is False, err_msg

    @with_context
    @patch('werkzeug.datastructures.FileStorage.save', return_value=None)
    def test_local_folder_is_created(self, mock):
        """Test LOCAL UPLOADER folder creation works."""
        mock.save.return_value = True
        u = LocalUploader()
        u.upload_folder = tempfile.mkdtemp()
        file = FileStorage(filename='test.jpg')
        container = 'mycontainer'
        res = u.upload_file(file, container=container)
        path = os.path.join(u.upload_folder, container)
        err_msg = "This local path should exist: %s" % path
        assert os.path.isdir(path) is True, err_msg

    @with_context
    @patch('os.remove', return_value=None)
    def test_local_folder_delete(self, mock):
        """Test LOCAL UPLOADER delete works."""
        u = LocalUploader()
        err_msg = "Delete should return true"
        assert u.delete_file('file', 'container') is True, err_msg

    @with_context
    @patch('os.remove', side_effect=OSError)
    def test_local_folder_delete_fails(self, mock):
        """Test LOCAL UPLOADER delete fail works."""
        u = LocalUploader()
        err_msg = "Delete should return False"
        assert u.delete_file('file', 'container') is False, err_msg


########NEW FILE########
__FILENAME__ = test_rackspace_uploader
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""This module tests the Uploader class."""

from default import Test
from pybossa.uploader.rackspace import RackspaceUploader
from mock import patch, PropertyMock, call, MagicMock
from werkzeug.datastructures import FileStorage
from pyrax.fakes import FakeContainer
from pyrax.exceptions import NoSuchObject, NoSuchContainer
from test_uploader import cloudfiles_mock, fake_container


class TestRackspaceUploader(Test):

    """Test PyBossa Rackspace Uploader module."""

    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    def test_rackspace_uploader_init(self, Mock):
        """Test RACKSPACE UPLOADER init works."""
        new_extensions = ['pdf', 'doe']
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles',
                   return_value=cloudfiles_mock):
            with patch.dict(self.flask_app.config,
                            {'ALLOWED_EXTENSIONS': new_extensions}):

                with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
                    mycf.get_container.return_value = True
                    u = RackspaceUploader()
                    res = u.init_app(self.flask_app, cont_name='mycontainer')
                    err_msg = "It should return the container."
                    assert res is True, err_msg
                    err_msg = "The container name should be updated."
                    assert u.cont_name == 'mycontainer', err_msg
                    for ext in new_extensions:
                        err_msg = "The .%s extension should be allowed" % ext
                        assert ext in u.allowed_extensions, err_msg

    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    @patch('pybossa.uploader.rackspace.pyrax.utils.get_checksum',
           return_value="1234abcd")
    def test_rackspace_uploader_creates_container(self, mock, mock2):
        """Test RACKSPACE UPLOADER creates container works."""
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            mycf.get_container.side_effect = NoSuchContainer
            mycf.create_container.return_value = True
            mycf.make_container_public.return_value = True
            u = RackspaceUploader()
            res = u.init_app(self.flask_app)
            err_msg = "Init app should return the container."
            assert res is True, err_msg


    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    @patch('pybossa.uploader.rackspace.pyrax.utils.get_checksum',
           return_value="1234abcd")
    def test_rackspace_uploader_upload_correct_file(self, mock, mock2):
        """Test RACKSPACE UPLOADER upload file works."""
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            mycf.upload_file.return_value=True
            mycf.get_object.side_effect = NoSuchObject
            u = RackspaceUploader()
            u.init_app(self.flask_app)
            file = FileStorage(filename='test.jpg')
            err_msg = "Upload file should return True"
            assert u.upload_file(file, container='user_3') is True, err_msg
            calls = [call.get_container('user_3'),
                     call.get_container().get_object('test.jpg')]
            mycf.assert_has_calls(calls, any_order=True)

    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    @patch('pybossa.uploader.rackspace.pyrax.utils.get_checksum',
           return_value="1234abcd")
    def test_rackspace_uploader_upload_correct_purgin_first_file(self, mock, mock2):
        """Test RACKSPACE UPLOADER upload file purging first file works."""
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            mycf.upload_file.return_value=True
            mycf.get_object.side_effect = True
            u = RackspaceUploader()
            u.init_app(self.flask_app)
            file = FileStorage(filename='test.jpg')
            err_msg = "Upload file should return True"
            assert u.upload_file(file, container='user_3') is True, err_msg
            calls = [call.get_container('user_3'),
                     call.get_container().get_object().delete(),
                     call.get_container().get_object('test.jpg')]
            print mycf.mock_calls
            mycf.assert_has_calls(calls, any_order=True)


    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    @patch('pybossa.uploader.rackspace.pyrax.utils.get_checksum',
           return_value="1234abcd")
    def test_rackspace_uploader_upload_file_fails(self, mock, mock2):
        """Test RACKSPACE UPLOADER upload file fail works."""
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            from pyrax.exceptions import UploadFailed
            mycf.upload_file.side_effect = UploadFailed
            u = RackspaceUploader()
            u.init_app(self.flask_app)
            file = FileStorage(filename='test.jpg')
            err_msg = "Upload file should return False"
            assert u.upload_file(file, container='user_3') is False, err_msg

    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    @patch('pybossa.uploader.rackspace.pyrax.utils.get_checksum',
           return_value="1234abcd")
    def test_rackspace_uploader_upload_file_object_fails(self, mock, mock2):
        """Test RACKSPACE UPLOADER upload file object fail works."""
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            from pyrax.exceptions import NoSuchObject
            container = MagicMock()
            container.get_object.side_effect = NoSuchObject
            mycf.get_container.return_value = container
            u = RackspaceUploader()
            u.init_app(self.flask_app)
            file = FileStorage(filename='test.jpg')
            err_msg = "Upload file should return True"
            assert u.upload_file(file, container='user_3') is True, err_msg

    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    @patch('pybossa.uploader.rackspace.pyrax.utils.get_checksum',
           return_value="1234abcd")
    def test_rackspace_uploader_upload_wrong_file(self, mock, mock2):
        """Test RACKSPACE UPLOADER upload wrong file extension works."""
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            mycf.upload_file.return_value = True
            u = RackspaceUploader()
            u.init_app(self.flask_app)
            file = FileStorage(filename='test.docs')
            err_msg = "Upload file should return False"
            res = u.upload_file(file, container='user_3')
            assert res is False, err_msg

    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    def test_rackspace_uploader_lookup_url(self, mock1):
        """Test RACKSPACE UPLOADER lookup returns a valid link."""
        uri = 'http://rackspace.com'
        filename = 'test.jpg'
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            cdn_enabled_mock = PropertyMock(return_value=True)
            type(fake_container).cdn_enabled = cdn_enabled_mock
            mycf.get_container.return_value = fake_container

            u = RackspaceUploader()
            u.init_app(self.flask_app)
            res = u._lookup_url('rackspace', {'filename': filename,
                                              'container': 'user_3'})
            expected_url = "%s/%s" % (uri, filename)
            print res
            err_msg = "We should get the following URL: %s" % expected_url
            assert res == expected_url, err_msg

    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    def test_rackspace_uploader_lookup_url_none(self, mock1):
        """Test RACKSPACE UPLOADER lookup returns None for non enabled CDN."""
        filename = 'test.jpg'
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            cdn_enabled_mock = PropertyMock(return_value=False)
            type(fake_container).cdn_enabled = cdn_enabled_mock
            mycf.get_container.return_value = fake_container

            u = RackspaceUploader()
            u.init_app(self.flask_app)
            res = u._lookup_url('rackspace', {'filename': filename,
                                              'container': 'user_3'})
            err_msg = "We should get the None"
            assert res is None, err_msg

    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    def test_rackspace_uploader_get_container(self, mock1):
        """Test RACKSPACE UPLOADER get_container method works."""
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            cdn_enabled_mock = PropertyMock(return_value=False)
            type(fake_container).cdn_enabled = cdn_enabled_mock
            mycf.get_container.side_effect = NoSuchContainer

            calls = [call.get_container('user_3'),
                     call.create_container('user_3'),
                     call.make_container_public('user_3')
                     ]
            u = RackspaceUploader()
            u.init_app(self.flask_app)
            assert u.get_container('user_3')
            mycf.assert_has_calls(calls, any_order=True)

    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    def test_rackspace_uploader_delete(self, mock1):
        """Test RACKSPACE UPLOADER delete method works."""
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            calls = [call.get_container('container'),
                     call.get_container().get_object('file'),
                     call.get_container().get_object().delete()
                     ]
            u = RackspaceUploader()
            u.init_app(self.flask_app)
            err_msg = "It should return True"
            assert u.delete_file('file', 'container') is True, err_msg
            mycf.assert_has_calls(calls, any_order=True)

    @patch('pybossa.uploader.rackspace.pyrax.set_credentials',
           return_value=True)
    def test_rackspace_uploader_delete_fails(self, mock1):
        """Test RACKSPACE UPLOADER delete fails method works."""
        with patch('pybossa.uploader.rackspace.pyrax.cloudfiles') as mycf:
            container = MagicMock()
            container.get_object.side_effect = NoSuchObject
            mycf.get_container.return_value = container

            calls = [call.get_container('container'),
                     ]
            u = RackspaceUploader()
            u.init_app(self.flask_app)
            err_msg = "It should return False"
            assert u.delete_file('file', 'container') is False, err_msg
            mycf.assert_has_calls(calls, any_order=True)

########NEW FILE########
__FILENAME__ = test_util
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
import pybossa.util
from default import Test, db
from mock import patch
from datetime import datetime, timedelta
import dateutil.parser
import calendar
import time
import csv
import tempfile


class TestWebModule(Test):
    def setUp(self):
        super(TestWebModule, self).setUp()
        with self.flask_app.app_context():
            self.create()

    def test_jsonpify(self):
        """Test jsonpify decorator works."""
        res = self.app.get('/api/app/1?callback=mycallback')
        err_msg = "mycallback should be included in the response"
        assert "mycallback" in res.data, err_msg
        err_msg = "Status code should be 200"
        assert res.status_code == 200, err_msg

    def test_cors(self):
        """Test CORS decorator works."""
        res = self.app.get('/api/app/1')
        err_msg = "CORS should be enabled"
        print res.headers
        assert res.headers['Access-Control-Allow-Origin'] == '*', err_msg
        methods = ['PUT', 'HEAD', 'DELETE', 'OPTIONS', 'GET']
        for m in methods:
            assert m in res.headers['Access-Control-Allow-Methods'], err_msg
        assert res.headers['Access-Control-Max-Age'] == '21600', err_msg
        headers = 'CONTENT-TYPE, AUTHORIZATION'
        assert res.headers['Access-Control-Allow-Headers'] == headers, err_msg

    def test_pretty_date(self):
        """Test pretty_date works."""
        now = datetime.now()
        pd = pybossa.util.pretty_date()
        assert pd == "just now", pd

        pd = pybossa.util.pretty_date(now.isoformat())
        assert pd == "just now", pd

        pd = pybossa.util.pretty_date(calendar.timegm(time.gmtime()))
        assert pd == "just now", pd

        d = now + timedelta(days=10)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == '', pd

        d = now - timedelta(seconds=10)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == '10 seconds ago', pd

        d = now - timedelta(minutes=1)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == 'a minute ago', pd

        d = now - timedelta(minutes=2)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == '2 minutes ago', pd

        d = now - timedelta(hours=1)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == 'an hour ago', pd

        d = now - timedelta(hours=5)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == '5 hours ago', pd

        d = now - timedelta(days=1)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == 'Yesterday', pd

        d = now - timedelta(days=5)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == '5 days ago', pd

        d = now - timedelta(weeks=1)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == '1 weeks ago', pd

        d = now - timedelta(days=32)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == '1 month ago', pd

        d = now - timedelta(days=62)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == '2 months ago', pd

        d = now - timedelta(days=366)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == '1 year ago', pd

        d = now - timedelta(days=766)
        pd = pybossa.util.pretty_date(d.isoformat())
        assert pd == '2 years ago', pd

    def test_pagination(self):
        """Test Class Pagination works."""
        page = 1
        per_page = 5
        total_count = 10
        p = pybossa.util.Pagination(page, per_page, total_count)
        assert p.page == page, p.page
        assert p.per_page == per_page, p.per_page
        assert p.total_count == total_count, p.total_count

        err_msg = "It should return two pages"
        assert p.pages == 2, err_msg
        p.total_count = 7
        assert p.pages == 2, err_msg
        p.total_count = 10

        err_msg = "It should return False"
        assert p.has_prev is False, err_msg
        err_msg = "It should return True"
        assert p.has_next is True, err_msg
        p.page = 2
        assert p.has_prev is True, err_msg
        err_msg = "It should return False"
        assert p.has_next is False, err_msg

        for i in p.iter_pages():
            err_msg = "It should return the page: %s" % page
            assert i == page, err_msg
            page += 1

    def test_unicode_csv_reader(self):
        """Test unicode_csv_reader works."""
        fake_csv = ['one, two, three']
        err_msg = "Each cell should be encoded as Unicode"
        for row in pybossa.util.unicode_csv_reader(fake_csv):
            for item in row:
                assert type(item) == unicode, err_msg

    def test_UnicodeWriter(self):
        """Test UnicodeWriter class works."""
        tmp = tempfile.NamedTemporaryFile()
        uw = pybossa.util.UnicodeWriter(tmp)
        fake_csv = ['one, two, three, {"i": 1}']
        for row in csv.reader(fake_csv):
            # change it for a dict
            row[3] = dict(i=1)
            uw.writerow(row)
        tmp.seek(0)
        err_msg = "It should be the same CSV content"
        with open(tmp.name, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                for item in row:
                    assert item in fake_csv[0], err_msg

########NEW FILE########
__FILENAME__ = test_validator
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
from default import Test, db
from pybossa.model.user import User
import pybossa.validator
from pybossa.view.account import LoginForm
from wtforms import ValidationError
from nose.tools import raises


class TestValidator(Test):
    def setUp(self):
        super(TestValidator, self).setUp()
        with self.flask_app.app_context():
            self.create()

    @raises(ValidationError)
    def test_unique(self):
        """Test VALIDATOR Unique works."""
        with self.flask_app.test_request_context('/'):
            f = LoginForm()
            f.email.data = self.email_addr
            u = pybossa.validator.Unique(db.session, User,
                                         User.email_addr)
            u.__call__(f, f.email)

    @raises(ValidationError)
    def test_not_allowed_chars(self):
        """Test VALIDATOR NotAllowedChars works."""
        with self.flask_app.test_request_context('/'):
            f = LoginForm()
            f.email.data = self.email_addr + "$"
            u = pybossa.validator.NotAllowedChars()
            u.__call__(f, f.email)

    @raises(ValidationError)
    def test_comma_separated_integers(self):
        """Test VALIDATOR CommaSeparatedIntegers works."""
        with self.flask_app.test_request_context('/'):
            f = LoginForm()
            f.email.data = '1 2 3'
            u = pybossa.validator.CommaSeparatedIntegers()
            u.__call__(f, f.email)

########NEW FILE########
__FILENAME__ = test_blog
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.


from helper import web
from default import db, with_context
from pybossa.model.blogpost import Blogpost
from pybossa.model.user import User
from pybossa.model.app import App
from mock import patch




class TestBlogpostView(web.Helper):

    @with_context
    def test_blogposts_get_all(self):
        """Test blogpost GET all blogposts"""
        user = self.create_users()[1]
        app = self.create_app(info=None)
        app.owner = user
        blogpost = Blogpost(owner=user, app=app, title='thisisatitle', body='body')
        db.session.add_all([user, app, blogpost])
        db.session.commit()
        url = "/app/%s/blog" % app.short_name

        # As anonymous
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert 'thisisatitle' in res.data

        # As authenticated
        self.register()
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert 'thisisatitle' in res.data


    @with_context
    def test_blogposts_get_all_with_hidden_app(self):
        """Test blogpost GET does not show hidden apps"""
        self.register()
        admin = db.session.query(User).get(1)
        self.signout()
        self.register(name='user', email='user@user.com')
        user = db.session.query(User).get(2)
        app = self.create_app(info=None)
        app.owner = user
        app.hidden = 1
        blogpost = Blogpost(owner=user, app=app, title='thisisatitle', body='body')
        db.session.add_all([app, blogpost])
        db.session.commit()
        url = "/app/%s/blog" % app.short_name

        # As app owner
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert 'thisisatitle' in res.data

        # As authenticated
        self.signout()
        self.register(name='notowner', email='user2@user.com')
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 403, res.status_code

        # As anonymous
        self.signout()
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 401, res.status_code

        # As admin
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert 'thisisatitle' in res.data


    def test_blogpost_get_all_errors(self):
        """Test blogpost GET all raises error if the app does not exist"""
        url = "/app/non-existing-app/blog"

        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code


    @with_context
    def test_blogpost_get_one(self):
        """Test blogpost GET with id shows one blogpost"""
        user = self.create_users()[1]
        app = self.create_app(info=None)
        app.owner = user
        blogpost = Blogpost(owner=user, app=app, title='thisisatitle', body='body')
        db.session.add_all([user, app, blogpost])
        db.session.commit()
        url = "/app/%s/%s" % (app.short_name, blogpost.id)

        # As anonymous
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert 'thisisatitle' in res.data

        # As authenticated
        self.register()
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert 'thisisatitle' in res.data


    @with_context
    def test_blogpost_get_one_with_hidden_app(self):
        """Test blogpost GET a given post id with hidden app does not show the post"""
        self.register()
        admin = db.session.query(User).get(1)
        self.signout()
        self.register(name='user', email='user@user.com')
        user = db.session.query(User).get(2)
        app = self.create_app(info=None)
        app.owner = user
        app.hidden = 1
        blogpost = Blogpost(owner=user, app=app, title='thisisatitle', body='body')
        db.session.add_all([app, blogpost])
        db.session.commit()
        url = "/app/%s/%s" % (app.short_name, blogpost.id)

        # As app owner
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert 'thisisatitle' in res.data

        # As authenticated
        self.signout()
        self.register(name='notowner', email='user2@user.com')
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 403, res.status_code

        # As anonymous
        self.signout()
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 401, res.status_code

        # As admin
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert 'thisisatitle' in res.data


    @with_context
    def test_blogpost_get_one_errors(self):
        """Test blogposts GET non existing posts raises errors"""
        self.register()
        user = db.session.query(User).get(1)
        app1 = App(name='app1',
                short_name='app1',
                description=u'description')
        app2 = self.create_app(info=None)
        app1.owner = user
        app2.owner = user
        blogpost = Blogpost(owner=user, app=app1, title='thisisatitle', body='body')
        db.session.add_all([app1, app2, blogpost])
        db.session.commit()

        # To a non-existing app
        url = "/app/non-existing-app/%s" % blogpost.id
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code

        # To a non-existing post
        url = "/app/%s/999999" % app1.short_name
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code

        # To an existing post but with an app in the URL it does not belong to
        url = "/app/%s/%s" % (app2.short_name, blogpost.id)
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code


    from pybossa.view.applications import redirect

    @with_context
    @patch('pybossa.view.applications.redirect', wraps=redirect)
    def test_blogpost_create_by_owner(self, mock_redirect):
        """Test blogposts, app owners can create"""
        self.register()
        user = db.session.query(User).get(1)
        app = self.create_app(info=None)
        app.owner = user
        db.session.add(app)
        db.session.commit()
        url = "/app/%s/new-blogpost" % app.short_name

        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code

        res = self.app.post(url,
                            data={'title':'blogpost title', 'body':'body'},
                            follow_redirects=True)
        assert res.status_code == 200, res.status_code
        mock_redirect.assert_called_with('/app/%s/blog' % app.short_name)

        blogpost = db.session.query(Blogpost).first()
        assert blogpost.title == 'blogpost title', blogpost.title
        assert blogpost.app_id == app.id, blogpost.app.id
        assert blogpost.user_id == user.id, blogpost.user_id


    @with_context
    def test_blogpost_create_by_anonymous(self):
        """Test blogpost create, anonymous users are redirected to signin"""
        user = self.create_users()[1]
        app = self.create_app(info=None)
        app.owner = user
        db.session.add_all([user, app])
        db.session.commit()
        url = "/app/%s/new-blogpost" % app.short_name

        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert "Please sign in to access this page" in res.data, res

        res = self.app.post(url,
                            data={'title':'blogpost title', 'body':'body'},
                            follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert "Please sign in to access this page" in res.data

        blogpost = db.session.query(Blogpost).first()
        assert blogpost == None, blogpost


    @with_context
    def test_blogpost_create_by_non_owner(self):
        """Test blogpost create by non owner of the app is forbidden"""
        user = self.create_users()[1]
        app = self.create_app(info=None)
        app.owner = user
        db.session.add_all([user, app])
        db.session.commit()
        url = "/app/%s/new-blogpost" % app.short_name
        self.register()

        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 403, res.status_code

        res = self.app.post(url,
                            data={'title':'blogpost title', 'body':'body'},
                            follow_redirects=True)
        assert res.status_code == 403, res.status_code


    def test_blogpost_create_errors(self):
        """Test blogposts create for non existing apps raises errors"""
        self.register()
        url = "/app/non-existing-app/new-blogpost"

        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code

        res = self.app.post(url, data={'title':'blogpost title', 'body':'body'},
                            follow_redirects=True)
        assert res.status_code == 404, res.status_code


    @with_context
    @patch('pybossa.view.applications.redirect', wraps=redirect)
    def test_blogpost_update_by_owner(self, mock_redirect):
        """Test blogposts, app owners can update"""
        self.register()
        user = db.session.query(User).get(1)
        app = self.create_app(info=None)
        app.owner = user
        blogpost = Blogpost(owner=user, app=app, title='thisisatitle', body='body')
        db.session.add_all([app, blogpost])
        db.session.commit()
        url = "/app/%s/%s/update" % (app.short_name, blogpost.id)

        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code

        res = self.app.post(url,
                            data={'id': blogpost.id,
                                  'title':'blogpost title',
                                  'body':'new body'},
                            follow_redirects=True)
        assert res.status_code == 200, res.status_code
        mock_redirect.assert_called_with('/app/%s/blog' % app.short_name)

        blogpost = db.session.query(Blogpost).first()
        assert blogpost.title == 'blogpost title', blogpost.title
        assert blogpost.body == 'new body', blogpost.body



    @with_context
    def test_blogpost_update_by_anonymous(self):
        """Test blogpost update, anonymous users are redirected to signin"""
        user = self.create_users()[1]
        app = self.create_app(info=None)
        app.owner = user
        blogpost = Blogpost(owner=user, app=app, title='thisisatitle', body='body')
        db.session.add_all([user, app, blogpost])
        db.session.commit()
        url = "/app/%s/%s/update" % (app.short_name, blogpost.id)

        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert "Please sign in to access this page" in res.data, res.data

        res = self.app.post(url,
                            data={'id':blogpost.id,
                                  'title':'new title',
                                  'body':'new body'},
                            follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert "Please sign in to access this page" in res.data

        blogpost = db.session.query(Blogpost).first()
        assert blogpost.title == 'thisisatitle', blogpost.title


    @with_context
    def test_blogpost_update_by_non_owner(self):
        """Test blogpost update by non owner of the app is forbidden"""
        user = self.create_users()[1]
        app = self.create_app(info=None)
        app.owner = user
        blogpost = Blogpost(owner=user, app=app, title='thisisatitle', body='body')
        db.session.add_all([user, app, blogpost])
        db.session.commit()
        url = "/app/%s/%s/update" % (app.short_name, blogpost.id)
        self.register()

        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 403, res.status_code

        res = self.app.post(url,
                            data={'title':'new title', 'body':'body'},
                            follow_redirects=True)
        assert res.status_code == 403, res.status_code

        blogpost = db.session.query(Blogpost).first()
        assert blogpost.title == 'thisisatitle', blogpost.title


    @with_context
    def test_blogpost_update_errors(self):
        """Test blogposts update for non existing apps raises errors"""
        self.register()
        user = db.session.query(User).get(1)
        app1 = App(name='app1',
                short_name='app1',
                description=u'description')
        app2 = self.create_app(info=None)
        app1.owner = user
        app2.owner = user
        blogpost = Blogpost(owner=user, app=app1, title='thisisatitle', body='body')
        db.session.add_all([app1, app2, blogpost])
        db.session.commit()

        # To a non-existing app
        url = "/app/non-existing-app/%s/update" % blogpost.id
        res = self.app.post(url, data={'title':'new title', 'body':'body'},
                            follow_redirects=True)
        assert res.status_code == 404, res.status_code

        # To a non-existing post
        url = "/app/%s/999999/update" % app1.short_name
        res = self.app.post(url, data={'title':'new title', 'body':'body'},
                            follow_redirects=True)
        assert res.status_code == 404, res.status_code

        # To an existing post but with an app in the URL it does not belong to
        url = "/app/%s/%s/update" % (app2.short_name, blogpost.id)
        res = self.app.post(url, data={'title':'new title', 'body':'body'},
                            follow_redirects=True)
        assert res.status_code == 404, res.status_code


    @with_context
    @patch('pybossa.view.applications.redirect', wraps=redirect)
    def test_blogpost_delete_by_owner(self, mock_redirect):
        """Test blogposts, app owners can delete"""
        self.register()
        user = db.session.query(User).get(1)
        app = self.create_app(info=None)
        app.owner = user
        blogpost = Blogpost(owner=user, app=app, title='thisisatitle', body='body')
        db.session.add_all([app, blogpost])
        db.session.commit()
        url = "/app/%s/%s/delete" % (app.short_name, blogpost.id)
        redirect_url = '/app/%s/blog' % app.short_name

        res = self.app.post(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        mock_redirect.assert_called_with(redirect_url)

        blogpost = db.session.query(Blogpost).first()
        assert blogpost is None, blogpost



    @with_context
    def test_blogpost_delete_by_anonymous(self):
        """Test blogpost delete, anonymous users are redirected to signin"""
        user = self.create_users()[1]
        app = self.create_app(info=None)
        app.owner = user
        blogpost = Blogpost(owner=user, app=app, title='thisisatitle', body='body')
        db.session.add_all([user, app, blogpost])
        db.session.commit()
        url = "/app/%s/%s/delete" % (app.short_name, blogpost.id)

        res = self.app.post(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert "Please sign in to access this page" in res.data

        blogpost = db.session.query(Blogpost).first()
        assert blogpost is not None


    @with_context
    def test_blogpost_delete_by_non_owner(self):
        """Test blogpost delete by non owner of the app is forbidden"""
        user = self.create_users()[1]
        app = self.create_app(info=None)
        app.owner = user
        blogpost = Blogpost(owner=user, app=app, title='thisisatitle', body='body')
        db.session.add_all([user, app, blogpost])
        db.session.commit()
        url = "/app/%s/%s/delete" % (app.short_name, blogpost.id)
        self.register()

        res = self.app.post(url, follow_redirects=True)
        assert res.status_code == 403, res.status_code

        blogpost = db.session.query(Blogpost).first()
        assert blogpost is not None


    @with_context
    def test_blogpost_delete_errors(self):
        """Test blogposts delete for non existing apps raises errors"""
        self.register()
        user = db.session.query(User).get(1)
        app1 = App(name='app1',
                short_name='app1',
                description=u'description')
        app2 = self.create_app(info=None)
        app1.owner = user
        app2.owner = user
        blogpost = Blogpost(owner=user, app=app1, title='thisisatitle', body='body')
        db.session.add_all([app1, app2, blogpost])
        db.session.commit()

        # To a non-existing app
        url = "/app/non-existing-app/%s/delete" % blogpost.id
        res = self.app.post(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code

        # To a non-existing post
        url = "/app/%s/999999/delete" % app1.short_name
        res = self.app.post(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code

        # To an existing post but with an app in the URL it does not belong to
        url = "/app/%s/%s/delete" % (app2.short_name, blogpost.id)
        res = self.app.post(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code




########NEW FILE########
__FILENAME__ = test_vmcp
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import pybossa.vmcp as vmcp
from mock import patch
import hashlib
import M2Crypto
import base64


class TestAPI:

    def test_myquote(self):
        """Test myquote works."""
        # Valid char should be the same
        err_msg = "Valid chars should not be quoted"
        assert vmcp.myquote('a') == 'a', err_msg
        # Non-valid
        err_msg = "Non-Valid chars should be quoted"
        assert vmcp.myquote('%') == '%25', err_msg

    def test_calculate_buffer(self):
        """Test calculate_buffer works"""
        data = {"flags": 8,
                "name": "MyAwesomeVM",
                "ram": 512,
                "secret": "mg041na39123",
                "userData": "[amiconfig]\nplugins=cernvm\n[cernvm]\nusers=user:users;password",
                "vcpus": 1,
                "true": True,
                "false": False,
                "version": "1.5"}

        out = vmcp.calculate_buffer(data, 'salt')
        err_msg = "Salt should be appended to the string"
        assert 'salt' in out, err_msg
        err_msg = "Boolean True has to be converted to 1"
        assert "true=1" in out, err_msg
        err_msg = "Boolean False has to be converted to 0"
        assert "false=0" in out, err_msg

    def _sign(self, data, salt):
        """Help function to prepare the data for signing."""
        strBuffer = ""
        # print data.keys()
        for k in sorted(data.iterkeys()):

            # Handle the BOOL special case
            v = data[k]
            if type(v) == bool:
                if v:
                    v = 1
                else:
                    v = 0
                data[k] = v

            # Update buffer
            strBuffer += "%s=%s\n" % (str(k).lower(), vmcp.myquote(str(v)))

        # Append salt
        strBuffer += salt
        return strBuffer

    def test_sign(self):
        """Test sign works."""
        rsa = M2Crypto.RSA.gen_key(2048, 65537)
        salt = 'salt'
        data = {"flags": 8,
                "name": "MyAwesomeVM",
                "ram": 512,
                "secret": "mg041na39123",
                "userData": "[amiconfig]\nplugins=cernvm\n[cernvm]\nusers=user:users;password",
                "vcpus": 1,
                "version": "1.5"}
        strBuffer = self._sign(data, salt)
        digest = hashlib.new('sha512', strBuffer).digest()

        with patch('M2Crypto.RSA.load_key', return_value=rsa):
            out = vmcp.sign(data, salt, 'key')
            err_msg = "There should be a key named signature"
            assert out.get('signature'), err_msg

            err_msg = "The signature should not be empty"
            assert out['signature'] is not None, err_msg
            assert out['signature'] != '', err_msg

            err_msg = "The signature should be the same"
            assert strBuffer == out['strBuffer']
            assert digest == out['digest']
            signature = base64.b64decode(out['signature'])
            assert rsa.verify(digest, signature, 'sha512') == 1, err_msg

########NEW FILE########
__FILENAME__ = test_web
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

import json
import StringIO

from default import db, Fixtures, with_context
from helper import web
from mock import patch, Mock
from flask import Response
from itsdangerous import BadSignature
from collections import namedtuple
from pybossa.core import signer, mail
from pybossa.util import unicode_csv_reader
from pybossa.util import get_user_signup_method
from pybossa.ckan import Ckan
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError
from werkzeug.exceptions import NotFound
from pybossa.model.app import App
from pybossa.model.category import Category
from pybossa.model.task import Task
from pybossa.model.task_run import TaskRun
from pybossa.model.user import User
from pybossa.model.featured import Featured
from factories import AppFactory, TaskFactory, TaskRunFactory


FakeRequest = namedtuple('FakeRequest', ['text', 'status_code', 'headers'])


class TestWeb(web.Helper):
    pkg_json_not_found = {
        "help": "Return ...",
        "success": False,
        "error": {
            "message": "Not found",
            "__type": "Not Found Error"}}

    @with_context
    def test_01_index(self):
        """Test WEB home page works"""
        res = self.app.get("/", follow_redirects=True)
        assert self.html_title() in res.data, res
        assert "Create an App" in res.data, res

    @with_context
    def test_01_search(self):
        """Test WEB search page works."""
        res = self.app.get('/search')
        err_msg = "Search page should be accessible"
        assert "Search" in res.data, err_msg

    @with_context
    @patch('pybossa.stats.pygeoip', autospec=True)
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_02_stats(self, mock1, mock2):
        """Test WEB leaderboard or stats page works"""
        with self.flask_app.app_context():
            res = self.register()
            res = self.signin()
            res = self.new_application(short_name="igil")
            returns = [Mock()]
            returns[0].GeoIP.return_value = 'gic'
            returns[0].GeoIP.record_by_addr.return_value = {}
            mock1.side_effects = returns

            app = db.session.query(App).first()
            # Without stats
            url = '/app/%s/stats' % app.short_name
            res = self.app.get(url)
            assert "Sorry" in res.data, res.data

            # We use a string here to check that it works too
            task = Task(app_id=app.id, n_answers=10)
            db.session.add(task)
            db.session.commit()

            for i in range(10):
                task_run = TaskRun(app_id=app.id, task_id=1,
                                         user_id=1,
                                         info={'answer': 1})
                db.session.add(task_run)
                db.session.commit()
                self.app.get('api/app/%s/newtask' % app.id)

            # With stats
            url = '/app/%s/stats' % app.short_name
            res = self.app.get(url)
            assert res.status_code == 200, res.status_code
            assert "Distribution" in res.data, res.data

            with patch.dict(self.flask_app.config, {'GEO': True}):
                url = '/app/%s/stats' % app.short_name
                res = self.app.get(url)
                assert "GeoLite" in res.data, res.data

            res = self.app.get('/leaderboard', follow_redirects=True)
            assert self.html_title("Community Leaderboard") in res.data, res
            assert self.user.fullname in res.data, res.data

            # With hidden app
            app.hidden = 1
            db.session.add(app)
            db.session.commit()
            url = '/app/%s/stats' % app.short_name
            res = self.app.get(url)
            assert res.status_code == 200, res.status_code
            assert "Distribution" in res.data, res.data
            self.signout()

            self.create()
            # As anonymous
            url = '/app/%s/stats' % app.short_name
            res = self.app.get(url)
            assert res.status_code == 403, res.status_code
            # As another user, but not owner
            self.signin(email=Fixtures.email_addr2, password=Fixtures.password)
            url = '/app/%s/stats' % app.short_name
            res = self.app.get(url)
            assert res.status_code == 403, res.status_code

    @with_context
    def test_03_account_index(self):
        """Test WEB account index works."""
        # Without users
        with self.flask_app.app_context():
            res = self.app.get('/account/page/15', follow_redirects=True)
            assert res.status_code == 404, res.status_code

            self.create()
            res = self.app.get('/account', follow_redirects=True)
            assert res.status_code == 200, res.status_code
            err_msg = "There should be a Community page"
            assert "Community" in res.data, err_msg

    @with_context
    def test_03_register(self):
        """Test WEB register user works"""
        with self.flask_app.app_context():
            res = self.app.get('/account/signin')
            assert 'Forgot Password' in res.data

            res = self.register(method="GET")
            # The output should have a mime-type: text/html
            assert res.mimetype == 'text/html', res
            assert self.html_title("Register") in res.data, res

            res = self.register()
            assert self.html_title() in res.data, res
            assert "Thanks for signing-up" in res.data, res.data

            res = self.register()
            assert self.html_title("Register") in res.data, res
            assert "The user name is already taken" in res.data, res.data

            res = self.register(fullname='')
            assert self.html_title("Register") in res.data, res
            msg = "Full name must be between 3 and 35 characters long"
            assert msg in res.data, res.data

            res = self.register(name='')
            assert self.html_title("Register") in res.data, res
            msg = "User name must be between 3 and 35 characters long"
            assert msg in res.data, res.data

            res = self.register(name='%a/$|')
            assert self.html_title("Register") in res.data, res
            msg = '$#&amp;\/| and space symbols are forbidden'
            assert msg in res.data, res.data

            res = self.register(email='')
            assert self.html_title("Register") in res.data, res.data
            assert self.html_title("Register") in res.data, res.data
            msg = "Email must be between 3 and 35 characters long"
            assert msg in res.data, res.data

            res = self.register(email='invalidemailaddress')
            assert self.html_title("Register") in res.data, res.data
            assert "Invalid email address" in res.data, res.data

            res = self.register()
            assert self.html_title("Register") in res.data, res.data
            assert "Email is already taken" in res.data, res.data

            res = self.register(password='')
            assert self.html_title("Register") in res.data, res.data
            assert "Password cannot be empty" in res.data, res.data

            res = self.register(password2='different')
            assert self.html_title("Register") in res.data, res.data
            assert "Passwords must match" in res.data, res.data

    @with_context
    def test_04_signin_signout(self):
        """Test WEB sign in and sign out works"""
        res = self.register()
        # Log out as the registration already logs in the user
        res = self.signout()

        res = self.signin(method="GET")
        assert self.html_title("Sign in") in res.data, res.data
        assert "Sign in" in res.data, res.data

        res = self.signin(email='')
        assert "Please correct the errors" in res.data, res
        assert "The e-mail is required" in res.data, res

        res = self.signin(password='')
        assert "Please correct the errors" in res.data, res
        assert "You must provide a password" in res.data, res

        res = self.signin(email='', password='')
        assert "Please correct the errors" in res.data, res
        assert "The e-mail is required" in res.data, res
        assert "You must provide a password" in res.data, res

        # Non-existant user
        msg = "Ooops, we didn't find you in the system"
        res = self.signin(email='wrongemail')
        assert msg in res.data, res.data

        res = self.signin(email='wrongemail', password='wrongpassword')
        assert msg in res.data, res

        # Real user but wrong password or username
        msg = "Ooops, Incorrect email/password"
        res = self.signin(password='wrongpassword')
        assert msg in res.data, res

        res = self.signin()
        assert self.html_title() in res.data, res
        assert "Welcome back %s" % self.user.fullname in res.data, res

        # Check profile page with several information chunks
        res = self.profile()
        assert self.html_title("Profile") in res.data, res
        assert self.user.fullname in res.data, res
        assert self.user.email_addr in res.data, res

        # Log out
        res = self.signout()
        assert self.html_title() in res.data, res
        assert "You are now signed out" in res.data, res

        # Request profile as an anonymous user
        # Check profile page with several information chunks
        res = self.profile()
        assert self.user.fullname in res.data, res
        assert self.user.email_addr not in res.data, res

        # Try to access protected areas like update
        res = self.app.get('/account/johndoe/update', follow_redirects=True)
        # As a user must be signed in to access, the page the title will be the
        # redirection to log in
        assert self.html_title("Sign in") in res.data, res.data
        assert "Please sign in to access this page." in res.data, res.data

        res = self.signin(next='%2Faccount%2Fprofile')
        assert self.html_title("Profile") in res.data, res
        assert "Welcome back %s" % self.user.fullname in res.data, res

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_profile_applications(self, mock):
        """Test WEB user profile applications page works."""
        with self.flask_app.app_context():
            self.create()
            self.signin(email=Fixtures.email_addr, password=Fixtures.password)
            self.new_application()
            url = '/account/%s/applications' % Fixtures.name
            res = self.app.get(url)
            assert "Applications" in res.data, res.data
            assert "Published" in res.data, res.data
            assert "Draft" in res.data, res.data
            assert Fixtures.app_name in res.data, res.data

            url = '/account/fakename/applications'
            res = self.app.get(url)
            assert res.status_code == 404, res.status_code

            url = '/account/%s/applications' % Fixtures.name2
            res = self.app.get(url)
            assert res.status_code == 403, res.status_code


    @with_context
    def test_05_update_user_profile(self):
        """Test WEB update user profile"""


        # Create an account and log in
        self.register()
        url = "/account/fake/update"
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 404, res.status_code

        # Update profile with new data
        res = self.update_profile(method="GET")
        msg = "Update your profile: %s" % self.user.fullname
        assert self.html_title(msg) in res.data, res.data
        msg = 'input id="id" name="id" type="hidden" value="1"'
        assert msg in res.data, res
        assert self.user.fullname in res.data, res
        assert "Save the changes" in res.data, res
        msg = '<a href="/account/johndoe/update" class="btn">Cancel</a>'
        assert  msg in res.data, res.data

        res = self.update_profile(fullname="John Doe 2",
                                  email_addr="johndoe2@example",
                                  locale="en")
        assert "Please correct the errors" in res.data, res.data


        res = self.update_profile(fullname="John Doe 2",
                                  email_addr="johndoe2@example.com",
                                  locale="en")
        title = "Update your profile: John Doe 2"
        assert self.html_title(title) in res.data, res.data
        assert "Your profile has been updated!" in res.data, res.data
        assert "John Doe 2" in res.data, res
        assert "johndoe" in res.data, res
        assert "johndoe2@example.com" in res.data, res

        # Updating the username field forces the user to re-log in
        res = self.update_profile(fullname="John Doe 2",
                                  email_addr="johndoe2@example.com",
                                  locale="en",
                                  new_name="johndoe2")
        assert "Your profile has been updated!" in res.data, res
        assert "Please sign in" in res.data, res.data

        res = self.signin(method="POST", email="johndoe2@example.com",
                          password="p4ssw0rd",
                          next="%2Faccount%2Fprofile")
        assert "Welcome back John Doe 2" in res.data, res.data
        assert "John Doe 2" in res.data, res
        assert "johndoe2" in res.data, res
        assert "johndoe2@example.com" in res.data, res

        res = self.signout()
        assert self.html_title() in res.data, res
        assert "You are now signed out" in res.data, res

        # A user must be signed in to access the update page, the page
        # the title will be the redirection to log in
        res = self.update_profile(method="GET")
        assert self.html_title("Sign in") in res.data, res
        assert "Please sign in to access this page." in res.data, res

        # A user must be signed in to access the update page, the page
        # the title will be the redirection to log in
        res = self.update_profile()
        assert self.html_title("Sign in") in res.data, res
        assert "Please sign in to access this page." in res.data, res

        self.register(fullname="new", name="new")
        url = "/account/johndoe2/update"
        res = self.app.get(url)
        assert res.status_code == 403

    @with_context
    def test_05a_get_nonexistant_app(self):
        """Test WEB get not existant app should return 404"""
        res = self.app.get('/app/nonapp', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

    @with_context
    def test_05b_get_nonexistant_app_newtask(self):
        """Test WEB get non existant app newtask should return 404"""
        res = self.app.get('/app/noapp/presenter', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        res = self.app.get('/app/noapp/newtask', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

    @with_context
    def test_05c_get_nonexistant_app_tutorial(self):
        """Test WEB get non existant app tutorial should return 404"""
        res = self.app.get('/app/noapp/tutorial', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

    @with_context
    def test_05d_get_nonexistant_app_delete(self):
        """Test WEB get non existant app delete should return 404"""
        self.register()
        # GET
        res = self.app.get('/app/noapp/delete', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.data
        # POST
        res = self.delete_application(short_name="noapp")
        assert res.status == '404 NOT FOUND', res.status

    @with_context
    def test_05d_get_nonexistant_app_update(self):
        """Test WEB get non existant app update should return 404"""
        self.register()
        # GET
        res = self.app.get('/app/noapp/update', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # POST
        res = self.update_application(short_name="noapp")
        assert res.status == '404 NOT FOUND', res.status

    @with_context
    def test_05d_get_nonexistant_app_import(self):
        """Test WEB get non existant app import should return 404"""
        self.register()
        # GET
        res = self.app.get('/app/noapp/import', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # POST
        res = self.app.post('/app/noapp/import', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

    @with_context
    def test_05d_get_nonexistant_app_task(self):
        """Test WEB get non existant app task should return 404"""
        res = self.app.get('/app/noapp/task', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # Pagination
        res = self.app.get('/app/noapp/task/25', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

    @with_context
    def test_05d_get_nonexistant_app_results_json(self):
        """Test WEB get non existant app results json should return 404"""
        res = self.app.get('/app/noapp/24/results.json', follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

    @with_context
    def test_06_applications_without_apps(self):
        """Test WEB applications index without apps works"""
        # Check first without apps
        with self.flask_app.app_context():
            self.create_categories()
            res = self.app.get('/app', follow_redirects=True)
            assert "Applications" in res.data, res.data
            assert Fixtures.cat_1 in res.data, res.data

    @with_context
    def test_06_applications_2(self):
        """Test WEB applications index with apps"""
        with self.flask_app.app_context():
            self.create()

            res = self.app.get('/app', follow_redirects=True)
            assert self.html_title("Applications") in res.data, res.data
            assert "Applications" in res.data, res.data
            assert Fixtures.app_short_name in res.data, res.data


    @with_context
    def test_06_featured_apps(self):
        """Test WEB application index shows featured apps in all the pages works"""
        with self.flask_app.app_context():
            self.create()

            f = Featured()
            f.app_id = 1
            db.session.add(f)
            db.session.commit()

            res = self.app.get('/app', follow_redirects=True)
            assert self.html_title("Applications") in res.data, res.data
            assert "Applications" in res.data, res.data
            assert '/app/test-app' in res.data, res.data
            assert '<h2><a href="/app/test-app/">My New App</a></h2>' in res.data, res.data

            # Update one task to have more answers than expected
            task = db.session.query(Task).get(1)
            task.n_answers=1
            db.session.add(task)
            db.session.commit()
            task = db.session.query(Task).get(1)
            cat = db.session.query(Category).get(1)
            url = '/app/category/featured/'
            res = self.app.get(url, follow_redirects=True)
            tmp = '1 Featured Applications'
            assert tmp in res.data, res.data

    @with_context
    @patch('pybossa.ckan.requests.get')
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_10_get_application(self, Mock, mock2):
        """Test WEB application URL/<short_name> works"""
        # Sign in and create an application
        with self.flask_app.app_context():
            html_request = FakeRequest(json.dumps(self.pkg_json_not_found), 200,
                                       {'content-type': 'application/json'})
            Mock.return_value = html_request
            self.register()
            res = self.new_application()

            res = self.app.get('/app/sampleapp', follow_redirects=True)
            msg = "Application: Sample App"
            assert self.html_title(msg) in res.data, res
            err_msg = "There should be a contribute button"
            assert "Start Contributing Now" in res.data, err_msg

            res = self.app.get('/app/sampleapp/settings', follow_redirects=True)
            assert res.status == '200 OK', res.status
            self.signout()

            # Now as an anonymous user
            res = self.app.get('/app/sampleapp', follow_redirects=True)
            assert self.html_title("Application: Sample App") in res.data, res
            assert "Start Contributing Now" in res.data, err_msg
            res = self.app.get('/app/sampleapp/settings', follow_redirects=True)
            assert res.status == '200 OK', res.status
            err_msg = "Anonymous user should be redirected to sign in page"
            assert "Please sign in to access this page" in res.data, err_msg

            # Now with a different user
            self.register(fullname="Perico Palotes", name="perico")
            res = self.app.get('/app/sampleapp', follow_redirects=True)
            assert self.html_title("Application: Sample App") in res.data, res
            assert "Start Contributing Now" in res.data, err_msg
            res = self.app.get('/app/sampleapp/settings')
            assert res.status == '403 FORBIDDEN', res.status

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_10b_application_long_description_allows_markdown(self, mock):
        """Test WEB long description markdown is supported"""
        with self.flask_app.app_context():
            markdown_description = u'Markdown\n======='
            self.register()
            self.new_application(long_description=markdown_description)

            res = self.app.get('/app/sampleapp', follow_redirects=True)
            data = res.data
            assert '<h1>Markdown</h1>' in data, 'Markdown text not being rendered!'

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_11_create_application(self, mock):
        """Test WEB create an application works"""
        # Create an app as an anonymous user
        with self.flask_app.app_context():
            res = self.new_application(method="GET")
            assert self.html_title("Sign in") in res.data, res
            assert "Please sign in to access this page" in res.data, res

            res = self.new_application()
            assert self.html_title("Sign in") in res.data, res.data
            assert "Please sign in to access this page." in res.data, res.data

            # Sign in and create an application
            res = self.register()

            res = self.new_application(method="GET")
            assert self.html_title("Create an Application") in res.data, res
            assert "Create the application" in res.data, res

            res = self.new_application(long_description='My Description')
            assert "<strong>Sample App</strong>: Update the application" in res.data
            assert "Application created!" in res.data, res

            app = db.session.query(App).first()
            assert app.name == 'Sample App', 'Different names %s' % app.name
            assert app.short_name == 'sampleapp', \
                'Different names %s' % app.short_name

            assert app.long_description == 'My Description', \
                "Long desc should be the same: %s" % app.long_description

    # After refactoring applications view, these 3 tests should be more isolated and moved to another place
    @with_context
    def test_description_is_generated_from_long_desc(self):
        """Test WEB when creating an application, the description field is
        automatically filled in by truncating the long_description"""
        self.register()
        res = self.new_application(long_description="Hello")

        app = db.session.query(App).first()
        assert app.description == "Hello", app.description

    @with_context
    def test_description_is_generated_from_long_desc_formats(self):
        """Test WEB when when creating an application, the description generated
        from the long_description is only text (no html, no markdown)"""
        self.register()
        res = self.new_application(long_description="## Hello")

        app = db.session.query(App).first()
        assert '##' not in app.description, app.description
        assert '<h2>' not in app.description, app.description

    @with_context
    def test_description_is_generated_from_long_desc_truncates(self):
        """Test WEB when when creating an application, the description generated
        from the long_description is only text (no html, no markdown)"""
        self.register()
        res = self.new_application(long_description="a"*300)

        app = db.session.query(App).first()
        assert len(app.description) == 255, len(app.description)
        assert app.description[-3:] == '...'

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_11_a_create_application_errors(self, mock):
        """Test WEB create an application issues the errors"""
        with self.flask_app.app_context():
            self.register()
            # Required fields checks
            # Issue the error for the app.name
            res = self.new_application(name="")
            err_msg = "An application must have a name"
            assert "This field is required" in res.data, err_msg

            # Issue the error for the app.short_name
            res = self.new_application(short_name="")
            err_msg = "An application must have a short_name"
            assert "This field is required" in res.data, err_msg

            # Issue the error for the app.description
            res = self.new_application(long_description="")
            err_msg = "An application must have a description"
            assert "This field is required" in res.data, err_msg

            # Issue the error for the app.short_name
            res = self.new_application(short_name='$#/|')
            err_msg = "An application must have a short_name without |/$# chars"
            assert '$#&amp;\/| and space symbols are forbidden' in res.data, err_msg

            # Now Unique checks
            self.new_application()
            res = self.new_application()
            err_msg = "There should be a Unique field"
            assert "Name is already taken" in res.data, err_msg
            assert "Short Name is already taken" in res.data, err_msg

    @with_context
    @patch('pybossa.ckan.requests.get')
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_12_update_application(self, Mock, mock):
        """Test WEB update application works"""
        with self.flask_app.app_context():
            html_request = FakeRequest(json.dumps(self.pkg_json_not_found), 200,
                                       {'content-type': 'application/json'})
            Mock.return_value = html_request

            self.register()
            self.new_application()

            # Get the Update App web page
            res = self.update_application(method="GET")
            msg = "Application: Sample App &middot; Update"
            assert self.html_title(msg) in res.data, res
            msg = 'input id="id" name="id" type="hidden" value="1"'
            assert msg in res.data, res
            assert "Save the changes" in res.data, res

            # Check form validation
            res = self.update_application(new_name="",
                                          new_short_name="",
                                          new_description="New description",
                                          new_long_description='New long desc',
                                          new_hidden=True)
            assert "Please correct the errors" in res.data, res.data

            # Update the application
            res = self.update_application(new_name="New Sample App",
                                          new_short_name="newshortname",
                                          new_description="New description",
                                          new_long_description='New long desc',
                                          new_hidden=True)
            app = db.session.query(App).first()
            assert "Application updated!" in res.data, res
            err_msg = "App name not updated %s" % app.name
            assert app.name == "New Sample App", err_msg
            err_msg = "App short name not updated %s" % app.short_name
            assert app.short_name == "newshortname", err_msg
            err_msg = "App description not updated %s" % app.description
            assert app.description == "New description", err_msg
            err_msg = "App long description not updated %s" % app.long_description
            assert app.long_description == "New long desc", err_msg
            err_msg = "App hidden not updated %s" % app.hidden
            assert app.hidden == 1, err_msg


            # Check that the owner can access it even though is hidden

            user = db.session.query(User).filter_by(name='johndoe').first()
            user.admin = False
            db.session.add(user)
            db.session.commit()
            res = self.app.get('/app/newshortname/')
            err_msg = "Owner should be able to see his hidden app"
            assert app.name in res.data, err_msg
            self.signout()

            res = self.register(fullname='Paco', name='paco')
            url = '/app/newshortname/'
            res = self.app.get(url, follow_redirects=True)
            assert "Forbidden" in res.data, res.data
            assert res.status_code == 403

            tmp = db.session.query(App).first()
            tmp.hidden = 0
            db.session.add(tmp)
            db.session.commit()

            url = '/app/newshortname/update'
            res = self.app.get(url, follow_redirects=True)
            assert res.status_code == 403, res.status_code

            tmp.hidden = 1
            db.session.add(tmp)
            db.session.commit()


            user = db.session.query(User).filter_by(name='paco').first()
            user.admin = True
            db.session.add(user)
            db.session.commit()
            res = self.app.get('/app/newshortname/')
            err_msg = "Root user should be able to see his hidden app"
            assert app.name in res.data, err_msg


    @with_context
    def test_update_application_errors(self):
        """Test WEB update form validation issues the errors"""
        with self.flask_app.app_context():

            self.register()
            self.new_application()

            res = self.update_application(new_name="")
            assert "This field is required" in res.data

            res = self.update_application(new_short_name="")
            assert "This field is required" in res.data

            res = self.update_application(new_description="")
            assert "You must provide a description." in res.data

            res = self.update_application(new_description="a"*256)
            assert "Field cannot be longer than 255 characters." in res.data

            res = self.update_application(new_long_description="")
            assert "This field is required" not in res.data


    @with_context
    @patch('pybossa.ckan.requests.get')
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_13_hidden_applications(self, Mock, mock):
        """Test WEB hidden application works"""
        with self.flask_app.app_context():
            html_request = FakeRequest(json.dumps(self.pkg_json_not_found), 200,
                                       {'content-type': 'application/json'})
            Mock.return_value = html_request
            self.register()
            self.new_application()
            self.update_application(new_hidden=True)
            self.signout()

            res = self.app.get('/app/', follow_redirects=True)
            assert "Sample App" not in res.data, res

            res = self.app.get('/app/sampleapp', follow_redirects=True)
            err_msg = "Hidden apps should return a 403"
            res.status_code == 403, err_msg

    @with_context
    @patch('pybossa.ckan.requests.get')
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_13a_hidden_applications_owner(self, Mock, mock):
        """Test WEB hidden applications are shown to their owners"""
        with self.flask_app.app_context():
            html_request = FakeRequest(json.dumps(self.pkg_json_not_found), 200,
                                       {'content-type': 'application/json'})
            Mock.return_value = html_request

            self.register()
            self.new_application()
            self.update_application(new_hidden=True)

            res = self.app.get('/app/', follow_redirects=True)
            assert "Sample App" not in res.data, ("Applications should be hidden"
                                                  "in the index")

            res = self.app.get('/app/sampleapp', follow_redirects=True)
            assert "Sample App" in res.data, ("Application should be shown to"
                                              "the owner")

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_14_delete_application(self, mock):
        """Test WEB delete application works"""
        with self.flask_app.app_context():
            self.create()
            self.register()
            self.new_application()
            res = self.delete_application(method="GET")
            msg = "Application: Sample App &middot; Delete"
            assert self.html_title(msg) in res.data, res
            assert "No, do not delete it" in res.data, res

            app = db.session.query(App).filter_by(short_name='sampleapp').first()
            app.hidden = 1
            db.session.add(app)
            db.session.commit()
            res = self.delete_application(method="GET")
            msg = "Application: Sample App &middot; Delete"
            assert self.html_title(msg) in res.data, res
            assert "No, do not delete it" in res.data, res

            res = self.delete_application()
            assert "Application deleted!" in res.data, res

            self.signin(email=Fixtures.email_addr2, password=Fixtures.password)
            res = self.delete_application(short_name=Fixtures.app_short_name)
            assert res.status_code == 403, res.status_code


    @with_context
    def test_15_twitter_email_warning(self):
        """Test WEB Twitter email warning works"""
        # This test assumes that the user allows Twitter to authenticate,
        #  returning a valid resp. The only difference is a user object
        #  without a password
        #  Register a user and sign out
        with self.flask_app.app_context():
            user = User(name="tester", passwd_hash="tester",
                              fullname="tester",
                              email_addr="tester")
            user.set_password('tester')
            db.session.add(user)
            db.session.commit()
            db.session.query(User).all()

            # Sign in again and check the warning message
            self.signin(email="tester", password="tester")
            res = self.app.get('/', follow_redirects=True)
            msg = "Please update your e-mail address in your profile page, " \
                  "right now it is empty!"
            user = db.session.query(User).get(1)
            assert msg in res.data, res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_16_task_status_completed(self, mock):
        """Test WEB Task Status Completed works"""
        with self.flask_app.app_context():
            self.register()
            self.new_application()

            app = db.session.query(App).first()
            # We use a string here to check that it works too
            task = Task(app_id=app.id, info={'n_answers': '10'})
            db.session.add(task)
            db.session.commit()

            res = self.app.get('app/%s/tasks/browse' % (app.short_name),
                               follow_redirects=True)
            dom = BeautifulSoup(res.data)
            assert "Sample App" in res.data, res.data
            assert '0 of 10' in res.data, res.data
            err_msg = "Download button should be disabled"
            assert dom.find(id='nothingtodownload') is not None, err_msg

            for i in range(5):
                task_run = TaskRun(app_id=app.id, task_id=1,
                                         info={'answer': 1})
                db.session.add(task_run)
                db.session.commit()
                self.app.get('api/app/%s/newtask' % app.id)

            res = self.app.get('app/%s/tasks/browse' % (app.short_name),
                               follow_redirects=True)
            dom = BeautifulSoup(res.data)
            assert "Sample App" in res.data, res.data
            assert '5 of 10' in res.data, res.data
            err_msg = "Download Partial results button should be shown"
            assert dom.find(id='partialdownload') is not None, err_msg

            for i in range(5):
                task_run = TaskRun(app_id=app.id, task_id=1,
                                         info={'answer': 1})
                db.session.add(task_run)
                db.session.commit()
                self.app.get('api/app/%s/newtask' % app.id)

            self.signout()

            app = db.session.query(App).first()

            res = self.app.get('app/%s/tasks/browse' % (app.short_name),
                               follow_redirects=True)
            assert "Sample App" in res.data, res.data
            msg = 'Task <span class="label label-success">#1</span>'
            assert msg in res.data, res.data
            assert '10 of 10' in res.data, res.data
            dom = BeautifulSoup(res.data)
            err_msg = "Download Full results button should be shown"
            assert dom.find(id='fulldownload') is not None, err_msg

            app.hidden = 1
            db.session.add(app)
            db.session.commit()
            res = self.app.get('app/%s/tasks/browse' % (app.short_name),
                               follow_redirects=True)
            assert res.status_code == 403, res.status_code

            self.create()
            self.signin(email=Fixtures.email_addr2, password=Fixtures.password)
            res = self.app.get('app/%s/tasks/browse' % (app.short_name),
                               follow_redirects=True)
            assert res.status_code == 403, res.status_code


    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_17_export_task_runs(self, mock):
        """Test WEB TaskRun export works"""
        with self.flask_app.app_context():
            self.register()
            self.new_application()

            app = db.session.query(App).first()
            task = Task(app_id=app.id, info={'n_answers': 10})
            db.session.add(task)
            db.session.commit()

            for i in range(10):
                task_run = TaskRun(app_id=app.id, task_id=1,
                                         info={'answer': 1})
                db.session.add(task_run)
                db.session.commit()


            app = db.session.query(App).first()
            res = self.app.get('app/%s/%s/results.json' % (app.short_name, 1),
                               follow_redirects=True)
            data = json.loads(res.data)
            assert len(data) == 10, data
            for tr in data:
                assert tr['info']['answer'] == 1, tr

            # Check with correct app but wrong task id
            res = self.app.get('app/%s/%s/results.json' % (app.short_name, 5000),
                               follow_redirects=True)
            assert res.status_code == 404, res.status_code

            # Check with hidden app: owner should have access to it
            app.hidden = 1
            db.session.add(app)
            db.session.commit()
            res = self.app.get('app/%s/%s/results.json' % (app.short_name, 1),
                               follow_redirects=True)
            data = json.loads(res.data)
            assert len(data) == 10, data
            for tr in data:
                assert tr['info']['answer'] == 1, tr
            self.signout()

            # Check with hidden app: anonymous should not have access to it
            res = self.app.get('app/%s/%s/results.json' % (app.short_name, 1),
                               follow_redirects=True)
            assert res.status_code == 403, res.data
            assert "Forbidden" in res.data, res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_18_task_status_wip(self, mock):
        """Test WEB Task Status on going works"""
        with self.flask_app.app_context():
            self.register()
            self.new_application()

            app = db.session.query(App).first()
            task = Task(app_id=app.id, info={'n_answers': 10})
            db.session.add(task)
            db.session.commit()
            self.signout()

            app = db.session.query(App).first()

            res = self.app.get('app/%s/tasks/browse' % (app.short_name),
                               follow_redirects=True)
            assert "Sample App" in res.data, res.data
            msg = 'Task <span class="label label-info">#1</span>'
            assert msg in res.data, res.data
            assert '0 of 10' in res.data, res.data

            # For a non existing page
            res = self.app.get('app/%s/tasks/browse/5000' % (app.short_name),
                               follow_redirects=True)
            assert res.status_code == 404, res.status_code


    @with_context
    def test_19_app_index_categories(self):
        """Test WEB Application Index categories works"""
        with self.flask_app.app_context():
            self.register()
            self.create()
            self.signout()

            res = self.app.get('app', follow_redirects=True)
            assert "Applications" in res.data, res.data
            assert Fixtures.cat_1 in res.data, res.data

            task = db.session.query(Task).get(1)
            # Update one task to have more answers than expected
            task.n_answers=1
            db.session.add(task)
            db.session.commit()
            task = db.session.query(Task).get(1)
            cat = db.session.query(Category).get(1)
            url = '/app/category/%s/' % Fixtures.cat_1
            res = self.app.get(url, follow_redirects=True)
            tmp = '1 %s Applications' % Fixtures.cat_1
            assert tmp in res.data, res

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_20_app_index_published(self, mock):
        """Test WEB Application Index published works"""
        with self.flask_app.app_context():
            self.register()
            self.new_application()
            self.update_application(new_category_id="1")
            app = db.session.query(App).first()
            info = dict(task_presenter="some html")
            app.info = info
            db.session.commit()
            task = Task(app_id=app.id, info={'n_answers': 10})
            db.session.add(task)
            db.session.commit()
            self.signout()

            res = self.app.get('app', follow_redirects=True)
            assert "Applications" in res.data, res.data
            assert Fixtures.cat_1 in res.data, res.data
            assert "draft" not in res.data, res.data
            assert "Sample App" in res.data, res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_20_app_index_draft(self, mock):
        """Test WEB Application Index draft works"""
        # Create root
        with self.flask_app.app_context():
            self.register()
            self.new_application()
            self.signout()
            # Create a user
            self.register(fullname="jane", name="jane", email="jane@jane.com")
            self.signout()

            # As Anonymous
            res = self.app.get('/app/draft', follow_redirects=True)
            dom = BeautifulSoup(res.data)
            err_msg = "Anonymous should not see draft apps"
            assert dom.find(id='signin') is not None, err_msg

            # As authenticated but not admin
            self.signin(email="jane@jane.com", password="p4ssw0rd")
            res = self.app.get('/app/draft', follow_redirects=True)
            assert res.status_code == 403, "Non-admin should not see draft apps"
            self.signout()

            # As Admin
            self.signin()
            res = self.app.get('/app/draft', follow_redirects=True)
            assert "Applications" in res.data, res.data
            assert "app-published" not in res.data, res.data
            assert "draft" in res.data, res.data
            assert "Sample App" in res.data, res.data

    @with_context
    def test_21_get_specific_ongoing_task_anonymous(self):
        """Test WEB get specific ongoing task_id for
        an app works as anonymous"""

        with self.flask_app.app_context():
            self.create()
            self.delete_task_runs()
            app = db.session.query(App).first()
            task = db.session.query(Task)\
                     .filter(App.id == app.id)\
                     .first()
            res = self.app.get('app/%s/task/%s' % (app.short_name, task.id),
                               follow_redirects=True)
            assert 'TaskPresenter' in res.data, res.data
            msg = "?next=%2Fapp%2F" + app.short_name + "%2Ftask%2F" + str(task.id)
            assert msg in res.data, res.data

            # Try with a hidden app
            app.hidden = 1
            db.session.add(app)
            db.session.commit()
            res = self.app.get('app/%s/task/%s' % (app.short_name, task.id),
                               follow_redirects=True)
            assert 'Forbidden' in res.data, res.data
            assert res.status_code == 403, "It should be forbidden"
            # Try with only registered users
            app.allow_anonymous_contributors = False
            app.hidden = 0
            db.session.add(app)
            db.session.commit()
            res = self.app.get('app/%s/task/%s' % (app.short_name, task.id),
                               follow_redirects=True)
            assert "sign in to participate" in res.data

    @with_context
    def test_22_get_specific_completed_task_anonymous(self):
        """Test WEB get specific completed task_id
        for an app works as anonymous"""

        #model.rebuild_db()
        with self.flask_app.app_context():
            self.create()
            app = db.session.query(App).first()
            task = db.session.query(Task)\
                     .filter(App.id == app.id)\
                     .first()

            for i in range(10):
                task_run = TaskRun(app_id=app.id, task_id=task.id,
                                         user_ip="127.0.0.1", info={'answer': 1})
                db.session.add(task_run)
                db.session.commit()

            ntask = Task(id=task.id, state='completed')

            assert ntask not in db.session
            db.session.merge(ntask)
            db.session.commit()

            res = self.app.get('app/%s/task/%s' % (app.short_name, task.id),
                               follow_redirects=True)
            msg = 'You have already participated in this task'
            assert msg in res.data, res.data
            assert 'Try with another one' in res.data, res.data

    @with_context
    def test_23_get_specific_ongoing_task_user(self):
        """Test WEB get specific ongoing task_id for an app works as an user"""

        with self.flask_app.app_context():
            self.create()
            self.delete_task_runs()
            self.register()
            self.signin()
            app = db.session.query(App).first()
            task = db.session.query(Task)\
                     .filter(App.id == app.id)\
                     .first()
            res = self.app.get('app/%s/task/%s' % (app.short_name, task.id),
                               follow_redirects=True)
            assert 'TaskPresenter' in res.data, res.data
            self.signout()

    @with_context
    def test_24_get_specific_completed_task_user(self):
        """Test WEB get specific completed task_id
        for an app works as an user"""

        #model.rebuild_db()
        with self.flask_app.app_context():
            self.create()
            self.register()

            user = db.session.query(User)\
                     .filter(User.name == self.user.username)\
                     .first()
            app = db.session.query(App).first()
            task = db.session.query(Task)\
                     .filter(App.id == app.id)\
                     .first()
            for i in range(10):
                task_run = TaskRun(app_id=app.id, task_id=task.id, user_id=user.id,
                                         info={'answer': 1})
                db.session.add(task_run)
                db.session.commit()
                #self.app.get('api/app/%s/newtask' % app.id)

            ntask = Task(id=task.id, state='completed')
            #self.signin()
            assert ntask not in db.session
            db.session.merge(ntask)
            db.session.commit()

            res = self.app.get('app/%s/task/%s' % (app.short_name, task.id),
                               follow_redirects=True)
            msg = 'You have already participated in this task'
            assert msg in res.data, res.data
            assert 'Try with another one' in res.data, res.data
            self.signout()

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_25_get_wrong_task_app(self, mock):
        """Test WEB get wrong task.id for an app works"""

        with self.flask_app.app_context():
            self.create()
            app1 = db.session.query(App).get(1)
            app1_short_name = app1.short_name

            db.session.query(Task)\
                      .filter(Task.app_id == 1)\
                      .first()

            self.register()
            self.new_application()
            app2 = db.session.query(App).get(2)
            self.new_task(app2.id)
            task2 = db.session.query(Task)\
                      .filter(Task.app_id == 2)\
                      .first()
            task2_id = task2.id
            self.signout()

            res = self.app.get('/app/%s/task/%s' % (app1_short_name, task2_id))
            assert "Error" in res.data, res.data
            msg = "This task does not belong to %s" % app1_short_name
            assert msg in res.data, res.data

    @with_context
    def test_26_tutorial_signed_user(self):
        """Test WEB tutorials work as signed in user"""
        with self.flask_app.app_context():
            self.create()
            app1 = db.session.query(App).get(1)
            app1.info = dict(tutorial="some help")
            db.session.commit()
            self.register()
            # First time accessing the app should redirect me to the tutorial
            res = self.app.get('/app/test-app/newtask', follow_redirects=True)
            err_msg = "There should be some tutorial for the application"
            assert "some help" in res.data, err_msg
            # Second time should give me a task, and not the tutorial
            res = self.app.get('/app/test-app/newtask', follow_redirects=True)
            assert "some help" not in res.data

            # Check if the tutorial can be accessed directly
            res = self.app.get('/app/test-app/tutorial', follow_redirects=True)
            err_msg = "There should be some tutorial for the application"
            assert "some help" in res.data, err_msg

            # Hidden app
            app1.hidden = 1
            db.session.add(app1)
            db.session.commit()
            url = '/app/%s/tutorial' % app1.short_name
            res = self.app.get(url, follow_redirects=True)
            assert res.status_code == 403, res.status_code


    @with_context
    def test_27_tutorial_anonymous_user(self):
        """Test WEB tutorials work as an anonymous user"""
        with self.flask_app.app_context():
            self.create()
            app1 = db.session.query(App).get(1)
            app1.info = dict(tutorial="some help")
            db.session.commit()
            # First time accessing the app should redirect me to the tutorial
            res = self.app.get('/app/test-app/newtask', follow_redirects=True)
            err_msg = "There should be some tutorial for the application"
            assert "some help" in res.data, err_msg
            # Second time should give me a task, and not the tutorial
            res = self.app.get('/app/test-app/newtask', follow_redirects=True)
            assert "some help" not in res.data

            # Check if the tutorial can be accessed directly
            res = self.app.get('/app/test-app/tutorial', follow_redirects=True)
            err_msg = "There should be some tutorial for the application"
            assert "some help" in res.data, err_msg

            # Hidden app
            app1.hidden = 1
            db.session.add(app1)
            db.session.commit()
            res = self.app.get('/app/test-app/tutorial', follow_redirects=True)
            assert res.status_code == 403, res.status_code

    @with_context
    def test_28_non_tutorial_signed_user(self):
        """Test WEB app without tutorial work as signed in user"""
        with self.flask_app.app_context():
            self.create()
            db.session.commit()
            self.register()
            # First time accessing the app should redirect me to the tutorial
            res = self.app.get('/app/test-app/newtask', follow_redirects=True)
            err_msg = "There should not be a tutorial for the application"
            assert "some help" not in res.data, err_msg
            # Second time should give me a task, and not the tutorial
            res = self.app.get('/app/test-app/newtask', follow_redirects=True)
            assert "some help" not in res.data

    @with_context
    def test_29_tutorial_anonymous_user(self):
        """Test WEB app without tutorials work as an anonymous user"""
        with self.flask_app.app_context():
            self.create()
            db.session.commit()
            self.register()
            # First time accessing the app should redirect me to the tutorial
            res = self.app.get('/app/test-app/newtask', follow_redirects=True)
            err_msg = "There should not be a tutorial for the application"
            assert "some help" not in res.data, err_msg
            # Second time should give me a task, and not the tutorial
            res = self.app.get('/app/test-app/newtask', follow_redirects=True)
            assert "some help" not in res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_30_app_id_owner(self, mock):
        """Test WEB application settings page shows the ID to the owner"""
        self.register()
        self.new_application()

        res = self.app.get('/app/sampleapp/settings', follow_redirects=True)
        assert "Sample App" in res.data, ("Application should be shown to "
                                          "the owner")
        msg = '<strong><i class="icon-cog"></i> ID</strong>: 1'
        err_msg = "Application ID should be shown to the owner"
        assert msg in res.data, err_msg

        self.signout()
        with self.flask_app.app_context():
            self.create()
            self.signin(email=Fixtures.email_addr2, password=Fixtures.password)
            res = self.app.get('/app/sampleapp/settings', follow_redirects=True)
            assert res.status_code == 403, res.status_code

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    @patch('pybossa.ckan.requests.get')
    def test_30_app_id_anonymous_user(self, Mock, mock):
        """Test WEB application page does not show the ID to anonymous users"""
        html_request = FakeRequest(json.dumps(self.pkg_json_not_found), 200,
                                   {'content-type': 'application/json'})
        Mock.return_value = html_request

        self.register()
        self.new_application()
        self.signout()

        res = self.app.get('/app/sampleapp', follow_redirects=True)
        assert "Sample App" in res.data, ("Application name should be shown"
                                          " to users")
        assert '<strong><i class="icon-cog"></i> ID</strong>: 1' not in \
            res.data, "Application ID should be shown to the owner"

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_31_user_profile_progress(self, mock):
        """Test WEB user progress profile page works"""
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        task = Task(app_id=app.id, info={'n_answers': '10'})
        db.session.add(task)
        db.session.commit()
        for i in range(10):
            task_run = TaskRun(app_id=app.id, task_id=1, user_id=1,
                                     info={'answer': 1})
            db.session.add(task_run)
            db.session.commit()
            self.app.get('api/app/%s/newtask' % app.id)

        res = self.app.get('account/johndoe', follow_redirects=True)
        assert "Sample App" in res.data, res.data
        assert "You have contributed to <strong>10</strong> tasks" in res.data, res.data
        assert "Contribute!" in res.data, "There should be a Contribute button"

    @with_context
    def test_32_oauth_password(self):
        """Test WEB user sign in without password works"""
        user = User(email_addr="johndoe@johndoe.com",
                          name=self.user.username,
                          passwd_hash=None,
                          fullname=self.user.fullname,
                          api_key="api-key")
        db.session.add(user)
        db.session.commit()
        res = self.signin()
        assert "Ooops, we didn't find you in the system" in res.data, res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    @patch('pybossa.view.importer.requests.get')
    def test_33_bulk_csv_import_unauthorized(self, Mock, mock):
        """Test WEB bulk import unauthorized works"""
        unauthorized_request = FakeRequest('Unauthorized', 403,
                                           {'content-type': 'text/csv'})
        Mock.return_value = unauthorized_request
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'csv_url': 'http://myfakecsvurl.com',
                                       'formtype': 'csv'},
                            follow_redirects=True)
        msg = "Oops! It looks like you don't have permission to access that file"
        assert msg in res.data, res.data

    @with_context
    @patch('pybossa.view.importer.requests.get')
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_34_bulk_csv_import_non_html(self, Mock, mock):
        """Test WEB bulk import non html works"""
        html_request = FakeRequest('Not a CSV', 200,
                                   {'content-type': 'text/html'})
        Mock.return_value = html_request
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'csv_url': 'http://myfakecsvurl.com'},
                            follow_redirects=True)
        assert "Oops! That file doesn't look like the right file." in res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    @patch('pybossa.view.importer.requests.get')
    def test_35_bulk_csv_import_non_html(self, Mock, mock):
        """Test WEB bulk import non html works"""
        empty_file = FakeRequest('CSV,with,no,content\n', 200,
                                 {'content-type': 'text/plain'})
        Mock.return_value = empty_file
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'csv_url': 'http://myfakecsvurl.com',
                                       'formtype': 'csv'},
                            follow_redirects=True)
        assert "Oops! It looks like the file is empty." in res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    @patch('pybossa.view.importer.requests.get')
    def test_36_bulk_csv_import_dup_header(self, Mock, mock):
        """Test WEB bulk import duplicate header works"""
        empty_file = FakeRequest('Foo,Bar,Foo\n1,2,3', 200,
                                 {'content-type': 'text/plain'})
        Mock.return_value = empty_file
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'csv_url': 'http://myfakecsvurl.com',
                                       'formtype': 'csv'},
                            follow_redirects=True)
        msg = "The file you uploaded has two headers with the same name"
        assert msg in res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    @patch('pybossa.view.importer.requests.get')
    def test_37_bulk_csv_import_no_column_names(self, Mock, mock):
        """Test WEB bulk import no column names works"""
        empty_file = FakeRequest('Foo,Bar,Baz\n1,2,3', 200,
                                 {'content-type': 'text/plain'})
        Mock.return_value = empty_file
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'csv_url': 'http://myfakecsvurl.com',
                                       'formtype': 'csv'},
                            follow_redirects=True)
        task = db.session.query(Task).first()
        assert {u'Bar': u'2', u'Foo': u'1', u'Baz': u'3'} == task.info
        assert "1 Task imported successfully!" in res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    @patch('pybossa.view.importer.requests.get')
    def test_38_bulk_csv_import_with_column_name(self, Mock, mock):
        """Test WEB bulk import with column name works"""
        empty_file = FakeRequest('Foo,Bar,priority_0\n1,2,3', 200,
                                 {'content-type': 'text/plain'})
        Mock.return_value = empty_file
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'csv_url': 'http://myfakecsvurl.com',
                                       'formtype': 'csv'},
                            follow_redirects=True)
        task = db.session.query(Task).first()
        assert {u'Bar': u'2', u'Foo': u'1'} == task.info
        assert task.priority_0 == 3
        assert "1 Task imported successfully!" in res.data

        # Check that only new items are imported
        empty_file = FakeRequest('Foo,Bar,priority_0\n1,2,3\n4,5,6', 200,
                                 {'content-type': 'text/plain'})
        Mock.return_value = empty_file
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'csv_url': 'http://myfakecsvurl.com',
                                       'formtype': 'csv'},
                            follow_redirects=True)
        app = db.session.query(App).first()
        assert len(app.tasks) == 2, "There should be only 2 tasks"
        n = 0
        csv_tasks = [{u'Foo': u'1', u'Bar': u'2'}, {u'Foo': u'4', u'Bar': u'5'}]
        for t in app.tasks:
            assert t.info == csv_tasks[n], "The task info should be the same"
            n += 1

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    @patch('pybossa.view.importer.requests.get')
    def test_38_bulk_gdocs_import(self, Mock, mock):
        """Test WEB bulk GDocs import works."""
        empty_file = FakeRequest('Foo,Bar,priority_0\n1,2,3', 200,
                                 {'content-type': 'text/plain'})
        Mock.return_value = empty_file
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'googledocs_url': 'http://drive.google.com',
                                       'formtype': 'gdocs'},
                            follow_redirects=True)
        task = db.session.query(Task).first()
        assert {u'Bar': u'2', u'Foo': u'1'} == task.info
        assert task.priority_0 == 3
        assert "1 Task imported successfully!" in res.data

        # Check that only new items are imported
        empty_file = FakeRequest('Foo,Bar,priority_0\n1,2,3\n4,5,6', 200,
                                 {'content-type': 'text/plain'})
        Mock.return_value = empty_file
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'googledocs_url': 'http://drive.google.com',
                                       'formtype': 'gdocs'},
                            follow_redirects=True)
        app = db.session.query(App).first()
        assert len(app.tasks) == 2, "There should be only 2 tasks"
        n = 0
        csv_tasks = [{u'Foo': u'1', u'Bar': u'2'}, {u'Foo': u'4', u'Bar': u'5'}]
        for t in app.tasks:
            assert t.info == csv_tasks[n], "The task info should be the same"
            n += 1

        # Check that only new items are imported
        empty_file = FakeRequest('Foo,Bar,priority_0\n1,2,3\n4,5,6', 200,
                                 {'content-type': 'text/plain'})
        Mock.return_value = empty_file
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'googledocs_url': 'http://drive.google.com',
                                       'formtype': 'gdocs'},
                            follow_redirects=True)
        app = db.session.query(App).first()
        assert len(app.tasks) == 2, "There should be only 2 tasks"
        n = 0
        csv_tasks = [{u'Foo': u'1', u'Bar': u'2'}, {u'Foo': u'4', u'Bar': u'5'}]
        for t in app.tasks:
            assert t.info == csv_tasks[n], "The task info should be the same"
            n += 1
        assert "no new records" in res.data, res.data

    @with_context
    def test_39_google_oauth_creation(self):
        """Test WEB Google OAuth creation of user works"""
        fake_response = {
            u'access_token': u'access_token',
            u'token_type': u'Bearer',
            u'expires_in': 3600,
            u'id_token': u'token'}

        fake_user = {
            u'family_name': u'Doe', u'name': u'John Doe',
            u'picture': u'https://goo.gl/img.jpg',
            u'locale': u'en',
            u'gender': u'male',
            u'email': u'john@gmail.com',
            u'birthday': u'0000-01-15',
            u'link': u'https://plus.google.com/id',
            u'given_name': u'John',
            u'id': u'111111111111111111111',
            u'verified_email': True}

        from pybossa.view import google
        response_user = google.manage_user(fake_response['access_token'],
                                           fake_user, None)

        user = db.session.query(User).get(1)

        assert user.email_addr == response_user.email_addr, response_user

    @with_context
    def test_40_google_oauth_creation(self):
        """Test WEB Google OAuth detects same user name/email works"""
        fake_response = {
            u'access_token': u'access_token',
            u'token_type': u'Bearer',
            u'expires_in': 3600,
            u'id_token': u'token'}

        fake_user = {
            u'family_name': u'Doe', u'name': u'John Doe',
            u'picture': u'https://goo.gl/img.jpg',
            u'locale': u'en',
            u'gender': u'male',
            u'email': u'john@gmail.com',
            u'birthday': u'0000-01-15',
            u'link': u'https://plus.google.com/id',
            u'given_name': u'John',
            u'id': u'111111111111111111111',
            u'verified_email': True}

        self.register()
        self.signout()

        from pybossa.view import google
        response_user = google.manage_user(fake_response['access_token'],
                                           fake_user, None)

        assert response_user is None, response_user

    @with_context
    def test_39_facebook_oauth_creation(self):
        """Test WEB Facebook OAuth creation of user works"""
        fake_response = {
            u'access_token': u'access_token',
            u'token_type': u'Bearer',
            u'expires_in': 3600,
            u'id_token': u'token'}

        fake_user = {
            u'username': u'teleyinex',
            u'first_name': u'John',
            u'last_name': u'Doe',
            u'verified': True,
            u'name': u'John Doe',
            u'locale': u'en_US',
            u'gender': u'male',
            u'email': u'johndoe@example.com',
            u'quotes': u'"quote',
            u'link': u'http://www.facebook.com/johndoe',
            u'timezone': 1,
            u'updated_time': u'2011-11-11T12:33:52+0000',
            u'id': u'11111'}

        from pybossa.view import facebook
        response_user = facebook.manage_user(fake_response['access_token'],
                                             fake_user, None)

        user = db.session.query(User).get(1)

        assert user.email_addr == response_user.email_addr, response_user

    @with_context
    def test_40_facebook_oauth_creation(self):
        """Test WEB Facebook OAuth detects same user name/email works"""
        fake_response = {
            u'access_token': u'access_token',
            u'token_type': u'Bearer',
            u'expires_in': 3600,
            u'id_token': u'token'}

        fake_user = {
            u'username': u'teleyinex',
            u'first_name': u'John',
            u'last_name': u'Doe',
            u'verified': True,
            u'name': u'John Doe',
            u'locale': u'en_US',
            u'gender': u'male',
            u'email': u'johndoe@example.com',
            u'quotes': u'"quote',
            u'link': u'http://www.facebook.com/johndoe',
            u'timezone': 1,
            u'updated_time': u'2011-11-11T12:33:52+0000',
            u'id': u'11111'}

        self.register()
        self.signout()

        from pybossa.view import facebook
        response_user = facebook.manage_user(fake_response['access_token'],
                                             fake_user, None)

        assert response_user is None, response_user

    @with_context
    def test_39_twitter_oauth_creation(self):
        """Test WEB Twitter OAuth creation of user works"""
        fake_response = {
            u'access_token': {u'oauth_token': u'oauth_token',
                              u'oauth_token_secret': u'oauth_token_secret'},
            u'token_type': u'Bearer',
            u'expires_in': 3600,
            u'id_token': u'token'}

        fake_user = {u'screen_name': u'johndoe',
                     u'user_id': u'11111'}

        from pybossa.view import twitter
        response_user = twitter.manage_user(fake_response['access_token'],
                                            fake_user, None)

        user = db.session.query(User).get(1)

        assert user.email_addr == response_user.email_addr, response_user

        res = self.signin(email=user.email_addr, password='wrong')
        msg = "It seems like you signed up with your Twitter account"
        assert msg in res.data, msg

    @with_context
    def test_40_twitter_oauth_creation(self):
        """Test WEB Twitter OAuth detects same user name/email works"""
        fake_response = {
            u'access_token': {u'oauth_token': u'oauth_token',
                              u'oauth_token_secret': u'oauth_token_secret'},
            u'token_type': u'Bearer',
            u'expires_in': 3600,
            u'id_token': u'token'}

        fake_user = {u'screen_name': u'johndoe',
                     u'user_id': u'11111'}

        self.register()
        self.signout()

        from pybossa.view import twitter
        response_user = twitter.manage_user(fake_response['access_token'],
                                            fake_user, None)

        assert response_user is None, response_user

    @with_context
    def test_41_password_change(self):
        """Test WEB password changing"""
        password = "mehpassword"
        self.register(password=password)
        res = self.app.post('/account/johndoe/update',
                            data={'current_password': password,
                                  'new_password': "p4ssw0rd",
                                  'confirm': "p4ssw0rd",
                                  'btn': 'Password'},
                            follow_redirects=True)
        assert "Yay, you changed your password succesfully!" in res.data, res.data

        password = "mehpassword"
        self.register(password=password)
        res = self.app.post('/account/johndoe/update',
                            data={'current_password': "wrongpassword",
                                  'new_password': "p4ssw0rd",
                                  'confirm': "p4ssw0rd",
                                  'btn': 'Password'},
                            follow_redirects=True)
        msg = "Your current password doesn't match the one in our records"
        assert msg in res.data

        self.register(password=password)
        res = self.app.post('/account/johndoe/update',
                            data={'current_password': '',
                                  'new_password':'',
                                  'confirm': '',
                                  'btn': 'Password'},
                            follow_redirects=True)
        msg = "Please correct the errors"
        assert msg in res.data

    @with_context
    def test_42_password_link(self):
        """Test WEB visibility of password change link"""
        self.register()
        res = self.app.get('/account/johndoe/update')
        assert "Change your Password" in res.data
        user = User.query.get(1)
        user.twitter_user_id = 1234
        db.session.add(user)
        db.session.commit()
        res = self.app.get('/account/johndoe/update')
        assert "Change your Password" not in res.data, res.data

    @with_context
    def test_43_terms_of_use_and_data(self):
        """Test WEB terms of use is working"""
        res = self.app.get('account/signin', follow_redirects=True)
        assert "/help/terms-of-use" in res.data, res.data
        assert "http://opendatacommons.org/licenses/by/" in res.data, res.data

        res = self.app.get('account/register', follow_redirects=True)
        assert "http://okfn.org/terms-of-use/" in res.data, res.data
        assert "http://opendatacommons.org/licenses/by/" in res.data, res.data

    @with_context
    @patch('pybossa.view.account.signer.signer.loads')
    def test_44_password_reset_key_errors(self, Mock):
        """Test WEB password reset key errors are caught"""
        self.register()
        user = User.query.get(1)
        userdict = {'user': user.name, 'password': user.passwd_hash}
        fakeuserdict = {'user': user.name, 'password': 'wronghash'}
        fakeuserdict_err = {'user': user.name, 'passwd': 'some'}
        fakeuserdict_form = {'user': user.name, 'passwd': 'p4ssw0rD'}
        key = signer.signer.dumps(userdict, salt='password-reset')
        returns = [BadSignature('Fake Error'), BadSignature('Fake Error'), userdict,
                   fakeuserdict, userdict, userdict, fakeuserdict_err]

        def side_effects(*args, **kwargs):
            result = returns.pop(0)
            if isinstance(result, BadSignature):
                raise result
            return result
        Mock.side_effect = side_effects
        # Request with no key
        res = self.app.get('/account/reset-password', follow_redirects=True)
        assert 403 == res.status_code
        # Request with invalid key
        res = self.app.get('/account/reset-password?key=foo', follow_redirects=True)
        assert 403 == res.status_code
        # Request with key exception
        res = self.app.get('/account/reset-password?key=%s' % (key), follow_redirects=True)
        assert 403 == res.status_code
        res = self.app.get('/account/reset-password?key=%s' % (key), follow_redirects=True)
        assert 200 == res.status_code
        res = self.app.get('/account/reset-password?key=%s' % (key), follow_redirects=True)
        assert 403 == res.status_code

        # Check validation
        res = self.app.post('/account/reset-password?key=%s' % (key),
                            data={'new_password': '',
                                  'confirm': '#4a4'},
                            follow_redirects=True)

        assert "Please correct the errors" in res.data, res.data

        res = self.app.post('/account/reset-password?key=%s' % (key),
                            data={'new_password': 'p4ssw0rD',
                                  'confirm': 'p4ssw0rD'},
                            follow_redirects=True)

        assert "You reset your password successfully!" in res.data

        # Request without password
        res = self.app.get('/account/reset-password?key=%s' % (key), follow_redirects=True)
        assert 403 == res.status_code

    @with_context
    def test_45_password_reset_link(self):
        """Test WEB password reset email form"""
        res = self.app.post('/account/forgot-password',
                            data={'email_addr': self.user.email_addr},
                            follow_redirects=True)
        assert ("We don't have this email in our records. You may have"
                " signed up with a different email or used Twitter, "
                "Facebook, or Google to sign-in") in res.data

        self.register()
        self.register(name='janedoe')
        self.register(name='google')
        self.register(name='facebook')
        jane = User.query.get(2)
        jane.twitter_user_id = 10
        google = User.query.get(3)
        google.google_user_id = 103
        facebook = User.query.get(4)
        facebook.facebook_user_id = 104
        db.session.add_all([jane, google, facebook])
        db.session.commit()
        with mail.record_messages() as outbox:
            self.app.post('/account/forgot-password',
                          data={'email_addr': self.user.email_addr},
                          follow_redirects=True)
            self.app.post('/account/forgot-password',
                          data={'email_addr': 'janedoe@example.com'},
                          follow_redirects=True)
            self.app.post('/account/forgot-password',
                          data={'email_addr': 'google@example.com'},
                          follow_redirects=True)
            self.app.post('/account/forgot-password',
                          data={'email_addr': 'facebook@example.com'},
                          follow_redirects=True)

            assert 'Click here to recover your account' in outbox[0].body
            assert 'your Twitter account to ' in outbox[1].body
            assert 'your Google account to ' in outbox[2].body
            assert 'your Facebook account to ' in outbox[3].body

        # Test with not valid form
        res = self.app.post('/account/forgot-password',
                            data={'email_addr': ''},
                            follow_redirects=True)
        msg = "Something went wrong, please correct the errors"
        assert msg in res.data, res.data


    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_46_tasks_exists(self, mock):
        """Test WEB tasks page works."""
        self.register()
        self.new_application()
        res = self.app.get('/app/sampleapp/tasks/', follow_redirects=True)
        assert "Edit the task presenter" in res.data, \
            "Task Presenter Editor should be an option"

        app = db.session.query(App).first()
        app.hidden = 1
        db.session.add(app)
        db.session.commit()
        # As owner
        res = self.app.get('/app/sampleapp/tasks/', follow_redirects=True)
        assert res.status_code == 200, res.status_code
        assert "Edit the task presenter" in res.data, \
            "Task Presenter Editor should be an option"
        self.signout()
        # As anonymous
        res = self.app.get('/app/sampleapp/tasks/', follow_redirects=True)
        assert res.status_code == 403, res.status_code

        with self.flask_app.app_context():
            self.create()

        # As another user, but not owner
        self.signin(email=Fixtures.email_addr2, password=Fixtures.password)
        res = self.app.get('/app/sampleapp/tasks/', follow_redirects=True)
        assert res.status_code == 403, res.status_code
        self.signout()

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_47_task_presenter_editor_loads(self, mock):
        """Test WEB task presenter editor loads"""
        self.register()
        self.new_application()
        res = self.app.get('/app/sampleapp/tasks/taskpresentereditor',
                           follow_redirects=True)
        err_msg = "Task Presenter options not found"
        assert "Task Presenter Editor" in res.data, err_msg
        err_msg = "Basic template not found"
        assert "The most basic template" in res.data, err_msg
        err_msg = "Image Pattern Recognition not found"
        assert "Flickr Person Finder template" in res.data, err_msg
        err_msg = "Geo-coding"
        assert "Urban Park template" in res.data, err_msg
        err_msg = "Transcribing documents"
        assert "PDF transcription template" in res.data, err_msg

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_48_task_presenter_editor_works(self, mock):
        """Test WEB task presenter editor works"""
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        err_msg = "Task Presenter should be empty"
        assert not app.info.get('task_presenter'), err_msg

        res = self.app.get('/app/sampleapp/tasks/taskpresentereditor?template=basic',
                           follow_redirects=True)
        assert "var editor" in res.data, "CodeMirror Editor not found"
        assert "Task Presenter" in res.data, "CodeMirror Editor not found"
        assert "Task Presenter Preview" in res.data, "CodeMirror View not found"
        res = self.app.post('/app/sampleapp/tasks/taskpresentereditor',
                            data={'editor': 'Some HTML code!'},
                            follow_redirects=True)
        assert "Sample App" in res.data, "Does not return to app details"
        app = db.session.query(App).first()
        err_msg = "Task Presenter failed to update"
        assert app.info['task_presenter'] == 'Some HTML code!', err_msg

        # Check it loads the previous posted code:
        res = self.app.get('/app/sampleapp/tasks/taskpresentereditor',
                           follow_redirects=True)
        assert "Some HTML code" in res.data, res.data

        # Now with hidden apps
        app.hidden = 1
        db.session.add(app)
        db.session.commit()
        res = self.app.get('/app/sampleapp/tasks/taskpresentereditor?template=basic',
                           follow_redirects=True)
        assert "var editor" in res.data, "CodeMirror Editor not found"
        assert "Task Presenter" in res.data, "CodeMirror Editor not found"
        assert "Task Presenter Preview" in res.data, "CodeMirror View not found"

        res = self.app.post('/app/sampleapp/tasks/taskpresentereditor',
                            data={'editor': 'Some HTML code!'},
                            follow_redirects=True)
        assert "Sample App" in res.data, "Does not return to app details"
        app = db.session.query(App).first()
        err_msg = "Task Presenter failed to update"
        assert app.info['task_presenter'] == 'Some HTML code!', err_msg

        # Check it loads the previous posted code:
        res = self.app.get('/app/sampleapp/tasks/taskpresentereditor',
                           follow_redirects=True)
        assert "Some HTML code" in res.data, res.data

        self.signout()
        with self.flask_app.app_context():
            self.create()
        self.signin(email=Fixtures.email_addr2, password=Fixtures.password)
        res = self.app.get('/app/sampleapp/tasks/taskpresentereditor?template=basic',
                           follow_redirects=True)
        assert res.status_code == 403


    @with_context
    @patch('pybossa.ckan.requests.get')
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_48_update_app_info(self, Mock, mock):
        """Test WEB app update/edit works keeping previous info values"""
        html_request = FakeRequest(json.dumps(self.pkg_json_not_found), 200,
                                   {'content-type': 'application/json'})
        Mock.return_value = html_request

        self.register()
        self.new_application()
        app = db.session.query(App).first()
        err_msg = "Task Presenter should be empty"
        assert not app.info.get('task_presenter'), err_msg

        res = self.app.post('/app/sampleapp/tasks/taskpresentereditor',
                            data={'editor': 'Some HTML code!'},
                            follow_redirects=True)
        assert "Sample App" in res.data, "Does not return to app details"
        app = db.session.query(App).first()
        for i in range(10):
            key = "key_%s" % i
            app.info[key] = i
        db.session.add(app)
        db.session.commit()
        _info = app.info

        self.update_application()
        app = db.session.query(App).first()
        for key in _info:
            assert key in app.info.keys(), \
                "The key %s is lost and it should be here" % key
        assert app.name == "Sample App", "The app has not been updated"
        error_msg = "The app description has not been updated"
        assert app.description == "Description", error_msg
        error_msg = "The app long description has not been updated"
        assert app.long_description == "Long desc", error_msg

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_49_announcement_messages(self, mock):
        """Test WEB announcement messages works"""
        self.register()
        res = self.app.get("/", follow_redirects=True)
        error_msg = "There should be a message for the root user"
        print res.data
        assert "Root Message" in res.data, error_msg
        error_msg = "There should be a message for the user"
        assert "User Message" in res.data, error_msg
        error_msg = "There should not be an owner message"
        assert "Owner Message" not in res.data, error_msg
        # Now make the user an app owner
        self.new_application()
        res = self.app.get("/", follow_redirects=True)
        error_msg = "There should be a message for the root user"
        assert "Root Message" in res.data, error_msg
        error_msg = "There should be a message for the user"
        assert "User Message" in res.data, error_msg
        error_msg = "There should be an owner message"
        assert "Owner Message" in res.data, error_msg
        self.signout()

        # Register another user
        self.register(method="POST", fullname="Jane Doe", name="janedoe",
                      password="janedoe", password2="janedoe",
                      email="jane@jane.com")
        res = self.app.get("/", follow_redirects=True)
        error_msg = "There should not be a message for the root user"
        assert "Root Message" not in res.data, error_msg
        error_msg = "There should be a message for the user"
        assert "User Message" in res.data, error_msg
        error_msg = "There should not be an owner message"
        assert "Owner Message" not in res.data, error_msg
        self.signout()

        # Now as an anonymous user
        res = self.app.get("/", follow_redirects=True)
        error_msg = "There should not be a message for the root user"
        assert "Root Message" not in res.data, error_msg
        error_msg = "There should not be a message for the user"
        assert "User Message" not in res.data, error_msg
        error_msg = "There should not be an owner message"
        assert "Owner Message" not in res.data, error_msg

    @with_context
    def test_50_export_task_json(self):
        """Test WEB export Tasks to JSON works"""
        Fixtures.create()
        # First test for a non-existant app
        uri = '/app/somethingnotexists/tasks/export'
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # Now get the tasks in JSON format
        uri = "/app/somethingnotexists/tasks/export?type=task&format=json"
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

        # Now with a real app
        uri = '/app/%s/tasks/export' % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        heading = "<strong>%s</strong>: Export All Tasks and Task Runs" % Fixtures.app_name
        assert heading in res.data, "Export page should be available\n %s" % res.data
        # Now test that a 404 is raised when an arg is invalid
        uri = "/app/%s/tasks/export?type=ask&format=json" % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        uri = "/app/%s/tasks/export?format=json" % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        uri = "/app/%s/tasks/export?type=task" % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # And a 415 is raised if the requested format is not supported or invalid
        uri = "/app/%s/tasks/export?type=task&format=gson" % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '415 UNSUPPORTED MEDIA TYPE', res.status

        # Now get the tasks in JSON format
        uri = "/app/%s/tasks/export?type=task&format=json" % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        exported_tasks = json.loads(res.data)
        app = db.session.query(App)\
                .filter_by(short_name=Fixtures.app_short_name)\
                .first()
        err_msg = "The number of exported tasks is different from App Tasks"
        assert len(exported_tasks) == len(app.tasks), err_msg

        app.hidden = 1
        db.session.add(app)
        db.session.commit()
        res = self.app.get('app/%s/tasks/export' % (app.short_name),
                           follow_redirects=True)
        assert res.status_code == 403, res.status_code

        self.signin(email=Fixtures.email_addr2, password=Fixtures.password)
        res = self.app.get('app/%s/tasks/export' % (app.short_name),
                           follow_redirects=True)
        assert res.status_code == 403, res.status_code
        # Owner
        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        res = self.app.get('app/%s/tasks/export' % (app.short_name),
                           follow_redirects=True)
        assert res.status_code == 200, res.status_code

    @with_context
    def test_51_export_taskruns_json(self):
        """Test WEB export Task Runs to JSON works"""
        Fixtures.create()
        # First test for a non-existant app
        uri = '/app/somethingnotexists/tasks/export'
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # Now get the tasks in JSON format
        uri = "/app/somethingnotexists/tasks/export?type=taskrun&format=json"
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

        # Now with a real app
        uri = '/app/%s/tasks/export' % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        heading = "<strong>%s</strong>: Export All Tasks and Task Runs" % Fixtures.app_name
        assert heading in res.data, "Export page should be available\n %s" % res.data
        # Now get the tasks in JSON format
        uri = "/app/%s/tasks/export?type=task_run&format=json" % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        exported_task_runs = json.loads(res.data)
        app = db.session.query(App)\
                .filter_by(short_name=Fixtures.app_short_name)\
                .first()
        err_msg = "The number of exported task runs is different from App Tasks"
        assert len(exported_task_runs) == len(app.task_runs), err_msg

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_52_export_task_csv(self, mock):
        """Test WEB export Tasks to CSV works"""
        Fixtures.create()
        # First test for a non-existant app
        uri = '/app/somethingnotexists/tasks/export'
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # Now get the tasks in CSV format
        uri = "/app/somethingnotexists/tasks/export?type=task&format=csv"
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # Now get the wrong table name in CSV format
        uri = "/app/%s/tasks/export?type=wrong&format=csv" % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

        # Now with a real app
        uri = '/app/%s/tasks/export' % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        heading = "<strong>%s</strong>: Export All Tasks and Task Runs" % Fixtures.app_name
        assert heading in res.data, "Export page should be available\n %s" % res.data
        # Now get the tasks in CSV format
        uri = "/app/%s/tasks/export?type=task&format=csv" % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        csv_content = StringIO.StringIO(res.data)
        csvreader = unicode_csv_reader(csv_content)
        app = db.session.query(App)\
                .filter_by(short_name=Fixtures.app_short_name)\
                .first()
        exported_tasks = []
        n = 0
        for row in csvreader:
            if n != 0:
                exported_tasks.append(row)
            n = n + 1
        err_msg = "The number of exported tasks is different from App Tasks"
        assert len(exported_tasks) == len(app.tasks), err_msg

        # With an empty app
        self.register()
        self.new_application()
        # Now get the tasks in CSV format
        uri = "/app/sampleapp/tasks/export?type=task&format=csv"
        res = self.app.get(uri, follow_redirects=True)
        msg = "application does not have tasks"
        assert msg in res.data, msg

    @with_context
    def test_53_export_task_runs_csv(self):
        """Test WEB export Task Runs to CSV works"""
        Fixtures.create()
        # First test for a non-existant app
        uri = '/app/somethingnotexists/tasks/export'
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # Now get the tasks in CSV format
        uri = "/app/somethingnotexists/tasks/export?type=tas&format=csv"
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

        # Now with a real app
        uri = '/app/%s/tasks/export' % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        heading = "<strong>%s</strong>: Export All Tasks and Task Runs" % Fixtures.app_name
        assert heading in res.data, "Export page should be available\n %s" % res.data
        # Now get the tasks in CSV format
        uri = "/app/%s/tasks/export?type=task_run&format=csv" % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        csv_content = StringIO.StringIO(res.data)
        csvreader = unicode_csv_reader(csv_content)
        app = db.session.query(App)\
                .filter_by(short_name=Fixtures.app_short_name)\
                .first()
        exported_task_runs = []
        n = 0
        for row in csvreader:
            if n != 0:
                exported_task_runs.append(row)
            n = n + 1
        err_msg = "The number of exported task runs is different \
                   from App Tasks Runs"
        assert len(exported_task_runs) == len(app.task_runs), err_msg

    @with_context
    @patch('pybossa.view.applications.Ckan', autospec=True)
    def test_export_tasks_ckan_exception(self, mock1):
        mocks = [Mock()]
        from test_ckan import TestCkanModule
        fake_ckn = TestCkanModule()
        package = fake_ckn.pkg_json_found
        package['id'] = 3
        mocks[0].package_exists.return_value = (False,
                                                Exception("CKAN: error",
                                                          "error", 500))
        # mocks[0].package_create.return_value = fake_ckn.pkg_json_found
        # mocks[0].resource_create.return_value = dict(result=dict(id=3))
        # mocks[0].datastore_create.return_value = 'datastore'
        # mocks[0].datastore_upsert.return_value = 'datastore'

        mock1.side_effect = mocks

        """Test WEB Export CKAN Tasks works."""
        Fixtures.create()
        user = db.session.query(User).filter_by(name=Fixtures.name).first()
        app = db.session.query(App).first()
        user.ckan_api = 'ckan-api-key'
        app.owner_id = user.id
        db.session.add(user)
        db.session.add(app)
        db.session.commit()

        self.signin(email=user.email_addr, password=Fixtures.password)
        # Now with a real app
        uri = '/app/%s/tasks/export' % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        heading = "<strong>%s</strong>: Export All Tasks and Task Runs" % Fixtures.app_name
        assert heading in res.data, "Export page should be available\n %s" % res.data
        # Now get the tasks in CKAN format
        uri = "/app/%s/tasks/export?type=task&format=ckan" % Fixtures.app_short_name
        with patch.dict(self.flask_app.config, {'CKAN_URL': 'http://ckan.com'}):
            # First time exporting the package
            res = self.app.get(uri, follow_redirects=True)
            msg = 'Error'
            err_msg = "An exception should be raised"
            assert msg in res.data, err_msg

    @with_context
    @patch('pybossa.view.applications.Ckan', autospec=True)
    def test_export_tasks_ckan_connection_error(self, mock1):
        mocks = [Mock()]
        from test_ckan import TestCkanModule
        fake_ckn = TestCkanModule()
        package = fake_ckn.pkg_json_found
        package['id'] = 3
        mocks[0].package_exists.return_value = (False, ConnectionError)
        # mocks[0].package_create.return_value = fake_ckn.pkg_json_found
        # mocks[0].resource_create.return_value = dict(result=dict(id=3))
        # mocks[0].datastore_create.return_value = 'datastore'
        # mocks[0].datastore_upsert.return_value = 'datastore'

        mock1.side_effect = mocks

        """Test WEB Export CKAN Tasks works."""
        Fixtures.create()
        user = db.session.query(User).filter_by(name=Fixtures.name).first()
        app = db.session.query(App).first()
        user.ckan_api = 'ckan-api-key'
        app.owner_id = user.id
        db.session.add(user)
        db.session.add(app)
        db.session.commit()

        self.signin(email=user.email_addr, password=Fixtures.password)
        # Now with a real app
        uri = '/app/%s/tasks/export' % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        heading = "<strong>%s</strong>: Export All Tasks and Task Runs" % Fixtures.app_name
        assert heading in res.data, "Export page should be available\n %s" % res.data
        # Now get the tasks in CKAN format
        uri = "/app/%s/tasks/export?type=task&format=ckan" % Fixtures.app_short_name
        with patch.dict(self.flask_app.config, {'CKAN_URL': 'http://ckan.com'}):
            # First time exporting the package
            res = self.app.get(uri, follow_redirects=True)
            msg = 'CKAN server seems to be down'
            err_msg = "A connection exception should be raised"
            assert msg in res.data, err_msg

    @with_context
    @patch('pybossa.view.applications.Ckan', autospec=True)
    def test_task_export_tasks_ckan_first_time(self, mock1):
        """Test WEB Export CKAN Tasks works without an existing package."""
        # Second time exporting the package
        mocks = [Mock()]
        resource = dict(name='task', id=1)
        package = dict(id=3, resources=[resource])
        mocks[0].package_exists.return_value = (None, None)
        mocks[0].package_create.return_value = package
        #mocks[0].datastore_delete.return_value = None
        mocks[0].datastore_create.return_value = None
        mocks[0].datastore_upsert.return_value = None
        mocks[0].resource_create.return_value = dict(result=dict(id=3))
        mocks[0].datastore_create.return_value = 'datastore'
        mocks[0].datastore_upsert.return_value = 'datastore'

        mock1.side_effect = mocks

        Fixtures.create()
        user = db.session.query(User).filter_by(name=Fixtures.name).first()
        app = db.session.query(App).first()
        user.ckan_api = 'ckan-api-key'
        app.owner_id = user.id
        db.session.add(user)
        db.session.add(app)
        db.session.commit()

        self.signin(email=user.email_addr, password=Fixtures.password)
        # First test for a non-existant app
        uri = '/app/somethingnotexists/tasks/export'
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # Now get the tasks in CKAN format
        uri = "/app/somethingnotexists/tasks/export?type=task&format=ckan"
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # Now get the tasks in CKAN format
        uri = "/app/somethingnotexists/tasks/export?type=other&format=ckan"
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status


        # Now with a real app
        uri = '/app/%s/tasks/export' % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        heading = "<strong>%s</strong>: Export All Tasks and Task Runs" % Fixtures.app_name
        assert heading in res.data, "Export page should be available\n %s" % res.data
        # Now get the tasks in CKAN format
        uri = "/app/%s/tasks/export?type=task&format=ckan" % Fixtures.app_short_name
        #res = self.app.get(uri, follow_redirects=True)
        with patch.dict(self.flask_app.config, {'CKAN_URL': 'http://ckan.com'}):
            # First time exporting the package
            res = self.app.get(uri, follow_redirects=True)
            msg = 'Data exported to http://ckan.com'
            err_msg = "Tasks should be exported to CKAN"
            assert msg in res.data, err_msg



    @with_context
    @patch('pybossa.view.applications.Ckan', autospec=True)
    def test_task_export_tasks_ckan_second_time(self, mock1):
        """Test WEB Export CKAN Tasks works with an existing package."""
        # Second time exporting the package
        mocks = [Mock()]
        resource = dict(name='task', id=1)
        package = dict(id=3, resources=[resource])
        mocks[0].package_exists.return_value = (package, None)
        mocks[0].package_update.return_value = package
        mocks[0].datastore_delete.return_value = None
        mocks[0].datastore_create.return_value = None
        mocks[0].datastore_upsert.return_value = None
        mocks[0].resource_create.return_value = dict(result=dict(id=3))
        mocks[0].datastore_create.return_value = 'datastore'
        mocks[0].datastore_upsert.return_value = 'datastore'

        mock1.side_effect = mocks

        Fixtures.create()
        user = db.session.query(User).filter_by(name=Fixtures.name).first()
        app = db.session.query(App).first()
        user.ckan_api = 'ckan-api-key'
        app.owner_id = user.id
        db.session.add(user)
        db.session.add(app)
        db.session.commit()

        self.signin(email=user.email_addr, password=Fixtures.password)
        # First test for a non-existant app
        uri = '/app/somethingnotexists/tasks/export'
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # Now get the tasks in CKAN format
        uri = "/app/somethingnotexists/tasks/export?type=task&format=ckan"
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

        # Now with a real app
        uri = '/app/%s/tasks/export' % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        heading = "<strong>%s</strong>: Export All Tasks and Task Runs" % Fixtures.app_name
        assert heading in res.data, "Export page should be available\n %s" % res.data
        # Now get the tasks in CKAN format
        uri = "/app/%s/tasks/export?type=task&format=ckan" % Fixtures.app_short_name
        #res = self.app.get(uri, follow_redirects=True)
        with patch.dict(self.flask_app.config, {'CKAN_URL': 'http://ckan.com'}):
            # First time exporting the package
            res = self.app.get(uri, follow_redirects=True)
            msg = 'Data exported to http://ckan.com'
            err_msg = "Tasks should be exported to CKAN"
            assert msg in res.data, err_msg

    @with_context
    @patch('pybossa.view.applications.Ckan', autospec=True)
    def test_task_export_tasks_ckan_without_resources(self, mock1):
        """Test WEB Export CKAN Tasks works without resources ."""
        mocks = [Mock()]
        package = dict(id=3, resources=[])
        mocks[0].package_exists.return_value = (package, None)
        mocks[0].package_update.return_value = package
        mocks[0].resource_create.return_value = dict(result=dict(id=3))
        mocks[0].datastore_create.return_value = 'datastore'
        mocks[0].datastore_upsert.return_value = 'datastore'


        mock1.side_effect = mocks

        Fixtures.create()
        user = db.session.query(User).filter_by(name=Fixtures.name).first()
        app = db.session.query(App).first()
        user.ckan_api = 'ckan-api-key'
        app.owner_id = user.id
        db.session.add(user)
        db.session.add(app)
        db.session.commit()

        self.signin(email=user.email_addr, password=Fixtures.password)
        # First test for a non-existant app
        uri = '/app/somethingnotexists/tasks/export'
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status
        # Now get the tasks in CKAN format
        uri = "/app/somethingnotexists/tasks/export?type=task&format=ckan"
        res = self.app.get(uri, follow_redirects=True)
        assert res.status == '404 NOT FOUND', res.status

        # Now with a real app
        uri = '/app/%s/tasks/export' % Fixtures.app_short_name
        res = self.app.get(uri, follow_redirects=True)
        heading = "<strong>%s</strong>: Export All Tasks and Task Runs" % Fixtures.app_name
        assert heading in res.data, "Export page should be available\n %s" % res.data
        # Now get the tasks in CKAN format
        uri = "/app/%s/tasks/export?type=task&format=ckan" % Fixtures.app_short_name
        #res = self.app.get(uri, follow_redirects=True)
        with patch.dict(self.flask_app.config, {'CKAN_URL': 'http://ckan.com'}):
            # First time exporting the package
            res = self.app.get(uri, follow_redirects=True)
            msg = 'Data exported to http://ckan.com'
            err_msg = "Tasks should be exported to CKAN"
            assert msg in res.data, err_msg

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_54_import_tasks(self, mock):
        """Test WEB import Task templates should work"""
        Fixtures.create()
        self.register()
        self.new_application()
        # Without tasks, there should be a template
        res = self.app.get('/app/sampleapp/tasks/import', follow_redirects=True)
        err_msg = "There should be a CSV template"
        assert "template=csv" in res.data, err_msg
        err_msg = "There should be an Image template"
        assert "mode=image" in res.data, err_msg
        err_msg = "There should be a Map template"
        assert "mode=map" in res.data, err_msg
        err_msg = "There should be a PDF template"
        assert "mode=pdf" in res.data, err_msg
        # With tasks
        self.new_task(1)
        res = self.app.get('/app/sampleapp/tasks/import', follow_redirects=True)
        err_msg = "There should load directly the basic template"
        err_msg = "There should not be a CSV template"
        assert "template=basic" not in res.data, err_msg
        err_msg = "There should not be an Image template"
        assert "template=image" not in res.data, err_msg
        err_msg = "There should not be a Map template"
        assert "template=map" not in res.data, err_msg
        err_msg = "There should not be a PDF template"
        assert "template=pdf" not in res.data, err_msg
        self.signout()

        self.signin(email=Fixtures.email_addr2, password=Fixtures.password)
        res = self.app.get('/app/sampleapp/tasks/import', follow_redirects=True)
        assert res.status_code == 403, res.status_code

    @with_context
    def test_55_facebook_account_warning(self):
        """Test WEB Facebook OAuth user gets a hint to sign in"""
        user = User(fullname='John',
                          name='john',
                          email_addr='john@john.com',
                          info={})

        user.info = dict(facebook_token=u'facebook')
        msg, method = get_user_signup_method(user)
        err_msg = "Should return 'facebook' but returned %s" % method
        assert method == 'facebook', err_msg

        user.info = dict(google_token=u'google')
        msg, method = get_user_signup_method(user)
        err_msg = "Should return 'google' but returned %s" % method
        assert method == 'google', err_msg

        user.info = dict(twitter_token=u'twitter')
        msg, method = get_user_signup_method(user)
        err_msg = "Should return 'twitter' but returned %s" % method
        assert method == 'twitter', err_msg

        user.info = {}
        msg, method = get_user_signup_method(user)
        err_msg = "Should return 'local' but returned %s" % method
        assert method == 'local', err_msg

    @with_context
    def test_56_delete_tasks(self):
        """Test WEB delete tasks works"""
        Fixtures.create()
        # Anonymous user
        res = self.app.get('/app/test-app/tasks/delete', follow_redirects=True)
        err_msg = "Anonymous user should be redirected for authentication"
        assert "Please sign in to access this page" in res.data, err_msg
        err_msg = "Anonymous user should not be allowed to delete tasks"
        res = self.app.post('/app/test-app/tasks/delete', follow_redirects=True)
        err_msg = "Anonymous user should not be allowed to delete tasks"
        assert "Please sign in to access this page" in res.data, err_msg

        # Authenticated user but not owner
        self.register()
        res = self.app.get('/app/test-app/tasks/delete', follow_redirects=True)
        err_msg = "Authenticated user but not owner should get 403 FORBIDDEN in GET"
        assert res.status == '403 FORBIDDEN', err_msg
        res = self.app.post('/app/test-app/tasks/delete', follow_redirects=True)
        err_msg = "Authenticated user but not owner should get 403 FORBIDDEN in POST"
        assert res.status == '403 FORBIDDEN', err_msg
        self.signout()

        # Owner
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        res = self.signin(email=u'tester@tester.com', password=u'tester')
        res = self.app.get('/app/test-app/tasks/delete', follow_redirects=True)
        err_msg = "Owner user should get 200 in GET"
        assert res.status == '200 OK', err_msg
        assert len(tasks) > 0, "len(app.tasks) > 0"
        res = self.app.post('/app/test-app/tasks/delete', follow_redirects=True)
        err_msg = "Owner should get 200 in POST"
        assert res.status == '200 OK', err_msg
        tasks = db.session.query(Task).filter_by(app_id=1).all()
        assert len(tasks) == 0, "len(app.tasks) != 0"

        # Admin
        res = self.signin(email=u'root@root.com', password=u'tester' + 'root')
        res = self.app.get('/app/test-app/tasks/delete', follow_redirects=True)
        err_msg = "Admin user should get 200 in GET"
        assert res.status_code == 200, err_msg
        res = self.app.post('/app/test-app/tasks/delete', follow_redirects=True)
        err_msg = "Admin should get 200 in POST"
        assert res.status_code == 200, err_msg

    @with_context
    def test_57_reset_api_key(self):
        """Test WEB reset api key works"""
        url = "/account/johndoe/update"
        # Anonymous user
        res = self.app.get(url, follow_redirects=True)
        err_msg = "Anonymous user should be redirected for authentication"
        assert "Please sign in to access this page" in res.data, err_msg
        res = self.app.post(url, follow_redirects=True)
        assert "Please sign in to access this page" in res.data, err_msg

        # Authenticated user
        self.register()
        user = db.session.query(User).get(1)
        url = "/account/%s/update" % user.name
        api_key = user.api_key
        res = self.app.get(url, follow_redirects=True)
        err_msg = "Authenticated user should get access to reset api key page"
        assert res.status_code == 200, err_msg
        assert "reset your personal API Key" in res.data, err_msg
        url = "/account/%s/resetapikey" % user.name
        res = self.app.post(url, follow_redirects=True)
        err_msg = "Authenticated user should be able to reset his api key"
        assert res.status_code == 200, err_msg
        user = db.session.query(User).get(1)
        err_msg = "New generated API key should be different from old one"
        assert api_key != user.api_key, err_msg

        self.register(fullname="new", name="new")
        res = self.app.post(url)
        res.status_code == 403

        url = "/account/fake/resetapikey"
        res = self.app.post(url)
        assert res.status_code == 404


    @with_context
    @patch('pybossa.view.stats.get_locs', return_value=[{'latitude':0, 'longitude':0}])
    def test_58_global_stats(self, mock1):
        """Test WEB global stats of the site works"""
        Fixtures.create()

        url = "/stats"
        res = self.app.get(url, follow_redirects=True)
        err_msg = "There should be a Global Statistics page of the project"
        assert "General Statistics" in res.data, err_msg

        with patch.dict(self.flask_app.config, {'GEO': True}):
            res = self.app.get(url, follow_redirects=True)
            assert "GeoLite" in res.data, res.data

    @with_context
    def test_59_help_api(self):
        """Test WEB help api page exists"""
        Fixtures.create()
        url = "/help/api"
        res = self.app.get(url, follow_redirects=True)
        err_msg = "There should be a help api page"
        assert "API Help" in res.data, err_msg

    @with_context
    def test_59_help_license(self):
        """Test WEB help license page exists."""
        url = "/help/license"
        res = self.app.get(url, follow_redirects=True)
        err_msg = "There should be a help license page"
        assert "Licenses" in res.data, err_msg

    @with_context
    def test_59_about(self):
        """Test WEB help about page exists."""
        url = "/about"
        res = self.app.get(url, follow_redirects=True)
        err_msg = "There should be an about page"
        assert "About" in res.data, err_msg

    @with_context
    def test_59_help_tos(self):
        """Test WEB help TOS page exists."""
        url = "/help/terms-of-use"
        res = self.app.get(url, follow_redirects=True)
        err_msg = "There should be a TOS page"
        assert "Terms for use" in res.data, err_msg

    @with_context
    def test_59_help_policy(self):
        """Test WEB help policy page exists."""
        url = "/help/cookies-policy"
        res = self.app.get(url, follow_redirects=True)
        err_msg = "There should be a TOS page"
        assert "uses cookies" in res.data, err_msg

    @with_context
    def test_69_allow_anonymous_contributors(self):
        """Test WEB allow anonymous contributors works"""
        Fixtures.create()
        app = db.session.query(App).first()
        url = '/app/%s/newtask' % app.short_name

        # All users are allowed to participate by default
        # As Anonymous user
        res = self.app.get(url, follow_redirects=True)
        err_msg = "The anonymous user should be able to participate"
        assert app.name in res.data, err_msg

        # As registered user
        self.register()
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        err_msg = "The anonymous user should be able to participate"
        assert app.name in res.data, err_msg
        self.signout()

        # Now only allow authenticated users
        app.allow_anonymous_contributors = False
        db.session.add(app)
        db.session.commit()

        # As Anonymous user
        res = self.app.get(url, follow_redirects=True)
        err_msg = "User should be redirected to sign in"
        app = db.session.query(App).first()
        msg = "Oops! You have to sign in to participate in <strong>%s</strong>" % app.name
        assert msg in res.data, err_msg

        # As registered user
        res = self.signin()
        res = self.app.get(url, follow_redirects=True)
        err_msg = "The authenticated user should be able to participate"
        assert app.name in res.data, err_msg
        self.signout()

        # However if the app is hidden, it should be forbidden
        app.hidden = 1
        db.session.add(app)
        db.session.commit()

        # As Anonymous user
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 403, res.status_code

        # As registered user
        self.register()
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 403, res.status_code
        self.signout()

        # As admin
        self.signin(email=Fixtures.root_addr, password=Fixtures.root_password)
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        self.signout()

        # As owner
        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200, res.status_code
        self.signout()

        # Now only allow authenticated users
        app.allow_anonymous_contributors = False
        app.hidden = 0
        db.session.add(app)
        db.session.commit()
        res = self.app.get(url, follow_redirects=True)
        err_msg = "Only authenticated users can participate"
        assert "You have to sign in" in res.data, err_msg


    @with_context
    def test_70_public_user_profile(self):
        """Test WEB public user profile works"""
        Fixtures.create()

        # Should work as an anonymous user
        url = '/account/%s/' % Fixtures.name
        res = self.app.get(url, follow_redirects=True)
        err_msg = "There should be a public profile page for the user"
        assert Fixtures.fullname in res.data, err_msg

        # Should work as an authenticated user
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        assert Fixtures.fullname in res.data, err_msg

        # Should return 404 when a user does not exist
        url = '/account/a-fake-name-that-does-not-exist/'
        res = self.app.get(url, follow_redirects=True)
        err_msg = "It should return a 404"
        assert res.status_code == 404, err_msg

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    @patch('pybossa.view.importer.requests.get')
    def test_71_bulk_epicollect_import_unauthorized(self, Mock, mock):
        """Test WEB bulk import unauthorized works"""
        unauthorized_request = FakeRequest('Unauthorized', 403,
                                           {'content-type': 'application/json'})
        Mock.return_value = unauthorized_request
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'epicollect_project': 'fakeproject',
                                       'epicollect_form': 'fakeform',
                                       'formtype': 'json'},
                            follow_redirects=True)
        msg = "Oops! It looks like you don't have permission to access the " \
              "EpiCollect Plus project"
        assert msg in res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    @patch('pybossa.view.importer.requests.get')
    def test_72_bulk_epicollect_import_non_html(self, Mock, mock):
        """Test WEB bulk import non html works"""
        html_request = FakeRequest('Not an application/json', 200,
                                   {'content-type': 'text/html'})
        Mock.return_value = html_request
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        url = '/app/%s/tasks/import?template=csv' % (app.short_name)
        res = self.app.post(url, data={'epicollect_project': 'fakeproject',
                                       'epicollect_form': 'fakeform',
                                       'formtype': 'json'},
                            follow_redirects=True)
        msg = "Oops! That project and form do not look like the right one."
        assert msg in res.data

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    @patch('pybossa.view.importer.requests.get')
    def test_73_bulk_epicollect_import_json(self, Mock, mock):
        """Test WEB bulk import json works"""
        data = [dict(DeviceID=23)]
        html_request = FakeRequest(json.dumps(data), 200,
                                   {'content-type': 'application/json'})
        Mock.return_value = html_request
        self.register()
        self.new_application()
        app = db.session.query(App).first()
        res = self.app.post(('/app/%s/tasks/import' % (app.short_name)),
                            data={'epicollect_project': 'fakeproject',
                                  'epicollect_form': 'fakeform',
                                  'formtype': 'json'},
                            follow_redirects=True)

        app = db.session.query(App).first()
        err_msg = "Tasks should be imported"
        assert "1 Task imported successfully!" in res.data, err_msg
        tasks = db.session.query(Task).filter_by(app_id=app.id).all()
        err_msg = "The imported task from EpiCollect is wrong"
        assert tasks[0].info['DeviceID'] == 23, err_msg

        data = [dict(DeviceID=23), dict(DeviceID=24)]
        html_request = FakeRequest(json.dumps(data), 200,
                                   {'content-type': 'application/json'})
        Mock.return_value = html_request
        res = self.app.post(('/app/%s/tasks/import' % (app.short_name)),
                            data={'epicollect_project': 'fakeproject',
                                  'epicollect_form': 'fakeform',
                                  'formtype': 'json'},
                            follow_redirects=True)
        app = db.session.query(App).first()
        assert len(app.tasks) == 2, "There should be only 2 tasks"
        n = 0
        epi_tasks = [{u'DeviceID': 23}, {u'DeviceID': 24}]
        for t in app.tasks:
            assert t.info == epi_tasks[n], "The task info should be the same"
            n += 1

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_74_task_settings_page(self, mock):
        """Test WEB TASK SETTINGS page works"""
        # Creat root user
        self.register()
        self.signout()
        # As owner
        self.register(fullname="owner", name="owner")
        res = self.new_application()
        url = "/app/sampleapp/tasks/settings"

        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        divs = ['task_scheduler', 'task_delete', 'task_redundancy']
        for div in divs:
            err_msg = "There should be a %s section" % div
            assert dom.find(id=div) is not None, err_msg

        self.signout()
        # As an authenticated user
        self.register(fullname="juan", name="juan")
        res = self.app.get(url, follow_redirects=True)
        err_msg = "User should not be allowed to access this page"
        assert res.status_code == 403, err_msg
        self.signout()

        # As an anonymous user
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "User should be redirected to sign in"
        assert dom.find(id="signin") is not None, err_msg

        # As root
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        divs = ['task_scheduler', 'task_delete', 'task_redundancy']
        for div in divs:
            err_msg = "There should be a %s section" % div
            assert dom.find(id=div) is not None, err_msg

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_75_task_settings_scheduler(self, mock):
        """Test WEB TASK SETTINGS scheduler page works"""
        # Creat root user
        self.register()
        self.signout()
        # Create owner
        self.register(fullname="owner", name="owner")
        self.new_application()
        url = "/app/sampleapp/tasks/scheduler"
        form_id = 'task_scheduler'
        self.signout()

        # As owner and root
        for i in range(0, 1):
            if i == 0:
                # As owner
                self.signin(email="owner@example.com")
                sched = 'random'
            else:
                sched = 'default'
                self.signin()
            res = self.app.get(url, follow_redirects=True)
            dom = BeautifulSoup(res.data)
            err_msg = "There should be a %s section" % form_id
            assert dom.find(id=form_id) is not None, err_msg
            res = self.task_settings_scheduler(short_name="sampleapp",
                                               sched=sched)
            dom = BeautifulSoup(res.data)
            err_msg = "Task Scheduler should be updated"
            assert dom.find(id='msg_success') is not None, err_msg
            app = db.session.query(App).get(1)
            assert app.info['sched'] == sched, err_msg
            self.signout()

        # As an authenticated user
        self.register(fullname="juan", name="juan")
        res = self.app.get(url, follow_redirects=True)
        err_msg = "User should not be allowed to access this page"
        assert res.status_code == 403, err_msg
        self.signout()

        # As an anonymous user
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "User should be redirected to sign in"
        assert dom.find(id="signin") is not None, err_msg

        # With hidden app
        app.hidden = 1
        db.session.add(app)
        db.session.commit()
        self.register(fullname="daniel", name="daniel")
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 403, res.status_code
        self.signout()
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        # Correct values
        err_msg = "There should be a %s section" % form_id
        assert dom.find(id=form_id) is not None, err_msg


    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_76_task_settings_redundancy(self, mock):
        """Test WEB TASK SETTINGS redundancy page works"""
        # Creat root user
        self.register()
        self.signout()
        # Create owner
        self.register(fullname="owner", name="owner")
        self.new_application()
        self.new_task(1)
        url = "/app/sampleapp/tasks/redundancy"
        form_id = 'task_redundancy'
        self.signout()

        # As owner and root
        for i in range(0, 1):
            if i == 0:
                # As owner
                self.signin(email="owner@example.com")
                n_answers = 20
            else:
                n_answers = 10
                self.signin()
            res = self.app.get(url, follow_redirects=True)
            dom = BeautifulSoup(res.data)
            # Correct values
            err_msg = "There should be a %s section" % form_id
            assert dom.find(id=form_id) is not None, err_msg
            res = self.task_settings_redundancy(short_name="sampleapp",
                                                n_answers=n_answers)
            dom = BeautifulSoup(res.data)
            err_msg = "Task Redundancy should be updated"
            assert dom.find(id='msg_success') is not None, err_msg
            app = db.session.query(App).get(1)
            for t in app.tasks:
                assert t.n_answers == n_answers, err_msg
            # Wrong values, triggering the validators
            res = self.task_settings_redundancy(short_name="sampleapp",
                                                n_answers=0)
            dom = BeautifulSoup(res.data)
            err_msg = "Task Redundancy should be a value between 0 and 1000"
            assert dom.find(id='msg_error') is not None, err_msg
            res = self.task_settings_redundancy(short_name="sampleapp",
                                                n_answers=10000000)
            dom = BeautifulSoup(res.data)
            err_msg = "Task Redundancy should be a value between 0 and 1000"
            assert dom.find(id='msg_error') is not None, err_msg


            self.signout()

        # As an authenticated user
        self.register(fullname="juan", name="juan")
        res = self.app.get(url, follow_redirects=True)
        err_msg = "User should not be allowed to access this page"
        assert res.status_code == 403, err_msg
        self.signout()

        # As an anonymous user
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "User should be redirected to sign in"
        assert dom.find(id="signin") is not None, err_msg

        # With hidden app
        app.hidden = 1
        db.session.add(app)
        db.session.commit()
        self.register(fullname="daniel", name="daniel")
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 403, res.status_code
        self.signout()
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        # Correct values
        err_msg = "There should be a %s section" % form_id
        assert dom.find(id=form_id) is not None, err_msg

    @with_context
    @patch('pybossa.view.applications.uploader.upload_file', return_value=True)
    def test_77_task_settings_priority(self, mock):
        """Test WEB TASK SETTINGS priority page works"""
        # Creat root user
        self.register()
        self.signout()
        # Create owner
        self.register(fullname="owner", name="owner")
        self.new_application()
        self.new_task(1)
        url = "/app/sampleapp/tasks/priority"
        form_id = 'task_priority'
        self.signout()

        # As owner and root
        app = db.session.query(App).get(1)
        _id = app.tasks[0].id
        for i in range(0, 1):
            if i == 0:
                # As owner
                self.signin(email="owner@example.com")
                task_ids = str(_id)
                priority_0 = 1.0
            else:
                task_ids = "1"
                priority_0 = 0.5
                self.signin()
            res = self.app.get(url, follow_redirects=True)
            dom = BeautifulSoup(res.data)
            # Correct values
            err_msg = "There should be a %s section" % form_id
            assert dom.find(id=form_id) is not None, err_msg
            res = self.task_settings_priority(short_name="sampleapp",
                                              task_ids=task_ids,
                                              priority_0=priority_0)
            dom = BeautifulSoup(res.data)
            err_msg = "Task Priority should be updated"
            assert dom.find(id='msg_success') is not None, err_msg
            task = db.session.query(Task).get(_id)
            assert task.id == int(task_ids), err_msg
            assert task.priority_0 == priority_0, err_msg
            # Wrong values, triggering the validators
            res = self.task_settings_priority(short_name="sampleapp",
                                              priority_0=3,
                                              task_ids="1")
            dom = BeautifulSoup(res.data)
            err_msg = "Task Priority should be a value between 0.0 and 1.0"
            assert dom.find(id='msg_error') is not None, err_msg
            res = self.task_settings_priority(short_name="sampleapp",
                                              task_ids="1, 2")
            dom = BeautifulSoup(res.data)
            err_msg = "Task Priority task_ids should be a comma separated, no spaces, integers"
            assert dom.find(id='msg_error') is not None, err_msg
            res = self.task_settings_priority(short_name="sampleapp",
                                              task_ids="1,a")
            dom = BeautifulSoup(res.data)
            err_msg = "Task Priority task_ids should be a comma separated, no spaces, integers"
            assert dom.find(id='msg_error') is not None, err_msg

            self.signout()

        # As an authenticated user
        self.register(fullname="juan", name="juan")
        res = self.app.get(url, follow_redirects=True)
        err_msg = "User should not be allowed to access this page"
        assert res.status_code == 403, err_msg
        self.signout()

        # As an anonymous user
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "User should be redirected to sign in"
        assert dom.find(id="signin") is not None, err_msg

        # With hidden app
        app.hidden = 1
        db.session.add(app)
        db.session.commit()
        self.register(fullname="daniel", name="daniel")
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 403, res.status_code
        self.signout()
        self.signin()
        res = self.app.get(url, follow_redirects=True)
        dom = BeautifulSoup(res.data)
        # Correct values
        err_msg = "There should be a %s section" % form_id
        assert dom.find(id=form_id) is not None, err_msg


    @with_context
    def test_78_cookies_warning(self):
        """Test WEB cookies warning is displayed"""
        # As Anonymous
        res = self.app.get('/', follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "If cookies are not accepted, cookies banner should be shown"
        assert dom.find(id='cookies_warning') is not None, err_msg

        # As user
        self.signin(email=Fixtures.email_addr2, password=Fixtures.password)
        res = self.app.get('/', follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "If cookies are not accepted, cookies banner should be shown"
        assert dom.find(id='cookies_warning') is not None, err_msg
        self.signout()

        # As admin
        self.signin(email=Fixtures.root_addr, password=Fixtures.root_password)
        res = self.app.get('/', follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "If cookies are not accepted, cookies banner should be shown"
        assert dom.find(id='cookies_warning') is not None, err_msg
        self.signout()

    @with_context
    def test_79_cookies_warning2(self):
        """Test WEB cookies warning is hidden"""
        # As Anonymous
        self.app.set_cookie("localhost", "PyBossa_accept_cookies", "Yes")
        res = self.app.get('/', follow_redirects=True, headers={})
        dom = BeautifulSoup(res.data)
        err_msg = "If cookies are not accepted, cookies banner should be hidden"
        assert dom.find(id='cookies_warning') is None, err_msg

        # As user
        self.signin(email=Fixtures.email_addr2, password=Fixtures.password)
        res = self.app.get('/', follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "If cookies are not accepted, cookies banner should be hidden"
        assert dom.find(id='cookies_warning') is None, err_msg
        self.signout()

        # As admin
        self.signin(email=Fixtures.root_addr, password=Fixtures.root_password)
        res = self.app.get('/', follow_redirects=True)
        dom = BeautifulSoup(res.data)
        err_msg = "If cookies are not accepted, cookies banner should be hidden"
        assert dom.find(id='cookies_warning') is None, err_msg
        self.signout()


    @with_context
    def test_user_with_no_more_tasks_find_volunteers(self):
        """Test WEB when a user has contributed to all available tasks, he is
        asked to find new volunteers for a project, if the project is not
        completed yet (overall progress < 100%)"""

        self.register()
        user = User.query.first()
        app = AppFactory.create(owner=user)
        task = TaskFactory.create(app=app)
        taskrun = TaskRunFactory.create(task=task, user=user)
        res = self.app.get('/app/%s/newtask' % app.short_name)

        message = "Sorry, you've contributed to all the tasks for this project, but this project still needs more volunteers, so please spread the word!"
        assert message in res.data
        self.signout()


    @with_context
    def test_user_with_no_more_tasks_find_volunteers_project_completed(self):
        """Test WEB when a user has contributed to all available tasks, he is
        not asked to find new volunteers for a project, if the project is
        completed (overall progress = 100%)"""

        self.register()
        user = User.query.first()
        app = AppFactory.create(owner=user)
        task = TaskFactory.create(app=app, n_answers=1)
        taskrun = TaskRunFactory.create(task=task, user=user)
        res = self.app.get('/app/%s/newtask' % app.short_name)

        assert task.state == 'completed', task.state
        message = "Sorry, you've contributed to all the tasks for this project, but this project still needs more volunteers, so please spread the word!"
        assert message not in res.data
        self.signout()

########NEW FILE########
__FILENAME__ = test_web_module
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
from default import Test, flask_app, with_context
from pybossa.util import get_port
from pybossa.core import url_for_other_page
from mock import patch


class TestWebModule(Test):
    def setUp(self):
        super(TestWebModule, self).setUp()
        with self.flask_app.app_context():
            self.create()

    def test_url_for_other_page(self):
        """Test url_for_other page works."""
        with self.flask_app.test_request_context('/'):
            for i in range(1, 3):
                url = url_for_other_page(i)
                tmp = '/?page=%s' % i
                err_msg = "The page url is not built correctly"
                assert tmp == url, err_msg

    @with_context
    def test_get_port(self):
        """Test get_port works."""
        # Without os.environ
        err_msg = "It should return the default Flask port"
        with patch.dict(flask_app.config, {'PORT': 5000}):
            assert get_port() == 5000, err_msg
        with patch('os.environ.get', return_value='99'):
            err_msg = "The returning port should be 99"
            assert get_port() == 99, err_msg

########NEW FILE########
__FILENAME__ = warm
# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2014 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

#!/usr/bin/env python
import os
import sys
import optparse
import inspect

#import pybossa.model as model
from pybossa.core import create_app

app = create_app()


def warm_cache():
    '''Warm cache'''
    # Disable cache, so we can refresh the data in Redis
    os.environ['PYBOSSA_REDIS_CACHE_DISABLED'] = '1'
    # Cache 3 pages
    apps_cached = []
    pages = range(1, 4)
    with app.app_context():
        import pybossa.cache.apps as cached_apps
        import pybossa.cache.categories as cached_cat
        import pybossa.cache.users as cached_users
        import pybossa.stats as stats

        def warm_app(id, short_name):
            if id not in apps_cached:
                cached_apps.get_app(short_name)
                cached_apps.n_tasks(id)
                n_task_runs = cached_apps.n_task_runs(id)
                cached_apps.overall_progress(id)
                cached_apps.last_activity(id)
                cached_apps.n_completed_tasks(id)
                cached_apps.n_volunteers(id)
                if n_task_runs >= 1000:
                    print "Getting stats for %s as it has %s" % (id, n_task_runs)
                    stats.get_stats(id, app.config.get('GEO'))
                apps_cached.append(id)

        # Cache top apps
        cached_apps.get_featured_front_page()
        apps = cached_apps.get_top()
        for a in apps:
            warm_app(a['id'], a['short_name'])
        for page in pages:
            apps, count = cached_apps.get_featured('featured',
                                                   page,
                                                   app.config['APPS_PER_PAGE'])
            for a in apps:
                warm_app(a['id'], a['short_name'])

        # Categories
        categories = cached_cat.get_used()
        for c in categories:
            for page in pages:
                 apps, count = cached_apps.get(c['short_name'],
                                               page,
                                               app.config['APPS_PER_PAGE'])
                 for a in apps:
                     warm_app(a['id'], a['short_name'])
        # Users
        cached_users.get_top()


## ==================================================
## Misc stuff for setting up a command line interface

def _module_functions(functions):
    local_functions = dict(functions)
    for k,v in local_functions.items():
        if not inspect.isfunction(v) or k.startswith('_'):
            del local_functions[k]
    return local_functions

def _main(functions_or_object):
    isobject = inspect.isclass(functions_or_object)
    if isobject:
        _methods = _object_methods(functions_or_object)
    else:
        _methods = _module_functions(functions_or_object)

    usage = '''%prog {action}

Actions:
    '''
    usage += '\n    '.join(
        [ '%s: %s' % (name, m.__doc__.split('\n')[0] if m.__doc__ else '') for (name,m)
        in sorted(_methods.items()) ])
    parser = optparse.OptionParser(usage)
    # Optional: for a config file
    # parser.add_option('-c', '--config', dest='config',
    #         help='Config file to use.')
    options, args = parser.parse_args()

    if not args or not args[0] in _methods:
        parser.print_help()
        sys.exit(1)

    method = args[0]
    if isobject:
        getattr(functions_or_object(), method)(*args[1:])
    else:
        _methods[method](*args[1:])

__all__ = [ '_main' ]

if __name__ == '__main__':
    _main(locals())

########NEW FILE########
