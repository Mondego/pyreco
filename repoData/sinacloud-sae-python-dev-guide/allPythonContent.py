__FILENAME__ = bundle_local
#!/usr/bin/env python

"""Create a local bundle for your virtualenv environment

Export all the packages listed in requirements.txt to ./virtualenv.bundle
directory

Then you can create a .zip file before uploading them to sae

Usage: bundle_local -r requirements.txt

"""

from optparse import OptionParser
import os
import sys
import pip.util
import shutil

TMP = 'virtualenv.bundle'

ZIP_FILE = TMP + '.zip'

def main():
    parser = OptionParser()
    parser.add_option("-r", dest="requirements",
                      help="The requirements.txt file outputed by pip freeze")
    (options, args) = parser.parse_args()

    if not options.requirements:
        print 'requirements.txt not found'
        sys.exit(-1)

    if os.path.exists(TMP):
        shutil.rmtree(TMP)
    os.mkdir(TMP)

    shutil.copy2(options.requirements, os.path.join(TMP, 'requirements.txt'))

    # Get all installed packages on system
    installed_dists = {}
    for dist in pip.util.get_installed_distributions():
        installed_dists[dist.project_name] = dist

    # Get the dists in requirements.txt
    dists = []
    for line in open(options.requirements, 'r').readlines():
        if line.strip() or line.startswith('#'):
            pass
        pkg = line.split('==')[0]

        if pkg not in installed_dists:
            raise Exception('%s not installed' % pkg)
        dists.append(installed_dists[pkg])

    top_levels = []
    for dist in dists:
        mods = [(dist.location, mod) for mod in dist.get_metadata('top_level.txt').splitlines()]
        top_levels += mods

    top_levels = list(set(top_levels))
    copy_modules(top_levels, TMP)


def copy_modules(mod_paths, dest):
    for loc, mod in mod_paths:
        if os.path.isdir(loc):
            src = os.path.join(loc, mod)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(dest, mod), ignore=shutil.ignore_patterns('*.pyc'))
            else:
                # Single file module
                shutil.copy2(src + '.py', dest)
        else:
            # Egg file ?
            import zipfile
            zf = zipfile.ZipFile(loc)
            members = filter(lambda f: f.startswith(mod), zf.namelist())
            for m in members:
                zf.extract(m, dest)
            zf.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = cloudsql
#!/usr/bin/env python

# Copyright (C) 2012-2013 SINA, All rights reserved.

"""Command line client for SAE MySQL Service. """

import sys
import os
import logging
import optparse

import sae._restful_mysql
import sae._restful_mysql._mysql_exceptions
sys.modules['_mysql_exceptions'] = sae._restful_mysql._mysql_exceptions

from grizzled import db
from grizzled.db import mysql
import prettytable
import sqlcmd
from sqlcmd import config

logging.basicConfig(level=logging.WARNING)
sqlcmd.log = logging.getLogger('cloudsql')

sqlcmd.DEFAULT_CONFIG_DIR = os.path.expanduser('~/.saecloud')
sqlcmd.RC_FILE = os.path.join(sqlcmd.DEFAULT_CONFIG_DIR, 'cloudsql.config')
sqlcmd.HISTORY_FILE_FORMAT = os.path.join(sqlcmd.DEFAULT_CONFIG_DIR, '%s.hist')
sqlcmd.INTRO = 'SAE MySQL Client\n\nType "help" or "?" for help.\n'

DEFAULT_ENCODING = 'utf-8'
USAGE = '%prog [options] database_name'

DEFAULT_SAE_MYSQL_HOST = 'w.rdc.sae.sina.com.cn'
DEFAULT_SAE_MYSQL_PORT = 3307
DEFAULT_SAE_MYSQL_DB_PREFIX = 'app_'

class CloudSqlDriver(mysql.MySQLDriver):
    """Grizzled DB Driver for Cloud SAE MySQL Service."""

    NAME = 'cloudsql'

    def get_import(self):
        return sae._restful_mysql

    def get_display_name(self):
        return 'Cloud SQL'

    def do_connect(self, host, port, user, password, database):
        # Fix grizzled's mysql driver which omit the port argument when connecting.
        dbi = self.get_import()
        port = port and int(port) or 3306
        return dbi.connect(host=host, user=user, passwd=password, db=database, port=port)

class CloudSqlCmd(sqlcmd.SQLCmd):
    """The SQLCmd command interpreter for Cloud SQL."""

    sqlcmd.SQLCmd.MAIN_PROMPT = 'mysql> '
    sqlcmd.SQLCmd.CONTINUATION_PROMPT = '    -> '

    sqlcmd.SQLCmd.NO_SEMI_NEEDED.update(
        ['about', 'desc', 'describe', 'echo', 'exit', 'h', 'hist',
         'history', 'load', 'run', 'r', 'redo', 'set', 'show', 'var', 'vars'])

    for method in ['do_dot_connect', 'do_dot_desc', 'do_begin']:
        delattr(sqlcmd.SQLCmd, method)

    for cmd in ['show', 'describe', 'echo', 'load', 'run', 'exit', 'h',
                'hist', 'history', 'var', 'vars', 'about']:
        method = 'do_dot_' + cmd
        setattr(sqlcmd.SQLCmd, method.replace('dot_', ''), getattr(
            sqlcmd.SQLCmd, method))
        delattr(sqlcmd.SQLCmd, method)
        method = 'complete_dot_' + cmd
        if hasattr(sqlcmd.SQLCmd, method):
            setattr(sqlcmd.SQLCmd, method.replace('dot_', ''), getattr(
                sqlcmd.SQLCmd, method))
            delattr(sqlcmd.SQLCmd, method)

    def do_redo(self, args):
        # XXX: Fix global name 'do_r' is not defined problem in sqlcmd
        self.do_r(args)

    def _SQLCmd__set_setting(self, varname, value):
        # XXX: Fix bool object has no lower attribute in sqlcmd
        return sqlcmd.SQLCmd._SQLCmd__set_setting(self, varname, str(value))

    def do_desc(self, args):
        self.do_describe(args, cmd='.desc')
    complete_desc = sqlcmd.SQLCmd.complete_dot_desc

    def do_load(self, args):
        self.do_run(args)

    def preloop(self, *args, **kwargs):
        sqlcmd.SQLCmd.preloop(self, *args, **kwargs)
        # Just exit if the connect failed
        if self._SQLCmd__db is None: sys.exit(1)

    def __init__(self, *args, **kwargs):
        sqlcmd.SQLCmd.__init__(self, *args, **kwargs)
        self.prompt = sqlcmd.SQLCmd.MAIN_PROMPT
        self.output_encoding = DEFAULT_ENCODING

    def set_output_encoding(self, encoding):
        self.output_encoding = encoding

    def _build_table(self, cursor):
        """Builds an output PrettyTable from the results in the given cursor."""
        if not cursor.description:
            return None

        column_names = [column[0] for column in cursor.description]
        table = prettytable.PrettyTable(column_names)
        rows = cursor.fetchall()
        if not rows:
            return table
        for i, col in enumerate(rows[0]):
            table.align[column_names[i]] = isinstance(col, basestring) and 'l' or 'r'
        for row in rows: table.add_row(row)
        return table

    def _SQLCmd__handle_select(self, args, cursor, command='select'):
        """Overrides SQLCmd.__handle_select to display output with prettytable."""
        self._SQLCmd__exec_SQL(cursor, command, args)
        table = self._build_table(cursor)
        if table:
            output = table.get_string()
            if isinstance(output, unicode):
                print output.encode(self.output_encoding)
            else:
                print output

def _create_config_dir():
    """Creates the sqlcmd config directory if necessary."""
    directory = sqlcmd.DEFAULT_CONFIG_DIR
    if not os.access(directory, os.R_OK | os.W_OK | os.X_OK):
        old_umask = os.umask(077)
        os.makedirs(sqlcmd.DEFAULT_CONFIG_DIR)
        os.umask(old_umask)

def main(argv):
    parser = optparse.OptionParser(usage=USAGE)
    parser.add_option('-u', '--username', dest='username',
                      help='MySQL username to use when connecting to the server.')
    parser.add_option('-p', '--password', dest='password',
                      help='MySQL password to use when connecting to the server.')
    parser.add_option('-e', '--output_encoding', dest='output_encoding',
                      default=DEFAULT_ENCODING,
                      help='Output encoding. Defaults to %s.' % DEFAULT_ENCODING)

    (options, args) = parser.parse_args(argv[1:])

    if len(args) != 1:
        parser.print_help(sys.stderr)
        return 1

    if not options.username or not options.password:
        print >>sys.stderr, 'Error: username or password is missing.\n'
        return 1

    if args[0].startswith(DEFAULT_SAE_MYSQL_DB_PREFIX):
        database_name = args[0]
    else:
        database_name = DEFAULT_SAE_MYSQL_DB_PREFIX + args[0]
    instance_alias = database_name

    _create_config_dir()

    db.add_driver(CloudSqlDriver.NAME, CloudSqlDriver)
    sql_cmd_config = config.SQLCmdConfig(None)
    sql_cmd_config.add('__cloudsql__', instance_alias,
                       DEFAULT_SAE_MYSQL_HOST , DEFAULT_SAE_MYSQL_PORT, database_name,
                       CloudSqlDriver.NAME, options.username, options.password)
    sql_cmd = CloudSqlCmd(sql_cmd_config)
    sql_cmd.set_output_encoding(options.output_encoding)
    sql_cmd.set_database(instance_alias)
    sql_cmd.cmdloop()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = dev_server
#!/usr/bin/env python

"""Simple development server

Make sure you're use python 2.7 for developing

"""
import sys
import os
import os.path
import re
import imp
import yaml
from optparse import OptionParser

from sae.util import search_file_bottom_up

from sae.channel import _channel_wrapper

app_root = search_file_bottom_up('config.yaml')
if app_root is None:
    print >> sys.stderr, \
        'Error: Not an app directory(or any of the parent directories)'
    sys.exit(1)
if app_root != os.getcwd(): os.chdir(app_root)

def setup_sae_environ(conf):
    # Add dummy pylibmc module
    import sae.memcache
    sys.modules['pylibmc'] = sae.memcache

    # Save kvdb data in this file else the data will lost
    # when the dev_server.py is down
    if conf.kvdb:
        print 'KVDB: ', conf.kvdb
        os.environ['sae.kvdb.file'] = conf.kvdb

    # Add app_root to sys.path
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    try:
        appname = str(conf.name)
        appversion = str(conf.version)
    except AttributeError:
        raise AttributeError('`name` or `version` not found in `config.yaml`')

    if conf.mysql:
        import sae.const

        p = re.compile('^(.+):(.+)@(.+):(\d+)$')
        m = p.match(conf.mysql)
        if not m:
            raise Exception("Invalid mysql configuration")

        user, password, host, port = m.groups()
        dbname = 'app_' + appname
        sae.const.MYSQL_DB = dbname
        sae.const.MYSQL_USER = user
        sae.const.MYSQL_PASS = password
        sae.const.MYSQL_PORT = port
        sae.const.MYSQL_HOST = host

        print 'MySQL: %s.%s' % (conf.mysql, dbname)
    else:
        print 'MySQL config not found'

    if conf.storage:
        os.environ['sae.storage.path'] = os.path.abspath(conf.storage)
        
    # Add custom environment variable
    os.environ['HTTP_HOST'] = '%s:%d' % (conf.host, conf.port)
    os.environ['APP_NAME'] = appname
    os.environ['APP_VERSION'] = appversion

class Worker:
    def __init__(self, conf, app):
        self.conf = conf
        self.application = app
        self.collect_statifiles()

    def collect_statifiles(self):
        self.static_files = {}
        if hasattr(self.conf, 'handlers'):
            for h in self.conf.handlers:
                url = h['url']
                if h.has_key('static_dir'):
                    self.static_files[url] = os.path.join(app_root, h['static_dir'])
                elif h.has_key('static_path'):
                    self.static_files[url] = os.path.join(app_root, h['static_path'])
        if not len(self.static_files):
            self.static_files.update({
                '/static': os.path.join(app_root,  'static'),
                '/media': os.path.join(app_root,  'media'),
                '/favicon.ico': os.path.join(app_root,  'favicon.ico'),
            })
        import sae
        self.static_files['/_sae/channel/api.js'] = os.path.join(os.path.dirname(sae.__file__), 'channel.js')

        if self.conf.storage:
            # stor dispatch: for test usage only
            self.static_files['/stor-stub/'] = os.path.abspath(self.conf.storage)

    def run(self):
        raise NotImplementedError()

class WsgiWorker(Worker):
    def run(self):
        # FIXME: All files under current directory
        files = ['index.wsgi']

        # XXX:
        # when django template renders `environ` in its 500 page, it will
        # try to call `environ['werkzeug.server.shutdown'` and cause the
        # server exit unexpectedly.
        # See: https://docs.djangoproject.com/en/dev/ref/templates/api/#variables-and-lookups
        def wrap(app):
            def _(environ, start_response):
                try:
                    del environ['werkzeug.server.shutdown']
                except KeyError:
                    pass
                return app(environ, start_response)
            return _

        if 'WERKZEUG_RUN_MAIN' in os.environ:
            os.environ['sae.run_main'] = '1'

        self.application = _channel_wrapper(self.application)
        from werkzeug.serving import run_simple
        run_simple(self.conf.host, self.conf.port,
                   wrap(self.application),
                   use_reloader = True,
                   use_debugger = True,
                   extra_files = files,
                   static_files = self.static_files)

class TornadoWorker(Worker):
    def run(self):
        import tornado.autoreload
        tornado.autoreload.watch('index.wsgi')

        import re
        from tornado.web import URLSpec, StaticFileHandler
        # The user should not use `tornado.web.Application.add_handlers`
        # since here in SAE one application only has a single host, so here
        # we can just use the first host_handers.
        handlers = self.application.handlers[0][1]
        for prefix, path in self.static_files.iteritems():
            pattern = re.escape(prefix) + r"(.*)"
            handlers.insert(0, URLSpec(pattern, StaticFileHandler, {"path": path}))

        os.environ['sae.run_main'] = '1'

        import tornado.ioloop
        from tornado.httpserver import HTTPServer
        server = HTTPServer(self.application, xheaders=True)
        server.listen(self.conf.port, self.conf.host)
        tornado.ioloop.IOLoop.instance().start()

def main(options):
    conf_path = os.path.join(app_root, 'config.yaml')
    conf = yaml.load(open(conf_path, "r"))
    options.__dict__.update(conf)
    conf = options

    # if env `WERKZEUG_RUN_MAIN` is not defined, then we are in 
    # the reloader process.
    # if os.environ.get('WERKZEUG_RUN_MAIN', False):

    setup_sae_environ(conf)

    try:
        index = imp.load_source('index', 'index.wsgi')
    except IOError:
        print >>sys.stderr, "Seems you don't have an index.wsgi"
        return
    if not hasattr(index, 'application'):
        print >>sys.stderr, "application not found in index.wsgi"
        return
    if not callable(index.application):
        print >>sys.stderr, "application is not a callable"
        return

    application = index.application

    cls_name = getattr(conf, 'worker', 'wsgi').capitalize() + 'Worker'
    try:
        globals().get(cls_name, WsgiWorker)(conf, application).run()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-p", "--port", type="int", dest="port", default="8080",
                      help="Which port to listen")
    parser.add_option("--host", dest="host", default="localhost",
                      help="Which host to listen")
    parser.add_option("--mysql", dest="mysql", help="Mysql configuration: user:password@host:port")
    parser.add_option("--storage-path", dest="storage", help="Directory used as local stoarge")
    parser.add_option("--kvdb-file", dest="kvdb", help="File to save kvdb data")
    (options, args) = parser.parse_args()

    main(options)

########NEW FILE########
__FILENAME__ = channel
#!/usr/bin/env python
# -*-coding: utf8 -*-

"""Channel API
"""

import time
import json
import os

MAXIMUM_CLIENT_ID_LENGTH = 118

MAXIMUM_TOKEN_DURATION_SECONDS = 24 * 60

MAXIMUM_MESSAGE_LENGTH = 32767

class Error(Exception):
    """Base error class for this module."""

class InvalidChannelClientIdError(Error):
    """Error that indicates a bad client id."""

class InvalidChannelTokenDurationError(Error):
    """Error that indicates the requested duration is invalid."""

class InvalidMessageError(Error):
    """Error that indicates a message is malformed."""

class InternalError(Error):
    """Error that indicates server side error"""

def _validate_client_id(client_id):
    if not isinstance(client_id, basestring):
        raise InvalidChannelClientIdError('"%s" is not a string.' % client_id)

    if isinstance(client_id, unicode):
        client_id = client_id.encode('utf-8')

    if len(client_id) > MAXIMUM_CLIENT_ID_LENGTH:
        msg = 'Client id length %d is greater than max length %d' % (
            len(client_id), MAXIMUM_CLIENT_ID_LENGTH)
        raise InvalidChannelClientIdError(msg)

    return client_id

def create_channel(name, duration=None):
    client_id = _validate_client_id(name)

    if duration is not None:
        if not isinstance(duration, (int, long)):
            raise InvalidChannelTokenDurationError(
                'Argument duration must be integral')
        elif duration < 1:
            raise InvalidChannelTokenDurationError(
                'Argument duration must not be less than 1')
        elif duration > MAXIMUM_TOKEN_DURATION_SECONDS:
            msg = ('Argument duration must be less than %d'
                 % (MAXIMUM_TOKEN_DURATION_SECONDS + 1))
            raise InvalidChannelTokenDurationError(msg)

    _cache[name] = []
    return 'http://%s/_sae/channel/%s' % (os.environ['HTTP_HOST'], name)

def send_message(name, message):
    client_id = name

    if isinstance(message, unicode):
        message = message.encode('utf-8')
    elif not isinstance(message, str):
        raise InvalidMessageError('Message must be a string')
    if len(message) > MAXIMUM_MESSAGE_LENGTH:
        raise InvalidMessageError(
            'Message must be no longer than %d chars' % MAXIMUM_MESSAGE_LENGTH)

    if name in _cache:
        _cache[name].append(message)
        return 1
    else:
        return 0

_cache = {}

import urllib
import urlparse
import cStringIO

def _channel_wrapper(app):
    def _(environ, start_response):
        if not environ['PATH_INFO'].startswith('/_sae/channel/dev'):
            return app(environ, start_response)

        qs = urlparse.parse_qs(environ['QUERY_STRING'])

        token = qs['channel'][0]
        command = qs['command'][0]

        if token not in _cache:
            start_response('401 forbidden', [])
            return []

        start_response('200 ok', [])

        if command == 'poll':
            try:
                return [_cache[token].pop(0),]
            except IndexError:
                return []
        else:
            qs = urllib.urlencode({'from': token})
            environ['PATH_INFO'] = '/_sae/channel/%sed' % command
            environ['QUERY_STRING'] = ''
            environ['REQUEST_METHOD'] = 'POST'
            environ['HTTP_CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
            environ['HTTP_CONTENT_LENGTH'] = len(qs)
            environ['wsgi.input'] = cStringIO.StringIO(qs)
            try:
                print '[CHANNEL]', [i for i in app(environ, lambda x, y: None)]
            except Exception:
                pass
            return []

    return _ 

########NEW FILE########
__FILENAME__ = conf
""" SAE Settings"""

import os

SAE_STOREHOST = 'http://stor.sae.sina.com.cn/storageApi.php'
SAE_S3HOST = 'http://s3.sae.sina.com.cn/s3Api.php'
SAE_TMP_PATH = '$SAE_TMPFS_PATH'

SAE_MYSQL_HOST_M = 'w.rdc.sae.sina.com.cn'
SAE_MYSQL_HOST_S = 'r.rdc.sae.sina.com.cn'
SAE_MYSQL_PORT = '3307'

SAE_FETCHURL_HOST = 'http://fetchurl.sae.sina.com.cn'


########NEW FILE########
__FILENAME__ = const
"""Constants about app

"""
import os
import conf

# Private
APP_NAME = os.environ.get('APP_NAME', '')
APP_HASH = os.environ.get('APP_HASH', '')
ACCESS_KEY = os.environ.get('ACCESS_KEY', '')
SECRET_KEY = os.environ.get('SECRET_KEY', '')

# Public
MYSQL_DB = '_'.join(['app', APP_NAME])
MYSQL_USER = ACCESS_KEY
MYSQL_PASS = SECRET_KEY
MYSQL_HOST = conf.SAE_MYSQL_HOST_M
MYSQL_PORT = conf.SAE_MYSQL_PORT
MYSQL_HOST_S = conf.SAE_MYSQL_HOST_S

########NEW FILE########
__FILENAME__ = core
"""Core functions of SAE

environ    A copy of the environ passed to your wsgi app, should not be used directly

"""

def get_access_key():
    """Return access_key of your app"""
    return environ.get('HTTP_ACCESSKEY', '')

def get_secret_key():
    """Return secret_key of your app"""
    return environ.get('HTTP_SECRETKEY', '')

def get_trusted_hosts():
    return [host for host in environ.get('TRUSTED_HOSTS', '').split() if host]

environ = {}

########NEW FILE########
__FILENAME__ = backend
"""send mail via sae's mail service"""

import threading

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from email.mime.base import MIMEBase

from sae.mail import EmailMessage, Error

class EmailBackend(BaseEmailBackend):
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, **kwargs):
        super(EmailBackend, self).__init__(fail_silently=fail_silently)
        self.host = host or settings.EMAIL_HOST
        self.port = port or settings.EMAIL_PORT
        if username is None:
            self.username = settings.EMAIL_HOST_USER
        else:
            self.username = username
        if password is None:
            self.password = settings.EMAIL_HOST_PASSWORD
        else:
            self.password = password
        if use_tls is None:
            self.use_tls = settings.EMAIL_USE_TLS
        else:
            self.use_tls = use_tls
        self.smtp = (self.host, self.port, self.username, self.password,
                     self.use_tls)
        self._lock = threading.RLock()

    def send_messages(self, email_messages):
        if not email_messages:
            return
        with self._lock:
            num_sent = 0
            for message in email_messages:
                sent = self._send(message)
                if sent:
                    num_sent += 1
        return num_sent

    def _send(self, email_message):
        if not email_message.recipients():
            return False
        attachments = []
        for attach in email_message.attachments:
            if isinstance(attach, MIMEBase):
                if not self.fail_silently:
                    raise NotImplemented()
                else:
                    return False
            else:
                attachments.append((attach[0], attach[1]))
        try:
            message = EmailMessage()
            message.to = email_message.recipients()
            message.from_addr = email_message.from_email
            message.subject = email_message.subject
            message.body = email_message.body
            message.smtp = self.smtp
            if attachments:
                message.attachments = attachments
            message.send()
        except Error, e:
            if not self.fail_silently:
                raise
            return False
        return True

########NEW FILE########
__FILENAME__ = backend
import sys
from StringIO import StringIO

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.exceptions import ImproperlyConfigured

from sae.storage import Connection, Error

from sae.const import ACCESS_KEY, SECRET_KEY, APP_NAME

STORAGE_BUCKET_NAME = getattr(settings, 'STORAGE_BUCKET_NAME')
STORAGE_ACCOUNT = getattr(settings, 'STORAGE_ACCOUNT', APP_NAME)
STORAGE_ACCESSKEY = getattr(settings, 'STORAGE_ACCESSKEY', ACCESS_KEY)
STORAGE_SECRETKEY = getattr(settings, 'STORAGE_SECRETKEY', SECRET_KEY)
STORAGE_GZIP = getattr(settings, 'STORAGE_GZIP', False)

class Storage(Storage):
    def __init__(self, bucket_name=STORAGE_BUCKET_NAME,
                 accesskey=STORAGE_ACCESSKEY, secretkey=STORAGE_SECRETKEY,
                 account=STORAGE_ACCOUNT):
        conn = Connection(accesskey, secretkey, account)
        self.bucket = conn.get_bucket(bucket_name)

    def _open(self, name, mode='rb'):
        name = self._normalize_name(name)
        return StorageFile(name, mode, self)

    def _save(self, name, content):
        name = self._normalize_name(name)
        try:
            self.bucket.put_object(name, content)
        except Error, e:
            raise IOError('Storage Error: %s' % e.args)
        return name

    def delete(self, name):
        name = self._normalize_name(name)
        try:
            self.bucket.delete_object(name)
        except Error, e:
            raise IOError('Storage Error: %s' % e.args)

    def exists(self, name):
        name = self._normalize_name(name)
        try:
            self.bucket.stat_object(name)
        except Error, e:
            if e[0] == 404:
                return False
            raise
        return True

    #def listdir(self, path):
    #    path = self._normalize_name(path)
    #    try:
    #        result = self.bucket.list(path=path)
    #        return [i.name for i in result]
    #    except Error, e:
    #        raise IOError('Storage Error: %s' % e.args)

    def size(self, name):
        name = self._normalize_name(name)
        try:
            attrs = self.bucket.stat_object(name)
            return attrs.bytes
        except Error, e:
            raise IOError('Storage Error: %s' % e.args)

    def url(self, name):
        name = self._normalize_name(name)
        return self.bucket.generate_url(name)

    def _open_read(self, name):
        name = self._normalize_name(name)
        class _:
            def __init__(self, chunks):
                self.buf = ''
            def read(self, num_bytes=None):
                if num_bytes is None:
                    num_bytes = sys.maxint
                try:
                    while len(self.buf) < num_bytes:
                        self.buf += chunks.next()
                except StopIteration:
                    pass
                except Error, e:
                    raise IOError('Storage Error: %s' % e.args)
                retval = self.buf[:num_bytes]
                self.buf = self.buf[num_bytes:]
                return retval
        chunks = self.bucket.get_object_contents(name, chunk_size=8192)
        return _(chunks)

    def _normalize_name(self, name):
        return name.lstrip('/')

class StorageFile(File):
    def __init__(self, name, mode, storage):
        self.name = name
        self.mode = mode
        self.file = StringIO()
        self._storage = storage
        self._is_dirty = False

    @property
    def size(self):
        if hasattr(self, '_size'):
            self._size = self.storage.size()
        return self._size

    def read(self, num_bytes=None):
        if not hasattr(self, '_obj'):
            self._obj = self._storage._open_read(self.name)
        return self._obj.read(num_bytes)

    def write(self, content):
        if 'w' not in self._mode:
            raise AttributeError("File was opened for read-only access.")
        self.file = StringIO(content)
        self._is_dirty = True

    def close(self):
        if self._is_dirty:
            self._storage._save(self.name, self.file.getvalue())
        self.file.close()

########NEW FILE########
__FILENAME__ = shell

# Copyright (C) 2012-2013 SINA, All rights reserved.

ShellMiddleware = lambda x: x

########NEW FILE########
__FILENAME__ = monkey

# Copyright (C) 2012-2013 SINA, All rights reserved.

import os.path
import sys
import re
import time
import errno

from sae.storage import Connection, Error

_S_FILEPATH_REGEX = re.compile('^(?:/s|/s/.*)$')
_S_FILENAME_REGEX = re.compile('^(?:/s|/s/([^/]*)/?(.*))$')

def _parse_name(filename):
    m = _S_FILENAME_REGEX.match(os.path.normpath(filename))
    if m:
        return m.groups()
    else:
        raise ValueError('invalid filename')

STORAGE_PATH = os.environ.get('sae.storage.path')

_is_storage_path = lambda n: _S_FILEPATH_REGEX.match(n)
def _get_storage_path(path):
    if not STORAGE_PATH:
        raise RuntimeError(
            "Please specify --storage-path in the command line")
    return STORAGE_PATH + n[2:]

class _File(file):

    def isatty(self):
        return False

    # Unimplemented interfaces below here.

    def flush(self):
        pass

    def fileno(self):
        raise NotImplementedError()

    def next(self):
        raise NotImplementedError()

    def readinto(self):
        raise NotImplementedError()

    def readline(self):
        raise NotImplementedError()

    def readlines(self):
        raise NotImplementedError()

    def truncate(self):
        raise NotImplementedError()

    def writelines(self):
        raise NotImplementedError()

    def xreadlines(self):
        raise NotImplementedError()

import __builtin__

_real_open = __builtin__.open
def open(filename, mode='r', buffering=-1):
    if _is_storage_path(filename):
        filename = _get_storage_path(filename)
    return _real_open(filename, mode, buffering)

import os

_real_os_listdir = os.listdir
def os_listdir(path):
    if _is_storage_path(path):
        path = _get_storage_path(path)
    return _real_os_listdir(path)

_real_os_mkdir = os.mkdir
def os_mkdir(path, mode=0777):
    if _is_storage_path(path):
        path = _get_storage_path(path)
    return _real_os_mkdir(path, mode)

_real_os_open = os.open
def os_open(filename, flag, mode=0777):
    if _is_storage_path(filename):
        filename = _get_storage_path(filename)
    return  _real_os_open(filename, flag, mode)

_real_os_fdopen = getattr(os, 'fdopen', None)
def os_fdopen(fd, mode='r', bufsize=-1):
    return _real_os_fdopen(fd, mode, bufsize)

_real_os_close = os.close
def os_close(fd):
    return _real_os_close(fd)

_real_os_chmod = os.chmod
def os_chmod(path, mode):
    if _is_storage_path(path):
        pass
    else:
        return _real_os_chmod(path, mode)

_real_os_stat = os.stat
def os_stat(path):
    if _is_storage_path(path):
        path = _get_storage_path(path)
    return _real_os_stat(path)

_real_os_unlink = os.unlink
def os_unlink(path):
    if _is_storage_path(path):
        path = _get_storage_path(path)
    return _real_os_unlink(path)

import os.path

_real_os_path_exists = os.path.exists
def os_path_exists(path):
    if _is_storage_path(path):
        path = _get_storage_path(path)
    return _real_os_path_exists(path)

_real_os_path_isdir = os.path.isdir
def os_path_isdir(path):
    if _is_storage_path(path):
        path = _get_storage_path(path)
    return _real_os_path_isdir(path)

_real_os_rmdir = os.rmdir
def os_rmdir(path):
    if _is_storage_path(path):
        path = _get_storage_path(path)
    return _real_os_rmdir(path)

def patch_all():
    __builtin__.open = open
    os.listdir = os_listdir
    os.mkdir = os_mkdir
    os.path.exists = os_path_exists
    os.path.isdir = os_path_isdir
    os.open = os_open
    os.fdopen = os_fdopen
    os.close = os_close
    os.chmod = os_chmod
    os.stat = os_stat
    os.unlink = os_unlink
    os.rmdir = os_rmdir

########NEW FILE########
__FILENAME__ = kvdb
#!/usr/bin/env python

"""
Fake client for sae kvdb service.

This should give you a feel for how this module operates::

    import kvdb
    kv = kvdb.KVClient()

    kv.set("some_key", "Some value")
    value = kv.get("some_key")

    kv.set("another_key", 3)
    kv.delete("another_key")
"""

import sys
import os
import re
import time
import pickle

SERVER_MAX_KEY_LENGTH = 250
#  Storing values larger than 1MB requires recompiling memcached.  If you do,
#  this value can be changed by doing "memcache.SERVER_MAX_VALUE_LENGTH = N"
#  after importing this module.
SERVER_MAX_VALUE_LENGTH = 1024*1024

class _Error(Exception):
    pass

class _ConnectionDeadError(Exception):
    pass

class _CacheEntry(object):
    
    def __init__(self, value, flags, expiration):
        self.value = value
        self.flags = flags
        self.created_time = time.time()
        self.will_expire = expiration != 0
        self.locked = False
        self._set_expiration(expiration)

    def _set_expiration(self, expiration):
        if expiration > (86400 * 30):
            self.expiration = expiration
        else:
            self.expiration = self.created_time + expiration

    def is_expired(self):
        return self.will_expire and time.time() > self.expiration

class local(object):
    pass

_DEAD_RETRY = 30  # number of seconds before retrying a dead server.
_SOCKET_TIMEOUT = 3  #  number of seconds before sockets timeout.

_cache = {}

class Client(local):
    """
    Object representing a pool of memcache servers.

    See L{memcache} for an overview.

    In all cases where a key is used, the key can be either:
        1. A simple hashable type (string, integer, etc.).
        2. A tuple of C{(hashvalue, key)}.  This is useful if you want to avoid
        making this module calculate a hash value.  You may prefer, for
        example, to keep all of a given user's objects on the same memcache
        server, so you could use the user's unique id as the hash value.

    @group Setup: __init__, set_servers, forget_dead_hosts, disconnect_all, debuglog
    @group Insertion: set, add, replace, set_multi
    @group Retrieval: get, get_multi
    @group Integers: incr, decr
    @group Removal: delete, delete_multi
    @sort: __init__, set_servers, forget_dead_hosts, disconnect_all, debuglog,\
           set, set_multi, add, replace, get, get_multi, incr, decr, delete, delete_multi
    """
    _FLAG_PICKLE  = 1<<0
    _FLAG_INTEGER = 1<<1
    _FLAG_LONG    = 1<<2
    _FLAG_COMPRESSED = 1<<3

    _SERVER_RETRIES = 10  # how many times to try finding a free server.

    # exceptions for Client
    class MemcachedKeyError(Exception):
        pass
    class MemcachedKeyLengthError(MemcachedKeyError):
        pass
    class MemcachedKeyCharacterError(MemcachedKeyError):
        pass
    class MemcachedKeyNoneError(MemcachedKeyError):
        pass
    class MemcachedKeyTypeError(MemcachedKeyError):
        pass
    class MemcachedStringEncodingError(Exception):
        pass

    def __init__(self, servers=[], debug=0, pickleProtocol=0,
                 pickler=pickle.Pickler, unpickler=pickle.Unpickler,
                 pload=None, pid=None,
                 server_max_key_length=SERVER_MAX_KEY_LENGTH,
                 server_max_value_length=SERVER_MAX_VALUE_LENGTH,
                 dead_retry=_DEAD_RETRY, socket_timeout=_SOCKET_TIMEOUT,
                 cache_cas = False):
        """
        Create a new Client object with the given list of servers.

        @param servers: C{servers} is passed to L{set_servers}.
        @param debug: whether to display error messages when a server can't be
        contacted.
        @param pickleProtocol: number to mandate protocol used by (c)Pickle.
        @param pickler: optional override of default Pickler to allow subclassing.
        @param unpickler: optional override of default Unpickler to allow subclassing.
        @param pload: optional persistent_load function to call on pickle loading.
        Useful for cPickle since subclassing isn't allowed.
        @param pid: optional persistent_id function to call on pickle storing.
        Useful for cPickle since subclassing isn't allowed.
        @param dead_retry: number of seconds before retrying a blacklisted
        server. Default to 30 s.
        @param socket_timeout: timeout in seconds for all calls to a server. Defaults
        to 3 seconds.
        @param cache_cas: (default False) If true, cas operations will be
        cached.  WARNING: This cache is not expired internally, if you have
        a long-running process you will need to expire it manually via
        "client.reset_cas(), or the cache can grow unlimited.
        @param server_max_key_length: (default SERVER_MAX_KEY_LENGTH)
        Data that is larger than this will not be sent to the server.
        @param server_max_value_length: (default SERVER_MAX_VALUE_LENGTH)
        Data that is larger than this will not be sent to the server.
        """
        local.__init__(self)
        self.debug = debug
        self.cache_cas = cache_cas
        self.reset_cas()

        # Allow users to modify pickling/unpickling behavior
        self.server_max_key_length = server_max_key_length
        self.server_max_value_length = server_max_value_length

        _cache = {}

        self.reset_stats()

    def reset_stats(self):
        self._get_hits = 0
        self._get_misses = 0
        self._cmd_set = 0
        self._cmd_get = 0

    def reset_cas(self):
        """
        Reset the cas cache.  This is only used if the Client() object
        was created with "cache_cas=True".  If used, this cache does not
        expire internally, so it can grow unbounded if you do not clear it
        yourself.
        """
        self.cas_ids = {}

    def set_servers(self, servers):
        """
        Set the pool of servers used by this client.

        @param servers: an array of servers.
        Servers can be passed in two forms:
            1. Strings of the form C{"host:port"}, which implies a default weight of 1.
            2. Tuples of the form C{("host:port", weight)}, where C{weight} is
            an integer weight value.
        """
        pass

    def get_info(self, stat_args = None):
        '''Get statistics from each of the servers.

        @param stat_args: Additional arguments to pass to the memcache
            "stats" command.

        @return: A list of tuples ( server_identifier, stats_dictionary ).
            The dictionary contains a number of name/value pairs specifying
            the name of the status field and the string value associated with
            it.  The values are not converted from strings.
        '''

        info = {
            'outbytes': 41, 
            'total_size': 22, 
            'inbytes': 62, 
            'set_count': 16, 
            'delete_count': 0, 
            'total_count': 4, 
            'get_count': 11
        }

        return info

    def debuglog(self, str):
        if self.debug:
            sys.stderr.write("MemCached: %s\n" % str)

    def forget_dead_hosts(self):
        """
        Reset every host in the pool to an "alive" state.
        """
        pass

    def disconnect_all(self):
        pass

    def delete(self, key):
        '''Deletes a key from the memcache.

        @return: Nonzero on success.
        '''
        if key not in _cache:
            return False
        del _cache[key]
        return True

    def add(self, key, val, time = 0, min_compress_len = 0):
        '''
        Add new key with value.

        Like L{set}, but only stores in memcache if the key doesn't already exist.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("add", key, val, time, min_compress_len)

    def replace(self, key, val, time=0, min_compress_len=0):
        '''Replace existing key with value.

        Like L{set}, but only stores in memcache if the key already exists.
        The opposite of L{add}.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("replace", key, val, time, min_compress_len)

    def set(self, key, val, time=0, min_compress_len=0):
        '''Unconditionally sets a key to a given value in the memcache.

        The C{key} can optionally be an tuple, with the first element
        being the server hash value and the second being the key.
        If you want to avoid making this module calculate a hash value.
        You may prefer, for example, to keep all of a given user's objects
        on the same memcache server, so you could use the user's unique
        id as the hash value.

        @return: Nonzero on success.
        @rtype: int
        @param time: Tells memcached the time which this value should expire, either
        as a delta number of seconds, or an absolute unix time-since-the-epoch
        value. See the memcached protocol docs section "Storage Commands"
        for more info on <exptime>. We default to 0 == cache forever.
        @param min_compress_len: The threshold length to kick in auto-compression
        of the value using the zlib.compress() routine. If the value being cached is
        a string, then the length of the string is measured, else if the value is an
        object, then the length of the pickle result is measured. If the resulting
        attempt at compression yeilds a larger string than the input, then it is
        discarded. For backwards compatability, this parameter defaults to 0,
        indicating don't ever try to compress.
        '''
        return self._set("set", key, val, time, min_compress_len)

    def _set(self, cmd, key, val, time, min_compress_len = 0):
        self.check_key(key)

        self._cmd_set += 1

        key_exists = key in _cache

        if ((cmd == 'add' and key_exists) or
            (cmd == 'replace' and not key_exists) or
            (cmd == 'prepend' and not key_exists) or
            (cmd == 'append' and not key_exists)):
            return False

        if cmd == 'prepend':
            new_val = val + _cache[key].value
        elif cmd == 'append':
            new_val = _cache[key].value + val
        else:
            new_val = val

        _cache[key] = _CacheEntry(new_val, 0, time)
        return True

    def _get(self, cmd, key):
        self.check_key(key)

        self._cmd_get += 1

        if key in _cache:
            entry = _cache[key]
            if not entry.is_expired():
                self._get_hits += 1
                return entry.value
        self._get_misses += 1
        return None

    def get(self, key):
        '''Retrieves a key from the memcache.

        @return: The value or None.
        '''
        return self._get('get', key)

    def get_multi(self, keys, key_prefix=''):
        '''
        Retrieves multiple keys from the memcache doing just one query.

        >>> success = mc.set("foo", "bar")
        >>> success = mc.set("baz", 42)
        >>> mc.get_multi(["foo", "baz", "foobar"]) == {"foo": "bar", "baz": 42}
        1

        get_mult [ and L{set_multi} ] can take str()-ables like ints / longs as keys too. Such as your db pri key fields.
        They're rotored through str() before being passed off to memcache, with or without the use of a key_prefix.
        In this mode, the key_prefix could be a table name, and the key itself a db primary key number.

        This method is recommended over regular L{get} as it lowers the number of
        total packets flying around your network, reducing total latency, since
        your app doesn't have to wait for each round-trip of L{get} before sending
        the next one.

        See also L{set_multi}.

        @param keys: An array of keys.
        @param key_prefix: A string to prefix each key when we communicate with memcache.
            Facilitates pseudo-namespaces within memcache. Returned dictionary keys will not have this prefix.
        @return:  A dictionary of key/value pairs that were available. If key_prefix was provided, the keys in the retured dictionary will not have it present.

        '''
        retval = {}
        for e in keys:
            _key = key_prefix + str(e)
            val = self._get('get', _key)
            if val is not None:
                retval[e] = val
        return retval

    def get_by_prefix(self, prefix, limit=None, max_count=None,
                      marker=None, start_key=None):
        '''
        >>> success = mc.set('k1', 1)
        >>> success = mc.set('k2', 2)
        >>> success = mc.set('xyz', 'xxxxxxx')
        >>> mc.get_by_prefix('k') == [('k2', 2), ('k1', 1)]
        1

        '''
        start_key = marker or start_key
        max_count = limit or max_count or 100

        ignore = False
        if start_key is not None:
            ignore = True

        for k, e in _cache.iteritems():
            if ignore:
                if k == start_key:
                    ignore = False
                continue

            if e.is_expired():
                continue

            if max_count <= 0: break

            if str(k).startswith(prefix):
                max_count -= 1
                yield k, e.value

    def getkeys_by_prefix(self, prefix, limit=None, max_count=None,
                          marker=None, start_key=None):
        max_count = limit or max_count
        marker = marker or start_key
        kv = self.get_by_prefix(prefix, max_count, marker=marker)
        return [e[0] for e in kv]

    def check_key(self, key, key_extra_len=0):
        """Checks sanity of key.  Fails if:
            Key length is > SERVER_MAX_KEY_LENGTH (Raises MemcachedKeyLength).
            Contains control characters  (Raises MemcachedKeyCharacterError).
            Is not a string (Raises MemcachedStringEncodingError)
            Is an unicode string (Raises MemcachedStringEncodingError)
            Is not a string (Raises MemcachedKeyError)
            Is None (Raises MemcachedKeyError)
        """
        if isinstance(key, tuple): key = key[1]
        if not key:
            raise Client.MemcachedKeyNoneError("Key is None")
        if isinstance(key, unicode):
            raise Client.MemcachedStringEncodingError(
                    "Keys must be str()'s, not unicode.  Convert your unicode "
                    "strings using mystring.encode(charset)!")
        if not isinstance(key, str):
            raise Client.MemcachedKeyTypeError("Key must be str()'s")

        if isinstance(key, basestring):
            if self.server_max_key_length != 0 and \
                len(key) + key_extra_len > self.server_max_key_length:
                raise Client.MemcachedKeyLengthError("Key length is > %s"
                         % self.server_max_key_length)
            for char in key:
                if ord(char) < 33 or ord(char) == 127:
                    raise Client.MemcachedKeyCharacterError(
                            "Control characters not allowed")

KVClient = Client

def _doctest():
    import doctest, kvdb
    servers = ["127.0.0.1:11211"]
    mc = Client(servers, debug=1)
    globs = {"mc": mc}
    return doctest.testmod(kvdb, globs=globs)

if __name__ == "__main__":
    failures = 0
    print "Testing docstrings..."
    _doctest()
    print "Running tests:"
    print
    serverList = [["127.0.0.1:11211"]]
    if '--do-unix' in sys.argv:
        serverList.append([os.path.join(os.getcwd(), 'memcached.socket')])

    for servers in serverList:
        mc = KVClient(servers, debug=1)

        def to_s(val):
            if not isinstance(val, basestring):
                return "%s (%s)" % (val, type(val))
            return "%s" % val
        def test_setget(key, val):
            global failures
            print "Testing set/get {'%s': %s} ..." % (to_s(key), to_s(val)),
            mc.set(key, val)
            newval = mc.get(key)
            if newval == val:
                print "OK"
                return 1
            else:
                print "FAIL"; failures = failures + 1
                return 0


        class FooStruct(object):
            def __init__(self):
                self.bar = "baz"
            def __str__(self):
                return "A FooStruct"
            def __eq__(self, other):
                if isinstance(other, FooStruct):
                    return self.bar == other.bar
                return 0

        test_setget("a_string", "some random string")
        test_setget("an_integer", 42)
        if test_setget("long", long(1<<30)):
            print "Testing delete ...",
            if mc.delete("long"):
                print "OK"
            else:
                print "FAIL"; failures = failures + 1
            print "Checking results of delete ..."
            if mc.get("long") == None:
                print "OK"
            else:
                print "FAIL"; failures = failures + 1
        print "Testing get_multi ...",
        print mc.get_multi(["a_string", "an_integer"])

        #  removed from the protocol
        #if test_setget("timed_delete", 'foo'):
        #    print "Testing timed delete ...",
        #    if mc.delete("timed_delete", 1):
        #        print "OK"
        #    else:
        #        print "FAIL"; failures = failures + 1
        #    print "Checking results of timed delete ..."
        #    if mc.get("timed_delete") == None:
        #        print "OK"
        #    else:
        #        print "FAIL"; failures = failures + 1

        print "Testing get(unknown value) ...",
        print to_s(mc.get("unknown_value"))

        f = FooStruct()
        test_setget("foostruct", f)

        #print "Testing incr ...",
        #x = mc.incr("an_integer", 1)
        #if x == 43:
        #    print "OK"
        #else:
        #    print "FAIL"; failures = failures + 1

        #print "Testing decr ...",
        #x = mc.decr("an_integer", 1)
        #if x == 42:
        #    print "OK"
        #else:
        #    print "FAIL"; failures = failures + 1
        sys.stdout.flush()

        # sanity tests
        print "Testing sending spaces...",
        sys.stdout.flush()
        try:
            x = mc.set("this has spaces", 1)
        except Client.MemcachedKeyCharacterError, msg:
            print "OK"
        else:
            print "FAIL"; failures = failures + 1

        print "Testing sending control characters...",
        try:
            x = mc.set("this\x10has\x11control characters\x02", 1)
        except Client.MemcachedKeyCharacterError, msg:
            print "OK"
        else:
            print "FAIL"; failures = failures + 1

        print "Testing using insanely long key...",
        try:
            x = mc.set('a'*SERVER_MAX_KEY_LENGTH, 1)
        except Client.MemcachedKeyLengthError, msg:
            print "FAIL"; failures = failures + 1
        else:
            print "OK"
        try:
            x = mc.set('a'*SERVER_MAX_KEY_LENGTH + 'a', 1)
        except Client.MemcachedKeyLengthError, msg:
            print "OK"
     
db_file = os.environ.get('sae.kvdb.file')
if db_file:
    import pickle
    def _save_cache():
        # XXX: reloader should not do this
        if not os.environ.get('sae.run_main'): return
        try:
            pickle.dump(_cache, open(db_file, 'wb'))
        except Exception, e:
            print "save kvdb to '%s' failed: %s" % (db_file, str(e))
    def _restore_cache():
        try:
            _cache.update(pickle.load(open(db_file, 'rb')))
        except Exception, e:
            print "load kvdb from '%s' failed: %s" % (db_file, str(e))
    import atexit
    atexit.register(_save_cache)
    _restore_cache()

########NEW FILE########
__FILENAME__ = mail
#!/usr/bin/env python
# -*-coding: utf8 -*-

"""SAE Mail API

Provides functions for application developers to deliver mail messages 
for their applications. Currently we only support send mail through SMTP 
asynchronously.

Examle:

1. Send a simple plain-text message.

    from sae.mail import send_mail

    send_mail('recipient@sina.com', 'subject', 'plain text',
              ('smtp.sina.com', 25, 'me@sina.com', 'password', False))

2. Send a HTML-format message.

    from sae.mail import EmailMessage

    m = EmailMessage()
    m.to = 'recipient@sina.com'
    m.subject = 'unforgivable sinner'
    m.html = '<b>darling, please, please forgive me...</b>'
    m.smtp = ('smtp.sina.com', 25, 'me@sina.com', 'password', False)
    m.send()
"""

__all__ = ['Error', 'InternalError', 'InvalidAttachmentTypeError', 
           'InvalidRequestError', 'MailTooLargeError', 'MissingBodyError', 
           'MissingRecipientError', 'MissingSMTPError', 'MissingSubjectError',
           'ServiceUnavailableError', 'MAX_EMAIL_SIZE', 'EmailMessage', 
           'send_mail']

import base64
import json
import time
import urllib
import urllib2

import core
import conf
import util

class Error(Exception):
    """Base-class for all errors in this module"""

class InternalError(Error):
    """There was an internal error while sending message, it should be 
    temporary, it problem continues, please contact us"""

class InvalidRequestError(Error):
    """The request we send to the mail backend is illengal."""

class MissingRecipientError(Error):
    """No recipient specified in message"""

class MissingSubjectError(Error):
    """No subject specified in message"""

class MissingBodyError(Error):
    """No body content specified in the message"""

class MissingSMTPError(Error):
    """No smtp server configuration is provided."""

class InvalidAttachmentTypeError(Error):
    """The type of the attachment is not permitted."""

class MailTooLargeError(Error):
    """The email is too large, """

class ServiceUnavailableError(Error):
    """The application has reached its service quota or has no permission."""

_ERROR_MAPPING = {3: InvalidRequestError, 500: InternalError, 999: InternalError,
                  999: ServiceUnavailableError}

_MAIL_BACKEND = "http://mail.sae.sina.com.cn/index.php"

MAX_EMAIL_SIZE = 1048576 # bytes (1M)

class EmailMessage(object):
    """Main interface to SAE Mail Service
    """
    _properties = ['to', 'subject', 'body', 'html', 'attachments', 'smtp', 'from_addr']
    _ext_to_disposition = {
        'bmp':  'I', 'css':  'A',
        'csv':  'A', 'gif':  'I',
        'htm':  'I', 'html': 'I',
        'jpeg': 'I', 'jpg':  'I',
        'jpe':  'I', 'pdf':  'A',
        'png':  'I', 'rss':  'I',
        'text': 'A', 'txt':  'A',
        'asc':  'A', 'diff': 'A',
        'pot':  'A', 'tiff': 'A',
        'tif':  'A', 'wbmp': 'I',
        'ics':  'I', 'vcf':  'I'
    }

    def __init__(self, **kwargs):
        """Initializer"""
        self.initialize(**kwargs)

    def initialize(self, **kwargs):
        """Sets fields of the email message
        
        Args:
          to: The recipient's email address.
          subject: The subject of the message.
          body: The content of the message, plain-text only.
          html: Use this field when you want to send html-encoded message.
          smtp: This is a five-element tuple of your smtp server's configuration
            (smtp_host, smtp_port, smtp_username, smtp_password, smtp_tls).
          attachments: The file attachments of the message, as a list of 
            two-value tuples, one tuple for each attachment. Each tuple contains
            a filename as the first element, and the file contents as the second
            element.
        """
        for name, value in kwargs.iteritems():
            setattr(self, name, value)

    def send(self):
        """Sends the email message.
        
        This method just post the message to the mail delivery queue.
        """
        message = self._to_proto()
        #print message
        self._remote_call(message)

    def check_initialized(self):
        if not hasattr(self, 'to'):
            raise MissingRecipientError()

        if not hasattr(self, 'subject'):
            raise MissingSubjectError()

        if not hasattr(self, 'smtp'):
            raise MissingSMTPError()

        if not hasattr(self, 'body') and not hasattr(self, 'html'):
            raise MissingBodyError()

    def _check_email_valid(self, address):
        if not isinstance(address, basestring):
            raise TypeError()

        # TODO: validate email address

    def _check_smtp_valid(self, smtp):
        if not isinstance(smtp, tuple) or len(smtp) != 5:
            raise TypeError()

    def _check_attachments(self, attachments):
        for a in attachments:
            if not isinstance(a, tuple) or len(a) != 2:
                raise TypeError()

    def __setattr__(self, attr, value):
        if attr not in self._properties:
            raise AttributeError("'EmailMessage' has no attribute '%s'" % attr)

        if not value:
            raise ValueError("May not set empty value for '%s'" % attr)

        if attr == 'to':
            if isinstance(value, list):
                for v in value:
                    self._check_email_valid(v)
                to = ','.join(value)
                super(EmailMessage, self).__setattr__(attr, to) 
                return

            self._check_email_valid(value)
        elif attr == 'smtp':
            self._check_smtp_valid(value)
        elif attr == 'attachments':
            self._check_attachments(value)

        super(EmailMessage, self).__setattr__(attr, value)

    def _to_proto(self):
        """Convert mail mesage to protocol message"""
        self.check_initialized()

        args = {'from':          getattr(self, 'from_addr', self.smtp[2]),
                'to':            self.to,
                'subject':       self.subject,
                'smtp_host':     self.smtp[0],
                'smtp_port':     self.smtp[1],
                'smtp_username': self.smtp[2],
                'smtp_password': self.smtp[3],
                'tls':           self.smtp[4]}

        size = 0

        if hasattr(self, 'body'):
            args['content'] = self.body
            args['content_type'] = 'TEXT'
            size = size + len(self.body)
        elif hasattr(self, 'html'):
            args['content'] = self.html
            args['content_type']  = 'HTML'
            size = size + len(self.html)

        if hasattr(self, 'attachments'):
            for attachment in self.attachments:
                ext = attachment[0].split('.')[-1]

                disposition = self._ext_to_disposition.get(ext)
                if not disposition:
                    raise InvalidAttachmentTypeError()

                key = 'attach:' + attachment[0] + ':B:' + disposition
                args[key] = base64.encodestring(attachment[1])

                size = size + len(attachment[1])

        if size > MAX_EMAIL_SIZE:
            raise MailTooLargeError()

        message = {'saemail': json.dumps(args)}
        return message

    def _remote_call(self, message):
        args = json.loads(message['saemail'])

        # just print the message on console
        print '[SAE:MAIL] Sending new mail'
        import pprint
        pprint.pprint(args)

    def _get_headers(self):
        access_key = core.get_access_key()
        secret_key = core.get_secret_key()

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        msg = 'ACCESSKEY' + access_key + 'TIMESTAMP' + timestamp
        headers = {'TimeStamp': timestamp,
                   'AccessKey': access_key,
                   'Signature': util.get_signature(secret_key, msg)}

        return headers

def send_mail(to, subject, body, smtp, **kwargs):
    """A shortcut for sending mail"""
    kwargs['to'] = to
    kwargs['subject'] = subject
    kwargs['body'] = body
    kwargs['smtp'] = smtp
    
    EmailMessage(**kwargs).send()


########NEW FILE########
__FILENAME__ = memcache
#!/usr/bin/env python

"""
Fake client for sae memcached service.

This client keeps all the data in local memory, and the data will be lost once 
the process is down.

This should give you a feel for how this module operates::

    import pylibmc
    mc = pylibmc.Client()

    mc.set("some_key", "Some value")
    value = mc.get("some_key")

    mc.set("another_key", 3)
    mc.delete("another_key")

    mc.set("key", "1")   # note that the key used for incr/decr must be a string.
    mc.incr("key")
    mc.decr("key")

The standard way to use memcache with a database is like this::

    key = derive_key(obj)
    obj = mc.get(key)
    if not obj:
        obj = backend_api.get(...)
        mc.set(key, obj)

    # we now have obj, and future passes through this code
    # will use the object from the cache.

Detailed Documentation
======================

More detailed documentation is available in the L{Client} class.
"""

import sys
import os
import re
import time
import pickle

SERVER_MAX_KEY_LENGTH = 250
#  Storing values larger than 1MB requires recompiling memcached.  If you do,
#  this value can be changed by doing "memcache.SERVER_MAX_VALUE_LENGTH = N"
#  after importing this module.
SERVER_MAX_VALUE_LENGTH = 1024*1024

class _Error(Exception):
    pass

class _ConnectionDeadError(Exception):
    pass

class _CacheEntry(object):
    
    def __init__(self, value, flags, expiration):
        self.value = value
        self.flags = flags
        self.created_time = time.time()
        self.will_expire = expiration != 0
        self.locked = False
        self._set_expiration(expiration)

    def _set_expiration(self, expiration):
        if expiration > (86400 * 30):
            self.expiration = expiration
        else:
            self.expiration = self.created_time + expiration

    def is_expired(self):
        return self.will_expire and time.time() > self.expiration

class local(object):
    pass

_DEAD_RETRY = 30  # number of seconds before retrying a dead server.
_SOCKET_TIMEOUT = 3  #  number of seconds before sockets timeout.

_cache = {}

class Client(local):
    """
    Object representing a pool of memcache servers.

    See L{memcache} for an overview.

    In all cases where a key is used, the key can be either:
        1. A simple hashable type (string, integer, etc.).
        2. A tuple of C{(hashvalue, key)}.  This is useful if you want to avoid
        making this module calculate a hash value.  You may prefer, for
        example, to keep all of a given user's objects on the same memcache
        server, so you could use the user's unique id as the hash value.

    @group Setup: __init__, set_servers, forget_dead_hosts, disconnect_all, debuglog
    @group Insertion: set, add, replace, set_multi
    @group Retrieval: get, get_multi
    @group Integers: incr, decr
    @group Removal: delete, delete_multi
    @sort: __init__, set_servers, forget_dead_hosts, disconnect_all, debuglog,\
           set, set_multi, add, replace, get, get_multi, incr, decr, delete, delete_multi
    """
    _FLAG_PICKLE  = 1<<0
    _FLAG_INTEGER = 1<<1
    _FLAG_LONG    = 1<<2
    _FLAG_COMPRESSED = 1<<3

    _SERVER_RETRIES = 10  # how many times to try finding a free server.

    # exceptions for Client
    class MemcachedKeyError(Exception):
        pass
    class MemcachedKeyLengthError(MemcachedKeyError):
        pass
    class MemcachedKeyCharacterError(MemcachedKeyError):
        pass
    class MemcachedKeyNoneError(MemcachedKeyError):
        pass
    class MemcachedKeyTypeError(MemcachedKeyError):
        pass
    class MemcachedStringEncodingError(Exception):
        pass

    def __init__(self, servers=[], debug=0, pickleProtocol=0,
                 pickler=pickle.Pickler, unpickler=pickle.Unpickler,
                 pload=None, pid=None,
                 server_max_key_length=SERVER_MAX_KEY_LENGTH,
                 server_max_value_length=SERVER_MAX_VALUE_LENGTH,
                 dead_retry=_DEAD_RETRY, socket_timeout=_SOCKET_TIMEOUT,
                 cache_cas = False):
        """
        Create a new Client object with the given list of servers.

        @param servers: C{servers} is passed to L{set_servers}.
        @param debug: whether to display error messages when a server can't be
        contacted.
        @param pickleProtocol: number to mandate protocol used by (c)Pickle.
        @param pickler: optional override of default Pickler to allow subclassing.
        @param unpickler: optional override of default Unpickler to allow subclassing.
        @param pload: optional persistent_load function to call on pickle loading.
        Useful for cPickle since subclassing isn't allowed.
        @param pid: optional persistent_id function to call on pickle storing.
        Useful for cPickle since subclassing isn't allowed.
        @param dead_retry: number of seconds before retrying a blacklisted
        server. Default to 30 s.
        @param socket_timeout: timeout in seconds for all calls to a server. Defaults
        to 3 seconds.
        @param cache_cas: (default False) If true, cas operations will be
        cached.  WARNING: This cache is not expired internally, if you have
        a long-running process you will need to expire it manually via
        "client.reset_cas(), or the cache can grow unlimited.
        @param server_max_key_length: (default SERVER_MAX_KEY_LENGTH)
        Data that is larger than this will not be sent to the server.
        @param server_max_value_length: (default SERVER_MAX_VALUE_LENGTH)
        Data that is larger than this will not be sent to the server.
        """
        local.__init__(self)
        self.debug = debug
        self.cache_cas = cache_cas
        self.reset_cas()

        # Allow users to modify pickling/unpickling behavior
        self.server_max_key_length = server_max_key_length
        self.server_max_value_length = server_max_value_length

        _cache = {}

        self.reset_stats()

    def reset_stats(self):
        self._get_hits = 0
        self._get_misses = 0
        self._cmd_set = 0
        self._cmd_get = 0

    def reset_cas(self):
        """
        Reset the cas cache.  This is only used if the Client() object
        was created with "cache_cas=True".  If used, this cache does not
        expire internally, so it can grow unbounded if you do not clear it
        yourself.
        """
        self.cas_ids = {}

    def set_servers(self, servers):
        """
        Set the pool of servers used by this client.

        @param servers: an array of servers.
        Servers can be passed in two forms:
            1. Strings of the form C{"host:port"}, which implies a default weight of 1.
            2. Tuples of the form C{("host:port", weight)}, where C{weight} is
            an integer weight value.
        """
        pass

    def get_stats(self, stat_args = None):
        '''Get statistics from each of the servers.

        @param stat_args: Additional arguments to pass to the memcache
            "stats" command.

        @return: A list of tuples ( server_identifier, stats_dictionary ).
            The dictionary contains a number of name/value pairs specifying
            the name of the status field and the string value associated with
            it.  The values are not converted from strings.
        '''

        total_bytes= 0
        for k, e in _cache.iteritems():
            total_bytes += len(str(e.value))

        curr_items = len(_cache)

        name = '10.67.15.110:9211 (0)'
        stats = {
            'bytes': str(total_bytes),
            'bytes_read': '920852',
            'bytes_written': '3615514',
            'cmd_get': str(self._cmd_get),
            'cmd_set': str(self._cmd_set),
            'connection_structures': '676',
            'curr_connections': '3',
            'curr_items': str(curr_items),
            'evictions': '0',
            'get_hits': str(self._get_hits),
            'get_misses': str(self._get_misses),
            'limit_maxbytes': '1048576',
            'pid': '24925',
            'pointer_size': '64',
            'rusage_system': '38237.950000',
            'rusage_user': '53464.940000',
            'threads': '0',
            'time': str(int(time.time())),
            'total_connections': '350149607',
            'total_items': str(curr_items),
            'uptime': '2541642',
            'version': '1.4.5'
        }

        return [(name, stats),]

    def flush_all(self):
        'Expire all data currently in the memcache servers.'
        _cache.clear()

    def debuglog(self, str):
        if self.debug:
            sys.stderr.write("MemCached: %s\n" % str)

    def forget_dead_hosts(self):
        """
        Reset every host in the pool to an "alive" state.
        """
        pass

    def disconnect_all(self):
        pass

    def delete_multi(self, keys, time=0, key_prefix=''):
        '''
        Delete multiple keys in the memcache doing just one query.

        >>> notset_keys = mc.set_multi({'key1' : 'val1', 'key2' : 'val2'})
        >>> mc.get_multi(['key1', 'key2']) == {'key1' : 'val1', 'key2' : 'val2'}
        1
        >>> mc.delete_multi(['key1', 'key2'])
        1
        >>> mc.get_multi(['key1', 'key2']) == {}
        1


        This method is recommended over iterated regular L{delete}s as it reduces total latency, since
        your app doesn't have to wait for each round-trip of L{delete} before sending
        the next one.

        @param keys: An iterable of keys to clear
        @param time: number of seconds any subsequent set / update commands should fail. Defaults to 0 for no delay.
        @param key_prefix:  Optional string to prepend to each key when sending to memcache.
            See docs for L{get_multi} and L{set_multi}.

        @return: 1 if no failure in communication with any memcacheds.
        @rtype: int

        '''
        for key in keys:
            _key = key_prefix + str(key)
            try:
                del _cache[_key]
            except KeyError:
                pass

        return True

    def delete(self, key):
        '''Deletes a key from the memcache.

        @return: Nonzero on success.
        '''
        if key not in _cache:
            return False
        del _cache[key]
        return True

    def incr(self, key, delta=1):
        """
        Sends a command to the server to atomically increment the value
        for C{key} by C{delta}, or by 1 if C{delta} is unspecified.
        Returns None if C{key} doesn't exist on server, otherwise it
        returns the new value after incrementing.

        Note that the value for C{key} must already exist in the memcache,
        and it must be the string representation of an integer.

        >>> mc.set("counter", "20")  # returns 1, indicating success
        1
        >>> mc.incr("counter")
        21
        >>> mc.incr("counter")
        22

        Overflow on server is not checked.  Be aware of values approaching
        2**32.  See L{decr}.

        @param delta: Integer amount to increment by (should be zero or greater).
        @return: New value after incrementing.
        @rtype: int
        """
        return self._incrdecr("incr", key, delta)

    def decr(self, key, delta=1):
        """
        Like L{incr}, but decrements.  Unlike L{incr}, underflow is checked and
        new values are capped at 0.  If server value is 1, a decrement of 2
        returns 0, not -1.

        @param delta: Integer amount to decrement by (should be zero or greater).
        @return: New value after decrementing.
        @rtype: int
        """
        return self._incrdecr("decr", key, delta)

    def _incrdecr(self, cmd, key, delta):
        self.check_key(key)

        if key not in _cache:
            return False

        if cmd == 'decr':
            delta = - delta

        value = int(_cache[key].value) + delta
        if value < 0: value = 0
        _cache[key].value = value

        return value

    def add(self, key, val, time = 0, min_compress_len = 0):
        '''
        Add new key with value.

        Like L{set}, but only stores in memcache if the key doesn't already exist.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("add", key, val, time, min_compress_len)

    def append(self, key, val, time=0, min_compress_len=0):
        '''Append the value to the end of the existing key's value.

        Only stores in memcache if key already exists.
        Also see L{prepend}.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("append", key, val, time, min_compress_len)

    def prepend(self, key, val, time=0, min_compress_len=0):
        '''Prepend the value to the beginning of the existing key's value.

        Only stores in memcache if key already exists.
        Also see L{append}.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("prepend", key, val, time, min_compress_len)

    def replace(self, key, val, time=0, min_compress_len=0):
        '''Replace existing key with value.

        Like L{set}, but only stores in memcache if the key already exists.
        The opposite of L{add}.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("replace", key, val, time, min_compress_len)

    def set(self, key, val, time=0, min_compress_len=0):
        '''Unconditionally sets a key to a given value in the memcache.

        The C{key} can optionally be an tuple, with the first element
        being the server hash value and the second being the key.
        If you want to avoid making this module calculate a hash value.
        You may prefer, for example, to keep all of a given user's objects
        on the same memcache server, so you could use the user's unique
        id as the hash value.

        @return: Nonzero on success.
        @rtype: int
        @param time: Tells memcached the time which this value should expire, either
        as a delta number of seconds, or an absolute unix time-since-the-epoch
        value. See the memcached protocol docs section "Storage Commands"
        for more info on <exptime>. We default to 0 == cache forever.
        @param min_compress_len: The threshold length to kick in auto-compression
        of the value using the zlib.compress() routine. If the value being cached is
        a string, then the length of the string is measured, else if the value is an
        object, then the length of the pickle result is measured. If the resulting
        attempt at compression yeilds a larger string than the input, then it is
        discarded. For backwards compatability, this parameter defaults to 0,
        indicating don't ever try to compress.
        '''
        return self._set("set", key, val, time, min_compress_len)


    def cas(self, key, val, time=0, min_compress_len=0):
        '''Sets a key to a given value in the memcache if it hasn't been
        altered since last fetched. (See L{gets}).

        The C{key} can optionally be an tuple, with the first element
        being the server hash value and the second being the key.
        If you want to avoid making this module calculate a hash value.
        You may prefer, for example, to keep all of a given user's objects
        on the same memcache server, so you could use the user's unique
        id as the hash value.

        @return: Nonzero on success.
        @rtype: int
        @param time: Tells memcached the time which this value should expire,
        either as a delta number of seconds, or an absolute unix
        time-since-the-epoch value. See the memcached protocol docs section
        "Storage Commands" for more info on <exptime>. We default to
        0 == cache forever.
        @param min_compress_len: The threshold length to kick in
        auto-compression of the value using the zlib.compress() routine. If
        the value being cached is a string, then the length of the string is
        measured, else if the value is an object, then the length of the
        pickle result is measured. If the resulting attempt at compression
        yeilds a larger string than the input, then it is discarded. For
        backwards compatability, this parameter defaults to 0, indicating
        don't ever try to compress.
        '''
        return self._set("cas", key, val, time, min_compress_len)

    def set_multi(self, mapping, time=0, key_prefix='', min_compress_len=0):
        '''
        Sets multiple keys in the memcache doing just one query.

        >>> notset_keys = mc.set_multi({'key1' : 'val1', 'key2' : 'val2'})
        >>> mc.get_multi(['key1', 'key2']) == {'key1' : 'val1', 'key2' : 'val2'}
        1


        This method is recommended over regular L{set} as it lowers the number of
        total packets flying around your network, reducing total latency, since
        your app doesn't have to wait for each round-trip of L{set} before sending
        the next one.

        @param mapping: A dict of key/value pairs to set.
        @param time: Tells memcached the time which this value should expire, either
        as a delta number of seconds, or an absolute unix time-since-the-epoch
        value. See the memcached protocol docs section "Storage Commands"
        for more info on <exptime>. We default to 0 == cache forever.
        @param key_prefix:  Optional string to prepend to each key when sending to memcache. Allows you to efficiently stuff these keys into a pseudo-namespace in memcache:
            >>> notset_keys = mc.set_multi({'key1' : 'val1', 'key2' : 'val2'}, key_prefix='subspace_')
            >>> len(notset_keys) == 0
            True
            >>> mc.get_multi(['subspace_key1', 'subspace_key2']) == {'subspace_key1' : 'val1', 'subspace_key2' : 'val2'}
            True

            Causes key 'subspace_key1' and 'subspace_key2' to be set. Useful in conjunction with a higher-level layer which applies namespaces to data in memcache.
            In this case, the return result would be the list of notset original keys, prefix not applied.

        @param min_compress_len: The threshold length to kick in auto-compression
        of the value using the zlib.compress() routine. If the value being cached is
        a string, then the length of the string is measured, else if the value is an
        object, then the length of the pickle result is measured. If the resulting
        attempt at compression yeilds a larger string than the input, then it is
        discarded. For backwards compatability, this parameter defaults to 0,
        indicating don't ever try to compress.
        @return: List of keys which failed to be stored [ memcache out of memory, etc. ].
        @rtype: list

        '''
        self._cmd_set += 1

        for key, value in mapping.iteritems():
            if isinstance(key, basestring):
                flags = 0
            else:
                flags = 1
            _key = key_prefix + str(key)
            self.check_key(_key)
            _cache[_key] = _CacheEntry(value, flags, time)

        return []
        

    def _set(self, cmd, key, val, time, min_compress_len = 0):
        self.check_key(key)

        self._cmd_set += 1

        key_exists = key in _cache

        if ((cmd == 'add' and key_exists) or
            (cmd == 'replace' and not key_exists) or
            (cmd == 'prepend' and not key_exists) or
            (cmd == 'append' and not key_exists)):
            return False

        if cmd == 'prepend':
            new_val = val + _cache[key].value
        elif cmd == 'append':
            new_val = _cache[key].value + val
        else:
            new_val = val

        _cache[key] = _CacheEntry(new_val, 0, time)
        return True

    def _get(self, cmd, key):
        self.check_key(key)

        self._cmd_get += 1

        if key in _cache:
            entry = _cache[key]
            if not entry.is_expired():
                self._get_hits += 1
                return entry.value
        self._get_misses += 1
        return None

    def get(self, key):
        '''Retrieves a key from the memcache.

        @return: The value or None.
        '''
        return self._get('get', key)

    def gets(self, key):
        '''Retrieves a key from the memcache. Used in conjunction with 'cas'.

        @return: The value or None.
        '''
        return self._get('gets', key)

    def get_multi(self, keys, key_prefix=''):
        '''
        Retrieves multiple keys from the memcache doing just one query.

        >>> success = mc.set("foo", "bar")
        >>> success = mc.set("baz", 42)
        >>> mc.get_multi(["foo", "baz", "foobar"]) == {"foo": "bar", "baz": 42}
        1
        >>> mc.set_multi({'k1' : 1, 'k2' : 2}, key_prefix='pfx_') == []
        1

        This looks up keys 'pfx_k1', 'pfx_k2', ... . Returned dict will just have unprefixed keys 'k1', 'k2'.
        >>> mc.get_multi(['k1', 'k2', 'nonexist'], key_prefix='pfx_') == {'k1' : 1, 'k2' : 2}
        1

        get_mult [ and L{set_multi} ] can take str()-ables like ints / longs as keys too. Such as your db pri key fields.
        They're rotored through str() before being passed off to memcache, with or without the use of a key_prefix.
        In this mode, the key_prefix could be a table name, and the key itself a db primary key number.

        >>> mc.set_multi({42: 'douglass adams', 46 : 'and 2 just ahead of me'}, key_prefix='numkeys_') == []
        1
        >>> mc.get_multi([46, 42], key_prefix='numkeys_') == {42: 'douglass adams', 46 : 'and 2 just ahead of me'}
        1

        This method is recommended over regular L{get} as it lowers the number of
        total packets flying around your network, reducing total latency, since
        your app doesn't have to wait for each round-trip of L{get} before sending
        the next one.

        See also L{set_multi}.

        @param keys: An array of keys.
        @param key_prefix: A string to prefix each key when we communicate with memcache.
            Facilitates pseudo-namespaces within memcache. Returned dictionary keys will not have this prefix.
        @return:  A dictionary of key/value pairs that were available. If key_prefix was provided, the keys in the retured dictionary will not have it present.

        '''
        self._cmd_get += 1

        retvals = {}
        for key in keys:
            _key = key_prefix + str(key)
            try:
                entry = _cache[_key]
            except KeyError:
                self._get_misses += 1
                continue

            if entry.is_expired():
                self._get_misses += 1
                continue
            if entry.flags ==  1:
                key = int(key)
            retvals[key] = entry.value
            self._get_hits += 1

        return retvals

    def check_key(self, key, key_extra_len=0):
        """Checks sanity of key.  Fails if:
            Key length is > SERVER_MAX_KEY_LENGTH (Raises MemcachedKeyLength).
            Contains control characters  (Raises MemcachedKeyCharacterError).
            Is not a string (Raises MemcachedStringEncodingError)
            Is an unicode string (Raises MemcachedStringEncodingError)
            Is not a string (Raises MemcachedKeyError)
            Is None (Raises MemcachedKeyError)
        """
        if isinstance(key, tuple): key = key[1]
        if not key:
            raise Client.MemcachedKeyNoneError("Key is None")
        if isinstance(key, unicode):
            raise Client.MemcachedStringEncodingError(
                    "Keys must be str()'s, not unicode.  Convert your unicode "
                    "strings using mystring.encode(charset)!")
        if not isinstance(key, str):
            raise Client.MemcachedKeyTypeError("Key must be str()'s")

        if isinstance(key, basestring):
            if self.server_max_key_length != 0 and \
                len(key) + key_extra_len > self.server_max_key_length:
                raise Client.MemcachedKeyLengthError("Key length is > %s"
                         % self.server_max_key_length)
            for char in key:
                if ord(char) < 33 or ord(char) == 127:
                    raise Client.MemcachedKeyCharacterError(
                            "Control characters not allowed")

def _doctest():
    import doctest, memcache
    servers = ["127.0.0.1:11211"]
    mc = Client(servers, debug=1)
    globs = {"mc": mc}
    return doctest.testmod(memcache, globs=globs)

if __name__ == "__main__":
    failures = 0
    print "Testing docstrings..."
    _doctest()
    print "Running tests:"
    print
    serverList = [["127.0.0.1:11211"]]
    if '--do-unix' in sys.argv:
        serverList.append([os.path.join(os.getcwd(), 'memcached.socket')])

    for servers in serverList:
        mc = Client(servers, debug=1)

        def to_s(val):
            if not isinstance(val, basestring):
                return "%s (%s)" % (val, type(val))
            return "%s" % val
        def test_setget(key, val):
            global failures
            print "Testing set/get {'%s': %s} ..." % (to_s(key), to_s(val)),
            mc.set(key, val)
            newval = mc.get(key)
            if newval == val:
                print "OK"
                return 1
            else:
                print "FAIL"; failures = failures + 1
                return 0


        class FooStruct(object):
            def __init__(self):
                self.bar = "baz"
            def __str__(self):
                return "A FooStruct"
            def __eq__(self, other):
                if isinstance(other, FooStruct):
                    return self.bar == other.bar
                return 0

        test_setget("a_string", "some random string")
        test_setget("an_integer", 42)
        if test_setget("long", long(1<<30)):
            print "Testing delete ...",
            if mc.delete("long"):
                print "OK"
            else:
                print "FAIL"; failures = failures + 1
            print "Checking results of delete ..."
            if mc.get("long") == None:
                print "OK"
            else:
                print "FAIL"; failures = failures + 1
        print "Testing get_multi ...",
        print mc.get_multi(["a_string", "an_integer"])

        #  removed from the protocol
        #if test_setget("timed_delete", 'foo'):
        #    print "Testing timed delete ...",
        #    if mc.delete("timed_delete", 1):
        #        print "OK"
        #    else:
        #        print "FAIL"; failures = failures + 1
        #    print "Checking results of timed delete ..."
        #    if mc.get("timed_delete") == None:
        #        print "OK"
        #    else:
        #        print "FAIL"; failures = failures + 1

        print "Testing get(unknown value) ...",
        print to_s(mc.get("unknown_value"))

        f = FooStruct()
        test_setget("foostruct", f)

        print "Testing incr ...",
        x = mc.incr("an_integer", 1)
        if x == 43:
            print "OK"
        else:
            print "FAIL"; failures = failures + 1

        print "Testing decr ...",
        x = mc.decr("an_integer", 1)
        if x == 42:
            print "OK"
        else:
            print "FAIL"; failures = failures + 1
        sys.stdout.flush()

        # sanity tests
        print "Testing sending spaces...",
        sys.stdout.flush()
        try:
            x = mc.set("this has spaces", 1)
        except Client.MemcachedKeyCharacterError, msg:
            print "OK"
        else:
            print "FAIL"; failures = failures + 1

        print "Testing sending control characters...",
        try:
            x = mc.set("this\x10has\x11control characters\x02", 1)
        except Client.MemcachedKeyCharacterError, msg:
            print "OK"
        else:
            print "FAIL"; failures = failures + 1

        print "Testing using insanely long key...",
        try:
            x = mc.set('a'*SERVER_MAX_KEY_LENGTH, 1)
        except Client.MemcachedKeyLengthError, msg:
            print "FAIL"; failures = failures + 1
        else:
            print "OK"
        try:
            x = mc.set('a'*SERVER_MAX_KEY_LENGTH + 'a', 1)
        except Client.MemcachedKeyLengthError, msg:
            print "OK"
     

########NEW FILE########
__FILENAME__ = sae_signature

import os
import base64
import hmac
import hashlib

def get_signature(key, msg):
    h = hmac.new(key, msg, hashlib.sha256)
    return base64.b64encode(h.digest())

def get_signatured_headers(headers):
    """Given a list of headers, return a signatured dict
    Becareful of the order of headers when signaturing
    """
    d = {}
    msg = ''
    for k, v in headers:
        d[k] = v
        msg += k + v

    secret = os.environ.get('SECRET_KEY', '')
    d['Signature'] = get_signature(secret, msg)
    return d

########NEW FILE########
__FILENAME__ = storage
#!/usr/bin/env python
# -*-coding: utf8 -*-

""" Dummy SAE Storage API
"""

import os
import errno
import mimetypes
from datetime import datetime
from urllib import quote as _quote

DEFAULT_API_URL = 'https://api.sinas3.com'
ACCESS_KEY = SECRET_KEY = APP_NAME = 'x'
DEFAULT_API_VERSION = 'v1'
DEFAULT_RESELLER_PREFIX = 'SAE_'

class Error(Exception): pass

class AttrDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

def q(value, safe='/'):
    value = encode_utf8(value)
    if isinstance(value, str):
        return _quote(value, safe)
    else:
        return value

def encode_utf8(value):
    if isinstance(value, unicode):
        value = value.encode('utf8')
    return value

class Bucket:
    def __init__(self, bucket, conn=None):
        self.conn = conn if conn else Connection()
        self.bucket = bucket

    _s = """
def %s(self, *args, **kws):
    return self.conn.%s_bucket(self.bucket, *args, **kws)
"""
    for _m in ('put', 'post', 'stat', 'delete', 'list'):
        exec _s % (_m, _m)

    _s = """
def %s(self, *args, **kws):
    return self.conn.%s(self.bucket, *args, **kws)
"""
    for _m in ('get_object', 'get_object_contents', 'put_object',
               'post_object', 'stat_object', 'delete_object',
               'generate_url'):
        exec _s % (_m, _m)

    del _m, _s

class Connection(object):
    def __init__(self, accesskey=ACCESS_KEY, secretkey=SECRET_KEY,
                 account=APP_NAME, retries=3, backoff=0.5,
                 api_url=DEFAULT_API_URL,
                 api_version = DEFAULT_API_VERSION,
                 reseller_prefix=DEFAULT_RESELLER_PREFIX,
                 bucket_class=Bucket):
        if accesskey is None or secretkey is None or account is None:
            raise TypeError(
                '`accesskey` or `secretkey` or `account` is missing')
        self.bucket_class = bucket_class

    def list_bucket(self, bucket, prefix=None, delimiter=None,
                    path=None, limit=10000, marker=None):
        if path:
            prefix = path
            delimiter = '/'
        objs = []
        pth = os.path.normpath(self._get_storage_path(bucket))
        for dpath, dnames, fnames in os.walk(pth):
            rpath = dpath[len(pth)+1:]
            objs.extend([os.path.join(rpath, f) for f in fnames])
        last_subdir = None
        startpos = len(prefix) if delimiter and prefix else 0
        for obj in objs:
            if prefix:
                if not obj.startswith(prefix):
                    continue
            if delimiter:
                endpos = obj.find(delimiter, startpos)
                if endpos != -1:
                    subdir = obj[:endpos+1]
                    if subdir != last_subdir:
                        item = AttrDict()
                        item['bytes'] = None
                        item['content_type'] = None
                        item['hash'] = None
                        item['last_modified'] = None
                        item['name'] = subdir
                        yield item
                        last_subdir = subdir
                    continue
            item = AttrDict()
            item['bytes'] = '12'
            item['content_type'] = 'application/octet-stream'
            item['hash'] = 'x' * 40
            item['last_modified'] = '2013-05-23T03:01:59.051030'
            item['name'] = obj
            yield item

    def stat_bucket(self, bucket):
        attrs = AttrDict()
        attrs['acl'] = '.r:*'
        attrs['bytes'] = '10240'
        attrs['objects'] = '10240'
        attrs['metadata'] = {}
        return attrs

    def get_bucket(self, bucket):
        return self.bucket_class(bucket)

    def put_bucket(self, bucket, acl=None, metadata=None):
        path = self._get_storage_path(bucket)
        try:
            os.mkdir(path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise Error(500, str(e))

    def post_bucket(self, bucket, acl=None, metadata=None):
        pass

    def delete_bucket(self, bucket):
        path = self._get_storage_path(bucket)
        try:
            os.rmdir(path)
        except OSError, e:
            if e.errno == errno.ENOENT:
                raise Error(404, 'Not Found')
            elif e.errno == errno.ENOTEMPTY:
                raise Error(409, 'Confict')
            else:
                raise Error(500, str(e))

    def get_object(self, bucket, obj, chunk_size=None):
        return self.stat_object(bucket, obj), \
                self.get_object_contents(bucket, obj, chunk_size)

    def get_object_contents(self, bucket, obj, chunk_size=None):
        fname = self._get_storage_path(bucket, obj)
        try:
            resp = open(fname, 'rb')
        except IOError, e:
            if e.errno == errno.ENOENT:
                raise Error(404, 'Not Found')
            else:
                raise Error(500, str(e))
        if chunk_size:
            def _body():
                buf = resp.read(chunk_size)
                while buf:
                    yield buf
                    buf = resp.read(chunk_size)
            return _body()
        else:
            return resp.read()

    def stat_object(self, bucket, obj):
        fname = self._get_storage_path(bucket, obj)
        try:
            st = os.stat(fname)
        except OSError, e:
            if e.errno == errno.ENOENT:
                raise Error(404, 'Not Found')
            else:
                raise Error(500, str(e))
        attrs = AttrDict()
        attrs['bytes'] = str(st.st_size)
        attrs['hash'] = 'x'*40
        attrs['last_modified'] = datetime.utcfromtimestamp(
                float(st.st_mtime)).isoformat()
        attrs['content_type'] = mimetypes.guess_type(obj)[0] or \
                                'application/octet-stream'
        attrs['content_encoding'] = None
        attrs['timestamp'] = str(st.st_mtime)
        attrs['metadata'] = {}
        return attrs

    def put_object(self, bucket, obj, contents,
                   content_type=None, content_encoding=None,
                   metadata=None):
        fname = self._get_storage_path(bucket, obj)
        if hasattr(contents, 'read'):
            contents = contents.read()
        try:
            os.makedirs(os.path.dirname(fname))
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise Error(500, str(e))
        try:
            open(fname, 'wb').write(contents)
        except IOError, e:
            raise Error(500, str(e))

    def post_object(self, bucket, obj,
                    content_type=None, content_encoding=None,
                    metadata=None):
        pass

    def generate_url(self, bucket, obj):
        return 'http://%s/stor-stub/%s/%s' % \
            (os.environ['HTTP_HOST'], bucket, q(obj))

    def delete_object(self, bucket, obj):
        fname = self._get_storage_path(bucket, obj)
        try:
            os.unlink(fname)
        except OSError, e:
            if e.errno == errno.ENOENT:
                raise Error(404, 'Not Found')
        bname = self._get_storage_path(bucket)
        fname = os.path.dirname(fname)
        while fname and len(fname) > len(bname):
            try:
                os.rmdir(fname)
            except OSError, e:
                if e.errno == errno.ENOTEMPTY:
                    break
                else:
                    raise Error(500, str(e))
            fname = os.path.dirname(fname)

    _STORAGE_PATH = os.environ.get('sae.storage.path')
    def _get_storage_path(self, *args):
        if not self._STORAGE_PATH:
            raise RuntimeError(
                "Please specify --storage-path in the command line")
        if not os.path.isdir(self._STORAGE_PATH):
            raise RuntimeError(
                "'%s' directory does not exists" % self._STORAGE_PATH)
        return os.path.join(self._STORAGE_PATH, *args)

########NEW FILE########
__FILENAME__ = taskqueue
#!/usr/bin/env python
# -*-coding: utf8 -*-

"""Task Queue API
TaskQueue is a distributed task queue service provided by SAE for developers as
a simple way to execute asynchronous user tasks.

Example:

1. Add a GET task.
    
    from sae.taskqueue import Task, TaskQueue

    queue = TaskQueue('queue_name')
    queue.add(Task("/tasks/cd"))

2. Add a POST task.

    queue.add(Task("/tasks/strip", "postdata"))

3. Add a bundle of tasks.

    tasks = [Task("/tasks/grep", d) for d in datas]
    queue.add(tasks)

4. A simple way to add task.

    from sae.taskqueue import add_task
    add_task('queue_name', '/tasks/fsck', 'postdata')
"""

__all__ = ['Error', 'InternalError', 'InvalidTaskError', 
           'PermissionDeniedError', 'TaskQueueNotExistsError', 
           'TooManyTasksError', 'add_task', 'Task', 'TaskQueue']

import os
import time
import json
import urllib
import urllib2
import urlparse
import base64

import util
import const

class Error(Exception):
    """Base-class for all exception in this module"""

class InvalidTaskError(Error):
    """The task's url, payload, or options is invalid"""

class InternalError(Error):
    """There was an internal error while accessing this queue, it should be 
    temporary, it problem continues, please contact us"""

class PermissionDeniedError(Error):
    """The requested operation is not allowed for this app"""

class TaskQueueNotExistsError(Error):
    """The specified task queue does not exist"""

class TooManyTasksError(Error):
    """Either the taskqueue is Full or the space left's not enough"""

_ERROR_MAPPING = {
    1: PermissionDeniedError, 3: InvalidTaskError, 10: TaskQueueNotExistsError,
    11: TooManyTasksError, 500: InternalError, #999: UnknownError,
    #403: Permission denied or out of quota 
}

_TASKQUEUE_BACKEND = 'http://taskqueue.sae.sina.com.cn/index.php'

class Task:

    _default_netloc = 'http://' + os.environ['HTTP_HOST']

    def __init__(self, url, payload = None, **kwargs):
        """Initializer.

        Args:
          url: URL where the taskqueue daemon should handle this task.
          payload: Optinal, if provided, the taskqueue daemon will take this 
            task as a POST task and |payload| as POST data.
          delay: Delay the execution of the task for certain second(s). Up to
            600 seconds.
          prior: If set to True, the task will be add to the head of the queue.

        Raises:
          InvalidTaskError: if there's a unrecognized argument.
        """
        self.info = {}
        if url.startswith('http://'):
            self.info['url'] = url
        else:
            self.info['url'] = urlparse.urljoin(self._default_netloc, url)
        if payload:
            self.info['postdata'] = base64.b64encode(payload)
                
        for k, v in kwargs.iteritems():
            if k == 'delay':
                self.info['delay'] = v
            elif k == 'prior':
                self.info['prior'] = v
            else:
                raise InvalidTaskError()

    def extract_params(self):
        return self.info

class TaskQueue:

    def __init__(self, name, auth_token=None):
        """Initializer.

        Args:
          name: The name of the taskqueue.
          auth_token: Optional, a two-element tuple (access_key, secretkey_key),
            useful when you want to access other application's taskqueue.
        """
        self.name = name

        if auth_token: 
            self.accesskey_key, self.secret_key = auth_token
        else:
            self.access_key = const.ACCESS_KEY
            self.secret_key = const.SECRET_KEY

    def add(self, task):
        """Add task to the task queue

        Args:
          task: The task to be added, it can be a single Task, or a list of 
            Tasks.
        """
        try:
            tasks = list(iter(task))
        except TypeError:
            tasks = [task]

        task_args = {}
        task_args['name'] = self.name
        task_args['queue'] = []
        for t in tasks:
            task_args['queue'].append(t.extract_params())

        #print task_args
        args = [('taskqueue', json.dumps(task_args))]

        return self._remote_call(args)

    def size(self):
        """Query for how many task is left(not executed) in the queue. """
        args = []
        args.append(('act', 'curlen'))
        args.append(('params', json.dumps({'name': self.name})))
        return int(self._remote_call(args))

    def _remote_call(self, args):
        args_dict = dict(args)

        command = args_dict.get('act')
        if command == 'curlen':
            return "0"

        tasks = json.loads(args_dict['taskqueue'])['queue']
        for t in tasks:
            url = t['url']
            payload = t.get('postdata')

            if payload:
                payload = base64.b64decode(payload)
            print '[SAE:TASKQUEUE] Add task:', url, payload

            #try:
            #    # Try to make a sync call.
            #    rep = urllib2.urlopen(url, payload, 5)
            #    print rep.read()
            #except:
            #    import traceback
            #    print 'TASKQUEUE_ERROR:', t    
            #    traceback.print_exc()

        return True

    def _get_headers(self):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        msg = 'ACCESSKEY' + self.access_key + 'TIMESTAMP' + timestamp
        headers = {'TimeStamp': timestamp,
                   'AccessKey': self.access_key,
                   'Signature': util.get_signature(self.secret_key, msg)}

        return headers

def add_task(queue_name, url, payload=None, **kws):
    """A shortcut for adding task
    
    Args:
      queue_name: The queue's name of which you want the task be added to.
      url: URL where the taskqueue daemon should handle this task.
      payload: The post data if you want to do a POST task.
    """
    TaskQueue(queue_name).add(Task(url, payload, **kws))

########NEW FILE########
__FILENAME__ = util

from sae_signature import get_signature, get_signatured_headers

def half_secret(d, k):
    """Hidden part of the secret"""
    l = len(d[k])
    if l > 2:
        d[k] = d[k][:2] + '*' * (l - 2)
    else:
        d[k] = '*' * l

def protect_secret(d):
    for k, v in d.items():
        if 'KEY' in k:
            half_secret(d, k)

import os.path

def search_file_bottom_up(name):
    curdir = os.getcwd()

    while True:
        path = os.path.join(curdir, name)
        if os.path.isfile(path):
            return curdir
        _curdir = os.path.dirname(curdir)
        if _curdir == curdir:
            return None
        curdir = _curdir


########NEW FILE########
__FILENAME__ = connections
"""

This module implements connections for MySQLdb. Presently there is
only one class: Connection. Others are unlikely. However, you might
want to make your own subclasses. In most cases, you will probably
override Connection.default_cursor with a non-standard Cursor class.

"""
import cursors
from _mysql_exceptions import Warning, Error, InterfaceError, DataError, \
     DatabaseError, OperationalError, IntegrityError, InternalError, \
     NotSupportedError, ProgrammingError
import types, _mysql
import re


def defaulterrorhandler(connection, cursor, errorclass, errorvalue):
    """

    If cursor is not None, (errorclass, errorvalue) is appended to
    cursor.messages; otherwise it is appended to
    connection.messages. Then errorclass is raised with errorvalue as
    the value.

    You can override this with your own error handler by assigning it
    to the instance.

    """
    error = errorclass, errorvalue
    if cursor:
        cursor.messages.append(error)
    else:
        connection.messages.append(error)
    del cursor
    del connection
    raise errorclass, errorvalue

re_numeric_part = re.compile(r"^(\d+)")

def numeric_part(s):
    """Returns the leading numeric part of a string.
    
    >>> numeric_part("20-alpha")
    20
    >>> numeric_part("foo")
    >>> numeric_part("16b")
    16
    """
    
    m = re_numeric_part.match(s)
    if m:
        return int(m.group(1))
    return None


class Connection(_mysql.connection):

    """MySQL Database Connection Object"""

    default_cursor = cursors.Cursor
    
    def __init__(self, *args, **kwargs):
        """

        Create a connection to the database. It is strongly recommended
        that you only use keyword parameters. Consult the MySQL C API
        documentation for more information.

        host
          string, host to connect
          
        user
          string, user to connect as

        passwd
          string, password to use

        db
          string, database to use

        port
          integer, TCP/IP port to connect to

        unix_socket
          string, location of unix_socket to use

        conv
          conversion dictionary, see MySQLdb.converters

        connect_timeout
          number of seconds to wait before the connection attempt
          fails.

        compress
          if set, compression is enabled

        named_pipe
          if set, a named pipe is used to connect (Windows only)

        init_command
          command which is run once the connection is created

        read_default_file
          file from which default client values are read

        read_default_group
          configuration group to use from the default file

        cursorclass
          class object, used to create cursors (keyword only)

        use_unicode
          If True, text-like columns are returned as unicode objects
          using the connection's character set.  Otherwise, text-like
          columns are returned as strings.  columns are returned as
          normal strings. Unicode objects will always be encoded to
          the connection's character set regardless of this setting.

        charset
          If supplied, the connection character set will be changed
          to this character set (MySQL-4.1 and newer). This implies
          use_unicode=True.

        sql_mode
          If supplied, the session SQL mode will be changed to this
          setting (MySQL-4.1 and newer). For more details and legal
          values, see the MySQL documentation.
          
        client_flag
          integer, flags to use or 0
          (see MySQL docs or constants/CLIENTS.py)

        ssl
          dictionary or mapping, contains SSL connection parameters;
          see the MySQL documentation for more details
          (mysql_ssl_set()).  If this is set, and the client does not
          support SSL, NotSupportedError will be raised.

        local_infile
          integer, non-zero enables LOAD LOCAL INFILE; zero disables
    
        There are a number of undocumented, non-standard methods. See the
        documentation for the MySQL C API for some hints on what they do.

        """
        from constants import CLIENT, FIELD_TYPE
        from converters import conversions
        from weakref import proxy, WeakValueDictionary
        
        import types

        kwargs2 = kwargs.copy()
        
        if kwargs.has_key('conv'):
            conv = kwargs['conv']
        else:
            conv = conversions

        conv2 = {}
        for k, v in conv.items():
            if isinstance(k, int) and isinstance(v, list):
                conv2[k] = v[:]
            else:
                conv2[k] = v
        kwargs2['conv'] = conv2

        self.cursorclass = kwargs2.pop('cursorclass', self.default_cursor)
        charset = kwargs2.pop('charset', '')

        if charset:
            use_unicode = True
        else:
            use_unicode = False
            
        use_unicode = kwargs2.pop('use_unicode', use_unicode)
        sql_mode = kwargs2.pop('sql_mode', '')

        client_flag = kwargs.get('client_flag', 0)
        client_version = tuple([ numeric_part(n) for n in _mysql.get_client_info().split('.')[:2] ])
        if client_version >= (4, 1):
            client_flag |= CLIENT.MULTI_STATEMENTS
        if client_version >= (5, 0):
            client_flag |= CLIENT.MULTI_RESULTS
            
        kwargs2['client_flag'] = client_flag

        super(Connection, self).__init__(*args, **kwargs2)

        self.encoders = dict([ (k, v) for k, v in conv.items()
                               if type(k) is not int ])
        
        self._server_version = tuple([ numeric_part(n) for n in self.get_server_info().split('.')[:2] ])

        db = proxy(self)
        def _get_string_literal():
            def string_literal(obj, dummy=None):
                return db.string_literal(obj)
            return string_literal

        def _get_unicode_literal():
            def unicode_literal(u, dummy=None):
                return db.literal(u.encode(unicode_literal.charset))
            return unicode_literal

        def _get_string_decoder():
            def string_decoder(s):
                return s.decode(string_decoder.charset)
            return string_decoder
        
        string_literal = _get_string_literal()
        self.unicode_literal = unicode_literal = _get_unicode_literal()
        self.string_decoder = string_decoder = _get_string_decoder()
        if not charset:
            charset = self.character_set_name()
        self.set_character_set(charset)

        if sql_mode:
            self.set_sql_mode(sql_mode)

        if use_unicode:
            self.converter[FIELD_TYPE.STRING].append((None, string_decoder))
            self.converter[FIELD_TYPE.VAR_STRING].append((None, string_decoder))
            self.converter[FIELD_TYPE.VARCHAR].append((None, string_decoder))
            self.converter[FIELD_TYPE.BLOB].append((None, string_decoder))

        self.encoders[types.StringType] = string_literal
        self.encoders[types.UnicodeType] = unicode_literal
        self._transactional = self.server_capabilities & CLIENT.TRANSACTIONS
        if self._transactional:
            # PEP-249 requires autocommit to be initially off
            self.autocommit(False)
        self.messages = []
        
    def cursor(self, cursorclass=None):
        """

        Create a cursor on which queries may be performed. The
        optional cursorclass parameter is used to create the
        Cursor. By default, self.cursorclass=cursors.Cursor is
        used.

        """
        return (cursorclass or self.cursorclass)(self)

    def __enter__(self): return self.cursor()
    
    def __exit__(self, exc, value, tb):
        if exc:
            self.rollback()
        else:
            self.commit()
            
    def literal(self, o):
        """

        If o is a single object, returns an SQL literal as a string.
        If o is a non-string sequence, the items of the sequence are
        converted and returned as a sequence.

        Non-standard. For internal use; do not use this in your
        applications.

        """
        return self.escape(o, self.encoders)

    def begin(self):
        """Explicitly begin a connection. Non-standard.
        DEPRECATED: Will be removed in 1.3.
        Use an SQL BEGIN statement instead."""
        from warnings import warn
        warn("begin() is non-standard and will be removed in 1.3",
             DeprecationWarning, 2)
        self.query("BEGIN")
        
    if not hasattr(_mysql.connection, 'warning_count'):

        def warning_count(self):
            """Return the number of warnings generated from the
            last query. This is derived from the info() method."""
            from string import atoi
            info = self.info()
            if info:
                return atoi(info.split()[-1])
            else:
                return 0

    def set_character_set(self, charset):
        """Set the connection character set to charset. The character
        set can only be changed in MySQL-4.1 and newer. If you try
        to change the character set from the current value in an
        older version, NotSupportedError will be raised."""
        if self.character_set_name() != charset:
            try:
                super(Connection, self).set_character_set(charset)
            except AttributeError:
                if self._server_version < (4, 1):
                    raise NotSupportedError("server is too old to set charset")
                self.query('SET NAMES %s' % charset)
                self.store_result()
        self.string_decoder.charset = charset
        self.unicode_literal.charset = charset

    def set_sql_mode(self, sql_mode):
        """Set the connection sql_mode. See MySQL documentation for
        legal values."""
        if self._server_version < (4, 1):
            raise NotSupportedError("server is too old to set sql_mode")
        self.query("SET SESSION sql_mode='%s'" % sql_mode)
        self.store_result()
        
    def show_warnings(self):
        """Return detailed information about warnings as a
        sequence of tuples of (Level, Code, Message). This
        is only supported in MySQL-4.1 and up. If your server
        is an earlier version, an empty sequence is returned."""
        if self._server_version < (4,1): return ()
        self.query("SHOW WARNINGS")
        r = self.store_result()
        warnings = r.fetch_row(0)
        return warnings
    
    Warning = Warning
    Error = Error
    InterfaceError = InterfaceError
    DatabaseError = DatabaseError
    DataError = DataError
    OperationalError = OperationalError
    IntegrityError = IntegrityError
    InternalError = InternalError
    ProgrammingError = ProgrammingError
    NotSupportedError = NotSupportedError

    errorhandler = defaulterrorhandler

########NEW FILE########
__FILENAME__ = CLIENT
"""MySQL CLIENT constants

These constants are used when creating the connection. Use bitwise-OR
(|) to combine options together, and pass them as the client_flags
parameter to MySQLdb.Connection. For more information on these flags,
see the MySQL C API documentation for mysql_real_connect().

"""

LONG_PASSWORD = 1
FOUND_ROWS = 2
LONG_FLAG = 4
CONNECT_WITH_DB = 8
NO_SCHEMA = 16
COMPRESS = 32
ODBC = 64
LOCAL_FILES = 128
IGNORE_SPACE = 256
CHANGE_USER = 512
INTERACTIVE = 1024
SSL = 2048
IGNORE_SIGPIPE = 4096
TRANSACTIONS = 8192 # mysql_com.h was WRONG prior to 3.23.35
RESERVED = 16384
SECURE_CONNECTION = 32768
MULTI_STATEMENTS = 65536
MULTI_RESULTS = 131072



########NEW FILE########
__FILENAME__ = CR
"""MySQL Connection Errors

Nearly all of these raise OperationalError. COMMANDS_OUT_OF_SYNC
raises ProgrammingError.

"""

MIN_ERROR = 2000
MAX_ERROR = 2999
UNKNOWN_ERROR = 2000
SOCKET_CREATE_ERROR = 2001
CONNECTION_ERROR = 2002
CONN_HOST_ERROR = 2003
IPSOCK_ERROR = 2004
UNKNOWN_HOST = 2005
SERVER_GONE_ERROR = 2006
VERSION_ERROR = 2007
OUT_OF_MEMORY = 2008
WRONG_HOST_INFO = 2009
LOCALHOST_CONNECTION = 2010
TCP_CONNECTION = 2011
SERVER_HANDSHAKE_ERR = 2012
SERVER_LOST = 2013
COMMANDS_OUT_OF_SYNC = 2014
NAMEDPIPE_CONNECTION = 2015
NAMEDPIPEWAIT_ERROR = 2016
NAMEDPIPEOPEN_ERROR = 2017
NAMEDPIPESETSTATE_ERROR = 2018
CANT_READ_CHARSET = 2019
NET_PACKET_TOO_LARGE = 2020

########NEW FILE########
__FILENAME__ = ER
"""MySQL ER Constants

These constants are error codes for the bulk of the error conditions
that may occur.

"""

HASHCHK = 1000
NISAMCHK = 1001
NO = 1002
YES = 1003
CANT_CREATE_FILE = 1004
CANT_CREATE_TABLE = 1005
CANT_CREATE_DB = 1006
DB_CREATE_EXISTS = 1007
DB_DROP_EXISTS = 1008
DB_DROP_DELETE = 1009
DB_DROP_RMDIR = 1010
CANT_DELETE_FILE = 1011
CANT_FIND_SYSTEM_REC = 1012
CANT_GET_STAT = 1013
CANT_GET_WD = 1014
CANT_LOCK = 1015
CANT_OPEN_FILE = 1016
FILE_NOT_FOUND = 1017
CANT_READ_DIR = 1018
CANT_SET_WD = 1019
CHECKREAD = 1020
DISK_FULL = 1021
DUP_KEY = 1022
ERROR_ON_CLOSE = 1023
ERROR_ON_READ = 1024
ERROR_ON_RENAME = 1025
ERROR_ON_WRITE = 1026
FILE_USED = 1027
FILSORT_ABORT = 1028
FORM_NOT_FOUND = 1029
GET_ERRNO = 1030
ILLEGAL_HA = 1031
KEY_NOT_FOUND = 1032
NOT_FORM_FILE = 1033
NOT_KEYFILE = 1034
OLD_KEYFILE = 1035
OPEN_AS_READONLY = 1036
OUTOFMEMORY = 1037
OUT_OF_SORTMEMORY = 1038
UNEXPECTED_EOF = 1039
CON_COUNT_ERROR = 1040
OUT_OF_RESOURCES = 1041
BAD_HOST_ERROR = 1042
HANDSHAKE_ERROR = 1043
DBACCESS_DENIED_ERROR = 1044
ACCESS_DENIED_ERROR = 1045
NO_DB_ERROR = 1046
UNKNOWN_COM_ERROR = 1047
BAD_NULL_ERROR = 1048
BAD_DB_ERROR = 1049
TABLE_EXISTS_ERROR = 1050
BAD_TABLE_ERROR = 1051
NON_UNIQ_ERROR = 1052
SERVER_SHUTDOWN = 1053
BAD_FIELD_ERROR = 1054
WRONG_FIELD_WITH_GROUP = 1055
WRONG_GROUP_FIELD = 1056
WRONG_SUM_SELECT = 1057
WRONG_VALUE_COUNT = 1058
TOO_LONG_IDENT = 1059
DUP_FIELDNAME = 1060
DUP_KEYNAME = 1061
DUP_ENTRY = 1062
WRONG_FIELD_SPEC = 1063
PARSE_ERROR = 1064
EMPTY_QUERY = 1065
NONUNIQ_TABLE = 1066
INVALID_DEFAULT = 1067
MULTIPLE_PRI_KEY = 1068
TOO_MANY_KEYS = 1069
TOO_MANY_KEY_PARTS = 1070
TOO_LONG_KEY = 1071
KEY_COLUMN_DOES_NOT_EXITS = 1072
BLOB_USED_AS_KEY = 1073
TOO_BIG_FIELDLENGTH = 1074
WRONG_AUTO_KEY = 1075
READY = 1076
NORMAL_SHUTDOWN = 1077
GOT_SIGNAL = 1078
SHUTDOWN_COMPLETE = 1079
FORCING_CLOSE = 1080
IPSOCK_ERROR = 1081
NO_SUCH_INDEX = 1082
WRONG_FIELD_TERMINATORS = 1083
BLOBS_AND_NO_TERMINATED = 1084
TEXTFILE_NOT_READABLE = 1085
FILE_EXISTS_ERROR = 1086
LOAD_INFO = 1087
ALTER_INFO = 1088
WRONG_SUB_KEY = 1089
CANT_REMOVE_ALL_FIELDS = 1090
CANT_DROP_FIELD_OR_KEY = 1091
INSERT_INFO = 1092
INSERT_TABLE_USED = 1093
NO_SUCH_THREAD = 1094
KILL_DENIED_ERROR = 1095
NO_TABLES_USED = 1096
TOO_BIG_SET = 1097
NO_UNIQUE_LOGFILE = 1098
TABLE_NOT_LOCKED_FOR_WRITE = 1099
TABLE_NOT_LOCKED = 1100
BLOB_CANT_HAVE_DEFAULT = 1101
WRONG_DB_NAME = 1102
WRONG_TABLE_NAME = 1103
TOO_BIG_SELECT = 1104
UNKNOWN_ERROR = 1105
UNKNOWN_PROCEDURE = 1106
WRONG_PARAMCOUNT_TO_PROCEDURE = 1107
WRONG_PARAMETERS_TO_PROCEDURE = 1108
UNKNOWN_TABLE = 1109
FIELD_SPECIFIED_TWICE = 1110
INVALID_GROUP_FUNC_USE = 1111
UNSUPPORTED_EXTENSION = 1112
TABLE_MUST_HAVE_COLUMNS = 1113
RECORD_FILE_FULL = 1114
UNKNOWN_CHARACTER_SET = 1115
TOO_MANY_TABLES = 1116
TOO_MANY_FIELDS = 1117
TOO_BIG_ROWSIZE = 1118
STACK_OVERRUN = 1119
WRONG_OUTER_JOIN = 1120
NULL_COLUMN_IN_INDEX = 1121
CANT_FIND_UDF = 1122
CANT_INITIALIZE_UDF = 1123
UDF_NO_PATHS = 1124
UDF_EXISTS = 1125
CANT_OPEN_LIBRARY = 1126
CANT_FIND_DL_ENTRY = 1127
FUNCTION_NOT_DEFINED = 1128
HOST_IS_BLOCKED = 1129
HOST_NOT_PRIVILEGED = 1130
PASSWORD_ANONYMOUS_USER = 1131
PASSWORD_NOT_ALLOWED = 1132
PASSWORD_NO_MATCH = 1133
UPDATE_INFO = 1134
CANT_CREATE_THREAD = 1135
WRONG_VALUE_COUNT_ON_ROW = 1136
CANT_REOPEN_TABLE = 1137
INVALID_USE_OF_NULL = 1138
REGEXP_ERROR = 1139
MIX_OF_GROUP_FUNC_AND_FIELDS = 1140
NONEXISTING_GRANT = 1141
TABLEACCESS_DENIED_ERROR = 1142
COLUMNACCESS_DENIED_ERROR = 1143
ILLEGAL_GRANT_FOR_TABLE = 1144
GRANT_WRONG_HOST_OR_USER = 1145
NO_SUCH_TABLE = 1146
NONEXISTING_TABLE_GRANT = 1147
NOT_ALLOWED_COMMAND = 1148
SYNTAX_ERROR = 1149
DELAYED_CANT_CHANGE_LOCK = 1150
TOO_MANY_DELAYED_THREADS = 1151
ABORTING_CONNECTION = 1152
NET_PACKET_TOO_LARGE = 1153
NET_READ_ERROR_FROM_PIPE = 1154
NET_FCNTL_ERROR = 1155
NET_PACKETS_OUT_OF_ORDER = 1156
NET_UNCOMPRESS_ERROR = 1157
NET_READ_ERROR = 1158
NET_READ_INTERRUPTED = 1159
NET_ERROR_ON_WRITE = 1160
NET_WRITE_INTERRUPTED = 1161
TOO_LONG_STRING = 1162
TABLE_CANT_HANDLE_BLOB = 1163
TABLE_CANT_HANDLE_AUTO_INCREMENT = 1164
DELAYED_INSERT_TABLE_LOCKED = 1165
WRONG_COLUMN_NAME = 1166
WRONG_KEY_COLUMN = 1167
WRONG_MRG_TABLE = 1168
DUP_UNIQUE = 1169
BLOB_KEY_WITHOUT_LENGTH = 1170
PRIMARY_CANT_HAVE_NULL = 1171
TOO_MANY_ROWS = 1172
REQUIRES_PRIMARY_KEY = 1173
NO_RAID_COMPILED = 1174
UPDATE_WITHOUT_KEY_IN_SAFE_MODE = 1175
KEY_DOES_NOT_EXITS = 1176
CHECK_NO_SUCH_TABLE = 1177
CHECK_NOT_IMPLEMENTED = 1178
CANT_DO_THIS_DURING_AN_TRANSACTION = 1179
ERROR_DURING_COMMIT = 1180
ERROR_DURING_ROLLBACK = 1181
ERROR_DURING_FLUSH_LOGS = 1182
ERROR_DURING_CHECKPOINT = 1183
NEW_ABORTING_CONNECTION = 1184
DUMP_NOT_IMPLEMENTED = 1185
FLUSH_MASTER_BINLOG_CLOSED = 1186
INDEX_REBUILD = 1187
MASTER = 1188
MASTER_NET_READ = 1189
MASTER_NET_WRITE = 1190
FT_MATCHING_KEY_NOT_FOUND = 1191
LOCK_OR_ACTIVE_TRANSACTION = 1192
UNKNOWN_SYSTEM_VARIABLE = 1193
CRASHED_ON_USAGE = 1194
CRASHED_ON_REPAIR = 1195
WARNING_NOT_COMPLETE_ROLLBACK = 1196
TRANS_CACHE_FULL = 1197
SLAVE_MUST_STOP = 1198
SLAVE_NOT_RUNNING = 1199
BAD_SLAVE = 1200
MASTER_INFO = 1201
SLAVE_THREAD = 1202
TOO_MANY_USER_CONNECTIONS = 1203
SET_CONSTANTS_ONLY = 1204
LOCK_WAIT_TIMEOUT = 1205
LOCK_TABLE_FULL = 1206
READ_ONLY_TRANSACTION = 1207
DROP_DB_WITH_READ_LOCK = 1208
CREATE_DB_WITH_READ_LOCK = 1209
WRONG_ARGUMENTS = 1210
NO_PERMISSION_TO_CREATE_USER = 1211
UNION_TABLES_IN_DIFFERENT_DIR = 1212
LOCK_DEADLOCK = 1213
TABLE_CANT_HANDLE_FT = 1214
CANNOT_ADD_FOREIGN = 1215
NO_REFERENCED_ROW = 1216
ROW_IS_REFERENCED = 1217
CONNECT_TO_MASTER = 1218
QUERY_ON_MASTER = 1219
ERROR_WHEN_EXECUTING_COMMAND = 1220
WRONG_USAGE = 1221
WRONG_NUMBER_OF_COLUMNS_IN_SELECT = 1222
CANT_UPDATE_WITH_READLOCK = 1223
MIXING_NOT_ALLOWED = 1224
DUP_ARGUMENT = 1225
USER_LIMIT_REACHED = 1226
SPECIFIC_ACCESS_DENIED_ERROR = 1227
LOCAL_VARIABLE = 1228
GLOBAL_VARIABLE = 1229
NO_DEFAULT = 1230
WRONG_VALUE_FOR_VAR = 1231
WRONG_TYPE_FOR_VAR = 1232
VAR_CANT_BE_READ = 1233
CANT_USE_OPTION_HERE = 1234
NOT_SUPPORTED_YET = 1235
MASTER_FATAL_ERROR_READING_BINLOG = 1236
SLAVE_IGNORED_TABLE = 1237
INCORRECT_GLOBAL_LOCAL_VAR = 1238
WRONG_FK_DEF = 1239
KEY_REF_DO_NOT_MATCH_TABLE_REF = 1240
OPERAND_COLUMNS = 1241
SUBQUERY_NO_1_ROW = 1242
UNKNOWN_STMT_HANDLER = 1243
CORRUPT_HELP_DB = 1244
CYCLIC_REFERENCE = 1245
AUTO_CONVERT = 1246
ILLEGAL_REFERENCE = 1247
DERIVED_MUST_HAVE_ALIAS = 1248
SELECT_REDUCED = 1249
TABLENAME_NOT_ALLOWED_HERE = 1250
NOT_SUPPORTED_AUTH_MODE = 1251
SPATIAL_CANT_HAVE_NULL = 1252
COLLATION_CHARSET_MISMATCH = 1253
SLAVE_WAS_RUNNING = 1254
SLAVE_WAS_NOT_RUNNING = 1255
TOO_BIG_FOR_UNCOMPRESS = 1256
ZLIB_Z_MEM_ERROR = 1257
ZLIB_Z_BUF_ERROR = 1258
ZLIB_Z_DATA_ERROR = 1259
CUT_VALUE_GROUP_CONCAT = 1260
WARN_TOO_FEW_RECORDS = 1261
WARN_TOO_MANY_RECORDS = 1262
WARN_NULL_TO_NOTNULL = 1263
WARN_DATA_OUT_OF_RANGE = 1264
WARN_DATA_TRUNCATED = 1265
WARN_USING_OTHER_HANDLER = 1266
CANT_AGGREGATE_2COLLATIONS = 1267
DROP_USER = 1268
REVOKE_GRANTS = 1269
CANT_AGGREGATE_3COLLATIONS = 1270
CANT_AGGREGATE_NCOLLATIONS = 1271
VARIABLE_IS_NOT_STRUCT = 1272
UNKNOWN_COLLATION = 1273
SLAVE_IGNORED_SSL_PARAMS = 1274
SERVER_IS_IN_SECURE_AUTH_MODE = 1275
WARN_FIELD_RESOLVED = 1276
BAD_SLAVE_UNTIL_COND = 1277
MISSING_SKIP_SLAVE = 1278
UNTIL_COND_IGNORED = 1279
WRONG_NAME_FOR_INDEX = 1280
WRONG_NAME_FOR_CATALOG = 1281
WARN_QC_RESIZE = 1282
BAD_FT_COLUMN = 1283
UNKNOWN_KEY_CACHE = 1284
WARN_HOSTNAME_WONT_WORK = 1285
UNKNOWN_STORAGE_ENGINE = 1286
WARN_DEPRECATED_SYNTAX = 1287
NON_UPDATABLE_TABLE = 1288
FEATURE_DISABLED = 1289
OPTION_PREVENTS_STATEMENT = 1290
DUPLICATED_VALUE_IN_TYPE = 1291
TRUNCATED_WRONG_VALUE = 1292
TOO_MUCH_AUTO_TIMESTAMP_COLS = 1293
INVALID_ON_UPDATE = 1294
UNSUPPORTED_PS = 1295
GET_ERRMSG = 1296
GET_TEMPORARY_ERRMSG = 1297
UNKNOWN_TIME_ZONE = 1298
WARN_INVALID_TIMESTAMP = 1299
INVALID_CHARACTER_STRING = 1300
WARN_ALLOWED_PACKET_OVERFLOWED = 1301
CONFLICTING_DECLARATIONS = 1302
SP_NO_RECURSIVE_CREATE = 1303
SP_ALREADY_EXISTS = 1304
SP_DOES_NOT_EXIST = 1305
SP_DROP_FAILED = 1306
SP_STORE_FAILED = 1307
SP_LILABEL_MISMATCH = 1308
SP_LABEL_REDEFINE = 1309
SP_LABEL_MISMATCH = 1310
SP_UNINIT_VAR = 1311
SP_BADSELECT = 1312
SP_BADRETURN = 1313
SP_BADSTATEMENT = 1314
UPDATE_LOG_DEPRECATED_IGNORED = 1315
UPDATE_LOG_DEPRECATED_TRANSLATED = 1316
QUERY_INTERRUPTED = 1317
SP_WRONG_NO_OF_ARGS = 1318
SP_COND_MISMATCH = 1319
SP_NORETURN = 1320
SP_NORETURNEND = 1321
SP_BAD_CURSOR_QUERY = 1322
SP_BAD_CURSOR_SELECT = 1323
SP_CURSOR_MISMATCH = 1324
SP_CURSOR_ALREADY_OPEN = 1325
SP_CURSOR_NOT_OPEN = 1326
SP_UNDECLARED_VAR = 1327
SP_WRONG_NO_OF_FETCH_ARGS = 1328
SP_FETCH_NO_DATA = 1329
SP_DUP_PARAM = 1330
SP_DUP_VAR = 1331
SP_DUP_COND = 1332
SP_DUP_CURS = 1333
SP_CANT_ALTER = 1334
SP_SUBSELECT_NYI = 1335
STMT_NOT_ALLOWED_IN_SF_OR_TRG = 1336
SP_VARCOND_AFTER_CURSHNDLR = 1337
SP_CURSOR_AFTER_HANDLER = 1338
SP_CASE_NOT_FOUND = 1339
FPARSER_TOO_BIG_FILE = 1340
FPARSER_BAD_HEADER = 1341
FPARSER_EOF_IN_COMMENT = 1342
FPARSER_ERROR_IN_PARAMETER = 1343
FPARSER_EOF_IN_UNKNOWN_PARAMETER = 1344
VIEW_NO_EXPLAIN = 1345
FRM_UNKNOWN_TYPE = 1346
WRONG_OBJECT = 1347
NONUPDATEABLE_COLUMN = 1348
VIEW_SELECT_DERIVED = 1349
VIEW_SELECT_CLAUSE = 1350
VIEW_SELECT_VARIABLE = 1351
VIEW_SELECT_TMPTABLE = 1352
VIEW_WRONG_LIST = 1353
WARN_VIEW_MERGE = 1354
WARN_VIEW_WITHOUT_KEY = 1355
VIEW_INVALID = 1356
SP_NO_DROP_SP = 1357
SP_GOTO_IN_HNDLR = 1358
TRG_ALREADY_EXISTS = 1359
TRG_DOES_NOT_EXIST = 1360
TRG_ON_VIEW_OR_TEMP_TABLE = 1361
TRG_CANT_CHANGE_ROW = 1362
TRG_NO_SUCH_ROW_IN_TRG = 1363
NO_DEFAULT_FOR_FIELD = 1364
DIVISION_BY_ZERO = 1365
TRUNCATED_WRONG_VALUE_FOR_FIELD = 1366
ILLEGAL_VALUE_FOR_TYPE = 1367
VIEW_NONUPD_CHECK = 1368
VIEW_CHECK_FAILED = 1369
PROCACCESS_DENIED_ERROR = 1370
RELAY_LOG_FAIL = 1371
PASSWD_LENGTH = 1372
UNKNOWN_TARGET_BINLOG = 1373
IO_ERR_LOG_INDEX_READ = 1374
BINLOG_PURGE_PROHIBITED = 1375
FSEEK_FAIL = 1376
BINLOG_PURGE_FATAL_ERR = 1377
LOG_IN_USE = 1378
LOG_PURGE_UNKNOWN_ERR = 1379
RELAY_LOG_INIT = 1380
NO_BINARY_LOGGING = 1381
RESERVED_SYNTAX = 1382
WSAS_FAILED = 1383
DIFF_GROUPS_PROC = 1384
NO_GROUP_FOR_PROC = 1385
ORDER_WITH_PROC = 1386
LOGGING_PROHIBIT_CHANGING_OF = 1387
NO_FILE_MAPPING = 1388
WRONG_MAGIC = 1389
PS_MANY_PARAM = 1390
KEY_PART_0 = 1391
VIEW_CHECKSUM = 1392
VIEW_MULTIUPDATE = 1393
VIEW_NO_INSERT_FIELD_LIST = 1394
VIEW_DELETE_MERGE_VIEW = 1395
CANNOT_USER = 1396
XAER_NOTA = 1397
XAER_INVAL = 1398
XAER_RMFAIL = 1399
XAER_OUTSIDE = 1400
XAER_RMERR = 1401
XA_RBROLLBACK = 1402
NONEXISTING_PROC_GRANT = 1403
PROC_AUTO_GRANT_FAIL = 1404
PROC_AUTO_REVOKE_FAIL = 1405
DATA_TOO_LONG = 1406
SP_BAD_SQLSTATE = 1407
STARTUP = 1408
LOAD_FROM_FIXED_SIZE_ROWS_TO_VAR = 1409
CANT_CREATE_USER_WITH_GRANT = 1410
WRONG_VALUE_FOR_TYPE = 1411
TABLE_DEF_CHANGED = 1412
SP_DUP_HANDLER = 1413
SP_NOT_VAR_ARG = 1414
SP_NO_RETSET = 1415
CANT_CREATE_GEOMETRY_OBJECT = 1416
FAILED_ROUTINE_BREAK_BINLOG = 1417
BINLOG_UNSAFE_ROUTINE = 1418
BINLOG_CREATE_ROUTINE_NEED_SUPER = 1419
EXEC_STMT_WITH_OPEN_CURSOR = 1420
STMT_HAS_NO_OPEN_CURSOR = 1421
COMMIT_NOT_ALLOWED_IN_SF_OR_TRG = 1422
NO_DEFAULT_FOR_VIEW_FIELD = 1423
SP_NO_RECURSION = 1424
TOO_BIG_SCALE = 1425
TOO_BIG_PRECISION = 1426
M_BIGGER_THAN_D = 1427
WRONG_LOCK_OF_SYSTEM_TABLE = 1428
CONNECT_TO_FOREIGN_DATA_SOURCE = 1429
QUERY_ON_FOREIGN_DATA_SOURCE = 1430
FOREIGN_DATA_SOURCE_DOESNT_EXIST = 1431
FOREIGN_DATA_STRING_INVALID_CANT_CREATE = 1432
FOREIGN_DATA_STRING_INVALID = 1433
CANT_CREATE_FEDERATED_TABLE = 1434
TRG_IN_WRONG_SCHEMA = 1435
STACK_OVERRUN_NEED_MORE = 1436
TOO_LONG_BODY = 1437
WARN_CANT_DROP_DEFAULT_KEYCACHE = 1438
TOO_BIG_DISPLAYWIDTH = 1439
XAER_DUPID = 1440
DATETIME_FUNCTION_OVERFLOW = 1441
CANT_UPDATE_USED_TABLE_IN_SF_OR_TRG = 1442
VIEW_PREVENT_UPDATE = 1443
PS_NO_RECURSION = 1444
SP_CANT_SET_AUTOCOMMIT = 1445
MALFORMED_DEFINER = 1446
VIEW_FRM_NO_USER = 1447
VIEW_OTHER_USER = 1448
NO_SUCH_USER = 1449
FORBID_SCHEMA_CHANGE = 1450
ROW_IS_REFERENCED_2 = 1451
NO_REFERENCED_ROW_2 = 1452
SP_BAD_VAR_SHADOW = 1453
TRG_NO_DEFINER = 1454
OLD_FILE_FORMAT = 1455
SP_RECURSION_LIMIT = 1456
SP_PROC_TABLE_CORRUPT = 1457
ERROR_LAST = 1457


########NEW FILE########
__FILENAME__ = FIELD_TYPE
"""MySQL FIELD_TYPE Constants

These constants represent the various column (field) types that are
supported by MySQL.

"""

DECIMAL = 0
TINY = 1
SHORT = 2
LONG = 3
FLOAT = 4
DOUBLE = 5
NULL = 6
TIMESTAMP = 7
LONGLONG = 8
INT24 = 9
DATE = 10
TIME = 11
DATETIME = 12
YEAR = 13
NEWDATE = 14
VARCHAR = 15
BIT = 16
NEWDECIMAL = 246
ENUM = 247
SET = 248
TINY_BLOB = 249
MEDIUM_BLOB = 250
LONG_BLOB = 251
BLOB = 252
VAR_STRING = 253
STRING = 254
GEOMETRY = 255

CHAR = TINY
INTERVAL = ENUM	

########NEW FILE########
__FILENAME__ = FLAG
"""MySQL FLAG Constants

These flags are used along with the FIELD_TYPE to indicate various
properties of columns in a result set.

"""

NOT_NULL = 1
PRI_KEY = 2
UNIQUE_KEY = 4
MULTIPLE_KEY = 8
BLOB = 16
UNSIGNED = 32
ZEROFILL = 64
BINARY = 128
ENUM = 256
AUTO_INCREMENT = 512
TIMESTAMP = 1024
SET = 2048
NUM = 32768
PART_KEY = 16384
GROUP = 32768
UNIQUE = 65536

########NEW FILE########
__FILENAME__ = REFRESH
"""MySQL REFRESH Constants

These constants seem to mostly deal with things internal to the
MySQL server. Forget you saw this.

"""

GRANT = 1
LOG = 2
TABLES = 4
HOSTS = 8
STATUS = 16
THREADS = 32
SLAVE = 64
MASTER = 128
READ_LOCK = 16384
FAST = 32768

########NEW FILE########
__FILENAME__ = converters
"""MySQLdb type conversion module

This module handles all the type conversions for MySQL. If the default
type conversions aren't what you need, you can make your own. The
dictionary conversions maps some kind of type to a conversion function
which returns the corresponding value:

Key: FIELD_TYPE.* (from MySQLdb.constants)

Conversion function:

    Arguments: string

    Returns: Python object

Key: Python type object (from types) or class

Conversion function:

    Arguments: Python object of indicated type or class AND 
               conversion dictionary

    Returns: SQL literal value

    Notes: Most conversion functions can ignore the dictionary, but
           it is a required parameter. It is necessary for converting
           things like sequences and instances.

Don't modify conversions if you can avoid it. Instead, make copies
(with the copy() method), modify the copies, and then pass them to
MySQL.connect().

"""

from _mysql import string_literal, escape_sequence, escape_dict, escape, NULL
from constants import FIELD_TYPE, FLAG
from times import *
import types
import array

try:
    set
except NameError:
    from sets import Set as set

def Bool2Str(s, d): return str(int(s))

def Str2Set(s):
    return set([ i for i in s.split(',') if i ])

def Set2Str(s, d):
    return string_literal(','.join(s), d)
    
def Thing2Str(s, d):
    """Convert something into a string via str()."""
    return str(s)

def Unicode2Str(s, d):
    """Convert a unicode object to a string using the default encoding.
    This is only used as a placeholder for the real function, which
    is connection-dependent."""
    return s.encode()

Long2Int = Thing2Str

def Float2Str(o, d):
    return '%.15g' % o

def None2NULL(o, d):
    """Convert None to NULL."""
    return NULL # duh

def Thing2Literal(o, d):
    
    """Convert something into a SQL string literal.  If using
    MySQL-3.23 or newer, string_literal() is a method of the
    _mysql.MYSQL object, and this function will be overridden with
    that method when the connection is created."""

    return string_literal(o, d)


def Instance2Str(o, d):

    """

    Convert an Instance to a string representation.  If the __str__()
    method produces acceptable output, then you don't need to add the
    class to conversions; it will be handled by the default
    converter. If the exact class is not found in d, it will use the
    first class it can find for which o is an instance.

    """

    if d.has_key(o.__class__):
        return d[o.__class__](o, d)
    cl = filter(lambda x,o=o:
                type(x) is types.ClassType
                and isinstance(o, x), d.keys())
    if not cl and hasattr(types, 'ObjectType'):
        cl = filter(lambda x,o=o:
                    type(x) is types.TypeType
                    and isinstance(o, x)
                    and d[x] is not Instance2Str,
                    d.keys())
    if not cl:
        return d[types.StringType](o,d)
    d[o.__class__] = d[cl[0]]
    return d[cl[0]](o, d)

def char_array(s):
    return array.array('c', s)

def array2Str(o, d):
    return Thing2Literal(o.tostring(), d)

conversions = {
    types.IntType: Thing2Str,
    types.LongType: Long2Int,
    types.FloatType: Float2Str,
    types.NoneType: None2NULL,
    types.TupleType: escape_sequence,
    types.ListType: escape_sequence,
    types.DictType: escape_dict,
    types.InstanceType: Instance2Str,
    array.ArrayType: array2Str,
    types.StringType: Thing2Literal, # default
    types.UnicodeType: Unicode2Str,
    types.ObjectType: Instance2Str,
    types.BooleanType: Bool2Str,
    DateTimeType: DateTime2literal,
    DateTimeDeltaType: DateTimeDelta2literal,
    set: Set2Str,
    FIELD_TYPE.TINY: int,
    FIELD_TYPE.SHORT: int,
    FIELD_TYPE.LONG: long,
    FIELD_TYPE.FLOAT: float,
    FIELD_TYPE.DOUBLE: float,
    FIELD_TYPE.DECIMAL: float,
    FIELD_TYPE.NEWDECIMAL: float,
    FIELD_TYPE.LONGLONG: long,
    FIELD_TYPE.INT24: int,
    FIELD_TYPE.YEAR: int,
    FIELD_TYPE.SET: Str2Set,
    FIELD_TYPE.TIMESTAMP: mysql_timestamp_converter,
    FIELD_TYPE.DATETIME: DateTime_or_None,
    FIELD_TYPE.TIME: TimeDelta_or_None,
    FIELD_TYPE.DATE: Date_or_None,
    FIELD_TYPE.BLOB: [
        (FLAG.BINARY, str),
        ],
    FIELD_TYPE.STRING: [
        (FLAG.BINARY, str),
        ],
    FIELD_TYPE.VAR_STRING: [
        (FLAG.BINARY, str),
        ],
    FIELD_TYPE.VARCHAR: [
        (FLAG.BINARY, str),
        ],
    }

try:
    from decimal import Decimal
    conversions[FIELD_TYPE.DECIMAL] = Decimal
    conversions[FIELD_TYPE.NEWDECIMAL] = Decimal
except ImportError:
    pass




########NEW FILE########
__FILENAME__ = cursors
"""MySQLdb Cursors

This module implements Cursors of various types for MySQLdb. By
default, MySQLdb uses the Cursor class.

"""

import re
import sys
from types import ListType, TupleType, UnicodeType


restr = (r"\svalues\s*"
        r"(\(((?<!\\)'[^\)]*?\)[^\)]*(?<!\\)?'"
        r"|[^\(\)]|"
        r"(?:\([^\)]*\))"
        r")+\))")

insert_values= re.compile(restr)
from _mysql_exceptions import Warning, Error, InterfaceError, DataError, \
     DatabaseError, OperationalError, IntegrityError, InternalError, \
     NotSupportedError, ProgrammingError


class BaseCursor(object):
    
    """A base for Cursor classes. Useful attributes:
    
    description
        A tuple of DB API 7-tuples describing the columns in
        the last executed query; see PEP-249 for details.

    description_flags
        Tuple of column flags for last query, one entry per column
        in the result set. Values correspond to those in
        MySQLdb.constants.FLAG. See MySQL documentation (C API)
        for more information. Non-standard extension.
    
    arraysize
        default number of rows fetchmany() will fetch

    """

    from _mysql_exceptions import MySQLError, Warning, Error, InterfaceError, \
         DatabaseError, DataError, OperationalError, IntegrityError, \
         InternalError, ProgrammingError, NotSupportedError
    
    _defer_warnings = False
    
    def __init__(self, connection):
        from weakref import proxy
    
        self.connection = proxy(connection)
        self.description = None
        self.description_flags = None
        self.rowcount = -1
        self.arraysize = 1
        self._executed = None
        self.lastrowid = None
        self.messages = []
        self.errorhandler = connection.errorhandler
        self._result = None
        self._warnings = 0
        self._info = None
        self.rownumber = None
        
    def __del__(self):
        self.close()
        self.errorhandler = None
        self._result = None

    def close(self):
        """Close the cursor. No further queries will be possible."""
        if not self.connection: return
        while self.nextset(): pass
        self.connection = None

    def _check_executed(self):
        if not self._executed:
            self.errorhandler(self, ProgrammingError, "execute() first")

    def _warning_check(self):
        from warnings import warn
        if self._warnings:
            warnings = self._get_db().show_warnings()
            if warnings:
                # This is done in two loops in case
                # Warnings are set to raise exceptions.
                for w in warnings:
                    self.messages.append((self.Warning, w))
                for w in warnings:
                    warn(w[-1], self.Warning, 3)
            elif self._info:
                self.messages.append((self.Warning, self._info))
                warn(self._info, self.Warning, 3)

    def nextset(self):
        """Advance to the next result set.

        Returns None if there are no more result sets.
        """
        if self._executed:
            self.fetchall()
        del self.messages[:]
        
        db = self._get_db()
        nr = db.next_result()
        if nr == -1:
            return None
        self._do_get_result()
        self._post_get_result()
        self._warning_check()
        return 1

    def _post_get_result(self): pass
    
    def _do_get_result(self):
        db = self._get_db()
        self._result = self._get_result()
        self.rowcount = db.affected_rows()
        self.rownumber = 0
        self.description = self._result and self._result.describe() or None
        self.description_flags = self._result and self._result.field_flags() or None
        self.lastrowid = db.insert_id()
        self._warnings = db.warning_count()
        self._info = db.info()
    
    def setinputsizes(self, *args):
        """Does nothing, required by DB API."""
      
    def setoutputsizes(self, *args):
        """Does nothing, required by DB API."""

    def _get_db(self):
        if not self.connection:
            self.errorhandler(self, ProgrammingError, "cursor closed")
        return self.connection
    
    def execute(self, query, args=None):

        """Execute a query.
        
        query -- string, query to execute on server
        args -- optional sequence or mapping, parameters to use with query.

        Note: If args is a sequence, then %s must be used as the
        parameter placeholder in the query. If a mapping is used,
        %(key)s must be used as the placeholder.

        Returns long integer rows affected, if any

        """
        del self.messages[:]
        db = self._get_db()
        charset = db.character_set_name()
        if isinstance(query, unicode):
            query = query.encode(charset)
        if args is not None:
            query = query % db.literal(args)
        try:
            r = self._query(query)
        except TypeError, m:
            if m.args[0] in ("not enough arguments for format string",
                             "not all arguments converted"):
                self.messages.append((ProgrammingError, m.args[0]))
                self.errorhandler(self, ProgrammingError, m.args[0])
            else:
                self.messages.append((TypeError, m))
                self.errorhandler(self, TypeError, m)
        except:
            exc, value, tb = sys.exc_info()
            del tb
            self.messages.append((exc, value))
            self.errorhandler(self, exc, value)
        self._executed = query
        if not self._defer_warnings: self._warning_check()
        return r

    def executemany(self, query, args):

        """Execute a multi-row query.
        
        query -- string, query to execute on server

        args

            Sequence of sequences or mappings, parameters to use with
            query.
            
        Returns long integer rows affected, if any.
        
        This method improves performance on multiple-row INSERT and
        REPLACE. Otherwise it is equivalent to looping over args with
        execute().

        """
        del self.messages[:]
        db = self._get_db()
        if not args: return
        charset = db.character_set_name()
        if isinstance(query, unicode): query = query.encode(charset)
        m = insert_values.search(query)
        if not m:
            r = 0
            for a in args:
                r = r + self.execute(query, a)
            return r
        p = m.start(1)
        e = m.end(1)
        qv = m.group(1)
        try:
            q = [ qv % db.literal(a) for a in args ]
        except TypeError, msg:
            if msg.args[0] in ("not enough arguments for format string",
                               "not all arguments converted"):
                self.errorhandler(self, ProgrammingError, msg.args[0])
            else:
                self.errorhandler(self, TypeError, msg)
        except:
            exc, value, tb = sys.exc_info()
            del tb
            self.errorhandler(self, exc, value)
        r = self._query('\n'.join([query[:p], ',\n'.join(q), query[e:]]))
        if not self._defer_warnings: self._warning_check()
        return r
    
    def callproc(self, procname, args=()):

        """Execute stored procedure procname with args
        
        procname -- string, name of procedure to execute on server

        args -- Sequence of parameters to use with procedure

        Returns the original args.

        Compatibility warning: PEP-249 specifies that any modified
        parameters must be returned. This is currently impossible
        as they are only available by storing them in a server
        variable and then retrieved by a query. Since stored
        procedures return zero or more result sets, there is no
        reliable way to get at OUT or INOUT parameters via callproc.
        The server variables are named @_procname_n, where procname
        is the parameter above and n is the position of the parameter
        (from zero). Once all result sets generated by the procedure
        have been fetched, you can issue a SELECT @_procname_0, ...
        query using .execute() to get any OUT or INOUT values.

        Compatibility warning: The act of calling a stored procedure
        itself creates an empty result set. This appears after any
        result sets generated by the procedure. This is non-standard
        behavior with respect to the DB-API. Be sure to use nextset()
        to advance through all result sets; otherwise you may get
        disconnected.
        """

        db = self._get_db()
        charset = db.character_set_name()
        for index, arg in enumerate(args):
            q = "SET @_%s_%d=%s" % (procname, index,
                                         db.literal(arg))
            if isinstance(q, unicode):
                q = q.encode(charset)
            self._query(q)
            self.nextset()
            
        q = "CALL %s(%s)" % (procname,
                             ','.join(['@_%s_%d' % (procname, i)
                                       for i in range(len(args))]))
        if type(q) is UnicodeType:
            q = q.encode(charset)
        self._query(q)
        self._executed = q
        if not self._defer_warnings: self._warning_check()
        return args
    
    def _do_query(self, q):
        db = self._get_db()
        self._last_executed = q
        db.query(q)
        self._do_get_result()
        return self.rowcount

    def _query(self, q): return self._do_query(q)
    
    def _fetch_row(self, size=1):
        if not self._result:
            return ()
        return self._result.fetch_row(size, self._fetch_type)

    def __iter__(self):
        return iter(self.fetchone, None)

    Warning = Warning
    Error = Error
    InterfaceError = InterfaceError
    DatabaseError = DatabaseError
    DataError = DataError
    OperationalError = OperationalError
    IntegrityError = IntegrityError
    InternalError = InternalError
    ProgrammingError = ProgrammingError
    NotSupportedError = NotSupportedError
   

class CursorStoreResultMixIn(object):

    """This is a MixIn class which causes the entire result set to be
    stored on the client side, i.e. it uses mysql_store_result(). If the
    result set can be very large, consider adding a LIMIT clause to your
    query, or using CursorUseResultMixIn instead."""

    def _get_result(self): return self._get_db().store_result()

    def _query(self, q):
        rowcount = self._do_query(q)
        self._post_get_result()
        return rowcount

    def _post_get_result(self):
        self._rows = self._fetch_row(0)
        self._result = None

    def fetchone(self):
        """Fetches a single row from the cursor. None indicates that
        no more rows are available."""
        self._check_executed()
        if self.rownumber >= len(self._rows): return None
        result = self._rows[self.rownumber]
        self.rownumber = self.rownumber+1
        return result

    def fetchmany(self, size=None):
        """Fetch up to size rows from the cursor. Result set may be smaller
        than size. If size is not defined, cursor.arraysize is used."""
        self._check_executed()
        end = self.rownumber + (size or self.arraysize)
        result = self._rows[self.rownumber:end]
        self.rownumber = min(end, len(self._rows))
        return result

    def fetchall(self):
        """Fetchs all available rows from the cursor."""
        self._check_executed()
        if self.rownumber:
            result = self._rows[self.rownumber:]
        else:
            result = self._rows
        self.rownumber = len(self._rows)
        return result
    
    def scroll(self, value, mode='relative'):
        """Scroll the cursor in the result set to a new position according
        to mode.
        
        If mode is 'relative' (default), value is taken as offset to
        the current position in the result set, if set to 'absolute',
        value states an absolute target position."""
        self._check_executed()
        if mode == 'relative':
            r = self.rownumber + value
        elif mode == 'absolute':
            r = value
        else:
            self.errorhandler(self, ProgrammingError,
                              "unknown scroll mode %s" % `mode`)
        if r < 0 or r >= len(self._rows):
            self.errorhandler(self, IndexError, "out of range")
        self.rownumber = r

    def __iter__(self):
        self._check_executed()
        result = self.rownumber and self._rows[self.rownumber:] or self._rows
        return iter(result)
    

class CursorUseResultMixIn(object):

    """This is a MixIn class which causes the result set to be stored
    in the server and sent row-by-row to client side, i.e. it uses
    mysql_use_result(). You MUST retrieve the entire result set and
    close() the cursor before additional queries can be peformed on
    the connection."""

    _defer_warnings = True
    
    def _get_result(self): return self._get_db().use_result()

    def fetchone(self):
        """Fetches a single row from the cursor."""
        self._check_executed()
        r = self._fetch_row(1)
        if not r:
            self._warning_check()
            return None
        self.rownumber = self.rownumber + 1
        return r[0]
             
    def fetchmany(self, size=None):
        """Fetch up to size rows from the cursor. Result set may be smaller
        than size. If size is not defined, cursor.arraysize is used."""
        self._check_executed()
        r = self._fetch_row(size or self.arraysize)
        self.rownumber = self.rownumber + len(r)
        if not r:
            self._warning_check()
        return r
         
    def fetchall(self):
        """Fetchs all available rows from the cursor."""
        self._check_executed()
        r = self._fetch_row(0)
        self.rownumber = self.rownumber + len(r)
        self._warning_check()
        return r

    def __iter__(self):
        return self

    def next(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row
    

class CursorTupleRowsMixIn(object):

    """This is a MixIn class that causes all rows to be returned as tuples,
    which is the standard form required by DB API."""

    _fetch_type = 0


class CursorDictRowsMixIn(object):

    """This is a MixIn class that causes all rows to be returned as
    dictionaries. This is a non-standard feature."""

    _fetch_type = 1

    def fetchoneDict(self):
        """Fetch a single row as a dictionary. Deprecated:
        Use fetchone() instead. Will be removed in 1.3."""
        from warnings import warn
        warn("fetchoneDict() is non-standard and will be removed in 1.3",
             DeprecationWarning, 2)
        return self.fetchone()

    def fetchmanyDict(self, size=None):
        """Fetch several rows as a list of dictionaries. Deprecated:
        Use fetchmany() instead. Will be removed in 1.3."""
        from warnings import warn
        warn("fetchmanyDict() is non-standard and will be removed in 1.3",
             DeprecationWarning, 2)
        return self.fetchmany(size)

    def fetchallDict(self):
        """Fetch all available rows as a list of dictionaries. Deprecated:
        Use fetchall() instead. Will be removed in 1.3."""
        from warnings import warn
        warn("fetchallDict() is non-standard and will be removed in 1.3",
             DeprecationWarning, 2)
        return self.fetchall()


class CursorOldDictRowsMixIn(CursorDictRowsMixIn):

    """This is a MixIn class that returns rows as dictionaries with
    the same key convention as the old Mysqldb (MySQLmodule). Don't
    use this."""

    _fetch_type = 2


class Cursor(CursorStoreResultMixIn, CursorTupleRowsMixIn,
             BaseCursor):

    """This is the standard Cursor class that returns rows as tuples
    and stores the result set in the client."""


class DictCursor(CursorStoreResultMixIn, CursorDictRowsMixIn,
                 BaseCursor):

     """This is a Cursor class that returns rows as dictionaries and
    stores the result set in the client."""
   

class SSCursor(CursorUseResultMixIn, CursorTupleRowsMixIn,
               BaseCursor):

    """This is a Cursor class that returns rows as tuples and stores
    the result set in the server."""


class SSDictCursor(CursorUseResultMixIn, CursorDictRowsMixIn,
                   BaseCursor):

    """This is a Cursor class that returns rows as dictionaries and
    stores the result set in the server."""



########NEW FILE########
__FILENAME__ = monkey

# Copyright (C) 2012-2013 SINA, All rights reserved.

def patch():
    import sys

    if  'MySQLdb' in sys.modules:
        import warnings
        warnings.warn('MySQLdb has alreay been imported', Warning)

    modules_to_replace = (
        'MySQLdb',
        'MySQLdb.release',
        'MySQLdb.connections',
        'MySQLdb.cursors',
        'MySQLdb.converters',
        'MySQLdb.constants',
        'MySQLdb.constants.CLIENT',
        'MySQLdb.constants.FIELD_TYPE',
        'MySQLdb.constants.FLAG',
    )

    for name in modules_to_replace:
        if name in sys.modules:
            sys.modules.pop(name)

    import sae._restful_mysql
    from sae._restful_mysql import _mysql, _mysql_exceptions
    sys.modules['MySQLdb'] = sae._restful_mysql
    sys.modules['_mysql'] = _mysql
    sys.modules['_mysql_exceptions'] = _mysql_exceptions

########NEW FILE########
__FILENAME__ = release

__author__ = "Andy Dustman <adustman@users.sourceforge.net>"
version_info = (1,2,3,'final',0)
__version__ = "1.2.3"

########NEW FILE########
__FILENAME__ = times
"""times module

This module provides some Date and Time classes for dealing with MySQL data.

Use Python datetime module to handle date and time columns."""

import math
from time import localtime
from datetime import date, datetime, time, timedelta
from _mysql import string_literal

Date = date
Time = time
TimeDelta = timedelta
Timestamp = datetime

DateTimeDeltaType = timedelta
DateTimeType = datetime

def DateFromTicks(ticks):
    """Convert UNIX ticks into a date instance."""
    return date(*localtime(ticks)[:3])

def TimeFromTicks(ticks):
    """Convert UNIX ticks into a time instance."""
    return time(*localtime(ticks)[3:6])

def TimestampFromTicks(ticks):
    """Convert UNIX ticks into a datetime instance."""
    return datetime(*localtime(ticks)[:6])

format_TIME = format_DATE = str

def format_TIMEDELTA(v):
    seconds = int(v.seconds) % 60
    minutes = int(v.seconds / 60) % 60
    hours = int(v.seconds / 3600) % 24
    return '%d %d:%d:%d' % (v.days, hours, minutes, seconds)

def format_TIMESTAMP(d):
    return d.strftime("%Y-%m-%d %H:%M:%S")


def DateTime_or_None(s):
    if ' ' in s:
        sep = ' '
    elif 'T' in s:
        sep = 'T'
    else:
        return Date_or_None(s)

    try:
        d, t = s.split(sep, 1)
        return datetime(*[ int(x) for x in d.split('-')+t.split(':') ])
    except:
        return Date_or_None(s)

def TimeDelta_or_None(s):
    try:
        h, m, s = s.split(':')
        h, m, s = int(h), int(m), float(s)
        td = timedelta(hours=abs(h), minutes=m, seconds=int(s),
                       microseconds=int(math.modf(s)[0] * 1000000))
        if h < 0:
            return -td
        else:
            return td
    except ValueError:
        # unpacking or int/float conversion failed
        return None

def Time_or_None(s):
    try:
        h, m, s = s.split(':')
        h, m, s = int(h), int(m), float(s)
        return time(hour=h, minute=m, second=int(s),
                    microsecond=int(math.modf(s)[0] * 1000000))
    except ValueError:
        return None

def Date_or_None(s):
    try: return date(*[ int(x) for x in s.split('-',2)])
    except: return None

def DateTime2literal(d, c):
    """Format a DateTime object as an ISO timestamp."""
    return string_literal(format_TIMESTAMP(d),c)
    
def DateTimeDelta2literal(d, c):
    """Format a DateTimeDelta object as a time."""
    return string_literal(format_TIMEDELTA(d),c)

def mysql_timestamp_converter(s):
    """Convert a MySQL TIMESTAMP to a Timestamp object."""
    # MySQL>4.1 returns TIMESTAMP in the same format as DATETIME
    if s[4] == '-': return DateTime_or_None(s)
    s = s + "0"*(14-len(s)) # padding
    parts = map(int, filter(None, (s[:4],s[4:6],s[6:8],
                                   s[8:10],s[10:12],s[12:14])))
    try: return Timestamp(*parts)
    except: return None

########NEW FILE########
__FILENAME__ = _mysql

# Copyright (C) 2012-2013 SINA, All rights reserved.

from _mysql_exceptions import *

"""An proxy for the MySQL C API
Translate the _mysql C API call into restfull call
"""

import types
import pickle
import urllib2

from release import __version__, version_info

import logging
logger = logging.getLogger('sae._mysql')

NULL = 'NULL'
_SAE_MYSQL_API_BACKEND = 'http://2.python.sinaapp.com/api/mysql/'

# refs:
# http://www.python.org/dev/peps/pep-0249
# http://mysql-python.sourceforge.net/MySQLdb.html#mysql

class connection(object):
    def __init__(self, *args, **kwargs):
        self.converter = kwargs.pop('conv', {})
        self._conn_args = args
        self._conn_kwargs = kwargs
        self._conn_id = None
        self._rows = None
        self._description = None
        self._description_flags = None
        self._rowcount = None
        self._warnings = None
        self._info = None
        self._lastrowid = None
        self._open_connection()

    def open(self):
        pass

    def close(self):
        self._conn_id = None

    def shutdown(self):
        pass

    def select_db(self, *args):
        self._request('select_db', args)

    def change_user(self):
        pass

    def character_set_name(self):
        if not hasattr(self, '_charset'):
            self._charset = self._request('character_set_name')
        return self._charset

    def set_character_set(self, charset):
        if getattr(self, '_charset', None) != charset:
            self._request('set_character_set', charset)
        self._charset = charset

    def set_server_option(self, *args, **kws):
        logging.warning('Ignored set_server_option: %s, %s', args, kws)

    def query(self, query):
        retval = self._request('query', query=query)
        self._rows = retval['rows']
        self._description = retval['description']
        self._description_flags = retval['description_flags']
        self._rowcount = retval['rowcount']
        self._warnings = retval['warnings']
        self._info = retval['info']
        self._lastrowid = retval['lastrowid']

    def commit(self):
        pass

    def rollback(self):
        pass

    def autocommit(self, value):
        pass

    def use_result(self):
        return self.store_result()

    def store_result(self):
        if self._rows:
            return StoreResult(self, self._rows, self.converter,
                               self._description, self._description_flags)
        else:
            return None

    def next_result(self, *args, **kws):
        # TODO
        return -1

    def affected_rows(self):
        return self._rowcount

    def insert_id(self):
        return self._lastrowid

    def info(self):
        return self._info

    def get_host_info(self):
        return self._host_info

    def get_proto_info(self):
        return self._proto_info

    def get_server_info(self):
        return self._server_info

    def ping(self):
        pass

    def escape(self, item, dct=None):
        return escape(item, dct or self.converter)
        
    def escape_string(self, str):
        return escape_string(str)

    def string_literal(self, obj):
        return '\'%s\'' % escape_string(str(obj)) 

    def _open_connection(self):
        retval = self._request('open', *self._conn_args, **self._conn_kwargs)
        self._conn_id = retval['connection_id']
        self._host_info = retval['host_info']
        self._proto_info = retval['proto_info']
        self._server_info = retval['server_info']
        self.server_capabilities = retval['server_capabilities']

    def _request(self, op, *args, **kwargs):
        req = {
            'connection_id': self._conn_id,
            'op': op, 'args': args, 'kwargs': kwargs
        }
        logger.debug('REQ: %s', req)
        payload = pickle.dumps(req)
        body = urllib2.urlopen(_SAE_MYSQL_API_BACKEND, payload).read()
        rep = pickle.loads(body)
        logger.debug('REP: %s', rep)
        if rep.get('sql_exception'):
            raise rep.get('sql_exception')
        return rep.get('result')

def _mysql_rows_to_python(rows, conv, field_info, how):
    def row_to_python0(row):
        nrow = []
        for i, v in enumerate(row):
            # XXX: NULL is always converted to None, so here we
            # do not need to do it again.
            nrow.append(None if v is None else conv[i](v))
        return tuple(nrow)
    def row_to_python1(row):
        nrow = {}
        for i, v in enumerate(row):
            # XXX: NULL is always converted to None, so here we
            # do not need to do it again.
            nrow[field_info[i][0]] = None if v is None else conv[i](v)
        return nrow
    if how:
        return tuple(row_to_python1(r) for r in rows)
    else:
        return tuple(row_to_python0(r) for r in rows)

class StoreResult:
    def __init__(self, conn, rows, conv, description, description_flags):
        self.conn = conn
        self.current = 0
        self.description = description
        self.description_flags = description_flags
        self._cached = rows
        self._init_conv(conv)

    def _init_conv(self, conv):
        # _mysql.c:_mysql_ResultObject_Initialize
        self.converter = []
        for n, i in enumerate(self.description):
            c = conv.get(i[1], str)     # search by field.type
            if isinstance(c, list):
                nc = None
                mask = self.description_flags[n]
                for j in c:
                    if isinstance(j[0], int):
                        if mask & j[0]: # search by field.flags
                            nc = j[1]
                            break
                    else:
                        nc = j[1]
                        break           # wildcard
                c = nc if nc is not None else str
            self.converter.append(c)

    def fetch_row(self, maxrows=1, how=0):
        if maxrows == 0:
            retval = self._cached
            self._cached = ()
        else:
            retval = self._cached[self.current:maxrows]
            self.current += maxrows
        return _mysql_rows_to_python(retval, self.converter, self.description, how)

    def describe(self):
        return self.description

    def field_flags(self):
        return self.description_flags

connect = connection

def get_client_info():
    return '5.1.67'


def escape(item, dct):
    return _escape_item(item, dct)
    
def _escape_item(val, dct):
    d = dct.get(type(val)) or dct.get(types.StringType)
    return d(val, dct)

# Copied from pymysql
# See: https://github.com/petehunt/PyMySQL/blob/master/pymysql/converters.py
import re
ESCAPE_REGEX = re.compile(r"[\0\n\r\032\'\"\\]", re.IGNORECASE)
def escape_string(value):
    def rep(m):
        n = m.group(0)
        if n == "\0":
            return "\\0"
        elif n == "\n":
            return "\\n"
        elif n == "\r":
            return "\\r"
        elif n == "\032":
            return "\\Z"
        else:
            return "\\"+n
    s = re.sub(ESCAPE_REGEX, rep, value)
    return s

def string_literal(obj):
    return '\'%s\'' % escape_string(str(obj)) 

def escape_dict(val, dct):
    n = {}
    for k, v in val.items():
        quoted = _escape_item(v)
        n[k] = quoted
    return n

def escape_sequence(val, dct):
    return tuple(_escape_item(v, dct) for v in val)

########NEW FILE########
__FILENAME__ = _mysql_exceptions
"""_mysql_exceptions: Exception classes for _mysql and MySQLdb.

These classes are dictated by the DB API v2.0:

    http://www.python.org/topics/database/DatabaseAPI-2.0.html
"""

from exceptions import Exception, StandardError, Warning

class MySQLError(StandardError):
    
    """Exception related to operation with MySQL."""


class Warning(Warning, MySQLError):

    """Exception raised for important warnings like data truncations
    while inserting, etc."""

class Error(MySQLError):

    """Exception that is the base class of all other error exceptions
    (not Warning)."""


class InterfaceError(Error):

    """Exception raised for errors that are related to the database
    interface rather than the database itself."""


class DatabaseError(Error):

    """Exception raised for errors that are related to the
    database."""


class DataError(DatabaseError):

    """Exception raised for errors that are due to problems with the
    processed data like division by zero, numeric value out of range,
    etc."""


class OperationalError(DatabaseError):

    """Exception raised for errors that are related to the database's
    operation and not necessarily under the control of the programmer,
    e.g. an unexpected disconnect occurs, the data source name is not
    found, a transaction could not be processed, a memory allocation
    error occurred during processing, etc."""


class IntegrityError(DatabaseError):

    """Exception raised when the relational integrity of the database
    is affected, e.g. a foreign key check fails, duplicate key,
    etc."""


class InternalError(DatabaseError):

    """Exception raised when the database encounters an internal
    error, e.g. the cursor is not valid anymore, the transaction is
    out of sync, etc."""


class ProgrammingError(DatabaseError):

    """Exception raised for programming errors, e.g. table not found
    or already exists, syntax error in the SQL statement, wrong number
    of parameters specified, etc."""


class NotSupportedError(DatabaseError):

    """Exception raised in case a method or database API was used
    which is not supported by the database, e.g. requesting a
    .rollback() on a connection that does not support transaction or
    has transactions turned off."""


del Exception, StandardError

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# SAE Python References documentation build configuration file, created by
# sphinx-quickstart on Fri Sep 23 11:25:19 2011.
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
sys.path.insert(0, os.path.abspath('../../Lib/'))
sys.path.insert(0, os.path.abspath('exts'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.todo', 'sphinx.ext.ifconfig']
extensions += ['chinese_search',]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u"SAE Python Developer's Guide"
copyright = u'2011, SAE Python Team'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0(beta)'

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

html_search_language = 'zh_CN'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['theme']

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
html_static_path = ['static']

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
htmlhelp_basename = 'SAEPythonReferencesdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'SAEPythonReferences.tex', u'SAE Python References Documentation',
   u'SAE Python Team', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'saepythonreferences', u'SAE Python References Documentation',
     [u'SAE Python Team'], 1)
]


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'SAE Python References'
epub_author = u'SAE Python Team'
epub_publisher = u'SAE Python Team'
epub_copyright = u'2011, SAE Python Team'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

########NEW FILE########
__FILENAME__ = chinese_search
from sphinx.search import SearchLanguage
import jieba

class SearchChinese(SearchLanguage):
    lang = 'zh'

    def init(self, options):
        pass

    def split(self, input):
        return jieba.cut_for_search(input.encode("utf8")) 

    def word_filter(self, stemmed_word):
        return True

def setup(app): 
    import sphinx.search as search
    search.languages["zh_CN"] = SearchChinese

########NEW FILE########
__FILENAME__ = apibus_handler
#-*-coding: utf8 -*-

"""
urllib2 handler for SAE APIBus Service

Usage:

import urllib2
from apibus_handler import APIBusHandler
opener = urllib2.build_opener(APIBusHandler(ACCESSKEY, SECRETKEY))

Then you can use *opener* to request sae internal service such as segement,
sms as you want.
"""

import hmac
import base64
import hashlib
import time
from urllib2 import BaseHandler, Request

_APIBUS_ENDPOINT = 'http://g.apibus.io'

class APIBusHandler(BaseHandler):
    # apibus handler must be in front
    handler_order = 100

    def __init__(self, accesskey, secretkey):
        self.accesskey = accesskey
        self.secretkey = secretkey

    def _signature(self, headers):
        msg = ''.join([k + v for k, v in headers])
        h = hmac.new(self.secretkey, msg, hashlib.sha256).digest()
        return base64.b64encode(h)

    def http_request(self, req):
        orig_url = req.get_full_url()
        timestamp = str(int(time.time()))
        headers = [
            ('Fetchurl', orig_url),
            ('Timestamp', timestamp),
            ('Accesskey', self.accesskey),
        ]
        headers.append(('Signature', self._signature(headers)))
        # Create a new request
        _req = Request(_APIBUS_ENDPOINT, req.get_data(), origin_req_host=orig_url)
        _req.headers.update(req.header_items())
        _req.headers.update(headers)
        _req.timeout = req.timeout
        return _req

    https_request = http_request


########NEW FILE########
__FILENAME__ = demo
# -*-coding: utf8 -*-

import urllib
import urllib2
from apibus_handler import APIBusHandler

ACCESSKEY = '你的某个开启了服务的应用的accesskey'
SECRETKEY = '你的某个开启了服务的应用的secretkey'

apibus_handler = APIBusHandler(ACCESSKEY, SECRETKEY)
opener = urllib2.build_opener(apibus_handler)

print 'call sae segment api:'
chinese_text = '中文文本'
url = 'http://segment.sae.sina.com.cn/urlclient.php?word_tag=1&encoding=UTF-8'
payload = urllib.urlencode([('context', chinese_text),])
print opener.open(url, payload).read()

# sending sms
print 'call sae sms api:'
url = 'http://inno.smsinter.sina.com.cn/sae_sms_service/sendsms.php'
payload = 'mobile=186****8203&msg=helloworld'
print opener.open(url, payload).read()

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.
class Demo(models.Model):
    text = models.CharField(max_length=256)


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
# Create your views here.

from django.http import HttpResponse
from django.template import Template, Context
from django.core.context_processors import csrf
from demo.models import Demo

def showdemo(request):
    if request.method == 'POST':
        d = Demo(text=request.POST.get('text', ''))
        d.save()

    messages = Demo.objects.all()
    t = Template("""
    {{ xxxx }}
    {% for m in messages %}
        <p>{{ m.text }}</p>
    {% endfor %}
    <form action="" method="post"> {% csrf_token %}
        <div><textarea cols="40" name="text"></textarea></div>
        <div><input type="submit" /></div>
    </form>
    """);
    d = {'messages': messages}
    d.update(csrf(request))

    return HttpResponse(t.render(Context(d)))


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
# Django settings for mysite project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

from sae.const import (MYSQL_HOST, MYSQL_HOST_S,
    MYSQL_PORT, MYSQL_USER, MYSQL_PASS, MYSQL_DB
)

DATABASES = {
    'default': {
        'ENGINE':   'mysql',
        'NAME':     MYSQL_DB,
        'USER':     MYSQL_USER, 
        'PASSWORD': MYSQL_PASS,
        'HOST':     MYSQL_HOST,
        'PORT':     MYSQL_PORT,
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

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'xr45ymz8fs5wn*039+l462qwg7)7_yg$u7g6osv*3pynsr3#0#'

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

ROOT_URLCONF = 'mysite.urls'

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
    'mysite.demo',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^mysite/', include('mysite.foo.urls')),
    (r'^$', 'mysite.views.hello'),
    (r'^demo/$', 'mysite.demo.views.showdemo'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse

def hello(request):
    return HttpResponse("Hello, world! - Django")


########NEW FILE########
__FILENAME__ = compress
#!/usr/bin/env python
import os
import optparse
import subprocess
import sys

here = os.path.dirname(__file__)

def main():
    usage = "usage: %prog [file1..fileN]"
    description = """With no file paths given this script will automatically
compress all jQuery-based files of the admin app. Requires the Google Closure
Compiler library and Java version 6 or later."""
    parser = optparse.OptionParser(usage, description=description)
    parser.add_option("-c", dest="compiler", default="~/bin/compiler.jar",
                      help="path to Closure Compiler jar file")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose")
    (options, args) = parser.parse_args()

    compiler = os.path.expanduser(options.compiler)
    if not os.path.exists(compiler):
        sys.exit("Google Closure compiler jar file %s not found. Please use the -c option to specify the path." % compiler)

    if not args:
        if options.verbose:
            sys.stdout.write("No filenames given; defaulting to admin scripts\n")
        args = [os.path.join(here, f) for f in [
            "actions.js", "collapse.js", "inlines.js", "prepopulate.js"]]

    for arg in args:
        if not arg.endswith(".js"):
            arg = arg + ".js"
        to_compress = os.path.expanduser(arg)
        if os.path.exists(to_compress):
            to_compress_min = "%s.min.js" % "".join(arg.rsplit(".js"))
            cmd = "java -jar %s --js %s --js_output_file %s" % (compiler, to_compress, to_compress_min)
            if options.verbose:
                sys.stdout.write("Running: %s\n" % cmd)
            subprocess.call(cmd.split())
        else:
            sys.stdout.write("File %s not found. Sure it exists?\n" % to_compress)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for mysite project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

import os

if 'SERVER_SOFTWARE' in os.environ:
    from sae.const import (
        MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASS, MYSQL_DB
    )
else:
    # Make `python manage.py syncdb` works happy!
    MYSQL_HOST = 'localhost'
    MYSQL_PORT = '3306'
    MYSQL_USER = 'root'
    MYSQL_PASS = 'root'
    MYSQL_DB   = 'app_pylabs'

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql',
        'NAME':     MYSQL_DB,
        'USER':     MYSQL_USER,
        'PASSWORD': MYSQL_PASS,
        'HOST':     MYSQL_HOST,
        'PORT':     MYSQL_PORT,
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
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'up)24f2-l-+#g7ek4hp8ri1ng$@nbwqk+(fhdshgn9sc#b*oyl'

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'mysite.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'mysite.wsgi.application'

import os.path

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.path.dirname(__file__), 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'polls',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mysite.views.home', name='home'),
    # url(r'^mysite/', include('mysite.foo.urls')),
    url(r'^polls/', include('polls.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

# Serve static files for admin, use this for debug usage only
# `python manage.py collectstatic` is preferred.
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()


########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for mysite project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from polls.models import Poll, Choice

class ChoiceInline(admin.StackedInline):
    model = Choice
    extra = 3

class PollAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['question']}),
        ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
    ]
    inlines = [ChoiceInline]
    list_display = ('question', 'pub_date', 'was_published_recently')
    list_filter = ['pub_date']
    search_fields = ['question']
    date_hierarchy = 'pub_date'

admin.site.register(Poll, PollAdmin)

########NEW FILE########
__FILENAME__ = models
import time
from django.db import models

class Poll(models.Model):
    question = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')

    def was_published_recently(self):
        return self.pub_date >= time.now() - datetime.timedelta(days=1)

    was_published_recently.admin_order_field = 'pub_date'
    was_published_recently.boolean = True
    was_published_recently.short_description = 'Published recently?'

class Choice(models.Model):
    poll = models.ForeignKey(Poll)
    choice = models.CharField(max_length=200)
    votes = models.IntegerField()

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('polls.views',
    url(r'^$', 'index'),
    url(r'^(?P<poll_id>\d+)/$', 'detail'),
    url(r'^(?P<poll_id>\d+)/results/$', 'results'),
    url(r'^(?P<poll_id>\d+)/vote/$', 'vote'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from polls.models import Poll, Choice

def index(request):
    latest_poll_list = Poll.objects.all().order_by('-pub_date')[:5]
    return render_to_response('index.html', {'latest_poll_list': latest_poll_list})

def detail(request, poll_id):
    p = get_object_or_404(Poll, pk=poll_id)
    return render_to_response('detail.html', {'poll': p},
                               context_instance=RequestContext(request))

def vote(request, poll_id):
    p = get_object_or_404(Poll, pk=poll_id)
    try:
        selected_choice = p.choice_set.get(pk=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the poll voting form.
        return render_to_response('detail.html', {
            'poll': p,
            'error_message': "You didn't select a choice.",
        }, context_instance=RequestContext(request))
    else:
        selected_choice.votes += 1
        selected_choice.save()
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('polls.views.results', args=(p.id,)))

def results(request, poll_id):
    p = get_object_or_404(Poll, pk=poll_id)
    return render_to_response('results.html', {'poll': p})

########NEW FILE########
__FILENAME__ = app

########NEW FILE########
__FILENAME__ = myapp

import MySQLdb
from flask import Flask, g, request

app = Flask(__name__)
app.debug = True

from sae.const import (MYSQL_HOST, MYSQL_HOST_S,
    MYSQL_PORT, MYSQL_USER, MYSQL_PASS, MYSQL_DB
)

@app.before_request
def before_request():
    g.db = MySQLdb.connect(MYSQL_HOST, MYSQL_USER, MYSQL_PASS,
                           MYSQL_DB, port=int(MYSQL_PORT))

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'): g.db.close()

@app.route('/')
def hello():
    return "Hello, world! - Flask"

@app.route('/demo', methods=['GET', 'POST'])
def greeting():
    html = ''

    if request.method == 'POST':
        c = g.db.cursor()
        c.execute("insert into demo(text) values(%s)", (request.form['text']))

    html += """
    <form action="" method="post">
        <div><textarea cols="40" name="text"></textarea></div>
        <div><input type="submit" /></div>
    </form>
    """
    c = g.db.cursor()
    c.execute('select * from demo')
    msgs = list(c.fetchall())
    msgs.reverse()
    for row in msgs:
        html +=  '<p>' + row[-1] + '</p>'

    return html


########NEW FILE########
__FILENAME__ = renrenoauth
#!/usr/bin/env python
#coding=utf-8
# 
# Copyright 2010 RenRen
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A demo SAE application that uses RenRen for login.

This application is modified from the offical renren oauth sdk for python.

This application uses OAuth 2.0 directly rather than relying on renren's
JavaScript SDK for login. It also accesses the RenRen API directly
using the Python SDK. It is designed to illustrate how easy
it is to use the renren Platform without any third party code.

Befor runing the demo, you have to register a RenRen Application and modify the root domain.
e.g. If you specify the redirect_rui as "http://www.example.com/example_uri". The root domain must be "example.com"

@Author 414nch4n <chenfeng2@staff.sina.com.cn>

"""

# Replace these keys with your own one.
RENREN_APP_API_KEY = "06c0673d123240e7acd75e181cb5e40c"
RENREN_APP_SECRET_KEY = "a11b055a759241bd8bc6af9d99aacbd4"


RENREN_AUTHORIZATION_URI = "http://graph.renren.com/oauth/authorize"
RENREN_ACCESS_TOKEN_URI = "http://graph.renren.com/oauth/token"
RENREN_SESSION_KEY_URI = "http://graph.renren.com/renren_api/session_key"
RENREN_API_SERVER = "http://api.renren.com/restserver.do"



import base64
import Cookie
import email.utils
import hashlib
import hmac
import logging
import os.path
import time
import urllib

# Find a JSON parser
try:
    import json
    _parse_json = lambda s: json.loads(s)
except ImportError:
    try:
        import simplejson
        _parse_json = lambda s: simplejson.loads(s)
    except ImportError:
        from django.utils import simplejson
        _parse_json = lambda s: simplejson.loads(s)

import tornado.web
import tornado.wsgi
import tornado.database

from sae.const import (MYSQL_HOST, MYSQL_HOST_S,
    MYSQL_PORT, MYSQL_USER, MYSQL_PASS, MYSQL_DB
)

_db = tornado.database.Connection(
   ':'.join([MYSQL_HOST, MYSQL_PORT]), MYSQL_DB, MYSQL_USER, MYSQL_PASS,
   max_idle_time = 5
)

class User:
    def __init__(self, uid=None, name=None, avatar=None, access_token=None):
        self.uid = uid
        self.name = name
        self.avatar = avatar
        self.access_token = access_token

    @classmethod
    def get(cls, uid):
        user = cls()
        row = _db.get("""
            select * from users where uid = %s
        """, uid)
        user.uid = row.uid
        user.name = row.name
        user.avatar = row.avatar
        user.access_token = row.access_token
        return user

    def put(self):
        _db.execute("""
            insert into users(uid, name, avatar, access_token)
            values(%s, %s, %s, %s) on duplicate key update
            name = %s, avatar = %s, access_token = %s
        """, self.uid, self.name, self.avatar, self.access_token,
        self.name, self.avatar, self.access_token)

class BaseHandler(tornado.web.RequestHandler):
    @property
    def current_user(self):
        """Returns the logged in renren user, or None if unconnected."""
        if not hasattr(self, "_current_user"):
            self._current_user = None
            user_id = parse_cookie(self.get_secure_cookie("renren_user"))
            if user_id:
                logging.info("renren_user in cookie is: %s", user_id)
                self._current_user = User.get(user_id)
        return self._current_user

class HomeHandler(BaseHandler):
    def get(self):
        template_file = os.path.join(os.path.dirname(__file__), 
                                     'oauth.html')
        self.render(template_file, current_user=self.current_user)

class LoginHandler(BaseHandler):
    def get(self):
        verification_code = self.get_argument("code", None)
        # FIXME: use path_url from the request to construct the redirect_uri
        args = dict(client_id=RENREN_APP_API_KEY, redirect_uri='http://%s/auth/login' % self.request.host)
        
        error = self.get_argument("error", None)
        
        if error:
            args["error"] = error
            args["error_description"] = self.get_argument("error_description", '')
            args["error_uri"] = self.get_argument("error_uri", '')
            path = os.path.join(os.path.dirname(__file__), "error.html")
            args = dict(error=args)
            self.render(path, **args)
        elif verification_code:
            scope = self.get_argument("scope", "")
            scope_array = str(scope).split("[\\s,+]")
            logging.info("returning scope is :" + str(scope_array))
            response_state = self.get_argument("state", "")
            logging.info("returning state is :" + response_state)
            args["client_secret"] = RENREN_APP_SECRET_KEY
            args["code"] = verification_code
            args["grant_type"] = "authorization_code"
            logging.info(RENREN_ACCESS_TOKEN_URI + "?" + urllib.urlencode(args))
            response = urllib.urlopen(RENREN_ACCESS_TOKEN_URI + "?" + urllib.urlencode(args)).read()
            logging.info(response)
            access_token = _parse_json(response)["access_token"]
            logging.info("obtained access_token is: " + access_token)
            
            '''Obtain session key from the Resource Service.'''
            session_key_request_args = {"oauth_token": access_token}
            response = urllib.urlopen(RENREN_SESSION_KEY_URI + "?" + urllib.urlencode(session_key_request_args)).read()
            logging.info("session_key service response: " + str(response))
            session_key = str(_parse_json(response)["renren_token"]["session_key"])
            logging.info("obtained session_key is: " + session_key)
            
            '''Requesting the Renren API Server obtain the user's base info.'''
            params = {"method": "users.getInfo", "fields": "name,tinyurl"}
            api_client = RenRenAPIClient(session_key, RENREN_APP_API_KEY, RENREN_APP_SECRET_KEY)
            response = api_client.request(params);
            
            if type(response) is list:
                response = response[0]
            
            user_id = response["uid"]#str(access_token).split("-")[1]
            name = response["name"]
            avatar = response["tinyurl"]
            
            user = User(uid=user_id, name=name, avatar=avatar, access_token=access_token)
            user.put()
            
            set_cookie(self, "renren_user", str(user_id),
                       expires=time.time() + 30 * 86400)
            self.redirect("/")
        else:
            args["response_type"] = "code"
            args["scope"] = "publish_feed email status_update"
            args["state"] = "1 23 abc&?|."
            self.redirect(
                RENREN_AUTHORIZATION_URI + "?" +
                urllib.urlencode(args))


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('renren_user')
        self.redirect("/")

class RenRenAPIClient(object):
    def __init__(self, session_key = None, api_key = None, secret_key = None):
        self.session_key = session_key
        self.api_key = api_key
        self.secret_key = secret_key
    def request(self, params = None):
        """Fetches the given method's response returning from RenRen API.

        Send a POST request to the given method with the given params.
        """
        params["api_key"] = self.api_key
        params["call_id"] = str(int(time.time() * 1000))
        params["format"] = "json"
        params["session_key"] = self.session_key
        params["v"] = '1.0'
        sig = self.hash_params(params);
        params["sig"] = sig
        
        post_data = None if params is None else urllib.urlencode(params)
        
        #logging.info("request params are: " + str(post_data))
        
        file = urllib.urlopen(RENREN_API_SERVER, post_data)
        
        try:
            s = file.read()
            logging.info("api response is: " + s)
            response = _parse_json(s)
        finally:
            file.close()
        if type(response) is not list and response["error_code"]:
            logging.info(response["error_msg"])
            raise RenRenAPIError(response["error_code"], response["error_msg"])
        return response
    def hash_params(self, params = None):
        hasher = hashlib.md5("".join(["%s=%s" % (self.unicode_encode(x), self.unicode_encode(params[x])) for x in sorted(params.keys())]))
        hasher.update(self.secret_key)
        return hasher.hexdigest()
    def unicode_encode(self, str):
        """
        Detect if a string is unicode and encode as utf-8 if necessary
        """
        return isinstance(str, unicode) and str.encode('utf-8') or str
    
class RenRenAPIError(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code

def set_cookie(response, name, value, domain=None, path="/", expires=None):
    """Generates and signs a cookie for the give name/value"""
    # Now we just ignore domain, path and expires
    response.set_secure_cookie(name, value)
    logging.info("set cookie as " + name + ", value is: " + value)

def parse_cookie(value):
    """Parses and verifies a cookie value from set_cookie"""
    if not value: return None
    return value

settings = {
  "debug": True,
  "cookie_secret": "c19e4cc825adee8ab0928244186538aca2821425",
  "static_path": os.path.join(os.path.dirname(__file__))
}

app = tornado.wsgi.WSGIApplication([
    (r"/", HomeHandler),
    (r"/auth/login", LoginHandler),
    (r"/auth/logout", LogoutHandler),
], **settings)

if __name__ == '__main__':
    import wsgiref.simple_server
    httpd = wsgiref.simple_server.make_server('', 8080, app)
    httpd.serve_forever()

########NEW FILE########
__FILENAME__ = appstack

from flask import Flask, request, redirect, session
from weibopy import OAuthHandler, oauth, API

app = Flask(__name__)
app.debug = True
app.secret_key = 'test'

consumer_key = '199***'
consumer_secret = 'a1f8****'

def get_referer():
    return request.headers.get('HTTP_REFERER', '/')

def get_weibo_user():
    auth = OAuthHandler(consumer_key, consumer_secret)
    # Get currrent user access token from session
    access_token = session['oauth_access_token']
    auth.setToken(access_token.key, access_token.secret)
    api = API(auth)
    # Get info from weibo
    return api.me()

def login_ok(f):
    def login_wrapper(*args, **kw):
        if 'oauth_access_token' not in session:
            return redirect('/login')
        return f(*args, **kw)
    return login_wrapper

@app.route('/')
@login_ok
def hello():
    user = get_weibo_user()
    return "Hello, %s <img src=%s>" % (user.screen_name, user.profile_image_url)

@app.route('/login')
def login():
    session['login_ok_url'] = get_referer()
    callback = 'http://appstack.sinaapp.com/login_callback'

    auth = OAuthHandler(consumer_key, consumer_secret, callback)
    # Get request token and login url from the provider
    url = auth.get_authorization_url()
    session['oauth_request_token'] = auth.request_token
    # Redirect user to login
    return redirect(url)

@app.route('/login_callback')
def login_callback():
    # This is called by the provider when user has granted permission to your app
    verifier = request.args.get('oauth_verifier', None)
    auth = OAuthHandler(consumer_key, consumer_secret)
    request_token = session['oauth_request_token']
    del session['oauth_request_token']
    
    # Show the provider it's us really
    auth.set_request_token(request_token.key, request_token.secret)
    # Ask for a temporary access token
    session['oauth_access_token'] = auth.get_access_token(verifier)
    return redirect(session.get('login_ok_url', '/'))

@app.route('/logout')
def logout():
    del session['oauth_access_token']
    return redirect(get_referer())

########NEW FILE########
