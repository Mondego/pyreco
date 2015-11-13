__FILENAME__ = auth
import json
import requests
from requests.auth import HTTPBasicAuth

class BaseAuth(object):
    def args_hook(self, args):
        pass

    def pre_request_hook(self, request):
        pass

    def response_hook(self, session, response):
        pass


class NullAuth(BaseAuth):
    pass


class BasicAuth(BaseAuth):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def args_hook(self, args):
        args['auth'] = HTTPBasicAuth(self.username, self.password)
        return args


class OAuth2Auth(BaseAuth):
    def __init__(self, access_token=None, refresh_token=None, scope=None,
                 client_id=None, client_secret=None, token_url=None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.scope = scope
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self._retry_count = 0

    def pre_request_hook(self, request):
        request.headers.setdefault('Authorization',
            'Bearer {0}'.format(self.access_token))

    def response_hook(self, session, response):
        if response.status_code == requests.codes.unauthorized:
            if self._retry_count >= 1:
                return
            self._retry_count += 1
            if self.refresh_credentials():
                return session.send(response.request)  # override response

    def refresh_credentials(self):
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope or ''
        }
        if hasattr(self, 'pre_refresh_callback'):
            self.pre_refresh_callback(data)
        res = requests.post(self.token_url, data=data)
        res.raise_for_status()
        if not res.ok:
            return False
        data = json.loads(res.text)
        if data.get('access_token'):
            self.access_token = data['access_token']
            self.refresh_token = data['refresh_token']
            if hasattr(self, 'post_refresh_callback'):
                return self.post_refresh_callback(data)
        return False

########NEW FILE########
__FILENAME__ = client
import requests
import json
import sys
import time

from .auth import BasicAuth, OAuth2Auth, NullAuth
from .response import *
from .errors import RESTAPIError


class RESTClient(object):
    def __init__(self, endpoint='https://rest.dotcloud.com/v1',
            debug=False, user_agent=None, version_checker=None):
        self.endpoint = endpoint
        self.debug = debug
        self.authenticator = NullAuth()
        self._make_session()
        self._user_agent = user_agent
        self._version_checker = version_checker
        if self.debug:
            requests.packages.urllib3.connectionpool.HTTPSConnection.debuglevel = 1
            requests.packages.urllib3.connectionpool.HTTPConnection.debuglevel = 1

    def make_prefix_client(self, prefix=''):
        subclient = RESTClient(
                endpoint='{endpoint}{prefix}'.format(
                    endpoint=self.endpoint, prefix=prefix),
                debug=self.debug, user_agent=self._user_agent,
                version_checker=self._version_checker)
        subclient.session = self.session
        subclient.authenticator = self.authenticator
        return subclient

    def _make_session(self):
        headers = {'Accept': 'application/json'}
        hooks = {
            'response': self._response_hook
        }
        self.session = requests.session()
        self.session.headers = headers
        self.session.hooks = hooks
        self.session.auth = self._request_hook

    def _request_hook(self, request):
        if self._user_agent:
            request.headers['User-Agent'] = self._user_agent

        self.authenticator.pre_request_hook(request)
        if self.debug:
            print >>sys.stderr, '### {method} {url} data={data}'.format(
                method  = request.method,
                url     = request.path_url,
                data    = request.body
            )
        return request

    def _response_hook(self, response, **kw):
        r = self.authenticator.response_hook(self.session, response)
        if self.debug:
            print >>sys.stderr, '### {code} TraceID:{trace_id}'.format(
                code=response.status_code,
                trace_id=response.headers['X-DotCloud-TraceID'])
        return r

    def build_url(self, path):
        if path == '' or path.startswith('/'):
            return self.endpoint + path
        else:
            return path

    def request(self, method, path, streaming=False, **kw):
        url = self.build_url(path)
        kw = self.authenticator.args_hook(kw) or kw

        def do_request():
            return self.make_response(
                    self.session.request(
                        method, url, stream=streaming, **kw),
                    streaming
                    )

        for i in range(4):
            try:
                return do_request()
            except requests.exceptions.RequestException:
                time.sleep(1)
        return do_request()

    def get(self, path='', streaming=False):
        return self.request('GET', path, streaming, timeout=180)

    def post(self, path='', payload={}):
        return self.request('POST', path,
                            data=json.dumps(payload), headers={'Content-Type': 'application/json'})

    def put(self, path='', payload={}):
        return self.request('PUT', path,
                            data=json.dumps(payload), headers={'Content-Type': 'application/json'})

    def delete(self, path=''):
        return self.request('DELETE', path, headers={'Content-Length': '0'})

    def patch(self, path='', payload={}):
        return self.request('PATCH', path,
                            headers={'Content-Type': 'application/json'},
                            data=json.dumps(payload),
                            )

    def make_response(self, res, streaming=False):
        trace_id = res.headers.get('X-DotCloud-TraceID')
        if res.headers['Content-Type'] == 'application/json':
            pass
        elif res.status_code == requests.codes.no_content:
            return BaseResponse.create(res=res, trace_id=trace_id)
        else:
            raise RESTAPIError(code=requests.codes.server_error,
                               desc='Server responded with unsupported ' \
                                'media type: {0} (status: {1})' \
                                .format(res.headers['Content-Type'],
                                    res.status_code),
                               trace_id=trace_id)

        if res.status_code == requests.codes.im_a_teapot:
            # Maintenance mode
            message = 'The API is currently in maintenance mode.\n'\
            'Please try again later and check http://status.dotcloud.com '\
            'for more information.'
            if res.json['error']['description'] is not None:
                message = res.json['error']['description']
            raise RESTAPIError(code=requests.codes.im_a_teapot, desc=message)

        if not res.ok:
            data = json.loads(res.text)
            raise RESTAPIError(code=res.status_code,
                desc=data['error']['description'], trace_id=trace_id)

        if self._version_checker:
            self._version_checker(res.headers.get('X-DOTCLOUD-CLI-VERSION-MIN'),
                    res.headers.get('X-DOTCLOUD-CLI-VERSION-CUR'))

        return BaseResponse.create(res=res, trace_id=trace_id,
                streaming=streaming)

########NEW FILE########
__FILENAME__ = errors
class RESTAPIError(Exception):
    def __init__(self, code=None, desc=None, trace_id=None):
        self.code = code
        self.desc = desc
        self.trace_id = trace_id

    def __str__(self):
        return self.desc

class AuthenticationNotConfigured(Exception):
    pass

########NEW FILE########
__FILENAME__ = response
import json
import httplib  # only for exception

def bytes_to_lines(stream):
    """Reads single bytes from stream, emits lines.
    
       This hack makes me sick, but requests makes this impossible
       to do reliably, otherwise."""
    line = ""
    for byte in stream:
        line += byte
        if line.endswith("\r\n"):
            yield line
            line = ""

class BaseResponse(object):
    def __init__(self, obj=None):
        self.obj = obj

    @classmethod
    def create(cls, res=None, trace_id=None, streaming=False):
        resp = None

        if streaming:
            stream = bytes_to_lines(res.iter_content(chunk_size=1))
            first_line = next(stream)
            data = json.loads(first_line)
        else:
            if res.text:
                data = json.loads(res.text)
            else:
                data = None
        if streaming:
            resp = StreamingJsonObjectResponse(obj=data['object'], stream=stream)
        elif data and 'object' in data:
            resp = ItemResponse(obj=data['object'])
        elif data and 'objects' in data:
            resp = ListResponse(obj=data['objects'])
        else:
            resp = NoItemResponse(obj=None)
        resp.trace_id = trace_id
        resp.res = res
        resp.data = data
        return resp

    def find_link(self, rel):
        for link in self.data.get('links', []):
            if link.get('rel') == rel:
                return link
        return None

class ListResponse(BaseResponse):
    @property
    def items(self):
        return self.obj

    @property
    def item(self):
        return self.obj[0]

class ItemResponse(BaseResponse):
    @property
    def items(self):
        return [self.obj]

    @property
    def item(self):
        return self.obj

class NoItemResponse(BaseResponse):
    @property
    def items(self):
        return None

    @property
    def item(self):
        return None

class StreamingJsonObjectResponse(BaseResponse):
    def __init__(self, obj, stream):
        BaseResponse.__init__(self, obj)
        self._stream = stream

    @property
    def items(self):
        def stream():
            try:
                for line in self._stream:
                    line = line.rstrip()
                    if line:  # ignore empty lines (keep-alive)
                        yield json.loads(line)['object']
            except httplib.HTTPException:
                pass  # simply ignore when the connection is dropped
        return stream()

    @property
    def item(self):
        return self.obj

########NEW FILE########
__FILENAME__ = bytesconverter
#!/usr/bin/env python

"""
Bytes-to-human / human-to-bytes converter.
Based on: http://goo.gl/kTQMs
Working with Python 2.x and 3.x.

Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
License: MIT
"""

# see: http://goo.gl/kTQMs
SYMBOLS = {
    'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                       'zetta', 'iotta'),
    'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                       'zebi', 'yobi'),
}

def bytes2human(n, format='%(value).1f %(symbol)s', symbols='customary'):
    """
    Convert n bytes into a human readable string based on format.
    symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
    see: http://goo.gl/kTQMs

      >>> bytes2human(0)
      '0.0 B'
      >>> bytes2human(0.9)
      '0.0 B'
      >>> bytes2human(1)
      '1.0 B'
      >>> bytes2human(1.9)
      '1.0 B'
      >>> bytes2human(1024)
      '1.0 K'
      >>> bytes2human(1048576)
      '1.0 M'
      >>> bytes2human(1099511627776127398123789121)
      '909.5 Y'

      >>> bytes2human(9856, symbols="customary")
      '9.6 K'
      >>> bytes2human(9856, symbols="customary_ext")
      '9.6 kilo'
      >>> bytes2human(9856, symbols="iec")
      '9.6 Ki'
      >>> bytes2human(9856, symbols="iec_ext")
      '9.6 kibi'

      >>> bytes2human(10000, "%(value).1f %(symbol)s/sec")
      '9.8 K/sec'

      >>> # precision can be adjusted by playing with %f operator
      >>> bytes2human(10000, format="%(value).5f %(symbol)s")
      '9.76562 K'
    """
    n = int(n)
    if n < 0:
        raise ValueError("n < 0")
    symbols = SYMBOLS[symbols]
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i+1)*10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return format % locals()
    return format % dict(symbol=symbols[0], value=n)

def human2bytes(s):
    """
    Attempts to guess the string format based on default symbols
    set and return the corresponding bytes as an integer.
    When unable to recognize the format ValueError is raised.

      >>> human2bytes('0 B')
      0
      >>> human2bytes('1 K')
      1024
      >>> human2bytes('1 M')
      1048576
      >>> human2bytes('1 Gi')
      1073741824
      >>> human2bytes('1 tera')
      1099511627776

      >>> human2bytes('0.5kilo')
      512
      >>> human2bytes('0.1  byte')
      0
      >>> human2bytes('1 k')  # k is an alias for K
      1024
      >>> human2bytes('12 foo')
      Traceback (most recent call last):
          ...
      ValueError: can't interpret '12 foo'
    """
    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]
    num = float(num)
    letter = s.strip()
    for name, sset in SYMBOLS.items():
        if letter in sset:
            break
    else:
        if letter == 'k':
            # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]:1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i+1)*10
    return int(num * prefix[letter])


if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = cli
from __future__ import unicode_literals

from .debug import global_endpoint_info
from .parser import get_parser
from .version import VERSION
from .config import GlobalConfig, CLIENT_KEY, CLIENT_SECRET
from .colors import Colors
from .utils import pprint_table, pprint_kv
from ..client import RESTClient
from ..client.errors import RESTAPIError, AuthenticationNotConfigured
from ..client.auth import BasicAuth, NullAuth, OAuth2Auth
from ..packages.bytesconverter import bytes2human

import sys
import codecs
import os
import json
import subprocess
import re
import time
import shutil
import getpass
import requests
import urllib2
import datetime
import tempfile
import stat
import platform
import locale

# Set locale
locale.setlocale(locale.LC_ALL, '')

class CLI(object):
    __version__ = VERSION
    def __init__(self, debug=False, colors=None, endpoint=None, username=None):
        # If you re-open stdout/stderr like this twice, then the second time
        # something weird happen and you cannot print unicode again (it will
        # raise this: UnicodeDecodeError: 'ascii' codec can't decode byte
        # 0xe2...).
        utf_8_stream_writer = codecs.getwriter('utf-8')
        if not isinstance(sys.stdout, utf_8_stream_writer):
            sys.stdout = utf_8_stream_writer(sys.stdout)
            sys.stderr = utf_8_stream_writer(sys.stderr)
        self.info_output = sys.stdout

        self._version_checked = False
        self.client = RESTClient(endpoint=endpoint, debug=debug,
                user_agent=self._build_useragent_string(),
                version_checker=self._check_version)
        self.debug = debug
        self.colors = Colors(colors)
        self.error_handlers = {
            401: self.error_authen,
            403: self.error_authz,
            404: self.error_not_found,
            418: self.error_maintenance,
            422: self.error_unprocessable,
            500: self.error_server,
        }
        self.global_config = GlobalConfig()
        self.setup_auth()
        if username:
            self.info('Assuming username ' \
                '{c.bright}{username}{c.reset}' \
                .format(username=username, c=self.colors))
            self.user = self.client.make_prefix_client('/users/{username}' \
                    .format(username=username))
            self.global_config.key = \
                    self.global_config.path_to('user_{0}.key'.format(username))
        else:
            self.user = self.client.make_prefix_client('/me')
        self.cmd = os.path.basename(sys.argv[0])

    def _build_useragent_string(self):
        (system, node, release, version, machine, processor) = platform.uname()
        pyimpl = platform.python_implementation()
        pyver = platform.python_version()
        (langcode, encoding) = ('en_US', 'UTF-8')
        try:
            (langcode, encoding) = locale.getdefaultlocale()
        except ValueError:
            pass
        return 'dotcloud-cli/{cliver} ({system}; {release}; ' \
                '{machine}; {pyimpl}; {pyver}; {langcode})'.format(
                cliver=self.__version__, **locals())

    def setup_auth(self):
        if self.global_config.get('token'):
            token = self.global_config.get('token')
            client = self.global_config.get('client')
            self.client.authenticator = OAuth2Auth(access_token=token['access_token'],
                                                   refresh_token=token['refresh_token'],
                                                   scope=token.get('scope'),
                                                   client_id=CLIENT_KEY,
                                                   client_secret=CLIENT_SECRET,
                                                   token_url=token['url'])
            self.client.authenticator.pre_refresh_callback = self.pre_refresh_token
            self.client.authenticator.post_refresh_callback = self.post_refresh_token
        elif self.global_config.get('apikey'):
            access_key, secret = self.global_config.get('apikey').split(':')
            self.client.authenticator = BasicAuth(access_key, secret)
            if getattr(self, 'user', None):
                self.user.authenticator = self.client.authenticator

    def pre_refresh_token(self, req):
        self.info('Refreshing OAuth2 token...')

    def post_refresh_token(self, res):
        self.info('Refreshed OAuth2 token')
        self.global_config.data['token']['access_token'] = res['access_token']
        self.global_config.data['token']['refresh_token'] = res['refresh_token']
        self.global_config.data['token']['expires_in'] = res['expires_in']
        self.global_config.save()
        return True

    def run(self, args):
        try:
            self.info_output = sys.stderr
            p = get_parser(self.cmd)
            args = p.parse_args(args)
            if args.debug is True:
                self.debug = True
                self.client.debug = True
            if not self.global_config.loaded and args.cmd != 'setup':
                self.die('Not configured yet. Please run "{0} setup"'.format(self.cmd))
            self.load_local_config(args)
            cmd = 'cmd_{0}'.format(args.cmd)
            if not hasattr(self, cmd):
                raise NotImplementedError('cmd not implemented: "{0}"'.format(cmd))
            try:
                return getattr(self, cmd)(args)
            except AuthenticationNotConfigured:
                self.error('Authentication is not configured. Please run `{0} setup`'.format(self.cmd))
            except RESTAPIError, e:
                handler = self.error_handlers.get(e.code, self.default_error_handler)
                handler(e)
            except KeyboardInterrupt:
                pass
            except urllib2.URLError as e:
                self.error('Accessing dotCloud API failed: {0}'.format(str(e)))
        except requests.ConnectionError as e:
            self.error('The server seems to be unresponsive. Please check that you are '
                'connected to the Internet or try again later.\n'
                'If the problem persists, issue a support ticket to support@dotcloud.com')
            self.error('Details: {exc}'.format(exc=e))
            if self.debug:
                raise
            return 1
        except Exception as e:
            message = u'An unexpected error has occurred: {exc}.\n'.format(exc=e)
            if global_endpoint_info:
                message += ('The remote server handling the last request was '
                            '{remotehost}:{remoteport}.\n'
                            'The {timesource} timestamp was {timestamp}.\n'
                            .format(**global_endpoint_info))
            else:
                message += ('It looks like we could not establish an healthy '
                            'TCP connection to any of the API endpoints.\n')
            message += ('Please try again; and if the problem persists, '
                        'contact support@dotcloud.com with this information.')
            self.error(message)
            if self.debug:
                raise
            return 1
        finally:
            self.info_output = sys.stdout

    def _parse_version(self, s):
        if not s:
            return None
        parts = s.split('.')
        if not parts:
            return None
        for x in xrange(3-len(parts)):
            parts.append('0')
        return parts[0:3]

    def _is_version_gte(self, a, b):
        for p1, p2 in zip(a, b):
            if p1 > p2:
                return True
            elif p1 < p2:
                return False
        return True

    def _check_version(self, version_min_s, version_cur_s):
        if self._version_checked:
            return  # check only one time per run of the CLI
        self._version_checked = True
        version_min = self._parse_version(version_min_s)
        version_cur = self._parse_version(version_cur_s)
        if version_min is None or version_cur is None:
            return
        version_local = self._parse_version(self.__version__)

        if not self._is_version_gte(version_local, version_min):
            # always warn when it is really too old.
            self.warning('Your cli version ({0}) is outdated.'.format(self.__version__,
                version_min_s))
        last_version_check = self.global_config.get('last_version_check', None)

        if last_version_check and last_version_check > time.time() \
                - (60 * 60 * 2):  # inform the user of the new version every 2h
            return
        self.global_config.data['last_version_check'] = time.time()
        self.global_config.save()

        if not self._is_version_gte(version_local, version_cur):
            self.info('A newer version ({0}) of the CLI is available ' \
                '(upgrade with: pip install -U dotcloud).'.format(version_cur_s))

    def ensure_app_local(self, args):
        if args.application is None:
            self.die('No application specified. '
                     'Run this command from an application directory '
                     'or specify which application to use with --application.')

    def app_local(func):
        def wrapped(self, args):
            self.ensure_app_local(args)
            return func(self, args)
        return wrapped

    def save_config(self, config):
        dir = '.dotcloud'
        if not os.path.exists(dir):
            os.mkdir(dir, 0700)
        f = open(os.path.join(dir, 'config'), 'w+')
        json.dump(config, f, indent=4)

    def patch_config(self, new_config):
        config = {}
        try:
            io = open('.dotcloud/config')
            config = json.load(io)
        except IOError:
            pass
        config.update(new_config)
        self.save_config(config)

    def load_local_config(self, args):
        last_path = None
        path = os.environ.get('PWD') or os.getcwd()
        for x in xrange(256):
            try:
                io = open(os.path.join(path, '.dotcloud/config'))
                config = json.load(io)
                if not args.application:
                    args.application = config['application']
                self.local_config = config
                self.local_config_root = path
                return
            except IOError:
                pass
            last_path = path
            path = os.path.split(path)[0]
            if path == last_path:
                break
        self.local_config = {}

    def destroy_local_config(self):
        try:
            shutil.rmtree('.dotcloud')
        except:
            pass

    def die(self, message=None, stderr=False):
        if message is not None:
            if stderr:
                print >>sys.stderr, message
            else:
                self.error(message)
        sys.exit(1)

    def prompt(self, prompt, noecho=False):
        method = getpass.getpass if noecho else raw_input
        input = method(prompt + ': '.encode('ascii'))
        return input

    def confirm(self, args, prompt, default='n'):
        choice = ' [Y/n]' if default == 'y' else ' [y/N]'
        text = prompt + choice + ': '

        if args.assume_yes:
            print text, 'Y'
            return True

        if args.assume_no:
            print text, 'N'
            return False

        input = raw_input(text).lower()
        if input == '':
            input = default
        return re.match(r'^y(?:es)?$', input.strip(), re.IGNORECASE)

    def error(self, message):
        print '{c.red}{c.bright}Error:{c.reset} {message}' \
            .format(c=self.colors, message=message)

    def info(self, message):
        print >> self.info_output, '{c.blue}{c.bright}==>{c.reset} {message}' \
            .format(c=self.colors, message=message)

    def warning(self, message):
        print '{c.yellow}{c.bright}Warning:{c.reset} {message}' \
            .format(c=self.colors, message=message)

    def success(self, message):
        print '{c.green}{c.bright}==>{c.reset} ' \
            '{message}' \
            .format(c=self.colors, message=message)

    def default_error_handler(self, e):
        self.error('An unknown error has occurred: {0}'.format(e))
        self.error('If the problem persists, please e-mail ' \
            'support@dotcloud.com {0}' \
            .format('and mention Trace ID "{0}"'.format(e.trace_id)
                if e.trace_id else ''))
        self.die()

    def error_authen(self, e):
        self.die("Authentication Error: {0}".format(e.code))

    def error_authz(self, e):
        self.die("Authorization Error: {0}".format(e.desc))

    def error_not_found(self, e):
        self.die("Not Found: {0}".format(e.desc))

    def error_unprocessable(self, e):
        self.die(e.desc)

    def error_server(self, e):
        self.error('Server Error: {0}'.format(e.desc))
        self.error('If the problem persists, please e-mail ' \
            'support@dotcloud.com {0}' \
            .format('and mention Trace ID "{0}"'.format(e.trace_id)
                if e.trace_id else ''))
        self.die()

    def error_maintenance(self, e):
        self.die('{0}'.format(e.desc))

    def cmd_check(self, args):
        # TODO Check ~/.dotcloud stuff
        try:
            self.info('Checking the authentication status')
            res = self.user.get()
            self.success('Client is authenticated as ' \
                '{c.bright}{username}{c.reset}' \
                .format(username=res.item['username'], c=self.colors))
        except Exception:
            self.die('Authentication failed. Run `{cmd} setup` to redo the authentication'.format(cmd=self.cmd))
        self.get_keys()

    def cmd_setup(self, args):
        if args.api_key:
            if 'DOTCLOUD_API_KEY' in os.environ:
                self.info('Using API key configured at environment variable'
                          ' DOTCLOUD_API_KEY.')
                api_key = os.environ['DOTCLOUD_API_KEY']
            else:
                # API Key
                self.info('You can find your API key at https://account.dotcloud.com/settings/')
                api_key = self.prompt('Please enter your API key')

            if not re.match('\w{20}:\w{40}', api_key):
                self.die('Invalid API Key')
            config = GlobalConfig()
            config.data = {'apikey': api_key}
            config.save()
        else:
            # OAuth2
            client = RESTClient(endpoint=self.client.endpoint)
            client.authenticator = NullAuth()
            urlmap = client.get('/auth/discovery').item
            username = self.prompt('dotCloud username or email')
            password = self.prompt('Password'.encode('ascii'), noecho=True)
            credential = {'token_url': urlmap.get('token'),
                'key': CLIENT_KEY, 'secret': CLIENT_SECRET}
            try:
                token = self.authorize_client(urlmap.get('token'), credential, username, password)
            except Exception:
                self.die('Username and password do not match. Try again.')
            token['url'] = credential['token_url']
            config = GlobalConfig()
            config.data = {'token': token}
            config.save()
        self.global_config = GlobalConfig()  # reload
        self.setup_auth()
        self.get_keys()
        self.success('dotCloud authentication is complete! You are recommended to run `{cmd} check` now.'.format(cmd=self.cmd))

    def authorize_client(self, url, credential, username, password):
        form = {
            'username': username,
            'password': password,
            'grant_type': 'password',
            'client_id': credential['key']
        }
        res = requests.post(url, data=form,
            auth=(credential['key'], credential['secret']))
        res.raise_for_status()
        return json.loads(res.text)

    def get_keys(self):
        res = self.user.get('/private_keys')
        try:
            key = res.items[0]['private_key']
            self.global_config.save_key(key)
        except (KeyError, IndexError):
            self.die('Retrieving push keys failed. You might have to run `{0} check` again'.format(self.cmd))

    def cmd_list(self, args):
        res = self.user.get('/applications')
        if not res.items:
            self.info('You don\'t have any application yet, create one with `{0} create`'.format(self.cmd))
            return

        padding = max([len(app['name']) for app in res.items]) + 2
        for app in sorted(res.items, key=lambda x: x['name']):
            if app['name'] == args.application:
                print '* {0}{1}{2}'.format(
                    self.colors.green(app['name']),
                    ' ' * (padding - len(app['name'])),
                    app['flavor'])
            else:
                print '  {0}{1}{2}'.format(
                    app['name'],
                    ' ' * (padding - len(app['name'])),
                    app.get('flavor'))

    def cmd_create(self, args):
        self.info('Creating a {c.bright}{flavor}{c.reset} application named "{name}"'.format(
            flavor=args.flavor,
            name=args.application,
            c=self.colors))
        url = '/applications'
        try:
            self.user.post(url, {
                'name': args.application,
                'flavor': args.flavor
                })
        except RESTAPIError as e:
            if e.code == 409:
                self.die('Application "{0}" already exists.'.format(args.application))
            else:
                self.die('Creating application "{0}" failed: {1}'.format(args.application, e))
        self.success('Application "{0}" created.'.format(args.application))
        if self.confirm(args, 'Connect the current directory to "{0}"?'.format(args.application), 'y'):
            self._connect(args)

    def cmd_traffic(self, args):

        duration = self.parse_duration(args.duration)
        self.info('Retrieving traffic metrics on {0} for the {1}'.format(args.application, duration))
        url = '/applications/{0}/metrics/http?range={1}'.format(args.application, args.duration)

        # dictionary of the array that is returned by the service
        # [0] 1373387184, # timestamp
        # [1] 4.808187, # 2xxs req/sec
        # [2] 0, # 3xxs req/sec
        # [3] 3.4046783, # 4xxs req/sec
        # [4] 0, # 5xxs req/sec
        # [5] 0.6730711, # application latency
        # [6] 0.0046018595 # platform latency


        try:
            res = self.user.get(url)
            services_table = [
                [
                    'time',
                    '2xx',
                    '3xx',
                    '4xx',
                    '5xx',
                    'total req/sec',
                    'platform latency',
                    'application latency',
                    'total latency'
                ]
            ]
            for metric in res.items:
                services_table.append([
                    time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime(metric[0])),
                    int(metric[1]),
                    int(metric[2]),
                    int(metric[3]),
                    int(metric[4]),
                    int(metric[1]+metric[2]+metric[3]+metric[4]),
                    '{0} ms'.format(int(metric[6]*1000)),
                    '{0} ms'.format(int(metric[5]*1000)),
                    '{0} ms'.format(int(metric[6]*1000 + metric[5]*1000))
                ])
            pprint_table(services_table)
        except RESTAPIError as e:
            self.die('Retrieving traffic metrics failed: {1}'.format(args.application, e))

    def cmd_memory(self, args):

        duration = self.parse_duration(args.duration)
        service_name, instance_id = self.parse_service_instance(args.service_or_instance, args.cmd)
        self.info('Retrieving memory metrics on {0}.{1} for the {2}'.format(service_name, instance_id, duration))
        url = '/applications/{0}/services/{1}/instances/{2}/metrics/memory?range={3}' \
            .format(args.application, service_name, instance_id, args.duration)

        # dictionary of the array that is returned by the service
        # [0] 1376073600, # timestamp
        # [1] 4.2341864E7, # inactive + active page size + resident state size (total used)
        # [2] 1.34217728E8, # memory size at time
        # [3] 1861094.4,
        # [4] 49.1875864E7, # unused memory
        # [5] 4.0493056E7, # resident set size
        # [6] 339968,
        # [7] 240588.8, # active page cache
        # [8] 1268249.6 # inactive page cache

        try:
            res = self.user.get(url)
            services_table = [ ['time', 'overage', 'unused', 'used', 'allocated'] ]
            for metric in res.items:
                services_table.append([
                    time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime(metric[0])),
                    bytes2human(abs(metric[2]-metric[1])) if metric[1] > metric[2] else bytes2human(0),
                    bytes2human(metric[4]),
                    bytes2human(metric[1]),
                    bytes2human(metric[2]),
                ])
            pprint_table(services_table)
        except RESTAPIError as e:
            self.die('Retrieving memory metrics failed: {1}'.format(args.application, e))

    def cmd_connect(self, args):
        url = '/applications/{0}'.format(args.application)
        try:
            self.user.get(url)
            self._connect(args)
        except RESTAPIError:
            self.die('Application "{app}" doesn\'t exist. Try `{cmd} create <appname>`.' \
                         .format(app=args.application, cmd=self.cmd))

    @app_local
    def cmd_disconnect(self, args):
        self.info('Disconnecting the current directory from "{0}"'.format(args.application))
        self.destroy_local_config()

    @app_local
    def cmd_destroy(self, args):
        if args.service is None:
            what_destroy = 'application'
            to_destroy = args.application
            url = '/applications/{0}'.format(args.application)
        else:
            what_destroy = 'service'
            to_destroy = '{0}.{1}'.format(args.application, args.service)
            url = '/applications/{0}/services/{1}'.format(args.application, args.service)

        if not self.confirm(args, 'Destroy the {0} "{1}"?'.format(what_destroy, to_destroy)):
            return
        self.info('Destroying "{0}"'.format(to_destroy))
        try:
            self.user.delete(url)
        except RESTAPIError as e:
            if e.code == 404:
                self.die('The {0} "{1}" does not exist.'.format(what_destroy, to_destroy))
            else:
                raise
        self.success('Destroyed.')
        if args.service is None:
            if self.local_config.get('application') == args.application:
                self.destroy_local_config()

    def _connect(self, args):
        protocol_arg, protocol = self._selected_push_protocol(args)
        branch = args.branch if protocol != 'rsync' else None

        self.info('Connecting with the application "{0}"'.format(args.application))
        self.save_config({
            'application': args.application,
            'version': self.__version__
        })

        self.patch_config({
            'push_protocol': protocol,
            'push_branch': branch
            })

        push_args = [ protocol_arg ]
        if branch:
            push_args.append('--branch {0}'.format(branch))
        self.success('Connected with default push options: {0}'.format(' '.join(push_args)))

    @app_local
    def cmd_app(self, args):
        print args.application

    @app_local
    def cmd_domain(self, args):
        if args.subcmd == 'list':
            url = '/applications/{0}/services'.format(args.application)
            res = self.user.get(url)
            for svc in res.items:
                url = '/applications/{0}/services/{1}/domains'\
                    .format(args.application, svc.get('name'))
                res = self.user.get(url)
                for domain in res.items:
                    print '{0}: {1}'.format(svc.get('name'), domain.get('domain'))
        elif args.subcmd == 'add':
            url = '/applications/{0}/services/{1}/domains' \
                .format(args.application, args.service)
            res = self.user.post(url, {'domain': args.domain})
            http_gateway = res.item.get('gateway')
            self.success('domain "{0}" created for "{1}"'.format(
                args.domain, args.service))
            if http_gateway:
                self.success('Now please add the following DNS record:\n'
                        '{0}. IN CNAME {1}.'.format(args.domain, http_gateway))
        elif args.subcmd == 'rm':
            url = '/applications/{0}/services/{1}/domains/{2}' \
                .format(args.application, args.service, args.domain)
            self.user.delete(url)
            self.success('domain "{0}" deleted from "{1}"'.format(
                args.domain, args.service))

    @app_local
    def cmd_env(self, args):
        url = '/applications/{0}/environment'.format(args.application)
        deploy = None
        if args.subcmd == 'list':
            self.info('Environment variables for application {0}'.format(args.application))
            var = self.user.get(url).item
            for name in sorted(var.keys()):
                print '='.join((name, str(var.get(name))))
        elif args.subcmd == 'set':
            self.info('Setting {0} (application {1})'.format(
                ', '.join(args.variables), args.application))
            patch = {}
            for pair in args.variables:
                key, val = pair.split('=', 1)
                patch[key] = val
            self.user.patch(url, patch)
            deploy = True
        elif args.subcmd == 'unset':
            self.info('Un-setting {0} (application {1})'.format(
                ', '.join(args.variables), args.application))
            patch = {}
            for name in args.variables:
                patch[name] = None
            self.user.patch(url, patch)
            deploy = True
        else:
            self.die('Unknown sub command {0}'.format(args.subcmd), stderr=True)
        if deploy:
            self.deploy(args.application)

    @app_local
    def cmd_scale(self, args):
        self.info('Scaling application {0}'.format(args.application))
        def round_memory(value):
            # Memory scaling has to be performed in increments of 32M
            # Let's align max(step, value) to closest upper or lower step boundary.
            step = 32 * (1024 * 1024)
            return ((max(step, value) & ~(step / 2 - 1)) + step - 1) & ~(step - 1)

        for svc in args.services:
            url = '/applications/{0}/services/{1}' \
                .format(args.application, svc.name)
            try:
                if svc.action == 'instances':
                    self.info('Changing instances of {0} to {1}'.format(
                        svc.name, svc.original_value))
                    self.user.patch(url, {'instance_count': svc.value})
                elif svc.action == 'memory':
                    memory = round_memory(svc.value)
                    self.info('Changing memory of {0} to {1}B'.format(
                        svc.name, bytes2human(memory)))
                    self.user.patch(url, {'reserved_memory': memory})
            except RESTAPIError as e:
                if e.code == requests.codes.bad_request:
                    self.die('Failed to scale {0} of "{1}": {2}'.format(
                        svc.action, svc.name, e))
                raise

        ret = 0
        # If we changed the number of instances of any service, then we need
        # to trigger a deploy
        if any(svc.action == 'instances' for svc in args.services):
            ret = self.deploy(args.application)

        if ret == 0:
            self.success('Successfully scaled {0} to {1}'.format(args.application,
                ' '.join(['{0}:{1}={2}'.format(svc.name, svc.action,
                    svc.original_value)
                    for svc in args.services])))

    @app_local
    def cmd_status(self, args):
        color_map = {
            'up': self.colors.green,
            'down': self.colors.red,
            'hibernating': self.colors.blue
        }

        self.info('Probing status for service "{0}"...'.format(args.service))
        url = '/applications/{0}/services/{1}'.format(args.application, args.service)
        res = self.user.get(url)
        for instance in res.item['instances']:
            url = '/applications/{0}/services/{1}/instances/{2}/status'.format(
                args.application, args.service, instance['instance_id'])
            title = '{0}.{1}: '.format(
                args.service, instance['instance_id'])
            print title,
            sys.stdout.flush()
            status = self.user.get(url).item
            print '{color}{c.bright}{status}{c.reset}'.format(
                color=color_map.get(status['status'], self.colors.reset),
                status=status['status'],
                c=self.colors)
            if 'custom' in status:
                for (k, v) in status['custom'].items():
                    print '{0} {1} -> {2}'.format(' ' * len(title), k, v)


    @app_local
    def cmd_info(self, args):
        if args.service:
            return self.cmd_info_service(args)
        else:
            return self.cmd_info_app(args)

    def cmd_info_service(self, args):
        url = '/applications/{0}/services/{1}'.format(args.application,
            args.service)
        service = self.user.get(url).item

        print '== {0}'.format(service.get('name'))

        pprint_kv([
            ('type', service.get('service_type')),
            ('instances', service.get('instance_count')),
            ('reserved memory',
                bytes2human(service.get('reserved_memory')) if service.get('reserved_memory') else 'N/A'),
            ('config', service.get('runtime_config').items()),
            ('URLs', 'N/A' if not service.get('domains') else ' ')
        ])

        for domain in service.get('domains'):
            print '  - http://{0}'.format(domain.get('domain'))

        for instance in sorted(service.get('instances', []), key=lambda i: i.get('instance_id')):
            service_revision = instance.get('image_version')
            image_upgrade = instance.get('image_upgrade')
            if service_revision and image_upgrade is not None:
                service_revision += ' ({0})'.format('upgrade available' if image_upgrade else 'latest revision')
            print
            print '=== {0}.{1}'.format(service.get('name'), instance.get('instance_id'))
            pprint_kv([
                ('datacenter', instance.get('datacenter')),
                ('host', instance.get('host')),
                ('container', instance.get('container_name')),
                ('service revision', '{0}/{1}'.format(service.get('service_type'), service_revision)),
                ('revision', instance.get('revision')),
                ('ports', [(port.get('name'), port.get('url'))
                    for port in instance.get('ports')
                    if port.get('name') != 'http'])
            ])

    def cmd_info_app(self, args):
        url = '/applications/{0}'.format(args.application)
        application = self.user.get(url).item
        print '=== {0}'.format(application.get('name'))

        info = [
            ('flavor', application.get('flavor'))
        ]

        billing = application.get('billing')
        if not billing.get('free', False):
            info.append(('cost to date', '${0}'.format(
                locale.format("%d", billing.get('cost'), grouping=True))))
            info.append(('expected month-end cost', '${0}'.format(
                locale.format("%d", billing.get('expected_month_end_cost'), grouping=True))))
        else:
            info.append(('cost to date', 'Free'))

        # FIXME: Show deployed revision

        info.append(('services', ''))
        pprint_kv(info, padding=5)

        services = application.get('services', [])
        if not services:
            self.warning('It looks like you haven\'t deployed your application.')
            self.warning('Run {0} push to deploy and see the information about your stack.'.
                         format(self.cmd))
            return

        services_table = [
            ['name', 'type', 'containers', 'reserved memory']
        ]

        for service in sorted(services, key=lambda s: s.get('name')):
            services_table.append([
                service.get('name'),
                service.get('service_type'),
                service.get('instance_count'),
                bytes2human(service.get('reserved_memory'))
                    if service.get('reserved_memory') else 'N/A'])
        pprint_table(services_table)

    @app_local
    def cmd_url(self, args):
        if args.service:
            urls = self.get_url(args.application, args.service)
            if urls:
                print ' '.join(urls)
        else:
            pprint_kv([
                (service, ' ; '.join(urls))
                for (service, urls) in self.get_url(args.application).items()
            ], padding=5)

    @app_local
    def cmd_open(self, args):
        import webbrowser

        if args.service:
            urls = self.get_url(args.application, args.service)
            if urls:
                self.info('Opening service "{0}" in a browser: {c.bright}{1}{c.reset}'.format(
                    args.service,
                    urls[-1],
                    c=self.colors))
                webbrowser.open(urls[-1])
            else:
                self.die('No URLs found for service "{0}"'.format(args.service))
        else:
            urls = self.get_url(args.application)
            if not urls:
                self.die('No URLs found for the application')
            if len(urls) > 1:
                self.die('More than one service exposes an URL. ' \
                    'Please specify the name of the one you want to open: {0}' \
                    .format(', '.join(urls.keys())))
            self.info('Opening service "{0}" in a browser: {c.bright}{1}{c.reset}'.format(
                urls.keys()[0],
                urls.values()[0][-1],
                c=self.colors))
            webbrowser.open(urls.values()[0][-1])

    def get_url(self, application, service=None):
        if service is None:
            urls = {}
            url = '/applications/{0}/services'.format(application)
            res = self.user.get(url)
            for service in res.items:
                domains = service.get('domains')
                if domains:
                    urls[service['name']] = \
                        ['http://{0}'.format(d.get('domain')) for d in domains]
            return urls
        else:
            url = '/applications/{0}/services/{1}'.format(application,
                service)
            domains = self.user.get(url).item.get('domains')
            if not domains:
                return []
            return ['http://{0}'.format(d.get('domain')) for d in domains]

    @app_local
    def cmd_deploy(self, args):
        self.deploy(args.application, clean=args.clean, revision=args.revision)

    def _select_endpoint(self, endpoints, protocol):
        try:
            return [endpoint for endpoint in endpoints
                    if endpoint['protocol'] == protocol][0]['endpoint']
        except IndexError:
            self.die('Unable to find {0} endpoint in [{1}]'.format(
                protocol,
                ', '.join(endpoint['protocol'] for endpoint in endpoints))
                )

    def _selected_push_protocol(self, args, use_local_config=False):
        args_proto_map = {
                'git': 'git',
                'hg': 'mercurial',
                'rsync': 'rsync'
                }

        for arg, protocol in args_proto_map.items():
            if getattr(args, arg, None):
                return ('--' + arg, protocol)

        if use_local_config:
            saved_protocol = self.local_config.get('push_protocol')
            arg = None
            for find_arg, find_protocol in args_proto_map.iteritems():
                if find_protocol == saved_protocol:
                    arg = find_arg
                    break
            if arg is None:
                arg = 'rsync'
        else:
            arg = 'rsync'

        return ('--' + arg, args_proto_map[arg])

    def _yml_exists_check(self, args):
        root = getattr(self, 'local_config_root', None)
        if args.path is not None :
            if not os.path.exists(os.path.join(args.path, 'dotcloud.yml')):
                question = "No 'dotcloud.yml' found in '{0}'\n"\
                    "Are you sure you entered the correct directory path?".format(
                        args.path
                )
                if not self.confirm(args, question):
                    self.die()
        else :
            if root is None :
                if not os.path.exists('dotcloud.yml'):
                    question = "No 'dotcloud.yml' found in '{0}'\n" \
                        "Are you sure you are in the correct directory?".format(
                            os.getcwd()
                    )
                    if not self.confirm(args, question):
                        self.die()
            else :
                if not os.path.exists(os.path.join(self.local_config_root, 'dotcloud.yml')):
                    question = "No 'dotcloud.yml' found in '{0}',\n" \
                        "the closest parent folder connected to an application.\n" \
                        "Did you forget to create a 'dotcloud.yml'?" \
                        "Continue?".format(
                        self.local_config_root
                    )
                    if not self.confirm(args, question):
                        self.die()

    @app_local
    def cmd_push(self, args):
        self._yml_exists_check(args)

        protocol = self._selected_push_protocol(args, use_local_config=True)[1]
        branch = None
        commit = None
        parameters = ''

        if protocol != 'rsync':
            branch = args.branch or self.local_config.get('push_branch')
            if args.commit:
                commit = args.commit
                parameters = '?commit={0}'.format(args.commit)
            else:
                branch = args.branch
                # If we weren't passed a branch and don't have a
                # default one, then get the current branch
                if not branch:
                    get_local_branch = getattr(self,
                            'get_local_branch_{0}'.format(protocol), None)
                    if get_local_branch:
                        branch = get_local_branch(args)
                if branch:
                    parameters = '?branch={0}'.format(branch)

        url = '/applications/{0}/push-endpoints{1}'.format(args.application,
                parameters)
        endpoint = self._select_endpoint(self.user.get(url).items, protocol)

        path = os.path.join(os.path.relpath(args.path or
            getattr(self, 'local_config_root', '.')), '')
        if commit or branch:
            self.info('Pushing code with {0}'
                    ', {1} {c.bright}{2}{c.reset} from "{3}" to application {4}'.format(
                protocol, 'commit' if commit else 'branch',
                commit or branch, path, args.application,
                c=self.colors))
        else:
            self.info('Pushing code with {c.bright}{0}{c.reset} from "{1}" to application {2}'.format(
                protocol, path, args.application, c=self.colors))

        ret = getattr(self, 'push_with_{0}'.format(protocol))(args, endpoint)

        if ret != 0:
            return ret

        return self.deploy(args.application, clean=args.clean)

    def push_with_mercurial(self, args, mercurial_endpoint, local_dir='.'):
        ssh_cmd = ' '.join(self.common_ssh_options + [
            '-o', 'LogLevel=ERROR',
            '-o', 'UserKnownHostsFile=/dev/null',
            ])

        mercurial_cmd = ['hg', 'outgoing', '-f', '-e', "{0}".format(ssh_cmd),
                mercurial_endpoint]

        try:
            outgoing_ret = subprocess.call(mercurial_cmd, close_fds=True,
                    cwd=args.path, stdout=open(os.path.devnull))
        except OSError:
            self.die('Unable to spawn mercurial')

        if outgoing_ret == 255:
            self.die('Mercurial returned a fatal error')

        if outgoing_ret == 1:
            return 0  # nothing to push

        mercurial_cmd = ['hg', 'push', '-f', '-e', "{0}".format(ssh_cmd),
                mercurial_endpoint]

        try:
            subprocess.call(mercurial_cmd, close_fds=True, cwd=args.path)
            return 0
        except OSError:
            self.die('Unable to spawn mercurial')

    def push_with_git(self, args, git_endpoint):
        ssh_cmd = ' '.join(self.common_ssh_options + [
            '-o', 'LogLevel=ERROR',
            '-o', 'UserKnownHostsFile=/dev/null',
            ])

        git_cmd = ['git', 'push', '-f', '--all', '--progress', '--repo', git_endpoint]

        git_ssh_script_fd, git_ssh_script_path = tempfile.mkstemp()
        try:
            with os.fdopen(git_ssh_script_fd, 'w') as git_ssh_script_writeable:
                git_ssh_script_writeable.write("#!/bin/sh\nexec {0} $@\n".format(ssh_cmd))
                os.fchmod(git_ssh_script_fd, stat.S_IREAD | stat.S_IEXEC)

            try:
                return subprocess.call(git_cmd,
                        env=dict(GIT_SSH=git_ssh_script_path), close_fds=True,
                        cwd=args.path)
            except OSError:
                self.die('Unable to spawn git')
        finally:
            os.remove(git_ssh_script_path)

    def get_local_branch_git(self, args):
        git_cmd = ['git', 'symbolic-ref', 'HEAD']
        try:
            try:
                ref = subprocess.check_output(git_cmd, close_fds=True,
                        cwd=args.path)
            except AttributeError:
                # Python < 2.7
                p = subprocess.Popen(git_cmd, stdout=subprocess.PIPE)
                ref = p.communicate()[0]
        except subprocess.CalledProcessError:
            self.die('Unable to determine the active branch (git)')
        except OSError:
            self.die('Unable to spawn git')
        return ref.strip().split('/')[-1]

    def push_with_rsync(self, args, rsync_endpoint):
        local_dir = args.path or getattr(self, 'local_config_root', '.')
        if not local_dir.endswith('/'):
            local_dir += '/'
        url = self.parse_url(rsync_endpoint)
        ssh = ' '.join(self.common_ssh_options + ['-o', 'LogLevel=QUIET'])
        ssh += ' -p {0}'.format(url['port'])
        excludes = ('*.pyc', '.git', '.hg')
        ignore_file = os.path.join(local_dir, '.dotcloudignore')
        ignore_opt = ('--exclude-from', ignore_file) if os.path.exists(ignore_file) else tuple()
        verbose_opt = ('--verbose', '--progress') if args.verbose else tuple()
        rsync = ('rsync', '-lpthrz', '--delete', '--safe-links') + \
                 verbose_opt + \
                 tuple('--exclude={0}'.format(e) for e in excludes) + \
                 ignore_opt + \
                 ('-e', ssh, local_dir,
                  '{user}@{host}:{dest}/'.format(user=url['user'],
                                                 host=url['host'], dest=url['path']))
        try:
            return subprocess.call(rsync, close_fds=True)
        except OSError:
            self.die('Unable to spawn rsync')

    def deploy(self, application, clean=False, revision=None, service=None):
        if revision is not None:
            self.info('Submitting a deployment request for revision {0} of application {1}'.format(
                revision, application))
        else:
            self.info('Submitting a deployment request for application {0}'.format(
                application))
        url = '/applications/{0}/deployments'.format(application)
        response = self.user.post(url,
            {'revision': revision, 'clean': clean, 'service': service})
        deploy_trace_id = response.trace_id
        deploy_id = response.item['deploy_id']
        self.info('Deployment of revision {c.bright}{0}{c.reset}' \
                ' scheduled for {1}'.format(
            response.item.get('revision'), application, c=self.colors))

        try:
            res = self._stream_deploy_logs(application, deploy_id,
                    deploy_trace_id=deploy_trace_id, follow=True)
            if res != 0:
                return res
        except KeyboardInterrupt:
            self.error('You\'ve closed your log stream with Ctrl-C, ' \
                'but the deployment is still running in the background.')
            self.error('If you aborted because of an error ' \
                '(e.g. the deployment got stuck), please e-mail\n' \
                'support@dotcloud.com and mention this trace ID: {0}'
                .format(deploy_trace_id))
            self.error('If you want to continue following your deployment, ' \
                    'try:\n{0}'.format(
                        self._fmt_deploy_logs_command(deploy_id)))
            self.die()
        urls = self.get_url(application)
        if urls:
            self.success('Application is live at {c.bright}{url}{c.reset}' \
                .format(url=urls.values()[-1][-1], c=self.colors))
        else:
            self.success('Application is live')
        return 0

    @property
    def common_ssh_options(self):
        return [
            'ssh',
            '-i', self.global_config.key,
            '-o', 'IdentitiesOnly=yes',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'PasswordAuthentication=no',
            '-o', 'ServerAliveInterval=10',
        ]

    def _escape(self, s):
        for c in ('`', '$', '"'):
            s = s.replace(c, '\\' + c)
        return s

    def parse_duration(self, duration):
        message = ''
        if duration == '1h':
            message = 'last 60 minutes'
        elif duration == '6h':
            message = 'last 6 hours'
        elif duration == '1d':
            message = 'last 24 hours'
        elif duration == '1w':
            message = 'last 7 days'
        elif duration == '1M':
            message = 'last 30 days'
        else:
            self.error('Invalid duration identifier: {0}'.format(duration))
            self.info('Valid options are: 1h (last 60 minutes), 6h (last 6 hours), 1d (last 24 hours), 1w (last 7 days), 1M (last 30 days)')
            self.die()
        return message

    def parse_service_instance(self, service_or_instance, command):
        if '.' not in service_or_instance:
            self.die('You must specify a service and instance, e.g. "www.0"')
        service_name, instance_id = service_or_instance.split('.', 1)
        if not (service_name and instance_id):
            self.die('Service instances must be formed like, "www.0"')
        try:
            instance_id = int(instance_id)
            if instance_id < 0:
                raise ValueError('value should be >= 0')
        except ValueError:
            self.error('Invalid service instance identifier: {0}'.format(service_or_instance))
            self.info('Did you mean `{0} {1} -A {2} {3}` ?'.format(self.cmd, command, service_name, instance_id))
            self.die()

        return service_name, instance_id

    def get_ssh_endpoint(self, args):
        if '.' in args.service_or_instance:
            service_name, instance_id = self.parse_service_instance(args.service_or_instance, args.cmd)
        else:
            service_name, instance_id = (args.service_or_instance, None)

        url = '/applications/{0}/services/{1}'.format(args.application,
                service_name)
        service = self.user.get(url).item
        if instance_id is None:
            if len(service['instances']) != 1:
                self.die('There are multiple instances of service "{0}". '
                    'Please specify the full instance name: {1}'.format(
                        service['name'],
                        ', '.join(['{0}.{1}'.format(service['name'], i['instance_id']) for i in service['instances']])))
            instance_id = service['instances'][0]['instance_id']
        instance = filter(lambda i: i['instance_id'] == instance_id, service['instances'])
        if not instance:
            self.die('Not Found: Service ({0}) instance #{1} does not exist'.format(
                service['name'], instance_id))
        instance = instance[0]

        if instance.get('hibernating', False):
            self.error('It looks like your container is currently hibernating '
                'and can\'t be accessed through SSH. Please issue an HTTP '
                'request to your application in order to wake it up.')
            self.info('Sandbox applications are put in hibernation when they '
                'don\'t receive traffic for a given amount of time. Upgrade '
                'to live to remove this limitation.')
            self.die('Wake up your application and try again.')

        try:
            ssh_endpoint = filter(lambda p: p['name'] == 'ssh',
                    instance.get('ports', []))[0]['url']
        except (IndexError, KeyError):
            self.die('No ssh endpoint for service ({0}) instance #{1}'.format(
                service['name'], instance_id))

        url = self.parse_url(ssh_endpoint)
        if None in [url['host'], url['port']]:
            self.die('Invalid ssh endpoint "{0}" ' \
                    'for service ({1}) instance #{2}'.format(
                        ssh_endpoint, service['name'], instance_id))

        return dict(service=service['name'],
                instance=instance_id, host=url['host'], port=url['port'],
                user=url.get('user', 'dotcloud'),
                )

    def spawn_ssh(self, ssh_endpoint, cmd_args=None):
        ssh_args = self.common_ssh_options + [
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'LogLevel=ERROR',
            '-l', ssh_endpoint['user'],
            '-p', str(ssh_endpoint['port']),
            ssh_endpoint['host']
        ]
        if os.isatty(sys.stdin.fileno()):
            ssh_args.append('-t')
        if cmd_args:
            ssh_args.append('--')
            ssh_args.extend(cmd_args)
        return subprocess.Popen(ssh_args)

    @app_local
    def cmd_run(self, args):
        ssh_endpoint = self.get_ssh_endpoint(args)
        if args.command:
            cmd = ['bash -l -c "{0} {1}"'.format(args.command , ' '.join(args.args))]
            self.info('Executing "{0}" on service ({1}) instance #{2} (application {3})'.format(
                ' '.join([args.command] + args.args), ssh_endpoint['service'],
                ssh_endpoint['instance'], args.application))
        else:
            cmd = None
            self.info('Opening a shell on service ({0}) instance #{1} (application {2})'.format(
                    ssh_endpoint['service'], ssh_endpoint['instance'],
                    args.application))
        return self.spawn_ssh(ssh_endpoint, cmd).wait()

    def cmd_ssh(self, args):
        self.warning('This command is deprecated. Use "dotcloud run" instead.')

    def parse_url(self, url):
        m = re.match('^(?P<scheme>[^:]+)://((?P<user>[^@]+)@)?(?P<host>[^:/]+)(:(?P<port>\d+))?(?P<path>/.*)?$', url)
        if not m:
            raise ValueError('"{url}" is not a valid url'.format(url=url))
        ret = m.groupdict()
        return ret

    @app_local
    def cmd_restart(self, args):
        # FIXME: Handle --all?
        service_name, instance_id = self.parse_service_instance(args.instance, args.cmd)

        url = '/applications/{0}/services/{1}/instances/{2}/status' \
            .format(args.application, service_name, instance_id)
        try:
            self.user.put(url, {'status': 'restart'})
        except RESTAPIError as e:
            if e.code == 404:
                self.die('Service ({0}) instance #{1} not found'.format(
                    service_name, instance_id))
            raise
        self.info('Service ({0}) instance #{1} of application {2} is being restarted.'.format(
            service_name, instance_id, args.application))

    def iso_dtime_local(self, strdate):
        try:
            return datetime.datetime.strptime(strdate, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            return datetime.datetime.strptime(strdate, "%Y-%m-%dT%H:%M:%SZ")

    def cmd_activity(self, args):
        if not args.all and args.application:
            url = '/applications/{0}/activity'.format(args.application)
        else:
            url = '/activity'
        activities = self.user.get(url).items
        print 'time', ' ' * 14,
        print 'category action   application.service (details)'
        for activity in activities:
            print '{ts:19} {category:8} {action:8}'.format(
                    ts=str(self.iso_dtime_local(activity['created_at'])),
                    **activity),
            category = activity['category']
            if category == 'app':
                print '{application}'.format(**activity),
                if activity['action'] == 'deploy':
                    print '(revision={revision} build={build})' \
                        .format(**activity),
            elif category == 'domain':
                print '{application}.{service}'.format(**activity),
                print '(cname={domain})'.format(**activity),
            elif category == 'service':
                print '{application}.{service}'.format(**activity),
                action = activity['action']
                if action == 'scale':
                    scale = activity['scale']
                    if scale == 'instances':
                        print '(instances={0})'.format(activity['value']),
                    elif scale == 'memory':
                        print '(memory={0})'.format(
                                bytes2human(activity['value'])
                                ),
            user = activity.get('user')
            if user is not None and not user['self']:
                print '/by <{0}>'.format(user.get('username')),
            print

    @app_local
    def cmd_dlist(self, args):
        deployments = self.user.get('/applications/{0}/deployments'.format(
            args.application))
        print 'deployment date', ' ' * 3,
        print 'revision', ' ' * 15, 'deploy_id [application {0}]'.format(args.application)
        deploy_id = None
        previous_deploy_id = None
        for log in deployments.items:
            previous_deploy_id = deploy_id
            ts = self.iso_dtime_local(log['created_at'])
            deploy_id = log['deploy_id']
            print '{0} {1:24} {2}'.format(ts, log['revision'], deploy_id)

        if previous_deploy_id:
            print '-- <hint> display previous deployment\'s logs:'
            print self._fmt_deploy_logs_command(previous_deploy_id)
        print '-- <hint> display latest deployment\'s logs:'
        print self._fmt_deploy_logs_command('latest')

    def _stream_formated_logs(self, url, filter_svc=None, filter_inst=None):
        response = self.user.get(url, streaming=True)
        meta = response.item
        def _iterator():
            last_ts = None
            for log in response.items:
                raw_ts = log.get('created_at')
                if raw_ts is not None:
                    ts = self.iso_dtime_local(log['created_at'])
                    if self.debug and (last_ts is None or (last_ts.day != ts.day
                            or last_ts.month != ts.month
                            or last_ts.year != ts.year
                            )):
                        print '- {0} ({1} deployment, deploy_id={2})'.format(ts.date(),
                                meta['application'], meta['deploy_id'])
                    last_ts = ts
                    line = '{0}: '.format(ts.time())
                else:
                    line = ''

                tags = ''
                svc = log.get('service')
                inst = log.get('instance')

                if filter_svc:
                    if filter_svc != svc:
                        continue
                    if (filter_inst is not None and inst is not None
                            and filter_inst != int(inst)):
                        continue

                if svc is not None:
                    if inst is not None:
                        tags = '[{0}.{1}] '.format(svc, inst)
                    else:
                        tags = '[{0}] '.format(svc)
                else:
                    tags = '--> '

                line += '{0}{1}'.format(tags, log['message'])
                if log.get('level') == 'ERROR':
                    line = '{c.red}{0}{c.reset}'.format(line, c=self.colors)

                yield log, line
        return meta, _iterator()

    def _stream_deploy_logs(self, app, did=None, filter_svc=None,
            filter_inst=None, deploy_trace_id=None, follow=False, lines=None):
        url = '/applications/{0}/deployments/{1}/logs?stream'.format(app,
                did or 'latest')

        if follow:
            url += '&follow'

        if lines is not None:
            url += '&lines={0}'.format(lines)

        last_read_ts = None
        retry = 10 if follow else 1
        while retry > 0:
            logs_meta, logs = self._stream_formated_logs(url, filter_svc, filter_inst)
            for log, formated_line in logs:

                ts = self.iso_dtime_local(log['created_at'])
                if last_read_ts and last_read_ts >= ts:
                    continue
                last_read_ts = ts

                if log.get('partial', False):
                    print formated_line, '\r',
                    sys.stdout.flush()
                else:
                    print formated_line

                status = log.get('status')
                if status is not None:
                    if status == 'deploy_end':
                        return 0
                    if status == 'deploy_fail':
                        return 2

            retry -= 1
            if retry > 0:
                sys.stderr.write('.')
                time.sleep(1)

        if not follow:
            return 0

        self.error('The connection was lost, ' \
                'but the deployment is still running in the background.')
        if deploy_trace_id is not None:
            self.error('If this message happens too often, please e-mail\n' \
                    'support@dotcloud.com and mention this trace ID: {0}'
                .format(deploy_trace_id))
        self.error('if you want to continue following your deployment, ' \
                'try:\n{0}'.format(
                    self._fmt_deploy_logs_command(logs_meta.get('deploy_id',
                        did))))
        self.die()

    def _fmt_deploy_logs_command(self, deploy_id):
        return '{0} dlogs {1}'.format(self.cmd, deploy_id)

    @app_local
    def cmd_dlogs(self, args):
        filter_svc = None
        filter_inst = None
        if args.service_or_instance:
            parts = args.service_or_instance.split('.')
            filter_svc = parts[0]
            if len(parts) > 1:
                filter_inst = int(parts[1])

        follow = not args.no_follow if (filter_svc is None and (args.lines is
            None or args.lines > 0)) else False
        return self._stream_deploy_logs(args.application, did=args.deployment_id,
                filter_svc=filter_svc, filter_inst=filter_inst,
                follow=follow, lines=args.lines)

    @app_local
    def cmd_logs(self, args):
        url = '/applications/{0}/logs?stream'.format(
                args.application)

        if not args.no_follow:
            url += '&follow'

        if args.lines is not None:
            url += '&lines={0}'.format(args.lines)

        if args.service_or_instance:
            url += '&filter={0}'.format(','.join(args.service_or_instance))

        logs_meta, logs = self._stream_formated_logs(url)
        empty = True
        for log, formated_line, in logs:
            empty = False
            if log.get('partial', False):
                print formated_line, '\r',
                sys.stdout.flush()
            else:
                print formated_line

        if empty is True and args.service_or_instance:
            self.warning('Nothing to show... Does the service named \"{0}\" exist?'.format(
                args.service_or_instance[0]))

    @app_local
    def cmd_revisions(self, args):
        self.info('Revisions for application {0}:'.format(args.application))
        url = '/applications/{0}/revisions'.format(
                args.application)
        versions = [x['revision'] for x in self.user.get(url).items]

        try:
            url = '/applications/{0}/revision'.format(args.application)
            revision = self.user.get(url).item['revision']
        except RESTAPIError as e:
            if e.code != 404:
                raise
            revision = None

        for version in versions:
            if revision == version:
                print '*', self.colors.green(version)
            else:
                print ' ', version

    @app_local
    def cmd_upgrade(self, args):
        app_url = '/applications/{0}'.format(args.application)
        if not args.service:
            application = self.user.get(app_url).item
            # Unfortunately we don't get the details (such as the
            # image_revision) we need on the service in the application object.
            # So we will have to query the REST API for each service later.
            services = [svc['name'] for svc in application.get('services', [])]
        else:
            services = [args.service]

        upgradeable = set() # List of services that have an upgrade available
        upgrade = set() # List of services we can upgrade with a clean deploy
        for service_name in services:
            service_url = '{0}/services/{1}'.format(app_url, service_name)
            service = self.user.get(service_url).item

            service_type = service.get('service_type')
            service_instances = service.get('instances')
            if not service_type or not service_instances:
                continue

            service_revision = service_instances[0].get('image_version')
            image_upgrade = service_instances[0].get('image_upgrade')
            if not service_revision or not image_upgrade:
                continue

            # Fetch informations about the current and the latest revisions
            # of the service image (note: we could put that into a cache,
            # in case the app has several service of the same type at the
            # same revision):
            image_infos = self.client.get(
                '/images/{0}'.format(service_type)
            ).item
            upgrade_revision_infos = image_infos['latest_revision']
            service_revision_infos = self.client.get(
                '/images/{0}/revisions/{1}'.format(
                    service_type, service_revision
                )
            ).item

            upgradeable.add(service_name)
            if image_infos['upgradeable']:
                upgrade.add(service_name)

            self.info(
                "{service} can be {how} upgraded from {type}/{from_rev} "
                "({from_date}) to {type}/{to_rev} ({to_date})".format(
                    service=service_name,
                    how='automatically' if image_infos['upgradeable'] else 'manually',
                    type=service_type,
                    from_rev=service_revision,
                    from_date=self.iso_dtime_local(service_revision_infos['date']).date(),
                    to_rev=upgrade_revision_infos['revision'],
                    to_date=self.iso_dtime_local(upgrade_revision_infos['date']).date()
                )
            )

        if not upgradeable:
            self.success("All the services are up to date in {0}".format(args.application))
            return

        if upgrade and not args.dry_run and self.confirm(args, "Upgrade {0}?".format(", ".join(upgrade))):
            manual_upgrades = upgradeable - upgrade
            if len(upgrade) == 1:
                single_service = upgrade.pop()
                self.info("Upgrading {0}".format(single_service))
                self.deploy(args.application, clean=True, service=single_service)
            else:
                self.info(
                    "Upgrading all the automatically upgradeable services "
                    "in {0}".format(args.application)
                )
                self.deploy(args.application, clean=True)
            if manual_upgrades:
                self.info("{0} must be upgraded manually.".format(", ".join(manual_upgrades)))

########NEW FILE########
__FILENAME__ = colors
"""
dotcloud.ui.colors - Pythonic wrapper around colorama

Usage:
    colors = Colors()

    # Format string inlining
    print '{c.green}->{c.reset} Hello world!'.format(c=colors)

    # Call
    print colors.blue('Hello world!')

    # Wrapper
    with colors.red:
        print 'Hello world'

"""

import sys
import colorama

colorama.init()


class Colors(object):
    def __init__(self, disable_colors=None):
        """ Initialize Colors

        disable_colors can be either:
            * True: Disable colors. Useful to disable colors dynamically
            * None: Automatic colors. Colors will be enabled unless stdin is
                    not a tty (for instance if piped to another program).
            * False: Force enable colors, even if not running on a pty.
        """
        self.disable_colors = disable_colors
        if self.disable_colors is None:
            self.disable_colors = False if sys.stdout.isatty() else True

    def __getattr__(self, color):
        if self.disable_colors:
            return Color(None)
        color = color.upper()
        if color in ['DIM', 'BRIGHT']:
            return getattr(colorama.Style, color.upper())
        if color == 'RESET':
            return colorama.Style.RESET_ALL
        return Color(color)


class Color(object):
    def __init__(self, color):
        self.color = self._lookup_color(color)

    def _lookup_color(self, color):
        """ Lookup color by name """
        if color is None:
            return None
        if not hasattr(colorama.Fore, color.upper()):
            raise KeyError('Unknown color "{0}"'.format(color))
        return getattr(colorama.Fore, color.upper())

    def __enter__(self):
        if self.color is not None:
            sys.stdout.write(self.color)

    def __exit__(self, type, value, traceback):
        if self.color is not None:
            sys.stdout.write(colorama.Style.RESET_ALL)

    def __str__(self):
        if self.color is None:
            return ''
        return self.color

    def __call__(self, text):
        if self.color is None:
            return text
        return '{color}{text}{reset}'.format(
            color=self.color,
            text=text,
            reset=colorama.Style.RESET_ALL
            )

########NEW FILE########
__FILENAME__ = config
import os
import json


# OAuth2 client key and secret
CLIENT_KEY = '9b8d4bc07a4a60f7536cafd46ec492'
CLIENT_SECRET = '2fa7e44a09e3c9b7d63de7ffb97112'


class GlobalConfig(object):
    def __init__(self):
        self.dir = os.path.expanduser('~/.dotcloud_cli')
        self.path = self.path_to('config')
        self.key = self.path_to('dotcloud.key')
        self.load()

    def path_to(self, name):
        path = os.path.join(self.dir, name)
        if os.environ.get('SETTINGS_FLAVOR'):
            path = path + '.' + os.environ.get('SETTINGS_FLAVOR')
        return path

    def load(self):
        try:
            self.data = json.load(file(self.path))
            self.loaded = True
        except (IOError, ValueError):
            self.loaded = False

    def save(self):
        if not os.path.exists(self.dir):
            os.mkdir(self.dir, 0700)
        try:
            f = open(self.path, 'w+')
            json.dump(self.data, f, indent=4)
        except:
            raise

    def get(self, *args):
        if not self.loaded:
            return None
        return self.data.get(*args)

    def save_key(self, key):
        f = open(self.key, 'w')
        f.write(key)
        try:
            os.fchmod(f.fileno(), 0600)
        except:
            pass
        f.close()

########NEW FILE########
__FILENAME__ = debug
import socket
import time
import wsgiref.handlers

from ..client.client import RESTClient

# Monkey patch socket.create_connection to track the IP address, port,
# and timestamp of TCP connections that we create.
# What we really want to know is which API endpoint was contacted, and
# when, to report it when an error occurs.
# WARNING: this is absolutely not thread- or async- safe. Yuck!
# However, requests/urllib3 do not expose the necessary hooks to get
# this information cleanly and reliably.
_real_create_connection = socket.create_connection
def _fake_create_connection(*args, **kwargs):
    global_endpoint_info.clear()
    sock = _real_create_connection(*args, **kwargs)
    remotehost, remoteport = sock.getpeername()
    localtimestamp = wsgiref.handlers.format_date_time(time.time())
    global_endpoint_info['remotehost'] = remotehost
    global_endpoint_info['remoteport'] = remoteport
    global_endpoint_info['timestamp'] = localtimestamp
    global_endpoint_info['timesource'] = 'local'
    global_endpoint_info['localtimestamp'] = localtimestamp
    global_endpoint_info['remotetimestamp'] = None
    return sock
socket.create_connection = _fake_create_connection

# Likewise, monkey patch make_response to intercept HTTP headers,
# and save the remote server date.
_real_make_response = RESTClient.make_response
def _fake_make_response(self, res, *args, **kwargs):
    remotetimestamp = res.headers.get('Date')
    if remotetimestamp:
        global_endpoint_info['timestamp'] = remotetimestamp
        global_endpoint_info['timesource'] = 'remote'
        global_endpoint_info['remotetimestamp'] = remotetimestamp
    return _real_make_response(self, res, *args, **kwargs)
RESTClient.make_response = _fake_make_response

global_endpoint_info = {}

########NEW FILE########
__FILENAME__ = parser
import argparse
import sys
from .version import VERSION
from ..packages.bytesconverter import human2bytes


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print >>sys.stderr, 'error: {0}'.format(message)
        self.print_help()
        sys.exit(1)


class ScaleOperation(object):
    def __init__(self, kv):
        if kv.startswith('=') or kv.count('=') != 1:
            raise argparse.ArgumentTypeError('Invalid action "{0}"'.format(kv))
        (k, v) = kv.split('=')
        if not v:
            raise argparse.ArgumentTypeError('Invalid value for "{0}"'.format(k))
        if ':' in k:
            (self.name, self.action) = k.split(':', 1)
        else:
            (self.name, self.action) = (k, 'instances')

        if self.action not in ['instances', 'memory']:
            raise argparse.ArgumentTypeError('Invalid action for "{0}": '
                    'Action must be either "instances" or "memory"'
                    .format(self.action))

        if self.action == 'instances':
            try:
                self.original_value = int(v)
                self.value = int(v)
            except ValueError:
                raise argparse.ArgumentTypeError(
                        'Invalid value for "{0}": Instance count must be a number'.format(kv))
        elif self.action == 'memory':
            self.original_value = v
            # Normalize the memory value
            v = v.upper()
            # Strip the trailing B as human2bytes doesn't handle those
            if v.endswith('B'):
                v = v[:-1]
            if v.isdigit():
                self.value = int(v)
            else:
                try:
                    self.value = human2bytes(v)
                except Exception:
                    raise argparse.ArgumentTypeError('Invalid value for "{0}"'.format(kv))


def validate_env(kv):
    # Expressions must contain a name and '='.
    if kv.find('=') in (-1, 0):
        raise argparse.ArgumentTypeError(
                '"{0}" is an invalid environment variable expresion. '
                'Environment variables are set like "foo=bar".'.format(kv))
    return kv


def get_parser(name='dotcloud'):
    # The common parser is used as a parent for all sub-commands so that
    # they all share --application
    common_parser = Parser(prog=name, add_help=False)
    common_parser.add_argument('--application', '-A', help='Specify the application')
    common_parser.add_argument('--debug', '-D', action='store_true',
            help='Enable debug messages (same as "export DOTCLOUD_DEBUG=true")')
    common_parser.add_argument('--assume-yes', '-y', action='store_true',
            help='Automatic yes to prompts; assume "yes" as answer to all prompts'
                 ' and run non-interactively.')
    common_parser.add_argument('--assume-no', '-o', action='store_true',
            help='Automatic "no" to all prompts.')

    # The "connect" and "create" share some options, as "create" will
    # offer to connect the current directory to the new application.
    connect_options_parser = Parser(prog=name, add_help=False)
    rsync_or_dvcs = connect_options_parser.add_mutually_exclusive_group()
    rsync_or_dvcs.add_argument('--rsync', action='store_true',
            help='Always use rsync to push (default)')
    rsync_or_dvcs.add_argument('--git', action='store_true',
            help='Always use git to push')
    rsync_or_dvcs.add_argument('--hg', action='store_true',
            help='Always use mercurial to push')
    connect_options_parser.add_argument('--branch', '-b', metavar='NAME',
            help='Always use this branch when pushing via DVCS. '
                 '(If not set, each push will use the active branch by default)')

    # Define all of the commands...
    parser = Parser(prog=name, description='dotcloud CLI',
            parents=[common_parser])
    parser.add_argument('--version', '-v', action='version', version='dotcloud/{0}'.format(VERSION))

    subcmd = parser.add_subparsers(dest='cmd')

    # dotcloud setup
    setup = subcmd.add_parser('setup', help='Setup the client authentication')
    setup.add_argument('--api-key', action='store_true',
            help='Authenticate using an API Key rather than username/password combination.')

    # dotcloud check
    subcmd.add_parser('check', help='Check the installation and authentication')

    # dotcloud list
    subcmd.add_parser('list', help='List all applications')

    # dotcloud connect
    connect = subcmd.add_parser('connect',
            help='Connect a local directory to an existing application',
            parents=[connect_options_parser])
    connect.add_argument('application', help='Specify the application')

    # dotcloud disconnect
    subcmd.add_parser('disconnect',
            help='Disconnect the current directory from its application')

    # dotcloud create
    create = subcmd.add_parser('create', help='Create a new application',
            parents=[connect_options_parser])
    create.add_argument('--flavor', '-f', default='live',
            help='Choose a flavor for your application. Defaults to live, a paid service.')
    create.add_argument('application', help='Specify the application')

    # dotcloud destroy
    destroy = subcmd.add_parser('destroy', help='Destroy a whole app or a specific service',
            parents=[common_parser])
    destroy.add_argument('service', nargs='?', help='Specify the service')

    # dotcloud app
    subcmd.add_parser('app',
            help='Display the application name connected to the current directory')

    # dotcloud activity
    activity = subcmd.add_parser('activity', help='Display your recent activity',
            parents=[common_parser])
    activity.add_argument('--all' ,'-a', action='store_true',
            help='Print out your activities among all your applications rather than the '
                 'currently connected or selected one. (This is the default behavior when '
                 'not connected to any application.)')

    # dotcloud info
    info = subcmd.add_parser('info', help='Get information about the application or service',
            parents=[common_parser])
    info.add_argument('service', nargs='?', help='Specify the service')

    # dotcloud url
    url = subcmd.add_parser('url', help='Display the URL(s) for the application',
            parents=[common_parser])
    url.add_argument('service', nargs='?', help='Specify the service')

    # dotcloud status
    status = subcmd.add_parser('status', help='Probe the status of a service',
            parents=[common_parser])
    status.add_argument('service', help='Specify the service')

    # dotcloud open
    open_ = subcmd.add_parser('open', help='Open the application in the browser',
            parents=[common_parser])
    open_.add_argument('service', nargs='?', help='Specify the service')

    # dotcloud run service ...
    run = subcmd.add_parser('run',
            help='Open a shell or run a command inside a service instance',
            parents=[common_parser])
    run.add_argument('service_or_instance',
            help='Open a shell or run the command on the first instance of a given service '
                 '(ex: www) or a specific one (ex: www.1)')
    run.add_argument('command', nargs='?',
            help='The command to execute on the service\'s instance. '
                 'If not specified, open a shell.')
    run.add_argument('args', nargs=argparse.REMAINDER, metavar='...',
            help='Any arguments to the command')

    # dotcloud memory
    memory = subcmd.add_parser('memory',
            help='Gets memory metrics for a specific service and instance',
            parents=[common_parser])
    memory.add_argument('service_or_instance',
            help='Open a shell or run the command on a specific instance of a given service (ex: www.1)')
    memory.add_argument('duration', help="Specify the duration of time to receive data (ex: 1h for last 60 minutes)")

    # dotcloud traffic
    traffic = subcmd.add_parser('traffic',
            help='Gets traffic metrics for your application',
            parents=[common_parser])
    traffic.add_argument('duration', help="Specify the duration of time to receive data (ex: 1h for last 60 minutes)")

    # dotcloud ssh (alias to run)
    ssh = subcmd.add_parser('ssh',
            help='DEPRECATED. Use "dotcloud run"', add_help=False)

    # dotcloud push
    push = subcmd.add_parser('push', help='Push the code', parents=[common_parser])
    push.add_argument('path', nargs='?', default=None,
            help='Path to the directory to push (by default "./")')
    push.add_argument('--clean', action='store_true',
            help='Do a full build (rather than incremental)')
    push.add_argument('--verbose', action='store_true',
            help='Provide verbose output during push')
    rsync_or_dvcs = push.add_mutually_exclusive_group()
    rsync_or_dvcs.add_argument('--rsync', action='store_true', help='Use rsync to push (default)')
    rsync_or_dvcs.add_argument('--git', action='store_true', help='Use git to push')
    rsync_or_dvcs.add_argument('--hg', action='store_true', help='Use mercurial to push')
    branch_or_commit = push.add_mutually_exclusive_group()
    branch_or_commit.add_argument('--branch', '-b', metavar='NAME',
            help='Specify the branch to push when pushing via DVCS '
                 '(by default, use the active one)')
    branch_or_commit.add_argument('--commit', '-c', metavar='HASH',
            help='Specify the commit hash to push when pushing via DVCS '
                 '(by default, use the latest one)')

    # dotcloud deploy revision
    deploy = subcmd.add_parser('deploy', help='Deploy a specific revision',
            parents=[common_parser])
    deploy.add_argument('revision',
            help='Revision to deploy (Symbolic revisions "latest" and "previous" are supported)')
    deploy.add_argument('--clean', action='store_true',
            help='If a build is needed, do a full build (rather than incremental)')

    # dotcloud dlist
    subcmd.add_parser('dlist', help='List recent deployments', parents=[common_parser])

    # dotcloud dlogs deployment
    dlogs = subcmd.add_parser('dlogs', help='Review past deployments or watch one in-flight',
            parents=[common_parser])
    dlogs.add_argument('deployment_id',
            help='Which recorded deployment to view (discoverable with the command, '
                 '"dotcloud dlist") or "latest".')
    dlogs.add_argument('service_or_instance', nargs='?',
            help='Filter logs by a given service (ex: www) or a specific instance (ex: www.0). ')
    dlogs.add_argument('--no-follow', '-N', action='store_true',
            help='Do not follow real-time logs')
    dlogs.add_argument('--lines', '-n', type=int, metavar='N',
            help='Tail only N logs (before following real-time logs by default)')

#    dlogs.add_argument('--build', action='store_true',
#            help='Retrieve only build logs.')
#    dlogs.add_argument('--install', action='store_true',
#            help='Retrieve only install logs.')

#    dlogs.add_argument('--head', '-H', type=int, metavar='N',
#            help='Display the first N logs.'
#            ' Wait after real-time logs if needed.'
#            ' If --no-follow, display up to N recorded logs')

#    dlogs.add_argument('--from', metavar='DATE',
#            help='Start from DATE. DATE Can be XXX define format XXX'
#            ' or a negative value from now (ex: -1h)')
#    dlogs.add_argument('--to', metavar='DATE',
#            help='End at DATE. Same format as --from.'
#            ' If --no-follow, display up to DATE'
#            )

    # dotcloud logs
    logs = subcmd.add_parser('logs', help='View your application logs or watch logs live',
            parents=[common_parser])
    logs.add_argument('service_or_instance',
            nargs='*',
            help='Display only logs of a given service (ex: www) or a specific instance (ex: www.1)')
    logs.add_argument('--no-follow', '-N', action='store_true',
            help='Do not follow real-time logs')
    logs.add_argument('--lines', '-n', type=int, metavar='N',
            help='Tail only N logs (before following real-time logs by default)')

    # dotcloud var <list/set/unset> ...
    var = subcmd.add_parser('env', help='Manipulate application environment variables',
            parents=[common_parser]).add_subparsers(dest='subcmd')
    var.add_parser('list', help='List the application environment variables',
            parents=[common_parser])
    var_set = var.add_parser('set', help='Set application environment variables',
            parents=[common_parser])
    var_set.add_argument('variables', help='Application environment variables to set',
            metavar='key=value', nargs='+', type=validate_env)
    var_unset = var.add_parser('unset', help='Unset (remove) application environment variables',
            parents=[common_parser])
    var_unset.add_argument('variables', help='Application environment variables to unset',
            metavar='var', nargs='+')

    # dotcloud scale foo=3 bar:memory=128M
    scale = subcmd.add_parser('scale', help='Scale services',
            description='Manage horizontal (instances) or vertical (memory) scaling of services',
            parents=[common_parser])
    scale.add_argument('services', nargs='+', metavar='service:action=value',
                       help='Scaling action to perform e.g. www:instances=2 or www:memory=1gb',
                       type=ScaleOperation)

    # dotcloud restart foo.0
    restart = subcmd.add_parser('restart', help='Restart a service instance',
            parents=[common_parser])
    restart.add_argument('instance',
            help='Restart the first instance of a given service (ex: www) or '
                 'a specific one (ex: www.1)')

    # dotcloud domain <list/add/rm> service domain
    domain = subcmd.add_parser('domain', help='Manage domains for the service',
            parents=[common_parser]).add_subparsers(dest='subcmd')
    domain.add_parser('list', help='List the domains', parents=[common_parser])
    domain_add = domain.add_parser('add', help='Add a new domain', parents=[common_parser])
    domain_add.add_argument('service', help='Service to set domain for')
    domain_add.add_argument('domain', help='New domain name')
    domain_rm = domain.add_parser('rm', help='Remove a domain', parents=[common_parser])
    domain_rm.add_argument('service', help='Service to remove the domain from')
    domain_rm.add_argument('domain', help='Domain name to remove')

    # dotcloud revisions
    revisions = subcmd.add_parser('revisions',
            help='Display all the known revision of the application',
            parents=[common_parser])

    # dotcloud upgrade
    upgrade = subcmd.add_parser('upgrade',
            help='Upgrade a service to a new image revision',
            parents=[common_parser])
    upgrade.add_argument('--dry-run', '-n', action='store_true',
            help='Only check if you can upgrade services to a newer service revision')
    upgrade.add_argument('service', help='Service to upgrade', nargs='?')

    return parser

########NEW FILE########
__FILENAME__ = test_hello
from dotcloud.cli2 import CLI

def test_hello():
    CLI().run()
    assert True

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals
import sys

def get_columns_width(rows):
    width = {}
    for row in rows:
        for (idx, word) in enumerate(map(unicode, row)):
            width.setdefault(idx, 0)
            width[idx] = max(width[idx], len(word))
    return width

def pprint_table(rows):
    rows = list(rows)
    width = get_columns_width(rows)

    def print_separator():
        if not rows:
            return
        sys.stdout.write('+')
        for (idx, word) in enumerate(map(unicode, rows[0])):
            sys.stdout.write('-{sep}-+'.format(sep=('-' * width[idx])))
        print ''

    print_separator()
    for row_idx, row in enumerate(rows):
        sys.stdout.write('|')
        for (idx, word) in enumerate(map(unicode, row)):
            sys.stdout.write(' {word:{width}} |'.format(word=word, width=(width[idx]))),
        print ''
        if row_idx == 0:
            # We just printed the table header
            print_separator()
    print_separator()


def pprint_kv(items, separator=':', padding=2, offset=0, skip_empty=True):
    if not items:
        return
    width = max([len(item[0]) for item in items if item[1] or not skip_empty]) + padding
    for item in items:
        (key, value) = item
        if not value:
            continue
        if isinstance(value, list) or isinstance(value, tuple):
            print '{align}{0}:'.format(key, align=' ' * offset)
            pprint_kv(value, offset=offset + 2)
        else:
            print'{align}{key:{width}}{value}'.format(
                align=' ' * offset,
                key='{0}{1}'.format(key, separator),
                value=value,
                width=width)

########NEW FILE########
__FILENAME__ = version
VERSION = '0.9.8'

########NEW FILE########
