__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from alembic.config import Config
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
from flask.ext.alembic import FlaskAlembicConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = FlaskAlembicConfig("alembic.ini")

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from flask import current_app
with current_app.app_context():
    # set the database url
    config.set_main_option('sqlalchemy.url', current_app.config.get('SQLALCHEMY_BINDS', {}).get('lastuser', None))
    flask_app = __import__('%s' % (current_app.name), fromlist=[current_app.name])

db_obj_name = config.get_main_option("flask_sqlalchemy")
db_obj = getattr(flask_app, db_obj_name)
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
__FILENAME__ = 11a71745a9a8_referring_user_for_i
"""Referring user for invitees

Revision ID: 11a71745a9a8
Revises: 16f88a0a1ad3
Create Date: 2014-04-15 23:42:38.808138

"""

# revision identifiers, used by Alembic.
revision = '11a71745a9a8'
down_revision = '16f88a0a1ad3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user', sa.Column('referrer_id', sa.Integer(),
        sa.ForeignKey('user.id', name='user_referrer_id_fkey'), nullable=True))


def downgrade():
    op.drop_column('user', 'referrer_id')

########NEW FILE########
__FILENAME__ = 165f20377abe_timestamp_team_membe
"""Timestamp team membership

Revision ID: 165f20377abe
Revises: 35a6ffd7a079
Create Date: 2014-03-25 18:17:30.010140

"""

# revision identifiers, used by Alembic.
revision = '165f20377abe'
down_revision = '35a6ffd7a079'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('team_membership', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column('team_membership', sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.alter_column('team_membership', 'created_at', server_default=None)
    op.alter_column('team_membership', 'updated_at', server_default=None)
    op.create_primary_key('team_membership_pkey', 'team_membership', ['user_id', 'team_id'])


def downgrade():
    op.drop_column('team_membership', 'updated_at')
    op.drop_column('team_membership', 'created_at')

########NEW FILE########
__FILENAME__ = 16f88a0a1ad3_client_ids_for_user_
"""Client ids for user/org/team

Revision ID: 16f88a0a1ad3
Revises: 3a4e0ea70ef
Create Date: 2014-04-13 15:12:17.408052

"""

# revision identifiers, used by Alembic.
revision = '16f88a0a1ad3'
down_revision = '3a4e0ea70ef'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('organization', sa.Column('client_id', sa.Integer(),
        sa.ForeignKey('client.id', name='organization_client_id_fkey'), nullable=True))
    op.add_column('team', sa.Column('client_id', sa.Integer(),
        sa.ForeignKey('client.id', name='team_client_id_fkey'), nullable=True))
    op.add_column('user', sa.Column('client_id', sa.Integer(),
        sa.ForeignKey('client.id', name='user_client_id_fkey'), nullable=True))


def downgrade():
    op.drop_column('user', 'client_id')
    op.drop_column('team', 'client_id')
    op.drop_column('organization', 'client_id')

########NEW FILE########
__FILENAME__ = 184ed1055383_init
"""init

Revision ID: 184ed1055383
Revises: None
Create Date: 2013-04-20 10:15:06.179822

"""

# revision identifiers, used by Alembic.
revision = '184ed1055383'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('userid', sa.String(length=22), nullable=False),
    sa.Column('fullname', sa.Unicode(length=80), nullable=False),
    sa.Column('username', sa.Unicode(length=80), nullable=True),
    sa.Column('pw_hash', sa.String(length=80), nullable=True),
    sa.Column('timezone', sa.Unicode(length=40), nullable=True),
    sa.Column('description', sa.UnicodeText(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('userid'),
    sa.UniqueConstraint('username')
    )
    op.create_table('organization',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('owners_id', sa.Integer(), nullable=True),
    sa.Column('userid', sa.String(length=22), nullable=False),
    sa.Column('name', sa.Unicode(length=80), nullable=True),
    sa.Column('title', sa.Unicode(length=80), nullable=False),
    sa.Column('description', sa.UnicodeText(), nullable=False),
    sa.ForeignKeyConstraint(['owners_id'], ['team.id'], name='fk_organization_owners_id'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    sa.UniqueConstraint('userid')
    )
    op.create_table('smsmessage',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('phone_number', sa.String(length=15), nullable=False),
    sa.Column('transaction_id', sa.Unicode(length=40), nullable=True),
    sa.Column('message', sa.UnicodeText(), nullable=False),
    sa.Column('status', sa.Integer(), nullable=False),
    sa.Column('status_at', sa.DateTime(), nullable=True),
    sa.Column('fail_reason', sa.Unicode(length=25), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('transaction_id')
    )
    op.create_table('client',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=True),
    sa.Column('title', sa.Unicode(length=250), nullable=False),
    sa.Column('description', sa.UnicodeText(), nullable=False),
    sa.Column('website', sa.Unicode(length=250), nullable=False),
    sa.Column('redirect_uri', sa.Unicode(length=250), nullable=True),
    sa.Column('notification_uri', sa.Unicode(length=250), nullable=True),
    sa.Column('iframe_uri', sa.Unicode(length=250), nullable=True),
    sa.Column('resource_uri', sa.Unicode(length=250), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('allow_any_login', sa.Boolean(), nullable=False),
    sa.Column('team_access', sa.Boolean(), nullable=False),
    sa.Column('key', sa.String(length=22), nullable=False),
    sa.Column('secret', sa.String(length=44), nullable=False),
    sa.Column('trusted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_table('permission',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.Unicode(length=80), nullable=False),
    sa.Column('title', sa.Unicode(length=250), nullable=False),
    sa.Column('description', sa.UnicodeText(), nullable=False),
    sa.Column('allusers', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('noticetype',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Unicode(length=80), nullable=False),
    sa.Column('title', sa.Unicode(length=250), nullable=False),
    sa.Column('description', sa.UnicodeText(), nullable=False),
    sa.Column('allusers', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('useremailclaim',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('email', sa.Unicode(length=80), nullable=True),
    sa.Column('verification_code', sa.String(length=44), nullable=False),
    sa.Column('md5sum', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('useroldid',
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('userid', sa.String(length=22), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('userid')
    )
    op.create_table('userphoneclaim',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('phone', sa.Unicode(length=80), nullable=False),
    sa.Column('gets_text', sa.Boolean(), nullable=False),
    sa.Column('verification_code', sa.Unicode(length=4), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('useremail',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('email', sa.Unicode(length=80), nullable=False),
    sa.Column('md5sum', sa.String(length=32), nullable=False),
    sa.Column('primary', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('md5sum')
    )
    op.create_table('userphone',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('primary', sa.Boolean(), nullable=False),
    sa.Column('phone', sa.Unicode(length=80), nullable=False),
    sa.Column('gets_text', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('phone')
    )
    op.create_table('team',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('userid', sa.String(length=22), nullable=False),
    sa.Column('title', sa.Unicode(length=250), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('userid')
    )
    op.create_table('userexternalid',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('service', sa.String(length=20), nullable=False),
    sa.Column('userid', sa.String(length=250), nullable=False),
    sa.Column('username', sa.Unicode(length=80), nullable=True),
    sa.Column('oauth_token', sa.String(length=250), nullable=True),
    sa.Column('oauth_token_secret', sa.String(length=250), nullable=True),
    sa.Column('oauth_token_type', sa.String(length=250), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('service','userid')
    )
    op.create_table('passwordresetrequest',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('reset_code', sa.String(length=44), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('userflashmessage',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('category', sa.Unicode(length=20), nullable=False),
    sa.Column('message', sa.Unicode(length=250), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('authcode',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=44), nullable=False),
    sa.Column('scope', sa.Unicode(length=250), nullable=False),
    sa.Column('redirect_uri', sa.Unicode(length=1024), nullable=False),
    sa.Column('used', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['client.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('team_membership',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint()
    )
    op.create_table('userclientpermissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('permissions', sa.Unicode(length=250), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['client.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id','client_id')
    )
    op.create_table('authtoken',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('token', sa.String(length=22), nullable=False),
    sa.Column('token_type', sa.String(length=250), nullable=False),
    sa.Column('secret', sa.String(length=44), nullable=True),
    sa.Column('algorithm', sa.String(length=20), nullable=True),
    sa.Column('scope', sa.Unicode(length=250), nullable=False),
    sa.Column('validity', sa.Integer(), nullable=False),
    sa.Column('refresh_token', sa.String(length=22), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['client.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('refresh_token'),
    sa.UniqueConstraint('token'),
    sa.UniqueConstraint('user_id','client_id')
    )
    op.create_table('teamclientpermissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('permissions', sa.Unicode(length=250), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['client.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('team_id','client_id')
    )
    op.create_table('resource',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('name', sa.Unicode(length=20), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.Unicode(length=250), nullable=False),
    sa.Column('description', sa.UnicodeText(), nullable=False),
    sa.Column('siteresource', sa.Boolean(), nullable=False),
    sa.Column('trusted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['client.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('clientteamaccess',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=True),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('access_level', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['client.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('resourceaction',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('name', sa.Unicode(length=20), nullable=False),
    sa.Column('resource_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.Unicode(length=250), nullable=False),
    sa.Column('description', sa.UnicodeText(), nullable=False),
    sa.ForeignKeyConstraint(['resource_id'], ['resource.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name','resource_id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('resourceaction')
    op.drop_table('clientteamaccess')
    op.drop_table('resource')
    op.drop_table('teamclientpermissions')
    op.drop_table('authtoken')
    op.drop_table('userclientpermissions')
    op.drop_table('team_membership')
    op.drop_table('authcode')
    op.drop_table('userflashmessage')
    op.drop_table('passwordresetrequest')
    op.drop_table('userexternalid')
    op.drop_table('team')
    op.drop_table('userphone')
    op.drop_table('useremail')
    op.drop_table('userphoneclaim')
    op.drop_table('useroldid')
    op.drop_table('useremailclaim')
    op.drop_table('noticetype')
    op.drop_table('permission')
    op.drop_table('client')
    op.drop_table('smsmessage')
    op.drop_table('organization')
    op.drop_table('user')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 25e7a9839cd4_user_status_flag
"""User status flag

Revision ID: 25e7a9839cd4
Revises: 184ed1055383
Create Date: 2013-04-20 11:38:45.227518

"""

# revision identifiers, used by Alembic.
revision = '25e7a9839cd4'
down_revision = '184ed1055383'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('status', sa.SmallInteger(), nullable=False,
        server_default=sa.text('0')))
    op.alter_column('user', 'status', server_default=None)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'status')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 2dcc6f5ab4cf_one_claim_per_email_
"""One claim per email and phone

Revision ID: 2dcc6f5ab4cf
Revises: 4072c5dbca9f
Create Date: 2014-02-09 03:47:17.404097

"""

# revision identifiers, used by Alembic.
revision = '2dcc6f5ab4cf'
down_revision = '4072c5dbca9f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_unique_constraint('useremailclaim_user_id_email_key', 'useremailclaim', ['user_id', 'email'])
    op.create_unique_constraint('userphoneclaim_user_id_phone_key', 'userphoneclaim', ['user_id', 'phone'])


def downgrade():
    op.drop_constraint('userphoneclaim_user_id_phone_key', 'userphoneclaim', type_='unique')
    op.drop_constraint('useremailclaim_user_id_email_key', 'useremailclaim', type_='unique')

########NEW FILE########
__FILENAME__ = 35a6ffd7a079_restricted_resources
"""Restricted resources

Revision ID: 35a6ffd7a079
Revises: 3b3583fcbaea
Create Date: 2014-03-19 04:55:01.382718

"""

# revision identifiers, used by Alembic.
revision = '35a6ffd7a079'
down_revision = '3b3583fcbaea'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('resource', 'trusted', new_column_name='restricted')


def downgrade():
    op.alter_column('resource', 'restricted', new_column_name='trusted')

########NEW FILE########
__FILENAME__ = 3a4e0ea70ef_user_sessions
"""User sessions

Revision ID: 3a4e0ea70ef
Revises: 165f20377abe
Create Date: 2014-04-10 01:39:00.122310

"""

# revision identifiers, used by Alembic.
revision = '3a4e0ea70ef'
down_revision = '165f20377abe'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('user_session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('buid', sa.Unicode(length=22), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ipaddr', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.Unicode(length=250), nullable=False),
        sa.Column('accessed_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('sudo_enabled_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('buid')
        )
    op.add_column('authcode', sa.Column('session_id', sa.Integer(), sa.ForeignKey('user_session.id'), nullable=True))


def downgrade():
    op.drop_column('authcode', 'session_id')
    op.drop_table('user_session')

########NEW FILE########
__FILENAME__ = 3b3583fcbaea_namespace_column
"""namespace column

Revision ID: 3b3583fcbaea
Revises: 7b0ba76b89e
Create Date: 2013-11-10 00:21:06.881127

"""

# revision identifiers, used by Alembic.
revision = '3b3583fcbaea'
down_revision = '7b0ba76b89e'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import select, bindparam, table, column

from coaster.utils import namespace_from_url


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('client', sa.Column('namespace', sa.Unicode(length=250), nullable=True))
    op.create_unique_constraint('client_namespace_key', 'client', ['namespace'])
    ### end Alembic commands ###

    connection = op.get_bind()
    client = table('client', 
        column('id', sa.Integer),
        column('website', sa.Unicode(250)),
        column('namespace', sa.Unicode(250)))
    results = connection.execute(select([client.c.id, client.c.website]))
    namespaces = []
    namespace_list = []
    for r in results:
        new_namespace = namespace = namespace_from_url(r[1])
        append_count = 0
        while new_namespace in namespace_list:
            append_count = append_count + 1
            new_namespace = "%s%s" % (namespace, append_count)
        namespaces.append({'clientid': r[0], 'namespace': new_namespace})
        namespace_list.append(new_namespace)
    updt_stmt = client.update().where(client.c.id == bindparam('clientid')).values(namespace=bindparam('namespace'))
    connection.execute(updt_stmt, namespaces)

def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('client', 'namespace')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 3e15e2b894d5_longer_scope
"""Longer scope

Revision ID: 3e15e2b894d5
Revises: 2dcc6f5ab4cf
Create Date: 2014-02-10 02:38:16.568657

"""

# revision identifiers, used by Alembic.
revision = '3e15e2b894d5'
down_revision = '2dcc6f5ab4cf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('authcode', 'scope', type_=sa.UnicodeText)
    op.alter_column('authtoken', 'scope', type_=sa.UnicodeText)

def downgrade():
    op.alter_column('authtoken', 'scope', type_=sa.Unicode(250))
    op.alter_column('authcode', 'scope', type_=sa.Unicode(250))

########NEW FILE########
__FILENAME__ = 4072c5dbca9f_email_length
"""Email length

Revision ID: 4072c5dbca9f
Revises: 25e7a9839cd4
Create Date: 2014-02-07 13:12:41.886046

"""

# revision identifiers, used by Alembic.
revision = '4072c5dbca9f'
down_revision = '25e7a9839cd4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('useremail', 'email', type_=sa.Unicode(254))
    op.alter_column('useremailclaim', 'email', type_=sa.Unicode(254))

def downgrade():
    op.alter_column('useremailclaim', 'email', type_=sa.Unicode(80))
    op.alter_column('useremail', 'email', type_=sa.Unicode(80))

########NEW FILE########
__FILENAME__ = 7b0ba76b89e_resource_namespace
"""resource namespace

Revision ID: 7b0ba76b89e
Revises: 3e15e2b894d5
Create Date: 2013-11-08 18:09:33.077996

"""

# revision identifiers, used by Alembic.
revision = '7b0ba76b89e'
down_revision = '3e15e2b894d5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint('resource_name_key','resource')
    op.create_unique_constraint('resource_client_id_name_key', 'resource', ['client_id', 'name'])


def downgrade():
    op.drop_constraint('resource_client_id_name_key','resource')
    op.create_unique_constraint('resource_name_key', 'resource', ['name'])

########NEW FILE########
__FILENAME__ = settings-sample
# -*- coding: utf-8 -*-
from flask import Markup

#: The title of this site
SITE_TITLE = 'Lastuser'

#: Support contact email
SITE_SUPPORT_EMAIL = 'test@example.com'

#: TypeKit code for fonts
TYPEKIT_CODE = ''

#: Google Analytics code UA-XXXXXX-X
GA_CODE = ''

#: Database backend
SQLALCHEMY_BINDS = {
    'lastuser': 'sqlite:///test.db',
    }

#: Cache type
CACHE_TYPE = 'redis'

#: Secret key
SECRET_KEY = 'make this something random'

#: Timezone
TIMEZONE = 'Asia/Calcutta'

#: Reserved usernames
#: Add to this list but do not remove any unless you want to break
#: the website
RESERVED_USERNAMES = set([
    'app',
    'apps',
    'auth',
    'client',
    'confirm',
    'login',
    'logout',
    'new',
    'profile',
    'reset',
    'register',
    'token',
    'organizations',
    'embed',
    'api',
    'static',
    '_baseframe',
    'www',
    'ftp',
    'smtp',
    'imap',
    'pop',
    'pop3',
    'email',
    ])

#: Mail settings
#: MAIL_FAIL_SILENTLY : default True
#: MAIL_SERVER : default 'localhost'
#: MAIL_PORT : default 25
#: MAIL_USE_TLS : default False
#: MAIL_USE_SSL : default False
#: MAIL_USERNAME : default None
#: MAIL_PASSWORD : default None
#: DEFAULT_MAIL_SENDER : default None
MAIL_FAIL_SILENTLY = False
MAIL_SERVER = 'localhost'
DEFAULT_MAIL_SENDER = 'Lastuser <test@example.com>'
MAIL_DEFAULT_SENDER = DEFAULT_MAIL_SENDER  # For new versions of Flask-Mail

#: Logging: recipients of error emails
ADMINS = []

#: Log file
LOGFILE = 'error.log'

#: Use SSL for some URLs
USE_SSL = False

#: Twitter integration
OAUTH_TWITTER_KEY = ''
OAUTH_TWITTER_SECRET = ''

#: GitHub integration
OAUTH_GITHUB_KEY = ''
OAUTH_GITHUB_SECRET = ''

#: Recaptcha for the registration form
RECAPTCHA_USE_SSL = USE_SSL
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_OPTIONS = ''

#: SMS gateways
#: SMSGupShup support is deprecated
SMS_SMSGUPSHUP_MASK = ''
SMS_SMSGUPSHUP_USER = ''
SMS_SMSGUPSHUP_PASS = ''
#: Exotel support is active
SMS_EXOTEL_SID = ''
SMS_EXOTEL_TOKEN = ''
SMS_FROM = ''

#: Messages (text or HTML)
MESSAGE_FOOTER = Markup('Copyright &copy; <a href="http://hasgeek.com/">HasGeek</a>. Powered by <a href="https://github.com/hasgeek/lastuser" title="GitHub project page">Lastuser</a>, open source software from <a href="https://github.com/hasgeek">HasGeek</a>.')
USERNAME_REASON = ''
EMAIL_REASON = 'Please provide an email address to complete your profile'
TIMEZONE_REASON = 'Dates and times will be shown in your preferred timezone'
ORG_NAME_REASON = u"Your company’s name as it will appear in the URL. Letters, numbers and dashes only"
ORG_TITLE_REASON = u"Your organization’s given name, preferably without legal suffixes"
LOGIN_MESSAGE_1 = ""
LOGIN_MESSAGE_2 = ""
SMS_VERIFICATION_TEMPLATE = 'Your verification code is {code}. If you did not request this, please ignore.'
CREATE_ACCOUNT_MESSAGE = u"This account is for you as an individual. We’ll make one for your company later"
LOGOUT_UNAUTHORIZED_MESSAGE = "We detected a possibly unauthorized attempt to log you out. If you really did intend to logout, please click on the logout link again"

########NEW FILE########
__FILENAME__ = testing
# -*- coding: utf-8 -*-
from flask import Markup
from os import environ

#: The title of this site
SITE_TITLE = 'Lastuser'

#: Support contact email
SITE_SUPPORT_EMAIL = 'test@example.com'

#: TypeKit code for fonts
TYPEKIT_CODE = ''

#: Google Analytics code UA-XXXXXX-X
GA_CODE = ''

#: Database backend
SQLALCHEMY_BINDS = {
    'lastuser': environ.get('SQLALCHEMY_DATABASE_URI', 'postgres://:@localhost:5432/lastuser_test_app'),
}
SQLALCHEMY_ECHO = False

#: Cache type
CACHE_TYPE = 'redis'

#: Secret key
SECRET_KEY = 'random_string_here'

#: Timezone
TIMEZONE = 'Asia/Calcutta'

#: Reserved usernames
#: Add to this list but do not remove any unless you want to break
#: the website
RESERVED_USERNAMES = set([
    'app',
    'apps',
    'auth',
    'client',
    'confirm',
    'login',
    'logout',
    'new',
    'profile',
    'reset',
    'register',
    'token',
    'organizations',
    ])

#: Mail settings
#: MAIL_FAIL_SILENTLY : default True
#: MAIL_SERVER : default 'localhost'
#: MAIL_PORT : default 25
#: MAIL_USE_TLS : default False
#: MAIL_USE_SSL : default False
#: MAIL_USERNAME : default None
#: MAIL_PASSWORD : default None
#: DEFAULT_MAIL_SENDER : default None
MAIL_FAIL_SILENTLY = False
MAIL_SERVER = 'localhost'
DEFAULT_MAIL_SENDER = ('Lastuser', 'test@example.com')
MAIL_DEFAULT_SENDER = DEFAULT_MAIL_SENDER  # For new versions of Flask-Mail

#: Logging: recipients of error emails
ADMINS = []

#: Log file
LOGFILE = 'error.log'

#: Use SSL for some URLs
USE_SSL = False

#: Twitter integration
OAUTH_TWITTER_KEY = ''
OAUTH_TWITTER_SECRET = ''

#: GitHub integration
OAUTH_GITHUB_KEY = ''
OAUTH_GITHUB_SECRET = ''

#: Recaptcha for the registration form
RECAPTCHA_USE_SSL = USE_SSL
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_OPTIONS = ''

#: SMS gateways
SMS_SMSGUPSHUP_MASK = ''
SMS_SMSGUPSHUP_USER = ''
SMS_SMSGUPSHUP_PASS = ''

#: Messages (text or HTML)
MESSAGE_FOOTER = Markup('Copyright &copy; <a href="http://hasgeek.com/">HasGeek</a>. Powered by <a href="https://github.com/hasgeek/lastuser" title="GitHub project page">Lastuser</a>, open source software from <a href="https://github.com/hasgeek">HasGeek</a>.')
USERNAME_REASON = ''
EMAIL_REASON = 'Please provide an email address to complete your profile'
BIO_REASON = ''
TIMEZONE_REASON = 'Dates and times will be shown in your preferred timezone'
ORG_NAME_REASON = u"Your company’s name as it will appear in the URL. Letters, numbers and dashes only"
ORG_TITLE_REASON = u"Your organization’s given name, preferably without legal suffixes"
ORG_DESCRIPTION_REASON = u"A few words about your organization (optional). Plain text only"
LOGIN_MESSAGE_1 = ""
LOGIN_MESSAGE_2 = ""

########NEW FILE########
__FILENAME__ = _version
__all__ = ['__version__', '__version_info__']

__version__ = '0.2.0'
__version_info__ = tuple([int(num) if num.isdigit() else num for num in __version__.replace('-', '.', 1).split('.')])

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from sqlalchemy.ext.declarative import declared_attr
from coaster import newid, newsecret

from . import db, BaseMixin
from coaster.sqlalchemy import BaseScopedNameMixin
from .user import User, Organization, Team
from .session import UserSession

__all__ = ['Client', 'UserFlashMessage', 'Resource', 'ResourceAction', 'AuthCode', 'AuthToken',
    'Permission', 'UserClientPermissions', 'TeamClientPermissions', 'NoticeType',
    'CLIENT_TEAM_ACCESS', 'ClientTeamAccess']


class Client(BaseMixin, db.Model):
    """OAuth client applications"""
    __tablename__ = 'client'
    __bind_key__ = 'lastuser'
    #: User who owns this client
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('clients', cascade="all"))
    #: Organization that owns this client. Only one of this or user must be set
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True)
    org = db.relationship(Organization, primaryjoin=org_id == Organization.id,
        backref=db.backref('clients', cascade="all"))
    #: Human-readable title
    title = db.Column(db.Unicode(250), nullable=False)
    #: Long description
    description = db.Column(db.UnicodeText, nullable=False, default=u'')
    #: Website
    website = db.Column(db.Unicode(250), nullable=False)
    #: Redirect URI
    redirect_uri = db.Column(db.Unicode(250), nullable=True, default=u'')
    #: Back-end notification URI
    notification_uri = db.Column(db.Unicode(250), nullable=True, default=u'')
    #: Front-end notification URI
    iframe_uri = db.Column(db.Unicode(250), nullable=True, default=u'')
    #: Resource discovery URI
    resource_uri = db.Column(db.Unicode(250), nullable=True, default=u'')
    #: Active flag
    active = db.Column(db.Boolean, nullable=False, default=True)
    #: Allow anyone to login to this app?
    allow_any_login = db.Column(db.Boolean, nullable=False, default=True)
    #: Team access flag
    team_access = db.Column(db.Boolean, nullable=False, default=False)
    #: OAuth client key/id
    key = db.Column(db.String(22), nullable=False, unique=True, default=newid)
    #: OAuth client secret
    secret = db.Column(db.String(44), nullable=False, default=newsecret)
    #: Trusted flag: trusted clients are authorized to access user data
    #: without user consent, but the user must still login and identify themself.
    #: When a single provider provides multiple services, each can be declared
    #: as a trusted client to provide single sign-in across the services
    trusted = db.Column(db.Boolean, nullable=False, default=False)
    #: Namespace: determines inter-app resource access
    namespace = db.Column(db.Unicode(250), nullable=True, unique=True)

    def __repr__(self):
        return u'<Client "{title}" {key}>'.format(title=self.title, key=self.key)

    def secret_is(self, candidate):
        """
        Check if the provided client secret is valid.
        """
        return self.secret == candidate

    @property
    def owner_title(self):
        """
        Return human-readable owner name.
        """
        if self.user:
            return self.user.pickername
        elif self.org:
            return self.org.pickername
        else:
            raise AttributeError("This client has no owner")

    @property
    def owner(self):
        return self.user or self.org

    def owner_is(self, user):
        if not user:
            return False
        return self.user == user or (self.org and self.org in user.organizations_owned())

    def orgs_with_team_access(self):
        """
        Return a list of organizations that this client has access to the teams of.
        """
        return [cta.org for cta in self.org_team_access if cta.access_level == CLIENT_TEAM_ACCESS.ALL]

    def permissions(self, user, inherited=None):
        perms = super(Client, self).permissions(user, inherited)
        perms.add('view')
        if user and self.owner_is(user):
            perms.add('edit')
            perms.add('delete')
            perms.add('assign-permissions')
            perms.add('new-resource')
        return perms

    @classmethod
    def get(cls, key=None, namespace=None):
        """
        Return a Client identified by its client key or namespace. Only returns active clients.

        :param str key: Client key to lookup
        :param str namespace: Client namespace to lookup
        """
        if not bool(key) ^ bool(namespace):
            raise TypeError("Either key or namespace should be specified")
        if key:
            return cls.query.filter_by(key=key, active=True).one_or_none()
        else:
            return cls.query.filter_by(namespace=namespace, active=True).one_or_none()


class UserFlashMessage(BaseMixin, db.Model):
    """
    Saved messages for a user, to be relayed to trusted clients.
    """
    __tablename__ = 'userflashmessage'
    __bind_key__ = 'lastuser'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref("flashmessages", cascade="delete, delete-orphan"))
    seq = db.Column(db.Integer, default=0, nullable=False)
    category = db.Column(db.Unicode(20), nullable=False)
    message = db.Column(db.Unicode(250), nullable=False)


class Resource(BaseScopedNameMixin, db.Model):
    """
    Resources are provided by client applications. Other client applications
    can request access to user data at resource servers by providing the
    `name` as part of the requested `scope`.
    """
    __tablename__ = 'resource'
    __bind_key__ = 'lastuser'
    # Resource names are unique across client apps
    name = db.Column(db.Unicode(20), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship(Client, primaryjoin=client_id == Client.id,
        backref=db.backref('resources', cascade="all, delete-orphan"))
    parent = db.synonym('client')
    title = db.Column(db.Unicode(250), nullable=False)
    description = db.Column(db.UnicodeText, default=u'', nullable=False)
    siteresource = db.Column(db.Boolean, default=False, nullable=False)
    restricted = db.Column(db.Boolean, default=False, nullable=False)
    __table_args__ = (db.UniqueConstraint('client_id', 'name', name='resource_client_id_name_key'),)

    def permissions(self, user, inherited=None):
        perms = super(Resource, self).permissions(user, inherited)
        if user and self.client.owner_is(user):
            perms.add('edit')
            perms.add('delete')
            perms.add('new-action')
        return perms

    @classmethod
    def get(cls, name, client=None, namespace=None):
        """
        Return a Resource with the given name.

        :param str name: Name of the resource.
        """
        if not bool(client) ^ bool(namespace):
            raise TypeError("Either client or namespace should be specified")

        if client:
            return cls.query.filter_by(name=name, client=client).one_or_none()
        else:
            return cls.query.filter_by(name=name).join(Client).filter(Client.namespace == namespace).one_or_none()

    def get_action(self, name):
        """
        Return a ResourceAction on this Resource with the given name.

        :param str name: Name of the action
        """
        return ResourceAction.get(name=name, resource=self)


class ResourceAction(BaseMixin, db.Model):
    """
    Actions that can be performed on resources. There should always be at minimum
    a 'read' action.
    """
    __tablename__ = 'resourceaction'
    __bind_key__ = 'lastuser'
    name = db.Column(db.Unicode(20), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    resource = db.relationship(Resource, primaryjoin=resource_id == Resource.id,
        backref=db.backref('actions', cascade="all, delete-orphan"))
    title = db.Column(db.Unicode(250), nullable=False)
    description = db.Column(db.UnicodeText, default=u'', nullable=False)

    # Action names are unique per client app
    __table_args__ = (db.UniqueConstraint("name", "resource_id"), {})

    def permissions(self, user, inherited=None):
        perms = super(ResourceAction, self).permissions(user, inherited)
        if user and self.resource.client.owner_is(user):
            perms.add('edit')
            perms.add('delete')
        return perms

    @classmethod
    def get(cls, name, resource):
        """
        Return a ResourceAction on the specified resource with the specified name.

        :param str name: Name of the action
        :param Resource resource: Resource on which this action exists
        """
        return cls.query.filter_by(name=name, resource=resource).one_or_none()


class ScopeMixin(object):
    @declared_attr
    def _scope(self):
        return db.Column('scope', db.UnicodeText, nullable=False)

    def _scope_get(self):
        return sorted([t.strip() for t in self._scope.replace('\r', ' ').replace('\n', ' ').split(u' ') if t])

    def _scope_set(self, value):
        if isinstance(value, basestring):
            value = [value]
        self._scope = u' '.join(sorted([t.strip() for t in value if t]))

    @declared_attr
    def scope(self):
        return db.synonym('_scope', descriptor=property(self._scope_get, self._scope_set))

    def add_scope(self, additional):
        if isinstance(additional, basestring):
            additional = [additional]
        self.scope = list(set(self.scope).union(set(additional)))


class AuthCode(ScopeMixin, BaseMixin, db.Model):
    """Short-lived authorization tokens."""
    __tablename__ = 'authcode'
    __bind_key__ = 'lastuser'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship(Client, primaryjoin=client_id == Client.id,
        backref=db.backref("authcodes", cascade="all, delete-orphan"))
    session_id = db.Column(None, db.ForeignKey('user_session.id'), nullable=True)
    session = db.relationship(UserSession)
    code = db.Column(db.String(44), default=newsecret, nullable=False)
    redirect_uri = db.Column(db.Unicode(1024), nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)

    def is_valid(self):
        # Time limit: 3 minutes. Should be reasonable enough to load a page
        # on a slow mobile connection, without keeping the code valid too long
        return not self.used and self.created_at >= datetime.utcnow() - timedelta(minutes=3)


class AuthToken(ScopeMixin, BaseMixin, db.Model):
    """Access tokens for access to data."""
    __tablename__ = 'authtoken'
    __bind_key__ = 'lastuser'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null for client-only tokens
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref("authtokens", cascade="all, delete-orphan"))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship(Client, primaryjoin=client_id == Client.id,
        backref=db.backref("authtokens", cascade="all, delete-orphan"))
    token = db.Column(db.String(22), default=newid, nullable=False, unique=True)
    token_type = db.Column(db.String(250), default='bearer', nullable=False)  # 'bearer', 'mac' or a URL
    secret = db.Column(db.String(44), nullable=True)
    _algorithm = db.Column('algorithm', db.String(20), nullable=True)
    validity = db.Column(db.Integer, nullable=False, default=0)  # Validity period in seconds
    refresh_token = db.Column(db.String(22), nullable=True, unique=True)

    # Only one authtoken per user and client. Add to scope as needed
    __table_args__ = (db.UniqueConstraint("user_id", "client_id"), {})

    def __init__(self, **kwargs):
        super(AuthToken, self).__init__(**kwargs)
        self.token = newid()
        if self.user:
            self.refresh_token = newid()
        self.secret = newsecret()

    def __repr__(self):
        return u'<AuthToken {token} of {client} {user}>'.format(
            token=self.token, client=repr(self.client)[1:-1], user=repr(self.user)[1:-1])

    def refresh(self):
        """
        Create a new token while retaining the refresh token.
        """
        if self.refresh_token is not None:
            self.token = newid()
            self.secret = newsecret()

    @property
    def algorithm(self):
        return self._algorithm

    @algorithm.setter
    def algorithm(self, value):
        if value is None:
            self._algorithm = None
            self.secret = None
        elif value in ['hmac-sha-1', 'hmac-sha-256']:
            self._algorithm = value
        else:
            raise ValueError(u"Unrecognized algorithm ‘{value}’".format(value=value))

    algorithm = db.synonym('_algorithm', descriptor=algorithm)

    def is_valid(self):
        if self.validity == 0:
            return True  # This token is perpetually valid
        now = datetime.utcnow()
        if self.created_at < now - timedelta(seconds=self.validity):
            return False
        return True

    @classmethod
    def migrate_user(cls, olduser, newuser):
        if not olduser or not newuser:
            return  # Don't mess with client-only tokens
        oldtokens = cls.query.filter_by(user=olduser).all()
        newtokens = {}  # Client: token mapping
        for token in cls.query.filter_by(user=newuser).all():
            newtokens.setdefault(token.client_id, []).append(token)

        for token in oldtokens:
            merge_performed = False
            if token.client_id in newtokens:
                for newtoken in newtokens[token.client_id]:
                    if newtoken.user == newuser:
                        # There's another token for  newuser with the same client.
                        # Just extend the scope there
                        newtoken.scope = set(newtoken.scope) | set(token.scope)
                        db.session.delete(token)
                        merge_performed = True
                        break
            if merge_performed is False:
                token.user = newuser  # Reassign this token to newuser

    @classmethod
    def get(cls, token):
        """
        Return an AuthToken with the matching token.

        :param str token: Token to lookup
        """
        return cls.query.filter_by(token=token).one_or_none()

    @classmethod
    def all(cls, users):
        """
        Return all AuthToken for the specified users.
        """
        if len(users) == 0:
            return []
        elif len(users) == 1:
            return cls.query.filter_by(user=users[0]).all()
        else:
            return cls.query.filter(AuthToken.user_id.in_([u.id for u in users])).all()


class Permission(BaseMixin, db.Model):
    __tablename__ = 'permission'
    __bind_key__ = 'lastuser'
    #: User who created this permission
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('permissions_created', cascade="all, delete-orphan"))
    #: Organization which created this permission
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True)
    org = db.relationship(Organization, primaryjoin=org_id == Organization.id,
        backref=db.backref('permissions_created', cascade="all, delete-orphan"))
    #: Name token
    name = db.Column(db.Unicode(80), nullable=False)
    #: Human-friendly title
    title = db.Column(db.Unicode(250), nullable=False)
    #: Description of what this permission is about
    description = db.Column(db.UnicodeText, default=u'', nullable=False)
    #: Is this permission available to all users and client apps?
    allusers = db.Column(db.Boolean, default=False, nullable=False)

    def owner_is(self, user):
        return user is not None and self.user == user or (self.org and self.org in user.organizations_owned())

    @property
    def owner_title(self):
        if self.user:
            return self.user.pickername
        else:
            return self.org.pickername

    def permissions(self, user, inherited=None):
        perms = super(Permission, self).permissions(user, inherited)
        if user and self.owner_is(user):
            perms.add('edit')
            perms.add('delete')
        return perms

    @classmethod
    def get(cls, name, user=None, org=None, allusers=False):
        """
        Get a permission with the given name and owned by the given user or org,
        or a permission available to all users.

        :param str name: Name of the permission
        :param User user: User who owns this permission
        :param Organization org: Organization which owns this permission
        :param bool allusers: Whether resources that belong to all users should be returned

        One of ``user`` and ``org`` must be specified, unless ``allusers`` is ``True``.
        """
        if allusers:
            return cls.query.filter_by(name=name, allusers=True).one_or_none()
        else:
            if not bool(user) ^ bool(org):
                raise TypeError("Either user or org should be specified")
            if user is not None:
                return cls.query.filter_by(name=name, user=user).one_or_none()
            else:
                return cls.query.filter_by(name=name, org=org).one_or_none()


# This model's name is in plural because it defines multiple permissions within each instance
class UserClientPermissions(BaseMixin, db.Model):
    __tablename__ = 'userclientpermissions'
    __bind_key__ = 'lastuser'
    #: User who has these permissions
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('client_permissions', cascade='all, delete-orphan'))
    #: Client app they are assigned on
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship(Client, primaryjoin=client_id == Client.id,
        backref=db.backref('user_permissions', cascade="all, delete-orphan"))
    #: The permissions as a string of tokens
    access_permissions = db.Column('permissions', db.Unicode(250), default=u'', nullable=False)

    # Only one assignment per user and client
    __table_args__ = (db.UniqueConstraint("user_id", "client_id"), {})

    # Used by lastuser_ui/client_info.html
    @property
    def pickername(self):
        return self.user.pickername

    # Used by lastuser_ui/client_info.html for url_for
    @property
    def userid(self):
        return self.user.userid

    @classmethod
    def migrate_user(cls, olduser, newuser):
        for operm in olduser.client_permissions:
            merge_performed = False
            for nperm in newuser.client_permissions:
                if nperm.client == operm.client:
                    # Merge permission strings
                    tokens = set(operm.access_permissions.split(' '))
                    tokens.update(set(nperm.access_permissions.split(' ')))
                    if u' ' in tokens:
                        tokens.remove(u' ')
                    nperm.access_permissions = u' '.join(sorted(tokens))
                    db.session.delete(operm)
                    merge_performed = True
            if not merge_performed:
                operm.user = newuser


# This model's name is in plural because it defines multiple permissions within each instance
class TeamClientPermissions(BaseMixin, db.Model):
    __tablename__ = 'teamclientpermissions'
    __bind_key__ = 'lastuser'
    #: Team which has these permissions
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team = db.relationship(Team, primaryjoin=team_id == Team.id,
        backref=db.backref('client_permissions', cascade='all, delete-orphan'))
    #: Client app they are assigned on
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship(Client, primaryjoin=client_id == Client.id,
        backref=db.backref('team_permissions', cascade="all, delete-orphan"))
    #: The permissions as a string of tokens
    access_permissions = db.Column('permissions', db.Unicode(250), default=u'', nullable=False)

    # Only one assignment per team and client
    __table_args__ = (db.UniqueConstraint("team_id", "client_id"), {})

    # Used by lastuser_ui/client_info.html
    @property
    def pickername(self):
        return self.team.pickername

    # Used by lastuser_ui/client_info.html for url_for
    @property
    def userid(self):
        return self.team.userid


class CLIENT_TEAM_ACCESS:
    NONE = 0     # The default if there's no connecting object
    ALL = 1      # All teams can be seen
    PARTIAL = 2  # TODO: Not supported yet


class ClientTeamAccess(BaseMixin, db.Model):
    __tablename__ = 'clientteamaccess'
    __bind_key__ = 'lastuser'
    #: Organization whose teams are exposed to the client app
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True)
    org = db.relationship(Organization, primaryjoin=org_id == Organization.id,
        backref=db.backref('client_team_access', cascade="all, delete-orphan"))
    #: Client app they are exposed to
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship(Client, primaryjoin=client_id == Client.id,
        backref=db.backref('org_team_access', cascade="all, delete-orphan"))
    access_level = db.Column(db.Integer, default=CLIENT_TEAM_ACCESS.NONE, nullable=False)


class NoticeType(BaseMixin, db.Model):
    __tablename__ = 'noticetype'
    __bind_key__ = 'lastuser'
    #: User who created this notice type
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('noticetypes_created', cascade="all, delete-orphan"))
    #: Name token
    name = db.Column(db.Unicode(80), nullable=False)
    #: Human-friendly title
    title = db.Column(db.Unicode(250), nullable=False)
    #: Description of what this notice type is about
    description = db.Column(db.UnicodeText, default=u'', nullable=False)
    #: Is this notice type available to all users and client apps?
    allusers = db.Column(db.Boolean, default=False, nullable=False)

########NEW FILE########
__FILENAME__ = notice
# -*- coding: utf-8 -*-

from . import db, BaseMixin

__all__ = ['SMSMessage', 'SMS_STATUS']


# --- Flags -------------------------------------------------------------------

class SMS_STATUS:
    QUEUED = 0
    PENDING = 1
    DELIVERED = 2
    FAILED = 3
    UNKNOWN = 4


# --- Channels ----------------------------------------------------------------

class Channel(object):
    delivery_flag = False
    bounce_flag = False
    read_flag = False
    channel_type = 0


class ChannelBrowser(Channel):
    delivery_flag = True
    bounce_flag = False
    read_flag = True
    channel_type = 1


class ChannelEmail(Channel):
    delivery_flag = False
    bounce_flag = True
    read_flag = False
    channel_type = 2


class ChannelTwitter(Channel):
    delivery_flag = True
    bounce_flag = True
    read_flag = False
    channel_type = 3


class ChannelSMS(Channel):
    delivery_flag = True
    bounce_flag = True
    read_flag = False
    channel_type = 4


# --- Models ------------------------------------------------------------------

class SMSMessage(BaseMixin, db.Model):
    __tablename__ = 'smsmessage'
    __bind_key__ = 'lastuser'
    # Phone number that the message was sent to
    phone_number = db.Column(db.String(15), nullable=False)
    transaction_id = db.Column(db.Unicode(40), unique=True, nullable=True)
    # The message itself
    message = db.Column(db.UnicodeText, nullable=False)
    # Flags
    status = db.Column(db.Integer, default=0, nullable=False)
    status_at = db.Column(db.DateTime, nullable=True)
    fail_reason = db.Column(db.Unicode(25), nullable=True)

########NEW FILE########
__FILENAME__ = session
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from werkzeug import cached_property
from werkzeug.useragents import UserAgent
from flask import request
from coaster.utils import buid as make_buid
from . import db, BaseMixin
from .user import User
from ..signals import session_revoked

__all__ = ['UserSession']


class UserSession(BaseMixin, db.Model):
    __tablename__ = 'user_session'
    __bind_key__ = 'lastuser'

    buid = db.Column(db.Unicode(22), nullable=False, unique=True, default=make_buid)
    sessionid = db.synonym('buid')

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, backref=db.backref('sessions', cascade='all, delete-orphan', lazy='dynamic'))

    ipaddr = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.Unicode(250), nullable=False)

    accessed_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    sudo_enabled_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())

    def __init__(self, **kwargs):
        super(UserSession, self).__init__(**kwargs)
        if not self.buid:
            self.buid = make_buid()

    def access(self, api=False):
        """
        Mark as a session as currently active.

        :param bool api: Is this an API access call? Don't save the IP address and browser then.
        """
        # `accessed_at` will be different from the automatic `updated_at` in one
        # crucial context: when the session was revoked remotely
        self.accessed_at = datetime.utcnow()
        if not api:
            self.ipaddr = request.environ.get('REMOTE_ADDR', u'')
            self.user_agent = unicode(request.user_agent.string[:250]) or u''

    @cached_property
    def ua(self):
        return UserAgent(self.user_agent)

    @property
    def has_sudo(self):
        return self.sudo_enabled_at > datetime.utcnow() - timedelta(hours=1)

    def set_sudo(self):
        self.sudo_enabled_at = datetime.utcnow()

    def revoke(self):
        if not self.revoked_at:
            self.revoked_at = datetime.utcnow()
            session_revoked.send(self)

    @classmethod
    def get(cls, buid):
        return cls.query.filter_by(buid=buid).one_or_none()

    @classmethod
    def authenticate(cls, buid):
        return cls.query.filter(
            # Session key must match.
            cls.buid == buid,
            # Sessions are valid for two weeks...
            cls.accessed_at > datetime.utcnow() - timedelta(days=14),
            # ...unless explicitly revoked (or user logged out)
            cls.revoked_at == None).one_or_none()


# Patch a retriever into the User class. This could be placed in the
# UserSession.user relationship's backref with a custom primaryjoin
# clause and explicit foreign_keys, but we're not sure if we can
# put the datetime.utcnow() in there too.
def active_sessions(self):
    return self.sessions.filter(
        UserSession.accessed_at > datetime.utcnow() - timedelta(days=14),
        UserSession.revoked_at == None).all()

User.active_sessions = active_sessions

########NEW FILE########
__FILENAME__ = user
# -*- coding: utf-8 -*-

from hashlib import md5
from werkzeug import check_password_hash, cached_property
import bcrypt
from sqlalchemy import or_
from sqlalchemy.orm import defer, deferred
from sqlalchemy.ext.hybrid import hybrid_property
from coaster import newid, newsecret, newpin, valid_username
from coaster.sqlalchemy import Query as CoasterQuery, timestamp_columns

from . import db, TimestampMixin, BaseMixin


__all__ = ['User', 'UserEmail', 'UserEmailClaim', 'PasswordResetRequest', 'UserExternalId',
           'UserPhone', 'UserPhoneClaim', 'Team', 'Organization', 'UserOldId', 'USER_STATUS']


class USER_STATUS:
    ACTIVE = 0
    SUSPENDED = 1
    MERGED = 2


class User(BaseMixin, db.Model):
    __tablename__ = 'user'
    __bind_key__ = 'lastuser'
    userid = db.Column(db.String(22), unique=True, nullable=False, default=newid)
    fullname = db.Column(db.Unicode(80), default=u'', nullable=False)
    _username = db.Column('username', db.Unicode(80), unique=True, nullable=True)
    pw_hash = db.Column(db.String(80), nullable=True)
    timezone = db.Column(db.Unicode(40), nullable=True)
    #: Deprecated, but column preserved for existing data until migration
    description = deferred(db.Column(db.UnicodeText, default=u'', nullable=False))
    status = db.Column(db.SmallInteger, nullable=False, default=USER_STATUS.ACTIVE)

    #: Client id that created this account
    client_id = db.Column(None, db.ForeignKey('client.id',
        use_alter=True, name='user_client_id_fkey'), nullable=True)
    #: If this user was created by a client app via the API, record it here
    client = db.relationship('Client', foreign_keys=[client_id])  # No backref or cascade

    #: Id of user who invited this user
    referrer_id = db.Column(None, db.ForeignKey('user.id',
        use_alter=True, name='user_referrer_id_fkey'), nullable=True)
    #: User who invited this user
    referrer = db.relationship('User', foreign_keys=[referrer_id])

    _defercols = [
        defer('created_at'),
        defer('updated_at'),
        defer('pw_hash'),
        defer('timezone'),
        ]

    def __init__(self, password=None, **kwargs):
        self.userid = newid()
        self.password = password
        super(User, self).__init__(**kwargs)

    @property
    def is_active(self):
        return self.status == USER_STATUS.ACTIVE

    def merged_user(self):
        if self.status == USER_STATUS.MERGED:
            return UserOldId.get(self.userid).user
        else:
            return self

    def _set_password(self, password):
        if password is None:
            self.pw_hash = None
        else:
            self.pw_hash = bcrypt.hashpw(
                password.encode('utf-8') if isinstance(password, unicode) else password,
                bcrypt.gensalt())

    #: Write-only property (passwords cannot be read back in plain text)
    password = property(fset=_set_password)

    #: Username (may be null)
    @hybrid_property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        if not value:
            self._username = None
        elif self.is_valid_username(value):
            self._username = value

    def is_valid_username(self, value):
        if not valid_username(value):
            return False
        existing = User.query.filter(db.or_(
            User.username == value,
            User.userid == value)).first()  # Avoid User.get to skip status check
        if existing and existing.id != self.id:
            return False
        existing = Organization.get(name=value)
        if existing:
            return False
        return True

    def password_is(self, password):
        if self.pw_hash is None:
            return False
        if self.pw_hash.startswith('sha1$'):
            return check_password_hash(self.pw_hash, password)
        else:
            return bcrypt.hashpw(
                password.encode('utf-8') if isinstance(password, unicode) else password,
                self.pw_hash) == self.pw_hash

    def __repr__(self):
        return u'<User {username} "{fullname}">'.format(username=self.username or self.userid,
            fullname=self.fullname)

    def profileid(self):
        if self.username:
            return self.username
        else:
            return self.userid

    def displayname(self):
        return self.fullname or self.username or self.userid

    @property
    def pickername(self):
        if self.username:
            return u'{fullname} (~{username})'.format(fullname=self.fullname, username=self.username)
        else:
            return self.fullname

    def add_email(self, email, primary=False):
        if primary:
            for emailob in self.emails:
                if emailob.primary:
                    emailob.primary = False
        useremail = UserEmail(user=self, email=email, primary=primary)
        db.session.add(useremail)
        return useremail

    def del_email(self, email):
        setprimary = False
        useremail = UserEmail.query.filter_by(user=self, email=email).first()
        if useremail:
            if useremail.primary:
                setprimary = True
            db.session.delete(useremail)
        if setprimary:
            for emailob in UserEmail.query.filter_by(user=self).all():
                if emailob is not useremail:
                    emailob.primary = True
                    break

    @cached_property
    def email(self):
        """
        Returns primary email address for user.
        """
        # Look for a primary address
        useremail = UserEmail.query.filter_by(user_id=self.id, primary=True).first()
        if useremail:
            return useremail
        # No primary? Maybe there's one that's not set as primary?
        useremail = UserEmail.query.filter_by(user_id=self.id).first()
        if useremail:
            # XXX: Mark at primary. This may or may not be saved depending on
            # whether the request ended in a database commit.
            useremail.primary = True
            return useremail
        # This user has no email address. Return a blank string instead of None
        # to support the common use case, where the caller will use unicode(user.email)
        # to get the email address as a string.
        return u''

    @cached_property
    def phone(self):
        """
        Returns primary phone number for user.
        """
        # Look for a primary address
        userphone = UserPhone.query.filter_by(user=self, primary=True).first()
        if userphone:
            return userphone
        # No primary? Maybe there's one that's not set as primary?
        userphone = UserPhone.query.filter_by(user=self).first()
        if userphone:
            # XXX: Mark at primary. This may or may not be saved depending on
            # whether the request ended in a database commit.
            userphone.primary = True
            return userphone
        # This user has no phone number. Return a blank string instead of None
        # to support the common use case, where the caller will use unicode(user.phone)
        # to get the phone number as a string.
        return u''

    def organizations(self):
        """
        Return the organizations this user is a member of.
        """
        return sorted(set([team.org for team in self.teams]), key=lambda o: o.title)

    def organizations_owned(self):
        """
        Return the organizations this user is an owner of.
        """
        return sorted(set([team.org for team in self.teams if team.org.owners == team]),
            key=lambda o: o.title)

    def organizations_owned_ids(self):
        """
        Return the database ids of the organizations this user is an owner of. This is used
        for database queries.
        """
        return list(set([team.org.id for team in self.teams if team.org.owners == team]))

    def is_profile_complete(self):
        """
        Return True if profile is complete (fullname, username and email are present), False
        otherwise.
        """
        return bool(self.fullname and self.username and self.email)

    def available_permissions(self):
        """
        Return all permission objects available to this user
        (either owned by user or available to all users).
        """
        from .client import Permission
        return Permission.query.filter(
            db.or_(Permission.allusers == True, Permission.user == self)
            ).order_by(Permission.name).all()

    def clients_with_team_access(self):
        """
        Return a list of clients with access to the user's organizations' teams.
        """
        return [token.client for token in self.authtokens if 'teams' in token.scope]


    @classmethod
    def get(cls, username=None, userid=None, defercols=False):
        """
        Return a User with the given username or userid.

        :param str username: Username to lookup
        :param str userid: Userid to lookup
        :param bool defercols: Defer loading non-critical columns
        """
        if not bool(username) ^ bool(userid):
            raise TypeError("Either username or userid should be specified")

        if userid:
            query = cls.query.filter_by(userid=userid)
        else:
            query = cls.query.filter_by(username=username)
        if defercols:
            query = query.options(*cls._defercols)
        user = query.one_or_none()
        if user and user.status == USER_STATUS.MERGED:
            user = user.merged_user()
        if user and user.is_active:
            return user

    @classmethod
    def all(cls, userids=None, usernames=None, defercols=False):
        """
        Return all matching users.

        :param list userids: Userids to look up
        :param list usernames: Usernames to look up
        :param bool defercols: Defer loading non-critical columns
        """
        users = set()
        if userids:
            query = cls.query.filter(cls.userid.in_(userids))
            if defercols:
                query = query.options(*cls._defercols)
            for user in query.all():
                user = user.merged_user()
                if user.is_active:
                    users.add(user)
        return list(users)

    @classmethod
    def autocomplete(cls, query):
        """
        Return users whose names begin with the query, for autocomplete widgets.
        Looks up users by fullname, username, external ids and email addresses.

        :param str query: Letters to start matching with
        """
        # Escape the '%' and '_' wildcards in SQL LIKE clauses.
        # Some SQL dialects respond to '[' and ']', so remove them.
        query = query.replace(u'%', ur'\%').replace(u'_', ur'\_').replace(u'[', u'').replace(u']', u'') + u'%'
        # Use User._username since 'username' is a hybrid property that checks for validity
        # before passing on to _username, the actual column name on the model.
        # We convert to lowercase and use the LIKE operator since ILIKE isn't standard.
        if not query:
            return []
        users = cls.query.filter(cls.status == USER_STATUS.ACTIVE,
            or_(  # Match against userid (exact value only), fullname or username, case insensitive
                cls.userid == query[:-1],
                db.func.lower(cls.fullname).like(db.func.lower(query)),
                db.func.lower(cls._username).like(db.func.lower(query))
                )
            ).options(*cls._defercols).limit(100).all()  # Limit to 100 results
        if query.startswith('@'):
            # Add Twitter/GitHub accounts to the head of results
            # TODO: Move this query to a login provider class method
            users = cls.query.filter(cls.status == USER_STATUS.ACTIVE, cls.id.in_(
                db.session.query(UserExternalId.user_id).filter(
                    UserExternalId.service.in_([u'twitter', u'github']),
                    db.func.lower(UserExternalId.username).like(db.func.lower(query[1:]))
                ).subquery())).options(*cls._defercols).limit(100).all() + users
        elif '@' in query:
            users = cls.query.filter(cls.status == USER_STATUS.ACTIVE, cls.id.in_(
                db.session.query(UserEmail.user_id).filter(
                    db.func.lower(UserEmail.email).like(db.func.lower(query))
                ).subquery())).options(*cls._defercols).limit(100).all() + users
        return users


class UserOldId(TimestampMixin, db.Model):
    __tablename__ = 'useroldid'
    __bind_key__ = 'lastuser'
    query_class = CoasterQuery

    userid = db.Column(db.String(22), nullable=False, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('oldids', cascade="all, delete-orphan"))

    def __repr__(self):
        return u'<UserOldId {userid} of {user}'.format(
            userid=self.userid, user=repr(self.user)[1:-1])

    @classmethod
    def get(cls, userid):
        return cls.query.filter_by(userid=userid).one_or_none()


class UserEmail(BaseMixin, db.Model):
    __tablename__ = 'useremail'
    __bind_key__ = 'lastuser'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('emails', cascade="all, delete-orphan"))
    _email = db.Column('email', db.Unicode(254), unique=True, nullable=False)
    md5sum = db.Column(db.String(32), unique=True, nullable=False)
    primary = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, email, **kwargs):
        super(UserEmail, self).__init__(**kwargs)
        self._email = email
        self.md5sum = md5(self._email).hexdigest()

    @hybrid_property
    def email(self):
        return self._email

    #: Make email immutable. There is no setter for email.
    email = db.synonym('_email', descriptor=email)

    def __repr__(self):
        return u'<UserEmail {email} of {user}>'.format(
            email=self.email, user=repr(self.user)[1:-1])

    def __unicode__(self):
        return unicode(self.email)

    def __str__(self):
        return str(self.__unicode__())

    @classmethod
    def get(cls, email=None, md5sum=None):
        """
        Return a UserEmail with matching email or md5sum.

        :param str email: Email address to lookup
        :param str md5sum: md5sum of email address to lookup
        """
        if not bool(email) ^ bool(md5sum):
            raise TypeError("Either email or md5sum should be specified")

        if email:
            return cls.query.filter(cls.email.in_([email, email.lower()])).one_or_none()
        else:
            return cls.query.filter_by(md5sum=md5sum).one_or_none()


class UserEmailClaim(BaseMixin, db.Model):
    __tablename__ = 'useremailclaim'
    __bind_key__ = 'lastuser'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('emailclaims', cascade="all, delete-orphan"))
    _email = db.Column('email', db.Unicode(254), nullable=True)
    verification_code = db.Column(db.String(44), nullable=False, default=newsecret)
    md5sum = db.Column(db.String(32), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'email'),)

    def __init__(self, email, **kwargs):
        super(UserEmailClaim, self).__init__(**kwargs)
        self.verification_code = newsecret()
        self._email = email
        self.md5sum = md5(self._email).hexdigest()

    @hybrid_property
    def email(self):
        return self._email

    #: Make email immutable. There is no setter for email.
    email = db.synonym('_email', descriptor=email)

    def __repr__(self):
        return u'<UserEmailClaim {email} of {user}>'.format(
            email=self.email, user=repr(self.user)[1:-1])

    def __unicode__(self):
        return unicode(self.email)

    def __str__(self):
        return str(self.__unicode__())

    def permissions(self, user, inherited=None):
        perms = super(UserEmailClaim, self).permissions(user, inherited)
        if user and user == self.user:
            perms.add('verify')
        return perms

    @classmethod
    def get(cls, email, user):
        """
        Return a UserEmailClaim with matching email address for the given user.

        :param str email: Email address to lookup
        :param User user: User who claimed this email address
        """
        return cls.query.filter(UserEmailClaim.email.in_([email, email.lower()])).filter_by(user=user).one_or_none()

    @classmethod
    def all(cls, email):
        """
        Return all UserEmailClaim instances with matching email address.

        :param str email: Email address to lookup
        """
        return cls.query.filter(UserEmailClaim.email.in_([email, email.lower()])).order_by(cls.user_id).all()


class UserPhone(BaseMixin, db.Model):
    __tablename__ = 'userphone'
    __bind_key__ = 'lastuser'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('phones', cascade="all, delete-orphan"))
    primary = db.Column(db.Boolean, nullable=False, default=False)
    _phone = db.Column('phone', db.Unicode(80), unique=True, nullable=False)
    gets_text = db.Column(db.Boolean, nullable=False, default=True)

    def __init__(self, phone, **kwargs):
        super(UserPhone, self).__init__(**kwargs)
        self._phone = phone

    @hybrid_property
    def phone(self):
        return self._phone

    phone = db.synonym('_phone', descriptor=phone)

    def __repr__(self):
        return u'<UserPhone {phone} of {user}>'.format(
            phone=self.phone, user=repr(self.user)[1:-1])

    def __unicode__(self):
        return unicode(self.phone)

    def __str__(self):
        return str(self.__unicode__())

    @classmethod
    def get(cls, phone):
        """
        Return a UserPhone with matching phone number.

        :param str phone: Phone number to lookup (must be an exact match)
        """
        return cls.query.filter_by(phone=phone).one_or_none()


class UserPhoneClaim(BaseMixin, db.Model):
    __tablename__ = 'userphoneclaim'
    __bind_key__ = 'lastuser'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('phoneclaims', cascade="all, delete-orphan"))
    _phone = db.Column('phone', db.Unicode(80), nullable=False)
    gets_text = db.Column(db.Boolean, nullable=False, default=True)
    verification_code = db.Column(db.Unicode(4), nullable=False, default=newpin)

    __table_args__ = (db.UniqueConstraint('user_id', 'phone'),)

    def __init__(self, phone, **kwargs):
        super(UserPhoneClaim, self).__init__(**kwargs)
        self.verification_code = newpin()
        self._phone = phone

    @hybrid_property
    def phone(self):
        return self._phone

    phone = db.synonym('_phone', descriptor=phone)

    def __repr__(self):
        return u'<UserPhoneClaim {phone} of {user}>'.format(
            phone=self.phone, user=repr(self.user)[1:-1])

    def __unicode__(self):
        return unicode(self.phone)

    def __str__(self):
        return str(self.__unicode__())

    def permissions(self, user, inherited=None):
        perms = super(UserPhoneClaim, self).permissions(user, inherited)
        if user and user == self.user:
            perms.add('verify')
        return perms

    @classmethod
    def get(cls, phone, user):
        """
        Return a UserPhoneClaim with matching phone number for the given user.

        :param str phone: Phone number to lookup (must be an exact match)
        :param User user: User who claimed this phone number
        """
        return cls.query.filter_by(phone=phone, user=user).one_or_none()

    @classmethod
    def all(cls, phone):
        """
        Return all UserPhoneClaim instances with matching phone number.

        :param str phone: Phone number to lookup (must be an exact match)
        """
        return cls.query.filter_by(phone=phone).all()


class PasswordResetRequest(BaseMixin, db.Model):
    __tablename__ = 'passwordresetrequest'
    __bind_key__ = 'lastuser'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id)
    reset_code = db.Column(db.String(44), nullable=False, default=newsecret)

    def __init__(self, **kwargs):
        super(PasswordResetRequest, self).__init__(**kwargs)
        self.reset_code = newsecret()


class UserExternalId(BaseMixin, db.Model):
    __tablename__ = 'userexternalid'
    __bind_key__ = 'lastuser'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('externalids', cascade="all, delete-orphan"))
    service = db.Column(db.String(20), nullable=False)
    userid = db.Column(db.String(250), nullable=False)  # Unique id (or OpenID)
    username = db.Column(db.Unicode(80), nullable=True)
    oauth_token = db.Column(db.String(250), nullable=True)
    oauth_token_secret = db.Column(db.String(250), nullable=True)
    oauth_token_type = db.Column(db.String(250), nullable=True)

    __table_args__ = (db.UniqueConstraint("service", "userid"), {})

    def __repr__(self):
        return u'<UserExternalId {service}:{username} of {user}'.format(
            service=self.service, username=self.username, user=repr(self.user)[1:-1])

    @classmethod
    def get(cls, service, userid=None, username=None):
        """
        Return a UserExternalId with the given service and userid or username.

        :param str service: Service to lookup
        :param str userid: Userid to lookup
        :param str username: Username to lookup (may be non-unique)

        Usernames are not guaranteed to be unique within a service. An example is with Google,
        where the userid is a directed OpenID URL, unique but subject to change if the Lastuser
        site URL changes. The username is the email address, which will be the same despite
        different userids.
        """
        if not bool(userid) ^ bool(username):
            raise TypeError("Either userid or username should be specified")

        if userid:
            return cls.query.filter_by(service=service, userid=userid).one_or_none()
        else:
            return cls.query.filter_by(service=service, username=username).one_or_none()

# --- Organizations and teams -------------------------------------------------


team_membership = db.Table(
    'team_membership', db.Model.metadata,
    *(timestamp_columns + (
        db.Column('user_id', db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True),
        db.Column('team_id', db.Integer, db.ForeignKey('team.id'), nullable=False, primary_key=True))),
    info={'bind_key': 'lastuser'}
    )


class Organization(BaseMixin, db.Model):
    __tablename__ = 'organization'
    __bind_key__ = 'lastuser'
    # owners_id cannot be null, but must be declared with nullable=True since there is
    # a circular dependency. The post_update flag on the relationship tackles the circular
    # dependency within SQLAlchemy.
    owners_id = db.Column(db.Integer, db.ForeignKey('team.id',
        use_alter=True, name='fk_organization_owners_id'), nullable=True)
    owners = db.relationship('Team', primaryjoin='Organization.owners_id == Team.id',
        uselist=False, cascade='all', post_update=True)
    userid = db.Column(db.String(22), unique=True, nullable=False, default=newid)
    _name = db.Column('name', db.Unicode(80), unique=True, nullable=True)
    title = db.Column(db.Unicode(80), default=u'', nullable=False)
    #: Deprecated, but column preserved for existing data until migration
    description = deferred(db.Column(db.UnicodeText, default=u'', nullable=False))

    #: Client id that created this account
    client_id = db.Column(None, db.ForeignKey('client.id',
        use_alter=True, name='organization_client_id_fkey'), nullable=True)
    #: If this org was created by a client app via the API, record it here
    client = db.relationship('Client', foreign_keys=[client_id])  # No backref or cascade

    _defercols = [
        defer('created_at'),
        defer('updated_at'),
        ]

    def __init__(self, *args, **kwargs):
        super(Organization, self).__init__(*args, **kwargs)
        if self.owners is None:
            self.owners = Team(title=u"Owners", org=self)

    @hybrid_property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if self.valid_name(value):
            self._name = value

    def valid_name(self, value):
        if not valid_username(value):
            return False
        existing = Organization.get(name=value)
        if existing and existing.id != self.id:
            return False
        existing = User.query.filter_by(username=value).first()  # Avoid User.get to skip status check
        if existing:
            return False
        return True

    def __repr__(self):
        return u'<Organization {name} "{title}">'.format(
            name=self.name or self.userid, title=self.title)

    @property
    def pickername(self):
        if self.name:
            return u'{title} (~{name})'.format(title=self.title, name=self.name)
        else:
            return self.title

    def clients_with_team_access(self):
        """
        Return a list of clients with access to the organization's teams.
        """
        from lastuser_core.models.client import CLIENT_TEAM_ACCESS
        return [cta.client for cta in self.client_team_access if cta.access_level == CLIENT_TEAM_ACCESS.ALL]

    def permissions(self, user, inherited=None):
        perms = super(Organization, self).permissions(user, inherited)
        if user and user in self.owners.users:
            perms.add('view')
            perms.add('edit')
            perms.add('delete')
            perms.add('view-teams')
            perms.add('new-team')
        else:
            if 'view' in perms:
                perms.remove('view')
            if 'edit' in perms:
                perms.remove('edit')
            if 'delete' in perms:
                perms.remove('delete')
        return perms

    def available_permissions(self):
        """
        Return all permission objects available to this organization
        (either owned by this organization or available to all users).
        """
        from .client import Permission
        return Permission.query.filter(
            db.or_(Permission.allusers == True, Permission.org == self)
            ).order_by(Permission.name).all()

    @classmethod
    def get(cls, name=None, userid=None, defercols=False):
        """
        Return an Organization with matching name or userid. Note that ``name`` is the username, not the title.

        :param str name: Name of the organization
        :param str userid: Userid of the organization
        :param bool defercols: Defer loading non-critical columns
        """
        if not bool(name) ^ bool(userid):
            raise TypeError("Either name or userid should be specified")

        if userid:
            query = cls.query.filter_by(userid=userid)
        else:
            query = cls.query.filter_by(name=name)
        if defercols:
            query = query.options(*cls._defercols)
        return query.one_or_none()

    @classmethod
    def all(cls, userids=None, names=None, defercols=False):
        orgs = []
        if userids:
            query = cls.query.filter(cls.userid.in_(userids))
            if defercols:
                query = query.options(*cls._defercols)
            orgs.extend(query.all())
        if names:
            query = cls.query.filter(cls.name.in_(names))
            if defercols:
                query = query.options(*cls._defercols)
            orgs.extend(query.all())
        return orgs


class Team(BaseMixin, db.Model):
    __tablename__ = 'team'
    __bind_key__ = 'lastuser'
    #: Unique and non-changing id
    userid = db.Column(db.String(22), unique=True, nullable=False, default=newid)
    #: Displayed name
    title = db.Column(db.Unicode(250), nullable=False)
    #: Organization
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    org = db.relationship(Organization, primaryjoin=org_id == Organization.id,
        backref=db.backref('teams', order_by=title, cascade='all, delete-orphan'))
    users = db.relationship(User, secondary='team_membership',
        backref='teams')  # No cascades here! Cascades will delete users

    #: Client id that created this team
    client_id = db.Column(None, db.ForeignKey('client.id',
        use_alter=True, name='team_client_id_fkey'), nullable=True)
    #: If this team was created by a client app via the API, record it here
    client = db.relationship('Client', foreign_keys=[client_id])  # No backref or cascade

    def __repr__(self):
        return u'<Team {team} of {org}>'.format(
            team=self.title, org=repr(self.org)[1:-1])

    @property
    def pickername(self):
        return self.title

    def permissions(self, user, inherited=None):
        perms = super(Team, self).permissions(user, inherited)
        if user and user in self.org.owners.users:
            perms.add('edit')
            perms.add('delete')
        return perms

    @classmethod
    def migrate_user(cls, olduser, newuser):
        for team in olduser.teams:
            if team not in newuser.teams:
                newuser.teams.append(team)
        olduser.teams = []

    @classmethod
    def get(cls, userid=None):
        """
        Return a Team with matching userid.

        :param str userid: Userid of the organization
        """
        return cls.query.filter_by(userid=userid).one_or_none()

########NEW FILE########
__FILENAME__ = registry
# -*- coding: utf-8 -*-

"""
Resource registry
"""

from functools import wraps
import re
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from flask import Response, request, jsonify, abort
from .models import AuthToken

# Bearer token, as per http://tools.ietf.org/html/draft-ietf-oauth-v2-bearer-15#section-2.1
auth_bearer_re = re.compile("^Bearer ([a-zA-Z0-9_.~+/-]+=*)$")


class ResourceRegistry(OrderedDict):
    """
    Dictionary of resources
    """
    def resource(self, name, description=None, trusted=False, scope=None):
        """
        Decorator for resource functions.

        :param unicode name: Name of the resource
        :param unicode description: User-friendly description
        :param bool trusted: Restrict access to trusted clients?
        :param unicode scope: Grant access via this other resource name
        """
        def resource_auth_error(message):
            return Response(message, 401,
                {'WWW-Authenticate': 'Bearer realm="Token Required" scope="%s"' % name})

        def wrapper(f):
            @wraps(f)
            def decorated_function():
                if request.method == 'GET':
                    args = request.args
                elif request.method in ['POST', 'PUT', 'DELETE']:
                    args = request.form
                else:
                    abort(405)
                if 'Authorization' in request.headers:
                    token_match = auth_bearer_re.search(request.headers['Authorization'])
                    if token_match:
                        token = token_match.group(1)
                    else:
                        # Unrecognized Authorization header
                        return resource_auth_error(u"A Bearer token is required in the Authorization header.")
                    if 'access_token' in args:
                        return resource_auth_error(u"Access token specified in both header and body.")
                else:
                    token = args.get('access_token')
                    if not token:
                        # No token provided in Authorization header or in request parameters
                        return resource_auth_error(u"An access token is required to access this resource.")
                authtoken = AuthToken.get(token=token)
                if not authtoken:
                    return resource_auth_error(u"Unknown access token.")
                if not authtoken.is_valid():
                    return resource_auth_error(u"Access token has expired.")
                if (scope and scope not in authtoken.scope) or (not scope and name not in authtoken.scope):
                    return resource_auth_error(u"Token does not provide access to this resource.")
                if trusted and not authtoken.client.trusted:
                    return resource_auth_error(u"This resource can only be accessed by trusted clients.")
                # All good. Return the result value
                try:
                    result = f(authtoken, args, request.files)
                    response = jsonify({'status': 'ok', 'result': result})
                except Exception as exception:
                    response = jsonify({'status': 'error',
                                        'error': exception.__class__.__name__,
                                        'error_description': unicode(exception)
                                        })
                # XXX: Let resources control how they return?
                response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                return response

            self[name] = {
                'name': name,
                'scope': scope or name,
                'description': description,
                'f': f,
                }
            return decorated_function
        return wrapper


class LoginError(Exception):
    """External service login failure"""
    pass


class LoginInitError(Exception):
    """External service login failure (during init)"""
    pass


class LoginCallbackError(Exception):
    """External service login failure (during callback)"""
    pass


class LoginProvider(object):
    """
    Base class for login providers. Each implementation provides
    two methods: :meth:`do` and :meth:`callback`. :meth:`do` is called
    when the user chooses to login with the specified provider.
    :meth:`callback` is called with the response from the provider.

    Both :meth:`do` and :meth:`callback` are called as part of a Flask
    view and have full access to the view infrastructure. However, while
    :meth:`do` is expected to return a Response to the user,
    :meth:`callback` only returns information on the user back to Lastuser.

    Implementations must take their configuration via the __init__
    constructor.

    :param name: Name of the service (stored in the database)
    :param title: Title (shown to user)
    :param at_login: (default True). Is this service available to the user for login? If false, it
      will only be available to be added in the user's profile page. Use this for multiple instances
      of the same external service with differing access permissions (for example, with Twitter).
    :param priority: (default False). Is this service high priority? If False, it'll be hidden behind
      a show more link.
    """

    #: URL to icon for the login button
    icon = None
    #: Login form, if required
    form = None

    def __init__(self, name, title, at_login=True, priority=False, **kwargs):
        self.name = name
        self.title = title
        self.at_login = at_login

    def get_form(self):
        """
        Returns form data, with three keys, next, error and form.
        """
        return {'next': None, 'error': None, 'form': None}

    def do(self, callback_url, form=None):
        raise NotImplementedError

    def callback(self, *args, **kwargs):
        raise NotImplementedError
        return {
            'userid': None,              # Unique user id at this service
            'username': None,            # Public username. This may change
            'avatar_url': None,          # URL to avatar image
            'oauth_token': None,         # OAuth token, for OAuth-based services
            'oauth_token_secret': None,  # If required
            'oauth_token_type': None,    # Type of token
            'email': None,               # Verified email address. Service can be trusted
            'emailclaim': None,          # Claimed email address. Must be verified
            'email_md5sum': None,        # For when we have the email md5sum, but not the email itself
        }


class LoginProviderRegistry(OrderedDict):
    """
    Dictionary of login providers (service: instance).
    """
    pass

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-

from flask.signals import Namespace
from sqlalchemy import event as sqla_event
from .models import User, Organization, Team


lastuser_signals = Namespace()

model_user_new = lastuser_signals.signal('model-user-new')
model_user_edited = lastuser_signals.signal('model-user-edited')
model_user_deleted = lastuser_signals.signal('model-user-deleted')

model_org_new = lastuser_signals.signal('model-org-new')
model_org_edited = lastuser_signals.signal('model-org-edited')
model_org_deleted = lastuser_signals.signal('model-org-deleted')

model_team_new = lastuser_signals.signal('model-team-new')
model_team_edited = lastuser_signals.signal('model-team-edited')
model_team_deleted = lastuser_signals.signal('model-team-deleted')

resource_access_granted = lastuser_signals.signal('resource-access-granted')

# Higher level signals
user_login = lastuser_signals.signal('user-login')
user_logout = lastuser_signals.signal('user-logout')
user_registered = lastuser_signals.signal('user-registered')
user_data_changed = lastuser_signals.signal('user-data-changed')
org_data_changed = lastuser_signals.signal('org-data-changed')
team_data_changed = lastuser_signals.signal('team-data-changed')
session_revoked = lastuser_signals.signal('session-revoked')

@sqla_event.listens_for(User, 'after_insert')
def _user_new(mapper, connection, target):
    model_user_new.send(target)


@sqla_event.listens_for(User, 'after_update')
def _user_edited(mapper, connection, target):
    model_user_edited.send(target)


@sqla_event.listens_for(User, 'after_delete')
def _user_deleted(mapper, connection, target):
    model_user_deleted.send(target)


@sqla_event.listens_for(Organization, 'after_insert')
def _org_new(mapper, connection, target):
    model_org_new.send(target)


@sqla_event.listens_for(Organization, 'after_update')
def _org_edited(mapper, connection, target):
    model_org_edited.send(target)


@sqla_event.listens_for(Organization, 'after_delete')
def _org_deleted(mapper, connection, target):
    model_org_deleted.send(target)


@sqla_event.listens_for(Team, 'after_insert')
def _team_new(mapper, connection, target):
    model_team_new.send(target)


@sqla_event.listens_for(Team, 'after_update')
def _team_edited(mapper, connection, target):
    model_team_edited.send(target)


@sqla_event.listens_for(Team, 'after_delete')
def _team_deleted(mapper, connection, target):
    model_team_deleted.send(target)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

# Id generation
import re
import urlparse
from urllib import urlencode as make_query_string

# --- Constants ---------------------------------------------------------------

USERNAME_VALID_RE = re.compile('^[a-z0-9][a-z0-9-]*[a-z0-9]$')
PHONE_STRIP_RE = re.compile(r'[\t .()\[\]-]+')
PHONE_VALID_RE = re.compile(r'^\+[0-9]+$')

# --- Utilities ---------------------------------------------------------------


def make_redirect_url(url, **params):
    urlparts = list(urlparse.urlsplit(url))
    # URL parts:
    # 0: scheme
    # 1: netloc
    # 2: path
    # 3: query -- appended to
    # 4: fragment
    queryparts = urlparse.parse_qsl(urlparts[3], keep_blank_values=True)
    queryparts.extend(params.items())
    queryparts = [(key.encode('utf-8') if isinstance(key, unicode) else key,
                   value.encode('utf-8') if isinstance(value, unicode) else value) for key, value in queryparts]
    urlparts[3] = make_query_string(queryparts)
    return urlparse.urlunsplit(urlparts)


def strip_phone(candidate):
    return PHONE_STRIP_RE.sub('', candidate)


def valid_phone(candidate):
    return not PHONE_VALID_RE.search(candidate) is None


def get_gravatar_md5sum(url):
    """
    Retrieve the MD5 sum from a Gravatar URL. Returns None if the URL is invalid.

    >>> get_gravatar_md5sum(
    ...     'https://secure.gravatar.com/avatar/31b0e7df40a7e327e7908f61a314fe47?d=https'
    ...     '://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-140.png')
    '31b0e7df40a7e327e7908f61a314fe47'
    """
    parts = urlparse.urlparse(url)
    if parts.netloc not in ['www.gravatar.com', 'secure.gravatar.com', 'gravatar.com']:
        return None
    if not parts.path.startswith('/avatar/'):
        return None
    md5sum = parts.path.split('/')[2]
    if len(md5sum) != 32:
        return None
    return md5sum

########NEW FILE########
__FILENAME__ = auth
# -*- coding: utf-8 -*-

from baseframe.forms import Form


class AuthorizeForm(Form):
    """
    OAuth authorization form. Has no fields and is only used for CSRF protection.
    """
    pass

########NEW FILE########
__FILENAME__ = login
# -*- coding: utf-8 -*-

from flask import Markup, url_for, current_app, escape
import wtforms
import wtforms.fields.html5
import flask.ext.wtf as wtf
from coaster import valid_username
from baseframe.forms import Form

from lastuser_core.models import User, UserEmail, getuser


class LoginForm(Form):
    username = wtforms.TextField('Username or Email', validators=[wtforms.validators.Required()])
    password = wtforms.PasswordField('Password', validators=[wtforms.validators.Required()])

    def validate_username(self, field):
        existing = getuser(field.data)
        if existing is None:
            raise wtforms.ValidationError("User does not exist")

    def validate_password(self, field):
        user = getuser(self.username.data)
        if user is None or not user.password_is(field.data):
            if not self.username.errors:
                raise wtforms.ValidationError("Incorrect password")
        self.user = user


class RegisterForm(Form):
    fullname = wtforms.TextField('Full name', validators=[wtforms.validators.Required()])
    email = wtforms.fields.html5.EmailField('Email address', validators=[wtforms.validators.Required(), wtforms.validators.Email()])
    username = wtforms.TextField('Username', validators=[wtforms.validators.Required()],
        description="Single word that can contain letters, numbers and dashes")
    password = wtforms.PasswordField('Password', validators=[wtforms.validators.Required()])
    confirm_password = wtforms.PasswordField('Confirm password',
                          validators=[wtforms.validators.Required(), wtforms.validators.EqualTo('password')])
    recaptcha = wtf.RecaptchaField('Are you human?',
        description="Type both words into the text box to prove that you are a human and not a computer program")

    def validate_username(self, field):
        if field.data in current_app.config['RESERVED_USERNAMES']:
            raise wtforms.ValidationError, "That name is reserved"
        if not valid_username(field.data):
            raise wtforms.ValidationError(u"Invalid characters in name. Names must be made of ‘a-z’, ‘0-9’ and ‘-’, without trailing dashes")
        existing = User.get(username=field.data)
        if existing is not None:
            raise wtforms.ValidationError("That username is taken")

    def validate_email(self, field):
        field.data = field.data.lower()  # Convert to lowercase
        existing = UserEmail.get(email=field.data)
        if existing is not None:
            raise wtforms.ValidationError(Markup(
                u'This email address is already registered. Do you want to <a href="{loginurl}">login</a> instead?'.format(
                    loginurl=escape(url_for('.login')))))

########NEW FILE########
__FILENAME__ = profile
# -*- coding: utf-8 -*-

from flask import current_app
import wtforms
import wtforms.fields.html5
from coaster import valid_username, sorted_timezones
from baseframe.forms import Form, ValidEmailDomain

from lastuser_core.models import UserEmail, getuser

timezones = sorted_timezones()


class PasswordResetRequestForm(Form):
    username = wtforms.TextField('Username or Email', validators=[wtforms.validators.Required()])

    def validate_username(self, field):
        user = getuser(field.data)
        if user is None:
            raise wtforms.ValidationError("Could not find a user with that id")
        self.user = user


class PasswordResetForm(Form):
    username = wtforms.TextField('Username or Email', validators=[wtforms.validators.Required()],
        description="Please reconfirm your username or email address")
    password = wtforms.PasswordField('New password', validators=[wtforms.validators.Required()])
    confirm_password = wtforms.PasswordField('Confirm password',
                          validators=[wtforms.validators.Required(), wtforms.validators.EqualTo('password')])

    def validate_username(self, field):
        user = getuser(field.data)
        if user is None or user != self.edit_user:
            raise wtforms.ValidationError(
                "That username or email does not match the user the reset code is for")


class PasswordChangeForm(Form):
    old_password = wtforms.PasswordField('Current password', validators=[wtforms.validators.Required()])
    password = wtforms.PasswordField('New password', validators=[wtforms.validators.Required()])
    confirm_password = wtforms.PasswordField('Confirm password',
                          validators=[wtforms.validators.Required(), wtforms.validators.EqualTo('password')])

    def validate_old_password(self, field):
        if self.edit_user is None:
            raise wtforms.ValidationError("Not logged in")
        if not self.edit_user.password_is(field.data):
            raise wtforms.ValidationError("Incorrect password")


class ProfileForm(Form):
    fullname = wtforms.TextField('Full name', validators=[wtforms.validators.Required()])
    email = wtforms.fields.html5.EmailField('Email address',
        validators=[wtforms.validators.Required(), wtforms.validators.Email(), ValidEmailDomain()])
    username = wtforms.TextField('Username', validators=[wtforms.validators.Required()])
    timezone = wtforms.SelectField('Timezone', validators=[wtforms.validators.Required()], choices=timezones)

    def validate_username(self, field):
        ## Usernames are now mandatory. This should be commented out:
        # if not field.data:
        #     field.data = None
        #     return
        field.data = field.data.lower()  # Usernames can only be lowercase
        if not valid_username(field.data):
            raise wtforms.ValidationError("Usernames can only have alphabets, numbers and dashes (except at the ends)")
        if field.data in current_app.config['RESERVED_USERNAMES']:
            raise wtforms.ValidationError("That name is reserved")
        if not self.edit_user.is_valid_username(field.data):
            raise wtforms.ValidationError("That username is taken")

    # TODO: Move to function and place before ValidEmailDomain()
    def validate_email(self, field):
        field.data = field.data.lower()  # Convert to lowercase
        existing = UserEmail.get(email=field.data)
        if existing is not None and existing.user != self.edit_obj:
            raise wtforms.ValidationError("That email address has been claimed by another user")


class ProfileMergeForm(Form):
    pass

########NEW FILE########
__FILENAME__ = mailclient
# -*- coding: utf-8 -*-

from markdown import markdown
from flask import render_template
from flask.ext.mail import Mail, Message

mail = Mail()


def send_email_verify_link(useremail):
    """
    Mail a verification link to the user.
    """
    msg = Message(subject="Confirm your email address",
        recipients=[useremail.email])
    msg.body = render_template("emailverify.md", useremail=useremail)
    msg.html = markdown(msg.body)
    mail.send(msg)


def send_password_reset_link(email, user, secret):
    msg = Message(subject="Reset your password",
        recipients=[email])
    msg.body = render_template("emailreset.md", user=user, secret=secret)
    msg.html = markdown(msg.body)
    mail.send(msg)

########NEW FILE########
__FILENAME__ = github
# -*- coding: utf-8 -*-

from urllib import quote
import requests
from flask import redirect, request
from lastuser_core.registry import LoginProvider, LoginCallbackError

__all__ = ['GitHubProvider']


class GitHubProvider(LoginProvider):
    auth_url = "https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}"
    token_url = "https://github.com/login/oauth/access_token"
    user_info = "https://api.github.com/user"
    user_emails = "https://api.github.com/user/emails"

    def __init__(self, name, title, key, secret, at_login=True, priority=False):
        self.name = name
        self.title = title
        self.at_login = at_login
        self.priority = priority

        self.key = key
        self.secret = secret

    def do(self, callback_url):
        return redirect(self.auth_url.format(
            client_id=self.key,
            redirect_uri=quote(callback_url),
            scope='user:email'))

    def callback(self):
        if request.args.get('error'):
            if request.args['error'] == 'user_denied':
                raise LoginCallbackError(u"You denied the GitHub login request")
            elif request.args['error'] == 'redirect_uri_mismatch':
                # TODO: Log this as an exception for the server admin to look at
                raise LoginCallbackError(u"This server's callback URL is misconfigured")
            else:
                raise LoginCallbackError(u"Unknown failure")
        code = request.args.get('code', None)
        try:
            response = requests.post(self.token_url, headers={'Accept': 'application/json'},
                params={
                    'client_id': self.key,
                    'client_secret': self.secret,
                    'code': code
                    }
                ).json()
        except requests.ConnectionError as e:
            raise LoginCallbackError(u"Unable to authenticate via GitHub. Internal details: {error}".format(error=e))
        if 'error' in response:
            raise LoginCallbackError(response['error'])
        ghinfo = requests.get(self.user_info,
            params={'access_token': response['access_token']}).json()
        ghemails = requests.get(self.user_emails,
            params={'access_token': response['access_token']},
            headers={'Accept': 'application/vnd.github.v3+json'}).json()

        email = None
        if ghemails and isinstance(ghemails, (list, tuple)):
            for result in ghemails:
                if result.get('verified'):
                    email = result['email']
                    break  # TODO: Support multiple emails in login providers
        return {'email': email,
                'userid': ghinfo['login'],
                'username': ghinfo['login'],
                'fullname': ghinfo.get('name'),
                'avatar_url': ghinfo.get('avatar_url'),
                'oauth_token': response['access_token'],
                'oauth_token_secret': None,  # OAuth 2 doesn't need token secrets
                'oauth_token_type': response['token_type']
                }

########NEW FILE########
__FILENAME__ = google
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from functools import wraps
from flask import session
from .openid import oid, OpenIdProvider
from openid.fetchers import HTTPFetchingError
from lastuser_core.registry import LoginCallbackError

__all__ = ['GoogleProvider']


def exception_handler(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except HTTPFetchingError as e:
            raise LoginCallbackError(e)
    return decorated_function


class GoogleProvider(OpenIdProvider):
    form = None  # Don't need a form for Google

    def __init__(self, *args, **kwargs):
        super(GoogleProvider, self).__init__(*args, **kwargs)
        self.do = exception_handler(oid.loginhandler(self.unwrapped_do))

    def unwrapped_do(self, callback_url=None, form=None):
        session['openid_service'] = self.name
        return oid.try_login('https://www.google.com/accounts/o8/id',
            ask_for=['email', 'fullname'])

########NEW FILE########
__FILENAME__ = linkedin
# -*- coding: utf-8 -*-

from urllib import quote
import requests
from uuid import uuid4
from flask import redirect, request, session
from lastuser_core.registry import LoginProvider, LoginCallbackError

__all__ = ['LinkedInProvider']


class LinkedInProvider(LoginProvider):
    auth_url = "https://www.linkedin.com/uas/oauth2/authorization?response_type=code&client_id={client_id}&scope={scope}&redirect_uri={redirect_uri}&state={state}"
    token_url = "https://www.linkedin.com/uas/oauth2/accessToken"
    user_info = "https://api.linkedin.com/v1/people/~:(id,formatted-name,email-address,picture-url,public-profile-url)?secure-urls=true"

    def __init__(self, name, title, key, secret, at_login=True, priority=False):
        self.name = name
        self.title = title
        self.at_login = at_login
        self.priority = priority

        self.key = key
        self.secret = secret

    def do(self, callback_url):
        session['linkedin_state'] = unicode(uuid4())
        session['linkedin_callback'] = callback_url
        return redirect(self.auth_url.format(
            client_id=self.key,
            redirect_uri=quote(callback_url),
            scope='r_basicprofile r_emailaddress',
            state=session['linkedin_state']))

    def callback(self):
        state = session.pop('linkedin_state', None)
        callback_url = session.pop('linkedin_callback', None)
        if state is None or request.args.get('state') != state:
            raise LoginCallbackError("We detected a possible attempt at cross-site request forgery")
        if 'error' in request.args:
            if request.args['error'] == 'access_denied':
                raise LoginCallbackError(u"You denied the LinkedIn login request")
            elif request.args['error'] == 'redirect_uri_mismatch':
                # TODO: Log this as an exception for the server admin to look at
                raise LoginCallbackError(u"This server's callback URL is misconfigured")
            else:
                raise LoginCallbackError(u"Unknown failure")
        code = request.args.get('code', None)
        try:
            response = requests.post(self.token_url, headers={'Accept': 'application/json'},
                params={
                    'grant_type': 'authorization_code',
                    'client_id': self.key,
                    'client_secret': self.secret,
                    'code': code,
                    'redirect_uri': callback_url,
                    }
                ).json()
        except requests.exceptions.RequestException as e:
            raise LoginCallbackError(u"Unable to authenticate via LinkedIn. Internal details: {error}".format(error=e))
        if 'error' in response:
            raise LoginCallbackError(response['error'])
        try:
            info = requests.get(self.user_info,
                params={'oauth2_access_token': response['access_token']},
                headers={'x-li-format': 'json'}).json()
        except requests.exceptions.RequestException as e:
            raise LoginCallbackError(u"Unable to authenticate via LinkedIn. Internal details: {error}".format(error=e))

        if not info.get('id'):
            raise LoginCallbackError(u"Unable to retrieve user details from LinkedIn. Please try again")

        return {'email': info.get('emailAddress'),
                'userid': info.get('id'),
                'username': info.get('publicProfileUrl'),
                'fullname': info.get('formattedName'),
                'avatar_url': info.get('pictureUrl'),
                'oauth_token': response['access_token'],
                'oauth_token_secret': None,  # OAuth 2 doesn't need token secrets
                'oauth_token_type': None
                }

########NEW FILE########
__FILENAME__ = openid
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from flask import Markup, session
import wtforms
import wtforms.fields.html5
from baseframe.forms import Form
from lastuser_core.registry import LoginProvider, LoginInitError
from ..views.login import oid
from ..views.account import login_service_postcallback

__all__ = ['OpenIdProvider']


class OpenIdForm(Form):
    openid = wtforms.fields.html5.URLField('Login with OpenID', validators=[wtforms.validators.Required()], default='http://',
        description=Markup("Don't forget the <code>http://</code> or <code>https://</code> prefix"))


class OpenIdProvider(LoginProvider):
    form = OpenIdForm

    def __init__(self, name, title, key=None, secret=None, at_login=True, priority=False):
        self.name = name
        self.title = title
        self.at_login = at_login
        self.priority = priority

    def get_form(self):
        return {
            'error': oid.fetch_error(),
            'next': oid.get_next_url(),
            'form': self.form() if self.form else None
            }

    def do(self, callback_url=None, form=None):
        if form and form.validate_on_submit():
            session['openid_service'] = self.name
            return oid.try_login(form.openid.data,
                ask_for=['email', 'fullname', 'nickname'])
        raise LoginInitError("OpenID URL is invalid")


@oid.after_login
def login_openid_success(resp):
    """
    Called when OpenID login succeeds
    """
    openid = resp.identity_url
    if (openid.startswith('https://profiles.google.com/') or
            openid.startswith('https://www.google.com/accounts/o8/id?id=')):
        service = 'google'
    else:
        service = 'openid'

    response = {
        'userid': openid,
        'username': None,
        'fullname': getattr(resp, 'fullname', None),
        'oauth_token': None,
        'oauth_token_secret': None,
        'oauth_token_type': None,
    }
    if resp.email:
        if service == 'google':
            # Google id. Trust the email address.
            response['email'] = resp.email
        else:
            # Not Google. Treat it as a claim.
            response['emailclaim'] = resp.email
    # Set username for Google ids
    if openid.startswith('https://profiles.google.com/'):
        # Use profile name as username
        parts = openid.split('/')
        while not parts[-1]:
            parts.pop(-1)
        response['username'] = parts[-1]
    elif openid.startswith('https://www.google.com/accounts/o8/id?id='):
        # Use email address as username
        response['username'] = resp.email

    return login_service_postcallback(session.pop('openid_service', service), response)

########NEW FILE########
__FILENAME__ = twitter
# -*- coding: utf-8 -*-

from functools import wraps
from tweepy import TweepError, OAuthHandler as TwitterOAuthHandler, API as TwitterAPI
from httplib import BadStatusLine
from ssl import SSLError
from socket import error as socket_error, gaierror
from flask.ext.oauth import OAuth, OAuthException  # OAuth 1.0a
from lastuser_core.registry import LoginProvider, LoginInitError, LoginCallbackError

__all__ = ['TwitterProvider']


def twitter_exception_handler(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (OAuthException, BadStatusLine, AttributeError, socket_error, gaierror) as e:
            raise LoginCallbackError(e)
    return decorated_function


class TwitterProvider(LoginProvider):
    def __init__(self, name, title, key, secret, access_key, access_secret, at_login=True, priority=True):
        self.name = name
        self.title = title
        self.at_login = at_login
        self.priority = priority
        self.consumer_key = key
        self.consumer_secret = secret
        self.access_key = access_key
        self.access_secret = access_secret
        oauth = OAuth()
        twitter = oauth.remote_app('twitter',
            base_url='https://api.twitter.com/1/',
            request_token_url='https://api.twitter.com/oauth/request_token',
            access_token_url='https://api.twitter.com/oauth/access_token',
            authorize_url='https://api.twitter.com/oauth/authenticate',
            consumer_key=key,
            consumer_secret=secret,
            )

        twitter.tokengetter(lambda token=None: None)  # We have no use for tokengetter

        self.callback = twitter_exception_handler(twitter.authorized_handler(self.unwrapped_callback))
        self.twitter = twitter

    def do(self, callback_url):
        try:
            return self.twitter.authorize(callback=callback_url)
        except (OAuthException, BadStatusLine, SSLError), e:
            raise LoginInitError(e)

    def unwrapped_callback(self, resp):
        if resp is None:
            raise LoginCallbackError("You denied the request to login")

        # Try to read more from the user's Twitter profile
        auth = TwitterOAuthHandler(self.consumer_key, self.consumer_secret)
        if self.access_key is not None and self.access_secret is not None:
            auth.set_access_token(self.access_key, self.access_secret)
        else:
            auth.set_access_token(resp['oauth_token'], resp['oauth_token_secret'])
        api = TwitterAPI(auth)
        try:
            twinfo = api.lookup_users(user_ids=[resp['user_id']])[0]
            fullname = twinfo.name
            avatar_url = twinfo.profile_image_url_https.replace("_normal.", "_bigger.")
        except TweepError:
            fullname = None
            avatar_url = None

        return {'userid': resp['user_id'],
                'username': resp['screen_name'],
                'fullname': fullname,
                'avatar_url': avatar_url,
                'oauth_token': resp['oauth_token'],
                'oauth_token_secret': resp['oauth_token_secret'],
                'oauth_token_type': None,  # Twitter doesn't have token types
                }

########NEW FILE########
__FILENAME__ = account
# -*- coding: utf-8 -*-
from flask import abort, url_for, flash, redirect, g, session, render_template, request

from coaster import valid_username
from coaster.views import get_next_url
from baseframe.signals import exception_catchall
from lastuser_core import login_registry
from lastuser_core.models import db, getextid, merge_users, User, UserEmail, UserExternalId, UserEmailClaim
from lastuser_core.registry import LoginInitError, LoginCallbackError
from lastuser_core.signals import user_data_changed
from .. import lastuser_oauth
from ..forms.profile import ProfileMergeForm
from ..mailclient import send_email_verify_link
from ..views.helpers import login_internal, register_internal, set_loginmethod_cookie, requires_login


@lastuser_oauth.route('/login/<service>', methods=['GET', 'POST'])
def login_service(service):
    """
    Handle login with a registered service.
    """
    if service not in login_registry:
        abort(404)
    provider = login_registry[service]
    next_url = get_next_url(referrer=False, default=None)
    callback_url = url_for('.login_service_callback', service=service, next=next_url, _external=True)
    try:
        return provider.do(callback_url=callback_url)
    except (LoginInitError, LoginCallbackError) as e:
        msg = u"{service} login failed: {error}".format(service=provider.title, error=unicode(e))
        exception_catchall.send(e, message=msg)
        flash(msg, category='danger')
        return redirect(next_url or get_next_url(referrer=True))


@lastuser_oauth.route('/login/<service>/callback', methods=['GET', 'POST'])
def login_service_callback(service):
    """
    Callback handler for a login service.
    """
    if service not in login_registry:
        abort(404)
    provider = login_registry[service]
    try:
        userdata = provider.callback()
    except (LoginInitError, LoginCallbackError) as e:
        msg = u"{service} login failed: {error}".format(service=provider.title, error=unicode(e))
        exception_catchall.send(e, message=msg)
        flash(msg, category='danger')
        if g.user:
            return redirect(get_next_url(referrer=False))
        else:
            return redirect(url_for('.login'))
    return login_service_postcallback(service, userdata)


def get_user_extid(service, userdata):
    """
    Retrieves a 'user', 'extid' and 'useremail' from the given service and userdata.
    """
    provider = login_registry[service]
    extid = getextid(service=service, userid=userdata['userid'])

    useremail = None
    if userdata.get('email'):
        useremail = UserEmail.get(email=userdata['email'])

    user = None
    if extid is not None:
        user = extid.user
    elif useremail is not None:
        user = useremail.user
    else:
        # Cross-check with all other instances of the same LoginProvider (if we don't have a user)
        # This is (for eg) for when we have two Twitter services with different access levels.
        for other_service, other_provider in login_registry.items():
            if other_service != service and other_provider.__class__ == provider.__class__:
                other_extid = getextid(service=other_service, userid=userdata['userid'])
                if other_extid is not None:
                    user = other_extid.user
                    break

    # TODO: Make this work when we have multiple confirmed email addresses available
    return user, extid, useremail


def login_service_postcallback(service, userdata):
    user, extid, useremail = get_user_extid(service, userdata)

    if extid is not None:
        extid.oauth_token = userdata.get('oauth_token')
        extid.oauth_token_secret = userdata.get('oauth_token_secret')
        extid.oauth_token_type = userdata.get('oauth_token_type')
        extid.username = userdata.get('username')
        # TODO: Save refresh token and expiry date where present
        extid.oauth_refresh_token = userdata.get('oauth_refresh_token')
        extid.oauth_expiry_date = userdata.get('oauth_expiry_date')
        extid.oauth_refresh_expiry = userdata.get('oauth_refresh_expiry')  # TODO: Check this
    else:
        # New external id. Register it.
        extid = UserExternalId(
            user=user,  # This may be None right now. Will be handled below
            service=service,
            userid=userdata['userid'],
            username=userdata.get('username'),
            oauth_token=userdata.get('oauth_token'),
            oauth_token_secret=userdata.get('oauth_token_secret'),
            oauth_token_type=userdata.get('oauth_token_type')
            # TODO: Save refresh token
            )
        db.session.add(extid)

    if user is None:
        if g.user:
            # Attach this id to currently logged-in user
            user = g.user
            extid.user = user
        else:
            # Register a new user
            user = register_internal(None, userdata.get('fullname'), None)
            extid.user = user
            if userdata.get('username'):
                if valid_username(userdata['username']) and user.is_valid_username(userdata['username']):
                    # Set a username for this user if it's available
                    user.username = userdata['username']
    else:  # This id is attached to a user
        if g.user and g.user != user:
            # Woah! Account merger handler required
            # Always confirm with user before doing an account merger
            session['merge_userid'] = user.userid

    # Check for new email addresses
    if userdata.get('email') and not useremail:
        user.add_email(userdata['email'])

    if userdata.get('emailclaim'):
        emailclaim = UserEmailClaim(user=user, email=userdata['emailclaim'])
        db.session.add(emailclaim)
        send_email_verify_link(emailclaim)

    # Is the user's fullname missing? Populate it.
    if not user.fullname and userdata.get('fullname'):
        user.fullname = userdata['fullname']

    if not g.user:  # If a user isn't already logged in, login now.
        login_internal(user)
        flash(u"You have logged in via {service}.".format(service=login_registry[service].title), 'success')
    next_url = get_next_url(session=True)

    db.session.commit()

    # Finally: set a login method cookie and send user on their way
    if not user.is_profile_complete():
        login_next = url_for('.profile_new', next=next_url)
    else:
        login_next = next_url

    if 'merge_userid' in session:
        return set_loginmethod_cookie(redirect(url_for('.profile_merge', next=login_next), code=303), service)
    else:
        return set_loginmethod_cookie(redirect(login_next, code=303), service)


@lastuser_oauth.route('/profile/merge', methods=['GET', 'POST'])
@requires_login
def profile_merge():
    if 'merge_userid' not in session:
        return redirect(get_next_url(), code=302)
    other_user = User.get(userid=session['merge_userid'])
    if other_user is None:
        session.pop('merge_userid', None)
        return redirect(get_next_url(), code=302)
    form = ProfileMergeForm()
    if form.validate_on_submit():
        if 'merge' in request.form:
            new_user = merge_users(g.user, other_user)
            login_internal(new_user)
            user_data_changed.send(new_user, changes=['merge'])
            flash("Your accounts have been merged.", 'success')
            session.pop('merge_userid', None)
            db.session.commit()
            return redirect(get_next_url(), code=303)
        else:
            session.pop('merge_userid', None)
            return redirect(get_next_url(), code=303)
    return render_template("merge.html", form=form, user=g.user, other_user=other_user,
        login_registry=login_registry)

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-

import os
from datetime import datetime, timedelta
from functools import wraps
from urllib import unquote
from pytz import common_timezones
from flask import g, current_app, request, session, flash, redirect, url_for, Response
from coaster.views import get_current_url
from lastuser_core.models import db, User, Client, UserSession
from lastuser_core.signals import user_login, user_logout, user_registered
from .. import lastuser_oauth

valid_timezones = set(common_timezones)


@lastuser_oauth.before_app_request
def lookup_current_user():
    """
    If there's a userid in the session, retrieve the user object and add
    to the request namespace object g.
    """
    g.user = None
    g.usersession = None

    if 'sessionid' in session:
        usersession = UserSession.authenticate(buid=session['sessionid'])
        g.usersession = usersession
        if usersession:
            usersession.access()
            db.session.commit()  # Save access
            g.user = usersession.user
        else:
            session.pop('sessionid', None)

    # Transition users with 'userid' to 'sessionid'
    if 'userid' in session:
        if not g.usersession:
            user = User.get(userid=session['userid'])
            if user:
                usersession = UserSession(user=user)
                usersession.access()
                db.session.commit()  # Save access
                g.usersession = usersession
                g.user = user
                session['sessionid'] = usersession.buid
        session.pop('userid', None)

    # This will be set to True downstream by the requires_login decorator
    g.login_required = False


@lastuser_oauth.after_app_request
def cache_expiry_headers(response):
    if 'Expires' not in response.headers:
        response.headers['Expires'] = 'Fri, 01 Jan 1990 00:00:00 GMT'
    if 'Cache-Control' in response.headers:
        if 'private' not in response.headers['Cache-Control']:
            response.headers['Cache-Control'] = 'private, ' + response.headers['Cache-Control']
    else:
        response.headers['Cache-Control'] = 'private'
    return response


@lastuser_oauth.app_template_filter('usessl')
def usessl(url):
    """
    Convert a URL to https:// if SSL is enabled in site config
    """
    if not current_app.config.get('USE_SSL'):
        return url
    if url.startswith('//'):  # //www.example.com/path
        return 'https:' + url
    if url.startswith('/'):  # /path
        url = os.path.join(request.url_root, url[1:])
    if url.startswith('http:'):  # http://www.example.com
        url = 'https:' + url[5:]
    return url


@lastuser_oauth.app_template_filter('nossl')
def nossl(url):
    """
    Convert a URL to http:// if using SSL
    """
    if url.startswith('//'):
        return 'http:' + url
    if url.startswith('/') and request.url.startswith('https:'):  # /path and SSL is on
        url = os.path.join(request.url_root, url[1:])
    if url.startswith('https://'):
        return 'http:' + url[6:]
    return url


def requires_login(f):
    """
    Decorator to require a login for the given view.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.login_required = True
        if g.user is None:
            flash(u"You need to be logged in for that page", "info")
            session['next'] = get_current_url()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def requires_login_no_message(f):
    """
    Decorator to require a login for the given view.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.login_required = True
        if g.user is None:
            session['next'] = get_current_url()
            if 'message' in request.args and request.args['message']:
                flash(request.args['message'], 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def _client_login_inner():
    if request.authorization is None or not request.authorization.username:
        return Response(u"Client credentials required.", 401,
            {'WWW-Authenticate': 'Basic realm="Client credentials"'})
    client = Client.get(key=request.authorization.username)
    if client is None or not client.secret_is(request.authorization.password):
        return Response(u"Invalid client credentials.", 401,
            {'WWW-Authenticate': 'Basic realm="Client credentials"'})
    g.client = client


def requires_client_login(f):
    """
    Decorator to require a client login via HTTP Basic Authorization.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = _client_login_inner()
        if result is None:
            return f(*args, **kwargs)
        else:
            return result
    return decorated_function


def requires_user_or_client_login(f):
    """
    Decorator to require a user or client login (user by cookie, client by HTTP Basic).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.login_required = True
        # Check for user first:
        if g.user is not None:
            return f(*args, **kwargs)
        # If user is not logged in, check for client
        result = _client_login_inner()
        if result is None:
            return f(*args, **kwargs)
        else:
            return result
    return decorated_function


def login_internal(user):
    g.user = user
    usersession = UserSession(user=user)
    usersession.access()
    session['sessionid'] = usersession.buid
    session.permanent = True
    autoset_timezone(user)
    user_login.send(user)


def autoset_timezone(user):
    # Set the user's timezone automatically if available
    if user.timezone is None or user.timezone not in valid_timezones:
        if request.cookies.get('timezone'):
            timezone = unquote(request.cookies.get('timezone'))
            if timezone in valid_timezones:
                user.timezone = timezone


def logout_internal():
    user = g.user
    g.user = None
    if g.usersession:
        g.usersession.revoke()
        g.usersession = None
    session.pop('sessionid', None)
    session.pop('userid', None)
    session.pop('merge_userid', None)
    session.pop('userid_external', None)
    session.pop('avatar_url', None)
    session.permanent = False
    if user is not None:
        user_logout.send(user)


def register_internal(username, fullname, password):
    user = User(username=username, fullname=fullname, password=password)
    if not username:
        user.username = None
    db.session.add(user)
    user_registered.send(user)
    return user


def set_loginmethod_cookie(response, value):
    response.set_cookie('login', value, max_age=31557600,  # Keep this cookie for a year
        expires=datetime.utcnow() + timedelta(days=365))   # Expire one year from now
    return response

########NEW FILE########
__FILENAME__ = login
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import urlparse
from openid import oidutil
from flask import g, current_app, redirect, request, flash, render_template, url_for, Markup, escape, abort
from flask.ext.openid import OpenID
from coaster.views import get_next_url, load_model
from baseframe.forms import render_form, render_message, render_redirect

from lastuser_core import login_registry
from .. import lastuser_oauth
from ..mailclient import send_email_verify_link, send_password_reset_link
from lastuser_core.models import db, User, UserEmailClaim, PasswordResetRequest, Client, UserSession
from ..forms import LoginForm, RegisterForm, PasswordResetForm, PasswordResetRequestForm
from .helpers import login_internal, logout_internal, register_internal, set_loginmethod_cookie

oid = OpenID()


def openid_log(message, level=0):
    if current_app.debug:
        import sys
        print >> sys.stderr, message

oidutil.log = openid_log


@lastuser_oauth.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    # If user is already logged in, send them back
    if g.user:
        return redirect(get_next_url(referrer=True), code=303)

    loginform = LoginForm()
    service_forms = {}
    for service, provider in login_registry.items():
        if provider.at_login and provider.form is not None:
            service_forms[service] = provider.get_form()

    loginmethod = None
    if request.method == 'GET':
        loginmethod = request.cookies.get('login')

    formid = request.form.get('form.id')
    if request.method == 'POST' and formid == 'passwordlogin':
        if loginform.validate():
            user = loginform.user
            login_internal(user)
            db.session.commit()
            flash('You are now logged in', category='success')
            return set_loginmethod_cookie(render_redirect(get_next_url(session=True), code=303),
                'password')
    elif request.method == 'POST' and formid in service_forms:
        form = service_forms[formid]['form']
        if form.validate():
            return set_loginmethod_cookie(login_registry[formid].do(form=form), formid)
    elif request.method == 'POST':
        abort(500)
    if request.is_xhr and formid == 'passwordlogin':
        return render_template('forms/loginform.html', loginform=loginform, Markup=Markup)
    else:
        return render_template('login.html', loginform=loginform, lastused=loginmethod,
            service_forms=service_forms, Markup=Markup, login_registry=login_registry)


logout_errormsg = ("We detected a possibly unauthorized attempt to log you out. "
    "If you really did intend to logout, please click on the logout link again")


def logout_user():
    """
    User-initiated logout
    """
    if not request.referrer or (urlparse.urlsplit(request.referrer).hostname != urlparse.urlsplit(request.url).hostname):
        # TODO: present a logout form
        flash(current_app.config.get('LOGOUT_UNAUTHORIZED_MESSAGE') or logout_errormsg, 'danger')
        return redirect(url_for('index'))
    else:
        logout_internal()
        db.session.commit()
        flash('You are now logged out', category='info')
        return redirect(get_next_url())


def logout_client():
    """
    Client-initiated logout
    """
    client = Client.get(key=request.args['client_id'])
    if client is None:
        # No such client. Possible CSRF. Don't logout and don't send them back
        flash(logout_errormsg, 'danger')
        return redirect(url_for('index'))
    if client.trusted:
        # This is a trusted client. Does the referring domain match?
        clienthost = urlparse.urlsplit(client.redirect_uri).hostname
        if request.referrer:
            if clienthost != urlparse.urlsplit(request.referrer).hostname:
                # Doesn't. Don't logout and don't send back
                flash(logout_errormsg, 'danger')
                return redirect(url_for('index'))
        # else: no referrer? Either stripped out by browser or a proxy, or this is a direct link.
        # We can't do anything about that, so assume it's a legit case.
        #
        # If there is a next destination, is it in the same domain?
        if 'next' in request.args:
            if clienthost != urlparse.urlsplit(request.args['next']).hostname:
                # Doesn't. Assume CSRF and redirect to index without logout
                flash(logout_errormsg, 'danger')
                return redirect(url_for('index'))
        # All good. Log them out and send them back
        logout_internal()
        db.session.commit()
        return redirect(get_next_url(external=True))
    else:
        # We know this client, but it's not trusted. Send back without logout.
        return redirect(get_next_url(external=True))


@lastuser_oauth.route('/logout')
def logout():

    # Logout, but protect from CSRF attempts
    if 'client_id' in request.args:
        return logout_client()
    else:
        # If this is not a logout request from a client, check if all is good.
        return logout_user()


@lastuser_oauth.route('/logout/<session>')
@load_model(UserSession, {'buid': 'session'}, 'session')
def logout_session(session):
    if not request.referrer or (urlparse.urlsplit(request.referrer).hostname != urlparse.urlsplit(request.url).hostname) or (session.user != g.user):
        flash(current_app.config.get('LOGOUT_UNAUTHORIZED_MESSAGE') or logout_errormsg, 'danger')
        return redirect(url_for('index'))

    session.revoke()
    db.session.commit()
    return redirect(get_next_url(referrer=True), code=303)


@lastuser_oauth.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('index'))
    form = RegisterForm()
    # Make Recaptcha optional
    if not (current_app.config.get('RECAPTCHA_PUBLIC_KEY') and current_app.config.get('RECAPTCHA_PRIVATE_KEY')):
        del form.recaptcha
    form.fullname.description = current_app.config.get('FULLNAME_REASON')
    form.email.description = current_app.config.get('EMAIL_REASON')
    form.username.description = current_app.config.get('USERNAME_REASON')
    if form.validate_on_submit():
        user = register_internal(None, form.fullname.data, form.password.data)
        user.username = form.username.data or None
        useremail = UserEmailClaim(user=user, email=form.email.data)
        db.session.add(useremail)
        send_email_verify_link(useremail)
        login_internal(user)
        db.session.commit()
        flash("You are now one of us. Welcome aboard!", category='success')
        return redirect(get_next_url(session=True), code=303)
    return render_form(form=form, title='Create an account', formid='register', submit='Register',
        message=current_app.config.get('CREATE_ACCOUNT_MESSAGE'))


@lastuser_oauth.route('/reset', methods=['GET', 'POST'])
def reset():
    # User wants to reset password
    # Ask for username or email, verify it, and send a reset code
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        username = form.username.data
        user = form.user
        if '@' in username and not username.startswith('@'):
            # They provided an email address. Send reset email to that address
            email = username
        else:
            # Send to their existing address
            # User.email is a UserEmail object
            email = unicode(user.email)
        if not email:
            # They don't have an email address. Maybe they logged in via Twitter
            # and set a local username and password, but no email. Could happen.
            if len(user.externalids) > 0:
                extid = user.externalids[0]
                return render_message(title="Cannot reset password", message=Markup(u"""
                    We do not have an email address for your account. However, your account
                    is linked to <strong>{service}</strong> with the id <strong>{username}</strong>.
                    You can use that to login.
                    """.format(service=login_registry[extid.service].title, username=extid.username or extid.userid)))
            else:
                return render_message(title="Cannot reset password", message=Markup(
                    u"""
                    We do not have an email address for your account and therefore cannot
                    email you a reset link. Please contact
                    <a href="mailto:{email}">{email}</a> for assistance.
                    """.format(email=escape(current_app.config['SITE_SUPPORT_EMAIL']))))
        resetreq = PasswordResetRequest(user=user)
        db.session.add(resetreq)
        send_password_reset_link(email=email, user=user, secret=resetreq.reset_code)
        db.session.commit()
        return render_message(title="Reset password", message=
            u"""
            We sent you an email with a link to reset your password.
            Please check your email. If it doesn’t arrive in a few minutes,
            it may have landed in your spam or junk folder.
            The reset link is valid for 24 hours.
            """)

    return render_form(form=form, title="Reset password", submit="Send reset code", ajax=True)


@lastuser_oauth.route('/reset/<userid>/<secret>', methods=['GET', 'POST'])
@load_model(User, {'userid': 'userid'}, 'user', kwargs=True)
def reset_email(user, kwargs):
    resetreq = PasswordResetRequest.query.filter_by(user=user, reset_code=kwargs['secret']).first()
    if not resetreq:
        return render_message(title="Invalid reset link",
            message=u"The reset link you clicked on is invalid.")
    if resetreq.created_at < datetime.utcnow() - timedelta(days=1):
        # Reset code has expired (> 24 hours). Delete it
        db.session.delete(resetreq)
        db.session.commit()
        return render_message(title="Expired reset link",
            message=u"The reset link you clicked on has expired.")

    # Logout *after* validating the reset request to prevent DoS attacks on the user
    logout_internal()
    db.session.commit()
    # Reset code is valid. Now ask user to choose a new password
    form = PasswordResetForm()
    form.edit_user = user
    if form.validate_on_submit():
        user.password = form.password.data
        db.session.delete(resetreq)
        db.session.commit()
        return render_message(title="Password reset complete", message=Markup(
            u'Your password has been reset. You may now <a href="{loginurl}">login</a> with your new password.'.format(
                loginurl=escape(url_for('.login')))))
    return render_form(form=form, title="Reset password", formid='reset', submit="Reset password",
        message=Markup(u'Hello, <strong>{fullname}</strong>. You may now choose a new password.'.format(
            fullname=escape(user.fullname))),
        ajax=True)

########NEW FILE########
__FILENAME__ = notify
# -*- coding: utf-8 -*-

import requests
from flask.ext.rq import job
from lastuser_core.models import AuthToken
from lastuser_core.signals import user_data_changed, org_data_changed, team_data_changed, session_revoked


user_changes_to_notify = set(['merge', 'profile', 'email', 'email-claim', 'email-delete',
    'phone', 'phone-claim', 'phone-delete'])


@session_revoked.connect
def notify_session_revoked(session):
    for token in session.user.authtokens:
        if token.is_valid() and token.client.notification_uri:
            send_notice.delay(token.client.notification_uri, data=
                {'userid': session.user.userid,
                 'type': 'user',
                 'changes': ['logout'],
                 'sessionid': session.buid})


@user_data_changed.connect
def notify_user_data_changed(user, changes):
    """
    Look for changes that need to be notified to client apps,
    then look for apps that have user data and accept notifications,
    and then notify them.
    """
    if user_changes_to_notify & set(changes):
        # We have changes that apps need to hear about
        for token in user.authtokens:
            if token.is_valid() and token.client.notification_uri:
                notify_changes = []
                for change in changes:
                    if change in ['merge', 'profile']:
                        notify_changes.append(change)
                    elif change in ['email', 'email-claim', 'email-delete']:
                        if 'email' in token.scope:
                            notify_changes.append(change)
                    elif change in ['phone', 'phone-claim', 'phone-delete']:
                        if 'phone' in token.scope:
                            notify_changes.append(change)
                if notify_changes:
                    send_notice.delay(token.client.notification_uri, data=
                        {'userid': user.userid,
                        'type': 'user',
                        'changes': notify_changes})


@org_data_changed.connect
def notify_org_data_changed(org, user, changes, team=None):
    """
    Like :func:`notify_user_data_changed`, except we'll also look at
    all other owners of this org to find apps that need to be notified.
    """
    client_users = {}
    if team is not None:
        team_access = set(org.clients_with_team_access()) | set(user.clients_with_team_access())
    else:
        team_access = []
    for token in AuthToken.all(users=org.owners.users):
        if 'organizations' in token.scope and token.client.notification_uri and token.is_valid():
            if team is not None:
                if token.client not in team_access:
                    continue
            client_users.setdefault(token.client, []).append(token.user)
    # Now we have a list of clients to notify and a list of users to notify them with
    for client, users in client_users.items():
        if user in users:
            notify_user = user
        else:
            notify_user = users[0]  # First user available
        send_notice.delay(client.notification_uri, data=
            {'userid': notify_user.userid,
            'type': 'org' if team is None else 'team',
            'orgid': org.userid,
            'teamid': team.userid if team is not None else None,
            'changes': changes,
            })


@team_data_changed.connect
def notify_team_data_changed(team, user, changes):
    """
    Pass-through function that calls :func:`notify_org_data_changed`.
    """
    notify_org_data_changed(team.org, user=user, changes=['team-' + c for c in changes], team=team)


@job("lastuser")
def send_notice(url, params=None, data=None, method='POST'):
    requests.request(method, url, params=params, data=data)

########NEW FILE########
__FILENAME__ = oauth
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import urlparse
from flask import g, render_template, redirect, request, jsonify, get_flashed_messages
from coaster import newsecret

from lastuser_core.utils import make_redirect_url
from lastuser_core import resource_registry
from lastuser_core.models import (db, Client, AuthCode, AuthToken, UserFlashMessage,
    UserClientPermissions, TeamClientPermissions, getuser, Resource)
from .. import lastuser_oauth
from ..forms import AuthorizeForm
from .helpers import requires_login_no_message, requires_client_login
from .resource import get_userinfo


class ScopeException(Exception):
    pass


def verifyscope(scope, client):
    """
    Verify if requested scope is valid for this client. Scope must be a list.
    """
    resources = {}  # resource_object: [action_object, ...]

    for item in scope:
        if item not in resource_registry:  # Validation is only required for non-internal resources
            # Validation 1: namespace:resource/action is properly formatted
            if ':' not in item:
                raise ScopeException(u"No namespace specified for external resource ‘{scope}’ in scope".format(scope=item))
            itemparts = item.split(':')
            if len(itemparts) != 2:
                raise ScopeException(u"Too many ‘:’ characters in ‘{scope}’ in scope".format(scope=item))
            namespace, item = itemparts
            if '/' in item:
                parts = item.split('/')
                if len(parts) != 2:
                    raise ScopeException(u"Too many / characters in ‘{scope}’ in scope".format(scope=item))
                resource_name, action_name = parts
            else:
                resource_name = item
                action_name = None
            resource = Resource.get(name=resource_name, namespace=namespace)

            # Validation 2: Resource exists and client has access to it
            if not resource:
                raise ScopeException(u"Unknown resource ‘{resource}’ under namespace ‘{namespace}’ in scope".format(resource=resource_name, namespace=namespace))
            if resource.restricted and resource.client.owner != client.owner:
                raise ScopeException(
                    u"This application does not have access to resource ‘{resource}’ in scope".format(resource=resource_name))

            # Validation 3: Action is valid
            if action_name:
                action = resource.get_action(action_name)
                if not action:
                    raise ScopeException(u"Unknown action ‘{action}’ on resource ‘{resource}’ under namespace ‘{namespace}’".format(
                        action=action_name, resource=resource_name, namespace=namespace))
                resources.setdefault(resource, []).append(action)
            else:
                resources.setdefault(resource, [])
    return resources


def oauth_auth_403(reason):
    """
    Returns 403 errors for /auth
    """
    return render_template('oauth403.html', reason=reason), 403


def oauth_make_auth_code(client, scope, redirect_uri):
    """
    Make an auth code for a given client. Caller must commit
    the database session for this to work.
    """
    authcode = AuthCode(user=g.user, session=g.usersession, client=client, scope=scope, redirect_uri=redirect_uri)
    authcode.code = newsecret()
    db.session.add(authcode)
    return authcode.code


def clear_flashed_messages():
    """
    Clear pending flashed messages. This is useful when redirecting the user to a
    remote site where they cannot see the messages. If they return much later,
    they could be confused by a message for an action they do not recall.
    """
    list(get_flashed_messages())


def save_flashed_messages():
    """
    Save flashed messages so they can be relayed back to trusted clients.
    """
    for index, (category, message) in enumerate(get_flashed_messages(with_categories=True)):
        db.session.add(UserFlashMessage(user=g.user, seq=index, category=category, message=message))


def oauth_auth_success(client, redirect_uri, state, code):
    """
    Commit session and redirect to OAuth redirect URI
    """
    if client.trusted:
        save_flashed_messages()
    else:
        clear_flashed_messages()
    db.session.commit()
    if state is None:
        response = redirect(make_redirect_url(redirect_uri, code=code), code=302)
    else:
        response = redirect(make_redirect_url(redirect_uri, code=code, state=state), code=302)
    response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response


def oauth_auth_error(redirect_uri, state, error, error_description=None, error_uri=None):
    """
    Auth request resulted in an error. Return to client.
    """
    params = {'error': error}
    if state is not None:
        params['state'] = state
    if error_description is not None:
        params['error_description'] = error_description
    if error_uri is not None:
        params['error_uri'] = error_uri
    clear_flashed_messages()
    response = redirect(make_redirect_url(redirect_uri, **params), code=302)
    response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response


@lastuser_oauth.route('/auth', methods=['GET', 'POST'])
@requires_login_no_message
def oauth_authorize():
    """
    OAuth2 server -- authorization endpoint
    """
    form = AuthorizeForm()

    response_type = request.args.get('response_type')
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    scope = request.args.get('scope', u'').split(u' ')
    state = request.args.get('state')

    # Validation 1.1: Client_id present
    if not client_id:
        return oauth_auth_403(u"Missing client_id")
    # Validation 1.2: Client exists
    client = Client.query.filter_by(key=client_id).first()
    if not client:
        return oauth_auth_403(u"Unknown client_id")

    # Validation 1.2.1: Is the client active?
    if not client.active:
        return oauth_auth_error(client.redirect_uri, state, 'unauthorized_client')

    # Validation 1.3: Cross-check redirect_uri
    if not redirect_uri:
        redirect_uri = client.redirect_uri
        if not redirect_uri:  # Validation 1.3.1: No redirect_uri specified
            return oauth_auth_403(u"No redirect URI specified")
    elif redirect_uri != client.redirect_uri:
        if urlparse.urlsplit(redirect_uri).hostname != urlparse.urlsplit(client.redirect_uri).hostname:
            return oauth_auth_error(client.redirect_uri, state, 'invalid_request', u"Redirect URI hostname doesn't match")

    # Validation 1.4: Client allows login for this user
    if not client.allow_any_login:
        if client.user:
            perms = UserClientPermissions.query.filter_by(user=g.user, client=client).first()
        else:
            perms = TeamClientPermissions.query.filter_by(client=client).filter(
                TeamClientPermissions.team_id.in_([team.id for team in g.user.teams])).first()
        if not perms:
            return oauth_auth_error(client.redirect_uri, state, 'invalid_scope', u"You do not have access to this application")

    # Validation 2.1: Is response_type present?
    if not response_type:
        return oauth_auth_error(redirect_uri, state, 'invalid_request', "response_type missing")
    # Validation 2.2: Is response_type acceptable?
    if response_type not in [u'code']:
        return oauth_auth_error(redirect_uri, state, 'unsupported_response_type')

    # Validation 3.1: Is scope present?
    if not scope:
        return oauth_auth_error(redirect_uri, state, 'invalid_request', "Scope not specified")

    # Validation 3.2: Is scope valid?
    try:
        resources = verifyscope(scope, client)
    except ScopeException as scopeex:
        return oauth_auth_error(redirect_uri, state, 'invalid_scope', unicode(scopeex))

    # Validations complete. Now ask user for permission
    # If the client is trusted (Lastuser feature, not in OAuth2 spec), don't ask user.
    # The client does not get access to any data here -- they still have to authenticate to /token.
    if request.method == 'GET' and client.trusted:
        # Return auth token. No need for user confirmation
        return oauth_auth_success(client, redirect_uri, state, oauth_make_auth_code(client, scope, redirect_uri))

    # If there is an existing auth token with the same or greater scope, don't ask user again; authorise silently
    existing_token = AuthToken.query.filter_by(user=g.user, client=client).first()
    if existing_token and set(scope).issubset(set(existing_token.scope)):
        return oauth_auth_success(client, redirect_uri, state, oauth_make_auth_code(client, scope, redirect_uri))

    # First request. Ask user.
    if form.validate_on_submit():
        if 'accept' in request.form:
            # User said yes. Return an auth code to the client
            return oauth_auth_success(client, redirect_uri, state, oauth_make_auth_code(client, scope, redirect_uri))
        elif 'deny' in request.form:
            # User said no. Return "access_denied" error (OAuth2 spec)
            return oauth_auth_error(redirect_uri, state, 'access_denied')
        # else: shouldn't happen, so just show the form again

    # GET request or POST with invalid CSRF
    return render_template('authorize.html',
        form=form,
        client=client,
        redirect_uri=redirect_uri,
        scope=scope,
        resources=resources,
        resource_registry=resource_registry,
        ), 200, {'X-Frame-Options': 'SAMEORIGIN'}


def oauth_token_error(error, error_description=None, error_uri=None):
    params = {'error': error}
    if error_description is not None:
        params['error_description'] = error_description
    if error_uri is not None:
        params['error_uri'] = error_uri
    response = jsonify(**params)
    response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.status_code = 400
    return response


def oauth_make_token(user, client, scope):
    token = AuthToken.query.filter_by(user=user, client=client).first()
    if token:
        token.add_scope(scope)
    else:
        token = AuthToken(user=user, client=client, scope=scope, token_type='bearer')
        db.session.add(token)
    # TODO: Look up Resources for items in scope; look up their providing clients apps,
    # and notify each client app of this token
    return token


def oauth_token_success(token, **params):
    params['access_token'] = token.token
    params['token_type'] = token.token_type
    params['scope'] = u' '.join(token.scope)
    if token.client.trusted:
        # Trusted client. Send back waiting user messages.
        for ufm in list(UserFlashMessage.query.filter_by(user=token.user).all()):
            params.setdefault('messages', []).append({
                'category': ufm.category,
                'message': ufm.message
                })
            db.session.delete(ufm)
    # TODO: Understand how refresh_token works.
    if token.validity:
        params['expires_in'] = token.validity
        # No refresh tokens for client_credentials tokens
        if token.user is not None:
            params['refresh_token'] = token.refresh_token
    response = jsonify(**params)
    response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    db.session.commit()
    return response


@lastuser_oauth.route('/token', methods=['POST'])
@requires_client_login
def oauth_token():
    """
    OAuth2 server -- token endpoint
    """
    # Always required parameters
    grant_type = request.form.get('grant_type')
    client = g.client  # Provided by @requires_client_login
    scope = request.form.get('scope', u'').split(u' ')
    # if grant_type == 'authorization_code' (POST)
    code = request.form.get('code')
    redirect_uri = request.form.get('redirect_uri')
    # if grant_type == 'password' (GET)
    username = request.form.get('username')
    password = request.form.get('password')

    # Validations 1: Required parameters
    if not grant_type:
        return oauth_token_error('invalid_request', "Missing grant_type")
    # grant_type == 'refresh_token' is not supported. All tokens are permanent unless revoked
    if grant_type not in ['authorization_code', 'client_credentials', 'password']:
        return oauth_token_error('unsupported_grant_type')

    # Validations 2: client scope
    if grant_type == 'client_credentials':
        # Client data. User isn't part of it
        try:
            verifyscope(scope, client)
        except ScopeException as scopeex:
            return oauth_token_error('invalid_scope', unicode(scopeex))

        token = oauth_make_token(user=None, client=client, scope=scope)
        return oauth_token_success(token)

    # Validations 3: auth code
    elif grant_type == 'authorization_code':
        authcode = AuthCode.query.filter_by(code=code, client=client).first()
        if not authcode:
            return oauth_token_error('invalid_grant', "Unknown auth code")
        if not authcode.is_valid():
            db.session.delete(authcode)
            db.session.commit()
            return oauth_token_error('invalid_grant', "Expired auth code")
        # Validations 3.1: scope in authcode
        if not scope or scope[0] == '':
            return oauth_token_error('invalid_scope', "Scope is blank")
        if not set(scope).issubset(set(authcode.scope)):
            return oauth_token_error('invalid_scope', "Scope expanded")
        else:
            # Scope not provided. Use whatever the authcode allows
            scope = authcode.scope
        if redirect_uri != authcode.redirect_uri:
            return oauth_token_error('invalid_client', "redirect_uri does not match")

        token = oauth_make_token(user=authcode.user, client=client, scope=scope)
        db.session.delete(authcode)
        return oauth_token_success(token, userinfo=get_userinfo(
            user=authcode.user, client=client, scope=scope, session=authcode.session))

    elif grant_type == 'password':
        # Validations 4.1: password grant_type is only for trusted clients
        if not client.trusted:
            # Refuse to untrusted clients
            return oauth_token_error('unauthorized_client', "Client is not trusted for password grant_type")
        # Validations 4.2: Are username and password provided and correct?
        if not username or not password:
            return oauth_token_error('invalid_request', "Username or password not provided")
        user = getuser(username)
        if not user:
            return oauth_token_error('invalid_client', "No such user")  # XXX: invalid_client doesn't seem right
        if not user.password_is(password):
            return oauth_token_error('invalid_client', "Password mismatch")
        # Validations 4.3: verify scope
        try:
            verifyscope(scope, client)
        except ScopeException as scopeex:
            return oauth_token_error('invalid_scope', unicode(scopeex))
        # All good. Grant access
        token = oauth_make_token(user=user, client=client, scope=scope)
        return oauth_token_success(token, userinfo=get_userinfo(user=user, client=client, scope=scope))

########NEW FILE########
__FILENAME__ = profile
# -*- coding: utf-8 -*-

from flask import g, current_app, flash, url_for, Markup, escape
from coaster.views import get_next_url
from baseframe.forms import render_form, render_redirect, render_message

from lastuser_core.models import db, UserEmail, UserEmailClaim
from lastuser_core.signals import user_data_changed
from .. import lastuser_oauth
from ..mailclient import send_email_verify_link
from ..forms import ProfileForm
from .helpers import requires_login


@lastuser_oauth.route('/profile/edit', methods=['GET', 'POST'], defaults={'newprofile': False}, endpoint='profile_edit')
@lastuser_oauth.route('/profile/new', methods=['GET', 'POST'], defaults={'newprofile': True}, endpoint='profile_new')
@requires_login
def profile_edit(newprofile=False):
    form = ProfileForm(obj=g.user)
    form.edit_user = g.user
    form.fullname.description = current_app.config.get('FULLNAME_REASON')
    form.email.description = current_app.config.get('EMAIL_REASON')
    form.username.description = current_app.config.get('USERNAME_REASON')
    form.timezone.description = current_app.config.get('TIMEZONE_REASON')
    if g.user.email or newprofile is False:
        del form.email

    if form.validate_on_submit():
        # Can't auto-populate here because user.email is read-only
        g.user.fullname = form.fullname.data
        g.user.username = form.username.data
        g.user.timezone = form.timezone.data

        if newprofile and not g.user.email:
            useremail = UserEmailClaim.get(user=g.user, email=form.email.data)
            if useremail is None:
                useremail = UserEmailClaim(user=g.user, email=form.email.data)
                db.session.add(useremail)
            send_email_verify_link(useremail)
            db.session.commit()
            user_data_changed.send(g.user, changes=['profile', 'email-claim'])
            flash("Your profile has been updated. We sent you an email to confirm your address", category='success')
        else:
            db.session.commit()
            user_data_changed.send(g.user, changes=['profile'])
            flash("Your profile has been updated.", category='success')

        if newprofile:
            return render_redirect(get_next_url(), code=303)
        else:
            return render_redirect(url_for('profile'), code=303)
    if newprofile:
        return render_form(form, title="Update profile", formid="profile_new", submit="Continue",
            message=Markup(u"Hello, <strong>{fullname}</strong>. Please spare a minute to fill out your profile.".format(
                fullname=escape(g.user.fullname))),
            ajax=True)
    else:
        return render_form(form, title="Edit profile", formid="profile_edit", submit="Save changes", ajax=True)


# FIXME: Don't modify db on GET. Autosubmit via JS and process on POST
@lastuser_oauth.route('/confirm/<md5sum>/<secret>')
@requires_login
def confirm_email(md5sum, secret):
    emailclaim = UserEmailClaim.query.filter_by(md5sum=md5sum, verification_code=secret).first()
    if emailclaim is not None:
        if 'verify' in emailclaim.permissions(g.user):
            existing = UserEmail.query.filter(UserEmail.email.in_([emailclaim.email, emailclaim.email.lower()])).first()
            if existing is not None:
                claimed_email = emailclaim.email
                claimed_user = emailclaim.user
                db.session.delete(emailclaim)
                db.session.commit()
                if claimed_user != g.user:
                    return render_message(title="Email address already claimed",
                        message=Markup(
                            u"The email address <code>{email}</code> has already been verified by another user.".format(
                                email=escape(claimed_email))))
                else:
                    return render_message(title="Email address already verified",
                        message=Markup(u"Hello <strong>{fullname}</strong>! "
                            u"Your email address <code>{email}</code> has already been verified.".format(
                                fullname=escape(claimed_user.fullname), email=escape(claimed_email))))

            useremail = emailclaim.user.add_email(emailclaim.email.lower(), primary=emailclaim.user.email is None)
            db.session.delete(emailclaim)
            for claim in UserEmailClaim.query.filter(UserEmailClaim.email.in_([useremail.email, useremail.email.lower()])).all():
                db.session.delete(claim)
            db.session.commit()
            user_data_changed.send(g.user, changes=['email'])
            return render_message(title="Email address verified",
                message=Markup(u"Hello <strong>{fullname}</strong>! "
                    u"Your email address <code>{email}</code> has now been verified.".format(
                        fullname=escape(emailclaim.user.fullname), email=escape(useremail.email))))
        else:
            return render_message(
                title="That was not for you",
                message=u"You’ve opened an email verification link that was meant for another user. "
                        u"If you are managing multiple accounts, please login with the correct account "
                        u"and open the link again.",
                code=403)
    else:
        return render_message(
            title="Expired confirmation link",
            message=u"The confirmation link you clicked on is either invalid or has expired.",
            code=404)

########NEW FILE########
__FILENAME__ = resource
# -*- coding: utf-8 -*-

from flask import request, g
from coaster.utils import getbool
from coaster.views import jsonp, requestargs

from lastuser_core.models import (db, getuser, User, Organization, AuthToken, Resource,
    ResourceAction, UserClientPermissions, TeamClientPermissions, UserSession)
from lastuser_core import resource_registry
from .. import lastuser_oauth
from .helpers import requires_client_login, requires_user_or_client_login


def get_userinfo(user, client, scope=[], session=None, get_permissions=True):

    teams = {}

    if 'id' in scope:
        userinfo = {'userid': user.userid,
                    'username': user.username,
                    'fullname': user.fullname,
                    'timezone': user.timezone,
                    'oldids': [o.userid for o in user.oldids]}
    else:
        userinfo = {}

    if session:
        userinfo['sessionid'] = session.buid

    if 'email' in scope:
        userinfo['email'] = unicode(user.email)
    if 'phone' in scope:
        userinfo['phone'] = unicode(user.phone)
    if 'organizations' in scope:
        userinfo['organizations'] = {
            'owner': [{'userid': org.userid, 'name': org.name, 'title': org.title} for org in user.organizations_owned()],
            'member': [{'userid': org.userid, 'name': org.name, 'title': org.title} for org in user.organizations()],
            }

    if 'organizations' in scope or 'teams' in scope:
        for team in user.teams:
            teams[team.userid] = {
                'userid': team.userid,
                'title': team.title,
                'org': team.org.userid,
                'owners': team == team.org.owners,
                'member': True}

    if 'teams' in scope:
        for org in user.organizations_owned():
            for team in org.teams:
                if team.userid not in teams:
                    teams[team.userid] = {
                        'userid': team.userid,
                        'title': team.title,
                        'org': team.org.userid,
                        'owners': team == team.org.owners,
                        'member': False}

    if teams:
        userinfo['teams'] = teams.values()

    if get_permissions:
        if client.user:
            perms = UserClientPermissions.query.filter_by(user=user, client=client).first()
            if perms:
                userinfo['permissions'] = perms.access_permissions.split(u' ')
        else:
            perms = TeamClientPermissions.query.filter_by(client=client).filter(
                TeamClientPermissions.team_id.in_([team.id for team in user.teams])).all()
            permsset = set()
            for permob in perms:
                permsset.update(permob.access_permissions.split(u' '))
            userinfo['permissions'] = sorted(permsset)
    return userinfo


def resource_error(error, description=None, uri=None):
    params = {'status': 'error', 'error': error}
    if description:
        params['error_description'] = description
    if uri:
        params['error_uri'] = uri

    response = jsonp(params)
    response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.status_code = 400
    return response


def api_result(status, **params):
    status_code = 200
    if status in (200, 201):
        status_code = status
        status = 'ok'
    params['status'] = status
    response = jsonp(params)
    response.status_code = status_code
    response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response


# --- Client access endpoints -------------------------------------------------

@lastuser_oauth.route('/api/1/token/verify', methods=['POST'])
@requires_client_login
def token_verify():
    token = request.form.get('access_token')
    client_resource = request.form.get('resource')  # Can only be a single resource
    if not client_resource:
        # No resource specified by caller
        return resource_error('no_resource')
    if not token:
        # No token specified by caller
        return resource_error('no_token')

    authtoken = AuthToken.query.filter_by(token=token).first()
    if not authtoken:
        # No such auth token
        return api_result('error', error='no_token')
    if g.client.namespace + ':' + client_resource not in authtoken.scope:
        # Token does not grant access to this resource
        return api_result('error', error='access_denied')
    if '/' in client_resource:
        parts = client_resource.split('/')
        if len(parts) != 2:
            return api_result('error', error='invalid_scope')
        resource_name, action_name = parts
    else:
        resource_name = client_resource
        action_name = None
    resource = Resource.query.filter_by(name=resource_name).first()
    if not resource or resource.client != g.client:
        # Resource does not exist or does not belong to this client
        return api_result('error', error='access_denied')
    if action_name:
        action = ResourceAction.query.filter_by(name=action_name, resource=resource).first()
        if not action:
            return api_result('error', error='access_denied')

    # All validations passed. Token is valid for this client and scope. Return with information on the token
    # TODO: Don't return validity. Set the HTTP cache headers instead.
    params = {'validity': 120}  # Period (in seconds) for which this assertion may be cached.
    if authtoken.user:
        params['userinfo'] = get_userinfo(authtoken.user, g.client, scope=authtoken.scope)
    params['clientinfo'] = {
        'title': authtoken.client.title,
        'userid': authtoken.client.user.userid,
        'buid': authtoken.client.user.userid,
        'owner_title': authtoken.client.owner_title,
        'website': authtoken.client.website,
        'key': authtoken.client.key,
        'trusted': authtoken.client.trusted,
        }
    return api_result('ok', **params)


@lastuser_oauth.route('/api/1/resource/sync', methods=['POST'])
@requires_client_login
def sync_resources():
    resources = request.get_json().get('resources', [])
    actions_list = {}
    results = {}

    for name in resources:
        if '/' in name:
            parts = name.split('/')
            if len(parts) != 2:
                results[name] = {'status': 'error', 'error': u"Invalid resource name {name}".format(name=name)}
                continue
            resource_name, action_name = parts
        else:
            resource_name = name
            action_name = None
        description = resources[name].get('description')
        siteresource = getbool(resources[name].get('siteresource'))
        restricted = getbool(resources[name].get('restricted'))
        actions_list.setdefault(resource_name, [])
        resource = Resource.get(name=resource_name, client=g.client)
        if resource:
            results[resource.name] = {'status': 'exists', 'actions': {}}
            if not action_name and resource.description != description:
                resource.description = description
                results[resource.name]['status'] = 'updated'
            if not action_name and resource.siteresource != siteresource:
                resource.siteresource = siteresource
                results[resource.name]['status'] = 'updated'
            if not action_name and resource.restricted != restricted:
                resource.restricted = restricted
                results[resource.name]['status'] = 'updated'
        else:
            resource = Resource(client=g.client, name=resource_name,
                title=resources.get(resource_name, {}).get('title') or resource_name.title(),
                description=resources.get(resource_name, {}).get('description') or u'')
            db.session.add(resource)
            results[resource.name] = {'status': 'added', 'actions': {}}

        if action_name:
            if action_name not in actions_list[resource_name]:
                actions_list[resource_name].append(action_name)
            action = resource.get_action(name=action_name)
            if action:
                if description != action.description:
                    action.description = description
                    results[resource.name]['actions'][action.name] = {'status': 'updated'}
                else:
                    results[resource.name]['actions'][action.name] = {'status': 'exists'}
            else:
                action = ResourceAction(resource=resource, name=action_name,
                    title=resources[name].get('title') or action_name.title() + " " + resource.title,
                    description=description)
                db.session.add(action)
                results[resource.name]['actions'][action.name] = {'status': 'added'}

    # Deleting resources & actions not defined in client application.
    for resource_name in actions_list:
        resource = Resource.get(name=resource_name, client=g.client)
        actions = ResourceAction.query.filter(~ResourceAction.name.in_(actions_list[resource_name]), ResourceAction.resource==resource)
        for action in actions.all():
            results[resource_name]['actions'][action.name] = {'status': 'deleted'}
        actions.delete(synchronize_session='fetch')
    del_resources = Resource.query.filter(~Resource.name.in_(actions_list.keys()), Resource.client==g.client)
    for resource in del_resources.all():
        ResourceAction.query.filter_by(resource=resource).delete(synchronize_session='fetch')
        results[resource.name] = {'status': 'deleted'}
    del_resources.delete(synchronize_session='fetch')

    db.session.commit()
    
    return api_result('ok', results=results)


@lastuser_oauth.route('/api/1/user/get_by_userid', methods=['GET', 'POST'])
@requires_user_or_client_login
def user_get_by_userid():
    """
    Returns user or organization with the given userid (Lastuser internal userid)
    """
    userid = request.values.get('userid')
    if not userid:
        return api_result('error', error='no_userid_provided')
    user = User.get(userid=userid, defercols=True)
    if user:
        return api_result('ok',
            type='user',
            userid=user.userid,
            buid=user.userid,
            name=user.username,
            title=user.fullname,
            label=user.pickername,
            timezone=user.timezone,
            oldids=[o.userid for o in user.oldids])
    else:
        org = Organization.get(userid=userid, defercols=True)
        if org:
            return api_result('ok',
                type='organization',
                userid=org.userid,
                buid=org.userid,
                name=org.name,
                title=org.title,
                label=org.pickername)
    return api_result('error', error='not_found')


@lastuser_oauth.route('/api/1/user/get_by_userids', methods=['GET', 'POST'])
@requires_user_or_client_login
@requestargs('userid[]')
def user_get_by_userids(userid):
    """
    Returns users and organizations with the given userids (Lastuser internal userid).
    This is identical to get_by_userid but accepts multiple userids and returns a list
    of matching users and organizations
    """
    if not userid:
        return api_result('error', error='no_userid_provided')
    users = User.all(userids=userid)
    orgs = Organization.all(userids=userid)
    return api_result('ok',
        results=[
            {'type': 'user',
             'buid': u.userid,
             'userid': u.userid,
             'name': u.username,
             'title': u.fullname,
             'label': u.pickername,
             'timezone': u.timezone,
             'oldids': [o.userid for o in u.oldids]} for u in users] + [
            {'type': 'organization',
             'buid': o.userid,
             'userid': o.userid,
             'name': o.name,
             'title': o.fullname,
             'label': o.pickername} for o in orgs]
        )


@lastuser_oauth.route('/api/1/user/get', methods=['GET', 'POST'])
@requires_user_or_client_login
@requestargs('name')
def user_get(name):
    """
    Returns user with the given username, email address or Twitter id
    """
    if not name:
        return api_result('error', error='no_name_provided')
    user = getuser(name)
    if user:
        return api_result('ok',
            type='user',
            userid=user.userid,
            buid=user.userid,
            name=user.username,
            title=user.fullname,
            label=user.pickername,
            timezone=user.timezone,
            oldids=[o.userid for o in user.oldids])
    else:
        return api_result('error', error='not_found')


@lastuser_oauth.route('/api/1/user/getusers', methods=['GET', 'POST'])
@requires_user_or_client_login
@requestargs('name[]')
def user_getall(name):
    """
    Returns users with the given username, email address or Twitter id
    """
    names = name
    userids = set()  # Dupe checker
    if not names:
        return api_result('error', error='no_name_provided')
    results = []
    for name in names:
        user = getuser(name)
        if user and user.userid not in userids:
            results.append({
                'type': 'user',
                'userid': user.userid,
                'buid': user.userid,
                'name': user.username,
                'title': user.fullname,
                'label': user.pickername,
                'timezone': user.timezone,
                'oldids': [o.userid for o in user.oldids],
                })
            userids.add(user.userid)
    if not results:
        return api_result('error', error='not_found')
    else:
        return api_result('ok', results=results)


@lastuser_oauth.route('/api/1/user/autocomplete', methods=['GET', 'POST'])
@requires_user_or_client_login
def user_autocomplete():
    """
    Returns users (userid, username, fullname, twitter, github or email) matching the search term.
    """
    q = request.values.get('q', '')
    if not q:
        return api_result('error', error='no_query_provided')
    users = User.autocomplete(q)
    result = [{
        'userid': u.userid,
        'buid': u.userid,
        'name': u.username,
        'title': u.fullname,
        'label': u.pickername} for u in users]
    return api_result('ok', users=result)


# This is org/* instead of organizations/* because it's a client resource. TODO: Reconsider
# DEPRECATED, to be removed soon
@lastuser_oauth.route('/api/1/org/get_teams', methods=['GET', 'POST'])
@requires_client_login
def org_team_get():
    """
    Returns a list of teams in the given organization.
    """
    if not g.client.team_access:
        return api_result('error', error='no_team_access')
    org_userids = request.values.getlist('org')
    if not org_userids:
        return api_result('error', error='no_org_provided')
    organizations = Organization.all(userids=org_userids)
    if not organizations:
        return api_result('error', error='no_such_organization')
    orgteams = {}
    for org in organizations:
        # If client has access to team information, make a list of teams.
        # XXX: Should trusted clients have access anyway? Will this be an abuse
        # of the trusted flag? It was originally meant to only bypass user authorization
        # on login to HasGeek websites as that would have been very confusing to users.
        # XXX: Return user list here?
        if g.client in org.clients_with_team_access():
            orgteams[org.userid] = [{'userid': team.userid,
                                     'org': org.userid,
                                     'title': team.title,
                                     'owners': team == org.owners} for team in org.teams]
    return api_result('ok', org_teams=orgteams)


# --- Token-based resource endpoints ------------------------------------------

@lastuser_oauth.route('/api/1/id')
@resource_registry.resource('id', u"Read your name and username")
def resource_id(authtoken, args, files=None):
    """
    Return user's id
    """
    if 'all' in args and getbool(args['all']):
        return get_userinfo(authtoken.user, authtoken.client, scope=authtoken.scope, get_permissions=True)
    else:
        return get_userinfo(authtoken.user, authtoken.client, scope=['id'], get_permissions=False)


@lastuser_oauth.route('/api/1/session/verify', methods=['POST'])
@resource_registry.resource('session/verify', u"Verify user session", scope='id')
def session_verify(authtoken, args, files=None):
    sessionid = args['sessionid']
    session = UserSession.authenticate(buid=sessionid)
    if session and session.user == authtoken.user:
        session.access(api=True)
        db.session.commit()
        return {
            'active': True,
            'sessionid': session.buid,
            'userid': session.user.userid,
            'sudo': session.has_sudo,
            }
    else:
        return {'active': False}


@lastuser_oauth.route('/api/1/email')
@resource_registry.resource('email', u"Read your email address")
def resource_email(authtoken, args, files=None):
    """
    Return user's email addresses.
    """
    if 'all' in args and getbool(args['all']):
        return {'email': unicode(authtoken.user.email),
                'all': [unicode(email) for email in authtoken.user.emails]}
    else:
        return {'email': unicode(authtoken.user.email)}


@lastuser_oauth.route('/api/1/email/add', methods=['POST'])
@resource_registry.resource('email/add', u"Add an email address to your profile")
def resource_email_add(authtoken, args, files=None):
    """
    TODO: Add an email address to the user's profile.
    """
    email = args['email']
    return {'email': email}  # TODO


@lastuser_oauth.route('/api/1/phone')
@resource_registry.resource('phone', u"Read your phone number")
def resource_phone(authtoken, args, files=None):
    """
    Return user's phone numbers.
    """
    if 'all' in args and getbool(args['all']):
        return {'phone': unicode(authtoken.user.phone),
                'all': [unicode(phone) for phone in authtoken.user.phones]}
    else:
        return {'phone': unicode(authtoken.user.phone)}


@lastuser_oauth.route('/api/1/user/externalids')
@resource_registry.resource('user/externalids', u"Access your external account information such as Twitter and Google", trusted=True)
def resource_login_providers(authtoken, args, files=None):
    """
    Return user's login providers' data.
    """
    service = args.get('service')
    response = {}
    for extid in authtoken.user.externalids:
        if service is None or extid.service == service:
            response[extid.service] = {
                "userid": unicode(extid.userid),
                "username": unicode(extid.username),
                "oauth_token": unicode(extid.oauth_token),
                "oauth_token_secret": unicode(extid.oauth_token_secret),
                "oauth_token_type": unicode(extid.oauth_token_type)
            }
    return response


@lastuser_oauth.route('/api/1/organizations')
@resource_registry.resource('organizations', u"Read the organizations you are a member of")
def resource_organizations(authtoken, args, files=None):
    """
    Return user's organizations and teams that they are a member of.
    """
    return get_userinfo(authtoken.user, authtoken.client, scope=['organizations'], get_permissions=False)


@lastuser_oauth.route('/api/1/teams')
@resource_registry.resource('teams', u"Read the list of teams in your organizations")
def resource_teams(authtoken, args, files=None):
    """
    Return user's organizations' teams.
    """
    return get_userinfo(authtoken.user, authtoken.client, scope=['teams'], get_permissions=False)


@lastuser_oauth.route('/api/1/notice/send')
@resource_registry.resource('notice/send', u"Send you notifications")
def resource_notice_send(authtoken, args, files=None):
    pass

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-

from urlparse import urlparse

import wtforms
import wtforms.fields.html5
from baseframe.forms import Form
from coaster import valid_username

from lastuser_core.models import Permission, Resource, getuser, Organization
from lastuser_core import resource_registry


class ConfirmDeleteForm(Form):
    """
    Confirm a delete operation
    """
    delete = wtforms.SubmitField('Delete')
    cancel = wtforms.SubmitField('Cancel')


class RegisterClientForm(Form):
    """
    Register a new OAuth client application
    """
    title = wtforms.TextField('Application title', validators=[wtforms.validators.Required()],
        description="The name of your application")
    description = wtforms.TextAreaField('Description', validators=[wtforms.validators.Required()],
        description="A description to help users recognize your application")
    client_owner = wtforms.RadioField('Owner', validators=[wtforms.validators.Required()],
        description="User or organization that owns this application. Changing the owner "
            "will revoke all currently assigned permissions for this app")
    website = wtforms.fields.html5.URLField('Application website', validators=[wtforms.validators.Required(), wtforms.validators.URL()],
        description="Website where users may access this application")
    redirect_uri = wtforms.fields.html5.URLField('Redirect URL', validators=[wtforms.validators.Optional(), wtforms.validators.URL()],
        description="OAuth2 Redirect URL")
    notification_uri = wtforms.fields.html5.URLField('Notification URL', validators=[wtforms.validators.Optional(), wtforms.validators.URL()],
        description="When the user's data changes, Lastuser will POST a notice to this URL. "
            "Other notices may be posted too")
    iframe_uri = wtforms.fields.html5.URLField('IFrame URL', validators=[wtforms.validators.Optional(), wtforms.validators.URL()],
        description="Front-end notifications URL. This is loaded in a hidden iframe to notify the app that the "
            "user updated their profile in some way (not yet implemented)")
    resource_uri = wtforms.fields.html5.URLField('Resource URL', validators=[wtforms.validators.Optional(), wtforms.validators.URL()],
        description="URL at which this application provides resources as per the Lastuser Resource API "
            "(not yet implemented)")
    namespace = wtforms.TextField('Client namespace', validators=[wtforms.validators.Required()],
        description="A dot-based namespace that uniquely identifies your client application and provides external clients access to resources. For example, if your client website is http://funnel.hasgeek.com, use 'com.hasgeek.funnel'.")
    allow_any_login = wtforms.BooleanField('Allow anyone to login', default=True,
        description="If your application requires access to be restricted to specific users, uncheck this, "
            "and only users who have been assigned a permission to the app will be able to login")
    team_access = wtforms.BooleanField('Requires access to teams', default=False,
        description="If your application is capable of assigning access permissions to teams, check this. "
            "Organization owners will then able to grant access to teams in their organizations")

    def validate_client_owner(self, field):
        if field.data == self.edit_user.userid:
            self.user = self.edit_user
            self.org = None
        else:
            orgs = [org for org in self.edit_user.organizations_owned() if org.userid == field.data]
            if len(orgs) != 1:
                raise wtforms.ValidationError("Invalid owner")
            self.user = None
            self.org = orgs[0]

    def _urls_match(self, url1, url2):
        p1 = urlparse(url1)
        p2 = urlparse(url2)
        return (p1.netloc == p2.netloc) and (p1.scheme == p2.scheme) and (
            p1.username == p2.username) and (p1.password == p2.password)

    def validate_redirect_uri(self, field):
        if not self._urls_match(self.website.data, field.data):
            raise wtforms.ValidationError("The scheme, domain and port must match that of the website URL")

    def validate_notification_uri(self, field):
        if not self._urls_match(self.website.data, field.data):
            raise wtforms.ValidationError("The scheme, domain and port must match that of the website URL")

    def validate_resource_uri(self, field):
        if not self._urls_match(self.website.data, field.data):
            raise wtforms.ValidationError("The scheme, domain and port must match that of the website URL")

    def validate_namespace(self, field):
        client = self.edit_model.get(namespace=field.data)
        if client:
            if client == self.edit_obj:
                return
            raise wtforms.ValidationError("This namespace has been claimed by another client app")


class PermissionForm(Form):
    """
    Create or edit a permission
    """
    name = wtforms.TextField('Permission name', validators=[wtforms.validators.Required()],
        description='Name of the permission as a single word in lower case. '
            'This is passed to the application when a user logs in. '
            'Changing the name will not automatically update it everywhere. '
            'You must reassign the permission to users who had it with the old name')
    title = wtforms.TextField('Title', validators=[wtforms.validators.Required()],
        description='Permission title that is displayed to users')
    description = wtforms.TextAreaField('Description',
        description='An optional description of what the permission is for')
    context = wtforms.RadioField('Context', validators=[wtforms.validators.Required()],
        description='Context where this permission is available')

    def validate(self):
        rv = super(PermissionForm, self).validate()
        if not rv:
            return False

        if not valid_username(self.name.data):
            self.name.errors.append("Name contains invalid characters")
            return False

        existing = Permission.get(name=self.name.data, allusers=True)
        if existing and existing.id != self.edit_id:
            self.name.errors.append("A global permission with that name already exists")
            return False

        if self.context.data == self.edit_user.userid:
            existing = Permission.get(name=self.name.data, user=self.edit_user)
        else:
            org = Organization.get(userid=self.context.data)
            if org:
                existing = Permission.get(name=self.name.data, org=org)
            else:
                existing = None
        if existing and existing.id != self.edit_id:
            self.name.errors.append("You have another permission with the same name")
            return False

        return True

    def validate_context(self, field):
        if field.data == self.edit_user.userid:
            self.user = self.edit_user
            self.org = None
        else:
            orgs = [org for org in self.edit_user.organizations_owned() if org.userid == field.data]
            if len(orgs) != 1:
                raise wtforms.ValidationError("Invalid context")
            self.user = None
            self.org = orgs[0]


class UserPermissionAssignForm(Form):
    """
    Assign permissions to a user
    """
    username = wtforms.TextField("User", validators=[wtforms.validators.Required()],
        description='Lookup a user by their username or email address')
    perms = wtforms.SelectMultipleField("Permissions", validators=[wtforms.validators.Required()])

    def validate_username(self, field):
        existing = getuser(field.data)
        if existing is None:
            raise wtforms.ValidationError("User does not exist")
        self.user = existing


class TeamPermissionAssignForm(Form):
    """
    Assign permissions to a team
    """
    team_id = wtforms.RadioField("Team", validators=[wtforms.validators.Required()],
        description='Select a team to assign permissions to')
    perms = wtforms.SelectMultipleField("Permissions", validators=[wtforms.validators.Required()])

    def validate_team_id(self, field):
        teams = [team for team in self.org.teams if team.userid == field.data]
        if len(teams) != 1:
            raise wtforms.ValidationError("Unknown team")
        self.team = teams[0]


class PermissionEditForm(Form):
    """
    Edit a user or team's permissions
    """
    perms = wtforms.SelectMultipleField("Permissions", validators=[wtforms.validators.Required()])


class ResourceForm(Form):
    """
    Edit a resource provided by an application
    """
    name = wtforms.TextField('Resource name', validators=[wtforms.validators.Required()],
        description="Name of the resource as a single word in lower case. "
            "This is provided by applications as part of the scope "
            "when requesting access to a user's resources.")
    title = wtforms.TextField('Title', validators=[wtforms.validators.Required()],
        description='Resource title that is displayed to users')
    description = wtforms.TextAreaField('Description',
        description='An optional description of what the resource is')
    siteresource = wtforms.BooleanField('Site resource',
        description='Enable if this resource is generic to the site and not owned by specific users')
    restricted = wtforms.BooleanField('Restrict access to your apps',
        description='Enable if access to the resource should be restricted to client apps '
            'that share the same owner. You may want to do this for sensitive resources '
            'that should only be available to your own apps')

    def validate_name(self, field):
        if not valid_username(field.data):
            raise wtforms.ValidationError("Name contains invalid characters.")

        if field.data in resource_registry:
            raise wtforms.ValidationError("This name is reserved for internal use")

        existing = Resource.get(name=field.data, client=self.client)
        if existing and existing.id != self.edit_id:
            raise wtforms.ValidationError("A resource with that name already exists")


class ResourceActionForm(Form):
    """
    Edit an action associated with a resource
    """
    name = wtforms.TextField('Action name', validators=[wtforms.validators.Required()],
        description="Name of the action as a single word in lower case. "
            "This is provided by applications as part of the scope in the form "
            "'resource/action' when requesting access to a user's resources. "
            "Read actions are implicit when applications request just 'resource' "
            "in the scope and do not need to be specified as an explicit action.")
    title = wtforms.TextField('Title', validators=[wtforms.validators.Required()],
        description='Action title that is displayed to users')
    description = wtforms.TextAreaField('Description',
        description='An optional description of what the action is')

    def validate_name(self, field):
        if not valid_username(field.data):
            raise wtforms.ValidationError("Name contains invalid characters.")

        existing = self.edit_resource.get_action(field.data)
        if existing and existing.id != self.edit_id:
            raise wtforms.ValidationError("An action with that name already exists for this resource")


class ClientTeamAccessForm(Form):
    """
    Select organizations that the client has access to the teams of
    """
    organizations = wtforms.SelectMultipleField('Organizations')

########NEW FILE########
__FILENAME__ = org
# -*- coding: utf-8 -*-

from flask import current_app
import wtforms
from coaster import valid_username
from baseframe.forms import Form, HiddenMultiField

from lastuser_core.models import User, Organization


class OrganizationForm(Form):
    title = wtforms.TextField('Organization name', validators=[wtforms.validators.Required()])
    name = wtforms.TextField('Username', validators=[wtforms.validators.Required()])

    def validate_name(self, field):
        if not valid_username(field.data):
            raise wtforms.ValidationError("Invalid characters in name")
        if field.data in current_app.config['RESERVED_USERNAMES']:
            raise wtforms.ValidationError("That name is reserved")
        existing = User.get(username=field.data)
        if existing is not None:
            raise wtforms.ValidationError("That name is taken")
        existing = Organization.get(name=field.data)
        if existing is not None and existing.id != self.edit_id:
            raise wtforms.ValidationError("That name is taken")


class TeamForm(Form):
    title = wtforms.TextField('Team name', validators=[wtforms.validators.Required()])
    users = HiddenMultiField('Users', validators=[wtforms.validators.Required()])

########NEW FILE########
__FILENAME__ = profile
# -*- coding: utf-8 -*-

from flask import g
import wtforms
import wtforms.fields.html5
from baseframe.forms import Form, ValidEmailDomain

from lastuser_core.utils import strip_phone, valid_phone
from lastuser_core.models import UserEmail, UserEmailClaim, UserPhone, UserPhoneClaim


class NewEmailAddressForm(Form):
    email = wtforms.fields.html5.EmailField('Email address', validators=[wtforms.validators.Required(), wtforms.validators.Email(), ValidEmailDomain()])

    # TODO: Move to function and place before ValidEmailDomain()
    def validate_email(self, field):
        field.data = field.data.lower()  # Convert to lowercase
        existing = UserEmail.get(email=field.data)
        if existing is not None:
            if existing.user == g.user:
                raise wtforms.ValidationError("You have already registered this email address.")
            else:
                raise wtforms.ValidationError("This email address has already been claimed.")
        existing = UserEmailClaim.get(email=field.data, user=g.user)
        if existing is not None:
            raise wtforms.ValidationError("This email address is pending verification.")


class NewPhoneForm(Form):
    phone = wtforms.TextField('Phone number', default='+91', validators=[wtforms.validators.Required()],
        description="Indian mobile numbers only")

    def validate_phone(self, field):
        existing = UserPhone.get(phone=field.data)
        if existing is not None:
            if existing.user == g.user:
                raise wtforms.ValidationError("You have already registered this phone number.")
            else:
                raise wtforms.ValidationError("That phone number has already been claimed.")
        existing = UserPhoneClaim.get(phone=field.data, user=g.user)
        if existing is not None:
            raise wtforms.ValidationError("That phone number is pending verification.")
        # Step 1: Remove punctuation in number
        field.data = strip_phone(field.data)
        # Step 2: Validate number format
        if not valid_phone(field.data):
            raise wtforms.ValidationError("Invalid phone number (must be in international format with a leading + symbol)")
        # Step 3: Check if Indian number (startswith('+91'))
        if not field.data.startswith('+91') or len(field.data) != 13:
            raise wtforms.ValidationError("Only Indian mobile numbers are allowed at this time")


class VerifyPhoneForm(Form):
    verification_code = wtforms.TextField('Verification code', validators=[wtforms.validators.Required()])

    def validate_verification_code(self, field):
        if self.phoneclaim.verification_code != field.data:
            raise wtforms.ValidationError("Verification code does not match.")

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-

from flask import g, request, render_template, url_for, flash, abort
from coaster.views import load_model, load_models
from baseframe.forms import render_form, render_redirect, render_delete_sqla

from lastuser_core.models import (db, User, Client, Organization, Team, Permission,
    UserClientPermissions, TeamClientPermissions, Resource, ResourceAction, ClientTeamAccess,
    CLIENT_TEAM_ACCESS)
from lastuser_oauth.views.helpers import requires_login
from .. import lastuser_ui
from ..forms import (RegisterClientForm, PermissionForm, UserPermissionAssignForm,
    TeamPermissionAssignForm, PermissionEditForm, ResourceForm, ResourceActionForm, ClientTeamAccessForm)

# --- Routes: client apps -----------------------------------------------------


@lastuser_ui.route('/apps')
def client_list():
    if g.user:
        return render_template('client_list.html', clients=Client.query.filter(db.or_(Client.user == g.user,
            Client.org_id.in_(g.user.organizations_owned_ids()))).order_by('title').all())
    else:
        # TODO: Show better UI for non-logged in users
        return render_template('client_list.html', clients=[])


@lastuser_ui.route('/apps/all')
def client_list_all():
    return render_template('client_list.html', clients=Client.query.order_by('title').all())


def available_client_owners():
    """
    Return a list of possible client owners for the current user.
    """
    choices = []
    choices.append((g.user.userid, g.user.pickername))
    for org in g.user.organizations_owned():
        choices.append((org.userid, org.pickername))
    return choices


@lastuser_ui.route('/apps/new', methods=['GET', 'POST'])
@requires_login
def client_new():
    form = RegisterClientForm(model=Client)
    form.edit_user = g.user
    form.client_owner.choices = available_client_owners()
    if request.method == 'GET':
        form.client_owner.data = g.user.userid

    if form.validate_on_submit():
        client = Client()
        form.populate_obj(client)
        client.user = form.user
        client.org = form.org
        client.trusted = False
        db.session.add(client)
        db.session.commit()
        return render_redirect(url_for('.client_info', key=client.key), code=303)

    return render_form(form=form, title="Register a new client application",
        formid="client_new", submit="Register application", ajax=True)


@lastuser_ui.route('/apps/<key>')
@load_model(Client, {'key': 'key'}, 'client', permission='view')
def client_info(client):
    if client.user:
        permassignments = UserClientPermissions.query.filter_by(client=client).all()
    else:
        permassignments = TeamClientPermissions.query.filter_by(client=client).all()
    resources = Resource.query.filter_by(client=client).order_by('name').all()
    return render_template('client_info.html', client=client,
        permassignments=permassignments,
        resources=resources)


@lastuser_ui.route('/apps/<key>/edit', methods=['GET', 'POST'])
@requires_login
@load_model(Client, {'key': 'key'}, 'client', permission='edit')
def client_edit(client):
    form = RegisterClientForm(obj=client, model=Client)
    form.edit_user = g.user
    form.client_owner.choices = available_client_owners()
    if request.method == 'GET':
        if client.user:
            form.client_owner.data = client.user.userid
        else:
            form.client_owner.data = client.org.userid

    if form.validate_on_submit():
        if client.user != form.user or client.org != form.org:
            # Ownership has changed. Remove existing permission assignments
            for perm in UserClientPermissions.query.filter_by(client=client).all():
                db.session.delete(perm)
            for perm in TeamClientPermissions.query.filter_by(client=client).all():
                db.session.delete(perm)
            flash("This application’s owner has changed, so all previously assigned permissions "
                "have been revoked", "warning")
        form.populate_obj(client)
        client.user = form.user
        client.org = form.org
        if not client.team_access:
            # This client does not have access to teams in organizations. Remove all existing assignments
            for cta in ClientTeamAccess.query.filter_by(client=client).all():
                db.session.delete(cta)
        db.session.commit()
        return render_redirect(url_for('.client_info', key=client.key), code=303)

    return render_form(form=form, title="Edit application", formid="client_edit",
        submit="Save changes", ajax=True)


@lastuser_ui.route('/apps/<key>/delete', methods=['GET', 'POST'])
@requires_login
@load_model(Client, {'key': 'key'}, 'client', permission='delete')
def client_delete(client):
    return render_delete_sqla(client, db, title=u"Confirm delete", message=u"Delete application ‘{title}’? ".format(
            title=client.title),
        success=u"You have deleted application ‘{title}’ and all its associated resources and permission assignments".format(
            title=client.title),
        next=url_for('.client_list'))


# --- Routes: user permissions ------------------------------------------------


@lastuser_ui.route('/perms')
@requires_login
def permission_list():
    allperms = Permission.query.filter_by(allusers=True).order_by('name').all()
    userperms = Permission.query.filter(
        db.or_(Permission.user_id == g.user.id,
               Permission.org_id.in_(g.user.organizations_owned_ids()))
        ).order_by('name').all()
    return render_template('permission_list.html', allperms=allperms, userperms=userperms)


@lastuser_ui.route('/perms/new', methods=['GET', 'POST'])
@requires_login
def permission_new():
    form = PermissionForm()
    form.edit_user = g.user
    form.context.choices = available_client_owners()
    if request.method == 'GET':
        form.context.data = g.user.userid
    if form.validate_on_submit():
        perm = Permission()
        form.populate_obj(perm)
        perm.user = form.user
        perm.org = form.org
        perm.allusers = False
        db.session.add(perm)
        db.session.commit()
        flash("Your new permission has been defined", 'success')
        return render_redirect(url_for('.permission_list'), code=303)
    return render_form(form=form, title="Define a new permission", formid="perm_new",
        submit="Define new permission", ajax=True)


@lastuser_ui.route('/perms/<int:id>/edit', methods=['GET', 'POST'])
@requires_login
@load_model(Permission, {'id': 'id'}, 'perm', permission='edit')
def permission_edit(perm):
    form = PermissionForm(obj=perm)
    form.edit_user = g.user
    form.context.choices = available_client_owners()
    if request.method == 'GET':
        if perm.user:
            form.context.data = perm.user.userid
        else:
            form.context.data = perm.org.userid
    if form.validate_on_submit():
        form.populate_obj(perm)
        perm.user = form.user
        perm.org = form.org
        db.session.commit()
        flash("Your permission has been saved", 'success')
        return render_redirect(url_for('.permission_list'), code=303)
    return render_form(form=form, title="Edit permission", formid="perm_edit",
        submit="Save changes", ajax=True)


@lastuser_ui.route('/perms/<int:id>/delete', methods=['GET', 'POST'])
@requires_login
@load_model(Permission, {'id': 'id'}, 'perm', permission='delete')
def permission_delete(perm):
    return render_delete_sqla(perm, db, title=u"Confirm delete", message=u"Delete permission ‘{name}’?".format(name=perm.name),
        success="Your permission has been deleted",
        next=url_for('.permission_list'))


# --- Routes: client app permissions ------------------------------------------


@lastuser_ui.route('/apps/<key>/perms/new', methods=['GET', 'POST'])
@requires_login
@load_model(Client, {'key': 'key'}, 'client', permission='assign-permissions')
def permission_user_new(client):
    if client.user:
        available_perms = Permission.query.filter(db.or_(
            Permission.allusers == True,
            Permission.user == g.user)).order_by('name').all()
        form = UserPermissionAssignForm()
    elif client.org:
        available_perms = Permission.query.filter(db.or_(
            Permission.allusers == True,
            Permission.org == client.org)).order_by('name').all()
        form = TeamPermissionAssignForm()
        form.org = client.org
        form.team_id.choices = [(team.userid, team.title) for team in client.org.teams]
    else:
        abort(403)  # This should never happen. Clients always have an owner.
    form.perms.choices = [(ap.name, u"{name} – {title}".format(name=ap.name, title=ap.title)) for ap in available_perms]
    if form.validate_on_submit():
        perms = set()
        if client.user:
            permassign = UserClientPermissions.query.filter_by(user=form.user, client=client).first()
            if permassign:
                perms.update(permassign.access_permissions.split(u' '))
            else:
                permassign = UserClientPermissions(user=form.user, client=client)
                db.session.add(permassign)
        else:
            permassign = TeamClientPermissions.query.filter_by(team=form.team, client=client).first()
            if permassign:
                perms.update(permassign.access_permissions.split(u' '))
            else:
                permassign = TeamClientPermissions(team=form.team, client=client)
                db.session.add(permassign)
        perms.update(form.perms.data)
        permassign.access_permissions = u' '.join(sorted(perms))
        db.session.commit()
        if client.user:
            flash(u"Permissions have been assigned to user {pname}".format(pname=form.user.pickername), 'success')
        else:
            flash(u"Permissions have been assigned to team ‘{pname}’".format(pname=permassign.team.pickername), 'success')
        return render_redirect(url_for('.client_info', key=client.key), code=303)
    return render_form(form=form, title="Assign permissions", formid="perm_assign", submit="Assign permissions", ajax=True)


@lastuser_ui.route('/apps/<key>/perms/<userid>/edit', methods=['GET', 'POST'])
@requires_login
@load_model(Client, {'key': 'key'}, 'client', permission='assign-permissions', kwargs=True)
def permission_user_edit(client, kwargs):
    if client.user:
        user = User.get(userid=kwargs['userid'])
        if not user:
            abort(404)
        available_perms = Permission.query.filter(db.or_(
            Permission.allusers == True,
            Permission.user == g.user)).order_by('name').all()
        permassign = UserClientPermissions.query.filter_by(user=user, client=client).first_or_404()
    elif client.org:
        team = Team.get(userid=kwargs['userid'])
        if not team:
            abort(404)
        available_perms = Permission.query.filter(db.or_(
            Permission.allusers == True,
            Permission.org == client.org)).order_by('name').all()
        permassign = TeamClientPermissions.query.filter_by(team=team, client=client).first_or_404()
    form = PermissionEditForm()
    form.perms.choices = [(ap.name, u"{name} – {title}".format(name=ap.name, title=ap.title)) for ap in available_perms]
    if request.method == 'GET':
        if permassign:
            form.perms.data = permassign.access_permissions.split(u' ')
    if form.validate_on_submit():
        form.perms.data.sort()
        perms = u' '.join(form.perms.data)
        if not perms:
            db.session.delete(permassign)
        else:
            permassign.access_permissions = perms
        db.session.commit()
        if perms:
            if client.user:
                flash(u"Permissions have been updated for user {pname}".format(pname=user.pickername), 'success')
            else:
                flash(u"Permissions have been updated for team {title}".format(title=team.title), 'success')
        else:
            if client.user:
                flash(u"All permissions have been revoked for user {pname}".format(pname=user.pickername), 'success')
            else:
                flash(u"All permissions have been revoked for team {title}".format(title=team.title), 'success')
        return render_redirect(url_for('.client_info', key=client.key), code=303)
    return render_form(form=form, title="Edit permissions", formid="perm_edit", submit="Save changes", ajax=True)


@lastuser_ui.route('/apps/<key>/perms/<userid>/delete', methods=['GET', 'POST'])
@requires_login
@load_model(Client, {'key': 'key'}, 'client', permission='assign-permissions', kwargs=True)
def permission_user_delete(client, kwargs):
    if client.user:
        user = User.get(userid=kwargs['userid'])
        if not user:
            abort(404)
        permassign = UserClientPermissions.query.filter_by(user=user, client=client).first_or_404()
        return render_delete_sqla(permassign, db, title=u"Confirm delete", message=u"Remove all permissions assigned to user {pname} for app ‘{title}’?".format(
                pname=user.pickername, title=client.title),
            success=u"You have revoked permisions for user {pname}".format(pname=user.pickername),
            next=url_for('.client_info', key=client.key))
    else:
        team = Team.get(userid=kwargs['userid'])
        if not team:
            abort(404)
        permassign = TeamClientPermissions.query.filter_by(team=team, client=client).first_or_404()
        return render_delete_sqla(permassign, db, title=u"Confirm delete", message=u"Remove all permissions assigned to team ‘{pname}’ for app ‘{title}’?".format(
                pname=team.title, title=client.title),
            success=u"You have revoked permisions for team {title}".format(title=team.title),
            next=url_for('.client_info', key=client.key))


# --- Routes: client app resources --------------------------------------------

@lastuser_ui.route('/apps/<key>/resources/new', methods=['GET', 'POST'])
@requires_login
@load_model(Client, {'key': 'key'}, 'client', permission='new-resource')
def resource_new(client):
    form = ResourceForm()
    form.client = client
    form.edit_id = None
    if form.validate_on_submit():
        resource = Resource(client=client)
        form.populate_obj(resource)
        db.session.add(resource)
        db.session.commit()
        flash("Your new resource has been saved", 'success')
        return render_redirect(url_for('.client_info', key=client.key), code=303)
    return render_form(form=form, title="Define a resource", formid="resource_new", submit="Define resource", ajax=True)


@lastuser_ui.route('/apps/<key>/resources/<int:idr>/edit', methods=['GET', 'POST'])
@requires_login
@load_models(
    (Client, {'key': 'key'}, 'client'),
    (Resource, {'id': 'idr', 'client': 'client'}, 'resource'),
    permission='edit')
def resource_edit(client, resource):
    form = ResourceForm(obj=resource)
    form.client = client
    if form.validate_on_submit():
        form.populate_obj(resource)
        db.session.commit()
        flash("Your resource has been edited", 'success')
        return render_redirect(url_for('.client_info', key=client.key), code=303)
    return render_form(form=form, title="Edit resource", formid="resource_edit", submit="Save changes", ajax=True)


@lastuser_ui.route('/apps/<key>/resources/<int:idr>/delete', methods=['GET', 'POST'])
@requires_login
@load_models(
    (Client, {'key': 'key'}, 'client'),
    (Resource, {'id': 'idr', 'client': 'client'}, 'resource'),
    permission='delete')
def resource_delete(client, resource):
    return render_delete_sqla(resource, db, title=u"Confirm delete",
        message=u"Delete resource ‘{resource}’ from app ‘{client}’?".format(
            resource=resource.title, client=client.title),
        success=u"You have deleted resource ‘{resource}’ on app ‘{client}’".format(
            resource=resource.title, client=client.title),
        next=url_for('.client_info', key=client.key))


# --- Routes: resource actions ------------------------------------------------

@lastuser_ui.route('/apps/<key>/resources/<int:idr>/actions/new', methods=['GET', 'POST'])
@requires_login
@load_models(
    (Client, {'key': 'key'}, 'client'),
    (Resource, {'id': 'idr', 'client': 'client'}, 'resource'),
    permission='new-action')
def resource_action_new(client, resource):
    form = ResourceActionForm()
    form.edit_id = None
    form.edit_resource = resource
    if form.validate_on_submit():
        action = ResourceAction(resource=resource)
        form.populate_obj(action)
        db.session.add(action)
        db.session.commit()
        flash("Your new action has been saved", 'success')
        return render_redirect(url_for('.client_info', key=client.key), code=303)
    return render_form(form=form, title="Define an action", formid="action_new", submit="Define action", ajax=True)


@lastuser_ui.route('/apps/<key>/resources/<int:idr>/actions/<int:ida>/edit', methods=['GET', 'POST'])
@requires_login
@load_models(
    (Client, {'key': 'key'}, 'client'),
    (Resource, {'id': 'idr', 'client': 'client'}, 'resource'),
    (ResourceAction, {'id': 'ida', 'resource': 'resource'}, 'action'),
    permission='edit')
def resource_action_edit(client, resource, action):
    form = ResourceActionForm(obj=action)
    form.edit_resource = resource
    if form.validate_on_submit():
        form.populate_obj(action)
        db.session.commit()
        flash("Your action has been edited", 'success')
        return render_redirect(url_for('.client_info', key=client.key), code=303)
    return render_form(form=form, title="Edit action", formid="action_edit", submit="Save changes", ajax=True)


@lastuser_ui.route('/apps/<key>/resources/<int:idr>/actions/<int:ida>/delete', methods=['GET', 'POST'])
@requires_login
@load_models(
    (Client, {'key': 'key'}, 'client'),
    (Resource, {'id': 'idr', 'client': 'client'}, 'resource'),
    (ResourceAction, {'id': 'ida', 'resource': 'resource'}, 'action'),
    permission='delete')
def resource_action_delete(client, resource, action):
    return render_delete_sqla(action, db, title="Confirm delete",
        message=u"Delete action ‘{action}’ from resource ‘{resource}’ of app ‘{client}’?".format(
            action=action.title, resource=resource.title, client=client.title),
        success=u"You have deleted action ‘{action}’ on resource ‘{resource}’ of app ‘{client}’".format(
            action=action.title, resource=resource.title, client=client.title),
        next=url_for('.client_info', key=client.key))


# --- Routes: client team access ----------------------------------------------

@lastuser_ui.route('/apps/<key>/teams', methods=['GET', 'POST'])
@requires_login
@load_model(Client, {'key': 'key'}, 'client')
def client_team_access(client):
    form = ClientTeamAccessForm()
    user_orgs = g.user.organizations_owned()
    form.organizations.choices = [(org.userid, org.title) for org in user_orgs]
    org_selected = [org.userid for org in user_orgs if client in org.clients_with_team_access()]
    if request.method == 'GET':
        form.organizations.data = org_selected
    if form.validate_on_submit():
        org_del = Organization.query.filter(Organization.userid.in_(
            set(org_selected) - set(form.organizations.data))).all()
        org_add = Organization.query.filter(Organization.userid.in_(
            set(form.organizations.data) - set(org_selected))).all()
        cta_del = ClientTeamAccess.query.filter_by(client=client).filter(
            ClientTeamAccess.org_id.in_([org.id for org in org_del])).all()
        for cta in cta_del:
            db.session.delete(cta)
        for org in org_add:
            cta = ClientTeamAccess(org=org, client=client, access_level=CLIENT_TEAM_ACCESS.ALL)
            db.session.add(cta)
        db.session.commit()
        flash("You have assigned access to teams in your organizations for this app.", 'success')
        return render_redirect(url_for('.client_info', key=client.key), code=303)
    return render_form(form=form, title="Select organizations", submit="Save", ajax=True)

########NEW FILE########
__FILENAME__ = index
# -*- coding: utf-8 -*-

from flask import render_template

from .. import lastuser_ui


@lastuser_ui.route('/')
def index():
    return render_template('index.html')

########NEW FILE########
__FILENAME__ = org
# -*- coding: utf-8 -*-

from flask import g, current_app, render_template, url_for, abort, redirect, make_response, request
from baseframe.forms import render_form, render_redirect, render_delete_sqla
from coaster.views import load_model, load_models

from lastuser_core.models import db, Organization, Team, User
from lastuser_core.signals import user_data_changed, org_data_changed, team_data_changed
from lastuser_oauth.views.helpers import requires_login
from .. import lastuser_ui
from ..forms.org import OrganizationForm, TeamForm

# --- Routes: Organizations ---------------------------------------------------


@lastuser_ui.route('/organizations')
@requires_login
def org_list():
    return render_template('org_list.html', organizations=g.user.organizations_owned())


@lastuser_ui.route('/organizations/new', methods=['GET', 'POST'])
@requires_login
def org_new():
    form = OrganizationForm()
    form.name.description = current_app.config.get('ORG_NAME_REASON')
    form.title.description = current_app.config.get('ORG_TITLE_REASON')
    if form.validate_on_submit():
        org = Organization()
        form.populate_obj(org)
        org.owners.users.append(g.user)
        db.session.add(org)
        db.session.commit()
        org_data_changed.send(org, changes=['new'], user=g.user)
        return render_redirect(url_for('.org_info', name=org.name), code=303)
    return render_form(form=form, title="New Organization", formid="org_new", submit="Create", ajax=False)


@lastuser_ui.route('/organizations/<name>')
@requires_login
@load_model(Organization, {'name': 'name'}, 'org', permission='view')
def org_info(org):
    return render_template('org_info.html', org=org)


@lastuser_ui.route('/organizations/<name>/edit', methods=['GET', 'POST'])
@requires_login
@load_model(Organization, {'name': 'name'}, 'org', permission='edit')
def org_edit(org):
    form = OrganizationForm(obj=org)
    form.name.description = current_app.config.get('ORG_NAME_REASON')
    form.title.description = current_app.config.get('ORG_TITLE_REASON')
    if form.validate_on_submit():
        form.populate_obj(org)
        db.session.commit()
        org_data_changed.send(org, changes=['edit'], user=g.user)
        return render_redirect(url_for('.org_info', name=org.name), code=303)
    return render_form(form=form, title="New Organization", formid="org_edit", submit="Save", ajax=False)


@lastuser_ui.route('/organizations/<name>/delete', methods=['GET', 'POST'])
@requires_login
@load_model(Organization, {'name': 'name'}, 'org', permission='delete')
def org_delete(org):
    if request.method == 'POST':
        # FIXME: Find a better way to do this
        org_data_changed.send(org, changes=['delete'], user=g.user)
    return render_delete_sqla(org, db, title=u"Confirm delete", message=u"Delete organization ‘{title}’? ".format(
            title=org.title),
        success=u"You have deleted organization ‘{title}’ and all its associated teams.".format(title=org.title),
        next=url_for('.org_list'))


@lastuser_ui.route('/organizations/<name>/teams')
@requires_login
@load_model(Organization, {'name': 'name'}, 'org', permission='view-teams')
def team_list(org):
    # There's no separate teams page at the moment
    return redirect(url_for('.org_info', name=org.name))


@lastuser_ui.route('/organizations/<name>/teams/new', methods=['GET', 'POST'])
@requires_login
@load_model(Organization, {'name': 'name'}, 'org', permission='new-team')
def team_new(org):
    form = TeamForm()
    if form.validate_on_submit():
        team = Team(org=org)
        team.title = form.title.data
        if form.users.data:
            team.users = User.query.filter(User.userid.in_(form.users.data)).all()
        db.session.add(team)
        db.session.commit()
        team_data_changed.send(team, changes=['new'], user=g.user)
        return render_redirect(url_for('.org_info', name=org.name), code=303)
    return make_response(render_template('edit_team.html', form=form, title=u"Create new team",
        formid='team_new', submit="Create"))


@lastuser_ui.route('/organizations/<name>/teams/<userid>', methods=['GET', 'POST'])
@requires_login
@load_models(
    (Organization, {'name': 'name'}, 'org'),
    (Team, {'org': 'org', 'userid': 'userid'}, 'team'),
    permission='edit'
    )
def team_edit(org, team):
    form = TeamForm(obj=team)
    if request.method == 'GET':
        form.users.data = [u.userid for u in team.users]
    if form.validate_on_submit():
        team.title = form.title.data
        if form.users.data:
            team.users = User.query.filter(User.userid.in_(form.users.data)).all()
        db.session.commit()
        team_data_changed.send(team, changes=['edit'], user=g.user)
        return render_redirect(url_for('.org_info', name=org.name), code=303)
    return make_response(render_template(u'edit_team.html', form=form,
        title=u"Edit team: {title}".format(title=team.title),
        formid='team_edit', submit="Save", ajax=False))


@lastuser_ui.route('/organizations/<name>/teams/<userid>/delete', methods=['GET', 'POST'])
@requires_login
@load_models(
    (Organization, {'name': 'name'}, 'org'),
    (Team, {'org': 'org', 'userid': 'userid'}, 'team'),
    permission='delete'
    )
def team_delete(org, team):
    if team == org.owners:
        abort(403)
    if request.method == 'POST':
        team_data_changed.send(team, changes=['delete'], user=g.user)
    return render_delete_sqla(team, db, title=u"Confirm delete", message=u"Delete team {title}?".format(title=team.title),
        success=u"You have deleted team ‘{team}’ from organization ‘{org}’.".format(team=team.title, org=org.title),
        next=url_for('.org_info', name=org.name))

########NEW FILE########
__FILENAME__ = profile
# -*- coding: utf-8 -*-

from flask import g, flash, render_template, url_for, request
from coaster.views import load_model
from baseframe.forms import render_form, render_redirect, render_delete_sqla

from lastuser_core.models import db, UserEmail, UserEmailClaim, UserPhone, UserPhoneClaim
from lastuser_core.signals import user_data_changed
from lastuser_oauth.mailclient import send_email_verify_link
from lastuser_oauth.views.helpers import requires_login
from lastuser_oauth.forms import PasswordResetForm, PasswordChangeForm
from .. import lastuser_ui
from ..forms import NewEmailAddressForm, NewPhoneForm, VerifyPhoneForm
from .sms import send_phone_verify_code


@lastuser_ui.route('/profile')
@requires_login
def profile():
    return render_template('profile.html')


@lastuser_ui.route('/profile/password', methods=['GET', 'POST'])
@requires_login
def change_password():
    if g.user.pw_hash is None:
        form = PasswordResetForm()
        form.edit_user = g.user
        del form.username
    else:
        form = PasswordChangeForm()
        form.edit_user = g.user
    if form.validate_on_submit():
        g.user.password = form.password.data
        db.session.commit()
        flash("Your new password has been saved.", category='success')
        return render_redirect(url_for('.profile'), code=303)
    return render_form(form=form, title="Change password", formid="changepassword", submit="Change password", ajax=True)


@lastuser_ui.route('/profile/email/new', methods=['GET', 'POST'])
@requires_login
def add_email():
    form = NewEmailAddressForm()
    if form.validate_on_submit():
        useremail = UserEmailClaim.get(user=g.user, email=form.email.data)
        if useremail is None:
            useremail = UserEmailClaim(user=g.user, email=form.email.data)
            db.session.add(useremail)
            db.session.commit()
        send_email_verify_link(useremail)
        flash("We sent you an email to confirm your address.", 'success')
        user_data_changed.send(g.user, changes=['email-claim'])
        return render_redirect(url_for('.profile'), code=303)
    return render_form(form=form, title="Add an email address", formid="email_add", submit="Add email", ajax=True)


@lastuser_ui.route('/profile/email/<md5sum>/remove', methods=['GET', 'POST'])
@requires_login
def remove_email(md5sum):
    useremail = UserEmail.query.filter_by(md5sum=md5sum, user=g.user).first()
    if not useremail:
        useremail = UserEmailClaim.query.filter_by(md5sum=md5sum, user=g.user).first_or_404()
    if isinstance(useremail, UserEmail) and useremail.primary:
        flash("You cannot remove your primary email address", "error")
        return render_redirect(url_for('.profile'), code=303)
    if request.method == 'POST':
        user_data_changed.send(g.user, changes=['email-delete'])
    return render_delete_sqla(useremail, db, title=u"Confirm removal", message=u"Remove email address {email}?".format(
            email=useremail.email),
        success=u"You have removed your email address {email}.".format(email=useremail.email),
        next=url_for('.profile'))


@lastuser_ui.route('/profile/phone/new', methods=['GET', 'POST'])
@requires_login
def add_phone():
    form = NewPhoneForm()
    if form.validate_on_submit():
        userphone = UserPhoneClaim.get(user=g.user, phone=form.phone.data)
        if userphone is None:
            userphone = UserPhoneClaim(user=g.user, phone=form.phone.data)
            db.session.add(userphone)
        send_phone_verify_code(userphone)
        db.session.commit()  # Commit after sending because send_phone_verify_code saves the message sent
        flash("We sent a verification code to your phone number.", 'success')
        user_data_changed.send(g.user, changes=['phone-claim'])
        return render_redirect(url_for('.verify_phone', number=userphone.phone), code=303)
    return render_form(form=form, title="Add a phone number", formid="phone_add", submit="Add phone", ajax=True)


@lastuser_ui.route('/profile/phone/<number>/remove', methods=['GET', 'POST'])
@requires_login
def remove_phone(number):
    userphone = UserPhone.query.filter_by(phone=number, user=g.user).first()
    if userphone is None:
        userphone = UserPhoneClaim.query.filter_by(phone=number, user=g.user).first_or_404()
    if request.method == 'POST':
        user_data_changed.send(g.user, changes=['phone-delete'])
    return render_delete_sqla(userphone, db, title=u"Confirm removal", message=u"Remove phone number {phone}?".format(
            phone=userphone.phone),
        success=u"You have removed your number {phone}.".format(phone=userphone.phone),
        next=url_for('.profile'))


@lastuser_ui.route('/profile/phone/<number>/verify', methods=['GET', 'POST'])
@requires_login
@load_model(UserPhoneClaim, {'phone': 'number'}, 'phoneclaim', permission='verify')
def verify_phone(phoneclaim):
    form = VerifyPhoneForm()
    form.phoneclaim = phoneclaim
    if form.validate_on_submit():
        if UserPhone.get(phoneclaim.phone) is None:
            if not g.user.phones:
                primary = True
            else:
                primary = False
            userphone = UserPhone(user=g.user, phone=phoneclaim.phone, gets_text=True, primary=primary)
            db.session.add(userphone)
            db.session.delete(phoneclaim)
            db.session.commit()
            flash("Your phone number has been verified.", 'success')
            user_data_changed.send(g.user, changes=['phone'])
            return render_redirect(url_for('.profile'), code=303)
        else:
            db.session.delete(phoneclaim)
            db.session.commit()
            flash("This phone number has already been claimed by another user.", 'danger')
    return render_form(form=form, title="Verify phone number", formid="phone_verify", submit="Verify", ajax=True)

########NEW FILE########
__FILENAME__ = sms
# -*- coding: utf-8 -*-

"""
Adds support for texting Indian mobile numbers
"""

from datetime import datetime
from pytz import timezone
import requests
# from urllib2 import urlopen, URLError
# from urllib import urlencode

from flask import current_app, flash, request
from lastuser_core.models import db, SMSMessage, SMS_STATUS
from .. import lastuser_ui

# SMS GupShup sends delivery reports with this timezone
SMSGUPSHUP_TIMEZONE = timezone('Asia/Kolkata')


def send_message(msg):
    if msg.phone_number.startswith('+91'):  # Indian number. Use Exotel
        if len(msg.phone_number) != 13:
            raise ValueError("Invalid Indian mobile number")
        # All okay. Send!
        if not (current_app.config.get('SMS_EXOTEL_SID') and current_app.config.get('SMS_EXOTEL_TOKEN')):
            raise ValueError("Lastuser is not configured for SMS")
        else:
            sid = current_app.config['SMS_EXOTEL_SID']
            token = current_app.config['SMS_EXOTEL_TOKEN']
            r = requests.post('https://twilix.exotel.in/v1/Accounts/{sid}/Sms/send.json'.format(sid=sid),
                auth=(sid, token),
                data={
                    'From': current_app.config.get('SMS_FROM'),
                    'To': msg.phone_number,
                    'Body': msg.message
                })
            if r.status_code in (200, 201):
                # All good
                msg.transaction_id = r.json().get('SMSMessage', {}).get('Sid')
            else:
                # FIXME: This function should not be sending messages to the UI
                flash("Message could not be sent.", 'danger')

        # # TODO: Also check if we have SMS GupShup credentials in settings.py
        # params = urlencode(dict(
        #     method='SendMessage',
        #     send_to=msg.phone_number[1:],  # Number with leading +
        #     msg=msg.message,
        #     msg_type='TEXT',
        #     format='text',
        #     v='1.1',
        #     auth_scheme='plain',
        #     userid=current_app.config['SMS_SMSGUPSHUP_USER'],
        #     password=current_app.config['SMS_SMSGUPSHUP_PASS'],
        #     mask=current_app.config['SMS_SMSGUPSHUP_MASK']
        #     ))
        # try:
        #     response = urlopen('https://enterprise.smsgupshup.com/GatewayAPI/rest?%s' % params).read()
        #     r_status, r_phone, r_id = [item.strip() for item in response.split('|')]
        #     if r_status == 'success':
        #         msg.status = SMS_STATUS.PENDING
        #         msg.transaction_id = r_id
        # except URLError, e:
        #     # FIXME: This function should not be sending messages to the UI
        #     flash("Message could not be sent. Error: %s" % e)
    else:
        # Unsupported at this time
        raise ValueError("Unsupported phone number")


def send_phone_verify_code(phoneclaim):
    msg = SMSMessage(phone_number=phoneclaim.phone,
        message=current_app.config['SMS_VERIFICATION_TEMPLATE'].format(code=phoneclaim.verification_code))
    # Now send this
    send_message(msg)
    db.session.add(msg)


@lastuser_ui.route('/report/smsgupshup')
def report_smsgupshup():
    externalId = request.args.get('externalId')
    deliveredTS = request.args.get('deliveredTS')
    status = request.args.get('status')
    phoneNo = request.args.get('phoneNo')
    cause = request.args.get('cause')

    # Find a corresponding message and ensure the parameters match
    msg = SMSMessage.query.filter_by(transaction_id=externalId).first()
    if not msg:
        return "No such message", 404
    elif msg.phone_number != '+' + phoneNo:
        return "Incorrect phone number", 404
    else:
        if status == 'SUCCESS':
            msg.status = SMS_STATUS.DELIVERED
        elif status == 'FAIL':
            msg.status = SMS_STATUS.FAILED
        else:
            msg.status == SMS_STATUS.UNKNOWN
        msg.fail_reason = cause
        if deliveredTS:
            deliveredTS = float(deliveredTS) / 1000.0
        # This delivery time is in IST, GMT+0530
        # Convert this into a naive UTC timestamp before saving
        local_status_at = datetime.fromtimestamp(deliveredTS)
        msg.status_at = local_status_at - SMSGUPSHUP_TIMEZONE.utcoffset(local_status_at)
    db.session.commit()
    return "Status updated"

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from coaster.manage import init_manager

from lastuser_core.models import db
from lastuserapp import app, init_for


if __name__ == "__main__":
    db.init_app(app)
    manager = init_manager(app, db, init_for)
    manager.run()

########NEW FILE########
__FILENAME__ = rqdev
from urlparse import urlparse
from lastuserapp import init_for, app

init_for('dev')

REDIS_URL = app.config.get('REDIS_URL', 'redis://localhost:6379/0')

# REDIS_URL is not taken by setup_default_arguments function of rq/scripts/__init__.py
# so, parse it into pieces and give it

r = urlparse(REDIS_URL)
REDIS_HOST = r.hostname
REDIS_PORT = r.port
REDIS_PASSWORD = r.password
REDIS_DB = 0

########NEW FILE########
__FILENAME__ = rqinit
from urlparse import urlparse
from lastuserapp import init_for, app

init_for('production')
REDIS_URL = app.config.get('REDIS_URL', 'redis://localhost:6379/0')

# REDIS_URL is not taken by setup_default_arguments function of rq/scripts/__init__.py
# so, parse that into pieces and give it

r = urlparse(REDIS_URL)
REDIS_HOST = r.hostname
REDIS_PORT = r.port
REDIS_PASSWORD = r.password
REDIS_DB = 0

########NEW FILE########
__FILENAME__ = runserver
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from lastuserapp import app, init_for

init_for('dev')
app.run('0.0.0.0', port=7000, debug=True)

########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python
import os
import readline
from pprint import pprint

os.environ['LASTUSER_ENV'] = 'dev'

from lastuserapp import *
from lastuser_core import models
from lastuser_core.models import db


os.environ['PYTHONINSPECT'] = 'True'

########NEW FILE########
__FILENAME__ = sitecustomize
# Required to make OpenID work with Wordpress (first instance where it came up)
import sys
if not hasattr(sys, 'setdefaultencoding'):
    reload(sys)
sys.setdefaultencoding("utf-8")

########NEW FILE########
__FILENAME__ = fixtures
# -*- coding: utf-8 -*-

from lastuserapp import db
from lastuser_core.models import *


def make_fixtures():
    user1 = User(username=u"user1", fullname=u"User 1")
    user2 = User(username=u"user2", fullname=u"User 2")
    db.session.add_all([user1, user2])
    
    email1 = UserEmail(email=u"user1@example.com", user=user1)
    phone1 = UserPhone(phone=u"1234567890", user=user1)
    email2 = UserEmail(email=u"user2@example.com", user=user2)
    phone2 = UserPhone(phone=u"1234567891", user=user2)
    db.session.add_all([email1, phone1, email2, phone2])

    org = Organization(name=u"org", title=u"Organization")
    org.owners.users.append(user1)
    db.session.add(org)

    client = Client(title=u"Test Application", org=org, user=user1, website=u"http://example.com")
    db.session.add(client)

    resource = Resource(name=u"test_resource", title=u"Test Resource", client=client)
    db.session.add(resource)

    action = ResourceAction(name=u"read", title=u"Read", resource=resource)
    db.session.add(action)

    message = SMSMessage(phone_number=phone1.phone, transaction_id=u"1" * 40, message=u"Test message")
    db.session.add(message)

    db.session.commit()

########NEW FILE########
__FILENAME__ = test_db
# -*- coding: utf-8 -*-

import unittest
from lastuserapp import app, db, init_for
from .fixtures import make_fixtures


class TestDatabaseFixture(unittest.TestCase):
    def setUp(self):
        init_for('testing')
        app.config['TESTING'] = True
        db.app = app
        db.create_all()
        self.db = db
        make_fixtures()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        db.session.remove()

########NEW FILE########
__FILENAME__ = test_model_client
# -*- coding: utf-8 -*-

from lastuserapp import db
import lastuser_core.models as models
from .test_db import TestDatabaseFixture


class TestClient(TestDatabaseFixture):
    def setUp(self):
        super(TestClient, self).setUp()
        self.user = models.User.query.filter_by(username=u"user1").first()


class TestUserClientPermissions(TestDatabaseFixture):
    def setUp(self):
        super(TestUserClientPermissions, self).setUp()
        self.user = models.User.query.filter_by(username=u"user1").first()
        self.create_fixtures()

    def create_fixtures(self):
        # Add permission to the client
        client = models.Client.query.filter_by(user=self.user).first()
        self.permission = models.UserClientPermissions(user=self.user, client=client)
        self.permission.permissions = u"admin"
        db.session.add(self.permission)
        db.session.commit()


class TestTeamClientPermissions(TestDatabaseFixture):
    def setUp(self):
        super(TestTeamClientPermissions, self).setUp()
        self.user = models.User.query.filter_by(username=u"user1").first()
        self.client = models.Client.query.filter_by(user=self.user).first()
        self.create_fixtures()

    def create_fixtures(self):
        self.org = models.Organization(title=u"test", name=u"Test")
        self.org.owners.users.append(self.user)
        db.session.add(self.org)
        self.team = models.Team(userid=self.user.userid, title=u"developers", org=self.org)
        db.session.add(self.team)
        self.team_client_permission = models.TeamClientPermissions(team=self.team, client=self.client, access_permissions=u"admin")
        db.session.add(self.team_client_permission)
        db.session.commit()


class TestResource(TestDatabaseFixture):
    def setUp(self):
        super(TestResource, self).setUp()
        self.user = models.User.query.filter_by(username=u"user1").first()
        self.client = models.Client.query.filter_by(user=self.user).first()
        self.create_fixtures()

    def create_fixtures(self):
        resource = models.Resource(name=u"resource", title=u"Resource", client=self.client)
        db.session.add(resource)
        db.session.commit()

    def test_find_all(self):
        resources = self.client.resources
        self.assertEqual(len(resources), 2)
        self.assertEqual(set([r.name for r in resources]), set([u'test_resource', u'resource']))


class TestClientTeamAccess(TestDatabaseFixture):
    def setUp(self):
        super(TestClientTeamAccess, self).setUp()
        self.user = models.User.query.filter_by(username=u"user1").first()
        self.client = models.Client.query.filter_by(user=self.user).first()
        self.client.team_access = True
        db.session.commit()
        self.create_fixtures()

    def create_fixtures(self):
        self.org = models.Organization(title=u"test", name=u"Test")
        self.org.owners.users.append(self.user)
        db.session.add(self.org)
        self.team = models.Team(userid=self.user.userid, title=u"developers", org=self.org)
        db.session.add(self.team)
        self.team_client_permission = models.TeamClientPermissions(team=self.team, client=self.client, access_permissions=u"admin")
        db.session.add(self.team_client_permission)
        self.client_team_access = models.ClientTeamAccess(org=self.org, client=self.client, access_level=models.CLIENT_TEAM_ACCESS.ALL)
        db.session.add(self.client_team_access)
        db.session.commit()

    def test_find_all(self):
        self.assertIs(self.client.org_team_access[0], self.client_team_access)


class TestPermission(TestDatabaseFixture):
    def setUp(self):
        super(TestPermission, self).setUp()
        self.user = models.User.query.filter_by(username=u"user1").first()
        self.create_fixtures()

    def create_fixtures(self):
        self.org = models.Organization(title=u"test", name=u"Test")
        self.org.owners.users.append(self.user)
        db.session.add(self.org)
        self.permission = models.Permission(user=self.user, org=self.org, name=u"admin", title=u"admin", allusers=True)
        db.session.add(self.permission)
        db.session.commit()

########NEW FILE########
__FILENAME__ = test_model_notice
# -*- coding: utf-8 -*-

import lastuser_core.models as models
from .test_db import TestDatabaseFixture


class TestSMS(TestDatabaseFixture):
    def setUp(self):
        super(TestSMS, self).setUp()

########NEW FILE########
__FILENAME__ = test_model_user
# -*- coding: utf-8 -*-

from lastuserapp import db
import lastuser_core.models as models
from .test_db import TestDatabaseFixture


class TestTeam(TestDatabaseFixture):
    def setUp(self):
        super(TestTeam, self).setUp()
        self.user = models.User.query.filter_by(username=u"user1").first()
        self.create_fixtures()

    def create_fixtures(self):
        self.org = models.Organization(title=u"title", name=u"Test")
        self.org.owners.users.append(self.user)
        db.session.add(self.org)
        self.team = models.Team(userid=self.user.userid, title=u"developers", org=self.org)
        db.session.add(self.team)
        db.session.commit()


class TestOrganization(TestDatabaseFixture):
    def setUp(self):
        super(TestOrganization, self).setUp()
        self.user = models.User.query.filter_by(username=u"user1").first()
        self.client = models.Client.query.filter_by(user=self.user).first()
        self.create_fixtures()

    def create_fixtures(self):
        self.org = models.Organization(title=u"test", name=u"Test")
        self.org.owners.users.append(self.user)
        self.org1 = models.Organization(title=u"test1", name=u"Test1")
        self.org1.owners.users.append(self.user)
        self.client_team_access = models.ClientTeamAccess(org=self.org, client=self.client, access_level=models.CLIENT_TEAM_ACCESS.ALL)
        self.client_team_access1 = models.ClientTeamAccess(org=self.org1, client=self.client, access_level=models.CLIENT_TEAM_ACCESS.ALL)
        db.session.add_all([self.org, self.org1, self.client_team_access, self.client_team_access1])
        db.session.commit()

########NEW FILE########
__FILENAME__ = website
import sys
import os.path
sys.path.insert(0, os.path.dirname(__file__))
from lastuserapp import app as application, init_for
init_for('production')

########NEW FILE########
