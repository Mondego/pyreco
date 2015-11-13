__FILENAME__ = app
import random
import urllib
import logging
from xml.sax import saxutils
from wsgiref.util import setup_testing_defaults

from firepython.demo._body import BODY, EXCLAMATIONS

LOGGER_NAME = __name__


class FirePythonDemoApp(object):
    _did_setup_logging = False

    def __init__(self, global_config=None):
        if not global_config:
            global_config = {}
        self.global_config = global_config
        self.__body__ = BODY
        self.log = logging.getLogger(LOGGER_NAME)

    def _setup_logging(self):
        if self._did_setup_logging:
            return

        self.log.setLevel(logging.DEBUG)

        for handler in self.log.root.handlers + self.log.handlers:
            handler.setLevel(logging.DEBUG)

        self._did_setup_logging = True

    def __call__(self, environ, start_response):
        self._setup_logging()
        if 'error' in environ.get('QUERY_STRING', '').lower():
            try:
                busted = 10000 / 0
            except Exception:
                self.log.exception('OMG you cannot has division by zero!: ')
                self.log.critical('It is because the Zero cannot be divided!')
                self.log.error('and if you continue to WANT, will be ERROR')
                self.log.warn('I am givin you dis warning!')
                self.log.info('It is for your information')
                self.log.debug('While this is just a bonus')
        else:
            self.log.info('Nothing to see here, folks')
            self.log.debug('for serious ... is nothing')

        start_response('200 OK', [('content-type', 'text/html')])
        body = self.__body__ % dict(
                environ='\n' + self._get_pretty_environ(environ),
                error=urllib.quote(random.choice(EXCLAMATIONS)),
        )
        return [body]

    def _get_pretty_environ(self, environ):
        base = {'QUERY_STRING': ''}

        setup_testing_defaults(base)
        for key in base.keys():
            base[key] = environ.get(key, base[key])

        sortkeys = base.keys()
        sortkeys.sort()

        ret = []
        for key in sortkeys:
            escaped = saxutils.escape(repr(base[key]))
            ret.append('%s: %s\n' % (key, escaped))

        return ''.join(ret)

########NEW FILE########
__FILENAME__ = _body
# This is an importable rather than a standalone html file
# for a couple of reasons, not least of those being
# than as soon as we take the step toward using file system
# resources, it makes packaging more complex ...
# The other reasons can be summarized as "laziness".


FIRELOGGER_HREF = "https://addons.mozilla.org/en-US/firefox/addon/11090"
FIREPYTHON_BASE_HREF = "http://firepython.binaryage.com"
BODY_HEADER = """\
<div id="header">
<div class="container">
    <div class="header-left span-8">
        <a href="http://www.binaryage.com"
            title="Binary Age"><div class="header-logo"></div></a>
        <a href="http://twitter.com/binaryage"><div
            class="twitter" title="Follow us on Twitter"></div></a>
    </div>
</div>
</div>
"""
BODY = """\
<!DOCTYPE html>
<html>
  <head>
    <title>FirePython demo app</title>
    <link rel="stylesheet" href="__BASE__/shared/css/screen.css"
        type="text/css" media="screen, projection">
    <link rel="stylesheet" href="__BASE__/shared/css/print.css"
        type="text/css" media="print">
    <!--[if lt IE 8]>
    <link rel="stylesheet"
        href="__BASE__/shared/css/ie.css" type="text/css"
        media="screen, projection">
    <![endif]-->
    <link rel="stylesheet" href="__BASE__/shared/css/site.css" type="text/css">
  </head>
  <body>
    __BODY_HEADER__
    <div id='site'>
      <div class='container'>
        <div class='main-left span-12'>
        <div class="logo">
          <img src="__BASE__/shared/img/firepython-icon.png"
              width="32" height="32"/>
          <h1>FirePython</h1>
        </div>
          <h2 id='instructions-header'>welcome to the FirePython demo app!</h2>
          <p id='instructions'>
              Make sure you have
                <a href="__FIRELOGGER_HREF__">firelogger</a> installed,
              then hit <a href="/BORK?error=%(error)s">this link</a>
              or any other request containing 'error' in the
              <strong>QUERY_STRING</strong> to see some output in
              the firebug <strong>Logger</strong> panel.
          </p>
          <h2 id='environ-header'><abbr
            title='partial environ, that is'>environ:</abbr></h2>
          <pre id='environ'>%(environ)s</pre>
        </div>
      </div>
    </div>
  </body>
</html>
"""

# poor man's templating, ftw!
REPLACEMENTS = (
    ('__FIRELOGGER_HREF__', FIRELOGGER_HREF),
    ('__BODY_HEADER__', BODY_HEADER),
    ('__BASE__', FIREPYTHON_BASE_HREF),   # this one *last*
)

for old, new in REPLACEMENTS:
    BODY = BODY.replace(old, new)

del old, new

EXCLAMATIONS = (
    "'bye", "'dswounds", "'sblood", "'sdeath", "'sfoot", "'struth",
    "'zackly", "'zactly", '10-4', 'AIUI', 'Abyssinia', 'BFD',
    'Baruch HaShem', 'Bueller', 'CBF', 'Christ', 'Christ alive',
    'Christ almighty', 'Deo volente', 'F off', 'FTMFW', 'FTW', 'G2G',
    'GDGD', 'GIYF', 'GTH', 'God Almighty', 'God Save the King',
    'God Save the Queen', 'God bless you', 'God damn',
    'God in heaven', 'God willing', 'Goddy', 'Godspeed',
    'Gordon Bennett', 'HTH', 'Happy Thanksgiving', 'Hell no',
    'Hell yeah', 'Holy Mother', 'Holy Mother of God', "I don't think",
    'I never did', 'I say', 'I should coco', 'I should cocoa', "I'll be",
    "I'll drink to that", "I'll say", 'JFGI', 'JSYK', 'Janey Mack',
    'Jeebus', 'Jeezum Crow', 'Jeremiah', 'Jesum Crow', 'Jesus',
    'Jesus Christ', 'Jesus H. Christ', 'Jesus Harold Christ',
    'Judas Priest', 'LOL', 'Lord be praised', 'Lord love a duck',
    'Lord willing', 'MTFBWY', 'NVRM', 'O', 'OK', 'OKDK', 'OMGWTFBBQ',
    'P U', "Qapla'", 'ROTFLMAO', 'ReHi', 'Selah', 'Sieg Heil', 'TT4N',
    'XD', 'ZOMFG', 'ZOMG', '^H', '^W', 'a', "a'ight", "a'right", 'aah',
    'aargh', 'aarrghh', 'about face', 'about sledge', 'abracadabra',
    'abso-fucking-lutely', 'absolutely', 'achoo', 'ack', 'action',
    'adieu', 'adios', 'agreed', 'ah', 'ah-choo', 'aha', 'ahchoo', 'ahem',
    'ahh', 'ahoy', 'ahoy-hoy', 'ai', 'ai yah', 'alack', 'alakazam', 'alas',
    'alley oop', 'allrighty', 'alreet', 'alrighty', 'amen', 'amidships',
    'and the horse you rode in on', 'applesauce',
    'arf', 'argh', 'arr', 'arrah now', 'as if', 'as you like',
    'as you wish', 'astaghfirullah',
    'atchoo', 'atishoo', 'attaboy', 'attagirl', 'au revoir', 'avast',
    'aw', 'aw shucks',
    'aweel', 'aww', 'ay', 'ay, chihuahua', 'aye', 'aye man',
    'ba da bing ba da boom',
    'bababadalgharaghtakamminarronnkonnbronntonnerronntuonnthunntrovar'
    'rhounawnskawntoohoohoordenenthurnuk', 'baccare', 'bad luck',
    'bada bing', 'bada bing bada boom', 'bada bing, bada boom', 'bada boom',
    'bada boom bada bing', 'bah', 'bam', 'banzai', 'bastard', 'batter up',
    'battle stations', 'beauty',
    'because', 'begad', 'begorra', 'begorrah', 'bejeezus', 'bejesus',
    'big deal', 'big whoop',
    'big wow', 'bingo', 'bish bash bosh', 'blah', 'blah blah blah', 'bleah',
    'blech', 'bleeding heck',
    'bleeding hell', 'bleh', 'bless you', 'blimey', "blimey O'Reilly",
    "blimey O'Riley", 'blood and tommy', 'bloody Nora',
    'blooming heck', 'blooming hell', 'blow this for a game of soldiers',
    'bog off', 'bollocks', 'bon voyage', 'boo', 'boo hoo',
    'boom', 'booyah', 'booyakasha', 'bosh', 'bostin', 'bother', 'bottoms up',
    'boutye',
)
# vim:filetype=html

########NEW FILE########
__FILENAME__ = handlers
# -*- mode: python; coding: utf-8 -*-

from logging import Handler

__all__ = ['ThreadBufferedHandler']


threading_supported = False
try:
    import threading
    if threading:
        threading_supported = True
except ImportError:
    pass


class ThreadBufferedHandler(Handler):
    """ A logging handler that buffers records by thread. """

    def __init__(self):
        Handler.__init__(self)
        self.records = {} # dictionary (Thread -> list of records)
        self._enabled = {} # dictionary (Thread -> enabled/disabled)
        self.republished = {} # dictionary (Thread -> list of tuples (header_name, header_value) )

    def start(self, thread=None):
        if not thread and threading_supported:
            thread = threading.currentThread()
        self._enabled[thread] = True

    def finish(self, thread=None):
        if not thread and threading_supported:
            thread = threading.currentThread()
        self._enabled.pop(thread, None)

    def is_enabled(self, thread=None):
        if not thread and threading_supported:
            thread = threading.currentThread()
        return self._enabled.get(thread, False)

    def emit(self, record):
        """ Append the record to the buffer for the current thread. """
        if self.is_enabled():
            self.get_records().append(record)

    def get_records(self, thread=None):
        """
        Gets the log messages of the specified thread, or the current thread if
        no thread is specified.
        """
        if not thread and threading_supported:
            thread = threading.currentThread()
        if thread not in self.records:
            self.records[thread] = []
        return self.records[thread]

    def clear_records(self, thread=None):
        """
        Clears the log messages of the specified thread, or the current thread
        if no thread is specified.
        """
        if not thread and threading_supported:
            thread = threading.currentThread()
        if thread in self.records:
            del self.records[thread]

    def republish(self, headers):
        """ Appends republished firepython headers for the current thread. """
        if self.is_enabled():
            self.get_republished().extend(headers)

    def get_republished(self, thread=None):
        if not thread and threading_supported:
            thread = threading.currentThread()
        if thread not in self.republished:
            self.republished[thread] = []
        return self.republished[thread]

    def clear_republished(self, thread=None):
        if not thread and threading_supported:
            thread = threading.currentThread()
        if thread in self.republished:
            del self.republished[thread]

########NEW FILE########
__FILENAME__ = middleware
# -*- mode: python; coding: utf-8 -*-

import os
import sys
import time
import random
import logging
import traceback

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import jsonpickle

try:
    import gprof2dot
except ImportError:
    gprof2dot = None

import firepython
import firepython.utils
import firepython._const as CONST
from firepython.handlers import ThreadBufferedHandler

__all__ = [
    'FirePythonBase',
    'FirePythonDjango',
    'FirePythonWSGI',
    'paste_filter_factory',
]


# add a new backed jsonpickle for Django
# jsonpickle will attempt to import this if default
# jsonpickle libraries are not present
jsonpickle.load_backend('django.utils.simplejson', 'dumps',
                        'loads', ValueError)

class FirePythonBase(object):

    def __init__(self):
        raise NotImplementedError("Must be subclassed")

    def install_handler(self):
        logger = logging.getLogger(self._logger_name)
        self._handler = ThreadBufferedHandler()
        logger.addHandler(self._handler)

    def uninstall_handler(self):
        if self._handler is None:
            return
        logger = logging.getLogger(self._logger_name)
        logger.removeHandler(self._handler)
        self._handler = None

    def _version_check(self, version_header):
        firelogger_api_version = version_header.strip()
        if firelogger_api_version == '':
            logging.info('FireLogger not detected')
            return False
        if firepython.__api_version__ != firelogger_api_version:
            self._client_message += (
                'Warning: FireLogger (client) has version %s, but '
                'FirePython (server) is version %s. Check http://firelogger.binaryage.com for latest version.' % (firelogger_api_version,
                                                 firepython.__api_version__)
            )
            logging.warning('FireLogger (client) has version %s, but FirePython '
                            '(server) is version %s. Check http://firelogger.binaryage.com for latest version.', firelogger_api_version,
                            firepython.__api_version__)
        return True

    def _password_check(self, token):
        if self._password is None:
            raise Exception("self._password must be set!")
        if not firepython.utils.get_auth_token(self._password) == token:
            self._client_message += 'FireLogger password does not match. '
            logging.warning('FireLogger password does not match. Logging output won\'t be sent to FireLogger. Double check your settings!')
            return False
        return True

    def _appengine_check(self):
        if 'google.appengine' not in sys.modules:
            return True  # Definitely not running under Google App Engine
        try:
            from google.appengine.api import users
        except ImportError:
            return True  # Apparently not running under Google App Engine
        if os.getenv('SERVER_SOFTWARE', '').startswith('Dev'):
            return True  # Running in SDK dev_appserver
        # Running in production, only allow admin users
        if not users.is_current_user_admin():
            self._client_message += 'Security: Log in as a project administrator to see FirePython logs (App Engine in production mode). '
            logging.warning('Security: Log in as a project administrator to see FirePython logs (App Engine in production mode)')
            return False
        return True

    def _check(self, env):
        self._client_message = ''
        self._profile_enabled = \
            env.get(CONST.FIRELOGGER_PROFILER_ENABLED_HEADER, '') != ''
        self._appstats_enabled = \
            env.get(CONST.FIRELOGGER_APPSTATS_ENABLED_HEADER, '') != ''
        if self._check_agent and not self._version_check(
            env.get(CONST.FIRELOGGER_VERSION_HEADER, '')):
            return False
        if ((self._password and not
              self._password_check(
                env.get(CONST.FIRELOGGER_AUTH_HEADER, '')))):
            return False
        # If _password is set, skip _appengine_check()
        if (not self._password and not self._appengine_check()):
            return False
        return True

    def _sanitize_exc_info(self, exc_info):
        if exc_info == None:
            return ("?", "No exception info available", [])
        exc_type = exc_info[0]
        exc_value = exc_info[1]
        exc_traceback = exc_info[2]
        if exc_traceback is not None:
            exc_traceback = traceback.extract_tb(exc_traceback)
        return (exc_type, exc_value, exc_traceback)

    def _handle_internal_exception(self, e):
        if CONST.RAZOR_MODE: # in razor mode hurt web server
            raise e
        # in non-razor mode report internal error to firepython addon
        exc_info = self._sanitize_exc_info(sys.exc_info())
        return {"message": "Internal FirePython error: %s" % unicode(e),
                "exc_info": exc_info}

    def _encode(self, logs, errors=None, profile=None, extension_data=None):
        data = {"logs": logs}
        if errors:
            data['errors'] = errors
        if profile:
            data['profile'] = profile
        if extension_data:
            data['extension_data'] = extension_data
        try:
            data = jsonpickle.encode(data, unpicklable=False,
                                     max_depth=CONST.JSONPICKLE_DEPTH)
        except Exception, e:
            # this exception may be fired, because of buggy __repr__ or
            # __str__ implementations on various objects
            errors = [self._handle_internal_exception(e)]
            try:
                data = jsonpickle.encode({"errors": errors },
                                         unpicklable=False,
                                         max_depth=CONST.JSONPICKLE_DEPTH)
            except Exception, e:
                # even unable to serialize error message
                data = jsonpickle.encode(
                        {"errors": {
                            "message": "FirePython has a really bad day :-("
                        }
                    },
                    unpicklable=False,
                    max_depth=CONST.JSONPICKLE_DEPTH
                )
        data = data.encode('utf-8')
        data = data.encode('base64')
        return data.splitlines()

    def republish(self, headers):
        firelogger_headers = []
        for key, value in headers.iteritems():
            if CONST.FIRELOGGER_RESPONSE_HEADER.match(key):
                firelogger_headers.append((key, value))

        self._handler.republish(firelogger_headers)

    def _flush_records(self, add_header, profile=None, extension_data=None):
        """
        Flush collected logs into response.

        Argument ``add_header`` should be a function receiving two arguments:
        ``name`` and ``value`` of header.
        """

        records = self._handler.get_records()
        self._handler.clear_records()
        republished = self._handler.get_republished()
        self._handler.clear_republished()

        for name, value in republished:
            add_header(name, value)

        logs = []
        errors = []
        for record in records:
            try:
                logs.append(self._prepare_log_record(record))
            except Exception, e:
                # this exception may be fired, because of buggy __repr__ or
                # __str__ implementations on various objects
                errors.append(self._handle_internal_exception(e))

        chunks = self._encode(logs, errors, profile, extension_data)
        guid = "%08x" % random.randint(0, 0xFFFFFFFF)
        for i, chunk in enumerate(chunks):
            add_header(CONST.FIRELOGGER_HEADER_FORMAT %
                       dict(guid=guid, identity=i), chunk)

    def _prepare_log_record(self, record):
        data = {
            "level": self._log_level(record.levelno),
            "message": self._handler.format(record),
            "template": record.msg,
            "timestamp": long(record.created * 1000 * 1000),
            "time": (time.strftime("%H:%M:%S",
                     time.localtime(record.created)) +
                (".%03d" % ((record.created - long(record.created)) * 1000))
            )
        }
        props = ["args", "pathname", "lineno", "exc_text", "name", "process",
                 "thread", "threadName"]
        for p in props:
            try:
                data[p] = getattr(record, p)
            except AttributeError:
                pass

        try:
            exc_info = getattr(record, 'exc_info')
            if exc_info is not None:
                data['exc_info'] = self._sanitize_exc_info(exc_info)

                frames = []
                t = exc_info[2]
                while t:
                    try:
                        d = {}
                        for k,v in t.tb_frame.f_locals.iteritems():
                            if CONST.DEEP_LOCALS:
                                d[unicode(k)] = v
                            else:
                                d[unicode(k)] = repr(v)
                        frames.append(d)
                    except:
                        frames.append('?')
                    t = t.tb_next
                data['exc_frames'] = frames
        except AttributeError:
            pass
        return data

    def _log_level(self, level):
        if level >= logging.CRITICAL:
            return "critical"
        elif level >= logging.ERROR:
            return "error"
        elif level >= logging.WARNING:
            return "warning"
        elif level >= logging.INFO:
            return "info"
        else:
            return "debug"

    def _start(self):
        self._handler.start()

    def _finish(self):
        self._handler.finish()

    def _profile_wrap(self, func):
        '''If the FIRELOGGER_RESPONSE_HEADER header has been passed with a
        request, given function will be wrapped with a profile.
        '''
        if not self._profile_enabled:
            return func
        try:
            import cProfile as profile
        except ImportError:
            import profile
        self._prof = profile.Profile()
        def prof_wrapper(*args, **kwargs):
            return self._prof.runcall(func, *args, **kwargs)
        return prof_wrapper

    def _prepare_profile(self):
        """Prepares profiling information."""
        if not self._profile_enabled or not hasattr(self, '_prof'):
            return None

        if not gprof2dot:
            logging.warn('failed to import ``gprof2dot``, will not profile')
            return None

        self._prof.create_stats()
        parser = gprof2dot.PstatsParser(self._prof)

        def get_function_name((filename, line, name)):
            module = os.path.splitext(filename)[0]
            module_pieces = module.split(os.path.sep)
            return "%s:%d:%s" % ("/".join(module_pieces[-4:]), line, name)

        parser.get_function_name = get_function_name
        output = StringIO()
        gprof = parser.parse()

        gprof.prune(0.005, 0.001)
                # TODO: ^--- Parameterize node and edge thresholds.
        dot = gprof2dot.DotWriter(output)
        theme = gprof2dot.TEMPERATURE_COLORMAP
        theme.bgcolor = (0.0, 0.0, 0.0)
                        # ^--- Use black text, for less eye-bleeding.
        dot.graph(gprof, theme)

        def get_info(self):
            s = "Profile Graph:"
            s += " %.3fs CPU" % self.total_tt
            s += ": %d function calls" % self.total_calls
            if self.total_calls != self.prim_calls:
                s += " (%d primitive calls)" % self.prim_calls
            return s

        profile = {
          "producer": "gprof2dot",
          "producerVersion": str(gprof2dot.__version__),
          "info": get_info(parser.stats),
          "dot": output.getvalue(),
        }

        return profile


class FirePythonDjango(FirePythonBase):
    """
    Django middleware to enable FirePython logging.

    To use add 'firepython.middleware.FirePythonDjango' to your
    MIDDLEWARE_CLASSES setting.

    Optional settings:

     - ``FIREPYTHON_PASSWORD``: password to protect your logs
     - ``FIREPYTHON_LOGGER_NAME``: specific logger name you want to monitor
     - ``FIREPYTHON_CHECK_AGENT``: set to False for prevent server to check
       presence of firepython in user-agent HTTP header.
    """

    def __init__(self):
        from django.conf import settings
        self._extension_data = {}
        self._password = getattr(settings, 'FIREPYTHON_PASSWORD', None)
        self._logger_name = getattr(settings, 'FIREPYTHON_LOGGER_NAME', None)
        self._check_agent = getattr(settings, 'FIREPYTHON_CHECK_AGENT', True)
        self.install_handler()

    def __del__(self):
        self.uninstall_handler()

    def process_request(self, request):
        if not self._check(request.META):
            return

        self._start()
        # Make set_extension_data available via the request object.
        if self._appstats_enabled:
            request.firepython_appstats_enabled = True
        request.firepython_set_extension_data = self._extension_data.__setitem__

    def process_view(self, request, callback, callback_args, callback_kwargs):
        args = (request, ) + callback_args
        return self._profile_wrap(callback)(*args, **callback_kwargs)

    def process_response(self, request, response):
        check = self._check(request.META)
        if self._client_message:
            response.__setitem__(CONST.FIRELOGGER_MESSAGE_HEADER,
                                 self._client_message)
        if not check:
            return response
            
        profile = self._prepare_profile()
        self._finish()
        self._flush_records(response.__setitem__, profile, self._extension_data)
        return response

    def process_exception(self, request, exception):
        if not self._check(request.META):
            return

        logging.exception(exception)


class FirePythonWSGI(FirePythonBase):
    """
    WSGI middleware to enable FirePython logging.

    Supply an application object and an optional password to enable password
    protection. Also logger name may be specified.
    """
    def __init__(self, app, password=None, logger_name=None, check_agent=True):
        self.app = app
        self._password = password
        self._logger_name = logger_name
        self._check_agent = check_agent
        self.install_handler()

    def __del__(self):
        self.uninstall_handler()

    def __call__(self, environ, start_response):
        check = self._check(environ)
        if not check and not self._client_message:
            return self.app(environ, start_response) # a quick path

        # firepython is enabled or we have a client message we want to communicate in headers
        client_message = self._client_message

        # asking why? see __ref_pymod_counter__
        closure = ["200 OK", [], None]
        extension_data = {}  # Collect extension data here
        sio = StringIO()
        def faked_start_response(_status, _headers, _exc_info=None):
            closure[0] = _status
            closure[1] = _headers
            closure[2] = _exc_info
            if client_message:
                closure[1].append(
                    (CONST.FIRELOGGER_MESSAGE_HEADER, client_message))
            return sio.write

        def add_header(name, value):
            closure[1].append((name, value))

        if self._appstats_enabled:
            environ['firepython.appstats_enabled'] = True
            
        if check: 
            self._start()
            environ['firepython.set_extension_data'] = extension_data.__setitem__
            
        # run app
        try:
            # the nested try-except block within
            # a try-finally block is so that we stay
            # python2.3 compatible
            try:
                app = self.app
                if check:
                    app = self._profile_wrap(app)
                app_iter = app(environ, faked_start_response)
                output = list(app_iter)
            except:
                logging.warning("DeprecationWarning: raising a "
                                "string exception is deprecated")
                logging.exception(sys.exc_info()[0])
                raise
        finally:
            # Output the profile first, so we can see any errors in profiling.
            if check: 
                profile = self._prepare_profile()
                self._finish()
                self._flush_records(add_header, profile, extension_data)

        # start responding
        write = start_response(*closure)
        if sio.tell(): # position is not 0
            sio.seek(0)
            write(sio.read())
        # return output
        return output


def paste_filter_factory(global_conf, password_file='', logger_name='',
                         check_agent='true'):
    from paste.deploy.converters import asbool

    check_agent = asbool(check_agent)
    get_password = lambda: ''
    if password_file:
        def get_password():
            return open(password_file).read().strip()

    def with_firepython_middleware(app):
        return FirePythonWSGI(app, password=get_password(),
                              logger_name=logger_name,
                              check_agent=check_agent)
    return with_firepython_middleware


__ref_pymod_counter__ = \
"http://jjinux.blogspot.com/2006/10/python-modifying-counter-in-closure.html"

########NEW FILE########
__FILENAME__ = mini_graphviz
import sys
import optparse
import tempfile
import subprocess

__all__ = [
    'main',
]

DEFAULT_DOT = 'dot'
DEFAULT_VIEWER = 'eog'
USAGE = "%prog [options]"
OPTIONS = (
    (('-D', '--dot-exe'),
        dict(dest='dot', action='store', default=DEFAULT_DOT,
             help='dot executable to use for making png, '
                  'default=%r' % DEFAULT_DOT)),
    (('-V', '--viewer'),
        dict(dest='viewer', action='store', default=DEFAULT_VIEWER,
             help='viewer with which to open resulting png, '
                  'default=%r' % DEFAULT_VIEWER)),
)


def main(sysargs=sys.argv[:]):
    parser = get_option_parser()
    opts, targets = parser.parse_args(sysargs[1:])

    for target in targets:
        graphviz = MiniGraphviz(dot=opts.dot, viewer=opts.viewer)
        graphviz.view_as_png(target)

    return 0


def get_option_parser():
    parser = optparse.OptionParser(usage=USAGE)
    for args, kwargs in OPTIONS:
        parser.add_option(*args, **kwargs)
    return parser


class MiniGraphviz(object):

    def __init__(self, dot=DEFAULT_DOT, viewer=DEFAULT_VIEWER):
        self.dot = dot
        self.viewer = viewer

    def view_as_png(self, dot_input_file):
        png_maker = Dot2PngMaker(dot_input_file, dot=self.dot)
        png_path = png_maker.get_png()
        self._open_png_with_viewer(png_path)
        return png_path

    def _open_png_with_viewer(self, png_path):
        if self.viewer:
            cmd = [self.viewer, png_path]
            subprocess.call(cmd)


class Dot2PngMaker(object):
    _tempfile = ''

    def __init__(self, dot_input_file, dot=DEFAULT_DOT):
        self.dot_input_file = dot_input_file
        self.dot = dot

    def get_png(self):
        self._get_tempfile()
        self._get_png_from_dot()
        return self._tempfile

    def _get_tempfile(self):
        self._tempfile = tempfile.mkstemp('.png', __name__)[1]

    def _get_png_from_dot(self):
        cmd = [self.dot, '-T', 'png', '-o', self._tempfile,
               self.dot_input_file]
        subprocess.call(cmd)


if __name__ == '__main__':
    sys.exit(main())

# vim:filetype=python

########NEW FILE########
__FILENAME__ = utils
# -*- mode: python; coding: utf-8 -*-
import sys
from firepython import __api_version__
import firepython._const as CONST


__all__ = [
    'json_encode',
    'get_version_header',
    'get_auth_token',
    'get_auth_header',
]

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        from django.utils import simplejson as json

try:
    from hashlib import md5
except ImportError:
    from md5 import md5


class TolerantJSONEncoder(json.JSONEncoder):

    def default(self, o):
        return str(o)


def json_encode(data):
    return json.dumps(data, cls=TolerantJSONEncoder)


def get_version_header(version=__api_version__):
    return (CONST.FIRELOGGER_VERSION_HEADER, version)


def get_auth_token(password):
    return md5(CONST.AUTHTOK_FORMAT % password).hexdigest()


def get_auth_header(password):
    return (CONST.FIRELOGGER_AUTH_HEADER, get_auth_token(password))

########NEW FILE########
__FILENAME__ = _const
import re

AUTHTOK_FORMAT = '#FireLoggerPassword#%s#'
DEEP_LOCALS = True
FIRELOGGER_APPSTATS_ENABLED_HEADER = 'HTTP_X_FIRELOGGERAPPSTATS'
FIRELOGGER_AUTH_HEADER = 'HTTP_X_FIRELOGGERAUTH'
FIRELOGGER_HEADER_FORMAT = 'FireLogger-%(guid)s-%(identity)s'
FIRELOGGER_MESSAGE_HEADER = 'FireLoggerMessage'
FIRELOGGER_PROFILER_ENABLED_HEADER = 'HTTP_X_FIRELOGGERPROFILER'
FIRELOGGER_RESPONSE_HEADER = re.compile(r'^FireLogger', re.IGNORECASE)
FIRELOGGER_VERSION_HEADER = 'HTTP_X_FIRELOGGER'
JSONPICKLE_DEPTH = 16
RAZOR_MODE = False

########NEW FILE########
__FILENAME__ = gprof2dot
#!/usr/bin/env python
#
# Copyright 2008-2009 Jose Fonseca
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Generate a dot graph from the output of several profilers."""

__author__ = "Jose Fonseca"

__version__ = "1.0"


import sys
import math
import os.path
import re
import textwrap
import optparse
import xml.parsers.expat


try:
    # Debugging helper module
    import debug
except ImportError:
    pass


def percentage(p):
    return "%.02f%%" % (p*100.0,)

def add(a, b):
    return a + b

def equal(a, b):
    if a == b:
        return a
    else:
        return None

def fail(a, b):
    assert False


tol = 2 ** -23

def ratio(numerator, denominator):
    try:
        ratio = float(numerator)/float(denominator)
    except ZeroDivisionError:
        # 0/0 is undefined, but 1.0 yields more useful results
        return 1.0
    if ratio < 0.0:
        if ratio < -tol:
            sys.stderr.write('warning: negative ratio (%s/%s)\n' % (numerator, denominator))
        return 0.0
    if ratio > 1.0:
        if ratio > 1.0 + tol:
            sys.stderr.write('warning: ratio greater than one (%s/%s)\n' % (numerator, denominator))
        return 1.0
    return ratio


class UndefinedEvent(Exception):
    """Raised when attempting to get an event which is undefined."""

    def __init__(self, event):
        Exception.__init__(self)
        self.event = event

    def __str__(self):
        return 'unspecified event %s' % self.event.name


class Event(object):
    """Describe a kind of event, and its basic operations."""

    def __init__(self, name, null, aggregator, formatter = str):
        self.name = name
        self._null = null
        self._aggregator = aggregator
        self._formatter = formatter

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)

    def null(self):
        return self._null

    def aggregate(self, val1, val2):
        """Aggregate two event values."""
        assert val1 is not None
        assert val2 is not None
        return self._aggregator(val1, val2)

    def format(self, val):
        """Format an event value."""
        assert val is not None
        return self._formatter(val)


MODULE = Event("Module", None, equal)
PROCESS = Event("Process", None, equal)

CALLS = Event("Calls", 0, add)
SAMPLES = Event("Samples", 0, add)
SAMPLES2 = Event("Samples", 0, add)

TIME = Event("Time", 0.0, add, lambda x: '(' + str(x) + ')')
TIME_RATIO = Event("Time ratio", 0.0, add, lambda x: '(' + percentage(x) + ')')
TOTAL_TIME = Event("Total time", 0.0, fail)
TOTAL_TIME_RATIO = Event("Total time ratio", 0.0, fail, percentage)

CALL_RATIO = Event("Call ratio", 0.0, add, percentage)

PRUNE_RATIO = Event("Prune ratio", 0.0, add, percentage)


class Object(object):
    """Base class for all objects in profile which can store events."""

    def __init__(self, events=None):
        if events is None:
            self.events = {}
        else:
            self.events = events

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

    def __contains__(self, event):
        return event in self.events

    def __getitem__(self, event):
        try:
            return self.events[event]
        except KeyError:
            raise UndefinedEvent(event)

    def __setitem__(self, event, value):
        if value is None:
            if event in self.events:
                del self.events[event]
        else:
            self.events[event] = value


class Call(Object):
    """A call between functions.

    There should be at most one call object for every pair of functions.
    """

    def __init__(self, callee_id):
        Object.__init__(self)
        self.callee_id = callee_id


class Function(Object):
    """A function."""

    def __init__(self, id, name):
        Object.__init__(self)
        self.id = id
        self.name = name
        self.calls = {}
        self.cycle = None

    def add_call(self, call):
        if call.callee_id in self.calls:
            sys.stderr.write('warning: overwriting call from function %s to %s\n' % (str(self.id), str(call.callee_id)))
        self.calls[call.callee_id] = call

    # TODO: write utility functions

    def __repr__(self):
        return self.name


class Cycle(Object):
    """A cycle made from recursive function calls."""

    def __init__(self):
        Object.__init__(self)
        # XXX: Do cycles need an id?
        self.functions = set()

    def add_function(self, function):
        assert function not in self.functions
        self.functions.add(function)
        # XXX: Aggregate events?
        if function.cycle is not None:
            for other in function.cycle.functions:
                if function not in self.functions:
                    self.add_function(other)
        function.cycle = self


class Profile(Object):
    """The whole profile."""

    def __init__(self):
        Object.__init__(self)
        self.functions = {}
        self.cycles = []

    def add_function(self, function):
        if function.id in self.functions:
            sys.stderr.write('warning: overwriting function %s (id %s)\n' % (function.name, str(function.id)))
        self.functions[function.id] = function

    def add_cycle(self, cycle):
        self.cycles.append(cycle)

    def validate(self):
        """Validate the edges."""

        for function in self.functions.itervalues():
            for callee_id in function.calls.keys():
                assert function.calls[callee_id].callee_id == callee_id
                if callee_id not in self.functions:
                    sys.stderr.write('warning: call to undefined function %s from function %s\n' % (str(callee_id), function.name))
                    del function.calls[callee_id]

    def find_cycles(self):
        """Find cycles using Tarjan's strongly connected components algorithm."""

        # Apply the Tarjan's algorithm successively until all functions are visited
        visited = set()
        for function in self.functions.itervalues():
            if function not in visited:
                self._tarjan(function, 0, [], {}, {}, visited)
        cycles = []
        for function in self.functions.itervalues():
            if function.cycle is not None and function.cycle not in cycles:
                cycles.append(function.cycle)
        self.cycles = cycles
        if 0:
            for cycle in cycles:
                sys.stderr.write("Cycle:\n")
                for member in cycle.functions:
                    sys.stderr.write("\t%s\n" % member.name)

    def _tarjan(self, function, order, stack, orders, lowlinks, visited):
        """Tarjan's strongly connected components algorithm.

        See also:
        - http://en.wikipedia.org/wiki/Tarjan's_strongly_connected_components_algorithm
        """

        visited.add(function)
        orders[function] = order
        lowlinks[function] = order
        order += 1
        pos = len(stack)
        stack.append(function)
        for call in function.calls.itervalues():
            callee = self.functions[call.callee_id]
            # TODO: use a set to optimize lookup
            if callee not in orders:
                order = self._tarjan(callee, order, stack, orders, lowlinks, visited)
                lowlinks[function] = min(lowlinks[function], lowlinks[callee])
            elif callee in stack:
                lowlinks[function] = min(lowlinks[function], orders[callee])
        if lowlinks[function] == orders[function]:
            # Strongly connected component found
            members = stack[pos:]
            del stack[pos:]
            if len(members) > 1:
                cycle = Cycle()
                for member in members:
                    cycle.add_function(member)
        return order

    def call_ratios(self, event):
        # Aggregate for incoming calls
        cycle_totals = {}
        for cycle in self.cycles:
            cycle_totals[cycle] = 0.0
        function_totals = {}
        for function in self.functions.itervalues():
            function_totals[function] = 0.0
        for function in self.functions.itervalues():
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    function_totals[callee] += call[event]
                    if callee.cycle is not None and callee.cycle is not function.cycle:
                        cycle_totals[callee.cycle] += call[event]

        # Compute the ratios
        for function in self.functions.itervalues():
            for call in function.calls.itervalues():
                assert CALL_RATIO not in call
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is not None and callee.cycle is not function.cycle:
                        total = cycle_totals[callee.cycle]
                    else:
                        total = function_totals[callee]
                    call[CALL_RATIO] = ratio(call[event], total)

    def integrate(self, outevent, inevent):
        """Propagate function time ratio allong the function calls.

        Must be called after finding the cycles.

        See also:
        - http://citeseer.ist.psu.edu/graham82gprof.html
        """

        # Sanity checking
        assert outevent not in self
        for function in self.functions.itervalues():
            assert outevent not in function
            assert inevent in function
            for call in function.calls.itervalues():
                assert outevent not in call
                if call.callee_id != function.id:
                    assert CALL_RATIO in call

        # Aggregate the input for each cycle
        for cycle in self.cycles:
            total = inevent.null()
            for function in self.functions.itervalues():
                total = inevent.aggregate(total, function[inevent])
            self[inevent] = total

        # Integrate along the edges
        total = inevent.null()
        for function in self.functions.itervalues():
            total = inevent.aggregate(total, function[inevent])
            self._integrate_function(function, outevent, inevent)
        self[outevent] = total

    def _integrate_function(self, function, outevent, inevent):
        if function.cycle is not None:
            return self._integrate_cycle(function.cycle, outevent, inevent)
        else:
            if outevent not in function:
                total = function[inevent]
                for call in function.calls.itervalues():
                    if call.callee_id != function.id:
                        total += self._integrate_call(call, outevent, inevent)
                function[outevent] = total
            return function[outevent]

    def _integrate_call(self, call, outevent, inevent):
        assert outevent not in call
        assert CALL_RATIO in call
        callee = self.functions[call.callee_id]
        subtotal = call[CALL_RATIO]*self._integrate_function(callee, outevent, inevent)
        call[outevent] = subtotal
        return subtotal

    def _integrate_cycle(self, cycle, outevent, inevent):
        if outevent not in cycle:

            total = inevent.null()
            for member in cycle.functions:
                subtotal = member[inevent]
                for call in member.calls.itervalues():
                    callee = self.functions[call.callee_id]
                    if callee.cycle is not cycle:
                        subtotal += self._integrate_call(call, outevent, inevent)
                total += subtotal
            cycle[outevent] = total

            callees = {}
            for function in self.functions.itervalues():
                if function.cycle is not cycle:
                    for call in function.calls.itervalues():
                        callee = self.functions[call.callee_id]
                        if callee.cycle is cycle:
                            try:
                                callees[callee] += call[CALL_RATIO]
                            except KeyError:
                                callees[callee] = call[CALL_RATIO]

            for callee, call_ratio in callees.iteritems():
                ranks = {}
                call_ratios = {}
                partials = {}
                self._rank_cycle_function(cycle, callee, 0, ranks)
                self._call_ratios_cycle(cycle, callee, ranks, call_ratios, set())
                partial = self._integrate_cycle_function(cycle, callee, call_ratio, partials, ranks, call_ratios, outevent, inevent)
                assert partial == max(partials.values())
                assert not total or abs(1.0 - partial/(call_ratio*total)) <= 0.001

        return cycle[outevent]

    def _rank_cycle_function(self, cycle, function, rank, ranks):
        if function not in ranks or ranks[function] > rank:
            ranks[function] = rank
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is cycle:
                        self._rank_cycle_function(cycle, callee, rank + 1, ranks)

    def _call_ratios_cycle(self, cycle, function, ranks, call_ratios, visited):
        if function not in visited:
            visited.add(function)
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is cycle:
                        if ranks[callee] > ranks[function]:
                            call_ratios[callee] = call_ratios.get(callee, 0.0) + call[CALL_RATIO]
                            self._call_ratios_cycle(cycle, callee, ranks, call_ratios, visited)

    def _integrate_cycle_function(self, cycle, function, partial_ratio, partials, ranks, call_ratios, outevent, inevent):
        if function not in partials:
            partial = partial_ratio*function[inevent]
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is not cycle:
                        assert outevent in call
                        partial += partial_ratio*call[outevent]
                    else:
                        if ranks[callee] > ranks[function]:
                            callee_partial = self._integrate_cycle_function(cycle, callee, partial_ratio, partials, ranks, call_ratios, outevent, inevent)
                            call_ratio = ratio(call[CALL_RATIO], call_ratios[callee])
                            call_partial = call_ratio*callee_partial
                            try:
                                call[outevent] += call_partial
                            except UndefinedEvent:
                                call[outevent] = call_partial
                            partial += call_partial
            partials[function] = partial
            try:
                function[outevent] += partial
            except UndefinedEvent:
                function[outevent] = partial
        return partials[function]

    def aggregate(self, event):
        """Aggregate an event for the whole profile."""

        total = event.null()
        for function in self.functions.itervalues():
            try:
                total = event.aggregate(total, function[event])
            except UndefinedEvent:
                return
        self[event] = total

    def ratio(self, outevent, inevent):
        assert outevent not in self
        assert inevent in self
        for function in self.functions.itervalues():
            assert outevent not in function
            assert inevent in function
            function[outevent] = ratio(function[inevent], self[inevent])
            for call in function.calls.itervalues():
                assert outevent not in call
                if inevent in call:
                    call[outevent] = ratio(call[inevent], self[inevent])
        self[outevent] = 1.0

    def prune(self, node_thres, edge_thres):
        """Prune the profile"""

        # compute the prune ratios
        for function in self.functions.itervalues():
            try:
                function[PRUNE_RATIO] = function[TOTAL_TIME_RATIO]
            except UndefinedEvent:
                pass

            for call in function.calls.itervalues():
                callee = self.functions[call.callee_id]

                if TOTAL_TIME_RATIO in call:
                    # handle exact cases first
                    call[PRUNE_RATIO] = call[TOTAL_TIME_RATIO]
                else:
                    try:
                        # make a safe estimate
                        call[PRUNE_RATIO] = min(function[TOTAL_TIME_RATIO], callee[TOTAL_TIME_RATIO])
                    except UndefinedEvent:
                        pass

        # prune the nodes
        for function_id in self.functions.keys():
            function = self.functions[function_id]
            try:
                if function[PRUNE_RATIO] < node_thres:
                    del self.functions[function_id]
            except UndefinedEvent:
                pass

        # prune the egdes
        for function in self.functions.itervalues():
            for callee_id in function.calls.keys():
                call = function.calls[callee_id]
                try:
                    if callee_id not in self.functions or call[PRUNE_RATIO] < edge_thres:
                        del function.calls[callee_id]
                except UndefinedEvent:
                    pass

    def dump(self):
        for function in self.functions.itervalues():
            sys.stderr.write('Function %s:\n' % (function.name,))
            self._dump_events(function.events)
            for call in function.calls.itervalues():
                callee = self.functions[call.callee_id]
                sys.stderr.write('  Call %s:\n' % (callee.name,))
                self._dump_events(call.events)

    def _dump_events(self, events):
        for event, value in events.iteritems():
            sys.stderr.write('    %s: %s\n' % (event.name, event.format(value)))


class Struct:
    """Masquerade a dictionary with a structure-like behavior."""

    def __init__(self, attrs = None):
        if attrs is None:
            attrs = {}
        self.__dict__['_attrs'] = attrs

    def __getattr__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self._attrs[name] = value

    def __str__(self):
        return str(self._attrs)

    def __repr__(self):
        return repr(self._attrs)


class ParseError(Exception):
    """Raised when parsing to signal mismatches."""

    def __init__(self, msg, line):
        self.msg = msg
        # TODO: store more source line information
        self.line = line

    def __str__(self):
        return '%s: %r' % (self.msg, self.line)


class Parser:
    """Parser interface."""

    def __init__(self):
        pass

    def parse(self):
        raise NotImplementedError


class LineParser(Parser):
    """Base class for parsers that read line-based formats."""

    def __init__(self, file):
        Parser.__init__(self)
        self._file = file
        self.__line = None
        self.__eof = False

    def readline(self):
        line = self._file.readline()
        if not line:
            self.__line = ''
            self.__eof = True
        self.__line = line.rstrip('\r\n')

    def lookahead(self):
        assert self.__line is not None
        return self.__line

    def consume(self):
        assert self.__line is not None
        line = self.__line
        self.readline()
        return line

    def eof(self):
        assert self.__line is not None
        return self.__eof


XML_ELEMENT_START, XML_ELEMENT_END, XML_CHARACTER_DATA, XML_EOF = range(4)


class XmlToken:

    def __init__(self, type, name_or_data, attrs = None, line = None, column = None):
        assert type in (XML_ELEMENT_START, XML_ELEMENT_END, XML_CHARACTER_DATA, XML_EOF)
        self.type = type
        self.name_or_data = name_or_data
        self.attrs = attrs
        self.line = line
        self.column = column

    def __str__(self):
        if self.type == XML_ELEMENT_START:
            return '<' + self.name_or_data + ' ...>'
        if self.type == XML_ELEMENT_END:
            return '</' + self.name_or_data + '>'
        if self.type == XML_CHARACTER_DATA:
            return self.name_or_data
        if self.type == XML_EOF:
            return 'end of file'
        assert 0


class XmlTokenizer:
    """Expat based XML tokenizer."""

    def __init__(self, fp, skip_ws = True):
        self.fp = fp
        self.tokens = []
        self.index = 0
        self.final = False
        self.skip_ws = skip_ws

        self.character_pos = 0, 0
        self.character_data = ''

        self.parser = xml.parsers.expat.ParserCreate()
        self.parser.StartElementHandler  = self.handle_element_start
        self.parser.EndElementHandler    = self.handle_element_end
        self.parser.CharacterDataHandler = self.handle_character_data

    def handle_element_start(self, name, attributes):
        self.finish_character_data()
        line, column = self.pos()
        token = XmlToken(XML_ELEMENT_START, name, attributes, line, column)
        self.tokens.append(token)

    def handle_element_end(self, name):
        self.finish_character_data()
        line, column = self.pos()
        token = XmlToken(XML_ELEMENT_END, name, None, line, column)
        self.tokens.append(token)

    def handle_character_data(self, data):
        if not self.character_data:
            self.character_pos = self.pos()
        self.character_data += data

    def finish_character_data(self):
        if self.character_data:
            if not self.skip_ws or not self.character_data.isspace():
                line, column = self.character_pos
                token = XmlToken(XML_CHARACTER_DATA, self.character_data, None, line, column)
                self.tokens.append(token)
            self.character_data = ''

    def next(self):
        size = 16*1024
        while self.index >= len(self.tokens) and not self.final:
            self.tokens = []
            self.index = 0
            data = self.fp.read(size)
            self.final = len(data) < size
            try:
                self.parser.Parse(data, self.final)
            except xml.parsers.expat.ExpatError, e:
                #if e.code == xml.parsers.expat.errors.XML_ERROR_NO_ELEMENTS:
                if e.code == 3:
                    pass
                else:
                    raise e
        if self.index >= len(self.tokens):
            line, column = self.pos()
            token = XmlToken(XML_EOF, None, None, line, column)
        else:
            token = self.tokens[self.index]
            self.index += 1
        return token

    def pos(self):
        return self.parser.CurrentLineNumber, self.parser.CurrentColumnNumber


class XmlTokenMismatch(Exception):

    def __init__(self, expected, found):
        self.expected = expected
        self.found = found

    def __str__(self):
        return '%u:%u: %s expected, %s found' % (self.found.line, self.found.column, str(self.expected), str(self.found))


class XmlParser(Parser):
    """Base XML document parser."""

    def __init__(self, fp):
        Parser.__init__(self)
        self.tokenizer = XmlTokenizer(fp)
        self.consume()

    def consume(self):
        self.token = self.tokenizer.next()

    def match_element_start(self, name):
        return self.token.type == XML_ELEMENT_START and self.token.name_or_data == name

    def match_element_end(self, name):
        return self.token.type == XML_ELEMENT_END and self.token.name_or_data == name

    def element_start(self, name):
        while self.token.type == XML_CHARACTER_DATA:
            self.consume()
        if self.token.type != XML_ELEMENT_START:
            raise XmlTokenMismatch(XmlToken(XML_ELEMENT_START, name), self.token)
        if self.token.name_or_data != name:
            raise XmlTokenMismatch(XmlToken(XML_ELEMENT_START, name), self.token)
        attrs = self.token.attrs
        self.consume()
        return attrs

    def element_end(self, name):
        while self.token.type == XML_CHARACTER_DATA:
            self.consume()
        if self.token.type != XML_ELEMENT_END:
            raise XmlTokenMismatch(XmlToken(XML_ELEMENT_END, name), self.token)
        if self.token.name_or_data != name:
            raise XmlTokenMismatch(XmlToken(XML_ELEMENT_END, name), self.token)
        self.consume()

    def character_data(self, strip = True):
        data = ''
        while self.token.type == XML_CHARACTER_DATA:
            data += self.token.name_or_data
            self.consume()
        if strip:
            data = data.strip()
        return data


class GprofParser(Parser):
    """Parser for GNU gprof output.

    See also:
    - Chapter "Interpreting gprof's Output" from the GNU gprof manual
      http://sourceware.org/binutils/docs-2.18/gprof/Call-Graph.html#Call-Graph
    - File "cg_print.c" from the GNU gprof source code
      http://sourceware.org/cgi-bin/cvsweb.cgi/~checkout~/src/gprof/cg_print.c?rev=1.12&cvsroot=src
    """

    def __init__(self, fp):
        Parser.__init__(self)
        self.fp = fp
        self.functions = {}
        self.cycles = {}

    def readline(self):
        line = self.fp.readline()
        if not line:
            sys.stderr.write('error: unexpected end of file\n')
            sys.exit(1)
        line = line.rstrip('\r\n')
        return line

    _int_re = re.compile(r'^\d+$')
    _float_re = re.compile(r'^\d+\.\d+$')

    def translate(self, mo):
        """Extract a structure from a match object, while translating the types in the process."""
        attrs = {}
        groupdict = mo.groupdict()
        for name, value in groupdict.iteritems():
            if value is None:
                value = None
            elif self._int_re.match(value):
                value = int(value)
            elif self._float_re.match(value):
                value = float(value)
            attrs[name] = (value)
        return Struct(attrs)

    _cg_header_re = re.compile(
        # original gprof header
        r'^\s+called/total\s+parents\s*$|' +
        r'^index\s+%time\s+self\s+descendents\s+called\+self\s+name\s+index\s*$|' +
        r'^\s+called/total\s+children\s*$|' +
        # GNU gprof header
        r'^index\s+%\s+time\s+self\s+children\s+called\s+name\s*$'
    )

    _cg_ignore_re = re.compile(
        # spontaneous
        r'^\s+<spontaneous>\s*$|'
        # internal calls (such as "mcount")
        r'^.*\((\d+)\)$'
    )

    _cg_primary_re = re.compile(
        r'^\[(?P<index>\d+)\]?' +
        r'\s+(?P<percentage_time>\d+\.\d+)' +
        r'\s+(?P<self>\d+\.\d+)' +
        r'\s+(?P<descendants>\d+\.\d+)' +
        r'\s+(?:(?P<called>\d+)(?:\+(?P<called_self>\d+))?)?' +
        r'\s+(?P<name>\S.*?)' +
        r'(?:\s+<cycle\s(?P<cycle>\d+)>)?' +
        r'\s\[(\d+)\]$'
    )

    _cg_parent_re = re.compile(
        r'^\s+(?P<self>\d+\.\d+)?' +
        r'\s+(?P<descendants>\d+\.\d+)?' +
        r'\s+(?P<called>\d+)(?:/(?P<called_total>\d+))?' +
        r'\s+(?P<name>\S.*?)' +
        r'(?:\s+<cycle\s(?P<cycle>\d+)>)?' +
        r'\s\[(?P<index>\d+)\]$'
    )

    _cg_child_re = _cg_parent_re

    _cg_cycle_header_re = re.compile(
        r'^\[(?P<index>\d+)\]?' +
        r'\s+(?P<percentage_time>\d+\.\d+)' +
        r'\s+(?P<self>\d+\.\d+)' +
        r'\s+(?P<descendants>\d+\.\d+)' +
        r'\s+(?:(?P<called>\d+)(?:\+(?P<called_self>\d+))?)?' +
        r'\s+<cycle\s(?P<cycle>\d+)\sas\sa\swhole>' +
        r'\s\[(\d+)\]$'
    )

    _cg_cycle_member_re = re.compile(
        r'^\s+(?P<self>\d+\.\d+)?' +
        r'\s+(?P<descendants>\d+\.\d+)?' +
        r'\s+(?P<called>\d+)(?:\+(?P<called_self>\d+))?' +
        r'\s+(?P<name>\S.*?)' +
        r'(?:\s+<cycle\s(?P<cycle>\d+)>)?' +
        r'\s\[(?P<index>\d+)\]$'
    )

    _cg_sep_re = re.compile(r'^--+$')

    def parse_function_entry(self, lines):
        parents = []
        children = []

        while True:
            if not lines:
                sys.stderr.write('warning: unexpected end of entry\n')
            line = lines.pop(0)
            if line.startswith('['):
                break

            # read function parent line
            mo = self._cg_parent_re.match(line)
            if not mo:
                if self._cg_ignore_re.match(line):
                    continue
                sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            else:
                parent = self.translate(mo)
                parents.append(parent)

        # read primary line
        mo = self._cg_primary_re.match(line)
        if not mo:
            sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            return
        else:
            function = self.translate(mo)

        while lines:
            line = lines.pop(0)

            # read function subroutine line
            mo = self._cg_child_re.match(line)
            if not mo:
                if self._cg_ignore_re.match(line):
                    continue
                sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            else:
                child = self.translate(mo)
                children.append(child)

        function.parents = parents
        function.children = children

        self.functions[function.index] = function

    def parse_cycle_entry(self, lines):

        # read cycle header line
        line = lines[0]
        mo = self._cg_cycle_header_re.match(line)
        if not mo:
            sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            return
        cycle = self.translate(mo)

        # read cycle member lines
        cycle.functions = []
        for line in lines[1:]:
            mo = self._cg_cycle_member_re.match(line)
            if not mo:
                sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
                continue
            call = self.translate(mo)
            cycle.functions.append(call)

        self.cycles[cycle.cycle] = cycle

    def parse_cg_entry(self, lines):
        if lines[0].startswith("["):
            self.parse_cycle_entry(lines)
        else:
            self.parse_function_entry(lines)

    def parse_cg(self):
        """Parse the call graph."""

        # skip call graph header
        while not self._cg_header_re.match(self.readline()):
            pass
        line = self.readline()
        while self._cg_header_re.match(line):
            line = self.readline()

        # process call graph entries
        entry_lines = []
        while line != '\014': # form feed
            if line and not line.isspace():
                if self._cg_sep_re.match(line):
                    self.parse_cg_entry(entry_lines)
                    entry_lines = []
                else:
                    entry_lines.append(line)
            line = self.readline()

    def parse(self):
        self.parse_cg()
        self.fp.close()

        profile = Profile()
        profile[TIME] = 0.0

        cycles = {}
        for index in self.cycles.iterkeys():
            cycles[index] = Cycle()

        for entry in self.functions.itervalues():
            # populate the function
            function = Function(entry.index, entry.name)
            function[TIME] = entry.self
            if entry.called is not None:
                function[CALLS] = entry.called
            if entry.called_self is not None:
                call = Call(entry.index)
                call[CALLS] = entry.called_self
                function[CALLS] += entry.called_self

            # populate the function calls
            for child in entry.children:
                call = Call(child.index)

                assert child.called is not None
                call[CALLS] = child.called

                if child.index not in self.functions:
                    # NOTE: functions that were never called but were discovered by gprof's
                    # static call graph analysis dont have a call graph entry so we need
                    # to add them here
                    missing = Function(child.index, child.name)
                    function[TIME] = 0.0
                    function[CALLS] = 0
                    profile.add_function(missing)

                function.add_call(call)

            profile.add_function(function)

            if entry.cycle is not None:
                cycles[entry.cycle].add_function(function)

            profile[TIME] = profile[TIME] + function[TIME]

        for cycle in cycles.itervalues():
            profile.add_cycle(cycle)

        # Compute derived events
        profile.validate()
        profile.ratio(TIME_RATIO, TIME)
        profile.call_ratios(CALLS)
        profile.integrate(TOTAL_TIME, TIME)
        profile.ratio(TOTAL_TIME_RATIO, TOTAL_TIME)

        return profile


class OprofileParser(LineParser):
    """Parser for oprofile callgraph output.

    See also:
    - http://oprofile.sourceforge.net/doc/opreport.html#opreport-callgraph
    """

    _fields_re = {
        'samples': r'(?P<samples>\d+)',
        '%': r'(?P<percentage>\S+)',
        'linenr info': r'(?P<source>\(no location information\)|\S+:\d+)',
        'image name': r'(?P<image>\S+(?:\s\(tgid:[^)]*\))?)',
        'app name': r'(?P<application>\S+)',
        'symbol name': r'(?P<symbol>\(no symbols\)|.+?)',
    }

    def __init__(self, infile):
        LineParser.__init__(self, infile)
        self.entries = {}
        self.entry_re = None

    def add_entry(self, callers, function, callees):
        try:
            entry = self.entries[function.id]
        except KeyError:
            self.entries[function.id] = (callers, function, callees)
        else:
            callers_total, function_total, callees_total = entry
            self.update_subentries_dict(callers_total, callers)
            function_total.samples += function.samples
            self.update_subentries_dict(callees_total, callees)

    def update_subentries_dict(self, totals, partials):
        for partial in partials.itervalues():
            try:
                total = totals[partial.id]
            except KeyError:
                totals[partial.id] = partial
            else:
                total.samples += partial.samples

    def parse(self):
        # read lookahead
        self.readline()

        self.parse_header()
        while self.lookahead():
            self.parse_entry()

        profile = Profile()

        reverse_call_samples = {}

        # populate the profile
        profile[SAMPLES] = 0
        for _callers, _function, _callees in self.entries.itervalues():
            function = Function(_function.id, _function.name)
            function[SAMPLES] = _function.samples
            profile.add_function(function)
            profile[SAMPLES] += _function.samples

            if _function.application:
                function[PROCESS] = os.path.basename(_function.application)
            if _function.image:
                function[MODULE] = os.path.basename(_function.image)

            total_callee_samples = 0
            for _callee in _callees.itervalues():
                total_callee_samples += _callee.samples

            for _callee in _callees.itervalues():
                if not _callee.self:
                    call = Call(_callee.id)
                    call[SAMPLES2] = _callee.samples
                    function.add_call(call)

        # compute derived data
        profile.validate()
        profile.find_cycles()
        profile.ratio(TIME_RATIO, SAMPLES)
        profile.call_ratios(SAMPLES2)
        profile.integrate(TOTAL_TIME_RATIO, TIME_RATIO)

        return profile

    def parse_header(self):
        while not self.match_header():
            self.consume()
        line = self.lookahead()
        fields = re.split(r'\s\s+', line)
        entry_re = r'^\s*' + r'\s+'.join([self._fields_re[field] for field in fields]) + r'(?P<self>\s+\[self\])?$'
        self.entry_re = re.compile(entry_re)
        self.skip_separator()

    def parse_entry(self):
        callers = self.parse_subentries()
        if self.match_primary():
            function = self.parse_subentry()
            if function is not None:
                callees = self.parse_subentries()
                self.add_entry(callers, function, callees)
        self.skip_separator()

    def parse_subentries(self):
        subentries = {}
        while self.match_secondary():
            subentry = self.parse_subentry()
            subentries[subentry.id] = subentry
        return subentries

    def parse_subentry(self):
        entry = Struct()
        line = self.consume()
        mo = self.entry_re.match(line)
        if not mo:
            raise ParseError('failed to parse', line)
        fields = mo.groupdict()
        entry.samples = int(fields.get('samples', 0))
        entry.percentage = float(fields.get('percentage', 0.0))
        if 'source' in fields and fields['source'] != '(no location information)':
            source = fields['source']
            filename, lineno = source.split(':')
            entry.filename = filename
            entry.lineno = int(lineno)
        else:
            source = ''
            entry.filename = None
            entry.lineno = None
        entry.image = fields.get('image', '')
        entry.application = fields.get('application', '')
        if 'symbol' in fields and fields['symbol'] != '(no symbols)':
            entry.symbol = fields['symbol']
        else:
            entry.symbol = ''
        if entry.symbol.startswith('"') and entry.symbol.endswith('"'):
            entry.symbol = entry.symbol[1:-1]
        entry.id = ':'.join((entry.application, entry.image, source, entry.symbol))
        entry.self = fields.get('self', None) != None
        if entry.self:
            entry.id += ':self'
        if entry.symbol:
            entry.name = entry.symbol
        else:
            entry.name = entry.image
        return entry

    def skip_separator(self):
        while not self.match_separator():
            self.consume()
        self.consume()

    def match_header(self):
        line = self.lookahead()
        return line.startswith('samples')

    def match_separator(self):
        line = self.lookahead()
        return line == '-'*len(line)

    def match_primary(self):
        line = self.lookahead()
        return not line[:1].isspace()

    def match_secondary(self):
        line = self.lookahead()
        return line[:1].isspace()


class SharkParser(LineParser):
    """Parser for MacOSX Shark output.

    Author: tom@dbservice.com
    """

    def __init__(self, infile):
        LineParser.__init__(self, infile)
        self.stack = []
        self.entries = {}

    def add_entry(self, function):
        try:
            entry = self.entries[function.id]
        except KeyError:
            self.entries[function.id] = (function, { })
        else:
            function_total, callees_total = entry
            function_total.samples += function.samples

    def add_callee(self, function, callee):
        func, callees = self.entries[function.id]
        try:
            entry = callees[callee.id]
        except KeyError:
            callees[callee.id] = callee
        else:
            entry.samples += callee.samples

    def parse(self):
        self.readline()
        self.readline()
        self.readline()
        self.readline()

        match = re.compile(r'(?P<prefix>[|+ ]*)(?P<samples>\d+), (?P<symbol>[^,]+), (?P<image>.*)')

        while self.lookahead():
            line = self.consume()
            mo = match.match(line)
            if not mo:
                raise ParseError('failed to parse', line)

            fields = mo.groupdict()
            prefix = len(fields.get('prefix', 0)) / 2 - 1

            symbol = str(fields.get('symbol', 0))
            image = str(fields.get('image', 0))

            entry = Struct()
            entry.id = ':'.join([symbol, image])
            entry.samples = int(fields.get('samples', 0))

            entry.name = symbol
            entry.image = image

            # adjust the callstack
            if prefix < len(self.stack):
                del self.stack[prefix:]

            if prefix == len(self.stack):
                self.stack.append(entry)

            # if the callstack has had an entry, it's this functions caller
            if prefix > 0:
                self.add_callee(self.stack[prefix - 1], entry)

            self.add_entry(entry)

        profile = Profile()
        profile[SAMPLES] = 0
        for _function, _callees in self.entries.itervalues():
            function = Function(_function.id, _function.name)
            function[SAMPLES] = _function.samples
            profile.add_function(function)
            profile[SAMPLES] += _function.samples

            if _function.image:
                function[MODULE] = os.path.basename(_function.image)

            for _callee in _callees.itervalues():
                call = Call(_callee.id)
                call[SAMPLES] = _callee.samples
                function.add_call(call)

        # compute derived data
        profile.validate()
        profile.find_cycles()
        profile.ratio(TIME_RATIO, SAMPLES)
        profile.call_ratios(SAMPLES)
        profile.integrate(TOTAL_TIME_RATIO, TIME_RATIO)

        return profile


class AQtimeTable:

    def __init__(self, name, fields):
        self.name = name

        self.fields = fields
        self.field_column = {}
        for column in range(len(fields)):
            self.field_column[fields[column]] = column
        self.rows = []

    def __len__(self):
        return len(self.rows)

    def __iter__(self):
        for values, children in self.rows:
            fields = {}
            for name, value in zip(self.fields, values):
                fields[name] = value
            children = dict([(child.name, child) for child in children])
            yield fields, children
        raise StopIteration

    def add_row(self, values, children=()):
        self.rows.append((values, children))


class AQtimeParser(XmlParser):

    def __init__(self, stream):
        XmlParser.__init__(self, stream)
        self.tables = {}

    def parse(self):
        self.element_start('AQtime_Results')
        self.parse_headers()
        results = self.parse_results()
        self.element_end('AQtime_Results')
        return self.build_profile(results)

    def parse_headers(self):
        self.element_start('HEADERS')
        while self.token.type == XML_ELEMENT_START:
            self.parse_table_header()
        self.element_end('HEADERS')

    def parse_table_header(self):
        attrs = self.element_start('TABLE_HEADER')
        name = attrs['NAME']
        id = int(attrs['ID'])
        field_types = []
        field_names = []
        while self.token.type == XML_ELEMENT_START:
            field_type, field_name = self.parse_table_field()
            field_types.append(field_type)
            field_names.append(field_name)
        self.element_end('TABLE_HEADER')
        self.tables[id] = name, field_types, field_names

    def parse_table_field(self):
        attrs = self.element_start('TABLE_FIELD')
        type = attrs['TYPE']
        name = self.character_data()
        self.element_end('TABLE_FIELD')
        return type, name

    def parse_results(self):
        self.element_start('RESULTS')
        table = self.parse_data()
        self.element_end('RESULTS')
        return table

    def parse_data(self):
        rows = []
        attrs = self.element_start('DATA')
        table_id = int(attrs['TABLE_ID'])
        table_name, field_types, field_names = self.tables[table_id]
        table = AQtimeTable(table_name, field_names)
        while self.token.type == XML_ELEMENT_START:
            row, children = self.parse_row(field_types)
            table.add_row(row, children)
        self.element_end('DATA')
        return table

    def parse_row(self, field_types):
        row = [None]*len(field_types)
        children = []
        self.element_start('ROW')
        while self.token.type == XML_ELEMENT_START:
            if self.token.name_or_data == 'FIELD':
                field_id, field_value = self.parse_field(field_types)
                row[field_id] = field_value
            elif self.token.name_or_data == 'CHILDREN':
                children = self.parse_children()
            else:
                raise XmlTokenMismatch("<FIELD ...> or <CHILDREN ...>", self.token)
        self.element_end('ROW')
        return row, children

    def parse_field(self, field_types):
        attrs = self.element_start('FIELD')
        id = int(attrs['ID'])
        type = field_types[id]
        value = self.character_data()
        if type == 'Integer':
            value = int(value)
        elif type == 'Float':
            value = float(value)
        elif type == 'Address':
            value = int(value)
        elif type == 'String':
            pass
        else:
            assert False
        self.element_end('FIELD')
        return id, value

    def parse_children(self):
        children = []
        self.element_start('CHILDREN')
        while self.token.type == XML_ELEMENT_START:
            table = self.parse_data()
            assert table.name not in children
            children.append(table)
        self.element_end('CHILDREN')
        return children

    def build_profile(self, results):
        assert results.name == 'Routines'
        profile = Profile()
        profile[TIME] = 0.0
        for fields, tables in results:
            function = self.build_function(fields)
            children = tables['Children']
            for fields, _ in children:
                call = self.build_call(fields)
                function.add_call(call)
            profile.add_function(function)
            profile[TIME] = profile[TIME] + function[TIME]
        profile[TOTAL_TIME] = profile[TIME]
        profile.ratio(TOTAL_TIME_RATIO, TOTAL_TIME)
        return profile

    def build_function(self, fields):
        function = Function(self.build_id(fields), self.build_name(fields))
        function[TIME] = fields['Time']
        function[TOTAL_TIME] = fields['Time with Children']
        #function[TIME_RATIO] = fields['% Time']/100.0
        #function[TOTAL_TIME_RATIO] = fields['% with Children']/100.0
        return function

    def build_call(self, fields):
        call = Call(self.build_id(fields))
        call[TIME] = fields['Time']
        call[TOTAL_TIME] = fields['Time with Children']
        #call[TIME_RATIO] = fields['% Time']/100.0
        #call[TOTAL_TIME_RATIO] = fields['% with Children']/100.0
        return call

    def build_id(self, fields):
        return ':'.join([fields['Module Name'], fields['Unit Name'], fields['Routine Name']])

    def build_name(self, fields):
        # TODO: use more fields
        return fields['Routine Name']


class PstatsParser:
    """Parser python profiling statistics saved with te pstats module."""

    def __init__(self, *filename):
        import pstats
        try:
            self.stats = pstats.Stats(*filename)
        except ValueError:
            import hotshot.stats
            self.stats = hotshot.stats.load(filename[0])
        self.profile = Profile()
        self.function_ids = {}

    def get_function_name(self, (filename, line, name)):
        module = os.path.splitext(filename)[0]
        module = os.path.basename(module)
        return "%s:%d:%s" % (module, line, name)

    def get_function(self, key):
        try:
            id = self.function_ids[key]
        except KeyError:
            id = len(self.function_ids)
            name = self.get_function_name(key)
            function = Function(id, name)
            self.profile.functions[id] = function
            self.function_ids[key] = id
        else:
            function = self.profile.functions[id]
        return function

    def parse(self):
        self.profile[TIME] = 0.0
        self.profile[TOTAL_TIME] = self.stats.total_tt
        for fn, (cc, nc, tt, ct, callers) in self.stats.stats.iteritems():
            callee = self.get_function(fn)
            callee[CALLS] = nc
            callee[TOTAL_TIME] = ct
            callee[TIME] = tt
            self.profile[TIME] += tt
            self.profile[TOTAL_TIME] = max(self.profile[TOTAL_TIME], ct)
            for fn, value in callers.iteritems():
                caller = self.get_function(fn)
                call = Call(callee.id)
                if isinstance(value, tuple):
                    for i in xrange(0, len(value), 4):
                        nc, cc, tt, ct = value[i:i+4]
                        if CALLS in call:
                            call[CALLS] += cc
                        else:
                            call[CALLS] = cc

                        if TOTAL_TIME in call:
                            call[TOTAL_TIME] += ct
                        else:
                            call[TOTAL_TIME] = ct

                else:
                    call[CALLS] = value
                    call[TOTAL_TIME] = ratio(value, nc)*ct

                caller.add_call(call)
        #self.stats.print_stats()
        #self.stats.print_callees()

        # Compute derived events
        self.profile.validate()
        self.profile.ratio(TIME_RATIO, TIME)
        self.profile.ratio(TOTAL_TIME_RATIO, TOTAL_TIME)

        return self.profile


class Theme:

    def __init__(self,
            bgcolor = (0.0, 0.0, 1.0),
            mincolor = (0.0, 0.0, 0.0),
            maxcolor = (0.0, 0.0, 1.0),
            fontname = "Arial",
            minfontsize = 10.0,
            maxfontsize = 10.0,
            minpenwidth = 0.5,
            maxpenwidth = 4.0,
            gamma = 2.2):
        self.bgcolor = bgcolor
        self.mincolor = mincolor
        self.maxcolor = maxcolor
        self.fontname = fontname
        self.minfontsize = minfontsize
        self.maxfontsize = maxfontsize
        self.minpenwidth = minpenwidth
        self.maxpenwidth = maxpenwidth
        self.gamma = gamma

    def graph_bgcolor(self):
        return self.hsl_to_rgb(*self.bgcolor)

    def graph_fontname(self):
        return self.fontname

    def graph_fontsize(self):
        return self.minfontsize

    def node_bgcolor(self, weight):
        return self.color(weight)

    def node_fgcolor(self, weight):
        return self.graph_bgcolor()

    def node_fontsize(self, weight):
        return self.fontsize(weight)

    def edge_color(self, weight):
        return self.color(weight)

    def edge_fontsize(self, weight):
        return self.fontsize(weight)

    def edge_penwidth(self, weight):
        return max(weight*self.maxpenwidth, self.minpenwidth)

    def edge_arrowsize(self, weight):
        return 0.5 * math.sqrt(self.edge_penwidth(weight))

    def fontsize(self, weight):
        return max(weight**2 * self.maxfontsize, self.minfontsize)

    def color(self, weight):
        weight = min(max(weight, 0.0), 1.0)

        hmin, smin, lmin = self.mincolor
        hmax, smax, lmax = self.maxcolor

        h = hmin + weight*(hmax - hmin)
        s = smin + weight*(smax - smin)
        l = lmin + weight*(lmax - lmin)

        return self.hsl_to_rgb(h, s, l)

    def hsl_to_rgb(self, h, s, l):
        """Convert a color from HSL color-model to RGB.

        See also:
        - http://www.w3.org/TR/css3-color/#hsl-color
        """

        h = h % 1.0
        s = min(max(s, 0.0), 1.0)
        l = min(max(l, 0.0), 1.0)

        if l <= 0.5:
            m2 = l*(s + 1.0)
        else:
            m2 = l + s - l*s
        m1 = l*2.0 - m2
        r = self._hue_to_rgb(m1, m2, h + 1.0/3.0)
        g = self._hue_to_rgb(m1, m2, h)
        b = self._hue_to_rgb(m1, m2, h - 1.0/3.0)

        # Apply gamma correction
        r **= self.gamma
        g **= self.gamma
        b **= self.gamma

        return (r, g, b)

    def _hue_to_rgb(self, m1, m2, h):
        if h < 0.0:
            h += 1.0
        elif h > 1.0:
            h -= 1.0
        if h*6 < 1.0:
            return m1 + (m2 - m1)*h*6.0
        elif h*2 < 1.0:
            return m2
        elif h*3 < 2.0:
            return m1 + (m2 - m1)*(2.0/3.0 - h)*6.0
        else:
            return m1


TEMPERATURE_COLORMAP = Theme(
    mincolor = (2.0/3.0, 0.80, 0.25), # dark blue
    maxcolor = (0.0, 1.0, 0.5), # satured red
    gamma = 1.0
)

PINK_COLORMAP = Theme(
    mincolor = (0.0, 1.0, 0.90), # pink
    maxcolor = (0.0, 1.0, 0.5), # satured red
)

GRAY_COLORMAP = Theme(
    mincolor = (0.0, 0.0, 0.85), # light gray
    maxcolor = (0.0, 0.0, 0.0), # black
)

BW_COLORMAP = Theme(
    minfontsize = 8.0,
    maxfontsize = 24.0,
    mincolor = (0.0, 0.0, 0.0), # black
    maxcolor = (0.0, 0.0, 0.0), # black
    minpenwidth = 0.1,
    maxpenwidth = 8.0,
)


class DotWriter:
    """Writer for the DOT language.

    See also:
    - "The DOT Language" specification
      http://www.graphviz.org/doc/info/lang.html
    """

    def __init__(self, fp):
        self.fp = fp

    def graph(self, profile, theme):
        self.begin_graph()

        fontname = theme.graph_fontname()

        self.attr('graph', fontname=fontname, ranksep=0.25, nodesep=0.125)
        self.attr('node', fontname=fontname, shape="box", style="filled,rounded", fontcolor="white", width=0, height=0)
        self.attr('edge', fontname=fontname)

        for function in profile.functions.itervalues():
            labels = []
            for event in PROCESS, MODULE:
                if event in function.events:
                    label = event.format(function[event])
                    labels.append(label)
            labels.append(function.name)
            for event in TOTAL_TIME_RATIO, TIME_RATIO, CALLS:
                if event in function.events:
                    label = event.format(function[event])
                    labels.append(label)

            try:
                weight = function[PRUNE_RATIO]
            except UndefinedEvent:
                weight = 0.0

            label = '\n'.join(labels)
            self.node(function.id,
                label = label,
                color = self.color(theme.node_bgcolor(weight)),
                fontcolor = self.color(theme.node_fgcolor(weight)),
                fontsize = "%.2f" % theme.node_fontsize(weight),
            )

            for call in function.calls.itervalues():
                callee = profile.functions[call.callee_id]

                labels = []
                for event in TOTAL_TIME_RATIO, CALLS:
                    if event in call.events:
                        label = event.format(call[event])
                        labels.append(label)

                try:
                    weight = call[PRUNE_RATIO]
                except UndefinedEvent:
                    try:
                        weight = callee[PRUNE_RATIO]
                    except UndefinedEvent:
                        weight = 0.0

                label = '\n'.join(labels)

                self.edge(function.id, call.callee_id,
                    label = label,
                    color = self.color(theme.edge_color(weight)),
                    fontcolor = self.color(theme.edge_color(weight)),
                    fontsize = "%.2f" % theme.edge_fontsize(weight),
                    penwidth = "%.2f" % theme.edge_penwidth(weight),
                    labeldistance = "%.2f" % theme.edge_penwidth(weight),
                    arrowsize = "%.2f" % theme.edge_arrowsize(weight),
                )

        self.end_graph()

    def begin_graph(self):
        self.write('digraph {\n')

    def end_graph(self):
        self.write('}\n')

    def attr(self, what, **attrs):
        self.write("\t")
        self.write(what)
        self.attr_list(attrs)
        self.write(";\n")

    def node(self, node, **attrs):
        self.write("\t")
        self.id(node)
        self.attr_list(attrs)
        self.write(";\n")

    def edge(self, src, dst, **attrs):
        self.write("\t")
        self.id(src)
        self.write(" -> ")
        self.id(dst)
        self.attr_list(attrs)
        self.write(";\n")

    def attr_list(self, attrs):
        if not attrs:
            return
        self.write(' [')
        first = True
        for name, value in attrs.iteritems():
            if first:
                first = False
            else:
                self.write(", ")
            self.id(name)
            self.write('=')
            self.id(value)
        self.write(']')

    def id(self, id):
        if isinstance(id, (int, float)):
            s = str(id)
        elif isinstance(id, basestring):
            if id.isalnum():
                s = id
            else:
                s = self.escape(id)
        else:
            raise TypeError
        self.write(s)

    def color(self, (r, g, b)):

        def float2int(f):
            if f <= 0.0:
                return 0
            if f >= 1.0:
                return 255
            return int(255.0*f + 0.5)

        return "#" + "".join(["%02x" % float2int(c) for c in (r, g, b)])

    def escape(self, s):
        s = s.encode('utf-8')
        s = s.replace('\\', r'\\')
        s = s.replace('\n', r'\n')
        s = s.replace('\t', r'\t')
        s = s.replace('"', r'\"')
        return '"' + s + '"'

    def write(self, s):
        self.fp.write(s)


class Main:
    """Main program."""

    themes = {
            "color": TEMPERATURE_COLORMAP,
            "pink": PINK_COLORMAP,
            "gray": GRAY_COLORMAP,
            "bw": BW_COLORMAP,
    }

    def main(self):
        """Main program."""

        parser = optparse.OptionParser(
            usage="\n\t%prog [options] [file] ...",
            version="%%prog %s" % __version__)
        parser.add_option(
            '-o', '--output', metavar='FILE',
            type="string", dest="output",
            help="output filename [stdout]")
        parser.add_option(
            '-n', '--node-thres', metavar='PERCENTAGE',
            type="float", dest="node_thres", default=0.5,
            help="eliminate nodes below this threshold [default: %default]")
        parser.add_option(
            '-e', '--edge-thres', metavar='PERCENTAGE',
            type="float", dest="edge_thres", default=0.1,
            help="eliminate edges below this threshold [default: %default]")
        parser.add_option(
            '-f', '--format',
            type="choice", choices=('prof', 'oprofile', 'pstats', 'shark', 'aqtime'),
            dest="format", default="prof",
            help="profile format: prof, oprofile, shark, aqtime, or pstats [default: %default]")
        parser.add_option(
            '-c', '--colormap',
            type="choice", choices=('color', 'pink', 'gray', 'bw'),
            dest="theme", default="color",
            help="color map: color, pink, gray, or bw [default: %default]")
        parser.add_option(
            '-s', '--strip',
            action="store_true",
            dest="strip", default=False,
            help="strip function parameters, template parameters, and const modifiers from demangled C++ function names")
        parser.add_option(
            '-w', '--wrap',
            action="store_true",
            dest="wrap", default=False,
            help="wrap function names")
        (self.options, self.args) = parser.parse_args(sys.argv[1:])

        if len(self.args) > 1 and self.options.format != 'pstats':
            parser.error('incorrect number of arguments')

        try:
            self.theme = self.themes[self.options.theme]
        except KeyError:
            parser.error('invalid colormap \'%s\'' % self.options.theme)

        if self.options.format == 'prof':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = GprofParser(fp)
        elif self.options.format == 'oprofile':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = OprofileParser(fp)
        elif self.options.format == 'pstats':
            if not self.args:
                parser.error('at least a file must be specified for pstats input')
            parser = PstatsParser(*self.args)
        elif self.options.format == 'shark':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = SharkParser(fp)
        elif self.options.format == 'aqtime':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = AQtimeParser(fp)
        else:
            parser.error('invalid format \'%s\'' % self.options.format)

        self.profile = parser.parse()

        if self.options.output is None:
            self.output = sys.stdout
        else:
            self.output = open(self.options.output, 'wt')

        self.write_graph()

    _parenthesis_re = re.compile(r'\([^()]*\)')
    _angles_re = re.compile(r'<[^<>]*>')
    _const_re = re.compile(r'\s+const$')

    def strip_function_name(self, name):
        """Remove extraneous information from C++ demangled function names."""

        # Strip function parameters from name by recursively removing paired parenthesis
        while True:
            name, n = self._parenthesis_re.subn('', name)
            if not n:
                break

        # Strip const qualifier
        name = self._const_re.sub('', name)

        # Strip template parameters from name by recursively removing paired angles
        while True:
            name, n = self._angles_re.subn('', name)
            if not n:
                break

        return name

    def wrap_function_name(self, name):
        """Split the function name on multiple lines."""

        if len(name) > 32:
            ratio = 2.0/3.0
            height = max(int(len(name)/(1.0 - ratio) + 0.5), 1)
            width = max(len(name)/height, 32)
            # TODO: break lines in symbols
            name = textwrap.fill(name, width, break_long_words=False)

        # Take away spaces
        name = name.replace(", ", ",")
        name = name.replace("> >", ">>")
        name = name.replace("> >", ">>") # catch consecutive

        return name

    def compress_function_name(self, name):
        """Compress function name according to the user preferences."""

        if self.options.strip:
            name = self.strip_function_name(name)

        if self.options.wrap:
            name = self.wrap_function_name(name)

        # TODO: merge functions with same resulting name

        return name

    def write_graph(self):
        dot = DotWriter(self.output)
        profile = self.profile
        profile.prune(self.options.node_thres/100.0, self.options.edge_thres/100.0)

        for function in profile.functions.itervalues():
            function.name = self.compress_function_name(function.name)

        dot.graph(profile, self.theme)


if __name__ == '__main__':
    Main().main()

########NEW FILE########
__FILENAME__ = pavement
# -*- coding: utf-8 -*-
import os
import re
import sys

from paver.easy import *
from paver.setuputils import setup, find_packages

ROOT = path.getcwd()
sys.path.insert(0, ROOT) # use firepython from current folder

from firepython._setup_common import SETUP_ARGS

BUILD_DIR = ROOT/'build'
DIST_DIR = ROOT/'dist'
FPY = ROOT/'firepython'
FPY_EGG_INFO = ROOT/'FirePython.egg-info'
CRUFT = [
    BUILD_DIR,
    DIST_DIR,
    FPY_EGG_INFO,
    ROOT/'paver-minilib.zip',
]
API_VERSION = re.compile(r'<em:version>([^<]*)<\/em:version>')
PY_API_VERSION_DEF_RE = re.compile('__api_version__ = [\'"][^\'"]+[\'"]')
PY_API_VERSION_DEF = '__api_version__ = \'%s\''


SETUP_ARGS['packages'] = find_packages(exclude=['tests'])
setup(**SETUP_ARGS)


@task
@needs(['sdist'])
def pypi():
    """Update PyPI index and upload library sources"""
    sh('python setup.py register')
    sh('python setup.py sdist --formats=gztar,bztar,zip upload')

@task
def clean():
    """Clean up generated cruft"""
    for cruft_path in CRUFT:
        if cruft_path.isfile():
            cruft_path.remove()
        elif cruft_path.isdir():
            cruft_path.rmtree()


@task
@needs(['minilib', 'distutils.command.sdist'])
def sdist():
    """Combines paver minilib with setuptools' sdist"""
    pass


_TESTS_INSTALL_PKG = """\
    Tests require `%(mod)s`.
    Please `easy_install` or `pip install` the `%(pkg)s` package'
"""

@task
def _pretest_check():
    had_fail = False

    for mod, pkg in (('mock', 'Mock'), ('webtest', 'WebTest')):
        try:
            import mock
        except ImportError:
            info(_TESTS_INSTALL_PKG % dict(mod=mod, pkg=pkg))
            had_fail = True

    if had_fail:
        raise ImportError


@task
@needs(['_pretest_check', 'setuptools.command.test'])
def test():
    """make sure we have test dependencies, possibly alert user
    about what to do to resolve, then run setuptools' `test`
    """
    pass


@task
def testall():
    """run *all* of the tests (requires nose)"""
    try:
        import nose
    except ImportError:
        info(_TESTS_INSTALL_PKG % dict(mod='nose', pkg='nose'))
        raise

    args = [
        'nosetests',
        '-i',
        '^itest',
        '-v',
        ROOT/'tests',
        '--with-coverage',
        '--cover-package',
        'firepython',
    ]
    nose.run(argv=args)

########NEW FILE########
__FILENAME__ = itest_middleware
from StringIO import StringIO
import nose.tools as NT

from wsgiref.simple_server import demo_app
from paste.fixture import TestApp

import firepython as FPY
import firepython.utils as FU
import firepython._const as FC
import firepython.middleware as FM

try:
    import gprof2dot
except ImportError:
    gprof2dot = None


def test_middleware():
    app = get_app()
    fp = app.app

    yield NT.assert_equal, 'snarf', fp._password, "_password set"
    yield NT.assert_equal, 'itest', fp._logger_name, "_logger_name set"
    yield NT.assert_equal, True, fp._check_agent, "_check_agent set"

    real_stringio = FM.StringIO
    FM.StringIO = MonkeyPatchStringIO
    FM.StringIO.writebuf[:] = []

    filtered_req = app.get('/', extra_environ=get_filterable_env())

    if gprof2dot:
        yield NT.assert_true, bool(FM.StringIO.writebuf), \
            "filtered request writes to StringIO instance"

    FM.StringIO = real_stringio


def get_app():
    app = FM.FirePythonWSGI(demo_app, password='snarf', logger_name='itest')
    app = TestApp(app)
    return app


def get_filterable_env():
    env = {}
    env[FC.FIRELOGGER_PROFILER_ENABLED_HEADER] = 'yes'
    env[FC.FIRELOGGER_VERSION_HEADER] = FPY.__api_version__
    env[FC.FIRELOGGER_AUTH_HEADER] = FU.get_auth_token('snarf')
    return env


class MonkeyPatchStringIO(StringIO):
    writebuf = []

    def write(self, some_bytes):
        self.writebuf.append(some_bytes)
        StringIO.write(self, some_bytes)
        # ^--- can't use `super` because this is a classobj :(

########NEW FILE########
__FILENAME__ = itest_mini_graphviz
import os
from hashlib import md5

from nose import SkipTest
import nose.tools as NT
import firepython.mini_graphviz as FM


HERE = os.path.dirname(os.path.abspath(__file__))
CLUSTERS_DOT = os.path.join(HERE, 'clusters.dot')
EXPECTED_MD5SUM = 'f889300cc5e22e860ba8e9c28864d1e2'
EXPECTED_MD5SUM_MAC = 'a4925b08632f65aceac09d903a6aa2c5'

def test_mini_graphviz():
    if os.name != 'posix':
        def raiser(exc, msg):
            raise exc(msg)
        yield raiser, SkipTest, 'mini graphviz helper is very much geared ' \
                                'toward linux as it makes use of the `dot` ' \
                                'and `eog` binaries by default'
        raise StopIteration
    mini_graphviz = FM.MiniGraphviz()
    mini_graphviz.viewer = ''
    out_png = mini_graphviz.view_as_png(CLUSTERS_DOT)

    md5sum = md5(open(out_png).read()).hexdigest()
    yield NT.assert_true, EXPECTED_MD5SUM==md5sum or EXPECTED_MD5SUM_MAC==md5sum, 'MD5 sum match'

    os.remove(out_png)

########NEW FILE########
__FILENAME__ = itest_paste_integration
import os

from nose import SkipTest
import nose.tools as NT

try:
    from paste.fixture import TestApp
    from paste.deploy import loadapp
except ImportError:
    TestApp = loadapp = None

import firepython as FP
import firepython._const as FPC
import firepython.utils as FPU

try:
    import json
except ImportError:
    import simplejson as json

HERE = os.path.dirname(os.path.abspath(__file__))
INI = os.path.join(HERE, 'test.ini')


def test_paste_integration():
    if None in (TestApp, loadapp):
        def raiser(exc, msg):
            raise exc(msg)
        yield raiser, SkipTest, 'incomplete Paste dependencies, so ' \
                                'not testing Paste integration'
        raise StopIteration
    app = get_app()
    clean_response = app.get('/')
    yield NT.assert_true, bool(clean_response.body)
    yield NT.assert_equal, 1, len(clean_response.headers)

    with_error = app.get('/BORK?error=PLEASE',
                         extra_environ=get_extra_environ(app))
    yield NT.assert_true, len(with_error.headers) >= 226 #TODO improve accuracy
                                                         # of assertion

    firelogger_headers = []
    for assertion in _check_and_gather_headers(with_error,
                                               firelogger_headers):
        yield assertion

    firelogger_headers.sort()
    as_python = _get_headers_as_python(firelogger_headers)
    yield NT.assert_equal, ['logs'], as_python.keys()
    logs = as_python['logs']
    yield NT.assert_equal, 6, len(logs)


def get_app():
    return TestApp('config:%s' % INI)


def get_extra_environ(app):
    ret = {
        FPC.FIRELOGGER_VERSION_HEADER: FP.__api_version__,
    }
    auth_key, auth_value = FPU.get_auth_header(app.app._password)
    ret[auth_key] = auth_value
    return ret


def _check_and_gather_headers(response, out_headers):
    for header, value in response.headers:
        if header.startswith('Fire'):
            index = int(header.split('-')[-1])
            out_headers.append((index, value))
            match = bool(FPC.FIRELOGGER_RESPONSE_HEADER.match(header))
            yield NT.assert_true, match, "header is of correct format"


def _get_headers_as_python(headers):
    decoded = _get_headers_as_string(headers)
    as_python = json.loads(decoded)
    return as_python


def _get_headers_as_string(headers):
    decoded = _get_headers_as_base64(headers).decode('base64')
    return decoded


def _get_headers_as_base64(headers):
    return ''.join([header[1] for header in headers])


EXPECTED_RECORD_KEYS = [
    u'args',
    u'exc_frames',
    u'exc_info',
    u'exc_text',
    u'level',
    u'lineno',
    u'message',
    u'name',
    u'pathname',
    u'process',
    u'template',
    u'thread',
    u'threadName',
    u'time',
    u'timestamp',
]

########NEW FILE########
__FILENAME__ = test_basic
import nose.tools as NT


IMPORT_MODS = [
    'firepython',
    'firepython.utils',
    'firepython.middleware',
    'firepython.handlers',
    'firepython._const',
    'firepython._setup_common',
    'firepython.demo',
    'firepython.demo.app',
    'firepython.demo._body',
]


def test_can_import_everything_okay_and_dunder_alls_are_good():
    for mod in IMPORT_MODS:
        imported = __import__(mod, {}, {}, mod.split('.'))

        yield NT.assert_true, bool(imported), \
            "module %s imports okay" % mod

        for member in getattr(imported, '__all__', []):
            yield NT.assert_true, hasattr(imported, member), \
                "module %s has attr %s" % (imported, member)

########NEW FILE########
__FILENAME__ = test_utils
import nose.tools as NT
import mock

import firepython._const as CONST
import firepython.utils as FU


def test_tolerant_json_encoder_strs_on_default():
    encoder = FU.TolerantJSONEncoder()
    yield NT.assert_equal, "{'ho': 'hum'}", encoder.default({'ho': 'hum'})
    yield NT.assert_equal, '[9, 8, 7, 6]', encoder.default([9, 8, 7, 6])


def test_json_encode():
    real_json = FU.json
    FU.json = mock.Mock()
    FU.json.dumps = mock.Mock()

    in_data = {'foo': 'bar', 'ham': 9000}
    FU.json_encode(in_data)
    yield NT.assert_equal, [((in_data,), dict(cls=FU.TolerantJSONEncoder))], \
                           FU.json.dumps.call_args_list

    FU.json = real_json


def test_get_version_header():
    ret = FU.get_version_header('bork')
    yield NT.assert_equal, EXPECTED_VERSION_HEADER, ret


def test_get_auth_token():
    ret = FU.get_auth_token('fashizzle')
    yield NT.assert_equal, EXPECTED_AUTH_TOK, ret


EXPECTED_VERSION_HEADER = (CONST.FIRELOGGER_VERSION_HEADER, 'bork')
EXPECTED_AUTH_TOK = 'c5d00db3f939c1cc523f57d67e5cc319'

########NEW FILE########
