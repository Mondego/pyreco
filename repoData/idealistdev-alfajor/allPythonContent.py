__FILENAME__ = apiclient
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""A low-level HTTP client suitable for testing APIs."""
import copy
from cStringIO import StringIO
import dummy_threading
from cookielib import DefaultCookiePolicy
from logging import DEBUG, getLogger
import mimetypes
from urllib import urlencode
from urlparse import urlparse, urlunparse
from wsgiref.util import request_uri

from werkzeug import BaseResponse, Headers, create_environ, run_wsgi_app
from werkzeug.test import _TestCookieJar, encode_multipart

from alfajor.utilities import eval_dotted_path
from alfajor._compat import json_loads as loads


logger = getLogger(__name__)

_json_content_types = set([
    'application/json',
    'application/x-javascript',
    'text/javascript',
    'text/x-javascript',
    'text/x-json',
    ])


class WSGIClientManager(object):
    """Lifecycle manager for global api clients."""

    def __init__(self, frontend_name, backend_config, runner_options):
        self.config = backend_config

    def create(self):
        from alfajor.apiclient import APIClient

        entry_point = self.config['server-entry-point']
        app = eval_dotted_path(entry_point)

        base_url = self.config.get('base_url')
        logger.debug("Created in-process WSGI api client rooted at %s.",
                     base_url)
        return APIClient(app, base_url=base_url)

    def destroy(self):
        logger.debug("Destroying in-process WSGI api client.")


class APIClient(object):

    def __init__(self, application, state=None, base_url=None):
        self.application = application
        self.state = state or _APIClientState(application)
        self.base_url = base_url

    def open(self, path='/', base_url=None, query_string=None, method='GET',
             data=None, input_stream=None, content_type=None,
             content_length=0, errors_stream=None, multithread=False,
             multiprocess=False, run_once=False, environ_overrides=None,
             buffered=True):

        parsed = urlparse(path)
        if parsed.scheme:
            if base_url is None:
                base_url = parsed.scheme + '://' + parsed.netloc
            if query_string is None:
                query_string = parsed.query
            path = parsed.path

        if (input_stream is None and
            data is not None and
            method in ('PUT', 'POST')):
            input_stream, content_length, content_type = \
                self._prep_input(input_stream, data, content_type)

        if base_url is None:
            base_url = self.base_url or self.state.base_url

        environ = create_environ(path, base_url, query_string, method,
                                 input_stream, content_type, content_length,
                                 errors_stream, multithread,
                                 multiprocess, run_once)

        current_state = self.state
        current_state.prepare_environ(environ)
        if environ_overrides:
            environ.update(environ_overrides)

        logger.info("%s %s" % (method, request_uri(environ)))
        rv = run_wsgi_app(self.application, environ, buffered=buffered)

        response = _APIClientResponse(*rv)
        response.state = new_state = current_state.copy()
        new_state.process_response(response, environ)
        return response

    def get(self, *args, **kw):
        """:meth:`open` as a GET request."""
        kw['method'] = 'GET'
        return self.open(*args, **kw)

    def post(self, *args, **kw):
        """:meth:`open` as a POST request."""
        kw['method'] = 'POST'
        return self.open(*args, **kw)

    def head(self, *args, **kw):
        """:meth:`open` as a HEAD request."""
        kw['method'] = 'HEAD'
        return self.open(*args, **kw)

    def put(self, *args, **kw):
        """:meth:`open` as a PUT request."""
        kw['method'] = 'PUT'
        return self.open(*args, **kw)

    def delete(self, *args, **kw):
        """:meth:`open` as a DELETE request."""
        kw['method'] = 'DELETE'
        return self.open(*args, **kw)

    def wrap_file(self, fd, filename=None, mimetype=None):
        """Wrap a file for use in POSTing or PUTing.

        :param fd: a file name or file-like object
        :param filename: file name to send in the HTTP request
        :param mimetype: mime type to send, guessed if not supplied.
        """
        return File(fd, filename, mimetype)

    def _prep_input(self, input_stream, data, content_type):
        if isinstance(data, basestring):
            assert content_type is not None, 'content type required'
        else:
            need_multipart = False
            pairs = []
            debugging = logger.isEnabledFor(DEBUG)
            for key, value in _to_pairs(data):
                if isinstance(value, basestring):
                    if isinstance(value, unicode):
                        value = str(value)
                    if debugging:
                        logger.debug("%r=%r" % (key, value))
                    pairs.append((key, value))
                    continue
                need_multipart = True
                if isinstance(value, tuple):
                    pairs.append((key, File(*value)))
                elif isinstance(value, dict):
                    pairs.append((key, File(**value)))
                elif not isinstance(value, File):
                    pairs.append((key, File(value)))
                else:
                    pairs.append((key, value))
            if need_multipart:
                boundary, data = encode_multipart(pairs)
                if content_type is None:
                    content_type = 'multipart/form-data; boundary=' + \
                        boundary
            else:
                data = urlencode(pairs)
                logger.debug('data: ' + data)
                if content_type is None:
                    content_type = 'application/x-www-form-urlencoded'
        content_length = len(data)
        input_stream = StringIO(data)
        return input_stream, content_length, content_type


class _APIClientResponse(object):
    state = None

    @property
    def client(self):
        """A new client born from this response.

        The client will have access to any cookies that were sent as part
        of this response & send this response's URL as a referrer.

        Each access to this property returns an independent client with its
        own copy of the cookie jar.

        """
        state = self.state
        return APIClient(application=state.application, state=state)

    status_code = BaseResponse.status_code

    @property
    def request_uri(self):
        """The source URI for this response."""
        return request_uri(self.state.source_environ)

    @property
    def is_json(self):
        """True if the response is JSON and the HTTP status was 200."""
        return (self.status_code == 200 and
                self.headers.get('Content-Type', '') in _json_content_types)

    @property
    def json(self):
        """The response parsed as JSON.

        No attempt is made to ensure the response is valid or even looks
        like JSON before parsing.
        """
        return loads(self.response)

    def __init__(self, app_iter, status, headers):
        self.headers = Headers(headers)
        if isinstance(status, (int, long)):
            self.status_code = status  # sets .status as well
        else:
            self.status = status

        if isinstance(app_iter, basestring):
            self.response = app_iter
        else:
            self.response = ''.join(app_iter)
        if 'Content-Length' not in self.headers:
            self.headers['Content-Length'] = len(self.response)


class _APIClientState(object):
    default_base_url = 'http://localhost'

    def __init__(self, application):
        self.application = application
        self.cookie_jar = _CookieJar()
        self.auth = None
        self.referrer = None

    @property
    def base_url(self):
        if not self.referrer:
            return self.default_base_url
        url = urlparse(self.referrer)
        return urlunparse(url[:2] + ('', '', '', ''))

    def copy(self):
        fork = copy.copy(self)
        fork.cookie_jar = self.cookie_jar.copy()
        return fork

    def prepare_environ(self, environ):
        if self.referrer:
            environ['HTTP_REFERER'] = self.referrer
        if len(self.cookie_jar):
            self.cookie_jar.inject_wsgi(environ)
        environ.setdefault('REMOTE_ADDR', '127.0.0.1')

    def process_response(self, response, request_environ):
        headers = response.headers
        if 'Set-Cookie' in headers or 'Set-Cookie2' in headers:
            self.cookie_jar.extract_wsgi(request_environ, headers)
        self.referrer = request_uri(request_environ)
        self.source_environ = request_environ


# lifted from werkzeug 0.4
class File(object):
    """Wraps a file descriptor or any other stream so that `encode_multipart`
    can get the mimetype and filename from it.
    """

    def __init__(self, fd, filename=None, mimetype=None):
        if isinstance(fd, basestring):
            if filename is None:
                filename = fd
            fd = file(fd, 'rb')
            try:
                self.stream = StringIO(fd.read())
            finally:
                fd.close()
        else:
            self.stream = fd
            if filename is None:
                if not hasattr(fd, 'name'):
                    raise ValueError('no filename for provided')
                filename = fd.name
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0]
        self.filename = filename
        self.mimetype = mimetype or 'application/octet-stream'

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.filename)


class _CookieJar(_TestCookieJar):
    """A lock-less, wsgi-friendly CookieJar that can clone itself."""

    def __init__(self, policy=None):
        if policy is None:
            policy = DefaultCookiePolicy()
        self._policy = policy
        self._cookies = {}
        self._cookies_lock = dummy_threading.RLock()

    def copy(self):
        fork = copy.copy(self)
        fork._cookies = copy.deepcopy(self._cookies)
        return fork


# taken from flatland
def _to_pairs(dictlike):
    """Yield (key, value) pairs from any dict-like object.

    Implements an optimized version of the dict.update() definition of
    "dictlike".

    """
    if hasattr(dictlike, 'items'):
        return dictlike.items()
    elif hasattr(dictlike, 'keys'):
        return [(key, dictlike[key]) for key in dictlike.keys()]
    else:
        return [(key, value) for key, value in dictlike]

########NEW FILE########
__FILENAME__ = managers
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Bridges between test runners and functional browsers."""

from logging import getLogger

from alfajor.utilities import ServerSubProcess, eval_dotted_path


logger = getLogger('alfajor')


def _verify_backend_config(config, required_keys):
    missing = [key for key in required_keys if key not in config]
    if not missing:
        return True
    missing_keys = ', '.join(missing)
    raise RuntimeError("Configuration is missing required keys %s" %
                       missing_keys)


class SeleniumManager(object):
    """TODO

    server_url
    cmd
    ping-address
    selenium-server

    """

    def __init__(self, frontend_name, backend_config, runner_options):
        self.browser_type = frontend_name
        self.config = backend_config
        self.runner_options = runner_options
        self.process = None
        self.browser = None
        self.server_url = self._config('server_url', False)
        if not self.server_url:
            raise RuntimeError("'server_url' is a required configuration "
                               "option for the Selenium backend.")

    def _config(self, key, *default):
        override = self.runner_options.get(key)
        if override:
            return override
        if key in self.config:
            return self.config[key]
        if default:
            return default[0]
        raise LookupError(key)

    def create(self):
        from alfajor.browsers.selenium import Selenium

        base_url = self.server_url
        if (self._config('without_server', False) or
            not self._config('cmd', False)):
            logger.debug("Connecting to existing URL %r", base_url)
        else:
            logger.debug("Starting service....")
            self.process = self.start_subprocess()
            logger.debug("Service started.")
        selenium_server = self._config('selenium-server',
                                       'http://localhost:4444')
        self.browser = Selenium(selenium_server, self.browser_type, base_url)
        return self.browser

    def destroy(self):
        if self.browser and self.browser.selenium._session_id:
            try:
                self.browser.selenium.test_complete()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                pass
        if self.process:
            self.process.stop()
        # avoid irritating __del__ exception on interpreter shutdown
        self.process = None
        self.browser = None

    def start_subprocess(self):
        cmd = self._config('cmd')
        ping = self._config('ping-address', None)

        logger.info("Starting server sub process with %s", cmd)
        process = ServerSubProcess(cmd, ping)
        process.start()
        return process


class WSGIManager(object):
    """Lifecycle manager for global WSGI browsers."""

    def __init__(self, frontend_name, backend_config, runner_options):
        self.config = backend_config

    def create(self):
        from alfajor.browsers.wsgi import WSGI

        entry_point = self.config['server-entry-point']
        app = eval_dotted_path(entry_point)

        base_url = self.config.get('base_url')
        logger.debug("Created in-process WSGI browser.")
        return WSGI(app, base_url)

    def destroy(self):
        logger.debug("Destroying in-process WSGI browser.")


class NetworkManager(object):
    """TODO

    server_url
    cmd
    ping-address

    """

    def __init__(self, frontend_name, backend_config, runner_options):
        self.config = backend_config
        self.runner_options = runner_options
        self.process = None
        self.browser = None
        self.server_url = self._config('server_url', False)
        if not self.server_url:
            raise RuntimeError("'server_url' is a required configuration "
                               "option for the Network backend.")

    def _config(self, key, *default):
        override = self.runner_options.get(key)
        if override:
            return override
        if key in self.config:
            return self.config[key]
        if default:
            return default[0]
        raise LookupError(key)

    def create(self):
        from alfajor.browsers.network import Network

        base_url = self.server_url
        if (self._config('without_server', False) or
            not self._config('cmd', False)):
            logger.debug("Connecting to existing URL %r", base_url)
        else:
            logger.debug("Starting service....")
            self.process = self.start_subprocess()
            logger.debug("Service started.")
        self.browser = Network(base_url)
        return self.browser

    def destroy(self):
        if self.process:
            self.process.stop()
        # avoid irritating __del__ exception on interpreter shutdown
        self.process = None
        self.browser = None

    def start_subprocess(self):
        cmd = self._config('cmd')
        ping = self._config('ping-address', None)

        logger.info("Starting server sub process with %s", cmd)
        process = ServerSubProcess(cmd, ping)
        process.start()
        return process


class ZeroManager(object):
    """Lifecycle manager for global Zero browsers."""

    def __init__(self, frontend_name, backend_config, runner_options):
        pass

    def create(self):
        from alfajor.browsers.zero import Zero
        logger.debug("Creating Zero browser.")
        return Zero()

    def destroy(self):
        logger.debug("Destroying Zero browser.")

########NEW FILE########
__FILENAME__ = network
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""A browser backend that talks over a network socket to a web server."""

from __future__ import absolute_import
from cookielib import Cookie, CookieJar
from logging import getLogger
import urllib2
from urllib import urlencode
from urlparse import urljoin
from time import time

from blinker import signal
from werkzeug import Headers

from alfajor.browsers._lxml import DOMMixin, html_parser_for
from alfajor.browsers._waitexpr import WaitExpression
from alfajor.browsers.wsgi import wsgi_elements
from alfajor.utilities import lazy_property
from alfajor._compat import property


__all__ = ['Network']
logger = getLogger('tests.browser')
after_browser_activity = signal('after_browser_activity')
before_browser_activity = signal('before_browser_activity')


class Network(DOMMixin):

    capabilities = [
        'cookies',
        'headers',
        ]

    wait_expression = WaitExpression

    user_agent = {
        'browser': 'network',
        'platform': 'python',
        'version': '1.0',
        }

    def __init__(self, base_url=None):
        # accept additional request headers?  (e.g. user agent)
        self._base_url = base_url
        self.reset()

    def open(self, url, wait_for=None, timeout=0):
        """Open web page at *url*."""
        self._open(url)

    def reset(self):
        self._referrer = None
        self._request_environ = None
        self._cookie_jar = CookieJar()
        self._opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self._cookie_jar)
        )
        self.status_code = 0
        self.status = ''
        self.response = None
        self.location = None
        self.headers = ()

    def wait_for(self, condition, timeout=None):
        pass

    def sync_document(self):
        """The document is always synced."""

    _sync_document = DOMMixin.sync_document

    @property
    def cookies(self):
        if not (self._cookie_jar and self.location):
            return {}
        request = urllib2.Request(self.location)
        policy = self._cookie_jar._policy

        # return ok will only return a cookie if the following attrs are set
        # correctly => # "version", "verifiability", "secure", "expires",
        # "port", "domain"
        return dict((c.name, c.value.strip('"'))
            for c in self._cookie_jar if policy.return_ok(c, request))

    def set_cookie(self, name, value, domain=None, path=None,
                   session=True, expires=None, port=None):
#        Cookie(version, name, value, port, port_specified,
#                 domain, domain_specified, domain_initial_dot,
#                 path, path_specified, secure, expires,
#                 discard, comment, comment_url, rest,
#                 rfc2109=False):

        cookie = Cookie(0, name, value, port, bool(port),
                        domain or '', bool(domain),
                        (domain and domain.startswith('.')),
                        path or '', bool(path), False, expires,
                        session, None, None, {}, False)
        self._cookie_jar.set_cookie(cookie)

    def delete_cookie(self, name, domain=None, path=None):
        try:
            self._cookie_jar.clear(domain, path, name)
        except KeyError:
            pass

    # Internal methods
    @lazy_property
    def _lxml_parser(self):
        return html_parser_for(self, wsgi_elements)

    def _open(self, url, method='GET', data=None, refer=True,
              content_type=None):
        before_browser_activity.send(self)
        open_started = time()

        if data:
            data = urlencode(data)

        url = urljoin(self._base_url, url)
        if method == 'GET':
            if '?' in url:
                url, query_string = url.split('?', 1)
            else:
                query_string = None

            if data:
                query_string = data
            if query_string:
                url = url + '?' + query_string

            request = urllib2.Request(url)
        elif method == 'POST':
            request = urllib2.Request(url, data)
        else:
            raise Exception('Unsupported method: %s' % method)
        if self._referrer and refer:
            request.add_header('Referer', self._referrer)

        logger.info('%s(%s)', url, method)
        request_started = time()

        response = self._opener.open(request)

        request_ended = time()

        self.status_code = response.getcode()
        self.headers = Headers(
            (head.strip().split(': ',1) for head in response.info().headers)
        )
        self._referrer = request.get_full_url()
        self.location = response.geturl()
        self._response = response
        self.response = ''.join(list(response))
        self._sync_document()

        open_ended = time()
        request_time = request_ended - request_started

        logger.info("Fetched %s in %0.3fsec + %0.3fsec browser overhead",
                    url, request_time,
                    open_ended - open_started - request_time)
        after_browser_activity.send(self)


########NEW FILE########
__FILENAME__ = selenium
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Bridge to live web browsers via Selenium RC."""
from __future__ import with_statement

from contextlib import contextmanager
import csv
from cStringIO import StringIO
from functools import partial
from logging import getLogger
import re
import time
from urllib2 import urlopen, Request
from urlparse import urljoin
from warnings import warn

from blinker import signal
from werkzeug import UserAgent, url_encode

from alfajor.browsers._lxml import (
    _append_text_value,
    _group_key_value_pairs,
    DOMElement,
    DOMMixin,
    FormElement,
    InputElement,
    SelectElement,
    TextareaElement,
    _options_xpath,
    html_parser_for,
    )
from alfajor.browsers._waitexpr import SeleniumWaitExpression, WaitExpression
from alfajor.utilities import lazy_property
from alfajor._compat import property


__all__ = ['Selenium']
logger = getLogger('tests.browser')
after_browser_activity = signal('after_browser_activity')
before_browser_activity = signal('before_browser_activity')
_enterable_chars_re = re.compile(r'(\\[a-z]|\\\d+|.)')
csv.register_dialect('cookies', delimiter=';',
                     skipinitialspace=True,
                     quoting=csv.QUOTE_NONE)


class Selenium(DOMMixin):

    capabilities = [
        'cookies',
        'javascript',
        'visibility',
        'selenium',
        ]

    wait_expression = SeleniumWaitExpression

    def __init__(self, server_url, browser_cmd, base_url=None,
                 default_timeout=16000):
        self.selenium = SeleniumRemote(
            server_url, browser_cmd, default_timeout)
        self._base_url = base_url

        self.status_code = 0
        self.status = ''
        self.response = None
        self.headers = {}

    def open(self, url, wait_for='page', timeout=None):
        logger.info('open(%s)', url)
        before_browser_activity.send(self)
        if self._base_url:
            url = urljoin(self._base_url, url)
        if not self.selenium._session_id:
            self.selenium.get_new_browser_session(url)
        # NOTE:err.- selenium's open waits for the page to load before
        # proceeding
        self.selenium.open(url, timeout)
        if wait_for != 'page':
            self.wait_for(wait_for, timeout)
        after_browser_activity.send(self)
        self.sync_document()

    def reset(self):
        self.selenium('deleteAllVisibleCookies')

    @property
    def user_agent(self):
        if not self.selenium._user_agent:
            return dict.fromkeys(('browser', 'platform', 'version'), 'unknown')
        ua = UserAgent(self.selenium._user_agent)
        return {
            'browser': ua.browser,
            'platform': ua.platform,
            'version': ua.version,
            }

    def sync_document(self):
        self.response = '<html>' + self.selenium('getHtmlSource') + '</html>'
        self.__dict__.pop('document', None)

    @property
    def location(self):
        return self.selenium('getLocation')

    def wait_for(self, condition, timeout=None):
        try:
            if not condition:
                return
            if isinstance(condition, WaitExpression):
                condition = u'js:' + unicode(condition)

            if condition == 'duration':
                if timeout:
                    time.sleep(timeout / 1000.0)
                return
            if timeout is None:
                timeout = self.selenium._current_timeout
            if condition == 'page':
                self.selenium('waitForPageToLoad', timeout)
            elif condition == 'ajax':
                js = ('selenium.browserbot.getCurrentWindow()'
                      '.jQuery.active == 0;')
                self.selenium('waitForCondition', js, timeout)
            elif condition.startswith('js:'):
                expr = condition[3:]
                js = ('var window = selenium.browserbot.getCurrentWindow(); ' +
                      expr)
                self.selenium('waitForCondition', js, timeout)
            elif condition.startswith('element:'):
                expr = condition[8:]
                self.selenium.wait_for_element_present(expr, timeout)
            elif condition.startswith('!element:'):
                expr = condition[9:]
                self.selenium.wait_for_element_not_present(expr, timeout)
        except RuntimeError, detail:
            raise AssertionError('Selenium encountered an error:  %s' % detail)

    @property
    def cookies(self):
        """A dictionary of cookie names and values."""
        return self.selenium('getCookie', dict=True)

    def set_cookie(self, name, value, domain=None, path=None, max_age=None,
                   session=None, expires=None, port=None):
        if domain or session or expires or port:
            message = "Selenium Cookies support only path and max_age"
            warn(message, UserWarning)
        cookie_string = '%s=%s' % (name, value)
        options_string = '' if not path else 'path=%s' % path
        self.selenium('createCookie', cookie_string, options_string)

    def delete_cookie(self, name, domain=None, path=None):
        self.selenium('deleteCookie', name, path)

    # temporary...
    def stop(self):
        self.selenium.test_complete()

    @lazy_property
    def _lxml_parser(self):
        return html_parser_for(self, selenium_elements)


class SeleniumRemote(object):

    def __init__(self, server_url, browser_cmd, default_timeout):
        self._server_url = server_url.rstrip('/') + '/selenium-server/driver/'
        self._browser_cmd = browser_cmd
        self._user_agent = None
        self._session_id = None
        self._default_timeout = default_timeout
        self._current_timeout = None

    def get_new_browser_session(self, browser_url, extension_js='', **options):
        opts = ';'.join("%s=%s" % item for item in options.items())
        self._session_id = self('getNewBrowserSession', self._browser_cmd,
                                browser_url, extension_js, opts)
        self.set_timeout(self._default_timeout)
        self._user_agent = self.get_eval('navigator.userAgent')

    getNewBrowserSession = get_new_browser_session

    def test_complete(self):
        self('testComplete')
        self._session_id = None

    testComplete = test_complete

    def __call__(self, command, *args, **kw):
        transform = _transformers[kw.pop('transform', 'unicode')]
        return_list = kw.pop('list', False)
        return_dict = kw.pop('dict', False)
        assert not kw, 'Unknown keyword argument.'

        payload = {'cmd': command, 'sessionId': self._session_id}
        for idx, arg in enumerate(args):
            payload[str(idx + 1)] = arg

        request = Request(self._server_url, url_encode(payload), {
            'Content-Type':
            'application/x-www-form-urlencoded; charset=utf-8'})
        logger.debug('selenium(%s, %r)', command, args)
        response = urlopen(request).read()

        if not response.startswith('OK'):
            raise RuntimeError(response.encode('utf-8'))
        if response == 'OK':
            return

        data = response[3:]
        if return_list:
            rows = list(csv.reader(StringIO(data)))
            return [transform(col) for col in rows[0]]

        elif return_dict:
            rows = list(csv.reader(StringIO(data), 'cookies'))

            if rows:
                return dict(
                    map(lambda x: x.strip('"'), x.split('=')) for x in rows[0])
            else:
                return {}
        else:
            return transform(data)

    def __getattr__(self, key):
        # proxy methods calls through to Selenium, converting
        # python_form to camelCase
        if '_' in key:
            key = toCamelCase(key)
        kw = {}
        if key.startswith('is') or key.startswith('getWhether'):
            kw['transform'] = 'bool'
        elif (key.startswith('get') and
              any(x in key for x in ('Speed', 'Position',
                                     'Height', 'Width',
                                     'Index', 'Count'))):
            kw['transform'] = 'int'
        if key.startswith('get') and key[-1] == 's':
            kw['list'] = True
        return partial(self, key, **kw)

    def set_timeout(self, value):
        # May be a no-op if the current session timeout is the same as the
        # requested value.
        if value is None:
            return
        if value != self._current_timeout:
            self('setTimeout', value)
        self._current_timeout = value

    def open(self, url, timeout=None):
        with self._scoped_timeout(timeout):
            # Workaround for XHR ERROR failure on non-200 responses
            # http://code.google.com/p/selenium/issues/detail?id=408
            self('open', url, 'true')

    def wait_for_element_present(self, expression, timeout=None):
        with self._scoped_timeout(timeout):
            self('waitForElementPresent', expression)

    def wait_for_element_not_present(self, expression, timeout=None):
        with self._scoped_timeout(timeout):
            self('waitForElementNotPresent', expression)

    @contextmanager
    def _scoped_timeout(self, timeout):
        """Used in 'with' statements to temporarily apply *timeout*."""
        current_timeout = self._current_timeout
        need_custom = timeout is not None and timeout != current_timeout
        if not need_custom:
            # Nothing to do: timeout is already in effect.
            yield
        else:
            # Set the temporary timeout value.
            self.set_timeout(timeout)
            try:
                yield
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, exc:
                try:
                    # Got an error, try to reset the timeout.
                    self.set_timeout(current_timeout)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    # Oh well.
                    pass
                raise exc
            else:
                # Reset the timeout to what it used to be.
                self.set_timeout(current_timeout)


_transformers = {
    'unicode': lambda d: unicode(d, 'utf-8'),
    'int': int,
    'bool': lambda d: {'true': True, 'false': False}.get(d, None),
    }

_underscrore_re = re.compile(r'_([a-z])')
_camel_convert = lambda match: match.group(1).upper()


def toCamelCase(string):
    """Convert a_underscore_string to aCamelCase string."""
    return re.sub(_underscrore_re, _camel_convert, string)


def event_sender(name):
    selenium_name = toCamelCase(name)

    def handler(self, wait_for=None, timeout=None):
        before_browser_activity.send(self.browser)
        self.browser.selenium(selenium_name, self._locator)
        # XXX:dc: when would a None wait_for be a good thing?
        if wait_for:
            self.browser.wait_for(wait_for, timeout)
        time.sleep(0.2)
        after_browser_activity.send(self.browser)
        self.browser.sync_document()
    handler.__name__ = name
    handler.__doc__ = "Emit %s on this element." % selenium_name
    return handler


class FormElement(FormElement):
    """A <form/> that can be submitted."""

    submit = event_sender('submit')

    def fill(self, values, wait_for=None, timeout=None, with_prefix=u''):
        grouped = _group_key_value_pairs(values, with_prefix)
        _fill_form_async(self, grouped, wait_for, timeout)


def _fill_fields(fields, values):
    """Fill all possible *fields* with key/[value] pairs from *values*.

    :return: subset of *values* that raised ValueError on fill (e.g. a select
      could not be filled in because JavaScript has not yet set its values.)

    """
    unfilled = []
    for name, field_values in values:
        if len(field_values) == 1:
            value = field_values[0]
        else:
            value = field_values
        try:
            fields[name] = value
        except ValueError:
            unfilled.append((name, field_values))
    return unfilled


def _fill_form_async(form, values, wait_for=None, timeout=None):
    """Fill *form* with *values*, retrying fields that fail with ValueErrors.

    If multiple passes are required to set all fields in *values, the document
    will be re-synchronizes between attempts with *wait_for* called between
    each attempt.

    """
    browser = form.browser
    unset_count = len(values)
    while values:
        values = _fill_fields(form.fields, values)
        if len(values) == unset_count:
            # nothing was able to be set
            raise ValueError("Unable to set fields %s" % (
                ', '.join(pair[0] for pair in values)))
        if wait_for:
            browser.wait_for(wait_for, timeout)
        browser.sync_document()
        # replace *form* with the new lxml element from the refreshed document
        form = browser.document.xpath(form.fq_xpath)[0]
        unset_count = len(values)


def type_text(element, text, wait_for=None, timeout=0, allow_newlines=False):
    # selenium.type_keys() doesn't work with non-printables like backspace
    selenium, locator = element.browser.selenium, element._locator
    # Store the original value
    field_value = element.value
    for char in _enterable_chars_re.findall(text):
        field_value = _append_text_value(field_value, char, allow_newlines)
        if len(char) == 1 and ord(char) < 32:
            char = r'\%i' % ord(char)
        selenium.key_down(locator, char)
        # Most browsers do not allow events to do the actual typing,
        # so we need to set the value
        if element.browser.user_agent['browser'] != 'firefox':
            selenium.type(locator, field_value)
        selenium.key_press(locator, char)
        selenium.key_up(locator, char)
    if wait_for and timeout:
        element.browser.wait_for(wait_for, timeout)
        element.browser.sync_document()


class InputElement(InputElement):
    """Input fields that can be filled in."""

    @property
    def value(self):
        """The value= of this input."""
        if self.checkable:
            # doesn't seem possible to mutate get value- via selenium
            return self.attrib.get('value', '')
        return self.browser.selenium('getValue', self._locator)

    @value.setter
    def value(self, value):
        if self.checkable:
            # doesn't seem possible to mutate these values via selenium
            pass
        else:
            self.attrib['value'] = value
            self.browser.selenium('type', self._locator, value)

    @value.deleter
    def value(self):
        if self.checkable:
            self.checked = False
        else:
            if 'value' in self.attrib:
                del self.attrib['value']
            self.browser.selenium('type', self._locator, u'')

    @property
    def checked(self):
        if not self.checkable:
            raise AttributeError('Not a checkable input type')
        status = self.browser.selenium.is_checked(self._locator)
        if status:
            self.attrib['checked'] = ''
        else:
            self.attrib.pop('checked', None)
        return status

    @checked.setter
    def checked(self, value):
        """True if a checkable type is checked.  Assignable."""
        current_state = self.checked
        if value == current_state:
            return
        # can't un-check a radio button
        if self.type == 'radio' and current_state:
            return
        elif self.type == 'radio':
            self.browser.selenium('check', self._locator)
            self.attrib['checked'] = ''
            for el in self.form.inputs[self.name]:
                if el.value != self.value:
                    el.attrib.pop('checked', None)
        else:
            if value:
                self.browser.selenium('check', self._locator)
                self.attrib['checked'] = ''
            else:
                self.browser.selenium('uncheck', self._locator)
                self.attrib.pop('checked', None)

    def set(self, key, value):
        if key != 'checked':
            super(InputElement, self).set(key, value)
        self.checked = True

    def enter(self, text, wait_for='duration', timeout=0.1):
        type_text(self, text, wait_for, timeout)


class TextareaElement(TextareaElement):

    @property
    def value(self):
        """The value= of this input."""
        return self.browser.selenium('getValue', self._locator)

    @value.setter
    def value(self, value):
        self.attrib['value'] = value
        self.browser.selenium('type', self._locator, value)

    def enter(self, text, wait_for='duration', timeout=0.1):
        type_text(self, text, wait_for, timeout, allow_newlines=True)


def _get_value_and_locator_from_option(option):
    if 'value' in option.attrib:
        if option.get('value') is None:
            return None, u'value=regexp:^$'
        else:
            return option.get('value'), u'value=%s' % option.get('value')
    option_text = (option.text or u'').strip()
    return option_text, u'label=%s' % option_text


class SelectElement(SelectElement):

    def _value__set(self, value):
        super(SelectElement, self)._value__set(value)
        selected = [el for el in _options_xpath(self)
                    if 'selected' in el.attrib]
        if self.multiple:
            values = value
        else:
            values = [value]
        for el in selected:
            val, option_locator = _get_value_and_locator_from_option(el)
            if val not in values:
                raise AssertionError("Option with value %r not present in "
                                     "remote document!" % val)
            if self.multiple:
                self.browser.selenium('addSelection', self._locator,
                                        option_locator)
            else:
                self.browser.selenium('select', self._locator, option_locator)
                break

    value = property(SelectElement._value__get, _value__set)


class DOMElement(DOMElement):
    """Behavior for all lxml Element types."""

    @property
    def _locator(self):
        """The fastest Selenium locator expression for this element."""
        try:
            return 'id=' + self.attrib['id']
        except KeyError:
            return 'xpath=' + self.fq_xpath

    click = event_sender('click')
    double_click = event_sender('double_click')
    mouse_over = event_sender('mouse_over')
    mouse_out = event_sender('mouse_out')
    context_menu = event_sender('context_menu')
    focus = event_sender('focus')

    def fire_event(self, name):
        before_browser_activity.send(self.browser)
        self.browser.selenium('fireEvent', self._locator, name)
        after_browser_activity.send(self.browser)

    @property
    def is_visible(self):
        return self.browser.selenium.is_visible(self._locator)


selenium_elements = {
    '*': DOMElement,
    'form': FormElement,
    'input': InputElement,
    'select': SelectElement,
    'textarea': TextareaElement,
    }

########NEW FILE########
__FILENAME__ = wsgi
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""An in-process browser that acts as a WSGI server."""

from __future__ import absolute_import
import cookielib
from cookielib import Cookie
import dummy_threading
from cStringIO import StringIO
from logging import getLogger
import os.path
from urlparse import urljoin, urlparse, urlunparse
from time import time
import urllib2
from wsgiref.util import request_uri

from blinker import signal
from werkzeug import (
    BaseResponse,
    FileStorage,
    MultiDict,
    create_environ,
    parse_cookie,
    run_wsgi_app,
    url_encode,
    )
from werkzeug.test import encode_multipart

from alfajor.browsers._lxml import (
    ButtonElement,
    DOMElement,
    DOMMixin,
    FormElement,
    InputElement,
    SelectElement,
    TextareaElement,
    html_parser_for,
    )
from alfajor.browsers._waitexpr import WaitExpression
from alfajor.utilities import lazy_property, to_pairs
from alfajor._compat import property


__all__ = ['WSGI']
logger = getLogger('tests.browser')
after_browser_activity = signal('after_browser_activity')
before_browser_activity = signal('before_browser_activity')


class WSGI(DOMMixin):

    capabilities = [
        'in-process',
        'cookies',
        'headers',
        'status',
        ]

    wait_expression = WaitExpression

    _wsgi_server = {
        'multithread': False,
        'multiprocess': False,
        'run_once': False,
        }

    user_agent = {
        'browser': 'wsgi',
        'platform': 'python',
        'version': '1.0',
        }

    def __init__(self, wsgi_app, base_url=None):
        # accept additional request headers?  (e.g. user agent)
        self._wsgi_app = wsgi_app
        self._base_url = base_url
        self._referrer = None
        self._request_environ = None
        self._cookie_jar = CookieJar()
        self._charset = 'utf-8'
        self.status_code = 0
        self.status = ''
        self.response = None
        self.headers = ()

    def open(self, url, wait_for=None, timeout=0):
        """Open web page at *url*."""
        self._open(url, refer=False)

    def reset(self):
        self._cookie_jar = CookieJar()

    @property
    def location(self):
        if not self._request_environ:
            return None
        return request_uri(self._request_environ)

    def wait_for(self, condition, timeout=None):
        pass

    def sync_document(self):
        """The document is always synced."""

    _sync_document = DOMMixin.sync_document

    @property
    def cookies(self):
        if not (self._cookie_jar and self.location):
            return {}
        request = urllib2.Request(self.location)
        policy = self._cookie_jar._policy
        policy._now = int(time())

        # return ok will only return a cookie if the following attrs are set
        # correctly => # "version", "verifiability", "secure", "expires",
        # "port", "domain"
        return dict((c.name, c.value.strip('"'))
            for c in self._cookie_jar if policy.return_ok(c, request))

    def set_cookie(self, name, value, domain=None, path=None,
                   session=True, expires=None, port=None, request=None):
        """
        :param expires: Seconds from epoch
        :param port: must match request port
        :param domain: the fqn of your server hostname
        """
        # Cookie(version, name, value, port, port_specified,
        # domain, domain_specified, domain_initial_dot,
        # path, path_specified, secure, expires,
        # discard, comment, comment_url, rest,
        # rfc2109=False):
        cookie = Cookie(0, name, value, port, bool(port),
                        domain or '', bool(domain),
                        (domain and domain.startswith('.')),
                        path or '', bool(path), False, expires,
                        session, None, None, {}, False)
        self._cookie_jar.set_cookie(cookie)

    def delete_cookie(self, name, domain=None, path=None):
        try:
            self._cookie_jar.clear(domain, path, name)
        except KeyError:
            pass

    # Internal methods
    @lazy_property
    def _lxml_parser(self):
        return html_parser_for(self, wsgi_elements)

    def _open(self, url, method='GET', data=None, refer=True, content_type=None):
        before_browser_activity.send(self)
        open_started = time()
        environ = self._create_environ(url, method, data, refer, content_type)
        # keep a copy, the app may mutate the environ
        request_environ = dict(environ)

        logger.info('%s(%s) == %s', method, url, request_uri(environ))
        request_started = time()
        rv = run_wsgi_app(self._wsgi_app, environ)
        response = BaseResponse(*rv)
        # TODO:
        # response.make_sequence()  # werkzeug 0.6+
        # For now, must:
        response.response = list(response.response)
        if hasattr(rv[0], 'close'):
            rv[0].close()
        # end TODO

        # request is complete after the app_iter (rv[0]) has been fully read +
        # closed down.
        request_ended = time()

        self._request_environ = request_environ
        self._cookie_jar.extract_from_werkzeug(response, environ)
        self.status_code = response.status_code
        # Automatically follow redirects
        if 301 <= self.status_code <= 302:
            logger.debug("Redirect to %s", response.headers['Location'])
            after_browser_activity.send(self)
            self._open(response.headers['Location'])
            return
        # redirects report the original referrer
        self._referrer = request_uri(environ)
        self.status = response.status
        self.headers = response.headers
        # TODO: unicodify
        self.response = response.data
        self._sync_document()

        # TODO: what does a http-equiv redirect report for referrer?
        if 'meta[http-equiv=refresh]' in self.document:
            refresh = self.document['meta[http-equiv=refresh]'][0]
            if 'content' in refresh.attrib:
                parts = refresh.get('content').split(';url=', 1)
                if len(parts) == 2:
                    logger.debug("HTTP-EQUIV Redirect to %s", parts[1])
                    after_browser_activity.send(self)
                    self._open(parts[1])
                    return

        open_ended = time()
        request_time = request_ended - request_started
        logger.info("Fetched %s in %0.3fsec + %0.3fsec browser overhead",
                    url, request_time,
                    open_ended - open_started - request_time)
        after_browser_activity.send(self)

    def _create_environ(self, url, method, data, refer, content_type=None):
        """Return an environ to request *url*, including cookies."""
        environ_args = dict(self._wsgi_server, method=method)
        base_url = self._referrer if refer else self._base_url
        environ_args.update(self._canonicalize_url(url, base_url))
        environ_args.update(self._prep_input(method, data, content_type))
        environ = create_environ(**environ_args)
        if refer and self._referrer:
            environ['HTTP_REFERER'] = self._referrer
        environ.setdefault('REMOTE_ADDR', '127.0.0.1')
        self._cookie_jar.export_to_environ(environ)
        return environ

    def _canonicalize_url(self, url, base_url):
        """Return fully qualified URL components formatted for environ."""
        if '?' in url:
            url, query_string = url.split('?', 1)
        else:
            query_string = None

        canonical = {'query_string': query_string}

        # canonicalize against last request (add host/port, resolve
        # relative paths)
        if base_url:
            url = urljoin(base_url, url)

        parsed = urlparse(url)
        if not parsed.scheme:
            raise RuntimeError(
                "No base url available for resolving relative url %r" % url)

        canonical['path'] = urlunparse((
            '', '', parsed.path, parsed.params, '', ''))
        canonical['base_url'] = urlunparse((
            parsed.scheme, parsed.netloc, '', '', '', ''))
        return canonical

    def _prep_input(self, method, data, content_type):
        """Return encoded and packed POST data."""
        if data is None or method != 'POST':
            prepped = {
                'input_stream': None,
                'content_length': None,
                'content_type': None,
                }
            if method == 'GET' and data:
                qs = MultiDict()
                for key, value in to_pairs(data):
                    qs.setlistdefault(key).append(value)
                prepped['query_string'] = url_encode(qs)
            return prepped
        else:
            payload = url_encode(MultiDict(to_pairs(data)))
            content_type = 'application/x-www-form-urlencoded'
            return {
                'input_stream': StringIO(payload),
                'content_length': len(payload),
                'content_type': content_type
                }


def _wrap_file(filename, content_type):
    """Open the file *filename* and wrap in a FileStorage object."""
    assert os.path.isfile(filename), "File does not exist."
    return FileStorage(
        stream=open(filename, 'rb'),
        filename=os.path.basename(filename),
        content_type=content_type
    )


class FormElement(FormElement):
    """A <form/> that can be submitted."""

    def submit(self, wait_for=None, timeout=0, _extra_values=()):
        """Submit the form's values.

        Equivalent to hitting 'return' in a browser form: the data is
        submitted without the submit button's key/value pair.

        """
        if _extra_values and hasattr(_extra_values, 'items'):
            _extra_values = _extra_values.items()

        values = self.form_values()
        values.extend(_extra_values)
        method = self.method or 'GET'
        if self.action:
            action = self.action
        elif self.browser._referrer:
            action = urlparse(self.browser._referrer).path
        else:
            action = '/'
        self.browser._open(action, method=method, data=values,
                          content_type=self.get('enctype'))


class InputElement(InputElement):
    """An <input/> tag."""

    # Toss aside checkbox code present in the base lxml @value
    @property
    def value(self):
        return self.get('value')

    @value.setter
    def value(self, value):
        self.set('value', value)

    @value.deleter
    def value(self):
        if 'value' in self.attrib:
            del self.attrib['value']

    def click(self, wait_for=None, timeout=None):
        if self.checkable:
            self.checked = not self.checked
            return
        if self.type != 'submit':
            super(InputElement, self).click(wait_for, timeout)
            return
        for element in self.iterancestors():
            if element.tag == 'form':
                break
        else:
            # Not in a form: clicking does nothing.
            # TODO: probably not true
            return
        extra = ()
        if 'name' in self.attrib:
            extra = [[self.attrib['name'], self.attrib.get('value', 'Submit')]]
        element.submit(wait_for=wait_for, timeout=timeout, _extra_values=extra)


class ButtonElement(object):
    """Buttons that can be .click()ed."""

    def click(self, wait_for=None, timeout=0):
        # TODO: process type=submit|reset|button?
        for element in self.iterancestors():
            if element.tag == 'form':
                break
        else:
            # Not in a form: clicking does nothing.
            return
        pairs = []
        name = self.attrib.get('name', False)
        if name:
            pairs.append((name, self.attrib.get('value', '')))
        return element.submit(_extra_values=pairs)


class LinkElement(object):
    """Links that can be .click()ed."""

    def click(self, wait_for=None, timeout=0):
        try:
            link = self.attrib['href']
        except AttributeError:
            pass
        else:
            self.browser._open(link, 'GET')


wsgi_elements = {
    '*': DOMElement,
    'a': LinkElement,
    'button': ButtonElement,
    'form': FormElement,
    'input': InputElement,
    'select': SelectElement,
    'textarea': TextareaElement,
    }


class CookieJar(cookielib.CookieJar):
    """A lock-less CookieJar that can clone itself."""

    def __init__(self, policy=None):
        if policy is None:
            policy = cookielib.DefaultCookiePolicy()
        self._policy = policy
        self._cookies = {}
        self._cookies_lock = dummy_threading.RLock()

    def export_to_environ(self, environ):
        if len(self):
            u_request = _WSGI_urllib2_request(environ)
            self.add_cookie_header(u_request)

    def extract_from_werkzeug(self, response, request_environ):
        headers = response.headers
        if 'Set-Cookie' in headers or 'Set-Cookie2' in headers:
            u_response = _Werkzeug_urlib2_response(response)
            u_request = _WSGI_urllib2_request(request_environ)
            self.extract_cookies(u_response, u_request)


class _Duck(object):
    """Has arbitrary attributes assigned at construction time."""

    def __init__(self, **kw):
        for attr, value in kw.iteritems():
            setattr(self, attr, value)


class _Werkzeug_urlib2_response(object):
    __slots__ = 'response',

    def __init__(self, response):
        self.response = response

    def info(self):
        return _Duck(getallmatchingheaders=self.response.headers.getlist,
                     getheaders=self.response.headers.getlist)


class _WSGI_urllib2_request(object):

    def __init__(self, environ):
        self.environ = environ
        self.url = request_uri(self.environ)
        self.url_parts = urlparse(self.url)

    def get_full_url(self):
        return self.url

    def get_host(self):
        return self.url_parts.hostname

    def get_type(self):
        return self.url_parts.scheme

    def is_unverifiable(self):
        return False

    def get_origin_req_host(self):
        raise Exception('fixme need previous request')

    def has_header(self, header):
        key = header.replace('-', '_').upper()
        return key in self.environ or 'HTTP_%s' % key in self.environ

    def get_header(self, header):
        return self.environ.get('HTTP_%s' % header.replace('-', '_').upper())

    def header_items(self):
        items = []
        for key, value in self.environ.iteritems():
            if ((key.startswith('HTTP_') or key.startswith('CONTENT_')) and
                isinstance(value, basestring)):
                if key.startswith('HTTP_'):
                    key = key[5:]
                key = key.replace('_', '-').title()
                items.append((key, value))
        return items

    def add_unredirected_header(self, key, value):
        if key == 'Cookie':
            self.environ['HTTP_COOKIE'] = "%s: %s" % (key, value)

########NEW FILE########
__FILENAME__ = zero
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""A non-functional web browser.

Documents the canonical base implementation of browsers.  Zero is instantiable
and usable, however it does not supply any capabilities.

"""

from alfajor.utilities import lazy_property
from alfajor.browsers._lxml import DOMMixin, base_elements, html_parser_for
from alfajor.browsers._waitexpr import WaitExpression


__all__ = ['Zero']


class Zero(DOMMixin):
    """A non-functional web browser."""

    capabilities = []

    wait_expression = WaitExpression

    user_agent = {
        'browser': 'zero',
        'platform': 'python',
        'version': '0.1',
        }

    location = '/'

    status_code = 0

    status = None

    response = """\
<html>
  <body>
    <h1>Not Implemented</h>
    <p>Web browsing unavailable.</p>
  </body>
</html>
"""

    def open(self, url, wait_for=None, timeout=0):
        """Navigate to *url*."""

    def reset(self):
        """Reset browser state (clear cookies, etc.)"""

    def wait_for(self, condition, timeout=0):
        """Wait for *condition*."""

    def sync_document(self):
        """The document is always synced."""

    headers = {}
    """A dictionary of HTTP response headers."""

    cookies = {}
    """A dictionary of cookies visible to the current page."""

    def set_cookie(self, name, value, domain=None, path='/', **kw):
        """Set a cookie."""

    def delete_cookie(self, name, domain=None, path='/', **kw):
        """Delete a cookie."""

    @lazy_property
    def _lxml_parser(self):
        return html_parser_for(self, base_elements)

    # ? select_form(...) -> ...

    # future capability:
    #  file upload

########NEW FILE########
__FILENAME__ = _lxml
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.


"""Low level LXML element implementation & parser wrangling."""
from collections import defaultdict
import mimetypes
import re
from UserDict import DictMixin
from textwrap import fill

from lxml import html as lxml_html
from lxml.etree import ElementTree, XPath
from lxml.html import (
    fromstring as html_from_string,
    tostring,
    )
from lxml.html._setmixin import SetMixin

from alfajor._compat import property
from alfajor.utilities import lazy_property, to_pairs


__all__ = ['html_parser_for', 'html_from_string']
_single_id_selector = re.compile(r'#[A-Za-z][A-Za-z0-9:_.\-]*$')
XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"

# lifted from lxml
_options_xpath = XPath(
    "descendant-or-self::option|descendant-or-self::x:option",
    namespaces={'x': XHTML_NAMESPACE})
_collect_string_content = XPath("string()")
_forms_xpath = XPath("descendant-or-self::form|descendant-or-self::x:form",
                     namespaces={'x': XHTML_NAMESPACE})


def _nons(tag):
    if isinstance(tag, basestring):
        if (tag[0] == '{' and
            tag[1:len(XHTML_NAMESPACE) + 1] == XHTML_NAMESPACE):
            return tag.split('}')[-1]
    return tag

# not lifted from lxml
_enclosing_form_xpath = XPath('ancestor::form[1]')


class callable_unicode(unicode):
    """Compatibility class for 'element.text_content'"""

    def __call__(self):
        return unicode(self)


def html_parser_for(browser, element_mixins):
    "Return an HTMLParser linked to *browser* and powered by *element_mixins*."
    parser = lxml_html.HTMLParser()
    parser.set_element_class_lookup(ElementLookup(browser, element_mixins))
    return parser


class DOMMixin(object):
    """Supplies DOM parsing and query methods to browsers.

    Browsers must implement a ``self._lxml_parser`` property that contains a
    parser specific to this browser instance.  For example:

      element_mixins = {} # pairs of 'element name': <mixin class>

      @lazy_property
      def _lxml_parser(self):
          return html_parser_for(self, self.element_mixins)

    """

    @lazy_property
    def document(self):
        """An LXML tree of the :attr:`response` content."""
        # TODO: document decision to use 'fromstring' (means dom may
        # be what the remote sent, may not.)
        if self.response is None:
            return None
        return html_from_string(self.response, parser=self._lxml_parser)

    def sync_document(self):
        """Synchronize the :attr:`document` DOM with the visible page."""
        self.__dict__.pop('document', None)

    def __contains__(self, needle):
        """True if *needle* exists anywhere in the response content."""
        # TODO: make this normalize whitespace?  something like split
        # *needle* on whitespace, build a regex of r'\s+'-separated
        # bits.  this could be a fallback to a simple containment
        # test.
        document = self.document
        if document is None:
            return False
        return needle in document.text_content

    @property
    def xpath(self):
        """An xpath querying function querying at the top of the document."""
        return self.document.xpath

    @property
    def cssselect(self):
        """A CSS selector function selecting at the top of the document."""
        return self.document.cssselect


class DOMElement(object):
    """Functionality added to all elements on all browsers."""

    @lazy_property
    def fq_xpath(self):
        """The fully qualified xpath to this element."""
        return ElementTree(self).getpath(self)

    @property
    def forms(self):
        """Return a list of all the forms."""
        return _FormsList(_forms_xpath(self))

    # DOM methods (Mostly applicable only with javascript enabled.)  Capable
    # browsers should re-implement these methods.

    def click(self, wait_for=None, timeout=0):
        """Click this element."""

    def double_click(self, wait_for=None, timeout=0):
        """Double-click this element."""

    def mouse_over(self, wait_for=None, timeout=0):
        """Move the mouse into this element's bounding box."""

    def mouse_out(self, wait_for=None, timeout=0):
        """Move the mouse out of this element's bounding box."""

    def focus(self, wait_for=None, timeout=0):
        """Shift focus to this element."""

    def fire_event(self, name, wait_for=None, timeout=0):
        """Fire DOM event *name* on this element."""

    # TODO:jek: investigate css-tools for implementing this for the WSGI
    # browser
    is_visible = True
    """True if the element is visible.

    Note: currently always True in the WSGI browser.

    """

    @property
    def text_content(self):
        """The text content of the tag and its children.

        This property overrides the text_content() method of regular
        lxml.html elements.  Similar, but acts usable as an
        attribute or as a method call and normalizes all whitespace
        as single spaces.

        """
        text = u' '.join(_collect_string_content(self).split())
        return callable_unicode(text)

    @property
    def innerHTML(self):
        inner = ''.join(tostring(el) for el in self.iterchildren())
        if self.text:
            return self.text + inner
        else:
            return inner

    def __contains__(self, needle):
        """True if the element or its children contains *needle*.

        :param needle: may be an document element, integer index or a
        CSS select query.

        If *needle* is a document element, only immediate decedent
        elements are considered.

        """
        if not isinstance(needle, (int, basestring)):
            return super(DOMElement, self).__contains__(needle)
        try:
            self[needle]
        except (AssertionError, IndexError):
            return False
        else:
            return True

    def __getitem__(self, key):
        """Retrieve elements by integer index, id or CSS select query."""
        if not isinstance(key, basestring):
            return super(DOMElement, self).__getitem__(key)
        # '#foo'?  (and not '#foo li')
        if _single_id_selector.match(key):
            try:
                return self.get_element_by_id(key[1:])
            except KeyError:
                label = 'Document' if self.tag == 'html' else 'Fragment'
                raise AssertionError("%s contains no element with "
                                     "id %r" % (label, key))
        # 'li #foo'?  (and not 'li #foo li')
        elif _single_id_selector.search(key):
            elements = self.cssselect(key)
            if len(elements) != 1:
                label = 'Document' if self.tag == 'html' else 'Fragment'
                raise AssertionError("%s contains %s elements matching "
                                     "id %s!" % (label, len(elements), key))
            return elements[0]
        else:
            elements = self.cssselect(key)
            if not elements:
                label = 'Document' if self.tag == 'html' else 'Fragment'
                raise AssertionError("%s contains no elements matching "
                                     "css selector %r" % (label, key))
            return elements

    def __str__(self):
        """An excerpt of the HTML of this element (without its children)."""
        clone = self.makeelement(self.tag, self.attrib, self.nsmap)
        if self.text_content:
            clone.text = u'...'
        value = self.get('value', '')
        if len(value) > 32:
            clone.attrib['value'] = value + u'...'
        html = tostring(clone)
        return fill(html, 79, subsequent_indent='    ')


class FormElement(object):

    @property
    def inputs(self):
        """An accessor for all the input elements in the form.

        See :class:`InputGetter` for more information about the object.
        """
        return InputGetter(self)

    def fields(self):
        """A dict-like read/write mapping of form field values."""
        return FieldsDict(self.inputs)

    fields = property(fields, lxml_html.FormElement._fields__set)

    def submit(self, wait_for=None, timeout=0):
        """Submit the form's values.

        Equivalent to hitting 'return' in a browser form: the data is
        submitted without the submit button's key/value pair.

        """

    def fill(self, values, wait_for=None, timeout=0, with_prefix=u''):
        """Fill fields of the form from *values*.

        :param values: a mapping or sequence of name/value pairs of form data.
          If a sequence is provided, the sequence order will be respected when
          filling fields with the exception of disjoint pairs in a checkbox
          group, which will be set all at once.

        :param with_prefix: optional, a string that all form fields should
          start with.  If a supplied field name does not start with this
          prefix, it will be prepended.

        """
        grouped = _group_key_value_pairs(values, with_prefix)
        fields = self.fields
        for name, field_values in grouped:
            if len(field_values) == 1:
                value = field_values[0]
            else:
                value = field_values
            fields[name] = value

    def form_values(self):
        """Return name, value pairs of form data as a browser would submit."""
        results = []
        for name, elements in self.inputs.iteritems():
            if not name:
                continue
            if elements[0].tag == 'input':
                type = elements[0].type
            else:
                type = elements[0].tag
            if type in ('submit', 'image', 'reset'):
                continue
            for el in elements:
                value = el.value
                if getattr(el, 'checkable', False):
                    if not el.checked:
                        continue
                    # emulate browser behavior for valueless checkboxes
                    results.append((name, value or 'on'))
                    continue
                elif type == 'select':
                    if value is None:
                        # this won't be reached unless the first option is
                        # <option/>
                        options = el.cssselect('> option')
                        if options:
                            results.append((name, u''))
                        continue
                    elif el.multiple:
                        for v in value:
                            results.append((name, v))
                        continue
                elif type == 'file':
                    if value:
                        mimetype = mimetypes.guess_type(value)[0] \
                                or 'application/octet-stream'
                        results.append((name, (value, mimetype)))
                        continue
                results.append((name, value or u''))
        return results

    def __str__(self):
        """The HTML of this element and a dump of its fields."""
        lines = [DOMElement.__str__(self).rstrip('</form>').rstrip('...')]
        fields = self.fields
        for field_name in sorted(fields.keys()):
            lines.append('* %s = %s' % (field_name, fields[field_name]))
        return '\n'.join(lines)


class _InputControl(object):
    """Common functionality for all interactive form elements."""

    @property
    def form(self):
        """The enclosing <form> tag for this field."""
        try:
            return _enclosing_form_xpath(self)[0]
        except IndexError:
            return None


def _value_from_option(option):
    """
    Pulls the value out of an option element, following order rules of value
    attribute, text and finally empty string.
    """
    opt_value = option.get('value')
    if opt_value is None:
        opt_value = option.text or u''
    if opt_value:
        opt_value = opt_value.strip()
    return opt_value


# More or less from
class MultipleSelectOptions(SetMixin):
    """
    Represents all the selected options in a ``<select multiple>`` element.

    You can add to this set-like option to select an option, or remove
    to unselect the option.
    """

    def __init__(self, select):
        self.select = select

    def options(self):
        """
        Iterator of all the ``<option>`` elements.
        """
        return iter(_options_xpath(self.select))
    options = property(options)

    def __iter__(self):
        for option in self.options:
            if 'selected' in option.attrib:
                yield _value_from_option(option)

    def add(self, item):
        for option in self.options:
            opt_value = _value_from_option(option)
            if opt_value == item:
                option.set('selected', '')
                break
        else:
            raise ValueError(
                "There is no option with the value %r" % item)

    def remove(self, item):
        for option in self.options:
            opt_value = _value_from_option(option)
            if opt_value == item:
                if 'selected' in option.attrib:
                    del option.attrib['selected']
                else:
                    raise ValueError(
                        "The option %r is not currently selected" % item)
                break
        else:
            raise ValueError(
                "There is not option with the value %r" % item)

    def __repr__(self):
        return '<%s {%s} for select name=%r>' % (
            self.__class__.__name__,
            ', '.join([repr(v) for v in self]),
            self.select.name)


# Patched from lxml
class SelectElement(_InputControl):
    """
    ``<select>`` element.  You can get the name with ``.name``.

    ``.value`` will be the value of the selected option, unless this
    is a multi-select element (``<select multiple>``), in which case
    it will be a set-like object.  In either case ``.value_options``
    gives the possible values.

    The boolean attribute ``.multiple`` shows if this is a
    multi-select.
    """

    def _value__get(self):
        """
        Get/set the value of this select (the selected option).

        If this is a multi-select, this is a set-like object that
        represents all the selected options.
        """
        if self.multiple:
            return MultipleSelectOptions(self)
        for el in _options_xpath(self):
            if el.get('selected') is not None:
                return _value_from_option(el)
        return None

    def _value__set(self, value):
        if self.multiple:
            if isinstance(value, basestring):
                raise TypeError(
                    "You must pass in a sequence")
            self.value.clear()
            self.value.update(value)
            return
        if value is not None:
            value = value.strip()
            for el in _options_xpath(self):
                opt_value = _value_from_option(el)
                if opt_value == value:
                    checked_option = el
                    break
            else:
                raise ValueError(
                    "There is no option with the value of %r" % value)
        for el in _options_xpath(self):
            if 'selected' in el.attrib:
                del el.attrib['selected']
        if value is not None:
            checked_option.set('selected', '')

    def _value__del(self):
        # FIXME: should del be allowed at all?
        if self.multiple:
            self.value.clear()
        else:
            self.value = None

    value = property(_value__get, _value__set, _value__del, doc=_value__get.__doc__)

    def value_options(self):
        """
        All the possible values this select can have (the ``value``
        attribute of all the ``<option>`` elements.
        """
        options = []
        for el in _options_xpath(self):
            options.append(_value_from_option(el))
        return options
    value_options = property(value_options, doc=value_options.__doc__)

    def _multiple__get(self):
        """
        Boolean attribute: is there a ``multiple`` attribute on this element.
        """
        return 'multiple' in self.attrib
    def _multiple__set(self, value):
        if value:
            self.set('multiple', '')
        elif 'multiple' in self.attrib:
            del self.attrib['multiple']
    multiple = property(_multiple__get, _multiple__set, doc=_multiple__get.__doc__)


def _append_text_value(existing, new, allow_multiline):
    buffer = list(existing)
    for char in new:
        val = ord(char)
        # a printable char?
        if val > 31:
            buffer.append(char)
        elif allow_multiline and val in (10, 13):
            buffer.append(char)
        elif val == 127:
            raise NotImplementedError("delete? seriously?")
        # backspace
        elif val == 8:
            if buffer[-2:] == ['\r', '\n']:
                del buffer[-2:]
            else:
                del buffer[-1:]
    return ''.join(buffer)


class InputElement(_InputControl):

    def enter(self, text):
        """Append *text* into the value of the input field."""
        if self.type not in ('text', 'radio'):
            raise TypeError('Can not type into <input type=%s>' % self.type)
        self.value = _append_text_value(self.value, text, False)

    @property
    def checked(self):
        if not self.checkable:
            raise AttributeError("Not a checkable input type")
        return 'checked' in self.attrib

    @checked.setter
    def checked(self, value):
        if not self.checkable:
            raise AttributeError("Not a checkable input type")
        have = 'checked' in self.attrib
        if (value and have) or (not value and not have):
            return
        if self.type == 'radio':
            # You can't un-check a radio button in any browser I know of
            if have and not value:
                return
            for el in self.form.inputs[self.name]:
                if el.value == self.value:
                    el.set('checked', '')
                else:
                    el.attrib.pop('checked', None)
            return
        if value:
            self.set('checked', '')
        elif have:
            del self.attrib['checked']


class TextareaElement(_InputControl):

    def enter(self, text):
        """Append *text* into the value of the field."""
        self.value = _append_text_value(self.value, text, True)


class ButtonElement(_InputControl):
    pass


base_elements = {
    '*': DOMElement,
    'button': ButtonElement,
    'form': FormElement,
    'input': InputElement,
    'select': SelectElement,
    'textarea': TextareaElement,
    }


class ElementLookup(lxml_html.HtmlElementClassLookup):

    # derived from the lxml class

    def __init__(self, browser, mixins):
        lxml_html.HtmlElementClassLookup.__init__(self)
        mixins = list(to_pairs(mixins))

        mix_all = tuple(cls for name, cls in mixins if name == '*')

        for name in ('HtmlElement', 'HtmlComment', 'HtmlProcessingInstruction',
                     'HtmlEntity'):
            base = getattr(lxml_html, name)
            mixed = type(name,  mix_all + base.__bases__, {'browser': browser})
            setattr(self, name, mixed)

        classes = self._element_classes
        mixers = {}
        for name, value in mixins:
            if name == '*':
                continue
            mixers.setdefault(name, []).append(value)

        for name, value in mixins:
            if name != '*':
                continue
            for n in classes.keys():
                mixers.setdefault(n, []).append(value)

        for name, mix_bases in mixers.items():
            cur = classes.get(name, self.HtmlElement)
            bases = tuple(mix_bases + [cur])
            classes[name] = type(cur.__name__, bases, {'browser': browser})
        self._element_classes = classes

    def lookup(self, node_type, document, namespace, name):
        if node_type == 'element':
            return self._element_classes.get(name.lower(), self.HtmlElement)
        elif node_type == 'comment':
            return self.HtmlComment
        elif node_type == 'PI':
            return self.HtmlProcessingInstruction
        elif node_type == 'entity':
            return self.HtmlEntity


class InputGetter(lxml_html.InputGetter):
    """Accesses form elements by name.

    Indexing the object with ``[name]`` will return a list of elements
    having that name.

    This differs from the lxml behavior of this object, which comingles scalar
    and sequence results based on the form element type.

    """

    def __getitem__(self, name):
        results = self._name_xpath(self.form, name=name)
        if not results:
            raise KeyError("No input element with the name %r" % name)
        return results
        # TODO:             group = RadioGroup(results)

    def iteritems(self):
        for name in self.keys():
            yield (name, self[name])


class FieldsDict(DictMixin):
    """Reflects the current state of a form as a browser sees it."""

    # Modeled after lxml_html.FieldsDict

    class CheckableProxy(lxml_html.CheckboxValues):

        def __iter__(self):
            for el in self.group:
                if el.checked:
                    yield el.get('value', 'on')

        def add(self, value):
            for el in self.group:
                if el.get('value', 'on') == value:
                    el.checked = True
                    break
            else:
                raise KeyError("No checkbox with value %r" % value)

        def remove(self, value):
            for el in self.group:
                if el.get('value', 'on') == value:
                    el.checked = False
                    break
            else:
                raise KeyError("No checkbox with value %r" % value)

        def __repr__(self):
            return '<%s {%s} for checkboxes name=%r>' % (
                self.__class__.__name__,
                ', '.join([repr(v) for v in self]),
                self.group[0].name)

    def __init__(self, inputs):
        self.inputs = inputs

    def __getitem__(self, name):
        elements = self.inputs[name]
        first = elements[0]
        checkable = getattr(first, 'checkable', False)

        if len(elements) == 1:
            if checkable:
                return first.value if first.checked else ''
            return first.value
        # repeated <input type="text" name="name"> only report the first
        if not checkable:
            return first.value
        return self.CheckableProxy(elements)

    def __setitem__(self, name, value):
        elements = self.inputs[name]
        first = elements[0]
        checkable = getattr(first, 'checkable', False)

        if len(elements) == 1:
            if not checkable:
                first.value = value
            # checkbox dance
            elif value is True or value == first.value:
                first.checked = True
            elif value is False or value == u'':
                first.checked = False
            else:
                raise ValueError("Expected %r, '', True or False for "
                                 "checkable element %r" % (first.value, name))
        elif not checkable:
            # repeated <input type="text" name="name"> only set the first
            first.value = value
        else:
            proxy = self.CheckableProxy(elements)
            if isinstance(value, basestring):
                proxy.update([value])
            else:
                proxy.update(value)

    def __delitem__(self, name):
        raise KeyError("You cannot remove keys from FieldsDict")

    def keys(self):
        return self.inputs.keys()

    def __contains__(self, name):
        return name in self.inputs


def _group_key_value_pairs(values, with_prefix=''):
    """Transform *values* into a sequence of ('name', ['values']) pairs.

    For use by form.fill().  Collapses repeats of a given name into a single
    list of values.  (And non-repeated names as a list of one value.)

    :param values: a mapping or sequence of name/value pairs.

    :param with_prefix: optional, a string that all form fields should
      start with.  If a supplied field name does not start with this
      prefix, it will be prepended.

    """
    grouped = defaultdict(list)
    transformed_keys = []
    for key, value in to_pairs(values):
        if with_prefix and not key.startswith(with_prefix):
            key = with_prefix + key
        grouped[key].append(value)
        if key not in transformed_keys:
            transformed_keys.append(key)
    return [(key, grouped[key]) for key in transformed_keys]


class _FormsList(list):
    """A printable list of forms present in the document."""

    def __str__(self):
        return "\n".join(map(str, self))

########NEW FILE########
__FILENAME__ = _waitexpr
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Compound wait_for expression support."""

__all__ = 'WaitExpression', 'SeleniumWaitExpression'

OR = object()


class WaitExpression(object):
    """Generic wait_for expression generator and compiler.

    Expression objects chain in a jQuery/SQLAlchemy-esque fashion::

      expr = (browser.wait_expression().
              element_present('#druid').
              ajax_complete())

    Or can be configured at instantiation:

      expr = browser.wait_expression(['element_present', '#druid'],
                                     ['ajax_complete'])

    Expression components are and-ed (&&) together.  To or (||), separate
    components with :meth:`or_`::

      element_present('#druid').or_().ajax_complete()

    The expression object can be supplied to any operation which accepts
    a ``wait_for`` argument.

    """

    def __init__(self, *expressions):
        for spec in expressions:
            directive = spec[0]
            args = spec[1:]
            getattr(self, directive)(*args)

    def or_(self):
        """Combine the next expression with an OR instead of default AND."""
        return self

    def element_present(self, finder):
        """True if *finder* is present on the page.

        :param finder: a CSS selector or document element instance

        """
        return self

    def element_not_present(self, expr):
        """True if *finder* is not present on the page.

        :param finder: a CSS selector or document element instance

        """
        return self

    def evaluate_element(self, finder, expr):
        """True if *finder* is present on the page and evaluated by *expr*.

        :param finder: a CSS selector or document element instance

        :param expr: literal JavaScript text; should evaluate to true or
          false.  The variable ``element`` will hold the *finder* DOM element,
          and ``window`` is the current window.

        """
        return self

    def ajax_pending(self):
        """True if jQuery ajax requests are pending."""
        return self

    def ajax_complete(self):
        """True if no jQuery ajax requests are pending."""
        return self

    def __unicode__(self):
        """The rendered value of the expression."""
        return u''


class SeleniumWaitExpression(WaitExpression):
    """Compound wait_for expression compiler for Selenium browsers."""

    def __init__(self, *expressions):
        self._expressions = []
        WaitExpression.__init__(self, *expressions)

    def or_(self):
        self._expressions.append(OR)
        return self

    def element_present(self, finder):
        js = self._is_element_present('element_present', finder, 'true')
        self._expressions.append(js)
        return self

    def element_not_present(self, finder):
        js = self._is_element_present('element_not_present', finder, 'false')
        self._expressions.append(js)
        return self

    def evaluate_element(self, finder, expr):
        locator = to_locator(finder)
        log = evaluation_log('evaluate_element', 'result', locator, expr)
        js = """\
(function () {
  var element;
  try {
    element = selenium.browserbot.findElement('%s');
  } catch (e) {
    element = null;
  };
  var result = false;
  if (element != null)
    result = %s;
  %s
  return result;
})()""" % (js_quote(locator), expr, log)
        self._expressions.append(js)
        return self

    def ajax_pending(self):
        js = """\
(function() {
  var pending = window.jQuery && window.jQuery.active != 0;
  %s
  return pending;
})()""" % predicate_log('ajax_pending', 'complete')
        self._expressions.append(js)
        return self

    def ajax_complete(self):
        js = """\
(function() {
  var complete = window.jQuery ? window.jQuery.active == 0 : true;
  %s
  return complete;
})()""" % predicate_log('ajax_complete', 'complete')
        self._expressions.append(js)
        return self

    def _is_element_present(self, label, finder, result):
        locator = to_locator(finder)
        log = evaluation_log(label, 'found', locator)
        return u"""\
(function () {
  var found = true;
  try {
    selenium.browserbot.findElement('%s');
  } catch (e) {
    found = false;
  };
  %s
  return found == %s;
})()""" % (js_quote(locator), log, result)

    def __unicode__(self):
        last = None
        components = []
        for expr in self._expressions:
            if expr is OR:
                components.append(u'||')
            else:
                if last not in (None, OR):
                    components.append(u'&&')
                components.append(expr)
            last = expr
        predicate = u' '.join(components).replace('\n', ' ')
        return predicate


def js_quote(string):
    """Prepare a string for use in a 'single quoted' JS literal."""
    string = string.replace('\\', r'\\')
    string = string.replace('\'', r'\'')
    return string


def to_locator(expr):
    """Convert a css selector or document element into a selenium locator."""
    if isinstance(expr, basestring):
        return 'css=' + expr
    elif hasattr(expr, '_locator'):
        return expr._locator
    else:
        raise RuntimeError("Unknown page element %r" % expr)


def predicate_log(label, result_variable):
    """Return JS for logging a boolean result test in the Selenium console."""
    js = "LOG.info('wait_for %s ==' + %s);" % (
        js_quote(label), result_variable)
    return js


def evaluation_log(label, result_variable, *args):
    """Return JS for logging an expression eval in the Selenium console."""
    inner = ', '.join(map(js_quote, args))
    js = "LOG.info('wait_for %s(%s)=' + %s);" % (
        js_quote(label), inner, result_variable)
    return js

########NEW FILE########
__FILENAME__ = nose
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Integration with the 'nose' test runner."""

from __future__ import absolute_import
from base64 import b64decode
from logging import getLogger
from optparse import OptionGroup
from os import path

from nose.plugins.base import Plugin

from alfajor._management import ManagerLookupError, new_manager


logger = getLogger('nose.plugins')


class Alfajor(Plugin):

    name = 'alfajor'
    enabled = True  # FIXME
    alfajor_enabled_screenshot = False

    def __init__(self):
        Plugin.__init__(self)
        self._contexts = []

    def options(self, parser, env):
        group = OptionGroup(parser, "Alfajor options")
        group.add_option('-B', '--browser',
                         dest='alfajor_browser_frontend',
                         metavar='ALFAJOR_BROWSER',
                         default=env.get('ALFAJOR_BROWSER'),
                         help='Run functional tests with ALFAJOR_BROWSER '
                         '[ALFAJOR_BROWSER]')
        group.add_option('--alfajor-apiclient',
                         dest='alfajor_apiclient_frontend',
                         metavar='ALFAJOR_BROWSER',
                         default=env.get('ALFAJOR_BROWSER'),
                         help='Run functional tests with ALFAJOR_BROWSER '
                         '[ALFAJOR_BROWSER]')
        group.add_option('--alfajor-config',
                         dest='alfajor_ini_file',
                         metavar='ALFAJOR_CONFIG',
                         default=env.get('ALFAJOR_CONFIG'),
                         help='Specify the name of your configuration file,'
                         'which can be any path on the system. Defaults to'
                         'alfajor.ini'
                         '[ALFAJOR_CONFIG]')
        parser.add_option_group(group)

        group = OptionGroup(parser, "Alfajor Selenium backend options")
        group.add_option('--without-server',
                         dest='alfajor_without_server',
                         metavar='WITHOUT_SERVER',
                         action='store_true',
                         default=env.get('ALFAJOR_WITHOUT_SERVER', False),
                         help='Run functional tests against an already '
                         'running web server rather than start a new server '
                         'process.'
                         '[ALFAJOR_EXTERNAL_SERVER]')
        group.add_option('--server-url',
                         dest='alfajor_server_url',
                         metavar='SERVER_URL',
                         default=env.get('ALFAJOR_SERVER_URL', None),
                         help='Run functional tests against this URL, '
                         'overriding all file-based configuration.'
                         '[ALFAJOR_SERVER_URL]')
        parser.add_option_group(group)

        group = OptionGroup(parser, "Alfajor Screenshot Options")
        group.add_option(
            "--screenshot", action="store_true",
            dest="alfajor_enabled_screenshot",
            default=env.get('ALFAJOR_SCREENSHOT', False),
            help="Take screenshots of failed pages")
        group.add_option(
            "--screenshot-dir",
            dest="alfajor_screenshot_dir",
            default=env.get('ALFAJOR_SCREENSHOT_DIR', ''),
            help="Dir to store screenshots")
        parser.add_option_group(group)

    def configure(self, options, config):
        Plugin.configure(self, options, config)
        alfajor_options = {}
        for key, value in vars(options).iteritems():
            if key.startswith('alfajor_'):
                short = key[len('alfajor_'):]
                alfajor_options[short] = value
        self.options = alfajor_options

    def startContext(self, context):
        try:
            setups = context.__alfajor_setup__
        except AttributeError:
            return
        if not setups:
            return
        managers = set()

        logger.info("Processing alfajor functional browsing for context %r",
                    context.__name__)

        for declaration in setups:
            configuration = declaration.configuration
            logger.info("Enabling alfajor %s in configuration %s",
                        declaration.tool, configuration)

            try:
                manager = new_manager(declaration, self.options, logger)
            except ManagerLookupError, exc:
                logger.warn("Skipping setup of %s in context %r: %r",
                            declaration.tool, context, exc.args[0])
                continue
            managers.add((manager, declaration))
            declaration.proxy._factory = manager.create
        if managers:
            self._contexts.append((context, managers))

    def stopContext(self, context):
        # self._contexts is a list of tuples, [0] is the context key
        if self._contexts and context == self._contexts[-1][0]:
            key, managers = self._contexts.pop(-1)
            for manager, declaration in managers:
                manager.destroy()
                declaration.proxy._instance = None
                declaration.proxy._factory = None

    def addError(self, test, err):
        self.screenshotIfEnabled(test)

    def addFailure(self, test, err):
        self.screenshotIfEnabled(test)

    def screenshotIfEnabled(self, test):
        if self.options['enabled_screenshot']:
            selenium = self._getSelenium()
            if selenium:
                self.screenshot(selenium, test)

    def _getSelenium(self):
        """Get the selenium instance for this test if one exists.

        Otherwise return None.
        """
        assert self._contexts
        contexts, managers = self._contexts[-1]
        for manager, declaration in managers:
            instance = declaration.proxy._instance
            if hasattr(instance, 'selenium'):
                return instance.selenium
        return None

    def screenshot(self, selenium, test):
        img = selenium.capture_entire_page_screenshot_to_string()
        test_name = test.id().split('.')[-1]
        directory = self.options['screenshot_dir']
        output_file = open('/'.join(
                [path.abspath(directory), test_name + '.png']), "w")
        output_file.write(b64decode(img))
        output_file.close()

########NEW FILE########
__FILENAME__ = utilities
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Utilities useful for managing functional browsers and HTTP clients."""

import inspect
import sys
import time

__all__ = ['ServerSubProcess', 'eval_dotted_path', 'invoke']


def _import(module_name):
    """Import a module by name."""
    local_name = module_name.split('.')[-1]
    return __import__(module_name, {}, {}, local_name)


def _import_some(dotted_path):
    """Import as much of dotted.path as possible, returning module and
    remainder."""
    steps = list(dotted_path.split('.'))
    modname = [steps.pop(0)]
    mod = _import(modname[0])
    while steps:
        try:
            mod = _import('.'.join(modname + steps[:1]))
        except ImportError:
            break
        else:
            modname.append(steps.pop(0))
    return mod, '.'.join(steps)


def eval_dotted_path(string):
    """module.member.member or module.module:evaled.in.module"""

    if ':' not in string:
        mod, expr = _import_some(string)
    else:
        modname, expr = string.split(':', 1)
        mod = _import(modname)
    if expr:
        return eval(expr, mod.__dict__)
    else:
        return mod


class lazy_property(object):
    """An efficient, memoized @property."""

    def __init__(self, fn):
        self.fn = fn
        self.__name__ = fn.func_name
        self.__doc__ = fn.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        obj.__dict__[self.__name__] = result = self.fn(obj)
        return result


def to_pairs(dictlike):
    """Yield (key, value) pairs from any dict-like object.

    Implements an optimized version of the dict.update() definition of
    "dictlike".

    """
    if hasattr(dictlike, 'items'):
        return dictlike.items()
    elif hasattr(dictlike, 'keys'):
        return [(key, dictlike[key]) for key in dictlike.keys()]
    else:
        return [(key, value) for key, value in dictlike]


def _optargs_to_kwargs(args):
    """Convert --bar-baz=quux --xyzzy --no-squiz to kwargs-compatible pairs.

    E.g., [('bar_baz', 'quux'), ('xyzzy', True), ('squiz', False)]

    """
    kwargs = []
    for arg in args:
        if not arg.startswith('--'):
            raise RuntimeError("Unknown option %r" % arg)
        elif '=' in arg:
            key, value = arg.split('=', 1)
            key = key[2:].replace('-', '_')
            if value.isdigit():
                value = int(value)
        elif arg.startswith('--no-'):
            key, value = arg[5:].replace('-', '_'), False
        else:
            key, value = arg[2:].replace('-', '_'), True
        kwargs.append((key, value))
    return kwargs


def invoke():
    """Load and execute a Python function from the command line.

    Functions may be specified in dotted-path/eval syntax, in which case the
    expression should evaluate to a callable function:

       module.name:pythoncode.to.eval

    Or by module name alone, in which case the function 'main' is invoked in
    the named module.

       module.name

    If configuration files are provided, they will be read and all items from
    [defaults] will be passed to the function as keyword arguments.

    """
    def croak(msg):
        print >> sys.stderr, msg
        sys.exit(1)
    usage = "Usage: %s module.name OR module:callable"

    target, args = None, []
    try:
        for arg in sys.argv[1:]:
            if arg.startswith('-'):
                args.append(arg)
            else:
                if target:
                    raise RuntimeError
                target = arg
        if not target:
            raise RuntimeError
    except RuntimeError:
        croak(usage + "\n" + inspect.cleandoc(invoke.__doc__))
    clean = _optargs_to_kwargs(args)
    kwargs = dict(clean)

    try:
        hook = eval_dotted_path(target)
    except (NameError, ImportError), exc:
        croak("Could not invoke %r: %r" % (target, exc))

    if isinstance(hook, type(sys)) and hasattr(hook, 'main'):
        hook = hook.main
    if not callable(hook):
        croak("Entrypoint %r is not a callable function or "
              "module with a main() function.")

    retval = hook(**kwargs)
    sys.exit(retval)


class ServerSubProcess(object):
    """Starts and stops subprocesses."""

    def __init__(self, cmd, ping=None):
        self.cmd = cmd
        self.process = None
        if not ping:
            self.host = self.port = None
        else:
            if ':' in ping:
                self.host, port = ping.split(':', 1)
                self.port = int(port)
            else:
                self.host = ping
                self.port = 80

    def start(self):
        """Start the process."""
        import shlex
        from subprocess import Popen, PIPE, STDOUT

        if self.process:
            raise RuntimeError("Process already started.")
        if self.host and self.network_ping():
            raise RuntimeError("A process is already running on port %s" %
                               self.port)

        if isinstance(self.cmd, basestring):
            cmd = shlex.split(self.cmd)
        else:
            cmd = self.cmd
        process = Popen(cmd, stdout=PIPE, stderr=STDOUT, close_fds=True)

        if not self.host:
            time.sleep(0.35)
            if process.poll():
                output = process.communicate()[0]
                raise RuntimeError("Did not start server!  Woe!\n" + output)
            self.process = process
            return

        start = time.time()
        while process.poll() is None and time.time() - start < 15:
            if self.network_ping():
                break
        else:
            output = process.communicate()[0]
            raise RuntimeError("Did not start server!  Woe!\n" + output)
        self.process = process

    def stop(self):
        """Stop the process."""
        if not self.process:
            return
        try:
            self.process.terminate()
        except AttributeError:
            import os
            import signal
            os.kill(self.process.pid, signal.SIGQUIT)
        for i in xrange(20):
            if self.process.poll() is not None:
                break
            time.sleep(0.1)
        else:
            try:
                self.process.kill()
            except AttributeError:
                import os
                os.kill(self.process.pid, signal.SIGKILL)
        self.process = None

    def network_ping(self):
        """Return True if the :attr:`host` accepts connects on :attr:`port`."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.host, self.port))
            sock.shutdown(socket.SHUT_RDWR)
        except (IOError, socket.error):
            return False
        else:
            return True
        finally:
            del sock

########NEW FILE########
__FILENAME__ = _compat
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Glue code for Python version compatibility."""

_json = None

try:
    property.getter
except AttributeError:
    class property(property):
        """A work-alike for Python 2.6's property."""
        __slots__ = ()

        def getter(self, fn):
            return property(fn, self.fset, self.fdel)

        def setter(self, fn):
            return property(self.fget, fn, self.fdel)

        def deleter(self, fn):
            return property(self.fget, self.fset, fn)
else:
    property = property


def _load_json():
    global _json
    if _json is None:
        try:
            import json as _json
        except ImportError:
            try:
                import simplejson as _json
            except ImportError:
                pass
        if not _json:
            raise ImportError(
                "This feature requires Python 2.6+ or simplejson.")


def json_loads(*args, **kw):
    if _json is None:
        _load_json()
    return _json.loads(*args, **kw)


def json_dumps(*args, **kw):
    if _json is None:
        _load_json()
    return _json.dumps(*args, **kw)

########NEW FILE########
__FILENAME__ = _config
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""INI helpers."""
import ConfigParser
from StringIO import StringIO


class Configuration(ConfigParser.SafeConfigParser):
    """Alfajor run-time configuration."""

    _default_config = """\
[default]
wsgi = wsgi
* = selenium

[default+browser.zero]
    """

    def __init__(self, file):
        ConfigParser.SafeConfigParser.__init__(self)
        self.readfp(StringIO(self._default_config))
        if not self.read(file):
            raise IOError("Could not open config file %r" % file)
        self.source = file

    def get_section(self, name, default=None,
                    template='%(name)s', logger=None, fallback=None, **kw):
        section_name = template % dict(kw, name=name)
        try:
            return dict(self.items(section_name))
        except ConfigParser.NoSectionError:
            pass

        msg = "Configuration %r does not contain section %r" % (
            self.source, section_name)

        if fallback and fallback != name:
            try:
                section = self.get_section(fallback, default, template,
                                           logger, **kw)
            except LookupError:
                pass
            else:
                if logger:
                    fallback_name = fallback % dict(kw, name=fallback)
                    logger.debug("%s, falling back to %r" % (
                        msg, section_name, fallback_name))
                return section
        if default is not None:
            if logger:
                    logger.debug(msg + ", using default.")
            return default
        raise LookupError(msg)

########NEW FILE########
__FILENAME__ = _management
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'Alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

"""Routines for discovering and preparing backend managers."""
import inspect
from logging import getLogger
from os import path

from alfajor.utilities import eval_dotted_path
from alfajor._config import Configuration


__all__ = [
    'APIClient',
    'ManagerLookupError',
    'WebBrowser',
    'new_manager',
    ]

_default_logger = getLogger('alfajor')

managers = {
    'browser': {
        'selenium': 'alfajor.browsers.managers:SeleniumManager',
        'wsgi': 'alfajor.browsers.managers:WSGIManager',
        'network': 'alfajor.browsers.managers:NetworkManager',
        'zero': 'alfajor.browsers.managers:ZeroManager',
        },
    'apiclient': {
        'wsgi': 'alfajor.apiclient:WSGIClientManager',
        },
    }


try:
    import pkg_resources
except ImportError:
    pass
else:
    for tool in 'browser', 'apiclient':
        group = 'alfajor.' + tool
        for entrypoint in pkg_resources.iter_entry_points(group=group):
            try:
                entry = entrypoint.load()
            except Exception, exc:
                _default_logger.error("Error loading %s: %s", entrypoint, exc)
            else:
                managers[tool][entrypoint.name] = entry


class ManagerLookupError(Exception):
    """Raised if a declaration could not be resolved."""


def new_manager(declaration, runner_options, logger=None):
    try:
        factory = _ManagerFactory(declaration, runner_options, logger)
        return factory.get_instance()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception, exc:
        raise ManagerLookupError(exc)


class _DeferredProxy(object):
    """Fronts for another, created-on-demand instance."""

    def __init__(self):
        self._factory = None
        self._instance = None

    def _get_instance(self):
        if self._instance is not None:  # pragma: nocover
            return self._instance
        if self._factory is None:
            raise RuntimeError("%s is not configured." % type(self).__name__)
        self._instance = instance = self._factory()
        return instance

    def __getattr__(self, key):
        if self._instance is None:
            instance = self._get_instance()
        else:
            instance = self._instance
        return getattr(instance, key)

    def configure_in_scope(self, configuration='default', default_target=None,
                           ini_file=None):
        namespace = inspect.stack()[1][0].f_globals
        setups = namespace.setdefault('__alfajor_setup__', [])
        configuration = Declaration(proxy=self,
                                    configuration=configuration,
                                    default_target=default_target,
                                    ini_file=ini_file,
                                    tool=self.tool,
                                    declared_in=namespace.get('__file__'))
        setups.append(configuration)


class WebBrowser(_DeferredProxy):
    """A web browser for functional tests.

    Acts as a shell around a specific backend browser implementation,
    allowing a browser instance to be imported into a test module's
    namespace before configuration has been processed.

    """
    tool = 'browser'

    def __contains__(self, needle):
        browser = self._get_instance()
        return needle in browser


class APIClient(_DeferredProxy):
    """A wire-level HTTP client for functional tests.

    Acts as a shell around a demand-loaded backend implementation, allowing a
    client instance to be imported into a test module's namespace before
    configuration has been processed.
    """
    tool = 'apiclient'


class Declaration(object):

    def __init__(self, proxy, configuration, default_target, ini_file,
                 tool, declared_in):
        self.proxy = proxy
        self.configuration = configuration
        self.default_target = default_target
        self.ini_file = ini_file
        self.tool = tool
        self.declared_in = declared_in


class _ManagerFactory(object):
    """Encapsulates the process of divining and loading a backend manager."""
    _configs = {}

    def __init__(self, declaration, runner_options, logger=None):
        self.declaration = declaration
        self.runner_options = runner_options
        self.logger = logger or _default_logger
        self.config = self._get_configuration(declaration)
        self.name = declaration.configuration

    def get_instance(self):
        """Return a ready to instantiate backend manager callable.

        Will raise errors if problems are encountered during discovery.

        """
        frontend_name = self._get_frontend_name()
        backend_name = self._get_backend_name(frontend_name)
        tool = self.declaration.tool

        try:
            manager_factory = self._load_backend(tool, backend_name)
        except KeyError:
            raise KeyError("No known backend %r in configuration %r" % (
                backend_name, self.config.source))

        backend_config = self.config.get_section(
            self.name, template='%(name)s+%(tool)s.%(backend)s',
            tool=tool, backend=backend_name,
            logger=self.logger, fallback='default')

        return manager_factory(frontend_name,
                               backend_config,
                               self.runner_options)

    def _get_configuration(self, declaration):
        """Return a Configuration applicable to *declaration*.

        Configuration may come from a declaration option, a runner option
        or the default.

        """
        # --alfajor-config overrides any config data in code
        if self.runner_options['ini_file']:
            finder = self.runner_options['ini_file']
        # if not configured in code, look for 'alfajor.ini' or a declared path
        # relative to the file the declaration was made in.
        else:
            finder = path.abspath(
                path.join(path.dirname(declaration.declared_in),
                          (declaration.ini_file or 'alfajor.ini')))
        # TODO: empty config
        try:
            return self._configs[finder]
        except KeyError:
            config = Configuration(finder)
            self._configs[finder] = config
            return config

    def _get_frontend_name(self):
        """Return the frontend requested by the runner or declaration."""
        runner_override = self.declaration.tool + '_frontend'
        frontend = self.runner_options.get(runner_override)
        if not frontend:
            frontend = self.declaration.default_target
        if not frontend:
            frontend = 'default'
        return frontend

    def _get_backend_name(self, frontend):
        """Return the backend name for *frontend*."""
        if frontend == 'default':
            defaults = self.config.get_section('default-targets', default={})
            key = '%s+%s' % (self.declaration.configuration,
                             self.declaration.tool)
            if key not in defaults:
                key = 'default+%s' % (self.declaration.tool,)
            try:
                frontend = defaults[key]
            except KeyError:
                raise LookupError("No default target declared.")
        mapping = self.config.get_section(self.name, fallback='default')
        try:
            return mapping[frontend]
        except KeyError:
            return mapping['*']

    def _load_backend(self, tool, backend):
        """Load a *backend* callable for *tool*.

        Consults the [tool.backends] section of the active configuration
        first for a "tool = evalable.dotted:path" entry.  If not found,
        looks in the process-wide registry of built-in and pkg_resources
        managed backends.

        A config entry will override an equivalently named process entry.

        """
        point_of_service_managers = self.config.get_section(
            '%(tool)s.backends', default={}, logger=self.logger,
            tool=tool)
        try:
            entry = point_of_service_managers[backend]
        except KeyError:
            pass
        else:
            if callable(entry):
                return entry
            else:
                return eval_dotted_path(entry)

        entry = managers[tool][backend]
        if callable(entry):
            return entry
        fn = eval_dotted_path(entry)
        managers[tool].setdefault(backend, fn)
        return fn

########NEW FILE########
__FILENAME__ = test_simple
from docs.examples import browser, browser_test


@browser_test()
def test_entering_name():
    browser.open('/')
    assert 'Alfajor' in browser.document['#mainTitle'].text_content
    browser.document['form input[name="name"]'][0].value = 'Juan'
    browser.document['button'][0].click()
    assert 'Juan' in browser.document['h1'][0].text_content

########NEW FILE########
__FILENAME__ = webapp
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

import os
import tempfile

from werkzeug import Response, Request, Template
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.routing import Map, Rule


class WebApp(object):

    url_map = Map([
        Rule('/', endpoint='index'),
        Rule('/results', endpoint='results'),
        ])

    def __call__(self, environ, start_response):
        request = Request(environ)
        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
        except NotFound, exc:
            args = {}
            endpoint = '/'
        environ['routing_args'] = args
        environ['endpoint'] = endpoint

        try:
            response = self.template_renderer(request)
        except HTTPException, exc:
            # ok, maybe it really was a bogus URL.
            return exc(environ, start_response)
        return response(environ, start_response)

    def template_renderer(self, request):
        endpoint = request.environ['endpoint']
        path = '%s/templates/%s.html' % (
            os.path.dirname(__file__), endpoint)
        try:
            source = open(path).read()
        except IOError:
            raise NotFound()
        template = Template(source)
        handler = getattr(self, endpoint, None)
        context = dict()
        if handler:
            handler(request, context)
        print context
        body = template.render(context)
        return Response(body, mimetype='text/html')

    def results(self, request, context):
        context.update(
            name=request.args.get('name', 'Che'),
        )


def webapp():
    return WebApp()


def run(bind_address='0.0.0.0', port=8009):
    """Run the webapp in a simple server process."""
    from werkzeug import run_simple
    print "* Starting on %s:%s" % (bind_address, port)
    run_simple(bind_address, port, webapp(),
               use_reloader=False, threaded=True)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Alfajor documentation build configuration file

from os import path
import sys

sys.path.append(path.abspath(path.dirname(__file__) + "../../../"))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest',
              'sphinx.ext.coverage',
              'sphinx.ext.inheritance_diagram']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Alfajor'
copyright = '2011, the Alfajor authors and contributors'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = 'tip'
# The full version, including alpha/beta/rc tags.
release = 'tip'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
exclude_dirs = ['doctest']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# fails to parse :arg foo: in __init__ docs :(
#autoclass_content = 'both'

# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
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
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'alfajordoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'alfajor.tex', 'Alfajor Documentation',
   'The Alfajor Team', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

autodoc_member_order = 'groupwise'

########NEW FILE########
__FILENAME__ = test_browser
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.
import time

from nose.tools import raises

from . import browser, browser_test, screenshot_fails


@browser_test()
def test_simple():
    browser.open('/')

    if 'status' in browser.capabilities:
        assert browser.status_code == 200
        assert browser.status == '200 OK'
    if 'headers' in browser.capabilities:
        assert 'text/html' in browser.headers['Content-Type']
    assert not browser.cookies

    # This is generally not a safe assertion... the browser could (and does)
    # normalize the returned html in some fashion.
    assert browser.response == ('<html><head></head>'
                                '<body><p>hi there</p></body></html>')

    assert browser.document.cssselect('p')[0].text == 'hi there'


@browser_test()
def test_reset():
    # TODO: flesh this out when cookie querying is working and has
    # test coverage.  until then, just verify that the method doesn't
    # explode.
    browser.open('/')


@browser_test()
def test_user_agent():
    browser.open('/')
    ua = browser.user_agent
    assert ua['browser'] != 'unknown'


@browser_test()
def test_traversal():
    browser.open('/seq/a')
    a_id = browser.document['#request_id'].text
    assert browser.cssselect('title')[0].text == 'seq/a'
    assert browser.location.endswith('/seq/a')
    assert not browser.cssselect('p.referrer')[0].text

    browser.cssselect('a')[0].click(wait_for='page')
    b_id = browser.document['#request_id'].text
    assert a_id != b_id
    assert browser.cssselect('title')[0].text == 'seq/b'
    assert browser.location.endswith('/seq/b')
    assert '/seq/a' in browser.cssselect('p.referrer')[0].text

    # bounce through a redirect
    browser.cssselect('a')[0].click(wait_for='page')
    d_id = browser.document['#request_id'].text
    assert d_id != b_id
    assert browser.cssselect('title')[0].text == 'seq/d'
    assert browser.location.endswith('/seq/d')
    assert '/seq/b' in browser.cssselect('p.referrer')[0].text


@browser_test()
def _test_single_cookie(bounce):
    browser.open('/')
    assert not browser.cookies

    if bounce:
        landing_page = browser.location
        browser.open('/assign-cookie/1?bounce=%s' % landing_page)
    else:
        browser.open('/assign-cookie/1')

    assert browser.cookies == {'cookie1': 'value1'}

    browser.reset()
    assert not browser.cookies

    browser.open('/')
    assert not browser.cookies


@browser_test()
def test_single_cookie():
    yield _test_single_cookie, False
    yield _test_single_cookie, True


@browser_test()
def _test_multiple_cookies(bounce):
    browser.open('/')
    assert not browser.cookies

    if bounce:
        landing_page = browser.location
        browser.open('/assign-cookie/2?bounce=%s' % landing_page)
    else:
        browser.open('/assign-cookie/2')

    assert browser.cookies == {'cookie1': 'value1',
                               'cookie2': 'value 2'}

    browser.reset()
    assert not browser.cookies

    browser.open('/')
    assert not browser.cookies


@browser_test()
def test_multiple_cookies():
    yield _test_multiple_cookies, False
    yield _test_multiple_cookies, True


@browser_test()
def test_wait_for():
    # bare minimum no side-effects call browser.wait_for
    browser.wait_for('duration', 1)


@browser_test()
def test_wait_for_duration():
    if 'selenium' in browser.capabilities:
        start = time.time()
        browser.open('/waitfor', wait_for='duration', timeout=1000)
        duration = time.time() - start
        assert duration >= 1


@browser_test()
def test_wait_for_element():
    if 'selenium' in browser.capabilities:
        browser.open('/waitfor')
        browser.cssselect('a#appender')[0].click(
            wait_for='element:css=#expected_p', timeout=3000)
        assert browser.cssselect('#expected_p')


@browser_test()
@raises(AssertionError)
def test_wait_for_element_not_found():
    if 'selenium' in browser.capabilities:
        browser.open('/waitfor')
        browser.wait_for('element:css=#unexisting', timeout=10)
    else:
        raise AssertionError('Ignore if not selenium')


@browser_test()
def test_wait_for_element_not_present():
    if 'selenium' in browser.capabilities:
        browser.open('/waitfor')
        assert browser.cssselect('#removeme')
        browser.cssselect('#remover')[0].click(
            wait_for='!element:css=#removeme', timeout=3000)
        assert not browser.cssselect('#removeme')


@browser_test()
def test_wait_for_ajax():
    if 'selenium' in browser.capabilities:
        browser.open('/waitfor')
        browser.cssselect('#ajaxappender')[0].click(
            wait_for='ajax', timeout=3000)
        assert len(browser.cssselect('.ajaxAdded')) == 3


@browser_test()
def test_wait_for_js():
    if 'selenium' in browser.capabilities:
        browser.open('/waitfor')
        browser.cssselect('#counter')[0].click(
            wait_for='js:window.exampleCount==100;', timeout=3000)


@browser_test()
def test_set_cookie():
    if 'cookies' in browser.capabilities:
        browser.open('/')

        browser.set_cookie('foo', 'bar')
        browser.set_cookie('py', 'py', 'localhost.local', port='8008')
        browser.set_cookie('green', 'frog',
                           session=False, expires=time.time() + 3600)
        assert 'foo' in browser.cookies
        assert 'py' in browser.cookies
        assert 'green' in browser.cookies


@browser_test()
@screenshot_fails('test_screenshot.png')
def test_screenshot():
    if 'javascript' not in browser.capabilities:
        return
    browser.open('http://www.google.com')
    assert False

########NEW FILE########
__FILENAME__ = test_dom
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

from . import browser


def test_indexing():
    browser.open('/dom')
    doc = browser.document

    assert doc['#A'].tag == 'dl'
    assert doc['dl#A'].tag == 'dl'
    assert doc['body #A'].tag == 'dl'
    assert isinstance(doc['#A ul'], list)
    assert isinstance(doc['body #A ul'], list)
    assert doc['#C'][0].text == '1'
    assert len(doc['#C']['li']) == 2


def test_containment():
    browser.open('/dom')
    doc = browser.document

    assert 'dl' in doc
    assert '#C' in doc
    assert not '#C div' in doc
    assert 'li' in doc
    assert not 'div' in doc
    assert doc['body'][0] in doc
    assert not doc['#B'] in doc
    assert 0 in doc
    assert not 2 in doc


def test_xpath():
    browser.open('/dom')
    doc = browser.document

    assert doc['#A'].fq_xpath == '/html/body/dl'
    assert doc.xpath('/html/body/dl')[0] is doc['#A']


def test_innerhtml():
    browser.open('/dom')
    ps = browser.document['p']

    assert ps[0].innerHTML == 'msg 1'
    assert ps[1].innerHTML == 'msg<br>2'
    assert ps[2].innerHTML == 'msg<br>&amp;<br>3'
    assert ps[3].innerHTML == '<b>msg 4</b>'


def test_text_content():
    browser.open('/dom')
    ps = browser.document['p']

    assert ps[0].text_content == 'msg 1'
    assert ps[1].text_content == 'msg2'
    assert ps[2].text_content == 'msg&3'
    assert ps[2].text_content() == 'msg&3'
    assert ps[2].text == 'msg'
    assert ps[3].text_content == 'msg 4'


def test_visibility():
    browser.open('/dom')
    p = browser.document['p.hidden'][0]
    if 'visibility' in browser.capabilities:
        assert not p.is_visible
    else:
        assert p.is_visible

########NEW FILE########
__FILENAME__ = test_forms
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

from alfajor._compat import json_loads as loads

from nose.tools import eq_, raises

from . import browser


def test_get():
    for index in 0, 1, 2:
        browser.open('/form/methods')
        assert browser.document['#get_data'].text == '[]'
        data = {
            'first_name': 'Tester',
            'email': 'tester@tester.com',
        }
        form = browser.document.forms[index]
        form.fill(data)
        form.submit(wait_for='page')
        get = loads(browser.document['#get_data'].text)
        post = loads(browser.document['#post_data'].text)
        assert get == [['email', 'tester@tester.com'],
                       ['first_name', 'Tester']]
        assert not post


def test_get_qs_append():
    browser.open('/form/methods?stuff=already&in=querystring')
    form = browser.document.forms[3]
    form.submit(wait_for='page')
    get = loads(browser.document['#get_data'].text)
    post = loads(browser.document['#post_data'].text)
    assert sorted(get) == [['email', ''], ['first_name', '']]
    assert post == []

    browser.open('/form/methods?stuff=already&in=querystring')
    form = browser.document.forms[3]
    form.fill({'email': 'snorgle'})
    form.submit(wait_for='page')
    get = loads(browser.document['#get_data'].text)
    post = loads(browser.document['#post_data'].text)
    assert sorted(get) == [['email', 'snorgle'], ['first_name', '']]
    assert post == []


def test_post():
    browser.open('/form/methods')
    assert browser.document['#post_data'].text == '[]'
    data = {
        'first_name': 'Tester',
        'email': 'tester@tester.com',
    }
    form = browser.document.forms[4]
    form.fill(data)
    form.submit(wait_for='page')
    get = loads(browser.document['#get_data'].text)
    post = loads(browser.document['#post_data'].text)
    assert not get
    assert sorted(post) == [['email', 'tester@tester.com'],
                            ['first_name', 'Tester']]


def test_post_qs_append():
    browser.open('/form/methods?x=y')
    assert browser.document['#post_data'].text == '[]'
    data = {
        'first_name': 'Tester',
        'email': 'tester@tester.com',
    }
    form = browser.document.forms[5]
    form.fill(data)
    form.submit(wait_for='page')
    get = loads(browser.document['#get_data'].text)
    post = loads(browser.document['#post_data'].text)
    assert sorted(get) == [['x', 'y']]
    assert sorted(post) == [['email', 'tester@tester.com'],
                            ['first_name', 'Tester']]

    browser.open('/form/methods?x=y&email=a')
    assert browser.document['#post_data'].text == '[]'
    data = {
        'first_name': 'Tester',
        'email': 'tester@tester.com',
    }
    form = browser.document.forms[5]
    form.fill(data)
    form.submit(wait_for='page')
    get = loads(browser.document['#get_data'].text)
    post = loads(browser.document['#post_data'].text)
    assert sorted(get) == [['email', 'a'], ['x', 'y']]
    assert sorted(post) == [['email', 'tester@tester.com'],
                            ['first_name', 'Tester']]


def test_submit_buttonless():
    for idx in 0, 1:
        browser.open('/form/submit')
        browser.document.forms[idx].submit(wait_for='page')
        data = loads(browser.document['#data'].text)
        assert data == [['search', '']]


def test_nameless_submit_button():
    for idx in 2, 3:
        browser.open('/form/submit')
        button = browser.document.forms[idx]['input[type=submit]'][0]
        button.click(wait_for='page')
        data = loads(browser.document['#data'].text)
        assert data == [['search', '']]


def test_named_submit_button():
    for idx in 4, 5, 6:
        browser.open('/form/submit')
        assert browser.document['#method'].text == 'GET'
        button = browser.document.forms[idx]['input[type=submit]'][0]
        button.click(wait_for='page')
        assert browser.document['#method'].text == 'POST'
        data = loads(browser.document['#data'].text)
        assert sorted(data) == [['search', ''], ['submitA', 'SubmitA']]


def test_valueless_submit_button():
    browser.open('/form/submit')
    button = browser.document.forms[7]['input[type=submit]'][0]
    button.click(wait_for='page')
    data = loads(browser.document['#data'].text)
    assert len(data) == 2
    data = dict(data)
    assert data['search'] == ''
    # the value sent is browser implementation specific.  could be
    # Submit or Submit Query or ...
    assert data['submitA'] and data['submitA'] != ''


def test_multielement_submittal():
    browser.open('/form/submit')
    assert browser.document['#method'].text == 'GET'

    browser.document.forms[8].submit(wait_for='page')
    assert browser.document['#method'].text == 'POST'
    data = loads(browser.document['#data'].text)
    assert sorted(data) == [['x', ''], ['y', '']]

    browser.open('/form/submit')
    assert browser.document['#method'].text == 'GET'
    button = browser.document.forms[8]['input[type=submit]'][0]
    button.click(wait_for='page')
    assert browser.document['#method'].text == 'POST'
    data = loads(browser.document['#data'].text)
    assert sorted(data) == [['submitA', 'SubmitA'], ['x', ''], ['y', '']]


def test_textarea():
    browser.open('/form/textareas')
    browser.document.forms[0].submit(wait_for='page')
    data = loads(browser.document['#data'].text_content)
    assert data == [['ta', '']]

    browser.document.forms[0]['textarea'][0].value = 'foo\r\nbar'
    browser.document.forms[0].submit(wait_for='page')
    data = loads(browser.document['#data'].text_content)
    assert data == [['ta', 'foo\r\nbar']]

    textarea = browser.document.forms[0]['textarea'][0]
    textarea.enter('baz')
    # NOTE: Webkit Selenium Browsers seem to trim the string on returned
    # values (get).  Therefore do not end this test with a whitespace char.
    textarea.enter('\r\nquuX\r\nY')
    textarea.enter('\x08\x08\x08x')
    browser.document.forms[0].submit(wait_for='page')
    data = loads(browser.document['#data'].text_content)
    assert data == [['ta', 'baz\r\nquux']]

def test_multipart_simple():
    if 'upload' not in browser.capabilities:
        return

    browser.open('/form/multipart')
    data = loads(browser.document['#data'].text_content)
    assert data == []

    browser.document.forms[0]['input[name=search]'][0].value = 'foobar'
    browser.document.forms[0].submit(wait_for='page')
    data = loads(browser.document['#data'].text_content)
    assert data == [['search', 'foobar']]


def test_formless_submit_button():
    browser.open('/form/submit')
    assert browser.document['#method'].text == 'GET'
    request_id = browser.document['#request_id'].text

    browser.document['#floater'].click()
    assert browser.document['#request_id'].text == request_id


def test_select_default_initial_empty():
    browser.open('/form/select')
    browser.document.forms[0]['input[type=submit]'][0].click()
    data = loads(browser.document['#data'].text)
    assert data == [['sel', '']]


def _test_select(form_num, fieldname, value, expected_return):
    """Repeat tests with multiple lxml <select> value setting strategies."""

    def set_value():
        browser.document.forms[form_num]['select'][0].value = value

    def assign_to_field():
        browser.document.forms[form_num].fields[fieldname] = value

    def fill():
        browser.document.forms[form_num].fill({fieldname: value})

    for strategy in set_value, assign_to_field, fill:
        browser.open('/form/select')
        strategy()
        browser.document.forms[form_num]['input[type=submit]'][0].click()
        data = loads(browser.document['#data'].text)
        if isinstance(expected_return, basestring):
            expected_return = [expected_return]
        eq_(sorted(data), [[fieldname, val]
            for val in sorted(expected_return)])


def test_select_empty():
    _test_select(0, 'sel', None, '')


def test_select_empty_value():
    _test_select(1, 'sel', '', '')


def test_select_value_only():
    _test_select(0, 'sel', 'val_only', 'val_only')


def test_select_text_only():
    _test_select(0, 'sel', 'text only', 'text only')


def test_select_combo():
    _test_select(0, 'sel', 'combo', 'combo')


def test_select_multiple():
    _test_select(2, 'multi_sel', ['first', 'third'],
                ['first', 'third'])


def test_select_multiple_value_only_and_others():
    _test_select(2, 'multi_sel', ['second', 'Fourth option'],
                    ['second', 'Fourth option'])


def test_basic_checkbox_state():
    browser.open('/form/checkboxes')
    fields = browser.document['form'][0]['input[type=checkbox]']
    assert not fields[0].checked
    assert not fields[1].checked
    assert not fields[2].checked
    assert fields[3].checked

    assert fields[3].value == 'x4'

    fields[2].checked = True
    fields[3].checked = False
    assert fields[3].value == 'x4'

    assert fields[2].checked
    assert not fields[3].checked

    fields[3].checked = True

    assert fields[3].value == 'x4'


def test_checkbox_indirection():
    browser.open('/form/checkboxes')

    form = browser.document.forms[1]
    assert form.fields['y'] == ''
    assert form.fields['z'] == 'z1'

    form.fields['y'] = 'y1'
    form.fields['z'] = False

    assert form.fields['y'] == 'y1'
    assert form.inputs['y'][0].checked
    assert form.inputs['y'][0].value == 'y1'

    assert form.fields['z'] == ''
    assert not form.inputs['z'][0].checked
    assert form.inputs['z'][0].value == 'z1'

    form.fields['y'] = ''
    form.fields['z'] = True

    assert form.fields['y'] == ''
    assert not form.inputs['y'][0].checked
    assert form.inputs['y'][0].value == 'y1'

    assert form.fields['z'] == 'z1'
    assert form.inputs['z'][0].checked
    assert form.inputs['z'][0].value == 'z1'

    form.fields = {'y': 'y1', 'z': ''}

    assert form.fields['y'] == 'y1'
    assert form.inputs['y'][0].checked
    assert form.inputs['y'][0].value == 'y1'

    assert form.fields['z'] == ''
    assert not form.inputs['z'][0].checked
    assert form.inputs['z'][0].value == 'z1'


def _test_checkbox(form_num, field_num, value, expected_return):

    def _checkbox():
        boxes = browser.document.forms[form_num]['input[type=checkbox]']
        return boxes[field_num]

    def set_checked():
        _checkbox().checked = value

    def set_checked_bool():
        _checkbox().checked = bool(value)

    def click():
        _checkbox().click()

    for strategy in (set_checked, set_checked_bool, click):
        browser.open('/form/checkboxes')
        strategy()
        fieldname = _checkbox().name
        browser.document.forms[form_num]['input[type=submit]'][0].click()
        data = loads(browser.document['#data'].text_content)
        if expected_return:
            assert [fieldname, expected_return] in data
        else:
            assert fieldname not in dict(data).keys()


def _test_checkbox_container_assignment(form_num, fieldname, value,
                                        expected_return):

    def assign_to_field():
        form = browser.document.forms[form_num]
        # fields[fieldname] can be a set-like CheckboxGroup & set with a seq
        form.fields[fieldname] = value

    def fill():
        browser.document.forms[form_num].fill({fieldname: value})

    for strategy in (assign_to_field, fill):
        browser.open('/form/checkboxes')
        strategy()
        browser.document.forms[form_num]['input[type=submit]'][0].click()
        data = loads(browser.document['#data'].text_content)
        if expected_return:
            if isinstance(expected_return, list):
                # ['m1', 'm2']
                for er in expected_return:
                    assert [fieldname, er] in data
            else:
                # 'm1'
                assert [fieldname, expected_return] in data
        else:
            # ''
            assert fieldname not in dict(data).keys()


def test_checkbox_interaction():
    yield _test_checkbox, 1, 0, 'y1', 'y1'
    yield _test_checkbox_container_assignment, 1, 'y', 'y1', 'y1'
    yield _test_checkbox, 1, 1, '', None
    yield _test_checkbox_container_assignment, 1, 'z', '', None

    yield _test_checkbox, 2, 0, 'm1', 'm1'
    yield _test_checkbox_container_assignment, 2, 'm', ['m1'], ['m1']
    yield _test_checkbox_container_assignment, 2, 'm', ['m1', 'm3'], \
          ['m1', 'm3']


def test_basic_radio_state():
    browser.open('/form/radios')
    form = browser.document['form'][0]
    fields = form['input[type=radio]']

    assert not fields[0].checked
    assert not fields[1].checked
    assert not fields[2].checked
    assert fields[3].checked
    assert fields[3].value == 'x4'
    assert form.form_values() == [('x', 'x4')]

    fields[2].checked = True
    assert fields[2].checked
    assert not fields[3].checked
    assert fields[3].value == 'x4'
    assert form.form_values() == [('x', 'x3')]

    fields[3].checked = True
    assert form.form_values() == [('x', 'x4')]

    # can't uncheck a radio box
    fields[3].checked = False
    assert form.form_values() == [('x', 'x4')]

    form.submit(wait_for='page')
    data = loads(browser.document['#data'].text_content)
    assert data == [['x', 'x4']]


def _test_radio(form_num, field_num, value, expected_return):

    def _radio():
        boxes = browser.document.forms[form_num]['input[type=radio]']
        return boxes[field_num]

    def set_checked():
        _radio().checked = value

    def set_checked_bool():
        _radio().checked = bool(value)

    def click():
        _radio().click()

    def assign_to_field():
        form = browser.document.forms[form_num]
        form.fields[fieldname] = value

    def fill():
        browser.document.forms[form_num].fill({fieldname: value})

    for strategy in (set_checked, set_checked_bool, click):
        browser.open('/form/radios')
        strategy()
        fieldname = _radio().name
        browser.document.forms[form_num]['input[type=submit]'][0].click()
        data = loads(browser.document['#data'].text_content)
        if expected_return:
            assert [fieldname, expected_return] in data
        else:
            assert fieldname not in dict(data).keys()


def test_radio_interaction():
    # clears default
    yield _test_radio, 0, 0, 'x1', 'x1'

    # no default
    yield _test_radio, 1, 2, 'm3', 'm3'


@raises(KeyError)
def test_fill_field_not_found():
    browser.open('/form/select')
    browser.document.forms[0].fill({'unexisting': None})


@raises(ValueError)
def test_fill_option_not_found():
    browser.open('/form/select')
    browser.document.forms[0].fill({'sel': 'unexisting'})


def test_fill_ordering():
    browser.open('/form/fill')
    assert browser.document['#data'].text == '[]'
    data = {
        'language': 'espa',
        'derivate': 'lunf',
        'subderivate': 'rosa',
        }
    form = browser.document.forms[0]
    try:
        form.fill(data, wait_for='ajax', timeout=1000)
    except ValueError:
        assert 'javascript' not in browser.capabilities
    else:
        form.submit(wait_for='page')
        args_string = browser.document['#data'].text
        assert 'espa' in args_string
        assert 'lunf' in args_string
        assert 'rosa' in args_string


def test_fill_prefixes_dict():
    browser.open('/form/fill')
    assert browser.document['#data'].text == '[]'
    data = {
        'a': 'abc',
        'xx_b': 'def',
        'boxes': ['1', '3'],
        }
    form = browser.document.forms[1]
    form.fill(data, with_prefix='xx_')
    form.submit(wait_for='page')
    roundtrip = loads(browser.document['#data'].text_content)

    assert sorted(roundtrip) == [
        ['xx_a', 'abc'],
        ['xx_b', 'def'],
        ['xx_boxes', '1'],
        ['xx_boxes', '3'],
        ]


def test_fill_prefixes_sequence():
    browser.open('/form/fill')
    assert browser.document['#data'].text == '[]'
    data = [
        ['xx_a', 'abc'],
        ['boxes', '1'],
        ['b', 'def'],
        ['xx_boxes', '3'],
        ]
    form = browser.document.forms[1]
    form.fill(data, with_prefix='xx_')
    form.submit(wait_for='page')
    roundtrip = loads(browser.document['#data'].text_content)

    assert sorted(roundtrip) == [
        [u'xx_a', u'abc'],
        [u'xx_b', u'def'],
        [u'xx_boxes', u'1'],
        [u'xx_boxes', u'3'],
        ]

########NEW FILE########
__FILENAME__ = webapp
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

import os
import tempfile

from werkzeug import Response, Request, SharedDataMiddleware, Template
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.routing import Map, Rule

from alfajor._compat import json_dumps as dumps


class WebApp(object):

    url_map = Map([
        # Uurls like /form/fill get turned into templates/form_fill.html
        # automatically in __call__ and don't need a Rule & endpoint.
        #
        # We only need Rules and endpoints for alternate mappings or to do
        # dynamic processing.
        Rule('/', endpoint='index'),
        Rule('/assign-cookie/1', endpoint='assign_cookie'),
        Rule('/assign-cookie/2', endpoint='assign_cookies'),
        ])

    def __call__(self, environ, start_response):
        request = Request(environ)
        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
        except NotFound, exc:
            # Convert unknown /path/names into endpoints named path_names
            endpoint = request.path.lstrip('/').replace('/', '_')
            args = {}
        environ['routing_args'] = args
        environ['endpoint'] = endpoint

        try:
            # endpoints can be methods on this class
            handler = getattr(self, endpoint)
        except AttributeError:
            # or otherwise assumed to be files in templates/<endpoint>.html
            handler = self.generic_template_renderer
        self.call_count = getattr(self, 'call_count', 0) + 1
        try:
            response = handler(request)
        except HTTPException, exc:
            # ok, maybe it really was a bogus URL.
            return exc(environ, start_response)
        return response(environ, start_response)

    def generic_template_renderer(self, request):
        path = '%s/templates/%s.html' % (
            os.path.dirname(__file__), request.environ['endpoint'])
        try:
            source = open(path).read()
        except IOError:
            raise NotFound()
        template = Template(source)
        files = []
        for name, file in request.files.items():
            # Save the uploaded files to tmp storage.
            # The calling test should delete the files.
            fh, fname = tempfile.mkstemp()
            os.close(fh)
            file.save(fname)
            files.append(
                (name, (file.filename, file.content_type,
                        file.content_length, fname)))
        context = dict(
            request=request,
            request_id=self.call_count,
            args=dumps(sorted(request.args.items(multi=True))),
            form=dumps(sorted(request.form.items(multi=True))),
            data=dumps(sorted(request.args.items(multi=True) +
                              request.form.items(multi=True))),
            files=dumps(sorted(files)),
            referrer=request.referrer or '',
            #args=..
            )
        body = template.render(context)
        return Response(body, mimetype='text/html')

    def seq_c(self, request):
        rsp = self.generic_template_renderer(request)
        rsp.status = '301 Redirect'
        rsp.location = request.host_url.rstrip('/') + '/seq/d'
        return rsp

    def assign_cookie(self, request):
        rsp = self.generic_template_renderer(request)
        rsp.set_cookie('cookie1', 'value1', path='/')

        if request.args.get('bounce'):
            rsp.status = '301 Redirect'
            rsp.location = request.args['bounce']
        return rsp

    def assign_cookies(self, request):
        rsp = self.generic_template_renderer(request)
        rsp.set_cookie('cookie1', 'value1', path='/')
        rsp.set_cookie('cookie2', 'value 2', path='/')
        if request.args.get('bounce'):
            rsp.status = '301 Redirect'
            rsp.location = request.args['bounce']
        return rsp


def webapp():
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    return SharedDataMiddleware(WebApp(), {'/javascript': static_path})


def run(bind_address='0.0.0.0', port=8008):
    """Run the webapp in a simple server process."""
    from werkzeug import run_simple
    print "* Starting on %s:%s" % (bind_address, port)
    run_simple(bind_address, port, webapp(),
               use_reloader=False, threaded=True)

########NEW FILE########
__FILENAME__ = test_basic
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

from tests.client import client


def test_simple_json_fetch():
    response = client.get('/json_data')
    assert response.is_json
    assert response.json['test'] == 'data'

########NEW FILE########
__FILENAME__ = webapp
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

import os
import tempfile

from werkzeug import Response, Request, Template
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.routing import Map, Rule

from alfajor._compat import json_dumps as dumps


class WebApp(object):

    url_map = Map([
        # Uurls like /form/fill get turned into templates/form_fill.html
        # automatically in __call__ and don't need a Rule & endpoint.
        #
        # We only need Rules and endpoints for alternate mappings or to do
        # dynamic processing.
        Rule('/', endpoint='index'),
        Rule('/json_data', endpoint='json_data'),
        ])

    def __call__(self, environ, start_response):
        request = Request(environ)
        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
        except NotFound, exc:
            # Convert unknown /path/names into endpoints named path_names
            endpoint = request.path.lstrip('/').replace('/', '_')
            args = {}
        environ['routing_args'] = args
        environ['endpoint'] = endpoint

        try:
            # endpoints can be methods on this class
            handler = getattr(self, endpoint)
        except AttributeError:
            # or otherwise assumed to be files in templates/<endpoint>.html
            handler = self.generic_template_renderer
        self.call_count = getattr(self, 'call_count', 0) + 1
        try:
            response = handler(request)
        except HTTPException, exc:
            # ok, maybe it really was a bogus URL.
            return exc(environ, start_response)
        return response(environ, start_response)

    def generic_template_renderer(self, request):
        path = '%s/templates/%s.html' % (
            os.path.dirname(__file__), request.environ['endpoint'])
        try:
            source = open(path).read()
        except IOError:
            raise NotFound()
        template = Template(source)
        files = []
        for name, file in request.files.items():
            # Save the uploaded files to tmp storage.
            # The calling test should delete the files.
            fh, fname = tempfile.mkstemp()
            os.close(fh)
            file.save(fname)
            files.append(
                (name, (file.filename, file.content_type,
                        file.content_length, fname)))
        context = dict(
            request=request,
            request_id=self.call_count,
            args=dumps(sorted(request.args.items(multi=True))),
            form=dumps(sorted(request.form.items(multi=True))),
            data=dumps(sorted(request.args.items(multi=True) +
                              request.form.items(multi=True))),
            files=dumps(sorted(files)),
            referrer=request.referrer or '',
            #args=..
            )
        body = template.render(context)
        return Response(body, mimetype='text/html')

    def json_data(self, request):
        body = dumps({'test': 'data'})
        return Response(body, mimetype='application/json')


def run(bind_address='0.0.0.0', port=8008):
    """Run the webapp in a simple server process."""
    from werkzeug import run_simple
    print "* Starting on %s:%s" % (bind_address, port)
    run_simple(bind_address, port, WebApp(),
               use_reloader=False, threaded=True)

########NEW FILE########
__FILENAME__ = test_management
# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.

from alfajor._management import _DeferredProxy

from nose.tools import assert_raises


def test_proxy_readiness():
    class Sentinel(object):
        prop = 123
    sentinel = Sentinel()

    proxy = _DeferredProxy()
    assert_raises(RuntimeError, getattr, proxy, 'prop')

    proxy = _DeferredProxy()
    proxy._factory = lambda: sentinel
    assert proxy.prop == 123

########NEW FILE########
