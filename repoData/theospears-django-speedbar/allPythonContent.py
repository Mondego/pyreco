__FILENAME__ = middleware
"""
Speedbar module

This provides performance metrics, details of operations performed, and Chrome SpeedTracer integration
for page loads.

Information is provided by a set of modules, which are responsible for recording and reporting data.
The collected data is then collected and made available via template tags, headers, and a HAR file.

On startup each module is given a chance to initialize itself, typically this consists of monkey
patching a set of built in django functionality. A per request module object is created in response
to the start of each request. Over the course of the request modules record data, using thread local
storage to associate correctly with the right request. A middleware then writes out summary data,
and the headers required to fetch more detailed information from the server. Finally the request_finished
signal handler stores detailed information to memcache which can then be retrieved.

"""
import re

from django.conf import settings
from django.core.signals import request_started, request_finished
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_unicode, smart_str

from speedbar.signals import setup_request_tracing, store_request_trace
from speedbar.utils import init_modules
from speedbar.modules.base import RequestTrace


if getattr(settings, 'SPEEDBAR_ENABLE', True):
    # We hook everything up in the middleware file as loading the middleware is one of the first things performed
    # by the django WSGI implementation.
    init_modules()

    request_started.connect(setup_request_tracing, dispatch_uid='request_started_speedbar_setup_request_tracing')
    request_finished.connect(store_request_trace, dispatch_uid='request_started_speedbar_store_request_trace')


HTML_TYPES = ('text/html', 'application/xhtml+xml')
METRIC_PLACEHOLDER_RE = re.compile('<span data-module="(?P<module>[^"]+)" data-metric="(?P<metric>[^"]+)"></span>')


class SpeedbarMiddleware(object):
    def process_request(self, request):
        if getattr(settings, 'SPEEDBAR_ENABLE', True):
            request_trace = RequestTrace.instance()
            request_trace.stacktracer.root.label = '%s %s' % (request.method, request.path)
            request_trace.request = request

    def process_response(self, request, response):
        if not getattr(settings, 'SPEEDBAR_ENABLE', True):
            return response

        request_trace = RequestTrace.instance()
        # TODO: Do we also need to stash this on in case of exception?
        request_trace.response = response

        metrics = dict((key, module.get_metrics()) for key, module in request_trace.modules.items())

        if getattr(settings, 'SPEEDBAR_RESPONSE_HEADERS', False):
            self.add_response_headers(response, metrics)

        if hasattr(request, 'user') and request.user.is_staff:
            if getattr(settings, 'SPEEDBAR_TRACE', True):
                response['X-TraceUrl'] = reverse('speedbar_trace', args=[request_trace.id])
                request_trace.persist_log = True

            if 'gzip' not in response.get('Content-Encoding', '') and response.get('Content-Type', '').split(';')[0] in HTML_TYPES:

                # Force render of response (from lazy TemplateResponses) before speedbar is injected
                if hasattr(response, 'render'):
                    response.render()
                content = smart_unicode(response.content)

                content = self.replace_templatetag_placeholders(content, metrics)

                # Note: The URLs returned here do not exist at this point. The relevant data is added to the cache by a signal handler
                # once all page processing is finally done. This means it is possible summary values displayed and the detailed
                # break down won't quite correspond.
                if getattr(settings, 'SPEEDBAR_PANEL', True):
                    panel_url = reverse('speedbar_panel', args=[request_trace.id])
                    panel_placeholder_url = reverse('speedbar_details_for_this_request')
                    content = content.replace(panel_placeholder_url, panel_url)
                    request_trace.persist_details = True

                response.content = smart_str(content)
                if response.get('Content-Length', None):
                    response['Content-Length'] = len(response.content)
        return response

    def add_response_headers(self, response, metrics):
        """
        Adds all summary metrics to the response headers, so they can be stored in nginx logs if desired.
        """
        def sanitize(string):
            return string.title().replace(' ', '-')

        for module, module_values in metrics.items():
            for key, value in module_values.items():
                response['X-Speedbar-%s-%s' % (sanitize(module), sanitize(key))] = value

    def replace_templatetag_placeholders(self, content, metrics):
        """
        The templatetags defined in this module add placeholder values which we replace with true values here. They
        cannot just insert the values directly as not all processing may have happened by that point.
        """
        def replace_placeholder(match):
            module = match.group('module')
            metric = match.group('metric')
            return unicode(metrics[module][metric])
        return METRIC_PLACEHOLDER_RE.sub(replace_placeholder, content)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = base
from uuid import uuid4
import threading


class ThreadLocalSingleton(object):
    def __init__(self):
        if not hasattr(self.__class__, '_thread_lookup'):
            self.__class__._thread_lookup = threading.local()
        self.__class__._thread_lookup.instance = self

    def release(self):
        if getattr(self.__class_._thread_lookup, 'instance', None) is self:
            self.__class_._thread_lookup.instance = None

    @classmethod
    def instance(cls):
        if hasattr(cls, '_thread_lookup'):
            return getattr(cls._thread_lookup, 'instance', None)


class RequestTrace(ThreadLocalSingleton):
    """
    This is a container which keeps track of all module instances for a single request. For convenience they are made
    available as attributes based on their keyname
    """
    def __init__(self, modules=[]):
        super(RequestTrace, self).__init__()
        self.id = str(uuid4())
        self.modules = dict((m.key, m) for m in modules)
        self.__dict__.update(self.modules)
        self.persist_details = False
        self.persist_log = False

class BaseModule(object):
    def get_metrics(self):
        """
        Get a dictionary of summary metrics for the module
        """
        return dict()

    def get_details(self):
        """
        Get a detailed breakdown of all information collected by the module if available
        """
        return None

########NEW FILE########
__FILENAME__ = cassandra
from __future__ import absolute_import

try:
    from cassandra.cluster import Session
except ImportError:
    Session = None

from .base import BaseModule, RequestTrace
from .stacktracer import trace_method


class CassandraModule(BaseModule):
    key = 'cassandra'

    def get_metrics(self):
        return RequestTrace.instance().stacktracer.get_node_metrics('CASSANDRA')

    def get_details(self):
        nodes = RequestTrace.instance().stacktracer.get_nodes('CASSANDRA')
        return [{'cql': node.label, 'time': node.duration} for node in nodes]


def init():
    if Session is None:
        return False

    # The linter thinks the methods we monkeypatch are not used
    # pylint: disable=W0612
    @trace_method(Session)
    def execute(self, query, parameters=None, *args, **kwargs):
        return ('CASSANDRA', query, {})

    return CassandraModule

########NEW FILE########
__FILENAME__ = celeryjobs
from __future__ import absolute_import

try:
    from celery.task import Task as TaskTask
except ImportError:
    TaskTask = None

from .base import BaseModule, RequestTrace
from .stacktracer import trace_method

ENTRY_TYPE = 'CELERY'

class CeleryModule(BaseModule):
    key = 'celery'

    def get_metrics(self):
        return RequestTrace.instance().stacktracer.get_node_metrics(ENTRY_TYPE)

    def get_details(self):
        nodes = RequestTrace.instance().stacktracer.get_nodes(ENTRY_TYPE)
        return [{'type': node.extra['type'], 'args': node.extra['args'], 'kwargs': node.extra['kwargs'], 'time': node.duration} for node in nodes]


def init():
    if TaskTask is None:
        return False

    @trace_method(TaskTask)
    def apply_async(self, args=None, kwargs=None, *_args, **_kwargs):
        return (ENTRY_TYPE, 'Celery: %s' % (self.__name__,), {'type': self.__name__, 'args': args, 'kwargs': kwargs})

    return CeleryModule

########NEW FILE########
__FILENAME__ = haystack
from __future__ import absolute_import

try:
    import haystack
    from haystack.exceptions import MissingDependency
except ImportError:
    haystack = None
    MissingDependency = None

from .base import BaseModule, RequestTrace
from .stacktracer import trace_method


ENTRY_TYPE='haystack'

class HaystackModule(BaseModule):
    key = 'haystack'

    def get_metrics(self):
        return RequestTrace.instance().stacktracer.get_node_metrics(ENTRY_TYPE)

    def get_details(self):
        redis_nodes = RequestTrace.instance().stacktracer.get_nodes(ENTRY_TYPE)
        return [{'query_string': node.extra['query_string'], 'kwargs': node.extra['kwargs'], 'time': node.duration} for node in redis_nodes]

def init():
    if haystack is None:
        return False

    def search(self, query_string, *args, **kwargs):
        models = kwargs.get('models', None)
        if models:
            description = '[%s] %s' % (", ".join(m.__name__ for m in models), query_string)
        else:
            description = '[no models specified] %s' % (query_string,)

        return (ENTRY_TYPE, 'Haystack: %s' % (description,), {'query_string' : query_string, 'kwargs': kwargs})

    try:
        from haystack.backends.elasticsearch_backend import ElasticsearchSearchBackend
    except MissingDependency:
        pass
    else:
        trace_method(ElasticsearchSearchBackend)(search)

    try:
        from haystack.backends.simple_backend import SimpleSearchBackend
    except MissingDependency:
        pass
    else:
        trace_method(SimpleSearchBackend)(search)

    try:
        from haystack.backends.solr_backend import SolrSearchBackend
    except MissingDependency:
        pass
    else:
        trace_method(SolrSearchBackend)(search)

    try:
        from haystack.backends.whoosh_backend import WhooshSearchBackend
    except MissingDependency:
        pass
    else:
        trace_method(WhooshSearchBackend)(search)

    return HaystackModule

########NEW FILE########
__FILENAME__ = hostinformation
import socket

from .base import BaseModule


class HostInformationModule(BaseModule):
    key = 'host'

    def get_metrics(self):
        return {'name': socket.gethostname()}


def init():
    return HostInformationModule

########NEW FILE########
__FILENAME__ = memcache
from __future__ import absolute_import
from .base import BaseModule, RequestTrace
from .stacktracer import trace_method

try:
    import memcache
except ImportError:
    memcache = None

MEMCACHE_OPERATIONS = [ 'add', 'append', 'cas', 'decr', 'delete', 'get', 'gets', 'incr', 'prepend', 'replace', 'set', ]
MEMCACHE_MULTI_OPERATIONS = [ 'get_multi', 'set_multi', 'delete_multi', ]


class MemcacheModule(BaseModule):
    key = 'memcache'

    def get_metrics(self):
        return RequestTrace.instance().stacktracer.get_node_metrics('MEMCACHE')

    def get_details(self):
        memcache_nodes = RequestTrace.instance().stacktracer.get_nodes('MEMCACHE')
        return [{'operation': node.extra['operation'], 'key': node.extra['key'], 'time': node.duration} for node in memcache_nodes]


# The linter thinks the methods we monkeypatch are not used
# pylint: disable=W0612
def intercept_memcache_operation(operation):
    @trace_method(memcache.Client, operation)
    def info(self, *args, **kwargs):
        return ('MEMCACHE', 'Memcache: %s (%s)' % (operation, args[0]), {'operation': operation, 'key': args[0]})


def intercept_memcache_multi_operation(operation):
    @trace_method(memcache.Client, operation)
    def info(self, *args, **kwargs):
        return ('MEMCACHE', 'Memcache: %s' % (operation,), {'operation': operation, 'key': ''})


def init():
    if memcache is None:
        return False

    for operation in MEMCACHE_OPERATIONS:
        intercept_memcache_operation(operation)

    for operation in MEMCACHE_MULTI_OPERATIONS:
        intercept_memcache_multi_operation(operation)

    return MemcacheModule

########NEW FILE########
__FILENAME__ = monkey_patching
# This package has missing __init__.py files, so pylint can't see it
# pylint: disable=F0401
from peak.util.proxies import ObjectProxy

# The linter is dumb
# pylint: disable=E1001,E1002

class ExtendableObjectProxy(ObjectProxy):
    def __getattribute__(self, attr, oga=object.__getattribute__):
        if attr=='__subject__' or attr.startswith('__eop'):
            return oga(self, attr)
        subject = oga(self,'__subject__')
        return getattr(subject,attr)

    def __setattr__(self,attr,val, osa=object.__setattr__):
        if attr=='__subject__' or attr.startswith('__eop'):
            osa(self,attr,val)
        else:
            setattr(self.__subject__,attr,val)


class CallableProxy(ExtendableObjectProxy):
    __slots__ = ('__eop_wrapper__')
    def __init__(self, wrapped, wrapper):
        super(CallableProxy, self).__init__(wrapped)
        self.__eop_wrapper__ = wrapper

    def __call__(self, *args, **kwargs):
        return self.__eop_wrapper__(self.__subject__, *args, **kwargs)


class BoundMethodProxy(ExtendableObjectProxy):
    __slots__ = ('__eop_wrapper__', '__eop_instance__')
    def __init__(self, wrapped, instance, wrapper):
        super(BoundMethodProxy, self).__init__(wrapped)
        self.__eop_instance__ = instance
        self.__eop_wrapper__ = wrapper

    def __call__(self, *args, **kwargs):
        return self.__eop_wrapper__(self.__subject__, self.__eop_instance__, *args, **kwargs)


class UnboundMethodProxy(CallableProxy):
    __slots__ = ('__eop_wrapper__')

    def __get__(self, instance, owner):
        return BoundMethodProxy(self.__subject__.__get__(instance, owner), instance or owner, self.__eop_wrapper__)


def monkeypatch_method(cls, method_name=None):
    def decorator(func):
        method_to_patch = method_name or func.__name__
        original = cls.__dict__[method_to_patch]
        replacement = UnboundMethodProxy(original, func)
        type.__setattr__(cls, method_to_patch, replacement) # Avoid any overrides
        return func
    return decorator



########NEW FILE########
__FILENAME__ = pagetimer
from __future__ import absolute_import
from .base import BaseModule

import time

class PageTimerModule(BaseModule):
    key = 'overall'

    def __init__(self):
        super(PageTimerModule, self).__init__()
        self._start_time = time.time()

    def get_metrics(self):
        render_time = int((time.time() - self._start_time) * 1000)
        return { 'time' : render_time }


def init():
    return PageTimerModule

########NEW FILE########
__FILENAME__ = redis
from __future__ import absolute_import
from .base import BaseModule, RequestTrace
from .stacktracer import trace_method

try:
    from redis import StrictRedis
except ImportError:
    StrictRedis = None

class RedisModule(BaseModule):
    key = 'redis'

    def get_metrics(self):
        return RequestTrace.instance().stacktracer.get_node_metrics('REDIS')

    def get_details(self):
        redis_nodes = RequestTrace.instance().stacktracer.get_nodes('REDIS')
        return [{'operation': node.extra['operation'], 'key': node.extra['key'], 'time': node.duration} for node in redis_nodes]

def init():
    if StrictRedis is None:
        return False

    # The linter thinks the methods we monkeypatch are not used
    # pylint: disable=W0612
    @trace_method(StrictRedis)
    def execute_command(self, *args, **kwargs):
        if len(args) >= 2:
            action = 'Redis: %s (%s)' % args[:2]
            key = args[1]
        else:
            action = 'Redis: %s' % args[:1]
            key = ''
        return ('REDIS', action, {'operation': args[0], 'key': key})

    return RedisModule

########NEW FILE########
__FILENAME__ = requeststages
from __future__ import absolute_import

from django.core import urlresolvers
from django.core.handlers.base import BaseHandler
from django.core.handlers.wsgi import WSGIHandler

from .base import RequestTrace
from .monkey_patching import monkeypatch_method
from .stacktracer import trace_function

import traceback


def patch_function_list(functions, action_type, format_string):
    for i, func in enumerate(functions):
        if hasattr(func, 'im_class'):
            middleware_name = func.im_class.__name__
        else:
            middleware_name = func.__name__
        info = (action_type, format_string % (middleware_name,), {})
        functions[i] = trace_function(func, info)


def wrap_middleware_with_tracers(request_handler):
    patch_function_list(request_handler._request_middleware, 'MIDDLEWARE_REQUEST', 'Middleware: %s (request)')
    patch_function_list(request_handler._view_middleware, 'MIDDLEWARE_VIEW', 'Middleware: %s (view)')
    patch_function_list(request_handler._template_response_middleware, 'MIDDLEWARE_TEMPLATE_RESPONSE', 'Middleware: %s (template response)')
    patch_function_list(request_handler._response_middleware, 'MIDDLEWARE_RESPONSE', 'Middleware: %s (response)')
    patch_function_list(request_handler._exception_middleware, 'MIDDLEWARE_EXCEPTION', 'Middleware: %s (exeption)')


# The linter thinks the methods we monkeypatch are not used
# pylint: disable=W0612
middleware_patched = False
def intercept_middleware():
    @monkeypatch_method(WSGIHandler)
    def __call__(original, self, *args, **kwargs):
        # The middleware cache may have been built before we have a chance to monkey patch
        # it, so do so here
        global middleware_patched
        if not middleware_patched and self._request_middleware is not None:
            self.initLock.acquire()
            try:
                if not middleware_patched:
                    wrap_middleware_with_tracers(self)
                    middleware_patched = True
            finally:
                self.initLock.release()
        return original(*args, **kwargs)

    @monkeypatch_method(BaseHandler)
    def load_middleware(original, self, *args, **kwargs):
        global middleware_patched
        original(*args, **kwargs)
        wrap_middleware_with_tracers(self)
        middleware_patched = True


def intercept_resolver_and_view():
    # The only way we can really wrap the view method is by replacing the implementation
    # of RegexURLResolver.resolve. It would be nice if django had more configurability here, but it does not.
    # However, we only want to replace it when invoked directly from the request handling stack, so we
    # inspect the callstack in __new__ and return either a normal object, or an instance of our proxying
    # class.
    real_resolver_cls = urlresolvers.RegexURLResolver
    class ProxyRegexURLResolverMetaClass(urlresolvers.RegexURLResolver.__class__):
        def __instancecheck__(self, instance):
            # Some places in django do a type check against RegexURLResolver and behave differently based on the result, so we have to
            # make sure the replacement class we plug in accepts instances of both the default and replaced types.
            return isinstance(instance, real_resolver_cls) or super(ProxyRegexURLResolverMetaClass, self).__instancecheck__(instance)
    class ProxyRegexURLResolver(object):
        __metaclass__ = ProxyRegexURLResolverMetaClass
        def __new__(cls, *args, **kwargs):
            real_object = real_resolver_cls(*args, **kwargs)
            stack = traceback.extract_stack()
            if stack[-2][2] == 'get_response':
                obj = super(ProxyRegexURLResolver, cls).__new__(cls)
                obj.other = real_object
                return obj
            else:
                return real_object
        def __getattr__(self, attr):
            return getattr(self.other, attr)
        def resolve(self, path):
            request_trace = RequestTrace.instance()
            if request_trace:
                request_trace.stacktracer.push_stack('RESOLV', 'Resolving: ' + path)
            try:
                callbacks = self.other.resolve(path)
            finally:
                if request_trace:
                    request_trace.stacktracer.pop_stack()
            # Replace the callback function with a traced copy so we can time how long the view takes.
            callbacks.func = trace_function(callbacks.func, ('VIEW', 'View: ' + callbacks.view_name, {}))
            return callbacks
    urlresolvers.RegexURLResolver = ProxyRegexURLResolver


def init():
    intercept_middleware()
    intercept_resolver_and_view()

########NEW FILE########
__FILENAME__ = sql
from __future__ import absolute_import

from django.db.backends import BaseDatabaseWrapper
from django.db.backends.util import CursorWrapper
from .base import BaseModule, RequestTrace
from .monkey_patching import monkeypatch_method


class SqlModule(BaseModule):
    key = 'sql'

    def __init__(self):
        super(SqlModule, self).__init__()
        self.queries = []

    def get_metrics(self):
        return RequestTrace.instance().stacktracer.get_node_metrics('SQL')

    def get_details(self):
        sql_nodes = RequestTrace.instance().stacktracer.get_nodes('SQL')
        return [{'sql': node.label, 'time': int(node.duration*1000)} for node in sql_nodes]


class _DetailedTracingCursorWrapper(CursorWrapper):
    def execute(self, sql, params=()):
        request_trace = RequestTrace.instance()
        if request_trace:
            stack_entry = request_trace.stacktracer.push_stack('SQL', sql)
        try:
            return self.cursor.execute(sql, params)
        finally:
            if request_trace:
                request_trace.stacktracer.pop_stack()
                sql = self.db.ops.last_executed_query(self.cursor, sql, params)
                stack_entry.label = sql

    def executemany(self, sql, param_list):
        request_trace = RequestTrace.instance()
        if request_trace:
            request_trace.stacktracer.push_stack('SQL', sql)
        try:
            return self.cursor.executemany(sql, param_list)
        finally:
            if request_trace:
                request_trace.stacktracer.pop_stack()


# The linter thinks the methods we monkeypatch are not used
# pylint: disable=W0612
def init():
    @monkeypatch_method(BaseDatabaseWrapper)
    def cursor(original, self, *args, **kwargs):
        result = original(*args, **kwargs)
        return _DetailedTracingCursorWrapper(result, self)

    return SqlModule

########NEW FILE########
__FILENAME__ = stacktracer
from __future__ import absolute_import

from collections import defaultdict

from .base import BaseModule, RequestTrace
from .monkey_patching import monkeypatch_method, CallableProxy

import time

class StackEntry(object):
    def __init__(self, id_generator, entry_map, entry_type, label, extra=None):
        self.id_generator = id_generator
        self.entry_map = entry_map
        self.entry_id = id_generator()
        self.entry_type = entry_type
        self.label = label
        self.extra = extra
        self.start = time.time()
        self.children = []
        self.entry_map[entry_type].append(self)

    def mark_end(self):
        self.end = time.time()

    def add_child(self, entry_type, label, extra=None):
        child = StackEntry(self.id_generator, self.entry_map, entry_type, label, extra)
        self.children.append(child)
        return child

    @property
    def duration(self):
        if self.end:
            return self.end - self.start
        return 0

    def to_dict(self):
        return {
            'id': str(self.entry_id),
            'range': {
                'start': round(self.start * 1000, 1),
                'end': round(self.end * 1000, 1),
                'duration': round(self.duration * 1000, 1),
            },
            'operation' : {
                'type': self.entry_type,
                'label': self.label,
            },
            'children': [child.to_dict() for child in self.children],
        }


class StackTracer(BaseModule):
    """
    This class maintains a call tree, with a pointer to the current stack
    entry so that new frames can be added at any time without further context
    by the various monkey patching functions.

    It can provide all entries corresponding to operations of particular types, and
    also build a valid HAR file out of the entire call tree for use with SpeedTracer
    """
    key = 'stacktracer'

    def __init__(self):
        super(StackTracer, self).__init__()
        self.root = None
        self.stack = []
        self.stack_id = 0
        self.entry_map = defaultdict(list)

    def push_stack(self, entry_type, label, extra=None):
        if len(self.stack):
            entry = self.stack[-1].add_child(entry_type, label, extra)
        else:
            entry = self.root = StackEntry(self._get_next_id, self.entry_map, entry_type, label, extra)
        self.stack.append(entry)
        return entry

    def pop_stack(self):
        self.stack[-1].mark_end()
        self.stack.pop()

    def get_metrics(self):
        return {}

    def get_node_metrics(self, node_type):
        nodes = self.get_nodes(node_type)
        return {
            'time': int(sum(x.duration for x in nodes)*1000),
            'count': len(nodes),
        }

    def get_nodes(self, node_type):
        return self.entry_map[node_type]

    def speedtracer_log(self):
        entries_as_dict = self.root.to_dict()
        return {
            'trace': {
                'id': str(self.stack_id),
                'application': 'Speedbar',
                'date': time.time(),
                'range': entries_as_dict['range'],
                'frameStack': entries_as_dict,
            }
        }

    def _get_next_id(self):
        self.stack_id += 1
        return self.stack_id


# The linter thinks the methods we monkeypatch are not used
# pylint: disable=W0612
def trace_method(cls, method_name=None):
    def decorator(info_func):
        method_to_patch = method_name or info_func.__name__
        @monkeypatch_method(cls, method_to_patch)
        def tracing_method(original, self, *args, **kwargs):
            request_trace = RequestTrace.instance()
            if request_trace:
                entry_type, label, extra = info_func(self, *args, **kwargs)
                request_trace.stacktracer.push_stack(entry_type, label, extra=extra)
            try:
                return original(*args, **kwargs)
            finally:
                if request_trace:
                    request_trace.stacktracer.pop_stack()
        return tracing_method
    return decorator


def trace_function(func, info):
    try:
        def tracing_function(original, *args, **kwargs):
            request_trace = RequestTrace.instance()
            if request_trace:
                if callable(info):
                    entry_type, label, extra = info(*args, **kwargs)
                else:
                    entry_type, label, extra = info
                request_trace.stacktracer.push_stack(entry_type, label, extra)
            try:
                return original(*args, **kwargs)
            finally:
                if request_trace:
                    request_trace.stacktracer.pop_stack()
        return CallableProxy(func, tracing_function)
    except Exception:
        # If we can't wrap for any reason, just return the original
        return func


def init():
    return StackTracer

########NEW FILE########
__FILENAME__ = templates
from __future__ import absolute_import

from django.template import defaulttags
from django.template.base import add_to_builtins, Library, Template
from django.template.response import TemplateResponse
from django.template.loader_tags import BlockNode

from .stacktracer import trace_method, trace_function

register = Library()


class DecoratingParserProxy(object):
    """
    Mocks out the django template parser, passing templatetags through but
    first wrapping them to include performance data
    """
    def __init__(self, parser):
        self.parser = parser

    def add_library(self, library):
        wrapped_library = Library()
        wrapped_library.filters = library.filters
        for name, tag_compiler in library.tags.items():
            wrapped_library.tags[name] = self.wrap_compile_function(name, tag_compiler)
        self.parser.add_library(wrapped_library)

    def wrap_compile_function(self, name, tag_compiler):
        def compile(*args, **kwargs):
            node = tag_compiler(*args, **kwargs)
            node.render = trace_function(node.render, ('TEMPLATE_TAG', 'Render tag: ' + name, {}))
            return node
        return compile


@register.tag
def load(parser, token):
    decorating_parser = DecoratingParserProxy(parser)
    return defaulttags.load(decorating_parser, token)


# The linter thinks the methods we monkeypatch are not used
# pylint: disable=W0612
def init():
    # Our eventual aim is to patch the render() method on the Node objects
    # corresponding to custom template tags. However we have to jump through
    # a number of hoops in order to get access to the object.
    #
    # 1. Add ourselves to the set of built in template tags
    #    This allows us to replace the 'load' template tag which controls
    #    the loading of custom template tags
    # 2. Delegate to default load with replaced parser
    #    We provide our own parser class so we can catch and intercept
    #    calls to add_library.
    # 3. add_library receives a library of template tags
    #    It iterates through each template tag, wrapping its compile function
    # 4. compile is called as part of compiling the template
    #    Our wrapper is called instead of the original templatetag compile
    #    function. We delegate to the original function, but then modify
    #    the resulting object by wrapping its render() function. This
    #    render() function is what ends up being timed and appearing in the
    #    tree.
    add_to_builtins('speedbar.modules.templates')

    @trace_method(Template)
    def __init__(self, *args, **kwargs):
        name = args[2] if len(args) >= 3 else '<Unknown Template>'
        return ('TEMPLATE_COMPILE', 'Compile template: ' + name, {})

    @trace_method(Template)
    def render(self, *args, **kwargs):
        return ('TEMPLATE_RENDER', 'Render template: ' + self.name, {})

    @trace_method(BlockNode)
    def render(self, *args, **kwargs):
        return ('BLOCK_RENDER', 'Render block: ' + self.name, {})

    @trace_method(TemplateResponse)
    def resolve_context(self, *args, **kwargs):
        return ('TEMPLATE_CONTEXT', 'Resolve context', {})

########NEW FILE########
__FILENAME__ = signals
from django.core.cache import cache
from django.dispatch import Signal
from speedbar.utils import DETAILS_PREFIX, TRACE_PREFIX, loaded_modules
from speedbar.modules.base import RequestTrace

DETAILS_CACHE_TIME = 60 * 30  # 30 minutes


request_trace_complete = Signal(providing_args=['metrics', 'request', 'response'])


def setup_request_tracing(sender, **kwargs):
    RequestTrace(module() for module in loaded_modules)
    RequestTrace.instance().stacktracer.push_stack('HTTP', '')


def store_request_trace(sender, **kwargs):
    request_trace = RequestTrace.instance()
    if not request_trace:
        return

    request_trace.stacktracer.pop_stack()

    # Calculate values before doing any cache writes, so the cache writes don't affect the results
    if request_trace.persist_details:
        details_tuples = tuple(
            (key, module.get_details()) for key, module in request_trace.modules.items()
        )
        all_details = dict(details for details in details_tuples if details[1] is not None)
    if request_trace.persist_log:
        speedtracer_log = request_trace.stacktracer.speedtracer_log()
    metrics = dict((key, module.get_metrics()) for key, module in request_trace.modules.items())

    if request_trace.persist_details:
        cache.set(DETAILS_PREFIX + request_trace.id, all_details, DETAILS_CACHE_TIME)
    if request_trace.persist_log:
        cache.set(TRACE_PREFIX + request_trace.id, speedtracer_log, DETAILS_CACHE_TIME)

    request_trace_complete.send(
        sender,
        metrics=metrics,
        request=getattr(request_trace, 'request', None),
        response=getattr(request_trace, 'response', None)
    )

########NEW FILE########
__FILENAME__ = speedbar
from __future__ import absolute_import

from django import template
register = template.Library()

@register.simple_tag
def metric(module, metric):
    """
    Display a placeholder that the middleware converts to a particular summary metric
    """
    return '<span data-module="%s" data-metric="%s"></span>' % (module, metric)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *

urlpatterns = patterns('speedbar.views',
    url(r'^panel/(?P<trace_id>[a-zA-Z0-9_-]+)/$', 'panel', name='speedbar_panel'),
    url(r'^trace/(?P<trace_id>[a-zA-Z0-9_-]+)/$', 'trace', name='speedbar_trace'),
    url(r'^details-for-this-request/$', 'noop', name='speedbar_details_for_this_request'),
)

########NEW FILE########
__FILENAME__ = utils
from django.utils.importlib import import_module
from django.conf import settings

DETAILS_PREFIX='speedbar:details:'
TRACE_PREFIX='speedbar:trace:'

SPEEDBAR_MODULES = [
    'speedbar.modules.stacktracer', # Most other modules depend on this one
    'speedbar.modules.pagetimer',
    'speedbar.modules.hostinformation',
    'speedbar.modules.sql',
    'speedbar.modules.celeryjobs',
    'speedbar.modules.requeststages',
    'speedbar.modules.templates',
    'speedbar.modules.redis',
    'speedbar.modules.memcache',
    'speedbar.modules.haystack',
    'speedbar.modules.cassandra',
]

# A module comprises of two parts, both of which are optional. It may have an init() function which is called once
# on server startup, and it may have a class called Module which is instantiated once per request.

loaded_modules = []

modules_initialised = False
def init_modules():
    """
    Run the init function for all modules which have one
    """
    global modules_initialised
    if modules_initialised:
        return
    modules_initialised = True

    for module_name in getattr(settings, 'SPEEDBAR_MODULES', SPEEDBAR_MODULES):
        python_module = import_module(module_name)
        speedbar_module = python_module.init()
        if speedbar_module:
            loaded_modules.append(speedbar_module)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.core.cache import cache
from django.contrib.admin.views.decorators import staff_member_required
from speedbar.utils import DETAILS_PREFIX, TRACE_PREFIX

import json

@staff_member_required
def panel(request, trace_id):
    details = cache.get(DETAILS_PREFIX + trace_id)
    if details:
        details_json = json.dumps(details, skipkeys=True, default=repr, indent=2) # Cannot use decorator as need default=repr
        return HttpResponse(content=details_json, mimetype='text/javascript; charset=utf-8')
    return HttpResponse(status=404)

@staff_member_required
def trace(request, trace_id):
    trace = cache.get(TRACE_PREFIX + trace_id)
    if trace:
        return HttpResponse(json.dumps(trace))
    return HttpResponse(status=404)


def noop():
    pass

########NEW FILE########
