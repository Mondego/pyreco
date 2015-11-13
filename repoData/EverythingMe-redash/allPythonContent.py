__FILENAME__ = latest_release
#!/usr/bin/env python
import sys
import requests

if __name__ == '__main__':
    response = requests.get('https://api.github.com/repos/EverythingMe/redash/releases')

    if response.status_code != 200:
        exit("Failed getting releases (status code: %s)." % response.status_code)

    sorted_releases = sorted(response.json(), key=lambda release: release['id'], reverse=True)

    latest_release = sorted_releases[0]
    asset_url = latest_release['assets'][0]['url']
    filename = latest_release['assets'][0]['name']

    wget_command = 'wget --header="Accept: application/octet-stream" %s -O %s' % (asset_url, filename)

    if '--url-only' in sys.argv:
        print asset_url
    elif '--wget' in sys.argv:
        print wget_command
    else:
        print "Latest release: %s" % latest_release['tag_name']
        print latest_release['body']

        print "\nTarball URL: %s" % asset_url
        print 'wget: %s' % (wget_command)



########NEW FILE########
__FILENAME__ = test_multithreading
"""
Script to test concurrency (multithreading/multiprocess) issues with the workers. Use with caution.
"""
import json
import atfork
atfork.monkeypatch_os_fork_functions()
import atfork.stdlib_fixer
atfork.stdlib_fixer.fix_logging_module()

import time
from redash.data import worker
from redash import models, data_manager, redis_connection

if __name__ == '__main__':
    models.create_db(True, False)

    print "Creating data source..."
    data_source = models.DataSource.create(name="Concurrency", type="pg", options="dbname=postgres")

    print "Clear jobs/hashes:"
    redis_connection.delete("jobs")
    query_hashes = redis_connection.keys("query_hash_*")
    if query_hashes:
        redis_connection.delete(*query_hashes)

    starting_query_results_count = models.QueryResult.select().count()
    jobs_count = 5000
    workers_count = 10

    print "Creating jobs..."
    for i in xrange(jobs_count):
        query = "SELECT {}".format(i)
        print "Inserting: {}".format(query)
        data_manager.add_job(query=query, priority=worker.Job.LOW_PRIORITY,
                             data_source=data_source)

    print "Starting workers..."
    workers = data_manager.start_workers(workers_count)

    print "Waiting for jobs to be done..."
    keep_waiting = True
    while keep_waiting:
        results_count = models.QueryResult.select().count() - starting_query_results_count
        print "QueryResults: {}".format(results_count)
        time.sleep(5)
        if results_count == jobs_count:
            print "Yay done..."
            keep_waiting = False

    data_manager.stop_workers()

    qr_count = 0
    for qr in models.QueryResult.select():
        number = int(qr.query.split()[1])
        data_number = json.loads(qr.data)['rows'][0].values()[0]

        if number != data_number:
            print "Oops? {} != {} ({})".format(number, data_number, qr.id)
        qr_count += 1

    print "Verified {} query results.".format(qr_count)

    print "Done."
########NEW FILE########
__FILENAME__ = upload_version
#!python
import os
import sys
import json
import requests
import subprocess


def capture_output(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE)
    return proc.stdout.read()


if __name__ == '__main__':
    version = sys.argv[1]
    filepath = sys.argv[2]
    filename = filepath.split('/')[-1]
    github_token = os.environ['GITHUB_TOKEN']
    auth = (github_token, 'x-oauth-basic')
    commit_sha = os.environ['CIRCLE_SHA1']

    commit_body = capture_output(["git", "log", "--format=%b", "-n", "1", commit_sha])
    file_md5_checksum = capture_output(["md5sum", filepath]).split()[0]
    file_sha256_checksum = capture_output(["sha256sum", filepath]).split()[0]
    version_body = "%s\n\nMD5: %s\nSHA256: %s" % (commit_body, file_md5_checksum, file_sha256_checksum)

    params = json.dumps({
        'tag_name': 'v{0}'.format(version),
        'name': 're:dash v{0}'.format(version),
        'body': version_body,
        'target_commitish': commit_sha,
        'prerelease': True
    })

    response = requests.post('https://api.github.com/repos/everythingme/redash/releases',
                             data=params,
                             auth=auth)

    upload_url = response.json()['upload_url']
    upload_url = upload_url.replace('{?name}', '')

    with open(filepath) as file_content:
        headers = {'Content-Type': 'application/gzip'}
        response = requests.post(upload_url, file_content, params={'name': filename}, auth=auth,
                                 headers=headers, verify=False)


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
"""
CLI to manage redash.
"""
from flask.ext.script import Manager, prompt_pass

from redash import settings, models, __version__
from redash.wsgi import app
from redash.import_export import import_manager

manager = Manager(app)
database_manager = Manager(help="Manages the database (create/drop tables).")
users_manager = Manager(help="Users management commands.")
data_sources_manager = Manager(help="Data sources management commands.")

@manager.command
def version():
    """Displays re:dash version."""
    print __version__


@manager.command
def runworkers():
    """Prints deprecation warning."""
    print "** This command is deprecated. Please use Celery's CLI to control the workers. **"


@manager.shell
def make_shell_context():
    from redash.models import db
    return dict(app=app, db=db, models=models)

@manager.command
def check_settings():
    from types import ModuleType

    for name in dir(settings):
        item = getattr(settings, name)
        if not callable(item) and not name.startswith("__") and not isinstance(item, ModuleType):
            print "{} = {}".format(name, item)

@database_manager.command
def create_tables():
    """Creates the database tables."""
    from redash.models import create_db, init_db

    create_db(True, False)
    init_db()

@database_manager.command
def drop_tables():
    """Drop the database tables."""
    from redash.models import create_db

    create_db(False, True)


@users_manager.option('email', help="User's email")
@users_manager.option('name', help="User's full name")
@users_manager.option('--admin', dest='is_admin', action="store_true", default=False, help="set user as admin")
@users_manager.option('--google', dest='google_auth', action="store_true", default=False, help="user uses Google Auth to login")
@users_manager.option('--password', dest='password', default=None, help="Password for users who don't use Google Auth (leave blank for prompt).")
@users_manager.option('--groups', dest='groups', default=models.Group.DEFAULT_PERMISSIONS, help="Comma seperated list of groups (leave blank for default).")
def create(email, name, groups, is_admin=False, google_auth=False, password=None):
    print "Creating user (%s, %s)..." % (email, name)
    print "Admin: %r" % is_admin
    print "Login with Google Auth: %r\n" % google_auth
    if isinstance(groups, basestring):
        groups= groups.split(',')
        groups.remove('') # in case it was empty string

    if is_admin:
        groups += ['admin']

    user = models.User(email=email, name=name, groups=groups)
    if not google_auth:
        password = password or prompt_pass("Password")
        user.hash_password(password)

    try:
        user.save()
    except Exception, e:
        print "Failed creating user: %s" % e.message


@users_manager.option('email', help="email address of user to delete")
def delete(email):
    deleted_count = models.User.delete().where(models.User.email == email).execute()
    print "Deleted %d users." % deleted_count

@data_sources_manager.command
def import_from_settings(name=None):
    """Import data source from settings (env variables)."""
    name = name or "Default"
    data_source = models.DataSource.create(name=name,
                                           type=settings.CONNECTION_ADAPTER,
                                           options=settings.CONNECTION_STRING)

    print "Imported data source from settings (id={}).".format(data_source.id)


@data_sources_manager.command
def list():
    """List currently configured data sources"""
    for ds in models.DataSource.select():
        print "Name: {}\nType: {}\nOptions: {}".format(ds.name, ds.type, ds.options)

@data_sources_manager.command
def new(name, type, options):
    """Create new data source"""
    # TODO: validate it's a valid type and in the future, validate the options.
    print "Creating {} data source ({}) with options:\n{}".format(type, name, options)
    data_source = models.DataSource.create(name=name,
                                           type=type,
                                           options=options)
    print "Id: {}".format(data_source.id)


manager.add_command("database", database_manager)
manager.add_command("users", users_manager)
manager.add_command("import", import_manager)
manager.add_command("ds", data_sources_manager)

if __name__ == '__main__':
    manager.run()
########NEW FILE########
__FILENAME__ = add_created_at_field
from playhouse.migrate import Migrator
from redash import db
from redash import models


if __name__ == '__main__':
    db.connect_db()
    migrator = Migrator(db.database)
    with db.database.transaction():
        migrator.add_column(models.Dashboard, models.Dashboard.created_at, 'created_at')
        migrator.add_column(models.Widget, models.Widget.created_at, 'created_at')

    db.close_db(None)
########NEW FILE########
__FILENAME__ = add_global_filters_to_dashboard
from playhouse.migrate import Migrator
from redash import db
from redash import models


if __name__ == '__main__':
    db.connect_db()
    migrator = Migrator(db.database)
    with db.database.transaction():
        migrator.add_column(models.Dashboard, models.Dashboard.dashboard_filters_enabled, 'dashboard_filters_enabled')

    db.close_db(None)
########NEW FILE########
__FILENAME__ = add_password_to_users
from playhouse.migrate import Migrator
from redash import db
from redash import models


if __name__ == '__main__':
    db.connect_db()
    migrator = Migrator(db.database)
    with db.database.transaction():
        migrator.add_column(models.User, models.User.password_hash, 'password_hash')

    db.close_db(None)

########NEW FILE########
__FILENAME__ = add_permissions_to_user
from playhouse.migrate import Migrator
from redash import db
from redash import models


if __name__ == '__main__':
    db.connect_db()
    migrator = Migrator(db.database)
    with db.database.transaction():
        migrator.add_column(models.User, models.User.permissions, 'permissions')
        models.User.update(permissions=['admin'] + models.User.DEFAULT_PERMISSIONS).where(models.User.is_admin == True).execute()

    db.close_db(None)

########NEW FILE########
__FILENAME__ = add_queue_name_to_data_source
from playhouse.migrate import Migrator
from redash import db
from redash import models


if __name__ == '__main__':
    db.connect_db()
    migrator = Migrator(db.database)
    with db.database.transaction():
        migrator.add_column(models.DataSource, models.DataSource.queue_name, 'queue_name')
        migrator.add_column(models.DataSource, models.DataSource.scheduled_queue_name, 'scheduled_queue_name')

    db.close_db(None)
########NEW FILE########
__FILENAME__ = add_text_to_widgets
from playhouse.migrate import Migrator
from redash import db
from redash import models


if __name__ == '__main__':
    db.connect_db()
    migrator = Migrator(db.database)
    with db.database.transaction():
        migrator.add_column(models.Widget, models.Widget.text, 'text')
        migrator.set_nullable(models.Widget, models.Widget.visualization, True)

    db.close_db(None)
########NEW FILE########
__FILENAME__ = add_view_query_permission
import peewee
from redash import db
from redash import models


if __name__ == '__main__':
    db.connect_db()

    previous_default_permissions = models.User.DEFAULT_PERMISSIONS[:]
    previous_default_permissions.remove('view_query')
    models.User.update(permissions=peewee.fn.array_append(models.User.permissions, 'view_query')).where(peewee.SQL("'view_source' = any(permissions)")).execute()

    db.close_db(None)

########NEW FILE########
__FILENAME__ = change_queries_description_to_nullable
from playhouse.migrate import Migrator
from redash import db
from redash import models


if __name__ == '__main__':
    db.connect_db()
    migrator = Migrator(db.database)
    with db.database.transaction():
        migrator.set_nullable(models.Query, models.Query.description, True)

    db.close_db(None)
########NEW FILE########
__FILENAME__ = change_query_id_on_widgets_to_null
from playhouse.migrate import Migrator
from redash import db
from redash import models


if __name__ == '__main__':
    db.connect_db()
    migrator = Migrator(db.database)
    with db.database.transaction():
        migrator.set_nullable(models.Widget, models.Widget.query_id, True)
        migrator.set_nullable(models.Widget, models.Widget.type, True)

    db.close_db(None)
########NEW FILE########
__FILENAME__ = create_activity_log
from redash import db
from redash import models

if __name__ == '__main__':
    db.connect_db()

    if not models.ActivityLog.table_exists():
        print "Creating activity_log table..."
        models.ActivityLog.create_table()

    db.close_db(None)
########NEW FILE########
__FILENAME__ = create_data_sources
import logging
import peewee
from playhouse.migrate import Migrator
from redash import db
from redash import models
from redash import settings

if __name__ == '__main__':
    db.connect_db()

    if not models.DataSource.table_exists():
        print "Creating data_sources table..."
        models.DataSource.create_table()

        default_data_source = models.DataSource.create(name="Default",
                                                       type=settings.CONNECTION_ADAPTER,
                                                       options=settings.CONNECTION_STRING)
    else:
        default_data_source = models.DataSource.select().first()

    migrator = Migrator(db.database)
    models.Query.data_source.null = True
    models.QueryResult.data_source.null = True
    try:
        with db.database.transaction():
            migrator.add_column(models.Query, models.Query.data_source, "data_source_id")
    except peewee.ProgrammingError:
        print "Failed to create data_source_id column -- assuming it already exists"

    try:
        with db.database.transaction():
            migrator.add_column(models.QueryResult, models.QueryResult.data_source, "data_source_id")
    except peewee.ProgrammingError:
        print "Failed to create data_source_id column -- assuming it already exists"

    print "Updating data source to existing one..."
    models.Query.update(data_source=default_data_source.id).execute()
    models.QueryResult.update(data_source=default_data_source.id).execute()

    with db.database.transaction():
        print "Setting data source to non nullable..."
        migrator.set_nullable(models.Query, models.Query.data_source, False)

    with db.database.transaction():
        print "Setting data source to non nullable..."
        migrator.set_nullable(models.QueryResult, models.QueryResult.data_source, False)

    db.close_db(None)
########NEW FILE########
__FILENAME__ = create_users
import json
import itertools
import peewee
from playhouse.migrate import Migrator
from redash import db, settings
from redash import models

if __name__ == '__main__':
    db.connect_db()

    if not models.User.table_exists():
        print "Creating user table..."
        models.User.create_table()

    migrator = Migrator(db.database)
    with db.database.transaction():
        print "Creating user field on dashboard and queries..."
        try:
            migrator.rename_column(models.Query, '"user"', "user_email")
            migrator.rename_column(models.Dashboard, '"user"', "user_email")
        except peewee.ProgrammingError:
            print "Failed to rename user column -- assuming it already exists"

    with db.database.transaction():
        models.Query.user.null = True
        models.Dashboard.user.null = True

        try:
            migrator.add_column(models.Query, models.Query.user, "user_id")
            migrator.add_column(models.Dashboard, models.Dashboard.user, "user_id")
        except peewee.ProgrammingError:
            print "Failed to create user_id column -- assuming it already exists"

    print "Creating user for all queries and dashboards..."
    for obj in itertools.chain(models.Query.select(), models.Dashboard.select()):
        # Some old databases might have queries with empty string as user email:
        email = obj.user_email or settings.ADMINS[0]
        email = email.split(',')[0]

        print ".. {} , {}, {}".format(type(obj), obj.id, email)

        try:
            user = models.User.get(models.User.email == email)
        except models.User.DoesNotExist:
            is_admin = email in settings.ADMINS
            user = models.User.create(email=email, name=email, is_admin=is_admin)

        obj.user = user
        obj.save()

    print "Set user_id to non null..."
    with db.database.transaction():
        migrator.set_nullable(models.Query, models.Query.user, False)
        migrator.set_nullable(models.Dashboard, models.Dashboard.user, False)
        migrator.set_nullable(models.Query, models.Query.user_email, True)
        migrator.set_nullable(models.Dashboard, models.Dashboard.user_email, True)

########NEW FILE########
__FILENAME__ = create_visualizations
import json
from playhouse.migrate import Migrator
from redash import db
from redash import models

if __name__ == '__main__':
    default_options = {"series": {"type": "column"}}

    db.connect_db()

    if not models.Visualization.table_exists():
        print "Creating visualization table..."
        models.Visualization.create_table()

    with db.database.transaction():
        migrator = Migrator(db.database)
        print "Adding visualization_id to widgets:"
        field = models.Widget.visualization
        field.null = True
        migrator.add_column(models.Widget, models.Widget.visualization, 'visualization_id')

    print 'Creating TABLE visualizations for all queries...'
    for query in models.Query.select():
        vis = models.Visualization(query=query, name="Table",
                                   description=query.description or "",
                                   type="TABLE", options="{}")
        vis.save()

    print 'Creating COHORT visualizations for all queries named like %cohort%...'
    for query in models.Query.select().where(models.Query.name ** "%cohort%"):
        vis = models.Visualization(query=query, name="Cohort",
                                   description=query.description or "",
                                   type="COHORT", options="{}")
        vis.save()

    print 'Create visualization for all widgets (unless exists already):'
    for widget in models.Widget.select():
        print 'Processing widget id: %d:' % widget.id
        vis_type = widget.type.upper()
        if vis_type == 'GRID':
            vis_type = 'TABLE'

        query = models.Query.get_by_id(widget.query_id)
        vis = query.visualizations.where(models.Visualization.type == vis_type).first()
        if vis:
            print '... visualization type (%s) found.' % vis_type
            widget.visualization = vis
            widget.save()
        else:
            vis_name = vis_type.title()

            options = json.loads(widget.options)
            vis_options = {"series": options} if options else default_options
            vis_options = json.dumps(vis_options)

            vis = models.Visualization(query=query, name=vis_name,
                                       description=query.description or "",
                                       type=vis_type, options=vis_options)

            print '... Created visualization for type: %s' % vis_type
            vis.save()
            widget.visualization = vis
            widget.save()

    with db.database.transaction():
        migrator = Migrator(db.database)
        print "Setting visualization_id as not null..."
        migrator.set_nullable(models.Widget, models.Widget.visualization, False)

    db.close_db(None)
########NEW FILE########
__FILENAME__ = permissions_migration
import peewee
from playhouse.migrate import Migrator
from redash import db
from redash import models


if __name__ == '__main__':
    db.connect_db()
    migrator = Migrator(db.database)
    
    if not models.Group.table_exists():
        print "Creating groups table..."
        models.Group.create_table()
    
    with db.database.transaction():
        models.Group.insert(name='admin', permissions=['admin'], tables=['*']).execute()
        models.Group.insert(name='api', permissions=['view_query'], tables=['*']).execute()
        models.Group.insert(name='default', permissions=models.Group.DEFAULT_PERMISSIONS, tables=['*']).execute()

        migrator.add_column(models.User, models.User.groups, 'groups')
        
        models.User.update(groups=['admin', 'default']).where(peewee.SQL("is_admin = true")).execute()
        models.User.update(groups=['admin', 'default']).where(peewee.SQL("'admin' = any(permissions)")).execute()
        models.User.update(groups=['default']).where(peewee.SQL("is_admin = false")).execute()

        migrator.drop_column(models.User, 'permissions')
        migrator.drop_column(models.User, 'is_admin')

    db.close_db(None)

########NEW FILE########
__FILENAME__ = authentication
import functools
import hashlib
import hmac
import time
import logging

from flask import request, make_response, redirect, url_for
from flask.ext.login import LoginManager, login_user, current_user
from flask.ext.googleauth import GoogleAuth, login
from werkzeug.contrib.fixers import ProxyFix

from redash import models, settings

login_manager = LoginManager()
logger = logging.getLogger('authentication')


def sign(key, path, expires):
    if not key:
        return None

    h = hmac.new(str(key), msg=path, digestmod=hashlib.sha1)
    h.update(str(expires))

    return h.hexdigest()


class HMACAuthentication(object):
    @staticmethod
    def api_key_authentication():
        signature = request.args.get('signature')
        expires = float(request.args.get('expires') or 0)
        query_id = request.view_args.get('query_id', None)

        # TODO: 3600 should be a setting
        if signature and query_id and time.time() < expires <= time.time() + 3600:
            query = models.Query.get(models.Query.id == query_id)
            calculated_signature = sign(query.api_key, request.path, expires)

            if query.api_key and signature == calculated_signature:
                login_user(models.ApiUser(query.api_key), remember=False)
                return True

        return False

    def required(self, fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            if current_user.is_authenticated():
                return fn(*args, **kwargs)

            if self.api_key_authentication():
                return fn(*args, **kwargs)

            return make_response(redirect(url_for("login", next=request.url)))

        return decorated


def validate_email(email):
    if not settings.GOOGLE_APPS_DOMAIN:
        return True

    return email in settings.ALLOWED_EXTERNAL_USERS or email.endswith("@%s" % settings.GOOGLE_APPS_DOMAIN)


def create_and_login_user(app, user):
    if not validate_email(user.email):
        return

    try:
        user_object = models.User.get(models.User.email == user.email)
        if user_object.name != user.name:
            logger.debug("Updating user name (%r -> %r)", user_object.name, user.name)
            user_object.name = user.name
            user_object.save()
    except models.User.DoesNotExist:
        logger.debug("Creating user object (%r)", user.name)
        user_object = models.User.create(name=user.name, email=user.email, groups = ['default'])

    login_user(user_object, remember=True)

login.connect(create_and_login_user)


@login_manager.user_loader
def load_user(user_id):
    return models.User.select().where(models.User.id == user_id).first()


def setup_authentication(app):
    if settings.GOOGLE_OPENID_ENABLED:
        openid_auth = GoogleAuth(app, url_prefix="/google_auth")
        # If we don't have a list of external users, we can use Google's federated login, which limits
        # the domain with which you can sign in.
        if not settings.ALLOWED_EXTERNAL_USERS and settings.GOOGLE_APPS_DOMAIN:
            openid_auth._OPENID_ENDPOINT = "https://www.google.com/a/%s/o8/ud?be=o8" % settings.GOOGLE_APPS_DOMAIN

    login_manager.init_app(app)
    login_manager.anonymous_user = models.AnonymousUser
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.secret_key = settings.COOKIE_SECRET

    return HMACAuthentication()

########NEW FILE########
__FILENAME__ = controllers
"""
Flask-restful based API implementation for re:dash.

Currently the Flask server is used to serve the static assets (and the Angular.js app),
but this is only due to configuration issues and temporary.
"""
import csv
import hashlib
import json
import numbers
import cStringIO
import datetime

from flask import render_template, send_from_directory, make_response, request, jsonify, redirect, \
    session, url_for
from flask.ext.restful import Resource, abort
from flask_login import current_user, login_user, logout_user

import sqlparse
import events
from permissions import require_permission

from redash import redis_connection, statsd_client, models, settings, utils, __version__
from redash.wsgi import app, auth, api

import logging
from tasks import QueryTask


@app.route('/ping', methods=['GET'])
def ping():
    return 'PONG.'


@app.route('/admin/<anything>')
@app.route('/dashboard/<anything>')
@app.route('/queries')
@app.route('/queries/<query_id>')
@app.route('/queries/<query_id>/<anything>')
@app.route('/')
@auth.required
def index(**kwargs):
    email_md5 = hashlib.md5(current_user.email.lower()).hexdigest()
    gravatar_url = "https://www.gravatar.com/avatar/%s?s=40" % email_md5

    user = {
        'gravatar_url': gravatar_url,
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'groups': current_user.groups,
        'permissions': current_user.permissions
    }

    features = {
        'clientSideMetrics': settings.CLIENT_SIDE_METRICS
    }

    return render_template("index.html", user=json.dumps(user), name=settings.NAME,
                           features=json.dumps(features),
                           analytics=settings.ANALYTICS)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated():
        return redirect(request.args.get('next') or '/')

    if not settings.PASSWORD_LOGIN_ENABLED:
        blueprint = app.extensions['googleauth'].blueprint
        return redirect(url_for("%s.login" % blueprint.name, next=request.args.get('next')))

    if request.method == 'POST':
        user = models.User.select().where(models.User.email == request.form['username']).first()
        if user and user.verify_password(request.form['password']):
            remember = ('remember' in request.form)
            login_user(user, remember=remember)
            return redirect(request.args.get('next') or '/')

    return render_template("login.html",
                           name=settings.NAME,
                           analytics=settings.ANALYTICS,
                           next=request.args.get('next'),
                           username=request.form.get('username', ''),
                           show_google_openid=settings.GOOGLE_OPENID_ENABLED)


@app.route('/logout')
def logout():
    logout_user()
    session.pop('openid', None)

    return redirect('/login')

@app.route('/status.json')
@auth.required
@require_permission('admin')
def status_api():
    status = {}
    info = redis_connection.info()
    status['redis_used_memory'] = info['used_memory_human']
    status['version'] = __version__
    status['queries_count'] = models.Query.select().count()
    status['query_results_count'] = models.QueryResult.select().count()
    status['dashboards_count'] = models.Dashboard.select().count()
    status['widgets_count'] = models.Widget.select().count()

    status['workers'] = []

    manager_status = redis_connection.hgetall('redash:status')
    status['manager'] = manager_status
    status['manager']['queue_size'] = 'Unknown'#redis_connection.zcard('jobs')

    return jsonify(status)


@app.route('/api/queries/format', methods=['POST'])
@auth.required
def format_sql_query():
    arguments = request.get_json(force=True)
    query = arguments.get("query", "")

    return sqlparse.format(query, reindent=True, keyword_case='upper')


class BaseResource(Resource):
    decorators = [auth.required]

    def __init__(self, *args, **kwargs):
        super(BaseResource, self).__init__(*args, **kwargs)
        self._user = None

    @property
    def current_user(self):
        return current_user._get_current_object()

    def dispatch_request(self, *args, **kwargs):
        with statsd_client.timer('requests.{}.{}'.format(request.endpoint, request.method.lower())):
            response = super(BaseResource, self).dispatch_request(*args, **kwargs)
        return response


class EventAPI(BaseResource):
    def post(self):
        events_list = request.get_json(force=True)
        for event in events_list:
            events.record_event(event)


api.add_resource(EventAPI, '/api/events', endpoint='events')


class MetricsAPI(BaseResource):
    def post(self):
        for stat_line in request.data.split():
            stat, value = stat_line.split(':')
            statsd_client._send_stat('client.{}'.format(stat), value, 1)

        return "OK."

api.add_resource(MetricsAPI, '/api/metrics/v1/send', endpoint='metrics')


class DataSourceListAPI(BaseResource):
    def get(self):
        data_sources = [ds.to_dict() for ds in models.DataSource.select()]
        return data_sources

api.add_resource(DataSourceListAPI, '/api/data_sources', endpoint='data_sources')


class DashboardListAPI(BaseResource):
    def get(self):
        dashboards = [d.to_dict() for d in
                      models.Dashboard.select().where(models.Dashboard.is_archived==False)]

        return dashboards

    @require_permission('create_dashboard')
    def post(self):
        dashboard_properties = request.get_json(force=True)
        dashboard = models.Dashboard(name=dashboard_properties['name'],
                                     user=self.current_user,
                                     layout='[]')
        dashboard.save()
        return dashboard.to_dict()


class DashboardAPI(BaseResource):
    def get(self, dashboard_slug=None):
        try:
            dashboard = models.Dashboard.get_by_slug(dashboard_slug)
        except models.Dashboard.DoesNotExist:
            abort(404)

        return dashboard.to_dict(with_widgets=True)

    @require_permission('edit_dashboard')
    def post(self, dashboard_slug):
        dashboard_properties = request.get_json(force=True)
        # TODO: either convert all requests to use slugs or ids
        dashboard = models.Dashboard.get_by_id(dashboard_slug)
        dashboard.layout = dashboard_properties['layout']
        dashboard.name = dashboard_properties['name']
        dashboard.save()

        return dashboard.to_dict(with_widgets=True)

    @require_permission('edit_dashboard')
    def delete(self, dashboard_slug):
        dashboard = models.Dashboard.get_by_slug(dashboard_slug)
        dashboard.is_archived = True
        dashboard.save()

api.add_resource(DashboardListAPI, '/api/dashboards', endpoint='dashboards')
api.add_resource(DashboardAPI, '/api/dashboards/<dashboard_slug>', endpoint='dashboard')


class WidgetListAPI(BaseResource):
    @require_permission('edit_dashboard')
    def post(self):
        widget_properties = request.get_json(force=True)
        widget_properties['options'] = json.dumps(widget_properties['options'])
        widget_properties.pop('id', None)
        widget_properties['dashboard'] = widget_properties.pop('dashboard_id')
        widget_properties['visualization'] = widget_properties.pop('visualization_id')
        widget = models.Widget(**widget_properties)
        widget.save()

        layout = json.loads(widget.dashboard.layout)
        new_row = True

        if len(layout) == 0 or widget.width == 2:
            layout.append([widget.id])
        elif len(layout[-1]) == 1:
            neighbour_widget = models.Widget.get(models.Widget.id == layout[-1][0])
            if neighbour_widget.width == 1:
                layout[-1].append(widget.id)
                new_row = False
            else:
                layout.append([widget.id])
        else:
            layout.append([widget.id])

        widget.dashboard.layout = json.dumps(layout)
        widget.dashboard.save()

        return {'widget': widget.to_dict(), 'layout': layout, 'new_row': new_row}


class WidgetAPI(BaseResource):
    @require_permission('edit_dashboard')
    def delete(self, widget_id):
        widget = models.Widget.get(models.Widget.id == widget_id)
        # TODO: reposition existing ones
        layout = json.loads(widget.dashboard.layout)
        layout = map(lambda row: filter(lambda w: w != widget_id, row), layout)
        layout = filter(lambda row: len(row) > 0, layout)
        widget.dashboard.layout = json.dumps(layout)
        widget.dashboard.save()

        widget.delete_instance()

api.add_resource(WidgetListAPI, '/api/widgets', endpoint='widgets')
api.add_resource(WidgetAPI, '/api/widgets/<int:widget_id>', endpoint='widget')


class QueryListAPI(BaseResource):
    @require_permission('create_query')
    def post(self):
        query_def = request.get_json(force=True)
        for field in ['id', 'created_at', 'api_key', 'visualizations', 'latest_query_data']:
            query_def.pop(field, None)

        query_def['user'] = self.current_user
        query_def['data_source'] = query_def.pop('data_source_id')
        query = models.Query(**query_def)
        query.save()

        query.create_default_visualizations()

        return query.to_dict(with_result=False)

    @require_permission('view_query')
    def get(self):
        return [q.to_dict(with_result=False, with_stats=True) for q in models.Query.all_queries()]


class QueryAPI(BaseResource):
    @require_permission('edit_query')
    def post(self, query_id):
        query_def = request.get_json(force=True)
        for field in ['id', 'created_at', 'api_key', 'visualizations', 'latest_query_data', 'user']:
            query_def.pop(field, None)

        if 'latest_query_data_id' in query_def:
            query_def['latest_query_data'] = query_def.pop('latest_query_data_id')

        if 'data_source_id' in query_def:
            query_def['data_source'] = query_def.pop('data_source_id')

        models.Query.update_instance(query_id, **query_def)

        query = models.Query.get_by_id(query_id)

        return query.to_dict(with_result=False, with_visualizations=True)

    @require_permission('view_query')
    def get(self, query_id):
        q = models.Query.get(models.Query.id == query_id)
        if q:
            return q.to_dict(with_visualizations=True)
        else:
            abort(404, message="Query not found.")

api.add_resource(QueryListAPI, '/api/queries', endpoint='queries')
api.add_resource(QueryAPI, '/api/queries/<query_id>', endpoint='query')


class VisualizationListAPI(BaseResource):
    @require_permission('edit_query')
    def post(self):
        kwargs = request.get_json(force=True)
        kwargs['options'] = json.dumps(kwargs['options'])
        kwargs['query'] = kwargs.pop('query_id')

        vis = models.Visualization(**kwargs)
        vis.save()

        return vis.to_dict(with_query=False)


class VisualizationAPI(BaseResource):
    @require_permission('edit_query')
    def post(self, visualization_id):
        kwargs = request.get_json(force=True)
        if 'options' in kwargs:
            kwargs['options'] = json.dumps(kwargs['options'])
        kwargs.pop('id', None)

        update = models.Visualization.update(**kwargs).where(models.Visualization.id == visualization_id)
        update.execute()

        vis = models.Visualization.get_by_id(visualization_id)

        return vis.to_dict(with_query=False)

    @require_permission('edit_query')
    def delete(self, visualization_id):
        vis = models.Visualization.get(models.Visualization.id == visualization_id)
        vis.delete_instance()

api.add_resource(VisualizationListAPI, '/api/visualizations', endpoint='visualizations')
api.add_resource(VisualizationAPI, '/api/visualizations/<visualization_id>', endpoint='visualization')


class QueryResultListAPI(BaseResource):
    @require_permission('execute_query')
    def post(self):
        params = request.json

        if settings.FEATURE_TABLES_PERMISSIONS:
            metadata = utils.SQLMetaData(params['query'])

            if metadata.has_non_select_dml_statements or metadata.has_ddl_statements:
                return {
                    'job': {
                        'error': 'Only SELECT statements are allowed'
                    }
                }

            if len(metadata.used_tables - current_user.allowed_tables) > 0 and '*' not in current_user.allowed_tables:
                logging.warning('Permission denied for user %s to table %s', self.current_user.name, metadata.used_tables)
                return {
                    'job': {
                        'error': 'Access denied for table(s): %s' % (metadata.used_tables)
                    }
                }
        
        models.ActivityLog(
            user=self.current_user,
            type=models.ActivityLog.QUERY_EXECUTION,
            activity=params['query']
        ).save()

        if params['ttl'] == 0:
            query_result = None
        else:
            query_result = models.QueryResult.get_latest(params['data_source_id'], params['query'], int(params['ttl']))

        if query_result:
            return {'query_result': query_result.to_dict()}
        else:
            data_source = models.DataSource.get_by_id(params['data_source_id'])
            job = QueryTask.add_task(params['query'], data_source)
            return {'job': job.to_dict()}


class QueryResultAPI(BaseResource):
    @require_permission('view_query')
    def get(self, query_result_id):
        query_result = models.QueryResult.get_by_id(query_result_id)
        if query_result:
            return {'query_result': query_result.to_dict()}
        else:
            abort(404)


class CsvQueryResultsAPI(BaseResource):
    @require_permission('view_query')
    def get(self, query_id, query_result_id=None):
        if not query_result_id:
            query = models.Query.get(models.Query.id == query_id)
            if query:
                query_result_id = query._data['latest_query_data']

        query_result = query_result_id and models.QueryResult.get_by_id(query_result_id)
        if query_result:
            s = cStringIO.StringIO()

            query_data = json.loads(query_result.data)
            writer = csv.DictWriter(s, fieldnames=[col['name'] for col in query_data['columns']])
            writer.writer = utils.UnicodeWriter(s)
            writer.writeheader()
            for row in query_data['rows']:
                for k, v in row.iteritems():
                    if isinstance(v, numbers.Number) and (v > 1000 * 1000 * 1000 * 100):
                        row[k] = datetime.datetime.fromtimestamp(v/1000.0)

                writer.writerow(row)

            return make_response(s.getvalue(), 200, {'Content-Type': "text/csv; charset=UTF-8"})
        else:
            abort(404)

api.add_resource(CsvQueryResultsAPI, '/api/queries/<query_id>/results/<query_result_id>.csv',
                 '/api/queries/<query_id>/results.csv',
                 endpoint='csv_query_results')
api.add_resource(QueryResultListAPI, '/api/query_results', endpoint='query_results')
api.add_resource(QueryResultAPI, '/api/query_results/<query_result_id>', endpoint='query_result')


class JobAPI(BaseResource):
    def get(self, job_id):
        # TODO: if finished, include the query result
        job = QueryTask(job_id=job_id)
        return {'job': job.to_dict()}

    def delete(self, job_id):
        job = QueryTask(job_id=job_id)
        job.cancel()

api.add_resource(JobAPI, '/api/jobs/<job_id>', endpoint='job')

@app.route('/<path:filename>')
def send_static(filename):
    return send_from_directory(settings.STATIC_ASSETS_PATH, filename)


if __name__ == '__main__':
    app.run(debug=True)




########NEW FILE########
__FILENAME__ = query_runner
import json


def get_query_runner(connection_type, connection_string):
    if connection_type == 'mysql':
        from redash.data import query_runner_mysql
        runner = query_runner_mysql.mysql(connection_string)
    elif connection_type == 'graphite':
        from redash.data import query_runner_graphite
        connection_params = json.loads(connection_string)
        if connection_params['auth']:
            connection_params['auth'] = tuple(connection_params['auth'])
        else:
            connection_params['auth'] = None
        runner = query_runner_graphite.graphite(connection_params)
    elif connection_type == 'bigquery':
        from redash.data import query_runner_bigquery
        connection_params = json.loads(connection_string)
        runner = query_runner_bigquery.bigquery(connection_params)
    elif connection_type == 'script':
        from redash.data import query_runner_script
        runner = query_runner_script.script(connection_string)
    elif connection_type == 'url':
        from redash.data import query_runner_url
        runner = query_runner_url.url(connection_string)
    else:
        from redash.data import query_runner_pg
        runner = query_runner_pg.pg(connection_string)

    return runner
########NEW FILE########
__FILENAME__ = query_runner_bigquery
import httplib2
import json
import logging
import sys
import time

try:
    import apiclient.errors
    from apiclient.discovery import build
    from apiclient.errors import HttpError
    from oauth2client.client import SignedJwtAssertionCredentials
except ImportError:
    print "Missing dependencies. Please install google-api-python-client and oauth2client."
    print "You can use pip:   pip install google-api-python-client oauth2client"

from redash.utils import JSONEncoder


def bigquery(connection_string):
    def load_key(filename):
        f = file(filename, "rb")
        try:
            return f.read()
        finally:
            f.close()

    def get_bigquery_service():
        scope = [
            "https://www.googleapis.com/auth/bigquery",
        ]

        credentials = SignedJwtAssertionCredentials(connection_string["serviceAccount"],
                                                    load_key(connection_string["privateKey"]), scope=scope)
        http = httplib2.Http()
        http = credentials.authorize(http)

        return build("bigquery", "v2", http=http)

    def get_query_results(jobs, project_id, job_id, start_index):
        query_reply = jobs.getQueryResults(projectId=project_id, jobId=job_id, startIndex=start_index).execute()
        logging.debug('query_reply %s', query_reply)
        if not query_reply['jobComplete']:
            time.sleep(10)
            return get_query_results(jobs, project_id, job_id, start_index)

        return query_reply

    def query_runner(query):
        bigquery_service = get_bigquery_service()

        jobs = bigquery_service.jobs()
        job_data = {
            "configuration": {
                "query": {
                    "query": query,
                }
            }
        }

        logging.debug("bigquery got query: %s", query)

        project_id = connection_string["projectId"]

        try:
            insert_response = jobs.insert(projectId=project_id, body=job_data).execute()
            current_row = 0
            query_reply = get_query_results(jobs, project_id=project_id,
                                            job_id=insert_response['jobReference']['jobId'], start_index=current_row)

            rows = []
            field_names = []
            for f in query_reply["schema"]["fields"]:
                field_names.append(f["name"])

            while ("rows" in query_reply) and current_row < query_reply['totalRows']:
                for row in query_reply["rows"]:
                    row_data = {}
                    column_index = 0
                    for cell in row["f"]:
                        row_data[field_names[column_index]] = cell["v"]
                        column_index += 1

                    rows.append(row_data)

                current_row += len(query_reply['rows'])
                query_reply = jobs.getQueryResults(projectId=project_id, jobId=query_reply['jobReference']['jobId'],
                                                   startIndex=current_row).execute()

            columns = [{'name': name,
                        'friendly_name': name,
                        'type': None} for name in field_names]

            data = {
                "columns": columns,
                "rows": rows
            }
            error = None

            json_data = json.dumps(data, cls=JSONEncoder)
        except apiclient.errors.HttpError, e:
            json_data = None
            error = e.content
        except KeyboardInterrupt:
            error = "Query cancelled by user."
            json_data = None
        except Exception:
            raise sys.exc_info()[1], None, sys.exc_info()[2]

        return json_data, error


    return query_runner

########NEW FILE########
__FILENAME__ = query_runner_graphite
"""
QueryRunner for Graphite.
"""
import json
import datetime
import requests
from redash.utils import JSONEncoder


def graphite(connection_params):
    def transform_result(response):
        columns = [{'name': 'Time::x'}, {'name': 'value::y'}, {'name': 'name::series'}]
        rows = []

        for series in response.json():
            for values in series['datapoints']:
                timestamp = datetime.datetime.fromtimestamp(int(values[1]))
                rows.append({'Time::x': timestamp, 'name::series': series['target'], 'value::y': values[0]})

        data = {'columns': columns, 'rows': rows}
        return json.dumps(data, cls=JSONEncoder)

    def query_runner(query):
        base_url = "%s/render?format=json&" % connection_params['url']
        url = "%s%s" % (base_url, "&".join(query.split("\n")))
        error = None
        data = None

        try:
            response = requests.get(url, auth=connection_params['auth'],
                                    verify=connection_params['verify'])

            if response.status_code == 200:
                data = transform_result(response)
            else:
                error = "Failed getting results (%d)" % response.status_code

        except Exception, ex:
            data = None
            error = ex.message

        return data, error

    query_runner.annotate_query = False

    return query_runner
########NEW FILE########
__FILENAME__ = query_runner_mysql
"""
QueryRunner is the function that the workers use, to execute queries. This is the Redshift
(PostgreSQL in fact) version, but easily we can write another to support additional databases
(MySQL and others).

Because the worker just pass the query, this can be used with any data store that has some sort of
query language (for example: HiveQL).
"""
import logging
import json
import MySQLdb
import sys
from redash.utils import JSONEncoder

def mysql(connection_string):
    if connection_string.endswith(';'):
        connection_string = connection_string[0:-1]
    
    def query_runner(query):
        connections_params = [entry.split('=')[1] for entry in connection_string.split(';')]
        connection = MySQLdb.connect(*connections_params)
        cursor = connection.cursor()

        logging.debug("mysql got query: %s", query)
        
        try:
            cursor.execute(query)
            
            data = cursor.fetchall()
            
            cursor_desc = cursor.description
            if (cursor_desc != None):
                num_fields = len(cursor_desc)
                column_names = [i[0] for i in cursor.description]
            
                rows = [dict(zip(column_names, row)) for row in data]

                columns = [{'name': col_name,
                            'friendly_name': col_name,
                            'type': None} for col_name in column_names]
            
                data = {'columns': columns, 'rows': rows}
                json_data = json.dumps(data, cls=JSONEncoder)
                error = None
            else:
                json_data = None
                error = "No data was returned."
                
            cursor.close()
        except MySQLdb.Error, e:
            json_data = None
            error = e.args[1]
        except KeyboardInterrupt:
            error = "Query cancelled by user."
            json_data = None            
        except Exception as e:
            raise sys.exc_info()[1], None, sys.exc_info()[2]
        finally:
            connection.close()
        
        return json_data, error
        
    
    return query_runner
########NEW FILE########
__FILENAME__ = query_runner_pg
"""
QueryRunner is the function that the workers use, to execute queries. This is the PostgreSQL
version, but easily we can write another to support additional databases (MySQL and others).

Because the worker just pass the query, this can be used with any data store that has some sort of
query language (for example: HiveQL).
"""
import json
import sys
import select
import logging
import psycopg2

from redash.utils import JSONEncoder

types_map = {
    20: 'integer',
    21: 'integer',
    23: 'integer',
    700: 'float',
    1700: 'float',
    701: 'float',
    16: 'boolean',
    1082: 'date',
    1114: 'datetime',
    1184: 'datetime',
    1014: 'string',
    1015: 'string',
    1008: 'string',
    1009: 'string',
    2951: 'string'
}


def pg(connection_string):
    def column_friendly_name(column_name):
        return column_name

    def wait(conn):
        while 1:
            try:
                state = conn.poll()
                if state == psycopg2.extensions.POLL_OK:
                    break
                elif state == psycopg2.extensions.POLL_WRITE:
                    select.select([], [conn.fileno()], [])
                elif state == psycopg2.extensions.POLL_READ:
                    select.select([conn.fileno()], [], [])
                else:
                    raise psycopg2.OperationalError("poll() returned %s" % state)
            except select.error:
                raise psycopg2.OperationalError("select.error received")

    def query_runner(query):
        connection = psycopg2.connect(connection_string, async=True)
        wait(connection)

        cursor = connection.cursor()

        try:
            cursor.execute(query)
            wait(connection)

            # While set would be more efficient here, it sorts the data which is not what we want, but due to the small
            # size of the data we can assume it's ok.
            column_names = []
            columns = []
            duplicates_counter = 1

            for column in cursor.description:
                # TODO: this deduplication needs to be generalized and reused in all query runners.
                column_name = column.name
                if column_name in column_names:
                    column_name = column_name + str(duplicates_counter)
                    duplicates_counter += 1

                column_names.append(column_name)

                columns.append({
                    'name': column_name,
                    'friendly_name': column_friendly_name(column_name),
                    'type': types_map.get(column.type_code, None)
                })

            rows = [dict(zip(column_names, row)) for row in cursor]

            data = {'columns': columns, 'rows': rows}
            json_data = json.dumps(data, cls=JSONEncoder)
            error = None
            cursor.close()
        except (select.error, OSError, psycopg2.OperationalError) as e:
            logging.exception(e)
            error = "Query interrupted. Please retry."
            json_data = None
        except psycopg2.DatabaseError as e:
            json_data = None
            error = e.message
        except KeyboardInterrupt:
            connection.cancel()
            error = "Query cancelled by user."
            json_data = None
        except Exception as e:
            raise sys.exc_info()[1], None, sys.exc_info()[2]
        finally:
            connection.close()

        return json_data, error

    return query_runner

########NEW FILE########
__FILENAME__ = query_runner_script
import json
import logging
import sys
import os
import subprocess

# We use subprocess.check_output because we are lazy.
# If someone will really want to run this on Python < 2.7 they can easily update the code to run
# Popen, check the retcodes and other things and read the standard output to a variable.
if not "check_output" in subprocess.__dict__:
    print "ERROR: This runner uses subprocess.check_output function which exists in Python 2.7"

def script(connection_string):

    def query_runner(query):
        try:
            json_data = None
            error = None

            # Poor man's protection against running scripts from output the scripts directory
            if connection_string.find("../") > -1:
                return None, "Scripts can only be run from the configured scripts directory"

            query = query.strip()

            script = os.path.join(connection_string, query)
            if not os.path.exists(script):
                return None, "Script '%s' not found in script directory" % query

            output = subprocess.check_output(script, shell=False)
            if output != None:
                output = output.strip()
                if output != "":
                    return output, None

            error = "Error reading output"
        except subprocess.CalledProcessError as e:
            return None, str(e)
        except KeyboardInterrupt:
            error = "Query cancelled by user."
            json_data = None
        except Exception as e:
            raise sys.exc_info()[1], None, sys.exc_info()[2]

        return json_data, error

    query_runner.annotate_query = False
    return query_runner

########NEW FILE########
__FILENAME__ = query_runner_url
import json
import logging
import sys
import os
import urllib2

def url(connection_string):

    def query_runner(query):
        base_url = connection_string

        try:
            json_data = None
            error = None

            query = query.strip()

            if base_url is not None and base_url != "":
                if query.find("://") > -1:
                    return None, "Accepting only relative URLs to '%s'" % base_url

            if base_url is None:
                base_url = ""

            url = base_url + query

            json_data = urllib2.urlopen(url).read().strip()

            if not json_data:
                error = "Error reading data from '%s'" % url

            return json_data, error

        except urllib2.URLError as e:
            return None, str(e)
        except KeyboardInterrupt:
            error = "Query cancelled by user."
            json_data = None
        except Exception as e:
            raise sys.exc_info()[1], None, sys.exc_info()[2]

        return json_data, error

    query_runner.annotate_query = False
    return query_runner

########NEW FILE########
__FILENAME__ = events
import logging
import json

logger = logging.getLogger("redash.events")
logger.propagate = False


def setup_logging(log_path, console_output=False):
    if log_path:
        fh = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    if console_output:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(name)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def record_event(event):
    logger.info(json.dumps(event))
########NEW FILE########
__FILENAME__ = import_export
import contextlib
import json
from redash import models
from flask.ext.script import Manager


class Importer(object):
    def __init__(self, object_mapping=None, data_source=None):
        if object_mapping is None:
            object_mapping = {}
        self.object_mapping = object_mapping
        self.data_source = data_source

    def import_query_result(self, query_result):
        query_result = self._get_or_create(models.QueryResult, query_result['id'],
                                           data_source=self.data_source,
                                           data=json.dumps(query_result['data']),
                                           query_hash=query_result['query_hash'],
                                           retrieved_at=query_result['retrieved_at'],
                                           query=query_result['query'],
                                           runtime=query_result['runtime'])

        return query_result


    def import_query(self, user, query):
        query_result = self.import_query_result(query['latest_query_data'])

        new_query = self._get_or_create(models.Query, query['id'], name=query['name'],
                                        user=user,
                                        ttl=-1,
                                        query=query['query'],
                                        query_hash=query['query_hash'],
                                        description=query['description'],
                                        latest_query_data=query_result,
                                        data_source=self.data_source)

        return new_query


    def import_visualization(self, user, visualization):
        query = self.import_query(user, visualization['query'])

        new_visualization = self._get_or_create(models.Visualization, visualization['id'],
                                                name=visualization['name'],
                                                description=visualization['description'],
                                                type=visualization['type'],
                                                options=json.dumps(visualization['options']),
                                                query=query)
        return new_visualization

    def import_widget(self, dashboard, widget):
        visualization = self.import_visualization(dashboard.user, widget['visualization'])

        new_widget = self._get_or_create(models.Widget, widget['id'],
                                         dashboard=dashboard,
                                         width=widget['width'],
                                         options=json.dumps(widget['options']),
                                         visualization=visualization)

        return new_widget

    def import_dashboard(self, user, dashboard):
        """
        Imports dashboard along with widgets, visualizations and queries from another re:dash.

        user - the user to associate all objects with.
        dashboard - dashboard to import (can be result of loading a json output).
        """

        new_dashboard = self._get_or_create(models.Dashboard, dashboard['id'],
                                            name=dashboard['name'],
                                            slug=dashboard['slug'],
                                            layout='[]',
                                            user=user)

        layout = []

        for widgets in dashboard['widgets']:
            row = []
            for widget in widgets:
                widget_id = self.import_widget(new_dashboard, widget).id
                row.append(widget_id)

            layout.append(row)

        new_dashboard.layout = json.dumps(layout)
        new_dashboard.save()

        return new_dashboard

    def _get_or_create(self, object_type, external_id, **properties):
        internal_id = self._get_mapping(object_type, external_id)
        if internal_id:
            update = object_type.update(**properties).where(object_type.id == internal_id)
            update.execute()
            obj = object_type.get_by_id(internal_id)
        else:
            obj = object_type.create(**properties)
            self._update_mapping(object_type, external_id, obj.id)

        return obj

    def _get_mapping(self, object_type, external_id):
        self.object_mapping.setdefault(object_type.__name__, {})
        return self.object_mapping[object_type.__name__].get(str(external_id), None)

    def _update_mapping(self, object_type, external_id, internal_id):
        self.object_mapping.setdefault(object_type.__name__, {})
        self.object_mapping[object_type.__name__][str(external_id)] = internal_id

import_manager = Manager(help="import utilities")
export_manager = Manager(help="export utilities")


@contextlib.contextmanager
def importer_with_mapping_file(mapping_filename):
    with open(mapping_filename) as f:
        mapping = json.loads(f.read())

    importer = Importer(object_mapping=mapping, data_source=get_data_source())
    yield importer

    with open(mapping_filename, 'w') as f:
        f.write(json.dumps(importer.object_mapping, indent=2))


def get_data_source():
    try:
        data_source = models.DataSource.get(models.DataSource.name=="Import")
    except models.DataSource.DoesNotExist:
        data_source = models.DataSource.create(name="Import", type="import", options='{}')

    return data_source

@import_manager.command
def query(mapping_filename, query_filename, user_id):
    user = models.User.get_by_id(user_id)
    with open(query_filename) as f:
        query = json.loads(f.read())

    with importer_with_mapping_file(mapping_filename) as importer:
        imported_query = importer.import_query(user, query)

        print "New query id: {}".format(imported_query.id)


@import_manager.command
def dashboard(mapping_filename, dashboard_filename, user_id):
    user = models.User.get_by_id(user_id)
    with open(dashboard_filename) as f:
        dashboard = json.loads(f.read())

    with importer_with_mapping_file(mapping_filename) as importer:
        importer.import_dashboard(user, dashboard)




########NEW FILE########
__FILENAME__ = models
import json
import hashlib
import logging
import os
import threading
import time
import datetime
import itertools

import peewee
from passlib.apps import custom_app_context as pwd_context
from playhouse.postgres_ext import ArrayField
from flask.ext.login import UserMixin, AnonymousUserMixin

from redash import utils, settings


class Database(object):
    def __init__(self):
        self.database_config = dict(settings.DATABASE_CONFIG)
        self.database_name = self.database_config.pop('name')
        self.database = peewee.PostgresqlDatabase(self.database_name, **self.database_config)
        self.app = None
        self.pid = os.getpid()

    def init_app(self, app):
        self.app = app
        self.register_handlers()

    def connect_db(self):
        self._check_pid()
        self.database.connect()

    def close_db(self, exc):
        self._check_pid()
        if not self.database.is_closed():
            self.database.close()

    def _check_pid(self):
        current_pid = os.getpid()
        if self.pid != current_pid:
            logging.info("New pid detected (%d!=%d); resetting database lock.", self.pid, current_pid)
            self.pid = os.getpid()
            self.database._conn_lock = threading.Lock()

    def register_handlers(self):
        self.app.before_request(self.connect_db)
        self.app.teardown_request(self.close_db)


db = Database()


class BaseModel(peewee.Model):
    class Meta:
        database = db.database

    @classmethod
    def get_by_id(cls, model_id):
        return cls.get(cls.id == model_id)


class AnonymousUser(AnonymousUserMixin):
    @property
    def permissions(self):
        return []


class ApiUser(UserMixin):
    def __init__(self, api_key):
        self.id = api_key

    @property
    def permissions(self):
        return ['view_query']


class Group(BaseModel):
    DEFAULT_PERMISSIONS = ['create_dashboard', 'create_query', 'edit_dashboard', 'edit_query',
                           'view_query', 'view_source', 'execute_query']
    
    id = peewee.PrimaryKeyField()
    name = peewee.CharField(max_length=100)
    permissions = ArrayField(peewee.CharField, default=DEFAULT_PERMISSIONS)
    tables = ArrayField(peewee.CharField)
    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'groups'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'permissions': self.permissions,
            'tables': self.tables,
            'created_at': self.created_at
        }

    def __unicode__(self):
        return unicode(self.id)


class User(BaseModel, UserMixin):
    id = peewee.PrimaryKeyField()
    name = peewee.CharField(max_length=320)
    email = peewee.CharField(max_length=320, index=True, unique=True)
    password_hash = peewee.CharField(max_length=128, null=True)
    groups = ArrayField(peewee.CharField, default=['default'])

    class Meta:
        db_table = 'users'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email
        }

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self._allowed_tables = None

    @property
    def permissions(self):
        # TODO: this should be cached.
        return list(itertools.chain(*[g.permissions for g in
                                      Group.select().where(Group.name << self.groups)]))

    @property
    def allowed_tables(self):
        # TODO: cache this as weel
        if self._allowed_tables is None:
            self._allowed_tables = set([t.lower() for t in itertools.chain(*[g.tables for g in
                                        Group.select().where(Group.name << self.groups)])])

        return self._allowed_tables

    def __unicode__(self):
        return '%r, %r' % (self.name, self.email)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return self.password_hash and pwd_context.verify(password, self.password_hash)


class ActivityLog(BaseModel):
    QUERY_EXECUTION = 1
    
    id = peewee.PrimaryKeyField()
    user = peewee.ForeignKeyField(User)
    type = peewee.IntegerField()
    activity = peewee.TextField()
    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'activity_log'

    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.to_dict(),
            'type': self.type,
            'activity': self.activity,
            'created_at': self.created_at
        }

    def __unicode__(self):
        return unicode(self.id)


class DataSource(BaseModel):
    id = peewee.PrimaryKeyField()
    name = peewee.CharField()
    type = peewee.CharField()
    options = peewee.TextField()
    queue_name = peewee.CharField(default="queries")
    scheduled_queue_name = peewee.CharField(default="queries")
    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'data_sources'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type
        }


class QueryResult(BaseModel):
    id = peewee.PrimaryKeyField()
    data_source = peewee.ForeignKeyField(DataSource)
    query_hash = peewee.CharField(max_length=32, index=True)
    query = peewee.TextField()
    data = peewee.TextField()
    runtime = peewee.FloatField()
    retrieved_at = peewee.DateTimeField()

    class Meta:
        db_table = 'query_results'

    def to_dict(self):
        return {
            'id': self.id,
            'query_hash': self.query_hash,
            'query': self.query,
            'data': json.loads(self.data),
            'data_source_id': self._data.get('data_source', None),
            'runtime': self.runtime,
            'retrieved_at': self.retrieved_at
        }

    @classmethod
    def get_latest(cls, data_source, query, ttl=0):
        query_hash = utils.gen_query_hash(query)

        if ttl == -1:
            query = cls.select().where(cls.query_hash == query_hash,
                                       cls.data_source == data_source).order_by(cls.retrieved_at.desc())
        else:
            query = cls.select().where(cls.query_hash == query_hash, cls.data_source == data_source,
                                       peewee.SQL("retrieved_at + interval '%s second' >= now() at time zone 'utc'",
                                                  ttl)).order_by(cls.retrieved_at.desc())

        return query.first()

    @classmethod
    def store_result(cls, data_source_id, query_hash, query, data, run_time, retrieved_at):
        query_result = cls.create(query_hash=query_hash,
                                  query=query,
                                  runtime=run_time,
                                  data_source=data_source_id,
                                  retrieved_at=retrieved_at,
                                  data=data)

        logging.info("Inserted query (%s) data; id=%s", query_hash, query_result.id)

        updated_count = Query.update(latest_query_data=query_result).\
            where(Query.query_hash==query_hash, Query.data_source==data_source_id).\
            execute()

        logging.info("Updated %s queries with result (%s).", updated_count, query_hash)

        return query_result

    def __unicode__(self):
        return u"%d | %s | %s" % (self.id, self.query_hash, self.retrieved_at)


class Query(BaseModel):
    id = peewee.PrimaryKeyField()
    data_source = peewee.ForeignKeyField(DataSource)
    latest_query_data = peewee.ForeignKeyField(QueryResult, null=True)
    name = peewee.CharField(max_length=255)
    description = peewee.CharField(max_length=4096, null=True)
    query = peewee.TextField()
    query_hash = peewee.CharField(max_length=32)
    api_key = peewee.CharField(max_length=40)
    ttl = peewee.IntegerField()
    user_email = peewee.CharField(max_length=360, null=True)
    user = peewee.ForeignKeyField(User)
    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'queries'

    def create_default_visualizations(self):
        table_visualization = Visualization(query=self, name="Table",
                                            description='',
                                            type="TABLE", options="{}")
        table_visualization.save()

    def to_dict(self, with_result=True, with_stats=False, with_visualizations=False, with_user=True):
        d = {
            'id': self.id,
            'latest_query_data_id': self._data.get('latest_query_data', None),
            'name': self.name,
            'description': self.description,
            'query': self.query,
            'query_hash': self.query_hash,
            'ttl': self.ttl,
            'api_key': self.api_key,
            'created_at': self.created_at,
            'data_source_id': self._data.get('data_source', None)
        }

        if with_user:
            d['user'] = self.user.to_dict()
        else:
            d['user_id'] = self._data['user']

        if with_stats:
            d['avg_runtime'] = self.avg_runtime
            d['min_runtime'] = self.min_runtime
            d['max_runtime'] = self.max_runtime
            d['last_retrieved_at'] = self.last_retrieved_at
            d['times_retrieved'] = self.times_retrieved

        if with_visualizations:
            d['visualizations'] = [vis.to_dict(with_query=False)
                                   for vis in self.visualizations]

        if with_result and self.latest_query_data:
            d['latest_query_data'] = self.latest_query_data.to_dict()

        return d

    @classmethod
    def all_queries(cls):
        q = Query.select(Query, User,
                     peewee.fn.Count(QueryResult.id).alias('times_retrieved'),
                     peewee.fn.Avg(QueryResult.runtime).alias('avg_runtime'),
                     peewee.fn.Min(QueryResult.runtime).alias('min_runtime'),
                     peewee.fn.Max(QueryResult.runtime).alias('max_runtime'),
                     peewee.fn.Max(QueryResult.retrieved_at).alias('last_retrieved_at'))\
            .join(QueryResult, join_type=peewee.JOIN_LEFT_OUTER)\
            .switch(Query).join(User)\
            .group_by(Query.id, User.id)

        return q

    @classmethod
    def outdated_queries(cls):
        # TODO: this will only find scheduled queries that were executed before. I think this is
        # a reasonable assumption, but worth revisiting.
        outdated_queries_ids = cls.select(
            peewee.Func('first_value', cls.id).over(partition_by=[cls.query_hash, cls.data_source])) \
            .join(QueryResult) \
            .where(cls.ttl > 0,
                   (QueryResult.retrieved_at +
                    (cls.ttl * peewee.SQL("interval '1 second'"))) <
                   peewee.SQL("(now() at time zone 'utc')"))

        queries = cls.select(cls, DataSource).join(DataSource) \
            .where(cls.id << outdated_queries_ids )

        return queries

    @classmethod
    def update_instance(cls, query_id, **kwargs):
        if 'query' in kwargs:
            kwargs['query_hash'] = utils.gen_query_hash(kwargs['query'])

        update = cls.update(**kwargs).where(cls.id == query_id)
        return update.execute()

    def save(self, *args, **kwargs):
        self.query_hash = utils.gen_query_hash(self.query)
        self._set_api_key()
        super(Query, self).save(*args, **kwargs)

    def _set_api_key(self):
        if not self.api_key:
            self.api_key = hashlib.sha1(
                u''.join((str(time.time()), self.query, str(self._data['user']), self.name)).encode('utf-8')).hexdigest()

    def __unicode__(self):
        return unicode(self.id)


class Dashboard(BaseModel):
    id = peewee.PrimaryKeyField()
    slug = peewee.CharField(max_length=140, index=True)
    name = peewee.CharField(max_length=100)
    user_email = peewee.CharField(max_length=360, null=True)
    user = peewee.ForeignKeyField(User)
    layout = peewee.TextField()
    dashboard_filters_enabled = peewee.BooleanField(default=False)
    is_archived = peewee.BooleanField(default=False, index=True)
    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'dashboards'

    def to_dict(self, with_widgets=False):
        layout = json.loads(self.layout)

        if with_widgets:
            widgets = Widget.select(Widget, Visualization, Query, QueryResult, User)\
                .where(Widget.dashboard == self.id)\
                .join(Visualization, join_type=peewee.JOIN_LEFT_OUTER)\
                .join(Query, join_type=peewee.JOIN_LEFT_OUTER)\
                .join(User, join_type=peewee.JOIN_LEFT_OUTER)\
                .switch(Query)\
                .join(QueryResult, join_type=peewee.JOIN_LEFT_OUTER)
            widgets = {w.id: w.to_dict() for w in widgets}

            # The following is a workaround for cases when the widget object gets deleted without the dashboard layout
            # updated. This happens for users with old databases that didn't have a foreign key relationship between
            # visualizations and widgets.
            # It's temporary until better solution is implemented (we probably should move the position information
            # to the widget).
            widgets_layout = []
            for row in layout:
                new_row = []
                for widget_id in row:
                    widget = widgets.get(widget_id, None)
                    if widget:
                        new_row.append(widget)

                widgets_layout.append(new_row)

            # widgets_layout = map(lambda row: map(lambda widget_id: widgets.get(widget_id, None), row), layout)
        else:
            widgets_layout = None

        return {
            'id': self.id,
            'slug': self.slug,
            'name': self.name,
            'user_id': self._data['user'],
            'layout': layout,
            'dashboard_filters_enabled': self.dashboard_filters_enabled,
            'widgets': widgets_layout
        }

    @classmethod
    def get_by_slug(cls, slug):
        return cls.get(cls.slug == slug)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = utils.slugify(self.name)

            tries = 1
            while self.select().where(Dashboard.slug == self.slug).first() is not None:
                self.slug = utils.slugify(self.name) + "_{0}".format(tries)
                tries += 1

        super(Dashboard, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%s=%s" % (self.id, self.name)


class Visualization(BaseModel):
    id = peewee.PrimaryKeyField()
    type = peewee.CharField(max_length=100)
    query = peewee.ForeignKeyField(Query, related_name='visualizations')
    name = peewee.CharField(max_length=255)
    description = peewee.CharField(max_length=4096, null=True)
    options = peewee.TextField()

    class Meta:
        db_table = 'visualizations'

    def to_dict(self, with_query=True):
        d = {
            'id': self.id,
            'type': self.type,
            'name': self.name,
            'description': self.description,
            'options': json.loads(self.options),
        }

        if with_query:
            d['query'] = self.query.to_dict()

        return d

    def __unicode__(self):
        return u"%s %s" % (self.id, self.type)


class Widget(BaseModel):
    id = peewee.PrimaryKeyField()
    visualization = peewee.ForeignKeyField(Visualization, related_name='widgets', null=True)
    text = peewee.TextField(null=True)
    width = peewee.IntegerField()
    options = peewee.TextField()
    dashboard = peewee.ForeignKeyField(Dashboard, related_name='widgets', index=True)
    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    # unused; kept for backward compatability:
    type = peewee.CharField(max_length=100, null=True)
    query_id = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'widgets'

    def to_dict(self):
        d = {
            'id': self.id,
            'width': self.width,
            'options': json.loads(self.options),
            'dashboard_id': self._data['dashboard'],
            'text': self.text
        }

        if self.visualization and self.visualization.id:
            d['visualization'] = self.visualization.to_dict()

        return d

    def __unicode__(self):
        return u"%s" % self.id

all_models = (DataSource, User, QueryResult, Query, Dashboard, Visualization, Widget, ActivityLog, Group)


def init_db():
    Group.insert(name='admin', permissions=['admin'], tables=['*']).execute()
    Group.insert(name='default', permissions=Group.DEFAULT_PERMISSIONS, tables=['*']).execute()


def create_db(create_tables, drop_tables):
    db.connect_db()

    for model in all_models:
        if drop_tables and model.table_exists():
            # TODO: submit PR to peewee to allow passing cascade option to drop_table.
            db.database.execute_sql('DROP TABLE %s CASCADE' % model._meta.db_table)
            #model.drop_table()

        if create_tables and not model.table_exists():
            model.create_table()

    db.close_db(None)
########NEW FILE########
__FILENAME__ = permissions
import functools
from flask.ext.login import current_user
from flask.ext.restful import abort


class require_permissions(object):
    def __init__(self, permissions):
        self.permissions = permissions

    def __call__(self, fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            has_permissions = reduce(lambda a, b: a and b,
                                      map(lambda permission: permission in current_user.permissions,
                                          self.permissions),
                                      True)

            if has_permissions:
                return fn(*args, **kwargs)
            else:
                abort(403)

        return decorated


def require_permission(permission):
    return require_permissions((permission,))
########NEW FILE########
__FILENAME__ = settings
import json
import os
import urlparse


def parse_db_url(url):
    url_parts = urlparse.urlparse(url)
    connection = {'threadlocals': True}

    if url_parts.hostname and not url_parts.path:
        connection['name'] = url_parts.hostname
    else:
        connection['name'] = url_parts.path[1:]
        connection['host'] = url_parts.hostname
        connection['port'] = url_parts.port
        connection['user'] = url_parts.username
        connection['password'] = url_parts.password

    return connection


def fix_assets_path(path):
    fullpath = os.path.join(os.path.dirname(__file__), path)
    return fullpath


def array_from_string(str):
    array = str.split(',')
    if "" in array:
        array.remove("")

    return array


def parse_boolean(str):
    return json.loads(str.lower())


NAME = os.environ.get('REDASH_NAME', 're:dash')

REDIS_URL = os.environ.get('REDASH_REDIS_URL', "redis://localhost:6379/0")

STATSD_HOST = os.environ.get('REDASH_STATSD_HOST', "127.0.0.1")
STATSD_PORT = int(os.environ.get('REDASH_STATSD_PORT', "8125"))
STATSD_PREFIX = os.environ.get('REDASH_STATSD_PREFIX', "redash")

# The following is kept for backward compatability, and shouldn't be used any more.
CONNECTION_ADAPTER = os.environ.get("REDASH_CONNECTION_ADAPTER", "pg")
CONNECTION_STRING = os.environ.get("REDASH_CONNECTION_STRING", "user= password= host= port=5439 dbname=")

# Connection settings for re:dash's own database (where we store the queries, results, etc)
DATABASE_CONFIG = parse_db_url(os.environ.get("REDASH_DATABASE_URL", "postgresql://postgres"))

# Celery related settings
CELERY_BROKER = os.environ.get("REDASH_CELERY_BROKER", REDIS_URL)
CELERY_BACKEND = os.environ.get("REDASH_CELERY_BACKEND", REDIS_URL)

# Google Apps domain to allow access from; any user with email in this Google Apps will be allowed
# access
GOOGLE_APPS_DOMAIN = os.environ.get("REDASH_GOOGLE_APPS_DOMAIN", "")
GOOGLE_OPENID_ENABLED = parse_boolean(os.environ.get("REDASH_GOOGLE_OPENID_ENABLED", "true"))
PASSWORD_LOGIN_ENABLED = parse_boolean(os.environ.get("REDASH_PASSWORD_LOGIN_ENABLED", "false"))
ALLOWED_EXTERNAL_USERS = array_from_string(os.environ.get("REDASH_ALLOWED_EXTERNAL_USERS", ''))
STATIC_ASSETS_PATH = fix_assets_path(os.environ.get("REDASH_STATIC_ASSETS_PATH", "../rd_ui/app/"))
WORKERS_COUNT = int(os.environ.get("REDASH_WORKERS_COUNT", "2"))
JOB_EXPIRY_TIME = int(os.environ.get("REDASH_JOB_EXPIRY_TIME", 3600*24))
COOKIE_SECRET = os.environ.get("REDASH_COOKIE_SECRET", "c292a0a3aa32397cdb050e233733900f")
LOG_LEVEL = os.environ.get("REDASH_LOG_LEVEL", "INFO")
EVENTS_LOG_PATH = os.environ.get("REDASH_EVENTS_LOG_PATH", "")
EVENTS_CONSOLE_OUTPUT = parse_boolean(os.environ.get("REDASH_EVENTS_CONSOLE_OUTPUT", "false"))
CLIENT_SIDE_METRICS = parse_boolean(os.environ.get("REDASH_CLIENT_SIDE_METRICS", "false"))
ANALYTICS = os.environ.get("REDASH_ANALYTICS", "")

# Features:
FEATURE_TABLES_PERMISSIONS = parse_boolean(os.environ.get("REDASH_FEATURE_TABLES_PERMISSIONS", "false"))
########NEW FILE########
__FILENAME__ = tasks
import time
import datetime
import logging
import redis
from celery import Task
from celery.result import AsyncResult
from celery.utils.log import get_task_logger
from redash import redis_connection, models, statsd_client
from redash.utils import gen_query_hash
from redash.worker import celery
from redash.data.query_runner import get_query_runner

logger = get_task_logger(__name__)


class BaseTask(Task):
    abstract = True

    def after_return(self, *args, **kwargs):
        models.db.close_db(None)

    def __call__(self, *args, **kwargs):
        models.db.connect_db()
        return super(BaseTask, self).__call__(*args, **kwargs)


class QueryTask(object):
    MAX_RETRIES = 5

    # TODO: this is mapping to the old Job class statuses. Need to update the client side and remove this
    STATUSES = {
        'PENDING': 1,
        'STARTED': 2,
        'SUCCESS': 3,
        'FAILURE': 4,
        'REVOKED': 4
    }

    def __init__(self, job_id=None, async_result=None):
        if async_result:
            self._async_result = async_result
        else:
            self._async_result = AsyncResult(job_id, app=celery)

    @property
    def id(self):
        return self._async_result.id

    @classmethod
    def add_task(cls, query, data_source, scheduled=False):
        query_hash = gen_query_hash(query)
        logging.info("[Manager][%s] Inserting job", query_hash)
        try_count = 0
        job = None

        while try_count < cls.MAX_RETRIES:
            try_count += 1

            pipe = redis_connection.pipeline()
            try:
                pipe.watch(cls._job_lock_id(query_hash, data_source.id))
                job_id = pipe.get(cls._job_lock_id(query_hash, data_source.id))
                if job_id:
                    logging.info("[Manager][%s] Found existing job: %s", query_hash, job_id)

                    job = cls(job_id=job_id)
                else:
                    pipe.multi()

                    if scheduled:
                        queue_name = data_source.queue_name
                    else:
                        queue_name = data_source.scheduled_queue_name

                    result = execute_query.apply_async(args=(query, data_source.id), queue=queue_name)
                    job = cls(async_result=result)
                    logging.info("[Manager][%s] Created new job: %s", query_hash, job.id)
                    pipe.set(cls._job_lock_id(query_hash, data_source.id), job.id)
                    pipe.execute()
                break

            except redis.WatchError:
                continue

        if not job:
            logging.error("[Manager][%s] Failed adding job for query.", query_hash)

        return job

    def to_dict(self):
        if self._async_result.status == 'STARTED':
            updated_at = self._async_result.result.get('start_time', 0)
        else:
            updated_at = 0

        if self._async_result.failed() and isinstance(self._async_result.result, Exception):
            error = self._async_result.result.message
        elif self._async_result.status == 'REVOKED':
            error = 'Query execution cancelled.'
        else:
            error = ''

        if self._async_result.successful():
            query_result_id = self._async_result.result
        else:
            query_result_id = None

        return {
            'id': self._async_result.id,
            'updated_at': updated_at,
            'status': self.STATUSES[self._async_result.status],
            'error': error,
            'query_result_id': query_result_id,
        }

    def cancel(self):
        return self._async_result.revoke(terminate=True)

    @staticmethod
    def _job_lock_id(query_hash, data_source_id):
        return "query_hash_job:%s:%s" % (data_source_id, query_hash)

@celery.task(base=BaseTask)
def refresh_queries():
    # self.status['last_refresh_at'] = time.time()
    # self._save_status()

    logger.info("Refreshing queries...")

    outdated_queries_count = 0
    for query in models.Query.outdated_queries():
        # TODO: this should go into lower priority
        QueryTask.add_task(query.query, query.data_source, scheduled=True)
        outdated_queries_count += 1

    statsd_client.gauge('manager.outdated_queries', outdated_queries_count)
    # TODO: decide if we still need this
    # statsd_client.gauge('manager.queue_size', self.redis_connection.zcard('jobs'))

    logger.info("Done refreshing queries. Found %d outdated queries." % outdated_queries_count)

    status = redis_connection.hgetall('redash:status')
    now = time.time()

    redis_connection.hmset('redash:status', {
        'outdated_queries_count': outdated_queries_count,
        'last_refresh_at': now
    })

    statsd_client.gauge('manager.seconds_since_refresh', now - float(status.get('last_refresh_at', now)))

@celery.task(bind=True, base=BaseTask, track_started=True)
def execute_query(self, query, data_source_id):
    # TODO: maybe this should be a class?
    start_time = time.time()

    logger.info("Loading data source (%d)...", data_source_id)

    # TODO: we should probably cache data sources in Redis
    data_source = models.DataSource.get_by_id(data_source_id)

    self.update_state(state='STARTED', meta={'start_time': start_time, 'custom_message': ''})

    logger.info("Executing query:\n%s", query)

    query_hash = gen_query_hash(query)
    query_runner = get_query_runner(data_source.type, data_source.options)

    if getattr(query_runner, 'annotate_query', True):
        # TODO: anotate with queu ename
        annotated_query = "/* Task Id: %s, Query hash: %s */ %s" % \
                          (self.request.id, query_hash, query)
    else:
        annotated_query = query

    with statsd_client.timer('query_runner.{}.{}.run_time'.format(data_source.type, data_source.name)):
        data, error = query_runner(annotated_query)

    run_time = time.time() - start_time
    logger.info("Query finished... data length=%s, error=%s", data and len(data), error)

    self.update_state(state='STARTED', meta={'start_time': start_time, 'error': error, 'custom_message': ''})

    # Delete query_hash
    redis_connection.delete(QueryTask._job_lock_id(query_hash, data_source.id))

    # TODO: it is possible that storing the data will fail, and we will need to retry
    # while we already marked the job as done
    if not error:
        query_result = models.QueryResult.store_result(data_source.id, query_hash, query, data, run_time, datetime.datetime.utcnow())
    else:
        raise Exception(error)

    return query_result.id


########NEW FILE########
__FILENAME__ = utils
import cStringIO
import csv
import codecs
import decimal
import datetime
import json
import re
import hashlib
import sqlparse

COMMENTS_REGEX = re.compile("/\*.*?\*/")


class SQLMetaData(object):
    TABLE_SELECTION_KEYWORDS = ('FROM', 'JOIN', 'LEFT JOIN', 'FULL JOIN', 'RIGHT JOIN', 'CROSS JOIN', 'INNER JOIN',
                                'OUTER JOIN', 'LEFT OUTER JOIN', 'RIGHT OUTER JOIN', 'FULL OUTER JOIN')

    def __init__(self, sql):
        self.sql = sql
        self.parsed_sql = sqlparse.parse(self.sql)

        self.has_ddl_statements = self._find_ddl_statements()
        self.has_non_select_dml_statements = self._find_dml_statements()
        self.used_tables = self._find_tables()

    def _find_ddl_statements(self):
        for statement in self.parsed_sql:
            if len([x for x in statement.flatten() if x.ttype == sqlparse.tokens.DDL]):
                return True

        return False

    def _find_tables(self):
        tables = set()
        for statement in self.parsed_sql:
            tables.update(self.extract_table_names(statement.tokens))

        return tables

    def extract_table_names(self, tokens):
        tables = set()
        tokens = [t for t in tokens if t.ttype not in (sqlparse.tokens.Whitespace, sqlparse.tokens.Newline)]

        for i in range(len(tokens)):
            if tokens[i].is_group():
                tables.update(self.extract_table_names(tokens[i].tokens))
            else:
                if tokens[i].ttype == sqlparse.tokens.Keyword and tokens[i].normalized in self.TABLE_SELECTION_KEYWORDS:
                    if isinstance(tokens[i + 1], sqlparse.sql.Identifier):
                        tables.add(tokens[i + 1].value)

                    if isinstance(tokens[i + 1], sqlparse.sql.IdentifierList):
                        tables.update(set([t.value for t in tokens[i+1].get_identifiers()]))
        return tables

    def _find_dml_statements(self):
        for statement in self.parsed_sql:
            for token in statement.flatten():
                if token.ttype == sqlparse.tokens.DML and token.normalized != 'SELECT':
                    return True

        return False


def slugify(s):
    return re.sub('[^a-z0-9_\-]+', '-', s.lower())


def gen_query_hash(sql):
    """Returns hash of the given query after stripping all comments, line breaks and multiple
    spaces, and lower casing all text.

    TODO: possible issue - the following queries will get the same id:
        1. SELECT 1 FROM table WHERE column='Value';
        2. SELECT 1 FROM table where column='value';
    """
    sql = COMMENTS_REGEX.sub("", sql)
    sql = "".join(sql.split()).lower()
    return hashlib.md5(sql.encode('utf-8')).hexdigest()


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoding class, to handle Decimal and datetime.date instances.
    """
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)

        if isinstance(o, datetime.date):
            return o.isoformat()

        super(JSONEncoder, self).default(o)


def json_dumps(data):
    return json.dumps(data, cls=JSONEncoder)


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

    def _encode_utf8(self, val):
        if isinstance(val, (unicode, str)):
            return val.encode('utf-8')

        return val

    def writerow(self, row):
        self.writer.writerow([self._encode_utf8(s) for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
########NEW FILE########
__FILENAME__ = worker
from celery import Celery
from datetime import timedelta
from redash import settings


celery = Celery('redash',
                broker=settings.CELERY_BROKER,
                include='redash.tasks')

celery.conf.update(CELERY_RESULT_BACKEND=settings.CELERY_BACKEND,
                   CELERYBEAT_SCHEDULE={
                       'refresh_queries': {
                           'task': 'redash.tasks.refresh_queries',
                           'schedule': timedelta(seconds=30)
                       },
                   },
                   CELERY_TIMEZONE='UTC')


if __name__ == '__main__':
    celery.start()
########NEW FILE########
__FILENAME__ = wsgi
import json
from flask import Flask, make_response
from flask.ext.restful import Api

from redash import settings, utils
from redash.models import db

__version__ = '0.4.0'

app = Flask(__name__,
            template_folder=settings.STATIC_ASSETS_PATH,
            static_folder=settings.STATIC_ASSETS_PATH,
            static_path='/static')


api = Api(app)

# configure our database
settings.DATABASE_CONFIG.update({'threadlocals': True})
app.config['DATABASE'] = settings.DATABASE_CONFIG
db.init_app(app)

from redash.authentication import setup_authentication
auth = setup_authentication(app)

@api.representation('application/json')
def json_representation(data, code, headers=None):
    resp = make_response(json.dumps(data, cls=utils.JSONEncoder), code)
    resp.headers.extend(headers or {})
    return resp

from redash import controllers

########NEW FILE########
__FILENAME__ = factories
import datetime
import redash.models
from redash.utils import gen_query_hash


class ModelFactory(object):
    def __init__(self, model, **kwargs):
        self.model = model
        self.kwargs = kwargs

    def _get_kwargs(self, override_kwargs):
        kwargs = self.kwargs.copy()
        kwargs.update(override_kwargs)

        for key, arg in kwargs.items():
            if callable(arg):
                kwargs[key] = arg()

        return kwargs

    def instance(self, **override_kwargs):
        kwargs = self._get_kwargs(override_kwargs)

        return self.model(**kwargs)

    def create(self, **override_kwargs):
        kwargs = self._get_kwargs(override_kwargs)
        return self.model.create(**kwargs)


class Sequence(object):
    def __init__(self, string):
        self.sequence = 0
        self.string = string

    def __call__(self):
        self.sequence += 1

        return self.string.format(self.sequence)


user_factory = ModelFactory(redash.models.User,
                            name='John Doe', email=Sequence('test{}@example.com'),
                            groups=['default'])


data_source_factory = ModelFactory(redash.models.DataSource,
                                   name='Test',
                                   type='pg',
                                   options='')


dashboard_factory = ModelFactory(redash.models.Dashboard,
                                 name='test', user=user_factory.create, layout='[]')


query_factory = ModelFactory(redash.models.Query,
                             name='New Query',
                             description='',
                             query='SELECT 1',
                             ttl=-1,
                             user=user_factory.create,
                             data_source=data_source_factory.create)

query_result_factory = ModelFactory(redash.models.QueryResult,
                                    data='{"columns":{}, "rows":[]}',
                                    runtime=1,
                                    retrieved_at=datetime.datetime.utcnow,
                                    query="SELECT 1",
                                    query_hash=gen_query_hash('SELECT 1'),
                                    data_source=data_source_factory.create)

visualization_factory = ModelFactory(redash.models.Visualization,
                                     type='CHART',
                                     query=query_factory.create,
                                     name='Chart',
                                     description='',
                                     options='{}')

widget_factory = ModelFactory(redash.models.Widget,
                              type='chart',
                              width=1,
                              options='{}',
                              dashboard=dashboard_factory.create,
                              visualization=visualization_factory.create)
########NEW FILE########
__FILENAME__ = test_authentication
from unittest import TestCase
from mock import patch
from flask_googleauth import ObjectDict
from tests import BaseTestCase
from redash.authentication import validate_email, create_and_login_user
from redash import settings, models
from tests.factories import user_factory


class TestEmailValidation(TestCase):
    def test_accepts_address_with_correct_domain(self):
        with patch.object(settings, 'GOOGLE_APPS_DOMAIN', 'example.com'):
            self.assertTrue(validate_email('example@example.com'))

    def test_accepts_address_from_exception_list(self):
        with patch.multiple(settings, GOOGLE_APPS_DOMAIN='example.com', ALLOWED_EXTERNAL_USERS=['whatever@whatever.com']):
            self.assertTrue(validate_email('whatever@whatever.com'))

    def test_accept_any_address_when_domain_empty(self):
        with patch.object(settings, 'GOOGLE_APPS_DOMAIN', None):
            self.assertTrue(validate_email('whatever@whatever.com'))

    def test_rejects_address_with_incorrect_domain(self):
        with patch.object(settings, 'GOOGLE_APPS_DOMAIN', 'example.com'):
            self.assertFalse(validate_email('whatever@whatever.com'))


class TestCreateAndLoginUser(BaseTestCase):
    def test_logins_valid_user(self):
        user = user_factory.create(email='test@example.com')

        with patch.object(settings, 'GOOGLE_APPS_DOMAIN', 'example.com'), patch('redash.authentication.login_user') as login_user_mock:
            create_and_login_user(None, user)
            login_user_mock.assert_called_once_with(user, remember=True)

    def test_creates_vaild_new_user(self):
        openid_user = ObjectDict({'email': 'test@example.com', 'name': 'Test User'})

        with patch.multiple(settings, GOOGLE_APPS_DOMAIN='example.com'), \
             patch('redash.authentication.login_user') as login_user_mock:

            create_and_login_user(None, openid_user)

            self.assertTrue(login_user_mock.called)
            user = models.User.get(models.User.email == openid_user.email)

    def test_ignores_invliad_user(self):
        user = ObjectDict({'email': 'test@whatever.com'})

        with patch.object(settings, 'GOOGLE_APPS_DOMAIN', 'example.com'), patch('redash.authentication.login_user') as login_user_mock:
            create_and_login_user(None, user)
            self.assertFalse(login_user_mock.called)
########NEW FILE########
__FILENAME__ = test_controllers
from contextlib import contextmanager
import json
import time
from unittest import TestCase
from flask import url_for
from flask.ext.login import current_user
from mock import patch
from tests import BaseTestCase
from tests.factories import dashboard_factory, widget_factory, visualization_factory, query_factory, \
    query_result_factory, user_factory, data_source_factory
from redash import models, settings
from redash.wsgi import app
from redash.utils import json_dumps
from redash.authentication import sign


settings.GOOGLE_APPS_DOMAIN = "example.com"

@contextmanager
def authenticated_user(c, user=None):
    if not user:
        user = user_factory.create()

    with c.session_transaction() as sess:
        sess['user_id'] = user.id

    yield


def json_request(method, path, data=None):
    if data:
        response = method(path, data=json_dumps(data))
    else:
        response = method(path)

    if response.data:
        response.json = json.loads(response.data)
    else:
        response.json = None

    return response


class AuthenticationTestMixin():
    def test_redirects_when_not_authenticated(self):
        with app.test_client() as c:
            for path in self.paths:
                rv = c.get(path)
                self.assertEquals(302, rv.status_code)

    def test_returns_content_when_authenticated(self):
        with app.test_client() as c, authenticated_user(c):
            for path in self.paths:
                rv = c.get(path)
                self.assertEquals(200, rv.status_code)


class TestAuthentication(BaseTestCase):
    def test_redirects_for_nonsigned_in_user(self):
        with app.test_client() as c:
            rv = c.get("/")
            self.assertEquals(302, rv.status_code)


class PingTest(TestCase):
    def test_ping(self):
        with app.test_client() as c:
            rv = c.get('/ping')
            self.assertEquals(200, rv.status_code)
            self.assertEquals('PONG.', rv.data)


class IndexTest(BaseTestCase, AuthenticationTestMixin):
    def setUp(self):
        self.paths = ['/', '/dashboard/example', '/queries/1', '/admin/status']
        super(IndexTest, self).setUp()


class StatusTest(BaseTestCase):
    def test_returns_data_for_admin(self):
        admin = user_factory.create(groups=['admin', 'default'])
        with app.test_client() as c, authenticated_user(c, user=admin):
            rv = c.get('/status.json')
            self.assertEqual(rv.status_code, 200)

    def test_returns_403_for_non_admin(self):
        with app.test_client() as c, authenticated_user(c):
            rv = c.get('/status.json')
            self.assertEqual(rv.status_code, 403)

    def test_redirects_non_authenticated_user(self):
        with app.test_client() as c:
            rv = c.get('/status.json')
            self.assertEqual(rv.status_code, 302)


class DashboardAPITest(BaseTestCase, AuthenticationTestMixin):
    def setUp(self):
        self.paths = ['/api/dashboards']
        super(DashboardAPITest, self).setUp()

    def test_get_dashboard(self):
        d1 = dashboard_factory.create()
        with app.test_client() as c, authenticated_user(c):
            rv = c.get('/api/dashboards/{0}'.format(d1.slug))
            self.assertEquals(rv.status_code, 200)
            self.assertDictEqual(json.loads(rv.data), d1.to_dict(with_widgets=True))

    def test_get_non_existint_dashbaord(self):
        with app.test_client() as c, authenticated_user(c):
            rv = c.get('/api/dashboards/not_existing')
            self.assertEquals(rv.status_code, 404)

    def test_create_new_dashboard(self):
        user = user_factory.create()
        with app.test_client() as c, authenticated_user(c, user=user):
            dashboard_name = 'Test Dashboard'
            rv = json_request(c.post, '/api/dashboards', data={'name': dashboard_name})
            self.assertEquals(rv.status_code, 200)
            self.assertEquals(rv.json['name'], 'Test Dashboard')
            self.assertEquals(rv.json['user_id'], user.id)
            self.assertEquals(rv.json['layout'], [])

    def test_update_dashboard(self):
        d = dashboard_factory.create()
        new_name = 'New Name'
        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.post, '/api/dashboards/{0}'.format(d.id),
                              data={'name': new_name, 'layout': '[]'})
            self.assertEquals(rv.status_code, 200)
            self.assertEquals(rv.json['name'], new_name)

    def test_delete_dashboard(self):
        d = dashboard_factory.create()
        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.delete, '/api/dashboards/{0}'.format(d.slug))
            self.assertEquals(rv.status_code, 200)

            d = models.Dashboard.get_by_slug(d.slug)
            self.assertTrue(d.is_archived)


class WidgetAPITest(BaseTestCase):
    def create_widget(self, dashboard, visualization, width=1):
        data = {
            'visualization_id': visualization.id,
            'dashboard_id': dashboard.id,
            'options': {},
            'width': width
        }

        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.post, '/api/widgets', data=data)

        return rv

    def test_create_widget(self):
        dashboard = dashboard_factory.create()
        vis = visualization_factory.create()

        rv = self.create_widget(dashboard, vis)
        self.assertEquals(rv.status_code, 200)

        dashboard = models.Dashboard.get(models.Dashboard.id == dashboard.id)
        self.assertEquals(unicode(rv.json['layout']), dashboard.layout)

        self.assertEquals(dashboard.widgets, 1)
        self.assertEquals(rv.json['layout'], [[rv.json['widget']['id']]])
        self.assertEquals(rv.json['new_row'], True)

        rv2 = self.create_widget(dashboard, vis)
        self.assertEquals(dashboard.widgets, 2)
        self.assertEquals(rv2.json['layout'],
                          [[rv.json['widget']['id'], rv2.json['widget']['id']]])
        self.assertEquals(rv2.json['new_row'], False)

        rv3 = self.create_widget(dashboard, vis)
        self.assertEquals(rv3.json['new_row'], True)
        rv4 = self.create_widget(dashboard, vis, width=2)
        self.assertEquals(rv4.json['layout'],
                          [[rv.json['widget']['id'], rv2.json['widget']['id']],
                           [rv3.json['widget']['id']],
                           [rv4.json['widget']['id']]])
        self.assertEquals(rv4.json['new_row'], True)

    def test_create_text_widget(self):
        dashboard = dashboard_factory.create()

        data = {
            'visualization_id': None,
            'text': 'Sample text.',
            'dashboard_id': dashboard.id,
            'options': {},
            'width': 2
        }

        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.post, '/api/widgets', data=data)

        self.assertEquals(rv.status_code, 200)
        self.assertEquals(rv.json['widget']['text'], 'Sample text.')

    def test_delete_widget(self):
        widget = widget_factory.create()

        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.delete, '/api/widgets/{0}'.format(widget.id))

            self.assertEquals(rv.status_code, 200)
            dashboard = models.Dashboard.get_by_slug(widget.dashboard.slug)
            self.assertEquals(dashboard.widgets.count(), 0)
            self.assertEquals(dashboard.layout, '[]')

            # TODO: test how it updates the layout


class QueryAPITest(BaseTestCase, AuthenticationTestMixin):
    def setUp(self):
        self.paths = ['/api/queries']
        super(QueryAPITest, self).setUp()

    def test_update_query(self):
        query = query_factory.create()

        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.post, '/api/queries/{0}'.format(query.id), data={'name': 'Testing'})
            self.assertEqual(rv.status_code, 200)
            self.assertEquals(rv.json['name'], 'Testing')

    def test_create_query(self):
        user = user_factory.create()
        data_source = data_source_factory.create()
        query_data = {
            'name': 'Testing',
            'query': 'SELECT 1',
            'ttl': 3600,
            'data_source_id': data_source.id
        }

        with app.test_client() as c, authenticated_user(c, user=user):
            rv = json_request(c.post, '/api/queries', data=query_data)

            self.assertEquals(rv.status_code, 200)
            self.assertDictContainsSubset(query_data, rv.json)
            self.assertEquals(rv.json['user']['id'], user.id)
            self.assertIsNotNone(rv.json['api_key'])
            self.assertIsNotNone(rv.json['query_hash'])

            query = models.Query.get_by_id(rv.json['id'])
            self.assertEquals(len(list(query.visualizations)), 1)

    def test_get_query(self):
        query = query_factory.create()

        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.get, '/api/queries/{0}'.format(query.id))

            self.assertEquals(rv.status_code, 200)
            d = query.to_dict(with_visualizations=True)
            d.pop('created_at')
            self.assertDictContainsSubset(d, rv.json)

    def test_get_all_queries(self):
        queries = [query_factory.create() for _ in range(10)]

        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.get, '/api/queries')

            self.assertEquals(rv.status_code, 200)
            self.assertEquals(len(rv.json), 10)


class VisualizationAPITest(BaseTestCase):
    def test_create_visualization(self):
        query = query_factory.create()
        data = {
            'query_id': query.id,
            'name': 'Chart',
            'description':'',
            'options': {},
            'type': 'CHART'
        }

        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.post, '/api/visualizations', data=data)

            self.assertEquals(rv.status_code, 200)
            data.pop('query_id')
            self.assertDictContainsSubset(data, rv.json)

    def test_delete_visualization(self):
        visualization = visualization_factory.create()
        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.delete, '/api/visualizations/{0}'.format(visualization.id))

            self.assertEquals(rv.status_code, 200)
            self.assertEquals(models.Visualization.select().count(), 0)

    def test_update_visualization(self):
        visualization = visualization_factory.create()

        with app.test_client() as c, authenticated_user(c):
            rv = json_request(c.post, '/api/visualizations/{0}'.format(visualization.id),
                              data={'name': 'After Update'})

            self.assertEquals(rv.status_code, 200)
            self.assertEquals(rv.json['name'], 'After Update')


class QueryResultAPITest(BaseTestCase, AuthenticationTestMixin):
    def setUp(self):
        self.paths = []
        super(QueryResultAPITest, self).setUp()


class JobAPITest(BaseTestCase, AuthenticationTestMixin):
    def setUp(self):
        self.paths = []
        super(JobAPITest, self).setUp()


class CsvQueryResultAPITest(BaseTestCase, AuthenticationTestMixin):
    def setUp(self):
        super(CsvQueryResultAPITest, self).setUp()

        self.paths = []
        self.query_result = query_result_factory.create()
        self.query = query_factory.create()
        self.path = '/api/queries/{0}/results/{1}.csv'.format(self.query.id, self.query_result.id)

    # TODO: factor out the HMAC authentication tests

    def signature(self, expires):
        return sign(self.query.api_key, self.path, expires)

    def test_redirect_when_unauthenticated(self):
        with app.test_client() as c:
            rv = c.get(self.path)
            self.assertEquals(rv.status_code, 302)

    def test_redirect_for_wrong_signature(self):
        with app.test_client() as c:
            rv = c.get('/api/queries/{0}/results/{1}.csv'.format(self.query.id, self.query_result.id), query_string={'signature': 'whatever', 'expires': 0})
            self.assertEquals(rv.status_code, 302)

    def test_redirect_for_correct_signature_and_wrong_expires(self):
        with app.test_client() as c:
            rv = c.get('/api/queries/{0}/results/{1}.csv'.format(self.query.id, self.query_result.id), query_string={'signature': self.signature(0), 'expires': 0})
            self.assertEquals(rv.status_code, 302)

    def test_redirect_for_correct_signature_and_no_expires(self):
        with app.test_client() as c:
            rv = c.get('/api/queries/{0}/results/{1}.csv'.format(self.query.id, self.query_result.id), query_string={'signature': self.signature(time.time()+3600)})
            self.assertEquals(rv.status_code, 302)

    def test_redirect_for_correct_signature_and_expires_too_long(self):
        with app.test_client() as c:
            expires = time.time()+(10*3600)
            rv = c.get('/api/queries/{0}/results/{1}.csv'.format(self.query.id, self.query_result.id), query_string={'signature': self.signature(expires), 'expires': expires})
            self.assertEquals(rv.status_code, 302)

    def test_returns_200_for_correct_signature(self):
        with app.test_client() as c:
            expires = time.time()+1800
            rv = c.get('/api/queries/{0}/results/{1}.csv'.format(self.query.id, self.query_result.id), query_string={'signature': self.signature(expires), 'expires': expires})
            self.assertEquals(rv.status_code, 200)

    def test_returns_200_for_authenticated_user(self):
        with app.test_client() as c, authenticated_user(c):
            rv = c.get('/api/queries/{0}/results/{1}.csv'.format(self.query.id, self.query_result.id))
            self.assertEquals(rv.status_code, 200)


class TestLogin(BaseTestCase):
    def setUp(self):
        settings.PASSWORD_LOGIN_ENABLED = True
        super(TestLogin, self).setUp()

    def test_redirects_to_google_login_if_password_disabled(self):
        with app.test_client() as c, patch.object(settings, 'PASSWORD_LOGIN_ENABLED', False):
            rv = c.get('/login')
            self.assertEquals(rv.status_code, 302)
            self.assertTrue(rv.location.endswith(url_for('GoogleAuth.login')))

    def test_get_login_form(self):
        with app.test_client() as c:
            rv = c.get('/login')
            self.assertEquals(rv.status_code, 200)

    def test_submit_non_existing_user(self):
        with app.test_client() as c, patch('redash.controllers.login_user') as login_user_mock:
            rv = c.post('/login', data={'username': 'arik', 'password': 'password'})
            self.assertEquals(rv.status_code, 200)
            self.assertFalse(login_user_mock.called)

    def test_submit_correct_user_and_password(self):

        user = user_factory.create()
        user.hash_password('password')
        user.save()

        with app.test_client() as c, patch('redash.controllers.login_user') as login_user_mock:
            rv = c.post('/login', data={'username': user.email, 'password': 'password'})
            self.assertEquals(rv.status_code, 302)
            login_user_mock.assert_called_with(user, remember=False)

    def test_submit_correct_user_and_password_and_remember_me(self):
        user = user_factory.create()
        user.hash_password('password')
        user.save()

        with app.test_client() as c, patch('redash.controllers.login_user') as login_user_mock:
            rv = c.post('/login', data={'username': user.email, 'password': 'password', 'remember': True})
            self.assertEquals(rv.status_code, 302)
            login_user_mock.assert_called_with(user, remember=True)

    def test_submit_correct_user_and_password_with_next(self):
        user = user_factory.create()
        user.hash_password('password')
        user.save()

        with app.test_client() as c, patch('redash.controllers.login_user') as login_user_mock:
            rv = c.post('/login?next=/test',
                        data={'username': user.email, 'password': 'password'})
            self.assertEquals(rv.status_code, 302)
            self.assertEquals(rv.location, 'http://localhost/test')
            login_user_mock.assert_called_with(user, remember=False)

    def test_submit_incorrect_user(self):
        with app.test_client() as c, patch('redash.controllers.login_user') as login_user_mock:
            rv = c.post('/login', data={'username': 'non-existing', 'password': 'password'})
            self.assertEquals(rv.status_code, 200)
            self.assertFalse(login_user_mock.called)

    def test_submit_incorrect_password(self):
        user = user_factory.create()
        user.hash_password('password')
        user.save()

        with app.test_client() as c, patch('redash.controllers.login_user') as login_user_mock:
            rv = c.post('/login', data={'username': user.email, 'password': 'badbadpassword'})
            self.assertEquals(rv.status_code, 200)
            self.assertFalse(login_user_mock.called)

    def test_submit_incorrect_password(self):
        user = user_factory.create()

        with app.test_client() as c, patch('redash.controllers.login_user') as login_user_mock:
            rv = c.post('/login', data={'username': user.email, 'password': ''})
            self.assertEquals(rv.status_code, 200)
            self.assertFalse(login_user_mock.called)

    def test_user_already_loggedin(self):
        with app.test_client() as c, authenticated_user(c), patch('redash.controllers.login_user') as login_user_mock:
            rv = c.get('/login')
            self.assertEquals(rv.status_code, 302)
            self.assertFalse(login_user_mock.called)

    # TODO: brute force protection?


class TestLogout(BaseTestCase):
    def test_logout_when_not_loggedin(self):
        with app.test_client() as c:
            rv = c.get('/logout')
            self.assertEquals(rv.status_code, 302)
            self.assertFalse(current_user.is_authenticated())

    def test_logout_when_loggedin(self):
        with app.test_client() as c, authenticated_user(c):
            rv = c.get('/')
            self.assertTrue(current_user.is_authenticated())
            rv = c.get('/logout')
            self.assertEquals(rv.status_code, 302)
            self.assertFalse(current_user.is_authenticated())
########NEW FILE########
__FILENAME__ = test_import
import json
import os.path
from tests import BaseTestCase
from redash import models
from redash import import_export
from factories import user_factory, dashboard_factory, data_source_factory


class ImportTest(BaseTestCase):
    def setUp(self):
        super(ImportTest, self).setUp()

        with open(os.path.join(os.path.dirname(__file__), 'flights.json')) as f:
            self.dashboard = json.loads(f.read())
            self.user = user_factory.create()

    def test_imports_dashboard_correctly(self):
        importer = import_export.Importer(data_source=data_source_factory.create())
        dashboard = importer.import_dashboard(self.user, self.dashboard)

        self.assertIsNotNone(dashboard)
        self.assertEqual(dashboard.name, self.dashboard['name'])
        self.assertEqual(dashboard.slug, self.dashboard['slug'])
        self.assertEqual(dashboard.user, self.user)

        self.assertEqual(dashboard.widgets.count(),
                         reduce(lambda s, row: s + len(row), self.dashboard['widgets'], 0))

        self.assertEqual(models.Visualization.select().count(), dashboard.widgets.count())
        self.assertEqual(models.Query.select().count(), dashboard.widgets.count()-1)
        self.assertEqual(models.QueryResult.select().count(), dashboard.widgets.count()-1)

    def test_imports_updates_existing_models(self):
        importer = import_export.Importer(data_source=data_source_factory.create())
        importer.import_dashboard(self.user, self.dashboard)

        self.dashboard['name'] = 'Testing #2'
        dashboard = importer.import_dashboard(self.user, self.dashboard)
        self.assertEqual(dashboard.name, self.dashboard['name'])
        self.assertEquals(models.Dashboard.select().count(), 1)

    def test_using_existing_mapping(self):
        dashboard = dashboard_factory.create()
        mapping = {
            'Dashboard': {
                "1": dashboard.id
            }
        }

        importer = import_export.Importer(object_mapping=mapping, data_source=data_source_factory.create())
        imported_dashboard = importer.import_dashboard(self.user, self.dashboard)

        self.assertEqual(imported_dashboard, dashboard)
########NEW FILE########
__FILENAME__ = test_models
import datetime
from tests import BaseTestCase
from redash import models
from factories import dashboard_factory, query_factory, data_source_factory, query_result_factory
from redash.utils import gen_query_hash


class DashboardTest(BaseTestCase):
    def test_appends_suffix_to_slug_when_duplicate(self):
        d1 = dashboard_factory.create()
        self.assertEquals(d1.slug, 'test')

        d2 = dashboard_factory.create(user=d1.user)
        self.assertNotEquals(d1.slug, d2.slug)

        d3 = dashboard_factory.create(user=d1.user)
        self.assertNotEquals(d1.slug, d3.slug)
        self.assertNotEquals(d2.slug, d3.slug)


class QueryTest(BaseTestCase):
    def test_changing_query_text_changes_hash(self):
        q = query_factory.create()

        old_hash = q.query_hash
        models.Query.update_instance(q.id, query="SELECT 2;")

        q = models.Query.get_by_id(q.id)

        self.assertNotEquals(old_hash, q.query_hash)


class QueryResultTest(BaseTestCase):
    def setUp(self):
        super(QueryResultTest, self).setUp()

    def test_get_latest_returns_none_if_not_found(self):
        ds = data_source_factory.create()
        found_query_result = models.QueryResult.get_latest(ds, "SELECT 1", 60)
        self.assertIsNone(found_query_result)

    def test_get_latest_returns_when_found(self):
        qr = query_result_factory.create()
        found_query_result = models.QueryResult.get_latest(qr.data_source, qr.query, 60)

        self.assertEqual(qr, found_query_result)

    def test_get_latest_works_with_data_source_id(self):
        qr = query_result_factory.create()
        found_query_result = models.QueryResult.get_latest(qr.data_source.id, qr.query, 60)

        self.assertEqual(qr, found_query_result)

    def test_get_latest_doesnt_return_query_from_different_data_source(self):
        qr = query_result_factory.create()
        data_source = data_source_factory.create()
        found_query_result = models.QueryResult.get_latest(data_source, qr.query, 60)

        self.assertIsNone(found_query_result)

    def test_get_latest_doesnt_return_if_ttl_expired(self):
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        qr = query_result_factory.create(retrieved_at=yesterday)

        found_query_result = models.QueryResult.get_latest(qr.data_source, qr.query, ttl=60)

        self.assertIsNone(found_query_result)

    def test_get_latest_returns_if_ttl_not_expired(self):
        yesterday = datetime.datetime.now() - datetime.timedelta(seconds=30)
        qr = query_result_factory.create(retrieved_at=yesterday)

        found_query_result = models.QueryResult.get_latest(qr.data_source, qr.query, ttl=120)

        self.assertEqual(found_query_result, qr)

    def test_get_latest_returns_the_most_recent_result(self):
        yesterday = datetime.datetime.now() - datetime.timedelta(seconds=30)
        old_qr = query_result_factory.create(retrieved_at=yesterday)
        qr = query_result_factory.create()

        found_query_result = models.QueryResult.get_latest(qr.data_source, qr.query, 60)

        self.assertEqual(found_query_result.id, qr.id)

    def test_get_latest_returns_the_last_cached_result_for_negative_ttl(self):
        yesterday = datetime.datetime.now() + datetime.timedelta(days=-100)
        very_old = query_result_factory.create(retrieved_at=yesterday)

        yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
        qr = query_result_factory.create(retrieved_at=yesterday)
        found_query_result = models.QueryResult.get_latest(qr.data_source, qr.query, -1)

        self.assertEqual(found_query_result.id, qr.id)

class TestQueryResultStoreResult(BaseTestCase):
    def setUp(self):
        super(TestQueryResultStoreResult, self).setUp()
        self.data_source = data_source_factory.create()
        self.query = "SELECT 1"
        self.query_hash = gen_query_hash(self.query)
        self.runtime = 123
        self.utcnow = datetime.datetime.utcnow()
        self.data = "data"

    def test_stores_the_result(self):
        query_result = models.QueryResult.store_result(self.data_source.id, self.query_hash, self.query,
                                                          self.data, self.runtime, self.utcnow)

        self.assertEqual(query_result.data, self.data)
        self.assertEqual(query_result.runtime, self.runtime)
        self.assertEqual(query_result.retrieved_at, self.utcnow)
        self.assertEqual(query_result.query, self.query)
        self.assertEqual(query_result.query_hash, self.query_hash)
        self.assertEqual(query_result.data_source, self.data_source)

    def test_updates_existing_queries(self):
        query1 = query_factory.create(query=self.query, data_source=self.data_source)
        query2 = query_factory.create(query=self.query, data_source=self.data_source)
        query3 = query_factory.create(query=self.query, data_source=self.data_source)

        query_result = models.QueryResult.store_result(self.data_source.id, self.query_hash, self.query, self.data,
                                                       self.runtime, self.utcnow)

        self.assertEqual(models.Query.get_by_id(query1.id)._data['latest_query_data'], query_result.id)
        self.assertEqual(models.Query.get_by_id(query2.id)._data['latest_query_data'], query_result.id)
        self.assertEqual(models.Query.get_by_id(query3.id)._data['latest_query_data'], query_result.id)

    def test_doesnt_update_queries_with_different_hash(self):
        query1 = query_factory.create(query=self.query, data_source=self.data_source)
        query2 = query_factory.create(query=self.query, data_source=self.data_source)
        query3 = query_factory.create(query=self.query + "123", data_source=self.data_source)

        query_result = models.QueryResult.store_result(self.data_source.id, self.query_hash, self.query, self.data,
                                                       self.runtime, self.utcnow)

        self.assertEqual(models.Query.get_by_id(query1.id)._data['latest_query_data'], query_result.id)
        self.assertEqual(models.Query.get_by_id(query2.id)._data['latest_query_data'], query_result.id)
        self.assertNotEqual(models.Query.get_by_id(query3.id)._data['latest_query_data'], query_result.id)

    def test_doesnt_update_queries_with_different_data_source(self):
        query1 = query_factory.create(query=self.query, data_source=self.data_source)
        query2 = query_factory.create(query=self.query, data_source=self.data_source)
        query3 = query_factory.create(query=self.query, data_source=data_source_factory.create())

        query_result = models.QueryResult.store_result(self.data_source.id, self.query_hash, self.query, self.data,
                                                       self.runtime, self.utcnow)

        self.assertEqual(models.Query.get_by_id(query1.id)._data['latest_query_data'], query_result.id)
        self.assertEqual(models.Query.get_by_id(query2.id)._data['latest_query_data'], query_result.id)
        self.assertNotEqual(models.Query.get_by_id(query3.id)._data['latest_query_data'], query_result.id)
########NEW FILE########
__FILENAME__ = test_refresh_queries
import datetime
from mock import patch, call
from tests import BaseTestCase
from tests.factories import query_factory, query_result_factory
from redash.tasks import refresh_queries


# TODO: this test should be split into two:
# 1. tests for Query.outdated_queries method
# 2. test for the refresh_query task
class TestRefreshQueries(BaseTestCase):
    def test_enqueues_outdated_queries(self):
        query = query_factory.create(ttl=60)
        retrieved_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        query_result = query_result_factory.create(retrieved_at=retrieved_at, query=query.query,
                                                   query_hash=query.query_hash)
        query.latest_query_data = query_result
        query.save()

        with patch('redash.tasks.QueryTask.add_task') as add_job_mock:
            refresh_queries()
            add_job_mock.assert_called_with(query.query, query.data_source, scheduled=True)

    def test_skips_fresh_queries(self):
        query = query_factory.create(ttl=1200)
        retrieved_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        query_result = query_result_factory.create(retrieved_at=retrieved_at, query=query.query,
                                                   query_hash=query.query_hash)

        with patch('redash.tasks.QueryTask.add_task') as add_job_mock:
            refresh_queries()
            self.assertFalse(add_job_mock.called)

    def test_skips_queries_with_no_ttl(self):
        query = query_factory.create(ttl=-1)
        retrieved_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        query_result = query_result_factory.create(retrieved_at=retrieved_at, query=query.query,
                                                   query_hash=query.query_hash)

        with patch('redash.tasks.QueryTask.add_task') as add_job_mock:
            refresh_queries()
            self.assertFalse(add_job_mock.called)

    def test_enqueues_query_only_once(self):
        query = query_factory.create(ttl=60)
        query2 = query_factory.create(ttl=60, query=query.query, query_hash=query.query_hash,
                                      data_source=query.data_source)
        retrieved_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        query_result = query_result_factory.create(retrieved_at=retrieved_at, query=query.query,
                                                   query_hash=query.query_hash)
        query.latest_query_data = query_result
        query2.latest_query_data = query_result
        query.save()
        query2.save()

        with patch('redash.tasks.QueryTask.add_task') as add_job_mock:
            refresh_queries()
            add_job_mock.assert_called_once_with(query.query, query.data_source, scheduled=True)

    def test_enqueues_query_with_correct_data_source(self):
        query = query_factory.create(ttl=60)
        query2 = query_factory.create(ttl=60, query=query.query, query_hash=query.query_hash)
        retrieved_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        query_result = query_result_factory.create(retrieved_at=retrieved_at, query=query.query,
                                                   query_hash=query.query_hash)
        query.latest_query_data = query_result
        query2.latest_query_data = query_result
        query.save()
        query2.save()

        with patch('redash.tasks.QueryTask.add_task') as add_job_mock:
            refresh_queries()
            add_job_mock.assert_has_calls([call(query2.query, query2.data_source, scheduled=True), call(query.query, query.data_source, scheduled=True)], any_order=True)
            self.assertEquals(2, add_job_mock.call_count)

    def test_enqueues_only_for_relevant_data_source(self):
        query = query_factory.create(ttl=60)
        query2 = query_factory.create(ttl=3600, query=query.query, query_hash=query.query_hash)
        retrieved_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        query_result = query_result_factory.create(retrieved_at=retrieved_at, query=query.query,
                                                   query_hash=query.query_hash)
        query.latest_query_data = query_result
        query2.latest_query_data = query_result
        query.save()
        query2.save()

        with patch('redash.tasks.QueryTask.add_task') as add_job_mock:
            refresh_queries()
            add_job_mock.assert_called_once_with(query.query, query.data_source, scheduled=True)
########NEW FILE########
__FILENAME__ = test_settings
from redash import settings as settings
from unittest import TestCase


class TestDatabaseUrlParser(TestCase):
    def test_only_database_name(self):
        config = settings.parse_db_url("postgresql://postgres")
        self.assertEquals(config['name'], 'postgres')

    def test_host_and_database_name(self):
        config = settings.parse_db_url("postgresql://localhost/postgres")
        self.assertEquals(config['name'], 'postgres')
        self.assertEquals(config['host'], 'localhost')

    def test_host_with_port_and_database_name(self):
        config = settings.parse_db_url("postgresql://localhost:5432/postgres")
        self.assertEquals(config['name'], 'postgres')
        self.assertEquals(config['host'], 'localhost')
        self.assertEquals(config['port'], 5432)

    def test_full_url(self):
        config = settings.parse_db_url("postgresql://user:pass@localhost:5432/postgres")
        self.assertEquals(config['name'], 'postgres')
        self.assertEquals(config['host'], 'localhost')
        self.assertEquals(config['port'], 5432)
        self.assertEquals(config['user'], 'user')
        self.assertEquals(config['password'], 'pass')
########NEW FILE########
__FILENAME__ = test_sql_meta_data
from redash.utils import SQLMetaData
from unittest import TestCase


class TestSQLMetaData(TestCase):
    def test_simple_select(self):
        metadata = SQLMetaData("SELECT t FROM test")
        self.assertEquals(metadata.used_tables, set(("test",)))
        self.assertFalse(metadata.has_ddl_statements)
        self.assertFalse(metadata.has_non_select_dml_statements)

    def test_multiple_select(self):
        metadata = SQLMetaData("SELECT t FROM test, test2 WHERE t > 1; SELECT a, b, c FROM testing as tbl")
        self.assertEquals(metadata.used_tables, set(("test", "test2", "testing")))
        self.assertFalse(metadata.has_ddl_statements)
        self.assertFalse(metadata.has_non_select_dml_statements)

    def test_detects_ddl(self):
        metadata = SQLMetaData("SELECT t FROM test; DROP TABLE test")
        self.assertEquals(metadata.used_tables, set(("test",)))
        self.assertTrue(metadata.has_ddl_statements)
        self.assertFalse(metadata.has_non_select_dml_statements)

    def test_detects_dml(self):
        metadata = SQLMetaData("SELECT t FROM test; DELETE * FROM test")
        self.assertEquals(metadata.used_tables, set(("test",)))
        self.assertFalse(metadata.has_ddl_statements)
        self.assertTrue(metadata.has_non_select_dml_statements)

########NEW FILE########
