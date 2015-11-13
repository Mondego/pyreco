__FILENAME__ = querycount
"""
perftools.middleware.querycount
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import logging
import threading

from django.core.handlers.wsgi import WSGIRequest
from perftools.middleware import Base
from perftools.patcher import Patcher


class State(threading.local):
    def __init__(self):
        self.count = 0
        self.queries = []


class CursorWrapper(object):
    def __init__(self, cursor, connection, state, queries=False):
        self.cursor = cursor
        self.connection = connection
        self._state = state
        self._queries = queries

    def _incr(self, sql, params):
        if self._queries:
            self._state.queries.append((sql, params))
        self._state.count += 1

    def execute(self, sql, params=()):
        try:
            return self.cursor.execute(sql, params)
        finally:
            self._incr(sql, params)

    def executemany(self, sql, paramlist):
        try:
            return self.cursor.executemany(sql, paramlist)
        finally:
            self._incr(sql, paramlist)

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.cursor)


def get_cursor_wrapper(state, queries=False):
    def cursor(func, self, *args, **kwargs):
        result = func(self, *args, **kwargs)

        return CursorWrapper(result, self, state, queries=queries)
    return cursor


class QueryCountLoggingMiddleware(Base):
    def __init__(self, application, threshold=1, stacks=False, queries=False, logger=None, **kwargs):
        self.application = application
        self.threshold = threshold
        self.stacks = stacks
        self.logger = logger or logging.getLogger(__name__)
        self.queries = queries
        super(QueryCountLoggingMiddleware, self).__init__(application, **kwargs)

    def __call__(self, environ, start_response):
        if not self.should_run(environ):
            return self.application(environ, start_response)

        state = State()
        cursor = get_cursor_wrapper(state, queries=self.queries)

        with Patcher('django.db.backends.BaseDatabaseWrapper.cursor', cursor):
            try:
                return list(self.application(environ, start_response))
            finally:
                if state.count > self.threshold:
                    self.log_request(WSGIRequest(environ), state)

    def log_request(self, request, state):
        url = request.build_absolute_uri()

        self.logger.warning('Request exceeeded query count threshold: %s', url, extra={
            'request': request,
            'stack': self.stacks,
            'url': url,
            'data': {
                'threshold': self.threshold,
                'query_count': state.count,
                'queries': [(k, repr(v)) for k, v in state.queries],
            }
        })

########NEW FILE########
__FILENAME__ = remoteprof
"""
perftools.middleware.remoteprof
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import cProfile
import logging
import os.path
import socket
import simplejson
import thread
import time

from perftools.middleware import Base


class RemoteProfilingMiddleware(Base):
    logger = logging.getLogger(__name__)

    def __init__(self, application, outpath, threshold=0.5, **kwargs):
        self.application = application
        self.outpath = outpath
        self.threshold = threshold
        self.hostname = socket.gethostname()
        super(RemoteProfilingMiddleware, self).__init__(application, **kwargs)

    def __call__(self, environ, start_response):
        self.reqnum += 1
        if not self.should_run(environ):
            return self.application(environ, start_response)

        profile = cProfile.Profile()

        start = time.time()
        try:
            return list(profile.runcall(self.application, environ, start_response))
        finally:
            stop = time.time()
            try:
                if (stop - start) > self.threshold:
                    self.report_result(profile, environ, start, stop, self.outpath)
            except Exception, e:
                self.logger.exception(e)

    def report_result(self, profile, environ, start, stop, outpath):
        thread_ident = thread.get_ident()
        ts_parts = map(lambda x: str(int(x)), divmod(start, 100000))
        outpath = os.path.join(self.outpath, ts_parts[0], ts_parts[1])
        outfile_base = '%s-%s' % (self.reqnum, thread_ident)

        if not os.path.exists(outpath):
            os.makedirs(outpath)

        profile.dump_stats(os.path.join(outpath, outfile_base + '.profile'))

        with open(os.path.join(outpath, outfile_base + '.json'), 'w') as fp:
            fp.write(simplejson.dumps({
                'environ': dict((k, v) for k, v in environ.iteritems() if isinstance(v, basestring)),
                'start_time': start,
                'stop_time': stop,
                'request_number': self.reqnum,
                'thread_ident': thread_ident,
                'hostname': self.hostname,
            }, indent=2))

########NEW FILE########
__FILENAME__ = slowreq
"""
perftools.middleware.slowreq
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import inspect
import logging
import thread
import threading

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest

from perftools.middleware import Base
from perftools.utils import get_culprit

try:
    # Available from Python >= 2.5
    from sys import _current_frames as threadframe
except ImportError:
    import threadframe as _threadframe
    # Wrapper to provide the same interface as the one from Python >= 2.5
    threadframe = lambda: _threadframe.dict()


class SlowRequestLoggingMiddleware(Base):
    def __init__(self, application, threshold=1, stacks=True, logger=None, **kwargs):
        self.application = application
        self.threshold = float(threshold) / 1000
        self.stacks = stacks
        self.logger = logger or logging.getLogger(__name__)
        super(SlowRequestLoggingMiddleware, self).__init__(application, **kwargs)

    def __call__(self, environ, start_response):
        if not self.should_run(environ):
            return self.application(environ, start_response)

        request = WSGIRequest(environ)

        timer = threading.Timer(self.threshold, self.log_request, args=[thread.get_ident(), request])
        timer.start()

        try:
            return list(self.application(environ, start_response))
        finally:
            timer.cancel()

    def get_parent_frame(self, parent_id):
        return threadframe()[parent_id]

    def get_frames(self, frame):
        return inspect.getouterframes(frame)

    def log_request(self, parent_id, request):
        try:
            parent_frame = self.get_parent_frame(parent_id)
        except KeyError:
            frames = []
            culprit = None
        else:
            frames = self.get_frames(parent_frame)
            culprit = get_culprit(frames, settings.INSTALLED_APPS)

        url = request.build_absolute_uri()

        self.logger.warning('Request exceeeded execution time threshold: %s', url, extra={
            'request': request,
            'view': culprit,
            'stack': frames,
            'url': url,
            'data': {
                'threshold': self.threshold,
            }
        })

########NEW FILE########
__FILENAME__ = patcher
def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def import_string(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


class Patcher(object):
    def __init__(self, target, callback):
        target, attribute = target.rsplit('.', 1)
        self.target = import_string(target)
        self.attribute = attribute
        self.callback = callback

    def __enter__(self, *args, **kwargs):
        self.original = getattr(self.target, self.attribute)

        def wrapped(*args, **kwargs):
            return self.callback(self.original, *args, **kwargs)
        wrapped.__name__ = self.attribute

        setattr(self.target, self.attribute, wrapped)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        setattr(self.target, self.attribute, self.original)


def patch(target):
    """
    from disqus.utils import monkey

    @monkey.patch('psycopg2.connect')
    def psycopg2_connect(func, *args, **kwargs):
        print "Zomg im connecting!!!!"
        return func(*args, **kwargs)
    """
    target, attribute = target.rsplit('.', 1)
    target = import_string(target)
    func = getattr(target, attribute)

    def inner(callback):
        if getattr(func, '__patcher__', False):
            return func

        def wrapped(*args, **kwargs):
            return callback(func, *args, **kwargs)

        actual = getattr(func, '__wrapped__', func)
        wrapped.__wrapped__ = actual
        wrapped.__doc__ = getattr(actual, '__doc__', None)
        wrapped.__name__ = actual.__name__
        wrapped.__patcher__ = True

        setattr(target, attribute, wrapped)
        return wrapped
    return inner

########NEW FILE########
__FILENAME__ = utils
def contains(iterator, value):
    for k in iterator:
        if value.startswith(k):
            return True
    return False


def get_culprit(frames, modules=[]):
    best_guess = None
    for frame in frames:
        try:
            culprit = '.'.join([frame.f_globals['__name__'], frame.f_code.co_name])
        except:
            continue
        if contains(modules, culprit):
            if not best_guess:
                best_guess = culprit
        elif best_guess:
            break

    return best_guess

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
import logging
import os.path
import pstats
import shutil
import sys
import time
import unittest2

from perftools.middleware.slowreq import SlowRequestLoggingMiddleware
from perftools.middleware.remoteprof import RemoteProfilingMiddleware
from perftools.patcher import patch

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        DATABASES={
            'default': {
                'ENGINE': 'sqlite3',
            },
        },
        INSTALLED_APPS=['tests'],
        ROOT_URLCONF='',
        DEBUG=False,
        TEMPLATE_DEBUG=True,
    )


class MockApp(object):
    def __init__(self, wait=0):
        self.wait = wait

    def __call__(self, environ, start_response):
        if self.wait:
            time.sleep(self.wait)
        return start_response()


class SlowRequestLoggingMiddlewareTest(unittest2.TestCase):
    def setUp(self):
        self.captured_logs = []

        class CaptureHandler(logging.Handler):
            def __init__(self, inst, level=logging.NOTSET):
                self.inst = inst
                super(CaptureHandler, self).__init__(level=level)

            def emit(self, record):
                self.inst.captured_logs.append(record)

        logger = logging.getLogger('perftools')
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            logger.removeHandler(handler)
        logger.addHandler(CaptureHandler(self))

    def test_blocking(self):
        app = SlowRequestLoggingMiddleware(MockApp(wait=0.1), threshold=1)
        response = list(app({
            'REMOTE_ADDR': '127.0.0.1',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'test',
            'SERVER_PORT': '80',
            'wsgi.input': sys.stdin,
        }, lambda: ''))
        self.assertEquals(response, list(''))
        self.assertEquals(len(self.captured_logs), 1)

        record = self.captured_logs[0]
        self.assertEquals(record.levelno, logging.WARNING)

        self.assertTrue(hasattr(record, 'request'))
        request = record.request
        self.assertTrue('SERVER_NAME' in request.META)
        self.assertEquals(request.META['SERVER_NAME'], 'test')

        self.assertTrue(hasattr(record, 'view'))
        self.assertEquals(record.view, 'tests.tests.test_blocking')


class AlwaysProfileMiddleware(RemoteProfilingMiddleware):
    def should_run(self, environ):
        return True


class RemoteProfilingMiddlewareMiddlewareTest(unittest2.TestCase):
    def setUp(self):
        self.outpath = os.path.join(os.path.dirname(__file__), 'profiles')

    def tearDown(self):
        try:
            shutil.rmtree(self.outpath)
        except:
            pass

    def test_blocking(self):
        app = AlwaysProfileMiddleware(MockApp(wait=0.1), outpath=self.outpath)
        response = list(app({
            'REMOTE_ADDR': '127.0.0.1',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'test',
            'SERVER_PORT': '80',
            'wsgi.input': sys.stdin,
        }, lambda: ''))

        self.assertEquals(response, list(''))
        dirs = os.listdir(self.outpath)
        self.assertEquals(len(dirs), 1)
        dirs_2 = os.listdir(os.path.join(self.outpath, dirs[0]))
        self.assertEquals(len(dirs_2), 1)
        dirs_3 = os.listdir(os.path.join(self.outpath, dirs[0], dirs_2[0]))
        self.assertEquals(len(dirs_3), 1)
        self.assertTrue(dirs_3[0].endswith('.profile'))

        stats = pstats.Stats(os.path.join(self.outpath, dirs[0], dirs_2[0], dirs_3[0]))
        self.assertNotEquals(stats.total_calls, 0)
        self.assertTrue(any(__file__ in c[0] for c in stats.stats.iterkeys()))


def func_i_want_to_patch(foo):
    return foo


class PatchingTest(unittest2.TestCase):
    def test_patch(self):
        @patch('tests.tests.func_i_want_to_patch')
        def new_func(func, *args, **kwargs):
            new_func.called += 1
            return func(*args, **kwargs)
        new_func.called = 0

        result = func_i_want_to_patch('foo')
        self.assertEquals(result, 'foo')
        self.assertEquals(new_func.called, 1)

########NEW FILE########
