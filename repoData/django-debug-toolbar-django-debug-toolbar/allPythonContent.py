__FILENAME__ = apps
from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

from debug_toolbar import settings as dt_settings


class DebugToolbarConfig(AppConfig):
    name = 'debug_toolbar'
    verbose_name = _("Debug Toolbar")

    def ready(self):
        if dt_settings.PATCH_SETTINGS:
            dt_settings.patch_all()

########NEW FILE########
__FILENAME__ = debugsqlshell
from __future__ import absolute_import, print_function, unicode_literals

from time import time

# 'debugsqlshell' is the same as the 'shell'.
from django.core.management.commands.shell import Command               # noqa
try:
    from django.db.backends import utils
except ImportError:
    from django.db.backends import util as utils

import sqlparse


class PrintQueryWrapper(utils.CursorDebugWrapper):
    def execute(self, sql, params=()):
        start_time = time()
        try:
            return self.cursor.execute(sql, params)
        finally:
            raw_sql = self.db.ops.last_executed_query(self.cursor, sql, params)
            end_time = time()
            duration = (end_time - start_time) * 1000
            formatted_sql = sqlparse.format(raw_sql, reindent=True)
            print('%s [%.2fms]' % (formatted_sql, duration))


utils.CursorDebugWrapper = PrintQueryWrapper

########NEW FILE########
__FILENAME__ = middleware
"""
Debug Toolbar middleware
"""

from __future__ import absolute_import, unicode_literals

import re
import threading

from django.conf import settings
from django.utils.encoding import force_text
from django.utils.importlib import import_module

from debug_toolbar.toolbar import DebugToolbar
from debug_toolbar import settings as dt_settings

_HTML_TYPES = ('text/html', 'application/xhtml+xml')
# Handles python threading module bug - http://bugs.python.org/issue14308
threading._DummyThread._Thread__stop = lambda x: 1


def show_toolbar(request):
    """
    Default function to determine whether to show the toolbar on a given page.
    """
    if request.META.get('REMOTE_ADDR', None) not in settings.INTERNAL_IPS:
        return False

    if request.is_ajax():
        return False

    return bool(settings.DEBUG)


class DebugToolbarMiddleware(object):
    """
    Middleware to set up Debug Toolbar on incoming request and render toolbar
    on outgoing response.
    """
    debug_toolbars = {}

    def process_request(self, request):
        # Decide whether the toolbar is active for this request.
        func_path = dt_settings.CONFIG['SHOW_TOOLBAR_CALLBACK']
        # Replace this with import_by_path in Django >= 1.6.
        mod_path, func_name = func_path.rsplit('.', 1)
        show_toolbar = getattr(import_module(mod_path), func_name)
        if not show_toolbar(request):
            return

        toolbar = DebugToolbar(request)
        self.__class__.debug_toolbars[threading.current_thread().ident] = toolbar

        # Activate instrumentation ie. monkey-patch.
        for panel in toolbar.enabled_panels:
            panel.enable_instrumentation()

        # Run process_request methods of panels like Django middleware.
        response = None
        for panel in toolbar.enabled_panels:
            response = panel.process_request(request)
            if response:
                break
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        toolbar = self.__class__.debug_toolbars.get(threading.current_thread().ident)
        if not toolbar:
            return

        # Run process_view methods of panels like Django middleware.
        response = None
        for panel in toolbar.enabled_panels:
            response = panel.process_view(request, view_func, view_args, view_kwargs)
            if response:
                break
        return response

    def process_response(self, request, response):
        toolbar = self.__class__.debug_toolbars.pop(threading.current_thread().ident, None)
        if not toolbar:
            return response

        # Run process_response methods of panels like Django middleware.
        for panel in reversed(toolbar.enabled_panels):
            new_response = panel.process_response(request, response)
            if new_response:
                response = new_response

        # Deactivate instrumentation ie. monkey-unpatch. This must run
        # regardless of the response. Keep 'return' clauses below.
        # (NB: Django's model for middleware doesn't guarantee anything.)
        for panel in reversed(toolbar.enabled_panels):
            panel.disable_instrumentation()

        # Check for responses where the toolbar can't be inserted.
        content_encoding = response.get('Content-Encoding', '')
        content_type = response.get('Content-Type', '').split(';')[0]
        if any((getattr(response, 'streaming', False),
                'gzip' in content_encoding,
                content_type not in _HTML_TYPES)):
            return response

        # Collapse the toolbar by default if SHOW_COLLAPSED is set.
        if toolbar.config['SHOW_COLLAPSED'] and 'djdt' not in request.COOKIES:
            response.set_cookie('djdt', 'hide', 864000)

        # Insert the toolbar in the response.
        content = force_text(response.content, encoding=settings.DEFAULT_CHARSET)
        insert_before = dt_settings.CONFIG['INSERT_BEFORE']
        try:                    # Python >= 2.7
            pattern = re.escape(insert_before)
            bits = re.split(pattern, content, flags=re.IGNORECASE)
        except TypeError:       # Python < 2.7
            pattern = '(.+?)(%s|$)' % re.escape(insert_before)
            matches = re.findall(pattern, content, flags=re.DOTALL | re.IGNORECASE)
            bits = [m[0] for m in matches if m[1] == insert_before]
            # When the body ends with a newline, there's two trailing groups.
            bits.append(''.join(m[0] for m in matches if m[1] == ''))
        if len(bits) > 1:
            bits[-2] += toolbar.render_toolbar()
            response.content = insert_before.join(bits)
            if response.get('Content-Length', None):
                response['Content-Length'] = len(response.content)
        return response

########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import, unicode_literals

import django

from debug_toolbar import settings as dt_settings


if dt_settings.PATCH_SETTINGS and django.VERSION[:2] < (1, 7):
    dt_settings.patch_all()

########NEW FILE########
__FILENAME__ = cache
from __future__ import absolute_import, unicode_literals

import inspect
import sys
import time

from django.conf import settings
from django.core import cache
from django.core.cache import cache as original_cache, get_cache as original_get_cache
from django.core.cache.backends.base import BaseCache
from django.dispatch import Signal
from django.template import Node
from django.utils.translation import ugettext_lazy as _, ungettext
try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict

from debug_toolbar.panels import Panel
from debug_toolbar.utils import (tidy_stacktrace, render_stacktrace,
                                 get_template_info, get_stack)
from debug_toolbar import settings as dt_settings


cache_called = Signal(providing_args=[
    "time_taken", "name", "return_value", "args", "kwargs", "trace"])


def send_signal(method):
    def wrapped(self, *args, **kwargs):
        t = time.time()
        value = method(self, *args, **kwargs)
        t = time.time() - t

        if dt_settings.CONFIG['ENABLE_STACKTRACES']:
            stacktrace = tidy_stacktrace(reversed(get_stack()))
        else:
            stacktrace = []

        template_info = None
        cur_frame = sys._getframe().f_back
        try:
            while cur_frame is not None:
                if cur_frame.f_code.co_name == 'render':
                    node = cur_frame.f_locals['self']
                    if isinstance(node, Node):
                        template_info = get_template_info(node.source)
                        break
                cur_frame = cur_frame.f_back
        except Exception:
            pass
        del cur_frame
        cache_called.send(sender=self.__class__, time_taken=t,
                          name=method.__name__, return_value=value,
                          args=args, kwargs=kwargs, trace=stacktrace,
                          template_info=template_info, backend=self.cache)
        return value
    return wrapped


class CacheStatTracker(BaseCache):
    """A small class used to track cache calls."""
    def __init__(self, cache):
        self.cache = cache

    def __repr__(self):
        return str("<CacheStatTracker for %s>") % repr(self.cache)

    def _get_func_info(self):
        frame = sys._getframe(3)
        info = inspect.getframeinfo(frame)
        return (info[0], info[1], info[2], info[3])

    def __contains__(self, key):
        return self.cache.__contains__(key)

    def __getattr__(self, name):
        return getattr(self.cache, name)

    @send_signal
    def add(self, *args, **kwargs):
        return self.cache.add(*args, **kwargs)

    @send_signal
    def get(self, *args, **kwargs):
        return self.cache.get(*args, **kwargs)

    @send_signal
    def set(self, *args, **kwargs):
        return self.cache.set(*args, **kwargs)

    @send_signal
    def delete(self, *args, **kwargs):
        return self.cache.delete(*args, **kwargs)

    @send_signal
    def has_key(self, *args, **kwargs):
        return self.cache.has_key(*args, **kwargs)

    @send_signal
    def incr(self, *args, **kwargs):
        return self.cache.incr(*args, **kwargs)

    @send_signal
    def decr(self, *args, **kwargs):
        return self.cache.decr(*args, **kwargs)

    @send_signal
    def get_many(self, *args, **kwargs):
        return self.cache.get_many(*args, **kwargs)

    @send_signal
    def set_many(self, *args, **kwargs):
        self.cache.set_many(*args, **kwargs)

    @send_signal
    def delete_many(self, *args, **kwargs):
        self.cache.delete_many(*args, **kwargs)

    @send_signal
    def incr_version(self, *args, **kwargs):
        return self.cache.incr_version(*args, **kwargs)

    @send_signal
    def decr_version(self, *args, **kwargs):
        return self.cache.decr_version(*args, **kwargs)


def get_cache(*args, **kwargs):
    return CacheStatTracker(original_get_cache(*args, **kwargs))


class CachePanel(Panel):
    """
    Panel that displays the cache statistics.
    """
    template = 'debug_toolbar/panels/cache.html'

    def __init__(self, *args, **kwargs):
        super(CachePanel, self).__init__(*args, **kwargs)
        self.total_time = 0
        self.hits = 0
        self.misses = 0
        self.calls = []
        self.counts = OrderedDict((
            ('add', 0),
            ('get', 0),
            ('set', 0),
            ('delete', 0),
            ('get_many', 0),
            ('set_many', 0),
            ('delete_many', 0),
            ('has_key', 0),
            ('incr', 0),
            ('decr', 0),
            ('incr_version', 0),
            ('decr_version', 0),
        ))
        cache_called.connect(self._store_call_info)

    def _store_call_info(self, sender, name=None, time_taken=0,
                         return_value=None, args=None, kwargs=None,
                         trace=None, template_info=None, backend=None, **kw):
        if name == 'get':
            if return_value is None:
                self.misses += 1
            else:
                self.hits += 1
        elif name == 'get_many':
            for key, value in return_value.items():
                if value is None:
                    self.misses += 1
                else:
                    self.hits += 1
        time_taken *= 1000

        self.total_time += time_taken
        self.counts[name] += 1
        self.calls.append({
            'time': time_taken,
            'name': name,
            'args': args,
            'kwargs': kwargs,
            'trace': render_stacktrace(trace),
            'template_info': template_info,
            'backend': backend
        })

    # Implement the Panel API

    nav_title = _("Cache")

    @property
    def nav_subtitle(self):
        cache_calls = len(self.calls)
        return ungettext("%(cache_calls)d call in %(time).2fms",
                         "%(cache_calls)d calls in %(time).2fms",
                         cache_calls) % {'cache_calls': cache_calls,
                                         'time': self.total_time}

    @property
    def title(self):
        count = len(getattr(settings, 'CACHES', ['default']))
        return ungettext("Cache calls from %(count)d backend",
                         "Cache calls from %(count)d backends",
                         count) % dict(count=count)

    def enable_instrumentation(self):
        # This isn't thread-safe because cache connections aren't thread-local
        # in Django, unlike database connections.
        cache.cache = CacheStatTracker(original_cache)
        cache.get_cache = get_cache

    def disable_instrumentation(self):
        cache.cache = original_cache
        cache.get_cache = original_get_cache

    def process_response(self, request, response):
        self.record_stats({
            'total_calls': len(self.calls),
            'calls': self.calls,
            'total_time': self.total_time,
            'hits': self.hits,
            'misses': self.misses,
            'counts': self.counts,
        })

########NEW FILE########
__FILENAME__ = headers
from __future__ import absolute_import, unicode_literals

try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict
from django.utils.translation import ugettext_lazy as _
from debug_toolbar.panels import Panel


class HeadersPanel(Panel):
    """
    A panel to display HTTP headers.
    """
    # List of environment variables we want to display
    ENVIRON_FILTER = set((
        'CONTENT_LENGTH',
        'CONTENT_TYPE',
        'DJANGO_SETTINGS_MODULE',
        'GATEWAY_INTERFACE',
        'QUERY_STRING',
        'PATH_INFO',
        'PYTHONPATH',
        'REMOTE_ADDR',
        'REMOTE_HOST',
        'REQUEST_METHOD',
        'SCRIPT_NAME',
        'SERVER_NAME',
        'SERVER_PORT',
        'SERVER_PROTOCOL',
        'SERVER_SOFTWARE',
        'TZ',
    ))

    title = _("Headers")

    template = 'debug_toolbar/panels/headers.html'

    def process_request(self, request):
        wsgi_env = list(sorted(request.META.items()))
        self.request_headers = OrderedDict(
            (unmangle(k), v) for (k, v) in wsgi_env if is_http_header(k))
        if 'Cookie' in self.request_headers:
            self.request_headers['Cookie'] = '=> see Request panel'
        self.environ = OrderedDict(
            (k, v) for (k, v) in wsgi_env if k in self.ENVIRON_FILTER)
        self.record_stats({
            'request_headers': self.request_headers,
            'environ': self.environ,
        })

    def process_response(self, request, response):
        self.response_headers = OrderedDict(sorted(response.items()))
        self.record_stats({
            'response_headers': self.response_headers,
        })


def is_http_header(wsgi_key):
    # The WSGI spec says that keys should be str objects in the environ dict,
    # but this isn't true in practice. See issues #449 and #482.
    return isinstance(wsgi_key, str) and wsgi_key.startswith('HTTP_')


def unmangle(wsgi_key):
    return wsgi_key[5:].replace('_', '-').title()

########NEW FILE########
__FILENAME__ = logging
from __future__ import absolute_import, unicode_literals

import datetime
import logging
try:
    import threading
except ImportError:
    threading = None
from django.utils.translation import ungettext, ugettext_lazy as _
from debug_toolbar.panels import Panel
from debug_toolbar.utils import ThreadCollector

MESSAGE_IF_STRING_REPRESENTATION_INVALID = '[Could not get log message]'


class LogCollector(ThreadCollector):

    def collect(self, item, thread=None):
        # Avoid logging SQL queries since they are already in the SQL panel
        # TODO: Make this check whether SQL panel is enabled
        if item.get('channel', '') == 'django.db.backends':
            return
        super(LogCollector, self).collect(item, thread)


class ThreadTrackingHandler(logging.Handler):
    def __init__(self, collector):
        logging.Handler.__init__(self)
        self.collector = collector

    def emit(self, record):
        try:
            message = record.getMessage()
        except Exception:
            message = MESSAGE_IF_STRING_REPRESENTATION_INVALID

        record = {
            'message': message,
            'time': datetime.datetime.fromtimestamp(record.created),
            'level': record.levelname,
            'file': record.pathname,
            'line': record.lineno,
            'channel': record.name,
        }
        self.collector.collect(record)


# We don't use enable/disable_instrumentation because logging is global.
# We can't add thread-local logging handlers. Hopefully logging is cheap.

collector = LogCollector()
logging_handler = ThreadTrackingHandler(collector)
logging.root.setLevel(logging.NOTSET)
logging.root.addHandler(logging_handler)


class LoggingPanel(Panel):
    template = 'debug_toolbar/panels/logging.html'

    def __init__(self, *args, **kwargs):
        super(LoggingPanel, self).__init__(*args, **kwargs)
        self._records = {}

    nav_title = _("Logging")

    @property
    def nav_subtitle(self):
        records = self._records[threading.currentThread()]
        record_count = len(records)
        return ungettext("%(count)s message", "%(count)s messages",
                         record_count) % {'count': record_count}

    title = _("Log messages")

    def process_request(self, request):
        collector.clear_collection()

    def process_response(self, request, response):
        records = collector.get_collection()
        self._records[threading.currentThread()] = records
        collector.clear_collection()
        self.record_stats({'records': records})

########NEW FILE########
__FILENAME__ = profiling
from __future__ import absolute_import, division, unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from debug_toolbar.panels import Panel
from debug_toolbar import settings as dt_settings

import cProfile
from pstats import Stats
from colorsys import hsv_to_rgb
import os


class DjangoDebugToolbarStats(Stats):
    __root = None

    def get_root_func(self):
        if self.__root is None:
            for func, (cc, nc, tt, ct, callers) in self.stats.items():
                if len(callers) == 0:
                    self.__root = func
                    break
        return self.__root


class FunctionCall(object):
    def __init__(self, statobj, func, depth=0, stats=None,
                 id=0, parent_ids=[], hsv=(0, 0.5, 1)):
        self.statobj = statobj
        self.func = func
        if stats:
            self.stats = stats
        else:
            self.stats = statobj.stats[func][:4]
        self.depth = depth
        self.id = id
        self.parent_ids = parent_ids
        self.hsv = hsv

    def parent_classes(self):
        return self.parent_classes

    def background(self):
        r, g, b = hsv_to_rgb(*self.hsv)
        return 'rgb(%f%%,%f%%,%f%%)' % (r * 100, g * 100, b * 100)

    def func_std_string(self):  # match what old profile produced
        func_name = self.func
        if func_name[:2] == ('~', 0):
            # special case for built-in functions
            name = func_name[2]
            if name.startswith('<') and name.endswith('>'):
                return '{%s}' % name[1:-1]
            else:
                return name
        else:
            file_name, line_num, method = self.func
            idx = file_name.find('/site-packages/')
            if idx > -1:
                file_name = file_name[(idx + 14):]

            file_path, file_name = file_name.rsplit(os.sep, 1)

            return mark_safe(
                '<span class="path">{0}/</span>'
                '<span class="file">{1}</span>'
                ' in <span class="func">{3}</span>'
                '(<span class="lineno">{2}</span>)'.format(
                    file_path,
                    file_name,
                    line_num,
                    method))

    def subfuncs(self):
        i = 0
        h, s, v = self.hsv
        count = len(self.statobj.all_callees[self.func])
        for func, stats in self.statobj.all_callees[self.func].items():
            i += 1
            h1 = h + (i / count) / (self.depth + 1)
            if stats[3] == 0:
                s1 = 0
            else:
                s1 = s * (stats[3] / self.stats[3])
            yield FunctionCall(self.statobj,
                               func,
                               self.depth + 1,
                               stats=stats,
                               id=str(self.id) + '_' + str(i),
                               parent_ids=self.parent_ids + [self.id],
                               hsv=(h1, s1, 1))

    def count(self):
        return self.stats[1]

    def tottime(self):
        return self.stats[2]

    def cumtime(self):
        cc, nc, tt, ct = self.stats
        return self.stats[3]

    def tottime_per_call(self):
        cc, nc, tt, ct = self.stats

        if nc == 0:
            return 0

        return tt / nc

    def cumtime_per_call(self):
        cc, nc, tt, ct = self.stats

        if cc == 0:
            return 0

        return ct / cc

    def indent(self):
        return 16 * self.depth


class ProfilingPanel(Panel):
    """
    Panel that displays profiling information.
    """
    title = _("Profiling")

    template = 'debug_toolbar/panels/profiling.html'

    def process_view(self, request, view_func, view_args, view_kwargs):
        self.profiler = cProfile.Profile()
        args = (request,) + view_args
        return self.profiler.runcall(view_func, *args, **view_kwargs)

    def add_node(self, func_list, func, max_depth, cum_time=0.1):
        func_list.append(func)
        func.has_subfuncs = False
        if func.depth < max_depth:
            for subfunc in func.subfuncs():
                if subfunc.stats[3] >= cum_time:
                    func.has_subfuncs = True
                    self.add_node(func_list, subfunc, max_depth, cum_time=cum_time)

    def process_response(self, request, response):
        if not hasattr(self, 'profiler'):
            return None
        # Could be delayed until the panel content is requested (perf. optim.)
        self.profiler.create_stats()
        self.stats = DjangoDebugToolbarStats(self.profiler)
        self.stats.calc_callees()

        root = FunctionCall(self.stats, self.stats.get_root_func(), depth=0)

        func_list = []
        self.add_node(func_list,
                      root,
                      dt_settings.CONFIG['PROFILER_MAX_DEPTH'],
                      root.stats[3] / 8)

        self.record_stats({'func_list': func_list})

########NEW FILE########
__FILENAME__ = redirects
from __future__ import absolute_import, unicode_literals

from django.core.handlers.wsgi import STATUS_CODE_TEXT
from django.shortcuts import render_to_response
from django.utils.translation import ugettext_lazy as _

from debug_toolbar.panels import Panel


class RedirectsPanel(Panel):
    """
    Panel that intercepts redirects and displays a page with debug info.
    """

    has_content = False

    nav_title = _("Intercept redirects")

    def process_response(self, request, response):
        if 300 <= int(response.status_code) < 400:
            redirect_to = response.get('Location', None)
            if redirect_to:
                try:        # Django >= 1.6
                    reason_phrase = response.reason_phrase
                except AttributeError:
                    reason_phrase = STATUS_CODE_TEXT.get(response.status_code,
                                                         'UNKNOWN STATUS CODE')
                status_line = '%s %s' % (response.status_code, reason_phrase)
                cookies = response.cookies
                context = {'redirect_to': redirect_to, 'status_line': status_line}
                response = render_to_response('debug_toolbar/redirect.html', context)
                response.cookies = cookies
        return response

########NEW FILE########
__FILENAME__ = request
from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import resolve
from django.http import Http404
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from debug_toolbar.panels import Panel
from debug_toolbar.utils import get_name_from_obj


class RequestPanel(Panel):
    """
    A panel to display request variables (POST/GET, session, cookies).
    """
    template = 'debug_toolbar/panels/request.html'

    title = _("Request")

    @property
    def nav_subtitle(self):
        """
        Show abbreviated name of view function as subtitle
        """
        view_func = self.get_stats().get('view_func', '')
        return view_func.rsplit('.', 1)[-1]

    def process_response(self, request, response):
        self.record_stats({
            'get': [(k, request.GET.getlist(k)) for k in sorted(request.GET)],
            'post': [(k, request.POST.getlist(k)) for k in sorted(request.POST)],
            'cookies': [(k, request.COOKIES.get(k)) for k in sorted(request.COOKIES)],
        })
        view_info = {
            'view_func': _("<no view>"),
            'view_args': 'None',
            'view_kwargs': 'None',
            'view_urlname': 'None',
        }
        try:
            match = resolve(request.path)
            func, args, kwargs = match
            view_info['view_func'] = get_name_from_obj(func)
            view_info['view_args'] = args
            view_info['view_kwargs'] = kwargs
            view_info['view_urlname'] = getattr(match, 'url_name',
                                                _("<unavailable>"))
        except Http404:
            pass
        self.record_stats(view_info)

        if hasattr(request, 'session'):
            self.record_stats({
                'session': [(k, request.session.get(k))
                            for k in sorted(request.session.keys(), key=force_text)]
            })

########NEW FILE########
__FILENAME__ = settings
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.views.debug import get_safe_settings
from django.utils.translation import ugettext_lazy as _
try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict

from debug_toolbar.panels import Panel


class SettingsPanel(Panel):
    """
    A panel to display all variables in django.conf.settings
    """
    template = 'debug_toolbar/panels/settings.html'

    nav_title = _("Settings")

    def title(self):
        return _("Settings from <code>%s</code>") % settings.SETTINGS_MODULE

    def process_response(self, request, response):
        self.record_stats({
            'settings': OrderedDict(sorted(get_safe_settings().items(),
                                           key=lambda s: s[0])),
        })

########NEW FILE########
__FILENAME__ = signals
from __future__ import absolute_import, unicode_literals

from django.core.signals import (
    request_started, request_finished, got_request_exception)
from django.db.backends.signals import connection_created
from django.db.models.signals import (
    class_prepared, pre_init, post_init, pre_save, post_save,
    pre_delete, post_delete, post_syncdb)
try:
    from django.dispatch.dispatcher import WEAKREF_TYPES
except ImportError:
    import weakref
    WEAKREF_TYPES = weakref.ReferenceType,
from django.utils.translation import ugettext_lazy as _, ungettext
from django.utils.importlib import import_module

from debug_toolbar.panels import Panel


class SignalsPanel(Panel):
    template = 'debug_toolbar/panels/signals.html'

    SIGNALS = {
        'request_started': request_started,
        'request_finished': request_finished,
        'got_request_exception': got_request_exception,
        'connection_created': connection_created,
        'class_prepared': class_prepared,
        'pre_init': pre_init,
        'post_init': post_init,
        'pre_save': pre_save,
        'post_save': post_save,
        'pre_delete': pre_delete,
        'post_delete': post_delete,
        'post_syncdb': post_syncdb,
    }

    def nav_subtitle(self):
        signals = self.get_stats()['signals']
        num_receivers = sum(len(s[2]) for s in signals)
        num_signals = len(signals)
        # here we have to handle a double count translation, hence the
        # hard coding of one signal
        if num_signals == 1:
            return ungettext("%(num_receivers)d receiver of 1 signal",
                             "%(num_receivers)d receivers of 1 signal",
                             num_receivers) % {'num_receivers': num_receivers}
        return ungettext("%(num_receivers)d receiver of %(num_signals)d signals",
                         "%(num_receivers)d receivers of %(num_signals)d signals",
                         num_receivers) % {'num_receivers': num_receivers,
                                           'num_signals': num_signals}

    title = _("Signals")

    @property
    def signals(self):
        signals = self.SIGNALS.copy()
        for signal in self.toolbar.config['EXTRA_SIGNALS']:
            mod_path, signal_name = signal.rsplit('.', 1)
            signals_mod = import_module(mod_path)
            signals[signal_name] = getattr(signals_mod, signal_name)
        return signals

    def process_response(self, request, response):
        signals = []
        for name, signal in sorted(self.signals.items(), key=lambda x: x[0]):
            if signal is None:
                continue
            receivers = []
            for receiver in signal.receivers:
                receiver = receiver[1]
                if isinstance(receiver, WEAKREF_TYPES):
                    receiver = receiver()
                if receiver is None:
                    continue

                receiver = getattr(receiver, '__wraps__', receiver)
                receiver_name = getattr(receiver, '__name__', str(receiver))
                if getattr(receiver, '__self__', None) is not None:
                    receiver_class_name = getattr(receiver.__self__, '__class__', type).__name__
                    text = "%s.%s" % (receiver_class_name, receiver_name)
                elif getattr(receiver, 'im_class', None) is not None:   # Python 2 only
                    receiver_class_name = receiver.im_class.__name__
                    text = "%s.%s" % (receiver_class_name, receiver_name)
                else:
                    text = "%s" % receiver_name
                receivers.append(text)
            signals.append((name, signal, receivers))

        self.record_stats({'signals': signals})

########NEW FILE########
__FILENAME__ = forms
from __future__ import absolute_import, unicode_literals

import json
import hashlib

from django import forms
from django.conf import settings
from django.db import connections
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError

from debug_toolbar.panels.sql.utils import reformat_sql


class SQLSelectForm(forms.Form):
    """
    Validate params

        sql: The sql statement with interpolated params
        raw_sql: The sql statement with placeholders
        params: JSON encoded parameter values
        duration: time for SQL to execute passed in from toolbar just for redisplay
        hash: the hash of (secret + sql + params) for tamper checking
    """
    sql = forms.CharField()
    raw_sql = forms.CharField()
    params = forms.CharField()
    alias = forms.CharField(required=False, initial='default')
    duration = forms.FloatField()
    hash = forms.CharField()

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', None)

        if initial is not None:
            initial['hash'] = self.make_hash(initial)

        super(SQLSelectForm, self).__init__(*args, **kwargs)

        for name in self.fields:
            self.fields[name].widget = forms.HiddenInput()

    def clean_raw_sql(self):
        value = self.cleaned_data['raw_sql']

        if not value.lower().strip().startswith('select'):
            raise ValidationError("Only 'select' queries are allowed.")

        return value

    def clean_params(self):
        value = self.cleaned_data['params']

        try:
            return json.loads(value)
        except ValueError:
            raise ValidationError('Is not valid JSON')

    def clean_alias(self):
        value = self.cleaned_data['alias']

        if value not in connections:
            raise ValidationError("Database alias '%s' not found" % value)

        return value

    def clean_hash(self):
        hash = self.cleaned_data['hash']

        if hash != self.make_hash(self.data):
            raise ValidationError('Tamper alert')

        return hash

    def reformat_sql(self):
        return reformat_sql(self.cleaned_data['sql'])

    def make_hash(self, data):
        items = [settings.SECRET_KEY, data['sql'], data['params']]
        # Replace lines endings with spaces to preserve the hash value
        # even when the browser normalizes \r\n to \n in inputs.
        items = [' '.join(force_text(item).splitlines()) for item in items]
        return hashlib.sha1(''.join(items).encode('utf-8')).hexdigest()

    @property
    def connection(self):
        return connections[self.cleaned_data['alias']]

    @cached_property
    def cursor(self):
        return self.connection.cursor()

########NEW FILE########
__FILENAME__ = panel
from __future__ import absolute_import, unicode_literals

import uuid
from copy import copy
from collections import defaultdict

from django.conf.urls import patterns, url
from django.db import connections
from django.utils.translation import ugettext_lazy as _, ungettext_lazy as __

from debug_toolbar.panels import Panel
from debug_toolbar.panels.sql.forms import SQLSelectForm
from debug_toolbar.utils import render_stacktrace
from debug_toolbar.panels.sql.utils import reformat_sql, contrasting_color_generator
from debug_toolbar.panels.sql.tracking import wrap_cursor, unwrap_cursor


def get_isolation_level_display(vendor, level):
    if vendor == 'postgresql':
        import psycopg2.extensions
        choices = {
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT: _("Autocommit"),
            psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED: _("Read uncommitted"),
            psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED: _("Read committed"),
            psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ: _("Repeatable read"),
            psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE: _("Serializable"),
        }
    else:
        raise ValueError(vendor)
    return choices.get(level)


def get_transaction_status_display(vendor, level):
    if vendor == 'postgresql':
        import psycopg2.extensions
        choices = {
            psycopg2.extensions.TRANSACTION_STATUS_IDLE: _("Idle"),
            psycopg2.extensions.TRANSACTION_STATUS_ACTIVE: _("Active"),
            psycopg2.extensions.TRANSACTION_STATUS_INTRANS: _("In transaction"),
            psycopg2.extensions.TRANSACTION_STATUS_INERROR: _("In error"),
            psycopg2.extensions.TRANSACTION_STATUS_UNKNOWN: _("Unknown"),
        }
    else:
        raise ValueError(vendor)
    return choices.get(level)


class SQLPanel(Panel):
    """
    Panel that displays information about the SQL queries run while processing
    the request.
    """
    def __init__(self, *args, **kwargs):
        super(SQLPanel, self).__init__(*args, **kwargs)
        self._offset = dict((k, len(connections[k].queries)) for k in connections)
        self._sql_time = 0
        self._num_queries = 0
        self._queries = []
        self._databases = {}
        self._transaction_status = {}
        self._transaction_ids = {}

    def get_transaction_id(self, alias):
        if alias not in connections:
            return
        conn = connections[alias].connection
        if not conn:
            return

        if conn.vendor == 'postgresql':
            cur_status = conn.get_transaction_status()
        else:
            raise ValueError(conn.vendor)

        last_status = self._transaction_status.get(alias)
        self._transaction_status[alias] = cur_status

        if not cur_status:
            # No available state
            return None

        if cur_status != last_status:
            if cur_status:
                self._transaction_ids[alias] = uuid.uuid4().hex
            else:
                self._transaction_ids[alias] = None

        return self._transaction_ids[alias]

    def record(self, alias, **kwargs):
        self._queries.append((alias, kwargs))
        if alias not in self._databases:
            self._databases[alias] = {
                'time_spent': kwargs['duration'],
                'num_queries': 1,
            }
        else:
            self._databases[alias]['time_spent'] += kwargs['duration']
            self._databases[alias]['num_queries'] += 1
        self._sql_time += kwargs['duration']
        self._num_queries += 1

    # Implement the Panel API

    nav_title = _("SQL")

    @property
    def nav_subtitle(self):
        return __("%d query in %.2fms", "%d queries in %.2fms",
                  self._num_queries) % (self._num_queries, self._sql_time)

    @property
    def title(self):
        count = len(self._databases)
        return __('SQL queries from %(count)d connection',
                  'SQL queries from %(count)d connections',
                  count) % {'count': count}

    template = 'debug_toolbar/panels/sql.html'

    @classmethod
    def get_urls(cls):
        return patterns('debug_toolbar.panels.sql.views',               # noqa
            url(r'^sql_select/$', 'sql_select', name='sql_select'),
            url(r'^sql_explain/$', 'sql_explain', name='sql_explain'),
            url(r'^sql_profile/$', 'sql_profile', name='sql_profile'),
        )

    def enable_instrumentation(self):
        # This is thread-safe because database connections are thread-local.
        for connection in connections.all():
            wrap_cursor(connection, self)

    def disable_instrumentation(self):
        for connection in connections.all():
            unwrap_cursor(connection)

    def process_response(self, request, response):
        colors = contrasting_color_generator()
        trace_colors = defaultdict(lambda: next(colors))
        if self._queries:
            width_ratio_tally = 0
            factor = int(256.0 / (len(self._databases) * 2.5))
            for n, db in enumerate(self._databases.values()):
                rgb = [0, 0, 0]
                color = n % 3
                rgb[color] = 256 - n / 3 * factor
                nn = color
                # XXX: pretty sure this is horrible after so many aliases
                while rgb[color] < factor:
                    nc = min(256 - rgb[color], 256)
                    rgb[color] += nc
                    nn += 1
                    if nn > 2:
                        nn = 0
                    rgb[nn] = nc
                db['rgb_color'] = rgb

            trans_ids = {}
            trans_id = None
            i = 0
            for alias, query in self._queries:
                trans_id = query.get('trans_id')
                last_trans_id = trans_ids.get(alias)

                if trans_id != last_trans_id:
                    if last_trans_id:
                        self._queries[(i - 1)][1]['ends_trans'] = True
                    trans_ids[alias] = trans_id
                    if trans_id:
                        query['starts_trans'] = True
                if trans_id:
                    query['in_trans'] = True

                query['alias'] = alias
                if 'iso_level' in query:
                    query['iso_level'] = get_isolation_level_display(query['vendor'],
                                                                     query['iso_level'])
                if 'trans_status' in query:
                    query['trans_status'] = get_transaction_status_display(query['vendor'],
                                                                           query['trans_status'])

                query['form'] = SQLSelectForm(auto_id=None, initial=copy(query))

                if query['sql']:
                    query['sql'] = reformat_sql(query['sql'])
                query['rgb_color'] = self._databases[alias]['rgb_color']
                try:
                    query['width_ratio'] = (query['duration'] / self._sql_time) * 100
                    query['width_ratio_relative'] = (
                        100.0 * query['width_ratio'] / (100.0 - width_ratio_tally))
                except ZeroDivisionError:
                    query['width_ratio'] = 0
                    query['width_ratio_relative'] = 0
                query['start_offset'] = width_ratio_tally
                query['end_offset'] = query['width_ratio'] + query['start_offset']
                width_ratio_tally += query['width_ratio']
                query['stacktrace'] = render_stacktrace(query['stacktrace'])
                i += 1

                query['trace_color'] = trace_colors[query['stacktrace']]

            if trans_id:
                self._queries[(i - 1)][1]['ends_trans'] = True

        self.record_stats({
            'databases': sorted(self._databases.items(), key=lambda x: -x[1]['time_spent']),
            'queries': [q for a, q in self._queries],
            'sql_time': self._sql_time,
        })

########NEW FILE########
__FILENAME__ = tracking
from __future__ import absolute_import, unicode_literals

import sys

import json
from threading import local
from time import time

from django.template import Node
from django.utils.encoding import force_text
from django.utils import six

from debug_toolbar.utils import tidy_stacktrace, get_template_info, get_stack
from debug_toolbar import settings as dt_settings


class SQLQueryTriggered(Exception):
    """Thrown when template panel triggers a query"""
    pass


class ThreadLocalState(local):
    def __init__(self):
        self.enabled = True

    @property
    def Wrapper(self):
        if self.enabled:
            return NormalCursorWrapper
        return ExceptionCursorWrapper

    def recording(self, v):
        self.enabled = v


state = ThreadLocalState()
recording = state.recording  # export function


def wrap_cursor(connection, panel):
    if not hasattr(connection, '_djdt_cursor'):
        connection._djdt_cursor = connection.cursor

        def cursor():
            return state.Wrapper(connection._djdt_cursor(), connection, panel)

        connection.cursor = cursor
        return cursor


def unwrap_cursor(connection):
    if hasattr(connection, '_djdt_cursor'):
        del connection._djdt_cursor
        del connection.cursor


class ExceptionCursorWrapper(object):
    """
    Wraps a cursor and raises an exception on any operation.
    Used in Templates panel.
    """
    def __init__(self, cursor, db, logger):
        pass

    def __getattr__(self, attr):
        raise SQLQueryTriggered()


class NormalCursorWrapper(object):
    """
    Wraps a cursor and logs queries.
    """

    def __init__(self, cursor, db, logger):
        self.cursor = cursor
        # Instance of a BaseDatabaseWrapper subclass
        self.db = db
        # logger must implement a ``record`` method
        self.logger = logger

    def _quote_expr(self, element):
        if isinstance(element, six.string_types):
            return "'%s'" % force_text(element).replace("'", "''")
        else:
            return repr(element)

    def _quote_params(self, params):
        if not params:
            return params
        if isinstance(params, dict):
            return dict((key, self._quote_expr(value))
                        for key, value in params.items())
        return list(map(self._quote_expr, params))

    def _decode(self, param):
        try:
            return force_text(param, strings_only=True)
        except UnicodeDecodeError:
            return '(encoded string)'

    def _record(self, method, sql, params):
        start_time = time()
        try:
            return method(sql, params)
        finally:
            stop_time = time()
            duration = (stop_time - start_time) * 1000
            if dt_settings.CONFIG['ENABLE_STACKTRACES']:
                stacktrace = tidy_stacktrace(reversed(get_stack()))
            else:
                stacktrace = []
            _params = ''
            try:
                _params = json.dumps(list(map(self._decode, params)))
            except Exception:
                pass  # object not JSON serializable

            template_info = None
            cur_frame = sys._getframe().f_back
            try:
                while cur_frame is not None:
                    if cur_frame.f_code.co_name == 'render':
                        node = cur_frame.f_locals['self']
                        if isinstance(node, Node):
                            template_info = get_template_info(node.source)
                            break
                    cur_frame = cur_frame.f_back
            except Exception:
                pass
            del cur_frame

            alias = getattr(self.db, 'alias', 'default')
            conn = self.db.connection
            vendor = getattr(conn, 'vendor', 'unknown')

            params = {
                'vendor': vendor,
                'alias': alias,
                'sql': self.db.ops.last_executed_query(
                    self.cursor, sql, self._quote_params(params)),
                'duration': duration,
                'raw_sql': sql,
                'params': _params,
                'stacktrace': stacktrace,
                'start_time': start_time,
                'stop_time': stop_time,
                'is_slow': duration > dt_settings.CONFIG['SQL_WARNING_THRESHOLD'],
                'is_select': sql.lower().strip().startswith('select'),
                'template_info': template_info,
            }

            if vendor == 'postgresql':
                # If an erroneous query was ran on the connection, it might
                # be in a state where checking isolation_level raises an
                # exception.
                try:
                    iso_level = conn.isolation_level
                except conn.InternalError:
                    iso_level = 'unknown'
                params.update({
                    'trans_id': self.logger.get_transaction_id(alias),
                    'trans_status': conn.get_transaction_status(),
                    'iso_level': iso_level,
                    'encoding': conn.encoding,
                })

            # We keep `sql` to maintain backwards compatibility
            self.logger.record(**params)

    def callproc(self, procname, params=()):
        return self._record(self.cursor.callproc, procname, params)

    def execute(self, sql, params=()):
        return self._record(self.cursor.execute, sql, params)

    def executemany(self, sql, param_list):
        return self._record(self.cursor.executemany, sql, param_list)

    def __getattr__(self, attr):
        return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.cursor)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

########NEW FILE########
__FILENAME__ = utils
from __future__ import absolute_import, unicode_literals

import re

from django.utils.html import escape

import sqlparse
from sqlparse import tokens as T


class BoldKeywordFilter:
    """sqlparse filter to bold SQL keywords"""
    def process(self, stack, stream):
        """Process the token stream"""
        for token_type, value in stream:
            is_keyword = token_type in T.Keyword
            if is_keyword:
                yield T.Text, '<strong>'
            yield token_type, escape(value)
            if is_keyword:
                yield T.Text, '</strong>'


def reformat_sql(sql):
    stack = sqlparse.engine.FilterStack()
    stack.preprocess.append(BoldKeywordFilter())  # add our custom filter
    stack.postprocess.append(sqlparse.filters.SerializerUnicode())  # tokens -> strings
    return swap_fields(''.join(stack.run(sql)))


def swap_fields(sql):
    expr = r'SELECT</strong> (...........*?) <strong>FROM'
    subs = (r'SELECT</strong> '
            r'<a class="djDebugUncollapsed djDebugToggle" href="#">&#8226;&#8226;&#8226;</a> '
            r'<a class="djDebugCollapsed djDebugToggle" href="#">\1</a> '
            r'<strong>FROM')
    return re.sub(expr, subs, sql)


def contrasting_color_generator():
    """
    Generate constrasting colors by varying most significant bit of RGB first,
    and then vary subsequent bits systematically.
    """
    def rgb_to_hex(rgb):
        return '#%02x%02x%02x' % tuple(rgb)

    triples = [(1, 0, 0), (0, 1, 0), (0, 0, 1),
               (1, 1, 0), (0, 1, 1), (1, 0, 1), (1, 1, 1)]
    n = 1 << 7
    so_far = [[0, 0, 0]]
    while True:
        if n == 0:  # This happens after 2**24 colours; presumably, never
            yield "#000000"  # black
        copy_so_far = list(so_far)
        for triple in triples:
            for previous in copy_so_far:
                rgb = [n * triple[i] + previous[i] for i in range(3)]
                so_far.append(rgb)
                yield rgb_to_hex(rgb)
        n >>= 1

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import, unicode_literals

from django.http import HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt

from debug_toolbar.panels.sql.forms import SQLSelectForm


@csrf_exempt
def sql_select(request):
    """Returns the output of the SQL SELECT statement"""
    form = SQLSelectForm(request.POST or None)

    if form.is_valid():
        sql = form.cleaned_data['raw_sql']
        params = form.cleaned_data['params']
        cursor = form.cursor
        cursor.execute(sql, params)
        headers = [d[0] for d in cursor.description]
        result = cursor.fetchall()
        cursor.close()
        context = {
            'result': result,
            'sql': form.reformat_sql(),
            'duration': form.cleaned_data['duration'],
            'headers': headers,
            'alias': form.cleaned_data['alias'],
        }
        # Using render_to_response avoids running global context processors.
        return render_to_response('debug_toolbar/panels/sql_select.html', context)
    return HttpResponseBadRequest('Form errors')


@csrf_exempt
def sql_explain(request):
    """Returns the output of the SQL EXPLAIN on the given query"""
    form = SQLSelectForm(request.POST or None)

    if form.is_valid():
        sql = form.cleaned_data['raw_sql']
        params = form.cleaned_data['params']
        vendor = form.connection.vendor
        cursor = form.cursor

        if vendor == 'sqlite':
            # SQLite's EXPLAIN dumps the low-level opcodes generated for a query;
            # EXPLAIN QUERY PLAN dumps a more human-readable summary
            # See http://www.sqlite.org/lang_explain.html for details
            cursor.execute("EXPLAIN QUERY PLAN %s" % (sql,), params)
        elif vendor == 'postgresql':
            cursor.execute("EXPLAIN ANALYZE %s" % (sql,), params)
        else:
            cursor.execute("EXPLAIN %s" % (sql,), params)

        headers = [d[0] for d in cursor.description]
        result = cursor.fetchall()
        cursor.close()
        context = {
            'result': result,
            'sql': form.reformat_sql(),
            'duration': form.cleaned_data['duration'],
            'headers': headers,
            'alias': form.cleaned_data['alias'],
        }
        # Using render_to_response avoids running global context processors.
        return render_to_response('debug_toolbar/panels/sql_explain.html', context)
    return HttpResponseBadRequest('Form errors')


@csrf_exempt
def sql_profile(request):
    """Returns the output of running the SQL and getting the profiling statistics"""
    form = SQLSelectForm(request.POST or None)

    if form.is_valid():
        sql = form.cleaned_data['raw_sql']
        params = form.cleaned_data['params']
        cursor = form.cursor
        result = None
        headers = None
        result_error = None
        try:
            cursor.execute("SET PROFILING=1")  # Enable profiling
            cursor.execute(sql, params)  # Execute SELECT
            cursor.execute("SET PROFILING=0")  # Disable profiling
            # The Query ID should always be 1 here but I'll subselect to get
            # the last one just in case...
            cursor.execute("""
  SELECT  *
    FROM  information_schema.profiling
   WHERE  query_id = (
          SELECT  query_id
            FROM  information_schema.profiling
        ORDER BY  query_id DESC
           LIMIT  1
        )
""")
            headers = [d[0] for d in cursor.description]
            result = cursor.fetchall()
        except Exception:
            result_error = "Profiling is either not available or not supported by your database."
        cursor.close()
        context = {
            'result': result,
            'result_error': result_error,
            'sql': form.reformat_sql(),
            'duration': form.cleaned_data['duration'],
            'headers': headers,
            'alias': form.cleaned_data['alias'],
        }
        # Using render_to_response avoids running global context processors.
        return render_to_response('debug_toolbar/panels/sql_profile.html', context)
    return HttpResponseBadRequest('Form errors')

########NEW FILE########
__FILENAME__ = staticfiles
from __future__ import absolute_import, unicode_literals
from os.path import normpath, join
try:
    import threading
except ImportError:
    threading = None

from django.conf import settings
from django.core.files.storage import get_storage_class
from django.contrib.staticfiles import finders, storage
from django.contrib.staticfiles.templatetags import staticfiles

from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import LazyObject
from django.utils.translation import ungettext, ugettext_lazy as _
try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict

from debug_toolbar import panels
from debug_toolbar.utils import ThreadCollector


@python_2_unicode_compatible
class StaticFile(object):
    """
    Representing the different properties of a static file.
    """
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return self.path

    def real_path(self):
        return finders.find(self.path)

    def url(self):
        return storage.staticfiles_storage.url(self.path)


class FileCollector(ThreadCollector):

    def collect(self, path, thread=None):
        # handle the case of {% static "admin/" %}
        if path.endswith('/'):
            return
        super(FileCollector, self).collect(StaticFile(path), thread)


collector = FileCollector()


class DebugConfiguredStorage(LazyObject):
    """
    A staticfiles storage class to be used for collecting which paths
    are resolved by using the {% static %} template tag (which uses the
    `url` method).
    """
    def _setup(self):

        configured_storage_cls = get_storage_class(settings.STATICFILES_STORAGE)

        class DebugStaticFilesStorage(configured_storage_cls):

            def __init__(self, collector, *args, **kwargs):
                super(DebugStaticFilesStorage, self).__init__(*args, **kwargs)
                self.collector = collector

            def url(self, path):
                self.collector.collect(path)
                return super(DebugStaticFilesStorage, self).url(path)

        self._wrapped = DebugStaticFilesStorage(collector)

_original_storage = storage.staticfiles_storage


class StaticFilesPanel(panels.Panel):
    """
    A panel to display the found staticfiles.
    """
    name = 'Static files'
    template = 'debug_toolbar/panels/staticfiles.html'

    @property
    def title(self):
        return (_("Static files (%(num_found)s found, %(num_used)s used)") %
                {'num_found': self.num_found, 'num_used': self.num_used})

    def __init__(self, *args, **kwargs):
        super(StaticFilesPanel, self).__init__(*args, **kwargs)
        self.num_found = 0
        self._paths = {}

    def enable_instrumentation(self):
        storage.staticfiles_storage = staticfiles.staticfiles_storage = DebugConfiguredStorage()

    def disable_instrumentation(self):
        storage.staticfiles_storage = staticfiles.staticfiles_storage = _original_storage

    @property
    def num_used(self):
        return len(self._paths[threading.currentThread()])

    nav_title = _('Static files')

    @property
    def nav_subtitle(self):
        num_used = self.num_used
        return ungettext("%(num_used)s file used",
                         "%(num_used)s files used",
                         num_used) % {'num_used': num_used}

    def process_request(self, request):
        collector.clear_collection()

    def process_response(self, request, response):
        used_paths = collector.get_collection()
        self._paths[threading.currentThread()] = used_paths

        self.record_stats({
            'num_found': self.num_found,
            'num_used': self.num_used,
            'staticfiles': used_paths,
            'staticfiles_apps': self.get_staticfiles_apps(),
            'staticfiles_dirs': self.get_staticfiles_dirs(),
            'staticfiles_finders': self.get_staticfiles_finders(),
        })

    def get_staticfiles_finders(self):
        """
        Returns a sorted mapping between the finder path and the list
        of relative and file system paths which that finder was able
        to find.
        """
        finders_mapping = OrderedDict()
        for finder in finders.get_finders():
            for path, finder_storage in finder.list([]):
                if getattr(finder_storage, 'prefix', None):
                    prefixed_path = join(finder_storage.prefix, path)
                else:
                    prefixed_path = path
                finder_cls = finder.__class__
                finder_path = '.'.join([finder_cls.__module__,
                                        finder_cls.__name__])
                real_path = finder_storage.path(path)
                payload = (prefixed_path, real_path)
                finders_mapping.setdefault(finder_path, []).append(payload)
                self.num_found += 1
        return finders_mapping

    def get_staticfiles_dirs(self):
        """
        Returns a list of paths to inspect for additional static files
        """
        dirs = []
        for finder in finders.get_finders():
            if isinstance(finder, finders.FileSystemFinder):
                dirs.extend(finder.locations)
        return [(prefix, normpath(dir)) for prefix, dir in dirs]

    def get_staticfiles_apps(self):
        """
        Returns a list of app paths that have a static directory
        """
        apps = []
        for finder in finders.get_finders():
            if isinstance(finder, finders.AppDirectoriesFinder):
                for app in finder.apps:
                    if app not in apps:
                        apps.append(app)
        return apps

########NEW FILE########
__FILENAME__ = panel
from __future__ import absolute_import, unicode_literals

try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict
from os.path import normpath
from pprint import pformat

import django
from django import http
from django.conf import settings
from django.conf.urls import patterns, url
from django.db.models.query import QuerySet, RawQuerySet
from django.template import Context, RequestContext, Template
from django.template.context import get_standard_processors
from django.test.signals import template_rendered
from django.test.utils import instrumented_test_render
from django.utils.encoding import force_text
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from debug_toolbar.panels import Panel
from debug_toolbar.panels.sql.tracking import recording, SQLQueryTriggered


# Monkey-patch to enable the template_rendered signal. The receiver returns
# immediately when the panel is disabled to keep the overhead small.

# Code taken and adapted from Simon Willison and Django Snippets:
# http://www.djangosnippets.org/snippets/766/

if Template._render != instrumented_test_render:
    Template.original_render = Template._render
    Template._render = instrumented_test_render


# Monkey-patch to store items added by template context processors. The
# overhead is sufficiently small to justify enabling it unconditionally.

def _request_context__init__(
        self, request, dict_=None, processors=None, current_app=None,
        use_l10n=None, use_tz=None):
    Context.__init__(
        self, dict_, current_app=current_app,
        use_l10n=use_l10n, use_tz=use_tz)
    if processors is None:
        processors = ()
    else:
        processors = tuple(processors)
    self.context_processors = OrderedDict()
    updates = dict()
    for processor in get_standard_processors() + processors:
        name = '%s.%s' % (processor.__module__, processor.__name__)
        context = processor(request)
        self.context_processors[name] = context
        updates.update(context)
    self.update(updates)

RequestContext.__init__ = _request_context__init__


# Monkey-patch versions of Django where Template doesn't store origin.
# See https://code.djangoproject.com/ticket/16096.

if django.VERSION[:2] < (1, 7):

    old_template_init = Template.__init__

    def new_template_init(self, template_string, origin=None, name='<Unknown Template>'):
        old_template_init(self, template_string, origin, name)
        self.origin = origin

    Template.__init__ = new_template_init


class TemplatesPanel(Panel):
    """
    A panel that lists all templates used during processing of a response.
    """
    def __init__(self, *args, **kwargs):
        super(TemplatesPanel, self).__init__(*args, **kwargs)
        self.templates = []

    def _store_template_info(self, sender, **kwargs):
        template, context = kwargs['template'], kwargs['context']

        # Skip templates that we are generating through the debug toolbar.
        if (isinstance(template.name, six.string_types) and
                template.name.startswith('debug_toolbar/')):
            return

        context_list = []
        for context_layer in context.dicts:
            temp_layer = {}
            if hasattr(context_layer, 'items'):
                for key, value in context_layer.items():
                    # Replace any request elements - they have a large
                    # unicode representation and the request data is
                    # already made available from the Request panel.
                    if isinstance(value, http.HttpRequest):
                        temp_layer[key] = '<<request>>'
                    # Replace the debugging sql_queries element. The SQL
                    # data is already made available from the SQL panel.
                    elif key == 'sql_queries' and isinstance(value, list):
                        temp_layer[key] = '<<sql_queries>>'
                    # Replace LANGUAGES, which is available in i18n context processor
                    elif key == 'LANGUAGES' and isinstance(value, tuple):
                        temp_layer[key] = '<<languages>>'
                    # QuerySet would trigger the database: user can run the query from SQL Panel
                    elif isinstance(value, (QuerySet, RawQuerySet)):
                        model_name = "%s.%s" % (
                            value.model._meta.app_label, value.model.__name__)
                        temp_layer[key] = '<<%s of %s>>' % (
                            value.__class__.__name__.lower(), model_name)
                    else:
                        try:
                            recording(False)
                            pformat(value)  # this MAY trigger a db query
                        except SQLQueryTriggered:
                            temp_layer[key] = '<<triggers database query>>'
                        except UnicodeEncodeError:
                            temp_layer[key] = '<<unicode encode error>>'
                        except Exception:
                            temp_layer[key] = '<<unhandled exception>>'
                        else:
                            temp_layer[key] = value
                        finally:
                            recording(True)
            try:
                context_list.append(pformat(temp_layer))
            except UnicodeEncodeError:
                pass

        kwargs['context'] = [force_text(item) for item in context_list]
        kwargs['context_processors'] = getattr(context, 'context_processors', None)
        self.templates.append(kwargs)

    # Implement the Panel API

    nav_title = _("Templates")

    @property
    def title(self):
        num_templates = len(self.templates)
        return _("Templates (%(num_templates)s rendered)") % {'num_templates': num_templates}

    @property
    def nav_subtitle(self):
        if self.templates:
            return self.templates[0]['template'].name
        return ''

    template = 'debug_toolbar/panels/templates.html'

    @classmethod
    def get_urls(cls):
        return patterns('debug_toolbar.panels.templates.views',         # noqa
            url(r'^template_source/$', 'template_source', name='template_source'),
        )

    def enable_instrumentation(self):
        template_rendered.connect(self._store_template_info)

    def disable_instrumentation(self):
        template_rendered.disconnect(self._store_template_info)

    def process_response(self, request, response):
        template_context = []
        for template_data in self.templates:
            info = {}
            # Clean up some info about templates
            template = template_data.get('template', None)
            if not hasattr(template, 'origin'):
                continue
            if template.origin and template.origin.name:
                template.origin_name = template.origin.name
            else:
                template.origin_name = 'No origin'
            info['template'] = template
            # Clean up context for better readability
            if self.toolbar.config['SHOW_TEMPLATE_CONTEXT']:
                context_list = template_data.get('context', [])
                info['context'] = '\n'.join(context_list)
            template_context.append(info)

        # Fetch context_processors from any template
        if self.templates:
            context_processors = self.templates[0]['context_processors']
        else:
            context_processors = None

        self.record_stats({
            'templates': template_context,
            'template_dirs': [normpath(x) for x in settings.TEMPLATE_DIRS],
            'context_processors': context_processors,
        })

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import, unicode_literals

from django.http import HttpResponseBadRequest
from django.conf import settings
from django.shortcuts import render_to_response
from django.template import TemplateDoesNotExist
from django.template.loader import find_template_loader
from django.utils.safestring import mark_safe


def template_source(request):
    """
    Return the source of a template, syntax-highlighted by Pygments if
    it's available.
    """
    template_name = request.GET.get('template', None)
    if template_name is None:
        return HttpResponseBadRequest('"template" key is required')

    loaders = []
    for loader_name in settings.TEMPLATE_LOADERS:
        loader = find_template_loader(loader_name)
        if loader is not None:
            loaders.append(loader)
    for loader in loaders:
        try:
            source, display_name = loader.load_template_source(template_name)
            break
        except TemplateDoesNotExist:
            source = "Template Does Not Exist: %s" % (template_name,)

    try:
        from pygments import highlight
        from pygments.lexers import HtmlDjangoLexer
        from pygments.formatters import HtmlFormatter

        source = highlight(source, HtmlDjangoLexer(), HtmlFormatter())
        source = mark_safe(source)
        source.pygmentized = True
    except ImportError:
        pass

    # Using render_to_response avoids running global context processors.
    return render_to_response('debug_toolbar/panels/template_source.html', {
        'source': source,
        'template_name': template_name
    })

########NEW FILE########
__FILENAME__ = timer
from __future__ import absolute_import, unicode_literals

try:
    import resource     # Not available on Win32 systems
except ImportError:
    resource = None
import time
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from debug_toolbar.panels import Panel


class TimerPanel(Panel):
    """
    Panel that displays the time a response took in milliseconds.
    """

    def nav_subtitle(self):
        stats = self.get_stats()
        if hasattr(self, '_start_rusage'):
            utime = self._end_rusage.ru_utime - self._start_rusage.ru_utime
            stime = self._end_rusage.ru_stime - self._start_rusage.ru_stime
            return _("CPU: %(cum)0.2fms (%(total)0.2fms)") % {
                'cum': (utime + stime) * 1000.0,
                'total': stats['total_time']
            }
        elif 'total_time' in stats:
            return _("Total: %0.2fms") % stats['total_time']
        else:
            return ''

    has_content = resource is not None

    title = _("Time")

    template = 'debug_toolbar/panels/timer.html'

    @property
    def content(self):
        stats = self.get_stats()
        rows = (
            (_("User CPU time"), _("%(utime)0.3f msec") % stats),
            (_("System CPU time"), _("%(stime)0.3f msec") % stats),
            (_("Total CPU time"), _("%(total)0.3f msec") % stats),
            (_("Elapsed time"), _("%(total_time)0.3f msec") % stats),
            (_("Context switches"), _("%(vcsw)d voluntary, %(ivcsw)d involuntary") % stats),
        )
        return render_to_string(self.template, {'rows': rows})

    def process_request(self, request):
        self._start_time = time.time()
        if self.has_content:
            self._start_rusage = resource.getrusage(resource.RUSAGE_SELF)

    def process_response(self, request, response):
        stats = {}
        if hasattr(self, '_start_time'):
            stats['total_time'] = (time.time() - self._start_time) * 1000
        if hasattr(self, '_start_rusage'):
            self._end_rusage = resource.getrusage(resource.RUSAGE_SELF)
            stats['utime'] = 1000 * self._elapsed_ru('ru_utime')
            stats['stime'] = 1000 * self._elapsed_ru('ru_stime')
            stats['total'] = stats['utime'] + stats['stime']
            stats['vcsw'] = self._elapsed_ru('ru_nvcsw')
            stats['ivcsw'] = self._elapsed_ru('ru_nivcsw')
            stats['minflt'] = self._elapsed_ru('ru_minflt')
            stats['majflt'] = self._elapsed_ru('ru_majflt')
            # these are documented as not meaningful under Linux.  If you're running BSD
            # feel free to enable them, and add any others that I hadn't gotten to before
            # I noticed that I was getting nothing but zeroes and that the docs agreed. :-(
            #
            #        stats['blkin'] = self._elapsed_ru('ru_inblock')
            #        stats['blkout'] = self._elapsed_ru('ru_oublock')
            #        stats['swap'] = self._elapsed_ru('ru_nswap')
            #        stats['rss'] = self._end_rusage.ru_maxrss
            #        stats['srss'] = self._end_rusage.ru_ixrss
            #        stats['urss'] = self._end_rusage.ru_idrss
            #        stats['usrss'] = self._end_rusage.ru_isrss

        self.record_stats(stats)

    def _elapsed_ru(self, name):
        return getattr(self._end_rusage, name) - getattr(self._start_rusage, name)

########NEW FILE########
__FILENAME__ = versions
from __future__ import absolute_import, unicode_literals

import sys

import django
from django.conf import settings
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _
try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict

from debug_toolbar.panels import Panel


class VersionsPanel(Panel):
    """
    Shows versions of Python, Django, and installed apps if possible.
    """
    @property
    def nav_subtitle(self):
        return 'Django %s' % django.get_version()

    title = _("Versions")

    template = 'debug_toolbar/panels/versions.html'

    def process_response(self, request, response):
        versions = [
            ('Python', '%d.%d.%d' % sys.version_info[:3]),
            ('Django', self.get_app_version(django)),
        ]
        if django.VERSION[:2] >= (1, 7):
            versions += list(self.gen_app_versions_1_7())
        else:
            versions += list(self.gen_app_versions_1_6())
        self.record_stats({
            'versions': OrderedDict(sorted(versions, key=lambda v: v[0])),
            'paths': sys.path,
        })

    def gen_app_versions_1_7(self):
        from django.apps import apps
        for app_config in apps.get_app_configs():
            name = app_config.verbose_name
            app = app_config.module
            version = self.get_app_version(app)
            if version:
                yield name, version

    def gen_app_versions_1_6(self):
        for app in list(settings.INSTALLED_APPS):
            name = app.split('.')[-1].replace('_', ' ').capitalize()
            app = import_module(app)
            version = self.get_app_version(app)
            if version:
                yield name, version

    def get_app_version(self, app):
        if hasattr(app, 'get_version'):
            get_version = app.get_version
            if callable(get_version):
                version = get_version()
            else:
                version = get_version
        elif hasattr(app, 'VERSION'):
            version = app.VERSION
        elif hasattr(app, '__version__'):
            version = app.__version__
        else:
            return
        if isinstance(version, (list, tuple)):
            version = '.'.join(str(o) for o in version)
        return version

########NEW FILE########
__FILENAME__ = settings
from __future__ import absolute_import, unicode_literals

import warnings

from django.conf import settings
from django.utils.importlib import import_module
from django.utils import six


# Always import this module as follows:
# from debug_toolbar import settings [as dt_settings]

# Don't import directly CONFIG or PANELs, or you will miss changes performed
# with override_settings in tests.


CONFIG_DEFAULTS = {
    # Toolbar options
    'DISABLE_PANELS': set(['debug_toolbar.panels.redirects.RedirectsPanel']),
    'INSERT_BEFORE': '</body>',
    'JQUERY_URL': '//ajax.googleapis.com/ajax/libs/jquery/2.1.0/jquery.min.js',
    'RENDER_PANELS': None,
    'RESULTS_STORE_SIZE': 10,
    'ROOT_TAG_EXTRA_ATTRS': '',
    'SHOW_COLLAPSED': False,
    'SHOW_TOOLBAR_CALLBACK': 'debug_toolbar.middleware.show_toolbar',
    # Panel options
    'EXTRA_SIGNALS': [],
    'ENABLE_STACKTRACES': True,
    'HIDE_IN_STACKTRACES': (
        'socketserver' if six.PY3 else 'SocketServer',
        'threading',
        'wsgiref',
        'debug_toolbar',
        'django',
    ),
    'PROFILER_MAX_DEPTH': 10,
    'SHOW_TEMPLATE_CONTEXT': True,
    'SQL_WARNING_THRESHOLD': 500,   # milliseconds
}

USER_CONFIG = getattr(settings, 'DEBUG_TOOLBAR_CONFIG', {})
# Backward-compatibility for 1.0, remove in 2.0.
_RENAMED_CONFIG = {
    'RESULTS_STORE_SIZE': 'RESULTS_CACHE_SIZE',
    'ROOT_TAG_ATTRS': 'ROOT_TAG_EXTRA_ATTRS',
    'HIDDEN_STACKTRACE_MODULES': 'HIDE_IN_STACKTRACES'
}
for old_name, new_name in _RENAMED_CONFIG.items():
    if old_name in USER_CONFIG:
        warnings.warn(
            "%r was renamed to %r. Update your DEBUG_TOOLBAR_CONFIG "
            "setting." % (old_name, new_name), DeprecationWarning)
        USER_CONFIG[new_name] = USER_CONFIG.pop(old_name)
if 'HIDE_DJANGO_SQL' in USER_CONFIG:
    warnings.warn(
        "HIDE_DJANGO_SQL was removed. Update your "
        "DEBUG_TOOLBAR_CONFIG setting.", DeprecationWarning)
    USER_CONFIG.pop('HIDE_DJANGO_SQL')
if 'TAG' in USER_CONFIG:
    warnings.warn(
        "TAG was replaced by INSERT_BEFORE. Update your "
        "DEBUG_TOOLBAR_CONFIG setting.", DeprecationWarning)
    USER_CONFIG['INSERT_BEFORE'] = '</%s>' % USER_CONFIG.pop('TAG')

CONFIG = CONFIG_DEFAULTS.copy()
CONFIG.update(USER_CONFIG)
if not isinstance(CONFIG['SHOW_TOOLBAR_CALLBACK'], six.string_types):
    warnings.warn(
        "SHOW_TOOLBAR_CALLBACK is now a dotted path. Update your "
        "DEBUG_TOOLBAR_CONFIG setting.", DeprecationWarning)


PANELS_DEFAULTS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]

try:
    PANELS = list(settings.DEBUG_TOOLBAR_PANELS)
except AttributeError:
    PANELS = PANELS_DEFAULTS
else:
    # Backward-compatibility for 1.0, remove in 2.0.
    _RENAMED_PANELS = {
        'debug_toolbar.panels.version.VersionDebugPanel':
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerDebugPanel':
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings_vars.SettingsDebugPanel':
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeaderDebugPanel':
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request_vars.RequestVarsDebugPanel':
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLDebugPanel':
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.template.TemplateDebugPanel':
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CacheDebugPanel':
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalDebugPanel':
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logger.LoggingDebugPanel':
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.InterceptRedirectsDebugPanel':
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingDebugPanel':
        'debug_toolbar.panels.profiling.ProfilingPanel',
    }
    for index, old_panel in enumerate(PANELS):
        new_panel = _RENAMED_PANELS.get(old_panel)
        if new_panel is not None:
            warnings.warn(
                "%r was renamed to %r. Update your DEBUG_TOOLBAR_PANELS "
                "setting." % (old_panel, new_panel), DeprecationWarning)
            PANELS[index] = new_panel


if 'INTERCEPT_REDIRECTS' in USER_CONFIG:
    warnings.warn(
        "INTERCEPT_REDIRECTS is deprecated. Please use the "
        "DISABLE_PANELS config in the "
        "DEBUG_TOOLBAR_CONFIG setting.", DeprecationWarning)
    if USER_CONFIG['INTERCEPT_REDIRECTS']:
        if 'debug_toolbar.panels.redirects.RedirectsPanel' \
                in CONFIG['DISABLE_PANELS']:
            # RedirectsPanel should be enabled
            try:
                CONFIG['DISABLE_PANELS'].remove(
                    'debug_toolbar.panels.redirects.RedirectsPanel'
                )
            except KeyError:
                # We wanted to remove it, but it didn't exist. This is fine
                pass
    elif 'debug_toolbar.panels.redirects.RedirectsPanel' \
            not in CONFIG['DISABLE_PANELS']:
        # RedirectsPanel should be disabled
        CONFIG['DISABLE_PANELS'].add(
            'debug_toolbar.panels.redirects.RedirectsPanel'
        )


PATCH_SETTINGS = getattr(settings, 'DEBUG_TOOLBAR_PATCH_SETTINGS', settings.DEBUG)


# The following functions can monkey-patch settings automatically. Several
# imports are placed inside functions to make it safe to import this module.


def is_toolbar_middleware(middleware_path):
    from debug_toolbar.middleware import DebugToolbarMiddleware
    # This could be replaced by import_by_path in Django >= 1.6.
    try:
        mod_path, cls_name = middleware_path.rsplit('.', 1)
        mod = import_module(mod_path)
        middleware_cls = getattr(mod, cls_name)
    except (AttributeError, ImportError, ValueError):
        return
    return issubclass(middleware_cls, DebugToolbarMiddleware)


def is_toolbar_middleware_installed():
    return any(is_toolbar_middleware(middleware)
               for middleware in settings.MIDDLEWARE_CLASSES)


def prepend_to_setting(setting_name, value):
    """Insert value at the beginning of a list or tuple setting."""
    values = getattr(settings, setting_name)
    # Make a list [value] or tuple (value,)
    value = type(values)((value,))
    setattr(settings, setting_name, value + values)


def patch_internal_ips():
    if not settings.INTERNAL_IPS:
        prepend_to_setting('INTERNAL_IPS', '127.0.0.1')
        prepend_to_setting('INTERNAL_IPS', '::1')


def patch_middleware_classes():
    if not is_toolbar_middleware_installed():
        prepend_to_setting('MIDDLEWARE_CLASSES',
                           'debug_toolbar.middleware.DebugToolbarMiddleware')


def patch_root_urlconf():
    from django.conf.urls import include, patterns, url
    from django.core.urlresolvers import clear_url_caches, reverse, NoReverseMatch
    import debug_toolbar
    try:
        reverse('djdt:render_panel')
    except NoReverseMatch:
        urlconf_module = import_module(settings.ROOT_URLCONF)
        urlconf_module.urlpatterns = patterns('',                      # noqa
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ) + urlconf_module.urlpatterns
        clear_url_caches()


def patch_all():
    patch_internal_ips()
    patch_middleware_classes()
    patch_root_urlconf()

########NEW FILE########
__FILENAME__ = toolbar
"""
The main DebugToolbar class that loads and renders the Toolbar.
"""

from __future__ import absolute_import, unicode_literals

import uuid

import django
from django.conf import settings
from django.conf.urls import patterns, url
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.importlib import import_module
try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict

from debug_toolbar import settings as dt_settings


class DebugToolbar(object):

    def __init__(self, request):
        self.request = request
        self.config = dt_settings.CONFIG.copy()
        self._panels = OrderedDict()
        for panel_class in self.get_panel_classes():
            panel_instance = panel_class(self)
            self._panels[panel_instance.panel_id] = panel_instance
        self.stats = {}
        self.store_id = None

    # Manage panels

    @property
    def panels(self):
        """
        Get a list of all available panels.
        """
        return list(self._panels.values())

    @property
    def enabled_panels(self):
        """
        Get a list of panels enabled for the current request.
        """
        return [panel for panel in self._panels.values() if panel.enabled]

    def get_panel_by_id(self, panel_id):
        """
        Get the panel with the given id, which is the class name by default.
        """
        return self._panels[panel_id]

    # Handle rendering the toolbar in HTML

    def render_toolbar(self):
        """
        Renders the overall Toolbar with panels inside.
        """
        if not self.should_render_panels():
            self.store()
        try:
            context = {'toolbar': self}
            return render_to_string('debug_toolbar/base.html', context)
        except TemplateSyntaxError:
            if django.VERSION[:2] >= (1, 7):
                from django.apps import apps
                staticfiles_installed = apps.is_installed(
                    'django.contrib.staticfiles')
            else:
                staticfiles_installed = ('django.contrib.staticfiles'
                                         in settings.INSTALLED_APPS)
            if not staticfiles_installed:
                raise ImproperlyConfigured(
                    "The debug toolbar requires the staticfiles contrib app. "
                    "Add 'django.contrib.staticfiles' to INSTALLED_APPS and "
                    "define STATIC_URL in your settings.")
            else:
                raise

    # Handle storing toolbars in memory and fetching them later on

    _store = OrderedDict()

    def should_render_panels(self):
        render_panels = self.config['RENDER_PANELS']
        if render_panels is None:
            # Django 1.4 still supports mod_python :( Fall back to the safe
            # and inefficient default in that case. Revert when we drop 1.4.
            render_panels = self.request.META.get('wsgi.multiprocess', True)
        return render_panels

    def store(self):
        self.store_id = uuid.uuid4().hex
        cls = type(self)
        cls._store[self.store_id] = self
        for _ in range(len(cls._store) - self.config['RESULTS_STORE_SIZE']):
            try:
                # collections.OrderedDict
                cls._store.popitem(last=False)
            except TypeError:
                # django.utils.datastructures.SortedDict
                del cls._store[cls._store.keyOrder[0]]

    @classmethod
    def fetch(cls, store_id):
        return cls._store.get(store_id)

    # Manually implement class-level caching of panel classes and url patterns
    # because it's more obvious than going through an abstraction.

    _panel_classes = None

    @classmethod
    def get_panel_classes(cls):
        if cls._panel_classes is None:
            # Load panels in a temporary variable for thread safety.
            panel_classes = []
            for panel_path in dt_settings.PANELS:
                # This logic could be replaced with import_by_path in Django 1.6.
                try:
                    panel_module, panel_classname = panel_path.rsplit('.', 1)
                except ValueError:
                    raise ImproperlyConfigured(
                        "%s isn't a debug panel module" % panel_path)
                try:
                    mod = import_module(panel_module)
                except ImportError as e:
                    raise ImproperlyConfigured(
                        'Error importing debug panel %s: "%s"' %
                        (panel_module, e))
                try:
                    panel_class = getattr(mod, panel_classname)
                except AttributeError:
                    raise ImproperlyConfigured(
                        'Toolbar Panel module "%s" does not define a "%s" class' %
                        (panel_module, panel_classname))
                panel_classes.append(panel_class)
            cls._panel_classes = panel_classes
        return cls._panel_classes

    _urlpatterns = None

    @classmethod
    def get_urls(cls):
        if cls._urlpatterns is None:
            # Load URLs in a temporary variable for thread safety.
            # Global URLs
            urlpatterns = patterns('debug_toolbar.views',               # noqa
                url(r'^render_panel/$', 'render_panel', name='render_panel'),
            )
            # Per-panel URLs
            for panel_class in cls.get_panel_classes():
                urlpatterns += panel_class.get_urls()
            cls._urlpatterns = urlpatterns
        return cls._urlpatterns


urlpatterns = DebugToolbar.get_urls()

########NEW FILE########
__FILENAME__ = utils
from __future__ import absolute_import, unicode_literals

import inspect
import os.path
import re
import sys
try:
    import threading
except ImportError:
    threading = None

import django
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.importlib import import_module
from django.utils.safestring import mark_safe
from django.utils import six
from django.views.debug import linebreak_iter

from .settings import CONFIG

# Figure out some paths
django_path = os.path.realpath(os.path.dirname(django.__file__))


def get_module_path(module_name):
    try:
        module = import_module(module_name)
    except ImportError as e:
        raise ImproperlyConfigured(
            'Error importing HIDE_IN_STACKTRACES: %s' % (e,))
    else:
        source_path = inspect.getsourcefile(module)
        if source_path.endswith('__init__.py'):
            source_path = os.path.dirname(source_path)
        return os.path.realpath(source_path)


hidden_paths = [
    get_module_path(module_name)
    for module_name in CONFIG['HIDE_IN_STACKTRACES']
]


def omit_path(path):
    return any(path.startswith(hidden_path) for hidden_path in hidden_paths)


def tidy_stacktrace(stack):
    """
    Clean up stacktrace and remove all entries that:
    1. Are part of Django (except contrib apps)
    2. Are part of socketserver (used by Django's dev server)
    3. Are the last entry (which is part of our stacktracing code)

    ``stack`` should be a list of frame tuples from ``inspect.stack()``
    """
    trace = []
    for frame, path, line_no, func_name, text in (f[:5] for f in stack):
        if omit_path(os.path.realpath(path)):
            continue
        text = (''.join(force_text(t) for t in text)).strip() if text else ''
        trace.append((path, line_no, func_name, text))
    return trace


def render_stacktrace(trace):
    stacktrace = []
    for frame in trace:
        params = map(escape, frame[0].rsplit(os.path.sep, 1) + list(frame[1:]))
        params_dict = dict((six.text_type(idx), v) for idx, v in enumerate(params))
        try:
            stacktrace.append('<span class="path">%(0)s/</span>'
                              '<span class="file">%(1)s</span>'
                              ' in <span class="func">%(3)s</span>'
                              '(<span class="lineno">%(2)s</span>)\n'
                              '  <span class="code">%(4)s</span>'
                              % params_dict)
        except KeyError:
            # This frame doesn't have the expected format, so skip it and move on to the next one
            continue
    return mark_safe('\n'.join(stacktrace))


def get_template_info(source, context_lines=3):
    line = 0
    upto = 0
    source_lines = []
    # before = during = after = ""

    origin, (start, end) = source
    template_source = origin.reload()

    for num, next in enumerate(linebreak_iter(template_source)):
        if start >= upto and end <= next:
            line = num
            # before = template_source[upto:start]
            # during = template_source[start:end]
            # after = template_source[end:next]
        source_lines.append((num, template_source[upto:next]))
        upto = next

    top = max(1, line - context_lines)
    bottom = min(len(source_lines), line + 1 + context_lines)

    context = []
    for num, content in source_lines[top:bottom]:
        context.append({
            'num': num,
            'content': content,
            'highlight': (num == line),
        })

    return {
        'name': origin.name,
        'context': context,
    }


def get_name_from_obj(obj):
    if hasattr(obj, '__name__'):
        name = obj.__name__
    elif hasattr(obj, '__class__') and hasattr(obj.__class__, '__name__'):
        name = obj.__class__.__name__
    else:
        name = '<unknown>'

    if hasattr(obj, '__module__'):
        module = obj.__module__
        name = '%s.%s' % (module, name)

    return name


def getframeinfo(frame, context=1):
    """
    Get information about a frame or traceback object.

    A tuple of five things is returned: the filename, the line number of
    the current line, the function name, a list of lines of context from
    the source code, and the index of the current line within that list.
    The optional second argument specifies the number of lines of context
    to return, which are centered around the current line.

    This originally comes from ``inspect`` but is modified to handle issues
    with ``findsource()``.
    """
    if inspect.istraceback(frame):
        lineno = frame.tb_lineno
        frame = frame.tb_frame
    else:
        lineno = frame.f_lineno
    if not inspect.isframe(frame):
        raise TypeError('arg is not a frame or traceback object')

    filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
    if context > 0:
        start = lineno - 1 - context // 2
        try:
            lines, lnum = inspect.findsource(frame)
        except Exception:   # findsource raises platform-dependant exceptions
            first_lines = lines = index = None
        else:
            start = max(start, 1)
            start = max(0, min(start, len(lines) - context))
            first_lines = lines[:2]
            lines = lines[start:(start + context)]
            index = lineno - 1 - start
    else:
        first_lines = lines = index = None

    # Code taken from Django's ExceptionReporter._get_lines_from_file
    if first_lines and isinstance(first_lines[0], bytes):
        encoding = 'ascii'
        for line in first_lines[:2]:
            # File coding may be specified. Match pattern from PEP-263
            # (http://www.python.org/dev/peps/pep-0263/)
            match = re.search(br'coding[:=]\s*([-\w.]+)', line)
            if match:
                encoding = match.group(1).decode('ascii')
                break
        lines = [line.decode(encoding, 'replace') for line in lines]

    if hasattr(inspect, 'Traceback'):
        return inspect.Traceback(filename, lineno, frame.f_code.co_name, lines, index)
    else:
        return (filename, lineno, frame.f_code.co_name, lines, index)


def get_stack(context=1):
    """
    Get a list of records for a frame and all higher (calling) frames.

    Each record contains a frame object, filename, line number, function
    name, a list of lines of context, and index within the context.

    Modified version of ``inspect.stack()`` which calls our own ``getframeinfo()``
    """
    frame = sys._getframe(1)
    framelist = []
    while frame:
        framelist.append((frame,) + getframeinfo(frame, context))
        frame = frame.f_back
    return framelist


class ThreadCollector(object):
    def __init__(self):
        if threading is None:
            raise NotImplementedError(
                "threading module is not available, "
                "this panel cannot be used without it")
        self.collections = {}  # a dictionary that maps threads to collections

    def get_collection(self, thread=None):
        """
        Returns a list of collected items for the provided thread, of if none
        is provided, returns a list for the current thread.
        """
        if thread is None:
            thread = threading.currentThread()
        if thread not in self.collections:
            self.collections[thread] = []
        return self.collections[thread]

    def clear_collection(self, thread=None):
        if thread is None:
            thread = threading.currentThread()
        if thread in self.collections:
            del self.collections[thread]

    def collect(self, item, thread=None):
        self.get_collection(thread).append(item)

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import, unicode_literals

from django.http import HttpResponse
from django.utils.html import escape
from django.utils.translation import ugettext as _

from debug_toolbar.toolbar import DebugToolbar


def render_panel(request):
    """Render the contents of a panel"""
    toolbar = DebugToolbar.fetch(request.GET['store_id'])
    if toolbar is None:
        content = _("Data for this panel isn't available anymore. "
                    "Please reload the page and retry.")
        content = "<p>%s</p>" % escape(content)
    else:
        panel = toolbar.get_panel_by_id(request.GET['panel_id'])
        content = panel.content
    return HttpResponse(content)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django Debug Toolbar documentation build configuration file, created by
# sphinx-quickstart on Sun Oct 27 13:18:25 2013.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'example.settings'
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django Debug Toolbar'
copyright = u'2013, Django Debug Toolbar developers and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.2'
# The full version, including alpha/beta/rc tags.
release = '1.2.1'

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

# The reST default role (used for this markup: `text`) to use for all
# documents.
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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

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

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

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
htmlhelp_basename = 'DjangoDebugToolbardoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'DjangoDebugToolbar.tex', u'Django Debug Toolbar Documentation',
   u'Django Debug Toolbar developers and contributors', 'manual'),
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


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'djangodebugtoolbar', u'Django Debug Toolbar Documentation',
     [u'Django Debug Toolbar developers and contributors'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'DjangoDebugToolbar', u'Django Debug Toolbar Documentation',
   u'Django Debug Toolbar developers and contributors', 'DjangoDebugToolbar', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'http://docs.python.org/': None,
    'http://docs.djangoproject.com/en/dev/': 'http://docs.djangoproject.com/en/dev/_objects/',
}

# -- Options for Read the Docs --------------------------------------------

RTD_NEW_THEME = True

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
"""Django settings for example project."""

import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production

SECRET_KEY = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'

DEBUG = True

TEMPLATE_DEBUG = True


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'debug_toolbar',
)

ROOT_URLCONF = 'example.urls'

STATIC_URL = '/static/'

TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'example', 'templates')]

WSGI_APPLICATION = 'example.wsgi.application'


# Cache and database

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'example', 'db.sqlite3'),
    }
}

# To use another database, set the DJANGO_DATABASE_ENGINE environment variable.
if os.environ.get('DJANGO_DATABASE_ENGINE', '').lower() == 'postgresql':
    # % su postgres
    # % createuser debug_toolbar
    # % createdb debug_toolbar -O debug_toolbar
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'debug_toolbar',
            'USER': 'debug_toolbar',
        }
    }
if os.environ.get('DJANGO_DATABASE_ENGINE', '').lower() == 'mysql':
    # % mysql
    # mysql> CREATE DATABASE debug_toolbar;
    # mysql> GRANT ALL PRIVILEGES ON debug_toolbar.* TO 'debug_toolbar'@'localhost';
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'debug_toolbar',
            'USER': 'debug_toolbar',
        }
    }


# django-debug-toolbar

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'debug_toolbar.panels.profiling.ProfilingPanel',
]

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'example', 'static')]

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include
from django.contrib import admin
from django.views.generic import TemplateView

admin.autodiscover()

urlpatterns = patterns('',                                              # noqa
    (r'^$', TemplateView.as_view(template_name='index.html')),
    (r'^jquery/$', TemplateView.as_view(template_name='jquery/index.html')),
    (r'^mootools/$', TemplateView.as_view(template_name='mootools/index.html')),
    (r'^prototype/$', TemplateView.as_view(template_name='prototype/index.html')),
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""WSGI config for example project."""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = base
from __future__ import absolute_import, unicode_literals

import threading

from django.http import HttpResponse
from django.test import TestCase, RequestFactory

from debug_toolbar.middleware import DebugToolbarMiddleware
from debug_toolbar.toolbar import DebugToolbar

rf = RequestFactory()


class BaseTestCase(TestCase):

    def setUp(self):
        request = rf.get('/')
        response = HttpResponse()
        toolbar = DebugToolbar(request)

        DebugToolbarMiddleware.debug_toolbars[threading.current_thread().ident] = toolbar

        self.request = request
        self.response = response
        self.toolbar = toolbar
        self.toolbar.stats = {}

########NEW FILE########
__FILENAME__ = test_debugsqlshell
from __future__ import absolute_import, unicode_literals

import sys

from django.contrib.auth.models import User
from django.core import management
try:
    from django.db.backends import utils
except ImportError:
    from django.db.backends import util as utils
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import six


@override_settings(DEBUG=True)
class DebugSQLShellTestCase(TestCase):

    def setUp(self):
        self.original_cursor_wrapper = utils.CursorDebugWrapper
        # Since debugsqlshell monkey-patches django.db.backends.utils, we can
        # test it simply by loading it, without executing it. But we have to
        # undo the monkey-patch on exit.
        command_name = 'debugsqlshell'
        app_name = management.get_commands()[command_name]
        management.load_command_class(app_name, command_name)

    def tearDown(self):
        utils.CursorDebugWrapper = self.original_cursor_wrapper

    def test_command(self):
        original_stdout, sys.stdout = sys.stdout, six.StringIO()
        try:
            User.objects.count()
            self.assertIn("SELECT COUNT(*)", sys.stdout.getvalue())
        finally:
            sys.stdout = original_stdout

########NEW FILE########
__FILENAME__ = context_processors
def broken(request):
    request.non_existing_attribute

########NEW FILE########
__FILENAME__ = models
# coding: utf-8

from __future__ import absolute_import, unicode_literals

from django.utils import six


class NonAsciiRepr(object):
    def __repr__(self):
        return 'nôt åscíì' if six.PY3 else 'nôt åscíì'.encode('utf-8')

########NEW FILE########
__FILENAME__ = test_cache
# coding: utf-8

from __future__ import absolute_import, unicode_literals

from django.core import cache

from ..base import BaseTestCase


class CachePanelTestCase(BaseTestCase):

    def setUp(self):
        super(CachePanelTestCase, self).setUp()
        self.panel = self.toolbar.get_panel_by_id('CachePanel')
        self.panel.enable_instrumentation()

    def tearDown(self):
        self.panel.disable_instrumentation()
        super(CachePanelTestCase, self).tearDown()

    def test_recording(self):
        self.assertEqual(len(self.panel.calls), 0)
        cache.cache.set('foo', 'bar')
        cache.cache.get('foo')
        cache.cache.delete('foo')
        self.assertEqual(len(self.panel.calls), 3)

########NEW FILE########
__FILENAME__ = test_logging
from __future__ import absolute_import, unicode_literals

import logging

from debug_toolbar.panels.logging import (
    collector, MESSAGE_IF_STRING_REPRESENTATION_INVALID)

from ..base import BaseTestCase


class LoggingPanelTestCase(BaseTestCase):

    def setUp(self):
        super(LoggingPanelTestCase, self).setUp()
        self.panel = self.toolbar.get_panel_by_id('LoggingPanel')
        self.logger = logging.getLogger(__name__)
        collector.clear_collection()

    def test_happy_case(self):
        self.logger.info('Nothing to see here, move along!')

        self.panel.process_response(self.request, self.response)
        records = self.panel.get_stats()['records']

        self.assertEqual(1, len(records))
        self.assertEqual('Nothing to see here, move along!',
                         records[0]['message'])

    def test_formatting(self):
        self.logger.info('There are %d %s', 5, 'apples')

        self.panel.process_response(self.request, self.response)
        records = self.panel.get_stats()['records']

        self.assertEqual(1, len(records))
        self.assertEqual('There are 5 apples',
                         records[0]['message'])

    def test_failing_formatting(self):
        class BadClass(object):
            def __str__(self):
                raise Exception('Please not stringify me!')

        # should not raise exception, but fail silently
        self.logger.debug('This class is misbehaving: %s', BadClass())

        self.panel.process_response(self.request, self.response)
        records = self.panel.get_stats()['records']

        self.assertEqual(1, len(records))
        self.assertEqual(MESSAGE_IF_STRING_REPRESENTATION_INVALID,
                         records[0]['message'])

########NEW FILE########
__FILENAME__ = test_profiling
from __future__ import absolute_import, unicode_literals

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import unittest

from ..base import BaseTestCase
from ..views import regular_view


@override_settings(DEBUG_TOOLBAR_PANELS=['debug_toolbar.panels.profiling.ProfilingPanel'])
class ProfilingPanelTestCase(BaseTestCase):

    def setUp(self):
        super(ProfilingPanelTestCase, self).setUp()
        self.panel = self.toolbar.get_panel_by_id('ProfilingPanel')

    # This test fails randomly for a reason I don't understand.

    @unittest.expectedFailure
    def test_regular_view(self):
        self.panel.process_view(self.request, regular_view, ('profiling',), {})
        self.panel.process_response(self.request, self.response)
        self.assertIn('func_list', self.panel.get_stats())
        self.assertIn('regular_view', self.panel.content)


@override_settings(DEBUG=True,
                   DEBUG_TOOLBAR_PANELS=['debug_toolbar.panels.profiling.ProfilingPanel'])
class ProfilingPanelIntegrationTestCase(TestCase):

    def test_view_executed_once(self):
        self.assertEqual(User.objects.count(), 0)

        response = self.client.get('/new_user/')
        self.assertContains(response, 'Profiling')
        self.assertEqual(User.objects.count(), 1)

        with self.assertRaises(IntegrityError):
            if hasattr(transaction, 'atomic'):      # Django >= 1.6
                with transaction.atomic():
                    response = self.client.get('/new_user/')
            else:
                response = self.client.get('/new_user/')
        self.assertEqual(User.objects.count(), 1)

########NEW FILE########
__FILENAME__ = test_redirects
from __future__ import absolute_import, unicode_literals

import django
from django.conf import settings
from django.http import HttpResponse
from django.test.utils import override_settings
from django.utils import unittest

from ..base import BaseTestCase


@override_settings(DEBUG_TOOLBAR_CONFIG={'INTERCEPT_REDIRECTS': True})
class RedirectsPanelTestCase(BaseTestCase):

    def setUp(self):
        super(RedirectsPanelTestCase, self).setUp()
        self.panel = self.toolbar.get_panel_by_id('RedirectsPanel')

    def test_regular_response(self):
        response = self.panel.process_response(self.request, self.response)
        self.assertTrue(response is self.response)

    def test_not_a_redirect(self):
        redirect = HttpResponse(status=304)     # not modified
        response = self.panel.process_response(self.request, redirect)
        self.assertTrue(response is redirect)

    def test_redirect(self):
        redirect = HttpResponse(status=302)
        redirect['Location'] = 'http://somewhere/else/'
        response = self.panel.process_response(self.request, redirect)
        self.assertFalse(response is redirect)
        self.assertContains(response, '302 FOUND')
        self.assertContains(response, 'http://somewhere/else/')

    def test_redirect_with_broken_context_processor(self):
        context_processors = settings.TEMPLATE_CONTEXT_PROCESSORS + (
            'tests.context_processors.broken',
        )

        with self.settings(TEMPLATE_CONTEXT_PROCESSORS=context_processors):
            redirect = HttpResponse(status=302)
            redirect['Location'] = 'http://somewhere/else/'
            response = self.panel.process_response(self.request, redirect)
            self.assertFalse(response is redirect)
            self.assertContains(response, '302 FOUND')
            self.assertContains(response, 'http://somewhere/else/')

    def test_unknown_status_code(self):
        redirect = HttpResponse(status=369)
        redirect['Location'] = 'http://somewhere/else/'
        response = self.panel.process_response(self.request, redirect)
        self.assertContains(response, '369 UNKNOWN STATUS CODE')

    @unittest.skipIf(django.VERSION[:2] < (1, 6), "reason isn't supported")
    def test_unknown_status_code_with_reason(self):
        redirect = HttpResponse(status=369, reason='Look Ma!')
        redirect['Location'] = 'http://somewhere/else/'
        response = self.panel.process_response(self.request, redirect)
        self.assertContains(response, '369 Look Ma!')

########NEW FILE########
__FILENAME__ = test_request
# coding: utf-8

from __future__ import absolute_import, unicode_literals

from django.utils import six

from ..base import BaseTestCase


class RequestPanelTestCase(BaseTestCase):

    def setUp(self):
        super(RequestPanelTestCase, self).setUp()
        self.panel = self.toolbar.get_panel_by_id('RequestPanel')

    def test_non_ascii_session(self):
        self.request.session = {'où': 'où'}
        if not six.PY3:
            self.request.session['là'.encode('utf-8')] = 'là'.encode('utf-8')
        self.panel.process_request(self.request)
        self.panel.process_response(self.request, self.response)
        content = self.panel.content
        if six.PY3:
            self.assertIn('où', content)
        else:
            self.assertIn('o\\xf9', content)
            self.assertIn('l\\xc3\\xa0', content)

    def test_object_with_non_ascii_repr_in_request_params(self):
        self.request.path = '/non_ascii_request/'
        self.panel.process_request(self.request)
        self.panel.process_response(self.request, self.response)
        self.assertIn('nôt åscíì', self.panel.content)

########NEW FILE########
__FILENAME__ = test_sql
# coding: utf-8

from __future__ import absolute_import, unicode_literals

from django.contrib.auth.models import User
from django.db import connection
from django.db.utils import DatabaseError
from django.utils import unittest

from ..base import BaseTestCase


class SQLPanelTestCase(BaseTestCase):

    def setUp(self):
        super(SQLPanelTestCase, self).setUp()
        self.panel = self.toolbar.get_panel_by_id('SQLPanel')
        self.panel.enable_instrumentation()

    def tearDown(self):
        self.panel.disable_instrumentation()
        super(SQLPanelTestCase, self).tearDown()

    def test_recording(self):
        self.assertEqual(len(self.panel._queries), 0)

        list(User.objects.all())

        # ensure query was logged
        self.assertEqual(len(self.panel._queries), 1)
        query = self.panel._queries[0]
        self.assertEqual(query[0], 'default')
        self.assertTrue('sql' in query[1])
        self.assertTrue('duration' in query[1])
        self.assertTrue('stacktrace' in query[1])

        # ensure the stacktrace is populated
        self.assertTrue(len(query[1]['stacktrace']) > 0)

    def test_non_ascii_query(self):
        self.assertEqual(len(self.panel._queries), 0)

        # non-ASCII text query
        list(User.objects.extra(where=["username = 'apéro'"]))
        self.assertEqual(len(self.panel._queries), 1)

        # non-ASCII text parameters
        list(User.objects.filter(username='thé'))
        self.assertEqual(len(self.panel._queries), 2)

        # non-ASCII bytes parameters
        list(User.objects.filter(username='café'.encode('utf-8')))
        self.assertEqual(len(self.panel._queries), 3)

        self.panel.process_response(self.request, self.response)

        # ensure the panel renders correctly
        self.assertIn('café', self.panel.content)

    @unittest.skipUnless(connection.vendor == 'postgresql',
                         'Test valid only on PostgreSQL')
    def test_erroneous_query(self):
        """
        Test that an error in the query isn't swallowed by the middleware.
        """
        try:
            connection.cursor().execute("erroneous query")
        except DatabaseError as e:
            self.assertTrue('erroneous query' in str(e))

    def test_disable_stacktraces(self):
        self.assertEqual(len(self.panel._queries), 0)

        with self.settings(DEBUG_TOOLBAR_CONFIG={'ENABLE_STACKTRACES': False}):
            list(User.objects.all())

        # ensure query was logged
        self.assertEqual(len(self.panel._queries), 1)
        query = self.panel._queries[0]
        self.assertEqual(query[0], 'default')
        self.assertTrue('sql' in query[1])
        self.assertTrue('duration' in query[1])
        self.assertTrue('stacktrace' in query[1])

        # ensure the stacktrace is empty
        self.assertEqual([], query[1]['stacktrace'])

########NEW FILE########
__FILENAME__ = test_staticfiles
# coding: utf-8

from __future__ import absolute_import, unicode_literals

from django.contrib.staticfiles import finders

from ..base import BaseTestCase


class StaticFilesPanelTestCase(BaseTestCase):

    def setUp(self):
        super(StaticFilesPanelTestCase, self).setUp()
        self.panel = self.toolbar.get_panel_by_id('StaticFilesPanel')

    def test_default_case(self):
        self.panel.process_request(self.request)
        self.panel.process_response(self.request, self.response)
        self.assertIn('django.contrib.staticfiles.finders.'
                      'AppDirectoriesFinder', self.panel.content)
        self.assertIn('django.contrib.staticfiles.finders.'
                      'FileSystemFinder (2 files)', self.panel.content)
        self.assertEqual(self.panel.num_used, 0)
        self.assertNotEqual(self.panel.num_found, 0)
        self.assertEqual(self.panel.get_staticfiles_apps(),
                         ['django.contrib.admin', 'debug_toolbar'])
        self.assertEqual(self.panel.get_staticfiles_dirs(),
                         finders.FileSystemFinder().locations)

########NEW FILE########
__FILENAME__ = test_template
# coding: utf-8

from __future__ import absolute_import, unicode_literals

import django
from django.contrib.auth.models import User
from django.template import Context, RequestContext, Template

from ..base import BaseTestCase
from ..models import NonAsciiRepr


class TemplatesPanelTestCase(BaseTestCase):

    def setUp(self):
        super(TemplatesPanelTestCase, self).setUp()
        self.panel = self.toolbar.get_panel_by_id('TemplatesPanel')
        self.panel.enable_instrumentation()
        self.sql_panel = self.toolbar.get_panel_by_id('SQLPanel')
        self.sql_panel.enable_instrumentation()

    def tearDown(self):
        self.sql_panel.disable_instrumentation()
        self.panel.disable_instrumentation()
        super(TemplatesPanelTestCase, self).tearDown()

    def test_queryset_hook(self):
        t = Template("No context variables here!")
        c = Context({
            'queryset': User.objects.all(),
            'deep_queryset': {
                'queryset': User.objects.all(),
            }
        })
        t.render(c)

        # ensure the query was NOT logged
        self.assertEqual(len(self.sql_panel._queries), 0)

        base_ctx_idx = 1 if django.VERSION[:2] >= (1, 5) else 0
        ctx = self.panel.templates[0]['context'][base_ctx_idx]
        self.assertIn('<<queryset of auth.User>>', ctx)
        self.assertIn('<<triggers database query>>', ctx)

    def test_object_with_non_ascii_repr_in_context(self):
        self.panel.process_request(self.request)
        t = Template("{{ object }}")
        c = Context({'object': NonAsciiRepr()})
        t.render(c)
        self.panel.process_response(self.request, self.response)
        self.assertIn('nôt åscíì', self.panel.content)

    def test_custom_context_processor(self):
        self.panel.process_request(self.request)
        t = Template("{{ content }}")
        c = RequestContext(self.request, processors=[context_processor])
        t.render(c)
        self.panel.process_response(self.request, self.response)
        self.assertIn('tests.panels.test_template.context_processor', self.panel.content)


def context_processor(request):
    return {'content': 'set by processor'}

########NEW FILE########
__FILENAME__ = settings
"""Django settings for tests."""

import os
import django

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production

SECRET_KEY = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'

INTERNAL_IPS = ['127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'debug_toolbar',
    'tests',
]

MEDIA_URL = '/media/'   # Avoids https://code.djangoproject.com/ticket/21451

MIDDLEWARE_CLASSES = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tests.urls'

STATIC_ROOT = os.path.join(BASE_DIR, 'tests', 'static')

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'tests', 'additional_static'),
    ("prefix", os.path.join(BASE_DIR, 'tests', 'additional_static')),
]

# Cache and database

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}


# Debug Toolbar configuration

DEBUG_TOOLBAR_CONFIG = {
    # Django's test client sets wsgi.multiprocess to True inappropriately
    'RENDER_PANELS': False,
}

if django.VERSION[:2] < (1, 6):
    TEST_RUNNER = 'discover_runner.DiscoverRunner'

########NEW FILE########
__FILENAME__ = test_integration
# coding: utf-8

from __future__ import absolute_import, unicode_literals

import os
from xml.etree import ElementTree as ET

try:
    from selenium import webdriver
    from selenium.common.exceptions import NoSuchElementException
    from selenium.webdriver.support.wait import WebDriverWait
except ImportError:
    webdriver = None

from django.test import LiveServerTestCase, RequestFactory, TestCase
from django.test.utils import override_settings
from django.utils.unittest import skipIf, skipUnless

from debug_toolbar.middleware import DebugToolbarMiddleware, show_toolbar

from .base import BaseTestCase
from .views import regular_view


rf = RequestFactory()


@override_settings(DEBUG=True)
class DebugToolbarTestCase(BaseTestCase):

    def test_show_toolbar(self):
        self.assertTrue(show_toolbar(self.request))

    def test_show_toolbar_DEBUG(self):
        with self.settings(DEBUG=False):
            self.assertFalse(show_toolbar(self.request))

    def test_show_toolbar_INTERNAL_IPS(self):
        with self.settings(INTERNAL_IPS=[]):
            self.assertFalse(show_toolbar(self.request))

    def _resolve_stats(self, path):
        # takes stats from Request panel
        self.request.path = path
        panel = self.toolbar.get_panel_by_id('RequestPanel')
        panel.process_request(self.request)
        panel.process_response(self.request, self.response)
        return panel.get_stats()

    def test_url_resolving_positional(self):
        stats = self._resolve_stats('/resolving1/a/b/')
        self.assertEqual(stats['view_urlname'], 'positional-resolving')
        self.assertEqual(stats['view_func'], 'tests.views.resolving_view')
        self.assertEqual(stats['view_args'], ('a', 'b'))
        self.assertEqual(stats['view_kwargs'], {})

    def test_url_resolving_named(self):
        stats = self._resolve_stats('/resolving2/a/b/')
        self.assertEqual(stats['view_args'], ())
        self.assertEqual(stats['view_kwargs'], {'arg1': 'a', 'arg2': 'b'})

    def test_url_resolving_mixed(self):
        stats = self._resolve_stats('/resolving3/a/')
        self.assertEqual(stats['view_args'], ('a',))
        self.assertEqual(stats['view_kwargs'], {'arg2': 'default'})

    def test_url_resolving_bad(self):
        stats = self._resolve_stats('/non-existing-url/')
        self.assertEqual(stats['view_urlname'], 'None')
        self.assertEqual(stats['view_args'], 'None')
        self.assertEqual(stats['view_kwargs'], 'None')
        self.assertEqual(stats['view_func'], '<no view>')

    # Django doesn't guarantee that process_request, process_view and
    # process_response always get called in this order.

    def test_middleware_view_only(self):
        DebugToolbarMiddleware().process_view(self.request, regular_view, ('title',), {})

    def test_middleware_response_only(self):
        DebugToolbarMiddleware().process_response(self.request, self.response)

    def test_middleware_response_insertion(self):
        resp = regular_view(self.request, "İ")
        DebugToolbarMiddleware().process_response(self.request, resp)
        # check toolbar insertion before "</body>"
        self.assertContains(resp, '</div>\n</body>')


@override_settings(DEBUG=True)
class DebugToolbarIntegrationTestCase(TestCase):

    def test_middleware(self):
        response = self.client.get('/execute_sql/')
        self.assertEqual(response.status_code, 200)

    @override_settings(DEFAULT_CHARSET='iso-8859-1')
    def test_non_utf8_charset(self):
        response = self.client.get('/regular/ASCII/')
        self.assertContains(response, 'ASCII')      # template
        self.assertContains(response, 'djDebug')    # toolbar

        response = self.client.get('/regular/LÀTÍN/')
        self.assertContains(response, 'LÀTÍN')      # template
        self.assertContains(response, 'djDebug')    # toolbar

    def test_xml_validation(self):
        response = self.client.get('/regular/XML/')
        ET.fromstring(response.content)     # shouldn't raise ParseError


@skipIf(webdriver is None, "selenium isn't installed")
@skipUnless('DJANGO_SELENIUM_TESTS' in os.environ, "selenium tests not requested")
@override_settings(DEBUG=True)
class DebugToolbarLiveTestCase(LiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super(DebugToolbarLiveTestCase, cls).setUpClass()
        cls.selenium = webdriver.Firefox()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(DebugToolbarLiveTestCase, cls).tearDownClass()

    def test_basic(self):
        self.selenium.get(self.live_server_url + '/regular/basic/')
        version_panel = self.selenium.find_element_by_id('VersionsPanel')

        # Versions panel isn't loaded
        with self.assertRaises(NoSuchElementException):
            version_panel.find_element_by_tag_name('table')

        # Click to show the versions panel
        self.selenium.find_element_by_class_name('VersionsPanel').click()

        # Version panel loads
        table = WebDriverWait(self.selenium, timeout=10).until(
            lambda selenium: version_panel.find_element_by_tag_name('table'))
        self.assertIn("Name", table.text)
        self.assertIn("Version", table.text)

    @override_settings(DEBUG_TOOLBAR_CONFIG={'RESULTS_STORE_SIZE': 0})
    def test_expired_store(self):
        self.selenium.get(self.live_server_url + '/regular/basic/')
        version_panel = self.selenium.find_element_by_id('VersionsPanel')

        # Click to show the version panel
        self.selenium.find_element_by_class_name('VersionsPanel').click()

        # Version panel doesn't loads
        error = WebDriverWait(self.selenium, timeout=10).until(
            lambda selenium: version_panel.find_element_by_tag_name('p'))
        self.assertIn("Data for this panel isn't available anymore.", error.text)

########NEW FILE########
__FILENAME__ = test_utils
from __future__ import absolute_import, unicode_literals

from django.utils.unittest import TestCase

from debug_toolbar.utils import get_name_from_obj


class GetNameFromObjTestCase(TestCase):

    def test_func(self):
        def x():
            return 1
        res = get_name_from_obj(x)
        self.assertEqual(res, 'tests.test_utils.x')

    def test_lambda(self):
        res = get_name_from_obj(lambda: 1)
        self.assertEqual(res, 'tests.test_utils.<lambda>')

    def test_class(self):
        class A:
            pass
        res = get_name_from_obj(A)
        self.assertEqual(res, 'tests.test_utils.A')

########NEW FILE########
__FILENAME__ = urls
# coding: utf-8

from __future__ import absolute_import, unicode_literals

from django.conf.urls import include, patterns, url
from django.contrib import admin

import debug_toolbar

from .models import NonAsciiRepr


admin.autodiscover()

urlpatterns = patterns('tests.views',                                   # noqa
    url(r'^resolving1/(.+)/(.+)/$', 'resolving_view', name='positional-resolving'),
    url(r'^resolving2/(?P<arg1>.+)/(?P<arg2>.+)/$', 'resolving_view'),
    url(r'^resolving3/(.+)/$', 'resolving_view', {'arg2': 'default'}),
    url(r'^regular/(?P<title>.*)/$', 'regular_view'),
    url(r'^non_ascii_request/$', 'regular_view', {'title': NonAsciiRepr()}),
    url(r'^new_user/$', 'new_user'),
    url(r'^execute_sql/$', 'execute_sql'),
    url(r'^__debug__/', include(debug_toolbar.urls)),
)

########NEW FILE########
__FILENAME__ = views
# coding: utf-8

from __future__ import absolute_import, unicode_literals

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render


def execute_sql(request):
    list(User.objects.all())
    return HttpResponse()


def regular_view(request, title):
    return render(request, 'basic.html', {'title': title})


def new_user(request, username='joe'):
    User.objects.create_user(username=username)
    return render(request, 'basic.html', {'title': 'new user'})


def resolving_view(request, arg1, arg2):
    # see test_url_resolving in tests.py
    return HttpResponse()

########NEW FILE########
