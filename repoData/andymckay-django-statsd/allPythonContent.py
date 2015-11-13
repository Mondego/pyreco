__FILENAME__ = log
import logging

from django_statsd.clients.null import StatsClient

log = logging.getLogger('statsd')


class StatsClient(StatsClient):
    """A client that sends messages to the logging framework."""

    def timing(self, stat, delta, rate=1):
        """Send new timing information. `delta` is in milliseconds."""
        log.info('Timing: %s, %s, %s' % (stat, delta, rate))

    def incr(self, stat, count=1, rate=1):
        """Increment a stat by `count`."""
        log.info('Increment: %s, %s, %s' % (stat, count, rate))

    def decr(self, stat, count=1, rate=1):
        """Decrement a stat by `count`."""
        log.info('Decrement: %s, %s, %s' % (stat, count, rate))

    def gauge(self, stat, value, rate=1):
        """Set a gauge value."""
        log.info('Gauge: %s, %s, %s' % (stat, value, rate))

########NEW FILE########
__FILENAME__ = moz_metlog
from django_statsd.clients.null import StatsClient
from django.conf import settings


class StatsClient(StatsClient):
    """A client that pushes messages to metlog """

    def __init__(self, host='localhost', port=8125, prefix=None):
        super(StatsClient, self).__init__(host, port, prefix)
        if prefix is None:
            raise AttributeError(
                "Metlog needs settings.STATSD_PREFIX to be defined")

        self._prefix = prefix
        if getattr(settings, 'METLOG', None) is None:
            raise AttributeError(
                "Metlog needs to be configured as settings.METLOG")

        self.metlog = settings.METLOG

    def timing(self, stat, delta, rate=1):
        """Send new timing information. `delta` is in milliseconds."""
        stat = '%s.%s' % (self._prefix, stat)
        self.metlog.timer_send(stat, delta, rate=rate)

    def incr(self, stat, count=1, rate=1):
        """Increment a stat by `count`."""
        stat = '%s.%s' % (self._prefix, stat)
        self.metlog.incr(stat, count, rate=rate)

    def decr(self, stat, count=1, rate=1):
        """Decrement a stat by `count`."""
        stat = '%s.%s' % (self._prefix, stat)
        self.metlog.incr(stat, -count, rate=rate)

########NEW FILE########
__FILENAME__ = normal
from statsd.client import StatsClient

########NEW FILE########
__FILENAME__ = nose
# This is just a place holder, the toolbar works well enough for now.
from django_statsd.clients.toolbar import StatsClient

########NEW FILE########
__FILENAME__ = null
from statsd.client import StatsClient


class StatsClient(StatsClient):
    """A null client that does nothing."""

    def _after(self, data):
        pass

########NEW FILE########
__FILENAME__ = toolbar
from collections import defaultdict
from time import time

from django_statsd.clients.null import StatsClient


class StatsClient(StatsClient):
    """A client that pushes things into a local cache."""

    def __init__(self, *args, **kw):
        super(StatsClient, self).__init__(*args, **kw)
        self.reset()

    def reset(self):
        self.cache = defaultdict(list)
        self.timings = []

    def timing(self, stat, delta, rate=1):
        """Send new timing information. `delta` is in milliseconds."""
        stat = '%s|timing' % stat
        now = time() * 1000
        self.timings.append([stat, now - delta, delta, now])

    def incr(self, stat, count=1, rate=1):
        """Increment a stat by `count`."""
        stat = '%s|count' % stat
        self.cache[stat].append([count, rate])

    def decr(self, stat, count=1, rate=1):
        """Decrement a stat by `count`."""
        stat = '%s|count' % stat
        self.cache[stat].append([-count, rate])

    def gauge(self, stat, value, rate=1):
        """Set a gauge value."""
        stat = '%s|gauge' % stat
        self.cache[stat] = [[value, rate]]

    def set(self, stat, value, rate=1):
        stat = '%s|set' % stat
        self.cache[stat].append([value, rate])

########NEW FILE########
__FILENAME__ = errors
import logging

from django_statsd.clients import statsd


class StatsdHandler(logging.Handler):
    """Send error to statsd"""

    def emit(self, record):
        if not record.exc_info:
            return

        statsd.incr('error.%s' % record.exc_info[0].__name__.lower())

########NEW FILE########
__FILENAME__ = statsd_ping
from optparse import make_option
import time

from django.core.management.base import BaseCommand

from django_statsd.clients import statsd


class Command(BaseCommand):
    help = """
    Send a ping to statsd, this is suitable for using as a line in graphite
    charts, for example:
    http://codeascraft.etsy.com/2010/12/08/track-every-release/

    `key`: key.to.ping.with
    """
    option_list = BaseCommand.option_list + (
        make_option('--key', action='store', type='string',
                    dest='key', help='Key to ping'),
    )

    def handle(self, *args, **kw):
        statsd.timing(kw.get('key'), time.time())

########NEW FILE########
__FILENAME__ = middleware
from django.http import Http404
from django_statsd.clients import statsd
import inspect
import time


class GraphiteMiddleware(object):

    def process_response(self, request, response):
        statsd.incr('response.%s' % response.status_code)
        if hasattr(request, 'user') and request.user.is_authenticated():
            statsd.incr('response.auth.%s' % response.status_code)
        return response

    def process_exception(self, request, exception):
        if not isinstance(exception, Http404):
            statsd.incr('response.500')
            if hasattr(request, 'user') and request.user.is_authenticated():
                statsd.incr('response.auth.500')


class GraphiteRequestTimingMiddleware(object):
    """statsd's timing data per view."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        view = view_func
        if not inspect.isfunction(view_func):
            view = view.__class__
        try:
            request._view_module = view.__module__
            request._view_name = view.__name__
            request._start_time = time.time()
        except AttributeError:
            pass

    def process_response(self, request, response):
        self._record_time(request)
        return response

    def process_exception(self, request, exception):
        self._record_time(request)

    def _record_time(self, request):
        if hasattr(request, '_start_time'):
            ms = int((time.time() - request._start_time) * 1000)
            data = dict(module=request._view_module, name=request._view_name,
                        method=request.method)
            statsd.timing('view.{module}.{name}.{method}'.format(**data), ms)
            statsd.timing('view.{module}.{method}'.format(**data), ms)
            statsd.timing('view.{method}'.format(**data), ms)


class TastyPieRequestTimingMiddleware(GraphiteRequestTimingMiddleware):
    """statd's timing specific to Tastypie."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            request._view_module = view_kwargs['api_name']
            request._view_name = view_kwargs['resource_name']
            request._start_time = time.time()
        except (AttributeError, KeyError):
            super(TastyPieRequestTimingMiddleware, self).process_view(request,
                view_func, view_args, view_kwargs)

########NEW FILE########
__FILENAME__ = panel
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _, ungettext

from debug_toolbar.panels import DebugPanel
from django_statsd.clients import statsd


def munge(stats):
    # Munge the stats back into something easy for a template.
    results = []
    for stat in sorted(stats.keys()):
        values = stats[stat]
        name, type_ = stat.split('|')
        total = sum([x * y for x, y in values])
        data = {'name': name, 'type': type_,
                'count': len(values),
                'total': total,
                'values': values}
        results.append(data)
    return results


def times(stats):
    results = []
    if not stats:
        return results

    all_start = stats[0][1]
    all_end = max([t[3] for t in stats])
    all_duration = all_end - all_start
    for stat, start, duration, end in stats:
        start_rel = (start - all_start)
        start_ratio = (start_rel / float(all_duration))
        duration_ratio = (duration / float(all_duration))
        try:
            duration_ratio_relative = duration_ratio / (1.0 - start_ratio)
        except ZeroDivisionError:
            duration_ratio_relative = 0
        results.append([stat.split('|')[0],
                        # % start from left.
                        start_ratio * 100.0,
                        # % width
                        duration_ratio_relative * 100.0,
                        duration,
                        ])
    return results


class StatsdPanel(DebugPanel):

    name = 'Statsd'
    has_content = True

    def __init__(self, *args, **kw):
        super(StatsdPanel, self).__init__(*args, **kw)
        self.statsd = statsd
        try:
            self.statsd.reset()
        except AttributeError:
            raise ValueError('To use the toolbar, your STATSD_CLIENT must'
                             'be set to django_statsd.clients.toolbar')

    def nav_title(self):
        return _('Statsd')

    def nav_subtitle(self):
        length = len(self.statsd.cache) + len(self.statsd.timings)
        return ungettext('%s record', '%s records', length) % length

    def title(self):
        return _('Statsd')

    def url(self):
        return ''

    def content(self):
        context = self.context.copy()
        config = getattr(settings, 'TOOLBAR_STATSD', {})
        if 'roots' in config:
            for key in ['timers', 'counts']:
                context[key] = config['roots'][key]
        context['graphite'] = config.get('graphite')
        context['statsd'] = munge(self.statsd.cache)
        context['timings'] = times(self.statsd.timings)
        return render_to_string('toolbar_statsd/statsd.html', context)

########NEW FILE########
__FILENAME__ = cache
from django.core import cache
from django.core.cache.backends.base import BaseCache

from django_statsd.patches.utils import wrap


def key(cache, attr):
    return 'cache.%s.%s' % (cache.__module__.split('.')[-1], attr)


class StatsdTracker(BaseCache):

    def __init__(self, cache):
        self.cache = cache

    def __getattribute__(self, attr):
        if attr == 'cache':
            return BaseCache.__getattribute__(self, attr)
        return wrap(getattr(self.cache, attr), key(self.cache, attr))


def patch():
    cache.cache = StatsdTracker(cache.cache)

########NEW FILE########
__FILENAME__ = db
import django
from django.db.backends import util
from django_statsd.patches.utils import wrap, patch_method
from django_statsd.clients import statsd


def key(db, attr):
    return 'db.%s.%s.%s' % (db.client.executable_name, db.alias, attr)


def pre_django_1_6_cursorwrapper_getattr(self, attr):
    """
    The CursorWrapper is a pretty small wrapper around the cursor.
    If you are NOT in debug mode, this is the wrapper that's used.
    Sadly if it's in debug mode, we get a different wrapper.
    """
    if self.db.is_managed():
        self.db.set_dirty()
    if attr in self.__dict__:
        return self.__dict__[attr]
    else:
        if attr in ['execute', 'executemany', 'callproc']:
            return wrap(getattr(self.cursor, attr), key(self.db, attr))
        return getattr(self.cursor, attr)


def patched_execute(orig_execute, self, *args, **kwargs):
    with statsd.timer(key(self.db, 'execute')):
        return orig_execute(self, *args, **kwargs)


def patched_executemany(orig_executemany, self, *args, **kwargs):
    with statsd.timer(key(self.db, 'executemany')):
        return orig_executemany(self, *args, **kwargs)


def patched_callproc(orig_callproc, self, *args, **kwargs):
    with statsd.timer(key(self.db, 'callproc')):
        return orig_callproc(self, *args, **kwargs)


def patch():
    """
    The CursorWrapper is a pretty small wrapper around the cursor.  If
    you are NOT in debug mode, this is the wrapper that's used.  Sadly
    if it's in debug mode, we get a different wrapper for version
    earlier than 1.6.
    """

    if django.VERSION > (1, 6):
        # In 1.6+ util.CursorDebugWrapper just makes calls to CursorWrapper
        # As such, we only need to instrument CursorWrapper.
        # Instrumenting both will result in duplicated metrics
        patch_method(util.CursorWrapper, 'execute')(patched_execute)
        patch_method(util.CursorWrapper, 'executemany')(patched_executemany)
        patch_method(util.CursorWrapper, 'callproc')(patched_callproc)
    else:
        util.CursorWrapper.__getattr__ = pre_django_1_6_cursorwrapper_getattr
        patch_method(util.CursorDebugWrapper, 'execute')(patched_execute)
        patch_method(
            util.CursorDebugWrapper, 'executemany')(patched_executemany)

########NEW FILE########
__FILENAME__ = utils
from django_statsd.clients import statsd
from functools import partial, wraps

def patch_method(target, name, external_decorator=None):

    def decorator(patch_function):
        original_function = getattr(target, name)

        @wraps(patch_function)
        def wrapper(*args, **kw):
            return patch_function(original_function, *args, **kw)

        setattr(target, name, wrapper)
        return wrapper

    return decorator

def wrapped(method, key, *args, **kw):
    with statsd.timer(key):
        return method(*args, **kw)


def wrap(method, key, *args, **kw):
    return partial(wrapped, method, key, *args, **kw)

########NEW FILE########
__FILENAME__ = plugins
import logging
import os

NOSE = False
try:
    from nose.plugins.base import Plugin
    NOSE = True
except ImportError:
    class Plugin:
        pass

from django_statsd.clients import statsd

log = logging.getLogger(__name__)


class NoseStatsd(Plugin):
    name = 'statsd'

    def options(self, parse, env=os.environ):
        super(NoseStatsd, self).options(parse, env=env)

    def configure(self, options, conf):
        super(NoseStatsd, self).configure(options, conf)

    def report(self, stream):
        def write(line):
            stream.writeln('%s' % line)

        if not hasattr(statsd, 'timings'):
            write("Statsd timings not saved, ensure your statsd client is: "
                  "STATSD_CLIENT = 'django_statsd.clients.nose'")
            return

        timings = {}
        longest = 0
        for v in statsd.timings:
            k = v[0].split('|')[0]
            longest = max(longest, len(k))
            timings.setdefault(k, [])
            timings[k].append(v[2])

        counts = {}
        for k, v in statsd.cache.items():
            k = k.split('|')[0]
            longest = max(longest, len(k))
            counts.setdefault(k, [])
            [counts[k].append(_v) for _v in v]

        header = '%s | Number |  Avg (ms)  | Total (ms)' % (
            'Statsd Keys'.ljust(longest))
        header_len = len(header)

        write('')
        write('=' * header_len)
        write('%s | Number |  Avg (ms)  | Total (ms)' % (
            'Statsd Keys'.ljust(longest)))
        write('-' * header_len)
        if not timings:
            write('None')

        for k in sorted(timings.keys()):
            v = timings[k]
            write('%s | %s | %s | %s' % (
                k.ljust(longest),
                str(len(v)).rjust(6),
                ('%0.5f' % (sum(v) / float(len(v)))).rjust(10),
                ('%0.3f' % sum(v)).rjust(10)))

        write('=' * header_len)
        write('%s | Number | Total' % ('Statsd Counts'.ljust(longest)))
        write('-' * header_len)
        if not counts:
            write('None')

        for k in sorted(counts.keys()):
            v = counts[k]
            write('%s | %s | %d' % (
                k.ljust(longest),
                str(len(v)).rjust(6),
                sum([x * y for x, y in v])))

########NEW FILE########
__FILENAME__ = tests
import json
import logging
import sys

from django.conf import settings
from nose.exc import SkipTest
from nose import tools as nose_tools
from unittest2 import skipUnless

from django import VERSION
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseForbidden
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import dictconfig
from django.utils import unittest

import mock
from nose.tools import eq_
from django_statsd.clients import get_client, statsd
from django_statsd.patches import utils
from django_statsd.patches.db import (
    patched_callproc,
    patched_execute,
    patched_executemany,
)
from django_statsd import middleware

cfg = {
    'version': 1,
    'formatters': {},
    'handlers': {
        'test_statsd_handler': {
            'class': 'django_statsd.loggers.errors.StatsdHandler',
        },
    },
    'loggers': {
        'test.logging': {
            'handlers': ['test_statsd_handler'],
        },
    },
}


@mock.patch.object(middleware.statsd, 'incr')
class TestIncr(TestCase):

    def setUp(self):
        self.req = RequestFactory().get('/')
        self.res = HttpResponse()

    def test_graphite_response(self, incr):
        gmw = middleware.GraphiteMiddleware()
        gmw.process_response(self.req, self.res)
        assert incr.called

    def test_graphite_response_authenticated(self, incr):
        self.req.user = mock.Mock()
        self.req.user.is_authenticated.return_value = True
        gmw = middleware.GraphiteMiddleware()
        gmw.process_response(self.req, self.res)
        eq_(incr.call_count, 2)

    def test_graphite_exception(self, incr):
        gmw = middleware.GraphiteMiddleware()
        gmw.process_exception(self.req, None)
        assert incr.called

    def test_graphite_exception_authenticated(self, incr):
        self.req.user = mock.Mock()
        self.req.user.is_authenticated.return_value = True
        gmw = middleware.GraphiteMiddleware()
        gmw.process_exception(self.req, None)
        eq_(incr.call_count, 2)


@mock.patch.object(middleware.statsd, 'timing')
class TestTiming(unittest.TestCase):

    def setUp(self):
        self.req = RequestFactory().get('/')
        self.res = HttpResponse()

    def test_request_timing(self, timing):
        func = lambda x: x
        gmw = middleware.GraphiteRequestTimingMiddleware()
        gmw.process_view(self.req, func, tuple(), dict())
        gmw.process_response(self.req, self.res)
        eq_(timing.call_count, 3)
        names = ['view.%s.%s.GET' % (func.__module__, func.__name__),
                 'view.%s.GET' % func.__module__,
                 'view.GET']
        for expected, (args, kwargs) in zip(names, timing.call_args_list):
            eq_(expected, args[0])

    def test_request_timing_exception(self, timing):
        func = lambda x: x
        gmw = middleware.GraphiteRequestTimingMiddleware()
        gmw.process_view(self.req, func, tuple(), dict())
        gmw.process_exception(self.req, self.res)
        eq_(timing.call_count, 3)
        names = ['view.%s.%s.GET' % (func.__module__, func.__name__),
                 'view.%s.GET' % func.__module__,
                 'view.GET']
        for expected, (args, kwargs) in zip(names, timing.call_args_list):
            eq_(expected, args[0])

    def test_request_timing_tastypie(self, timing):
        func = lambda x: x
        gmw = middleware.TastyPieRequestTimingMiddleware()
        gmw.process_view(self.req, func, tuple(), {'api_name': 'my_api_name',
            'resource_name': 'my_resource_name'})
        gmw.process_response(self.req, self.res)
        eq_(timing.call_count, 3)
        names = ['view.my_api_name.my_resource_name.GET',
                 'view.my_api_name.GET',
                 'view.GET']
        for expected, (args, kwargs) in zip(names, timing.call_args_list):
            eq_(expected, args[0])

    def test_request_timing_tastypie_fallback(self, timing):
        func = lambda x: x
        gmw = middleware.TastyPieRequestTimingMiddleware()
        gmw.process_view(self.req, func, tuple(), dict())
        gmw.process_response(self.req, self.res)
        eq_(timing.call_count, 3)
        names = ['view.%s.%s.GET' % (func.__module__, func.__name__),
                 'view.%s.GET' % func.__module__,
                 'view.GET']
        for expected, (args, kwargs) in zip(names, timing.call_args_list):
            eq_(expected, args[0])


class TestClient(unittest.TestCase):

    @mock.patch.object(settings, 'STATSD_CLIENT', 'statsd.client')
    def test_normal(self):
        eq_(get_client().__module__, 'statsd.client')

    @mock.patch.object(settings, 'STATSD_CLIENT',
                       'django_statsd.clients.null')
    def test_null(self):
        eq_(get_client().__module__, 'django_statsd.clients.null')

    @mock.patch.object(settings, 'STATSD_CLIENT',
                       'django_statsd.clients.toolbar')
    def test_toolbar(self):
        eq_(get_client().__module__, 'django_statsd.clients.toolbar')

    @mock.patch.object(settings, 'STATSD_CLIENT',
                       'django_statsd.clients.toolbar')
    def test_toolbar_send(self):
        client = get_client()
        eq_(client.cache, {})
        client.incr('testing')
        eq_(client.cache, {'testing|count': [[1, 1]]})


class TestMetlogClient(TestCase):

    def check_metlog(self):
        try:
            from metlog.config import client_from_dict_config
            return client_from_dict_config
        except ImportError:
            raise SkipTest("Metlog is not installed")

    @nose_tools.raises(AttributeError)
    def test_no_metlog(self):
        with self.settings(STATSD_PREFIX='moz_metlog',
                           STATSD_CLIENT='django_statsd.clients.moz_metlog'):
            get_client()

    def _create_client(self):
        client_from_dict_config = self.check_metlog()

        # Need to load within the test in case metlog is not installed
        from metlog.config import client_from_dict_config

        METLOG_CONF = {
            'logger': 'django-statsd',
            'sender': {
                'class': 'metlog.senders.DebugCaptureSender',
            },
        }

        return client_from_dict_config(METLOG_CONF)

    def test_get_client(self):
        metlog = self._create_client()
        with self.settings(METLOG=metlog,
                           STATSD_PREFIX='moz_metlog',
                           STATSD_CLIENT='django_statsd.clients.moz_metlog'):
            client = get_client()
            eq_(client.__module__, 'django_statsd.clients.moz_metlog')

    def test_metlog_incr(self):
        metlog = self._create_client()
        with self.settings(METLOG=metlog,
                           STATSD_PREFIX='moz_metlog',
                           STATSD_CLIENT='django_statsd.clients.moz_metlog'):
            client = get_client()
            eq_(len(client.metlog.sender.msgs), 0)
            client.incr('testing')
            eq_(len(client.metlog.sender.msgs), 1)

            msg = json.loads(client.metlog.sender.msgs[0])
            eq_(msg['severity'], 6)
            eq_(msg['payload'], '1')
            eq_(msg['fields']['rate'], 1)
            eq_(msg['fields']['name'], 'moz_metlog.testing')
            eq_(msg['type'], 'counter')

    def test_metlog_decr(self):
        metlog = self._create_client()
        with self.settings(METLOG=metlog,
                           STATSD_PREFIX='moz_metlog',
                           STATSD_CLIENT='django_statsd.clients.moz_metlog'):
            client = get_client()
            eq_(len(client.metlog.sender.msgs), 0)
            client.decr('testing')
            eq_(len(client.metlog.sender.msgs), 1)

            msg = json.loads(client.metlog.sender.msgs[0])
            eq_(msg['severity'], 6)
            eq_(msg['payload'], '-1')
            eq_(msg['fields']['rate'], 1)
            eq_(msg['fields']['name'], 'moz_metlog.testing')
            eq_(msg['type'], 'counter')

    def test_metlog_timing(self):
        metlog = self._create_client()
        with self.settings(METLOG=metlog,
                           STATSD_PREFIX='moz_metlog',
                           STATSD_CLIENT='django_statsd.clients.moz_metlog'):
            client = get_client()
            eq_(len(client.metlog.sender.msgs), 0)
            client.timing('testing', 512, rate=2)
            eq_(len(client.metlog.sender.msgs), 1)

            msg = json.loads(client.metlog.sender.msgs[0])
            eq_(msg['severity'], 6)
            eq_(msg['payload'], '512')
            eq_(msg['fields']['rate'], 2)
            eq_(msg['fields']['name'], 'moz_metlog.testing')
            eq_(msg['type'], 'timer')

    @nose_tools.raises(AttributeError)
    def test_metlog_no_prefixes(self):
        metlog = self._create_client()

        with self.settings(METLOG=metlog,
                           STATSD_CLIENT='django_statsd.clients.moz_metlog'):
            client = get_client()
            client.incr('foo', 2)

    def test_metlog_prefixes(self):
        metlog = self._create_client()

        with self.settings(METLOG=metlog,
                           STATSD_PREFIX='some_prefix',
                           STATSD_CLIENT='django_statsd.clients.moz_metlog'):
            client = get_client()
            eq_(len(client.metlog.sender.msgs), 0)

            client.timing('testing', 512, rate=2)
            client.incr('foo', 2)
            client.decr('bar', 5)

            eq_(len(client.metlog.sender.msgs), 3)

            msg = json.loads(client.metlog.sender.msgs[0])
            eq_(msg['severity'], 6)
            eq_(msg['payload'], '512')
            eq_(msg['fields']['rate'], 2)
            eq_(msg['fields']['name'], 'some_prefix.testing')
            eq_(msg['type'], 'timer')

            msg = json.loads(client.metlog.sender.msgs[1])
            eq_(msg['severity'], 6)
            eq_(msg['payload'], '2')
            eq_(msg['fields']['rate'], 1)
            eq_(msg['fields']['name'], 'some_prefix.foo')
            eq_(msg['type'], 'counter')

            msg = json.loads(client.metlog.sender.msgs[2])
            eq_(msg['severity'], 6)
            eq_(msg['payload'], '-5')
            eq_(msg['fields']['rate'], 1)
            eq_(msg['fields']['name'], 'some_prefix.bar')
            eq_(msg['type'], 'counter')


# This is primarily for Zamboni, which loads in the custom middleware
# classes, one of which, breaks posts to our url. Let's stop that.
@mock.patch.object(settings, 'MIDDLEWARE_CLASSES', [])
class TestRecord(TestCase):

    urls = 'django_statsd.urls'

    def setUp(self):
        super(TestRecord, self).setUp()
        self.url = reverse('django_statsd.record')
        settings.STATSD_RECORD_GUARD = None
        self.good = {'client': 'boomerang', 'nt_nav_st': 1,
                     'nt_domcomp': 3}
        self.stick = {'client': 'stick',
                      'window.performance.timing.domComplete': 123,
                      'window.performance.timing.domInteractive': 456,
                      'window.performance.timing.domLoading': 789,
                      'window.performance.timing.navigationStart': 0,
                      'window.performance.navigation.redirectCount': 3,
                      'window.performance.navigation.type': 1}

    def test_no_client(self):
        assert self.client.get(self.url).status_code == 400

    def test_no_valid_client(self):
        assert self.client.get(self.url, {'client': 'no'}).status_code == 400

    def test_boomerang_almost(self):
        assert self.client.get(self.url,
                               {'client': 'boomerang'}).status_code == 400

    def test_boomerang_minimum(self):
        assert self.client.get(self.url,
                               {'client': 'boomerang',
                                'nt_nav_st': 1}).content == 'recorded'

    @mock.patch('django_statsd.views.process_key')
    def test_boomerang_something(self, process_key):
        assert self.client.get(self.url, self.good).content == 'recorded'
        assert process_key.called

    def test_boomerang_post(self):
        assert self.client.post(self.url, self.good).status_code == 405

    def test_good_guard(self):
        settings.STATSD_RECORD_GUARD = lambda r: None
        assert self.client.get(self.url, self.good).status_code == 200

    def test_bad_guard(self):
        settings.STATSD_RECORD_GUARD = lambda r: HttpResponseForbidden()
        assert self.client.get(self.url, self.good).status_code == 403

    def test_stick_get(self):
        assert self.client.get(self.url, self.stick).status_code == 405

    @mock.patch('django_statsd.views.process_key')
    def test_stick(self, process_key):
        assert self.client.post(self.url, self.stick).status_code == 200
        assert process_key.called

    def test_stick_start(self):
        data = self.stick.copy()
        del data['window.performance.timing.navigationStart']
        assert self.client.post(self.url, data).status_code == 400

    @mock.patch('django_statsd.views.process_key')
    def test_stick_missing(self, process_key):
        data = self.stick.copy()
        del data['window.performance.timing.domInteractive']
        assert self.client.post(self.url, data).status_code == 200
        assert process_key.called

    def test_stick_garbage(self):
        data = self.stick.copy()
        data['window.performance.timing.domInteractive'] = '<alert>'
        assert self.client.post(self.url, data).status_code == 400

    def test_stick_some_garbage(self):
        data = self.stick.copy()
        data['window.performance.navigation.redirectCount'] = '<alert>'
        assert self.client.post(self.url, data).status_code == 400

    def test_stick_more_garbage(self):
        data = self.stick.copy()
        data['window.performance.navigation.type'] = '<alert>'
        assert self.client.post(self.url, data).status_code == 400


@mock.patch.object(middleware.statsd, 'incr')
class TestErrorLog(TestCase):

    def setUp(self):
        dictconfig.dictConfig(cfg)
        self.log = logging.getLogger('test.logging')

    def division_error(self):
        try:
            1 / 0
        except:
            return sys.exc_info()

    def test_emit(self, incr):
        self.log.error('blargh!', exc_info=self.division_error())
        assert incr.call_args[0][0] == 'error.zerodivisionerror'

    def test_not_emit(self, incr):
        self.log.error('blargh!')
        assert not incr.called


class TestPatchMethod(TestCase):

    def setUp(self):
        super(TestPatchMethod, self).setUp()

        class DummyClass(object):

            def sumargs(self, a, b, c=3, d=4):
                return a + b + c + d

            def badfn(self, a, b=2):
                raise ValueError

        self.cls = DummyClass

    def test_late_patching(self):
        """
        Objects created before patching should get patched as well.
        """
        def patch_fn(original_fn, self, *args, **kwargs):
            return original_fn(self, *args, **kwargs) + 10

        obj = self.cls()
        self.assertEqual(obj.sumargs(1, 2, 3, 4), 10)
        utils.patch_method(self.cls, 'sumargs')(patch_fn)
        self.assertEqual(obj.sumargs(1, 2, 3, 4), 20)

    def test_doesnt_call_original_implicitly(self):
        """
        Original fn must be called explicitly from patched to be
        executed.
        """
        def patch_fn(original_fn, self, *args, **kwargs):
            return 10

        with self.assertRaises(ValueError):
            obj = self.cls()
            obj.badfn(1, 2)

        utils.patch_method(self.cls, 'badfn')(patch_fn)
        self.assertEqual(obj.badfn(1, 2), 10)

    def test_args_kwargs_are_honored(self):
        """
        Args and kwargs must be honored between calls from the patched to
        the original version.
        """
        def patch_fn(original_fn, self, *args, **kwargs):
            return original_fn(self, *args, **kwargs)

        utils.patch_method(self.cls, 'sumargs')(patch_fn)
        obj = self.cls()
        self.assertEqual(obj.sumargs(1, 2), 10)
        self.assertEqual(obj.sumargs(1, 1, d=1), 6)
        self.assertEqual(obj.sumargs(1, 1, 1, 1), 4)

    def test_patched_fn_can_receive_arbitrary_arguments(self):
        """
        Args and kwargs can be received arbitrarily with no contraints on
        the patched fn, even if the original_fn had a fixed set of
        allowed args and kwargs.
        """
        def patch_fn(original_fn, self, *args, **kwargs):
            return args, kwargs

        utils.patch_method(self.cls, 'badfn')(patch_fn)
        obj = self.cls()
        self.assertEqual(obj.badfn(1, d=2), ((1,), {'d': 2}))
        self.assertEqual(obj.badfn(1, d=2), ((1,), {'d': 2}))
        self.assertEqual(obj.badfn(1, 2, c=1, d=2), ((1, 2), {'c': 1, 'd': 2}))


class TestCursorWrapperPatching(TestCase):

    def test_patched_callproc_calls_timer(self):
        with mock.patch.object(statsd, 'timer') as timer:
            db = mock.Mock(executable_name='name', alias='alias')
            instance = mock.Mock(db=db)
            patched_callproc(lambda *args, **kwargs: None, instance)
            self.assertEqual(timer.call_count, 1)

    def test_patched_execute_calls_timer(self):
        with mock.patch.object(statsd, 'timer') as timer:
            db = mock.Mock(executable_name='name', alias='alias')
            instance = mock.Mock(db=db)
            patched_execute(lambda *args, **kwargs: None, instance)
            self.assertEqual(timer.call_count, 1)

    def test_patched_executemany_calls_timer(self):
        with mock.patch.object(statsd, 'timer') as timer:
            db = mock.Mock(executable_name='name', alias='alias')
            instance = mock.Mock(db=db)
            patched_executemany(lambda *args, **kwargs: None, instance)
            self.assertEqual(timer.call_count, 1)

    @mock.patch(
        'django_statsd.patches.db.pre_django_1_6_cursorwrapper_getattr')
    @mock.patch('django_statsd.patches.db.patched_executemany')
    @mock.patch('django_statsd.patches.db.patched_execute')
    @mock.patch('django.db.backends.util.CursorDebugWrapper')
    @skipUnless(VERSION < (1, 6, 0), "CursorWrapper Patching for Django<1.6")
    def test_cursorwrapper_patching(self,
                                    CursorDebugWrapper,
                                    execute,
                                    executemany,
                                    _getattr):
        try:
            from django.db.backends import util

            # We need to patch CursorWrapper like this because setting
            # __getattr__ on Mock instances raises AttributeError.
            class CursorWrapper(object):
                pass

            _CursorWrapper = util.CursorWrapper
            util.CursorWrapper = CursorWrapper

            from django_statsd.patches.db import patch
            execute.__name__ = 'execute'
            executemany.__name__ = 'executemany'
            _getattr.__name__ = '_getattr'
            execute.return_value = 'execute'
            executemany.return_value = 'executemany'
            _getattr.return_value = 'getattr'
            patch()

            self.assertEqual(CursorDebugWrapper.execute(), 'execute')
            self.assertEqual(CursorDebugWrapper.executemany(), 'executemany')
            self.assertEqual(CursorWrapper.__getattr__(), 'getattr')
        finally:
            util.CursorWrapper = _CursorWrapper

    @mock.patch('django_statsd.patches.db.patched_callproc')
    @mock.patch('django_statsd.patches.db.patched_executemany')
    @mock.patch('django_statsd.patches.db.patched_execute')
    @mock.patch('django.db.backends.util.CursorWrapper')
    @skipUnless(VERSION >= (1, 6, 0), "CursorWrapper Patching for Django>=1.6")
    def test_cursorwrapper_patching16(self,
                                      CursorWrapper,
                                      execute,
                                      executemany,
                                      callproc):
        from django_statsd.patches.db import patch
        execute.__name__ = 'execute'
        executemany.__name__ = 'executemany'
        callproc.__name__ = 'callproc'
        execute.return_value = 'execute'
        executemany.return_value = 'executemany'
        callproc.return_value = 'callproc'
        patch()

        self.assertEqual(CursorWrapper.execute(), 'execute')
        self.assertEqual(CursorWrapper.executemany(), 'executemany')
        self.assertEqual(CursorWrapper.callproc(), 'callproc')

########NEW FILE########
__FILENAME__ = test_settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'mydatabase'
    }
}

ROOT_URLCONF = ''
STATSD_CLIENT = 'django_statsd.clients.null'
STATSD_PREFIX = None
METLOG = None

SECRET_KEY = 'secret'

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError: # django < 1.4
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url('^record$', 'django_statsd.views.record',
        name='django_statsd.record'),
)

########NEW FILE########
__FILENAME__ = views
from django import http
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django_statsd.clients import statsd

boomerang = {
 'window.performance.navigation.redirectCount': 'nt_red_cnt',
 'window.performance.navigation.type': 'nt_nav_type',
 'window.performance.timing.connectEnd': 'nt_con_end',
 'window.performance.timing.connectStart': 'nt_con_st',
 'window.performance.timing.domComplete': 'nt_domcomp',
 'window.performance.timing.domContentLoaded': 'nt_domcontloaded',
 'window.performance.timing.domInteractive': 'nt_domint',
 'window.performance.timing.domLoading': 'nt_domloading',
 'window.performance.timing.domainLookupEnd': 'nt_dns_end',
 'window.performance.timing.domainLookupStart': 'nt_dns_st',
 'window.performance.timing.fetchStart': 'nt_fet_st',
 'window.performance.timing.loadEventEnd': 'nt_load_end',
 'window.performance.timing.loadEventStart': 'nt_load_st',
 'window.performance.timing.navigationStart': 'nt_nav_st',
 'window.performance.timing.redirectEnd': 'nt_red_end',
 'window.performance.timing.redirectStart': 'nt_red_st',
 'window.performance.timing.requestStart': 'nt_req_st',
 'window.performance.timing.responseEnd': 'nt_res_end',
 'window.performance.timing.responseStart': 'nt_res_st',
 'window.performance.timing.unloadEventEnd': 'nt_unload_end',
 'window.performance.timing.unloadEventStart': 'nt_unload_st'
}

types = {
 '0': 'navigate',
 '1': 'reload',
 '2': 'back_forward',
 '255': 'reserved'
}

# These are the default keys that we will try and record.
stick_keys = [
 'window.performance.timing.domComplete',
 'window.performance.timing.domInteractive',
 'window.performance.timing.domLoading',
 'window.performance.timing.loadEventEnd',
 'window.performance.timing.responseStart',
 'window.performance.navigation.redirectCount',
 'window.performance.navigation.type',
]


def process_key(start, key, value):
    if 'timing' in key:
        # Some values will be zero. We want the output of that to
        # be zero relative to start.
        value = max(start, int(value)) - start
        statsd.timing(key, value)
    elif key == 'window.performance.navigation.type':
        statsd.incr('%s.%s' % (key, types[value]))
    elif key == 'window.performance.navigation.redirectCount':
        statsd.incr(key, int(value))


def _process_summaries(start, keys):
    calculated = {
        'network': keys['window.performance.timing.responseStart'] - start,
        'app': keys['window.performance.timing.domLoading'] -
               keys['window.performance.timing.responseStart'],
        'dom': keys['window.performance.timing.domComplete'] -
               keys['window.performance.timing.domLoading'],
        'rendering': keys['window.performance.timing.loadEventEnd'] -
                     keys['window.performance.timing.domComplete'],
    }
    for k, v in calculated.items():
        # If loadEventEnd still does not get populated, we could end up with
        # negative numbers here.
        statsd.timing('window.performance.calculated.%s' % k, max(v, 0))


@require_http_methods(['GET', 'HEAD'])
def _process_boomerang(request):
    if 'nt_nav_st' not in request.GET:
        raise ValueError('nt_nav_st not in request.GET, make sure boomerang'
            ' is made with navigation API timings as per the following'
            ' http://yahoo.github.com/boomerang/doc/howtos/howto-9.html')

    # This when the request started, everything else will be relative to this
    # for the purposes of statsd measurement.
    start = int(request.GET['nt_nav_st'])

    keys = {}
    for k in getattr(settings, 'STATSD_RECORD_KEYS', stick_keys):
        v = request.GET.get(boomerang[k])
        if not v or v == 'undefined':
            continue
        if k in boomerang:
            process_key(start, k, v)
            keys[k] = int(v)

    try:
        _process_summaries(start, keys)
    except KeyError:
        pass


@require_http_methods(['POST'])
def _process_stick(request):
    start = request.POST.get('window.performance.timing.navigationStart', None)
    if not start:
        return http.HttpResponseBadRequest()

    start = int(start)
    keys = {}
    for k in getattr(settings, 'STATSD_RECORD_KEYS', stick_keys):
        v = request.POST.get(k, None)
        if v:
            keys[k] = int(request.POST[k])
            process_key(start, k, request.POST[k])

    # Only process the network when we have these.
    for key in ['window.performance.timing.loadEventEnd',
                'window.performance.timing.responseStart']:
        if key not in keys:
            return

    _process_summaries(start, keys)


clients = {
 'boomerang': _process_boomerang,
 'stick': _process_stick,
}


@csrf_exempt
def record(request):
    """
    This is a Django method you can link to in your URLs that process
    the incoming data. Be sure to add a client parameter into your request
    so that we can figure out how to process this request. For example
    if you are using boomerang, you'll need: client = boomerang.

    You can define a method in STATSD_RECORD_GUARD that will do any lookup
    you need for imposing security on this method, so that not just anyone
    can post to it.
    """
    if 'client' not in request.REQUEST:
        return http.HttpResponseBadRequest()

    client = request.REQUEST['client']
    if client not in clients:
        return http.HttpResponseBadRequest()

    guard = getattr(settings, 'STATSD_RECORD_GUARD', None)
    if guard:
        if not callable(guard):
            raise ValueError('STATSD_RECORD_GUARD must be callable')
        result = guard(request)
        if result:
            return result

    try:
        response = clients[client](request)
    except (ValueError, KeyError):
        return http.HttpResponseBadRequest()

    if response:
        return response
    return http.HttpResponse('recorded')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-statsd documentation build configuration file, created by
# sphinx-quickstart on Fri Apr 27 17:30:33 2012.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-statsd'
copyright = u'2012, Andy McKay'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3'
# The full version, including alpha/beta/rc tags.
release = '0.3'

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
html_theme = 'default'

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
htmlhelp_basename = 'django-statsddoc'


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
  ('index', 'django-statsd.tex', u'django-statsd Documentation',
   u'Andy McKay', 'manual'),
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
    ('index', 'django-statsd', u'django-statsd Documentation',
     [u'Andy McKay'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-statsd', u'django-statsd Documentation', u'Andy McKay',
   'django-statsd', 'One line description of project.', 'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
