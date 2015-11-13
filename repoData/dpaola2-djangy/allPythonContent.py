__FILENAME__ = apache
#
# Djangy installer -- apache web server.
#
# As a stopgap, apache needs to run on the master node, because the main
# controller/website hasn't been transitioned over to run using Gunicorn.
# Apache sits behind the nginx frontend, just like Gunicorn processes.
#
# Author: Sameer Sundresh <sameer@sundresh.org>
#

import os.path
from core import *

@print_when_used
def require_apache():
    run_ignore_failure('/etc/init.d/apache2', 'stop')
    run('a2enmod', 'ssl')
    require_file('/etc/apache2/ports.conf', 'root', 'root', 0644, contents=read_file('conf/apache/ports.conf'), overwrite=True)
    for (site, apache_conf) in [('000-defaults',   '/srv/djangy/install/conf/apache/000-defaults/config/apache.conf'), \
                                ('api.djangy.com', '/srv/djangy/src/server/master/web_api/config/apache.conf'       ), \
                                ('djangy.com',     '/srv/djangy/src/server/master/web_ui/config/apache.conf'        )]:
        assert os.path.exists(apache_conf)
        require_link(os.path.join('/etc/apache2/sites-available', site), apache_conf)
        require_link(os.path.join('/etc/apache2/sites-enabled', site), os.path.join('/etc/apache2/sites-available', site))
    run_ignore_failure('/etc/init.d/apache2', 'start')

@print_when_used
def require_no_apache():
    if os.path.isfile('/etc/init.d/apache2'):
        run_ignore_failure('/etc/init.d/apache2', 'stop')

########NEW FILE########
__FILENAME__ = application_uids_gids
#
# Djangy installer -- application uids/gids.
#
# Each application on Djangy runs as a separate host uid/gid.  At first, we
# tried running code as uid/gid without any entries in /etc/passwd or
# /etc/group, but apache wouldn't allow that.  We then switched over to
# running applicatinos using Gunicorn, but kept this code in place, since
# we use different uid/gid pairs for setup, web servers, and (planned, not
# fully implemented) cron jobs.
#
# Author: Sameer Sundresh <sameer@sundresh.org>
#
import re
from core import *

_UID_GID_BASE = 100000

def _is_application_uid(uid):
    return (uid >= _UID_GID_BASE)

_username_regex = re.compile('^([swc])([1-9][0-9]*)$')

def _assert_valid_application_user(username, uid, gid, homedir, shell):
    match = _username_regex.match(username)
    user_type = match.group(1)
    n = int(match.group(2))
    if user_type == 's':
        assert uid == _setup_uid(n)
    elif user_type == 'w':
        assert uid == _web_uid(n)
    elif user_type == 'c':
        assert uid == _cron_uid(n)
    else:
        assert False
    assert gid     == _application_gid(n)
    assert homedir == '/'
    assert shell   == '/bin/sh'

def _setup_uid(n):
    return 3*(n-1) + _UID_GID_BASE

def _web_uid(n):
    return _setup_uid(n) + 1

def _cron_uid(n):
    return _setup_uid(n) + 2

def _is_application_gid(gid):
    return (gid >= _UID_GID_BASE)

_groupname_regex = re.compile('^g([1-9][0-9]*)$')

def _assert_valid_application_group(groupname, gid, member_usernames):
    n = int(_groupname_regex.match(groupname).group(1))
    assert gid == _application_gid(n)
    assert member_usernames == set(['www-data'])

def _application_gid(n):
    return 3*(n-1) + _UID_GID_BASE

def _get_existing_application_uids():
    file = open('/etc/passwd', 'r')
    existing_application_uids = set()
    for line in file.readlines():
        try:
            line = line[:-1]
            (username, x, uid, gid, description, homedir, shell) = line.split(':')
            uid = int(uid)
            gid = int(gid)
            if _is_application_uid(uid):
                _assert_valid_application_user(username, uid, gid, homedir, shell)
                existing_application_uids.add(uid)
            else:
                assert None == _username_regex.match(username)
        except ValueError:
            print 'malformed /etc/passwd entry "%s"' % line
    file.close()
    return existing_application_uids

def _get_existing_application_gids():
    file = open('/etc/group', 'r')
    existing_application_groups = set()
    for line in file.readlines():
        try:
            line = line[:-1]
            (groupname, x, gid, member_usernames) = line.split(':')
            gid = int(gid)
            if _is_application_gid(gid):
                _assert_valid_application_group(groupname, gid, set(member_usernames.split(',')))
                existing_application_groups.add(gid)
            else:
                assert None == _groupname_regex.match(groupname)
        except ValueError:
            print 'malformed /etc/group entry "%s"' % line
    file.close()
    return existing_application_groups

# Returns (etc_passwd_entries, etc_shadow_entries, etc_group_entries)
def _get_application_entries():
    existing_application_uids = _get_existing_application_uids()
    existing_application_gids = _get_existing_application_gids()
    etc_passwd_entries = []
    etc_shadow_entries = []
    etc_group_entries  = []
    for n in range(1, 20000+1):
        gid       = _application_gid(n)
        setup_uid = _setup_uid(n)
        web_uid   = _web_uid(n)
        cron_uid  = _cron_uid(n)
        if setup_uid not in existing_application_uids:
            etc_passwd_entries.append('s%i:x:%i:%i::/:/bin/sh' % (n, setup_uid, gid))
            etc_shadow_entries.append('s%i:*:0:0:99999:7:::' % n)
        if web_uid not in existing_application_uids:
            etc_passwd_entries.append('w%i:x:%i:%i::/:/bin/sh' % (n, web_uid,   gid))
            etc_shadow_entries.append('w%i:*:0:0:99999:7:::' % n)
        if cron_uid not in existing_application_uids:
            etc_passwd_entries.append('c%i:x:%i:%i::/:/bin/sh' % (n, cron_uid,  gid))
            etc_shadow_entries.append('c%i:*:0:0:99999:7:::' % n)
        if gid not in existing_application_gids:
            etc_group_entries.append('g%i:x:%i:www-data' % (n, gid))
    return (etc_passwd_entries, etc_shadow_entries, etc_group_entries)

def _file_append_entries(file_path, entries):
    if len(entries) > 0:
        print "Adding %i entries to %s" % (len(entries), file_path)
        buf = '\n'.join(entries + [''])
        file = open(file_path, 'a')
        file.write(buf)
        file.close()
    else:
        print "%s already populated" % file_path

@print_when_used
def require_application_uids_gids():
    (etc_passwd_entries, etc_shadow_entries, etc_group_entries) = _get_application_entries()
    _file_append_entries('/etc/passwd', etc_passwd_entries)
    _file_append_entries('/etc/shadow', etc_shadow_entries)
    _file_append_entries('/etc/group',  etc_group_entries)

########NEW FILE########
__FILENAME__ = backup
#! /usr/bin/env python
#
# Perform a backup of the Djangy system state.
#
# Author: Dave Paola <dpaola2@gmail.com>
#

import subprocess, dump_archive, os
from s3put import *

# Makes a dump of the master node and uploads it to S3

def main():
    print "Dumping archive...",
    filename = dump_archive.main()
    print "Done."
    print "Uploading to S3...",
    upload(filename)
    print "Done."
    print "Cleaning up...",
    os.remove(filename)
    print "Done."

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = post_receive
../../../src/server/master/master_manager/post_receive.py
########NEW FILE########
__FILENAME__ = config
# Configuration options set by command-line arguments to install.py
ACTION                  = None  # 'install' or 'upgrade'
MASTER_NODE             = False
WORKER_NODE             = False
PROXYCACHE_NODE         = False
MASTER_MANAGER_HOST     = None
DEFAULT_PROXYCACHE_HOST = None
DEFAULT_DATABASE_HOST   = None
WORKERHOSTS             = []
PRODUCTION              = False
TO_SOUTH                = False

RABBITMQ_THIS_HOST      = None
RABBITMQ_LEADER_HOST    = None

# Configuration options set in config.py
DB_ROOT_PASSWORD = 'password goes here'
MASTER_DATABASES = [
    # (username, password, dbname)
    ('djangy',  'password goes here', 'djangy'),
    ('web_ui',  'password goes here', 'web_ui'),
    ('web_api', 'password goes here', 'web_api')
]

# S3 access stuff
S3_ACCESS_KEY   = 'password goes here'
S3_SECRET       = 'password goes here'
S3_BUCKET       = 'djangy_backups'

# Billing stuff
DEVPAYMENTS_TESTING     = 'password goes here'
DEVPAYMENTS_PRODUCTION  = 'password goes here'
DEVPAYMENTS_API_KEY     = DEVPAYMENTS_TESTING

########NEW FILE########
__FILENAME__ = core
#
# Declarative decorators and predicates for Djangy's installer.
#
# The idea is you specify how things should be, and the code either
# verifies that it is so, or performs actions to make it so, or
# fails with an exception if the system is in a conflicting state.
#
# Author: Sameer Sundresh <sameer@sundresh.org>
#

import grp, os, os.path, pwd, shutil, subprocess, tempfile


# Decorator to print out a status message boxing the output of a function. 
# Useful for long running functions or those that print output.
def print_when_used(func):
    def _line(char):
        return ''.join([char for i in range(0, 80/len(char))])
    def print_when_used(*args):
        print _line('=')
        print func.__name__ + str(args)
        print _line('- ')
        try:
            return func(*args)
        finally:
            print _line('-')
    return print_when_used

# Decorator to run a function in a temporary directory, and then delete the
# temporary directory when the function returns (or throws an exception).
def in_tempdir(func):
    def in_tempdir(*args, **kwargs):
        tempdir = tempfile.mkdtemp(prefix='djangy_install_')
        assert tempdir.startswith('/tmp/djangy_install_')
        old_dir = os.getcwd()
        try:
            os.chdir(tempdir)
            return func(*args, **kwargs)
        finally:
            os.chdir(old_dir)
            shutil.rmtree(tempdir)
    return in_tempdir

# Decorator to run a function in a given (static) directory
def in_dir(dir):
    def in_dir(func):
        def in_dir(*args, **kwargs):
            old_dir = os.getcwd()
            os.chdir(dir)
            try:
                return func(*args, **kwargs)
            finally:
                os.chdir(old_dir)
        return in_dir
    return in_dir

# For use as "with cd(dir): ..."
class cd(object):
    def __init__(self, dir_path):
        self._dir_path = dir_path
    def __enter__(self):
        self._old_dir_path = os.getcwd()
        os.chdir(self._dir_path)
    def __exit__(self, type, value, traceback):
        os.chdir(self._old_dir_path)

# Run an external program, fail if it returns non-zero
def run(*args):
    assert 0 == subprocess.call(list(args))

# Run an external program supplying stdin contents, fail if it returns non-zero
def run_with_stdin(args, stdin=None):
    p = subprocess.Popen(args, stdin=subprocess.PIPE)
    p.stdin.write(stdin)
    p.stdin.close()
    assert 0 == p.wait()

# Run an external program, ignore its return value
def run_ignore_failure(*args):
    subprocess.call(list(args))

# Check that a user exists, with the given settings.
# Settings with value None are not checked.
def user_exists(username=None, uid=None, gid=None, homedir=None, shell=None):
    try:
        passwd = pwd.getpwnam(username)
    except:
        try:
            passwd = pwd.getpwuid(uid)
        except:
            return False

    return not (
        (uid      and passwd.pw_uid   != uid     ) or
        (gid      and passwd.pw_gid   != gid     ) or
        (homedir  and passwd.pw_dir   != homedir ) or
        (shell    and passwd.pw_shell != shell   ))

# Check that a group exists, with the given settings.
# Settings with value None are not checked.
def group_exists(groupname=None, gid=None, member_usernames=None):
    try:
        group = grp.getgrnam(groupname)
    except:
        try:
            group = grp.getgrgid(gid)
        except:
            return False

    return not (
        (gid              and group.gr_gid      != gid                  ) or
        (member_usernames and set(group.gr_mem) != set(member_usernames)))

# Try to allocate a fresh UID.
# Raises UidAllocationException.
def _get_fresh_uid():
    for uid in range(100, 1000):
        try:
            pwd.getpwuid(uid)
        except KeyError:
            return uid
    raise UidAllocationException()

# Try to allocate a fresh GID.
# Raises UidAllocationException.
def _get_fresh_gid():
    for gid in range(100, 1000):
        try:
            grp.getgrgid(gid)
        except KeyError:
            return gid
    raise GidAllocationException()

# Called by require_user() to update /etc/passwd and /etc/shadow
# Called by require_group() to update /etc/group
def _append_to_file(file_path, line):
    file = open(file_path, 'a')
    file.write(line + '\n')
    file.close()

# Called by require_file() to create a file that doesn't exist but
# whose contents are specified.
def _create_file(file_path, contents):
    file = open(file_path, 'w')
    file.write(contents)
    file.close()

# Called by require_file() to read and check a file's contents.
# Also called by install.py
def read_file(file_path):
    file = open(file_path, 'r')
    contents = file.read()
    file.close()
    return contents

# Check that a user exists with the given settings, creating one if
# necessary and possible.  Raises RequireUserException
def require_user(username, gid=None, groupname=None, uid=None, homedir=None, shell=None, description=None, create=True):
    # Canonicalize arguments
    if gid == None:
        gid = grp.getgrnam(groupname).gr_gid
    # Create user if it doesn't exist
    if create and not user_exists(username=username):
        if uid != None:
            if user_exists(uid=uid):
                raise RequireUserException(username)
        else:
            uid = _get_fresh_uid()
        etc_passwd_line = '%s:x:%i:%i:%s:%s:%s' % (username, uid, gid, description or '', homedir or '/', shell)
        etc_shadow_line = '%s:*:14907:0:99999:7:::' % username
        _append_to_file('/etc/passwd', etc_passwd_line)
        _append_to_file('/etc/shadow', etc_shadow_line)
    # Check user has correct settings
    if not user_exists(username=username, uid=uid, gid=gid, homedir=homedir, shell=shell):
        raise RequireUserException(username)

# Check that a group exists with the given settings, creating one if
# necessary and possible.  member_usernames must match exactly.
# Raises RequireGroupException
def require_group(groupname, gid=None, member_usernames=[], create=True):
    # Create group if it doesn't exist
    if create and not group_exists(groupname=groupname):
        if gid != None:
            if group_exists(gid=gid):
                raise RequireGroupException(groupname)
        else:
            gid = _get_fresh_gid()
        etc_group_line = '%s:x:%i:%s' % (groupname, gid, ','.join(member_usernames))
        _append_to_file('/etc/group', etc_group_line)
    # Check group has correct settings
    if not group_exists(groupname=groupname, gid=gid, member_usernames=member_usernames):
        raise RequireGroupException(groupname)

@print_when_used
def _copy_directory(dir_path, initial_contents_path):
    run('cp', '-r', initial_contents_path, dir_path)
    print 'Done.'

# Check that a directory exists with the given settings, creating one if
# necessary and possible.
def require_directory(dir_path, username, groupname, mode, initial_contents_path=None, create=True):
    # Canonicalize arguments
    dir_path = os.path.abspath(dir_path)
    uid = pwd.getpwnam(username).pw_uid
    gid = grp.getgrnam(groupname).gr_gid
    # Create directory if it doesn't exist
    if create and not os.path.isdir(dir_path):
        if initial_contents_path:
            _copy_directory(dir_path, initial_contents_path)
        else:
            os.mkdir(dir_path, mode)
    # Ensure correct access permissions
    os.chown(dir_path, uid, gid)
    os.chmod(dir_path, mode)

# Check that a given file exists with the given settings.  If the
# initial_contents are specified and file does not exist, then it is
# created.
# Raises RequireFileException
def require_file(file_path, username, groupname, mode, contents=None, initial_contents=None, overwrite=False):
    # Canonicalize arguments
    file_path = os.path.abspath(file_path)
    uid = pwd.getpwnam(username).pw_uid
    gid = grp.getgrnam(groupname).gr_gid
    if initial_contents == None:
        initial_contents = contents
    # Create file if it doesn't exist or overwrite==True
    if type(initial_contents) == str and (overwrite and os.path.isfile(file_path) or not os.path.exists(file_path)):
        _create_file(file_path, initial_contents)
    # Check file exists
    if not os.path.isfile(file_path) or (contents != None and read_file(file_path) != contents):
        raise RequireFileException(file_path)
    # Ensure correct access permissions
    os.chown(file_path, uid, gid)
    os.chmod(file_path, mode)

# Check that a given link exists and points to a given source path, creating
# the link if possible and neccessary.  Raises RequireLinkException
def require_link(link_path, source_path):
    # Canonicalize arguments
    link_path   = os.path.abspath(link_path)
    source_path = os.path.abspath(source_path)
    # Create link if it doesn't exist or is already a link
    if os.path.islink(link_path):
        os.remove(link_path)
    if not os.path.exists(link_path):
        os.symlink(source_path, link_path)
    else:
        raise RequireLinkException(link_path)

# Make sure that a given file or directory has been removed.
def require_remove(path):
    if os.path.exists(path):
        run('rm', '-rf', path)

# Ensure that a given directory and all its recursive contents are owned by
# a given username/groupname.  Raises RequirePermisException
def require_recursive(root_path, username=None, groupname=None):
    # Canonicalize arguments
    root_path = os.path.abspath(root_path)
    # Call external program to do it
    try:
        run('chown', '-R', '%s:%s' % (username, groupname), root_path)
    except:
        raise RequirePermsException(root_path)

# Raises RequireUbuntuPackagesException
@print_when_used
def require_ubuntu_packages(*packages):
    if subprocess.call(['apt-get', '--yes', 'install'] + list(packages)) != 0:
        raise RequireUbuntuPackagesException(packages)

# Raises RequirePythonPackagesException
@print_when_used
def require_python_packages(*packages):
    for package in packages:
        if subprocess.call(['easy_install', package]) != 0:
            raise RequirePythonPackagesException([package])

# Failure exceptions below.

class RequireUserException(Exception):
    def __init__(self, username):
        self.username = username
    def __str__(self):
        return 'RequireUserException(username=\'%s\')' % self.username

class RequireGroupException(Exception):
    def __init__(self, groupname):
        self.groupname = groupname
    def __str__(self):
        return 'RequireGroupException(groupname=\'%s\')' % self.groupname

class RequireFileException(Exception):
    def __init__(self, file_path):
        self.file_path = file_path
    def __str__(self):
        return 'RequireFileException(file_path=\'%s\')' % self.file_path

class RequireLinkException(Exception):
    def __init__(self, link_path):
        self.link_path = link_path
    def __str__(self):
        return 'RequireLinkException(link_path=\'%s\')' % self.link_path

class RequirePermsException(Exception):
    def __init__(self, root_path):
        self.root_path = root_path
    def __str__(self):
        return 'RequirePermsException(root_path=\'%s\')' % self.root_path

class RequireUbuntuPackagesException(Exception):
    def __init__(self, packages):
        self.packages = packages
    def __str__(self):
        return 'RequireUbuntuPackagesException(packages=%s)' % str(self.packages)

class RequirePythonPackagesException(Exception):
    def __init__(self, package):
        self.package = package
    def __str__(self):
        return 'RequirePythonPackagesException(package=\'%s\')' % self.package

class UidAllocationException(Exception):
    def __init__(self):
        pass
    def __str__(self):
        return 'UidAllocationException(): could not find a free system UID'

class GidAllocationException(Exception):
    def __init__(self):
        pass
    def __str__(self):
        return 'GidAllocationException(): could not find a free system GID'

########NEW FILE########
__FILENAME__ = database
#
# Djangy installer -- MySQL database configuration.
#
# Authors: Sameer Sundresh <sameer@sundresh.org>
#          Dave Paola <dpaola2@gmail.com>
#

import os.path
import config
from core import *

_PYTHON = '/srv/djangy/run/python-virtual/bin/python'

def require_database():
    if config.MASTER_NODE:
        _configure_mysql_server()
    else:
        run_ignore_failure('service', 'mysql', 'stop')
    if config.MASTER_NODE:
        _create_databases(config.MASTER_DATABASES)
    _syncdb_and_migrate()
    if config.ACTION == 'install' and config.MASTER_NODE:
        _load_admins()
        _load_docs()
    if config.MASTER_NODE:
        _load_chargables()
        _load_subscription_types()
        if len(config.WORKERHOSTS) > 0:
            _load_workerhosts()

@print_when_used
def _configure_mysql_server():
    try:
        require_file('/etc/mysql/my.cnf', 'root', 'root', 0644, contents=read_file('conf/mysql/my.cnf.new'))
    except:
        require_file('/etc/mysql/my.cnf', 'root', 'root', 0644, contents=read_file('conf/mysql/my.cnf.orig'))
        require_file('/etc/mysql/my.cnf', 'root', 'root', 0644, contents=read_file('conf/mysql/my.cnf.new'), overwrite=True)
        run('service', 'mysql', 'restart')

@print_when_used
def _create_databases(databases):
    for user, password, db in databases:
        cmd1 = 'CREATE DATABASE IF NOT EXISTS %s;' % db
        cmd2 = 'GRANT ALL ON %s.* TO %s@\'%%\' IDENTIFIED BY \'%s\';' % (db, user, password)
        run_with_stdin(['mysql', '-u', 'root', '-p%s' % config.DB_ROOT_PASSWORD], stdin=cmd1+cmd2)

def _syncdb_and_migrate():
    if config.WORKER_NODE:
        _syncdb('/srv/djangy/src/server/worker/worker_manager/orm')
        if config.TO_SOUTH:
            _migrate('/srv/djangy/src/server/worker/worker_manager/orm', 'orm', '0001', '--fake')
        _migrate('/srv/djangy/src/server/worker/worker_manager/orm', 'orm')

    if config.MASTER_NODE:
        _syncdb('/srv/djangy/src/server/master/web_ui/application/web_ui')
        _syncdb('/srv/djangy/src/server/master/web_api/application/web_api')
        _syncdb('/srv/djangy/src/server/master/management_database/management_database')

    if config.MASTER_NODE:
        _migrate('/srv/djangy/src/server/master/management_database/management_database', 'management_database')
        _migrate('/srv/djangy/src/server/master/web_ui/application/web_ui',               'main')
        _migrate('/srv/djangy/src/server/master/web_ui/application/web_ui',               'docs')
        _migrate('/srv/djangy/src/server/master/web_ui/application/web_ui',               'management_database', 'zero')

@print_when_used
def _syncdb(dir_path):
    with cd(dir_path):
        run(_PYTHON, 'manage.py', 'syncdb', '--noinput')
    print 'Done.'

@print_when_used
def _migrate(dir_path, application_name, *args):
    with cd(dir_path):
        command = [_PYTHON, 'manage.py', 'migrate', application_name] + list(args)
        run(*command)
    print 'Done.'

@print_when_used
def _load_admins():
    with cd('/srv/djangy/src/server/master/management_database/management_database'):
        run(_PYTHON, 'manage.py', 'loaddata', 'loadadmins.yaml')
    print 'Done.'

@print_when_used
def _load_chargables():
    with cd('/srv/djangy/src/server/master/management_database/management_database'):
        run(_PYTHON, 'manage.py', 'loaddata', 'loadchargables.yaml')
    print 'Done.'

@print_when_used
def _load_subscription_types():
    with cd('/srv/djangy/src/server/master/management_database/management_database'):
        run(_PYTHON, 'manage.py', 'loaddata', 'loadsubscriptiontypes.yaml')
    print 'Done.'

@print_when_used
def _load_docs():
    with cd('/srv/djangy/src/server/master/web_ui/application/web_ui'):
        run(_PYTHON, 'manage.py', 'loaddata', 'docs/wiki_docs.yaml')
    print 'Done.'

@in_tempdir
@print_when_used
def _load_workerhosts():
    file = open('load_workerhosts.yaml', 'w')
    pk = 1
    for workerhost in config.WORKERHOSTS:
        file.write('- model: management_database.WorkerHost\n')
        file.write('  pk: %i\n' % pk)
        file.write('  fields:\n')
        file.write('    host: %s\n' % workerhost)
        file.write('    max_procs: 100\n\n')
        pk = pk+1
    file.close()
    yaml_path = os.path.abspath('load_workerhosts.yaml')
    with cd('/srv/djangy/src/server/master/management_database/management_database'):
        run(_PYTHON, 'manage.py', 'loaddata', yaml_path)
    print 'Done.'

########NEW FILE########
__FILENAME__ = dump_archive
#!/usr/bin/env python
#
# Dump an archive of a master node.  This Python file is self-contained, so
# you can copy it onto a machine without having to pull the whole git
# repository.
#
# Usage: dump_archive.py
# Creates an archive file called djangy_dump_YYYY-MM-DD_hh-mm-ss.fff.tar.gz
# in the current directory.
#
# Author: Sameer Sundresh <sameer@sundresh.org>
#

import os, os.path, re, shutil, subprocess, sys, tempfile, time

# This is the MySQL root password on the old master node whose state you're
# archiving, which might not be the same as the latest root password.
_MYSQL_ROOT_PASSWORD = 'password goes here'

def main():
    return dump_archive(os.path.abspath('.'))

################################################################################
# Decorators copied from core.py so that dump_archive.py is self-contained.

# Decorator to print out a status message boxing the output of a function. 
# Useful for long running functions or those that print output.
def print_when_used(func):
    def _line(char):
        return ''.join([char for i in range(0, 80/len(char))])
    def print_when_used(*args):
        print _line('=')
        print func.__name__ + str(args)
        print _line('- ')
        try:
            return func(*args)
        finally:
            print _line('-')
    return print_when_used

# Decorator to run a function in a temporary directory, and then delete the
# temporary directory when the function returns (or throws an exception).
def in_tempdir(func):
    def in_tempdir(*args, **kwargs):
        tempdir = tempfile.mkdtemp(prefix='djangy_install_')
        assert tempdir.startswith('/tmp/djangy_install_')
        old_dir = os.getcwd()
        try:
            os.chdir(tempdir)
            return func(*args, **kwargs)
        finally:
            os.chdir(old_dir)
            shutil.rmtree(tempdir)
    return in_tempdir

################################################################################

# Creates a timestamp of the form:
#   YYYY-MM-DD_hh-mm-ss.fff
def make_text_timestamp(numeric_time=None):
    if numeric_time == None:
        numeric_time = time.time()
    time_struct = time.gmtime(numeric_time)
    fractional_seconds = int((numeric_time % 1) * 1000)
    return '%04i-%02i-%02i_%02i-%02i-%02i.%03i' \
        % (time_struct.tm_year, time_struct.tm_mon, time_struct.tm_mday, \
           time_struct.tm_hour, time_struct.tm_min, time_struct.tm_sec, \
           fractional_seconds)

@in_tempdir
def dump_archive(dest_dir_path):
    dump_name = 'djangy_dump_%s' % make_text_timestamp()
    dest_file_path = os.path.join(dest_dir_path, '%s.tar.gz' % dump_name)
    # Create contents for archive
    os.mkdir(dump_name)
    create_mysql_dump(os.path.join(dump_name, 'all-databases.mysqldump'))
    create_archive(os.path.join(dump_name, 'git-repositories.tar.gz'), '/srv/git')
    # Create archive
    create_archive(dest_file_path, dump_name)
    return dest_file_path

@print_when_used
def create_mysql_dump(mysql_dump_file_path):
    # The MySQL dump could be pretty big, so it's easier to just use the
    # shell to redirect output.
    assert 0 == subprocess.call(['mysqldump -u root -p%s --all-databases > %s' % (_MYSQL_ROOT_PASSWORD, mysql_dump_file_path)], shell=True)
    print 'Done.'

@print_when_used
def create_archive(dest_tar_file_path, src_path):
    assert 0 == subprocess.call(['tar', '-czf', dest_tar_file_path, src_path])
    print 'Done.'


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = git_serve
#
# Djangy installer -- configure the git server.
#
# Author: Sameer Sundresh <sameer@sundresh.org>
#

import os, os.path, subprocess
from core import *

_POST_RECEIVE_HOOK_PATH='/srv/djangy/run/python-virtual/bin/post_receive.py'

@print_when_used
def require_no_git_serve():
    require_remove('/srv/git/.ssh')

@print_when_used
def require_git_serve():
    # Update system-wide post-receive hook template
    require_link('/usr/share/git-core/templates/hooks/post-receive', _POST_RECEIVE_HOOK_PATH)
    # Update post-receive hooks in all repositories
    for repo_name in os.listdir('/srv/git/repositories'):
        repo_post_receive = os.path.join('/srv/git/repositories', repo_name, 'hooks/post-receive')
        require_link(repo_post_receive, _POST_RECEIVE_HOOK_PATH)
    # Ownership permissions
    require_recursive('/srv/git', username='git', groupname='git')

########NEW FILE########
__FILENAME__ = install
#!/usr/bin/env python
#
# Djangy installer.  See core.py for the basic definitions of the
# declarative installer DSL used here.
#
# Author: Sameer Sundresh <sameer@sundresh.org>
#
import os, sys
import config
from core import *
from apache import *
from application_uids_gids import *
from git_serve import *
from nginx import *
from database import *

def equals_single_arg(arg):
    return arg.split('=', 1)[1]

def equals_multiple_args(arg):
    return arg.split('=', 1)[1].split(',')

# Command-line arguments
if len(sys.argv) >= 2:
    if (sys.argv[1] == 'install' or sys.argv[1] == 'upgrade'):
        config.ACTION = sys.argv[1]
    config.MASTER_NODE     = 'master'     in sys.argv[2:]
    config.WORKER_NODE     = 'worker'     in sys.argv[2:]
    config.PROXYCACHE_NODE = 'proxycache' in sys.argv[2:]
    for arg in sys.argv[2:]:
        if arg.startswith('--master-manager-host='):
            config.MASTER_MANAGER_HOST = equals_single_arg(arg)
        if arg.startswith('--default-database-host='):
            config.DEFAULT_DATABASE_HOST = equals_single_arg(arg)
        if arg.startswith('--default-proxycache-host='):
            config.DEFAULT_PROXYCACHE_HOST = equals_single_arg(arg)
        if arg.startswith('--to-south'):
            config.TO_SOUTH = True
        if arg.startswith('--workerhosts='):
            if config.ACTION != 'install':
                print '"--workerhosts=" argument is only valid for action "install"'
                sys.exit(1)
            config.WORKERHOSTS.extend(equals_multiple_args(arg))
        if arg.startswith('--production'):
            config.PRODUCTION = True
            config.DEVPAYMENTS_API_KEY = config.DEVPAYMENTS_PRODUCTION
if not config.ACTION or not config.MASTER_MANAGER_HOST or not config.DEFAULT_DATABASE_HOST or not config.DEFAULT_PROXYCACHE_HOST:
    print 'Usage: sudo install.py { install | upgrade } [master] [worker] [proxycache] --master-manager-host=<mh> --default-database-host=<dbh> --default-proxycache-host=<pch> [--workerhosts=<wh1>,<wh2>,...] [--production] [--to-south]'
    sys.exit(1)

# Find the source code
_DJANGY_CODE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Automate setup of mysql
run_with_stdin(['debconf-set-selections'], stdin='mysql-server-5.0 mysql-server/root_password password %s\n' % config.DB_ROOT_PASSWORD)
run_with_stdin(['debconf-set-selections'], stdin='mysql-server-5.0 mysql-server/root_password_again password %s\n' % config.DB_ROOT_PASSWORD)

require_ubuntu_packages('apache2', 'apache2-dev', 'build-essential', 'bzr',
    'cron', 'gcc', 'git-core', 'joe', 'libapache2-mod-wsgi',
    'libfreetype6-dev', 'libjpeg-dev', 'libyaml-dev', 'mercurial',
    'mysql-server', 'openssh-server', 'python', 'python-dev',
    'python-mysqldb', 'python-setuptools', 'python-sqlite', 'python-xapian',
    'python-yaml', 'rsync', 'sqlite3', 'subversion', 'vim')

require_python_packages('Django==1.2.1', 'Fabric==0.9.1', 'Mako==0.3.4',
    'PIL==1.1.7', 'South==0.7.2', 'django-sentry==1.0.9',
    'gunicorn==0.11.1', 'simplejson==2.1.1', 'virtualenv==1.4.9')

require_user('root', uid=0, gid=0, homedir='/root', create=False)
require_directory('/root', 'root', 'root', 0700)
require_directory('/root/.ssh', 'root', 'root', 0700)
require_file('/root/.ssh/id_rsa',          'root', 'root', 0600, contents=read_file('conf/ssh_keys/root_key'),     overwrite=True)
require_file('/root/.ssh/id_rsa.pub',      'root', 'root', 0600, contents=read_file('conf/ssh_keys/root_key.pub'), overwrite=True)
require_file('/root/.ssh/authorized_keys', 'root', 'root', 0600, contents=read_file('conf/ssh_keys/root_key.pub'), overwrite=True)
require_file('/root/.ssh/config',          'root', 'root', 0600, contents=read_file('conf/ssh_keys/ssh_config'),   overwrite=True)
if config.MASTER_NODE and config.PRODUCTION:
    require_file('/etc/ssh/ssh_host_dsa_key',     'root', 'root', 0600, contents=read_file('conf/etc_ssh/ssh_host_dsa_key'),     overwrite=True)
    require_file('/etc/ssh/ssh_host_dsa_key.pub', 'root', 'root', 0644, contents=read_file('conf/etc_ssh/ssh_host_dsa_key.pub'), overwrite=True)
    require_file('/etc/ssh/ssh_host_rsa_key',     'root', 'root', 0600, contents=read_file('conf/etc_ssh/ssh_host_rsa_key'),     overwrite=True)
    require_file('/etc/ssh/ssh_host_rsa_key.pub', 'root', 'root', 0644, contents=read_file('conf/etc_ssh/ssh_host_rsa_key.pub'), overwrite=True)
    require_file('/etc/crontab',                  'root', 'root', 0644, contents=read_file('conf/crontab'),                      overwrite=True)
require_group('www-data', create=False)
require_user('www-data', groupname='www-data', homedir='/var/www', create=False)

require_group('git')
require_user('git',        groupname='git',        homedir='/srv/git',                shell='/bin/sh', description='git version control')
require_group('proxycache')
require_user('proxycache', groupname='proxycache', homedir='/srv/proxycache_manager', shell='/bin/sh', description='proxy cache manager')

require_group('shell')
require_user('shell', groupname='shell', homedir='/srv/shell', shell='/bin/sh', description='shell account')
require_directory('/srv/shell',      'shell', 'shell', 0700)
require_directory('/srv/shell/.ssh', 'shell', 'shell', 0700)

require_group('djangy', member_usernames=['www-data', 'git', 'shell'])

if config.PRODUCTION:
    require_directory('/proc', 'root', 'admin', 0550, create=False)

require_directory('/srv',         'root', 'root', 0711)
require_directory('/srv/bundles', 'root', 'root', 0711)
if config.ACTION == 'install':
    assert not os.path.exists('/srv/djangy')
else:
    assert config.ACTION == 'upgrade'
require_remove('/srv/djangy')
require_directory('/srv/djangy',                         'root',       'djangy',     0710, initial_contents_path=_DJANGY_CODE_PATH)
require_file     ('/srv/djangy/src/server/shared/djangy_server_shared/installer_configured_constants.py', 'root', 'djangy', 0644, overwrite=True,
    contents = (('DEFAULT_DATABASE_HOST   = \'%s\'\n' % config.DEFAULT_DATABASE_HOST) +
                ('DEFAULT_PROXYCACHE_HOST = \'%s\'\n' % config.DEFAULT_PROXYCACHE_HOST) +
                ('MASTER_MANAGER_HOST     = \'%s\'\n' % config.MASTER_MANAGER_HOST) + 
                ('DEVPAYMENTS_API_KEY     = \'%s\'\n' % config.DEVPAYMENTS_API_KEY)))
if config.MASTER_NODE:
    require_directory('/srv/git',                        'git',        'git',        0710)
    require_directory('/srv/git/.ssh',                   'git',        'git',        0700)
    require_directory('/srv/git/repositories',           'git',        'git',        0710)

require_directory('/srv/logs',                           'root',       'root',       0711)
if config.MASTER_NODE:
    require_directory('/srv/logs/api.djangy.com',            'root',       'www-data',   0710)
    require_file     ('/srv/logs/api.djangy.com/django.log', 'www-data',   'www-data',   0600, initial_contents='')
    require_directory('/srv/logs/djangy.com',                'root',       'www-data',   0710)
    require_file     ('/srv/logs/djangy.com/django.log',     'www-data',   'www-data',   0600, initial_contents='')
    require_directory('/srv/logs/000-defaults',              'root',       'www-data',   0710)
    require_file     ('/srv/logs/000-defaults/access.log',   'www-data',   'www-data',   0600, initial_contents='')
    require_file     ('/srv/logs/000-defaults/error.log',    'www-data',   'www-data',   0600, initial_contents='')
    require_file     ('/srv/logs/master_api.log',            'www-data',   'www-data',   0600, initial_contents='')

if config.PROXYCACHE_NODE:
    if config.ACTION == 'install':
        assert not os.path.exists('/srv/proxycache_manager')
    require_directory('/srv/proxycache_manager',             'proxycache', 'proxycache', 0700)
require_directory('/srv/scratch',                        'root',       'root',       0700)
if config.WORKER_NODE:
    if config.ACTION == 'install':
        assert not os.path.exists('/srv/worker_manager')
    require_directory('/srv/worker_manager',                 'root',       'root',       0700)

@print_when_used
def require_make_djangy():
    with cd('/srv/djangy'):
        run('make', 'clean')
        run('make')

require_application_uids_gids()
require_make_djangy()
require_database()

if config.MASTER_NODE:
    require_git_serve()
else:
    require_no_git_serve()

if config.MASTER_NODE:
    require_apache()
else:
    require_no_apache()

if config.PROXYCACHE_NODE:
    require_nginx()
else:
    require_no_nginx()

# Create an upgrade script in /srv/upgrade
require_file('/srv/upgrade', 'root', 'root', 0700, contents="""#!/bin/bash
./install.py upgrade %(master)s %(worker)s %(proxycache)s \
--master-manager-host=%(master-manager-host)s \
--default-database-host=%(default-database-host)s \
--default-proxycache-host=%(default-proxycache-host)s \
%(production)s\
""" % {
    'master'                 : 'master'     if config.MASTER_NODE     else '',
    'worker'                 : 'worker'     if config.WORKER_NODE     else '',
    'proxycache'             : 'proxycache' if config.PROXYCACHE_NODE else '',
    'master-manager-host'    : config.MASTER_MANAGER_HOST,
    'default-database-host'  : config.DEFAULT_DATABASE_HOST,
    'default-proxycache-host': config.DEFAULT_PROXYCACHE_HOST,
    'production'             : 'production' if config.PRODUCTION      else ''
}, overwrite=True)

# Rebuild bundles and deploy applications...

########NEW FILE########
__FILENAME__ = load_archive
#!/usr/bin/env python
#
# Install a Djangy system dump created by dump_archive.py
# Useful for deploying a new clone of a Djangy server.
#
# Author: Sameer Sundresh <sameer@sundresh.org>
#

import os, os.path, re, subprocess, sys, time
from core import *
import config

def main():
    if len(sys.argv) != 2:
        print 'Usage: load_archive.py djangy_dump_YYYY-MM-DD_hh-mm-ss.fff.tar.gz'
        sys.exit(1)
    src_file_path = os.path.abspath(sys.argv[1])
    assert os.path.isfile(src_file_path)
    assert not os.path.exists('/srv/git')
    load_archive(src_file_path)

@in_tempdir
def load_archive(src_file_path):
    run('tar', '-xzf', src_file_path)
    dir_contents = os.listdir('.')
    assert len(dir_contents) == 1 and os.path.isdir(dir_contents[0])
    os.chdir(dir_contents[0])
    load_mysql_dump(os.path.abspath('all-databases.mysqldump'))
    extract_git_repositories(os.path.abspath('git-repositories.tar.gz'))

@print_when_used
def load_mysql_dump(mysql_dump_file_path):
    run_with_stdin( ['mysql', '-u', 'root', '-p%s'      % config.DB_ROOT_PASSWORD],           stdin='DROP DATABASE djangy;')
    subprocess.call(['mysql    -u    root    -p%s < %s' % (config.DB_ROOT_PASSWORD, mysql_dump_file_path)], shell=True)
    run_with_stdin( ['mysql', '-u', 'root', '-p%s'      % config.DB_ROOT_PASSWORD, 'djangy'], stdin='DELETE FROM process; FLUSH PRIVILEGES;')
    print 'Done.'

@print_when_used
def extract_git_repositories(git_repositories_tar_file_path):
    git_repositories_tar_file_path = os.path.abspath(git_repositories_tar_file_path)
    os.chdir('/')
    run('tar', '-xzf', git_repositories_tar_file_path, 'srv/git')
    print 'Done.'

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = nginx
#
# Djangy installer -- nginx front-end web server.
#
# Configure the front-end nginx proxy/caching server, if this is a front-end
# node.  A single nginx front-end node can proxy to applications running on
# multiple middle-tier application nodes.
#
# Author: Sameer Sundresh <sameer@sundresh.org>
#

import os, os.path
from core import *

_NGINX_VERSION = 'nginx-0.8.52'
_NGINX_INSTALL_PATH = os.path.join('/srv/proxycache_manager', _NGINX_VERSION)
_NGINX_BIN_PATH = '/srv/proxycache_manager/nginx/sbin/nginx'

def require_no_nginx():
    if os.path.isfile(_NGINX_BIN_PATH):
        run_ignore_failure(_NGINX_BIN_PATH, '-s', 'quit')

def require_nginx():
    require_group('proxycache')
    require_user('proxycache', groupname='proxycache', homedir='/srv/proxycache_manager', shell='/bin/sh', description='proxy cache manager')
    require_directory('/srv/proxycache_manager', 'proxycache', 'proxycache', 0700)
    require_install_nginx()
    require_configure_nginx()
    start_nginx()

def require_install_nginx():
    if not os.path.exists(_NGINX_INSTALL_PATH):
        _install_nginx()

@in_tempdir
@print_when_used
def _install_nginx():
    # Cache this file locally?
    run('wget', 'http://sysoev.ru/nginx/%s.tar.gz' % _NGINX_VERSION)
    run('tar', '-xzf', '%s.tar.gz' % _NGINX_VERSION)
    os.chdir(_NGINX_VERSION)
    run('./configure', '--prefix=%s' % _NGINX_INSTALL_PATH)
    run('make')
    require_directory(_NGINX_INSTALL_PATH, 'proxycache', 'proxycache', 0700)
    run('make', 'install')

def require_configure_nginx():
    require_remove(os.path.join(_NGINX_INSTALL_PATH, 'conf/nginx.conf.default'))
    require_directory(_NGINX_INSTALL_PATH, 'proxycache', 'proxycache', 0700)
    require_directory(os.path.join(_NGINX_INSTALL_PATH, 'conf/applications'), 'proxycache', 'proxycache', 0700)
    require_directory(os.path.join(_NGINX_INSTALL_PATH, 'cache'), 'proxycache', 'proxycache', 0700)
    require_file(os.path.join(_NGINX_INSTALL_PATH, 'conf/nginx.conf'), 'proxycache', 'proxycache', 0600, contents=read_file('conf/proxycache_manager/nginx.conf'), overwrite=True)
    require_link('/srv/proxycache_manager/nginx', _NGINX_INSTALL_PATH)
    require_recursive(_NGINX_INSTALL_PATH, username='proxycache', groupname='proxycache')
    require_file('/etc/rc.local', 'root', 'root', 0700, contents=read_file('conf/rc.local'), overwrite=True)
    require_file('/srv/proxycache_manager/502.html', 'proxycache', 'proxycache', 0400, contents=read_file('conf/proxycache_manager/502.html'), overwrite=True)

@print_when_used
def start_nginx():
    print "Stopping old nginx..."
    run_ignore_failure(_NGINX_BIN_PATH, '-s', 'quit')
    print "Starting new nginx..."
    run(_NGINX_BIN_PATH)


#    chmod -R g-rwx,o-rwx $PROXYCACHE_MANAGER_PATH

########NEW FILE########
__FILENAME__ = S3
#!/usr/bin/env python

#  This software code is made available "AS IS" without warranties of any
#  kind.  You may copy, display, modify and redistribute the software
#  code either by itself or as incorporated into your code; provided that
#  you do not remove any proprietary notices.  Your use of this software
#  code is at your own risk and you waive any claim against Amazon
#  Digital Services, Inc. or its affiliates with respect to your use of
#  this software code. (c) 2006-2007 Amazon Digital Services, Inc. or its
#  affiliates.

import base64
import hmac
import httplib
import re
import sha
import sys
import time
import urllib
import urlparse
import xml.sax

DEFAULT_HOST = 's3.amazonaws.com'
PORTS_BY_SECURITY = { True: 443, False: 80 }
METADATA_PREFIX = 'x-amz-meta-'
AMAZON_HEADER_PREFIX = 'x-amz-'

# generates the aws canonical string for the given parameters
def canonical_string(method, bucket="", key="", query_args={}, headers={}, expires=None):
    interesting_headers = {}
    for header_key in headers:
        lk = header_key.lower()
        if lk in ['content-md5', 'content-type', 'date'] or lk.startswith(AMAZON_HEADER_PREFIX):
            interesting_headers[lk] = headers[header_key].strip()

    # these keys get empty strings if they don't exist
    if not interesting_headers.has_key('content-type'):
        interesting_headers['content-type'] = ''
    if not interesting_headers.has_key('content-md5'):
        interesting_headers['content-md5'] = ''

    # just in case someone used this.  it's not necessary in this lib.
    if interesting_headers.has_key('x-amz-date'):
        interesting_headers['date'] = ''

    # if you're using expires for query string auth, then it trumps date
    # (and x-amz-date)
    if expires:
        interesting_headers['date'] = str(expires)

    sorted_header_keys = interesting_headers.keys()
    sorted_header_keys.sort()

    buf = "%s\n" % method
    for header_key in sorted_header_keys:
        if header_key.startswith(AMAZON_HEADER_PREFIX):
            buf += "%s:%s\n" % (header_key, interesting_headers[header_key])
        else:
            buf += "%s\n" % interesting_headers[header_key]

    # append the bucket if it exists
    if bucket != "":
        buf += "/%s" % bucket

    # add the key.  even if it doesn't exist, add the slash
    buf += "/%s" % urllib.quote_plus(key)

    # handle special query string arguments

    if query_args.has_key("acl"):
        buf += "?acl"
    elif query_args.has_key("torrent"):
        buf += "?torrent"
    elif query_args.has_key("logging"):
        buf += "?logging"
    elif query_args.has_key("location"):
        buf += "?location"

    return buf

# computes the base64'ed hmac-sha hash of the canonical string and the secret
# access key, optionally urlencoding the result
def encode(aws_secret_access_key, str, urlencode=False):
    b64_hmac = base64.encodestring(hmac.new(aws_secret_access_key, str, sha).digest()).strip()
    if urlencode:
        return urllib.quote_plus(b64_hmac)
    else:
        return b64_hmac

def merge_meta(headers, metadata):
    final_headers = headers.copy()
    for k in metadata.keys():
        final_headers[METADATA_PREFIX + k] = metadata[k]

    return final_headers

# builds the query arg string
def query_args_hash_to_string(query_args):
    query_string = ""
    pairs = []
    for k, v in query_args.items():
        piece = k
        if v != None:
            piece += "=%s" % urllib.quote_plus(str(v))
        pairs.append(piece)

    return '&'.join(pairs)


class CallingFormat:
    PATH = 1
    SUBDOMAIN = 2
    VANITY = 3

    def build_url_base(protocol, server, port, bucket, calling_format):
        url_base = '%s://' % protocol

        if bucket == '':
            url_base += server
        elif calling_format == CallingFormat.SUBDOMAIN:
            url_base += "%s.%s" % (bucket, server)
        elif calling_format == CallingFormat.VANITY:
            url_base += bucket
        else:
            url_base += server

        url_base += ":%s" % port

        if (bucket != '') and (calling_format == CallingFormat.PATH):
            url_base += "/%s" % bucket

        return url_base

    build_url_base = staticmethod(build_url_base)



class Location:
    DEFAULT = None
    EU = 'EU'



class AWSAuthConnection:
    def __init__(self, aws_access_key_id, aws_secret_access_key, is_secure=True,
            server=DEFAULT_HOST, port=None, calling_format=CallingFormat.SUBDOMAIN):

        if not port:
            port = PORTS_BY_SECURITY[is_secure]

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.is_secure = is_secure
        self.server = server
        self.port = port
        self.calling_format = calling_format

    def create_bucket(self, bucket, headers={}):
        return Response(self._make_request('PUT', bucket, '', {}, headers))

    def create_located_bucket(self, bucket, location=Location.DEFAULT, headers={}):
        if location == Location.DEFAULT:
            body = ""
        else:
            body = "<CreateBucketConstraint><LocationConstraint>" + \
                   location + \
                   "</LocationConstraint></CreateBucketConstraint>"
        return Response(self._make_request('PUT', bucket, '', {}, headers, body))

    def check_bucket_exists(self, bucket):
        return self._make_request('HEAD', bucket, '', {}, {})

    def list_bucket(self, bucket, options={}, headers={}):
        return ListBucketResponse(self._make_request('GET', bucket, '', options, headers))

    def delete_bucket(self, bucket, headers={}):
        return Response(self._make_request('DELETE', bucket, '', {}, headers))

    def put(self, bucket, key, object, headers={}):
        if not isinstance(object, S3Object):
            object = S3Object(object)

        return Response(
                self._make_request(
                    'PUT',
                    bucket,
                    key,
                    {},
                    headers,
                    object.data,
                    object.metadata))

    def get(self, bucket, key, headers={}):
        return GetResponse(
                self._make_request('GET', bucket, key, {}, headers))

    def delete(self, bucket, key, headers={}):
        return Response(
                self._make_request('DELETE', bucket, key, {}, headers))

    def get_bucket_logging(self, bucket, headers={}):
        return GetResponse(self._make_request('GET', bucket, '', { 'logging': None }, headers))

    def put_bucket_logging(self, bucket, logging_xml_doc, headers={}):
        return Response(self._make_request('PUT', bucket, '', { 'logging': None }, headers, logging_xml_doc))

    def get_bucket_acl(self, bucket, headers={}):
        return self.get_acl(bucket, '', headers)

    def get_acl(self, bucket, key, headers={}):
        return GetResponse(
                self._make_request('GET', bucket, key, { 'acl': None }, headers))

    def put_bucket_acl(self, bucket, acl_xml_document, headers={}):
        return self.put_acl(bucket, '', acl_xml_document, headers)

    def put_acl(self, bucket, key, acl_xml_document, headers={}):
        return Response(
                self._make_request(
                    'PUT',
                    bucket,
                    key,
                    { 'acl': None },
                    headers,
                    acl_xml_document))

    def list_all_my_buckets(self, headers={}):
        return ListAllMyBucketsResponse(self._make_request('GET', '', '', {}, headers))

    def get_bucket_location(self, bucket):
        return LocationResponse(self._make_request('GET', bucket, '', {'location' : None}))

    # end public methods

    def _make_request(self, method, bucket='', key='', query_args={}, headers={}, data='', metadata={}):

        server = ''
        if bucket == '':
            server = self.server
        elif self.calling_format == CallingFormat.SUBDOMAIN:
            server = "%s.%s" % (bucket, self.server)
        elif self.calling_format == CallingFormat.VANITY:
            server = bucket
        else:
            server = self.server

        path = ''

        if (bucket != '') and (self.calling_format == CallingFormat.PATH):
            path += "/%s" % bucket

        # add the slash after the bucket regardless
        # the key will be appended if it is non-empty
        path += "/%s" % urllib.quote_plus(key)


        # build the path_argument string
        # add the ? in all cases since 
        # signature and credentials follow path args
        if len(query_args):
            path += "?" + query_args_hash_to_string(query_args)

        is_secure = self.is_secure
        host = "%s:%d" % (server, self.port)
        while True:
            if (is_secure):
                connection = httplib.HTTPSConnection(host)
            else:
                connection = httplib.HTTPConnection(host)

            final_headers = merge_meta(headers, metadata);
            # add auth header
            self._add_aws_auth_header(final_headers, method, bucket, key, query_args)

            connection.request(method, path, data, final_headers)
            resp = connection.getresponse()
            if resp.status < 300 or resp.status >= 400:
                return resp
            # handle redirect
            location = resp.getheader('location')
            if not location:
                return resp
            # (close connection)
            resp.read()
            scheme, host, path, params, query, fragment \
                    = urlparse.urlparse(location)
            if scheme == "http":    is_secure = True
            elif scheme == "https": is_secure = False
            else: raise invalidURL("Not http/https: " + location)
            if query: path += "?" + query
            # retry with redirect

    def _add_aws_auth_header(self, headers, method, bucket, key, query_args):
        if not headers.has_key('Date'):
            headers['Date'] = time.strftime("%a, %d %b %Y %X GMT", time.gmtime())

        c_string = canonical_string(method, bucket, key, query_args, headers)
        headers['Authorization'] = \
            "AWS %s:%s" % (self.aws_access_key_id, encode(self.aws_secret_access_key, c_string))


class QueryStringAuthGenerator:
    # by default, expire in 1 minute
    DEFAULT_EXPIRES_IN = 60

    def __init__(self, aws_access_key_id, aws_secret_access_key, is_secure=True,
                 server=DEFAULT_HOST, port=None, calling_format=CallingFormat.SUBDOMAIN):

        if not port:
            port = PORTS_BY_SECURITY[is_secure]

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        if (is_secure):
            self.protocol = 'https'
        else:
            self.protocol = 'http'

        self.is_secure = is_secure
        self.server = server
        self.port = port
        self.calling_format = calling_format
        self.__expires_in = QueryStringAuthGenerator.DEFAULT_EXPIRES_IN
        self.__expires = None

        # for backwards compatibility with older versions
        self.server_name = "%s:%s" % (self.server, self.port)

    def set_expires_in(self, expires_in):
        self.__expires_in = expires_in
        self.__expires = None

    def set_expires(self, expires):
        self.__expires = expires
        self.__expires_in = None

    def create_bucket(self, bucket, headers={}):
        return self.generate_url('PUT', bucket, '', {}, headers)

    def list_bucket(self, bucket, options={}, headers={}):
        return self.generate_url('GET', bucket, '', options, headers)

    def delete_bucket(self, bucket, headers={}):
        return self.generate_url('DELETE', bucket, '', {}, headers)

    def put(self, bucket, key, object, headers={}):
        if not isinstance(object, S3Object):
            object = S3Object(object)

        return self.generate_url(
                'PUT',
                bucket,
                key,
                {},
                merge_meta(headers, object.metadata))

    def get(self, bucket, key, headers={}):
        return self.generate_url('GET', bucket, key, {}, headers)

    def delete(self, bucket, key, headers={}):
        return self.generate_url('DELETE', bucket, key, {}, headers)

    def get_bucket_logging(self, bucket, headers={}):
        return self.generate_url('GET', bucket, '', { 'logging': None }, headers)

    def put_bucket_logging(self, bucket, logging_xml_doc, headers={}):
        return self.generate_url('PUT', bucket, '', { 'logging': None }, headers)

    def get_bucket_acl(self, bucket, headers={}):
        return self.get_acl(bucket, '', headers)

    def get_acl(self, bucket, key='', headers={}):
        return self.generate_url('GET', bucket, key, { 'acl': None }, headers)

    def put_bucket_acl(self, bucket, acl_xml_document, headers={}):
        return self.put_acl(bucket, '', acl_xml_document, headers)

    # don't really care what the doc is here.
    def put_acl(self, bucket, key, acl_xml_document, headers={}):
        return self.generate_url('PUT', bucket, key, { 'acl': None }, headers)

    def list_all_my_buckets(self, headers={}):
        return self.generate_url('GET', '', '', {}, headers)

    def make_bare_url(self, bucket, key=''):
        full_url = self.generate_url(self, bucket, key)
        return full_url[:full_url.index('?')]

    def generate_url(self, method, bucket='', key='', query_args={}, headers={}):
        expires = 0
        if self.__expires_in != None:
            expires = int(time.time() + self.__expires_in)
        elif self.__expires != None:
            expires = int(self.__expires)
        else:
            raise "Invalid expires state"

        canonical_str = canonical_string(method, bucket, key, query_args, headers, expires)
        encoded_canonical = encode(self.aws_secret_access_key, canonical_str)

        url = CallingFormat.build_url_base(self.protocol, self.server, self.port, bucket, self.calling_format)

        url += "/%s" % urllib.quote_plus(key)

        query_args['Signature'] = encoded_canonical
        query_args['Expires'] = expires
        query_args['AWSAccessKeyId'] = self.aws_access_key_id

        url += "?%s" % query_args_hash_to_string(query_args)

        return url


class S3Object:
    def __init__(self, data, metadata={}):
        self.data = data
        self.metadata = metadata

class Owner:
    def __init__(self, id='', display_name=''):
        self.id = id
        self.display_name = display_name

class ListEntry:
    def __init__(self, key='', last_modified=None, etag='', size=0, storage_class='', owner=None):
        self.key = key
        self.last_modified = last_modified
        self.etag = etag
        self.size = size
        self.storage_class = storage_class
        self.owner = owner

class CommonPrefixEntry:
    def __init(self, prefix=''):
        self.prefix = prefix

class Bucket:
    def __init__(self, name='', creation_date=''):
        self.name = name
        self.creation_date = creation_date

class Response:
    def __init__(self, http_response):
        self.http_response = http_response
        # you have to do this read, even if you don't expect a body.
        # otherwise, the next request fails.
        self.body = http_response.read()
        if http_response.status >= 300 and self.body:
            self.message = self.body
        else:
            self.message = "%03d %s" % (http_response.status, http_response.reason)



class ListBucketResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        if http_response.status < 300:
            handler = ListBucketHandler()
            xml.sax.parseString(self.body, handler)
            self.entries = handler.entries
            self.common_prefixes = handler.common_prefixes
            self.name = handler.name
            self.marker = handler.marker
            self.prefix = handler.prefix
            self.is_truncated = handler.is_truncated
            self.delimiter = handler.delimiter
            self.max_keys = handler.max_keys
            self.next_marker = handler.next_marker
        else:
            self.entries = []

class ListAllMyBucketsResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        if http_response.status < 300: 
            handler = ListAllMyBucketsHandler()
            xml.sax.parseString(self.body, handler)
            self.entries = handler.entries
        else:
            self.entries = []

class GetResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        response_headers = http_response.msg   # older pythons don't have getheaders
        metadata = self.get_aws_metadata(response_headers)
        self.object = S3Object(self.body, metadata)

    def get_aws_metadata(self, headers):
        metadata = {}
        for hkey in headers.keys():
            if hkey.lower().startswith(METADATA_PREFIX):
                metadata[hkey[len(METADATA_PREFIX):]] = headers[hkey]
                del headers[hkey]

        return metadata

class LocationResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        if http_response.status < 300: 
            handler = LocationHandler()
            xml.sax.parseString(self.body, handler)
            self.location = handler.location

class ListBucketHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.entries = []
        self.curr_entry = None
        self.curr_text = ''
        self.common_prefixes = []
        self.curr_common_prefix = None
        self.name = ''
        self.marker = ''
        self.prefix = ''
        self.is_truncated = False
        self.delimiter = ''
        self.max_keys = 0
        self.next_marker = ''
        self.is_echoed_prefix_set = False

    def startElement(self, name, attrs):
        if name == 'Contents':
            self.curr_entry = ListEntry()
        elif name == 'Owner':
            self.curr_entry.owner = Owner()
        elif name == 'CommonPrefixes':
            self.curr_common_prefix = CommonPrefixEntry()


    def endElement(self, name):
        if name == 'Contents':
            self.entries.append(self.curr_entry)
        elif name == 'CommonPrefixes':
            self.common_prefixes.append(self.curr_common_prefix)
        elif name == 'Key':
            self.curr_entry.key = self.curr_text
        elif name == 'LastModified':
            self.curr_entry.last_modified = self.curr_text
        elif name == 'ETag':
            self.curr_entry.etag = self.curr_text
        elif name == 'Size':
            self.curr_entry.size = int(self.curr_text)
        elif name == 'ID':
            self.curr_entry.owner.id = self.curr_text
        elif name == 'DisplayName':
            self.curr_entry.owner.display_name = self.curr_text
        elif name == 'StorageClass':
            self.curr_entry.storage_class = self.curr_text
        elif name == 'Name':
            self.name = self.curr_text
        elif name == 'Prefix' and self.is_echoed_prefix_set:
            self.curr_common_prefix.prefix = self.curr_text
        elif name == 'Prefix':
            self.prefix = self.curr_text
            self.is_echoed_prefix_set = True
        elif name == 'Marker':
            self.marker = self.curr_text
        elif name == 'IsTruncated':
            self.is_truncated = self.curr_text == 'true'
        elif name == 'Delimiter':
            self.delimiter = self.curr_text
        elif name == 'MaxKeys':
            self.max_keys = int(self.curr_text)
        elif name == 'NextMarker':
            self.next_marker = self.curr_text

        self.curr_text = ''

    def characters(self, content):
        self.curr_text += content


class ListAllMyBucketsHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.entries = []
        self.curr_entry = None
        self.curr_text = ''

    def startElement(self, name, attrs):
        if name == 'Bucket':
            self.curr_entry = Bucket()

    def endElement(self, name):
        if name == 'Name':
            self.curr_entry.name = self.curr_text
        elif name == 'CreationDate':
            self.curr_entry.creation_date = self.curr_text
        elif name == 'Bucket':
            self.entries.append(self.curr_entry)

    def characters(self, content):
        self.curr_text = content


class LocationHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.location = None
        self.state = 'init'

    def startElement(self, name, attrs):
        if self.state == 'init':
            if name == 'LocationConstraint':
                self.state = 'tag_location'
                self.location = ''
            else: self.state = 'bad'
        else: self.state = 'bad'

    def endElement(self, name):
        if self.state == 'tag_location' and name == 'LocationConstraint':
            self.state = 'done'
        else: self.state = 'bad'

    def characters(self, content):
        if self.state == 'tag_location':
            self.location += content

########NEW FILE########
__FILENAME__ = s3get
#! /usr/bin/env python
#
# Download a file from the backups Amazon S3 bucket.
#
# Author: Dave Paola <dpaola2@gmail.com>
#

import S3, sys, config, os

def retrieve(filename):
    conn = S3.AWSAuthConnection(config.S3_ACCESS_KEY, config.S3_SECRET)
    assert 200 == conn.check_bucket_exists(config.S3_BUCKET).status

    result = conn.get(config.S3_BUCKET, filename)
    assert 200 == result.http_response.status

    f = open(filename, "w")
    f.write(result.object.data)
    f.close()

    print "File %s successfully retrieved (with same filename)." % filename

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Usage: s3get.py <archive>"
        sys.exit(1)
    filename = sys.argv[1]
    retrieve(filename)

########NEW FILE########
__FILENAME__ = s3list
#! /usr/bin/env python
#
# List the files contained in the backups Amazon S3 bucket.
#
# Author: Dave Paola <dpaola2@gmail.com>
#

import S3, sys, config, os

def list_files():
    conn = S3.AWSAuthConnection(config.S3_ACCESS_KEY, config.S3_SECRET)
    result = conn.check_bucket_exists(config.S3_BUCKET)
    if result.status != 200:
        result = conn.create_located_bucket(config.S3_BUCKET, S3.Location.DEFAULT)

    result = conn.list_bucket(config.S3_BUCKET)
    assert 200 == result.http_response.status
    print "Size\t\tKey"
    for entry in result.entries:
        print "%s\t%s" % (entry.size, entry.key)

if __name__ == '__main__':
    list_files()

########NEW FILE########
__FILENAME__ = s3put
#! /usr/bin/env python
#
# Upload a file to the backups Amazon S3 bucket.
#
# Author: Dave Paola <dpaola2@gmail.com>
#

import S3, sys, config, os
from core import read_file

def upload(filename):
    conn = S3.AWSAuthConnection(config.S3_ACCESS_KEY, config.S3_SECRET)
    result = conn.check_bucket_exists(config.S3_BUCKET)
    if result.status != 200:
        result = conn.create_located_bucket(config.S3_BUCKET, S3.Location.DEFAULT)

    assert 200 == conn.put(config.S3_BUCKET, os.path.basename(filename), read_file(filename)).http_response.status

    print "File %s successfully backed up to S3 (with same filename)." % filename

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Usage: s3put.py <archive>"
        sys.exit(1)
    filename = sys.argv[1]
    upload(filename)

########NEW FILE########
__FILENAME__ = report_billing
#! /srv/djangy/run/python-virtual/bin/python
#
# Report usage information to the billing agent.
#
# Author: Dave Paola <dpaola2@gmail.com>
#

from master_api import report_all_usage
import sys

def main():
    return report_all_usage()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = gen_invite_code
#!/usr/bin/env python
#
# Generate random invitation codes of the form "adjective adjective noun."
# You can customize the adjectives.txt and nouns.txt files to suit your tastes.
#
# Author: Sameer Sundresh <sameer@sundresh.org>
#

import random, sys

n = 1
if len(sys.argv) > 1:
    n = int(sys.argv[1])

def strip_newlines(lines):
    return map(lambda x: x[:-1], lines)

def choose_word(words):
    return words[random.randint(0, len(words)-1)]

adjectives = strip_newlines(open('adjectives.txt').readlines())
nouns      = strip_newlines(open('nouns.txt').readlines())

for i in range(0, n):
    adj1 = choose_word(adjectives)
    adj2 = choose_word(adjectives)
    while adj1[-1] == adj2[-1]:
        adj2 = choose_word(adjectives)
    # For some reason, results looked better to me when the last letter of
    # the first word came alphabetically before the last letter of the
    # second word.  Clearly, this is a superficial proxy for the actual
    # semantic interaction between adjectives.
    if adj1[-1] > adj2[-1]:
        (adj1, adj2) = (adj2, adj1)
    # Zombie usually sounds better as the second adjective than the first.
    if adj1 == 'zombie':
        (adj1, adj2) = (adj2, adj1)
    noun = choose_word(nouns)

    print "%s %s %s" % (adj1, adj2, noun)

########NEW FILE########
__FILENAME__ = djangy
#! /usr/bin/env python

import getpass, os, re, socket, subprocess, sys, urllib, urllib2, xmlrpclib, platform
from hashlib import md5
from pkg_resources import parse_version
from find_git_repository import *
from ConfigParser import RawConfigParser
try:
    import json
except ImportError:
    import simplejson as json

GIT_HOST = 'api.djangy.com'
API_BASE_URL = 'https://api.djangy.com'
VERSION = '0.14'

HOME = None
if platform.system() == 'Windows':
    HOME = os.environ['USERPROFILE']
else:
    HOME = os.environ['HOME']
CONFIG_PATH = os.path.join(HOME, '.djangy')

COMMANDS = [
    'create',
    'logs',
    'manage.py',
]

HELP_MESSAGE = """ Djangy Commands:
                                # NOTE: all commands accept
                                # the [-a app_name] argument:
                                # $ djangy -a myproject create

djangy create                   # create a new djangy application

djangy manage.py <command>      # remotely execute manage.py command
djangy manage.py syncdb
djangy manage.py migrate
djangy manage.py shell

djangy logs                     # display recent log output (last 100 lines)
djangy help                     # display this message

# Example:

    django-startproject myproject
    cd myproject
    git init
    git add .
    git commit -m "my new project"
    djangy create
    git push djangy master

# http://www.djangy.com/docs/ | support@djangy.com
"""

#### Update checker ####

def check_for_update():
    try:
        socket.setdefaulttimeout(2) # 2 second default timeout
        client = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
        version = client.package_releases('Djangy')[0]
        if parse_version(version) > parse_version(VERSION):
            print ''
            print 'Warning: There is an updated version of djangy available.'
            print '         Run easy_install -U Djangy to update.'
            print ''
    except Exception, e:
        print ''
        print 'Warning: Connection to pypi.python.org timed out, so we'
        print '         couldn\'t check if your djangy client is up-to-date.'
        print ''
        pass
    finally:
        socket.setdefaulttimeout(None)

#### Basic input ####

def prompt(text, blank_line=True):
    print ''
    print text + ' ',
    response = sys.stdin.readline().strip('\n')
    if blank_line:
        print ''
    return response

#### Communication with the API server ####

def request(command, email_address = None, hashed_password = None, pubkey = None, application_name = None, args = ' '):
    if not command in COMMANDS:
        print 'Invalid command.'
        sys.exit(1)
    data = {}
    if application_name: data['application_name'] = application_name
    if email_address: data['email'] = email_address
    if args: data['args'] = json.dumps(args)
    if pubkey: data['pubkey'] = pubkey
    if hashed_password: data['hashed_password'] = hashed_password
    url_values = urllib.urlencode(data)
    req = urllib2.Request('%s/%s' % (API_BASE_URL, command), url_values)
    try:
        response = urllib2.urlopen(req)
        print response.read()
        return True
    except urllib2.HTTPError as error:
        if error.code == 403:
            yn = prompt('Authentication error: would you like to re-enter your credentials (y/n)?')[0]
            if yn == 'y' or yn == 'Y':
                os.remove(CONFIG_PATH)
                set_retry()
            else:
                sys.exit(1)
        else:
            print error.read()
            sys.exit(1)
        return False

#### Git repository ####

def get_git_repository(command):
    try:
        git_repo_root = find_git_repository(os.getcwd())
        print 'Using git repository "%s"' % git_repo_root
        return git_repo_root
    except GitRepositoryNotFoundException as e:
        print 'Please run "djangy %s" from within a valid git repository.' % command
        sys.exit(1)

#### Application name ####

def validate_application_name(application_name):
    return re.match('^[A-Za-z][A-Za-z0-9]{4,14}$', application_name) != None

def warn_invalid_application_name(application_name):
    print 'Invalid application name "%s", please try again.' % application_name
    print 'Application name must be 5-15 characters long, A-Z a-z 0-9, starting with a letter.'

def ask_for_application_name():
    while True:
        application_name = prompt('Please enter your application name [Enter for %s]:' % os.path.basename(os.getcwd()))
        if application_name == '':
            # If the user just hit enter, default to the name of the git repo
            application_name = os.path.basename(os.getcwd())
        if validate_application_name(application_name):
            return application_name
        else:
            warn_invalid_application_name(application_name)

def load_application_name():
    parser = RawConfigParser()
    parser.read('djangy.config')
    try:
        return parser.get('application', 'application_name')
    except:
        return None

def save_application_name(application_name):
    # Only actually save if djangy.config doesn't exist.  We don't want to
    # potentially mess up a user-customized file.
    if not os.path.exists('djangy.config'):
        f = open('djangy.config', 'w')
        f.write('[application]\napplication_name=%s\nrootdir=%s\n' \
            % (application_name, os.path.basename(os.getcwd())))
        f.close()
        return True
    elif load_application_name() != application_name:
        print 'Warning: please update application_name in "%s"' % os.path.abspath('djangy.config')
        return False

def print_application_name(application_name, source_of_application_name):
    print 'Using application name "%s" from %s' % (application_name, source_of_application_name)

def get_application_name(application_name_arg=None, application_name_retry=None, write_djangy_config=True):
    if application_name_arg != None:
        application_name = application_name_arg
        print_application_name(application_name, '-a option')
        if not validate_application_name(application_name):
            warn_invalid_application_name(application_name)
            sys.exit(1)
        if write_djangy_config:
            save_application_name(application_name)
        return application_name
    application_name = load_application_name()
    if application_name != None:
        print_application_name(application_name, '"%s"' % os.path.abspath('djangy.config'))
        if not validate_application_name(application_name):
            warn_invalid_application_name(application_name)
            sys.exit(1)
    else:
        if application_name_retry != None:
            # We're retrying due to authentication failure, but the user
            # already entered an application name
            application_name = application_name_retry
        else:
            application_name = ask_for_application_name()
        print_application_name(application_name, 'user input')
        if write_djangy_config:
            save_application_name(application_name)
    return application_name


#### User credentials: email address and password ####

def validate_email_address(email_address):
    return re.match('^.+\\@[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,6}|[0-9]{1,3})$', email_address) != None

def ask_for_email_address():
    num_failures = 0
    while True:
        email_address = prompt('Enter your email address:', blank_line=False)
        if validate_email_address(email_address):
            return email_address
        else:
            num_failures = num_failures + 1
            print 'Invalid email address, please try again.'
            if num_failures > 1:
                print '(or email support@djangy.com if "%s" is correct.)' % email_address

def ask_for_password(email_address):
    hashed_password = md5('%s:%s' % (email_address, getpass.getpass('Please enter your password: '))).hexdigest()
    print ''
    return hashed_password

def ask_for_credentials():
    email_address = ask_for_email_address()
    hashed_password = ask_for_password(email_address)
    return (email_address, hashed_password)

def load_credentials():
    data = [d.strip('\n') for d in open(CONFIG_PATH).readlines()]
    if len(data) != 2:
        return None
    email_address = data[0]
    if not validate_email_address(email_address):
        return None
    hashed_password = data[1]
    return (email_address, hashed_password)

def save_credentials(email_address, hashed_password):
    f = open(CONFIG_PATH, 'w')
    f.write('%s\n%s' % (email_address, hashed_password))
    f.close()
    print 'Saved credentials.'
    print 'To change your email address or password, remove "%s"' % CONFIG_PATH

def get_credentials():
    try:
        return load_credentials()
    except:
        (email_address, hashed_password) = ask_for_credentials()
        save_credentials(email_address, hashed_password)
        return (email_address, hashed_password)

#### User public key ####

def validate_pubkey(pubkey_path):
    if os.path.isfile(pubkey_path):
        return True
    return False

def get_pubkey():
    # try to find public key path
    pubkey_path = None
    if os.path.exists('%s/.ssh/id_rsa.pub' % HOME):
        pubkey_path = '%s/.ssh/id_rsa.pub' % HOME
    else:
        is_valid_pubkey = False
        while not is_valid_pubkey:
            pubkey_path = os.path.abspath(prompt('Please enter the path to your ssh public key:'))
            if validate_pubkey(pubkey_path):
                is_valid_pubkey = True
            else:
                print 'Unable to locate ssh public key at path "%s"' % pubkey_path
    print 'Using public key file "%s"' % pubkey_path
    return open(pubkey_path).read()

#### Commands ####

_retry = True

def run_command(command, application_name_arg, args):
    global _retry
    application_name = application_name_arg
    while _retry:
        _retry = False
        email_address, hashed_password = get_credentials()
        application_name = get_application_name(application_name_arg=application_name_arg, \
            application_name_retry=application_name, write_djangy_config=(command != 'create'))
        if command == 'create':
            create(application_name, email_address, hashed_password)
        elif command == 'manage.py':
            manage_py(application_name, email_address, hashed_password, args)
        else:
            simple_command(command, application_name, email_address, hashed_password)

def set_retry():
    global _retry
    _retry = True

def create(application_name, email_address, hashed_password):
    pubkey = get_pubkey()
    if request('create', application_name = application_name, email_address = email_address, hashed_password = hashed_password, pubkey = pubkey):
        init_default_files(application_name)
        init_git_remote(application_name)

def init_default_files(application_name):
    files_created = []
    if os.path.exists('djangy.config'):
        if load_application_name() != application_name:
            print 'Please update application_name in "%s"' % os.path.abspath('djangy.config')
    else:
        if save_application_name(application_name):
            files_created.append('djangy.config')
    if not os.path.exists('djangy.eggs'):
        f = open('djangy.eggs', 'w')
        f.write('Django\nSouth\n')
        f.close()
        files_created.append('djangy.eggs')
    if not os.path.exists('djangy.pip'):
        f = open('djangy.pip', 'w')
        f.write('')
        f.close()
        files_created.append('djangy.pip')
    if len(files_created) > 0:
        n = len(files_created)
        git_add_and_commit(files_created)

def format_and_list(list, when_empty=''):
    list = map(lambda x: '"%s"' % x, list)
    if len(list) > 0:
        if len(list) == 1:
            return list[0]
        else:
            return (', '.join(list[:-1]) + ' and ' + list[-1])
    else:
        return when_empty

def singular_plural(n, singular, plural):
    if n > 1:
        return plural
    else:
        return singular

def init_git_remote(application_name):
    """Add the "djangy" remote"""
    subprocess.call(['git remote add djangy git@%s:%s.git > /dev/null 2>&1' % (GIT_HOST, application_name)], shell=True)
    print ""
    print 'You can now run "git push djangy master"'

def git_add_and_commit(files):
    if len(files) < 1:
        return False
    status = subprocess.call(['git', 'add'] + files)
    if status == 0:
        status = subprocess.call(['git', 'commit', '-m', 'added %s to repository' % format_and_list(files)])
        if status == 0:
            return True
    return False

def manage_py(application_name, email_address, hashed_password, args):
    print ""
    command = "ssh -oPasswordAuthentication=no shell@api.djangy.com %s manage.py %s" % (application_name, " ".join(args))
    os.system(command)

def simple_command(command, application_name, email_address, hashed_password):
    request(command, application_name = application_name, email_address = email_address, hashed_password = hashed_password)

#### Main ####

def main():
    # Parse command line arguments
    command = ''
    application_name = None
    args = sys.argv[1:]
    try:
        if args[0][0:2] == '-a':
            application_name = args[0][2:]
            if application_name != '':
                args = args[1:]
            else:
                application_name = args[1]
                args = args[2:]
        command = args[0]
        args    = args[1:]
    except:
        pass

    if command in COMMANDS:
        check_for_update()
        # Go to the root directory of the repository so that any files we
        # create are stored at the root level, and so the djangy.config and
        # djangy.eggs files can be created with the right contents/location.
        os.chdir(get_git_repository(command));
        run_command(command, application_name, args)
    elif command == 'help':
        print HELP_MESSAGE
    else:
        print HELP_MESSAGE
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = find_git_repository
import os.path

__DOT_GIT_FILES__            = ['config', 'description', 'HEAD']
__DOT_GIT_SUBDIRECTORIES__   = ['hooks', 'info', 'objects', 'refs']

def find_git_repository(cwd):
    """Finds the nearest enclosing git repository.  Raises a
    GitRepositoryNotFoundException if there is none."""

    # Normalize the path
    dir_path = os.path.abspath(cwd)
    # Start with this directory, and iterate up a level until we find a git
    # repository root directory.
    while dir_path != '/':
        if is_git_repository_root(dir_path):
            return dir_path
        else:
            dir_path = os.path.dirname(dir_path)

    # Check one more time just in case / is a git repository
    if is_git_repository_root(dir_path):
        return dir_path
    else:
        raise GitRepositoryNotFoundException(cwd)

def is_git_repository_root(dir_path):
    """Is dir_path the root directory of a git repository?"""

    # Is there a .git subdirectory?  And is it well-formed?
    git_dir = os.path.join(dir_path, '.git')
    if os.path.isdir(git_dir) \
    and is_git_dir(git_dir):
        return True

    # Is this directory itself a bare git repository with no working copy
    # checkout directory?
    return os.path.basename(dir_path).endswith('.git') \
        and os.path.basename(dir_path) != '.git' \
        and is_git_dir(dir_path)

def is_git_dir(dir_path):
    """Is dir_path a reasonably well-formed .git directory?"""

    # Files that must exist in a .git directory
    for git_file in __DOT_GIT_FILES__:
        if not os.path.isfile(os.path.join(dir_path, git_file)):
            return False

    # Subdirectories that must exist in a .git directory
    for git_subdir in __DOT_GIT_SUBDIRECTORIES__:
        if not os.path.isdir(os.path.join(dir_path, git_subdir)):
            return False
    return True

class GitRepositoryNotFoundException(Exception):
    """No git repository root found in any parent of specified directory."""
    def __init__(self, path):
        self.path = path
    def __str__(self):
        return 'No git repository root found in any parent of directory "%s".' % self.path

########NEW FILE########
__FILENAME__ = manage
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'WhiteList'
        db.create_table('whitelist', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('invite_code', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('management_database', ['WhiteList'])

        # Adding model 'User'
        db.create_table('user', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('passwd', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('admin', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('management_database', ['User'])

        # Adding model 'Application'
        db.create_table('application', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('account', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('max_processes', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('db_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('db_username', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('db_password', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('db_host', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('db_port', self.gf('django.db.models.fields.IntegerField')(default=3306)),
            ('db_max_size_mb', self.gf('django.db.models.fields.IntegerField')(default=5)),
            ('setup_uid', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('web_uid', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('cron_uid', self.gf('django.db.models.fields.IntegerField')(default=-1)),
        ))
        db.send_create_signal('management_database', ['Application'])

        # Adding model 'Process'
        db.create_table('process', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.Application'])),
            ('host', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('management_database', ['Process'])


    def backwards(self, orm):
        
        # Deleting model 'WhiteList'
        db.delete_table('whitelist')

        # Deleting model 'User'
        db.delete_table('user')

        # Deleting model 'Application'
        db.delete_table('application')

        # Deleting model 'Process'
        db.delete_table('process')


    models = {
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_processes': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0002_add_admins
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.core.management import call_command

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # outdated


    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_processes': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0003_add_app_gid
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Application.app_gid'
        db.add_column('application', 'app_gid', self.gf('django.db.models.fields.IntegerField')(default=-1))


    def backwards(self, orm):
        
        # Deleting field 'Application.app_gid'
        db.delete_column('application', 'app_gid')


    models = {
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_processes': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_application_bundle_version
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Application.bundle_version'
        db.add_column('application', 'bundle_version', self.gf('django.db.models.fields.CharField')(default='', max_length=255), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Application.bundle_version'
        db.delete_column('application', 'bundle_version')


    models = {
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_processes': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0005_resource_allocation
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Application.max_processes'
        db.delete_column('application', 'max_processes')

        # Adding field 'Application.proc_num_threads'
        db.add_column('application', 'proc_num_threads', self.gf('django.db.models.fields.IntegerField')(default=5), keep_default=False)

        # Adding field 'Application.proc_mem_mb'
        db.add_column('application', 'proc_mem_mb', self.gf('django.db.models.fields.IntegerField')(default=64), keep_default=False)

        # Adding field 'Application.proc_stack_mb'
        db.add_column('application', 'proc_stack_mb', self.gf('django.db.models.fields.IntegerField')(default=2), keep_default=False)

        # Adding field 'Application.debug'
        db.add_column('application', 'debug', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)

        # Adding field 'Process.num_procs'
        db.add_column('process', 'num_procs', self.gf('django.db.models.fields.IntegerField')(default=1), keep_default=False)

        # Adding unique constraint on 'Process', fields ['application', 'host']
        db.create_unique('process', ['application_id', 'host'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Process', fields ['application', 'host']
        db.delete_unique('process', ['application_id', 'host'])

        # Adding field 'Application.max_processes'
        db.add_column('application', 'max_processes', self.gf('django.db.models.fields.IntegerField')(default=1), keep_default=False)

        # Deleting field 'Application.proc_num_threads'
        db.delete_column('application', 'proc_num_threads')

        # Deleting field 'Application.proc_mem_mb'
        db.delete_column('application', 'proc_mem_mb')

        # Deleting field 'Application.proc_stack_mb'
        db.delete_column('application', 'proc_stack_mb')

        # Deleting field 'Application.debug'
        db.delete_column('application', 'debug')

        # Deleting field 'Process.num_procs'
        db.delete_column('process', 'num_procs')


    models = {
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "(('application', 'host'),)", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0006_mark_deletion
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Application.deleted'
        db.add_column('application', 'deleted', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Application.deleted'
        db.delete_column('application', 'deleted')


    models = {
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "(('application', 'host'),)", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0007_add_chargify_ids
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'User.customer_id'
        db.add_column('user', 'customer_id', self.gf('django.db.models.fields.CharField')(default=-1, max_length=255), keep_default=False)

        # Adding field 'User.subscription_id'
        db.add_column('user', 'subscription_id', self.gf('django.db.models.fields.CharField')(default=-1, max_length=255), keep_default=False)

        # Adding field 'User.masked_cc'
        db.add_column('user', 'masked_cc', self.gf('django.db.models.fields.CharField')(default=-1, max_length=255), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'User.customer_id'
        db.delete_column('user', 'customer_id')

        # Deleting field 'User.subscription_id'
        db.delete_column('user', 'subscription_id')

        # Deleting field 'User.masked_cc'
        db.delete_column('user', 'masked_cc')


    models = {
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "(('application', 'host'),)", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'masked_cc': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0008_remove_masked_cc
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'User.masked_cc'
        db.delete_column('user', 'masked_cc')


    def backwards(self, orm):
        
        # Adding field 'User.masked_cc'
        db.add_column('user', 'masked_cc', self.gf('django.db.models.fields.CharField')(default=-1, max_length=255), keep_default=False)


    models = {
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "(('application', 'host'),)", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0009_add_allocation_change
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'AllocationChange'
        db.create_table('allocation_change', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.Application'])),
            ('component', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('quantity', self.gf('django.db.models.fields.IntegerField')()),
            ('billed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('management_database', ['AllocationChange'])


    def backwards(self, orm):
        
        # Deleting model 'AllocationChange'
        db.delete_table('allocation_change')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "(('application', 'host'),)", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0010_add_ProxyCache_and_VirtualHost_and_Process_port
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'VirtualHost'
        db.create_table('virtualhost', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.Application'])),
            ('virtualhost', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('management_database', ['VirtualHost'])

        # Adding model 'ProxyCache'
        db.create_table('proxycache', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.Application'])),
            ('host', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('management_database', ['ProxyCache'])

        # Adding field 'Process.port'
        db.add_column('process', 'port', self.gf('django.db.models.fields.IntegerField')(default=8080), keep_default=False)


    def backwards(self, orm):
        
        # Deleting model 'VirtualHost'
        db.delete_table('virtualhost')

        # Deleting model 'ProxyCache'
        db.delete_table('proxycache')

        # Deleting field 'Process.port'
        db.delete_column('process', 'port')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "(('application', 'host'),)", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '8080'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0011_add_port_to_proxycache
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'ProxyCache.port'
        db.add_column('proxycache', 'port', self.gf('django.db.models.fields.IntegerField')(default=20000), keep_default=False)


    def backwards(self, orm):

        # Deleting field 'ProxyCache.port'
        db.delete_column('proxycache', 'port')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "(('application', 'host'),)", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '8080'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0012_remove_ProxyCache_port_and_add_some_uniqueness_constraints
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'Application', fields ['name']
        db.create_unique('application', ['name'])

        # Adding unique constraint on 'Process', fields ['host', 'port']
        db.create_unique('process', ['host', 'port'])

        # Deleting field 'ProxyCache.port'
        db.delete_column('proxycache', 'port')

        # Adding unique constraint on 'User', fields ['email']
        db.create_unique('user', ['email'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'User', fields ['email']
        db.delete_unique('user', ['email'])

        # Removing unique constraint on 'Process', fields ['host', 'port']
        db.delete_unique('process', ['host', 'port'])

        # Removing unique constraint on 'Application', fields ['name']
        db.delete_unique('application', ['name'])

        # Adding field 'ProxyCache.port'
        db.add_column('proxycache', 'port', self.gf('django.db.models.fields.IntegerField')(default=20000), keep_default=False)


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0013_create_table_WorkerHost
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'WorkerHost'
        db.create_table('worker_host', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('host', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('max_procs', self.gf('django.db.models.fields.IntegerField')(default=100)),
        ))
        db.send_create_signal('management_database', ['WorkerHost'])


    def backwards(self, orm):
        
        # Deleting model 'WorkerHost'
        db.delete_table('worker_host')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0014_add_application_num_procs
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Application.num_procs'
        db.add_column('application', 'num_procs', self.gf('django.db.models.fields.IntegerField')(default=1), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Application.num_procs'
        db.delete_column('application', 'num_procs')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0015_default_VirtualHost
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        # For each application, make sure it has a default entry in the VirtualHost table.
        for application in orm.Application.objects.all():
            if not orm.VirtualHost.objects.filter(application=application).all():
                print "Adding %s.djangy.com" % application.name
                virtualhost = orm.VirtualHost(application=application, virtualhost='%s.djangy.com' % application.name)
                virtualhost.save()


    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0016_default_ProxyCache
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        # For each application, make sure it has at least one entry in the
        # ProxyCache table.  We make that default "localhost", which is iffy
        # long-term, because it means the ProxyCache server and Master
        # server must be the same machine.
        for application in orm.Application.objects.all():
            if not orm.ProxyCache.objects.filter(application=application).all():
                proxycache = orm.ProxyCache(application=application, host='localhost')
                proxycache.save()


    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0017_make_virtualhost_unique
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'VirtualHost', fields ['application', 'virtualhost']
        db.create_unique('virtualhost', ['application_id', 'virtualhost'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'VirtualHost', fields ['application', 'virtualhost']
        db.delete_unique('virtualhost', ['application_id', 'virtualhost'])


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0018_add_referrers
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'WhiteList.referrer'
        db.add_column('whitelist', 'referrer', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['management_database.User'], null=True, blank=True), keep_default=False)

        # Adding field 'User.referrer'
        db.add_column('user', 'referrer', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['management_database.User'], null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'WhiteList.referrer'
        db.delete_column('whitelist', 'referrer_id')

        # Deleting field 'User.referrer'
        db.delete_column('user', 'referrer_id')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0019_add_invite_limit
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'User.invite_limit'
        db.add_column('user', 'invite_limit', self.gf('django.db.models.fields.IntegerField')(default=10), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'User.invite_limit'
        db.delete_column('user', 'invite_limit')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0020_add_SshPublicKey_and_Collaborator
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Rename Application.account to Application.owner - broken
        #db.rename_column('application', 'account_id', 'owner_id')

        # Adding model 'Collaborator'
        db.create_table('collaborator', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.Application'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.User'])),
        ))
        db.send_create_signal('management_database', ['Collaborator'])

        # Adding unique constraint on 'Collaborator', fields ['application', 'user']
        db.create_unique('collaborator', ['application_id', 'user_id'])

        # Adding model 'SshPublicKey'
        db.create_table('ssh_public_key', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.User'])),
            ('ssh_public_key', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('comment', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal('management_database', ['SshPublicKey'])


    def backwards(self, orm):
        
        # Rename Application.owner back to Application.account - broken
        #db.rename_column('application', 'owner_id', 'account_id')

        # Removing unique constraint on 'Collaborator', fields ['application', 'user']
        db.delete_unique('collaborator', ['application_id', 'user_id'])

        # Deleting model 'Collaborator'
        db.delete_table('collaborator')

        # Deleting model 'SshPublicKey'
        db.delete_table('ssh_public_key')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.collaborator': {
            'Meta': {'unique_together': "[('application', 'user')]", 'object_name': 'Collaborator', 'db_table': "'collaborator'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.sshpublickey': {
            'Meta': {'object_name': 'SshPublicKey', 'db_table': "'ssh_public_key'"},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_public_key': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'}),
            'subscription_id': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0021_chargify_to_devpayments_schema
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'User.subscription_id'
        db.delete_column('user', 'subscription_id')

        # Adding field 'User.first_name'
        db.add_column('user', 'first_name', self.gf('django.db.models.fields.CharField')(default=None, max_length=255, null=True, blank=True), keep_default=False)

        # Adding field 'User.last_name'
        db.add_column('user', 'last_name', self.gf('django.db.models.fields.CharField')(default=None, max_length=255, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'User.subscription_id'
        db.add_column('user', 'subscription_id', self.gf('django.db.models.fields.CharField')(default=-1, max_length=255), keep_default=False)

        # Deleting field 'User.first_name'
        db.delete_column('user', 'first_name')

        # Deleting field 'User.last_name'
        db.delete_column('user', 'last_name')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.collaborator': {
            'Meta': {'unique_together': "[('application', 'user')]", 'object_name': 'Collaborator', 'db_table': "'collaborator'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.sshpublickey': {
            'Meta': {'object_name': 'SshPublicKey', 'db_table': "'ssh_public_key'"},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_public_key': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'first_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'last_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0022_add_chargables
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Chargable'
        db.create_table('chargable', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('component', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('price', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('management_database', ['Chargable'])


    def backwards(self, orm):
        
        # Deleting model 'Chargable'
        db.delete_table('chargable')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.chargable': {
            'Meta': {'object_name': 'Chargable', 'db_table': "'chargable'"},
            'component': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'management_database.collaborator': {
            'Meta': {'unique_together': "[('application', 'user')]", 'object_name': 'Collaborator', 'db_table': "'collaborator'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.sshpublickey': {
            'Meta': {'object_name': 'SshPublicKey', 'db_table': "'ssh_public_key'"},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_public_key': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'first_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'last_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0023_alter_allocation_change
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'AllocationChange.component'
        db.delete_column('allocation_change', 'component')

        # Adding field 'AllocationChange.chargable'
        db.add_column('allocation_change', 'chargable', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.Chargable'], null=True), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'AllocationChange.component'
        db.add_column('allocation_change', 'component', self.gf('django.db.models.fields.CharField')(default='workers', max_length=255), keep_default=False)

        # Deleting field 'AllocationChange.chargable'
        db.delete_column('allocation_change', 'chargable_id')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'chargable': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Chargable']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.chargable': {
            'Meta': {'object_name': 'Chargable', 'db_table': "'chargable'"},
            'component': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'management_database.collaborator': {
            'Meta': {'unique_together': "[('application', 'user')]", 'object_name': 'Collaborator', 'db_table': "'collaborator'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.sshpublickey': {
            'Meta': {'object_name': 'SshPublicKey', 'db_table': "'ssh_public_key'"},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_public_key': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'first_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'last_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0024_add_billing_events
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'BillingEvent'
        db.create_table('billingevent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('customer_id', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('application_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('chargable_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('cents', self.gf('django.db.models.fields.IntegerField')()),
            ('success', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('memo', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal('management_database', ['BillingEvent'])


    def backwards(self, orm):
        
        # Deleting model 'BillingEvent'
        db.delete_table('billingevent')


    models = {
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'chargable': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Chargable']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.billingevent': {
            'Meta': {'object_name': 'BillingEvent', 'db_table': "'billingevent'"},
            'application_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'cents': ('django.db.models.fields.IntegerField', [], {}),
            'chargable_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memo': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.chargable': {
            'Meta': {'object_name': 'Chargable', 'db_table': "'chargable'"},
            'component': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'management_database.collaborator': {
            'Meta': {'unique_together': "[('application', 'user')]", 'object_name': 'Collaborator', 'db_table': "'collaborator'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.sshpublickey': {
            'Meta': {'object_name': 'SshPublicKey', 'db_table': "'ssh_public_key'"},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_public_key': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'first_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'last_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0025_add_ActiveApplicationName_table
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Application', fields ['name']
        db.delete_unique('application', ['name'])

        # Adding model 'ActiveApplicationName'
        db.create_table('active_application_name', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
        ))
        db.send_create_signal('management_database', ['ActiveApplicationName'])


    def backwards(self, orm):
        
        # Deleting model 'ActiveApplicationName'
        db.delete_table('active_application_name')

        # Adding unique constraint on 'Application', fields ['name']
        db.create_unique('application', ['name'])


    models = {
        'management_database.activeapplicationname': {
            'Meta': {'object_name': 'ActiveApplicationName', 'db_table': "'active_application_name'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'chargable': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Chargable']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.billingevent': {
            'Meta': {'object_name': 'BillingEvent', 'db_table': "'billingevent'"},
            'application_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'cents': ('django.db.models.fields.IntegerField', [], {}),
            'chargable_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memo': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.chargable': {
            'Meta': {'object_name': 'Chargable', 'db_table': "'chargable'"},
            'component': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'management_database.collaborator': {
            'Meta': {'unique_together': "[('application', 'user')]", 'object_name': 'Collaborator', 'db_table': "'collaborator'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.sshpublickey': {
            'Meta': {'object_name': 'SshPublicKey', 'db_table': "'ssh_public_key'"},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_public_key': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'first_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'last_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0026_add_subscriptions
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SubscriptionType'
        db.create_table('subscriptiontype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('price', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('management_database', ['SubscriptionType'])

        # Adding model 'Subscription'
        db.create_table('subscription', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.Application'])),
            ('subscription_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['management_database.SubscriptionType'])),
            ('price', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('enabled', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('disabled', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True)),
        ))
        db.send_create_signal('management_database', ['Subscription'])


    def backwards(self, orm):
        
        # Deleting model 'SubscriptionType'
        db.delete_table('subscriptiontype')

        # Deleting model 'Subscription'
        db.delete_table('subscription')


    models = {
        'management_database.activeapplicationname': {
            'Meta': {'object_name': 'ActiveApplicationName', 'db_table': "'active_application_name'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'chargable': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Chargable']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.billingevent': {
            'Meta': {'object_name': 'BillingEvent', 'db_table': "'billingevent'"},
            'application_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'cents': ('django.db.models.fields.IntegerField', [], {}),
            'chargable_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memo': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.chargable': {
            'Meta': {'object_name': 'Chargable', 'db_table': "'chargable'"},
            'component': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'management_database.collaborator': {
            'Meta': {'unique_together': "[('application', 'user')]", 'object_name': 'Collaborator', 'db_table': "'collaborator'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.sshpublickey': {
            'Meta': {'object_name': 'SshPublicKey', 'db_table': "'ssh_public_key'"},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_public_key': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.subscription': {
            'Meta': {'object_name': 'Subscription', 'db_table': "'subscription'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'disabled': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'enabled': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'subscription_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.SubscriptionType']"})
        },
        'management_database.subscriptiontype': {
            'Meta': {'object_name': 'SubscriptionType', 'db_table': "'subscriptiontype'"},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'first_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'last_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0027_add_cache_sizes
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Application.cache_index_size_kb'
        db.add_column('application', 'cache_index_size_kb', self.gf('django.db.models.fields.IntegerField')(default=0), keep_default=False)

        # Adding field 'Application.cache_size_kb'
        db.add_column('application', 'cache_size_kb', self.gf('django.db.models.fields.IntegerField')(default=0), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Application.cache_index_size_kb'
        db.delete_column('application', 'cache_index_size_kb')

        # Deleting field 'Application.cache_size_kb'
        db.delete_column('application', 'cache_size_kb')


    models = {
        'management_database.activeapplicationname': {
            'Meta': {'object_name': 'ActiveApplicationName', 'db_table': "'active_application_name'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'chargable': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Chargable']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cache_index_size_kb': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'cache_size_kb': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.billingevent': {
            'Meta': {'object_name': 'BillingEvent', 'db_table': "'billingevent'"},
            'application_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'cents': ('django.db.models.fields.IntegerField', [], {}),
            'chargable_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memo': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.chargable': {
            'Meta': {'object_name': 'Chargable', 'db_table': "'chargable'"},
            'component': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'management_database.collaborator': {
            'Meta': {'unique_together': "[('application', 'user')]", 'object_name': 'Collaborator', 'db_table': "'collaborator'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.sshpublickey': {
            'Meta': {'object_name': 'SshPublicKey', 'db_table': "'ssh_public_key'"},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_public_key': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.subscription': {
            'Meta': {'object_name': 'Subscription', 'db_table': "'subscription'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'disabled': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'enabled': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'null': 'True', 'blank': 'True'}),
            'subscription_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.SubscriptionType']"})
        },
        'management_database.subscriptiontype': {
            'Meta': {'object_name': 'SubscriptionType', 'db_table': "'subscriptiontype'"},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'first_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'last_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0028_add_celery_procs
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Application.celery_procs'
        db.add_column('application', 'celery_procs', self.gf('django.db.models.fields.IntegerField')(default=1), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Application.celery_procs'
        db.delete_column('application', 'celery_procs')


    models = {
        'management_database.activeapplicationname': {
            'Meta': {'object_name': 'ActiveApplicationName', 'db_table': "'active_application_name'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'chargable': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Chargable']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cache_index_size_kb': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'cache_size_kb': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'celery_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.billingevent': {
            'Meta': {'object_name': 'BillingEvent', 'db_table': "'billingevent'"},
            'application_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'cents': ('django.db.models.fields.IntegerField', [], {}),
            'chargable_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memo': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.chargable': {
            'Meta': {'object_name': 'Chargable', 'db_table': "'chargable'"},
            'component': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'management_database.collaborator': {
            'Meta': {'unique_together': "[('application', 'user')]", 'object_name': 'Collaborator', 'db_table': "'collaborator'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.sshpublickey': {
            'Meta': {'object_name': 'SshPublicKey', 'db_table': "'ssh_public_key'"},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_public_key': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.subscription': {
            'Meta': {'object_name': 'Subscription', 'db_table': "'subscription'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'disabled': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'enabled': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'subscription_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.SubscriptionType']"})
        },
        'management_database.subscriptiontype': {
            'Meta': {'object_name': 'SubscriptionType', 'db_table': "'subscriptiontype'"},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'first_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'last_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = 0029_add_proc_type_to_Process
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Process', fields ['application', 'host']
        db.delete_unique('process', ['application_id', 'host'])

        # Adding field 'Process.proc_type'
        db.add_column('process', 'proc_type', self.gf('django.db.models.fields.CharField')(default='gunicorn', max_length=64), keep_default=False)

        # Adding unique constraint on 'Process', fields ['application', 'host', 'proc_type']
        db.create_unique('process', ['application_id', 'host', 'proc_type'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Process', fields ['application', 'host', 'proc_type']
        db.delete_unique('process', ['application_id', 'host', 'proc_type'])

        # Deleting field 'Process.proc_type'
        db.delete_column('process', 'proc_type')

        # Adding unique constraint on 'Process', fields ['application', 'host']
        db.create_unique('process', ['application_id', 'host'])


    models = {
        'management_database.activeapplicationname': {
            'Meta': {'object_name': 'ActiveApplicationName', 'db_table': "'active_application_name'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'management_database.allocationchange': {
            'Meta': {'object_name': 'AllocationChange', 'db_table': "'allocation_change'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'billed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'chargable': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Chargable']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.application': {
            'Meta': {'object_name': 'Application', 'db_table': "'application'"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"}),
            'app_gid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'cache_index_size_kb': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'cache_size_kb': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'celery_procs': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'cron_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_max_size_mb': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'db_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_port': ('django.db.models.fields.IntegerField', [], {'default': '3306'}),
            'db_username': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {'default': '64'}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'setup_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'web_uid': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'management_database.billingevent': {
            'Meta': {'object_name': 'BillingEvent', 'db_table': "'billingevent'"},
            'application_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'cents': ('django.db.models.fields.IntegerField', [], {}),
            'chargable_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memo': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'management_database.chargable': {
            'Meta': {'object_name': 'Chargable', 'db_table': "'chargable'"},
            'component': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'management_database.collaborator': {
            'Meta': {'unique_together': "[('application', 'user')]", 'object_name': 'Collaborator', 'db_table': "'collaborator'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.process': {
            'Meta': {'unique_together': "[('application', 'proc_type', 'host'), ('host', 'port')]", 'object_name': 'Process', 'db_table': "'process'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '20000'}),
            'proc_type': ('django.db.models.fields.CharField', [], {'default': "'gunicorn'", 'max_length': '64'})
        },
        'management_database.proxycache': {
            'Meta': {'object_name': 'ProxyCache', 'db_table': "'proxycache'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'management_database.sshpublickey': {
            'Meta': {'object_name': 'SshPublicKey', 'db_table': "'ssh_public_key'"},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ssh_public_key': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.User']"})
        },
        'management_database.subscription': {
            'Meta': {'object_name': 'Subscription', 'db_table': "'subscription'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'disabled': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'enabled': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'subscription_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.SubscriptionType']"})
        },
        'management_database.subscriptiontype': {
            'Meta': {'object_name': 'SubscriptionType', 'db_table': "'subscriptiontype'"},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'price': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'management_database.user': {
            'Meta': {'object_name': 'User', 'db_table': "'user'"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'first_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_limit': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'last_name': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'passwd': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.virtualhost': {
            'Meta': {'unique_together': "[('application', 'virtualhost')]", 'object_name': 'VirtualHost', 'db_table': "'virtualhost'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['management_database.Application']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'virtualhost': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'management_database.whitelist': {
            'Meta': {'object_name': 'WhiteList', 'db_table': "'whitelist'"},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'referrer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['management_database.User']", 'null': 'True', 'blank': 'True'})
        },
        'management_database.workerhost': {
            'Meta': {'object_name': 'WorkerHost', 'db_table': "'worker_host'"},
            'host': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_procs': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        }
    }

    complete_apps = ['management_database']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.utils import IntegrityError
from datetime import datetime

class WhiteList(models.Model):
    class Meta:
        db_table = 'whitelist'

    email = models.CharField(max_length=255) # Shouldn't this be unique=True?
    invite_code = models.CharField(max_length=255)
    referrer = models.ForeignKey('User', blank = True, default = None, null = True)

    @staticmethod
    def verify(email, invite_code):
        try:
            wl = WhiteList.objects.get(email=email)
            if wl.invite_code == invite_code:
                return True
        except:
            pass
        return False

class User(models.Model):
    class Meta:
        db_table = 'user'

    email = models.CharField(max_length=255, unique=True)
    passwd = models.CharField(max_length=255)
    admin = models.BooleanField(default=False)
    customer_id = models.CharField(max_length=255)
    referrer = models.ForeignKey('User', blank = True, default = None, null = True)
    invite_limit = models.IntegerField(default=0)
    first_name = models.CharField(max_length=255, blank = True, default = None, null = True)
    last_name = models.CharField(max_length=255, blank = True, default = None, null = True)

    @staticmethod
    def get_by_email(email):
        try:
            return User.objects.get(email=email)
        except:
            return None

    def add_ssh_public_key(self, ssh_public_key, comment):
        if not SshPublicKey.objects.filter(user=self, ssh_public_key=ssh_public_key).exists():
            SshPublicKey(user=self, ssh_public_key=ssh_public_key, comment=comment).save()

    def get_ssh_public_keys(self):
        return self.sshpublickey_set.all()

    def remove_ssh_public_key(self, key_id):
        self.sshpublickey_set.filter(id=key_id).delete()

    def get_accessible_applications(self):
        owned_applications = list(self.application_set.filter(deleted=None).all())
        collaborating_applications = filter(lambda x: x.deleted==None, \
            [x.application for x in self.collaborator_set.select_related(depth=1)])
        applications = owned_applications + collaborating_applications
        applications.sort(cmp=lambda x, y: cmp(x.name, y.name))
        return applications

    def get_subscriptions(self):
        subs = []
        apps = self.application_set.all()
        for app in apps:
            subs += list(app.subscription_set.all())
        return subs

    def get_active_subscriptions(self):
        subs = []
        apps = self.application_set.all()
        for app in apps:
            subs += list(app.subscription_set.filter(disabled=None))
        return subs

class SshPublicKey(models.Model):
    class Meta:
        db_table = 'ssh_public_key'

    user = models.ForeignKey(User)
    ssh_public_key = models.CharField(max_length=1024)
    comment = models.CharField(max_length=64)

    @staticmethod
    def get_users_by_public_key_id(id):
        # Two-step process in case two users have the same SSH public key.
        ssh_public_key = SshPublicKey.objects.get(id=id).ssh_public_key
        return [x.user for x in SshPublicKey.objects.filter(ssh_public_key=ssh_public_key)]

class ActiveApplicationName(models.Model):
    class Meta:
        db_table = 'active_application_name'

    name = models.CharField(max_length=255, unique=True)

class Application(models.Model):
    class Meta:
        db_table = 'application'

    account = models.ForeignKey(User)
    bundle_version = models.CharField(max_length=255,default='')
    name = models.CharField(max_length=255)
    db_name = models.CharField(max_length=255)
    db_username = models.CharField(max_length=255)
    db_password = models.CharField(max_length=255)
    db_host = models.CharField(max_length=255)
    db_port = models.IntegerField(default=3306)
    db_max_size_mb = models.IntegerField(default=5)
    setup_uid = models.IntegerField(default=-1)
    web_uid = models.IntegerField(default=-1)
    cron_uid = models.IntegerField(default=-1)
    app_gid = models.IntegerField(default=-1)
    num_procs = models.IntegerField(default=1)
    proc_num_threads = models.IntegerField(default=20)
    proc_mem_mb = models.IntegerField(default=64)
    proc_stack_mb = models.IntegerField(default=2)
    cache_index_size_kb = models.IntegerField(default=64)
    cache_size_kb = models.IntegerField(default=16384)
    debug = models.BooleanField(default=False)
    deleted = models.DateTimeField(null=True, blank=True)
    celery_procs = models.IntegerField(default=0)

    @staticmethod
    def get_by_name(name):
        try:
            return Application.objects.get(name=name, deleted=None)
        except:
            return None

    def mark_deleted(self):
        if not self.deleted:
            self.deleted = datetime.now()
        self.save()
        self.process_set.all().delete()
        self.virtualhost_set.all().delete()
        try:
            ActiveApplicationName.objects.get(name=self.name).delete()
        except:
            pass

    def report_allocation_change(self, chargable, quantity):
        alloc = AllocationChange(application = self, chargable = chargable, quantity = quantity)
        alloc.save()

    def has_collaborator(self, user):
        return Collaborator.objects.filter(application=self, user=user).exists()

    def accessible_by(self, user):
        return (self.deleted == None) and ((user.admin == True) or (self.account == user) or self.has_collaborator(user))

    def accessible_by_any_of(self, users):
        return any([self.accessible_by(u) for u in users])

    def add_collaborator(self, email):
        user = User.get_by_email(email)
        if not user:
            raise NoUserException(email)
        if not self.deleted and (self.account != user) \
        and not Collaborator.objects.filter(application=self, user=user).exists():
            collaborator = Collaborator(application=self, user=user)
            collaborator.save()
            return True
        else:
            return False

    def remove_collaborator(self, email):
        user = User.get_by_email(email)
        if user and not self.deleted:
            try:
                Collaborator.objects.get(application=self, user=user).delete()
            except:
                pass

    def get_collaborators(self):
        """ Returns email addresses of collaborators on this application (not including the owner). """
        return [c.user.email for c in self.collaborator_set.all()]

    def is_server_cache_enabled(self):
        return self.cache_size_kb > 0

    def enable_server_cache(self):
        self.cache_index_size_kb = 64
        self.cache_size_kb = 16384
        self.save()

    def disable_server_cache(self):
        self.cache_index_size_kb = 0
        self.cache_size_kb = 0
        self.save()

    def add_domain_name(self, domain_name):
        if domain_name not in VirtualHost.get_virtualhosts_by_application(self):
            VirtualHost(application = self, virtualhost = str(domain_name)).save()

    def delete_domain_name(self, domain_name):
        VirtualHost.objects.filter(application = self, virtualhost = str(domain_name)).delete()

class NoUserException(Exception):
    def __init__(self, email):
        self.email = email
    def __str__(self):
        return 'No user exists with email address %s' % self.email

class Collaborator(models.Model):
    class Meta:
        db_table = 'collaborator'
        unique_together = [('application', 'user')]

    application = models.ForeignKey(Application)
    user = models.ForeignKey(User)

class WorkerHost(models.Model):
    class Meta:
        db_table = 'worker_host'

    host = models.CharField(max_length=255, unique=True)
    max_procs = models.IntegerField(default=100)
    # In the future, we may want to distinguish between hosts used by paid
    # users vs. free users, and offer paid users better service while packing
    # as many free users as possible onto a host.

class Process(models.Model):
    class Meta:
        db_table = 'process'
        unique_together = [('application', 'proc_type', 'host'), ('host', 'port')]

    application = models.ForeignKey(Application)
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=20000)
    num_procs = models.IntegerField(default=1)
    proc_type = models.CharField(max_length=64, default='gunicorn')

    @staticmethod
    def get_hosts_ports_by_application(application):
        try:
            return [(process.host, process.port) for process in application.process_set.all()]
        except:
            return None

class Chargable(models.Model):
    class Meta:
        db_table = 'chargable'
    
    component = models.IntegerField(default=0)
    price = models.IntegerField(default=0)

    components = {
        'application_processes': 0,
        'background_processes':1
    }
    @staticmethod
    def get_by_component(name):
        try:
            return Chargable.objects.get(component=Chargable.components[name])
        except:
            return None

    @staticmethod
    def get_by_id(id):
        try:
            return Chargable.objects.get(component=id)
        except:
            return None

    def __str__(self):
        reverse = dict((v,k) for k, v in self.components.iteritems())
        return reverse[self.component]


class AllocationChange(models.Model):
    class Meta:
        db_table = 'allocation_change'

    application = models.ForeignKey(Application)
    chargable = models.ForeignKey(Chargable, null=True)
    quantity = models.IntegerField()
    billed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

class ProxyCache(models.Model):
    class Meta:
        db_table = 'proxycache'

    application = models.ForeignKey(Application)
    host = models.CharField(max_length=255)

    @staticmethod
    def get_proxycache_hosts_by_application_name(name):
        return ProxyCache.get_proxycache_hosts_by_application(Application.get_by_name(name))

    @staticmethod
    def get_proxycache_hosts_by_application(application):
        try:
            return [proxycache.host for proxycache in application.proxycache_set.all()]
        except:
            return None

class VirtualHost(models.Model):
    class Meta:
        db_table = 'virtualhost'
        unique_together = [('application', 'virtualhost')]

    application = models.ForeignKey(Application)
    virtualhost = models.CharField(max_length=255)

    @staticmethod
    def get_virtualhosts_by_application_name(name):
        return VirtualHost.get_virtualhosts_by_application(Application.get_by_name(name))

    @staticmethod
    def get_virtualhosts_by_application(application):
        try:
            return [virtualhost.virtualhost for virtualhost in application.virtualhost_set.all()]
        except:
            return None

class BillingEvent(models.Model):
    class Meta:
        db_table = 'billingevent'

    email = models.CharField(max_length=255)
    customer_id = models.CharField(max_length=255)
    application_name = models.CharField(max_length=255)
    chargable_name = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    cents = models.IntegerField()
    success = models.BooleanField()
    memo = models.CharField(max_length=255, blank=True, null=True)

class SubscriptionType(models.Model):
    class Meta:
        db_table = 'subscriptiontype'

    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    price = models.IntegerField(blank=True, null=True)

    @staticmethod
    def get_by_name(name):
        return SubscriptionType.objects.get(name=name)

class Subscription(models.Model):
    class Meta:
        db_table = 'subscription'

    application = models.ForeignKey(Application)
    subscription_type = models.ForeignKey(SubscriptionType)
    price = models.IntegerField(blank=True, null=True, default=0)
    enabled = models.DateTimeField(auto_now_add=True)
    disabled = models.DateTimeField(blank=True, null=True, default=None)

    @staticmethod
    def subscribe(application, subscription_name, price=None):
        assert not Subscription.is_subscribed(application, subscription_name)
        subscription_type = SubscriptionType.get_by_name(subscription_name)
        if price == None:
            price = subscription_type.price
        Subscription(application=application, subscription_type=subscription_type, price=price).save()

    @staticmethod
    def is_subscribed(application, subscription_name):
        subscription_type = SubscriptionType.get_by_name(subscription_name)
        return Subscription.objects.filter(application=application, subscription_type=subscription_type, disabled=None).exists()

    @staticmethod
    def unsubscribe(application, subscription_name):
        subscription_type = SubscriptionType.get_by_name(subscription_name)
        for s in Subscription.objects.filter(application=application, subscription_type=subscription_type, disabled=None):
            s.disabled = datetime.now()
            s.save()

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'djangy',
        'USER': 'djangy',
        'PASSWORD': 'password goes here',
        'HOST': '',
        'PORT': ''
    }
}

INSTALLED_APPS = (
    'management_database',
    'south'
)

########NEW FILE########
__FILENAME__ = application_api
# Standard Python libraries
import os, re
# Djangy libraries installed in our virtualenv
from djangy_server_shared import *
from management_database.models import Application, Process, Chargable, Subscription
# Libraries within this package
import exceptions

open_log_file(os.path.join(LOGS_DIR, 'master_api.log'), 0600)

def retrieve_logs(application_name):
    return run_external_program([os.path.join(MASTER_SETUID_DIR, 'run_retrieve_logs'), 'application_name', application_name])['stdout_contents']

def name_available(name):
    """ Checks for application name availability. """
    if Application.get_by_name(name):
        return False
    else:
        return (re.match('^[A-Za-z][A-Za-z0-9]{4,14}$', name) != None) \
            and not (name in RESERVED_APPLICATION_NAMES)

def toggle_debug(application_name, debug):
    cmd = [os.path.join(MASTER_SETUID_DIR, 'run_allocate'), 'application_name', application_name, 'debug', str(debug)]
    run_external_program(cmd)

def update_application_allocation(application_name, changes):
    allocations = {
        'application_processes':'num_procs',
        'background_processes':'celery_procs'
    }
    try:
        application = Application.get_by_name(application_name)
        cmd = [os.path.join(MASTER_SETUID_DIR, 'run_allocate'), 'application_name', application_name]
        for key in changes.keys():
            if allocations.get(key):
                cmd += [str(allocations[key]), str(changes[key])]

        result = run_external_program(cmd)
        if external_program_encountered_error(result):
            raise exceptions.UpdateAllocationException(result['exit_code'], application_name)

        for key in changes.keys():
            if allocations.get(key):
                try:
                    application.report_allocation_change(Chargable.get_by_component(key), str(changes[key]))
                except Exception as e:
                    log_error_message(e)

    except Exception as e:
        log_last_exception()
        logging.error(e)
        return False
    return True

def _call_proxycache_manager(application_name):
    return run_external_program([os.path.join(MASTER_SETUID_DIR, 'run_configure_proxycache'), 'application_name', application_name])

def add_domain_name(application_name, domain_name):
    Application.get_by_name(application_name).add_domain_name(domain_name)
    result = _call_proxycache_manager(application_name)
    if external_program_encountered_error(result):
        raise exceptions.AddDomainException(result['exit_code'], application_name, domain_name)

def delete_domain_name(application_name, domain_name):
    Application.get_by_name(application_name).delete_domain_name(domain_name)
    result = _call_proxycache_manager(application_name)
    if external_program_encountered_error(result):
        raise exceptions.DeleteDomainException(result['exit_code'], application_name, domain_name)

def enable_server_cache(application_name):
    application = Application.get_by_name(application_name)
    application.enable_server_cache()
    result = _call_proxycache_manager(application_name)
    assert not external_program_encountered_error(result)

def disable_server_cache(application_name):
    application = Application.get_by_name(application_name)
    application.disable_server_cache()
    result = _call_proxycache_manager(application_name)
    assert not external_program_encountered_error(result)

def add_application(application_name, email, pubkey):
    result = run_external_program([ \
        os.path.join(MASTER_SETUID_DIR, 'run_add_application'), \
        'application_name', application_name, 'email', email, 'pubkey', pubkey])
    if external_program_encountered_error(result):
        raise exceptions.AddApplicationException(result['exit_code'], application_name, email, pubkey)

def remove_application(application_name):
    result = run_external_program([ \
        os.path.join(MASTER_SETUID_DIR, 'run_delete_application'), \
        'application_name', application_name])
    if external_program_encountered_error(result):
        raise exceptions.RemoveApplicationException(result['exit_code'], application_name)

def get_application_log(application_name, log_name='django.log'):
    result = run_external_program([ \
        os.path.join(MASTER_SETUID_DIR, 'run_get_application_log'), \
        'application_name', application_name, \
        'log_name', log_name])
    if external_program_encountered_error(result):
        return '[Log not found]'
    else:
        return result['stdout_contents']

def command(application_name, cmd, *args):
    result = run_external_program([ \
        os.path.join(MASTER_SETUID_DIR, 'run_command'), \
        'application_name', application_name, \
        'command', cmd] + list(args))
    return result['stdout_contents']

def add_ssh_public_key(email, ssh_public_key):
    result = run_external_program([ \
        os.path.join(MASTER_SETUID_DIR, 'run_add_ssh_public_key'), \
        'email', email, \
        'ssh_public_key', ssh_public_key])
    assert not external_program_encountered_error(result)

def remove_ssh_public_key(email, ssh_public_key_id):
    result = run_external_program([ \
        os.path.join(MASTER_SETUID_DIR, 'run_remove_ssh_public_key'), \
        'email', email, \
        'ssh_public_key_id', ssh_public_key_id])
    assert not external_program_encountered_error(result)

########NEW FILE########
__FILENAME__ = billing_api
# Standard Python libraries
import datetime
# Djangy libraries installed in our virtualenv
from djangy_server_shared import * # referenced?
from management_database.models import User, AllocationChange, Chargable, BillingEvent, Subscription
# Libraries within this package
from devpayments import DevPayException
import exceptions, devpayments
import application_api

def update_billing_info(email, info):
    def _unpack_customer_info():
        return {
            'first_name':info.get('first_name', ''),
            'last_name':info.get('last_name', ''),
            'email':email
        }

    def _unpack_billing_info():
        return {
            'number':info['cc_number'],
            'exp_month':info['expiration_month'],
            'exp_year':info['expiration_year'],
            'cvc':info['cvv']
        }

    def _create_new_customer():
        devpay = devpayments.Client(DEVPAYMENTS_API_KEY)
        try:
            result = devpay.createCustomer(
                mnemonic = _unpack_customer_info()['email'],
                card = _unpack_billing_info()
            )
            user.customer_id = result.id
            user.save()
        except DevPayException as e:
            return e.message
        return True

    def _update_customer():
        devpay = devpayments.Client(DEVPAYMENTS_API_KEY)
        try:
            result = devpay.updateCustomer(
                id = user.customer_id,
                mnemonic = _unpack_customer_info()['email'],
                card = _unpack_billing_info()
            )
            user.customer_id = result.id
            user.save()
        except DevPayException as e:
            return e.message
        return True

    user = User.get_by_email(email)
    if not user:
        raise exceptions.UserNotFoundException(email)
    message = True
    if user.customer_id == '-1' or user.customer_id == '':
        try:
            result = _create_new_customer()
            if True != result:
                message = result
        except Exception as e:
            log_error_message(e)
            return "Our system encountered an error.  Please contact support@djangy.com."
    else:
        try:
            result = _update_customer()
            if True != result:
                message = result
        except Exception as e:
            log_error_message(e)
            return "Our system encountered an error.  Please contact support@djangy.com."

    try:
        cust_info = _unpack_customer_info()
        user.first_name = cust_info.get('first_name', '')
        user.last_name = cust_info.get('last_name', '')
        user.save()
    except Exception as e:
        log_error_message(e)
        return "Our system encountered an error.  Please contact support@djangy.com."
    return message

def retrieve_billing_info(user):
    customer_id = user.customer_id
    if customer_id == '-1' or customer_id == '':
        return None
    try:
        devpay = devpayments.Client(DEVPAYMENTS_API_KEY)
        result = devpay.retrieveCustomer(id=customer_id)
        last4 = result.active_card.get('last4', '')
        usage = ''
        try:
            usage = result.next_recurring_charge.get('amount', '')
        except:
            pass
        bill_date = ''
        try:
            bill_date = result.next_recurring_charge.get('date', '')
        except:
            pass
        if last4 != '':
            last4 = "**** **** **** %s" % last4
        return {
            'first_name':user.first_name,
            'last_name':user.last_name,
            'cc_number':last4,
            'usage':usage,
            'bill_date':bill_date
        }
    except DevPayException as e:
        log_error_message(e.message)
        return None
    except Exception as e:
        log_error_message(e)
        return None

def report_all_usage():
    emails = [user.email for user in User.objects.all()]

    for email in emails:
        report_user_usage(email)

def report_user_usage(email):
    user = User.get_by_email(email)
    if not user:
        raise exceptions.UserNotFoundException(email)
    for application in user.application_set.all():
        changes = AllocationChange.objects.filter(application=application).filter(billed=False)
        if changes.count() < 1:
            continue
        log_info_message("for application %s, reporting %s changes" % (application, changes.count()))
        for chargable in Chargable.objects.all():
            total_seconds = 0.0
            total_cents = 0.0
            # only look at allocs from before one minute ago
            now = datetime.datetime.now() - datetime.timedelta(seconds=60)
            allocs = list(changes.filter(chargable=chargable).filter(timestamp__lt=now).order_by('-timestamp'))
            if len(allocs) < 1:
                continue
            latest = allocs[-1]
            latest_copy = AllocationChange(application = application, chargable = chargable, quantity = latest.quantity, timestamp = now)
            latest_copy.save()
            allocs.insert(0, latest_copy)
            for alloc in allocs:
                if alloc == latest_copy:
                    continue
                diff = (now - alloc.timestamp).seconds
                if chargable.component == Chargable.components['application_processes']:
                    # the (alloc.quantity - 1) is to ensure the first process is free
                    price = (diff * (alloc.quantity - 1) * (chargable.price / 3600.0))
                else:
                    price = (diff * (alloc.quantity) * (chargable.price / 3600.0))
                total_cents += price
                total_seconds += diff
                now = alloc.timestamp
                alloc.billed = True
            total_hours = (total_seconds / 3600) + 1
            result = report_usage(user, total_cents, memo="%s hours for %s" % (total_hours, chargable))
            if result:
                [alloc.save() for alloc in allocs]
                be = BillingEvent(
                    email = email,
                    customer_id = user.customer_id,
                    application_name = application.name,
                    chargable_name = str(chargable),
                    cents = total_cents,
                    success = True,
                    memo = "devpayments dump: %s" % str(result)
                )
                be.save()
                log_info_message("Reported %s cents for %s for application %s" % (total_cents, chargable, application.name))
            else:
                be = BillingEvent(
                    email = email,
                    customer_id = user.customer_id,
                    application_name = application.name,
                    chargable_name = str(chargable),
                    cents = total_cents,
                    success = False,
                    memo = "devpayments dump: %s" % str(result)
                )
                be.save()
                log_error_message("Reporting failed for %s cents for %s for application %s: %s" % (total_cents, chargable, application.name, result))

def report_usage(user, quantity, memo=""):
    devpay = devpayments.Client(DEVPAYMENTS_API_KEY)
    try:
        result = devpay.billCustomer(
            id = user.customer_id,
            amount = int(quantity),
            currency = 'usd'
        )
        return result
    except Exception as e:
        log_error_message(e)
        return False

def update_devpayments_subscription(user):
    total_cents = sum([sub.price for sub in user.get_active_subscriptions()])
    customer_id = user.customer_id

    devpay = devpayments.Client(DEVPAYMENTS_API_KEY)
    try:
        result = devpay.updateCustomer(
            id = user.customer_id,
            subscription = {
                'amount':total_cents,
                'per':'month',
                'currency':'usd'
            }
        )
        return result
    except Exception as e:
        log_error_message(e)
        return False

########NEW FILE########
__FILENAME__ = exceptions
class AddApplicationException(Exception):
    """Error adding application."""
    def __init__(self, result, application_name, email, pubkey):
        self.result = result
        self.application_name = application_name
        self.email = email
        self.pubkey = pubkey
    def __str__(self):
        return 'Error adding application.  Return code: %i, application_name: "%s", email: "%s", pubkey: "%s"' % \
            (self.result, self.application_name, self.email, self.pubkey)

class RemoveApplicationException(Exception):
    """Error removing application."""
    def __init__(self, result, application_name):
        self.result = result
        self.application_name = application_name
    def __str__(self):
        return 'Error removing application.  Return code: %i, application_name: "%s".' % (self.result, self.application_name)

class UserNotFoundException(Exception):
    """ Error finding user """
    def __init__(self, email):
        self.email = email
    def __str__(self):
        return "Error finding user with email: %s." % self.email

class UpdateBillingException(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class ComponentNotFoundException(Exception):
    def __init__(self, component):
        self.component = component
    def __str__(self):
        return "Error looking up component: %s" % self.component

class UpdateAllocationException(Exception):
    def __init__(self, result, application_name):
        self.result = result
        self.application_name = application_name
    def __str__(self):
        return "Error updating allocation. Return code: %i, application_name: %s" % (self.result, self.application_name)

class AddDomainException(Exception):
    def __init__(self, result, application_name, domain_name):
        self.result = result
        self.application_name = application_name
        self.domain_name = domain_name
    def __str__(self):
        return "Error adding domain '%s' to application '%s'. Return code: %i" % (self.domain_name, self.application_name, self.result)

class DeleteDomainException(Exception):
    def __init__(self, result, application_name, domain_name):
        self.result = result
        self.application_name = application_name
        self.domain_name = domain_name
    def __str__(self):
        return "Error deleting domain '%s' to application '%s'. Return code: %i" % (self.domain_name, self.application_name, self.result)

########NEW FILE########
__FILENAME__ = add_application
#!/usr/bin/env python

from shared import *
import _mysql, re
from ConfigParser import RawConfigParser
from management_database.models import User, Application

def main():
    check_trusted_uid(sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, ['application_name', 'email', 'pubkey'])
    add_application(**kwargs)

def gen_uids_gid(app_id):
    setup_uid = (app_id * 3) + 100000
    return {
        'setup_uid': setup_uid,
        'web_uid'  : setup_uid + 1,
        'cron_uid' : setup_uid + 2,
        'app_gid'  : setup_uid
    }

def add_application(application_name, email, pubkey):
    """ Add the application specified by application_name and a corresponding database, owned by the user with the email address specified. """

    # Claim the application name
    ActiveApplicationName(name=application_name).save()

    user = User.get_by_email(email)

    # generate a secure password
    db_password = gen_password()

    # create the application row
    app = Application()
    app.name = application_name
    app.account = user
    app.db_name = application_name
    app.db_username = application_name
    app.db_password = db_password
    app.db_host = DEFAULT_DATABASE_HOST
    app.num_procs = 1
    app.save()

    # generate user and group ids to run as
    uids_gid = gen_uids_gid(app.id)
    app.setup_uid = uids_gid['setup_uid']
    app.web_uid   = uids_gid['web_uid']
    app.cron_uid  = uids_gid['cron_uid']
    app.app_gid   = uids_gid['app_gid']
    app.save()

    # enable git push
    create_git_repository(application_name)
    add_ssh_public_key(user, pubkey)

    # allocate a proxycache host for the application -- improve on this later
    ProxyCache(application = app, host = DEFAULT_PROXYCACHE_HOST).save()

    # assign virtualhost on which to listen for application
    VirtualHost(application = app, virtualhost = application_name + '.djangy.com').save()

    # allocate the application to a worker host
    # Note: this must happen after ProxyCache and VirtualHost are filled in. 
    allocate_workers(app)

    # create the database
    db = _mysql.connect(
        host = DEFAULT_DATABASE_HOST,
        user = DATABASE_ROOT_USER, 
        passwd = DATABASE_ROOT_PASSWORD)

    try: # try to remove the user if it already exists
        db.query(""" DROP USER '%s'@'%%';""" % application_name)
    except:
        pass

    db.query("""
        CREATE USER '%s'@'%%' IDENTIFIED BY '%s';""" % (application_name, db_password))

    try: # try to drop the database in case it exists
        db.query(""" DROP DATABASE %s;""" % application_name)
    except:
        pass

    db.query("""
        CREATE DATABASE %s;""" % application_name)

    db.query("""
        USE %s""" % application_name)

    db.query("""
        GRANT ALL ON %s.* TO '%s'@'%%';""" % (application_name, application_name))

    return True

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = add_ssh_public_key
#!/usr/bin/env python

from shared import *

def main():
    check_trusted_uid(sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, ['email', 'ssh_public_key'])
    user = User.get_by_email(kwargs['email'])
    add_ssh_public_key(user, kwargs['ssh_public_key'])

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = allocate
#!/usr/bin/env python
#
# python application_name <x> [num_procs <x>] [proc_num_threads <x>] [proc_mem_mb <x>] [proc_stack_mb <x>] [debug <x>]
#

from shared import *
from management_database.models import Application, Process
from django.core.exceptions import ObjectDoesNotExist

def main():
    check_trusted_uid(sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, ['application_name'], \
        ['num_procs', 'proc_num_threads', 'proc_mem_mb', \
        'proc_stack_mb', 'debug', 'celery_procs'])
    try:
        allocate_application(**kwargs)
    except:
        log_last_exception()
        print 'Allocation failed for application "%s".' % kwargs['application_name']
        sys.exit(1)

def allocate_application(application_name, num_procs=None, proc_num_threads=None, proc_mem_mb=None, proc_stack_mb=None, debug=None, celery_procs=None):
    application_info = Application.get_by_name(application_name)

    if num_procs != None:
        application_info.num_procs = int(num_procs)
    if celery_procs != None:
        application_info.celery_procs = int(celery_procs)
    # Adjust allocation parameters relevant to each individual process of an
    # application: num threads, total memory, stack size, debug
    if proc_num_threads:
        application_info.proc_num_threads = int(proc_num_threads)
    if proc_mem_mb:
        application_info.proc_mem_mb = int(proc_mem_mb)
    if proc_stack_mb:
        application_info.proc_stack_mb = int(proc_stack_mb)
    if debug:
        application_info.debug = (debug == 'True')

    # Save the updated settings
    application_info.save()

    # Num processes is done differently because it requires
    # reallocation of processes to hosts, and must directly
    # contact hosts from which a process is removed.
    if (num_procs != None) or (celery_procs != None):
        allocate_workers(application_info)
    else:
        # Apply the settings to all deployed workers
        call_worker_managers_allocate(application_name)
        # (Don't need to update proxycache_managers)
        #call_proxycache_managers_configure(application_name)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = change_password
import sys
from hashlib import md5
from management_database import User

def hash_password(email, password):
    return md5("%s:%s" % (email, password)).hexdigest()

def main(email, password):
    try:
        user = User.get_by_email(email)
        user.passwd = hash_password(email, password)
        user.save()
    except Exception as e:
        print "Exception: %s" % e

    print "Success."

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: python change_password.py <email> <new_password>"
    email = str(sys.argv[1])
    password = str(sys.argv[2])
    main(email, password)

########NEW FILE########
__FILENAME__ = command
#!/usr/bin/env python
#
# Run a simple manage.py command as an application's setup_uid.
#

from shared import *

ALLOWED_CMDS = [
    'syncdb',
    'migrate',
    'createsuperuser'
]

def main():
    check_trusted_uid(sys.argv[0])

    # Check command line arguments
    if not (len(sys.argv) >= 5 \
    and sys.argv[1] == 'application_name' \
    and is_valid_django_app_name(sys.argv[2]) \
    and sys.argv[3] == 'command'
    and (sys.argv[4] in ALLOWED_CMDS)):
        print_or_log_usage("Usage: %s application_name <x> command <x> [...]" % sys.argv[0])
        sys.exit(1)

    # Extract command line arguments
    application_name = sys.argv[2]
    command = ['python', 'manage.py'] + sys.argv[4:]
    stdin_contents = None

    # handle the special case of adding a superuser (piping python code to python manage.py shell)
    if sys.argv[4] == 'createsuperuser':
        command = ['python', 'manage.py', 'shell']
        username = 'admin'
        email = ''
        password = gen_password()

        stdin_contents = """
from django.contrib.auth.models import User
try:
    found = User.objects.get(username='admin')
    found.delete()
except Exception, e:
    pass

User.objects.create_superuser('%s', '%s', '%s')

""" % (username, email, password)
        status = run_command(application_name, command, stdin_contents = stdin_contents, pass_stdout = False)
        if status == 0:
            print "Superuser '%s' created with password: '%s'" % (username, password)
        sys.exit(status)

    # Run the actual command as the application's setup_uid
    sys.exit(run_command(application_name, command, stdin_contents = stdin_contents))

def run_command(application_name, args, stdin_contents = None, pass_stdout = True):
    try:
        check_application_name(application_name)
        # Look up application info in the database
        application_info = Application.get_by_name(application_name)
        bundle_version   = application_info.bundle_version
        setup_uid        = application_info.setup_uid
        app_gid          = application_info.app_gid
        # Validate UID/GID
        check_setup_uid(setup_uid)
        check_app_gid(app_gid)
        # Compute the bundle path
        bundle_name         = '%s-%s' % (application_name, bundle_version)
        bundle_path         = os.path.join(BUNDLES_DIR, bundle_name)
        # Find the django project within the repository; this is where
        # manage.py needs to be run from
        django_project_path = find_django_project(os.path.join(bundle_path, 'application'))
        # Run the command
        result              = run_external_program(list(args), \
                                  cwd=django_project_path, pass_stdout=pass_stdout, stderr_to_stdout=True, \
                                  preexec_fn=gen_preexec(bundle_name, setup_uid, app_gid), stdin_contents = stdin_contents)
        return result['exit_code']
    except Exception as e:
        log_last_exception()
        print str(e)
        sys.exit(2)

def gen_preexec(bundle_name, uid, gid):
    """Generate a preexec_fn to be passed to run_external_program() which (a) sets up the environment, and (b) sets the uid/gid"""
    def command_preexec_fn():
        os.environ.clear()
        virtual_env_dir = os.path.join(BUNDLES_DIR, '%s/python-virtual' % bundle_name)
        os.environ['PATH'] = '%s:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' % os.path.join(virtual_env_dir, 'bin')
        os.environ['VIRTUAL_ENV'] = virtual_env_dir
        set_uid_gid(uid, gid)
    return command_preexec_fn

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = configure_proxycache
#!/usr/bin/env python
#
# python configure_proxycache.py application_name <x>
#

from shared import *
from management_database.models import Application, VirtualHost

def main():
    check_trusted_uid(sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, ['application_name'])
    try:
        call_proxycache_managers_configure(kwargs['application_name'])
    except:
        log_last_exception()
        print 'Configuring proxycache for application "%s" failed.' % kwargs['application_name']
        sys.exit(1)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = copy_etc_hosts
#!/usr/bin/env python
#
# Copy the /etc/hosts file to all other Djangy servers.
#
# We assume there is a line in /etc/hosts of the form "# djangy internal\n",
# and all host lines below that specify the internal IP address of all the
# Djangy servers.  There may be duplicates, e.g., master1.srv.djangy.com and
# worker1.srv.djangy.com might have the same IP address.  We only copy the
# /etc/hosts file to a given IP address once.
#

import re, subprocess

def read_lines(path):
    with open(path, 'r') as f:
        return f.readlines()

def get_hosts():
    in_djangy_section = False
    host_addresses = []
    for etc_hosts_line in read_lines('/etc/hosts'):
        if re.match(r'\s*#\s*djangy\s*internal.*\n', etc_hosts_line):
            in_djangy_section = True
        elif in_djangy_section:
            matches = re.match(r'^\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+', etc_hosts_line)
            if matches:
                host_addresses.append(matches.group(1))
    return set(host_addresses)

if __name__ == '__main__':
    for host in get_hosts():
        print host
        subprocess.call(['scp', '/etc/hosts', host + ':/etc/hosts'])

########NEW FILE########
__FILENAME__ = delete_application
#!/usr/bin/env python
#
# Delete an application.
#

from shared import *
import _mysql
from management_database.models import Application

def main():
    check_trusted_uid(program_name = sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, ['application_name'])
    application_name = kwargs['application_name']
    try:
        # Look up the application
        application = Application.get_by_name(application_name)
        # Disable the application to the outside world
        call_proxycache_managers_delete_application(application_name)
        # Stop running the application
        call_worker_managers_delete_application(application_name)
        # Remove the git repository
        try:
            shutil.rmtree(os.path.join(REPOS_DIR, application_name + ".git"))
        except:
            log_last_exception()
        # Remove the database
        db = _mysql.connect(
            host = application.db_host,
            user = DATABASE_ROOT_USER, 
            passwd = DATABASE_ROOT_PASSWORD)
        try: # try to remove the user if it already exists
            db.query(""" DROP USER '%s'@'%%';""" % application_name)
        except:
            pass
        try: # try to drop the database in case it exists
            db.query(""" DROP DATABASE %s;""" % application_name)
        except:
            pass
        # Mark the application as deleted
        application.mark_deleted()
    except:
        log_last_exception()
        print 'Remove failed for application "%s".' % application_name
        sys.exit(1)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = deploy
#!/usr/bin/env python

from ConfigParser import RawConfigParser
from mako.lookup import TemplateLookup
from shared import *

def main():
    check_trusted_uid(sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, ['application_name'])
    deploy(**kwargs)

def deploy(application_name):
    print ''
    print ''
    print 'Welcome to Djangy!'
    print ''
    print 'Deploying project %s.' % application_name
    print ''

    try:
        bundle_version = create_latest_bundle_via_db(application_name)
        print 'Deploying to worker hosts...',
        call_worker_managers_allocate(application_name)
        call_proxycache_managers_configure(application_name)
        log_info_message("Successfully deployed application '%s'!" % application_name)
        print 'Done.'
        print ''
    except BundleAlreadyExistsException as e:
        log_last_exception()
        print 'WARNING: ' + str(e)
        print 'Commit and push some changes to force redeployment.'
        print ''
    except ApplicationNotInDatabaseException as e:
        log_last_exception()
        print 'ERROR: ' + str(e)
        print ''
    except InvalidApplicationNameException as e:
        log_last_exception()
        print 'ERROR: ' + str(e)
        print ''
    except DjangoProjectNotFoundException as e:
        log_last_exception()
        print 'ERROR: No django project found in the git repository.'
        print ''
    except:
        log_last_exception()
        print 'Internal error, please contact support@djangy.com'
        print ''

def create_latest_bundle_via_db(application_name):
    """Create a bundle from the latest version of an application.  Fetches
    details like administrative email address and database credentials from
    the management database."""

    check_application_name(application_name)

    # Extract application info from management database
    try:
        application_info = Application.get_by_name(application_name)
        user_info        = application_info.account
        bundle_params = {
            'application_name': application_name,
            'admin_email'     : user_info.email,
            'db_host'         : application_info.db_host,
            'db_port'         : application_info.db_port,
            'db_name'         : application_info.db_name,
            'db_username'     : application_info.db_username,
            'db_password'     : application_info.db_password,
            'setup_uid'       : application_info.setup_uid,
            'web_uid'         : application_info.web_uid,
            'cron_uid'        : application_info.cron_uid,
            'app_gid'         : application_info.app_gid,
            'celery_procs'    : application_info.celery_procs,
        }
        # Also need to query DB for which hosts to run on; and
        # resource allocations may be heterogenous across hosts
        check_setup_uid(bundle_params['setup_uid'])
        check_web_uid  (bundle_params['web_uid'  ])
        check_cron_uid (bundle_params['cron_uid' ])
        check_app_gid  (bundle_params['app_gid'  ])
    except Exception as e:
        log_last_exception()
        print str(e)
        # Couldn't find application_name in the management database!
        raise ApplicationNotInDatabaseException(application_name)

    # Create the bundle.
    bundle_version = create_latest_bundle(**bundle_params)

    # Update latest bundle version in the database.
    application_info.bundle_version = bundle_version
    application_info.save()

    return bundle_version

def create_latest_bundle(application_name, admin_email, db_host, db_port, db_name, db_username, db_password, \
                         setup_uid, web_uid, cron_uid, app_gid, celery_procs):
    """Create a bundle from the latest version of an application.  Requires
    administrative email address and database credentials as arguments."""

    # Put application code in <bundle path>/application
    # and user-supplied config files in <bundle path>/config
    print 'Cloning git repository...',
    (bundle_version, bundle_name, bundle_application_path) = clone_repo_to_bundle(application_name)
    print 'Done.'
    print ''

    bundle_path = os.path.join(BUNDLES_DIR, bundle_name)
    recursive_chown_chmod(bundle_path, 0, app_gid, '0750')

    # Find the Django project directory
    django_project_path = find_django_project(os.path.join(bundle_path, 'application'))
    django_project_module_name = os.path.basename(django_project_path)

    # Rename the user's settings module to something that's unlikely to conflict
    if os.path.isfile(os.path.join(django_project_path, 'settings', '__init__.py')):
        user_settings_module_name = '__init__%s' % bundle_version
        os.rename(os.path.join(django_project_path, 'settings', '__init__.py'), \
                  os.path.join(django_project_path, 'settings', user_settings_module_name + '.py'))
    elif os.path.isfile(os.path.join(django_project_path, 'settings.py')):
        user_settings_module_name = 'settings_%s' % bundle_version
        os.rename(os.path.join(django_project_path, 'settings.py'), \
                  os.path.join(django_project_path, user_settings_module_name + '.py'))

    # Create production settings.py file in <bundle path>/application/.../settings.py
    # (code also exists in worker_manager.deploy)
    print 'Creating production settings.py file...',
    if os.path.isdir(os.path.join(django_project_path, 'settings')):
        settings_path = os.path.join(django_project_path, 'settings', '__init__.py')
    else:
        settings_path = os.path.join(django_project_path, 'settings.py')
    generate_config_file('generic_settings', settings_path,
                         user_settings_module_name  = user_settings_module_name,
                         django_project_module_name = django_project_module_name,
                         db_host                    = db_host,
                         db_port                    = db_port,
                         db_name                    = db_name,
                         db_username                = db_username,
                         db_password                = db_password,
                         bundle_name                = bundle_name,
                         debug                      = False,
                         celery_procs               = None,
                         application_name           = application_name)
    os.chown(settings_path, 0, app_gid)
    os.chmod(settings_path, 0750)
    print 'Done.'
    print ''

    # The create_virtualenv.py program calls setuid() to run as setup_uid
    python_virtual_path = os.path.join(bundle_path, 'python-virtual')
    os.mkdir(python_virtual_path, 0770)
    os.chown(python_virtual_path, 0, app_gid)
    os.chmod(python_virtual_path, 0770)
    sys.stdout.flush()
    run_external_program([PYTHON_BIN_PATH, os.path.join(MASTER_MANAGER_SRC_DIR, 'uid_application_setup/create_virtualenv.py'), \
        'application_name', application_name, 'bundle_name', bundle_name, \
        'setup_uid', str(setup_uid), 'app_gid', str(app_gid)], \
        pass_stdout=True, cwd=bundle_application_path)

    os.umask(0227)

    # Save the bundle info used by worker_manager to generate config files
    print 'Saving bundle info...',
    django_admin_media_path = get_django_admin_media_path(bundle_path)
    admin_media_prefix='/admin_media'
    BundleInfo( \
        django_project_path       = django_project_path, \
        django_admin_media_path   = django_admin_media_path, \
        admin_media_prefix        = admin_media_prefix, \
        admin_email               = admin_email, \
        setup_uid                 = setup_uid, \
        web_uid                   = web_uid, \
        cron_uid                  = cron_uid, \
        app_gid                   = app_gid, \
        user_settings_module_name = user_settings_module_name, \
        db_host                   = db_host, \
        db_port                   = db_port, \
        db_name                   = db_name, \
        db_username               = db_username, \
        db_password               = db_password
        ).save_to_file(os.path.join(bundle_path, 'config', 'bundle_info.config'))
    print 'Done.'
    print ''

    recursive_chown_chmod(bundle_path, 0, app_gid, '0750')
    # TODO: don't chmod everything +x, only what needs it.

    return bundle_version

### Also exists in worker_manager.deploy ###
def generate_config_file(__template_name__, __config_file_path__, **kwargs):
    """Generate a bundle config file from a template, supplying arguments
    from kwargs."""

    # Load the template
    lookup = TemplateLookup(directories = [WORKER_TEMPLATE_DIR])
    template = lookup.get_template(__template_name__)
    # Instantiate the template
    instance = template.render(**kwargs)
    # Write the instantiated template to the bundle
    f = open(__config_file_path__, 'w')
    f.write(instance)
    f.close()

def get_django_admin_media_path(bundle_path):
    try:
        # Currently assumes python2.6
        f = open(os.path.join(bundle_path, 'python-virtual/lib/python2.6/site-packages/easy-install.pth'))
        contents = f.read()
        f.close()
        django_path = re.search('^(.*/Django-.*\.egg)$', contents, flags=re.MULTILINE).group(0)
        admin_media_path = os.path.join(django_path, 'django/contrib/admin/media')
        return admin_media_path
    except:
        return os.path.join(bundle_path, 'directory_that_does_not_exist')

def clone_repo_to_bundle(application_name):
    """Try to clone an application's git repository and put the latest code
    into a new bundle.  Throws BundleAlreadyExistsException if a bundle
    directory already exists for the latest version in the repository."""

    # Create temporary directory in which to git clone
    master_repo_path = os.path.join(REPOS_DIR, application_name + '.git')
    temp_repo_path = tempfile.mkdtemp('.git', 'tmp-', BUNDLES_DIR)
    os.chown(temp_repo_path, GIT_UID, GIT_UID)
    os.chmod(temp_repo_path, 0700)
    # git clone and read current version of git repository
    result = run_external_program([PYTHON_BIN_PATH, os.path.join(MASTER_MANAGER_SRC_DIR, 'uid_git/clone_repo.py'), master_repo_path, temp_repo_path])
    stdout = result['stdout_contents'].split('\n')
    if len(stdout) < 1:
        git_repo_version = ''
    else:
        git_repo_version = stdout[0]
    # Validate git_repo_version
    if result['exit_code'] != 0 or not validate_git_repo_version(git_repo_version):
        raise GitCloneException(application_name, temp_repo_path)
    # Compute bundle path
    bundle_version = BUNDLE_VERSION_PREFIX + git_repo_version
    bundle_name = application_name + '-' + bundle_version
    bundle_path = os.path.join(BUNDLES_DIR, bundle_name)
    # Check if bundle already exists
    if os.path.exists(bundle_path):
        shutil.rmtree(temp_repo_path)
        raise BundleAlreadyExistsException(bundle_name)
    # Make bundle directory
    bundle_config_path = os.path.join(bundle_path, 'config')
    os.makedirs(bundle_config_path)
    os.chmod(bundle_path, 0700)
    # Move checked-out repo to bundle
    bundle_application_path = get_bundle_application_path(application_name, temp_repo_path, bundle_path)
    os.makedirs(bundle_application_path)
    os.rename(temp_repo_path, bundle_application_path)
    # Copy the user-supplied configuration files to a deterministic location
    copy_normal_file(os.path.join(bundle_application_path, 'djangy.config'), os.path.join(bundle_config_path, 'djangy.config'))
    copy_normal_file(os.path.join(bundle_application_path, 'djangy.eggs'  ), os.path.join(bundle_config_path, 'djangy.eggs'  ))
    copy_normal_file(os.path.join(bundle_application_path, 'djangy.pip'   ), os.path.join(bundle_config_path, 'djangy.pip'   ))
    # Remove .git history which is not relevant in bundle
    shutil.rmtree(os.path.join(bundle_application_path, '.git'))
    # Note: bundle permissions must be adjusted by caller
    return (bundle_version, bundle_name, bundle_application_path)

def validate_git_repo_version(git_repo_version):
    return (None != re.match('^[0-9a-f]{40}$', git_repo_version))

def get_bundle_application_path(application_name, repo_path, bundle_path):
    """Given the path to a copy of the code for an application and the path
    to the bundle in which it needs to be inserted, determine the path where
    the code needs to be moved to.  The simple case is
    (bundle_path)/application/(application_name), but if the user provides a
    djangy.config file in the root of the repository, they can override
    that, e.g., (bundle_path)/application/mydir"""
    # Default: (bundle_path)/application/(application_name)
    bundle_application_path = os.path.join(bundle_path, 'application', application_name)
    # But if djangy.config file exists, look for:
    #     [application]
    #     rootdir=(some directory)
    djangy_config_path = os.path.join(repo_path, 'djangy.config')
    if is_normal_file(djangy_config_path):
        parser = RawConfigParser()
        parser.read(djangy_config_path)
        try:
            # Normalize the path relative to a hypothetical root directory,
            # then remove the leftmost / to make the path relative again.
            rootdir = os.path.normpath(os.path.join('/', parser.get('application', 'rootdir')))[1:]
            # Put the path inside the bundle's application directory;
            # normalizing will remove a rightmost / if rootdir == ''
            bundle_application_path = os.path.normpath(os.path.join(bundle_path, 'application', rootdir))
        except:
            pass
    return bundle_application_path

def is_normal_file(path):
    return not os.path.islink(path) and os.path.isfile(path)

def copy_normal_file(src_path, dest_path):
    if is_normal_file(src_path) and \
    not os.path.exists(dest_path):
        shutil.copyfile(src_path, dest_path)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = deploy_all
#!/usr/bin/env python
#
# Can be used when installing/upgrading to rebuild all bundles and deploy
# their applications.  Not very fast.
#

from shared import *

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # If the user provided arguments, look up those individual
        # applications.
        applications = []
        for application_name in sys.argv[1:]:
            applications.extend(list(Application.objects.filter(deleted=None, name=application_name)))
    else:
        # No user arguments, so deploy all applications.
        applications = Application.objects.filter(deleted=None)

    for application in applications:
        # Two step deployment (in case the process table is empty)
        run_external_program(['/srv/djangy/run/master_manager/setuid/run_deploy',
            'application_name', application.name], pass_stdout=True)
        allocate_workers(application)

########NEW FILE########
__FILENAME__ = git_serve
#!/srv/djangy/run/python-virtual/bin/python
#
# Note: doesn't import shared.ssh_and_git because this runs as the "git"
# user, which doesn't have access to write to /srv/logs/master.log...
#

from djangy_server_shared import constants
from management_database import *
import os, re, sys

def main():
    try:
        git_serve(int(sys.argv[1]))
    except:
        sys.stderr.write('Access denied.  Please email support@djangy.com for help.\n')

def git_serve(ssh_public_key_id):
    """ Serve an incoming git push/pull request.  Should only be called via ~git/.ssh/authorized_keys """
    assert os.getuid() == constants.GIT_UID
    # Usage: git_serve <id>
    # git_serve() should only be called via ~git/.ssh/authorized_keys
    # Each line of authorized_keys specifies a particular SshPublicKey.id
    # from the database as an argument to git_serve.
    users = SshPublicKey.get_users_by_public_key_id(ssh_public_key_id)
    # Look at the command git wanted to run.
    # It should be one of git-upload-pack or git-receive-pack.
    # (or their variants, 'git upload-pack' and 'git receive-pack')
    # The argument to the command is <application_name>.git
    ssh_original_command = os.environ['SSH_ORIGINAL_COMMAND']
    matches = re.match('^\s*(git(-|\s+)(?P<command>upload-pack|receive-pack))' \
        + '\s+\'(?P<application_name>[A-Za-z0-9]{1,15})\.git\'\s*$', ssh_original_command)
    command = 'git-' + matches.group('command')
    application_name = matches.group('application_name')
    # Look up the requested application, and make sure that at least one
    # user associated with the SSH key that was used has access to it.
    application = Application.get_by_name(application_name)
    if application.accessible_by_any_of(users):
        # Finally, run the git server-side command
        os.execvp('git', ['git', 'shell', '-c', "%s '/srv/git/repositories/%s.git'" % (command, application_name)])

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = import_ssh_public_keys
#!/usr/bin/env python
#
# Utility script for importing gitosis-style SSH public keys.
#
# Must be run from a directory containing <email>.pub files or you can
# specify the path to such a directory on the command line.
#
# Will reject files containing things that don't look like SSH public keys.
#

from shared import *
import os, sys

def main():
    if len(sys.argv) > 1:
        os.chdir(sys.argv[1])
    import_ssh_public_keys()

def import_ssh_public_keys():
    for filename in os.listdir('.'):
        if filename.endswith('.pub'):
            email = filename[:-4]
            try:
                user = User.get_by_email(email)
                add_ssh_public_key(user, read_contents(filename))
                print 'Added %s' % email
            except Exception as e:
                sys.stderr.write('Skipping %s (Error: %s)\n' % (filename, str(e)))
        else:
            sys.stderr.write('Skipping %s\n' % filename)

def read_contents(filename):
    f = open(filename)
    contents = f.read()
    f.close()
    return contents

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = post_receive
#!/srv/djangy/run/python-virtual/bin/python

import warnings
warnings.simplefilter("ignore")

import os, re, sys

excluded_repos = [
    'gitosis-admin',
    'djangy',
    'test',
]

if __name__ == '__main__':
    # In practice, I've observed GIT_DIR to be '.', but it could potentially
    # be something else.  So we convert it to an absolute path and then
    # remove it from the environment, because it tends to confuse other
    # git operations performed later.
    if os.environ.has_key('GIT_DIR'):
        git_repository_path = os.path.abspath(os.environ['GIT_DIR'])
        os.environ.pop('GIT_DIR')
    else:
        git_repository_path = os.getcwd()
    # Make sure we were passed an official git project repository
    match = re.match('^/srv/git/repositories/([A-Za-z][A-Za-z0-9]*)\.git$', git_repository_path);
    if match == None:
        sys.exit(1)
    application_name = match.group(1)
    # Ignore special repositories that aren't supposed to use the post-receive hook
    if application_name in excluded_repos:
        sys.exit(0)
    # Update the deployment of this application
    args = ['/srv/djangy/run/master_manager/setuid/run_deploy', 'application_name', application_name]
    os.execv(args[0], args)

########NEW FILE########
__FILENAME__ = purge_old_bundles
#!/usr/bin/env python
#
# Utility script to remove old, unused bundles from a master_manager host.
#

import os, shutil
from management_database import *

BUNDLES_ROOT = '/srv/bundles';

def main():
    current_bundle_names = set([x.name + '-' + x.bundle_version for x in Application.objects.filter(deleted=None)])
    for bundle_name in os.listdir(BUNDLES_ROOT):
        if bundle_name not in current_bundle_names:
            print 'Removing %s ...' % bundle_name
            shutil.rmtree(os.path.join(BUNDLES_ROOT, bundle_name))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = regenerate_ssh_authorized_keys
#!/usr/bin/env python

from shared import *

def main():
    check_trusted_uid(sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, [])
    regenerate_ssh_authorized_keys()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = remove_ssh_public_key
#!/usr/bin/env python

from shared import *

def main():
    check_trusted_uid(sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, ['email', 'ssh_public_key_id'])
    user = User.get_by_email(kwargs['email'])
    user.remove_ssh_public_key(kwargs['ssh_public_key_id'])
    regenerate_ssh_authorized_keys()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = retrieve_logs
#!/usr/bin/env python

from ConfigParser import RawConfigParser
from shared import *

def main():
    check_trusted_uid(sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, ['application_name'])
    retrieve_logs(**kwargs)

def retrieve_logs(application_name):
    stdout_contents_dict = call_worker_managers_retrieve_logs(application_name)
    try:
        print stdout_contents_dict.values()[0]
    except:
        pass

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = allocate_workers
from management_database import Process, WorkerHost
import copy, random
from django.db.models import Sum
from djangy_server_shared.constants import *
from djangy_server_shared import log_info_message
from call_remote import *

def _random_worker_port():
    return random.randrange(WORKER_PORT_LOWER, WORKER_PORT_UPPER)

def _random_unique_worker_port_on_host(host):
    port = _random_worker_port()
    while Process.objects.filter(host=host).filter(port=port).exists():
        port = _random_worker_port()
    return port

def allocate_workers(application):
    # Theoretically, we should only allow one application to compute
    # reallocation at a time, to prevent accidentally overloading workers. 
    # In practice, that seems overly conservative.

    log_info_message('allocate_workers("%s", %i, %i)' % (application.name, application.num_procs, application.celery_procs))

    gunicorn_updated_worker_hosts = _compute_reallocation_to_worker_hosts_update_db(application, 'gunicorn', application.num_procs)
    celery_updated_worker_hosts   = _compute_reallocation_to_worker_hosts_update_db(application, 'celery'  , application.celery_procs)
    updated_worker_hosts = list(set(gunicorn_updated_worker_hosts).union(set(celery_updated_worker_hosts)))

    # Update the worker_managers whose allocations have changed
    call_worker_managers_allocate(application.name, updated_worker_hosts)
    # Update the proxycache_managers
    call_proxycache_managers_configure(application.name)

def _compute_reallocation_to_worker_hosts_update_db(application, proc_type, new_num_procs):
    # Compute the allocation of workers to hosts
    worker_hosts__num_procs = _compute_reallocation_to_worker_hosts_read_db(application, proc_type, new_num_procs)
    # Update the Process table
    updated_worker_hosts = []

    for (worker_host, num_procs) in worker_hosts__num_procs.items():
        try:
            proc = Process.objects.get(application=application, proc_type=proc_type, host=worker_host)
            if num_procs == 0:
                proc.delete()
            elif proc.num_procs != num_procs:
                proc.num_procs = num_procs
                proc.save()
            updated_worker_hosts.append(worker_host)
        except:
            if num_procs != 0:
                port = _random_unique_worker_port_on_host(worker_host)
                proc = Process(application=application, proc_type=proc_type, host=worker_host, port=port, num_procs=num_procs)
                proc.save()
                updated_worker_hosts.append(worker_host)

    return updated_worker_hosts

# Reads the database and returns information about how processes are
# allocated to worker hosts, structured as below.
# Returns :: { <worker_host> : { 'max_procs' : int, 'total_procs': int, 'application_procs' : int } }
def _read_worker_hosts_from_db(application, proc_type):
    # worker_host -> max_procs
    worker_host__max_procs = dict((row['host'], row['max_procs']) for row in WorkerHost.objects.values('host', 'max_procs').distinct())
    # worker_host -> total num_procs
    worker_host__total_procs = dict((row['host'], row['num_procs']) for row in Process.objects.values('host').annotate(num_procs=Sum('num_procs')))
    # worker_host -> application's num_procs
    worker_host__application_procs = dict((row['host'], row['num_procs']) for row in Process.objects.filter(application=application, proc_type=proc_type).values('host', 'num_procs'))

    worker_hosts = { }
    for h in worker_host__max_procs:
        max_procs = worker_host__max_procs[h]
        total_procs = worker_host__total_procs.get(h, 0)
        application_procs = worker_host__application_procs.get(h, 0)
        worker_hosts[h] = {'max_procs': max_procs, 'total_procs': total_procs, 'application_procs': application_procs}

    return worker_hosts

# Call this method to compute an updated allocation of an application's
# processes to hosts.  Does not touch the database or workers, simply
# computes and returns a result.
#
# Tries to spread out an application's processes evenly across all available
# worker hosts, but does not rebalance existing processes.  In other words,
# if N processes need to be added, they will be added to whichever hosts
# have additional capacity and currently have the fewest processe for this
# application.  Similarly, if N processes need to be removed, they will be
# removed from those hosts which have the most processes for this
# application.
#
# application :: management_database.models.Application instance
# new_num_procs :: int -- the number of processes that should be running
#     this application after reallocation (not the number of new processes)
# Returns :: { <worker_host> : int }
#
# Note: if an entry in the return value is 0, we need to contact the
# worker_manager to tell it to stop running this application, and when we
# update the proxycache_manager, we should no longer list that worker.
def _compute_reallocation_to_worker_hosts_read_db(application, proc_type, new_num_procs):
    existing_num_procs = Process.objects.filter(application=application, proc_type=proc_type).aggregate(num_procs=Sum('num_procs'))['num_procs']
    if not existing_num_procs:
        existing_num_procs = 0
    worker_hosts = _read_worker_hosts_from_db(application, proc_type)
    # host -> application's num_procs
    process_allocation = { }
    # Project out the current allocations of processes to hosts
    for h in worker_hosts:
        application_procs = worker_hosts[h]['application_procs']
        if application_procs > 0:
            process_allocation[h] = application_procs
    # More procs?  Compute the added processes to hosts.
    if new_num_procs > existing_num_procs:
        added_num_procs = new_num_procs - existing_num_procs
        added_procs = _compute_allocation_to_worker_hosts(added_num_procs, worker_hosts)
        for h in added_procs:
            process_allocation[h] = process_allocation.get(h, 0) + added_procs[h]
    # Fewer procs?  Compute the removed processes from hosts.
    elif new_num_procs < existing_num_procs:
        removed_num_procs = existing_num_procs - new_num_procs
        removed_procs = _compute_deallocation_from_worker_hosts(removed_num_procs, worker_hosts)
        for h in removed_procs:
            if process_allocation.get(h):
                process_allocation[h] -= removed_procs[h]

    return process_allocation

# Call this method to compute which hosts to allocate num_procs more
# processes for application to.  Does not touch the database or workers,
# simply computes and returns a result.  Tries to spread out an
# application's processes evenly across all available worker hosts.
#
# num_procs_to_add :: int
# worker_hosts :: { <worker_host> : { 'max_procs' : int, 'total_procs': int, 'application_procs' : int } }
# Returns :: { <worker_host> : <num_procs_to_add> }
def _compute_allocation_to_worker_hosts(num_procs_to_add, worker_hosts):
    worker_hosts = copy.deepcopy(worker_hosts)

    # Remove hosts that are maxed out
    maxed_out_worker_hosts = []
    for h in worker_hosts:
        if worker_hosts[h]['total_procs'] >= worker_hosts[h]['max_procs']:
            maxed_out_worker_hosts.append(h)
    for h in maxed_out_worker_hosts:
        del worker_hosts[h]

    # Additional processes added to hosts :: host -> int
    added_procs = { }

    # Helper function: find the host with capacity for at least one more
    # process, that has the fewest number of processes for this application,
    # using total number of processes as a tie-breaker.
    def find_min_host():
        worker_hosts_list = list(worker_hosts)
        # The following line will raise an exception if we're out of capacity.
        min_host = worker_hosts_list[0]
        min_value = worker_hosts[min_host]
        for h in worker_hosts_list[1:]:
            value = worker_hosts[h]
            if (value['application_procs'] < min_value['application_procs']) \
               or (value['application_procs'] == min_value['application_procs'] \
                   and value['total_procs'] < min_value['total_procs']):
                min_host = h
                min_value = value
        return min_host

    # Helper function: update state, adding one process to worker_host
    def add_to_host(worker_host):
        added_procs[worker_host] = added_procs.get(worker_host, 0) + 1
        value = worker_hosts[worker_host]
        value['total_procs'] += 1
        value['application_procs'] += 1
        # Remove host if maxed out
        if value['total_procs'] >= value['max_procs']:
            del worker_hosts[worker_host]

    for i in range(0, num_procs_to_add):
        h = find_min_host()
        add_to_host(h)

    return added_procs

# Call this method to deallocate up to num_procs worker processes for
# application.  If application has fewer than num_procs worker processes,
# that's ok, we'll just deallocate as many as we can.  Does not touch the
# database or workers, simply computes and returns a result.  Tries to leave
# the remaining processes evenly distributed across worker hosts.
#
# num_procs_to_remove :: int
# worker_hosts :: { <worker_host> : { 'max_procs' : int, 'total_procs': int, 'application_procs' : int } }
# Returns :: { <worker_host> : <num_procs_to_remove> }
def _compute_deallocation_from_worker_hosts(num_procs_to_remove, worker_hosts):
    worker_hosts = copy.deepcopy(worker_hosts)

    # Remove hosts that don't contain application processes
    unused_worker_hosts = []
    for h in worker_hosts:
        if worker_hosts[h]['application_procs'] <= 0:
            unused_worker_hosts.append(h)
    for h in unused_worker_hosts:
        del worker_hosts[h]

    # Processes removed from hosts :: host -> int
    removed_procs = { }

    # Helper function: find the host with the most processes from this
    # application, using total number of processes as a tie-breaker.
    def find_max_host():
        worker_hosts_list = list(worker_hosts)
        if worker_hosts_list == []:
            return None
        max_host = worker_hosts_list[0]
        max_value = worker_hosts[max_host]
        for h in worker_hosts_list[1:]:
            value = worker_hosts[h]
            if (value['application_procs'] > max_value['application_procs']) \
               or (value['application_procs'] == max_value['application_procs'] \
                   and value['total_procs'] > max_value['total_procs']):
                max_host = h
                max_value = value
        return max_host

    # Helper function: update state, removing one process from worker_host
    def remove_from_host(worker_host):
        removed_procs[worker_host] = removed_procs.get(worker_host, 0) + 1
        value = worker_hosts[worker_host]
        value['total_procs'] -= 1
        value['application_procs'] -= 1
        # Remove host if it contains no more application processes
        if value['application_procs'] <= 0:
            del worker_hosts[worker_host]

    for i in range(0, num_procs_to_remove):
        h = find_max_host()
        if h:
            remove_from_host(h)

    return removed_procs

########NEW FILE########
__FILENAME__ = call_remote
import os.path, sys
from djangy_server_shared import *
from management_database import *

def _call_remote(hosts, make_command):
    # Run commands in parallel on all designated hosts
    # Note: command arguments will be parsed by shell, and must not contain spaces
    num_success = 0
    num_failure = 0
    stdout_contents_dict = { }
    programs = []
    for h in hosts:
        p = ExternalProgram(['ssh', h] + make_command(h))
        p.host = h
        programs.append(p)
    sys.stdout.flush()
    for p in programs:
        if p:
            p.start()
    for p in programs:
        if p:
            result = p.finish()
            if external_program_encountered_error(result):
                num_failure = num_failure + 1
            else:
                num_success = num_success + 1
            stdout_contents_dict[p.host] = result['stdout_contents']
        else:
            num_failure = num_failure + 1

    return (num_success, num_failure, stdout_contents_dict)

def call_worker_managers_retrieve_logs(application_name, hosts=None):
    def make_retrieve_command(application_info, host):
        command = [os.path.join(WORKER_SETUID_DIR, 'run_retrieve_logs'),
            'application_name', application_info.name,
            'bundle_version', application_info.bundle_version
        ]
        return command

    (num_success, num_failure, stdout_contents_dict) = _call_worker_managers(application_name, make_retrieve_command, hosts)
    return stdout_contents_dict

def call_worker_managers_allocate(application_name, hosts=None):
    def make_allocate_command(application_info, host):
        try:
            p = Process.objects.get(application=application_info, proc_type='gunicorn', host=host)
            num_procs = p.num_procs
            port = p.port
        except:
            num_procs = 0
            port = 0
        try:
            p = Process.objects.get(application=application_info, proc_type='celery', host=host)
            celery_procs = p.num_procs
        except:
            celery_procs = 0
        virtualhosts = VirtualHost.get_virtualhosts_by_application_name(application_name)
        http_virtual_hosts = ','.join(virtualhosts)
        command = [os.path.join(WORKER_SETUID_DIR, 'run_deploy'), \
            'application_name', application_info.name, \
            'bundle_version', application_info.bundle_version, \
            'num_procs', str(num_procs), \
            'proc_num_threads', str(application_info.proc_num_threads), \
            'proc_mem_mb', str(application_info.proc_mem_mb), \
            'proc_stack_mb', str(application_info.proc_stack_mb), \
            'debug', str(application_info.debug), \
            'http_virtual_hosts', http_virtual_hosts, \
            'host', host, \
            'port', str(port),
            'celery_procs', str(celery_procs)]
        return command

    _call_worker_managers(application_name, make_allocate_command, hosts)

def call_worker_managers_delete_application(application_name, hosts=None):
    def make_delete_application_command(application_info, host):
        command = [os.path.join(WORKER_SETUID_DIR, 'run_delete_application'), \
            'application_name', application_info.name]
        return command

    _call_worker_managers(application_name, make_delete_application_command, hosts)

def _call_worker_managers(application_name, make_command, hosts=None):
    # Load global application info
    application = Application.get_by_name(application_name)
    bundle_version = application.bundle_version
    if bundle_version == None or bundle_version == '':
        return

    def make_command2(host):
        return make_command(application, host)

    # Load relevant hosts from database if none specified
    if hosts == None:
        hosts = [h for (h, p) in Process.get_hosts_ports_by_application(application)]

    (num_success, num_failure, stdout_contents_dict) = _call_remote(hosts, make_command2)
    if num_failure > 0:
        print ('%i success, %i failure' % (num_success, num_failure)),

    return (num_success, num_failure, stdout_contents_dict)

def call_proxycache_managers_configure(application_name):
    application        = Application.get_by_name(application_name)
    # Hosts running proxycache serving this application
    proxycache_hosts   = ProxyCache.get_proxycache_hosts_by_application(application)
    # Virtual hosts used by this application
    virtualhosts       = VirtualHost.get_virtualhosts_by_application(application)
    # Real hosts and port numbers running instances of this application
    worker_hosts_ports = Process.get_hosts_ports_by_application(application)

    http_virtual_hosts = ','.join(virtualhosts)
    worker_servers = ','.join(['%s:%s' % (h, p) for (h, p) in worker_hosts_ports])

    command = [os.path.join(PROXYCACHE_SETUID_DIR, 'run_configure'), \
        'application_name',    application_name, \
        'http_virtual_hosts',  http_virtual_hosts, \
        'worker_servers',      worker_servers, \
        'cache_index_size_kb', str(application.cache_index_size_kb), \
        'cache_size_kb',       str(application.cache_size_kb)]

    (num_success, num_failure, stdout_contents_dict) = _call_remote(proxycache_hosts, lambda h: command)
    if num_failure > 0:
        print ('%i success, %i failure' % (num_success, num_failure)),

def call_proxycache_managers_delete_application(application_name):
    # Hosts running proxycache serving this application
    proxycache_hosts   = ProxyCache.get_proxycache_hosts_by_application_name(application_name)

    command = [os.path.join(PROXYCACHE_SETUID_DIR, 'run_delete_application'), 'application_name', application_name]

    (num_success, num_failure, stdout_contents_dict) = _call_remote(proxycache_hosts, lambda h: command)
    if num_failure > 0:
        print ('%i success, %i failure' % (num_success, num_failure)),

########NEW FILE########
__FILENAME__ = ssh_and_git
from djangy_server_shared import *
from management_database import *
import os, os.path, re

def add_ssh_public_key(user, pubkey):
    """ Add a user's SSH public key to mangement_database and git access. """
    (ssh_public_key, comment) = parse_ssh_public_key(pubkey)
    # Update the management_database
    user.add_ssh_public_key(ssh_public_key, comment)
    # Update ~git/.ssh/authorized_keys
    regenerate_ssh_authorized_keys()

def parse_ssh_public_key(pubkey):
    """ Parse an SSH public key into the key proper and the optional
        comment.  Throws an exception when given a malformed key.  """
    pubkey2 = pubkey.replace('\r', '')
    matches = re.match('^(?P<ssh_public_key>(?:ssh-dss|ssh-rsa)\s+[A-Za-z0-9/+]+=*)\s+(?P<comment>.*)$', pubkey2, re.DOTALL)
    if matches:
        return (matches.group('ssh_public_key'), matches.group('comment'))
    key_data_matches = re.match('\s*---- BEGIN SSH2 PUBLIC KEY ----\s*\n(?:[^:\n]*:[^\n]*\n)*(?P<key_data>[A-Za-z0-9/+\s\n]+=*)\s*\n\s*---- END SSH2 PUBLIC KEY ----\s*', pubkey2, re.DOTALL)
    key_type_matches = re.match('.*?\s*Comment\s*:\s*(?P<comment>(?:(?P<rsa>[Rr][Ss][Aa])|(?P<dsa>[Dd][Ss][Aa])|(?P<dss>[Dd][Ss][Ss])|[^\n])*)\s*\n.*?', pubkey2, re.DOTALL)
    if key_data_matches:
        if key_type_matches.group('rsa'):
            key_type = 'rsa'
        elif key_type_matches.group('dsa'):
            key_type = 'dss'
        elif key_type_matches.group('dss'):
            key_type = 'dss'
        else:
            key_type = 'rsa'
        key_data = key_data_matches.group('key_data').replace('\n', '')
        ssh_public_key = 'ssh-%s %s' % (key_type, key_data)
        if key_type_matches.group('comment'):
            return (ssh_public_key, key_type_matches.group('comment'))
        else:
            return (ssh_public_key, '')
    return ('', 'Invalid SSH public key: %s' % pubkey)

def create_git_repository(application_name):
    """ Create a new git repository for a given application.  Performs no validation. """
    # Location of the repository: /srv/git/repositories/<application_name>.git
    repo_path = os.path.join(REPOS_DIR, application_name + '.git')
    # We will run "git init" as the git user/group
    def become_git_user():
        set_uid_gid(GIT_UID, GIT_GID)
    # Run "git init"
    run_external_program(['git', 'init', '--bare', repo_path], cwd='/', preexec_fn=become_git_user)

def regenerate_ssh_authorized_keys():
    """ Regenerate /srv/git/.ssh/authorized_keys and /srv/shell/.ssh/authorized_keys from the management_database. """
    # Programs that will be run when the user connects via ssh
    git_serve_path = GIT_SERVE_PATH
    shell_serve_path = SHELL_SERVE_PATH
    # Generate authorized_keys
    git_authorized_keys = generate_ssh_authorized_keys_contents(git_serve_path)
    shell_authorized_keys = generate_ssh_authorized_keys_contents(shell_serve_path)
    # Write out authorized_keys
    write_to_file(os.path.join(GIT_SSH_DIR, 'authorized_keys'), git_authorized_keys, GIT_UID, GIT_GID, AUTHORIZED_KEYS_MODE)
    write_to_file(os.path.join(SHELL_SSH_DIR, 'authorized_keys'), shell_authorized_keys, SHELL_UID, SHELL_GID, AUTHORIZED_KEYS_MODE)

def generate_ssh_authorized_keys_contents(command_path):
    # Options to lock down ssh access
    options = 'no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty'
    # Create lines in authorized_keys for each ssh public key in the datbasee
    keys = filter(lambda y: y.ssh_public_key.strip() != '', SshPublicKey.objects.all())
    lines = ['command="%s %i",%s %s' % (command_path, x.id, options, x.ssh_public_key) for x in keys]
    authorized_keys_contents = '\n'.join(lines) + '\n'
    return authorized_keys_contents

def write_to_file(path, contents, uid, gid, mode):
    f = open(path, 'w')
    f.write(contents)
    f.close()
    os.chown(path, uid, gid)
    os.chmod(path, mode)

########NEW FILE########
__FILENAME__ = shell_serve
#!/srv/djangy/run/python-virtual/bin/python
#
# Note: doesn't import shared.ssh_and_git because this runs as the "shell"
# user, which doesn't have access to write to /srv/logs/master.log...
#

from djangy_server_shared import become_application_setup_uid_gid, constants, find_django_project
from management_database import *
import os, re, subprocess, sys

def main():
    try:
        shell_serve(int(sys.argv[1]))
    except:
        sys.stderr.write('Access denied.  Please email support@djangy.com for help.\n')

def shell_serve(ssh_public_key_id):
    """ Serve an incoming manage.py request.  Should only be called via ~shell/.ssh/authorized_keys """
    # Get all users who have the specified public key
    users = SshPublicKey.get_users_by_public_key_id(ssh_public_key_id)
    # SSH_ORIGINAL_COMMAND format:
    # <application_name> manage.py [args...]
    ssh_original_command = os.environ['SSH_ORIGINAL_COMMAND']
    matches = re.match('^\s*(?P<application_name>[A-Za-z0-9]+)\s+manage\.py\s+(?P<args>.*?)\s*$', ssh_original_command)
    assert matches
    application_name = matches.group('application_name')
    args = matches.group('args')
    # blocked commands
    if args.split()[0] in constants.BLOCKED_COMMANDS:
        sys.stderr.write('For security reasons, that command has been disallowed.  Contact support@djangy.com for help.\n')
        return None
    # Look up the requested application, and make sure that at least one
    # user associated with the SSH key that was used has access to it.
    application = Application.get_by_name(application_name)
    if application.accessible_by_any_of(users):
        # Look up bundle information
        bundle_version      = application.bundle_version
        bundle_name         = '%s-%s' % (application_name, bundle_version)
        bundle_path         = os.path.join(constants.BUNDLES_DIR, bundle_name)
        setup_uid           = application.setup_uid
        app_gid             = application.app_gid
        bin_path            = os.path.join(bundle_path, 'python-virtual/bin')
        python_path         = os.path.join(bin_path, 'python')
        # It might be preferable to read the bundle configuration instead, to be consistent...
        django_project_path = find_django_project(os.path.join(bundle_path, 'application'))
        # Get around buffered stdout
        os.dup2(2, 1)
        # Run the command:
        os.chdir(django_project_path)
        become_application_setup_uid_gid('shell_serve', setup_uid, app_gid)
        command = '%s -u manage.py %s' % (python_path, args)
        os.execve('/bin/bash', ['bash', '-c', command], {'PATH':'/bin:/usr/bin:%s' % bin_path})

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = create_virtualenv
#!/usr/bin/env python
#
# Runs virtualenv create commands as an application setup UID.  This program
# is called as root, and then sets its own UID.  This allows us to protect
# the create_virtualenv.py script from end-user code.
#

from djangy_server_shared import *

def main():
    kwargs = check_and_return_keyword_args(sys.argv, ['application_name', 'bundle_name', 'setup_uid', 'app_gid'])
    become_application_setup_uid_gid(sys.argv[0], int(kwargs['setup_uid']), int(kwargs['app_gid']))
    os.umask(0027)
    os.environ['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
    del os.environ['VIRTUAL_ENV']
    create_virtualenv(**kwargs)

def create_virtualenv(application_name, bundle_name, setup_uid, app_gid):
    if os.getuid() == 0 or os.getuid() != int(setup_uid):
        print 'ERROR: setup_bundle must be run as setup_uid'
        sys.exit(2)

    bundle_path = os.path.join(BUNDLES_DIR, bundle_name)

    # Create virtualenv in <bundle path>/python-virtual
    print 'Installing dependencies...\n',
    virtualenv_path = os.path.join(bundle_path, 'python-virtual')
    generate_virtual_environment(bundle_path, virtualenv_path)
    print 'Done.'
    print ''

def generate_virtual_environment(bundle_path, virtualenv_path):
    # Create the virtualenv
    sys.stdout.flush()
    run_external_program(['virtualenv', virtualenv_path])
    # Install eggs using easy_install
    easy_install_eggs(bundle_path, virtualenv_path)
    # Install other required python packages using pip
    pip_install_requirements(bundle_path, virtualenv_path)

def easy_install_eggs(bundle_path, virtualenv_path):
    print '  Dependencies from djangy.eggs using easy_install:'
    # read the djangy.eggs file (if it exists) and install all the packages mentioned
    deps_path = os.path.join(bundle_path, 'config', 'djangy.eggs')
    deps = []
    if os.path.exists(deps_path):
        deps = [d.strip('\n') for d in open(deps_path, 'r').readlines()]
    elif not os.path.exists(os.path.join(bundle_path, 'config', 'djangy.pip')):
        deps = ['Django', 'South']
    if 'gunicorn' not in deps:
        deps += ['gunicorn']
    easy_install = os.path.join(virtualenv_path, 'bin', 'easy_install')
    install_deps([easy_install, '-Z'], deps)

def pip_install_requirements(bundle_path, virtualenv_path):
    print '  Dependencies from djangy.pip using pip:'
    # read the djangy.pip file (if it exists) and install all the packages mentioned
    deps_path = os.path.join(bundle_path, 'config', 'djangy.pip')
    if os.path.exists(deps_path):
        deps = [d.strip('\n') for d in open(deps_path, 'r').readlines()]
    else:
        deps = []
    pip_path = os.path.join(virtualenv_path, 'bin', 'pip')
    install_deps([pip_path, 'install'], deps)

def install_deps(install_command, deps):
    sys.stdout.flush()
    num_deps = 0
    for dep in deps:
        # Get the raw dependency, no comment.
        dep = dep.strip()
        # Install the dependency, but skip blank or comment lines
        if dep != '' and dep[0] != '#':
            num_deps = num_deps + 1
            print '    Installing %s...' % dep,
            sys.stdout.flush()
            result = run_external_program(install_command + dep.split())
            if result['exit_code'] == 0:
                print 'Success.'
            else:
                print 'FAILED!'
    if num_deps == 0:
        print '    None found.'
    sys.stdout.flush()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = get_admin_media_prefix
#!/usr/bin/env python
#
# Placeholder -- should import settings.py from the django project and print
# out ADMIN_MEDIA_PREFIX.  Needs to run as setup_uid and in the application's
# virtual environment.
#

from djangy_server_shared import *

def main():
    kwargs = check_and_return_keyword_args(sys.argv, ['setup_uid', 'app_gid', 'virtual_env_path', 'django_project_path'])
    os.chdir('/')
    become_application_setup_uid_gid(sys.argv[0], int(kwargs['setup_uid']), int(kwargs['app_gid']))
    os.chdir(kwargs['django_project_path'])

########NEW FILE########
__FILENAME__ = clone_repo
#!/usr/bin/env python
#
# Should be run as the git user/group.
#

from djangy_server_shared import *

def main():
    program_name = sys.argv[0]
    become_uid_gid(program_name, GIT_UID, GIT_GID)
    args = sys.argv[1:]
    if len(args) != 2:
        print_or_log_usage('Usage: %s <master_repo_path> <temp_repo_path>\n' % program_name)
        sys.exit(1)
    clone_repo(*args)

def clone_repo(master_repo_path, temp_repo_path):
    # git clone
    run_external_program(['git', 'clone', master_repo_path, temp_repo_path], cwd=temp_repo_path)
    if not os.path.exists(temp_repo_path):
        log_error_message('git clone failed')
        sys.exit(3)
    # read current version of git repository
    result = run_external_program(['git', 'show-ref', '--heads', '-s'], cwd=temp_repo_path)
    stdout = result['stdout_contents'].split('\n')
    if len(stdout) < 1:
        git_repo_version = ''
    else:
        git_repo_version = stdout[0]
    if not validate_git_repo_version(git_repo_version):
        log_error_message('git returned invalid application version (%s)' % git_repo_version)
        sys.exit(4)
    # output current version of git repository
    print git_repo_version
    sys.exit(0)

def validate_git_repo_version(git_repo_version):
    return (None != re.match('^[0-9a-f]{40}$', git_repo_version))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = Router
class Router(object):
    """ Router to tell the application when to use the management_database and when to use the 'default' database.
    see http://docs.djangoproject.com/en/1.2/topics/db/multi-db/
    """

    def check_for_md(self, model, **hints):
        if model._meta.app_label == 'management_database':
            return 'management_database'
        return None

    db_for_read = check_for_md
    db_for_write = check_for_md

    def allow_relation(self, obj1, obj2, **hints):
        if (obj1._meta.app_label == obj1._meta.app_label):
            return True
        return False

    def allow_syncdb(self, db, model):
        """ Keep the management database from being synchronized here."""
        if model._meta.app_label == 'management_database':
            return False
        return None

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, \
    HttpResponseNotFound, HttpResponseNotAllowed, HttpResponseServerError
from master_api import name_available, add_application, remove_application, retrieve_logs, command
from management_database import *
import logging, json

def _presence_of(arg, msg):
    """ Decorator that returns the specified message if the specified POST variable isn't present."""
    def presence(func):
        def verify(*args, **kwargs):
            if not args[0].POST.get(arg, None):
                return HttpResponseBadRequest(msg)
            return func(*args, **kwargs)
        return verify
    return presence

def _auth_required(func):
    """ Decorator for API function calls that ensures the presence of email, hashed_password, pubkey, and application_name. """
    def auth(*args, **kwargs):
        if args[0].method.lower() != 'post':
            return HttpResponseNotAllowed(['POST'])

        email = args[0].POST.get('email', None)
        if email is None:
            return HttpResponseBadRequest('No email provided.')

        hashed_password = args[0].POST.get('hashed_password', None)
        if hashed_password is None:
            return HttpResponseBadRequest('No password provided.')

        user = User.get_by_email(email)
        if user is None:
            return HttpResponseForbidden('Please create an account on Djangy.com first.')

        if user.passwd != hashed_password:
            return HttpResponseForbidden('Invalid password.')

        return func(*args, **kwargs)
    return auth

def _check_application_access(func):
    """ Decorator for checking that the user has access to the selected application.  Use after _auth_required. """
    def check_application_access(request):
        email = request.REQUEST.get('email')
        application_name = request.REQUEST.get('application_name')
        user = User.get_by_email(email)
        application = Application.get_by_name(application_name)
        if application and application.accessible_by(user):
            return func(request, email, application_name)
        else:
            return HttpResponseBadRequest('Access denied for user "%s" to application "%s".' % (email, application_name))
    return check_application_access

@_auth_required
def index(request):
    return HttpResponse('')

@_presence_of('pubkey', 'No public key provided.')
@_presence_of('application_name', 'No application name provided.')
@_auth_required
def create(request):
    """ create command, called from the djangy command line client."""
    email = request.POST.get('email')
    application_name = request.POST.get('application_name')

    # check for that application name
    if not name_available(application_name):
        return HttpResponseBadRequest('Error: an application named "%s" already exists.' % application_name)

    # create the application
    try:
        pubkey = request.POST.get('pubkey')
        add_application(application_name, email, pubkey)
    except Exception, e:
        return HttpResponseServerError('Exception while adding application: %s' % e)

    logging.info('Application created: %s.' % application_name)

    return HttpResponse('Application created.')

@_presence_of('application_name', 'No application name provided.')
@_auth_required
@_check_application_access
def delete(request, email, application_name):
    """ Remove a project. Called from the djangy.py command line client. """
    status = remove_application(application_name)
    if not status:
        return HttpResponseServerError('Error: %s.' % status)

    return HttpResponse('Your application, %s, has been deleted.' % application_name)

@_presence_of('application_name', 'No application name provided.')
@_auth_required
@_check_application_access
def logs(request, email, application_name):
    """ Return the last 100 lines of the django.log file for this application."""
    try:
        return HttpResponse(retrieve_logs(application_name))
    except Exception, e:
        return HttpResponseServerError('Error: %s.' % e)

@_presence_of('application_name', 'No application name provided.')
@_auth_required
@_check_application_access
def syncdb(request, email, application_name):
    """ Run the syncdb command. """
    try:
        return HttpResponse(command(application_name, 'syncdb', '--noinput'))
    except Exception, e:
        return HttpResponseServerError('Error: %s.' % e)

@_presence_of('application_name', 'No application name provided.')
@_auth_required
@_check_application_access
def migrate(request, email, application_name):
    """ Run the migrate command. """
    raw_args = request.POST.get('args', '')
    logging.info('[MIGRATE] got args: %s' % raw_args)
    try:
        args = json.loads(raw_args)
    except:
        args = []
    try:
        return HttpResponse(command(application_name, 'migrate', *args))
    except Exception, e:
        return HttpResponseServerError('Error: %s.' % e)

@_presence_of('application_name', 'No application name provided.')
@_auth_required
@_check_application_access
def createsuperuser(request, email, application_name):
    """ Run the createsuperuser command. """
    try:
        return HttpResponse(command(application_name, 'createsuperuser'))
    except Exception, e:
        return HttpResponseServerError('Error: %s.' % e)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for web_api project.
import djangy_server_shared, os.path

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Bob Jones', 'bob@jones.mil')
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE':'mysql',
        'NAME':'web_api',
        'USER':'web_api',
        'PASSWORD':'password goes here',
        'HOST':'',
        'PORT':'',
    },
    'management_database': {
        'ENGINE': 'mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'djangy',                      # Or path to database file if using sqlite3.
        'USER': 'djangy',                      # Not used with sqlite3.
        'PASSWORD': 'password goes here',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

DATABASE_ROUTERS = ['api.Router']
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
#SECRET_KEY = <password goes here>

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'web_api.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    #'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'management_database',
    'web_api.api',
    'sentry.client',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)
SENTRY_KEY = 'password goes here'
SENTRY_REMOTE_URL = 'django logsentry remote URL goes here'

import logging

LOG_FILENAME = os.path.join(djangy_server_shared.LOGS_DIR, 'api.djangy.com/django.log')
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)
from sentry.client.handlers import SentryHandler

logging.getLogger().addHandler(SentryHandler())

# Add StreamHandler to sentry's default so you can catch missed exceptions
logging.getLogger('sentry').addHandler(logging.StreamHandler())


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', 'web_api.api.views.index'),
    (r'^create$', 'web_api.api.views.create'),
    (r'^delete$', 'web_api.api.views.delete'),
    (r'^logs$', 'web_api.api.views.logs'),
    (r'^syncdb$', 'web_api.api.views.syncdb'),
    (r'^migrate$', 'web_api.api.views.migrate'),
    (r'^createsuperuser$', 'web_api.api.views.createsuperuser'),
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from models import Page


admin.site.register(Page)

########NEW FILE########
__FILENAME__ = forms
from django import forms as forms

from models import Page


class PageForm(forms.Form):
    name = forms.CharField(max_length=255)
    content = forms.CharField(widget=forms.Textarea(attrs={
        'cols':80,
        'rows':30
        }))

    def clean_name(self):
        import re
        from templatetags.wiki import WIKI_WORD

        pattern = re.compile(WIKI_WORD)

        name = self.cleaned_data['name']
        if not pattern.match(name):
            raise forms.ValidationError('Must be a WikiWord.')

        return name

########NEW FILE########
__FILENAME__ = 0001_create_tables
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Page'
        db.create_table('docs_page', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('rendered', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('docs', ['Page'])


    def backwards(self, orm):
        
        # Deleting model 'Page'
        db.delete_table('docs_page')


    models = {
        'docs.page': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Page'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'rendered': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['docs']

########NEW FILE########
__FILENAME__ = models
from django.db import models

from templatetags.wiki import wikify


class Page(models.Model):
    name = models.CharField(max_length=255, unique=True)
    content = models.TextField()
    rendered = models.TextField()

    class Meta:
        ordering = ('name', )

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.rendered = wikify(self.content)
        super(Page, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = wiki
import re

from django import template


WIKI_WORD = r'(?:[A-Z]+[a-z0-9]+){1,}'


register = template.Library()


wikifier = re.compile(r'\b(%s)\b' % WIKI_WORD)


@register.filter
def wikify(s):
    from django.core.urlresolvers import reverse
    wiki_root = reverse('docs.views.index', args=[], kwargs={})
    return wikifier.sub(r'<a href="%s\1/">\1</a>' % wiki_root, s)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from templatetags.wiki import WIKI_WORD


urlpatterns = patterns('docs.views',
    (r'^$', 'index'),
    ('overview.html', 'index'),
    ('(?P<name>%s)/$' % WIKI_WORD, 'view'),
    ('(?P<name>%s)/edit/$' % WIKI_WORD, 'edit'),
)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from main.views.shared import is_admin, get_user, auth_required, admin_required
from forms import PageForm
from models import Page

def index(request):
    return HttpResponseRedirect('/docs/Documentation')

def view(request, name):
    """Shows a single wiki page."""
    try:
        page = Page.objects.get(name=name)
    except Page.DoesNotExist:
        page = Page(name=name)

    return render_to_response('wiki/view.html', {
        'page': page, 
        'admin': is_admin(request),
        'user': get_user(request),
        'navbar':Page.objects.get(name='NavBar'),
    })

@auth_required
@admin_required
def edit(request, name):
    """Allows users to edit wiki pages."""
    try:
        page = Page.objects.get(name=name)
    except Page.DoesNotExist:
        page = None

    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            if not page:
                page = Page()
            page.name = form.cleaned_data['name']
            page.content = form.cleaned_data['content']

            page.save()
            return HttpResponseRedirect('../../%s/' % page.name)
    else:
        if page:
            form = PageForm(initial=page.__dict__)
        else:
            form = PageForm(initial={'name': name})

    return render_to_response('wiki/edit.html', {
        'form': form, 
        'admin': is_admin(request),
        'user': get_user(request),
        'navbar':Page.objects.get(name='NavBar'),
    })

########NEW FILE########
__FILENAME__ = adjectives
adjectives = [
'adorable',
'adventurous',
'aggressive',
'agreeable',
'alert',
'amused',
'ancient',
'angry',
'annoyed',
'annoying',
'anxious',
'arrogant',
'ashamed',
'attractive',
'average',
'awful',
'beautiful',
'bewildered',
'big',
'bitter',
'black',
'bloody',
'blue',
'blue-eyed',
'blushing',
'boiling',
'bored',
'brainy',
'brave',
'breakable',
'breezy',
'brief',
'bright',
'broad',
'broken',
'bumpy',
'busy',
'calm',
'careful',
'cautious',
'charming',
'cheerful',
'chilly',
'chubby',
'clean',
'clear',
'clever',
'cloudy',
'clumsy',
'cold',
'colorful',
'colossal',
'combative',
'comfortable',
'concerned',
'condemned',
'confused',
'cooing',
'cool',
'cooperative',
'courageous',
'crazy',
'creepy',
'crooked',
'crowded',
'cruel',
'cuddly',
'curious',
'curly',
'curved',
'cute',
'damaged',
'damp',
'dangerous',
'dark',
'dead',
'deafening',
'deep',
'defeated',
'defiant',
'delicious',
'delightful',
'depressed',
'determined',
'difficult',
'dirty',
'disgusted',
'distinct',
'disturbed',
'ditzy',
'dizzy',
'doubtful',
'drab',
'dry',
'dull',
'dusty',
'eager',
'easy',
'elated',
'elegant',
'embarrassed',
'empty',
'enchanting',
'encouraging',
'energetic',
'enthusiastic',
'envious',
'evil',
'excited',
'expensive',
'exuberant',
'faint',
'faithful',
'famous',
'fancy',
'fantastic',
'fast',
'fat',
'fierce',
'filthy',
'fine',
'flaky',
'flat',
'fluffy',
'fluttering',
'foolish',
'fragile',
'frail',
'frantic',
'freezing',
'fresh',
'friendly',
'frightened',
'funny',
'fuzzy',
'gentle',
'gifted',
'gigantic',
'glamorous',
'gleaming',
'glorious',
'gorgeous',
'graceful',
'greasy',
'grieving',
'grotesque',
'grubby',
'grumpy',
'handsome',
'happy',
'hard',
'harsh',
'healthy',
'heavy',
'helpful',
'helpless',
'high-pitched',
'hilarious',
'hissing',
'hollow',
'homeless',
'homely',
'horrible',
'hot',
'huge',
'hungry',
'hurt',
'hushed',
'husky',
'icy',
'immense',
'important',
'impossible',
'inexpensive',
'innocent',
'inquisitive',
'itchy',
'jealous',
'jittery',
'jolly',
'joyous',
'juicy',
'kind',
'large',
'late',
'lazy',
'little',
'lively',
'living',
'lonely',
'loud',
'lovely',
'lucky',
'magnificent',
'mammoth',
'manly',
'massive',
'melodic',
'melted',
'miniature',
'misty',
'moaning',
'modern',
'motionless',
'muddy',
'mushy',
'mute',
'mysterious',
'narrow',
'nasty',
'naughty',
'nervous',
'nice',
'noisy',
'nutritious',
'nutty',
'obedient',
'obnoxious',
'odd',
'old',
'old-fashioned',
'outrageous',
'outstanding',
'panicky',
'perfect',
'petite',
'plain',
'plastic',
'pleasant',
'poised',
'poor',
'powerful',
'precious',
'prickly',
'proud',
'puny',
'purring',
'puzzled',
'quaint',
'quick',
'quiet',
'rainy',
'rapid',
'raspy',
'real',
'relieved',
'repulsive',
'resonant',
'rich',
'ripe',
'rotten',
'rough',
'round',
'salty',
'scary',
'scattered',
'scrawny',
'screeching',
'selfish',
'shaggy',
'shaky',
'shallow',
'sharp',
'shiny',
'shivering',
'short',
'shrill',
'shy',
'silent',
'silky',
'silly',
'skinny',
'sleepy',
'slimy',
'slippery',
'slow',
'small',
'smiling',
'smitten',
'smoggy',
'smooth',
'soft',
'solid',
'sore',
'sour',
'sparkling',
'spicy',
'splendid',
'spotless',
'square',
'squealing',
'stale',
'steady',
'steep',
'sticky',
'stormy',
'straight',
'strange',
'strong',
'stupid',
'substantial',
'successful',
'super',
'sweet',
'swift',
'talented',
'tall',
'tame',
'tasteless',
'tasty',
'teeny',
'teeny-tiny',
'tender',
'tense',
'terrible',
'thankful',
'thirsty',
'thoughtful',
'thoughtless',
'thundering',
'tight',
'tiny',
'tired',
'tough',
'troubled',
'ugly',
'uneven',
'uninterested',
'unsightly',
'unusual',
'upset',
'uptight',
'victorious',
'vivacious',
'voiceless',
'wandering',
'warm',
'weak',
'weary',
'wet',
'whispering',
'wicked',
'wide',
'wide-eyed',
'wild',
'witty',
'wonderful',
'wooden',
'worldly',
'worried',
'young',
'yummy',
'zany',
'zealous',
'zombie',
]

########NEW FILE########
__FILENAME__ = gen_invite_code
#!/usr/bin/env python

import random, sys
from adjectives import *
from nouns import *

def gen_invite_code(n=1):
    if len(sys.argv) > 1:
        n = int(sys.argv[1])

    def strip_newlines(lines):
        return map(lambda x: x[:-1], lines)

    def choose_word(words):
        return words[random.randint(0, len(words)-1)]

    for i in range(0, n):
        adj1 = choose_word(adjectives)
        adj2 = choose_word(adjectives)
        while adj1[-1] == adj2[-1]:
            adj2 = choose_word(adjectives)
        if adj1[-1] > adj2[-1]:
            (adj1, adj2) = (adj2, adj1)
        if adj1 == 'zombie':
            (adj1, adj2) = (adj2, adj1)
        noun = choose_word(nouns)

        return "%s %s %s" % (adj1, adj2, noun)

if __name__ == '__main__':
    gen_invite_code()

########NEW FILE########
__FILENAME__ = nouns
nouns = [
'alien',
'artist',
'baby',
'badger',
'basketball',
'basketcase',
'bedsheet',
'bicycle',
'boy',
'boyscout',
'bratwurst',
'camera',
'candle',
'captain',
'cat',
'caveman',
'ceo',
'chair',
'cheek',
'cheesecake',
'chihuahua',
'chipmunk',
'cruller',
'digerati',
'dog',
'donkey',
'donut',
'dork',
'driver',
'drunk',
'elf',
'eskimo',
'fairy',
'fan',
'father',
'football',
'friend',
'frog',
'gangster',
'ghost',
'girl',
'girlscout',
'goalie',
'gorilla',
'hacker',
'hedgehog',
'helmet',
'hipster',
'hobo',
'horse',
'house',
'icecream',
'inmate',
'insect',
'jock',
'kangaroo',
'keyboard',
'king',
'kitten',
'knife',
'koala',
'lamp',
'llama',
'magistrate',
'mathematician',
'mom',
'monkey',
'monologue',
'moped',
'narwhal',
'nerd',
'ninja',
'painting',
'panda',
'pants',
'pencil',
'penguin',
'pig',
'pikachu',
'pirate',
'pizza',
'pogostick',
'pony',
'priest',
'prince',
'princess',
'pumpkin',
'puppy',
'queen',
'rabbit',
'racquet',
'redditor',
'roommate',
'scientist',
'sheep',
'skateboard',
'snail',
'solicitor',
'spork',
'spring',
'statue',
'summer',
'superstar',
'swimmer',
'teaspoon',
'toothbrush',
'towel',
'train',
'trashcan',
'troll',
'tulip',
'turtle',
'unicorn',
'viking',
'wallaby',
'weather',
'winnebago',
'wino',
'winter',
'yankee',
]

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Email'
        db.create_table('main_email', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('main', ['Email'])


    def backwards(self, orm):
        
        # Deleting model 'Email'
        db.delete_table('main_email')


    models = {
        'main.email': {
            'Meta': {'object_name': 'Email'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['main']

########NEW FILE########
__FILENAME__ = 0002_add_invited_field
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Email.invited'
        db.add_column('main_email', 'invited', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Email.invited'
        db.delete_column('main_email', 'invited')


    models = {
        'main.email': {
            'Meta': {'object_name': 'Email'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['main']

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Email(models.Model):
    email = models.EmailField()
    timestamp = models.DateTimeField(auto_now = True)
    invited = models.BooleanField(default = False)


########NEW FILE########
__FILENAME__ = Router
class Router(object):
    """ Router to tell the application when to use the management_database and when to use the 'default' database.
    see http://docs.djangoproject.com/en/1.2/topics/db/multi-db/
    """

    def check_for_md(self, model, **hints):
        if model._meta.app_label == 'management_database':
            return 'management_database'
        return None

    db_for_read = check_for_md
    db_for_write = check_for_md

    def allow_relation(self, obj1, obj2, **hints):
        return obj1._meta.app_label == obj1._meta.app_label

    def allow_syncdb(self, db, model):
        """ Keep the management database from being synchronized here."""
        if model._meta.app_label == 'management_database':
            return False
        return None

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = utils
from hashlib import md5

def hash_password(email, password):
    return md5("%s:%s" % (email, password)).hexdigest()

def check_password(email, password, hashed_password):
    if hash_password(email, password) != hashed_password:
        return False
    return True

########NEW FILE########
__FILENAME__ = admin
from shared import *

@http_methods('GET', 'POST')
@auth_required
@admin_required
def admin(request):
    message = get_session_message(request)

    user = User.get_by_email(request.session.get('email'))
    emails = Email.objects.all()
    user_count = User.objects.all().count()
    app_count = Application.objects.filter(deleted=None).all().count()
    emails_applications = [(u.email, u.application_set.filter(deleted=None)) for u in User.objects.all()]
    return render_to_response('admin.html', {
        'navbar_section':'admin',
        'emails_applications':emails_applications,
        'user':user,
        'message':message,
        'emails':emails,
        'user_count':user_count,
        'app_count':app_count
    })

# XXX - CSRF
@http_methods('GET', 'POST')
@auth_required
def invite(request):
    email = request.REQUEST.get('email')

    # ensure there are invitations left
    inviter = User.get_by_email(request.session.get('email', None))
    invitees = User.objects.filter(referrer=inviter).count() + WhiteList.objects.filter(referrer=inviter).count()
    if invitees > inviter.invite_limit and (not inviter.admin):
        request.session['message'] = 'You have no invitations left.'
        return HttpResponseRedirect('/dashboard/account')

    # Prevent duplicate invitations
    if User.get_by_email(email) != None:
        request.session['message'] = 'User already exists, email not sent to %s.' % email
        return HttpResponseRedirect('/dashboard/account')

    invite_code = gen_invite_code()

    wl = WhiteList.objects.all().filter(email=email)
    for obj in wl:
        WhiteList.delete(obj)
    wl = WhiteList(email=email)
    wl.invite_code = invite_code
    try:
        wl.referrer = User.get_by_email(request.session.get('email', None))
    except:
        logging.debug("tried to set whitelist referrer to: %s" % request.session.get("email", None))
    wl.save()
    referrer = 'the Djangy admin'
    if wl.referrer:
        referrer = wl.referrer.email
    # mark the user as invited
    try:
        email_object = Email.objects.filter(email=email).all()
        for em in email_object:
            em.invited = True
            em.save()
    except Exception, e:
        logging.debug(e)

    # email the user
    send_mail(
        'Your Djangy.com Private Beta Invitation',
        """
Congratulations, %s has invited you to join the private beta of Djangy.com,
the hosting service that lets you deploy your Django applications instantly!

Your invite code is: %s

Click the following link to sign up:
https://www.djangy.com/join?%s

For more information, check out our documentation:
http://www.djangy.com/docs

Please email support@djangy.com with any feedback you may have.

Love,
Djangy.com""" % (referrer, invite_code, urlencode({'email':email, 'invite_code':invite_code})),
        'support@djangy.com',
        [email, 'support@djangy.com'], fail_silently=False
    )

    request.session['message'] = 'Invitation sent to %s' % email
    return HttpResponseRedirect('/admin')

@auth_required
@admin_required
def get_emails(request):
    emails = [user.email for user in User.objects.all()]
    return render_to_response("emails.txt", {'emails':emails}, mimetype="text/plain")

########NEW FILE########
__FILENAME__ = create_account
from shared import *

@http_methods('POST')
def signup(request):
    email = request.POST.get('email')
    if not email:
        return HttpResponseRedirect('/')

    try:
        validate_email(email)
    except Exception, e:
        request.session['message'] = 'Please enter a valid email address, or email support@djangy.com for help.'
        return HttpResponseRedirect('/')
        #return render_to_response('index.html', {'message':'Please enter a valid email address, or email support@djangy.com for help.'})

    email_obj = Email(email = email)
    email_obj.save()

    request.session['message'] = "Thanks!  We'll send you an invitation soon."
    return HttpResponseRedirect('/')
    #return render_to_response('index.html', {'message':"Thanks!  We'll send you an invitation soon.", 'index':True})

# XXX
@http_methods('GET', 'POST')
def join(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        invite_code = request.POST.get('invite_code')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if (not email) or (not password1) or (not password2):
            return HttpResponseRedirect('/')

        if (password1 != password2):
            return render_to_response('join.html', {'message':'Whoops, looks like your passwords didn\'t match.  Please try again.', 'email':email, 'invite_code':invite_code})
        try:
            validate_email(email)
        except:
            return HttpResponseRedirect('/')

        user = User()
        user.email = email
        user.passwd = hash_password(email, password1)

        wl = WhiteList.objects.get(email = email)
        user.referrer = wl.referrer
        user.save()
        wl.delete()
        user.save()

        request.session['email'] = email
        logging.info('%s joined successfully.' % email)
        return HttpResponseRedirect('/dashboard')

    elif request.method == 'GET':
        email = request.GET.get('email')
        invite_code = request.GET.get('invite_code')
        if (email is None) or (invite_code is None):
            request.session['message'] = 'Email or invite code not found.'
            return HttpResponseRedirect('/')

        if WhiteList.verify(email, invite_code):
            return render_to_response('join.html', { 'email':email, 'invite_code':invite_code})
        else:
            request.session['message'] = 'Invalid invite code.'
        return HttpResponseRedirect('/')

# XXX
@http_methods('GET', 'POST')
def hackerdojo(request):
    if request.method == 'GET':
        return render_to_response('hackerdojo.html')

    elif request.method == 'POST':
        email = request.POST.get('email')
        invite_code = request.POST.get('invite_code')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if (not email) or (not password1) or (not password2):
            return render_to_response('hackerdojo.html', {'message':'Please enter a valid email address.', 'invite_code':invite_code})

        if (password1 != password2):
            return render_to_response('hackerdojo.html', {'message':'Whoops, looks like your passwords didn\'t match.  Please try again.', 'email':email, 'invite_code':invite_code})
        try:
            validate_email(email)
        except:
            return render_to_response('hackerdojo.html', {'message':'Please enter a valid email address.', 'invite_code':invite_code})
        if not invite_code:
            return render_to_response('hackerdojo.html', {'message':'It looks like you forgot to enter an invite code.  Try again.', 'email':email})

	try:
            wl = WhiteList.objects.get(invite_code = invite_code)
	    if wl.email:
                return render_to_response('hackerdojo.html', {'message':'That invite code has already been used.  Please try again.', 'email':email})
            wl.email = email
            wl.save()
	except:
            return render_to_response('hackerdojo.html', {'message':'That invite code is invalid.  Please try again.', 'email':email})

        user = User()
        user.email = email
        user.passwd = hash_password(email, password1)
        user.save()


        request.session['email'] = email
	request.session['message'] = 'Thanks for signing up!'
        logging.info('%s joined successfully.' % email)
        return HttpResponseRedirect('/dashboard')

########NEW FILE########
__FILENAME__ = dashboard_account
from shared import *
import master_api
from django.core.mail import send_mail

@http_methods('GET')
@auth_required
def account(request):
    message = get_session_message(request)
    email = request.session.get('email')
    user = User.get_by_email(email)
    return render_to_response('dashboard_account.html', {
        'navbar_section':'dashboard',
        'user':user,
        'email':email,
        'sessionid': request.COOKIES['sessionid'],
        'message':message,
        'ssh_public_keys':user.get_ssh_public_keys()
    })

@http_methods('POST')
@token_required
@auth_required
def change_password(request):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login')

    user = User.get_by_email(email)
    if not user:
        return HttpResponseRedirect('/login')

    # Check that the user knew the old password
    old_password = request.POST.get('old_password')
    if user.passwd != hash_password(email, old_password):
        request.session['message'] = 'Incorrect old password.'
        return HttpResponseRedirect('/dashboard/account')

    # Confirm that the new passwords are the same and nonempty
    new_password1 = request.POST.get('new_password1')
    new_password2 = request.POST.get('new_password2')
    if (not new_password1) or (not new_password2) or (new_password1 != new_password2):
        request.session['message'] = 'New passwords do not match.'
        return HttpResponseRedirect('/dashboard/account')

    user.passwd = hash_password(email, new_password1)
    user.save()

    request.session['message'] = 'Password successfully changed.'
    return HttpResponseRedirect('/dashboard/account')

@http_methods('POST')
@token_required
@auth_required
def change_email(request):
    email = request.session.get('email')
    user = User.get_by_email(email)
    if not user:
        request.session['message'] = 'There was a problem looking up your user account.  Please contact support@djangy.com'
        return HttpResponseRedirect('/dashboard/account')

    new_email = request.POST.get('new_email')

    if not new_email:
        request.session['message'] = 'Invalid email address.'
        return HttpResponseRedirect('/dashboard/account')

    password = request.POST.get('password') or ''

    if hash_password(email, password) != user.passwd:
        request.session['message'] = 'Invalid password.'
        return HttpResponseRedirect('/dashboard/account')

    user.email = new_email
    user.passwd = hash_password(new_email, password)
    user.save()
    request.session['email'] = new_email
    request.session['message'] = 'Your email address has been updated.'
    return HttpResponseRedirect('/dashboard/account')

@http_methods('POST')
@token_required
@auth_required
def add_ssh_public_key(request):
    email = request.session.get('email')
    if not User.get_by_email(email):
        request.session['message'] = 'There was a problem looking up your user account.  Please contact support@djangy.com'
        return HttpResponseRedirect('/dashboard/account')

    ssh_public_key = request.POST.get('ssh_public_key')
    master_api.add_ssh_public_key(email, ssh_public_key)

    return HttpResponseRedirect('/dashboard/account')

@http_methods('GET')
@token_required
@auth_required
def remove_ssh_public_key(request):
    email = request.session.get('email')
    if not User.get_by_email(email):
        request.session['message'] = 'There was a problem looking up your user account.  Please contact support@djangy.com'
        return HttpResponseRedirect('/dashboard/account')

    ssh_public_key_id = int(request.GET.get('id'))
    master_api.remove_ssh_public_key(email, str(ssh_public_key_id))

    return HttpResponseRedirect('/dashboard/account')

########NEW FILE########
__FILENAME__ = dashboard_application
import re, traceback
from shared import *
import management_database
from management_database import *

def _check_application_access(func):
    """ Decorator for checking that the user has access to the selected application.  Use after auth_required. """
    def check_application_access(request, application_name):
        email = request.session.get('email')
        user = User.get_by_email(email)
        application = Application.get_by_name(application_name)
        if application and application.accessible_by(user):
            return func(request, application_name)
        else:
            return HttpResponseForbidden('Access denied for user "%s" to application "%s".' % (email, application_name))
    return check_application_access

# GET /dashboard/application/<application_name>
@http_methods('GET')
@auth_required
@_check_application_access
def application(request, application_name):
    email = request.session.get('email')
    user = User.get_by_email(email)
    application = Application.get_by_name(application_name)

    message = get_session_message(request)
    gunicorn_processes = Process.objects.filter(application__name=application_name, proc_type='gunicorn').aggregate(Sum('num_procs'))['num_procs__sum']
    celery_processes   = Process.objects.filter(application__name=application_name, proc_type='celery'  ).aggregate(Sum('num_procs'))['num_procs__sum']
    custom_domains = VirtualHost.get_virtualhosts_by_application_name(application_name)
    custom_domains.remove('%s.djangy.com' % application.name)
    return render_to_response('dashboard_application.html', {
        'navbar_section':'dashboard',
        'user': user,
        'application_name': application.name,
        'sessionid': request.COOKIES['sessionid'],
        'application_instances': gunicorn_processes,
        'application_instances_range': range(1, 10+1),
        'background_workers': celery_processes,
        'background_workers_range': range(0, 5+1),
        'message': message,
        'custom_domains': custom_domains,
        'enable_debug': application.debug,
        'enable_server_cache': application.is_server_cache_enabled(),
        'owner_email': application.account.email,
        'collaborator_emails': application.get_collaborators()
    })

# POST /dashboard/application/<application_name>/delete?really_delete=yes
@http_methods('POST')
@token_required
@auth_required
@_check_application_access
def delete_application(request, application_name):
    if not request.POST.get('really_delete'):
        return HttpResponseRedirect('/dashboard/application/%s' % application_name)

    try:
        remove_application(application_name)
    except Exception, e:
        return HttpResponseServerError('Error deleting application.')

    request.session['message'] = 'Application %s was deleted.' % application_name
    return HttpResponseRedirect('/dashboard')

# POST /dashboard/application/<application_name>/add_collaborator?email=<email>
@http_methods('POST')
@token_required
@auth_required
@_check_application_access
def add_collaborator(request, application_name):
    email = request.POST.get('email')
    if email != None:
        try:
            application = management_database.Application.get_by_name(application_name)
            if application.add_collaborator(email):
                request.session['message'] = 'Collaborator %s added to %s' % (email, application_name)
            else:
                request.session['message'] = 'Collaborator %s already has access to %s' % (email, application_name)
        except NoUserException as e:
            request.session['message'] = 'Error: %s does not have a Djangy account' % email
        except Exception as e:
            request.session['message'] = 'Error adding collaborator %s <br/><pre>%s</pre>' % (email, traceback.format_exc())

    return HttpResponseRedirect('/dashboard/application/%s' % application_name)

# GET /dashboard/application/<application_name>/remove_collaborator?email=<email>
@http_methods('GET')
@token_required
@auth_required
@_check_application_access
def remove_collaborator(request, application_name):
    email = request.GET.get('email')
    if email != None:
        try:
            application = Application.get_by_name(application_name)
            application.remove_collaborator(email)
            request.session['message'] = 'Collaborator %s removed from %s' % (email, application_name)
        except Exception:
            request.session['message'] = 'Error removing collaborator %s' % email

    return HttpResponseRedirect('/dashboard/application/%s' % application_name)

# GET /dashboard/application/<application_name>/logs
@http_methods('GET')
@auth_required
@_check_application_access
def logs(request, application_name):
    return HttpResponse(retrieve_logs(application_name), content_type='text/plain')

# POST /dashboard/application/<application_name>/debug?enable_debug=yes
@http_methods('POST')
@token_required
@auth_required
@_check_application_access
def debug_redirect(request, application_name):
    _application_debug(request, application_name)
    return HttpResponseRedirect('/dashboard/application/%s' % application_name)

# Called by application_debug_redirect()
#@http_methods('GET', 'POST')
#@token_required
#@auth_required
#@_check_application_access
def _application_debug(request, application_name):
    if request.method == 'POST':
        enable_debug = not not request.POST.get('enable_debug')
        toggle_debug(application_name, enable_debug)

    elif request.method == 'GET':
        enable_debug = Application.get_by_name(application_name).debug
        return HttpResponse(enable_debug)

# POST /dashboard/application/<application_name>/server_cache?enable_server_cache=yes
@http_methods('POST')
@token_required
@auth_required
@_check_application_access
def server_cache_redirect(request, application_name):
    server_cache = not not request.POST.get('enable_server_cache')
    if server_cache:
        enable_server_cache(application_name)
    else:
        disable_server_cache(application_name)
    return HttpResponseRedirect('/dashboard/application/%s' % application_name)

# POST /dashboard/application/<application_name>/allocation
@http_methods('POST')
@token_required
@auth_required
@_check_application_access
def application_allocation_redirect(request, application_name):
    if _has_billing_info(application_name):
        _application_allocation(request, application_name)
        return HttpResponseRedirect('/dashboard/application/%s' % application_name)
    else:
        request.session['message'] = "We need your billing info first!"
        return HttpResponseRedirect('/dashboard/billing')

def _require_int(str_int):
    try:
        return int(str_int)
    except:
        return None

# Called by application_allocation_redirect()
#@http_methods('POST')
#@token_required
#@auth_required
#@_check_application_access
def _application_allocation(request, application_name):
    application_processes = _require_int(request.POST.get('application_instances'))
    if application_processes == None:
        return HttpResponseBadRequest('Missing argument: application_instances')
    background_processes = _require_int(request.POST.get('background_workers'))
    if background_processes == None:
        return HttpResponseBadRequest('Missing argument: background_workers')
    result = update_application_allocation(application_name, {'application_processes':application_processes, 'background_processes':background_processes})
    if not result:
        return HttpResponseServerError('There was a problem saving changes.  Djangy staff has been notified.')

# called by application_allocation_redirect
def _has_billing_info(application_name):
    app = Application.get_by_name(application_name)
    if not app:
        return False
    cust_id = app.account.customer_id
    if cust_id == '-1' or cust_id == '' or cust_id is None:
        return False
    return True

_domain_name_regex = re.compile('^[A-Za-z0-9-][A-Za-z0-9-\.]*[A-Za-z0-9-]$')

def _valid_custom_domain(domain):
    return domain \
    and _domain_name_regex.match(domain) != None \
    and not domain.endswith('.djangy.com') \
    and domain != 'djangy.com'

# POST /dashboard/application/<application_name>/add_domain
@http_methods('POST')
@token_required
@auth_required
@_check_application_access
def add_domain_redirect(request, application_name):
    domain = request.REQUEST.get('domain')
    if _valid_custom_domain(domain):
        add_domain_name(application_name, domain)
    return HttpResponseRedirect('/dashboard/application/%s' % application_name)

# GET /dashboard/application/<application_name>/remove_domain?sessionid=...
@http_methods('GET')
@token_required
@auth_required
@_check_application_access
def remove_domain_redirect(request, application_name):
    domain = request.REQUEST.get('domain')
    if _valid_custom_domain(domain):
        delete_domain_name(application_name, domain)
    return HttpResponseRedirect('/dashboard/application/%s' % application_name)


########NEW FILE########
__FILENAME__ = dashboard_applicationlist
from shared import *

@http_methods('GET')
@auth_required
def applicationlist(request):
    message = get_session_message(request)
    email = request.session.get('email')

    user = User.get_by_email(email)
    applications = user.get_accessible_applications()
    return render_to_response('dashboard_applicationlist.html', {
        'navbar_section':'dashboard',
        'applications':applications,
        'user':user,
        'email':email,
        'message': message
    })

########NEW FILE########
__FILENAME__ = dashboard_billing
from shared import *
from master_api import update_billing_info as do_update_billing_info

# XXX - CSRF
@http_methods('GET', 'POST')
@auth_required
def update_billing_info(request):
    email = request.session.get('email')
    user = User.get_by_email(email)
    REQUIRED_KEYS = [
        'first_name',
        'last_name',
        'cc_number',
        'cvv',
        'expiration_month',
        'expiration_year'
    ]
    if request.method == 'GET':
        info = retrieve_billing_info(user)
        # if the values are in the session, restore them and remove from session
        for key in REQUIRED_KEYS:
            try:
                value = request.session.get(key, None)
                if value:
                    info[key] = value
                del request.session[key]
            except:
                pass
        message = get_session_message(request)
        amount = None
        usage = None
        try:
            amount = int(info['usage'])
            dollars = (amount / 100)
            cents = (amount % 100)
            usage = "$%s.%02d" % (dollars, cents)
        except:
            pass
        return render_to_response('dashboard_billing.html', {
            'navbar_section':'dashboard', 
            'user':user, 
            'info':info, 
            'message':message,
            'months':cc_months(),
            'years':cc_years(),
            'usage':usage,
        })
    elif request.method == 'POST':
        email = request.session.get('email')
        if not email:
            return HttpResponseRedirect('/dashboard')

        msg_mapper = {
            'cc_number':'Card number',
            'exp_month':'Expiration month',
            'exp_year':'Expiration year',
            'cvv':'CVV',
            'first_name':'First name',
            'last_name':'Last name'
        }
        info = dict()
        for k in REQUIRED_KEYS:
            value = request.POST.get(k, None)
            info[k] = value
            if k != 'cc_number':
                request.session[k] = value
        for k in REQUIRED_KEYS:
            if info[k] is None or info[k] == '':
                    request.session['message'] = 'Missing: %s' % msg_mapper.get(k, k)
                    return HttpResponseRedirect('/dashboard/billing')

        message = do_update_billing_info(email, info)
        if True == message:
            for k in REQUIRED_KEYS:
                try:
                    del request.session[k]
                except:
                    pass
            request.session['message'] = 'Your billing settings have been saved.  Thanks!'
        else:
            request.session['message'] = message
            return HttpResponseRedirect('/dashboard/billing')
        return HttpResponseRedirect('/dashboard')

########NEW FILE########
__FILENAME__ = dashboard_invite
from shared import *
import admin

@http_methods('GET', 'POST')
@auth_required
def invite(request):
    if request.method == 'POST':
        admin.invite(request)

    message = get_session_message(request)
    email = request.session.get('email')
    user = User.get_by_email(email)

    num_invited = User.objects.filter(referrer=user).count() + WhiteList.objects.filter(referrer=user).count()
    num_remaining_invitations = user.invite_limit - num_invited

    return render_to_response('dashboard_invite.html', {
        'navbar_section': 'dashboard',
        'user': user,
        'email': email,
        'sessionid': request.COOKIES['sessionid'],
        'message': message,
        'num_remaining_invitations': num_remaining_invitations
    })

########NEW FILE########
__FILENAME__ = index
from shared import *

@http_methods('GET')
def index(request):
    message = get_session_message(request)
    email = request.session.get('email')
    if email:
        user = User.get_by_email(email)
    else:
        user = None
    return render_to_response('index.html', {'navbar_section':'home', 'message':message, 'user':user, 'index':True})

@http_methods('GET')
def pricing(request):
    message = get_session_message(request)
    email = request.session.get('email')
    if email:
        user = User.get_by_email(email)
    else:
        user = None
    return render_to_response('pricing.html', {'navbar_section':'pricing', 'message':message, 'user':user, 'index':False})

########NEW FILE########
__FILENAME__ = login_logout
from shared import *

@http_methods('GET', 'POST')
def login(request):
    if request.session.get('email'):
        return HttpResponseRedirect('/dashboard')

    if request.method == 'GET':
        return render_to_response('login.html', {'navbar_section':'login'})

    email = request.POST.get('email')
    password = request.POST.get('password')

    # Check the login email address and hashed password
    try:
        validate_email(email)
        user = User.get_by_email(email)
        assert check_password(email, password, user.passwd)
    except:
        return render_to_response('login.html', {'navbar_section':'login', 'message':'Incorrect email address or password.  Please try again.'})

    # set session data
    request.session['email'] = email

    # redirect to the dashboard

    return HttpResponseRedirect('/dashboard')

# XXX - CSRF?
@http_methods('GET', 'POST')
def logout(request):
    try:
        del request.session['email']
    except KeyError:
        pass
    request.session['message'] = 'You have been logged out.'
    return HttpResponseRedirect('/login')

@http_methods('GET', 'POST')
def reset_password(request):
    reset_hash = request.GET.get('reset', None)
    if not reset_hash:
        request.session['message'] = 'No reset code supplied.'
        return HttpResponseRedirect('/')

    email = request.GET.get('email', None)
    if not email:
        request.session['message'] = 'No email code supplied.'
        return HttpResponseRedirect('/')

    user = User.get_by_email(email)
    if not user:
        request.session['message'] = 'Invalid user.'
        return HttpResponseRedirect('/')

    if check_password(email, user.passwd, reset_hash):
        # legit request, go ahead and process
        return render_to_response('reset_password_form.html', {'email': email})
    request.session['message'] = 'Invalid reset hash.'
    return HttpResponseRedirect('/')

@http_methods('POST')
def set_password(request):
    email = request.POST.get("email", None)
    if not email:
        return HttpResponseRedirect('/')
    password1 = request.POST.get('password1', None)
    password2 = request.POST.get('password2', None)
    if not password1 or not password2 or password1 != password2:
        request.session['message'] = 'Your passwords did not match.'
        return render_to_response('reset_password_form.html', {'email':email})
    user = User.get_by_email(email)
    if not user:
        return HttpResponseRedirect('/')
    user.passwd = hash_password(email, password1)
    user.save()
    request.session['message'] = 'Your password has been reset.'
    request.session['email'] = email
    return HttpResponseRedirect('/dashboard')

@http_methods('POST', 'GET')
def request_reset_password(request):
    if request.method.lower() == 'post':
        # send the email
        email = request.POST.get('email', None)
        if not email:
            return HttpResponseRedirect('/')
        user = User.get_by_email(email)
        if not user:
            return HttpResponseRedirect('/')
        reset_hash = hash_password(email, user.passwd)
        message_body = """

A password reset request has been requested for the Djangy account owned by this email address.  If this is correct, please click on the following link:

https://www.djangy.com/reset_password?email=%s&reset=%s

If not, please simply disregard this message or contact support@djangy.com.

-Djangy
        """ % (email, reset_hash)
        result = send_mail('Password Reset request', message_body, 'support@djangy.com', [email], fail_silently=False)
        request.session['message'] = 'Please check your email for a link to reset your password.'
        return HttpResponseRedirect('/')
    else: # GET request
        return render_to_response('request_reset_password.html')

########NEW FILE########
__FILENAME__ = shared
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound, HttpResponseNotAllowed, HttpResponseRedirect, HttpResponseServerError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.db.models import Sum
from web_ui.main.utils import check_password, hash_password
from web_ui.main.models import *
from web_ui.main.invite_code import gen_invite_code
from management_database import *
from master_api import *
import os, logging
from urllib import urlencode
from datetime import datetime

#
# Decorators that abstract out common checks for views.
#

# Decorator for views that require users to be logged in.
def auth_required(func):
    """ Decorator for views that require users to be logged in. """
    def _auth_required(request, *args, **kwargs):
        if not request.session.get('email'):
            return HttpResponseRedirect('/login')
        return func(request, *args, **kwargs)
    return _auth_required

# Decorator for views that perform an action and hence must be protected against CSRF.
def token_required(func):
    """ Decorator for views that perform an action and hence must be protected against CSRF. """
    def _token_required(request, *args, **kwargs):
        posted_session_id = request.REQUEST.get('sessionid')
        if posted_session_id != request.COOKIES['sessionid']:
            return HttpResponseForbidden('Invalid session information.')
        return func(request, *args, **kwargs)
    return _token_required

# Decorator for views only accessible to admin users.
def admin_required(func):
    """ Decorator for views only accessible to admin users. """
    def _admin_required(request, *args, **kwargs):
        user = User.get_by_email(request.session.get('email'))

        if not user.admin:
            return HttpResponseRedirect('/dashboard')
        return func(request, *args, **kwargs)
    return _admin_required

# Decorator for views that only accept certain HTTP request methods (e.g., GET, POST).
def http_methods(*methods):
    """ Decorator for views that only accept certain HTTP request methods (e.g., GET, POST). """
    def http_methods_decorator(func):
        def _http_methods(request, *args, **kwargs):
            if not request.method in methods:
                return HttpResponseNotAllowed(methods)
            else:
                return func(request, *args, **kwargs)
        return _http_methods
    return http_methods_decorator

#
# Helper functions
#

def get_session_message(request):
    """ Remove and return the message stored in the session.  This is a poor
        design which can mess up if the user runs two concurrent requests in
        the same session (race condition). """
    message = request.session.get('message')
    try:
        del request.session['message']
    except:
        pass
    return message

# Return True or False the status of whether or not the current session is an admin
def is_admin(request):
    email = request.session.get("email", None)
    if not email:
        return False
    user = User.get_by_email(email)
    if not user:
        return False
    return user.admin
 
def get_user(request):
    email = request.session.get("email", None)
    if not email:
        return False
    return User.get_by_email(email)

def cc_years():
    current_year = datetime.now().year
    return range(current_year, current_year + 12)

def cc_months():
    months = []
    for month in range(1, 13):
        if len(str(month)) == 1:
            numeric = '0' + str(month)
        else:
            numeric = str(month)
        months.append(numeric)
    return months

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for web_ui project.
import django, os

DEBUG = False
TEMPLATE_DEBUG = DEBUG

DJANGO_ROOT = os.path.dirname(os.path.realpath(django.__file__))
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

ADMINS = (
    ('Bob Jones', 'bob@jones.mil')
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE':'mysql',
        'NAME':'web_ui',
        'USER':'web_ui',
        'PASSWORD':'password goes here',
        'HOST':'',
        'PORT':'',
    },
    'management_database': {
        'ENGINE': 'mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'djangy',                      # Or path to database file if using sqlite3.
        'USER': 'djangy',                      # Not used with sqlite3.
        'PASSWORD': 'password goes here',      # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

DATABASE_ROUTERS = ['main.Router']

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'admin@djangy.com'
EMAIL_HOST_PASSWORD = 'password goes here'
EMAIL_USE_TLS = True

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'password goes here'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'web_ui.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(SITE_ROOT, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'web_ui.main',
    'web_ui.docs',
    'management_database',
    'south',
    'sentry.client',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)
SENTRY_KEY = 'password goes here'
SENTRY_REMOTE_URL = 'http://logsentry.djangy.com/sentry/store/'

import logging
from sentry.client.handlers import SentryHandler

logging.getLogger().addHandler(SentryHandler())

# Add StreamHandler to sentry's default so you can catch missed exceptions
logging.getLogger('sentry').addHandler(logging.StreamHandler())


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()
urlpatterns = patterns('',
    (r'^$', 'web_ui.main.views.index.index'),
    (r'^pricing$',                  'web_ui.main.views.index.pricing'),
    # Log in/log out/request password reset
    (r'^login$',                  'web_ui.main.views.login_logout.login'),
    (r'^logout$',                 'web_ui.main.views.login_logout.logout'),
    (r'^request_reset_password$', 'web_ui.main.views.login_logout.request_reset_password'),
    (r'^reset_password$', 'web_ui.main.views.login_logout.reset_password'),
    (r'^set_password$', 'web_ui.main.views.login_logout.set_password'),
    # Request account/create account using invite code
    (r'^signup$',     'web_ui.main.views.create_account.signup'),
    (r'^join$',       'web_ui.main.views.create_account.join'),
    (r'^hackerdojo$', 'web_ui.main.views.create_account.hackerdojo'),
    # Administrative dashboard
    (r'^admin$',        'web_ui.main.views.admin.admin'),
    (r'^admin/invite$', 'web_ui.main.views.admin.invite'),
    (r'^admin/get_emails$', 'web_ui.main.views.admin.get_emails'),
    # User dashboard
    (r'^dashboard$',                                                             'web_ui.main.views.dashboard_applicationlist.applicationlist'),
    (r'^dashboard/account$',                                                     'web_ui.main.views.dashboard_account.account'),
    (r'^dashboard/account/change_password$',                                     'web_ui.main.views.dashboard_account.change_password'),
    (r'^dashboard/account/change_email$',                                        'web_ui.main.views.dashboard_account.change_email'),
    (r'^dashboard/account/add_ssh_public_key$',                                  'web_ui.main.views.dashboard_account.add_ssh_public_key'),
    (r'^dashboard/account/remove_ssh_public_key$',                               'web_ui.main.views.dashboard_account.remove_ssh_public_key'),
    (r'^dashboard/invite$',                                                      'web_ui.main.views.dashboard_invite.invite'),
    (r'^dashboard/application/(?P<application_name>[^/]*)$',                     'web_ui.main.views.dashboard_application.application'),
    (r'^dashboard/application/(?P<application_name>[^/]*)/allocation$',          'web_ui.main.views.dashboard_application.application_allocation_redirect'),
    (r'^dashboard/application/(?P<application_name>[^/]*)/add_domain$',          'web_ui.main.views.dashboard_application.add_domain_redirect'),
    (r'^dashboard/application/(?P<application_name>[^/]*)/remove_domain$',       'web_ui.main.views.dashboard_application.remove_domain_redirect'),
    (r'^dashboard/application/(?P<application_name>[^/]*)/debug$',               'web_ui.main.views.dashboard_application.debug_redirect'),
    (r'^dashboard/application/(?P<application_name>[^/]*)/server_cache$',        'web_ui.main.views.dashboard_application.server_cache_redirect'),
    (r'^dashboard/application/(?P<application_name>[^/]*)/logs$',                'web_ui.main.views.dashboard_application.logs'),
    (r'^dashboard/application/(?P<application_name>[^/]*)/add_collaborator$',    'web_ui.main.views.dashboard_application.add_collaborator'),
    (r'^dashboard/application/(?P<application_name>[^/]*)/remove_collaborator$', 'web_ui.main.views.dashboard_application.remove_collaborator'),
    (r'^dashboard/application/(?P<application_name>[^/]*)/delete$',              'web_ui.main.views.dashboard_application.delete_application'),
    (r'^dashboard/billing$',                                                     'web_ui.main.views.dashboard_billing.update_billing_info'),
    # Documentation
    (r'^docs/', include('docs.urls')),
    # Static content -- note, we should run web_ui as a djangy application since we're using static.serve
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root':'static'}),
)

########NEW FILE########
__FILENAME__ = clear_cache
#!/usr/bin/env python
#
# Erase the nginx cache for a given application
# Example usage:
#   clear_cache.py application_name testapp
#

from shared import *
import os, os.path, shutil

def main():
    try:
        check_trusted_uid(sys.argv[0])
        kwargs = check_and_return_keyword_args(sys.argv, ['application_name'])
        clear_cache(**kwargs)
    except:
        log_last_exception()

def clear_cache(application_name):
    if is_valid_application_name(application_name):
        try:
            shutil.rmtree(os.path.join(NGINX_CACHE_DIR, application_name))
        except:
            # Cache may not yet exist
            pass

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = configure
#!/usr/bin/env python
#
# Configure the nginx proxy cache for a given application.
# Example usage:
#   configure.py application_name testapp http_virtual_hosts 'testapp.djangy.com www.testapp.com' worker_servers 'worker3.internal.djangy.com:8080' cache_index_size_kb 16 cache_size_kb 1024
#

import os
from shared import *
from mako.template import Template
from mako.lookup import TemplateLookup
import clear_cache

def main():
    try:
        check_trusted_uid(sys.argv[0])
        kwargs = check_and_return_keyword_args(sys.argv, ['application_name', \
            'http_virtual_hosts', 'worker_servers', 'cache_index_size_kb', 'cache_size_kb'])

        configure(**kwargs)
    except:
        log_last_exception()

def configure(application_name, http_virtual_hosts, worker_servers, cache_index_size_kb, cache_size_kb):
    create_config_file(application_name, http_virtual_hosts.split(','), \
        worker_servers.split(','), int(cache_index_size_kb), int(cache_size_kb))
    clear_cache.clear_cache(application_name)
    reload_nginx_conf()

def create_config_file(application_name, http_virtual_hosts, \
    worker_servers, cache_index_size_kb, cache_size_kb):

    # Create Nginx config file in nginx/conf/applications/
    #   http_virtual_hosts -- list of virtual host names
    #   worker_servers -- list of 'host:port' for workers
    #   cache_index_size -- in memory
    #   cache_size -- on disk/in disk cache
    print 'Generating nginx configuration file...',
    nginx_conf_path = os.path.join(NGINX_APP_CONF_DIR, '%s.conf' % application_name)

    # Remove the old config file
    try:
        os.remove(nginx_conf_path)
    except:
        pass

    if http_virtual_hosts != [] and worker_servers != []:
        # Create new config file
        upstream_servers = '\n    '.join(map(lambda x: 'server %s;' % x, worker_servers))
        generate_config_file('generic_nginx_conf', nginx_conf_path,
                             application_name    = application_name, \
                             http_virtual_hosts  = ' '.join(http_virtual_hosts), \
                             upstream_servers    = upstream_servers, \
                             cache_index_size_kb = cache_index_size_kb, \
                             cache_size_kb       = cache_size_kb)
        # Set permissions
        os.chown(nginx_conf_path, PROXYCACHE_UID, PROXYCACHE_GID)
        os.chmod(nginx_conf_path, 0600)

    print 'Done.'
    print ''

### Copied from master_manager.deploy ###
def generate_config_file(__template_name__, __config_file_path__, **kwargs):
    """Generate a bundle config file from a template, supplying arguments
    from kwargs."""

    # Load the template
    lookup = TemplateLookup(directories = [PROXYCACHE_TEMPLATE_DIR])
    template = lookup.get_template(__template_name__)
    # Instantiate the template
    instance = template.render(**kwargs)
    # Write the instantiated template to the bundle
    f = open(__config_file_path__, 'w')
    f.write(instance)
    f.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = delete_application
#!/usr/bin/env python
#
# Remove a given application from the nginx proxy cache
# Example usage:
#   remove_application.py application_name testapp
#

import os
from shared import *
from mako.template import Template
from mako.lookup import TemplateLookup

def main():
    try:
        check_trusted_uid(sys.argv[0])
        kwargs = check_and_return_keyword_args(sys.argv, ['application_name'])

        delete_application(**kwargs)
    except:
        log_last_exception()

def delete_application(application_name):
    print 'Removing nginx configuration file for %s...' % application_name
    nginx_conf_path = os.path.join(NGINX_APP_CONF_DIR, '%s.conf' % application_name)

    # Remove the old config file
    try:
        os.remove(nginx_conf_path)
    except:
        pass

    # Remove the cache
    print 'Removing nginx cache for %s...' % application_name
    clear_cache.clear_cache(application_name)

    reload_nginx_conf()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = nginx
from djangy_server_shared import *

def reload_nginx_conf():
    result = run_external_program([NGINX_BIN_PATH, '-t'])
    if result['exit_code'] != 0: # (note that 'nginx -t' outputs on stderr on success as well as failure)
        # Error should already be logged by run_external_program
        return
    run_external_program([NGINX_BIN_PATH, '-s', 'reload'])

########NEW FILE########
__FILENAME__ = bundle_info
from ConfigParser import RawConfigParser

def write_params(file_path, section_name, **params):
    config = RawConfigParser()
    config.add_section(section_name)
    for (k, v) in params.items():
        config.set(section_name, k, str(v))
    f = open(file_path, 'w')
    config.write(f)
    f.close()

class BundleInfo(object):
    def __init__(self, django_project_path, django_admin_media_path, \
        admin_media_prefix, admin_email, setup_uid, web_uid, cron_uid, \
        app_gid, user_settings_module_name, db_host, db_port, db_name, \
        db_username, db_password):

        self.django_project_path       = django_project_path
        self.django_admin_media_path   = django_admin_media_path
        self.admin_media_prefix        = admin_media_prefix
        self.admin_email               = admin_email
        self.setup_uid                 = setup_uid
        self.web_uid                   = web_uid
        self.cron_uid                  = cron_uid
        self.app_gid                   = app_gid
        self.user_settings_module_name = user_settings_module_name
        self.db_host                   = db_host
        self.db_port                   = db_port
        self.db_name                   = db_name
        self.db_username               = db_username
        self.db_password               = db_password

    def save_to_file(self, file_path):
        write_params(file_path, 'bundle_info', \
            django_project_path       = self.django_project_path, \
            django_admin_media_path   = self.django_admin_media_path, \
            admin_media_prefix        = self.admin_media_prefix, \
            admin_email               = self.admin_email, \
            setup_uid                 = self.setup_uid, \
            web_uid                   = self.web_uid, \
            cron_uid                  = self.cron_uid, \
            app_gid                   = self.app_gid, \
            user_settings_module_name = self.user_settings_module_name, \
            db_host                   = self.db_host, \
            db_port                   = self.db_port, \
            db_name                   = self.db_name, \
            db_username               = self.db_username, \
            db_password               = self.db_password)

    @staticmethod
    def load_from_file(file_path):
        parser = RawConfigParser()
        parser.read(file_path)
        return BundleInfo( \
            django_project_path       = parser.get('bundle_info', 'django_project_path'), \
            django_admin_media_path   = parser.get('bundle_info', 'django_admin_media_path'), \
            admin_media_prefix        = parser.get('bundle_info', 'admin_media_prefix'), \
            admin_email               = parser.get('bundle_info', 'admin_email'), \
            setup_uid                 = int(parser.get('bundle_info', 'setup_uid')), \
            web_uid                   = int(parser.get('bundle_info', 'web_uid')), \
            cron_uid                  = int(parser.get('bundle_info', 'cron_uid')), \
            app_gid                   = int(parser.get('bundle_info', 'app_gid')), \
            user_settings_module_name = parser.get('bundle_info', 'user_settings_module_name'), \
            db_host                   = parser.get('bundle_info', 'db_host'), \
            db_port                   = int(parser.get('bundle_info', 'db_port')), \
            db_name                   = parser.get('bundle_info', 'db_name'), \
            db_username               = parser.get('bundle_info', 'db_username'), \
            db_password               = parser.get('bundle_info', 'db_password'))

########NEW FILE########
__FILENAME__ = constants
import grp, os, pwd
import installer_configured_constants

# Users and groups
# DJANGY_USERNAME         = 'djangy'
# TODO: we should create a 'djangy' user which has ssh access to
# worker_manager and proxycache_manager hosts and can only run
# the worker_manager and proxycache_manager methods, but can't
# do just arbitrary things on its own.  (Right now we ssh as root.)
DJANGY_GROUPNAME        = 'djangy'
GIT_USERNAME            = 'git'
GIT_GROUPNAME           = 'git'
PROXYCACHE_USERNAME     = 'proxycache'
PROXYCACHE_GROUPNAME    = 'proxycache'
SHELL_USERNAME          = 'shell'
SHELL_GROUPNAME         = 'shell'
WWW_DATA_USERNAME       = 'www-data'
WWW_DATA_GROUPNAME      = 'www-data'

# UIDs and GIDs -- computed from users and groups
# DJANGY_UID              = pwd.getpwnam(DJANGY_USERNAME).pw_uid
DJANGY_GID              = grp.getgrnam(DJANGY_GROUPNAME).gr_gid
GIT_UID                 = pwd.getpwnam(GIT_USERNAME).pw_uid
GIT_GID                 = grp.getgrnam(GIT_GROUPNAME).gr_gid
PROXYCACHE_UID          = pwd.getpwnam(PROXYCACHE_USERNAME ).pw_uid
PROXYCACHE_GID          = grp.getgrnam(PROXYCACHE_GROUPNAME).gr_gid
SHELL_UID               = pwd.getpwnam(SHELL_USERNAME ).pw_uid
SHELL_GID               = grp.getgrnam(SHELL_GROUPNAME).gr_gid
ROOT_UID                = 0
ROOT_GID                = 0
WWW_DATA_UID            = pwd.getpwnam(WWW_DATA_USERNAME).pw_uid
WWW_DATA_GID            = grp.getgrnam(WWW_DATA_GROUPNAME).gr_gid

# Other shared constants
INSTALL_ROOT_DIR        = '/srv'
BUNDLES_DIR             = os.path.join(INSTALL_ROOT_DIR, 'bundles')
DJANGY_DIR              = os.path.join(INSTALL_ROOT_DIR, 'djangy')
LOGS_DIR                = os.path.join(INSTALL_ROOT_DIR, 'logs')
PYTHON_BIN_PATH         = os.path.join(DJANGY_DIR, 'run/python-virtual/bin/python')
BUNDLE_VERSION_PREFIX   = 'v1g'

#GITOSIS_ADMIN_DIR       = os.path.join(INSTALL_ROOT_DIR, 'scratch')
#GITOSIS_ADMIN_REPO      = 'git@%s:gitosis-admin.git' % installer_configured_constants.MASTER_MANAGER_HOST

DATABASE_ROOT_USER      = 'root'
DATABASE_ROOT_PASSWORD  = 'password goes here'

DEFAULT_DATABASE_HOST   = installer_configured_constants.DEFAULT_DATABASE_HOST # XXX
DEFAULT_PROXYCACHE_HOST = installer_configured_constants.DEFAULT_PROXYCACHE_HOST # XXX

TRUSTED_UIDS            = []

# Master constants
MASTER_TRUSTED_UIDS     = [ROOT_UID, GIT_UID, WWW_DATA_UID]

MASTER_SETUID_DIR       = os.path.join(DJANGY_DIR, 'run/master_manager/setuid')
MASTER_MANAGER_SRC_DIR  = os.path.join(DJANGY_DIR, 'src/server/master/master_manager')
GIT_SSH_DIR             = os.path.join(INSTALL_ROOT_DIR, 'git/.ssh')
SHELL_SSH_DIR           = os.path.join(INSTALL_ROOT_DIR, 'shell/.ssh')
AUTHORIZED_KEYS_MODE    = 0644
REPOS_DIR               = os.path.join(INSTALL_ROOT_DIR, 'git/repositories')
MASTER_MANAGER_HOST     = installer_configured_constants.MASTER_MANAGER_HOST # XXX - used to define BUNDLES_SRC_HOST for worker_manager below
DEVPAYMENTS_API_KEY     = installer_configured_constants.DEVPAYMENTS_API_KEY

GIT_SERVE_PATH          = '/srv/djangy/run/python-virtual/bin/git_serve.py'
SHELL_SERVE_PATH        = '/srv/djangy/run/master_manager/setuid/run_shell_serve'

# XXX deprecate chargify constants
CHARGIFY_SUBDOMAIN = 'subdomain goes here'
CHARGIFY_API_KEY = 'password goes here'
CHARGIFY_PRODUCT_ID = 14215
CHARGIFY_COMPONENTS = [
    ('worker_processes',1537)
]

# List of specific names applications can't have
RESERVED_APPLICATION_NAMES = [ 'djangy', 'www', 'www-s', 'https', 'ssl', 'secure', 'api', 'mail', 'localhost', 'web' ]

# blocked remote manage.py commands
BLOCKED_COMMANDS = [
    'runserver',
    'dbshell',
    'test',
    'testserver',
    'runfcgi',
    'changepassword',
    'compilemessages',
    'makemessages',
    'schemamigration',
    'datamigration'
]

# Worker constants
WORKER_TRUSTED_UIDS     = [ROOT_UID]

WORKER_SETUID_DIR       = os.path.join(DJANGY_DIR, 'run/worker_manager/setuid')
WORKER_MANAGER_SRC_DIR  = os.path.join(DJANGY_DIR, 'src/server/worker/worker_manager')
WORKER_MANAGER_VAR_DIR  = os.path.join(INSTALL_ROOT_DIR, 'worker_manager')
WORKER_TEMPLATE_DIR     = os.path.join(WORKER_MANAGER_SRC_DIR, 'templates')

BUNDLES_SRC_HOST        = MASTER_MANAGER_HOST
BUNDLES_SRC_DIR         = BUNDLES_DIR
BUNDLES_DEST_DIR        = BUNDLES_DIR

APACHE_SITES_AVAILABLE  = '/etc/apache2/sites-available'

LOGS                    = ['django.log', 'error.log', 'access.log', 'celery.log']

MAX_PROCS_PER_WORKER    = 100
WORKER_PORT_LOWER       = 20000
WORKER_PORT_UPPER       = 40000
DEFAULT_WORKER_PORT     = 20000

# Proxycache constants
PROXYCACHE_TRUSTED_UIDS = [ROOT_UID]

PROXYCACHE_SETUID_DIR   = os.path.join(DJANGY_DIR, 'run/proxycache_manager/setuid')
PROXYCACHE_TEMPLATE_DIR = os.path.join(DJANGY_DIR, 'src/server/proxycache/proxycache_manager/templates')

NGINX_DIR               = os.path.join(INSTALL_ROOT_DIR, 'proxycache_manager/nginx')
NGINX_BIN_PATH          = os.path.join(NGINX_DIR, 'sbin/nginx')
NGINX_APP_CONF_DIR      = os.path.join(NGINX_DIR, 'conf/applications')
NGINX_CACHE_DIR         = os.path.join(NGINX_DIR, 'cache')

########NEW FILE########
__FILENAME__ = exceptions
class BundleAlreadyExistsException(Exception):
    """Could not create a bundle because it already exists."""
    def __init__(self, bundle_name):
        self.bundle_name = bundle_name
    def __str__(self):
        return 'Could not create bundle "%s" because it already exists.' % self.bundle_name

class InvalidBundleException(Exception):
    """Invalid bundle."""
    def __init__(self, bundle_name):
        self.bundle_name = bundle_name
    def __str__(self):
        return 'Invalid bundle name "%s".' % self.bundle_name

class GitCloneException(Exception):
    """Error in git clone."""
    def __init__(self, application_name, temp_repo_path):
        self.application_name = application_name
        self.temp_repo_path   = temp_repo_path
    def __str__(self):
        return 'Error in git clone: application_name="%s" and temp_repo_path="%s"' % (self.application_name, self.temp_repo_path)

class CheckApplicationUidGidException(Exception):
    """Checking application uid/gid failed."""
    def __init__(self, id_type, id_value):
        self.id_type  = id_type
        self.id_value = id_value
    def __str__(self):
        return 'Checking application uid/gid failed: %i is not a valid %s.' % (self.id_value, self.id_type)

class SetUidGidFailedException(Exception):
    """Set uid/gid failed."""
    def __init__(self):
        pass
    def __str__(self):
        return self.__doc__

class InvalidApplicationNameException(Exception):
    """The requested application name does not comply with Djangy's application naming guidelines."""
    def __init__(self, application_name):
        self.application_name = application_name
    def __str__(self):
        return 'The application name "%s" does not comply with Djangy\'s application naming guidelines.' % self.application_name

class ApplicationNotInDatabaseException(Exception):
    """The requested application was not found in the management database."""
    def __init__(self, application_name):
        self.application_name = application_name
    def __str__(self):
        return 'Could not find application "%s" in management database.' % self.application_name

class ArgumentException(Exception):
    """Error parsing command-line argument list."""
    def __init__(self):
        pass
    def __str__(self):
        return self.__doc__

class RepeatedArgumentException(ArgumentException):
    """The same key was used for multiple command-line arguments."""
    def __init__(self, key):
        self.key = key
    def __str__(self):
        return 'The key "%s" was used for multiple command-line arguments.' % self.key

class UnexpectedArgumentException(ArgumentException):
    """An unknown key was used for a command-line argument."""
    def __init__(self, key):
        self.key = key
    def __str__(self):
        return 'Unknown key "%s" was used for a command-line argument.' % self.key

class MissingArgumentException(ArgumentException):
    """A command-line argument was missing."""
    def __init__(self):
        pass
    def __str__(self):
        return self.__doc__

class PasswordGenerationException(Exception):
    """Password generation failed."""
    def __init__(self):
        pass
    def __str__(self):
        return self.__doc__

########NEW FILE########
__FILENAME__ = find_django_project
import os.path

__DJANGO_PROJECT_DIR_FILES__ = set(['__init__.py', 'manage.py', 'settings.py', 'urls.py'])

def find_django_project(repo_path):
    """Finds a django project within the given repository.  If the
    repository contains more than one django project, an arbitrary one will
    be chosen.  Raises a NoDjangoProjectFoundException if the repository
    does not contain any django projects."""

    # Traverse a git repository, but don't follow symbolic links because we
    # don't know where they might point.
    for (dir_path, sub_dir_names, file_names) in os.walk(repo_path, topdown=True, followlinks=False):
        # Don't bother stepping into the .git directory
        if '.git' in sub_dir_names:
            sub_dir_names.remove('.git')
        # Check if we've found a django project
        if '__init__.py' in file_names and \
        dir_contains_module(dir_path, 'manage') and \
        dir_contains_module(dir_path, 'settings') and \
        dir_contains_module(dir_path, 'urls'):
            return dir_path

    # If we got here, we did an exhaustive search of the repository and
    # couldn't find a django project.
    raise DjangoProjectNotFoundException(repo_path)

def dir_contains_module(dir_path, module_name):
    return os.path.isfile(os.path.join(dir_path, module_name + '.py')) or \
        os.path.isdir(os.path.join(dir_path, module_name)) and \
        os.path.isfile(os.path.join(dir_path, module_name, '__init__.py'))

class DjangoProjectNotFoundException(Exception):
    """No django project found in the specified repository."""
    def __init__(self, repo_path):
        self.repo_path = repo_path
    def __str__(self):
        return 'No django project found in the repository "%s".' % self.repo_path

########NEW FILE########
__FILENAME__ = functions
import binascii, os, re, sys
from constants import *
from exceptions import *
from json_log import *
from run_external_program import *

def may_not_be_run_as(program_name, uid, gid):
    print_or_log_usage('%s may not be run by uid %i gid %i' % (program_name, uid, gid))
    sys.exit(1)

def check_trusted_uid(program_name):
    if not os.getuid() in TRUSTED_UIDS:
        may_not_be_run_as(program_name, os.getuid(), os.getgid())
    set_uid_gid(0, 0)

def check_setup_uid(setup_uid):
    if setup_uid < 100000 \
    or (setup_uid - 100000) % 3 != 0:
        raise CheckApplicationUidGidException('setup_uid', setup_uid)

def check_web_uid(web_uid):
    if web_uid < 100000 \
    or (web_uid - 100000) % 3 != 1:
        raise CheckApplicationUidGidException('web_uid', web_uid)

def check_cron_uid(cron_uid):
    if cron_uid < 100000 \
    or (cron_uid - 100000) % 3 != 2:
        raise CheckApplicationUidGidException('cron_uid', cron_uid)

def check_app_gid(app_gid):
    if app_gid < 100000 \
    or (app_gid - 100000) % 3 != 0:
        raise CheckApplicationUidGidException('app_gid', app_gid)

def become_application_setup_uid_gid(program_name, setup_uid, app_gid):
    try:
        check_setup_uid(setup_uid)
        check_app_gid(app_gid)
        set_uid_gid(setup_uid, setup_uid)
    except Exception as e:
        may_not_be_run_as(program_name, setup_uid, app_gid)

def become_uid_gid(program_name, uid, gid, groups=[]):
    try:
        set_uid_gid(uid, gid, groups)
    except Exception as e:
        may_not_be_run_as(program_name, os.getuid(), os.getgid())

def check_positional_args(args, expected_num_args, help_string):
    if len(args) != expected_num_args+1:
        print_or_log_usage('Usage: %s %s' % (args[0], help_string))
        sys.exit(1)

def check_and_return_keyword_args(args, required_keys, optional_keys=None):
    try:
        return arg_list_to_dict(args[1:], required_keys, optional_keys)
    except ArgumentException as e:
        required_keys_message = ' '.join(map(lambda key: key + ' <x>', required_keys))
        if optional_keys:
            optional_keys_message = ' '.join(map(lambda key: '[%s <x>]' % key, optional_keys))
            print_or_log_usage('Usage: %s %s %s' % (args[0], required_keys_message, optional_keys_message))
        else:
            print_or_log_usage('Usage: %s %s' % (args[0], required_keys_message))
        sys.exit(1)

def arg_list_to_dict(args, required_keys, optional_keys=None):
    """Converts a list of alternating key-value pairs to a dictionary. 
    Checks that the dictionary keys are equal to a given list of expected
    keys."""
    dict = {}
    required_keys_used = []
    if optional_keys:
        allowed_keys = required_keys + optional_keys
    else:
        allowed_keys = required_keys
    for i in range(0, len(args)/2*2, 2):
        key   = args[i]
        value = args[i+1]
        if dict.has_key(key):
            raise RepeatedArgumentException()
        if not key in allowed_keys:
            raise UnexpectedArgumentException(key)
        dict[key] = value
        if key in required_keys:
            required_keys_used.append(key)
    if sort(required_keys_used) != sort(required_keys):
        raise MissingArgumentException()
    return dict

def sort(list):
    sorted_list = list + []
    sorted_list.sort()
    return sorted_list

def set_uid_gid(uid, gid, groups=[]):
    os.setgid(gid)
    os.setegid(gid)
    os.setgroups(groups)
    os.setuid(uid)
    os.seteuid(uid)
    if os.getgid() != gid or os.getegid() != gid \
    or os.getuid() != uid or os.geteuid() != uid \
    or (os.getgroups() != [] and os.getgroups != [gid]):
        raise SetUidGidFailedException()

# Validation for djangy projects/applications
def is_valid_application_name(application_name):
    return (re.match('^[A-Za-z][A-Za-z0-9]*$', application_name) != None)

def check_application_name(application_name):
    if not is_valid_application_name(application_name):
        raise InvalidApplicationNameException()

# Validation for django apps within a djangy project/application
def is_valid_django_app_name(django_app_name):
    return (re.match('^[A-Za-z_][A-Za-z0-9_]*$', django_app_name) != None)

def recursive_chown_chmod(bundle_path, uid, gid, mode):
    # Make sure we're not changing BUNDLES_DIR itself!
    if bundle_path.strip(' /') == '':
        raise InvalidBundleException()
    # chown/chmod bundle to setup_uid
    run_external_program(['chown', '-R', str(uid) + ':' + str(gid), bundle_path], cwd=bundle_path)
    run_external_program(['chmod', '-R', mode, bundle_path], cwd=bundle_path)

def gen_password():
    """ Generate a random 24-character password. """
    password1 = binascii.b2a_base64(os.urandom(9))[:-1]
    password2 = binascii.b2a_base64(os.urandom(9))[:-1]
    if len(password1) != 12 or len(password2) != 12 or password1 == password2:
        raise PasswordGenerationException()
    return password1 + password2

########NEW FILE########
__FILENAME__ = installer_configured_constants
# This is a placeholder version of this file; in an actual installation, it
# is generated from scratch by the installer.  The constants defined here
# are exposed by constants.py

DEFAULT_DATABASE_HOST   = None # XXX
DEFAULT_PROXYCACHE_HOST = None # XXX
MASTER_MANAGER_HOST     = None # XXX - used to define BUNDLES_SRC_HOST for worker_manager below
DEVPAYMENTS_API_KEY     = None

########NEW FILE########
__FILENAME__ = json_log
import json, os, socket, sys, time, traceback
import logging
#from sentry.client.base import SentryClient

__log_file_path__ = None
__log_file__ = None

class LogFileAlreadyOpenException(Exception):
    """Tried to open a different log file when the log file was already open."""
    def __init__(self, old_log_file, new_log_file):
        self.old_log_file = old_log_file
        self.new_log_file = new_log_file
    def __str__(self):
        return 'Tried to open new log file "%s" when old log file "%s%" was already open.' % (self.new_log_file, self.old_log_file)

def open_log_file(log_file_path, mode):
    global __log_file_path__
    global __log_file__
    if __log_file__ != None:
        if __log_file_path__ != log_file_path:
            raise LogFileAlreadyOpenException(__log_file_path__, log_file_path)
    else:
        __log_file_path__ = log_file_path
        __log_file__ = open(log_file_path, 'a')
        os.chmod(log_file_path, mode)

def __format_time_utc__(time_struct):
    return "%04i-%02i-%02i %02i:%02i:%02i.%03i UTC" % \
        (time_struct['tm_year'], time_struct['tm_mon'], time_struct['tm_mday'], \
         time_struct['tm_hour'], time_struct['tm_min'], time_struct['tm_sec'], time_struct['tm_msec'])

def __current_time_utc__():
    time_struct = time.gmtime()
    tm_msec = int(time.time() * 1000) % 1000
    time_dict = { \
        'tm_year': time_struct.tm_year, \
        'tm_mon' : time_struct.tm_mon, \
        'tm_mday': time_struct.tm_mday, \
        'tm_hour': time_struct.tm_hour, \
        'tm_min' : time_struct.tm_min, \
        'tm_sec' : time_struct.tm_sec, \
        'tm_msec': tm_msec \
    }
    return __format_time_utc__(time_dict)

def __format_list_as_struct__(list):
    out = '{'
    if len(list) % 2 == 1:
        list = list[:-1]
    for i in range(0, len(list), 2):
        if i > 0:
            out = out + ', '
        out = out + json.dumps(list[i]) + ':' + json.dumps(list[i+1])
    out = out + '}'
    return out

def __make_log_entry__(*args):
    ip = socket.gethostbyname(socket.gethostname())
    return __format_list_as_struct__(['date_time_utc', __current_time_utc__(), 'epoch_time', time.time(), \
        'host_ip', ip, 'program', sys.argv[0], 'pid', os.getpid(), 'uid', os.getuid(), 'gid', os.getgid()] \
        + list(args))

def log(*args):
    log_file = __log_file__
    if log_file == None:
        log_file = sys.stderr
    log_entry = __make_log_entry__(*args)
    log_file.write(log_entry + '\n')
    log_file.flush()

def print_or_log_usage(usage):
    if os.isatty(1):
        print usage
    else:
        log('type', 'USAGE_ERROR', 'usage', usage)

def log_info_message(message, *args):
    #SentryClient().create_from_text(message, level = logging.INFO)
    log('type', 'INFO_MESSAGE', 'message', message, *args)

def log_error_message(message, *args):
    #SentryClient().create_from_text(message, level = logging.ERROR)
    log('type', 'ERROR_MESSAGE', 'message', message, *args)

def log_warning_message(message, *args):
    #SentryClient().create_from_text(message, level = logging.WARN)
    log('type', 'WARNING_MESSAGE', 'message', message, *args)

def log_external_program(external_program_args, result, *args):
    #SentryClient().create_from_text("EXTERNAL PROGRAM ERROR: %s" % external_program_args, level = logging.ERROR)
    log('type', 'EXTERNAL_PROGRAM_ERROR', 'external_program_args', external_program_args, \
        'external_program_pid', result['pid'], 'exit_code', result['exit_code'], \
        'stdout', result['stdout_contents'], 'stderr', result['stderr_contents'], *args)

def log_external_program_log_stderr(external_program_args, result, *args):
    log('type', 'BEGIN_EXTERNAL_PROGRAM_LOG', 'external_program_args', external_program_args, \
        'external_program_pid', result['pid'], 'exit_code', result['exit_code'], \
        'stdout', result['stdout_contents'], 'stderr_follows_in_log', True, *args)
    for message in result['stderr_contents'].split('\n'):
        log(message)
    log('type', 'END_EXTERNAL_PROGRAM_LOG', 'external_program_pid', result['pid'])

def __log_exception__(exception, *args):
    log('type', 'EXCEPTION', 'class', exception.__class__.__name__, 'message', str(exception), *args)

def log_last_exception(*args):
    #SentryClient().create_from_exception()
    (_, exception, _) = sys.exc_info()
    __log_exception__(exception, 'traceback', traceback.format_exc(), *args)

########NEW FILE########
__FILENAME__ = resource_allocation
class ResourceAllocation(object):
    def __init__(self, num_procs, proc_num_threads, proc_mem_mb, proc_stack_mb, debug, http_virtual_hosts, host, port, celery_procs):
        self.num_procs          = num_procs
        self.proc_num_threads   = proc_num_threads
        self.proc_mem_mb        = proc_mem_mb
        self.proc_stack_mb      = proc_stack_mb
        self.debug              = debug
        self.http_virtual_hosts = http_virtual_hosts
        self.host               = host
        self.port               = port
        self.celery_procs       = celery_procs

    def to_command_line(self):
        return ['num_procs',          str(self.num_procs), \
                'proc_num_threads',   str(self.proc_num_threads), \
                'proc_mem_mb',        str(self.proc_mem_mb), \
                'proc_stack_mb',      str(self.proc_stack_mb), \
                'debug',              str(self.debug), \
                'http_virtual_hosts', ','.join(http_virtual_hosts), \
                'host',               self.host, \
                'port',               str(self.port), \
                'celery_procs',       str(self.celery_procs)]

    @staticmethod
    def from_command_line_dict(dict):
        return ResourceAllocation(
            num_procs          = int(dict['num_procs']),
            proc_num_threads   = int(dict['proc_num_threads']),
            proc_mem_mb        = int(dict['proc_mem_mb']),
            proc_stack_mb      = int(dict['proc_stack_mb']),
            debug              = (dict['debug'] == 'True'),
            http_virtual_hosts = dict['http_virtual_hosts'].split(','),
            host               = dict['host'],
            port               = int(dict['port']),
            celery_procs       = int(dict['celery_procs']))

########NEW FILE########
__FILENAME__ = run_external_program
import os, subprocess, sys, tempfile
from json_log import *

class RunExternalProgramException(Exception):
    """Exception trying to run external program."""
    def __init__(self, args, cause_exception):
        self.args            = args
        self.cause_exception = cause_exception
    def __str__(self):
        return 'Exception %s trying to run external program %s.' % (str(self.cause_exception), str(self.args))

def external_program_encountered_error(result):
    return result['exit_code'] != 0 # or len(result['stderr_contents']) > 0

class ExternalProgram(object):
    def __init__(self, args, cwd=None, preexec_fn=None, pass_stdin=False, pass_stdout=False, pass_stderr=False, stdin_contents=None, stderr_to_stdout=False, log_stderr=False):
        self._args             = args
        self._cwd              = cwd
        self._preexec_fn       = preexec_fn
        self._pass_stdin       = pass_stdin
        self._pass_stdout      = pass_stdout
        self._pass_stderr      = pass_stderr
        self._stdin_contents   = stdin_contents
        self._stderr_to_stdout = stderr_to_stdout
        self._log_stderr       = log_stderr
        self._has_started      = False
        self._has_finished     = False
    def run(self):
        self.start()
        return self.finish()
    def start(self):
        if self._has_started:
            return
        self._has_started = True
        try:
            # Flush output if necessary
            if self._pass_stdout:
                sys.stdout.flush()
            if self._pass_stderr:
                sys.stderr.flush()
            # Create temporary files to redirect stdin/stdout/stderr
            temp_stdin       = tempfile.NamedTemporaryFile()
            self._temp_stdout = tempfile.NamedTemporaryFile()
            self._temp_stderr = tempfile.NamedTemporaryFile()
            # After fork(), we will run this to redirect stdin/stdout/stderr
            def run_process_preexec_fn():
                if not self._pass_stdin and self._stdin_contents == None:
                    os.dup2(os.open(temp_stdin.name, os.O_RDONLY), 0)
                if not self._pass_stdout:
                    os.dup2(os.open(self._temp_stdout.name, os.O_WRONLY), 1)
                if not self._pass_stderr:
                    if self._stderr_to_stdout:
                        os.dup2(1, 2)
                    else:
                        os.dup2(os.open(self._temp_stderr.name, os.O_WRONLY), 2)
                if self._preexec_fn != None:
                    self._preexec_fn()
            # Start the subprocess--calls above function.
            self._stdin_flag = None
            if self._stdin_contents != None:
                self._stdin_flag = subprocess.PIPE
            self._process = subprocess.Popen(self._args, preexec_fn=run_process_preexec_fn, \
                executable=self._args[0], close_fds=True, shell=False, cwd=self._cwd, stdin=self._stdin_flag)
            if self._stdin_contents != None:
                self._process.stdin.write(self._stdin_contents)
                self._process.stdin.close()
        except Exception as e:
            # Couldn't run external program.  Log the exception.
            log_last_exception('external_program_args', self._args)
            raise RunExternalProgramException(self._args, e)

    def finish(self):
        if self._has_finished or not self._has_started:
            return None
        self._has_finished = True
        try:
            # Run the subprocess to completion
            pid = self._process.pid
            exit_code = self._process.wait()
            # Read out stdout/stderr
            stdout_contents = self._temp_stdout.read()
            stderr_contents = self._temp_stderr.read()
            # Close stdout/stderr
            self._temp_stdout.close()
            self._temp_stderr.close()
            # Return full results
            result = { \
                'pid'            : pid, \
                'exit_code'      : exit_code, \
                'stdout_contents': stdout_contents, \
                'stderr_contents': stderr_contents \
            }
            # (but first, log any error)
            if external_program_encountered_error(result):
                if self._log_stderr:
                    log_external_program_log_stderr(self._args, result)
                else:
                    log_external_program(self._args, result)
            return result
        except Exception as e:
            # Couldn't run external program.  Log the exception.
            log_last_exception('external_program_args', self._args)
            raise RunExternalProgramException(self._args, e)

def run_external_program(*args, **kwargs):
    return ExternalProgram(*args, **kwargs).run()

########NEW FILE########
__FILENAME__ = delete_application
#!/usr/bin/env python
#
# Stops and removes application from LocalApplication table but doesn't
# remove bundles or logs.
#

from shared import *

def main():
    try:
        check_trusted_uid(program_name = sys.argv[0])
        kwargs = check_and_return_keyword_args(sys.argv, ['application_name'])

        application_name = kwargs['application_name']

        delete_application(application_name)
    except:
        log_last_exception()

@lock_application
def delete_application(application_name):
    stop_application(application_name)
    application_info = LocalApplication.objects.get(application_name = application_name)
    application_info.delete()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = deploy
#!/usr/bin/env python

from shared import *
from mako.lookup import TemplateLookup
from django.core.exceptions import ObjectDoesNotExist
import re

def main():
    try:
        check_trusted_uid(sys.argv[0])
        kwargs = check_and_return_keyword_args(sys.argv, ['application_name', 'bundle_version',
            'num_procs', 'proc_num_threads', 'proc_mem_mb', 'proc_stack_mb', 'debug', 'http_virtual_hosts',
            'host', 'port', 'celery_procs'])

        application_name    = kwargs['application_name']
        bundle_version      = kwargs['bundle_version']
        resource_allocation = ResourceAllocation.from_command_line_dict(kwargs)

        set_application_allocation(application_name, resource_allocation)
        deploy_application(application_name    = application_name,
                           bundle_version      = bundle_version,
                           resource_allocation = resource_allocation)
    except:
        log_last_exception()

def set_application_allocation(application_name, resource_allocation):
    # Try to find an existing application
    try:
        application_info = LocalApplication.objects.get(application_name = application_name)
        # Uses manual locking rather than @lock_application because we have
        # to gracefully handle the case of creating a new object.
        lock = LocalApplicationLocks.lock(application_name)
    except ObjectDoesNotExist:
        # Or create a new one
        # XXX race condition if two LocalApplications with the same application_name are created concurrently...
        application_info = LocalApplication(application_name = application_name, is_stopped = False)
        lock = None

    ra = resource_allocation

    # Set fields
    application_info.num_procs        = ra.num_procs
    application_info.proc_num_threads = ra.proc_num_threads
    application_info.proc_mem_mb      = ra.proc_mem_mb
    application_info.proc_stack_mb    = ra.proc_stack_mb
    application_info.port             = ra.port
    application_info.celery_procs     = ra.celery_procs

    application_info.save()

    print lock
    LocalApplicationLocks.unlock(lock)

@lock_application
def deploy_application(application_name, bundle_version, resource_allocation):
    # Note that because this function is wrapped in @_lock_application,
    # it will raise an exception if called before set_application_allocation()

    # Compose bundle_name
    bundle_name = application_name + '-' + bundle_version

    # Copy bundle
    application_info = LocalApplication.objects.get(application_name=application_name)
    old_bundle_version = application_info.bundle_version
    bundle_info = copy_bundle_from_remote_host(application_name, bundle_version, old_bundle_version)

    # Stop old version of application
    should_restart = stop_application(application_name)
    # Either delete an application with zero processes or restart one with nonzero.
    if resource_allocation.num_procs == 0 and resource_allocation.celery_procs == 0:
        application_info.delete()
    else:
        try:
            # Create configuration files from templates
            create_config_files(application_name, bundle_version, bundle_name, bundle_info, resource_allocation)
            # Update current bundle version in database
            application_info.bundle_version = bundle_version
            application_info.save()
            # Create log files
            create_log_files(bundle_name, bundle_info.web_uid, bundle_info.app_gid)
        finally:
            # Start new version of application
            if should_restart:
                start_application(application_name)

    # If it all worked, we can delete the old bundle now...
    # For now, we just mark it by creating a file called 'old'
    if old_bundle_version and old_bundle_version != bundle_version:
        try:
            make_file(os.path.join(BUNDLES_DEST_DIR, application_name + '-' + old_bundle_version, 'old'), 0600)
        except:
            # Old bundle doesn't exist
            log_last_exception()

# Note: we should make as much of this as possible run without root
# permissions.  The tricky part is we need to know what permissions are
# needed, because the remote bundle's bundle_info.config file specifies
# its UIDs and GID...
def copy_bundle_from_remote_host(application_name, bundle_version, old_bundle_version):
    bundle_name           = application_name + '-' + bundle_version
    local_bundle_path     = os.path.join(BUNDLES_DEST_DIR,  bundle_name)
    remote_bundle_path    = BUNDLES_SRC_HOST + ':' + os.path.join(BUNDLES_SRC_DIR, bundle_name)
    #remote_bundle_path    = os.path.join(BUNDLES_SRC_DIR, bundle_name)
    if old_bundle_version != None:
        old_bundle_name       = application_name + '-' + old_bundle_version
        local_old_bundle_path = os.path.join(BUNDLES_DEST_DIR,  old_bundle_name)
    else:
        old_bundle_name       = ''
        local_old_bundle_path = ''

    # Check if bundle already exists
    if os.path.exists(local_bundle_path):
        # Assume the bundle is ok--but log a warning!
        log_warning_message('Warning: bundle "%s" already exists' % bundle_name)
        return BundleInfo.load_from_file(os.path.join(local_bundle_path, 'config', 'bundle_info.config'))

    # Copy bundle:
    # 1. Create a temporary directory to copy the new bundle into
    local_temp_bundle_path = tempfile.mkdtemp(dir=BUNDLES_DEST_DIR, prefix='tmp-' + bundle_name + '-', suffix='.download')

    # 2. Make a hard link "copy" of the existing bundle (speeds up rsync)
    if local_old_bundle_path != None and local_old_bundle_path != '':
        sys.stdout.flush()
        result = run_external_program(['cp', '-alT', local_old_bundle_path, local_temp_bundle_path])
        if external_program_encountered_error(result):
            log_error_message('Error copying old bundle "%s" as baseline for new bundle "%s"' % (old_bundle_name, bundle_name))

    # 3. Use rsync to copy over the changes.  Trailing / on remote_bundle_path is critical.
    sys.stdout.flush()
    result = run_external_program(['rsync', '-a', '--delete', remote_bundle_path + '/', local_temp_bundle_path])
    if external_program_encountered_error(result):
        log_error_message('Error downloading bundle "%s"' % bundle_name)

    # 4. Change ownership from bundles to setup_uid:app_gid
    bundle_info = BundleInfo.load_from_file(os.path.join(local_temp_bundle_path, 'config', 'bundle_info.config'))
    recursive_chown_chmod(local_temp_bundle_path, 0, bundle_info.app_gid, '0750')

    # 5. Rename temporary directory to final bundle directory
    try:
        os.rename(local_temp_bundle_path, local_bundle_path)
    except OSError as e:
        # This might happen if another process created the bundle while we
        # were busy.  Assume the bundle is ok--but log a warning!
        log_last_exception('custom_message', 'Warning: error copying downloaded bundle "%s"' % bundle_name)
        # TODO: it would be nice if we could mark the above as a warning.

    return bundle_info

def create_config_files(application_name, bundle_version, bundle_name, bundle_info, resource_allocation):
    bi = bundle_info
    ra = resource_allocation

    # Compute bundle path
    bundle_path = os.path.join(BUNDLES_DEST_DIR, bundle_name)
    config_path = os.path.join(bundle_path, 'config')

    (django_project_parent_path, django_project_module_name) = os.path.split(bi.django_project_path)

    # Remove old config files (if any)
    remove_no_exception(os.path.join(config_path, 'gunicorn.conf'))
    remove_no_exception(os.path.join(config_path, 'runnable.py'))
    remove_no_exception(os.path.join(bi.django_project_path, 'settings.py'))
    remove_no_exception(os.path.join(bi.django_project_path, 'settings/__init__.py'))

    os.umask(0227)

    # Create production settings.py file in <bundle path>/application/.../settings.py
    # (code also exists in master_manager.deploy)
    print 'Creating production settings.py file...',
    if os.path.isdir(os.path.join(bi.django_project_path, 'settings')):
        settings_path = os.path.join(bi.django_project_path, 'settings', '__init__.py')
    else:
        settings_path = os.path.join(bi.django_project_path, 'settings.py')
    generate_config_file('generic_settings', settings_path,
                         user_settings_module_name  = bi.user_settings_module_name,
                         db_host                    = bi.db_host,
                         db_port                    = bi.db_port,
                         db_name                    = bi.db_name,
                         db_username                = bi.db_username,
                         db_password                = bi.db_password,
                         bundle_name                = bundle_name,
                         application_name           = application_name,
                         celery_procs               = ra.celery_procs,
                         debug                      = ra.debug)
    os.chown(settings_path, 0, bi.app_gid)
    os.chmod(settings_path, 0750)
    print 'Done.'
    print ''

    # Create Django WSGI file in <django_project_path>/runnable_<bundle_version>.py
    print 'Generating django wsgi script for your project...',
    django_wsgi_path = os.path.join(config_path, 'runnable_%s.py' % bundle_version)
    if is_nonempty_file(os.path.join(bi.django_project_path, '__init__.py')):
        settings_module = '%s.settings' % os.path.basename(bi.django_project_path)
    else:
        settings_module = 'settings'
    # XXX - Try reenabling RLIMIT_NOFILE in generic_django_wsgi
    generate_config_file('generic_django_wsgi', django_wsgi_path, \
                         django_project_path        = escape(bi.django_project_path), \
                         django_project_parent_path = escape(django_project_parent_path), \
                         application_name           = application_name, \
                         bundle_name                = bundle_name, \
                         rlimit_data                = str(ra.proc_mem_mb - ra.proc_stack_mb), \
                         rlimit_stack               = str(ra.proc_stack_mb), \
                         rlimit_rss                 = str(ra.proc_mem_mb), \
                         rlimit_nproc               = str(ra.proc_num_threads * ra.num_procs), \
                         settings_module            = settings_module)
    os.chown(django_wsgi_path, 0, bi.app_gid)
    os.chmod(django_wsgi_path, 0750)
    print 'Done.'
    print ''

    # Create Gunicorn config file in <bundle path>/config/gunicorn.conf
    print 'Generating gunicorn configuration file...',
    gunicorn_conf_path   = os.path.join(config_path, 'gunicorn.conf')
    generate_config_file('generic_gunicorn_conf', gunicorn_conf_path,
                         application_name           = application_name, \
                         bundle_name                = bundle_name, \
                         web_uid                    = str(bi.web_uid), \
                         app_gid                    = str(bi.app_gid), \
                         num_processes              = str(ra.num_procs), \
                         host                       = ra.host, \
                         port                       = ra.port)
    os.chown(gunicorn_conf_path, 0, bi.app_gid)
    os.chmod(gunicorn_conf_path, 0750)
    print 'Done.'
    print ''

def is_nonempty_file(path):
    if not os.path.isfile(path):
        return False
    return os.stat(path).st_size > 0

def escape(text):
    text1 = re.sub('(\'|\"|\\\\)', '\\\\\\1', text)
    text2 = re.sub('\n', '\\\\n', text1)
    return text2

def remove_no_exception(path):
    try:
        os.remove(path)
    except:
        pass

### Copied from master_manager.deploy ###
def generate_config_file(__template_name__, __config_file_path__, **kwargs):
    """Generate a bundle config file from a template, supplying arguments
    from kwargs."""

    # Load the template
    lookup = TemplateLookup(directories = [WORKER_TEMPLATE_DIR])
    template = lookup.get_template(__template_name__)
    # Instantiate the template
    instance = template.render(**kwargs)
    # Write the instantiated template to the bundle
    f = open(__config_file_path__, 'w')
    f.write(instance)
    f.close()

def relink(src_path, link_path):
    """Equivalent to ln -sf: create a symbolic link, overriding any existing
    target link or file."""
    try:
        os.remove(link_path)
    except OSError as e:
        # Old link didn't exist, not a problem.
        pass
    os.symlink(src_path, link_path)

def create_log_files(bundle_name, web_uid, app_gid):
    """Create the /srv/logs/<bundle_name> directory and initially empty
    django and web server log files."""
    logdir_path = os.path.join(LOGS_DIR, bundle_name)
    try:
        os.mkdir(logdir_path, 0770)
        os.chown(logdir_path, 0, app_gid)
        os.chmod(logdir_path, 0770)
    except OSError as e:
        # Should log this--ok if it's just because the file exists.
        if not os.path.exists(logdir_path):
            log_last_exception('custom_message', 'Error: could not create log directory "%s"' % logdir_path)
            return
    for log_name in LOGS:
        logfile_path = os.path.join(logdir_path, log_name)
        try:
            make_file(logfile_path, 0660)
            os.chown(logfile_path, web_uid, app_gid)
            os.chmod(logfile_path, 0660)
        except OSError as e:
            log_last_exception('custom_message', 'Error: could not create log file "%s"' % logfile_path)

def make_file(path, mode):
    os.close(os.open(path, os.O_CREAT, mode))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'LocalApplication'
        db.create_table('local_application', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application_name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('bundle_version', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('is_stopped', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('num_procs', self.gf('django.db.models.fields.IntegerField')()),
            ('proc_num_threads', self.gf('django.db.models.fields.IntegerField')()),
            ('proc_mem_mb', self.gf('django.db.models.fields.IntegerField')()),
            ('proc_stack_mb', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('orm', ['LocalApplication'])

        # Adding model 'LocalApplicationLocks'
        db.create_table('local_application_locks', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['orm.LocalApplication'], unique=True)),
            ('pid', self.gf('django.db.models.fields.IntegerField')()),
            ('time', self.gf('django.db.models.fields.DateField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('orm', ['LocalApplicationLocks'])


    def backwards(self, orm):
        
        # Deleting model 'LocalApplication'
        db.delete_table('local_application')

        # Deleting model 'LocalApplicationLocks'
        db.delete_table('local_application_locks')


    models = {
        'orm.localapplication': {
            'Meta': {'object_name': 'LocalApplication', 'db_table': "'local_application'"},
            'application_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_stopped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {})
        },
        'orm.localapplicationlocks': {
            'Meta': {'object_name': 'LocalApplicationLocks', 'db_table': "'local_application_locks'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['orm.LocalApplication']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {}),
            'time': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['orm']

########NEW FILE########
__FILENAME__ = 0002_add_celery_procs
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'LocalApplication.celery_procs'
        db.add_column('local_application', 'celery_procs', self.gf('django.db.models.fields.IntegerField')(default=0), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'LocalApplication.celery_procs'
        db.delete_column('local_application', 'celery_procs')


    models = {
        'orm.localapplication': {
            'Meta': {'object_name': 'LocalApplication', 'db_table': "'local_application'"},
            'application_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'bundle_version': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'celery_procs': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_stopped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'num_procs': ('django.db.models.fields.IntegerField', [], {}),
            'proc_mem_mb': ('django.db.models.fields.IntegerField', [], {}),
            'proc_num_threads': ('django.db.models.fields.IntegerField', [], {}),
            'proc_stack_mb': ('django.db.models.fields.IntegerField', [], {})
        },
        'orm.localapplicationlocks': {
            'Meta': {'object_name': 'LocalApplicationLocks', 'db_table': "'local_application_locks'"},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['orm.LocalApplication']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {}),
            'time': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['orm']

########NEW FILE########
__FILENAME__ = models
import os
from django.db import models

class LocalApplication(models.Model):

    class Meta:
        db_table = 'local_application'

    application_name = models.CharField(max_length=255, unique=True)
    bundle_version   = models.CharField(max_length=255, null=True)
    is_stopped       = models.BooleanField(default=False)
    num_procs        = models.IntegerField()
    proc_num_threads = models.IntegerField()
    proc_mem_mb      = models.IntegerField()
    proc_stack_mb    = models.IntegerField()
    celery_procs     = models.IntegerField()

class LocalApplicationLocks(models.Model):

    class Meta:
        db_table = 'local_application_locks'

    application = models.ForeignKey(LocalApplication, unique=True)
    # Diagnostic information about the lock in case it is not properly
    # unlocked and we need to track down the problem.
    pid         = models.IntegerField()
    time        = models.DateField(auto_now_add=True)

    @staticmethod
    def lock(application_name):
        """Locks an application.  Throws an exception if it is already locked."""
        try:
            application = LocalApplication.objects.get(application_name=application_name)
            lock        = LocalApplicationLocks(application=application, pid=os.getpid())
            lock.save()
            return lock
        except Exception as e:
            raise LockFailedException(application_name)

    @staticmethod
    def unlock(lock):
        """Unlocks an application.  The argument must be the return value of 
           a previous call to lock() which has not already been unlocked."""
        try:
            if lock != None:
                lock.delete()
        except Exception as e:
            raise UnlockFailedException(lock.application.application_name)

class LockFailedException(Exception):
    """Could not lock the application."""
    def __init__(self, application_name):
        self.application_name = application_name
    def __str__(self):
        return 'Could not lock the application "%s".' % self.application_name

class UnlockFailedException(Exception):
    """Could not unlock the application."""
    def __init__(self, application_name):
        self.application_name = application_name
    def __str__(self):
        return 'Could not unlock the application "%s".' % self.application_name

########NEW FILE########
__FILENAME__ = settings
import djangy_server_shared, os.path

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(djangy_server_shared.WORKER_MANAGER_VAR_DIR, 'worker_manager.db'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': ''
    }
}

INSTALLED_APPS = (
    'orm',
    'south',
)

########NEW FILE########
__FILENAME__ = purge_old_bundles
#!/usr/bin/env python
#
# Utility script to remove old, unused bundles from a worker_manager host.
#

import os, shutil
from shared import *

BUNDLES_ROOT = '/srv/bundles';

def main():
    current_bundle_names = set([x.application_name + '-' + x.bundle_version for x in LocalApplication.objects.all()])
    for bundle_name in os.listdir(BUNDLES_ROOT):
        if bundle_name not in current_bundle_names:
            print 'Removing %s ...' % bundle_name
            shutil.rmtree(os.path.join(BUNDLES_ROOT, bundle_name))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = purge_old_logs
#!/usr/bin/env python
#
# Utility script to remove old, unused bundles from a worker_manager host.
#

import os, shutil
from shared import *

LOGS_ROOT = '/srv/logs';

def main():
    current_bundle_names = set([x.application_name + '-' + x.bundle_version for x in LocalApplication.objects.all()])
    for log_name in os.listdir(LOGS_ROOT):
        log_path = os.path.join(LOGS_ROOT, log_name)
        if log_name.find('-v1g') >= 0 and os.path.isdir(log_path) and log_name not in current_bundle_names:
            print 'Removing %s ...' % log_name
            shutil.rmtree(log_path)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = retrieve_logs
#!/usr/bin/env python

from shared import *
from mako.template import Template
from mako.lookup import TemplateLookup
import os

def main():
    try:
        check_trusted_uid(sys.argv[0])
        kwargs = check_and_return_keyword_args(sys.argv, ['application_name', 'bundle_version'])

        application_name    = kwargs['application_name']
        bundle_version      = kwargs['bundle_version']
        retrieve_logs(application_name, bundle_version)
    except:
        log_last_exception()

def retrieve_logs(application_name, bundle_version):
    bundle_name = application_name + '-' + bundle_version
    django_log_path = os.path.join(LOGS_DIR, bundle_name, "django.log")
    error_log_path = os.path.join(LOGS_DIR, bundle_name, "error.log")

    django_log = open(django_log_path).read()
    error_log = open(error_log_path).read()

    lookup = TemplateLookup(directories = [WORKER_TEMPLATE_DIR])
    template = lookup.get_template('logs.txt')
    instance = template.render(
        django_log = django_log, 
        error_log = error_log
    )
    print instance

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = lock_application
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'orm.settings'
from orm.models import *

def lock_application(func):
    def lock_and_call(application_name, *args, **kwargs):
        lock = LocalApplicationLocks.lock(application_name)
        try:
            func(application_name, *args, **kwargs)
        finally:
            LocalApplicationLocks.unlock(lock)
    return lock_and_call

########NEW FILE########
__FILENAME__ = start_stop
from shared import *
from socket import gethostname
import os, sys, pwd

def start_application(application_name):
    # Set the started status in the local database
    application_info = LocalApplication.objects.get(application_name=application_name)
    application_info.is_stopped = False
    application_info.save()
    # Start the application in gunicorn
    bundle_version = application_info.bundle_version
    bundle_name = application_name + "-" + bundle_version
    bundle_path = os.path.join('/srv/bundles', bundle_name)
    config_path = os.path.join(bundle_path, 'config')
    virtualenv_path = os.path.join(bundle_path, 'python-virtual')
    bundle_info = BundleInfo.load_from_file(os.path.join(config_path, 'bundle_info.config'))
    def become_web_uid():
        os.environ.clear()
        os.environ['PATH'] = '%s:/usr/bin:/bin' % os.path.join(virtualenv_path, 'bin')
        os.environ['VIRTUAL_ENV'] = virtualenv_path
        os.chdir(config_path)
        os.setgid(bundle_info.app_gid)
        os.setuid(bundle_info.web_uid)
    def become_cron_uid():
        os.environ.clear()
        os.environ['PATH'] = '%s:/usr/bin:/bin' % os.path.join(virtualenv_path, 'bin')
        os.environ['VIRTUAL_ENV'] = virtualenv_path
        os.chdir(bundle_info.django_project_path)
        os.setgid(bundle_info.app_gid)
        os.setuid(bundle_info.cron_uid)
    # Start gunicorn process
    sys.stdout.flush()
    run_external_program(['gunicorn', '-c', os.path.join(config_path, 'gunicorn.conf'), 'runnable_%s:application' % bundle_version], \
        cwd = config_path, \
        preexec_fn = become_web_uid)
    try:
        celery_procs = int(application_info.celery_procs)
        # only start celery if there is more than one process being allocated
        assert celery_procs > 0
    except:
        return
    pid = os.fork()
    if pid == 0:
        # child process
        os.closerange(1, 1024)
        become_cron_uid()
        hostname = "%s.%s" % (application_name, gethostname())
        os.execvp('python', [
            'python', 
            os.path.join(bundle_info.django_project_path, 'manage.py'), 
            'celeryd', 
            '-n', hostname, 
        ])


def stop_application(application_name):
    # Set the stopped status in the local database
    application_info = LocalApplication.objects.get(application_name=application_name)
    if application_info.is_stopped:
        return False
    application_info.is_stopped = True
    application_info.save()
    if not application_info.bundle_version:
        # There is no current running version
        return True
    try:
        bundle_name = application_name + "-" + application_info.bundle_version
        bundle_path = os.path.join('/srv/bundles', bundle_name)
        config_path = os.path.join(bundle_path, 'config')
        bundle_info = BundleInfo.load_from_file(os.path.join(config_path, 'bundle_info.config'))
        # Stop the running gunicorn process
        web_user = pwd.getpwuid(int(bundle_info.web_uid)).pw_name
        cron_user = pwd.getpwuid(int(bundle_info.cron_uid)).pw_name
        # send SIGKILL
        sys.stdout.flush()
        run_external_program(['killall', '-s', 'SIGKILL', '-u', str(web_user)])
        run_external_program(['killall', '-s', 'SIGKILL', '-u', str(cron_user)])
    except:
        # Database had a stale entry
        log_last_exception()
    return True

########NEW FILE########
__FILENAME__ = start
#!/usr/bin/env python

from shared import *

def main():
    check_trusted_uid(sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, ['application_name'])
    start(**kwargs)

@lock_application
def start(application_name):
    return start_application(application_name)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = stop
#!/usr/bin/env python

from shared import *

def main():
    check_trusted_uid(sys.argv[0])
    kwargs = check_and_return_keyword_args(sys.argv, ['application_name'])
    stop(**kwargs)

@lock_application
def stop(application_name):
    return stop_application(application_name)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
import os
from django.http import HttpResponse

def index(request):
    return HttpResponse('testapp.main')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for testapp project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '7=y^^6+_1&sqo*n=07pu@7(3=t&2rxv#-+4#ote0jo=a8f0jox'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'testapp.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^', 'testapp.main.views.index'),

    # Example:
    # (r'^testapp/', include('testapp.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
import os
from django.http import HttpResponse

def index(request):
    return HttpResponse('testapp.main second edition')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for testapp project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '7=y^^6+_1&sqo*n=07pu@7(3=t&2rxv#-+4#ote0jo=a8f0jox'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'testapp.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'site_media/'}),
    (r'^', 'testapp.main.views.index')

    # Example:
    # (r'^testapp/', include('testapp.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

class Foo(models.Model):
    name = models.CharField(max_length=255)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}

########NEW FILE########
__FILENAME__ = views
import os
from django.http import HttpResponse
from main.models import *

def index(request):
    return HttpResponse('testapp.main second edition')

def add_foo(request):
    f = Foo(name="bar")
    f.save()
    return HttpResponse("bar")

def count_rows(request):
    return HttpResponse(Foo.objects.all.count())

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for testapp project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '7=y^^6+_1&sqo*n=07pu@7(3=t&2rxv#-+4#ote0jo=a8f0jox'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'testapp.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'main',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^add_foo$', 'testapp.main.views.add_foo'),
    (r'^count_rows$', 'testapp.main.views.count_rows'),
    (r'^$', 'testapp.main.views.index'),
    # Example:
    # (r'^testapp/', include('testapp.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Foo'
        db.create_table('main_foo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('main', ['Foo'])


    def backwards(self, orm):
        
        # Deleting model 'Foo'
        db.delete_table('main_foo')


    models = {
        'main.foo': {
            'Meta': {'object_name': 'Foo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['main']

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

class Foo(models.Model):
    name = models.CharField(max_length=255)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}

########NEW FILE########
__FILENAME__ = views
import os
from django.http import HttpResponse
from main.models import *

def index(request):
    return HttpResponse('testapp.main second edition')

def add_foo(request):
    f = Foo(name="bar")
    f.save()
    return HttpResponse("bar")

def count_rows(request):
    return HttpResponse(Foo.objects.all.count())

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for testapp project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '7=y^^6+_1&sqo*n=07pu@7(3=t&2rxv#-+4#ote0jo=a8f0jox'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'testapp.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'main',
    'south',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^add_foo$', 'testapp.main.views.add_foo'),
    (r'^count_rows$', 'testapp.main.views.count_rows'),
    (r'^$', 'testapp.main.views.index'),
    # Example:
    # (r'^testapp/', include('testapp.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = fetch_url
import socket

def fetch_url(host, url):
    """Fetch the headers and body of a URL from a given host.  Useful when a
    host recognizes virtual hosts that don't actually point to it in DNS."""

    s = socket.create_connection((host, 80)).makefile()
    s.write('GET %s HTTP/1.0\n\n' % url)
    s.flush()
    response = s.read()
    s.close()
    return response

def fetch_url_body(host, url):
    """Return just the body from fetch_url(host, url)"""

    response = fetch_url(host, url)
    n = response.index('\r\n\r\n') + 4
    return response[n:]

def fetch_url_headers(host, url):
    """Return just the headers from fetch_url(host, url), as a dictionary."""

    response = fetch_url(host, url)
    n = response.index('\r\n\r\n')
    headers_list = response[:n].split('\r\n')
    headers_dict = {'STATUS': headers_list[0].split(' ', 2)[1]}
    for header in headers_list:
        try:
            (k, v) = header.split(':', 1)
            headers_dict[k.strip()] = v.strip()
        except:
            pass

    return headers_dict

########NEW FILE########
__FILENAME__ = testlib
"""
    Library of functions useful for writing test cases.
"""

import os, os.path, shutil, subprocess, sys, tempfile, traceback, urllib2

log_dir = os.path.join(os.getcwd(), 'test_logs')
if not os.path.isdir(log_dir):
    os.makedirs(log_dir)
test_log_file = None

def log(message):
    global test_log_file
    if test_log_file:
        test_log_file.write(message + '\n')
    else:
        print message

def testcase(func):
    """Decorator for test cases"""
    test_case_name = func.func_name
    def handle_exception(e):
        log(traceback.format_exc(e))
        print 'FAILED'
        return False
    def test_case_func(*args, **kwargs):
        global test_log_file
        try:
            test_log_file = open(os.path.join(log_dir, test_case_name + '.log'), 'w')
            print ('%s...' % test_case_name),
            sys.stdout.flush()
            log('BEGIN TEST CASE %s' % test_case_name)
            log('')
            func(*args, **kwargs)
            print 'OK'
            return True
        except Exception as e:
            return handle_exception(e)
        except KeyboardInterrupt as e:
            return handle_exception(e)
        except AssertionError as e:
            return handle_exception(e)
        finally:
            log('')
            log('END TEST CASE %s' % test_case_name)
            test_log_file.close()
    return test_case_func

def in_temp_dir(func):
    """Decorator for functions which need to run in a temporary scratch directory"""
    def in_temp_dir_func(*args, **kwargs):
        tempdir = tempfile.mkdtemp()
        #homedir = os.environ['HOME']
        olddir = os.getcwd()
        try:
            os.chdir(tempdir)
            #os.environ['HOME'] = tempdir
            #ssh_dir = os.path.join(tempdir, '.ssh')
            #os.mkdir(ssh_dir)
            #subprocess.call(['ssh-keygen', '-N', '', '-f', os.path.join(tempdir, '.ssh', 'id_rsa')])
            #subprocess.call(['cp', os.path.join(TEST_DIR, test.djangy), os.path.join(tempdir, '.djangy')])
            return func(*args, **kwargs)
        finally:
            os.chdir(olddir)
            #os.environ['HOME'] = homedir
            if os.path.dirname(tempdir) == '/tmp':
                shutil.rmtree(tempdir)
    return in_temp_dir_func

def call(*args, **kwargs):
    return call_list(list(args), **kwargs)

def call_list(args, should_fail=False, stdin_contents=None):
    log('Calling %s' % ' '.join(args))
    p = subprocess.Popen(list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    if stdin_contents:
        p.stdin.write(stdin_contents)
        p.stdin.close()
    output = p.stdout.read()
    log(output)
    if should_fail:
        assert p.wait() != 0
    else:
        assert p.wait() == 0
    return output

def test_url(url, expected_status_code=200, validation_function=None):
    try:
        response = urllib2.urlopen(url)
        if expected_status_code != 200:
            return False
        if validation_function:
            return validation_function(response.read())
        else:
            return True
    except urllib2.HTTPError as error:
        return error.code == expected_status_code

def test_urls(urls):
    for url in urls:
        print ('%s...' % url),
        if test_url(url):
            print 'OK'
        else:
            print 'FAILED'

########NEW FILE########
__FILENAME__ = test_cases
#! /usr/bin/env python

"""
    Djangy system correctness test cases.

    When you run this file, additional output will go to log files in the
    test_logs directory.
"""

import os, os.path, random, shutil, sys, time
#from fabric.api import *
import fetch_url, urls
from testlib import *
from time import sleep

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DJANGY_SRC_DIR = os.path.dirname(TEST_DIR)
os.environ['PATH'] = os.environ['PATH'] + ':' + os.path.join(DJANGY_SRC_DIR, 'src/client')

def random_application_name():
    return 'testapp' + str(random.randrange(10000000, 99999999))

@in_temp_dir
def test_cases():
    create_djangy_client_virtualenv()
    test_urls(urls.urls)
    assert test_create() # If test_create() fails, don't run the other test cases
    test_recreate()
    assert test_update()
    test_cache()
    test_logs()
    test_syncdb()
    test_migrate()

def create_djangy_client_virtualenv():
    cwd = os.getcwd()
    call('virtualenv', 'python-virtual')
    os.environ['PATH'] = '%s:/usr/bin:/bin' % os.path.join(cwd, "python-virtual", "bin")
    os.chdir(os.path.join(DJANGY_SRC_DIR, 'src', 'client'))
    call('make')
    os.chdir(cwd)

@testcase
def test_create():
    global application_name, repository_path
    # Make a new application
    log('[%s]' % time.ctime())
    (application_name, repository_path) = make_application('testapp')
    # Copy in code (as a subdirectory -- also need to test as direct contents)
    log('[%s]' % time.ctime())
    shutil.copytree(os.path.join(TEST_DIR, 'data', 'testapp-v1'), os.path.join(repository_path, 'testapp'))
    # Add code and djangy.config to git repository
    log('[%s]' % time.ctime())
    commit_code('initial version')
    # Push application to djangy
    log('[%s]' % time.ctime())
    push_code()
    # Check the website.
    log('[%s]' % time.ctime())
    check_website(application_name, 'testapp.main')
    log('[%s]' % time.ctime())
    return True

@testcase
def test_recreate():
    # Try to make the application a second time (should fail)
    call('djangy', 'create', should_fail=True)

@testcase
def test_update():
    global application_name, repository_path
    # Update code, move it to root level
    #shutil.rmtree(os.path.join(repository_path, 'testapp'))
    #shutil.copytree(, )
    call_list(['git', 'mv'] + listdir_path('testapp') + ['.'])
    call('/bin/bash', '-c', 'cp -r %s/* %s' % (os.path.join(TEST_DIR, 'data', 'testapp-v2'), repository_path))
    commit_code('updated version')
    # Push application to djangy
    push_code()
    # Check the website.
    check_website(application_name, 'testapp.main second edition')
    return True

@testcase
def test_cache():
    global application_name, repository_path
    # Check the website.
    log('Checking static web data is cached...')
    url = 'http://%s.djangy.com/site_media/index.html' % application_name
    log('url: %s' % url)
    headers1 = fetch_url.fetch_url_headers('api.djangy.com', url)
    log('headers1: %s' % str(headers1))
    time.sleep(2)
    headers2 = fetch_url.fetch_url_headers('api.djangy.com', url)
    log('headers2: %s' % str(headers2))
    assert headers1['Cache-Control'] == 'max-stale=600'
    assert headers1['Date']          != headers2['Date']
    assert headers1['Last-Modified'] == headers2['Last-Modified']
    assert headers1['Expires']       == headers2['Expires']

@testcase
def test_logs():
    # Check logs
    logs = call('djangy', 'logs')
    logs.index('DJANGY LOG')

@testcase
def test_syncdb():
    # Check syncdb
    call('/bin/bash', '-c', 'cp -r %s/* %s' % (os.path.join(TEST_DIR, 'data', 'testapp-v3'), repository_path))
    commit_code('test syncdb')
    # Push application to djangy
    push_code()
    # run syncdb
    output = call('djangy', 'manage.py', 'syncdb', stdin_contents="no")
    # Check the website.
    check_website(application_name, 'bar', resource="add_foo")
    return (application_name, repository_path)

@testcase
def test_migrate():
    # Check migrate
    (application_name, repository_path) = make_application('testapp')
    # Copy in code (as a subdirectory -- also need to test as direct contents)
    shutil.copytree(os.path.join(TEST_DIR, 'data', 'testapp-v4'), os.path.join(repository_path, 'testapp'))
    # Add code and djangy.config to git repository
    commit_code('initial version')
    # Push application to djangy
    push_code()
    # run syncdb
    output = call('djangy', 'manage.py', 'syncdb', stdin_contents="no")
    # run migrate
    output = call('djangy', 'manage.py', 'migrate')
    # Check the website.
    check_website(application_name, 'bar', resource="add_foo")
    return (application_name, repository_path)

def make_application(rootdir):
    # Choose an application name
    application_name = random_application_name()
    repository_path = os.path.join(os.getcwd(), application_name)
    os.mkdir(repository_path)
    os.chdir(repository_path)
    # Create a git repository
    call('git', 'init')
    # Create a djangy.config file
    create_file('djangy.config', '[application]\napplication_name=%s\nrootdir=%s\n' % (application_name, rootdir))
    commit_code('djangy.config')
    # Create a djangy application
    call('djangy', 'create')
    return (application_name, repository_path)

def create_file(file_path, file_contents):
    file = open(file_path, 'w')
    file.write(file_contents)
    file.close()

def commit_code(commit_message):
    call('git', 'add', '.')
    call('git', 'commit', '-m', commit_message)

def push_code():
    # Push application to djangy
    call('git', 'push', 'djangy', 'master')
    sleep(1)

def check_website(application_name, expected_output, resource=""):
    log('Checking website output...',)
    url = "http://%s.djangy.com/%s" % (application_name, resource)
    log("Using URL: %s" % url)
    result = fetch_url.fetch_url_body('api.djangy.com', url)
    log("Expected output: %s" % expected_output)
    log("Actual Output: %s" % result)
    assert result == expected_output
    log('Website output matched.')

def listdir_path(dir_path):
    return map(lambda x: os.path.join(dir_path, x), os.listdir(dir_path))

if __name__ == '__main__':
    try:
        test_cases()
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = update_billing
from master_api import update_billing_info
from management_database import User

def test_update_billing_info():
    user = User.get_by_email("bob@jones.mil")
    user.customer_id = '-1'
    user.subscription_id = '-1'
    user.save()
    info = {
        'first_name':'Bob',
        'last_name':'Jones',
        'addr1':'1234 Fast Lane',
        'addr2':'',
        'city':'San Francisco',
        'state':'CA',
        'zip':'94103',
        'expiration_month':'05',
        'expiration_year':'2015',
        'cc_number':'1',
        'cvv':'734'
    }
    
    assert (user.customer_id == '-1')
    assert (user.subscription_id == '-1')
    update_billing_info("bob@jones.mil", info)
    user = User.get_by_email("bob@jones.mil")
    assert (user.customer_id != '-1')
    assert (user.subscription_id != '-1')
    

########NEW FILE########
__FILENAME__ = urls
urls = [
    'https://www.djangy.com/',
    'https://www.djangy.com/login',
    'https://www.djangy.com/docs',
    'https://www.djangy.com/docs/Documentation',
    'https://www.djangy.com/docs/Tutorial',
    #'https://www.djangy.com/signup' # Should test this as a post request...
]

########NEW FILE########
