__FILENAME__ = app
#!/usr/bin/python
# -*- coding: utf-8 -*-

import tornado.web
import tornado.ioloop

from r3.app.handlers.healthcheck import HealthcheckHandler
from r3.app.handlers.stream import StreamHandler
from r3.app.handlers.index import IndexHandler
from r3.app.utils import kls_import

class R3ServiceApp(tornado.web.Application):

    def __init__(self, redis, config, log_level, debug, show_index_page):
        self.redis = redis
        self.log_level = log_level
        self.config = config
        self.debug = debug

        handlers = [
            (r'/healthcheck', HealthcheckHandler),
        ]

        if show_index_page:
            handlers.append(
                (r'/', IndexHandler)
            )

        handlers.append(
            (r'/stream/(?P<job_key>.+)/?', StreamHandler),
        )

        self.redis.delete('r3::mappers')

        self.load_input_streams()
        self.load_reducers()

        super(R3ServiceApp, self).__init__(handlers, debug=debug)

    def load_input_streams(self):
        self.input_streams = {}

        if hasattr(self.config, 'INPUT_STREAMS'):
            for stream_class in self.config.INPUT_STREAMS:
                stream = kls_import(stream_class)
                self.input_streams[stream.job_type] = stream()

    def load_reducers(self):
        self.reducers = {}

        if hasattr(self.config, 'REDUCERS'):
            for reducer_class in self.config.REDUCERS:
                reducer = kls_import(reducer_class)
                self.reducers[reducer.job_type] = reducer()



########NEW FILE########
__FILENAME__ = config
#!/usr/bin/python
# -*- coding: utf-8 -*-

from os.path import isabs, abspath
import imp

class Config:
    def __init__(self, path):
        if not isabs(path):
            self.path = abspath(path)
        else:
            self.path = path

        self.load()

    def load(self):
        with open(self.path) as config_file:
            name = 'configuration'
            code = config_file.read()
            module = imp.new_module(name)
            exec code in module.__dict__

            for name, value in module.__dict__.iteritems():
                setattr(self, name, value)



########NEW FILE########
__FILENAME__ = healthcheck
#!/usr/bin/python
# -*- coding: utf-8 -*-

from r3.app.handlers import BaseHandler

class HealthcheckHandler(BaseHandler):
    def get(self):
        self.write('WORKING')


########NEW FILE########
__FILENAME__ = index
#!/usr/bin/python
# -*- coding: utf-8 -*-

from r3.app.handlers import BaseHandler
from r3.app.keys import MAPPERS_KEY
from r3.version import __version__

class IndexHandler(BaseHandler):
    def get(self):
        has_reducers = len(self.application.reducers.keys()) > 0

        self.render(
            "../templates/index.html", 
            title="",
            r3_version=__version__,
            input_streams=self.application.input_streams.keys(),
            has_reducers=has_reducers,
            mappers=self.get_mappers()
        )

    def get_mappers(self):
        return self.redis.smembers(MAPPERS_KEY)



########NEW FILE########
__FILENAME__ = stream
#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
from uuid import uuid4
from ujson import dumps, loads
from datetime import datetime

import tornado.web
import tornado.gen

from r3.app.handlers import BaseHandler
from r3.app.utils import DATETIME_FORMAT
from r3.app.keys import PROCESSED, PROCESSED_FAILED, PROCESSED_SUCCESS, JOB_TYPE_KEY, MAPPER_INPUT_KEY, MAPPER_OUTPUT_KEY, MAPPER_ERROR_KEY

class StreamHandler(BaseHandler):
    def group_items(self, stream_items, group_size):
        items = []
        current_item = []
        items.append(current_item)
        for stream_item in stream_items:
            if len(current_item) == group_size:
                current_item = []
                items.append(current_item)
            current_item.append(stream_item)
        return items

    @tornado.web.asynchronous
    def get(self, job_key):
        arguments = self.request.arguments
        job_id = uuid4()
        job_date = datetime.now()

        job_type_input_queue = JOB_TYPE_KEY % job_key
        self.redis.sadd(job_type_input_queue, str(job_id))

        try:
            start = time.time()
            input_stream = self.application.input_streams[job_key]
            items = input_stream.process(self.application, arguments)
            if hasattr(input_stream, 'group_size'):
                items = self.group_items(items, input_stream.group_size)

            mapper_input_queue = MAPPER_INPUT_KEY % job_key
            mapper_output_queue = MAPPER_OUTPUT_KEY % (job_key, job_id)
            mapper_error_queue = MAPPER_ERROR_KEY % job_key

            with self.redis.pipeline() as pipe:
                start = time.time()

                for item in items:
                    msg = {
                        'output_queue': mapper_output_queue,
                        'job_id': str(job_id),
                        'job_key': job_key,
                        'item': item,
                        'date': job_date.strftime(DATETIME_FORMAT),
                        'retries': 0
                    }
                    pipe.rpush(mapper_input_queue, dumps(msg))
                pipe.execute()
            logging.debug("input queue took %.2f" % (time.time() - start))

            start = time.time()
            results = []
            errored = False
            while (len(results) < len(items)):
                key, item = self.redis.blpop(mapper_output_queue)
                json_item = loads(item)
                if 'error' in json_item:
                    json_item['retries'] -= 1
                    self.redis.hset(mapper_error_queue, json_item['job_id'], dumps(json_item))
                    errored = True
                    break
                results.append(loads(json_item['result']))

            self.redis.delete(mapper_output_queue)
            logging.debug("map took %.2f" % (time.time() - start))

            if errored:
                self.redis.incr(PROCESSED)
                self.redis.incr(PROCESSED_FAILED)
                self._error(500, 'Mapping failed. Check the error queue.')
            else:
                start = time.time()
                reducer = self.application.reducers[job_key]
                result = reducer.reduce(self.application, results)
                logging.debug("reduce took %.2f" % (time.time() - start))

                self.set_header('Content-Type', 'application/json')

                self.write(dumps(result))

                self.redis.incr(PROCESSED)
                self.redis.incr(PROCESSED_SUCCESS)
 
                self.finish()
        finally:
            self.redis.srem(job_type_input_queue, str(job_id))


########NEW FILE########
__FILENAME__ = keys
#!/usr/bin/python
# -*- coding: utf-8 -*-

ALL_KEYS = 'r3::*'

# MAPPER KEYS
MAPPERS_KEY = 'r3::mappers'
MAPPER_INPUT_KEY = 'r3::jobs::%s::input'
MAPPER_OUTPUT_KEY = 'r3::jobs::%s::%s::output'
MAPPER_ERROR_KEY = 'r3::jobs::%s::errors'
MAPPER_WORKING_KEY = 'r3::jobs::%s::working'
LAST_PING_KEY = 'r3::mappers::%s::last-ping'

# JOB TYPES KEYS
JOB_TYPES_KEY = 'r3::job-types'
JOB_TYPES_ERRORS_KEY = 'r3::jobs::*::errors'
JOB_TYPE_KEY = 'r3::job-types::%s'

# STATS KEYS
PROCESSED = 'r3::stats::processed'
PROCESSED_SUCCESS = 'r3::stats::processed::success'
PROCESSED_FAILED = 'r3::stats::processed::fail'


########NEW FILE########
__FILENAME__ = server
#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import logging
import argparse

import tornado.ioloop
from tornado.httpserver import HTTPServer
import redis

from r3.app.app import R3ServiceApp
from r3.app.config import Config


def main(arguments=None):
    '''Runs r³ server with the specified arguments.'''

    parser = argparse.ArgumentParser(description='runs the application that processes stream requests for r³')
    parser.add_argument('-b', '--bind', type=str, default='0.0.0.0', help='the ip that r³ will bind to')
    parser.add_argument('-p', '--port', type=int, default=9999, help='the port that r³ will bind to')
    parser.add_argument('-l', '--loglevel', type=str, default='warning', help='the log level that r³ will run under')
    parser.add_argument('-i', '--hide-index-page', action='store_true', default=False, help='indicates whether r³ app should show the help page')
    parser.add_argument('-d', '--debug', action='store_true', default=False, help='indicates whether r³ app should run in debug mode')
    parser.add_argument('--redis-host', type=str, default='0.0.0.0', help='the ip that r³ will use to connect to redis')
    parser.add_argument('--redis-port', type=int, default=6379, help='the port that r³ will use to connect to redis')
    parser.add_argument('--redis-db', type=int, default=0, help='the database that r³ will use to connect to redis')
    parser.add_argument('--redis-pass', type=str, default='', help='the password that r³ will use to connect to redis')
    parser.add_argument('-c', '--config-file', type=str, help='the config file that r³ will use to load input stream classes and reducers', required=True)

    args = parser.parse_args(arguments)

    cfg = Config(args.config_file)

    c = redis.StrictRedis(host=args.redis_host, port=args.redis_port, db=args.redis_db, password=args.redis_pass)

    logging.basicConfig(level=getattr(logging, args.loglevel.upper()))

    application = R3ServiceApp(redis=c, config=cfg, log_level=args.loglevel.upper(), debug=args.debug, show_index_page=not args.hide_index_page)

    server = HTTPServer(application)
    server.bind(args.port, args.bind)
    server.start(1)

    try:
        logging.debug('r³ service app running at %s:%d' % (args.bind, args.port))
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print
        print "-- r³ service app closed by user interruption --"

if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from datetime import datetime

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
TIMEOUT = 15

def real_import(name):
    if '.'  in name:
        return reduce(getattr, name.split('.')[1:], __import__(name))
    return __import__(name)

logger = logging.getLogger('R3ServiceApp')

def flush_dead_mappers(redis, mappers_key, ping_key):
    mappers = redis.smembers(mappers_key)
    for mapper in mappers:
        last_ping = redis.get(ping_key % mapper)
        if last_ping:
            now = datetime.now()
            last_ping = datetime.strptime(last_ping, DATETIME_FORMAT)
            if ((now - last_ping).seconds > TIMEOUT):
                logging.warning('MAPPER %s found to be inactive after %d seconds of not pinging back' % (mapper, TIMEOUT))
                redis.srem(mappers_key, mapper)
                redis.delete(ping_key % mapper)


def kls_import(fullname):
    if not '.' in fullname:
        return __import__(fullname)

    name_parts = fullname.split('.')
    klass_name = name_parts[-1]
    module_parts = name_parts[:-1]
    module = reduce(getattr, module_parts[1:], __import__('.'.join(module_parts)))
    klass = getattr(module, klass_name)
    return klass



########NEW FILE########
__FILENAME__ = version
#!/usr/bin/python
# -*- coding: utf-8 -*-

__version__ = '0.2.0'
version = __version__
VERSION = __version__

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, g, redirect, url_for
from ujson import loads

from r3.version import __version__
from r3.app.utils import flush_dead_mappers
from r3.app.keys import MAPPERS_KEY, JOB_TYPES_KEY, JOB_TYPE_KEY, LAST_PING_KEY, MAPPER_ERROR_KEY, MAPPER_WORKING_KEY, JOB_TYPES_ERRORS_KEY, ALL_KEYS, PROCESSED, PROCESSED_FAILED

app = Flask(__name__)

def server_context():
    return {
        'r3_service_status': 'running',
        'r3_version': __version__
    }

@app.before_request
def before_request():
    g.config = app.config
    g.server = server_context()
    g.job_types = app.db.connection.smembers(JOB_TYPES_KEY)
    g.jobs = get_all_jobs(g.job_types)
    g.mappers = get_mappers()

def get_mappers():
    all_mappers = app.db.connection.smembers(MAPPERS_KEY)
    mappers_status = {}
    for mapper in all_mappers:
        key = MAPPER_WORKING_KEY % mapper
        working = app.db.connection.lrange(key, 0, -1)
        if not working:
            mappers_status[mapper] = None
        else:
            mappers_status[mapper] = loads(working[0])

    return mappers_status

def get_all_jobs(all_job_types):
    all_jobs = {}
    for job_type in all_job_types:
        job_type_jobs = app.db.connection.smembers(JOB_TYPE_KEY % job_type)
        all_jobs[job_type] = []
        if job_type_jobs:
            all_jobs[job_type] = job_type_jobs

    return all_jobs

def get_errors():
    errors = []
    for job_type in g.job_types:
        errors = [loads(item) for key, item in app.db.connection.hgetall(MAPPER_ERROR_KEY % job_type).iteritems()]

    return errors

@app.route("/")
def index():
    error_queues = app.db.connection.keys(JOB_TYPES_ERRORS_KEY)

    has_errors = False
    for queue in error_queues:
        if app.db.connection.hlen(queue) > 0:
            has_errors = True

    flush_dead_mappers(app.db.connection, MAPPERS_KEY, LAST_PING_KEY)

    return render_template('index.html', failed_warning=has_errors)

@app.route("/mappers")
def mappers():
    flush_dead_mappers(app.db.connection, MAPPERS_KEY, LAST_PING_KEY)
    return render_template('mappers.html')

@app.route("/failed")
def failed():
    return render_template('failed.html', errors=get_errors())

@app.route("/failed/delete")
def delete_all_failed():
    for job_type in g.job_types:
        key = MAPPER_ERROR_KEY % job_type
        app.db.connection.delete(key)

    return redirect(url_for('failed'))

@app.route("/failed/delete/<job_id>")
def delete_failed(job_id):
    for job_type in g.job_types:
        key = MAPPER_ERROR_KEY % job_type
        if app.db.connection.hexists(key, job_id):
            app.db.connection.hdel(key, job_id)

    return redirect(url_for('failed'))

@app.route("/job-types")
def job_types():
    return render_template('job-types.html')

@app.route("/stats")
def stats():
    info = app.db.connection.info()
    key_names = app.db.connection.keys(ALL_KEYS)

    keys = []
    for key in key_names:
        key_type = app.db.connection.type(key)

        if key_type == 'list':
            size = app.db.connection.llen(key)
        elif key_type == 'set':
            size = app.db.connection.scard(key)
        else:
            size = 1

        keys.append({
            'name': key,
            'size': size,
            'type': key_type
        })

    processed = app.db.connection.get(PROCESSED)
    processed_failed = app.db.connection.get(PROCESSED_FAILED)

    return render_template('stats.html', info=info, keys=keys, processed=processed, failed=processed_failed)

@app.route("/stats/keys/<key>")
def key(key):
    key_type = app.db.connection.type(key)

    if key_type == 'list':
        value = app.db.connection.lrange(key, 0, -1)
        multi = True
    elif key_type == 'set':
        value = app.db.connection.smembers(key)
        multi = True
    else:
        value = app.db.connection.get(key)
        multi = False

    return render_template('show_key.html', key=key, multi=multi, value=value)

@app.route("/stats/keys/<key>/delete")
def delete_key(key):
    app.db.connection.delete(key)
    return redirect(url_for('stats'))
 
#if __name__ == "__main__":
    #app.config.from_object('r3.web.config')
    #db = RedisDB(app)
    #app.run(debug=True, host=app.config['WEB_HOST'], port=app.config['WEB_PORT'])


########NEW FILE########
__FILENAME__ = config
#!/usr/bin/python
# -*- coding: utf-8 -*-

DEBUG = True
SECRET_KEY = 'development key'

WEB_HOST = '0.0.0.0'
WEB_PORT = 8888

REDIS_HOST = 'localhost'
REDIS_PORT = 7778
REDIS_PASS = 'r3'

########NEW FILE########
__FILENAME__ = extensions
#!/usr/bin/python
# -*- coding: utf-8 -*-

import redis

from flask import _app_ctx_stack as stack

class RedisDB(object):

    def __init__(self, app=None):
        if app is not None:
            self.app = app
            self.init_app(self.app)
        else:
            self.app = None

    def init_app(self, app):
        app.config.setdefault('REDIS_HOST', '0.0.0.0')
        app.config.setdefault('REDIS_PORT', 6379)
        app.config.setdefault('REDIS_DB', 0)
        app.config.setdefault('REDIS_PASS', None)

        # Use the newstyle teardown_appcontext if it's available,
        # otherwise fall back to the request context
        if hasattr(app, 'teardown_appcontext'):
            app.teardown_appcontext(self.teardown)
        else:
            app.teardown_request(self.teardown)

    def connect(self):
        options = {
            'host': self.app.config['REDIS_HOST'],
            'port': self.app.config['REDIS_PORT'],
            'db': self.app.config['REDIS_DB']
        }

        if self.app.config['REDIS_PASS']:
            options['password'] = self.app.config['REDIS_PASS']

        conn = redis.StrictRedis(**options)
        return conn

    def teardown(self, exception):
        ctx = stack.top
        if hasattr(ctx, 'redis_db'):
            del ctx.redis_db

    @property
    def connection(self):
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'redis_db'):
                ctx.redis_db = self.connect()
            return ctx.redis_db

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
from os.path import abspath, isabs, join
import logging
import argparse

from r3.web.app import app
from r3.web.extensions import RedisDB

def main(arguments=None):
    '''Runs r³ web app with the specified arguments.'''

    parser = argparse.ArgumentParser(description='runs the web admin that helps in monitoring r³ usage')
    parser.add_argument('-b', '--bind', type=str, default='0.0.0.0', help='the ip that r³ will bind to')
    parser.add_argument('-p', '--port', type=int, default=8888, help='the port that r³ will bind to')
    parser.add_argument('-l', '--loglevel', type=str, default='warning', help='the log level that r³ will run under')
    parser.add_argument('--redis-host', type=str, default='0.0.0.0', help='the ip that r³ will use to connect to redis')
    parser.add_argument('--redis-port', type=int, default=6379, help='the port that r³ will use to connect to redis')
    parser.add_argument('--redis-db', type=int, default=0, help='the database that r³ will use to connect to redis')
    parser.add_argument('--redis-pass', type=str, default='', help='the password that r³ will use to connect to redis')
    parser.add_argument('-c', '--config-file', type=str, default='', help='the configuration file that r³ will use')
    parser.add_argument('-d', '--debug', default=False, action='store_true', help='indicates that r³ will be run in debug mode')

    args = parser.parse_args(arguments)

    logging.basicConfig(level=getattr(logging, args.loglevel.upper()))

    if args.config_file:
        config_path = args.config_file
        if not isabs(args.config_file):
            config_path = abspath(join(os.curdir, args.config_file))

        app.config.from_pyfile(config_path, silent=False)
    else:
        app.config.from_object('r3.web.config')

    app.db = RedisDB(app)
    try:
        logging.debug('r³ web app running at %s:%d' % (args.bind, args.port))
        app.run(debug=args.debug, host=app.config['WEB_HOST'], port=app.config['WEB_PORT'])
    except KeyboardInterrupt:
        print
        print "-- r³ web app closed by user interruption --"

if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = mapper
#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime
import signal
import logging
import sys
import os
import argparse

import redis
from ujson import loads, dumps

from r3.app.utils import DATETIME_FORMAT, kls_import
from r3.app.keys import MAPPERS_KEY, JOB_TYPES_KEY, MAPPER_INPUT_KEY, MAPPER_WORKING_KEY, LAST_PING_KEY

class JobError(RuntimeError):
    pass

class CrashError(JobError):
    pass

class TimeoutError(JobError):
    pass

class Mapper:
    def __init__(self, job_type, mapper_key, redis_host, redis_port, redis_db, redis_pass):
        self.job_type = job_type
        self.mapper_key = mapper_key
        self.full_name = '%s::%s' % (self.job_type, self.mapper_key)
        self.timeout = None
        self.input_queue = MAPPER_INPUT_KEY % self.job_type
        self.working_queue = MAPPER_WORKING_KEY % self.full_name
        self.max_retries = 5

        self.redis = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db, password=redis_pass)

        logging.basicConfig(level=getattr(logging, 'WARNING'))
        self.initialize()
        logging.debug("Mapper UP - pid: %s" % os.getpid())
        logging.debug("Input Q: %s" % self.input_queue)
        logging.debug("Working Q: %s" % self.working_queue)

    def handle_signal(self, number, stack):
        self.unregister()
        sys.exit(number)

    def initialize(self):
        signal.signal(signal.SIGTERM, self.handle_signal)
        self.ping()

        item = self.redis.rpop(self.working_queue)
        if item:
            json_item = loads(item)
            json_item['retries'] += 1

            if json_item['retries'] > self.max_retries:
                json_item['error'] = '%s errored out after %d retries.' % (self.full_name, json_item['retries'])
                self.redis.rpush(json_item['output_queue'], dumps(json_item))
            else:
                item = dumps(json_item)
                self.map_item(item, json_item)

    def map(self):
        raise NotImplementedError()

    def run_block(self):
        try:
            while True:
                self.ping()
                logging.debug('waiting to process next item...')
                values = self.redis.brpop(self.input_queue, timeout=5)
                if values:
                    key, item = values
                    json_item = loads(item)
                    self.map_item(item, json_item)
        finally:
            self.unregister()

    def unregister(self):
        self.redis.srem(MAPPERS_KEY, self.full_name)
        self.redis.delete(LAST_PING_KEY % self.full_name)

    def ping(self):
        self.redis.delete(MAPPER_WORKING_KEY % self.full_name)
        self.redis.sadd(JOB_TYPES_KEY, self.job_type)
        self.redis.sadd(MAPPERS_KEY, self.full_name)
        self.redis.set(LAST_PING_KEY % self.full_name, datetime.now().strftime(DATETIME_FORMAT))

    def map_item(self, item, json_item):
        self.redis.set('r3::mappers::%s::working' % self.full_name, json_item['job_id'])
        self.redis.rpush(self.working_queue, item)
        result = dumps(self.map(json_item['item']))
        self.redis.rpush(json_item['output_queue'], dumps({
            'result': result
        }))
        self.redis.delete(self.working_queue)
        self.redis.delete('r3::mappers::%s::working' % self.full_name)

def main(arguments=None):
    if not arguments:
        arguments = sys.argv[1:]

    parser = argparse.ArgumentParser(description='runs the application that processes stream requests for r³')
    parser.add_argument('-l', '--loglevel', type=str, default='warning', help='the log level that r³ will run under')
    parser.add_argument('--redis-host', type=str, default='0.0.0.0', help='the ip that r³ will use to connect to redis')
    parser.add_argument('--redis-port', type=int, default=6379, help='the port that r³ will use to connect to redis')
    parser.add_argument('--redis-db', type=int, default=0, help='the database that r³ will use to connect to redis')
    parser.add_argument('--redis-pass', type=str, default='', help='the password that r³ will use to connect to redis')
    parser.add_argument('--mapper-key', type=str, help='the unique identifier for this mapper', required=True)
    parser.add_argument('--mapper-class', type=str, help='the fullname of the class that this mapper will run', required=True)

    args = parser.parse_args(arguments)

    if not args.mapper_key:
        raise RuntimeError('The --mapper_key argument is required.')

    logging.basicConfig(level=getattr(logging, args.loglevel.upper()))

    try:
        klass = kls_import(args.mapper_class)
    except Exception, err:
        print "Could not import the specified %s class. Error: %s" % (args.mapper_class, err)
        raise

    mapper = klass(klass.job_type, args.mapper_key, redis_host=args.redis_host, redis_port=args.redis_port, redis_db=args.redis_db, redis_pass=args.redis_pass)
    try:
        mapper.run_block()
    except KeyboardInterrupt:
        print
        print "-- r³ mapper closed by user interruption --"


if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = app_config
#!/usr/bin/python
# -*- coding: utf-8 -*-

INPUT_STREAMS = [
    'test.count_words_stream.CountWordsStream'
]

REDUCERS = [
    'test.count_words_reducer.CountWordsReducer'
]

########NEW FILE########
__FILENAME__ = count_words_mapper
#!/usr/bin/python
# -*- coding: utf-8 -*-

from r3.worker.mapper import Mapper

class CountWordsMapper(Mapper):
    job_type = 'count-words'

    def map(self, lines):
        #time.sleep(0.5)
        return list(self.split_words(lines))

    def split_words(self, lines):
        for line in lines:
            for word in line.split():
                yield word.strip().strip('.').strip(','), 1

########NEW FILE########
__FILENAME__ = count_words_reducer
#!/usr/bin/python
# -*- coding: utf-8 -*-

from collections import defaultdict

class CountWordsReducer:
    job_type = 'count-words'

    def reduce(self, app, items):
        word_freq = defaultdict(int)
        for line in items:
            for word, frequency in line:
                word_freq[word] += frequency

        return word_freq

########NEW FILE########
__FILENAME__ = count_words_stream
#!/usr/bin/python
# -*- coding: utf-8 -*-

from os.path import abspath, dirname, join

class CountWordsStream:
    job_type = 'count-words'
    group_size = 1000

    def process(self, app, arguments):
        with open(abspath(join(dirname(__file__), 'chekhov.txt'))) as f:
            contents = f.readlines()

        return [line.lower() for line in contents]



########NEW FILE########
__FILENAME__ = test_count_words
#!/usr/bin/python
# -*- coding: utf-8 -*-

import time

from count_words_stream import CountWordsStream
from count_words_reducer import CountWordsReducer

class CountWordsMapper:
    def map(self, lines):
        #time.sleep(0.5)
        return list(self.split_words(lines))

    def split_words(self, lines):
        for line in lines:
            for word in line.split():
                yield word.strip().strip('.').strip(','), 1


def main():
    start = time.time()
    items = CountWordsStream().process(None, None)
    print "input stream took %.2f" % (time.time() - start)

    start = time.time()
    mapper = CountWordsMapper()
    results = []
    for item in items:
        results.append(mapper.map(item))
    print "mapping took %.2f" % (time.time() - start)

    start = time.time()
    CountWordsReducer().reduce(None, results)
    print "reducing took %.2f" % (time.time() - start)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_sync

########NEW FILE########
