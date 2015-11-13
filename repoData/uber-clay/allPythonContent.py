__FILENAME__ = celery
from __future__ import absolute_import
from celery import Celery
from clay import config


log = config.get_logger('clay.celery')

celery = Celery(log=log)
celery.config_from_object(config.get('celery'))


def main():
    '''
    Run a celery worker process
    '''
    celery.worker_main()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = config
from __future__ import absolute_import

import logging.config
import logging
import random
import signal
import json
import time
import os.path
import os
import sys


SERIALIZERS = {'json': json}

try:
    import yaml
    SERIALIZERS['yaml'] = yaml
except ImportError:
    pass


class Configuration(object):
    '''
    Manages global configuration from JSON files
    '''
    def __init__(self):
        self.paths = []
        self.config = {}
        self.last_updated = None
        self.init_logging()

    def load(self, signum=None, frame=None):
        '''
        Called when the configuration should be loaded. May be called multiple
        times during the execution of a program to change or update the
        configuration. This method should be overridden by a subclass.
        '''
        return

    def debug(self):
        '''
        Returns True if this server should use debug configuration and logging.
        This method is deprecated and 
        '''
        log = self.get_logger('clay.config')
        log.warning('Configuration.debug() is deprecated and may be removed in a future release of clay-flask. Please use config.get("debug.enabled", False) instead')
        return self.get('debug.enabled', False)

    def get(self, key, default=None):
        '''
        Get the configuration for a specific variable, using dots as
        delimiters for nested objects. Example: config.get('api.host') returns
        the value of self.config['api']['host'] or None if any of those keys
        does not exist. The default return value can be overridden.
        '''
        value = self.config
        for k in key.split('.'):
            try:
                value = value[k]
            except KeyError:
                return default
        #sys.stderr.write('config: %s=%r\n' % (key, value))
        return value

    def init_logging(self):
        '''
        Configure the default root logger to output WARNING to stderr
        '''
        logging.basicConfig(
            format='%(asctime)s %(name)s %(levelname)s %(message)s',
            level=logging.WARNING)

    def reset_logging(self):
        '''
        Reset the root logger configuration to no handlers
        '''
        root = logging.getLogger()
        if root.handlers:
            for handler in list(root.handlers):
                root.removeHandler(handler)

    def configure_logging(self, log_config):
        '''
        Remove all existing logging configuration and use the given
        configuration instead. The format of the log_config dict is specified at
        http://docs.python.org/2/library/logging.config.html#logging-config-dictschema
        '''
        logging.config.dictConfig(log_config)

    def get_logger(self, name):
        '''
        Returns a Logger instance that may be used to emit messages with the
        given log name, respecting debug behavior.
        '''

        log = logging.getLogger(name)
        if self.get('debug.logging', False):
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)
        return log

    def feature_flag(self, name):
        '''
        Returns a boolean value for the given feature, which may be
        probabalistic.
        '''
        feature = self.get('features.%s' % name)
        if not feature:
            return False
        if 'percent' in feature:
            percent = float(feature['percent']) / 100.0
            return (random.random() < percent)
        return feature.get('enabled', False)


class FileConfiguration(Configuration):
    def load(self, signum=None, frame=None):
        '''
        Iterate through expected config file paths, loading the ones that
        exist and can be parsed.
        '''
        cwd = os.getcwd()
        if not cwd in sys.path:
            sys.path.insert(0, cwd)

        self.config = {}
        paths = list(self.paths)

        if 'CLAY_CONFIG' in os.environ:
            paths += os.environ['CLAY_CONFIG'].split(':')

        for path in paths:
            path = os.path.expandvars(path)
            path = os.path.abspath(path)
            config = self.load_from_file(path)
            self.config.update(config)

        self.last_updated = time.time()

        self.init_logging()
        log_config = self.get('logging')
        if log_config:
            self.configure_logging(log_config)

    def load_from_file(self, filename):
        '''
        Attempt to load configuration from the given filename. Returns an empty
        dict upon failure.
        '''
        log = self.get_logger('clay.config')

        try:
            filetype = os.path.splitext(filename)[-1].lstrip('.').lower()
            if not filetype in SERIALIZERS:
                log.warning('Unknown config format %s, parsing as JSON' % filetype)
                filetype = 'json'

            # Try getting a safe_load function. If absent, use 'load'.
            load = getattr(SERIALIZERS[filetype], "safe_load",
                           getattr(SERIALIZERS[filetype], "load"))

            config = load(file(filename, 'r'))
            if not config:
                raise ValueError('Empty config')
            log.info('Loaded configuration from %s' % filename)
            return config
        except ValueError, e:
            log.critical('Error loading config from %s: %s' %
                (filename, str(e)))
            sys.exit(1)
            return {}


CONFIG = FileConfiguration()
CONFIG.load()

# Upon receiving a SIGHUP, configuration will be reloaded
signal.signal(signal.SIGHUP, CONFIG.load)

# Expose some functions at the top level for convenience
get = CONFIG.get
get_logger = CONFIG.get_logger
feature_flag = CONFIG.feature_flag
debug = CONFIG.debug

########NEW FILE########
__FILENAME__ = database
from clay import config
import threading
import random

log = config.get_logger('clay.database')


class DatabaseContext(object):
    def __init__(self, servers, dbapi_name):
        '''
        Servers is a list of config dicts for connecting to postgres
        '''
        self.servers = servers

        self.tlocal = threading.local()
        self.tlocal.dbconn = None

        if not dbapi_name in ('psycopg2', 'MySQLdb', 'sqlite3'):
            raise NotImplementedError('Unsupported database module: %s' % dbapi_name)
        self.dbapi_name = dbapi_name
        self.dbapi = __import__(dbapi_name)

    def __enter__(self):
        server = random.choice(self.servers)
        conn = self.dbapi.connect(**server)
        self.tlocal.dbconn = conn
        return conn

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.tlocal.dbconn.close()
        self.tlocal.dbconn = None

        if exc_type is not None:
            raise
    
    def __str__(self):
        if self.dbconn is not None:
            return 'DatabaseContext %s %r (connected)' % (self.dbapi_name, self.servers)
        else:
            return 'DatabaseContext %s %r (not connected)' % (self.dbapi_name, self.servers)


read = DatabaseContext(config.get('database.read'), config.get('database.module'))
write = DatabaseContext(config.get('database.write'), config.get('database.module'))

########NEW FILE########
__FILENAME__ = docs
from flask import request
from clay import app, config
import json

log = config.get_logger('clay.docs')


def parse_docstring_param(directive, key, value):
    p = {
        'name': key,
        'description': value.split('{', 1)[0],
        'required': False,
        'dataType': 'string',
        'type': 'primitive',
        'allowMultiple': False,
    }
    if '{' in value and '}' in value:
        p.update(json.loads(value[value.find('{'):value.find('}')]))

    if directive == 'json':
        directive = 'body'
        p['type'] = 'complex'

    if directive in ('query', 'body', 'path', 'form'):
        p['paramType'] = directive
    elif directive == 'reqheader':
        p['paramType'] = 'header'
    else:
        log.warning('Ignoring unknown docstring param %s', directive)
        return
    return p


def parse_docstring(docstring):
    '''
    Turns autodoc http dialect docstrings into swagger documentation
    '''
    if not docstring:
        return
    
    params = []
    responses = []
    stripped = ''
    rtype = None
    for line in docstring.split('\n'):
        line = line.lstrip('\t ')
        if not line.startswith(':'):
            stripped += line + '\n<br />'
            continue
        
        directive, value = line.split(':', 2)[1:]
        value = value.strip('\t ')

        directive = directive.split(' ', 1)
        if len(directive) > 1:
            directive, key = directive
        else:
            directive = directive[0]
            key = None

        if directive in ('json', 'body', 'query', 'path', 'form', 'reqheader'):
            param = parse_docstring_param(directive, key, value)
            if param:
                params.append(param)
            continue

        if directive == 'status':
            responses.append({
                'code': int(key),
                'message': value,
            })
            continue
        
        if directive == 'rtype':
            rtype = value
        log.warning('Ignoring unknown docstring param %s', directive)

    return (params, responses, stripped, rtype)


def get_model(modelspec):
    module, name = modelspec.rsplit('.', 1)
    module = __import__(module)
    return {
        'id': modelspec,
        'properties': getattr(module, name),
    }


@app.route('/_docs', methods=['GET'])
def clay_docs():
    '''
    Returns a JSON document describing this service's API

    Endpoints are inferred from routes registered with Flask and the docstrings
    bound to those methods.

    Dialect documentation http://pythonhosted.org/sphinxcontrib-httpdomain/
    Swagger documentation https://github.com/wordnik/swagger-core/wiki

    :status 200: Generated swagger documentation
    :status 500: Something went horribly wrong
    '''
    headers = {'Content-type': 'application/json'}
    response = {
        'apiVersion': '0.2',
        'swaggerVersion': '1.2',
        'basePath': config.get('docs.base_path', None) or request.url_root.rstrip('/'),
        'resourcePath': '/',
        'apis': [],
        'models': {},
    }

    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue

        api = {
            'path': rule.rule,
            'operations': [],
        }
        view_func = app.view_functions[rule.endpoint]
        if view_func.__doc__:
            docstring = view_func.__doc__.strip('\r\n\t ')
            params, responses, stripped_docstring, rtype = parse_docstring(docstring)

            shortdoc = [x for x in docstring.split('\n') if x]
            if not shortdoc:
                shortdoc = 'Undocumented'
            else:
                shortdoc = shortdoc[0]
        else:
            shortdoc = 'Undocumented'
            params = []
            responses = []
            stripped_docstring = shortdoc
            rtype = None


        for http_method in rule.methods:
            if http_method in ('HEAD', 'OPTIONS'):
                continue
            doc = {
                'method': http_method,
                'nickname': view_func.__name__,
                'summary': shortdoc,
                'notes': stripped_docstring,
                'parameters': params,
                'responseMessage': responses,
            }
            if rtype:
                doc['responseClass'] = rtype
                model = get_model(rtype)
                response['models'][rtype] = model

            api['operations'].append(doc)
        response['apis'].append(api)

    return (json.dumps(response, indent=2), 200, headers)

########NEW FILE########
__FILENAME__ = http
from __future__ import absolute_import

from flask import make_response
from collections import namedtuple
import contextlib
import functools
import httplib
import urllib2
import urlparse
import os.path
import ssl

from clay import config


Response = namedtuple('Response', ('status', 'headers', 'data'))
log = config.get_logger('clay.http')

DEFAULT_CA_CERTS = '/etc/ssl/certs/ca-certificates.crt'


class VerifiedHTTPSOpener(urllib2.HTTPSHandler):
    def https_open(self, req):
        ca_certs = config.get('http.ca_certs_file', DEFAULT_CA_CERTS)
        if config.get('http.verify_server_certificates', True) and os.path.exists(ca_certs):
            frags = urlparse.urlparse(req.get_full_url())
            ssl.get_server_certificate(
                (frags.hostname, frags.port or 443),
                ca_certs=ca_certs
            )
        return self.do_open(httplib.HTTPSConnection, req)

urllib2.install_opener(urllib2.build_opener(VerifiedHTTPSOpener))


class Request(urllib2.Request):
    '''
    This subclass adds "method" to urllib2.Request
    '''
    def __init__(self, url, data=None, headers={}, origin_req_host=None,
                 unverifiable=False, method=None):
        urllib2.Request.__init__(self, url, data, headers, origin_req_host,
                                 unverifiable)
        if headers is None:
            self.headers = {}
        self.method = method

    def get_method(self):
        if self.method is not None:
            return self.method
        if self.has_data():
            return 'POST'
        else:
            return 'GET'


def request(method, uri, headers={}, data=None, timeout=None):
    '''
    Convenience wrapper around urllib2. Returns a Response namedtuple with 'status', 'headers', and 'data' fields

    It is highly recommended to set the 'timeout' parameter to something sensible
    '''
    req = Request(uri, headers=headers, data=data, method=method)
    if not req.get_type() in ('http', 'https'):
        raise urllib2.URLError('Only http and https protocols are supported')

    try:
        with contextlib.closing(urllib2.urlopen(req, timeout=timeout)) as resp:
            resp = Response(
                status=resp.getcode(),
                headers=resp.headers,
                data=resp.read())
            log.debug('%i %s %s' % (resp.status, method, uri))
    except urllib2.HTTPError, e:
        # if there was a connection error, the underlying fd might be None and we can't read it
        if e.fp is not None:
            resp = Response(
                status=e.getcode(),
                headers=e.hdrs,
                data=e.read())
        else:
            resp = Response(
                status=e.getcode(),
                headers=e.hdrs,
                data=None)
        log.warning('%i %s %s' % (resp.status, method, uri))

    return resp


def cache_control(**cache_options):
    '''
    Decorator that adds a Cache-Control header to the response returned from a
    view. Each keyword argument to this decorator is an option to be appended
    to the Cache-Control header. Underscores '_' are replaced with dashes '-'
    and boolean values are assumed to be directives.

    Examples:
    @cache_control(max_age=0, no_cache=True)
    @cache_control(max_age=3600, public=True)
    '''
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            response = make_response(f(*args, **kwargs))

            cache_control = []
            for key, value in cache_options.iteritems():
                key = key.replace('_', '-')
                if isinstance(value, bool):
                    cache_control.append(key)
                elif isinstance(value, basestring):
                    cache_control.append('%s="%s"' % (key, value))
                else:
                    cache_control.append('%s=%s' % (key, value))
            cache_control = ', '.join(cache_control)

            response.headers['Cache-Control'] = cache_control
            return response
        return wrapper
    return decorator

########NEW FILE########
__FILENAME__ = logger
from traceback import format_exc
from datetime import datetime
from Queue import Queue
import threading
import logging
import socket
import json
import time
import ssl


LOG_QUEUE_SIZE = 5000
BACKOFF_INITIAL = 0.1
BACKOFF_MULTIPLE = 1.2
INTERNAL_LOG = logging.getLogger('clay_internal')


class TCPHandler(logging.Handler):
    '''
    Python logging handler for sending JSON formatted messages over
    TCP, optionally wrapping the connection with TLSv1
    '''
    def __init__(self, host, port, ssl_ca_file=None):
        '''
        Instantiate a TCPHandler with the intent of connecting to the
        given host (string) and port (int) with or without using SSL/TLSv1
        '''
        logging.Handler.__init__(self)
        self.host = host
        self.port = port
        self.ssl_ca_file = ssl_ca_file
        self.sock = None
        self.queue = Queue(LOG_QUEUE_SIZE)
        self.connect_wait = BACKOFF_INITIAL
        self.raiseExceptions = 0

        self.hostname = socket.gethostname()
        if self.hostname.find('.') != -1:
            self.hostname = self.hostname.split('.', 1)[0]

        self.sender = threading.Thread(target=self.run)
        self.sender.setDaemon(True)
        self.sender.start()

    def connect(self):
        '''
        Create a connection with the server, sleeping for some
        period of time if connection errors have occurred recently.
        '''
        self.sock = socket.socket()
        if self.ssl_ca_file:
            self.sock = ssl.wrap_socket(self.sock,
                ssl_version=ssl.PROTOCOL_TLSv1,
                cert_reqs=ssl.CERT_REQUIRED,
                ca_certs=self.ssl_ca_file)

        INTERNAL_LOG.debug('Connecting (backoff: %.03f)' %
            self.connect_wait)
        time.sleep(self.connect_wait)
        self.sock.connect((self.host, self.port))

    def jsonify(self, record):
        '''
        Translate a LogRecord instance into a json_event
        '''
        timestamp = datetime.utcfromtimestamp(record.created)
        timestamp = timestamp.isoformat()

        fields = {
            'level': record.levelname,
            'filename': record.pathname,
            'lineno': record.lineno,
            'method': record.funcName,
        }
        if record.exc_info:
            fields['exception'] = str(record.exc_info)
            fields['traceback'] = format_exc(record.exc_info)

        log = {
            '@source_host': self.hostname,
            '@timestamp': timestamp,
            '@tags': [record.name],
            '@message': record.getMessage(),
            '@fields': fields,
        }
        return json.dumps(log)

    def emit(self, record):
        '''
        Send a LogRecord object formatted as json_event via a
        queue and worker thread.
        '''
        self.queue.put_nowait(record)

    def run(self):
        '''
        Main loop of the logger thread. All network I/O and exception handling
        originates here. Strings are consumed from self.queue and sent to
        self.sock, creating a new connection if necessary.

        If any exceptions are caught, the message is put() back on the queue
        and the exception is allowed to propagate up through
        logging.Handler.handleError(), potentially causing this thread to abort.
        '''
        INTERNAL_LOG.debug('Log I/O thread started')
        while True:
            record = self.queue.get()
            if record is None:
                break

            jsonrecord = self.jsonify(record)
            jsonrecord = '%s\n' % jsonrecord

            try:
                if self.sock is None:
                    self.connect()
                self.send(jsonrecord)
            except Exception:
                # This exception will be silently ignored and the message
                # requeued unless self.raiseExceptions=1
                self.queue.put(record)
                self.handleError(record)
            self.queue.task_done()
        INTERNAL_LOG.debug('Log I/O thread exited cleanly')

    def send(self, data):
        '''
        Keep calling SSLSocket.write until the entire message has been sent
        '''
        while len(data) > 0:
            if self.ssl_ca_file:
                sent = self.sock.write(data)
            else:
                sent = self.sock.send(data)
            data = data[sent:]
        self.connect_wait = BACKOFF_INITIAL

    def handleError(self, record):
        '''
        If an error occurs trying to send the log message, close the connection
        and delegate the exception handling to the superclass' handleError,
        which raises the exception (potentially killing the log thread) unless
        self.raiseExceptions is False.
        http://hg.python.org/cpython/file/e64d4518b23c/Lib/logging/__init__.py#l797
        '''
        INTERNAL_LOG.exception('Unable to send log')
        self.cleanup()
        self.connect_wait *= BACKOFF_MULTIPLE
        logging.Handler.handleError(self, record)

    def cleanup(self):
        '''
        If the socket to the server is still open, close it. Otherwise, do
        nothing.
        '''
        if self.sock:
            INTERNAL_LOG.info('Closing socket')
            self.sock.close()
            self.sock = None

    def close(self):
        '''
        Send a sentinel None object to the worker thread, telling it to exit
        and disconnect from the server.
        '''
        self.queue.put(None)
        self.cleanup()
        #self.sender.join()


class UDPHandler(logging.Handler):
    '''
    Python logging handler for sending JSON formatted messages over UDP
    '''
    def __init__(self, host, port):
        '''
        Instantiate a UDPHandler with the intent of connecting to the
        given host (string) and port (int)
        '''
        logging.Handler.__init__(self)
        self.host = host
        self.port = port
        self.sock = None
        self.raiseExceptions = 0

        self.hostname = socket.gethostname()
        if self.hostname.find('.') != -1:
            self.hostname = self.hostname.split('.', 1)[0]

    def connect(self):
        '''
        Create a connection with the server, sleeping for some
        period of time if connection errors have occurred recently.
        '''
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect((self.host, self.port))

    def jsonify(self, record):
        '''
        Translate a LogRecord instance into a json_event
        '''
        timestamp = datetime.utcfromtimestamp(record.created)
        timestamp = timestamp.isoformat()

        fields = {
            'level': record.levelname,
            'filename': record.pathname,
            'lineno': record.lineno,
            'method': record.funcName,
        }
        if record.exc_info:
            fields['exception'] = str(record.exc_info)
            fields['traceback'] = format_exc(record.exc_info)

        log = {
            '@source_host': self.hostname,
            '@timestamp': timestamp,
            '@tags': [record.name],
            '@message': record.getMessage(),
            '@fields': fields,
        }
        return json.dumps(log)

    def emit(self, record):
        '''
        Send a LogRecord object formatted as json_event via a
        queue and worker thread.
        '''
        try:
            if self.sock is None:
                self.connect()
            jsonrecord = self.jsonify(record)
            jsonrecord = '%s\n' % jsonrecord
            self.sock.sendall(jsonrecord)
        except Exception:
            INTERNAL_LOG.exception('Error sending message to log server')
            self.close()

    def close(self):
        if self.sock:
            self.sock.close()
        self.sock = None

########NEW FILE########
__FILENAME__ = mail
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from clay import config

log = config.get_logger('clay.mail')


def _string_or_list(obj):
    '''
    If obj is a string, it's converted to a single element list, otherwise
    it's just returned as-is under the assumption that it's already a list. No
    further type checking is performed.
    '''

    if isinstance(obj, basestring):
        return [obj]
    else:
        return obj


def sendmail(mailto, subject, message, subtype='html', charset='utf-8', smtpconfig=None, **headers):
    '''
    Send an email to the given address. Additional SMTP headers may be specified
    as keyword arguments.
    '''

    if not smtpconfig:
        # we support both smtp and mail for legacy reasons
        # smtp is the correct usage.
        smtpconfig = config.get('smtp') or config.get('mail')

    # mailto arg is explicit to ensure that it's always set, but it's processed
    # mostly the same way as all other headers
    headers['To'] = _string_or_list(mailto)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    for key, value in headers.iteritems():
        for val in _string_or_list(value):
            msg.add_header(key, val)

    text = MIMEText(message, subtype, charset)
    msg.attach(text)

    if not 'From' in msg:
        msg['From'] = smtpconfig.get('from')
    mailfrom = msg['From']
    assert isinstance(mailfrom, basestring)

    recipients = []
    for toheader in ('To', 'CC', 'BCC'):
        recipients += msg.get_all(toheader, [])
    if 'BCC' in msg:
        del msg['BCC']

    smtp = smtplib.SMTP(smtpconfig.get('host'), smtpconfig.get('port'))
    if smtpconfig.get('username', None) is not None and smtpconfig.get('password', None) is not None:
        smtp.login(smtpconfig.get('username'), smtpconfig.get('password'))
    smtp.sendmail(mailfrom, recipients, msg.as_string())
    smtp.quit()
    log.info('Sent email to %s (Subject: %s)', recipients, subject)

########NEW FILE########
__FILENAME__ = sentry
from __future__ import absolute_import

import raven.utils.wsgi
import raven

from clay import config

log = config.get_logger('clay.sentry')
client = None


def get_sentry_client():
    global client
    if client:
        return client
    dsn = config.get('sentry.url', None)
    if not dsn:
        return
    client = raven.Client(dsn=dsn)
    return client


def exception(exc_info, request=None, event_id=None, **extra):
    try:
        _exception(exc_info, request=request, event_id=event_id, **extra)
    except:
        log.exception('Unable to send event to sentry')


def _exception(exc_info, request=None, event_id=None, **extra):
    client = get_sentry_client()
    if not client:
        # return silently if sentry isn't configured
        return
    if request is not None:
        environ = request.environ
        client.capture('Exception', data={
            'sentry.interfaces.Http': {
                'method': request.method,
                'url': request.base_url,
                'data': request.data,
                'query_string': environ.get('QUERY_STRING', ''),
                'headers': dict(raven.utils.wsgi.get_headers(environ)),
                'env': dict(raven.utils.wsgi.get_environ(environ)),
            },
            'logger': extra.get("logger", "sentry"),
        }, extra=extra, exc_info=exc_info, event_id=event_id)
    else:
        client.captureException(exc_info, extra=extra,
            event_id=event_id)

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
from __future__ import absolute_import
import sys

from flask import Flask
import werkzeug.serving

from clay import config

log = config.get_logger('clay.server')


def load_middleware(app, name, mwconfig):
    log.info('Loading WSGI middleware %s' % name)
    try:
        modulename, wsgi = name.rsplit('.', 1)
        mw = __import__(modulename)
        mw = sys.modules[modulename]
        mw = getattr(mw, wsgi, None)
        if mw is None or not callable(mw):
            log.error('No callable named %s in %s (%r)' % (wsgi, modulename, mw))
        else:
            app = mw(app, **mwconfig)
    except Exception:
        log.exception('Unable to load WSGI middleware %s' % name)
    return app

flask_init = config.get('flask.init', {
    'import_name': 'clayapp',
})

app = Flask(**flask_init)
app.debug = config.get('debug.enabled', False)
app.config.update(config.get('flask.config', {}))
application = app
for name, mwconfig in config.get('middleware', {}).iteritems():
    application = load_middleware(application, name, mwconfig)


def devserver():
    if not config.get('debug.enabled', False):
        sys.stderr.write('This server must be run in development mode, set debug.enabled in your config and try again\n')
        return -1

    for modulename in config.get('views'):
        log.debug('Loading views from %s' % modulename)
        __import__(modulename)

    conf = config.get('debug.server')
    log.warning('DEVELOPMENT MODE')
    log.info('Listening on %s:%i' % (conf['host'], conf['port']))

    kwargs = {
        'use_reloader': True,
        'use_debugger': True,
        'use_evalex': True,
        'threaded': False,
        'processes': 1,
    }
    kwargs.update(config.get('debug.werkzeug', {}))
    werkzeug.serving.run_simple(conf['host'], conf['port'], application, **kwargs)


if __name__ == '__main__':
    sys.exit(devserver())

########NEW FILE########
__FILENAME__ = stats
from __future__ import absolute_import

import functools
import socket
import time

from clay import config

log = config.get_logger('clay.stats')


class StatsConnection(object):
    '''
    Handles the lifecycle of stats sockets and connections.
    '''
    def __init__(self):
        self.sock = None
        self.proto = None
        self.host = None
        self.port = None
        self.next_retry = None
        self.backoff = 0.5
        self.max_backoff = 10.0

    def __str__(self):
        if self.sock is not None:
            return 'StatsConnection %s %s:%i (connected)' % (
                   self.proto, self.host, self.port)
        else:
            return 'StatsConnection %s %s:%i (not connected)' % (
                   self.proto, self.host, self.port)

    def get_socket(self):
        '''
        Creates and connects a new socket, or returns an existing one if this
        method was called previously. Returns a (protocol, socket) tuple, where
        protocol is either 'tcp' or 'udp'. If the returned socket is None, the
        operation failed and details were logged.
        '''
        if self.sock is not None:
            return (self.proto, self.sock)

        proto = config.get('statsd.protocol', 'udp')
        self.proto = proto
        self.host = config.get('statsd.host', None)
        self.port = config.get('statsd.port', 8125)

        if self.host is None or self.port is None:
            return (self.proto, None)

        if (self.next_retry is not None) and (self.next_retry > time.time()):
            return

        if proto == 'udp':
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            log.debug('Created udp statsd socket')
            return (proto, self.sock)

        if proto == 'tcp':
            if self.host is None or not isinstance(self.port, int):
                log.error('Invalid TCP statsd config: host=%r port=%r',
                          self.host, self.port)
                self.sock = None
            else:
                try:
                    self.sock = socket.create_connection(address=(self.host, self.port), timeout=4.0)
                    log.debug('Connected tcp statsd socket to %s:%i',
                              self.host, self.port)
                    # Succesful connection resets retry backoff to 1 second
                    self.next_retry = None
                    self.backoff = 0.5
                except socket.error:
                    log.exception('Cannot open tcp stats socket %s:%i',
                                  self.host, self.port)
                    self.sock = None

                    # Every time a connection fails, we add 25% of the backoff value
                    # We cap this at max_backoff so that we guarantee retries after
                    # some period of time
                    if self.backoff > self.max_backoff:
                        self.backoff = self.max_backoff
                    log.warning('Unable to connect to statsd, not trying again for %.03f seconds', self.backoff)
                    self.next_retry = (time.time() + self.backoff)
                    self.backoff *= 1.25
            return (proto, self.sock)

        log.warning('Unknown protocol configured for statsd socket: %s', proto)
        return (proto, None)

    def reset(self):
        '''
        Close and remove references to the socket.
        '''
        if self.sock is None:
            return
        try:
            self.sock.close()
        except socket.error:
            pass
        self.sock = None
        log.debug('Reset statsd socket')

    def send(self, stat):
        '''
        Send a raw stat line to statsd. A new socket will be opened and
        connected if necessary. Returns True if the stat was sent successfully.

        :param stat: The stat to be sent to statsd, with no trailing newline
        :type stat: string
        :rtype: boolean
        '''
        proto, sock = self.get_socket()
        if sock is None:
            return False

        if not stat.endswith('\n'):
            stat += '\n'

        try:
            if proto == 'udp':
                sock.sendto(stat, 0, (self.host, self.port))
                return True

            if proto == 'tcp':
                sock.sendall(stat)
                return True
        except socket.error:
            log.exception('Unable to send to statsd, resetting socket')
            self.reset()
        return False

connection = StatsConnection()
send = connection.send  # backwards compatibility


class Timer(object):
    '''
    Context manager for recording wall-clock timing stats.

    with clay.stats.Timer("myapp.example"):
        # do some work
    '''
    def __init__(self, key):
        self.key = key
        self.start = None

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        now = time.time()
        elapsed_ms = ((now - self.start) * 1000.0)
        timing(self.key, elapsed_ms)


def count(key, n, sample=1.0):
    '''
    Increment a counter by n, or decrement if n is negative.

    :param key: The key to increment by the count
    :type key: string
    :param n: The number to increment by
    :type n: integer
    :param sample: Optional sample rate to scale the counter by. Must be a
                   float between 0.0 and 1.0. Defaults to 1.0
    :type sample: float
    '''
    if sample == 1.0:
        return connection.send('%s:%i|c' % (key, n))
    else:
        return connection.send('%s:%i|c|@%f' % (key, n, sample))


def timing(key, ms):
    '''
    Send a timing stat to statsd

    :param key: A key identifying this stat
    :type key: string
    :param ms: A floating point number of milliseconds
    :type ms: float
    '''
    if not isinstance(ms, float):
        ms = float(ms)
    return connection.send('%s:%f|ms' % (key, ms))


def gauge(key, value):
    '''
    Send an instantaneous gauge value to statsd

    :param key: Name of this gauge
    :type key: string
    :param value: Gauge value or delta
    :type value: float
    '''
    if not isinstance(value, float):
        value = float(value)
    return connection.send('%s:%f|g' % (key, value))


def unique_set(key, value):
    '''
    Send a set stat to statsd, counting the approximate number of unique
    key/value pairs.

    :param key: Name of this set
    :type key: string
    :param value: Set value
    :type value: string
    '''
    return connection.send('%s:%s|s' % (key, value))


def wrapper(prefix):
    '''
    Decorator that logs timing, call count, and exception count statistics to
    statsd. Given a prefix of "example", the following keys would be created:

    stats.counts.example.calls
    stats.counts.example.exceptions
    stats.timers.example.duration

    :param: prefix
    :type key: Prefix for stats keys to be created under
    '''

    def clay_stats_wrapper(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            count('%s.calls' % prefix, 1)
            try:
                with Timer('%s.duration' % prefix):
                    return func(*args, **kwargs)
            except Exception:
                count('%s.exceptions' % prefix, 1)
                raise
        return wrap
    return clay_stats_wrapper

########NEW FILE########
__FILENAME__ = wsgi
from __future__ import absolute_import
from clay.server import application
from clay import config

log = config.get_logger('clay.wsgi')

views = config.get('views', [])
if not views:
    log.warning('No clay view modules configured')

for modulename in views:
    log.debug('Loading views from %s' % modulename)
    __import__(modulename)

########NEW FILE########
__FILENAME__ = helloworld
# This is a minimalist example of a clay view. Run it like so:
#
#   CLAY_CONFIG=simple-clay.conf clay-devserver
#
from __future__ import absolute_import
from clay import app


@app.route('/', methods=['GET'])
def hello():
    '''
    Ensures that the world is still there.
    '''
    return 'Hello World!'

########NEW FILE########
__FILENAME__ = test_database
from __future__ import absolute_import
import webtest.lint
import webtest
import threading
import os

os.environ['CLAY_CONFIG'] = 'config.json'

from clay import config, database
log = config.get_logger('clay.tests.database')


def test_database_cursor():
    with database.read as dbread:
        cur = dbread.cursor()
        cur.close()


def test_database_create_schema():
    with database.write as dbwrite:
        cur = dbwrite.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY NOT NULL,
                email TEXT NOT NULL
            )''')
        cur.execute('INSERT INTO users(email) VALUES("test@uber.com")')
        cur.close()
        dbwrite.commit()

    with database.read as dbread:
        cur = dbread.cursor()
        cur.execute('SELECT * FROM users WHERE id=1')
        assert cur.fetchone() == (1, 'test@uber.com')
        cur.close()


def test_database_threads():
    test_database_create_schema()

    def dbthread(num):
        with database.write as dbwrite:
            cur = dbwrite.cursor()
            cur.execute('INSERT INTO users(email) VALUES(?)', (str(num),))
            cur.close()
            dbwrite.commit()

        with database.read as dbread:
            cur = dbread.cursor()
            cur.execute('SELECT COUNT(*) FROM users')
            assert cur.fetchone()[0] > 1
            cur.close()

    threads = []
    for i in xrange(64):
        t = threading.Thread(target=dbthread, args=(i,))
        t.setDaemon(True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

########NEW FILE########
__FILENAME__ = test_hello_world
from __future__ import absolute_import
import webtest.lint
import webtest
import os

os.environ['CLAY_CONFIG'] = 'config.json'

from clay import app, config, http
import clay.wsgi
log = config.get_logger('clay.tests.hello_world')


# Test application
@app.route('/', methods=['GET'])
@http.cache_control(max_age=3600, public=True, no_cache="Cookies")
def hello_world():
    return 'Hello, world!'


# Test methods
app = clay.wsgi.application
app = webtest.lint.middleware(app)
app = webtest.TestApp(app)


def test_hello_world():
    res = app.get('/')
    assert res.status_int == 200
    assert res.body == 'Hello, world!'

def test_cache_control():
    res = app.get('/')
    assert res.headers['Cache-Control'] == 'max-age=3600, public, no-cache="Cookies"'

########NEW FILE########
__FILENAME__ = test_http
from __future__ import absolute_import

import httplib
import mock
import clay.config
from clay import http
import urllib2
import tempfile
import shutil
import os.path

from unittest import TestCase

s = mock.sentinel


class RequestTestCase(TestCase):
    def test_method_with_method(self):
        req = http.Request(url='http://www.uber.com', method=s.method)
        self.assertEqual(req.get_method(), s.method)

    def test_method_no_data(self):
        req = http.Request(url='http://www.uber.com', data=None)
        self.assertEqual(req.get_method(), 'GET')

    def test_method_data(self):
        req = http.Request(url='http://www.uber.com', data={'1': 2})
        self.assertEqual(req.get_method(), 'POST')


@mock.patch('ssl.get_server_certificate')
@mock.patch('urllib2.urlopen')
class LittleRequestTestCase(TestCase):
    def test_error_returns_response(self, mock_urlopen, mock_get_cert):
        e = urllib2.HTTPError('http://www.google.com', 404, 'Some message', {}, None)
        mock_urlopen.side_effect = e
        response = http.request('GET', 'http://www.google.com')
        self.assertEqual(response, http.Response(status=404, headers={}, data=None))

    def test_http_only(self, mock_urlopen, mock_get_cert):
        self.assertRaises(urllib2.URLError, http.request, 'GET', 'ftp://google.com')

    def test_good(self, mock_urlopen, mock_get_cert):
        mock_response = mock.Mock(name='resp')
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = s.body
        mock_response.headers = {}
        mock_urlopen.return_value = mock_response
        response = http.request('GET', 'http://www.google.com')
        self.assertEqual(response, http.Response(status=200, headers={}, data=s.body))

    def test_timeout_passed(self, mock_urlopen, mock_get_cert):
        http.request('GET', 'http://www.google.com', timeout=10)
        mock_urlopen.assert_called_once_with(mock.ANY, timeout=10)


def create_mock_http_connection():
    mock_conn = mock.Mock(name='https_connection')
    mock_resp = mock.Mock(name='https_response')
    mock_resp.read.return_value = ''
    mock_resp.recv.return_value = ''
    mock_resp.status = 200
    mock_resp.reason = 'A OK'
    mock_conn.getresponse.return_value = mock_resp
    conn = mock.MagicMock(spec=httplib.HTTPSConnection, return_value=mock_conn)
    return conn


@mock.patch('httplib.HTTPSConnection', new_callable=create_mock_http_connection)
@mock.patch('ssl.get_server_certificate')
class SSLTestCase(TestCase):
    def setUp(self, *args, **kwargs):
        self.wd = tempfile.mkdtemp()
        with open(os.path.join(self.wd, 'ca.crt'), 'w') as fd:
            fd.write('')

    def tearDown(self, *args, **kwargs):
        if self.wd is not None and os.path.exists(self.wd):
            shutil.rmtree(self.wd)

    def test_ssl_checks_if_enabled(self, mock_get_cert, mock_conn):
        config_dict = {
            'http': {
                'ca_certs_file': os.path.join(self.wd, 'ca.crt'),
                'verify_server_certificates': True,
            }
        }
        with mock.patch.dict(clay.config.CONFIG.config, config_dict):
            http.request('GET', 'https://www.google.com')
            mock_get_cert.assert_called_once_with(('www.google.com', 443), ca_certs=os.path.join(self.wd, 'ca.crt'))

    def test_ssl_checks_not_enabled(self, mock_get_cert, mock_conn):
        config_dict = {
            'http': {
                'ca_certs_file': os.path.join(self.wd, 'ca.crt'),
                'verify_server_certificates': False,
            }
        }
        with mock.patch.dict(clay.config.CONFIG.config, config_dict):
            http.request('GET', 'https://www.google.com')
            self.assertEqual(mock_get_cert.call_count, 0)

    def test_ssl_certs_disabled_if_no_file(self, mock_get_cert, mock_conn):
        config_dict = {
            'http': {
                'ca_certs_file': os.path.join(self.wd, 'does_not_exist.crt'),
                'verify_server_certificates': True,
            }
        }
        with mock.patch.dict(clay.config.CONFIG.config, config_dict):
            http.request('GET', 'https://www.google.com')
            self.assertEqual(mock_get_cert.call_count, 0)

    def test_ssl_checks_honored(self, mock_get_cert, mock_conn):
        config_dict = {
            'http': {
                'ca_certs_file': os.path.join(self.wd, 'ca.crt'),
                'verify_server_certificates': True,
            }
        }
        mock_get_cert.side_effect = ValueError('Invalid SSL certificate')
        with mock.patch.dict(clay.config.CONFIG.config, config_dict):
            self.assertRaises(ValueError, http.request, 'GET', 'https://www.google.com')
            mock_get_cert.assert_called_once_with(('www.google.com', 443), ca_certs=os.path.join(self.wd, 'ca.crt'))

########NEW FILE########
__FILENAME__ = test_mail
from __future__ import absolute_import

import mock
import os
import unittest

os.environ['CLAY_CONFIG'] = 'config.json'

from clay import config, mail
log = config.get_logger('clay.tests.mail')


class TestMail(unittest.TestCase):

    @mock.patch("smtplib.SMTP")
    def test_sendmail(self, mock_SMTP):
        mock_SMTP_instance = mock_SMTP.return_value

        mailto = 'fake@email.com'
        subject = 'This is a subject'
        message = 'This is a message'
        mail.sendmail(mailto, subject, message)

        args, kwargs = mock_SMTP_instance.sendmail.call_args
        from_header = config.get('smtp.from')
        self.assertEqual(from_header, args[0])
        self.assertIn(mailto, args[1])
        self.assertIn('To: %s' % mailto, args[2])
        self.assertIn('From: %s' % from_header, args[2])
        self.assertIn('Subject: %s' % subject, args[2])
        self.assertIn('Content-Type: text/html', args[2])

    @mock.patch("smtplib.SMTP")
    def test_sendmail_with_other_smtpconfig(self, mock_SMTP):
        mock_SMTP_instance = mock_SMTP.return_value

        mailto = 'otherfake@email.com'
        subject = 'This is another subject'
        message = 'This is another message'
        mail.sendmail(
            mailto,
            subject,
            message,
            smtpconfig=config.get('othersmtp'))

        args, kwargs = mock_SMTP_instance.sendmail.call_args
        from_header = config.get('othersmtp.from')
        self.assertEqual(from_header, args[0])
        self.assertIn(mailto, args[1])
        self.assertIn('To: %s' % mailto, args[2])
        self.assertIn('From: %s' % from_header, args[2])
        self.assertIn('Subject: %s' % subject, args[2])
        self.assertIn('Content-Type: text/html', args[2])

########NEW FILE########
__FILENAME__ = test_stats
from __future__ import absolute_import

import unittest
import socket
import os.path
import os
import re

os.environ['CLAY_CONFIG'] = 'config.json'

from clay import config, stats
log = config.get_logger('clay.tests.stats')


class MockTCPListener(object):
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(2)
        self.accepted = None
        self.buf = ''

    def readline(self):
        if not self.accepted:
            self.accepted, addr = self.sock.accept()
        while self.buf.find('\n') == -1:
            chunk = self.accepted.recv(1024)
            self.buf += chunk
        line, self.buf = self.buf.split('\n', 1)
        log.debug('mockserver.readline: %r' % line)
        return line

    def close(self):
        if self.buf:
            log.warning('Data still in mock server buffer at teardown: %r' % self.buf)
        self.sock.close()


socket.setdefaulttimeout(1.0)
mockserver = MockTCPListener(config.get('statsd.host'), config.get('statsd.port', 8125))

class TestStats(unittest.TestCase):
    def test_send(self):
        self.assertEqual(config.get('statsd.protocol'), 'tcp')
        stats.send('foo:1|c')
        line = mockserver.readline()
        self.assertEqual(line, 'foo:1|c')

    def test_timer_context(self):
        with stats.Timer('foo'):
            pass
        line = mockserver.readline()
        self.assertNotEqual(re.match('^foo:[0-9\.]+|ms$', line), None)
        self.assertNotEqual(line.split('|', 1)[0].split(':', 1)[1], '0.000000')

    def test_count(self):
        stats.count('foo', 1)
        line = mockserver.readline()
        self.assertEqual(line, 'foo:1|c')

    def test_count_sample(self):
        stats.count('foo', 1, 0.5)
        line = mockserver.readline()
        self.assertEqual(line, 'foo:1|c|@0.500000')

    def test_timing(self):
        stats.timing('foo', 10.5)
        line = mockserver.readline()
        self.assertEqual(line, 'foo:10.500000|ms')

    def test_gauge(self):
        stats.gauge('foo', 1)
        line = mockserver.readline()
        self.assertEqual(line, 'foo:1.000000|g')

    def test_unique_set(self):
        stats.unique_set('foo', 'bar')
        line = mockserver.readline()
        self.assertEqual(line, 'foo:bar|s')

    def test_wrapper(self):
        @stats.wrapper('foo')
        def foofunc(arg):
            self.assertTrue(arg)
            return arg

        foofunc(True)
        lines = [mockserver.readline() for i in range(2)]
        self.assertIn('foo.calls:1|c', lines)
        self.assertNotIn('foo.exceptions:1|c', lines)
        self.assertEqual(len([x for x in lines if re.match('^foo.duration:[0-9\.]+|ms$', x)]), 1)

########NEW FILE########
