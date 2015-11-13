__FILENAME__ = forms
from flask.ext.wtf import (
    Form,
    Required,
    TextAreaField,
    StringField,
    RadioField,
    HiddenField,
    SubmitField,
    Recaptcha,
    RecaptchaField,
    validators
    )
import re


reg = re.compile(r"^[\w\-.]*\.[a-z]{2,4}$")


class SpammerForm(Form):
    error_msg = u"""The address you tried to add is wrong. Please type it 
like this:<ul><li>Everything <em>after</em> the "@" sign, with no spaces.</li>
<li>Example: <strong>enterprise-weasels.co.uk</strong></li></ul>"""
    address = StringField(u"Address Entry",
        [
            validators.DataRequired(
                message=u"You have to enter an address."),
            validators.Regexp(
                reg,
                flags=0,
                message=error_msg
        )])
    recaptcha = RecaptchaField(
        label=u"ReCaptcha",
        validators=[Recaptcha(
            message=u"The ReCaptcha words you entered are wrong. \
Please try again."
        )])

    submit = SubmitField()

########NEW FILE########
__FILENAME__ = models
from webapp import app, db
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import validates
from sqlalchemy.sql import expression
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import DateTime

# auto-generated index names use the ix_table_column naming convention


class utcnow(expression.FunctionElement):
    """ UTC Timestamp for compilation """
    type = DateTime()


# Define PG utcnow() function
@compiles(utcnow, 'postgresql')
def pg_utcnow(element, compiler, **kw):
    """ Postgres UTC Timestamp """
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


class SpamsubMixin(object):
    """ Provides some common attributes to our models """

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    __mapper_args__ = {'always_refresh': True}

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=False, server_default=utcnow())


class Address(db.Model, SpamsubMixin):
    """ Address table """
    address = db.Column(
        db.String(250),
        nullable=False,
        unique=True,
        index=True)
    count = db.Column(
        db.Integer(),
        default=1)

    def __init__(self, address):
        self.address = address

    @classmethod
    def exists(self, address):
        """ Check if an address exists, increment counter if it does """
        exsts = self.query.filter_by(address=address).first()
        if exsts:
            exsts.count += 1
            db.session.add(exsts)
            db.session.commit()
            return True
        return False

    @classmethod
    def top(self, number=3):
        """ Return top spammers """
        return [{"x": each.address, "y": each.count} for each in 
            self.query.order_by(self.count.desc()).limit(number).all()]


class Counter(db.Model, SpamsubMixin):
    """ Counter table """
    count = db.Column(
        db.Integer(),
        nullable=False,
        unique=True,
        index=True)

    def __init__(self, count):
        self.count = count

    @validates('count')
    def validate_count(self, key, count):
        try:
            assert count >= 0
        except AssertionError:
            count = 0
        return count


class UpdateCheck(db.Model, SpamsubMixin):
    """ Update check timestamp table """

    def __init__(self):
        self.timestamp = utcnow()

########NEW FILE########
__FILENAME__ = utils
"""
Utility functions for interacting with our Git repos
"""
import os
import json
from datetime import datetime, timedelta

from webapp import app
from flask import abort, flash, render_template
from sqlalchemy import func, desc
from models import *
from models import utcnow as utcnow_
from git import Repo
from git.exc import *
from requests.exceptions import HTTPError
import requests
import humanize

basename = os.path.dirname(__file__)
now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")
repo = Repo(os.path.join(basename, "git_dir"))


def ok_to_update():
    """ If we've got more than two new addresses, or a day's gone by """
    counter = Counter.query.first()
    if not counter:
        counter = Count(0)
        db.session.add(counter)
        db.session.commit()
    elapsed = counter.timestamp - datetime.utcnow()
    return any([counter.count >= 2, abs(elapsed.total_seconds()) >= 86400])

def check_if_exists(address):
    """
    Check whether a submitted address exists in the DB, add it if not,
    re-generate the spammers.txt file, and open a pull request with the updates
    """
    normalised = u"@" + address.lower().strip()
    # add any missing spammers to our DB
    if Address.exists(normalised):
        # if we immediately find the address, don't continue
        return True
    else:
        # otherwise, pull updates from GitHub, and check again
        update_db()
    if not Address.exists(normalised):
        db.session.add(Address(address=normalised))
        count = Counter.query.first()
        if not count:
            count = Counter(0)
        count.count += 1
        db.session.add(count)
        db.session.commit()
        if ok_to_update():
            write_new_spammers()
        return False
    return True

def write_new_spammers():
    """
    Synchronise all changes between GitHub and webapp
    Because we may have multiple pending pull requests,
    each changeset must be added to a new integration branch, which issues
    the pull request to origin/master

    TODO: tidy up remote integration branches
    """
    errs = False
    # pull all branches from origin, and force-checkout master
    repo_checkout()
    # switch to a new integration branch
    newbranch = "integration_%s" % datetime.utcnow().strftime(
            "%Y_%b_%d_%H_%M_%S")
    git.checkout(b=newbranch)
    index = repo.index
    # re-generate spammers.txt
    try:
        output(filename="spammers.txt")
    except IOError as e:
        app.logger.error("Couldn't write spammers.txt. Err: %s" % e)
        repo.heads.master.checkout(f=True)
        git.branch(newbranch, D=True)
        errs = True
    # add spammers.txt to local integration branch
    try:
        index.add(['spammers.txt'])
        index.commit("Updating Spammers on %s" % now)
        # push local repo to webapp's remote
        our_remote.push(newbranch)
    except GitCommandError as e:
        errs = True
        app.logger.error("Couldn't push to staging remote. Err: %s" % e)
    # send pull request to main remote
    our_sha = "urschrei:%s" % newbranch
    their_sha = 'master'
    if not errs and pull_request(our_sha, their_sha):
        # delete our local integration branch, and reset counter
        counter = Counter.query.first()
        counter.count = 0
        counter.timestamp = utcnow_()
        db.session.add(counter)
        db.session.commit()
        git.checkout("master")
        git.branch(newbranch, D=True)
    else:
        # register an error
        errs = True
    if errs:
        flash(
            "There was an error sending your updates to GitHub. We'll \
try again later, though, and they <em>have</em> been saved.", "text-error"
            )

def output(filename, template="output.jinja"):
    """ write filename to the git directory, using the specified template """
    with open(os.path.join(basename, "git_dir", filename), "w") as f:
            f.write(render_template(
                template,
                addresses=[record.address.strip() for
                    record in Address.query.order_by('address').all()]))

def get_spammers():
    """ Return an up-to-date list of spammers from the main repo text file """
    with open(os.path.join(basename, "git_dir", 'spammers.txt'), 'r') as f:
        spammers = f.readlines()
    # trim the " OR" and final newline from the entries
    # FIXME: this is a bit fragile
    return [spammer.split()[0] for spammer in spammers]

def pull_request(our_sha, their_sha):
    """ Open a pull request on the main repo """
    payload = {
        "title": "Updated Spammers on %s" % now,
        "body": "Updates from the webapp",
        "head": our_sha,
        "base": their_sha
    }
    headers = {
        "Authorization": 'token %s' % app.config['GITHUB_TOKEN'],
    }
    req = requests.post(
        "https://api.github.com/repos/drcongo/spammy-recruiters/pulls",
        data=json.dumps(payload), headers=headers)
    try:
        req.raise_for_status()
    except HTTPError as e:
        app.logger.error("Couldn't open pull request. Error: %s" % e)
        return False
    return True

def repo_checkout():
    """ Ensure that the spammers.txt we're comparing is from origin/master """
    git = repo.git
    try:
        git.pull(all=True)
        repo.heads.master.checkout(f=True)
        git.checkout("spammers.txt", f=True)
    except (GitCommandError, CheckoutError) as e:
        # Not much point carrying on without the latest spammer file
        app.logger.critical("Couldn't check out latest spammers.txt: %s" % e)
        abort(500)

def update_db():
    """ Add any missing spammers to our app DB """
    # pull all branches from origin, and force-checkout master
    repo_checkout()
    their_spammers = set(get_spammers())
    our_spammers = set(addr.address.strip() for addr in
        Address.query.order_by('address').all())
    to_update = list(their_spammers - our_spammers)
    if to_update:
        db.session.add_all([Address(address=new_addr) for
            new_addr in to_update])
    # reset sync timestamp
    latest = UpdateCheck.query.first() or UpdateCheck()
    latest.timestamp = utcnow_()
    db.session.add(latest)
    db.session.commit()

def sync_check():
    """
    Syncing the local and remote repos is a relatively slow process;
    there's no need to do it more than once per hour, really
    """
    latest = UpdateCheck.query.first()
    if not latest:
        latest = UpdateCheck()
        db.session.add(latest)
        db.session.commit()
    elapsed = datetime.utcnow() - latest.timestamp
    if abs(elapsed.total_seconds()) > 3600:
        update_db()
        elapsed = datetime.utcnow() - timedelta(seconds=1)
    return humanize.naturaltime(elapsed)

########NEW FILE########
__FILENAME__ = views
import os
from flask import Blueprint, request, flash, render_template, send_file, jsonify
from models import *
from forms import SpammerForm
import utils

spamsub = Blueprint(
    'spamsub',
    __name__,
    template_folder='templates'
    )

@spamsub.route('/', methods=['GET', 'POST'])
def index():
    """ Index page """
    count = Address.query.count()
    form = SpammerForm()
    # try to validate, and check for AJAX submission
    if form.validate_on_submit():
            if not utils.check_if_exists(form.address.data):
                flash(
                    u"We've added %s to the database." % form.address.data,
                    "text-success")
            else:
                flash(
                    u"We already know about %s, though." % form.address.data,
                    "text-success")
    if request.is_xhr:
        # OK to send back a fragment
        return render_template(
            'form.jinja',
            form=form,
            )
    # GET or no JS, so render a full page
    return render_template(
        'index.jinja',
        form=form,
        count=count,
        recaptcha_public_key=app.config['RECAPTCHA_PUBLIC_KEY'])

@spamsub.route('download', methods=['GET'])
def download():
    """ Download the latest version of spammers.txt """
    utils.update_db()
    return send_file(
        os.path.join(utils.basename, "git_dir/spammers.txt"),
        as_attachment=True,
        attachment_filename="spammers.txt")

@spamsub.route('updates', methods=['GET'])
def updates():
    """ Check for updates in GitHub repo if more than an hour's passed """
    vals = {
        'last_updated': utils.sync_check(),
        'count': Address.query.count(),
        }
    return jsonify(vals)






########NEW FILE########
__FILENAME__ = common
# no debugging by default - this is overriden in run.py for local dev
DEBUG = False
# production DB
SQLALCHEMY_DATABASE_URI = 'postgresql://spamsub:@localhost/spamsub'

########NEW FILE########
__FILENAME__ = dev
# these settings are exported as SPAMSUB_CONFIGURATION by fabfile commands
# SPAMSUB_CONFIGURATION is then picked up by app/__init__.py

DEBUG = True
reloader = True
SQLALCHEMY_DATABASE_URI = 'postgresql://spamsub:@localhost/spamsub'
# this won't be picked up when running under production
SECRET_KEY = '088e57ce8c4db3c89c014cf463685601e3a02292efed95f20860e31a0cb7f0fc2216e29e2bfab8a9b4e0cb4e508698ef931839e044182b5d0e500dfeeaa027df6686ebc233b1361189dfde2a618cd6ad9fea99b0f8062545c9e60005724a4cf10eafabeaef8468020dad52dc7ebbe0b10c5d0d915604c56fed35614ae7b75737'
# recaptcha settings
RECAPTCHA_PUBLIC_KEY = "6LdLmtkSAAAAAMhQTQOq2zRvnSLeVDyLESrd59Kb"
RECAPTCHA_PRIVATE_KEY =  "6LdLmtkSAAAAAAxgwCKkN1UCbbUGD2rjU8bviSd1"
RECAPTCHA_USE_SSL = False
RECAPTCHA_OPTIONS = {
    'tabindex': 1,
}

########NEW FILE########
__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import sys

sys.path.append("..")

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
from webapp import db
target_metadata = db.Model.metadata

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
__FILENAME__ = 2f6bf42fb428_create_update_tracki
"""create update tracking table

Revision ID: 2f6bf42fb428
Revises: 32d061b864fd
Create Date: 2012-10-17 18:44:24.652632

"""

# revision identifiers, used by Alembic.
revision = '2f6bf42fb428'
down_revision = '32d061b864fd'

from alembic import op
import sqlalchemy as sa


def upgrade():
        counter = op.create_table(
        "counter",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("count", sa.Integer(), unique=True, nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP, server_default=sa.func.now())
        )
        op.create_index(
        "count_idx", "counter", ['count'])



def downgrade():
    op.drop_table("counter")

########NEW FILE########
__FILENAME__ = 31d14d064445_alter_timestamp_colu
"""Alter timestamp columns

Revision ID: 31d14d064445
Revises: 4cd0c6a2736f
Create Date: 2012-12-24 11:55:39.306586

"""

# revision identifiers, used by Alembic.
revision = '31d14d064445'
down_revision = '4cd0c6a2736f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import expression
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import DateTime



# define a "UTC" timestamp class
class utcnow(expression.FunctionElement):
    """ UTC Timestamp """
    type = DateTime()


# Define PG and MYSQL utcnow() functions
@compiles(utcnow, 'postgresql')
def pg_utcnow(element, compiler, **kw):
    """ Postgres UTC Timestamp """
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


@compiles(utcnow, 'mssql')
def ms_utcnow(element, compiler, **kw):
    """ MySQL UTC Timestamp """
    return "GETUTCDATE()"


def upgrade():
    op.alter_column("address", "timestamp", type_=DateTime,
        server_default=utcnow())
    op.alter_column("updatecheck", "timestamp", type_=DateTime,
        server_default=utcnow())
    op.alter_column("counter", "timestamp", type_=DateTime,
        server_default=utcnow())


def downgrade():
    op.alter_column("address", "timestamp",
        type_=sa.TIMESTAMP, server_default=sa.func.now())
    op.alter_column("updatecheck", "timestamp", type_=sa.TIMESTAMP,
        server_default=sa.func.now())
    op.alter_column("counter", "timestamp", type_=sa.TIMESTAMP,
        server_default=sa.func.now())

########NEW FILE########
__FILENAME__ = 32d061b864fd_add_index_to_address
"""Add index to address field

Revision ID: 32d061b864fd
Revises: 622a69a8204
Create Date: 2012-10-05 17:39:19.912912

"""

# revision identifiers, used by Alembic.
revision = '32d061b864fd'
down_revision = '622a69a8204'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index(
        "address_idx", "address", ['address'])


def downgrade():
    op.drop_index("address_idx", "address")

########NEW FILE########
__FILENAME__ = 358b3f6ca619_add_indexes
"""Add indexes

Revision ID: 358b3f6ca619
Revises: 3afd1b623cca
Create Date: 2012-11-27 13:23:46.777375

"""

# revision identifiers, used by Alembic.
revision = '358b3f6ca619'
down_revision = '3afd1b623cca'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index(
        "ix_address_address", "address", ['address'])
    op.create_index(
        "ix_counter_count", "counter", ['count'])
    op.create_index(
        "ix_updatecheck_timestamp", "updatecheck", ['timestamp'])


def downgrade():
    op.drop_index("ix_address_address", "address")
    op.drop_index("ix_counter_count", "counter")
    op.drop_index("ix_updatecheck_timestamp", "updatecheck")

########NEW FILE########
__FILENAME__ = 3afd1b623cca_adding_an_update_che
"""adding an update check table

Revision ID: 3afd1b623cca
Revises: 2f6bf42fb428
Create Date: 2012-11-10 01:28:45.605044

"""

# revision identifiers, used by Alembic.
revision = '3afd1b623cca'
down_revision = '2f6bf42fb428'

from alembic import op
import sqlalchemy as sa


def upgrade():
        updatecheck = op.create_table(
        "updatecheck",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column('timestamp', sa.TIMESTAMP, server_default=sa.func.now())
        )
        op.create_index(
        "update_timestamp", "updatecheck", ['timestamp'])



def downgrade():
    op.drop_table("updatecheck")

########NEW FILE########
__FILENAME__ = 4cd0c6a2736f_add_spammer_frequenc
"""add spammer frequency column

Revision ID: 4cd0c6a2736f
Revises: 358b3f6ca619
Create Date: 2012-12-20 17:26:40.632679

"""

# revision identifiers, used by Alembic.
revision = '4cd0c6a2736f'
down_revision = '358b3f6ca619'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("address",
        sa.Column(
            "count",
            sa.Integer,
            default=1))


def downgrade():
    op.drop_column("address", "count")

########NEW FILE########
__FILENAME__ = 622a69a8204_create_address_table
"""Create address table

Revision ID: 622a69a8204
Revises: None
Create Date: 2012-10-03 11:49:27.071970

"""

# revision identifiers, used by Alembic.
revision = '622a69a8204'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
        address = op.create_table(
        "address",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("address", sa.String(250), unique=True, nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP, server_default=sa.func.now())
        )



def downgrade():
    op.drop_table("address")

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
import sys

sys.path.append("..")

from webapp import app
app.run(host='127.0.0.1')
########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
sys.path.append("..")
from flask import *
from webapp import app, db
from webapp.apps.spamsub.models import *

app.testing = True
client = app.test_client()
ctx = app.test_request_context()
ctx.push()
print "app and db have been imported.\nYou have a test client: client,\nand a test request context: ctx"

########NEW FILE########
__FILENAME__ = test_spamsub
# -*- coding: utf-8 -*-


import os
from flask.ext.testing import TestCase
from webapp import app as ss
from webapp import db
from webapp.apps.spamsub.models import *
from webapp.apps.spamsub import utils
from datetime import timedelta


def mock_checkout():
    """ lets just pretend we're checking out the right file """
    pass

def mock_pull_request():
    """ don't actually open a pull request """
    return True

utils.repo_checkout = mock_checkout
utils.pull_request = mock_pull_request



class MyTest(TestCase):
    """ TestCase Flask extension class """

    # Setup boilerplate methods and settings

    def create_app(self):

        app = ss
        app.config.from_pyfile(os.path.join(app.root_path, 'config/dev.py'))
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite://"
        app.config['CSRF_ENABLED'] = False
        return app

    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite://"
        db.create_all()
        # add an initial timestamp, address, and update count
        db.session.add_all([
            UpdateCheck(),
            Address(address="@test-address.com"),
            Counter(count=0)
            ])
        db.session.commit()

    def tearDown(self):

        db.session.remove()
        db.drop_all()

    # Actual tests start here
    def test_exists(self):
        """ Should pass because we've added the address during setup """
        print Address.query.filter_by(address="@test-address.com").first().address
        assert utils.check_if_exists('test-address.com')
        print Address.query.filter_by(address="@test-address.com").first().address

    def test_address_exists(self):
        """ Passes if we get the "We already know about … though" message """
        response = self.client.post('/', data=dict(
            address='test-address.com',
            recaptcha_challenge_field='test',
            recaptcha_response_field='test'))
        assert 'though' in response.data

    def test_new_address(self):
        """ Passes if we add the POSTed address to the db """
        response = self.client.post('/', data=dict(
            address='new-address.com',
            recaptcha_challenge_field='test',
            recaptcha_response_field='test'))
        assert 'added' in response.data

    def test_ok_to_update_counter(self):
        """ Should pass because we have more than two new addresses """
        ctr = Counter.query.first()
        ctr.count += 2
        db.session.add(ctr)
        db.session.commit()
        assert utils.ok_to_update()

    def test_ok_to_update_date(self):
        """ Should pass because more than a day has passed """
        ctr = Counter.query.first()
        ctr.timestamp -= timedelta(days=1, seconds=1)
        db.session.add(ctr)
        db.session.commit()
        assert utils.ok_to_update()

    def test_ok_to_update_fails(self):
        """ Should fail because the counter's zero, and < 24 hours old """
        assert not utils.ok_to_update()



########NEW FILE########
