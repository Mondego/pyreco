__FILENAME__ = fabfile
from __future__ import with_statement
import os

from django.core import management
# We have to re-name this to avoid clashes with fabric.api.settings.
import settings as django_settings
management.setup_environ(django_settings)

from fabric.api import *
# This will import every command, you may need to get more selective if
# you aren't using all of the stuff we do.
# For example:
# from fabtastic.fabric.commands.c_common import *
# from fabtastic.fabric.commands.c_git import git_pull
from fabtastic.fabric.commands import *

"""
Here are some deployment related settings. These can be pulled from your
settings.py if you'd prefer. We keep strictly deployment-related stuff in
our fabfile.py, but you don't have to.
"""
# The path on your servers to your codebase's root directory. This needs to
# be the same for all of your servers. Worse case, symlink away.
env.REMOTE_CODEBASE_PATH = '/home/account/codebase'
# Path relative to REMOTE_CODEBASE_PATH.
env.PIP_REQUIREMENTS_PATH = 'requirements.txt'
# The standardized virtualenv name to use.
env.REMOTE_VIRTUALENV_NAME = 'your_virtualenv'

# This is used for reloading gunicorn processes after code updates.
# Only needed for gunicorn-related tasks.
env.GUNICORN_PID_PATH = os.path.join(env.REMOTE_CODEBASE_PATH, 'gunicorn.pid')

def staging():
    """
    Sets env.hosts to the sole staging server. No roledefs means that all
    deployment tasks get ran on every member of env.hosts.
    """
    env.hosts = ['staging.example.org']

def prod():
    """
    Set env.roledefs according to our deployment setup. From this, an
    env.hosts list is generated, which determines which hosts can be
    messed with. The roledefs are only used to determine what each server is.
    """
    # Nginx proxies.
    env.roledefs['proxy_servers'] = ['proxy1.example.org']
    # The Django + gunicorn app servers.
    env.roledefs['webapp_servers'] = ['app1.example.org']
    # Static media servers
    env.roledefs['media_servers'] = ['media1.example.org']
    # Postgres servers.
    env.roledefs['db_servers'] = ['db1.example.org']

    # Combine all of the roles into the env.hosts list.
    env.hosts = [host[0] for host in env.roledefs.values()]

def deploy():
    """
    Full git deployment. Migrations, reloading gunicorn.
    """
    git_pull()
    south_migrate()
    gunicorn_restart_workers()
    flush_cache()
    # Un-comment this if you have mediasync installed to sync on deploy.
    #mediasync_syncmedia()

def deploy_soft():
    """
    Just checkout the latest source, don't reload.
    """
    git_pull()
    print("--- Soft Deployment complete. ---")

########NEW FILE########
__FILENAME__ = postgres
import os
import stat
from bz2 import BZ2File
from subprocess import Popen, PIPE, call

def set_pgpass(database):
    """
    Sets the ~/.pgpass file up so that psql and pg_dump doesn't ask 
    for a password.
    """
    pgpass_file = os.path.expanduser('~')
    pgpass_file = os.path.join(pgpass_file, '.pgpass')
    
    db_host = database['HOST']
    db_port = database['PORT']
    #db_name = database['NAME']
    # Wildcarded for dropdb.
    db_name = '*'
    db_user = database['USER']
    db_pass = database['PASSWORD']
    
    if db_host is '':
        db_host = '*'
    if db_port is '':
        db_port = '*'
    
    fd = open(pgpass_file, 'wb')
    # host:port:database:username:password
    fd.write('%s:%s:%s:%s:%s' % (db_host, db_port, db_name, db_user, db_pass))
    fd.close()
    
    perms = stat.S_IRUSR | stat.S_IWUSR
    os.chmod(pgpass_file, perms)
    
def add_common_options_to_cmd(cmd, database, no_password_prompt=False,
                              **kwargs):
    """
    Adds some commonly used options to the given command string. psql,
    pg_dump, pg_restore, and a few others have some flags in common.
    
    cmd: (list) A command list, in format for Popen/call().
    """
    if database['HOST'] is not '':
        cmd.append('--host=%s' % database['HOST'])
        
    if database['PORT'] is not '':
        cmd.append('--port=%s' % database['PORT'])
        
    if no_password_prompt:
        cmd.append('--no-password')
        
    cmd.append('--username=%s' % database['USER'])

def dump_db_to_file(dump_path, database, no_owner=True, **kwargs):
    """
    pg_dumps the specified database to a given path. Passes output through
    bzip2 for compression.
    
    dump_path: (str) Complete path (with filename) to pg_dump out to.
    database: (dict) Django 1.2 style DATABASE settings dict.
    no_password_prompt: (bool) When True, never prompt for password, and fail
                               if none is provided by env variables or .pgpass.
                               
    Returns the path that was dumped to.
    """
    # Set a .pgpass file up so we're not prompted for a password.
    set_pgpass(database)
    
    cmd = ['pg_dump', '-i']
    
    # Add some common postgres options.
    add_common_options_to_cmd(cmd, database, **kwargs)
    
    # Plain formatting
    cmd.append('--format=p')

    if no_owner:
        cmd.append('--no-owner')

    cmd.append(database['NAME'])
    
    print "pg_dumping database '%s' to %s" % (database['NAME'], dump_path)
    
    # Run pg_dump
    db_dump = Popen(cmd, stdout=PIPE)
    # Open the eventual .tar.bz2 file for writing by bzip2.
    tfile = open(dump_path, 'w')
    # Use bzip2 to dump into the open file handle via stdout.
    db_bzip = Popen(['bzip2'], stdin=db_dump.stdout, stdout=tfile)
    db_bzip.wait()
    tfile.close()
    
    print "Database dump complete."
    
    return dump_path

def drop_db(database, **kwargs):
    """
    Drops the specified database.
    """
    # Set a .pgpass file up so we're not prompted for a password.
    set_pgpass(database)
    
    cmd = ['dropdb']
    
    # Add some common postgres options.
    add_common_options_to_cmd(cmd, database, **kwargs)
    
    cmd.append(database['NAME'])
    
    call(cmd)
    
def create_db(database, **kwargs):
    """
    Creates the specified database.
    """
    # Set a .pgpass file up so we're not prompted for a password.
    set_pgpass(database)
    
    cmd = ['createdb']
    
    add_common_options_to_cmd(cmd, database, no_password_prompt=False)
    
    cmd.append('--owner=%s' % database['USER'])
    cmd.append(database['NAME'])
    call(cmd)

def restore_db_from_file(dump_path, database, **kwargs):
    """
    Restores the specified database from a pg_dump file.
    
    dump_path: (str) Complete path (with filename) to pg_restore from.
    database: (dict) Django 1.2 style DATABASE settings dict.
    """
    decompress = ['bunzip2', '--keep', dump_path]
    print "De-compressing %s" % dump_path
    call(decompress)
    
    # Yank the .bz2 off of the end of the dump_path, now that it's
    # decompressed.
    decompresed_path = dump_path[:-4]
    
    # Set a .pgpass file up so we're not prompted for a password.
    set_pgpass(database)
    
    cmd = ['psql', '-q']
    
    # Add some common postgres options.
    add_common_options_to_cmd(cmd, database, **kwargs)

    cmd.append('--dbname=%s' % database['NAME'])
    cmd.append('--file=%s' % decompresed_path)

    print "Running pg_restore"
    # Run the assembled pg_restore above.
    Popen(cmd).wait()
    
    # Get rid of the decompressed db dump.
    del_decompressed = ['rm', '-f', decompresed_path]
    call(del_decompressed)
    
    print "Restoration complete."
########NEW FILE########
__FILENAME__ = util
"""
Various database-related utility functions.
"""
import datetime
from django.conf import settings

def get_db_setting(db_setting, db_alias='default'):
    """
    Gets a database setting from settings.py.
    
    db_setting: (str) One of the database setting names.
        For example, 'NAME', 'PORT', 'HOST'.
    db_alias: (str) In the case of settings in Django 1.2 format, get settings
                    for a DB other than the default.
    """
    return settings.DATABASES[db_alias].get(db_setting, '')
    
def get_db_setting_dict(db_alias='default'):
    """
    Returns a dict of DB settings, as per the Django 1.2 DATABASE settings.py
    dict. This can be used as a compatibility measure for Django 1.1 and
    earlier.
    """
    return {
        'ENGINE': get_db_setting('ENGINE', db_alias=db_alias),
        'NAME': get_db_setting('NAME', db_alias=db_alias),
        'HOST': get_db_setting('HOST', db_alias=db_alias),
        'PORT': get_db_setting('PORT', db_alias=db_alias),
        'USER': get_db_setting('USER', db_alias=db_alias),
        'PASSWORD': get_db_setting('PASSWORD', db_alias=db_alias),
    }
    
def get_db_dump_filename(db_alias='default'):
    """
    Returns a generic DB dump file name for use with backup/restore scripts.
    Fabric commands share this function with the management commands.
    """
    today = datetime.datetime.today()
    database_dict = get_db_setting_dict(db_alias)

    dump_filename = "%s-%s.sql.tar.bz2" %  (
        database_dict['NAME'], 
        today.strftime("%Y_%m_%d-%H%M"),
    )
    return dump_filename
########NEW FILE########
__FILENAME__ = c_celery
from fabric.api import *
from fabtastic.fabric.util import _current_host_has_role

def celeryd_restart(roles='celery_servers'):
    """
    Reloads celeryd. This must be done to re-compile the code after a new
    revision has been checked out.

    NOTE: This broadcasts a 'shutdown' call to all celery workers. You must have
    supervisor or something running to start them back up, or this ends up
    just being a shutdown (sans restart).
    """
    if _current_host_has_role(roles):
        print("=== RESTARTING CELERY DAEMON ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py ft_celeryd_restart" % env.REMOTE_VIRTUALENV_NAME)
            print "Celery shutdown broadcasted, workers restarting."

########NEW FILE########
__FILENAME__ = c_common
import os
import sys
from fabric.api import *
from fabtastic import db
from fabtastic.fabric.util import _current_host_has_role

def get_remote_db(roles='webapp_servers'):
    """
    Retrieves a remote DB dump and dumps it in your project's root directory.
    """
    if _current_host_has_role(roles):
        dump_filename = db.util.get_db_dump_filename()
        dump_path = os.path.join(env.REMOTE_CODEBASE_PATH, dump_filename)

        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py ft_dump_db %s" % (
                env.REMOTE_VIRTUALENV_NAME,
                dump_filename))
            get(dump_path, dump_filename)
            run("rm %s" % dump_filename)

        # In a multi-host environment, target hostname is appended by Fabric.
        # TODO: Make this use Fabric 1.0's improved get() when it's released.
        new_filename = '%s.%s' % (dump_filename, env['host'])
        # Move it back to what it should be.
        local('mv %s %s' % (new_filename, dump_filename))

        # Die after this to prevent executing this with more hosts.
        sys.exit(0)

def sync_to_remote_db(roles='webapp_servers'):
    """
    Retrieves a remote DB dump, wipes your local DB, and installs the
    remote copy in place.
    """
    if _current_host_has_role(roles):
        dump_filename = db.util.get_db_dump_filename()
        dump_path = os.path.join(env.REMOTE_CODEBASE_PATH, dump_filename)

        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py ft_dump_db %s" % (
                env.REMOTE_VIRTUALENV_NAME,
                dump_filename))
            get(dump_path, dump_filename)
            run("rm %s" % dump_filename)

        # In a multi-host environment, target hostname is appended by Fabric.
        # TODO: Make this use Fabric 1.0's improved get() when it's released.
        filename_with_hostname = '%s.%s' % (dump_filename, env['host'])
        if os.path.exists(filename_with_hostname):
            # Move it back to what it should be.
            local('mv %s %s' % (filename_with_hostname, dump_filename))
        local('./manage.py ft_restore_db %s' % dump_filename, capture=False)
        local('rm %s' % dump_filename)

        # Die after this to prevent executing this with more hosts.
        sys.exit(0)

def flush_cache(roles=['webapp_servers', 'celery_servers']):
    """
    Flushes the cache.
    """
    if _current_host_has_role(roles):
        print("=== FLUSHING CACHE ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py ft_clear_cache" % env.REMOTE_VIRTUALENV_NAME)

def pip_update_reqs(roles=['webapp_servers', 'celery_servers']):
    """
    Updates your virtualenv from requirements.txt.
    """
    if _current_host_has_role(roles):
        print("=== UPDATING REQUIREMENTS ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py ft_pip_update_reqs" % env.REMOTE_VIRTUALENV_NAME)

def fabtastic_update(roles=['webapp_servers', 'celery_servers']):
    """
    Updates your copy of django-fabtastic from the git repository.
    """
    if _current_host_has_role(roles):
        print("=== UPDATING FABTASTIC ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py ft_fabtastic_update" % env.REMOTE_VIRTUALENV_NAME)

def collectstatic(roles='webapp_servers'):
    """
    Syncs the checked out git media with S3.
    """
    if _current_host_has_role(roles) and not env.already_media_synced:
        print("=== SYNCING STATIC MEDIA WITH S3 ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py collectstatic --noinput" % env.REMOTE_VIRTUALENV_NAME)
        env.already_media_synced = True
########NEW FILE########
__FILENAME__ = c_compressor
from fabric.api import *
from fabtastic.fabric.util import _current_host_has_role

def compress(roles='webapp_servers'):
    """
    Runs django-compressor's offline compression command.
    """
    if _current_host_has_role(roles):
        print("=== COMPRESSING STATIC MEDIA ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py compress --force" % env.REMOTE_VIRTUALENV_NAME)
########NEW FILE########
__FILENAME__ = c_git
from fabric.api import *
from fabtastic.fabric.util import _current_host_has_role

def git_pull(roles=['webapp_servers', 'celery_servers']):
    """
    Pulls the latest master branch from the git repo.
    """
    if _current_host_has_role(roles):
        print("=== PULLING FROM GIT ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("git pull")
            # Remove .pyc files for modules that no longer exist.
            run("find . -name '*.pyc' -delete")

########NEW FILE########
__FILENAME__ = c_gunicorn
from fabric.api import *
from fabtastic.fabric.util import _current_host_has_role

def gunicorn_restart_workers():
    """
    Reloads gunicorn. This must be done to re-compile the code after a new
    revision has been checked out.
    """
    if _current_host_has_role('webapp_servers'):
        print("=== RESTARTING GUNICORN WORKERS ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py ft_gunicorn_restart" % env.REMOTE_VIRTUALENV_NAME)
        print("Gunicorn reloaded")
########NEW FILE########
__FILENAME__ = c_mediasync
from fabric.api import *
from fabtastic.fabric.util import _current_host_has_role

def mediasync_syncmedia(roles='webapp_servers'):
    """
    Syncs the checked out git media with S3.
    """
    if _current_host_has_role(roles) and not env.already_media_synced:
        print("=== SYNCING STATIC MEDIA WITH S3 ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py syncmedia" % env.REMOTE_VIRTUALENV_NAME)
        env.already_media_synced = True
########NEW FILE########
__FILENAME__ = c_s3cmd
import sys
from fabric.api import *
from fabtastic.fabric.util import _current_host_has_role
       
def backup_db_to_s3():
    """
    Backs up the DB to Amazon S3. The DB server runs pg_dump,
    then uploads to S3 via the s3cmd command. On new DB instances, you'll need
    to run 's3cmd --configure' (as the user that will be running s3cmd) to setup 
    the keys. You'll notice they aren't passed here as a result of that.
    """
    if _current_host_has_role('webapp_servers'):        
        print("=== BACKING UP DB TO S3 ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py ft_backup_db_to_s3" % env.REMOTE_VIRTUALENV_NAME)
        print("DB backed up to S3.")
        
        # Die after this to prevent executing this with more hosts.
        sys.exit(0)
########NEW FILE########
__FILENAME__ = c_south
from fabric.api import *
from fabtastic.fabric.util import _current_host_has_role

def south_migrate():
    """
    Migrates the DB schema with South. Sets already_db_migrated to prevent
    double migrations.
    """
    if _current_host_has_role('webapp_servers') and not env.already_db_migrated:
        print("=== RUNNING SOUTH DB MIGRATIONS ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py migrate" % env.REMOTE_VIRTUALENV_NAME)
        env.already_db_migrated = True
########NEW FILE########
__FILENAME__ = c_supervisord
from fabric.api import *
from fabtastic.fabric.util import _current_host_has_role

def supervisord_restart_all(roles='webapp_servers'):
    """
    Restarts all of supervisord's managed programs.
    """
    if _current_host_has_role(roles):
        print("=== RESTARTING SUPERVISORD PROGRAMS ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py ft_supervisord_restart_prog" % env.REMOTE_VIRTUALENV_NAME)

def supervisord_restart_prog(program, roles='webapp_servers'):
    """
    Restarts all of supervisord's managed programs.
    
    :arg str program: The name of the program to restart (as per supervisor's
        conf.d/ contents).
    """
    if _current_host_has_role(roles):
        print("=== RESTARTING SUPERVISORD PROGRAMS ===")
        with cd(env.REMOTE_CODEBASE_PATH):
            run("workon %s && ./manage.py ft_supervisord_restart_prog %s" % (
                env.REMOTE_VIRTUALENV_NAME, program))

########NEW FILE########
__FILENAME__ = util
from fabric.api import *

def _current_host_has_role(roles):
    """
    Looks to see if the host the current task is being executed on has
    the specified role.
    """
    if len(env.roledefs) is 0 and env.hosts:
        # No roledefs defined, but env.hosts is. If we set env.hosts, assume
        # that the operation should be done to everything in env.hosts.
        return True

    # Otherwise check the role list for the current host in env.
    if isinstance(roles, basestring):
        # roles is a string.
        return env['host_string'] in env.roledefs.get(roles, [])
    else:
        # roles is a list of roles.
        for role in roles:
            if env['host_string'] in env.roledefs.get(role, []):
                return True
        return False
########NEW FILE########
__FILENAME__ = ft_backup_db_to_s3
import os
import datetime

from django.core.management.base import BaseCommand
from django.conf import settings

from fabtastic import db
from fabtastic.util.aws import get_s3_connection

class Command(BaseCommand):
    help = 'Backs the DB up to S3.'

    def handle(self, *args, **options):
        db_alias = getattr(settings, 'FABTASTIC_DIRECT_TO_DB_ALIAS', 'default')
        # Get DB settings from settings.py.
        database = db.util.get_db_setting_dict(db_alias=db_alias)
        # Generate a temporary DB dump filename.      
        dump_filename = db.util.get_db_dump_filename(db_alias=db_alias)
        # Carry out the DB dump.
        dump_file_path = db.dump_db_to_file(dump_filename, database)

        print "Uploading to S3."
        conn = get_s3_connection()
        bucket = conn.create_bucket(settings.S3_DB_BACKUP['BUCKET'])
        now = datetime.datetime.now()
        s3_path = '%d/%d/%d/%s' % (
            now.year,
            now.month,
            now.day,
            dump_filename,
        )
        key = bucket.new_key(s3_path)
        key.set_contents_from_filename(dump_file_path)
        bucket.copy_key(
            'latest_db.sql.tar.bz2',
            settings.S3_DB_BACKUP['BUCKET'],
            s3_path,
        )
        print "S3 DB backup complete."

        # Clean up the temporary download file.
        os.remove(dump_filename)

########NEW FILE########
__FILENAME__ = ft_celeryd_restart
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Restarts all celery daemons.'

    def handle(self, *args, **options):
        try:
            from celery.task.control import broadcast
        except ImportError:
            raise CommandError("Celery is not currently installed.")
        
        # Shut them all down.
        broadcast("shutdown")
########NEW FILE########
__FILENAME__ = ft_check_reqs
from django.core.management.base import BaseCommand
from fabric.api import *
import fabfile
from fabtastic.util.req_syncer import compare_reqs_to_env

class Command(BaseCommand):
    help = "Compares your current virtualenv to requirements.txt."

    def handle(self, *args, **options):
        missing_pkgs, wrong_version_pkgs = compare_reqs_to_env(env.PIP_REQUIREMENTS_PATH)

        if wrong_version_pkgs:
            print "==== Version mis-matches ===="
            for pkg_tuple in wrong_version_pkgs:
                pkg_name, req_version, local_version = pkg_tuple
                print ' %s==%s in reqs.txt, but %s==%s local' % (
                    pkg_name,
                    req_version,
                    pkg_name,
                    local_version
                )

        if missing_pkgs:
            print "==== Missing (locally) packages ===="
            for pkg_name in missing_pkgs:
                print ' %s' % pkg_name

        if not wrong_version_pkgs and not missing_pkgs:
            print "Your local environment is up to date, good job."
########NEW FILE########
__FILENAME__ = ft_clear_cache
from django.core.management.base import BaseCommand
from django.core.cache import cache

class Command(BaseCommand):
    help = "Flushes the Django cache."

    def handle(self, *args, **options):
        cache.clear()

########NEW FILE########
__FILENAME__ = ft_dump_db
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from fabtastic import db

class Command(BaseCommand):
    args = '[<output_file_path>]'
    help = 'Dumps a SQL backup of your entire DB. Defaults to CWD.'
                        
    def get_dump_path(self, db_alias):
        """
        Determines the path to write the SQL dump to. Depends on whether the
        user specified a path or not.
        """
        if len(self.args) > 0:
            return self.args[0]
        else:
            dump_filename = db.util.get_db_dump_filename(db_alias=db_alias)
            return os.path.join(os.getcwd(), dump_filename)
        
    def handle(self, *args, **options):
        """
        Handle raw input.
        """
        self.args = args
        self.options = options

        db_alias = getattr(settings, 'FABTASTIC_DIRECT_TO_DB_ALIAS', 'default')
        # Get DB settings from settings.py.
        database = db.util.get_db_setting_dict(db_alias=db_alias)
        # Figure out where to dump the file to.
        dump_path = self.get_dump_path(db_alias)

        # Run the db dump.
        db.dump_db_to_file(dump_path, database)
########NEW FILE########
__FILENAME__ = ft_fabtastic_update
from subprocess import call
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Updates your copy of Fabtastic to the latest from git."

    def handle(self, *args, **options):
        fabtastic_repo = 'git+http://github.com/duointeractive/django-fabtastic.git#egg=fabtastic'
        cmd = ['pip', 'install', '--upgrade', fabtastic_repo]
        call(cmd)        

########NEW FILE########
__FILENAME__ = ft_get_db_backup_from_s3
from django.core.management.base import BaseCommand
from django.conf import settings

from fabtastic.util.aws import get_s3_connection

class Command(BaseCommand):
    help = 'Retrieves the latest backup from S3.'

    def handle(self, *args, **options):
        download_key = 'latest_db.sql.tar.bz2'
        
        conn = get_s3_connection()
        bucket = conn.create_bucket(settings.S3_DB_BACKUP['BUCKET'])
        key = bucket.new_key(download_key)

        print "Downloading %s DB backup from S3." % download_key
        fobj = open(download_key, 'w')
        key.get_contents_to_file(fobj)

        print "S3 DB backup download complete."

########NEW FILE########
__FILENAME__ = ft_gunicorn_restart
import os
import signal

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from fabric.api import *
import fabfile

class Command(BaseCommand):
    help = 'Restarts gunicorn workers after code changes.'

    def handle(self, *args, **options):
        pid_path = env.GUNICORN_PID_PATH
        if os.path.exists(pid_path):
            pid = int(open(pid_path, 'r').read())
            os.kill(pid, signal.SIGHUP)
        else:
            raise CommandError("No gunicorn process running.")
########NEW FILE########
__FILENAME__ = ft_pip_update_reqs
from subprocess import call
from django.core.management.base import BaseCommand
from fabric.api import *
import fabfile

class Command(BaseCommand):
    help = "Updates your virtualenv from requirements.txt."

    def handle(self, *args, **options):
        pip_req_path = env.PIP_REQUIREMENTS_PATH
        cmd = ['pip', 'install', '--upgrade', '-r', pip_req_path]
        call(cmd)        

########NEW FILE########
__FILENAME__ = ft_restore_db
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from fabtastic import db

class Command(BaseCommand):
    args = '[<output_file_path>]'
    help = 'Restores a DB from a SQL dump file.'

    option_list = BaseCommand.option_list + (
        make_option('-f',
                    action='store_true',
                    dest='prod_override',
                    default=False,
                    help='Override to allow restoring DB in production.'),
        )

    def handle(self, *args, **options):
        """
        Handle raw input.
        """
        self.args = args
        self.options = options

        if len(self.args) < 1:
            raise CommandError("ft_restore_db: You must specify the path to "
                               "the DB dump file to restore from.")

        is_production = getattr(settings, 'IS_PRODUCTION', False)
        has_prod_override = self.options['prod_override']
        if is_production and not has_prod_override:
            raise CommandError("ft_restore_db: Not allowed in production. "
                               "Use -f option to override.")

        # Path to file to restore from.
        dump_path = self.args[0]

        db_alias = getattr(settings, 'FABTASTIC_DIRECT_TO_DB_ALIAS', 'default')
        # Get DB settings from settings.py.
        database_dict = db.util.get_db_setting_dict(db_alias=db_alias)

        # Drop the DB.
        db.drop_db(database_dict)
        # Re-create an empty DB with the same name.
        db.create_db(database_dict)
        # Restore from the DB dump.
        db.restore_db_from_file(dump_path, database_dict)
########NEW FILE########
__FILENAME__ = ft_supervisord_restart_prog
from subprocess import call
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Restarts one or all of supervisord's managed programs"

    def handle(self, *args, **options):
        self.args = args
        self.options = options

        cmd = ['supervisorctl', 'restart']

        if self.args:
            cmd += self.args
        else:
            cmd.append('all')

        call(cmd)

########NEW FILE########
__FILENAME__ = aws
"""
Amazon AWS-related utils.
"""
import boto
from django.conf import settings

def get_s3_connection():
    """
    Returns an S3Connection object. Uses values from fabfile.env for creds.
    """
    conf = settings.S3_DB_BACKUP
    return boto.connect_s3(conf['AWS_ACCESS_KEY_ID'],
                           conf['AWS_SECRET_ACCESS_KEY'])

########NEW FILE########
__FILENAME__ = req_syncer
"""
Utilities for syncing your virtualenv to requirements.txt.
"""
import pkg_resources

class RequirementsParser(object):
    def __init__(self, path):
        self.path = path

    def parse(self):
        fobj = open(self.path, 'r')
        lines = fobj.readlines()
        req_packages = {}
        for line in lines:
            line = line.rstrip()
            if not line or line.startswith('git+') or not line[0].isalpha():
                continue

            equal_split = line.split('==', 1)
            pkg_name = equal_split[0]
            if len(equal_split) == 2:
                req_packages[pkg_name] = equal_split[1]
            else:
                req_packages[pkg_name] = None

        return req_packages


def compare_reqs_to_env(requirements_path):
    local_packages = {}
    for package in pkg_resources.working_set:
        local_packages[package.project_name] = package.version

    parser = RequirementsParser(requirements_path)
    req_packages = parser.parse()

    missing_pkgs = []
    wrong_version_pkgs = []
    for key, val in req_packages.items():
        if not local_packages.has_key(key):
            missing_pkgs.append(key)
            continue

        if val and val != local_packages[key]:
            wrong_version_pkgs.append((key, val, local_packages[key]))

    #print "MISSING"
    #print missing_pkgs
    #print "WRONG VERSION"
    #print wrong_version_pkgs
    return missing_pkgs, wrong_version_pkgs

########NEW FILE########
