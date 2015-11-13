__FILENAME__ = handlers
from django.core.handlers.wsgi import WSGIHandler

from devserver.middleware import DevServerMiddleware


class DevServerHandler(WSGIHandler):
    def load_middleware(self):
        super(DevServerHandler, self).load_middleware()

        i = DevServerMiddleware()

        # TODO: verify this order is fine
        self._request_middleware.append(i.process_request)
        self._view_middleware.append(i.process_view)
        self._response_middleware.append(i.process_response)
        self._exception_middleware.append(i.process_exception)

########NEW FILE########
__FILENAME__ = logger
import logging
import sys
import re
import datetime

from django.utils.encoding import smart_str
from django.core.management.color import color_style
from django.utils import termcolors


_bash_colors = re.compile(r'\x1b\[[^m]*m')


def strip_bash_colors(string):
    return _bash_colors.sub('', string)


class GenericLogger(object):
    def __init__(self, module):
        self.module = module
        self.style = color_style()

    def log(self, message, *args, **kwargs):
        id = kwargs.pop('id', None)
        duration = kwargs.pop('duration', None)
        level = kwargs.pop('level', logging.INFO)

        tpl_bits = []
        if id:
            tpl_bits.append(self.style.SQL_FIELD('[%s/%s]' % (self.module.logger_name, id)))
        else:
            tpl_bits.append(self.style.SQL_FIELD('[%s]' % self.module.logger_name))
        if duration:
            tpl_bits.append(self.style.SQL_KEYWORD('(%dms)' % duration))

        if args:
            message = message % args

        message = smart_str(message)

        if level == logging.ERROR:
            message = self.style.ERROR(message)
        elif level == logging.WARN:
            message = self.style.NOTICE(message)
        else:
            try:
                HTTP_INFO = self.style.HTTP_INFO
            except:
                HTTP_INFO = termcolors.make_style(fg='red')
            message = HTTP_INFO(message)

        tpl = ' '.join(tpl_bits) % dict(
            id=id,
            module=self.module.logger_name,
            asctime=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )

        indent = ' ' * (len(strip_bash_colors(tpl)) + 1)

        new_message = []
        first = True
        for line in message.split('\n'):
            if first:
                new_message.append(line)
            else:
                new_message.append('%s%s' % (indent, line))
            first = False

        message = '%s %s' % (tpl, '\n'.join(new_message))

        sys.stdout.write('    ' + message + '\n')

    warn = lambda x, *a, **k: x.log(level=logging.WARN, *a, **k)
    info = lambda x, *a, **k: x.log(level=logging.INFO, *a, **k)
    debug = lambda x, *a, **k: x.log(level=logging.DEBUG, *a, **k)
    error = lambda x, *a, **k: x.log(level=logging.ERROR, *a, **k)
    critical = lambda x, *a, **k: x.log(level=logging.CRITICAL, *a, **k)
    fatal = lambda x, *a, **k: x.log(level=logging.FATAL, *a, **k)

########NEW FILE########
__FILENAME__ = runserver
from django.conf import settings
from django.core.management.commands.runserver import Command as BaseCommand
from django.core.management.base import CommandError, handle_default_options
from django.core.servers.basehttp import WSGIServer
from django.core.handlers.wsgi import WSGIHandler

import os
import sys
import imp
import errno
import socket
import SocketServer
from optparse import make_option

from devserver.handlers import DevServerHandler
from devserver.utils.http import SlimWSGIRequestHandler

try:
    from django.core.servers.basehttp import (WSGIServerException as
                                              wsgi_server_exc_cls)
except ImportError:  # Django 1.6
    wsgi_server_exc_cls = socket.error


STATICFILES_APPS = ('django.contrib.staticfiles', 'staticfiles')


def null_technical_500_response(request, exc_type, exc_value, tb):
    raise exc_type, exc_value, tb


def run(addr, port, wsgi_handler, mixin=None, ipv6=False):
    if mixin:
        class new(mixin, WSGIServer):
            def __init__(self, *args, **kwargs):
                WSGIServer.__init__(self, *args, **kwargs)
    else:
        new = WSGIServer
    server_address = (addr, port)
    new.request_queue_size = 10
    httpd = new(server_address, SlimWSGIRequestHandler, ipv6=ipv6)
    httpd.set_app(wsgi_handler)
    httpd.serve_forever()


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--werkzeug', action='store_true', dest='use_werkzeug', default=False,
            help='Tells Django to use the Werkzeug interactive debugger.'),
        make_option(
            '--forked', action='store_true', dest='use_forked', default=False,
            help='Use forking instead of threading for multiple web requests.'),
        make_option(
            '--dozer', action='store_true', dest='use_dozer', default=False,
            help='Enable the Dozer memory debugging middleware.'),
        make_option(
            '--wsgi-app', dest='wsgi_app', default=None,
            help='Load the specified WSGI app as the server endpoint.'),
    )
    if any(map(lambda app: app in settings.INSTALLED_APPS, STATICFILES_APPS)):
        option_list += make_option(
            '--nostatic', dest='use_static_files', action='store_false', default=True,
            help='Tells Django to NOT automatically serve static files at STATIC_URL.'),

    help = "Starts a lightweight Web server for development which outputs additional debug information."
    args = '[optional port number, or ipaddr:port]'

    # Validation is called explicitly each time the server is reloaded.
    requires_model_validation = False

    def run_from_argv(self, argv):
        parser = self.create_parser(argv[0], argv[1])
        default_args = getattr(settings, 'DEVSERVER_ARGS', None)
        if default_args:
            options, args = parser.parse_args(default_args)
        else:
            options = None

        options, args = parser.parse_args(argv[2:], options)

        handle_default_options(options)
        self.execute(*args, **options.__dict__)

    def handle(self, addrport='', *args, **options):
        if args:
            raise CommandError('Usage is runserver %s' % self.args)

        if not addrport:
            addr = getattr(settings, 'DEVSERVER_DEFAULT_ADDR', '127.0.0.1')
            port = getattr(settings, 'DEVSERVER_DEFAULT_PORT', '8000')
            addrport = '%s:%s' % (addr, port)

        return super(Command, self).handle(addrport=addrport, *args, **options)

    def get_handler(self, *args, **options):
        if int(options['verbosity']) < 1:
            handler = WSGIHandler()
        else:
            handler = DevServerHandler()

        # AdminMediaHandler is removed in Django 1.5
        # Add it only when it avialable.
        try:
            from django.core.servers.basehttp import AdminMediaHandler
        except ImportError:
            pass
        else:
            handler = AdminMediaHandler(
                handler, options['admin_media_path'])

        if 'django.contrib.staticfiles' in settings.INSTALLED_APPS and options['use_static_files']:
            from django.contrib.staticfiles.handlers import StaticFilesHandler
            handler = StaticFilesHandler(handler)

        return handler

    def inner_run(self, *args, **options):
        # Flag the server as active
        from devserver import settings
        import devserver
        settings.DEVSERVER_ACTIVE = True
        settings.DEBUG = True

        from django.conf import settings
        from django.utils import translation

        shutdown_message = options.get('shutdown_message', '')
        use_werkzeug = options.get('use_werkzeug', False)
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'
        wsgi_app = options.get('wsgi_app', None)

        if use_werkzeug:
            try:
                from werkzeug import run_simple, DebuggedApplication
            except ImportError, e:
                self.stderr.write("WARNING: Unable to initialize werkzeug: %s\n" % e)
                use_werkzeug = False
            else:
                from django.views import debug
                debug.technical_500_response = null_technical_500_response

        self.stdout.write("Validating models...\n\n")
        self.validate(display_num_errors=True)
        self.stdout.write((
            "Django version %(version)s, using settings %(settings)r\n"
            "Running django-devserver %(devserver_version)s\n"
            "%(server_model)s %(server_type)s server is running at http://%(addr)s:%(port)s/\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "server_type": use_werkzeug and 'werkzeug' or 'Django',
            "server_model": options['use_forked'] and 'Forked' or 'Threaded',
            "version": self.get_version(),
            "devserver_version": devserver.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "addr": self._raw_ipv6 and '[%s]' % self.addr or self.addr,
            "port": self.port,
            "quit_command": quit_command,
        })

        # django.core.management.base forces the locale to en-us. We should
        # set it up correctly for the first request (particularly important
        # in the "--noreload" case).
        translation.activate(settings.LANGUAGE_CODE)

        app = self.get_handler(*args, **options)
        if wsgi_app:
            self.stdout.write("Using WSGI application %r\n" % wsgi_app)
            if os.path.exists(os.path.abspath(wsgi_app)):
                # load from file
                app = imp.load_source('wsgi_app', os.path.abspath(wsgi_app)).application
            else:
                try:
                    app = __import__(wsgi_app, {}, {}, ['application']).application
                except (ImportError, AttributeError):
                    raise

        if options['use_forked']:
            mixin = SocketServer.ForkingMixIn
        else:
            mixin = SocketServer.ThreadingMixIn

        middleware = getattr(settings, 'DEVSERVER_WSGI_MIDDLEWARE', [])
        for middleware in middleware:
            module, class_name = middleware.rsplit('.', 1)
            app = getattr(__import__(module, {}, {}, [class_name]), class_name)(app)

        if options['use_dozer']:
            from dozer import Dozer
            app = Dozer(app)

        try:
            if use_werkzeug:
                run_simple(
                    self.addr, int(self.port), DebuggedApplication(app, True),
                    use_reloader=False, use_debugger=True)
            else:
                run(self.addr, int(self.port), app, mixin, ipv6=options['use_ipv6'])

        except wsgi_server_exc_cls, e:
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                errno.EACCES: "You don't have permission to access that port.",
                errno.EADDRINUSE: "That port is already in use.",
                errno.EADDRNOTAVAIL: "That IP address can't be assigned-to.",
            }
            if not isinstance(e, socket.error):  # Django < 1.6
                ERRORS[13] = ERRORS.pop(errno.EACCES)
                ERRORS[98] = ERRORS.pop(errno.EADDRINUSE)
                ERRORS[99] = ERRORS.pop(errno.EADDRNOTAVAIL)

            try:
                if not isinstance(e, socket.error):  # Django < 1.6
                    error_text = ERRORS[e.args[0].args[0]]
                else:
                    error_text = ERRORS[e.errno]
            except (AttributeError, KeyError):
                error_text = str(e)
            sys.stderr.write(self.style.ERROR("Error: %s" % error_text) + '\n')
            # Need to use an OS exit because sys.exit doesn't work in a thread
            os._exit(1)

        except KeyboardInterrupt:
            if shutdown_message:
                self.stdout.write("%s\n" % shutdown_message)
            sys.exit(0)

########NEW FILE########
__FILENAME__ = middleware
from devserver.models import MODULES


class DevServerMiddleware(object):
    def should_process(self, request):
        from django.conf import settings

        if getattr(settings, 'STATIC_URL', None) and request.build_absolute_uri().startswith(request.build_absolute_uri(settings.STATIC_URL)):
            return False

        if settings.MEDIA_URL and request.build_absolute_uri().startswith(request.build_absolute_uri(settings.MEDIA_URL)):
            return False

        if getattr(settings, 'ADMIN_MEDIA_PREFIX', None) and request.path.startswith(settings.ADMIN_MEDIA_PREFIX):
            return False

        if request.path == '/favicon.ico':
            return False

        for path in getattr(settings, 'DEVSERVER_IGNORED_PREFIXES', []):
            if request.path.startswith(path):
                return False

        return True

    def process_request(self, request):
        # Set a sentinel value which process_response can use to abort when
        # another middleware app short-circuits processing:
        request._devserver_active = True

        self.process_init(request)

        if self.should_process(request):
            for mod in MODULES:
                mod.process_request(request)

    def process_response(self, request, response):
        # If this isn't set, it usually means that another middleware layer
        # has returned an HttpResponse and the following middleware won't see
        # the request. This happens most commonly with redirections - see
        # https://github.com/dcramer/django-devserver/issues/28 for details:
        if not getattr(request, "_devserver_active", False):
            return response

        if self.should_process(request):
            for mod in MODULES:
                mod.process_response(request, response)

        self.process_complete(request)

        return response

    def process_exception(self, request, exception):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_exception(request, exception)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_view(request, view_func, view_args, view_kwargs)
        #return view_func(request, *view_args, **view_kwargs)

    def process_init(self, request):
        from devserver.utils.stats import stats

        stats.reset()

        if self.should_process(request):
            for mod in MODULES:
                mod.process_init(request)

    def process_complete(self, request):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_complete(request)

########NEW FILE########
__FILENAME__ = models
from django.core import exceptions

from devserver.logger import GenericLogger


MODULES = []


def load_modules():
    global MODULES

    MODULES = []

    from devserver import settings

    for path in settings.DEVSERVER_MODULES:
        try:
            name, class_name = path.rsplit('.', 1)
        except ValueError:
            raise exceptions.ImproperlyConfigured, '%s isn\'t a devserver module' % path

        try:
            module = __import__(name, {}, {}, [''])
        except ImportError, e:
            raise exceptions.ImproperlyConfigured, 'Error importing devserver module %s: "%s"' % (name, e)

        try:
            cls = getattr(module, class_name)
        except AttributeError:
            raise exceptions.ImproperlyConfigured, 'Error importing devserver module "%s" does not define a "%s" class' % (name, class_name)

        try:
            instance = cls(GenericLogger(cls))
        except:
            raise  # Bubble up problem loading panel

        MODULES.append(instance)

if not MODULES:
    load_modules()

########NEW FILE########
__FILENAME__ = ajax
import json

from devserver.modules import DevServerModule
from devserver import settings


class AjaxDumpModule(DevServerModule):
    """
    Dumps the content of all AJAX responses.
    """

    logger_name = 'ajax'

    def process_response(self, request, response):
        if request.is_ajax():
            # Let's do a quick test to see what kind of response we have
            if len(response.content) < settings.DEVSERVER_AJAX_CONTENT_LENGTH:
                content = response.content
                if settings.DEVSERVER_AJAX_PRETTY_PRINT:
                    content = json.dumps(json.loads(content), indent=4)
                self.logger.info(content)

########NEW FILE########
__FILENAME__ = cache
from django.core.cache import cache

from devserver.modules import DevServerModule


class CacheSummaryModule(DevServerModule):
    """
    Outputs a summary of cache events once a response is ready.
    """
    real_time = False

    logger_name = 'cache'

    attrs_to_track = ['set', 'get', 'delete', 'add', 'get_many']

    def process_init(self, request):
        from devserver.utils.stats import track

        # save our current attributes
        self.old = dict((k, getattr(cache, k)) for k in self.attrs_to_track)

        for k in self.attrs_to_track:
            setattr(cache, k, track(getattr(cache, k), 'cache', self.logger if self.real_time else None))

    def process_complete(self, request):
        from devserver.utils.stats import stats

        calls = stats.get_total_calls('cache')
        hits = stats.get_total_hits('cache')
        misses = stats.get_total_misses_for_function('cache', cache.get) + stats.get_total_misses_for_function('cache', cache.get_many)

        if calls and (hits or misses):
            ratio = int(hits / float(misses + hits) * 100)
        else:
            ratio = 100

        if not self.real_time:
            self.logger.info('%(calls)s calls made with a %(ratio)d%% hit percentage (%(misses)s misses)' % dict(
                calls=calls,
                ratio=ratio,
                hits=hits,
                misses=misses,
            ), duration=stats.get_total_time('cache'))

        # set our attributes back to their defaults
        for k, v in self.old.iteritems():
            setattr(cache, k, v)


class CacheRealTimeModule(CacheSummaryModule):
    real_time = True

########NEW FILE########
__FILENAME__ = profile
from devserver.modules import DevServerModule
from devserver.utils.time import ms_from_timedelta
from devserver.settings import DEVSERVER_AUTO_PROFILE

from datetime import datetime

import functools
import gc


class ProfileSummaryModule(DevServerModule):
    """
    Outputs a summary of cache events once a response is ready.
    """

    logger_name = 'profile'

    def process_init(self, request):
        self.start = datetime.now()

    def process_complete(self, request):
        duration = datetime.now() - self.start

        self.logger.info('Total time to render was %.2fs', ms_from_timedelta(duration) / 1000)


class LeftOversModule(DevServerModule):
    """
    Outputs a summary of events the garbage collector couldn't handle.
    """
    # TODO: Not even sure this is correct, but the its a general idea

    logger_name = 'profile'

    def process_init(self, request):
        gc.enable()
        gc.set_debug(gc.DEBUG_SAVEALL)

    def process_complete(self, request):
        gc.collect()
        self.logger.info('%s objects left in garbage', len(gc.garbage))

from django.template.defaultfilters import filesizeformat

try:
    from guppy import hpy
except ImportError:
    import warnings

    class MemoryUseModule(DevServerModule):
        def __new__(cls, *args, **kwargs):
            warnings.warn('MemoryUseModule requires guppy to be installed.')
            return super(MemoryUseModule, cls).__new__(cls)
else:
    class MemoryUseModule(DevServerModule):
        """
        Outputs a summary of memory usage of the course of a request.
        """
        logger_name = 'profile'

        def __init__(self, request):
            super(MemoryUseModule, self).__init__(request)
            self.hpy = hpy()
            self.oldh = self.hpy.heap()
            self.logger.info('heap size is %s', filesizeformat(self.oldh.size))

        def process_complete(self, request):
            newh = self.hpy.heap()
            alloch = newh - self.oldh
            dealloch = self.oldh - newh
            self.oldh = newh
            self.logger.info('%s allocated, %s deallocated, heap size is %s', *map(filesizeformat, [alloch.size, dealloch.size, newh.size]))

try:
    from line_profiler import LineProfiler
except ImportError:
    import warnings

    class LineProfilerModule(DevServerModule):

        def __new__(cls, *args, **kwargs):
            warnings.warn('LineProfilerModule requires line_profiler to be installed.')
            return super(LineProfilerModule, cls).__new__(cls)

        class devserver_profile(object):
            def __init__(self, follow=[]):
                pass

            def __call__(self, func):
                return func
else:
    class LineProfilerModule(DevServerModule):
        """
        Outputs a Line by Line profile of any @devserver_profile'd functions that were run
        """
        logger_name = 'profile'

        def process_view(self, request, view_func, view_args, view_kwargs):
            request.devserver_profiler = LineProfiler()
            request.devserver_profiler_run = False
            if (DEVSERVER_AUTO_PROFILE):
                _unwrap_closure_and_profile(request.devserver_profiler, view_func)
                request.devserver_profiler.enable_by_count()

        def process_complete(self, request):
            if hasattr(request, 'devserver_profiler_run') and (DEVSERVER_AUTO_PROFILE or request.devserver_profiler_run):
                from cStringIO import StringIO
                out = StringIO()
                if (DEVSERVER_AUTO_PROFILE):
                    request.devserver_profiler.disable_by_count()
                request.devserver_profiler.print_stats(stream=out)
                self.logger.info(out.getvalue())

    def _unwrap_closure_and_profile(profiler, func):
        if not hasattr(func, 'func_code'):
            return
        profiler.add_function(func)
        if func.func_closure:
            for cell in func.func_closure:
                if hasattr(cell.cell_contents, 'func_code'):
                    _unwrap_closure_and_profile(profiler, cell.cell_contents)

    class devserver_profile(object):
        def __init__(self, follow=[]):
            self.follow = follow

        def __call__(self, func):
            def profiled_func(*args, **kwargs):
                request = args[0]
                if hasattr(request, 'request'):
                    # We're decorating a Django class-based-view and the first argument is actually self:
                    request = args[1]

                try:
                    request.devserver_profiler.add_function(func)
                    request.devserver_profiler_run = True
                    for f in self.follow:
                        request.devserver_profiler.add_function(f)
                    request.devserver_profiler.enable_by_count()
                    return func(*args, **kwargs)
                finally:
                    request.devserver_profiler.disable_by_count()

            return functools.wraps(func)(profiled_func)

########NEW FILE########
__FILENAME__ = request
import urllib

from devserver.modules import DevServerModule


class SessionInfoModule(DevServerModule):
    """
    Displays information about the currently authenticated user and session.
    """

    logger_name = 'session'

    def process_request(self, request):
        self.has_session = bool(getattr(request, 'session', False))
        if self.has_session is not None:
            self._save = request.session.save
            self.session = request.session
            request.session.save = self.handle_session_save

    def process_response(self, request, response):
        if getattr(self, 'has_session', False):
            if getattr(request, 'user', None) and request.user.is_authenticated():
                user = '%s (id:%s)' % (request.user.username, request.user.pk)
            else:
                user = '(Anonymous)'
            self.logger.info('Session %s authenticated by %s', request.session.session_key, user)
            request.session.save = self._save
            self._save = None
            self.session = None
            self.has_session = False

    def handle_session_save(self, *args, **kwargs):
        self._save(*args, **kwargs)
        self.logger.info('Session %s has been saved.', self.session.session_key)


class RequestDumpModule(DevServerModule):
    """
    Dumps the request headers and variables.
    """

    logger_name = 'request'

    def process_request(self, request):
        req = self.logger.style.SQL_KEYWORD('%s %s %s\n' % (request.method, '?'.join((request.META['PATH_INFO'], request.META['QUERY_STRING'])), request.META['SERVER_PROTOCOL']))
        for var, val in request.META.items():
            if var.startswith('HTTP_'):
                var = var[5:].replace('_', '-').title()
                req += '%s: %s\n' % (self.logger.style.SQL_KEYWORD(var), val)
        if request.META['CONTENT_LENGTH']:
            req += '%s: %s\n' % (self.logger.style.SQL_KEYWORD('Content-Length'), request.META['CONTENT_LENGTH'])
        if request.POST:
            req += '\n%s\n' % self.logger.style.HTTP_INFO(urllib.urlencode(dict((k, v.encode('utf8')) for k, v in request.POST.items())))
        if request.FILES:
            req += '\n%s\n' % self.logger.style.HTTP_NOT_MODIFIED(urllib.urlencode(request.FILES))
        self.logger.info('Full request:\n%s', req)

class ResponseDumpModule(DevServerModule):
    """
    Dumps the request headers and variables.
    """

    logger_name = 'response'

    def process_response(self, request, response):
        res = self.logger.style.SQL_FIELD('Status code: %s\n' % response.status_code)
        res += '\n'.join(['%s: %s' % (self.logger.style.SQL_FIELD(k), v)
            for k, v in response._headers.values()])
        self.logger.info('Full response:\n%s', res)

########NEW FILE########
__FILENAME__ = sql
"""
Based on initial work from django-debug-toolbar
"""
import re

from datetime import datetime

try:
    from django.db import connections
except ImportError:
    # Django version < 1.2
    from django.db import connection
    connections = {'default': connection}

from django.db.backends import util
from django.conf import settings as django_settings
#from django.template import Node

from devserver.modules import DevServerModule
#from devserver.utils.stack import tidy_stacktrace, get_template_info
from devserver.utils.time import ms_from_timedelta
from devserver import settings

try:
    import sqlparse
except ImportError:
    class sqlparse:
        @staticmethod
        def format(text, *args, **kwargs):
            return text


_sql_fields_re = re.compile(r'SELECT .*? FROM')
_sql_aggregates_re = re.compile(r'SELECT .*?(COUNT|SUM|AVERAGE|MIN|MAX).*? FROM')


def truncate_sql(sql, aggregates=True):
    if not aggregates and _sql_aggregates_re.match(sql):
        return sql
    return _sql_fields_re.sub('SELECT ... FROM', sql)

# # TODO:This should be set in the toolbar loader as a default and panels should
# # get a copy of the toolbar object with access to its config dictionary
# SQL_WARNING_THRESHOLD = getattr(settings, 'DEVSERVER_CONFIG', {}) \
#                             .get('SQL_WARNING_THRESHOLD', 500)

try:
    from debug_toolbar.panels.sql import DatabaseStatTracker
    debug_toolbar = True
except ImportError:
    debug_toolbar = False
    import django
    version = float('.'.join([str(x) for x in django.VERSION[:2]]))
    if version >= 1.6:
        DatabaseStatTracker = util.CursorWrapper
    else:
        DatabaseStatTracker = util.CursorDebugWrapper


class DatabaseStatTracker(DatabaseStatTracker):
    """
    Replacement for CursorDebugWrapper which outputs information as it happens.
    """
    logger = None

    def execute(self, sql, params=()):
        formatted_sql = sql % (params if isinstance(params, dict) else tuple(params))
        if self.logger:
            message = formatted_sql
            if settings.DEVSERVER_FILTER_SQL:
                if any(filter_.search(message) for filter_ in settings.DEVSERVER_FILTER_SQL):
                    message = None
            if message is not None:
                if settings.DEVSERVER_TRUNCATE_SQL:
                    message = truncate_sql(message, aggregates=settings.DEVSERVER_TRUNCATE_AGGREGATES)
                message = sqlparse.format(message, reindent=True, keyword_case='upper')
                self.logger.debug(message)

        start = datetime.now()

        try:
            return super(DatabaseStatTracker, self).execute(sql, params)
        finally:
            stop = datetime.now()
            duration = ms_from_timedelta(stop - start)

            if self.logger and (not settings.DEVSERVER_SQL_MIN_DURATION
                    or duration > settings.DEVSERVER_SQL_MIN_DURATION):
                if self.cursor.rowcount >= 0 and message is not None:
                    self.logger.debug('Found %s matching rows', self.cursor.rowcount, duration=duration)

            if not (debug_toolbar or django_settings.DEBUG):
                self.db.queries.append({
                    'sql': formatted_sql,
                    'time': duration,
                })

    def executemany(self, sql, param_list):
        start = datetime.now()
        try:
            return super(DatabaseStatTracker, self).executemany(sql, param_list)
        finally:
            stop = datetime.now()
            duration = ms_from_timedelta(stop - start)

            if self.logger:
                message = sqlparse.format(sql, reindent=True, keyword_case='upper')

                message = 'Executed %s times\n%s' % message

                self.logger.debug(message, duration=duration)
                self.logger.debug('Found %s matching rows', self.cursor.rowcount, duration=duration, id='query')

            if not (debug_toolbar or settings.DEBUG):
                self.db.queries.append({
                    'sql': '%s times: %s' % (len(param_list), sql),
                    'time': duration,
                })


class SQLRealTimeModule(DevServerModule):
    """
    Outputs SQL queries as they happen.
    """

    logger_name = 'sql'

    def process_init(self, request):
        if not issubclass(util.CursorDebugWrapper, DatabaseStatTracker):
            self.old_cursor = util.CursorDebugWrapper
            util.CursorDebugWrapper = DatabaseStatTracker
        DatabaseStatTracker.logger = self.logger

    def process_complete(self, request):
        if issubclass(util.CursorDebugWrapper, DatabaseStatTracker):
            util.CursorDebugWrapper = self.old_cursor


class SQLSummaryModule(DevServerModule):
    """
    Outputs a summary SQL queries.
    """

    logger_name = 'sql'

    def process_complete(self, request):
        queries = [
            q for alias in connections
            for q in connections[alias].queries
        ]
        num_queries = len(queries)
        if num_queries:
            unique = set([s['sql'] for s in queries])
            self.logger.info('%(calls)s queries with %(dupes)s duplicates' % dict(
                calls=num_queries,
                dupes=num_queries - len(unique),
            ), duration=sum(float(c.get('time', 0)) for c in queries) * 1000)

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

DEVSERVER_MODULES = getattr(settings, 'DEVSERVER_MODULES', (
    'devserver.modules.sql.SQLRealTimeModule',
    # 'devserver.modules.sql.SQLSummaryModule',
    # 'devserver.modules.profile.ProfileSummaryModule',
    # 'devserver.modules.request.SessionInfoModule',
    # 'devserver.modules.profile.MemoryUseModule',
    # 'devserver.modules.profile.LeftOversModule',
    # 'devserver.modules.cache.CacheSummaryModule',
))

DEVSERVER_FILTER_SQL = getattr(settings, 'DEVSERVER_FILTER_SQL', False)
DEVSERVER_TRUNCATE_SQL = getattr(settings, 'DEVSERVER_TRUNCATE_SQL', True)

DEVSERVER_TRUNCATE_AGGREGATES = getattr(settings, 'DEVSERVER_TRUNCATE_AGGREGATES', getattr(settings, 'DEVSERVER_TRUNCATE_AGGREGATES', False))

# This variable gets set to True when we're running the devserver
DEVSERVER_ACTIVE = False

DEVSERVER_AJAX_CONTENT_LENGTH = getattr(settings, 'DEVSERVER_AJAX_CONTENT_LENGTH', 300)
DEVSERVER_AJAX_PRETTY_PRINT = getattr(settings, 'DEVSERVER_AJAX_PRETTY_PRINT', False)

# Minimum time a query must execute to be shown, value is in MS
DEVSERVER_SQL_MIN_DURATION = getattr(settings, 'DEVSERVER_SQL_MIN_DURATION', None)

DEVSERVER_AUTO_PROFILE = getattr(settings, 'DEVSERVER_AUTO_PROFILE', False)

########NEW FILE########
__FILENAME__ = testcases
import socket
import SocketServer
import threading

from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from django.core.management import call_command
from django.core.servers.basehttp import WSGIServer

from devserver.utils.http import SlimWSGIRequestHandler

try:
    from django.core.servers.basehttp import (WSGIServerException as
                                              wsgi_server_exc_cls)
except ImportError:  # Django 1.6
    wsgi_server_exc_cls = socket.error


class StoppableWSGIServer(WSGIServer):
    """WSGIServer with short timeout, so that server thread can stop this server."""

    def server_bind(self):
        """Sets timeout to 1 second."""
        WSGIServer.server_bind(self)
        self.socket.settimeout(1)

    def get_request(self):
        """Checks for timeout when getting request."""
        try:
            sock, address = self.socket.accept()
            sock.settimeout(None)
            return (sock, address)
        except socket.timeout:
            raise


class ThreadedTestServerThread(threading.Thread):
    """Thread for running a http server while tests are running."""

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self._stopevent = threading.Event()
        self.started = threading.Event()
        self.error = None
        super(ThreadedTestServerThread, self).__init__()

    def _should_loaddata(self):
        # Must do database stuff in this new thread if database in memory.
        if not hasattr(self, 'fixtures'):
            return False
        if settings.DATABASE_ENGINE != 'sqlite3':
            return False
        if settings.TEST_DATABASE_NAME and settings.TEST_DATABASE_NAME != ':memory:':
            return False
        return True

    def run(self):
        """Sets up test server and database and loops over handling http requests."""
        # AdminMediaHandler was removed in Django 1.5; use it only when available.
        handler = WSGIHandler()
        try:
            from django.core.servers.basehttp import AdminMediaHandler
            handler = AdminMediaHandler(handler)
        except ImportError:
            pass

        try:
            server_address = (self.address, self.port)

            class new(SocketServer.ThreadingMixIn, StoppableWSGIServer):
                def __init__(self, *args, **kwargs):
                    StoppableWSGIServer.__init__(self, *args, **kwargs)

            httpd = new(server_address, SlimWSGIRequestHandler)
            httpd.set_app(handler)
            self.started.set()
        except wsgi_server_exc_cls, e:
            self.error = e
            self.started.set()
            return

        if self._should_loaddata():
            # We have to use this slightly awkward syntax due to the fact
            # that we're using *args and **kwargs together.
            call_command('loaddata', *self.fixtures, **{'verbosity': 0})

        # Loop until we get a stop event.
        while not self._stopevent.isSet():
            httpd.handle_request()

    def join(self, timeout=None):
        """Stop the thread and wait for it to finish."""
        self._stopevent.set()
        threading.Thread.join(self, timeout)

########NEW FILE########
__FILENAME__ = tests
# TODO
########NEW FILE########
__FILENAME__ = http
from datetime import datetime

from django.conf import settings
from django.core.servers.basehttp import WSGIRequestHandler

try:
    from django.db import connections
except ImportError:
    # Django version < 1.2
    from django.db import connection
    connections = {'default': connection}

from devserver.utils.time import ms_from_timedelta


class SlimWSGIRequestHandler(WSGIRequestHandler):
    """
    Hides all requests that originate from either ``STATIC_URL`` or ``MEDIA_URL``
    as well as any request originating with a prefix included in
    ``DEVSERVER_IGNORED_PREFIXES``.
    """
    def handle(self, *args, **kwargs):
        self._start_request = datetime.now()
        return WSGIRequestHandler.handle(self, *args, **kwargs)

    def get_environ(self):
        env = super(SlimWSGIRequestHandler, self).get_environ()
        env['REMOTE_PORT'] = self.client_address[-1]
        return env

    def log_message(self, format, *args):
        duration = datetime.now() - self._start_request

        env = self.get_environ()

        for url in (getattr(settings, 'STATIC_URL', None), settings.MEDIA_URL):
            if not url:
                continue
            if self.path.startswith(url):
                return
            elif url.startswith('http:'):
                if ('http://%s%s' % (env['HTTP_HOST'], self.path)).startswith(url):
                    return

        for path in getattr(settings, 'DEVSERVER_IGNORED_PREFIXES', []):
            if self.path.startswith(path):
                return

        format += " (time: %.2fs; sql: %dms (%dq))"
        queries = [
            q for alias in connections
            for q in connections[alias].queries
        ]
        args = list(args) + [
            ms_from_timedelta(duration) / 1000,
            sum(float(c.get('time', 0)) for c in queries) * 1000,
            len(queries),
        ]
        return WSGIRequestHandler.log_message(self, format, *args)

########NEW FILE########
__FILENAME__ = stack
import django
import SocketServer
import os.path

from django.conf import settings
from django.views.debug import linebreak_iter

# Figure out some paths
django_path = os.path.realpath(os.path.dirname(django.__file__))
socketserver_path = os.path.realpath(os.path.dirname(SocketServer.__file__))


def tidy_stacktrace(strace):
    """
    Clean up stacktrace and remove all entries that:
    1. Are part of Django (except contrib apps)
    2. Are part of SocketServer (used by Django's dev server)
    3. Are the last entry (which is part of our stacktracing code)
    """
    trace = []
    for s in strace[:-1]:
        s_path = os.path.realpath(s[0])
        if getattr(settings, 'DEVSERVER_CONFIG', {}).get('HIDE_DJANGO_SQL', True) \
            and django_path in s_path and not 'django/contrib' in s_path:
            continue
        if socketserver_path in s_path:
            continue
        trace.append((s[0], s[1], s[2], s[3]))
    return trace


def get_template_info(source, context_lines=3):
    line = 0
    upto = 0
    source_lines = []
    before = during = after = ""

    origin, (start, end) = source
    template_source = origin.reload()

    for num, next in enumerate(linebreak_iter(template_source)):
        if start >= upto and end <= next:
            line = num
            before = template_source[upto:start]
            during = template_source[start:end]
            after = template_source[end:next]
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

########NEW FILE########
__FILENAME__ = stats
try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

from datetime import datetime

from devserver.utils.time import ms_from_timedelta


__all__ = ('track', 'stats')


class StatCollection(object):
    def __init__(self, *args, **kwargs):
        super(StatCollection, self).__init__(*args, **kwargs)
        self.reset()

    def run(self, func, key, logger, *args, **kwargs):
        """Profile a function and store its information."""

        start_time = datetime.now()
        value = func(*args, **kwargs)
        end_time = datetime.now()
        this_time = ms_from_timedelta(end_time - start_time)
        values = {
            'args': args,
            'kwargs': kwargs,
            'count': 0,
            'hits': 0,
            'time': 0.0
        }
        row = self.grouped.setdefault(key, {}).setdefault(func.__name__, values)
        row['count'] += 1
        row['time'] += this_time
        if value is not None:
            row['hits'] += 1

        self.calls.setdefault(key, []).append({
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'time': this_time,
            'hit': value is not None,
            #'stack': [s[1:] for s in inspect.stack()[2:]],
        })
        row = self.summary.setdefault(key, {'count': 0, 'time': 0.0, 'hits': 0})
        row['count'] += 1
        row['time'] += this_time
        if value is not None:
            row['hits'] += 1

        if logger:
            logger.debug('%s("%s") %s (%s)', func.__name__, args[0], 'Miss' if value is None else 'Hit', row['hits'], duration=this_time)

        return value

    def reset(self):
        """Reset the collection."""
        self.grouped = {}
        self.calls = {}
        self.summary = {}

    def get_total_time(self, key):
        return self.summary.get(key, {}).get('time', 0)

    def get_total_calls(self, key):
        return self.summary.get(key, {}).get('count', 0)

    def get_total_hits(self, key):
        return self.summary.get(key, {}).get('hits', 0)

    def get_total_misses(self, key):
        return self.get_total_calls(key) - self.get_total_hits(key)

    def get_total_hits_for_function(self, key, func):
        return self.grouped.get(key, {}).get(func.__name__, {}).get('hits', 0)

    def get_total_calls_for_function(self, key, func):
        return self.grouped.get(key, {}).get(func.__name__, {}).get('count', 0)

    def get_total_misses_for_function(self, key, func):
        return self.get_total_calls_for_function(key, func) - self.get_total_hits_for_function(key, func)

    def get_total_time_for_function(self, key, func):
        return self.grouped.get(key, {}).get(func.__name__, {}).get('time', 0)

    def get_calls(self, key):
        return self.calls.get(key, [])

stats = StatCollection()


def track(func, key, logger):
    """A decorator which handles tracking calls on a function."""
    def wrapped(*args, **kwargs):
        global stats

        return stats.run(func, key, logger, *args, **kwargs)
    wrapped.__doc__ = func.__doc__
    wrapped.__name__ = func.__name__
    return wrapped

########NEW FILE########
__FILENAME__ = time
def ms_from_timedelta(td):
    """
    Given a timedelta object, returns a float representing milliseconds
    """
    return (td.seconds * 1000) + (td.microseconds / 1000.0)

########NEW FILE########
