__FILENAME__ = cli
"""CLI arguments definition.

NOTE: the CLI interface may change before reaching v1.0.

"""
from textwrap import dedent, wrap
#noinspection PyCompatibility
from argparse import (RawDescriptionHelpFormatter, FileType,
                      OPTIONAL, ZERO_OR_MORE, SUPPRESS)

from httpie import __doc__, __version__
from httpie.plugins.builtin import BuiltinAuthPlugin
from httpie.plugins import plugin_manager
from httpie.sessions import DEFAULT_SESSIONS_DIR
from httpie.output.formatters.colors import AVAILABLE_STYLES, DEFAULT_STYLE
from httpie.input import (Parser, AuthCredentialsArgType, KeyValueArgType,
                          SEP_PROXY, SEP_CREDENTIALS, SEP_GROUP_ALL_ITEMS,
                          OUT_REQ_HEAD, OUT_REQ_BODY, OUT_RESP_HEAD,
                          OUT_RESP_BODY, OUTPUT_OPTIONS,
                          OUTPUT_OPTIONS_DEFAULT, PRETTY_MAP,
                          PRETTY_STDOUT_TTY_ONLY, SessionNameValidator,
                          readable_file_arg)


class HTTPieHelpFormatter(RawDescriptionHelpFormatter):
    """A nicer help formatter.

    Help for arguments can be indented and contain new lines.
    It will be de-dented and arguments in the help
    will be separated by a blank line for better readability.


    """
    def __init__(self, max_help_position=6, *args, **kwargs):
        # A smaller indent for args help.
        kwargs['max_help_position'] = max_help_position
        super(HTTPieHelpFormatter, self).__init__(*args, **kwargs)

    def _split_lines(self, text, width):
        text = dedent(text).strip() + '\n\n'
        return text.splitlines()

parser = Parser(
    formatter_class=HTTPieHelpFormatter,
    description='%s <http://httpie.org>' % __doc__.strip(),
    epilog=dedent("""
    For every --OPTION there is also a --no-OPTION that reverts OPTION
    to its default value.

    Suggestions and bug reports are greatly appreciated:

        https://github.com/jakubroztocil/httpie/issues

    """)
)


#######################################################################
# Positional arguments.
#######################################################################

positional = parser.add_argument_group(
    title='Positional Arguments',
    description=dedent("""
    These arguments come after any flags and in the order they are listed here.
    Only URL is required.

    """)
)
positional.add_argument(
    'method',
    metavar='METHOD',
    nargs=OPTIONAL,
    default=None,
    help="""
    The HTTP method to be used for the request (GET, POST, PUT, DELETE, ...).

    This argument can be omitted in which case HTTPie will use POST if there
    is some data to be sent, otherwise GET:

        $ http example.org               # => GET
        $ http example.org hello=world   # => POST

    """
)
positional.add_argument(
    'url',
    metavar='URL',
    help="""
    The scheme defaults to 'http://' if the URL does not include one.

    You can also use a shorthand for localhost

        $ http :3000                    # => http://localhost:3000
        $ http :/foo                    # => http://localhost/foo

    """
)
positional.add_argument(
    'items',
    metavar='REQUEST_ITEM',
    nargs=ZERO_OR_MORE,
    type=KeyValueArgType(*SEP_GROUP_ALL_ITEMS),
    help=r"""
    Optional key-value pairs to be included in the request. The separator used
    determines the type:

    ':' HTTP headers:

        Referer:http://httpie.org  Cookie:foo=bar  User-Agent:bacon/1.0

    '==' URL parameters to be appended to the request URI:

        search==httpie

    '=' Data fields to be serialized into a JSON object (with --json, -j)
        or form data (with --form, -f):

        name=HTTPie  language=Python  description='CLI HTTP client'

    ':=' Non-string JSON data fields (only with --json, -j):

        awesome:=true  amount:=42  colors:='["red", "green", "blue"]'

    '@' Form file fields (only with --form, -f):

        cs@~/Documents/CV.pdf

    '=@' A data field like '=', but takes a file path and embeds its content:

         essay=@Documents/essay.txt

    ':=@' A raw JSON field like ':=', but takes a file path and embeds its content:

        package:=@./package.json

    You can use a backslash to escape a colliding separator in the field name:

        field-name-with\:colon=value

    """
)


#######################################################################
# Content type.
#######################################################################

content_type = parser.add_argument_group(
    title='Predefined Content Types',
    description=None
)

content_type.add_argument(
    '--json', '-j',
    action='store_true',
    help="""
    (default) Data items from the command line are serialized as a JSON object.
    The Content-Type and Accept headers are set to application/json
    (if not specified).

    """
)
content_type.add_argument(
    '--form', '-f',
    action='store_true',
    help="""
    Data items from the command line are serialized as form fields.

    The Content-Type is set to application/x-www-form-urlencoded (if not
    specified). The presence of any file fields results in a
    multipart/form-data request.

    """
)


#######################################################################
# Output processing
#######################################################################

output_processing = parser.add_argument_group(title='Output Processing')

output_processing.add_argument(
    '--pretty',
    dest='prettify',
    default=PRETTY_STDOUT_TTY_ONLY,
    choices=sorted(PRETTY_MAP.keys()),
    help="""
    Controls output processing. The value can be "none" to not prettify
    the output (default for redirected output), "all" to apply both colors
    and formatting (default for terminal output), "colors", or "format".

    """
)
output_processing.add_argument(
    '--style', '-s',
    dest='style',
    metavar='STYLE',
    default=DEFAULT_STYLE,
    choices=AVAILABLE_STYLES,
    help="""
    Output coloring style (default is "{default}"). One of:

{available}

    For this option to work properly, please make sure that the $TERM
    environment variable is set to "xterm-256color" or similar
    (e.g., via `export TERM=xterm-256color' in your ~/.bashrc).

    """.format(
        default=DEFAULT_STYLE,
        available='\n'.join(
            '{0}{1}'.format(8*' ', line.strip())
            for line in wrap(', '.join(sorted(AVAILABLE_STYLES)), 60)
        ).rstrip(),
    )
)


#######################################################################
# Output options
#######################################################################
output_options = parser.add_argument_group(title='Output Options')

output_options.add_argument(
    '--print', '-p',
    dest='output_options',
    metavar='WHAT',
    help="""
    String specifying what the output should contain:

        '{req_head}' request headers
        '{req_body}' request body
        '{res_head}' response headers
        '{res_body}' response body

    The default behaviour is '{default}' (i.e., the response headers and body
    is printed), if standard output is not redirected. If the output is piped
    to another program or to a file, then only the response body is printed
    by default.

    """
    .format(
        req_head=OUT_REQ_HEAD,
        req_body=OUT_REQ_BODY,
        res_head=OUT_RESP_HEAD,
        res_body=OUT_RESP_BODY,
        default=OUTPUT_OPTIONS_DEFAULT,
    )
)
output_options.add_argument(
    '--verbose', '-v',
    dest='output_options',
    action='store_const',
    const=''.join(OUTPUT_OPTIONS),
    help="""
    Print the whole request as well as the response. Shortcut for --print={0}.

    """
    .format(''.join(OUTPUT_OPTIONS))
)
output_options.add_argument(
    '--headers', '-h',
    dest='output_options',
    action='store_const',
    const=OUT_RESP_HEAD,
    help="""
    Print only the response headers. Shortcut for --print={0}.

    """
    .format(OUT_RESP_HEAD)
)
output_options.add_argument(
    '--body', '-b',
    dest='output_options',
    action='store_const',
    const=OUT_RESP_BODY,
    help="""
    Print only the response body. Shortcut for --print={0}.

    """
    .format(OUT_RESP_BODY)
)

output_options.add_argument(
    '--stream', '-S',
    action='store_true',
    default=False,
    help="""
    Always stream the output by line, i.e., behave like `tail -f'.

    Without --stream and with --pretty (either set or implied),
    HTTPie fetches the whole response before it outputs the processed data.

    Set this option when you want to continuously display a prettified
    long-lived response, such as one from the Twitter streaming API.

    It is useful also without --pretty: It ensures that the output is flushed
    more often and in smaller chunks.

    """
)
output_options.add_argument(
    '--output', '-o',
    type=FileType('a+b'),
    dest='output_file',
    metavar='FILE',
    help="""
    Save output to FILE. If --download is set, then only the response body is
    saved to the file. Other parts of the HTTP exchange are printed to stderr.

    """

)

output_options.add_argument(
    '--download', '-d',
    action='store_true',
    default=False,
    help="""
    Do not print the response body to stdout. Rather, download it and store it
    in a file. The filename is guessed unless specified with --output
    [filename]. This action is similar to the default behaviour of wget.

    """
)

output_options.add_argument(
    '--continue', '-c',
    dest='download_resume',
    action='store_true',
    default=False,
    help="""
    Resume an interrupted download. Note that the --output option needs to be
    specified as well.

    """
)


#######################################################################
# Sessions
#######################################################################

sessions = parser.add_argument_group(title='Sessions')\
                 .add_mutually_exclusive_group(required=False)

session_name_validator = SessionNameValidator(
    'Session name contains invalid characters.'
)

sessions.add_argument(
    '--session',
    metavar='SESSION_NAME_OR_PATH',
    type=session_name_validator,
    help="""
    Create, or reuse and update a session. Within a session, custom headers,
    auth credential, as well as any cookies sent by the server persist between
    requests.

    Session files are stored in:

        {session_dir}/<HOST>/<SESSION_NAME>.json.

    """
    .format(session_dir=DEFAULT_SESSIONS_DIR)
)
sessions.add_argument(
    '--session-read-only',
    metavar='SESSION_NAME_OR_PATH',
    type=session_name_validator,
    help="""
    Create or read a session without updating it form the request/response
    exchange.

    """
)


#######################################################################
# Authentication
#######################################################################

# ``requests.request`` keyword arguments.
auth = parser.add_argument_group(title='Authentication')
auth.add_argument(
    '--auth', '-a',
    metavar='USER[:PASS]',
    type=AuthCredentialsArgType(SEP_CREDENTIALS),
    help="""
    If only the username is provided (-a username), HTTPie will prompt
    for the password.

    """,
)

_auth_plugins = plugin_manager.get_auth_plugins()
auth.add_argument(
    '--auth-type',
    choices=[plugin.auth_type for plugin in _auth_plugins],
    default=_auth_plugins[0].auth_type,
    help="""
    The authentication mechanism to be used. Defaults to "{default}".

    {types}

    """
    .format(default=_auth_plugins[0].auth_type, types='\n    '.join(
        '"{type}": {name}{package}{description}'.format(
            type=plugin.auth_type,
            name=plugin.name,
            package=(
                '' if issubclass(plugin, BuiltinAuthPlugin)
                else ' (provided by %s)' % plugin.package_name
            ),
            description=(
                '' if not plugin.description else
                '\n      ' + ('\n      '.join(wrap(plugin.description)))
            )
        )
        for plugin in _auth_plugins
    )),
)


#######################################################################
# Network
#######################################################################

network = parser.add_argument_group(title='Network')

network.add_argument(
    '--proxy',
    default=[],
    action='append',
    metavar='PROTOCOL:PROXY_URL',
    type=KeyValueArgType(SEP_PROXY),
    help="""
    String mapping protocol to the URL of the proxy
    (e.g. http:http://foo.bar:3128). You can specify multiple proxies with
    different protocols.

    """
)
network.add_argument(
    '--follow',
    default=False,
    action='store_true',
    help="""
    Set this flag if full redirects are allowed (e.g. re-POST-ing of data at
    new Location).

    """
)
network.add_argument(
    '--verify',
    default='yes',
    help="""
    Set to "no" to skip checking the host's SSL certificate. You can also pass
    the path to a CA_BUNDLE file for private certs. You can also set the
    REQUESTS_CA_BUNDLE environment variable. Defaults to "yes".

    """
)

network.add_argument(
    '--cert',
    default=None,
    type=readable_file_arg,
    help="""
    You can specify a local cert to use as client side SSL certificate.
    This file may either contain both private key and certificate or you may
    specify --certkey separately.

    """
)

network.add_argument(
    '--certkey',
    default=None,
    type=readable_file_arg,
    help="""
    The private key to use with SSL. Only needed if --cert is given and the
    certificate file does not contain the private key.

    """
)

network.add_argument(
    '--timeout',
    type=float,
    default=30,
    metavar='SECONDS',
    help="""
    The connection timeout of the request in seconds. The default value is
    30 seconds.

    """
)
network.add_argument(
    '--check-status',
    default=False,
    action='store_true',
    help="""
    By default, HTTPie exits with 0 when no network or other fatal errors
    occur. This flag instructs HTTPie to also check the HTTP status code and
    exit with an error if the status indicates one.

    When the server replies with a 4xx (Client Error) or 5xx (Server Error)
    status code, HTTPie exits with 4 or 5 respectively. If the response is a
    3xx (Redirect) and --follow hasn't been set, then the exit status is 3.
    Also an error message is written to stderr if stdout is redirected.

    """
)


#######################################################################
# Troubleshooting
#######################################################################

troubleshooting = parser.add_argument_group(title='Troubleshooting')

troubleshooting.add_argument(
    '--ignore-stdin',
    action='store_true',
    default=False,
    help="""
    Do not attempt to read stdin.

    """
)
troubleshooting.add_argument(
    '--help',
    action='help',
    default=SUPPRESS,
    help="""
    Show this help message and exit.

    """
)
troubleshooting.add_argument(
    '--version',
    action='version',
    version=__version__,
    help="""
    Show version and exit.

    """
)
troubleshooting.add_argument(
    '--traceback',
    action='store_true',
    default=False,
    help="""
    Prints exception traceback should one occur.

    """
)
troubleshooting.add_argument(
    '--debug',
    action='store_true',
    default=False,
    help="""
    Prints exception traceback should one occur, and also other information
    that is useful for debugging HTTPie itself and for reporting bugs.

    """
)

########NEW FILE########
__FILENAME__ = client
import json
import sys
from pprint import pformat

import requests

from httpie import sessions
from httpie import __version__
from httpie.compat import str
from httpie.plugins import plugin_manager


FORM = 'application/x-www-form-urlencoded; charset=utf-8'
JSON = 'application/json; charset=utf-8'
DEFAULT_UA = 'HTTPie/%s' % __version__


def get_response(args, config_dir):
    """Send the request and return a `request.Response`."""

    if not args.session and not args.session_read_only:
        requests_kwargs = get_requests_kwargs(args)
        if args.debug:
            dump_request(requests_kwargs)
        response = requests.request(**requests_kwargs)
    else:
        response = sessions.get_response(
            args=args,
            config_dir=config_dir,
            session_name=args.session or args.session_read_only,
            read_only=bool(args.session_read_only),
        )

    return response


def dump_request(kwargs):
    sys.stderr.write('\n>>> requests.request(%s)\n\n'
                     % pformat(kwargs))


def encode_headers(headers):
    # This allows for unicode headers which is non-standard but practical.
    # See: https://github.com/jakubroztocil/httpie/issues/212
    return dict(
        (name, value.encode('utf8') if isinstance(value, str) else value)
        for name, value in headers.items()
    )


def get_default_headers(args):
    default_headers = {
        'User-Agent': DEFAULT_UA
    }

    auto_json = args.data and not args.form
    # FIXME: Accept is set to JSON with `http url @./file.txt`.
    if args.json or auto_json:
        default_headers['Accept'] = 'application/json'
        if args.json or (auto_json and args.data):
            default_headers['Content-Type'] = JSON

    elif args.form and not args.files:
        # If sending files, `requests` will set
        # the `Content-Type` for us.
        default_headers['Content-Type'] = FORM
    return default_headers


def get_requests_kwargs(args, base_headers=None):
    """
    Translate our `args` into `requests.request` keyword arguments.

    """
    # Serialize JSON data, if needed.
    data = args.data
    auto_json = data and not args.form
    if args.json or auto_json and isinstance(data, dict):
        if data:
            data = json.dumps(data)
        else:
            # We need to set data to an empty string to prevent requests
            # from assigning an empty list to `response.request.data`.
            data = ''

    # Finalize headers.
    headers = get_default_headers(args)
    if base_headers:
        headers.update(base_headers)
    headers.update(args.headers)
    headers = encode_headers(headers)

    credentials = None
    if args.auth:
        auth_plugin = plugin_manager.get_auth_plugin(args.auth_type)()
        credentials = auth_plugin.get_auth(args.auth.key, args.auth.value)

    cert = None
    if args.cert:
        cert = args.cert
        if args.certkey:
            cert = cert, args.certkey

    kwargs = {
        'stream': True,
        'method': args.method.lower(),
        'url': args.url,
        'headers': headers,
        'data': data,
        'verify': {
            'yes': True,
            'no': False
        }.get(args.verify, args.verify),
        'cert': cert,
        'timeout': args.timeout,
        'auth': credentials,
        'proxies': dict((p.key, p.value) for p in args.proxy),
        'files': args.files,
        'allow_redirects': args.follow,
        'params': args.params,
    }

    return kwargs

########NEW FILE########
__FILENAME__ = compat
"""
Python 2.6, 2.7, and 3.x compatibility.

"""
# Borrow these from requests:
#noinspection PyUnresolvedReferences
from requests.compat import is_windows, bytes, str, is_py3, is_py26

try:
    #noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.parse import urlsplit
except ImportError:
    #noinspection PyUnresolvedReferences,PyCompatibility
    from urlparse import urlsplit

try:
    #noinspection PyCompatibility
    from urllib.request import urlopen
except ImportError:
    #noinspection PyCompatibility
    from urllib2 import urlopen

try:
    from collections import OrderedDict
except ImportError:
    ### Python 2.6 OrderedDict class, needed for headers, parameters, etc .###
    ### <https://pypi.python.org/pypi/ordereddict/1.1>
    # noinspection PyCompatibility
    from UserDict import DictMixin

    # noinspection PyShadowingBuiltins
    class OrderedDict(dict, DictMixin):
        # Copyright (c) 2009 Raymond Hettinger
        #
        # Permission is hereby granted, free of charge, to any person
        # obtaining a copy of this software and associated documentation files
        # (the "Software"), to deal in the Software without restriction,
        # including without limitation the rights to use, copy, modify, merge,
        # publish, distribute, sublicense, and/or sell copies of the Software,
        # and to permit persons to whom the Software is furnished to do so,
        # subject to the following conditions:
        #
        #     The above copyright notice and this permission notice shall be
        #     included in all copies or substantial portions of the Software.
        #
        #     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
        #     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
        #     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
        #     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
        #     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
        #     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
        #     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
        #     OTHER DEALINGS IN THE SOFTWARE.
        # noinspection PyMissingConstructor
        def __init__(self, *args, **kwds):
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d'
                                % len(args))
            try:
                self.__end
            except AttributeError:
                self.clear()
            self.update(*args, **kwds)

        def clear(self):
            self.__end = end = []
            # noinspection PyUnusedLocal
            end += [None, end, end]     # sentinel node for doubly linked list
            self.__map = {}             # key --> [key, prev, next]
            dict.clear(self)

        def __setitem__(self, key, value):
            if key not in self:
                end = self.__end
                curr = end[1]
                curr[2] = end[1] = self.__map[key] = [key, curr, end]
            dict.__setitem__(self, key, value)

        def __delitem__(self, key):
            dict.__delitem__(self, key)
            key, prev, next = self.__map.pop(key)
            prev[2] = next
            next[1] = prev

        def __iter__(self):
            end = self.__end
            curr = end[2]
            while curr is not end:
                yield curr[0]
                curr = curr[2]

        def __reversed__(self):
            end = self.__end
            curr = end[1]
            while curr is not end:
                yield curr[0]
                curr = curr[1]

        def popitem(self, last=True):
            if not self:
                raise KeyError('dictionary is empty')
            if last:
                key = reversed(self).next()
            else:
                key = iter(self).next()
            value = self.pop(key)
            return key, value

        def __reduce__(self):
            items = [[k, self[k]] for k in self]
            tmp = self.__map, self.__end
            del self.__map, self.__end
            inst_dict = vars(self).copy()
            self.__map, self.__end = tmp
            if inst_dict:
                return self.__class__, (items,), inst_dict
            return self.__class__, (items,)

        def keys(self):
            return list(self)

        setdefault = DictMixin.setdefault
        update = DictMixin.update
        pop = DictMixin.pop
        values = DictMixin.values
        items = DictMixin.items
        iterkeys = DictMixin.iterkeys
        itervalues = DictMixin.itervalues
        iteritems = DictMixin.iteritems

        def __repr__(self):
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())

        def copy(self):
            return self.__class__(self)

        # noinspection PyMethodOverriding
        @classmethod
        def fromkeys(cls, iterable, value=None):
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            if isinstance(other, OrderedDict):
                if len(self) != len(other):
                    return False
                for p, q in zip(self.items(), other.items()):
                    if p != q:
                        return False
                return True
            return dict.__eq__(self, other)

        def __ne__(self, other):
            return not self == other

########NEW FILE########
__FILENAME__ = config
import os
import json
import errno

from httpie import __version__
from httpie.compat import is_windows


DEFAULT_CONFIG_DIR = os.environ.get(
    'HTTPIE_CONFIG_DIR',
    os.path.expanduser('~/.httpie') if not is_windows else
    os.path.expandvars(r'%APPDATA%\\httpie')
)


class BaseConfigDict(dict):

    name = None
    helpurl = None
    about = None

    def __getattr__(self, item):
        return self[item]

    def _get_path(self):
        """Return the config file path without side-effects."""
        raise NotImplementedError()

    @property
    def path(self):
        """Return the config file path creating basedir, if needed."""
        path = self._get_path()
        try:
            os.makedirs(os.path.dirname(path), mode=0o700)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        return path

    def is_new(self):
        return not os.path.exists(self._get_path())

    def load(self):
        try:
            with open(self.path, 'rt') as f:
                try:
                    data = json.load(f)
                except ValueError as e:
                    raise ValueError(
                        'Invalid %s JSON: %s [%s]' %
                        (type(self).__name__, e.message, self.path)
                    )
                self.update(data)
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise

    def save(self):
        self['__meta__'] = {
            'httpie': __version__
        }
        if self.helpurl:
            self['__meta__']['help'] = self.helpurl

        if self.about:
            self['__meta__']['about'] = self.about

        with open(self.path, 'w') as f:
            json.dump(self, f, indent=4, sort_keys=True, ensure_ascii=True)
            f.write('\n')

    def delete(self):
        try:
            os.unlink(self.path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise


class Config(BaseConfigDict):

    name = 'config'
    helpurl = 'https://github.com/jakubroztocil/httpie#config'
    about = 'HTTPie configuration file'

    DEFAULTS = {
        'implicit_content_type': 'json',
        'default_options': []
    }

    def __init__(self, directory=DEFAULT_CONFIG_DIR):
        super(Config, self).__init__()
        self.update(self.DEFAULTS)
        self.directory = directory

    def _get_path(self):
        return os.path.join(self.directory, self.name + '.json')

########NEW FILE########
__FILENAME__ = context
import os
import sys

from requests.compat import is_windows

from httpie.config import DEFAULT_CONFIG_DIR, Config


class Environment(object):
    """
    Information about the execution context
    (standard streams, config directory, etc).

    By default, it represents the actual environment.
    All of the attributes can be overwritten though, which
    is used by the test suite to simulate various scenarios.

    """
    is_windows = is_windows
    config_dir = DEFAULT_CONFIG_DIR
    colors = 256 if '256color' in os.environ.get('TERM', '') else 88
    stdin = sys.stdin
    stdin_isatty = stdin.isatty()
    stdin_encoding = None
    stdout = sys.stdout
    stdout_isatty = stdout.isatty()
    stdout_encoding = None
    stderr = sys.stderr
    stderr_isatty = stderr.isatty()
    if is_windows:
        # noinspection PyUnresolvedReferences
        from colorama.initialise import wrap_stream
        stdout = wrap_stream(stdout, convert=None, strip=None,
                             autoreset=True, wrap=True)
        stderr = wrap_stream(stderr, convert=None, strip=None,
                             autoreset=True, wrap=True)

    def __init__(self, **kwargs):
        """
        Use keyword arguments to overwrite
        any of the class attributes for this instance.

        """
        assert all(hasattr(type(self), attr) for attr in kwargs.keys())
        self.__dict__.update(**kwargs)

        # Keyword arguments > stream.encoding > default utf8
        if self.stdin_encoding is None:
            self.stdin_encoding = getattr(
                self.stdin, 'encoding', None) or 'utf8'
        if self.stdout_encoding is None:
            actual_stdout = self.stdout
            if is_windows:
                from colorama import AnsiToWin32
                if isinstance(self.stdout, AnsiToWin32):
                    actual_stdout = self.stdout.wrapped
            self.stdout_encoding = getattr(
                actual_stdout, 'encoding', None) or 'utf8'

    @property
    def config(self):
        if not hasattr(self, '_config'):
            self._config = Config(directory=self.config_dir)
            if self._config.is_new():
                self._config.save()
            else:
                self._config.load()
        return self._config

########NEW FILE########
__FILENAME__ = core
"""This module provides the main functionality of HTTPie.

Invocation flow:

  1. Read, validate and process the input (args, `stdin`).
  2. Create and send a request.
  3. Stream, and possibly process and format, the parts
     of the request-response exchange selected by output options.
  4. Simultaneously write to `stdout`
  5. Exit.

"""
import sys
import errno

import requests
from requests import __version__ as requests_version
from pygments import __version__ as pygments_version

from httpie import __version__ as httpie_version, ExitStatus
from httpie.compat import str, bytes, is_py3
from httpie.client import get_response
from httpie.downloads import Download
from httpie.context import Environment
from httpie.plugins import plugin_manager
from httpie.output.streams import (
    build_output_stream,
    write, write_with_colors_win_py3
)


def get_exit_status(http_status, follow=False):
    """Translate HTTP status code to exit status code."""
    if 300 <= http_status <= 399 and not follow:
        # Redirect
        return ExitStatus.ERROR_HTTP_3XX
    elif 400 <= http_status <= 499:
        # Client Error
        return ExitStatus.ERROR_HTTP_4XX
    elif 500 <= http_status <= 599:
        # Server Error
        return ExitStatus.ERROR_HTTP_5XX
    else:
        return ExitStatus.OK


def print_debug_info(env):
    env.stderr.writelines([
        'HTTPie %s\n' % httpie_version,
        'HTTPie data: %s\n' % env.config.directory,
        'Requests %s\n' % requests_version,
        'Pygments %s\n' % pygments_version,
        'Python %s %s\n' % (sys.version, sys.platform)
    ])


def decode_args(args, stdin_encoding):
    """
    Convert all bytes ags to str
    by decoding them using stdin encoding.

    """
    return [
        arg.decode(stdin_encoding) if type(arg) == bytes else arg
        for arg in args
    ]


def main(args=sys.argv[1:], env=Environment()):
    """Run the main program and write the output to ``env.stdout``.

    Return exit status code.

    """
    from httpie.cli import parser

    plugin_manager.load_installed_plugins()

    if env.config.default_options:
        args = env.config.default_options + args

    def error(msg, *args, **kwargs):
        msg = msg % args
        level = kwargs.get('level', 'error')
        env.stderr.write('\nhttp: %s: %s\n' % (level, msg))

    debug = '--debug' in args
    traceback = debug or '--traceback' in args
    exit_status = ExitStatus.OK

    if debug:
        print_debug_info(env)
        if args == ['--debug']:
            return exit_status

    download = None

    try:
        args = parser.parse_args(args=args, env=env)

        if args.download:
            args.follow = True  # --download implies --follow.
            download = Download(
                output_file=args.output_file,
                progress_file=env.stderr,
                resume=args.download_resume
            )
            download.pre_request(args.headers)

        response = get_response(args, config_dir=env.config.directory)

        if args.check_status or download:

            exit_status = get_exit_status(
                http_status=response.status_code,
                follow=args.follow
            )

            if not env.stdout_isatty and exit_status != ExitStatus.OK:
                error('HTTP %s %s',
                      response.raw.status,
                      response.raw.reason,
                      level='warning')

        write_kwargs = {
            'stream': build_output_stream(
                args, env, response.request, response),

            # This will in fact be `stderr` with `--download`
            'outfile': env.stdout,

            'flush': env.stdout_isatty or args.stream
        }

        try:

            if env.is_windows and is_py3 and 'colors' in args.prettify:
                write_with_colors_win_py3(**write_kwargs)
            else:
                write(**write_kwargs)

            if download and exit_status == ExitStatus.OK:
                # Response body download.
                download_stream, download_to = download.start(response)
                write(
                    stream=download_stream,
                    outfile=download_to,
                    flush=False,
                )
                download.finish()
                if download.interrupted:
                    exit_status = ExitStatus.ERROR
                    error('Incomplete download: size=%d; downloaded=%d' % (
                        download.status.total_size,
                        download.status.downloaded
                    ))

        except IOError as e:
            if not traceback and e.errno == errno.EPIPE:
                # Ignore broken pipes unless --traceback.
                env.stderr.write('\n')
            else:
                raise
    except (KeyboardInterrupt, SystemExit):
        if traceback:
            raise
        env.stderr.write('\n')
        exit_status = ExitStatus.ERROR

    except requests.Timeout:
        exit_status = ExitStatus.ERROR_TIMEOUT
        error('Request timed out (%ss).', args.timeout)

    except Exception as e:
        # TODO: Better distinction between expected and unexpected errors.
        #       Network errors vs. bugs, etc.
        if traceback:
            raise
        error('%s: %s', type(e).__name__, str(e))
        exit_status = ExitStatus.ERROR

    finally:
        if download and not download.finished:
            download.failed()

    return exit_status

########NEW FILE########
__FILENAME__ = downloads
# coding=utf-8
"""
Download mode implementation.

"""
from __future__ import division
import os
import re
import sys
import mimetypes
import threading
from time import sleep, time
from mailbox import Message

from httpie.output.streams import RawStream
from httpie.models import HTTPResponse
from httpie.utils import humanize_bytes
from httpie.compat import urlsplit


PARTIAL_CONTENT = 206


CLEAR_LINE = '\r\033[K'
PROGRESS = (
    '{percentage: 6.2f} %'
    ' {downloaded: >10}'
    ' {speed: >10}/s'
    ' {eta: >8} ETA'
)
PROGRESS_NO_CONTENT_LENGTH = '{downloaded: >10} {speed: >10}/s'
SUMMARY = 'Done. {downloaded} in {time:0.5f}s ({speed}/s)\n'
SPINNER = '|/-\\'


class ContentRangeError(ValueError):
    pass


def parse_content_range(content_range, resumed_from):
    """
    Parse and validate Content-Range header.

    <http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html>

    :param content_range: the value of a Content-Range response header
                          eg. "bytes 21010-47021/47022"
    :param resumed_from: first byte pos. from the Range request header
    :return: total size of the response body when fully downloaded.

    """
    if content_range is None:
        raise ContentRangeError('Missing Content-Range')

    pattern = (
        '^bytes (?P<first_byte_pos>\d+)-(?P<last_byte_pos>\d+)'
        '/(\*|(?P<instance_length>\d+))$'
    )
    match = re.match(pattern, content_range)

    if not match:
        raise ContentRangeError(
            'Invalid Content-Range format %r' % content_range)

    content_range_dict = match.groupdict()
    first_byte_pos = int(content_range_dict['first_byte_pos'])
    last_byte_pos = int(content_range_dict['last_byte_pos'])
    instance_length = (
        int(content_range_dict['instance_length'])
        if content_range_dict['instance_length']
        else None
    )

    # "A byte-content-range-spec with a byte-range-resp-spec whose
    # last- byte-pos value is less than its first-byte-pos value,
    # or whose instance-length value is less than or equal to its
    # last-byte-pos value, is invalid. The recipient of an invalid
    # byte-content-range- spec MUST ignore it and any content
    # transferred along with it."
    if (first_byte_pos >= last_byte_pos
            or (instance_length is not None
                and instance_length <= last_byte_pos)):
        raise ContentRangeError(
            'Invalid Content-Range returned: %r' % content_range)

    if (first_byte_pos != resumed_from
        or (instance_length is not None
            and last_byte_pos + 1 != instance_length)):
        # Not what we asked for.
        raise ContentRangeError(
            'Unexpected Content-Range returned (%r)'
            ' for the requested Range ("bytes=%d-")'
            % (content_range, resumed_from)
        )

    return last_byte_pos + 1


def filename_from_content_disposition(content_disposition):
    """
    Extract and validate filename from a Content-Disposition header.

    :param content_disposition: Content-Disposition value
    :return: the filename if present and valid, otherwise `None`

    """
    # attachment; filename=jakubroztocil-httpie-0.4.1-20-g40bd8f6.tar.gz

    msg = Message('Content-Disposition: %s' % content_disposition)
    filename = msg.get_filename()
    if filename:
        # Basic sanitation.
        filename = os.path.basename(filename).lstrip('.').strip()
        if filename:
            return filename


def filename_from_url(url, content_type):
    fn = urlsplit(url).path.rstrip('/')
    fn = os.path.basename(fn) if fn else 'index'
    if '.' not in fn and content_type:
        content_type = content_type.split(';')[0]
        if content_type == 'text/plain':
            # mimetypes returns '.ksh'
            ext = '.txt'
        else:
            ext = mimetypes.guess_extension(content_type)

        if ext == '.htm':  # Python 3
            ext = '.html'

        if ext:
            fn += ext

    return fn


def get_unique_filename(fn, exists=os.path.exists):
    attempt = 0
    while True:
        suffix = '-' + str(attempt) if attempt > 0 else ''
        if not exists(fn + suffix):
            return fn + suffix
        attempt += 1


class Download(object):

    def __init__(self, output_file=None,
                 resume=False, progress_file=sys.stderr):
        """
        :param resume: Should the download resume if partial download
                       already exists.
        :type resume: bool

        :param output_file: The file to store response body in. If not
                            provided, it will be guessed from the response.

        :param progress_file: Where to report download progress.

        """
        self._output_file = output_file
        self._resume = resume
        self._resumed_from = 0
        self.finished = False

        self.status = Status()
        self._progress_reporter = ProgressReporterThread(
            status=self.status,
            output=progress_file
        )

    def pre_request(self, request_headers):
        """Called just before the HTTP request is sent.

        Might alter `request_headers`.

        :type request_headers: dict

        """
        # Disable content encoding so that we can resume, etc.
        request_headers['Accept-Encoding'] = None
        if self._resume:
            bytes_have = os.path.getsize(self._output_file.name)
            if bytes_have:
                # Set ``Range`` header to resume the download
                # TODO: Use "If-Range: mtime" to make sure it's fresh?
                request_headers['Range'] = 'bytes=%d-' % bytes_have
                self._resumed_from = bytes_have

    def start(self, response):
        """
        Initiate and return a stream for `response` body  with progress
        callback attached. Can be called only once.

        :param response: Initiated response object with headers already fetched
        :type response: requests.models.Response

        :return: RawStream, output_file

        """
        assert not self.status.time_started

        try:
            total_size = int(response.headers['Content-Length'])
        except (KeyError, ValueError, TypeError):
            total_size = None

        if self._output_file:
            if self._resume and response.status_code == PARTIAL_CONTENT:
                total_size = parse_content_range(
                    response.headers.get('Content-Range'),
                    self._resumed_from
                )

            else:
                self._resumed_from = 0
                try:
                    self._output_file.seek(0)
                    self._output_file.truncate()
                except IOError:
                    pass  # stdout
        else:
            # TODO: Should the filename be taken from response.history[0].url?
            # Output file not specified. Pick a name that doesn't exist yet.
            fn = None
            if 'Content-Disposition' in response.headers:
                fn = filename_from_content_disposition(
                    response.headers['Content-Disposition'])
            if not fn:
                fn = filename_from_url(
                    url=response.url,
                    content_type=response.headers.get('Content-Type'),
                )
            self._output_file = open(get_unique_filename(fn), mode='a+b')

        self.status.started(
            resumed_from=self._resumed_from,
            total_size=total_size
        )

        stream = RawStream(
            msg=HTTPResponse(response),
            with_headers=False,
            with_body=True,
            on_body_chunk_downloaded=self.chunk_downloaded,
            chunk_size=1024 * 8
        )

        self._progress_reporter.output.write(
            'Downloading %sto "%s"\n' % (
                (humanize_bytes(total_size) + ' '
                 if total_size is not None
                 else ''),
                self._output_file.name
            )
        )
        self._progress_reporter.start()

        return stream, self._output_file

    def finish(self):
        assert not self.finished
        self.finished = True
        self.status.finished()

    def failed(self):
        self._progress_reporter.stop()

    @property
    def interrupted(self):
        return (
            self.finished
            and self.status.total_size
            and self.status.total_size != self.status.downloaded
        )

    def chunk_downloaded(self, chunk):
        """
        A download progress callback.

        :param chunk: A chunk of response body data that has just
                      been downloaded and written to the output.
        :type chunk: bytes

        """
        self.status.chunk_downloaded(len(chunk))


class Status(object):
    """Holds details about the downland status."""

    def __init__(self):
        self.downloaded = 0
        self.total_size = None
        self.resumed_from = 0
        self.time_started = None
        self.time_finished = None

    def started(self, resumed_from=0, total_size=None):
        assert self.time_started is None
        if total_size is not None:
            self.total_size = total_size
        self.downloaded = self.resumed_from = resumed_from
        self.time_started = time()

    def chunk_downloaded(self, size):
        assert self.time_finished is None
        self.downloaded += size

    @property
    def has_finished(self):
        return self.time_finished is not None

    def finished(self):
        assert self.time_started is not None
        assert self.time_finished is None
        self.time_finished = time()


class ProgressReporterThread(threading.Thread):
    """
    Reports download progress based on its status.

    Uses threading to periodically update the status (speed, ETA, etc.).

    """
    def __init__(self, status, output, tick=.1, update_interval=1):
        """

        :type status: Status
        :type output: file
        """
        super(ProgressReporterThread, self).__init__()
        self.status = status
        self.output = output
        self._tick = tick
        self._update_interval = update_interval
        self._spinner_pos = 0
        self._status_line = ''
        self._prev_bytes = 0
        self._prev_time = time()
        self._should_stop = threading.Event()

    def stop(self):
        """Stop reporting on next tick."""
        self._should_stop.set()

    def run(self):
        while not self._should_stop.is_set():
            if self.status.has_finished:
                self.sum_up()
                break

            self.report_speed()
            sleep(self._tick)

    def report_speed(self):

        now = time()

        if now - self._prev_time >= self._update_interval:
            downloaded = self.status.downloaded
            try:
                speed = ((downloaded - self._prev_bytes)
                         / (now - self._prev_time))
            except ZeroDivisionError:
                speed = 0

            if not self.status.total_size:
                self._status_line = PROGRESS_NO_CONTENT_LENGTH.format(
                    downloaded=humanize_bytes(downloaded),
                    speed=humanize_bytes(speed),
                )
            else:
                try:
                    percentage = downloaded / self.status.total_size * 100
                except ZeroDivisionError:
                    percentage = 0

                if not speed:
                    eta = '-:--:--'
                else:
                    s = int((self.status.total_size - downloaded) / speed)
                    h, s = divmod(s, 60 * 60)
                    m, s = divmod(s, 60)
                    eta = '{0}:{1:0>2}:{2:0>2}'.format(h, m, s)

                self._status_line = PROGRESS.format(
                    percentage=percentage,
                    downloaded=humanize_bytes(downloaded),
                    speed=humanize_bytes(speed),
                    eta=eta,
                )

            self._prev_time = now
            self._prev_bytes = downloaded

        self.output.write(
            CLEAR_LINE
            + ' '
            + SPINNER[self._spinner_pos]
            + ' '
            + self._status_line
        )
        self.output.flush()

        self._spinner_pos = (self._spinner_pos + 1
                             if self._spinner_pos + 1 != len(SPINNER)
                             else 0)

    def sum_up(self):
        actually_downloaded = (self.status.downloaded
                               - self.status.resumed_from)
        time_taken = self.status.time_finished - self.status.time_started

        self.output.write(CLEAR_LINE)

        try:
            speed = actually_downloaded / time_taken
        except ZeroDivisionError:
            # Either time is 0 (not all systems provide `time.time`
            # with a better precision than 1 second), and/or nothing
            # has been downloaded.
            speed = actually_downloaded

        self.output.write(SUMMARY.format(
            downloaded=humanize_bytes(actually_downloaded),
            total=(self.status.total_size
                   and humanize_bytes(self.status.total_size)),
            speed=humanize_bytes(speed),
            time=time_taken,
        ))
        self.output.flush()

########NEW FILE########
__FILENAME__ = input
"""Parsing and processing of CLI input (args, auth credentials, files, stdin).

"""
import os
import sys
import re
import json
import mimetypes
import getpass
from io import BytesIO
#noinspection PyCompatibility
from argparse import ArgumentParser, ArgumentTypeError, ArgumentError

# TODO: Use MultiDict for headers once added to `requests`.
# https://github.com/jakubroztocil/httpie/issues/130
from requests.structures import CaseInsensitiveDict

from httpie.compat import OrderedDict, urlsplit, str
from httpie.sessions import VALID_SESSION_NAME_PATTERN


HTTP_POST = 'POST'
HTTP_GET = 'GET'
HTTP = 'http://'
HTTPS = 'https://'


# Various separators used in args
SEP_HEADERS = ':'
SEP_CREDENTIALS = ':'
SEP_PROXY = ':'
SEP_DATA = '='
SEP_DATA_RAW_JSON = ':='
SEP_FILES = '@'
SEP_DATA_EMBED_FILE = '=@'
SEP_DATA_EMBED_RAW_JSON_FILE = ':=@'
SEP_QUERY = '=='

# Separators that become request data
SEP_GROUP_DATA_ITEMS = frozenset([
    SEP_DATA,
    SEP_DATA_RAW_JSON,
    SEP_FILES,
    SEP_DATA_EMBED_FILE,
    SEP_DATA_EMBED_RAW_JSON_FILE
])

# Separators for items whose value is a filename to be embedded
SEP_GROUP_DATA_EMBED_ITEMS = frozenset([
    SEP_DATA_EMBED_FILE,
    SEP_DATA_EMBED_RAW_JSON_FILE,
])

# Separators for raw JSON items
SEP_GROUP_RAW_JSON_ITEMS = frozenset([
    SEP_DATA_RAW_JSON,
    SEP_DATA_EMBED_RAW_JSON_FILE,
])

# Separators allowed in ITEM arguments
SEP_GROUP_ALL_ITEMS = frozenset([
    SEP_HEADERS,
    SEP_QUERY,
    SEP_DATA,
    SEP_DATA_RAW_JSON,
    SEP_FILES,
    SEP_DATA_EMBED_FILE,
    SEP_DATA_EMBED_RAW_JSON_FILE,
])


# Output options
OUT_REQ_HEAD = 'H'
OUT_REQ_BODY = 'B'
OUT_RESP_HEAD = 'h'
OUT_RESP_BODY = 'b'

OUTPUT_OPTIONS = frozenset([
    OUT_REQ_HEAD,
    OUT_REQ_BODY,
    OUT_RESP_HEAD,
    OUT_RESP_BODY
])

# Pretty
PRETTY_MAP = {
    'all': ['format', 'colors'],
    'colors': ['colors'],
    'format': ['format'],
    'none': []
}
PRETTY_STDOUT_TTY_ONLY = object()


# Defaults
OUTPUT_OPTIONS_DEFAULT = OUT_RESP_HEAD + OUT_RESP_BODY
OUTPUT_OPTIONS_DEFAULT_STDOUT_REDIRECTED = OUT_RESP_BODY


class Parser(ArgumentParser):
    """Adds additional logic to `argparse.ArgumentParser`.

    Handles all input (CLI args, file args, stdin), applies defaults,
    and performs extra validation.

    """

    def __init__(self, *args, **kwargs):
        kwargs['add_help'] = False
        super(Parser, self).__init__(*args, **kwargs)

    #noinspection PyMethodOverriding
    def parse_args(self, env, args=None, namespace=None):

        self.env = env
        self.args, no_options = super(Parser, self)\
            .parse_known_args(args, namespace)

        if self.args.debug:
            self.args.traceback = True

        # Arguments processing and environment setup.
        self._apply_no_options(no_options)
        self._apply_config()
        self._validate_download_options()
        self._setup_standard_streams()
        self._process_output_options()
        self._process_pretty_options()
        self._guess_method()
        self._parse_items()
        if not self.args.ignore_stdin and not env.stdin_isatty:
            self._body_from_file(self.env.stdin)
        if not (self.args.url.startswith((HTTP, HTTPS))):
            scheme = HTTP

            # See if we're using curl style shorthand for localhost (:3000/foo)
            shorthand = re.match(r'^:(?!:)(\d*)(/?.*)$', self.args.url)
            if shorthand:
                port = shorthand.group(1)
                rest = shorthand.group(2)
                self.args.url = scheme + 'localhost'
                if port:
                    self.args.url += ':' + port
                self.args.url += rest
            else:
                self.args.url = scheme + self.args.url
        self._process_auth()

        return self.args

    # noinspection PyShadowingBuiltins
    def _print_message(self, message, file=None):
        # Sneak in our stderr/stdout.
        file = {
            sys.stdout: self.env.stdout,
            sys.stderr: self.env.stderr,
            None: self.env.stderr
        }.get(file, file)
        if not hasattr(file, 'buffer') and isinstance(message, str):
            message = message.encode(self.env.stdout_encoding)
        super(Parser, self)._print_message(message, file)

    def _setup_standard_streams(self):
        """
        Modify `env.stdout` and `env.stdout_isatty` based on args, if needed.

        """
        if not self.env.stdout_isatty and self.args.output_file:
            self.error('Cannot use --output, -o with redirected output.')

        if self.args.download:
            # FIXME: Come up with a cleaner solution.
            if not self.env.stdout_isatty:
                # Use stdout as the download output file.
                self.args.output_file = self.env.stdout
            # With `--download`, we write everything that would normally go to
            # `stdout` to `stderr` instead. Let's replace the stream so that
            # we don't have to use many `if`s throughout the codebase.
            # The response body will be treated separately.
            self.env.stdout = self.env.stderr
            self.env.stdout_isatty = self.env.stderr_isatty
        elif self.args.output_file:
            # When not `--download`ing, then `--output` simply replaces
            # `stdout`. The file is opened for appending, which isn't what
            # we want in this case.
            self.args.output_file.seek(0)
            self.args.output_file.truncate()
            self.env.stdout = self.args.output_file
            self.env.stdout_isatty = False

    def _apply_config(self):
        if (not self.args.json
                and self.env.config.implicit_content_type == 'form'):
            self.args.form = True

    def _process_auth(self):
        """
        If only a username provided via --auth, then ask for a password.
        Or, take credentials from the URL, if provided.

        """
        url = urlsplit(self.args.url)

        if self.args.auth:
            if not self.args.auth.has_password():
                # Stdin already read (if not a tty) so it's save to prompt.
                if self.args.ignore_stdin:
                    self.error('Unable to prompt for passwords because'
                               ' --ignore-stdin is set.')
                self.args.auth.prompt_password(url.netloc)

        elif url.username is not None:
            # Handle http://username:password@hostname/
            username, password = url.username, url.password
            self.args.auth = AuthCredentials(
                key=username,
                value=password,
                sep=SEP_CREDENTIALS,
                orig=SEP_CREDENTIALS.join([username, password])
            )

    def _apply_no_options(self, no_options):
        """For every `--no-OPTION` in `no_options`, set `args.OPTION` to
        its default value. This allows for un-setting of options, e.g.,
        specified in config.

        """
        invalid = []

        for option in no_options:
            if not option.startswith('--no-'):
                invalid.append(option)
                continue

            # --no-option => --option
            inverted = '--' + option[5:]
            for action in self._actions:
                if inverted in action.option_strings:
                    setattr(self.args, action.dest, action.default)
                    break
            else:
                invalid.append(option)

        if invalid:
            msg = 'unrecognized arguments: %s'
            self.error(msg % ' '.join(invalid))

    def _body_from_file(self, fd):
        """There can only be one source of request data.

        Bytes are always read.

        """
        if self.args.data:
            self.error('Request body (from stdin or a file) and request '
                       'data (key=value) cannot be mixed.')
        self.args.data = getattr(fd, 'buffer', fd).read()

    def _guess_method(self):
        """Set `args.method` if not specified to either POST or GET
        based on whether the request has data or not.

        """
        if self.args.method is None:
            # Invoked as `http URL'.
            assert not self.args.items
            if not self.args.ignore_stdin and not self.env.stdin_isatty:
                self.args.method = HTTP_POST
            else:
                self.args.method = HTTP_GET

        # FIXME: False positive, e.g., "localhost" matches but is a valid URL.
        elif not re.match('^[a-zA-Z]+$', self.args.method):
            # Invoked as `http URL item+'. The URL is now in `args.method`
            # and the first ITEM is now incorrectly in `args.url`.
            try:
                # Parse the URL as an ITEM and store it as the first ITEM arg.
                self.args.items.insert(0, KeyValueArgType(
                    *SEP_GROUP_ALL_ITEMS).__call__(self.args.url))

            except ArgumentTypeError as e:
                if self.args.traceback:
                    raise
                self.error(e.args[0])

            else:
                # Set the URL correctly
                self.args.url = self.args.method
                # Infer the method
                has_data = (
                    (not self.args.ignore_stdin and not self.env.stdin_isatty)
                     or any(item.sep in SEP_GROUP_DATA_ITEMS
                            for item in self.args.items)
                )
                self.args.method = HTTP_POST if has_data else HTTP_GET

    def _parse_items(self):
        """Parse `args.items` into `args.headers`, `args.data`, `args.params`,
         and `args.files`.

        """
        self.args.headers = CaseInsensitiveDict()
        self.args.data = ParamDict() if self.args.form else OrderedDict()
        self.args.files = OrderedDict()
        self.args.params = ParamDict()

        try:
            parse_items(items=self.args.items,
                        headers=self.args.headers,
                        data=self.args.data,
                        files=self.args.files,
                        params=self.args.params)
        except ParseError as e:
            if self.args.traceback:
                raise
            self.error(e.args[0])

        if self.args.files and not self.args.form:
            # `http url @/path/to/file`
            file_fields = list(self.args.files.keys())
            if file_fields != ['']:
                self.error(
                    'Invalid file fields (perhaps you meant --form?): %s'
                    % ','.join(file_fields))

            fn, fd = self.args.files['']
            self.args.files = {}

            self._body_from_file(fd)

            if 'Content-Type' not in self.args.headers:
                mime, encoding = mimetypes.guess_type(fn, strict=False)
                if mime:
                    content_type = mime
                    if encoding:
                        content_type = '%s; charset=%s' % (mime, encoding)
                    self.args.headers['Content-Type'] = content_type

    def _process_output_options(self):
        """Apply defaults to output options, or validate the provided ones.

        The default output options are stdout-type-sensitive.

        """
        if not self.args.output_options:
            self.args.output_options = (
                OUTPUT_OPTIONS_DEFAULT
                if self.env.stdout_isatty
                else OUTPUT_OPTIONS_DEFAULT_STDOUT_REDIRECTED
            )

        unknown_output_options = set(self.args.output_options) - OUTPUT_OPTIONS
        if unknown_output_options:
            self.error(
                'Unknown output options: %s' % ','.join(unknown_output_options)
            )

        if self.args.download and OUT_RESP_BODY in self.args.output_options:
            # Response body is always downloaded with --download and it goes
            # through a different routine, so we remove it.
            self.args.output_options = str(
                set(self.args.output_options) - set(OUT_RESP_BODY))

    def _process_pretty_options(self):
        if self.args.prettify == PRETTY_STDOUT_TTY_ONLY:
            self.args.prettify = PRETTY_MAP[
                'all' if self.env.stdout_isatty else 'none']
        elif self.args.prettify and self.env.is_windows:
            self.error('Only terminal output can be colorized on Windows.')
        else:
            # noinspection PyTypeChecker
            self.args.prettify = PRETTY_MAP[self.args.prettify]

    def _validate_download_options(self):
        if not self.args.download:
            if self.args.download_resume:
                self.error('--continue only works with --download')
        if self.args.download_resume and not (
                self.args.download and self.args.output_file):
            self.error('--continue requires --output to be specified')


class ParseError(Exception):
    pass


class KeyValue(object):
    """Base key-value pair parsed from CLI."""

    def __init__(self, key, value, sep, orig):
        self.key = key
        self.value = value
        self.sep = sep
        self.orig = orig

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class SessionNameValidator(object):

    def __init__(self, error_message):
        self.error_message = error_message

    def __call__(self, value):
        # Session name can be a path or just a name.
        if (os.path.sep not in value
                and not VALID_SESSION_NAME_PATTERN.search(value)):
            raise ArgumentError(None, self.error_message)
        return value


class KeyValueArgType(object):
    """A key-value pair argument type used with `argparse`.

    Parses a key-value arg and constructs a `KeyValue` instance.
    Used for headers, form data, and other key-value pair types.

    """

    key_value_class = KeyValue

    def __init__(self, *separators):
        self.separators = separators

    def __call__(self, string):
        """Parse `string` and return `self.key_value_class()` instance.

        The best of `self.separators` is determined (first found, longest).
        Back slash escaped characters aren't considered as separators
        (or parts thereof). Literal back slash characters have to be escaped
        as well (r'\\').

        """

        class Escaped(str):
            """Represents an escaped character."""

        def tokenize(s):
            """Tokenize `s`. There are only two token types - strings
            and escaped characters:

            tokenize(r'foo\=bar\\baz')
            => ['foo', Escaped('='), 'bar', Escaped('\\'), 'baz']

            """
            tokens = ['']
            esc = False
            for c in s:
                if esc:
                    tokens.extend([Escaped(c), ''])
                    esc = False
                else:
                    if c == '\\':
                        esc = True
                    else:
                        tokens[-1] += c
            return tokens

        tokens = tokenize(string)

        # Sorting by length ensures that the longest one will be
        # chosen as it will overwrite any shorter ones starting
        # at the same position in the `found` dictionary.
        separators = sorted(self.separators, key=len)

        for i, token in enumerate(tokens):

            if isinstance(token, Escaped):
                continue

            found = {}
            for sep in separators:
                pos = token.find(sep)
                if pos != -1:
                    found[pos] = sep

            if found:
                # Starting first, longest separator found.
                sep = found[min(found.keys())]

                key, value = token.split(sep, 1)

                # Any preceding tokens are part of the key.
                key = ''.join(tokens[:i]) + key

                # Any following tokens are part of the value.
                value += ''.join(tokens[i + 1:])

                break

        else:
            raise ArgumentTypeError(
                u'"%s" is not a valid value' % string)

        return self.key_value_class(
            key=key, value=value, sep=sep, orig=string)


class AuthCredentials(KeyValue):
    """Represents parsed credentials."""

    def _getpass(self, prompt):
        # To allow mocking.
        return getpass.getpass(prompt)

    def has_password(self):
        return self.value is not None

    def prompt_password(self, host):
        try:
            self.value = self._getpass(
                'http: password for %s@%s: ' % (self.key, host))
        except (EOFError, KeyboardInterrupt):
            sys.stderr.write('\n')
            sys.exit(0)


class AuthCredentialsArgType(KeyValueArgType):
    """A key-value arg type that parses credentials."""

    key_value_class = AuthCredentials

    def __call__(self, string):
        """Parse credentials from `string`.

        ("username" or "username:password").

        """
        try:
            return super(AuthCredentialsArgType, self).__call__(string)
        except ArgumentTypeError:
            # No password provided, will prompt for it later.
            return self.key_value_class(
                key=string,
                value=None,
                sep=SEP_CREDENTIALS,
                orig=string
            )


class ParamDict(OrderedDict):
    """Multi-value dict for URL parameters and form data."""

    #noinspection PyMethodOverriding
    def __setitem__(self, key, value):
        """ If `key` is assigned more than once, `self[key]` holds a
        `list` of all the values.

        This allows having multiple fields with the same name in form
        data and URL params.

        """
        if key not in self:
            super(ParamDict, self).__setitem__(key, value)
        else:
            if not isinstance(self[key], list):
                super(ParamDict, self).__setitem__(key, [self[key]])
            self[key].append(value)


def parse_items(items, data=None, headers=None, files=None, params=None):
    """Parse `KeyValue` `items` into `data`, `headers`, `files`,
    and `params`.

    """
    if headers is None:
        headers = CaseInsensitiveDict()
    if data is None:
        data = OrderedDict()
    if files is None:
        files = OrderedDict()
    if params is None:
        params = ParamDict()

    for item in items:
        value = item.value

        if item.sep == SEP_HEADERS:
            target = headers
        elif item.sep == SEP_QUERY:
            target = params
        elif item.sep == SEP_FILES:
            try:
                with open(os.path.expanduser(value), 'rb') as f:
                    value = (os.path.basename(value),
                             BytesIO(f.read()))
            except IOError as e:
                raise ParseError('"%s": %s' % (item.orig, e))
            target = files

        elif item.sep in SEP_GROUP_DATA_ITEMS:

            if item.sep in SEP_GROUP_DATA_EMBED_ITEMS:
                try:
                    with open(os.path.expanduser(value), 'rb') as f:
                        value = f.read().decode('utf8')
                except IOError as e:
                    raise ParseError('"%s": %s' % (item.orig, e))
                except UnicodeDecodeError:
                    raise ParseError(
                        '"%s": cannot embed the content of "%s",'
                        ' not a UTF8 or ASCII-encoded text file'
                        % (item.orig, item.value)
                    )

            if item.sep in SEP_GROUP_RAW_JSON_ITEMS:
                try:
                    value = json.loads(value)
                except ValueError as e:
                    raise ParseError('"%s": %s' % (item.orig, e))
            target = data

        else:
            raise TypeError(item)

        target[item.key] = value

    return headers, data, files, params


def readable_file_arg(filename):
    try:
        open(filename, 'rb')
    except IOError as ex:
        raise ArgumentTypeError('%s: %s' % (filename, ex.args[1]))
    return filename

########NEW FILE########
__FILENAME__ = models
from httpie.compat import urlsplit, str


class HTTPMessage(object):
    """Abstract class for HTTP messages."""

    def __init__(self, orig):
        self._orig = orig

    def iter_body(self, chunk_size):
        """Return an iterator over the body."""
        raise NotImplementedError()

    def iter_lines(self, chunk_size):
        """Return an iterator over the body yielding (`line`, `line_feed`)."""
        raise NotImplementedError()

    @property
    def headers(self):
        """Return a `str` with the message's headers."""
        raise NotImplementedError()

    @property
    def encoding(self):
        """Return a `str` with the message's encoding, if known."""
        raise NotImplementedError()

    @property
    def body(self):
        """Return a `bytes` with the message's body."""
        raise NotImplementedError()

    @property
    def content_type(self):
        """Return the message content type."""
        ct = self._orig.headers.get('Content-Type', '')
        if not isinstance(ct, str):
            ct = ct.decode('utf8')
        return ct


class HTTPResponse(HTTPMessage):
    """A :class:`requests.models.Response` wrapper."""

    def iter_body(self, chunk_size=1):
        return self._orig.iter_content(chunk_size=chunk_size)

    def iter_lines(self, chunk_size):
        return ((line, b'\n') for line in self._orig.iter_lines(chunk_size))

    #noinspection PyProtectedMember
    @property
    def headers(self):
        original = self._orig.raw._original_response
        version = {9: '0.9', 10: '1.0', 11: '1.1'}[original.version]
        status_line = 'HTTP/{version} {status} {reason}'.format(
            version=version,
            status=original.status,
            reason=original.reason
        )
        headers = [status_line]
        try:
            # `original.msg` is a `http.client.HTTPMessage` on Python 3
            # `_headers` is a 2-tuple
            headers.extend(
                '%s: %s' % header for header in original.msg._headers)
        except AttributeError:
            # and a `httplib.HTTPMessage` on Python 2.x
            # `headers` is a list of `name: val<CRLF>`.
            headers.extend(h.strip() for h in original.msg.headers)

        return '\r\n'.join(headers)

    @property
    def encoding(self):
        return self._orig.encoding or 'utf8'

    @property
    def body(self):
        # Only now the response body is fetched.
        # Shouldn't be touched unless the body is actually needed.
        return self._orig.content


class HTTPRequest(HTTPMessage):
    """A :class:`requests.models.Request` wrapper."""

    def iter_body(self, chunk_size):
        yield self.body

    def iter_lines(self, chunk_size):
        yield self.body, b''

    @property
    def headers(self):
        url = urlsplit(self._orig.url)

        request_line = '{method} {path}{query} HTTP/1.1'.format(
            method=self._orig.method,
            path=url.path or '/',
            query='?' + url.query if url.query else ''
        )

        headers = dict(self._orig.headers)

        if 'Host' not in headers:
            headers['Host'] = url.netloc.split('@')[-1]

        headers = ['%s: %s' % (name, value)
                   for name, value in headers.items()]

        headers.insert(0, request_line)
        headers = '\r\n'.join(headers).strip()

        if isinstance(headers, bytes):
            # Python < 3
            headers = headers.decode('utf8')
        return headers

    @property
    def encoding(self):
        return 'utf8'

    @property
    def body(self):
        body = self._orig.body
        if isinstance(body, str):
            # Happens with JSON/form request data parsed from the command line.
            body = body.encode('utf8')
        return body or b''

########NEW FILE########
__FILENAME__ = colors
import pygments.lexer
import pygments.token
import pygments.styles
import pygments.lexers
import pygments.style
from pygments.formatters.terminal import TerminalFormatter
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.util import ClassNotFound

from httpie.compat import is_windows
from httpie.plugins import FormatterPlugin


# Colors on Windows via colorama don't look that
# great and fruity seems to give the best result there.
AVAILABLE_STYLES = set(pygments.styles.STYLE_MAP.keys())
AVAILABLE_STYLES.add('solarized')
DEFAULT_STYLE = 'solarized' if not is_windows else 'fruity'


class ColorFormatter(FormatterPlugin):
    """
    Colorize using Pygments

    This processor that applies syntax highlighting to the headers,
    and also to the body if its content type is recognized.

    """
    group_name = 'colors'

    def __init__(self, env, color_scheme=DEFAULT_STYLE, **kwargs):
        super(ColorFormatter, self).__init__(**kwargs)
        if not env.colors:
            self.enabled = False
            return

        # Cache to speed things up when we process streamed body by line.
        self.lexer_cache = {}

        try:
            style_class = pygments.styles.get_style_by_name(color_scheme)
        except ClassNotFound:
            style_class = Solarized256Style

        if env.is_windows or env.colors == 256:
            fmt_class = Terminal256Formatter
        else:
            fmt_class = TerminalFormatter
        self.formatter = fmt_class(style=style_class)

    def format_headers(self, headers):
        return pygments.highlight(headers, HTTPLexer(), self.formatter).strip()

    def format_body(self, body, mime):
        lexer = self.get_lexer(mime)
        if lexer:
            body = pygments.highlight(body, lexer, self.formatter)
        return body.strip()

    def get_lexer(self, mime):
        if mime in self.lexer_cache:
            return self.lexer_cache[mime]
        self.lexer_cache[mime] = get_lexer(mime)
        return self.lexer_cache[mime]


def get_lexer(mime):
    mime_types, lexer_names = [mime], []
    type_, subtype = mime.split('/')
    if '+' not in subtype:
        lexer_names.append(subtype)
    else:
        subtype_name, subtype_suffix = subtype.split('+')
        lexer_names.extend([subtype_name, subtype_suffix])
        mime_types.extend([
            '%s/%s' % (type_, subtype_name),
            '%s/%s' % (type_, subtype_suffix)
        ])
    lexer = None
    for mime_type in mime_types:
        try:
            lexer = pygments.lexers.get_lexer_for_mimetype(mime_type)
            break
        except ClassNotFound:
            pass
    else:
        for name in lexer_names:
            try:
                lexer = pygments.lexers.get_lexer_by_name(name)
            except ClassNotFound:
                pass
    return lexer


class HTTPLexer(pygments.lexer.RegexLexer):
    """Simplified HTTP lexer for Pygments.

    It only operates on headers and provides a stronger contrast between
    their names and values than the original one bundled with Pygments
    (:class:`pygments.lexers.text import HttpLexer`), especially when
    Solarized color scheme is used.

    """
    name = 'HTTP'
    aliases = ['http']
    filenames = ['*.http']
    tokens = {
        'root': [
            # Request-Line
            (r'([A-Z]+)( +)([^ ]+)( +)(HTTP)(/)(\d+\.\d+)',
             pygments.lexer.bygroups(
                 pygments.token.Name.Function,
                 pygments.token.Text,
                 pygments.token.Name.Namespace,
                 pygments.token.Text,
                 pygments.token.Keyword.Reserved,
                 pygments.token.Operator,
                 pygments.token.Number
             )),
            # Response Status-Line
            (r'(HTTP)(/)(\d+\.\d+)( +)(\d{3})( +)(.+)',
             pygments.lexer.bygroups(
                 pygments.token.Keyword.Reserved,  # 'HTTP'
                 pygments.token.Operator,  # '/'
                 pygments.token.Number,  # Version
                 pygments.token.Text,
                 pygments.token.Number,  # Status code
                 pygments.token.Text,
                 pygments.token.Name.Exception,  # Reason
             )),
            # Header
            (r'(.*?)( *)(:)( *)(.+)', pygments.lexer.bygroups(
                pygments.token.Name.Attribute,  # Name
                pygments.token.Text,
                pygments.token.Operator,  # Colon
                pygments.token.Text,
                pygments.token.String  # Value
            ))
        ]
    }


class Solarized256Style(pygments.style.Style):
    """
    solarized256
    ------------

    A Pygments style inspired by Solarized's 256 color mode.

    :copyright: (c) 2011 by Hank Gay, (c) 2012 by John Mastro.
    :license: BSD, see LICENSE for more details.

    """
    BASE03 = "#1c1c1c"
    BASE02 = "#262626"
    BASE01 = "#4e4e4e"
    BASE00 = "#585858"
    BASE0 = "#808080"
    BASE1 = "#8a8a8a"
    BASE2 = "#d7d7af"
    BASE3 = "#ffffd7"
    YELLOW = "#af8700"
    ORANGE = "#d75f00"
    RED = "#af0000"
    MAGENTA = "#af005f"
    VIOLET = "#5f5faf"
    BLUE = "#0087ff"
    CYAN = "#00afaf"
    GREEN = "#5f8700"

    background_color = BASE03
    styles = {
        pygments.token.Keyword: GREEN,
        pygments.token.Keyword.Constant: ORANGE,
        pygments.token.Keyword.Declaration: BLUE,
        pygments.token.Keyword.Namespace: ORANGE,
        pygments.token.Keyword.Reserved: BLUE,
        pygments.token.Keyword.Type: RED,
        pygments.token.Name.Attribute: BASE1,
        pygments.token.Name.Builtin: BLUE,
        pygments.token.Name.Builtin.Pseudo: BLUE,
        pygments.token.Name.Class: BLUE,
        pygments.token.Name.Constant: ORANGE,
        pygments.token.Name.Decorator: BLUE,
        pygments.token.Name.Entity: ORANGE,
        pygments.token.Name.Exception: YELLOW,
        pygments.token.Name.Function: BLUE,
        pygments.token.Name.Tag: BLUE,
        pygments.token.Name.Variable: BLUE,
        pygments.token.String: CYAN,
        pygments.token.String.Backtick: BASE01,
        pygments.token.String.Char: CYAN,
        pygments.token.String.Doc: CYAN,
        pygments.token.String.Escape: RED,
        pygments.token.String.Heredoc: CYAN,
        pygments.token.String.Regex: RED,
        pygments.token.Number: CYAN,
        pygments.token.Operator: BASE1,
        pygments.token.Operator.Word: GREEN,
        pygments.token.Comment: BASE01,
        pygments.token.Comment.Preproc: GREEN,
        pygments.token.Comment.Special: GREEN,
        pygments.token.Generic.Deleted: CYAN,
        pygments.token.Generic.Emph: 'italic',
        pygments.token.Generic.Error: RED,
        pygments.token.Generic.Heading: ORANGE,
        pygments.token.Generic.Inserted: GREEN,
        pygments.token.Generic.Strong: 'bold',
        pygments.token.Generic.Subheading: ORANGE,
        pygments.token.Token: BASE1,
        pygments.token.Token.Other: ORANGE,
    }

########NEW FILE########
__FILENAME__ = headers
from httpie.plugins import FormatterPlugin


class HeadersFormatter(FormatterPlugin):

    def format_headers(self, headers):
        """
        Sorts headers by name while retaining relative
        order of multiple headers with the same name.

        """
        lines = headers.splitlines()
        headers = sorted(lines[1:], key=lambda h: h.split(':')[0])
        return '\r\n'.join(lines[:1] + headers)

########NEW FILE########
__FILENAME__ = json
from __future__ import absolute_import
import json

from httpie.plugins import FormatterPlugin


DEFAULT_INDENT = 4


class JSONFormatter(FormatterPlugin):

    def format_body(self, body, mime):
        if 'json' in mime:
            try:
                obj = json.loads(body)
            except ValueError:
                # Invalid JSON, ignore.
                pass
            else:
                # Indent, sort keys by name, and avoid
                # unicode escapes to improve readability.
                body = json.dumps(obj,
                                  sort_keys=True,
                                  ensure_ascii=False,
                                  indent=DEFAULT_INDENT)
        return body

########NEW FILE########
__FILENAME__ = xml
from __future__ import absolute_import
import re
from xml.etree import ElementTree

from httpie.plugins import FormatterPlugin


DECLARATION_RE = re.compile('<\?xml[^\n]+?\?>', flags=re.I)
DOCTYPE_RE = re.compile('<!DOCTYPE[^\n]+?>', flags=re.I)


DEFAULT_INDENT = 4


def indent(elem, indent_text=' ' * DEFAULT_INDENT):
    """
    In-place prettyprint formatter
    C.f. http://effbot.org/zone/element-lib.htm#prettyprint

    """
    def _indent(elem, level=0):
        i = "\n" + level * indent_text
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + indent_text
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                _indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    return _indent(elem)


class XMLFormatter(FormatterPlugin):
    # TODO: tests

    def format_body(self, body, mime):
        if 'xml' in mime:
            # FIXME: orig NS names get forgotten during the conversion, etc.
            try:
                root = ElementTree.fromstring(body.encode('utf8'))
            except ElementTree.ParseError:
                # Ignore invalid XML errors (skips attempting to pretty print)
                pass
            else:
                indent(root)
                # Use the original declaration
                declaration = DECLARATION_RE.match(body)
                doctype = DOCTYPE_RE.match(body)
                body = ElementTree.tostring(root, encoding='utf-8')\
                                  .decode('utf8')
                if doctype:
                    body = '%s\n%s' % (doctype.group(0), body)
                if declaration:
                    body = '%s\n%s' % (declaration.group(0), body)
        return body

########NEW FILE########
__FILENAME__ = processing
import re

from httpie.plugins import plugin_manager
from httpie.context import Environment


MIME_RE = re.compile(r'^[^/]+/[^/]+$')


def is_valid_mime(mime):
    return mime and MIME_RE.match(mime)


class Conversion(object):

    def get_converter(self, mime):
        if is_valid_mime(mime):
            for converter_class in plugin_manager.get_converters():
                if converter_class.supports(mime):
                    return converter_class(mime)


class Formatting(object):
    """A delegate class that invokes the actual processors."""

    def __init__(self, groups, env=Environment(), **kwargs):
        """
        :param groups: names of processor groups to be applied
        :param env: Environment
        :param kwargs: additional keyword arguments for processors

        """
        available_plugins = plugin_manager.get_formatters_grouped()
        self.enabled_plugins = []
        for group in groups:
            for cls in available_plugins[group]:
                p = cls(env=env, **kwargs)
                if p.enabled:
                    self.enabled_plugins.append(p)

    def format_headers(self, headers):
        for p in self.enabled_plugins:
            headers = p.format_headers(headers)
        return headers

    def format_body(self, content, mime):
        if is_valid_mime(mime):
            for p in self.enabled_plugins:
                content = p.format_body(content, mime)
        return content

########NEW FILE########
__FILENAME__ = streams
from itertools import chain
from functools import partial

from httpie.compat import str
from httpie.context import Environment
from httpie.models import HTTPRequest, HTTPResponse
from httpie.input import (OUT_REQ_BODY, OUT_REQ_HEAD,
                          OUT_RESP_HEAD, OUT_RESP_BODY)
from httpie.output.processing import Formatting, Conversion


BINARY_SUPPRESSED_NOTICE = (
    b'\n'
    b'+-----------------------------------------+\n'
    b'| NOTE: binary data not shown in terminal |\n'
    b'+-----------------------------------------+'
)


class BinarySuppressedError(Exception):
    """An error indicating that the body is binary and won't be written,
     e.g., for terminal output)."""

    message = BINARY_SUPPRESSED_NOTICE


def write(stream, outfile, flush):
    """Write the output stream."""
    try:
        # Writing bytes so we use the buffer interface (Python 3).
        buf = outfile.buffer
    except AttributeError:
        buf = outfile

    for chunk in stream:
        buf.write(chunk)
        if flush:
            outfile.flush()


def write_with_colors_win_py3(stream, outfile, flush):
    """Like `write`, but colorized chunks are written as text
    directly to `outfile` to ensure it gets processed by colorama.
    Applies only to Windows with Python 3 and colorized terminal output.

    """
    color = b'\x1b['
    encoding = outfile.encoding
    for chunk in stream:
        if color in chunk:
            outfile.write(chunk.decode(encoding))
        else:
            outfile.buffer.write(chunk)
        if flush:
            outfile.flush()


def build_output_stream(args, env, request, response):
    """Build and return a chain of iterators over the `request`-`response`
    exchange each of which yields `bytes` chunks.

    """
    req_h = OUT_REQ_HEAD in args.output_options
    req_b = OUT_REQ_BODY in args.output_options
    resp_h = OUT_RESP_HEAD in args.output_options
    resp_b = OUT_RESP_BODY in args.output_options
    req = req_h or req_b
    resp = resp_h or resp_b

    output = []
    Stream = get_stream_type(env, args)

    if req:
        output.append(Stream(
            msg=HTTPRequest(request),
            with_headers=req_h,
            with_body=req_b))

    if req_b and resp:
        # Request/Response separator.
        output.append([b'\n\n'])

    if resp:
        output.append(Stream(
            msg=HTTPResponse(response),
            with_headers=resp_h,
            with_body=resp_b))

    if env.stdout_isatty and resp_b:
        # Ensure a blank line after the response body.
        # For terminal output only.
        output.append([b'\n\n'])

    return chain(*output)


def get_stream_type(env, args):
    """Pick the right stream type based on `env` and `args`.
    Wrap it in a partial with the type-specific args so that
    we don't need to think what stream we are dealing with.

    """
    if not env.stdout_isatty and not args.prettify:
        Stream = partial(
            RawStream,
            chunk_size=RawStream.CHUNK_SIZE_BY_LINE
            if args.stream
            else RawStream.CHUNK_SIZE
        )
    elif args.prettify:
        Stream = partial(
            PrettyStream if args.stream else BufferedPrettyStream,
            env=env,
            conversion=Conversion(),
            formatting=Formatting(env=env, groups=args.prettify,
                                  color_scheme=args.style),
        )
    else:
        Stream = partial(EncodedStream, env=env)

    return Stream


class BaseStream(object):
    """Base HTTP message output stream class."""

    def __init__(self, msg, with_headers=True, with_body=True,
                 on_body_chunk_downloaded=None):
        """
        :param msg: a :class:`models.HTTPMessage` subclass
        :param with_headers: if `True`, headers will be included
        :param with_body: if `True`, body will be included

        """
        assert with_headers or with_body
        self.msg = msg
        self.with_headers = with_headers
        self.with_body = with_body
        self.on_body_chunk_downloaded = on_body_chunk_downloaded

    def get_headers(self):
        """Return the headers' bytes."""
        return self.msg.headers.encode('utf8')

    def iter_body(self):
        """Return an iterator over the message body."""
        raise NotImplementedError()

    def __iter__(self):
        """Return an iterator over `self.msg`."""
        if self.with_headers:
            yield self.get_headers()
            yield b'\r\n\r\n'

        if self.with_body:
            try:
                for chunk in self.iter_body():
                    yield chunk
                    if self.on_body_chunk_downloaded:
                        self.on_body_chunk_downloaded(chunk)
            except BinarySuppressedError as e:
                if self.with_headers:
                    yield b'\n'
                yield e.message


class RawStream(BaseStream):
    """The message is streamed in chunks with no processing."""

    CHUNK_SIZE = 1024 * 100
    CHUNK_SIZE_BY_LINE = 1

    def __init__(self, chunk_size=CHUNK_SIZE, **kwargs):
        super(RawStream, self).__init__(**kwargs)
        self.chunk_size = chunk_size

    def iter_body(self):
        return self.msg.iter_body(self.chunk_size)


class EncodedStream(BaseStream):
    """Encoded HTTP message stream.

    The message bytes are converted to an encoding suitable for
    `self.env.stdout`. Unicode errors are replaced and binary data
    is suppressed. The body is always streamed by line.

    """
    CHUNK_SIZE = 1

    def __init__(self, env=Environment(), **kwargs):

        super(EncodedStream, self).__init__(**kwargs)

        if env.stdout_isatty:
            # Use the encoding supported by the terminal.
            output_encoding = env.stdout_encoding
        else:
            # Preserve the message encoding.
            output_encoding = self.msg.encoding

        # Default to utf8 when unsure.
        self.output_encoding = output_encoding or 'utf8'

    def iter_body(self):

        for line, lf in self.msg.iter_lines(self.CHUNK_SIZE):

            if b'\0' in line:
                raise BinarySuppressedError()

            yield line.decode(self.msg.encoding) \
                      .encode(self.output_encoding, 'replace') + lf


class PrettyStream(EncodedStream):
    """In addition to :class:`EncodedStream` behaviour, this stream applies
    content processing.

    Useful for long-lived HTTP responses that stream by lines
    such as the Twitter streaming API.

    """

    CHUNK_SIZE = 1

    def __init__(self, conversion, formatting, **kwargs):
        super(PrettyStream, self).__init__(**kwargs)
        self.formatting = formatting
        self.conversion = conversion
        self.mime = self.msg.content_type.split(';')[0]

    def get_headers(self):
        return self.formatting.format_headers(
            self.msg.headers).encode(self.output_encoding)

    def iter_body(self):
        first_chunk = True
        iter_lines = self.msg.iter_lines(self.CHUNK_SIZE)
        for line, lf in iter_lines:
            if b'\0' in line:
                if first_chunk:
                    converter = self.conversion.get_converter(self.mime)
                    if converter:
                        body = bytearray()
                        # noinspection PyAssignmentToLoopOrWithParameter
                        for line, lf in chain([(line, lf)], iter_lines):
                            body.extend(line)
                            body.extend(lf)
                        self.mime, body = converter.convert(body)
                        assert isinstance(body, str)
                        yield self.process_body(body)
                        return
                raise BinarySuppressedError()
            yield self.process_body(line) + lf
            first_chunk = False

    def process_body(self, chunk):
        if not isinstance(chunk, str):
            # Text when a converter has been used,
            # otherwise it will always be bytes.
            chunk = chunk.decode(self.msg.encoding, 'replace')
        chunk = self.formatting.format_body(content=chunk, mime=self.mime)
        return chunk.encode(self.output_encoding, 'replace')


class BufferedPrettyStream(PrettyStream):
    """The same as :class:`PrettyStream` except that the body is fully
    fetched before it's processed.

    Suitable regular HTTP responses.

    """

    CHUNK_SIZE = 1024 * 10

    def iter_body(self):
        # Read the whole body before prettifying it,
        # but bail out immediately if the body is binary.
        converter = None
        body = bytearray()

        for chunk in self.msg.iter_body(self.CHUNK_SIZE):
            if not converter and b'\0' in chunk:
                converter = self.conversion.get_converter(self.mime)
                if not converter:
                    raise BinarySuppressedError()
            body.extend(chunk)

        if converter:
            self.mime, body = converter.convert(body)

        yield self.process_body(body)

########NEW FILE########
__FILENAME__ = base
class BasePlugin(object):

    # The name of the plugin, eg. "My auth".
    name = None

    # Optional short description. Will be be shown in the help
    # under --auth-type.
    description = None

    # This be set automatically once the plugin has been loaded.
    package_name = None


class AuthPlugin(BasePlugin):
    """
    Base auth plugin class.

    See <https://github.com/jkbr/httpie-ntlm> for an example auth plugin.

    """
    # The value that should be passed to --auth-type
    # to use this auth plugin. Eg. "my-auth"
    auth_type = None

    def get_auth(self, username, password):
        """
        Return a ``requests.auth.AuthBase`` subclass instance.

        """
        raise NotImplementedError()


class ConverterPlugin(object):

    def __init__(self, mime):
        self.mime = mime

    def convert(self, content_bytes):
        raise NotImplementedError

    @classmethod
    def supports(cls, mime):
        raise NotImplementedError


class FormatterPlugin(object):

    def __init__(self, **kwargs):
        """
        :param env: an class:`Environment` instance
        :param kwargs: additional keyword argument that some
                       processor might require.

        """
        self.enabled = True
        self.kwargs = kwargs

    def format_headers(self, headers):
        """Return processed `headers`

        :param headers: The headers as text.

        """
        return headers

    def format_body(self, content, mime):
        """Return processed `content`.

        :param mime: E.g., 'application/atom+xml'.
        :param content: The body content as text

        """
        return content

########NEW FILE########
__FILENAME__ = builtin
from base64 import b64encode

import requests.auth

from httpie.plugins.base import AuthPlugin


class BuiltinAuthPlugin(AuthPlugin):

    package_name = '(builtin)'


class HTTPBasicAuth(requests.auth.HTTPBasicAuth):

    def __call__(self, r):
        """
        Override username/password serialization to allow unicode.

        See https://github.com/jakubroztocil/httpie/issues/212

        """
        r.headers['Authorization'] = type(self).make_header(
            self.username, self.password).encode('latin1')
        return r

    @staticmethod
    def make_header(username, password):
        credentials = u'%s:%s' % (username, password)
        token = b64encode(credentials.encode('utf8')).strip().decode('latin1')
        return 'Basic %s' % token


class BasicAuthPlugin(BuiltinAuthPlugin):

    name = 'Basic HTTP auth'
    auth_type = 'basic'

    def get_auth(self, username, password):
        return HTTPBasicAuth(username, password)


class DigestAuthPlugin(BuiltinAuthPlugin):

    name = 'Digest HTTP auth'
    auth_type = 'digest'

    def get_auth(self, username, password):
        return requests.auth.HTTPDigestAuth(username, password)

########NEW FILE########
__FILENAME__ = manager
from itertools import groupby
from pkg_resources import iter_entry_points
from httpie.plugins import AuthPlugin, FormatterPlugin, ConverterPlugin


ENTRY_POINT_NAMES = [
    'httpie.plugins.auth.v1',
    'httpie.plugins.formatter.v1',
    'httpie.plugins.converter.v1',
]


class PluginManager(object):

    def __init__(self):
        self._plugins = []

    def __iter__(self):
        return iter(self._plugins)

    def register(self, *plugins):
        for plugin in plugins:
            self._plugins.append(plugin)

    def load_installed_plugins(self):
        for entry_point_name in ENTRY_POINT_NAMES:
            for entry_point in iter_entry_points(entry_point_name):
                plugin = entry_point.load()
                plugin.package_name = entry_point.dist.key
                self.register(entry_point.load())

    # Auth
    def get_auth_plugins(self):
        return [plugin for plugin in self if issubclass(plugin, AuthPlugin)]

    def get_auth_plugin_mapping(self):
        return dict((plugin.auth_type, plugin)
                    for plugin in self.get_auth_plugins())

    def get_auth_plugin(self, auth_type):
        return self.get_auth_plugin_mapping()[auth_type]

    # Output processing
    def get_formatters(self):
        return [plugin for plugin in self
                if issubclass(plugin, FormatterPlugin)]

    def get_formatters_grouped(self):
        groups = {}
        for group_name, group in groupby(
                self.get_formatters(),
                key=lambda p: getattr(p, 'group_name', 'format')):
            groups[group_name] = list(group)
        return groups

    def get_converters(self):
        return [plugin for plugin in self
                if issubclass(plugin, ConverterPlugin)]

########NEW FILE########
__FILENAME__ = sessions
"""Persistent, JSON-serialized sessions.

"""
import re
import os

import requests
from requests.cookies import RequestsCookieJar, create_cookie

from httpie.compat import urlsplit
from httpie.config import BaseConfigDict, DEFAULT_CONFIG_DIR
from httpie.plugins import plugin_manager


SESSIONS_DIR_NAME = 'sessions'
DEFAULT_SESSIONS_DIR = os.path.join(DEFAULT_CONFIG_DIR, SESSIONS_DIR_NAME)
VALID_SESSION_NAME_PATTERN = re.compile('^[a-zA-Z0-9_.-]+$')
# Request headers starting with these prefixes won't be stored in sessions.
# They are specific to each request.
# http://en.wikipedia.org/wiki/List_of_HTTP_header_fields#Requests
SESSION_IGNORED_HEADER_PREFIXES = ['Content-', 'If-']


def get_response(session_name, config_dir, args, read_only=False):
    """Like `client.get_response`, but applies permanent
    aspects of the session to the request.

    """
    from .client import get_requests_kwargs, dump_request
    if os.path.sep in session_name:
        path = os.path.expanduser(session_name)
    else:
        hostname = (args.headers.get('Host', None)
                    or urlsplit(args.url).netloc.split('@')[-1])
        assert re.match('^[a-zA-Z0-9_.:-]+$', hostname)

        # host:port => host_port
        hostname = hostname.replace(':', '_')
        path = os.path.join(config_dir,
                            SESSIONS_DIR_NAME,
                            hostname,
                            session_name + '.json')

    session = Session(path)
    session.load()

    requests_kwargs = get_requests_kwargs(args, base_headers=session.headers)
    if args.debug:
        dump_request(requests_kwargs)
    session.update_headers(requests_kwargs['headers'])

    if args.auth:
        session.auth = {
            'type': args.auth_type,
            'username': args.auth.key,
            'password': args.auth.value,
        }
    elif session.auth:
        requests_kwargs['auth'] = session.auth

    requests_session = requests.Session()
    requests_session.cookies = session.cookies

    try:
        response = requests_session.request(**requests_kwargs)
    except Exception:
        raise
    else:
        # Existing sessions with `read_only=True` don't get updated.
        if session.is_new() or not read_only:
            session.cookies = requests_session.cookies
            session.save()
        return response


class Session(BaseConfigDict):
    helpurl = 'https://github.com/jakubroztocil/httpie#sessions'
    about = 'HTTPie session file'

    def __init__(self, path, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        self._path = path
        self['headers'] = {}
        self['cookies'] = {}
        self['auth'] = {
            'type': None,
            'username': None,
            'password': None
        }

    def _get_path(self):
        return self._path

    def update_headers(self, request_headers):
        """
        Update the session headers with the request ones while ignoring
        certain name prefixes.

        :type request_headers: dict

        """
        for name, value in request_headers.items():
            value = value.decode('utf8')
            if name == 'User-Agent' and value.startswith('HTTPie/'):
                continue

            for prefix in SESSION_IGNORED_HEADER_PREFIXES:
                if name.lower().startswith(prefix.lower()):
                    break
            else:
                self['headers'][name] = value

    @property
    def headers(self):
        return self['headers']

    @property
    def cookies(self):
        jar = RequestsCookieJar()
        for name, cookie_dict in self['cookies'].items():
            jar.set_cookie(create_cookie(
                name, cookie_dict.pop('value'), **cookie_dict))
        jar.clear_expired_cookies()
        return jar

    @cookies.setter
    def cookies(self, jar):
        """
        :type jar: CookieJar
        """
        # http://docs.python.org/2/library/cookielib.html#cookie-objects
        stored_attrs = ['value', 'path', 'secure', 'expires']
        self['cookies'] = {}
        for cookie in jar:
            self['cookies'][cookie.name] = dict(
                (attname, getattr(cookie, attname))
                for attname in stored_attrs
            )

    @property
    def auth(self):
        auth = self.get('auth', None)
        if not auth or not auth['type']:
            return
        auth_plugin = plugin_manager.get_auth_plugin(auth['type'])()
        return auth_plugin.get_auth(auth['username'], auth['password'])

    @auth.setter
    def auth(self, auth):
        assert set(['type', 'username', 'password']) == set(auth.keys())
        self['auth'] = auth

########NEW FILE########
__FILENAME__ = utils
from __future__ import division


def humanize_bytes(n, precision=2):
    # Author: Doug Latornell
    # Licence: MIT
    # URL: http://code.activestate.com/recipes/577081/
    """Return a humanized string representation of a number of bytes.

    Assumes `from __future__ import division`.

    >>> humanize_bytes(1)
    '1 B'
    >>> humanize_bytes(1024, precision=1)
    '1.0 kB'
    >>> humanize_bytes(1024 * 123, precision=1)
    '123.0 kB'
    >>> humanize_bytes(1024 * 12342, precision=1)
    '12.1 MB'
    >>> humanize_bytes(1024 * 12342, precision=2)
    '12.05 MB'
    >>> humanize_bytes(1024 * 1234, precision=2)
    '1.21 MB'
    >>> humanize_bytes(1024 * 1234 * 1111, precision=2)
    '1.31 GB'
    >>> humanize_bytes(1024 * 1234 * 1111, precision=1)
    '1.3 GB'

    """
    abbrevs = [
        (1 << 50, 'PB'),
        (1 << 40, 'TB'),
        (1 << 30, 'GB'),
        (1 << 20, 'MB'),
        (1 << 10, 'kB'),
        (1, 'B')
    ]

    if n == 1:
        return '1 B'

    for factor, suffix in abbrevs:
        if n >= factor:
            break

    # noinspection PyUnboundLocalVariable
    return '%.*f %s' % (precision, n / factor, suffix)


########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
"""The main entry point. Invoke as `http' or `python -m httpie'.

"""
import sys
from .core import main


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = fixtures
"""Test data"""
from os import path
import codecs


def patharg(path):
    """
    Back slashes need to be escaped in ITEM args,
    even in Windows paths.

    """
    return path.replace('\\', '\\\\\\')


FIXTURES_ROOT = path.join(path.abspath(path.dirname(__file__)), 'fixtures')
FILE_PATH = path.join(FIXTURES_ROOT, 'test.txt')
JSON_FILE_PATH = path.join(FIXTURES_ROOT, 'test.json')
BIN_FILE_PATH = path.join(FIXTURES_ROOT, 'test.bin')


FILE_PATH_ARG = patharg(FILE_PATH)
BIN_FILE_PATH_ARG = patharg(BIN_FILE_PATH)
JSON_FILE_PATH_ARG = patharg(JSON_FILE_PATH)


with codecs.open(FILE_PATH, encoding='utf8') as f:
    # Strip because we don't want new lines in the data so that we can
    # easily count occurrences also when embedded in JSON (where the new
    # line would be escaped).
    FILE_CONTENT = f.read().strip()


with codecs.open(JSON_FILE_PATH, encoding='utf8') as f:
    JSON_FILE_CONTENT = f.read()


with open(BIN_FILE_PATH, 'rb') as f:
    BIN_FILE_CONTENT = f.read()

UNICODE = FILE_CONTENT


########NEW FILE########
__FILENAME__ = test_auth
"""HTTP authentication-related tests."""
import requests
import pytest

from utils import http, httpbin, HTTP_OK
import httpie.input


class TestAuth:
    def test_basic_auth(self):
        r = http('--auth=user:password',
                 'GET', httpbin('/basic-auth/user/password'))
        assert HTTP_OK in r
        assert r.json == {'authenticated': True, 'user': 'user'}

    @pytest.mark.skipif(
        requests.__version__ == '0.13.6',
        reason='Redirects with prefetch=False are broken in Requests 0.13.6')
    def test_digest_auth(self):
        r = http('--auth-type=digest', '--auth=user:password',
                 'GET', httpbin('/digest-auth/auth/user/password'))
        assert HTTP_OK in r
        assert r.json == {'authenticated': True, 'user': 'user'}

    def test_password_prompt(self):
        httpie.input.AuthCredentials._getpass = lambda self, prompt: 'password'
        r = http('--auth', 'user', 'GET', httpbin('/basic-auth/user/password'))
        assert HTTP_OK in r
        assert r.json == {'authenticated': True, 'user': 'user'}

    def test_credentials_in_url(self):
        url = httpbin('/basic-auth/user/password', auth='user:password')
        r = http('GET', url)
        assert HTTP_OK in r
        assert r.json == {'authenticated': True, 'user': 'user'}

    def test_credentials_in_url_auth_flag_has_priority(self):
        """When credentials are passed in URL and via -a at the same time,
         then the ones from -a are used."""
        url = httpbin('/basic-auth/user/password', auth='user:wrong')
        r = http('--auth=user:password', 'GET', url)
        assert HTTP_OK in r
        assert r.json == {'authenticated': True, 'user': 'user'}

########NEW FILE########
__FILENAME__ = test_binary
"""Tests for dealing with binary request and response data."""
from httpie.compat import urlopen
from httpie.output.streams import BINARY_SUPPRESSED_NOTICE
from utils import TestEnvironment, http, httpbin
from fixtures import BIN_FILE_PATH, BIN_FILE_CONTENT, BIN_FILE_PATH_ARG


class TestBinaryRequestData:
    def test_binary_stdin(self):
        with open(BIN_FILE_PATH, 'rb') as stdin:
            env = TestEnvironment(
                stdin=stdin,
                stdin_isatty=False,
                stdout_isatty=False
            )
            r = http('--print=B', 'POST', httpbin('/post'), env=env)
            assert r == BIN_FILE_CONTENT

    def test_binary_file_path(self):
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--print=B', 'POST', httpbin('/post'),
                 '@' + BIN_FILE_PATH_ARG, env=env, )
        assert r == BIN_FILE_CONTENT

    def test_binary_file_form(self):
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--print=B', '--form', 'POST', httpbin('/post'),
                 'test@' + BIN_FILE_PATH_ARG, env=env)
        assert bytes(BIN_FILE_CONTENT) in bytes(r)


class TestBinaryResponseData:
    url = 'http://www.google.com/favicon.ico'

    @property
    def bindata(self):
        if not hasattr(self, '_bindata'):
            self._bindata = urlopen(self.url).read()
        return self._bindata

    def test_binary_suppresses_when_terminal(self):
        r = http('GET', self.url)
        assert BINARY_SUPPRESSED_NOTICE.decode() in r

    def test_binary_suppresses_when_not_terminal_but_pretty(self):
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--pretty=all', 'GET', self.url,
                 env=env)
        assert BINARY_SUPPRESSED_NOTICE.decode() in r

    def test_binary_included_and_correct_when_suitable(self):
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('GET', self.url, env=env)
        assert r == self.bindata

########NEW FILE########
__FILENAME__ = test_cli
"""CLI argument parsing related tests."""
import json
# noinspection PyCompatibility
import argparse

import pytest

from httpie import input
from httpie.input import KeyValue, KeyValueArgType
from httpie import ExitStatus
from httpie.cli import parser
from utils import TestEnvironment, http, httpbin, HTTP_OK
from fixtures import (
    FILE_PATH_ARG, JSON_FILE_PATH_ARG,
    JSON_FILE_CONTENT, FILE_CONTENT, FILE_PATH
)


class TestItemParsing:

    key_value_type = KeyValueArgType(*input.SEP_GROUP_ALL_ITEMS)

    def test_invalid_items(self):
        items = ['no-separator']
        for item in items:
            pytest.raises(argparse.ArgumentTypeError,
                          self.key_value_type, item)

    def test_escape(self):
        headers, data, files, params = input.parse_items([
            # headers
            self.key_value_type('foo\\:bar:baz'),
            self.key_value_type('jack\\@jill:hill'),
            # data
            self.key_value_type('baz\\=bar=foo'),
            # files
            self.key_value_type('bar\\@baz@%s' % FILE_PATH_ARG)
        ])
        # `requests.structures.CaseInsensitiveDict` => `dict`
        headers = dict(headers._store.values())
        assert headers == {
            'foo:bar': 'baz',
            'jack@jill': 'hill',
        }
        assert data == {'baz=bar': 'foo'}
        assert 'bar@baz' in files

    def test_escape_longsep(self):
        headers, data, files, params = input.parse_items([
            self.key_value_type('bob\\:==foo'),
        ])
        assert params == {'bob:': 'foo'}

    def test_valid_items(self):
        headers, data, files, params = input.parse_items([
            self.key_value_type('string=value'),
            self.key_value_type('header:value'),
            self.key_value_type('list:=["a", 1, {}, false]'),
            self.key_value_type('obj:={"a": "b"}'),
            self.key_value_type('eh:'),
            self.key_value_type('ed='),
            self.key_value_type('bool:=true'),
            self.key_value_type('file@' + FILE_PATH_ARG),
            self.key_value_type('query==value'),
            self.key_value_type('string-embed=@' + FILE_PATH_ARG),
            self.key_value_type('raw-json-embed:=@' + JSON_FILE_PATH_ARG),
        ])

        # Parsed headers
        # `requests.structures.CaseInsensitiveDict` => `dict`
        headers = dict(headers._store.values())
        assert headers == {'header': 'value', 'eh': ''}

        # Parsed data
        raw_json_embed = data.pop('raw-json-embed')
        assert raw_json_embed == json.loads(JSON_FILE_CONTENT)
        data['string-embed'] = data['string-embed'].strip()
        assert dict(data) == {
            "ed": "",
            "string": "value",
            "bool": True,
            "list": ["a", 1, {}, False],
            "obj": {"a": "b"},
            "string-embed": FILE_CONTENT,
        }

        # Parsed query string parameters
        assert params == {'query': 'value'}

        # Parsed file fields
        assert 'file' in files
        assert files['file'][1].read().strip().decode('utf8') == FILE_CONTENT


class TestQuerystring:
    def test_query_string_params_in_url(self):
        r = http('--print=Hhb', 'GET', httpbin('/get?a=1&b=2'))
        path = '/get?a=1&b=2'
        url = httpbin(path)
        assert HTTP_OK in r
        assert 'GET %s HTTP/1.1' % path in r
        assert '"url": "%s"' % url in r

    def test_query_string_params_items(self):
        r = http('--print=Hhb', 'GET', httpbin('/get'), 'a==1', 'b==2')
        path = '/get?a=1&b=2'
        url = httpbin(path)
        assert HTTP_OK in r
        assert 'GET %s HTTP/1.1' % path in r
        assert '"url": "%s"' % url in r

    def test_query_string_params_in_url_and_items_with_duplicates(self):
        r = http('--print=Hhb', 'GET', httpbin('/get?a=1&a=1'),
                 'a==1', 'a==1', 'b==2')
        path = '/get?a=1&a=1&a=1&a=1&b=2'
        url = httpbin(path)
        assert HTTP_OK in r
        assert 'GET %s HTTP/1.1' % path in r
        assert '"url": "%s"' % url in r


class TestCLIParser:
    def test_expand_localhost_shorthand(self):
        args = parser.parse_args(args=[':'], env=TestEnvironment())
        assert args.url == 'http://localhost'

    def test_expand_localhost_shorthand_with_slash(self):
        args = parser.parse_args(args=[':/'], env=TestEnvironment())
        assert args.url == 'http://localhost/'

    def test_expand_localhost_shorthand_with_port(self):
        args = parser.parse_args(args=[':3000'], env=TestEnvironment())
        assert args.url == 'http://localhost:3000'

    def test_expand_localhost_shorthand_with_path(self):
        args = parser.parse_args(args=[':/path'], env=TestEnvironment())
        assert args.url == 'http://localhost/path'

    def test_expand_localhost_shorthand_with_port_and_slash(self):
        args = parser.parse_args(args=[':3000/'], env=TestEnvironment())
        assert args.url == 'http://localhost:3000/'

    def test_expand_localhost_shorthand_with_port_and_path(self):
        args = parser.parse_args(args=[':3000/path'], env=TestEnvironment())
        assert args.url == 'http://localhost:3000/path'

    def test_dont_expand_shorthand_ipv6_as_shorthand(self):
        args = parser.parse_args(args=['::1'], env=TestEnvironment())
        assert args.url == 'http://::1'

    def test_dont_expand_longer_ipv6_as_shorthand(self):
        args = parser.parse_args(
            args=['::ffff:c000:0280'],
            env=TestEnvironment()
        )
        assert args.url == 'http://::ffff:c000:0280'

    def test_dont_expand_full_ipv6_as_shorthand(self):
        args = parser.parse_args(
            args=['0000:0000:0000:0000:0000:0000:0000:0001'],
            env=TestEnvironment()
        )
        assert args.url == 'http://0000:0000:0000:0000:0000:0000:0000:0001'


class TestArgumentParser:

    def setup_method(self, method):
        self.parser = input.Parser()

    def test_guess_when_method_set_and_valid(self):
        self.parser.args = argparse.Namespace()
        self.parser.args.method = 'GET'
        self.parser.args.url = 'http://example.com/'
        self.parser.args.items = []
        self.parser.args.ignore_stdin = False

        self.parser.env = TestEnvironment()

        self.parser._guess_method()

        assert self.parser.args.method == 'GET'
        assert self.parser.args.url == 'http://example.com/'
        assert self.parser.args.items == []

    def test_guess_when_method_not_set(self):
        self.parser.args = argparse.Namespace()
        self.parser.args.method = None
        self.parser.args.url = 'http://example.com/'
        self.parser.args.items = []
        self.parser.args.ignore_stdin = False
        self.parser.env = TestEnvironment()

        self.parser._guess_method()

        assert self.parser.args.method == 'GET'
        assert self.parser.args.url == 'http://example.com/'
        assert self.parser.args.items == []

    def test_guess_when_method_set_but_invalid_and_data_field(self):
        self.parser.args = argparse.Namespace()
        self.parser.args.method = 'http://example.com/'
        self.parser.args.url = 'data=field'
        self.parser.args.items = []
        self.parser.args.ignore_stdin = False
        self.parser.env = TestEnvironment()
        self.parser._guess_method()

        assert self.parser.args.method == 'POST'
        assert self.parser.args.url == 'http://example.com/'
        assert self.parser.args.items == [
            KeyValue(key='data',
                     value='field',
                     sep='=',
                     orig='data=field')
        ]

    def test_guess_when_method_set_but_invalid_and_header_field(self):
        self.parser.args = argparse.Namespace()
        self.parser.args.method = 'http://example.com/'
        self.parser.args.url = 'test:header'
        self.parser.args.items = []
        self.parser.args.ignore_stdin = False

        self.parser.env = TestEnvironment()

        self.parser._guess_method()

        assert self.parser.args.method == 'GET'
        assert self.parser.args.url == 'http://example.com/'
        assert self.parser.args.items, [
            KeyValue(key='test',
                     value='header',
                     sep=':',
                     orig='test:header')
        ]

    def test_guess_when_method_set_but_invalid_and_item_exists(self):
        self.parser.args = argparse.Namespace()
        self.parser.args.method = 'http://example.com/'
        self.parser.args.url = 'new_item=a'
        self.parser.args.items = [
            KeyValue(
                key='old_item', value='b', sep='=', orig='old_item=b')
        ]
        self.parser.args.ignore_stdin = False

        self.parser.env = TestEnvironment()

        self.parser._guess_method()

        assert self.parser.args.items, [
            KeyValue(key='new_item', value='a', sep='=', orig='new_item=a'),
            KeyValue(
                key='old_item', value='b', sep='=', orig='old_item=b'),
        ]


class TestNoOptions:
    def test_valid_no_options(self):
        r = http('--verbose', '--no-verbose', 'GET', httpbin('/get'))
        assert 'GET /get HTTP/1.1' not in r

    def test_invalid_no_options(self):
        r = http('--no-war', 'GET', httpbin('/get'),
                 error_exit_ok=True)
        assert r.exit_status == 1
        assert 'unrecognized arguments: --no-war' in r.stderr
        assert 'GET /get HTTP/1.1' not in r


class TestIgnoreStdin:
    def test_ignore_stdin(self):
        with open(FILE_PATH) as f:
            env = TestEnvironment(stdin=f, stdin_isatty=False)
            r = http('--ignore-stdin', '--verbose', httpbin('/get'), env=env)
        assert HTTP_OK in r
        assert 'GET /get HTTP' in r, "Don't default to POST."
        assert FILE_CONTENT not in r, "Don't send stdin data."

    def test_ignore_stdin_cannot_prompt_password(self):
        r = http('--ignore-stdin', '--auth=no-password', httpbin('/get'),
                 error_exit_ok=True)
        assert r.exit_status == ExitStatus.ERROR
        assert 'because --ignore-stdin' in r.stderr

########NEW FILE########
__FILENAME__ = test_defaults
"""
Tests for the provided defaults regarding HTTP method, and --json vs. --form.

"""
from utils import TestEnvironment, http, httpbin, HTTP_OK
from fixtures import FILE_PATH


class TestImplicitHTTPMethod:
    def test_implicit_GET(self):
        r = http(httpbin('/get'))
        assert HTTP_OK in r

    def test_implicit_GET_with_headers(self):
        r = http(httpbin('/headers'), 'Foo:bar')
        assert HTTP_OK in r
        assert r.json['headers']['Foo'] == 'bar'

    def test_implicit_POST_json(self):
        r = http(httpbin('/post'), 'hello=world')
        assert HTTP_OK in r
        assert r.json['json'] == {'hello': 'world'}

    def test_implicit_POST_form(self):
        r = http('--form', httpbin('/post'), 'foo=bar')
        assert HTTP_OK in r
        assert r.json['form'] == {'foo': 'bar'}

    def test_implicit_POST_stdin(self):
        with open(FILE_PATH) as f:
            env = TestEnvironment(stdin_isatty=False, stdin=f)
            r = http('--form', httpbin('/post'), env=env)
        assert HTTP_OK in r


class TestAutoContentTypeAndAcceptHeaders:
    """
    Test that Accept and Content-Type correctly defaults to JSON,
    but can still be overridden. The same with Content-Type when --form
    -f is used.

    """

    def test_GET_no_data_no_auto_headers(self):
        # https://github.com/jakubroztocil/httpie/issues/62
        r = http('GET', httpbin('/headers'))
        assert HTTP_OK in r
        assert r.json['headers']['Accept'] == '*/*'
        assert 'Content-Type' not in r.json['headers']

    def test_POST_no_data_no_auto_headers(self):
        # JSON headers shouldn't be automatically set for POST with no data.
        r = http('POST', httpbin('/post'))
        assert HTTP_OK in r
        assert '"Accept": "*/*"' in r
        assert '"Content-Type": "application/json' not in r

    def test_POST_with_data_auto_JSON_headers(self):
        r = http('POST', httpbin('/post'), 'a=b')
        assert HTTP_OK in r
        assert '"Accept": "application/json"' in r
        assert '"Content-Type": "application/json; charset=utf-8' in r

    def test_GET_with_data_auto_JSON_headers(self):
        # JSON headers should automatically be set also for GET with data.
        r = http('POST', httpbin('/post'), 'a=b')
        assert HTTP_OK in r
        assert '"Accept": "application/json"' in r, r
        assert '"Content-Type": "application/json; charset=utf-8' in r

    def test_POST_explicit_JSON_auto_JSON_accept(self):
        r = http('--json', 'POST', httpbin('/post'))
        assert HTTP_OK in r
        assert r.json['headers']['Accept'] == 'application/json'
        # Make sure Content-Type gets set even with no data.
        # https://github.com/jakubroztocil/httpie/issues/137
        assert 'application/json' in r.json['headers']['Content-Type']

    def test_GET_explicit_JSON_explicit_headers(self):
        r = http('--json', 'GET', httpbin('/headers'),
                 'Accept:application/xml',
                 'Content-Type:application/xml')
        assert HTTP_OK in r
        assert '"Accept": "application/xml"' in r
        assert '"Content-Type": "application/xml"' in r

    def test_POST_form_auto_Content_Type(self):
        r = http('--form', 'POST', httpbin('/post'))
        assert HTTP_OK in r
        assert '"Content-Type": "application/x-www-form-urlencoded' in r

    def test_POST_form_Content_Type_override(self):
        r = http('--form', 'POST', httpbin('/post'),
                 'Content-Type:application/xml')
        assert HTTP_OK in r
        assert '"Content-Type": "application/xml"' in r

    def test_print_only_body_when_stdout_redirected_by_default(self):
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('GET', httpbin('/get'), env=env)
        assert 'HTTP/' not in r

    def test_print_overridable_when_stdout_redirected(self):
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--print=h', 'GET', httpbin('/get'), env=env)
        assert HTTP_OK in r

########NEW FILE########
__FILENAME__ = test_docs
import os
import fnmatch
import subprocess

import pytest

from utils import TESTS_ROOT


def has_docutils():
    try:
        #noinspection PyUnresolvedReferences
        import docutils
        return True
    except ImportError:
        return False


def rst_filenames():
    for root, dirnames, filenames in os.walk(os.path.dirname(TESTS_ROOT)):
        if '.tox' not in root:
            for filename in fnmatch.filter(filenames, '*.rst'):
                yield os.path.join(root, filename)


filenames = list(rst_filenames())
assert filenames


@pytest.mark.skipif(not has_docutils(), reason='docutils not installed')
@pytest.mark.parametrize('filename', filenames)
def test_rst_file_syntax(filename):
    p = subprocess.Popen(
        ['rst2pseudoxml.py', '--report=1', '--exit-status=1', filename],
         stderr=subprocess.PIPE,
         stdout=subprocess.PIPE
    )
    err = p.communicate()[1]
    assert p.returncode == 0, err

########NEW FILE########
__FILENAME__ = test_downloads
import os
import time

import pytest
from requests.structures import CaseInsensitiveDict

from httpie.compat import urlopen
from httpie.downloads import (
    parse_content_range, filename_from_content_disposition, filename_from_url,
    get_unique_filename, ContentRangeError, Download,
)
from utils import httpbin, http, TestEnvironment


class Response(object):
    # noinspection PyDefaultArgument
    def __init__(self, url, headers={}, status_code=200):
        self.url = url
        self.headers = CaseInsensitiveDict(headers)
        self.status_code = status_code


class TestDownloadUtils:
    def test_Content_Range_parsing(self):
        parse = parse_content_range

        assert parse('bytes 100-199/200', 100) == 200
        assert parse('bytes 100-199/*', 100) == 200

        # missing
        pytest.raises(ContentRangeError, parse, None, 100)

        # syntax error
        pytest.raises(ContentRangeError, parse, 'beers 100-199/*', 100)

        # unexpected range
        pytest.raises(ContentRangeError, parse, 'bytes 100-199/*', 99)

        # invalid instance-length
        pytest.raises(ContentRangeError, parse, 'bytes 100-199/199', 100)

        # invalid byte-range-resp-spec
        pytest.raises(ContentRangeError, parse, 'bytes 100-99/199', 100)

        # invalid byte-range-resp-spec
        pytest.raises(ContentRangeError, parse, 'bytes 100-100/*', 100)

    @pytest.mark.parametrize('header, expected_filename', [
        ('attachment; filename=hello-WORLD_123.txt', 'hello-WORLD_123.txt'),
        ('attachment; filename=".hello-WORLD_123.txt"', 'hello-WORLD_123.txt'),
        ('attachment; filename="white space.txt"', 'white space.txt'),
        (r'attachment; filename="\"quotes\".txt"', '"quotes".txt'),
        ('attachment; filename=/etc/hosts', 'hosts'),
        ('attachment; filename=', None)
    ])
    def test_Content_Disposition_parsing(self, header, expected_filename):
        assert filename_from_content_disposition(header) == expected_filename

    def test_filename_from_url(self):
        assert 'foo.txt' == filename_from_url(
            url='http://example.org/foo',
            content_type='text/plain'
        )
        assert 'foo.html' == filename_from_url(
            url='http://example.org/foo',
            content_type='text/html; charset=utf8'
        )
        assert 'foo' == filename_from_url(
            url='http://example.org/foo',
            content_type=None
        )
        assert 'foo' == filename_from_url(
            url='http://example.org/foo',
            content_type='x-foo/bar'
        )

    def test_unique_filename(self):
        def attempts(unique_on_attempt=0):
            # noinspection PyUnresolvedReferences,PyUnusedLocal
            def exists(filename):
                if exists.attempt == unique_on_attempt:
                    return False
                exists.attempt += 1
                return True

            exists.attempt = 0
            return exists

        assert 'foo.bar' == get_unique_filename('foo.bar', attempts(0))
        assert 'foo.bar-1' == get_unique_filename('foo.bar', attempts(1))
        assert 'foo.bar-10' == get_unique_filename('foo.bar', attempts(10))


class TestDownloads:
    # TODO: more tests

    def test_actual_download(self):
        url = httpbin('/robots.txt')
        body = urlopen(url).read().decode()
        env = TestEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--download', url, env=env)
        assert 'Downloading' in r.stderr
        assert '[K' in r.stderr
        assert 'Done' in r.stderr
        assert body == r

    def test_download_with_Content_Length(self):
        devnull = open(os.devnull, 'w')
        download = Download(output_file=devnull, progress_file=devnull)
        download.start(Response(
            url=httpbin('/'),
            headers={'Content-Length': 10}
        ))
        time.sleep(1.1)
        download.chunk_downloaded(b'12345')
        time.sleep(1.1)
        download.chunk_downloaded(b'12345')
        download.finish()
        assert not download.interrupted

    def test_download_no_Content_Length(self):
        devnull = open(os.devnull, 'w')
        download = Download(output_file=devnull, progress_file=devnull)
        download.start(Response(url=httpbin('/')))
        time.sleep(1.1)
        download.chunk_downloaded(b'12345')
        download.finish()
        assert not download.interrupted

    def test_download_interrupted(self):
        devnull = open(os.devnull, 'w')
        download = Download(output_file=devnull, progress_file=devnull)
        download.start(Response(
            url=httpbin('/'),
            headers={'Content-Length': 5}
        ))
        download.chunk_downloaded(b'1234')
        download.finish()
        assert download.interrupted

########NEW FILE########
__FILENAME__ = test_exit_status
import requests
import pytest

from httpie import ExitStatus
from utils import TestEnvironment, http, httpbin, HTTP_OK


class TestExitStatus:
    def test_ok_response_exits_0(self):
        r = http('GET', httpbin('/status/200'))
        assert HTTP_OK in r
        assert r.exit_status == ExitStatus.OK

    def test_error_response_exits_0_without_check_status(self):
        r = http('GET', httpbin('/status/500'))
        assert 'HTTP/1.1 500' in r
        assert r.exit_status == ExitStatus.OK
        assert not r.stderr

    @pytest.mark.skipif(
        tuple(map(int, requests.__version__.split('.'))) < (2, 3, 0),
        reason='timeout broken in requests prior v2.3.0 (#185)'
    )
    def test_timeout_exit_status(self):

        r = http('--timeout=0.5', 'GET', httpbin('/delay/1'),
                 error_exit_ok=True)
        assert r.exit_status == ExitStatus.ERROR_TIMEOUT

    def test_3xx_check_status_exits_3_and_stderr_when_stdout_redirected(self):
        env = TestEnvironment(stdout_isatty=False)
        r = http('--check-status', '--headers', 'GET', httpbin('/status/301'),
                 env=env, error_exit_ok=True)
        assert 'HTTP/1.1 301' in r
        assert r.exit_status == ExitStatus.ERROR_HTTP_3XX
        assert '301 moved permanently' in r.stderr.lower()

    @pytest.mark.skipif(
        requests.__version__ == '0.13.6',
        reason='Redirects with prefetch=False are broken in Requests 0.13.6')
    def test_3xx_check_status_redirects_allowed_exits_0(self):
        r = http('--check-status', '--follow', 'GET', httpbin('/status/301'),
                 error_exit_ok=True)
        # The redirect will be followed so 200 is expected.
        assert 'HTTP/1.1 200 OK' in r
        assert r.exit_status == ExitStatus.OK

    def test_4xx_check_status_exits_4(self):
        r = http('--check-status', 'GET', httpbin('/status/401'),
                 error_exit_ok=True)
        assert 'HTTP/1.1 401' in r
        assert r.exit_status == ExitStatus.ERROR_HTTP_4XX
        # Also stderr should be empty since stdout isn't redirected.
        assert not r.stderr

    def test_5xx_check_status_exits_5(self):
        r = http('--check-status', 'GET', httpbin('/status/500'),
                 error_exit_ok=True)
        assert 'HTTP/1.1 500' in r
        assert r.exit_status == ExitStatus.ERROR_HTTP_5XX

########NEW FILE########
__FILENAME__ = test_httpie
"""High-level tests."""
from utils import TestEnvironment, http, httpbin, HTTP_OK
from fixtures import FILE_PATH, FILE_CONTENT
import httpie


class TestHTTPie:

    def test_debug(self):
        r = http('--debug')
        assert r.exit_status == httpie.ExitStatus.OK
        assert 'HTTPie %s' % httpie.__version__ in r.stderr
        assert 'HTTPie data:' in r.stderr

    def test_help(self):
        r = http('--help', error_exit_ok=True)
        assert r.exit_status == httpie.ExitStatus.ERROR
        assert 'https://github.com/jakubroztocil/httpie/issues' in r

    def test_version(self):
        r = http('--version', error_exit_ok=True)
        assert r.exit_status == httpie.ExitStatus.ERROR
        # FIXME: py3 has version in stdout, py2 in stderr
        assert httpie.__version__ == r.stderr.strip() + r.strip()

    def test_GET(self):
        r = http('GET', httpbin('/get'))
        assert HTTP_OK in r

    def test_DELETE(self):
        r = http('DELETE', httpbin('/delete'))
        assert HTTP_OK in r

    def test_PUT(self):
        r = http('PUT', httpbin('/put'), 'foo=bar')
        assert HTTP_OK in r
        assert r'\"foo\": \"bar\"' in r

    def test_POST_JSON_data(self):
        r = http('POST', httpbin('/post'), 'foo=bar')
        assert HTTP_OK in r
        assert r'\"foo\": \"bar\"' in r

    def test_POST_form(self):
        r = http('--form', 'POST', httpbin('/post'), 'foo=bar')
        assert HTTP_OK in r
        assert '"foo": "bar"' in r

    def test_POST_form_multiple_values(self):
        r = http('--form', 'POST', httpbin('/post'), 'foo=bar', 'foo=baz')
        assert HTTP_OK in r
        assert r.json['form'] == {'foo': ['bar', 'baz']}

    def test_POST_stdin(self):
        with open(FILE_PATH) as f:
            env = TestEnvironment(stdin=f, stdin_isatty=False)
            r = http('--form', 'POST', httpbin('/post'), env=env)
        assert HTTP_OK in r
        assert FILE_CONTENT in r

    def test_headers(self):
        r = http('GET', httpbin('/headers'), 'Foo:bar')
        assert HTTP_OK in r
        assert '"User-Agent": "HTTPie' in r, r
        assert '"Foo": "bar"' in r

########NEW FILE########
__FILENAME__ = test_output
import pytest

from httpie import ExitStatus
from httpie.output.formatters.colors import get_lexer
from utils import TestEnvironment, http, httpbin, HTTP_OK, COLOR, CRLF


class TestVerboseFlag:
    def test_verbose(self):
        r = http('--verbose', 'GET', httpbin('/get'), 'test-header:__test__')
        assert HTTP_OK in r
        assert r.count('__test__') == 2

    def test_verbose_form(self):
        # https://github.com/jakubroztocil/httpie/issues/53
        r = http('--verbose', '--form', 'POST', httpbin('/post'),
                 'A=B', 'C=D')
        assert HTTP_OK in r
        assert 'A=B&C=D' in r

    def test_verbose_json(self):
        r = http('--verbose', 'POST', httpbin('/post'), 'foo=bar', 'baz=bar')
        assert HTTP_OK in r
        assert '"baz": "bar"' in r  # request
        assert r'\"baz\": \"bar\"' in r  # response


class TestColors:

    @pytest.mark.parametrize('mime', [
        'application/json',
        'application/json+foo',
        'application/foo+json',
        'foo/json',
        'foo/json+bar',
        'foo/bar+json',
    ])
    def test_get_lexer(self, mime):
        lexer = get_lexer(mime)
        assert lexer is not None
        assert lexer.name == 'JSON'

    def test_get_lexer_not_found(self):
        assert get_lexer('xxx/yyy') is None


class TestPrettyOptions:
    """Test the --pretty flag handling."""

    def test_pretty_enabled_by_default(self):
        env = TestEnvironment(colors=256)
        r = http('GET', httpbin('/get'), env=env)
        assert COLOR in r

    def test_pretty_enabled_by_default_unless_stdout_redirected(self):
        r = http('GET', httpbin('/get'))
        assert COLOR not in r

    def test_force_pretty(self):
        env = TestEnvironment(stdout_isatty=False, colors=256)
        r = http('--pretty=all', 'GET', httpbin('/get'), env=env, )
        assert COLOR in r

    def test_force_ugly(self):
        r = http('--pretty=none', 'GET', httpbin('/get'))
        assert COLOR not in r

    def test_subtype_based_pygments_lexer_match(self):
        """Test that media subtype is used if type/subtype doesn't
        match any lexer.

        """
        env = TestEnvironment(colors=256)
        r = http('--print=B', '--pretty=all', httpbin('/post'),
                 'Content-Type:text/foo+json', 'a=b', env=env)
        assert COLOR in r

    def test_colors_option(self):
        env = TestEnvironment(colors=256)
        r = http('--print=B', '--pretty=colors', 'GET', httpbin('/get'), 'a=b',
                 env=env)
        # Tests that the JSON data isn't formatted.
        assert not r.strip().count('\n')
        assert COLOR in r

    def test_format_option(self):
        env = TestEnvironment(colors=256)
        r = http('--print=B', '--pretty=format', 'GET', httpbin('/get'), 'a=b',
                 env=env)
        # Tests that the JSON data is formatted.
        assert r.strip().count('\n') == 2
        assert COLOR not in r


class TestLineEndings:
    """
    Test that CRLF is properly used in headers
    and as the headers/body separator.

    """
    def _validate_crlf(self, msg):
        lines = iter(msg.splitlines(True))
        for header in lines:
            if header == CRLF:
                break
            assert header.endswith(CRLF), repr(header)
        else:
            assert 0, 'CRLF between headers and body not found in %r' % msg
        body = ''.join(lines)
        assert CRLF not in body
        return body

    def test_CRLF_headers_only(self):
        r = http('--headers', 'GET', httpbin('/get'))
        body = self._validate_crlf(r)
        assert not body, 'Garbage after headers: %r' % r

    def test_CRLF_ugly_response(self):
        r = http('--pretty=none', 'GET', httpbin('/get'))
        self._validate_crlf(r)

    def test_CRLF_formatted_response(self):
        r = http('--pretty=format', 'GET', httpbin('/get'))
        assert r.exit_status == ExitStatus.OK
        self._validate_crlf(r)

    def test_CRLF_ugly_request(self):
        r = http('--pretty=none', '--print=HB', 'GET', httpbin('/get'))
        self._validate_crlf(r)

    def test_CRLF_formatted_request(self):
        r = http('--pretty=format', '--print=HB', 'GET', httpbin('/get'))
        self._validate_crlf(r)

########NEW FILE########
__FILENAME__ = test_sessions
# coding=utf-8
import os
import shutil

from httpie.plugins.builtin import HTTPBasicAuth
from utils import TestEnvironment, mk_config_dir, http, httpbin, HTTP_OK
from fixtures import UNICODE


class SessionTestBase(object):
    def setup_method(self, method):
        """Create and reuse a unique config dir for each test."""
        self.config_dir = mk_config_dir()

    def teardown_method(self, method):
        shutil.rmtree(self.config_dir)

    def env(self):
        """
        Return an environment.

        Each environment created withing a test method
        will share the same config_dir. It is necessary
        for session files being reused.

        """
        return TestEnvironment(config_dir=self.config_dir)


class TestSessionFlow(SessionTestBase):
    """
    These tests start with an existing session created in `setup_method()`.

    """

    def setup_method(self, method):
        """
        Start a full-blown session with a custom request header,
        authorization, and response cookies.

        """
        super(TestSessionFlow, self).setup_method(method)
        r1 = http('--follow', '--session=test', '--auth=username:password',
                  'GET', httpbin('/cookies/set?hello=world'), 'Hello:World',
                  env=self.env())
        assert HTTP_OK in r1

    def test_session_created_and_reused(self):
        # Verify that the session created in setup_method() has been used.
        r2 = http('--session=test', 'GET', httpbin('/get'), env=self.env())
        assert HTTP_OK in r2
        assert r2.json['headers']['Hello'] == 'World'
        assert r2.json['headers']['Cookie'] == 'hello=world'
        assert 'Basic ' in r2.json['headers']['Authorization']

    def test_session_update(self):
        # Get a response to a request from the original session.
        r2 = http('--session=test', 'GET', httpbin('/get'), env=self.env())
        assert HTTP_OK in r2

        # Make a request modifying the session data.
        r3 = http('--follow', '--session=test', '--auth=username:password2',
                  'GET', httpbin('/cookies/set?hello=world2'), 'Hello:World2',
                  env=self.env())
        assert HTTP_OK in r3

        # Get a response to a request from the updated session.
        r4 = http('--session=test', 'GET', httpbin('/get'), env=self.env())
        assert HTTP_OK in r4
        assert r4.json['headers']['Hello'] == 'World2'
        assert r4.json['headers']['Cookie'] == 'hello=world2'
        assert (r2.json['headers']['Authorization'] !=
                r4.json['headers']['Authorization'])

    def test_session_read_only(self):
        # Get a response from the original session.
        r2 = http('--session=test', 'GET', httpbin('/get'), env=self.env())
        assert HTTP_OK in r2

        # Make a request modifying the session data but
        # with --session-read-only.
        r3 = http('--follow', '--session-read-only=test',
                  '--auth=username:password2', 'GET',
                  httpbin('/cookies/set?hello=world2'), 'Hello:World2',
                  env=self.env())
        assert HTTP_OK in r3

        # Get a response from the updated session.
        r4 = http('--session=test', 'GET', httpbin('/get'), env=self.env())
        assert HTTP_OK in r4

        # Origin can differ on Travis.
        del r2.json['origin'], r4.json['origin']
        # Different for each request.
        del r2.json['headers']['X-Request-Id']
        del r4.json['headers']['X-Request-Id']

        # Should be the same as before r3.
        assert r2.json == r4.json


class TestSession(SessionTestBase):
    """Stand-alone session tests."""

    def test_session_ignored_header_prefixes(self):
        r1 = http('--session=test', 'GET', httpbin('/get'),
                  'Content-Type: text/plain',
                  'If-Unmodified-Since: Sat, 29 Oct 1994 19:43:31 GMT',
                  env=self.env())
        assert HTTP_OK in r1

        r2 = http('--session=test', 'GET', httpbin('/get'), env=self.env())
        assert HTTP_OK in r2
        assert 'Content-Type' not in r2.json['headers']
        assert 'If-Unmodified-Since' not in r2.json['headers']

    def test_session_by_path(self):
        session_path = os.path.join(self.config_dir, 'session-by-path.json')
        r1 = http('--session=' + session_path, 'GET', httpbin('/get'),
                  'Foo:Bar', env=self.env())
        assert HTTP_OK in r1

        r2 = http('--session=' + session_path, 'GET', httpbin('/get'),
                  env=self.env())
        assert HTTP_OK in r2
        assert r2.json['headers']['Foo'] == 'Bar'

    def test_session_unicode(self):
        r1 = http('--session=test', '--auth', u'test:' + UNICODE,
                  'GET', httpbin('/get'),
                  u'Test:%s' % UNICODE,
                  env=self.env())
        assert HTTP_OK in r1

        r2 = http('--session=test', 'GET', httpbin('/get'), env=self.env())
        assert HTTP_OK in r2
        assert (r2.json['headers']['Authorization']
                == HTTPBasicAuth.make_header(u'test', UNICODE))
        assert r2.json['headers']['Test'] == UNICODE

    def test_session_default_header_value_overwritten(self):
        # https://github.com/jakubroztocil/httpie/issues/180
        r1 = http('--session=test', httpbin('/headers'), 'User-Agent:custom',
                  env=self.env())
        assert HTTP_OK in r1
        assert r1.json['headers']['User-Agent'] == 'custom'

        r2 = http('--session=test', httpbin('/headers'), env=self.env())
        assert HTTP_OK in r2
        assert r2.json['headers']['User-Agent'] == 'custom'

########NEW FILE########
__FILENAME__ = test_stream
import pytest

from httpie.compat import is_windows
from httpie.output.streams import BINARY_SUPPRESSED_NOTICE
from utils import http, httpbin, TestEnvironment
from fixtures import BIN_FILE_CONTENT, BIN_FILE_PATH


class TestStream:
    # GET because httpbin 500s with binary POST body.

    @pytest.mark.skipif(is_windows,
                        reason='Pretty redirect not supported under Windows')
    def test_pretty_redirected_stream(self):
        """Test that --stream works with prettified redirected output."""
        with open(BIN_FILE_PATH, 'rb') as f:
            env = TestEnvironment(colors=256, stdin=f,
                                  stdin_isatty=False,
                                  stdout_isatty=False)
            r = http('--verbose', '--pretty=all', '--stream', 'GET',
                     httpbin('/get'), env=env)
        assert BINARY_SUPPRESSED_NOTICE.decode() in r

    def test_encoded_stream(self):
        """Test that --stream works with non-prettified
        redirected terminal output."""
        with open(BIN_FILE_PATH, 'rb') as f:
            env = TestEnvironment(stdin=f, stdin_isatty=False)
            r = http('--pretty=none', '--stream', '--verbose', 'GET',
                     httpbin('/get'), env=env)
        assert BINARY_SUPPRESSED_NOTICE.decode() in r

    def test_redirected_stream(self):
        """Test that --stream works with non-prettified
        redirected terminal output."""
        with open(BIN_FILE_PATH, 'rb') as f:
            env = TestEnvironment(stdout_isatty=False,
                                  stdin_isatty=False,
                                  stdin=f)
            r = http('--pretty=none', '--stream', '--verbose', 'GET',
                     httpbin('/get'), env=env)
        assert BIN_FILE_CONTENT in r

########NEW FILE########
__FILENAME__ = test_unicode
# coding=utf-8
"""
Various unicode handling related tests.

"""
from utils import http, httpbin, HTTP_OK
from fixtures import UNICODE


class TestUnicode:

    def test_unicode_headers(self):
        r = http(httpbin('/headers'), u'Test:%s' % UNICODE)
        assert HTTP_OK in r
        assert r.json['headers']['Test'] == UNICODE

    def test_unicode_headers_verbose(self):
        r = http('--verbose', httpbin('/headers'), u'Test:%s' % UNICODE)
        assert HTTP_OK in r
        assert UNICODE in r

    def test_unicode_form_item(self):
        r = http('--form', 'POST', httpbin('/post'), u'test=%s' % UNICODE)
        assert HTTP_OK in r
        assert r.json['form'] == {'test': UNICODE}

    def test_unicode_form_item_verbose(self):
        r = http('--verbose', '--form',
                 'POST', httpbin('/post'), u'test=%s' % UNICODE)
        assert HTTP_OK in r
        assert UNICODE in r

    def test_unicode_json_item(self):
        r = http('--json', 'POST', httpbin('/post'), u'test=%s' % UNICODE)
        assert HTTP_OK in r
        assert r.json['json'] == {'test': UNICODE}

    def test_unicode_json_item_verbose(self):
        r = http('--verbose', '--json',
                 'POST', httpbin('/post'), u'test=%s' % UNICODE)
        assert HTTP_OK in r
        assert UNICODE in r

    def test_unicode_raw_json_item(self):
        r = http('--json', 'POST', httpbin('/post'),
                 u'test:={ "%s" : [ "%s" ] }' % (UNICODE, UNICODE))
        assert HTTP_OK in r
        assert r.json['json'] == {'test': {UNICODE: [UNICODE]}}

    def test_unicode_raw_json_item_verbose(self):
        r = http('--json', 'POST', httpbin('/post'),
                 u'test:={ "%s" : [ "%s" ] }' % (UNICODE, UNICODE))
        assert HTTP_OK in r
        assert r.json['json'] == {'test': {UNICODE: [UNICODE]}}

    def test_unicode_url_query_arg_item(self):
        r = http(httpbin('/get'), u'test==%s' % UNICODE)
        assert HTTP_OK in r
        assert r.json['args'] == {'test': UNICODE}, r

    def test_unicode_url_query_arg_item_verbose(self):
        r = http('--verbose', httpbin('/get'), u'test==%s' % UNICODE)
        assert HTTP_OK in r
        assert UNICODE in r

    def test_unicode_url(self):
        r = http(httpbin(u'/get?test=' + UNICODE))
        assert HTTP_OK in r
        assert r.json['args'] == {'test': UNICODE}

    # def test_unicode_url_verbose(self):
    #     r = http(httpbin('--verbose', u'/get?test=' + UNICODE))
    #     assert HTTP_OK in r

    def test_unicode_basic_auth(self):
        # it doesn't really authenticate us because httpbin
        # doesn't interpret the utf8-encoded auth
        http('--verbose', '--auth', u'test:%s' % UNICODE,
             httpbin(u'/basic-auth/test/' + UNICODE))

    def test_unicode_digest_auth(self):
        # it doesn't really authenticate us because httpbin
        # doesn't interpret the utf8-encoded auth
        http('--auth-type=digest',
             '--auth', u'test:%s' % UNICODE,
             httpbin(u'/digest-auth/auth/test/' + UNICODE))

########NEW FILE########
__FILENAME__ = test_uploads
import os

import pytest

from httpie.input import ParseError
from utils import TestEnvironment, http, httpbin, HTTP_OK
from fixtures import FILE_PATH_ARG, FILE_PATH, FILE_CONTENT


class TestMultipartFormDataFileUpload:
    def test_non_existent_file_raises_parse_error(self):
        with pytest.raises(ParseError):
            http('--form', 'POST', httpbin('/post'), 'foo@/__does_not_exist__')

    def test_upload_ok(self):
        r = http('--form', '--verbose', 'POST', httpbin('/post'),
                 'test-file@%s' % FILE_PATH_ARG, 'foo=bar')
        assert HTTP_OK in r
        assert 'Content-Disposition: form-data; name="foo"' in r
        assert 'Content-Disposition: form-data; name="test-file";' \
               ' filename="%s"' % os.path.basename(FILE_PATH) in r
        assert r.count(FILE_CONTENT) == 2
        assert '"foo": "bar"' in r


class TestRequestBodyFromFilePath:
    """
    `http URL @file'

    """

    def test_request_body_from_file_by_path(self):
        r = http('--verbose', 'POST', httpbin('/post'), '@' + FILE_PATH_ARG)
        assert HTTP_OK in r
        assert FILE_CONTENT in r, r
        assert '"Content-Type": "text/plain"' in r

    def test_request_body_from_file_by_path_with_explicit_content_type(self):
        r = http('POST', httpbin('/post'), '@' + FILE_PATH_ARG,
                 'Content-Type:x-foo/bar')
        assert HTTP_OK in r
        assert FILE_CONTENT in r
        assert '"Content-Type": "x-foo/bar"' in r

    def test_request_body_from_file_by_path_no_field_name_allowed(self):
        env = TestEnvironment(stdin_isatty=True)
        r = http('POST', httpbin('/post'), 'field-name@' + FILE_PATH_ARG,
                 env=env, error_exit_ok=True)
        assert 'perhaps you meant --form?' in r.stderr

    def test_request_body_from_file_by_path_no_data_items_allowed(self):
        env = TestEnvironment(stdin_isatty=False)
        r = http('POST', httpbin('/post'), '@' + FILE_PATH_ARG, 'foo=bar',
                 env=env, error_exit_ok=True)
        assert 'cannot be mixed' in r.stderr

########NEW FILE########
__FILENAME__ = test_windows
import os
import tempfile

import pytest
from httpie.context import Environment

from utils import TestEnvironment, http, httpbin
from httpie.compat import is_windows


@pytest.mark.skipif(not is_windows, reason='windows-only')
class TestWindowsOnly:

    @pytest.mark.skipif(True,
                        reason='this test for some reason kills the process')
    def test_windows_colorized_output(self):
        # Spits out the colorized output.
        http(httpbin('/get'), env=Environment())


class TestFakeWindows:
    def test_output_file_pretty_not_allowed_on_windows(self):
        env = TestEnvironment(is_windows=True)
        output_file = os.path.join(
            tempfile.gettempdir(), '__httpie_test_output__')
        r = http('--output', output_file,
                 '--pretty=all', 'GET', httpbin('/get'),
                 env=env, error_exit_ok=True)
        assert 'Only terminal output can be colorized on Windows' in r.stderr

########NEW FILE########
__FILENAME__ = utils
# coding=utf-8
"""Utilities used by HTTPie tests.

"""
import os
import sys
import time
import json
import shutil
import tempfile

import httpie
from httpie.context import Environment
from httpie.core import main
from httpie.compat import bytes, str


TESTS_ROOT = os.path.abspath(os.path.dirname(__file__))


CRLF = '\r\n'
COLOR = '\x1b['
HTTP_OK = 'HTTP/1.1 200'
HTTP_OK_COLOR = (
    'HTTP\x1b[39m\x1b[38;5;245m/\x1b[39m\x1b'
    '[38;5;37m1.1\x1b[39m\x1b[38;5;245m \x1b[39m\x1b[38;5;37m200'
    '\x1b[39m\x1b[38;5;245m \x1b[39m\x1b[38;5;136mOK'
)


def httpbin(path, auth=None,
            base=os.environ.get('HTTPBIN_URL', 'http://httpbin.org')):
    """
    Return a fully-qualified httpbin URL for `path`.

    >>> httpbin('/get')
    'http://httpbin.org/get'

    >>> httpbin('/get', auth='user:password')
    'http://user:password@httpbin.org/get'

    """
    if auth:
        proto, rest = base.split('://', 1)
        base = proto + '://' + auth + '@' + rest
    return base.rstrip('/') + path


class TestEnvironment(Environment):
    """
    Environment subclass with reasonable defaults suitable for testing.

    """
    colors = 0
    stdin_isatty = True,
    stdout_isatty = True
    is_windows = False

    _shutil = shutil  # needed by __del__ (would get gc'd)

    def __init__(self, **kwargs):

        if 'stdout' not in kwargs:
            kwargs['stdout'] = tempfile.TemporaryFile('w+b')

        if 'stderr' not in kwargs:
            kwargs['stderr'] = tempfile.TemporaryFile('w+t')

        self.delete_config_dir = False
        if 'config_dir' not in kwargs:
            kwargs['config_dir'] = mk_config_dir()
            self.delete_config_dir = True

        super(TestEnvironment, self).__init__(**kwargs)

    def __del__(self):
        if self.delete_config_dir:
            self._shutil.rmtree(self.config_dir)


def http(*args, **kwargs):
    """
    Run HTTPie and capture stderr/out and exit status.

    Invoke `httpie.core.main()` with `args` and `kwargs`,
    and return a `CLIResponse` subclass instance.

    The return value is either a `StrCLIResponse`, or `BytesCLIResponse`
    if unable to decode the output.

    The response has the following attributes:

        `stdout` is represented by the instance itself (print r)
        `stderr`: text written to stderr
        `exit_status`: the exit status
        `json`: decoded JSON (if possible) or `None`

    Exceptions are propagated.

    If you pass ``error_exit_ok=True``, then error exit statuses
    won't result into an exception.

    Example:

    $ http --auth=user:password GET httpbin.org/basic-auth/user/password

        >>> r = http('-a', 'user:pw', httpbin('/basic-auth/user/pw'))
        >>> type(r) == StrCLIResponse
        True
        >>> r.exit_status
        0
        >>> r.stderr
        ''
        >>> 'HTTP/1.1 200 OK' in r
        True
        >>> r.json == {'authenticated': True, 'user': 'user'}
        True


    """
    error_exit_ok = kwargs.pop('error_exit_ok', False)
    env = kwargs.get('env')
    if not env:
        env = kwargs['env'] = TestEnvironment()

    stdout = env.stdout
    stderr = env.stderr

    args = list(args)
    if '--debug' not in args and '--traceback' not in args:
        args = ['--traceback'] + args

    def dump_stderr():
        stderr.seek(0)
        sys.stderr.write(stderr.read())

    try:
        try:
            exit_status = main(args=args, **kwargs)
            if '--download' in args:
                # Let the progress reporter thread finish.
                time.sleep(.5)
        except SystemExit:
            if error_exit_ok:
                exit_status = httpie.ExitStatus.ERROR
            else:
                dump_stderr()
                raise
        except Exception:
            stderr.seek(0)
            sys.stderr.write(stderr.read())
            raise
        else:
            if exit_status != httpie.ExitStatus.OK and not error_exit_ok:
                dump_stderr()
                raise Exception('Unexpected exit status: %s', exit_status)

        stdout.seek(0)
        stderr.seek(0)
        output = stdout.read()
        try:
            output = output.decode('utf8')
        except UnicodeDecodeError:
            # noinspection PyArgumentList
            r = BytesCLIResponse(output)
        else:
            # noinspection PyArgumentList
            r = StrCLIResponse(output)
        r.stderr = stderr.read()
        r.exit_status = exit_status

        if r.exit_status != httpie.ExitStatus.OK:
            sys.stderr.write(r.stderr)

        return r

    finally:
        stdout.close()
        stderr.close()


class BaseCLIResponse(object):
    """
    Represents the result of simulated `$ http' invocation  via `http()`.

    Holds and provides access to:

        - stdout output: print(self)
        - stderr output: print(self.stderr)
        - exit_status output: print(self.exit_status)

    """
    stderr = None
    json = None
    exit_status = None


class BytesCLIResponse(bytes, BaseCLIResponse):
    """
    Used as a fallback when a StrCLIResponse cannot be used.

    E.g. when the output contains binary data or when it is colorized.

    `.json` will always be None.

    """


class StrCLIResponse(str, BaseCLIResponse):

    @property
    def json(self):
        """
        Return deserialized JSON body, if one included in the output
        and is parseable.

        """
        if not hasattr(self, '_json'):
            self._json = None
            # De-serialize JSON body if possible.
            if COLOR in self:
                # Colorized output cannot be parsed.
                pass
            elif self.strip().startswith('{'):
                # Looks like JSON body.
                self._json = json.loads(self)
            elif (self.count('Content-Type:') == 1
                    and 'application/json' in self):
                # Looks like a whole JSON HTTP message,
                # try to extract its body.
                try:
                    j = self.strip()[self.strip().rindex('\r\n\r\n'):]
                except ValueError:
                    pass
                else:
                    try:
                        self._json = json.loads(j)
                    except ValueError:
                        pass
        return self._json


def mk_config_dir():
    return tempfile.mkdtemp(prefix='httpie_test_config_dir_')

########NEW FILE########
