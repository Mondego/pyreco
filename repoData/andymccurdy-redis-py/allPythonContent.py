__FILENAME__ = base
import functools
import itertools
import redis
import sys
import timeit
from redis._compat import izip


class Benchmark(object):
    ARGUMENTS = ()

    def __init__(self):
        self._client = None

    def get_client(self, **kwargs):
        # eventually make this more robust and take optional args from
        # argparse
        if self._client is None or kwargs:
            defaults = {
                'db': 9
            }
            defaults.update(kwargs)
            pool = redis.ConnectionPool(**kwargs)
            self._client = redis.StrictRedis(connection_pool=pool)
        return self._client

    def setup(self, **kwargs):
        pass

    def run(self, **kwargs):
        pass

    def run_benchmark(self):
        group_names = [group['name'] for group in self.ARGUMENTS]
        group_values = [group['values'] for group in self.ARGUMENTS]
        for value_set in itertools.product(*group_values):
            pairs = list(izip(group_names, value_set))
            arg_string = ', '.join(['%s=%s' % (p[0], p[1]) for p in pairs])
            sys.stdout.write('Benchmark: %s... ' % arg_string)
            sys.stdout.flush()
            kwargs = dict(pairs)
            setup = functools.partial(self.setup, **kwargs)
            run = functools.partial(self.run, **kwargs)
            t = timeit.timeit(stmt=run, setup=setup, number=1000)
            sys.stdout.write('%f\n' % t)
            sys.stdout.flush()

########NEW FILE########
__FILENAME__ = command_packer_benchmark
import socket
import sys
from redis.connection import (Connection, SYM_STAR, SYM_DOLLAR, SYM_EMPTY,
                              SYM_CRLF, b)
from redis._compat import imap
from base import Benchmark


class StringJoiningConnection(Connection):
    def send_packed_command(self, command):
        "Send an already packed command to the Redis server"
        if not self._sock:
            self.connect()
        try:
            self._sock.sendall(command)
        except socket.error:
            e = sys.exc_info()[1]
            self.disconnect()
            if len(e.args) == 1:
                _errno, errmsg = 'UNKNOWN', e.args[0]
            else:
                _errno, errmsg = e.args
            raise ConnectionError("Error %s while writing to socket. %s." %
                                  (_errno, errmsg))
        except:
            self.disconnect()
            raise

    def pack_command(self, *args):
        "Pack a series of arguments into a value Redis command"
        args_output = SYM_EMPTY.join([
            SYM_EMPTY.join((SYM_DOLLAR, b(str(len(k))), SYM_CRLF, k, SYM_CRLF))
            for k in imap(self.encode, args)])
        output = SYM_EMPTY.join(
            (SYM_STAR, b(str(len(args))), SYM_CRLF, args_output))
        return output


class ListJoiningConnection(Connection):
    def send_packed_command(self, command):
        if not self._sock:
            self.connect()
        try:
            if isinstance(command, str):
                command = [command]
            for item in command:
                self._sock.sendall(item)
        except socket.error:
            e = sys.exc_info()[1]
            self.disconnect()
            if len(e.args) == 1:
                _errno, errmsg = 'UNKNOWN', e.args[0]
            else:
                _errno, errmsg = e.args
            raise ConnectionError("Error %s while writing to socket. %s." %
                                  (_errno, errmsg))
        except:
            self.disconnect()
            raise

    def pack_command(self, *args):
        output = []
        buff = SYM_EMPTY.join(
            (SYM_STAR, b(str(len(args))), SYM_CRLF))

        for k in imap(self.encode, args):
            if len(buff) > 6000 or len(k) > 6000:
                buff = SYM_EMPTY.join(
                    (buff, SYM_DOLLAR, b(str(len(k))), SYM_CRLF))
                output.append(buff)
                output.append(k)
                buff = SYM_CRLF
            else:
                buff = SYM_EMPTY.join((buff, SYM_DOLLAR, b(str(len(k))),
                                       SYM_CRLF, k, SYM_CRLF))
        output.append(buff)
        return output


class CommandPackerBenchmark(Benchmark):

    ARGUMENTS = (
        {
            'name': 'connection_class',
            'values': [StringJoiningConnection, ListJoiningConnection]
        },
        {
            'name': 'value_size',
            'values': [10, 100, 1000, 10000, 100000, 1000000, 10000000,
                       100000000]
        },
    )

    def setup(self, connection_class, value_size):
        self.get_client(connection_class=connection_class)

    def run(self, connection_class, value_size):
        r = self.get_client()
        x = 'a' * value_size
        r.set('benchmark', x)


if __name__ == '__main__':
    CommandPackerBenchmark().run_benchmark()

########NEW FILE########
__FILENAME__ = socket_read_size
from redis.connection import PythonParser, HiredisParser
from base import Benchmark


class SocketReadBenchmark(Benchmark):

    ARGUMENTS = (
        {
            'name': 'parser',
            'values': [PythonParser, HiredisParser]
        },
        {
            'name': 'value_size',
            'values': [10, 100, 1000, 10000, 100000, 1000000, 10000000,
                       100000000]
        },
        {
            'name': 'read_size',
            'values': [4096, 8192, 16384, 32768, 65536, 131072]
        }
    )

    def setup(self, value_size, read_size, parser):
        r = self.get_client(parser_class=parser,
                            socket_read_size=read_size)
        r.set('benchmark', 'a' * value_size)

    def run(self, value_size, read_size, parser):
        r = self.get_client()
        r.get('benchmark')


if __name__ == '__main__':
    SocketReadBenchmark().run_benchmark()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# redis-py documentation build configuration file, created by
# sphinx-quickstart on Fri Feb  8 00:47:08 2013.
#
# This file is execfile()d with the current directory set to its containing
# dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
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
project = u'redis-py'
copyright = u'2013, Andy McCurdy, Mahdi Yusuf'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.7.2'
# The full version, including alpha/beta/rc tags.
release = '2.7.2'

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


# -- Options for HTML output --------------------------------------------------

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
htmlhelp_basename = 'redis-pydoc'


# -- Options for LaTeX output -------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index', 'redis-py.tex', u'redis-py Documentation',
     u'Andy McCurdy, Mahdi Yusuf', 'manual'),
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


# -- Options for manual page output -------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'redis-py', u'redis-py Documentation',
     [u'Andy McCurdy, Mahdi Yusuf'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'redis-py', u'redis-py Documentation',
     u'Andy McCurdy, Mahdi Yusuf', 'redis-py',
     'One line description of project.', 'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = client
from __future__ import with_statement
from itertools import chain, starmap
import datetime
import sys
import warnings
import threading
import time as mod_time
from redis._compat import (b, basestring, bytes, imap, iteritems, iterkeys,
                           itervalues, izip, long, nativestr, unicode)
from redis.connection import (ConnectionPool, UnixDomainSocketConnection,
                              SSLConnection, Token)
from redis.exceptions import (
    ConnectionError,
    DataError,
    ExecAbortError,
    NoScriptError,
    PubSubError,
    RedisError,
    ResponseError,
    TimeoutError,
    WatchError,
)

SYM_EMPTY = b('')


def list_or_args(keys, args):
    # returns a single list combining keys and args
    try:
        iter(keys)
        # a string or bytes instance can be iterated, but indicates
        # keys wasn't passed as a list
        if isinstance(keys, (basestring, bytes)):
            keys = [keys]
    except TypeError:
        keys = [keys]
    if args:
        keys.extend(args)
    return keys


def timestamp_to_datetime(response):
    "Converts a unix timestamp to a Python datetime object"
    if not response:
        return None
    try:
        response = int(response)
    except ValueError:
        return None
    return datetime.datetime.fromtimestamp(response)


def string_keys_to_dict(key_string, callback):
    return dict.fromkeys(key_string.split(), callback)


def dict_merge(*dicts):
    merged = {}
    [merged.update(d) for d in dicts]
    return merged


def parse_debug_object(response):
    "Parse the results of Redis's DEBUG OBJECT command into a Python dict"
    # The 'type' of the object is the first item in the response, but isn't
    # prefixed with a name
    response = nativestr(response)
    response = 'type:' + response
    response = dict([kv.split(':') for kv in response.split()])

    # parse some expected int values from the string response
    # note: this cmd isn't spec'd so these may not appear in all redis versions
    int_fields = ('refcount', 'serializedlength', 'lru', 'lru_seconds_idle')
    for field in int_fields:
        if field in response:
            response[field] = int(response[field])

    return response


def parse_object(response, infotype):
    "Parse the results of an OBJECT command"
    if infotype in ('idletime', 'refcount'):
        return int_or_none(response)
    return response


def parse_info(response):
    "Parse the result of Redis's INFO command into a Python dict"
    info = {}
    response = nativestr(response)

    def get_value(value):
        if ',' not in value or '=' not in value:
            try:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                return value
        else:
            sub_dict = {}
            for item in value.split(','):
                k, v = item.rsplit('=', 1)
                sub_dict[k] = get_value(v)
            return sub_dict

    for line in response.splitlines():
        if line and not line.startswith('#'):
            if line.find(':') != -1:
                key, value = line.split(':', 1)
                info[key] = get_value(value)
            else:
                # if the line isn't splittable, append it to the "__raw__" key
                info.setdefault('__raw__', []).append(line)

    return info


SENTINEL_STATE_TYPES = {
    'can-failover-its-master': int,
    'config-epoch': int,
    'down-after-milliseconds': int,
    'failover-timeout': int,
    'info-refresh': int,
    'last-hello-message': int,
    'last-ok-ping-reply': int,
    'last-ping-reply': int,
    'last-ping-sent': int,
    'master-link-down-time': int,
    'master-port': int,
    'num-other-sentinels': int,
    'num-slaves': int,
    'o-down-time': int,
    'pending-commands': int,
    'parallel-syncs': int,
    'port': int,
    'quorum': int,
    'role-reported-time': int,
    's-down-time': int,
    'slave-priority': int,
    'slave-repl-offset': int,
    'voted-leader-epoch': int
}


def parse_sentinel_state(item):
    result = pairs_to_dict_typed(item, SENTINEL_STATE_TYPES)
    flags = set(result['flags'].split(','))
    for name, flag in (('is_master', 'master'), ('is_slave', 'slave'),
                       ('is_sdown', 's_down'), ('is_odown', 'o_down'),
                       ('is_sentinel', 'sentinel'),
                       ('is_disconnected', 'disconnected'),
                       ('is_master_down', 'master_down')):
        result[name] = flag in flags
    return result


def parse_sentinel_master(response):
    return parse_sentinel_state(imap(nativestr, response))


def parse_sentinel_masters(response):
    result = {}
    for item in response:
        state = parse_sentinel_state(imap(nativestr, item))
        result[state['name']] = state
    return result


def parse_sentinel_slaves_and_sentinels(response):
    return [parse_sentinel_state(imap(nativestr, item)) for item in response]


def parse_sentinel_get_master(response):
    return response and (response[0], int(response[1])) or None


def pairs_to_dict(response):
    "Create a dict given a list of key/value pairs"
    it = iter(response)
    return dict(izip(it, it))


def pairs_to_dict_typed(response, type_info):
    it = iter(response)
    result = {}
    for key, value in izip(it, it):
        if key in type_info:
            try:
                value = type_info[key](value)
            except:
                # if for some reason the value can't be coerced, just use
                # the string value
                pass
        result[key] = value
    return result


def zset_score_pairs(response, **options):
    """
    If ``withscores`` is specified in the options, return the response as
    a list of (value, score) pairs
    """
    if not response or not options['withscores']:
        return response
    score_cast_func = options.get('score_cast_func', float)
    it = iter(response)
    return list(izip(it, imap(score_cast_func, it)))


def sort_return_tuples(response, **options):
    """
    If ``groups`` is specified, return the response as a list of
    n-element tuples with n being the value found in options['groups']
    """
    if not response or not options['groups']:
        return response
    n = options['groups']
    return list(izip(*[response[i::n] for i in range(n)]))


def int_or_none(response):
    if response is None:
        return None
    return int(response)


def float_or_none(response):
    if response is None:
        return None
    return float(response)


def bool_ok(response):
    return nativestr(response) == 'OK'


def parse_client_list(response, **options):
    clients = []
    for c in nativestr(response).splitlines():
        clients.append(dict([pair.split('=') for pair in c.split(' ')]))
    return clients


def parse_config_get(response, **options):
    response = [nativestr(i) if i is not None else None for i in response]
    return response and pairs_to_dict(response) or {}


def parse_scan(response, **options):
    cursor, r = response
    return long(cursor), r


def parse_hscan(response, **options):
    cursor, r = response
    return long(cursor), r and pairs_to_dict(r) or {}


def parse_zscan(response, **options):
    score_cast_func = options.get('score_cast_func', float)
    cursor, r = response
    it = iter(r)
    return long(cursor), list(izip(it, imap(score_cast_func, it)))


def parse_slowlog_get(response, **options):
    return [{
        'id': item[0],
        'start_time': int(item[1]),
        'duration': int(item[2]),
        'command': b(' ').join(item[3])
    } for item in response]


class StrictRedis(object):
    """
    Implementation of the Redis protocol.

    This abstract class provides a Python interface to all Redis commands
    and an implementation of the Redis protocol.

    Connection and Pipeline derive from this, implementing how
    the commands are sent and received to the Redis server
    """
    RESPONSE_CALLBACKS = dict_merge(
        string_keys_to_dict(
            'AUTH EXISTS EXPIRE EXPIREAT HEXISTS HMSET MOVE MSETNX PERSIST '
            'PSETEX RENAMENX SISMEMBER SMOVE SETEX SETNX',
            bool
        ),
        string_keys_to_dict(
            'BITCOUNT DECRBY DEL GETBIT HDEL HLEN INCRBY LINSERT LLEN LPUSHX '
            'PFADD PFCOUNT RPUSHX SADD SCARD SDIFFSTORE SETBIT SETRANGE '
            'SINTERSTORE SREM STRLEN SUNIONSTORE ZADD ZCARD ZLEXCOUNT ZREM '
            'ZREMRANGEBYLEX ZREMRANGEBYRANK ZREMRANGEBYSCORE',
            int
        ),
        string_keys_to_dict('INCRBYFLOAT HINCRBYFLOAT', float),
        string_keys_to_dict(
            # these return OK, or int if redis-server is >=1.3.4
            'LPUSH RPUSH',
            lambda r: isinstance(r, long) and r or nativestr(r) == 'OK'
        ),
        string_keys_to_dict('SORT', sort_return_tuples),
        string_keys_to_dict('ZSCORE ZINCRBY', float_or_none),
        string_keys_to_dict(
            'FLUSHALL FLUSHDB LSET LTRIM MSET PFMERGE RENAME '
            'SAVE SELECT SHUTDOWN SLAVEOF WATCH UNWATCH',
            bool_ok
        ),
        string_keys_to_dict('BLPOP BRPOP', lambda r: r and tuple(r) or None),
        string_keys_to_dict(
            'SDIFF SINTER SMEMBERS SUNION',
            lambda r: r and set(r) or set()
        ),
        string_keys_to_dict(
            'ZRANGE ZRANGEBYSCORE ZREVRANGE ZREVRANGEBYSCORE',
            zset_score_pairs
        ),
        string_keys_to_dict('ZRANK ZREVRANK', int_or_none),
        string_keys_to_dict('BGREWRITEAOF BGSAVE', lambda r: True),
        {
            'CLIENT GETNAME': lambda r: r and nativestr(r),
            'CLIENT KILL': bool_ok,
            'CLIENT LIST': parse_client_list,
            'CLIENT SETNAME': bool_ok,
            'CONFIG GET': parse_config_get,
            'CONFIG RESETSTAT': bool_ok,
            'CONFIG SET': bool_ok,
            'DEBUG OBJECT': parse_debug_object,
            'HGETALL': lambda r: r and pairs_to_dict(r) or {},
            'HSCAN': parse_hscan,
            'INFO': parse_info,
            'LASTSAVE': timestamp_to_datetime,
            'OBJECT': parse_object,
            'PING': lambda r: nativestr(r) == 'PONG',
            'RANDOMKEY': lambda r: r and r or None,
            'SCAN': parse_scan,
            'SCRIPT EXISTS': lambda r: list(imap(bool, r)),
            'SCRIPT FLUSH': bool_ok,
            'SCRIPT KILL': bool_ok,
            'SCRIPT LOAD': nativestr,
            'SENTINEL GET-MASTER-ADDR-BY-NAME': parse_sentinel_get_master,
            'SENTINEL MASTER': parse_sentinel_master,
            'SENTINEL MASTERS': parse_sentinel_masters,
            'SENTINEL MONITOR': bool_ok,
            'SENTINEL REMOVE': bool_ok,
            'SENTINEL SENTINELS': parse_sentinel_slaves_and_sentinels,
            'SENTINEL SET': bool_ok,
            'SENTINEL SLAVES': parse_sentinel_slaves_and_sentinels,
            'SET': lambda r: r and nativestr(r) == 'OK',
            'SLOWLOG GET': parse_slowlog_get,
            'SLOWLOG LEN': int,
            'SLOWLOG RESET': bool_ok,
            'SSCAN': parse_scan,
            'TIME': lambda x: (int(x[0]), int(x[1])),
            'ZSCAN': parse_zscan
        }
    )

    @classmethod
    def from_url(cls, url, db=None, **kwargs):
        """
        Return a Redis client object configured from the given URL.

        For example::

            redis://[:password]@localhost:6379/0
            unix://[:password]@/path/to/socket.sock?db=0

        There are several ways to specify a database number. The parse function
        will return the first specified option:
            1. A ``db`` querystring option, e.g. redis://localhost?db=0
            2. If using the redis:// scheme, the path argument of the url, e.g.
               redis://localhost/0
            3. The ``db`` argument to this function.

        If none of these options are specified, db=0 is used.

        Any additional querystring arguments and keyword arguments will be
        passed along to the ConnectionPool class's initializer. In the case
        of conflicting arguments, querystring arguments always win.
        """
        connection_pool = ConnectionPool.from_url(url, db=db, **kwargs)
        return cls(connection_pool=connection_pool)

    def __init__(self, host='localhost', port=6379,
                 db=0, password=None, socket_timeout=None,
                 socket_connect_timeout=None,
                 socket_keepalive=None, socket_keepalive_options=None,
                 connection_pool=None, charset='utf-8', errors='strict',
                 decode_responses=False, retry_on_timeout=False,
                 unix_socket_path=None,
                 ssl=False, ssl_keyfile=None, ssl_certfile=None,
                 ssl_cert_reqs=None, ssl_ca_certs=None):
        if not connection_pool:
            kwargs = {
                'db': db,
                'password': password,
                'socket_timeout': socket_timeout,
                'encoding': charset,
                'encoding_errors': errors,
                'decode_responses': decode_responses,
                'retry_on_timeout': retry_on_timeout
            }
            # based on input, setup appropriate connection args
            if unix_socket_path is not None:
                kwargs.update({
                    'path': unix_socket_path,
                    'connection_class': UnixDomainSocketConnection
                })
            else:
                # TCP specific options
                kwargs.update({
                    'host': host,
                    'port': port,
                    'socket_connect_timeout': socket_connect_timeout,
                    'socket_keepalive': socket_keepalive,
                    'socket_keepalive_options': socket_keepalive_options,
                })

                if ssl:
                    kwargs.update({
                        'connection_class': SSLConnection,
                        'ssl_keyfile': ssl_keyfile,
                        'ssl_certfile': ssl_certfile,
                        'ssl_cert_reqs': ssl_cert_reqs,
                        'ssl_ca_certs': ssl_ca_certs,
                    })
            connection_pool = ConnectionPool(**kwargs)
        self.connection_pool = connection_pool

        self.response_callbacks = self.__class__.RESPONSE_CALLBACKS.copy()

    def __repr__(self):
        return "%s<%s>" % (type(self).__name__, repr(self.connection_pool))

    def set_response_callback(self, command, callback):
        "Set a custom Response Callback"
        self.response_callbacks[command] = callback

    def pipeline(self, transaction=True, shard_hint=None):
        """
        Return a new pipeline object that can queue multiple commands for
        later execution. ``transaction`` indicates whether all commands
        should be executed atomically. Apart from making a group of operations
        atomic, pipelines are useful for reducing the back-and-forth overhead
        between the client and server.
        """
        return StrictPipeline(
            self.connection_pool,
            self.response_callbacks,
            transaction,
            shard_hint)

    def transaction(self, func, *watches, **kwargs):
        """
        Convenience method for executing the callable `func` as a transaction
        while watching all keys specified in `watches`. The 'func' callable
        should expect a single argument which is a Pipeline object.
        """
        shard_hint = kwargs.pop('shard_hint', None)
        value_from_callable = kwargs.pop('value_from_callable', False)
        with self.pipeline(True, shard_hint) as pipe:
            while 1:
                try:
                    if watches:
                        pipe.watch(*watches)
                    func_value = func(pipe)
                    exec_value = pipe.execute()
                    return func_value if value_from_callable else exec_value
                except WatchError:
                    continue

    def lock(self, name, timeout=None, sleep=0.1):
        """
        Return a new Lock object using key ``name`` that mimics
        the behavior of threading.Lock.

        If specified, ``timeout`` indicates a maximum life for the lock.
        By default, it will remain locked until release() is called.

        ``sleep`` indicates the amount of time to sleep per loop iteration
        when the lock is in blocking mode and another client is currently
        holding the lock.
        """
        return Lock(self, name, timeout=timeout, sleep=sleep)

    def pubsub(self, **kwargs):
        """
        Return a Publish/Subscribe object. With this object, you can
        subscribe to channels and listen for messages that get published to
        them.
        """
        return PubSub(self.connection_pool, **kwargs)

    # COMMAND EXECUTION AND PROTOCOL PARSING
    def execute_command(self, *args, **options):
        "Execute a command and return a parsed response"
        pool = self.connection_pool
        command_name = args[0]
        connection = pool.get_connection(command_name, **options)
        try:
            connection.send_command(*args)
            return self.parse_response(connection, command_name, **options)
        except (ConnectionError, TimeoutError) as e:
            connection.disconnect()
            if not connection.retry_on_timeout and isinstance(e, TimeoutError):
                raise
            connection.send_command(*args)
            return self.parse_response(connection, command_name, **options)
        finally:
            pool.release(connection)

    def parse_response(self, connection, command_name, **options):
        "Parses a response from the Redis server"
        response = connection.read_response()
        if command_name in self.response_callbacks:
            return self.response_callbacks[command_name](response, **options)
        return response

    # SERVER INFORMATION
    def bgrewriteaof(self):
        "Tell the Redis server to rewrite the AOF file from data in memory."
        return self.execute_command('BGREWRITEAOF')

    def bgsave(self):
        """
        Tell the Redis server to save its data to disk.  Unlike save(),
        this method is asynchronous and returns immediately.
        """
        return self.execute_command('BGSAVE')

    def client_kill(self, address):
        "Disconnects the client at ``address`` (ip:port)"
        return self.execute_command('CLIENT KILL', address)

    def client_list(self):
        "Returns a list of currently connected clients"
        return self.execute_command('CLIENT LIST')

    def client_getname(self):
        "Returns the current connection name"
        return self.execute_command('CLIENT GETNAME')

    def client_setname(self, name):
        "Sets the current connection name"
        return self.execute_command('CLIENT SETNAME', name)

    def config_get(self, pattern="*"):
        "Return a dictionary of configuration based on the ``pattern``"
        return self.execute_command('CONFIG GET', pattern)

    def config_set(self, name, value):
        "Set config item ``name`` with ``value``"
        return self.execute_command('CONFIG SET', name, value)

    def config_resetstat(self):
        "Reset runtime statistics"
        return self.execute_command('CONFIG RESETSTAT')

    def config_rewrite(self):
        "Rewrite config file with the minimal change to reflect running config"
        return self.execute_command('CONFIG REWRITE')

    def dbsize(self):
        "Returns the number of keys in the current database"
        return self.execute_command('DBSIZE')

    def debug_object(self, key):
        "Returns version specific meta information about a given key"
        return self.execute_command('DEBUG OBJECT', key)

    def echo(self, value):
        "Echo the string back from the server"
        return self.execute_command('ECHO', value)

    def flushall(self):
        "Delete all keys in all databases on the current host"
        return self.execute_command('FLUSHALL')

    def flushdb(self):
        "Delete all keys in the current database"
        return self.execute_command('FLUSHDB')

    def info(self, section=None):
        """
        Returns a dictionary containing information about the Redis server

        The ``section`` option can be used to select a specific section
        of information

        The section option is not supported by older versions of Redis Server,
        and will generate ResponseError
        """
        if section is None:
            return self.execute_command('INFO')
        else:
            return self.execute_command('INFO', section)

    def lastsave(self):
        """
        Return a Python datetime object representing the last time the
        Redis database was saved to disk
        """
        return self.execute_command('LASTSAVE')

    def object(self, infotype, key):
        "Return the encoding, idletime, or refcount about the key"
        return self.execute_command('OBJECT', infotype, key, infotype=infotype)

    def ping(self):
        "Ping the Redis server"
        return self.execute_command('PING')

    def save(self):
        """
        Tell the Redis server to save its data to disk,
        blocking until the save is complete
        """
        return self.execute_command('SAVE')

    def sentinel(self, *args):
        "Redis Sentinel's SENTINEL command."
        warnings.warn(
            DeprecationWarning('Use the individual sentinel_* methods'))

    def sentinel_get_master_addr_by_name(self, service_name):
        "Returns a (host, port) pair for the given ``service_name``"
        return self.execute_command('SENTINEL GET-MASTER-ADDR-BY-NAME',
                                    service_name)

    def sentinel_master(self, service_name):
        "Returns a dictionary containing the specified masters state."
        return self.execute_command('SENTINEL MASTER', service_name)

    def sentinel_masters(self):
        "Returns a list of dictionaries containing each master's state."
        return self.execute_command('SENTINEL MASTERS')

    def sentinel_monitor(self, name, ip, port, quorum):
        "Add a new master to Sentinel to be monitored"
        return self.execute_command('SENTINEL MONITOR', name, ip, port, quorum)

    def sentinel_remove(self, name):
        "Remove a master from Sentinel's monitoring"
        return self.execute_command('SENTINEL REMOVE', name)

    def sentinel_sentinels(self, service_name):
        "Returns a list of sentinels for ``service_name``"
        return self.execute_command('SENTINEL SENTINELS', service_name)

    def sentinel_set(self, name, option, value):
        "Set Sentinel monitoring parameters for a given master"
        return self.execute_command('SENTINEL SET', name, option, value)

    def sentinel_slaves(self, service_name):
        "Returns a list of slaves for ``service_name``"
        return self.execute_command('SENTINEL SLAVES', service_name)

    def shutdown(self):
        "Shutdown the server"
        try:
            self.execute_command('SHUTDOWN')
        except ConnectionError:
            # a ConnectionError here is expected
            return
        raise RedisError("SHUTDOWN seems to have failed.")

    def slaveof(self, host=None, port=None):
        """
        Set the server to be a replicated slave of the instance identified
        by the ``host`` and ``port``. If called without arguments, the
        instance is promoted to a master instead.
        """
        if host is None and port is None:
            return self.execute_command('SLAVEOF', Token('NO'), Token('ONE'))
        return self.execute_command('SLAVEOF', host, port)

    def slowlog_get(self, num=None):
        """
        Get the entries from the slowlog. If ``num`` is specified, get the
        most recent ``num`` items.
        """
        args = ['SLOWLOG GET']
        if num is not None:
            args.append(num)
        return self.execute_command(*args)

    def slowlog_len(self):
        "Get the number of items in the slowlog"
        return self.execute_command('SLOWLOG LEN')

    def slowlog_reset(self):
        "Remove all items in the slowlog"
        return self.execute_command('SLOWLOG RESET')

    def time(self):
        """
        Returns the server time as a 2-item tuple of ints:
        (seconds since epoch, microseconds into this second).
        """
        return self.execute_command('TIME')

    # BASIC KEY COMMANDS
    def append(self, key, value):
        """
        Appends the string ``value`` to the value at ``key``. If ``key``
        doesn't already exist, create it with a value of ``value``.
        Returns the new length of the value at ``key``.
        """
        return self.execute_command('APPEND', key, value)

    def bitcount(self, key, start=None, end=None):
        """
        Returns the count of set bits in the value of ``key``.  Optional
        ``start`` and ``end`` paramaters indicate which bytes to consider
        """
        params = [key]
        if start is not None and end is not None:
            params.append(start)
            params.append(end)
        elif (start is not None and end is None) or \
                (end is not None and start is None):
            raise RedisError("Both start and end must be specified")
        return self.execute_command('BITCOUNT', *params)

    def bitop(self, operation, dest, *keys):
        """
        Perform a bitwise operation using ``operation`` between ``keys`` and
        store the result in ``dest``.
        """
        return self.execute_command('BITOP', operation, dest, *keys)

    def decr(self, name, amount=1):
        """
        Decrements the value of ``key`` by ``amount``.  If no key exists,
        the value will be initialized as 0 - ``amount``
        """
        return self.execute_command('DECRBY', name, amount)

    def delete(self, *names):
        "Delete one or more keys specified by ``names``"
        return self.execute_command('DEL', *names)

    def __delitem__(self, name):
        self.delete(name)

    def dump(self, name):
        """
        Return a serialized version of the value stored at the specified key.
        If key does not exist a nil bulk reply is returned.
        """
        return self.execute_command('DUMP', name)

    def exists(self, name):
        "Returns a boolean indicating whether key ``name`` exists"
        return self.execute_command('EXISTS', name)
    __contains__ = exists

    def expire(self, name, time):
        """
        Set an expire flag on key ``name`` for ``time`` seconds. ``time``
        can be represented by an integer or a Python timedelta object.
        """
        if isinstance(time, datetime.timedelta):
            time = time.seconds + time.days * 24 * 3600
        return self.execute_command('EXPIRE', name, time)

    def expireat(self, name, when):
        """
        Set an expire flag on key ``name``. ``when`` can be represented
        as an integer indicating unix time or a Python datetime object.
        """
        if isinstance(when, datetime.datetime):
            when = int(mod_time.mktime(when.timetuple()))
        return self.execute_command('EXPIREAT', name, when)

    def get(self, name):
        """
        Return the value at key ``name``, or None if the key doesn't exist
        """
        return self.execute_command('GET', name)

    def __getitem__(self, name):
        """
        Return the value at key ``name``, raises a KeyError if the key
        doesn't exist.
        """
        value = self.get(name)
        if value:
            return value
        raise KeyError(name)

    def getbit(self, name, offset):
        "Returns a boolean indicating the value of ``offset`` in ``name``"
        return self.execute_command('GETBIT', name, offset)

    def getrange(self, key, start, end):
        """
        Returns the substring of the string value stored at ``key``,
        determined by the offsets ``start`` and ``end`` (both are inclusive)
        """
        return self.execute_command('GETRANGE', key, start, end)

    def getset(self, name, value):
        """
        Sets the value at key ``name`` to ``value``
        and returns the old value at key ``name`` atomically.
        """
        return self.execute_command('GETSET', name, value)

    def incr(self, name, amount=1):
        """
        Increments the value of ``key`` by ``amount``.  If no key exists,
        the value will be initialized as ``amount``
        """
        return self.execute_command('INCRBY', name, amount)

    def incrby(self, name, amount=1):
        """
        Increments the value of ``key`` by ``amount``.  If no key exists,
        the value will be initialized as ``amount``
        """

        # An alias for ``incr()``, because it is already implemented
        # as INCRBY redis command.
        return self.incr(name, amount)

    def incrbyfloat(self, name, amount=1.0):
        """
        Increments the value at key ``name`` by floating ``amount``.
        If no key exists, the value will be initialized as ``amount``
        """
        return self.execute_command('INCRBYFLOAT', name, amount)

    def keys(self, pattern='*'):
        "Returns a list of keys matching ``pattern``"
        return self.execute_command('KEYS', pattern)

    def mget(self, keys, *args):
        """
        Returns a list of values ordered identically to ``keys``
        """
        args = list_or_args(keys, args)
        return self.execute_command('MGET', *args)

    def mset(self, *args, **kwargs):
        """
        Sets key/values based on a mapping. Mapping can be supplied as a single
        dictionary argument or as kwargs.
        """
        if args:
            if len(args) != 1 or not isinstance(args[0], dict):
                raise RedisError('MSET requires **kwargs or a single dict arg')
            kwargs.update(args[0])
        items = []
        for pair in iteritems(kwargs):
            items.extend(pair)
        return self.execute_command('MSET', *items)

    def msetnx(self, *args, **kwargs):
        """
        Sets key/values based on a mapping if none of the keys are already set.
        Mapping can be supplied as a single dictionary argument or as kwargs.
        Returns a boolean indicating if the operation was successful.
        """
        if args:
            if len(args) != 1 or not isinstance(args[0], dict):
                raise RedisError('MSETNX requires **kwargs or a single '
                                 'dict arg')
            kwargs.update(args[0])
        items = []
        for pair in iteritems(kwargs):
            items.extend(pair)
        return self.execute_command('MSETNX', *items)

    def move(self, name, db):
        "Moves the key ``name`` to a different Redis database ``db``"
        return self.execute_command('MOVE', name, db)

    def persist(self, name):
        "Removes an expiration on ``name``"
        return self.execute_command('PERSIST', name)

    def pexpire(self, name, time):
        """
        Set an expire flag on key ``name`` for ``time`` milliseconds.
        ``time`` can be represented by an integer or a Python timedelta
        object.
        """
        if isinstance(time, datetime.timedelta):
            ms = int(time.microseconds / 1000)
            time = (time.seconds + time.days * 24 * 3600) * 1000 + ms
        return self.execute_command('PEXPIRE', name, time)

    def pexpireat(self, name, when):
        """
        Set an expire flag on key ``name``. ``when`` can be represented
        as an integer representing unix time in milliseconds (unix time * 1000)
        or a Python datetime object.
        """
        if isinstance(when, datetime.datetime):
            ms = int(when.microsecond / 1000)
            when = int(mod_time.mktime(when.timetuple())) * 1000 + ms
        return self.execute_command('PEXPIREAT', name, when)

    def psetex(self, name, time_ms, value):
        """
        Set the value of key ``name`` to ``value`` that expires in ``time_ms``
        milliseconds. ``time_ms`` can be represented by an integer or a Python
        timedelta object
        """
        if isinstance(time_ms, datetime.timedelta):
            ms = int(time_ms.microseconds / 1000)
            time_ms = (time_ms.seconds + time_ms.days * 24 * 3600) * 1000 + ms
        return self.execute_command('PSETEX', name, time_ms, value)

    def pttl(self, name):
        "Returns the number of milliseconds until the key ``name`` will expire"
        return self.execute_command('PTTL', name)

    def randomkey(self):
        "Returns the name of a random key"
        return self.execute_command('RANDOMKEY')

    def rename(self, src, dst):
        """
        Rename key ``src`` to ``dst``
        """
        return self.execute_command('RENAME', src, dst)

    def renamenx(self, src, dst):
        "Rename key ``src`` to ``dst`` if ``dst`` doesn't already exist"
        return self.execute_command('RENAMENX', src, dst)

    def restore(self, name, ttl, value):
        """
        Create a key using the provided serialized value, previously obtained
        using DUMP.
        """
        return self.execute_command('RESTORE', name, ttl, value)

    def set(self, name, value, ex=None, px=None, nx=False, xx=False):
        """
        Set the value at key ``name`` to ``value``

        ``ex`` sets an expire flag on key ``name`` for ``ex`` seconds.

        ``px`` sets an expire flag on key ``name`` for ``px`` milliseconds.

        ``nx`` if set to True, set the value at key ``name`` to ``value`` if it
            does not already exist.

        ``xx`` if set to True, set the value at key ``name`` to ``value`` if it
            already exists.
        """
        pieces = [name, value]
        if ex:
            pieces.append('EX')
            if isinstance(ex, datetime.timedelta):
                ex = ex.seconds + ex.days * 24 * 3600
            pieces.append(ex)
        if px:
            pieces.append('PX')
            if isinstance(px, datetime.timedelta):
                ms = int(px.microseconds / 1000)
                px = (px.seconds + px.days * 24 * 3600) * 1000 + ms
            pieces.append(px)

        if nx:
            pieces.append('NX')
        if xx:
            pieces.append('XX')
        return self.execute_command('SET', *pieces)

    def __setitem__(self, name, value):
        self.set(name, value)

    def setbit(self, name, offset, value):
        """
        Flag the ``offset`` in ``name`` as ``value``. Returns a boolean
        indicating the previous value of ``offset``.
        """
        value = value and 1 or 0
        return self.execute_command('SETBIT', name, offset, value)

    def setex(self, name, time, value):
        """
        Set the value of key ``name`` to ``value`` that expires in ``time``
        seconds. ``time`` can be represented by an integer or a Python
        timedelta object.
        """
        if isinstance(time, datetime.timedelta):
            time = time.seconds + time.days * 24 * 3600
        return self.execute_command('SETEX', name, time, value)

    def setnx(self, name, value):
        "Set the value of key ``name`` to ``value`` if key doesn't exist"
        return self.execute_command('SETNX', name, value)

    def setrange(self, name, offset, value):
        """
        Overwrite bytes in the value of ``name`` starting at ``offset`` with
        ``value``. If ``offset`` plus the length of ``value`` exceeds the
        length of the original value, the new value will be larger than before.
        If ``offset`` exceeds the length of the original value, null bytes
        will be used to pad between the end of the previous value and the start
        of what's being injected.

        Returns the length of the new string.
        """
        return self.execute_command('SETRANGE', name, offset, value)

    def strlen(self, name):
        "Return the number of bytes stored in the value of ``name``"
        return self.execute_command('STRLEN', name)

    def substr(self, name, start, end=-1):
        """
        Return a substring of the string at key ``name``. ``start`` and ``end``
        are 0-based integers specifying the portion of the string to return.
        """
        return self.execute_command('SUBSTR', name, start, end)

    def ttl(self, name):
        "Returns the number of seconds until the key ``name`` will expire"
        return self.execute_command('TTL', name)

    def type(self, name):
        "Returns the type of key ``name``"
        return self.execute_command('TYPE', name)

    def watch(self, *names):
        """
        Watches the values at keys ``names``, or None if the key doesn't exist
        """
        warnings.warn(DeprecationWarning('Call WATCH from a Pipeline object'))

    def unwatch(self):
        """
        Unwatches the value at key ``name``, or None of the key doesn't exist
        """
        warnings.warn(
            DeprecationWarning('Call UNWATCH from a Pipeline object'))

    # LIST COMMANDS
    def blpop(self, keys, timeout=0):
        """
        LPOP a value off of the first non-empty list
        named in the ``keys`` list.

        If none of the lists in ``keys`` has a value to LPOP, then block
        for ``timeout`` seconds, or until a value gets pushed on to one
        of the lists.

        If timeout is 0, then block indefinitely.
        """
        if timeout is None:
            timeout = 0
        if isinstance(keys, basestring):
            keys = [keys]
        else:
            keys = list(keys)
        keys.append(timeout)
        return self.execute_command('BLPOP', *keys)

    def brpop(self, keys, timeout=0):
        """
        RPOP a value off of the first non-empty list
        named in the ``keys`` list.

        If none of the lists in ``keys`` has a value to LPOP, then block
        for ``timeout`` seconds, or until a value gets pushed on to one
        of the lists.

        If timeout is 0, then block indefinitely.
        """
        if timeout is None:
            timeout = 0
        if isinstance(keys, basestring):
            keys = [keys]
        else:
            keys = list(keys)
        keys.append(timeout)
        return self.execute_command('BRPOP', *keys)

    def brpoplpush(self, src, dst, timeout=0):
        """
        Pop a value off the tail of ``src``, push it on the head of ``dst``
        and then return it.

        This command blocks until a value is in ``src`` or until ``timeout``
        seconds elapse, whichever is first. A ``timeout`` value of 0 blocks
        forever.
        """
        if timeout is None:
            timeout = 0
        return self.execute_command('BRPOPLPUSH', src, dst, timeout)

    def lindex(self, name, index):
        """
        Return the item from list ``name`` at position ``index``

        Negative indexes are supported and will return an item at the
        end of the list
        """
        return self.execute_command('LINDEX', name, index)

    def linsert(self, name, where, refvalue, value):
        """
        Insert ``value`` in list ``name`` either immediately before or after
        [``where``] ``refvalue``

        Returns the new length of the list on success or -1 if ``refvalue``
        is not in the list.
        """
        return self.execute_command('LINSERT', name, where, refvalue, value)

    def llen(self, name):
        "Return the length of the list ``name``"
        return self.execute_command('LLEN', name)

    def lpop(self, name):
        "Remove and return the first item of the list ``name``"
        return self.execute_command('LPOP', name)

    def lpush(self, name, *values):
        "Push ``values`` onto the head of the list ``name``"
        return self.execute_command('LPUSH', name, *values)

    def lpushx(self, name, value):
        "Push ``value`` onto the head of the list ``name`` if ``name`` exists"
        return self.execute_command('LPUSHX', name, value)

    def lrange(self, name, start, end):
        """
        Return a slice of the list ``name`` between
        position ``start`` and ``end``

        ``start`` and ``end`` can be negative numbers just like
        Python slicing notation
        """
        return self.execute_command('LRANGE', name, start, end)

    def lrem(self, name, count, value):
        """
        Remove the first ``count`` occurrences of elements equal to ``value``
        from the list stored at ``name``.

        The count argument influences the operation in the following ways:
            count > 0: Remove elements equal to value moving from head to tail.
            count < 0: Remove elements equal to value moving from tail to head.
            count = 0: Remove all elements equal to value.
        """
        return self.execute_command('LREM', name, count, value)

    def lset(self, name, index, value):
        "Set ``position`` of list ``name`` to ``value``"
        return self.execute_command('LSET', name, index, value)

    def ltrim(self, name, start, end):
        """
        Trim the list ``name``, removing all values not within the slice
        between ``start`` and ``end``

        ``start`` and ``end`` can be negative numbers just like
        Python slicing notation
        """
        return self.execute_command('LTRIM', name, start, end)

    def rpop(self, name):
        "Remove and return the last item of the list ``name``"
        return self.execute_command('RPOP', name)

    def rpoplpush(self, src, dst):
        """
        RPOP a value off of the ``src`` list and atomically LPUSH it
        on to the ``dst`` list.  Returns the value.
        """
        return self.execute_command('RPOPLPUSH', src, dst)

    def rpush(self, name, *values):
        "Push ``values`` onto the tail of the list ``name``"
        return self.execute_command('RPUSH', name, *values)

    def rpushx(self, name, value):
        "Push ``value`` onto the tail of the list ``name`` if ``name`` exists"
        return self.execute_command('RPUSHX', name, value)

    def sort(self, name, start=None, num=None, by=None, get=None,
             desc=False, alpha=False, store=None, groups=False):
        """
        Sort and return the list, set or sorted set at ``name``.

        ``start`` and ``num`` allow for paging through the sorted data

        ``by`` allows using an external key to weight and sort the items.
            Use an "*" to indicate where in the key the item value is located

        ``get`` allows for returning items from external keys rather than the
            sorted data itself.  Use an "*" to indicate where int he key
            the item value is located

        ``desc`` allows for reversing the sort

        ``alpha`` allows for sorting lexicographically rather than numerically

        ``store`` allows for storing the result of the sort into
            the key ``store``

        ``groups`` if set to True and if ``get`` contains at least two
            elements, sort will return a list of tuples, each containing the
            values fetched from the arguments to ``get``.

        """
        if (start is not None and num is None) or \
                (num is not None and start is None):
            raise RedisError("``start`` and ``num`` must both be specified")

        pieces = [name]
        if by is not None:
            pieces.append(Token('BY'))
            pieces.append(by)
        if start is not None and num is not None:
            pieces.append(Token('LIMIT'))
            pieces.append(start)
            pieces.append(num)
        if get is not None:
            # If get is a string assume we want to get a single value.
            # Otherwise assume it's an interable and we want to get multiple
            # values. We can't just iterate blindly because strings are
            # iterable.
            if isinstance(get, basestring):
                pieces.append(Token('GET'))
                pieces.append(get)
            else:
                for g in get:
                    pieces.append(Token('GET'))
                    pieces.append(g)
        if desc:
            pieces.append(Token('DESC'))
        if alpha:
            pieces.append(Token('ALPHA'))
        if store is not None:
            pieces.append(Token('STORE'))
            pieces.append(store)

        if groups:
            if not get or isinstance(get, basestring) or len(get) < 2:
                raise DataError('when using "groups" the "get" argument '
                                'must be specified and contain at least '
                                'two keys')

        options = {'groups': len(get) if groups else None}
        return self.execute_command('SORT', *pieces, **options)

    # SCAN COMMANDS
    def scan(self, cursor=0, match=None, count=None):
        """
        Incrementally return lists of key names. Also return a cursor
        indicating the scan position.

        ``match`` allows for filtering the keys by pattern

        ``count`` allows for hint the minimum number of returns
        """
        pieces = [cursor]
        if match is not None:
            pieces.extend([Token('MATCH'), match])
        if count is not None:
            pieces.extend([Token('COUNT'), count])
        return self.execute_command('SCAN', *pieces)

    def scan_iter(self, match=None, count=None):
        """
        Make an iterator using the SCAN command so that the client doesn't
        need to remember the cursor position.

        ``match`` allows for filtering the keys by pattern

        ``count`` allows for hint the minimum number of returns
        """
        cursor = '0'
        while cursor != 0:
            cursor, data = self.scan(cursor=cursor, match=match, count=count)
            for item in data:
                yield item

    def sscan(self, name, cursor=0, match=None, count=None):
        """
        Incrementally return lists of elements in a set. Also return a cursor
        indicating the scan position.

        ``match`` allows for filtering the keys by pattern

        ``count`` allows for hint the minimum number of returns
        """
        pieces = [name, cursor]
        if match is not None:
            pieces.extend([Token('MATCH'), match])
        if count is not None:
            pieces.extend([Token('COUNT'), count])
        return self.execute_command('SSCAN', *pieces)

    def sscan_iter(self, name, match=None, count=None):
        """
        Make an iterator using the SSCAN command so that the client doesn't
        need to remember the cursor position.

        ``match`` allows for filtering the keys by pattern

        ``count`` allows for hint the minimum number of returns
        """
        cursor = '0'
        while cursor != 0:
            cursor, data = self.sscan(name, cursor=cursor,
                                      match=match, count=count)
            for item in data:
                yield item

    def hscan(self, name, cursor=0, match=None, count=None):
        """
        Incrementally return key/value slices in a hash. Also return a cursor
        indicating the scan position.

        ``match`` allows for filtering the keys by pattern

        ``count`` allows for hint the minimum number of returns
        """
        pieces = [name, cursor]
        if match is not None:
            pieces.extend([Token('MATCH'), match])
        if count is not None:
            pieces.extend([Token('COUNT'), count])
        return self.execute_command('HSCAN', *pieces)

    def hscan_iter(self, name, match=None, count=None):
        """
        Make an iterator using the HSCAN command so that the client doesn't
        need to remember the cursor position.

        ``match`` allows for filtering the keys by pattern

        ``count`` allows for hint the minimum number of returns
        """
        cursor = '0'
        while cursor != 0:
            cursor, data = self.hscan(name, cursor=cursor,
                                      match=match, count=count)
            for item in data.items():
                yield item

    def zscan(self, name, cursor=0, match=None, count=None,
              score_cast_func=float):
        """
        Incrementally return lists of elements in a sorted set. Also return a
        cursor indicating the scan position.

        ``match`` allows for filtering the keys by pattern

        ``count`` allows for hint the minimum number of returns

        ``score_cast_func`` a callable used to cast the score return value
        """
        pieces = [name, cursor]
        if match is not None:
            pieces.extend([Token('MATCH'), match])
        if count is not None:
            pieces.extend([Token('COUNT'), count])
        options = {'score_cast_func': score_cast_func}
        return self.execute_command('ZSCAN', *pieces, **options)

    def zscan_iter(self, name, match=None, count=None,
                   score_cast_func=float):
        """
        Make an iterator using the ZSCAN command so that the client doesn't
        need to remember the cursor position.

        ``match`` allows for filtering the keys by pattern

        ``count`` allows for hint the minimum number of returns

        ``score_cast_func`` a callable used to cast the score return value
        """
        cursor = '0'
        while cursor != 0:
            cursor, data = self.zscan(name, cursor=cursor, match=match,
                                      count=count,
                                      score_cast_func=score_cast_func)
            for item in data:
                yield item

    # SET COMMANDS
    def sadd(self, name, *values):
        "Add ``value(s)`` to set ``name``"
        return self.execute_command('SADD', name, *values)

    def scard(self, name):
        "Return the number of elements in set ``name``"
        return self.execute_command('SCARD', name)

    def sdiff(self, keys, *args):
        "Return the difference of sets specified by ``keys``"
        args = list_or_args(keys, args)
        return self.execute_command('SDIFF', *args)

    def sdiffstore(self, dest, keys, *args):
        """
        Store the difference of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        args = list_or_args(keys, args)
        return self.execute_command('SDIFFSTORE', dest, *args)

    def sinter(self, keys, *args):
        "Return the intersection of sets specified by ``keys``"
        args = list_or_args(keys, args)
        return self.execute_command('SINTER', *args)

    def sinterstore(self, dest, keys, *args):
        """
        Store the intersection of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        args = list_or_args(keys, args)
        return self.execute_command('SINTERSTORE', dest, *args)

    def sismember(self, name, value):
        "Return a boolean indicating if ``value`` is a member of set ``name``"
        return self.execute_command('SISMEMBER', name, value)

    def smembers(self, name):
        "Return all members of the set ``name``"
        return self.execute_command('SMEMBERS', name)

    def smove(self, src, dst, value):
        "Move ``value`` from set ``src`` to set ``dst`` atomically"
        return self.execute_command('SMOVE', src, dst, value)

    def spop(self, name):
        "Remove and return a random member of set ``name``"
        return self.execute_command('SPOP', name)

    def srandmember(self, name, number=None):
        """
        If ``number`` is None, returns a random member of set ``name``.

        If ``number`` is supplied, returns a list of ``number`` random
        memebers of set ``name``. Note this is only available when running
        Redis 2.6+.
        """
        args = number and [number] or []
        return self.execute_command('SRANDMEMBER', name, *args)

    def srem(self, name, *values):
        "Remove ``values`` from set ``name``"
        return self.execute_command('SREM', name, *values)

    def sunion(self, keys, *args):
        "Return the union of sets specified by ``keys``"
        args = list_or_args(keys, args)
        return self.execute_command('SUNION', *args)

    def sunionstore(self, dest, keys, *args):
        """
        Store the union of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        args = list_or_args(keys, args)
        return self.execute_command('SUNIONSTORE', dest, *args)

    # SORTED SET COMMANDS
    def zadd(self, name, *args, **kwargs):
        """
        Set any number of score, element-name pairs to the key ``name``. Pairs
        can be specified in two ways:

        As *args, in the form of: score1, name1, score2, name2, ...
        or as **kwargs, in the form of: name1=score1, name2=score2, ...

        The following example would add four values to the 'my-key' key:
        redis.zadd('my-key', 1.1, 'name1', 2.2, 'name2', name3=3.3, name4=4.4)
        """
        pieces = []
        if args:
            if len(args) % 2 != 0:
                raise RedisError("ZADD requires an equal number of "
                                 "values and scores")
            pieces.extend(args)
        for pair in iteritems(kwargs):
            pieces.append(pair[1])
            pieces.append(pair[0])
        return self.execute_command('ZADD', name, *pieces)

    def zcard(self, name):
        "Return the number of elements in the sorted set ``name``"
        return self.execute_command('ZCARD', name)

    def zcount(self, name, min, max):
        """
        Returns the number of elements in the sorted set at key ``name`` with
        a score between ``min`` and ``max``.
        """
        return self.execute_command('ZCOUNT', name, min, max)

    def zincrby(self, name, value, amount=1):
        "Increment the score of ``value`` in sorted set ``name`` by ``amount``"
        return self.execute_command('ZINCRBY', name, amount, value)

    def zinterstore(self, dest, keys, aggregate=None):
        """
        Intersect multiple sorted sets specified by ``keys`` into
        a new sorted set, ``dest``. Scores in the destination will be
        aggregated based on the ``aggregate``, or SUM if none is provided.
        """
        return self._zaggregate('ZINTERSTORE', dest, keys, aggregate)

    def zlexcount(self, name, min, max):
        """
        Return the number of items in the sorted set ``name`` between the
        lexicographical range ``min`` and ``max``.
        """
        return self.execute_command('ZLEXCOUNT', name, min, max)

    def zrange(self, name, start, end, desc=False, withscores=False,
               score_cast_func=float):
        """
        Return a range of values from sorted set ``name`` between
        ``start`` and ``end`` sorted in ascending order.

        ``start`` and ``end`` can be negative, indicating the end of the range.

        ``desc`` a boolean indicating whether to sort the results descendingly

        ``withscores`` indicates to return the scores along with the values.
        The return type is a list of (value, score) pairs

        ``score_cast_func`` a callable used to cast the score return value
        """
        if desc:
            return self.zrevrange(name, start, end, withscores,
                                  score_cast_func)
        pieces = ['ZRANGE', name, start, end]
        if withscores:
            pieces.append(Token('WITHSCORES'))
        options = {
            'withscores': withscores,
            'score_cast_func': score_cast_func
        }
        return self.execute_command(*pieces, **options)

    def zrangebylex(self, name, min, max, start=None, num=None):
        """
        Return the lexicographical range of values from sorted set ``name``
        between ``min`` and ``max``.

        If ``start`` and ``num`` are specified, then return a slice of the
        range.
        """
        if (start is not None and num is None) or \
                (num is not None and start is None):
            raise RedisError("``start`` and ``num`` must both be specified")
        pieces = ['ZRANGEBYLEX', name, min, max]
        if start is not None and num is not None:
            pieces.extend([Token('LIMIT'), start, num])
        return self.execute_command(*pieces)

    def zrangebyscore(self, name, min, max, start=None, num=None,
                      withscores=False, score_cast_func=float):
        """
        Return a range of values from the sorted set ``name`` with scores
        between ``min`` and ``max``.

        If ``start`` and ``num`` are specified, then return a slice
        of the range.

        ``withscores`` indicates to return the scores along with the values.
        The return type is a list of (value, score) pairs

        `score_cast_func`` a callable used to cast the score return value
        """
        if (start is not None and num is None) or \
                (num is not None and start is None):
            raise RedisError("``start`` and ``num`` must both be specified")
        pieces = ['ZRANGEBYSCORE', name, min, max]
        if start is not None and num is not None:
            pieces.extend([Token('LIMIT'), start, num])
        if withscores:
            pieces.append(Token('WITHSCORES'))
        options = {
            'withscores': withscores,
            'score_cast_func': score_cast_func
        }
        return self.execute_command(*pieces, **options)

    def zrank(self, name, value):
        """
        Returns a 0-based value indicating the rank of ``value`` in sorted set
        ``name``
        """
        return self.execute_command('ZRANK', name, value)

    def zrem(self, name, *values):
        "Remove member ``values`` from sorted set ``name``"
        return self.execute_command('ZREM', name, *values)

    def zremrangebylex(self, name, min, max):
        """
        Remove all elements in the sorted set ``name`` between the
        lexicographical range specified by ``min`` and ``max``.

        Returns the number of elements removed.
        """
        return self.execute_command('ZREMRANGEBYLEX', name, min, max)

    def zremrangebyrank(self, name, min, max):
        """
        Remove all elements in the sorted set ``name`` with ranks between
        ``min`` and ``max``. Values are 0-based, ordered from smallest score
        to largest. Values can be negative indicating the highest scores.
        Returns the number of elements removed
        """
        return self.execute_command('ZREMRANGEBYRANK', name, min, max)

    def zremrangebyscore(self, name, min, max):
        """
        Remove all elements in the sorted set ``name`` with scores
        between ``min`` and ``max``. Returns the number of elements removed.
        """
        return self.execute_command('ZREMRANGEBYSCORE', name, min, max)

    def zrevrange(self, name, start, end, withscores=False,
                  score_cast_func=float):
        """
        Return a range of values from sorted set ``name`` between
        ``start`` and ``end`` sorted in descending order.

        ``start`` and ``end`` can be negative, indicating the end of the range.

        ``withscores`` indicates to return the scores along with the values
        The return type is a list of (value, score) pairs

        ``score_cast_func`` a callable used to cast the score return value
        """
        pieces = ['ZREVRANGE', name, start, end]
        if withscores:
            pieces.append(Token('WITHSCORES'))
        options = {
            'withscores': withscores,
            'score_cast_func': score_cast_func
        }
        return self.execute_command(*pieces, **options)

    def zrevrangebyscore(self, name, max, min, start=None, num=None,
                         withscores=False, score_cast_func=float):
        """
        Return a range of values from the sorted set ``name`` with scores
        between ``min`` and ``max`` in descending order.

        If ``start`` and ``num`` are specified, then return a slice
        of the range.

        ``withscores`` indicates to return the scores along with the values.
        The return type is a list of (value, score) pairs

        ``score_cast_func`` a callable used to cast the score return value
        """
        if (start is not None and num is None) or \
                (num is not None and start is None):
            raise RedisError("``start`` and ``num`` must both be specified")
        pieces = ['ZREVRANGEBYSCORE', name, max, min]
        if start is not None and num is not None:
            pieces.extend([Token('LIMIT'), start, num])
        if withscores:
            pieces.append(Token('WITHSCORES'))
        options = {
            'withscores': withscores,
            'score_cast_func': score_cast_func
        }
        return self.execute_command(*pieces, **options)

    def zrevrank(self, name, value):
        """
        Returns a 0-based value indicating the descending rank of
        ``value`` in sorted set ``name``
        """
        return self.execute_command('ZREVRANK', name, value)

    def zscore(self, name, value):
        "Return the score of element ``value`` in sorted set ``name``"
        return self.execute_command('ZSCORE', name, value)

    def zunionstore(self, dest, keys, aggregate=None):
        """
        Union multiple sorted sets specified by ``keys`` into
        a new sorted set, ``dest``. Scores in the destination will be
        aggregated based on the ``aggregate``, or SUM if none is provided.
        """
        return self._zaggregate('ZUNIONSTORE', dest, keys, aggregate)

    def _zaggregate(self, command, dest, keys, aggregate=None):
        pieces = [command, dest, len(keys)]
        if isinstance(keys, dict):
            keys, weights = iterkeys(keys), itervalues(keys)
        else:
            weights = None
        pieces.extend(keys)
        if weights:
            pieces.append(Token('WEIGHTS'))
            pieces.extend(weights)
        if aggregate:
            pieces.append(Token('AGGREGATE'))
            pieces.append(aggregate)
        return self.execute_command(*pieces)

    # HYPERLOGLOG COMMANDS
    def pfadd(self, name, *values):
        "Adds the specified elements to the specified HyperLogLog."
        return self.execute_command('PFADD', name, *values)

    def pfcount(self, name):
        """
        Return the approximated cardinality of
        the set observed by the HyperLogLog at key.
        """
        return self.execute_command('PFCOUNT', name)

    def pfmerge(self, dest, *sources):
        "Merge N different HyperLogLogs into a single one."
        return self.execute_command('PFMERGE', dest, *sources)

    # HASH COMMANDS
    def hdel(self, name, *keys):
        "Delete ``keys`` from hash ``name``"
        return self.execute_command('HDEL', name, *keys)

    def hexists(self, name, key):
        "Returns a boolean indicating if ``key`` exists within hash ``name``"
        return self.execute_command('HEXISTS', name, key)

    def hget(self, name, key):
        "Return the value of ``key`` within the hash ``name``"
        return self.execute_command('HGET', name, key)

    def hgetall(self, name):
        "Return a Python dict of the hash's name/value pairs"
        return self.execute_command('HGETALL', name)

    def hincrby(self, name, key, amount=1):
        "Increment the value of ``key`` in hash ``name`` by ``amount``"
        return self.execute_command('HINCRBY', name, key, amount)

    def hincrbyfloat(self, name, key, amount=1.0):
        """
        Increment the value of ``key`` in hash ``name`` by floating ``amount``
        """
        return self.execute_command('HINCRBYFLOAT', name, key, amount)

    def hkeys(self, name):
        "Return the list of keys within hash ``name``"
        return self.execute_command('HKEYS', name)

    def hlen(self, name):
        "Return the number of elements in hash ``name``"
        return self.execute_command('HLEN', name)

    def hset(self, name, key, value):
        """
        Set ``key`` to ``value`` within hash ``name``
        Returns 1 if HSET created a new field, otherwise 0
        """
        return self.execute_command('HSET', name, key, value)

    def hsetnx(self, name, key, value):
        """
        Set ``key`` to ``value`` within hash ``name`` if ``key`` does not
        exist.  Returns 1 if HSETNX created a field, otherwise 0.
        """
        return self.execute_command('HSETNX', name, key, value)

    def hmset(self, name, mapping):
        """
        Set key to value within hash ``name`` for each corresponding
        key and value from the ``mapping`` dict.
        """
        if not mapping:
            raise DataError("'hmset' with 'mapping' of length 0")
        items = []
        for pair in iteritems(mapping):
            items.extend(pair)
        return self.execute_command('HMSET', name, *items)

    def hmget(self, name, keys, *args):
        "Returns a list of values ordered identically to ``keys``"
        args = list_or_args(keys, args)
        return self.execute_command('HMGET', name, *args)

    def hvals(self, name):
        "Return the list of values within hash ``name``"
        return self.execute_command('HVALS', name)

    def publish(self, channel, message):
        """
        Publish ``message`` on ``channel``.
        Returns the number of subscribers the message was delivered to.
        """
        return self.execute_command('PUBLISH', channel, message)

    def eval(self, script, numkeys, *keys_and_args):
        """
        Execute the Lua ``script``, specifying the ``numkeys`` the script
        will touch and the key names and argument values in ``keys_and_args``.
        Returns the result of the script.

        In practice, use the object returned by ``register_script``. This
        function exists purely for Redis API completion.
        """
        return self.execute_command('EVAL', script, numkeys, *keys_and_args)

    def evalsha(self, sha, numkeys, *keys_and_args):
        """
        Use the ``sha`` to execute a Lua script already registered via EVAL
        or SCRIPT LOAD. Specify the ``numkeys`` the script will touch and the
        key names and argument values in ``keys_and_args``. Returns the result
        of the script.

        In practice, use the object returned by ``register_script``. This
        function exists purely for Redis API completion.
        """
        return self.execute_command('EVALSHA', sha, numkeys, *keys_and_args)

    def script_exists(self, *args):
        """
        Check if a script exists in the script cache by specifying the SHAs of
        each script as ``args``. Returns a list of boolean values indicating if
        if each already script exists in the cache.
        """
        return self.execute_command('SCRIPT EXISTS', *args)

    def script_flush(self):
        "Flush all scripts from the script cache"
        return self.execute_command('SCRIPT FLUSH')

    def script_kill(self):
        "Kill the currently executing Lua script"
        return self.execute_command('SCRIPT KILL')

    def script_load(self, script):
        "Load a Lua ``script`` into the script cache. Returns the SHA."
        return self.execute_command('SCRIPT LOAD', script)

    def register_script(self, script):
        """
        Register a Lua ``script`` specifying the ``keys`` it will touch.
        Returns a Script object that is callable and hides the complexity of
        deal with scripts, keys, and shas. This is the preferred way to work
        with Lua scripts.
        """
        return Script(self, script)


class Redis(StrictRedis):
    """
    Provides backwards compatibility with older versions of redis-py that
    changed arguments to some commands to be more Pythonic, sane, or by
    accident.
    """

    # Overridden callbacks
    RESPONSE_CALLBACKS = dict_merge(
        StrictRedis.RESPONSE_CALLBACKS,
        {
            'TTL': lambda r: r >= 0 and r or None,
            'PTTL': lambda r: r >= 0 and r or None,
        }
    )

    def pipeline(self, transaction=True, shard_hint=None):
        """
        Return a new pipeline object that can queue multiple commands for
        later execution. ``transaction`` indicates whether all commands
        should be executed atomically. Apart from making a group of operations
        atomic, pipelines are useful for reducing the back-and-forth overhead
        between the client and server.
        """
        return Pipeline(
            self.connection_pool,
            self.response_callbacks,
            transaction,
            shard_hint)

    def setex(self, name, value, time):
        """
        Set the value of key ``name`` to ``value`` that expires in ``time``
        seconds. ``time`` can be represented by an integer or a Python
        timedelta object.
        """
        if isinstance(time, datetime.timedelta):
            time = time.seconds + time.days * 24 * 3600
        return self.execute_command('SETEX', name, time, value)

    def lrem(self, name, value, num=0):
        """
        Remove the first ``num`` occurrences of elements equal to ``value``
        from the list stored at ``name``.

        The ``num`` argument influences the operation in the following ways:
            num > 0: Remove elements equal to value moving from head to tail.
            num < 0: Remove elements equal to value moving from tail to head.
            num = 0: Remove all elements equal to value.
        """
        return self.execute_command('LREM', name, num, value)

    def zadd(self, name, *args, **kwargs):
        """
        NOTE: The order of arguments differs from that of the official ZADD
        command. For backwards compatability, this method accepts arguments
        in the form of name1, score1, name2, score2, while the official Redis
        documents expects score1, name1, score2, name2.

        If you're looking to use the standard syntax, consider using the
        StrictRedis class. See the API Reference section of the docs for more
        information.

        Set any number of element-name, score pairs to the key ``name``. Pairs
        can be specified in two ways:

        As *args, in the form of: name1, score1, name2, score2, ...
        or as **kwargs, in the form of: name1=score1, name2=score2, ...

        The following example would add four values to the 'my-key' key:
        redis.zadd('my-key', 'name1', 1.1, 'name2', 2.2, name3=3.3, name4=4.4)
        """
        pieces = []
        if args:
            if len(args) % 2 != 0:
                raise RedisError("ZADD requires an equal number of "
                                 "values and scores")
            pieces.extend(reversed(args))
        for pair in iteritems(kwargs):
            pieces.append(pair[1])
            pieces.append(pair[0])
        return self.execute_command('ZADD', name, *pieces)


class PubSub(object):
    """
    PubSub provides publish, subscribe and listen support to Redis channels.

    After subscribing to one or more channels, the listen() method will block
    until a message arrives on one of the subscribed channels. That message
    will be returned and it's safe to start listening again.
    """
    PUBLISH_MESSAGE_TYPES = ('message', 'pmessage')
    UNSUBSCRIBE_MESSAGE_TYPES = ('unsubscribe', 'punsubscribe')

    def __init__(self, connection_pool, shard_hint=None,
                 ignore_subscribe_messages=False):
        self.connection_pool = connection_pool
        self.shard_hint = shard_hint
        self.ignore_subscribe_messages = ignore_subscribe_messages
        self.connection = None
        # we need to know the encoding options for this connection in order
        # to lookup channel and pattern names for callback handlers.
        conn = connection_pool.get_connection('pubsub', shard_hint)
        try:
            self.encoding = conn.encoding
            self.encoding_errors = conn.encoding_errors
            self.decode_responses = conn.decode_responses
        finally:
            connection_pool.release(conn)
        self.reset()

    def __del__(self):
        try:
            # if this object went out of scope prior to shutting down
            # subscriptions, close the connection manually before
            # returning it to the connection pool
            self.reset()
        except Exception:
            pass

    def reset(self):
        if self.connection:
            self.connection.disconnect()
            self.connection.clear_connect_callbacks()
            self.connection_pool.release(self.connection)
            self.connection = None
        self.channels = {}
        self.patterns = {}

    def close(self):
        self.reset()

    def on_connect(self, connection):
        "Re-subscribe to any channels and patterns previously subscribed to"
        # NOTE: for python3, we can't pass bytestrings as keyword arguments
        # so we need to decode channel/pattern names back to unicode strings
        # before passing them to [p]subscribe.
        if self.channels:
            channels = {}
            for k, v in iteritems(self.channels):
                if not self.decode_responses:
                    k = k.decode(self.encoding, self.encoding_errors)
                channels[k] = v
            self.subscribe(**channels)
        if self.patterns:
            patterns = {}
            for k, v in iteritems(self.patterns):
                if not self.decode_responses:
                    k = k.decode(self.encoding, self.encoding_errors)
                patterns[k] = v
            self.psubscribe(**patterns)

    def encode(self, value):
        """
        Encode the value so that it's identical to what we'll
        read off the connection
        """
        if self.decode_responses and isinstance(value, bytes):
            value = value.decode(self.encoding, self.encoding_errors)
        elif not self.decode_responses and isinstance(value, unicode):
            value = value.encode(self.encoding, self.encoding_errors)
        return value

    @property
    def subscribed(self):
        "Indicates if there are subscriptions to any channels or patterns"
        return bool(self.channels or self.patterns)

    def execute_command(self, *args, **kwargs):
        "Execute a publish/subscribe command"

        # NOTE: don't parse the response in this function. it could pull a
        # legitmate message off the stack if the connection is already
        # subscribed to one or more channels

        if self.connection is None:
            self.connection = self.connection_pool.get_connection(
                'pubsub',
                self.shard_hint
            )
            # register a callback that re-subscribes to any channels we
            # were listening to when we were disconnected
            self.connection.register_connect_callback(self.on_connect)
        connection = self.connection
        self._execute(connection, connection.send_command, *args)

    def _execute(self, connection, command, *args):
        try:
            return command(*args)
        except (ConnectionError, TimeoutError) as e:
            connection.disconnect()
            if not connection.retry_on_timeout and isinstance(e, TimeoutError):
                raise
            # Connect manually here. If the Redis server is down, this will
            # fail and raise a ConnectionError as desired.
            connection.connect()
            # the ``on_connect`` callback should haven been called by the
            # connection to resubscribe us to any channels and patterns we were
            # previously listening to
            return command(*args)

    def parse_response(self, block=True):
        "Parse the response from a publish/subscribe command"
        connection = self.connection
        if not block and not connection.can_read():
            return None
        return self._execute(connection, connection.read_response)

    def psubscribe(self, *args, **kwargs):
        """
        Subscribe to channel patterns. Patterns supplied as keyword arguments
        expect a pattern name as the key and a callable as the value. A
        pattern's callable will be invoked automatically when a message is
        received on that pattern rather than producing a message via
        ``listen()``.
        """
        if args:
            args = list_or_args(args[0], args[1:])
        new_patterns = {}
        new_patterns.update(dict.fromkeys(imap(self.encode, args)))
        for pattern, handler in iteritems(kwargs):
            new_patterns[self.encode(pattern)] = handler
        ret_val = self.execute_command('PSUBSCRIBE', *iterkeys(new_patterns))
        # update the patterns dict AFTER we send the command. we don't want to
        # subscribe twice to these patterns, once for the command and again
        # for the reconnection.
        self.patterns.update(new_patterns)
        return ret_val

    def punsubscribe(self, *args):
        """
        Unsubscribe from the supplied patterns. If empy, unsubscribe from
        all patterns.
        """
        if args:
            args = list_or_args(args[0], args[1:])
        return self.execute_command('PUNSUBSCRIBE', *args)

    def subscribe(self, *args, **kwargs):
        """
        Subscribe to channels. Channels supplied as keyword arguments expect
        a channel name as the key and a callable as the value. A channel's
        callable will be invoked automatically when a message is received on
        that channel rather than producing a message via ``listen()`` or
        ``get_message()``.
        """
        if args:
            args = list_or_args(args[0], args[1:])
        new_channels = {}
        new_channels.update(dict.fromkeys(imap(self.encode, args)))
        for channel, handler in iteritems(kwargs):
            new_channels[self.encode(channel)] = handler
        ret_val = self.execute_command('SUBSCRIBE', *iterkeys(new_channels))
        # update the channels dict AFTER we send the command. we don't want to
        # subscribe twice to these channels, once for the command and again
        # for the reconnection.
        self.channels.update(new_channels)
        return ret_val

    def unsubscribe(self, *args):
        """
        Unsubscribe from the supplied channels. If empty, unsubscribe from
        all channels
        """
        if args:
            args = list_or_args(args[0], args[1:])
        return self.execute_command('UNSUBSCRIBE', *args)

    def listen(self):
        "Listen for messages on channels this client has been subscribed to"
        while self.subscribed:
            response = self.handle_message(self.parse_response(block=True))
            if response is not None:
                yield response

    def get_message(self, ignore_subscribe_messages=False):
        "Get the next message if one is available, otherwise None"
        response = self.parse_response(block=False)
        if response:
            return self.handle_message(response, ignore_subscribe_messages)
        return None

    def handle_message(self, response, ignore_subscribe_messages=False):
        """
        Parses a pub/sub message. If the channel or pattern was subscribed to
        with a message handler, the handler is invoked instead of a parsed
        message being returned.
        """
        message_type = nativestr(response[0])
        if message_type == 'pmessage':
            message = {
                'type': message_type,
                'pattern': response[1],
                'channel': response[2],
                'data': response[3]
            }
        else:
            message = {
                'type': message_type,
                'pattern': None,
                'channel': response[1],
                'data': response[2]
            }

        # if this is an unsubscribe message, remove it from memory
        if message_type in self.UNSUBSCRIBE_MESSAGE_TYPES:
            subscribed_dict = None
            if message_type == 'punsubscribe':
                subscribed_dict = self.patterns
            else:
                subscribed_dict = self.channels
            try:
                del subscribed_dict[message['channel']]
            except KeyError:
                pass

        if message_type in self.PUBLISH_MESSAGE_TYPES:
            # if there's a message handler, invoke it
            handler = None
            if message_type == 'pmessage':
                handler = self.patterns.get(message['pattern'], None)
            else:
                handler = self.channels.get(message['channel'], None)
            if handler:
                handler(message)
                return None
        else:
            # this is a subscribe/unsubscribe message. ignore if we don't
            # want them
            if ignore_subscribe_messages or self.ignore_subscribe_messages:
                return None

        return message

    def run_in_thread(self, sleep_time=0):
        for channel, handler in iteritems(self.channels):
            if handler is None:
                raise PubSubError("Channel: '%s' has no handler registered")
        for pattern, handler in iteritems(self.patterns):
            if handler is None:
                raise PubSubError("Pattern: '%s' has no handler registered")
        pubsub = self

        class WorkerThread(threading.Thread):
            def __init__(self, *args, **kwargs):
                super(WorkerThread, self).__init__(*args, **kwargs)
                self._running = False

            def run(self):
                if self._running:
                    return
                self._running = True
                while self._running and pubsub.subscribed:
                    pubsub.get_message(ignore_subscribe_messages=True)
                    mod_time.sleep(sleep_time)

            def stop(self):
                self._running = False
                self.join()

        thread = WorkerThread()
        thread.start()
        return thread


class BasePipeline(object):
    """
    Pipelines provide a way to transmit multiple commands to the Redis server
    in one transmission.  This is convenient for batch processing, such as
    saving all the values in a list to Redis.

    All commands executed within a pipeline are wrapped with MULTI and EXEC
    calls. This guarantees all commands executed in the pipeline will be
    executed atomically.

    Any command raising an exception does *not* halt the execution of
    subsequent commands in the pipeline. Instead, the exception is caught
    and its instance is placed into the response list returned by execute().
    Code iterating over the response list should be able to deal with an
    instance of an exception as a potential value. In general, these will be
    ResponseError exceptions, such as those raised when issuing a command
    on a key of a different datatype.
    """

    UNWATCH_COMMANDS = set(('DISCARD', 'EXEC', 'UNWATCH'))

    def __init__(self, connection_pool, response_callbacks, transaction,
                 shard_hint):
        self.connection_pool = connection_pool
        self.connection = None
        self.response_callbacks = response_callbacks
        self.transaction = transaction
        self.shard_hint = shard_hint

        self.watching = False
        self.reset()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.reset()

    def __del__(self):
        try:
            self.reset()
        except Exception:
            pass

    def __len__(self):
        return len(self.command_stack)

    def reset(self):
        self.command_stack = []
        self.scripts = set()
        # make sure to reset the connection state in the event that we were
        # watching something
        if self.watching and self.connection:
            try:
                # call this manually since our unwatch or
                # immediate_execute_command methods can call reset()
                self.connection.send_command('UNWATCH')
                self.connection.read_response()
            except ConnectionError:
                # disconnect will also remove any previous WATCHes
                self.connection.disconnect()
        # clean up the other instance attributes
        self.watching = False
        self.explicit_transaction = False
        # we can safely return the connection to the pool here since we're
        # sure we're no longer WATCHing anything
        if self.connection:
            self.connection_pool.release(self.connection)
            self.connection = None

    def multi(self):
        """
        Start a transactional block of the pipeline after WATCH commands
        are issued. End the transactional block with `execute`.
        """
        if self.explicit_transaction:
            raise RedisError('Cannot issue nested calls to MULTI')
        if self.command_stack:
            raise RedisError('Commands without an initial WATCH have already '
                             'been issued')
        self.explicit_transaction = True

    def execute_command(self, *args, **kwargs):
        if (self.watching or args[0] == 'WATCH') and \
                not self.explicit_transaction:
            return self.immediate_execute_command(*args, **kwargs)
        return self.pipeline_execute_command(*args, **kwargs)

    def immediate_execute_command(self, *args, **options):
        """
        Execute a command immediately, but don't auto-retry on a
        ConnectionError if we're already WATCHing a variable. Used when
        issuing WATCH or subsequent commands retrieving their values but before
        MULTI is called.
        """
        command_name = args[0]
        conn = self.connection
        # if this is the first call, we need a connection
        if not conn:
            conn = self.connection_pool.get_connection(command_name,
                                                       self.shard_hint)
            self.connection = conn
        try:
            conn.send_command(*args)
            return self.parse_response(conn, command_name, **options)
        except (ConnectionError, TimeoutError) as e:
            conn.disconnect()
            if not conn.retry_on_timeout and isinstance(e, TimeoutError):
                raise
            # if we're not already watching, we can safely retry the command
            try:
                if not self.watching:
                    conn.send_command(*args)
                    return self.parse_response(conn, command_name, **options)
            except ConnectionError:
                # the retry failed so cleanup.
                conn.disconnect()
                self.reset()
                raise

    def pipeline_execute_command(self, *args, **options):
        """
        Stage a command to be executed when execute() is next called

        Returns the current Pipeline object back so commands can be
        chained together, such as:

        pipe = pipe.set('foo', 'bar').incr('baz').decr('bang')

        At some other point, you can then run: pipe.execute(),
        which will execute all commands queued in the pipe.
        """
        self.command_stack.append((args, options))
        return self

    def _execute_transaction(self, connection, commands, raise_on_error):
        cmds = chain([(('MULTI', ), {})], commands, [(('EXEC', ), {})])
        all_cmds = chain.from_iterable(
            starmap(connection.pack_command,
                    [args for args, options in cmds]))
        connection.send_packed_command(all_cmds)
        errors = []

        # parse off the response for MULTI
        # NOTE: we need to handle ResponseErrors here and continue
        # so that we read all the additional command messages from
        # the socket
        try:
            self.parse_response(connection, '_')
        except ResponseError:
            errors.append((0, sys.exc_info()[1]))

        # and all the other commands
        for i, command in enumerate(commands):
            try:
                self.parse_response(connection, '_')
            except ResponseError:
                ex = sys.exc_info()[1]
                self.annotate_exception(ex, i + 1, command[0])
                errors.append((i, ex))

        # parse the EXEC.
        try:
            response = self.parse_response(connection, '_')
        except ExecAbortError:
            if self.explicit_transaction:
                self.immediate_execute_command('DISCARD')
            if errors:
                raise errors[0][1]
            raise sys.exc_info()[1]

        if response is None:
            raise WatchError("Watched variable changed.")

        # put any parse errors into the response
        for i, e in errors:
            response.insert(i, e)

        if len(response) != len(commands):
            self.connection.disconnect()
            raise ResponseError("Wrong number of response items from "
                                "pipeline execution")

        # find any errors in the response and raise if necessary
        if raise_on_error:
            self.raise_first_error(commands, response)

        # We have to run response callbacks manually
        data = []
        for r, cmd in izip(response, commands):
            if not isinstance(r, Exception):
                args, options = cmd
                command_name = args[0]
                if command_name in self.response_callbacks:
                    r = self.response_callbacks[command_name](r, **options)
            data.append(r)
        return data

    def _execute_pipeline(self, connection, commands, raise_on_error):
        # build up all commands into a single request to increase network perf
        all_cmds = chain.from_iterable(
            starmap(connection.pack_command,
                    [args for args, options in commands]))
        connection.send_packed_command(all_cmds)

        response = []
        for args, options in commands:
            try:
                response.append(
                    self.parse_response(connection, args[0], **options))
            except ResponseError:
                response.append(sys.exc_info()[1])

        if raise_on_error:
            self.raise_first_error(commands, response)
        return response

    def raise_first_error(self, commands, response):
        for i, r in enumerate(response):
            if isinstance(r, ResponseError):
                self.annotate_exception(r, i + 1, commands[i][0])
                raise r

    def annotate_exception(self, exception, number, command):
        cmd = unicode(' ').join(imap(unicode, command))
        msg = unicode('Command # %d (%s) of pipeline caused error: %s') % (
            number, cmd, unicode(exception.args[0]))
        exception.args = (msg,) + exception.args[1:]

    def parse_response(self, connection, command_name, **options):
        result = StrictRedis.parse_response(
            self, connection, command_name, **options)
        if command_name in self.UNWATCH_COMMANDS:
            self.watching = False
        elif command_name == 'WATCH':
            self.watching = True
        return result

    def load_scripts(self):
        # make sure all scripts that are about to be run on this pipeline exist
        scripts = list(self.scripts)
        immediate = self.immediate_execute_command
        shas = [s.sha for s in scripts]
        # we can't use the normal script_* methods because they would just
        # get buffered in the pipeline.
        exists = immediate('SCRIPT', 'EXISTS', *shas, **{'parse': 'EXISTS'})
        if not all(exists):
            for s, exist in izip(scripts, exists):
                if not exist:
                    s.sha = immediate('SCRIPT', 'LOAD', s.script,
                                      **{'parse': 'LOAD'})

    def execute(self, raise_on_error=True):
        "Execute all the commands in the current pipeline"
        stack = self.command_stack
        if not stack:
            return []
        if self.scripts:
            self.load_scripts()
        if self.transaction or self.explicit_transaction:
            execute = self._execute_transaction
        else:
            execute = self._execute_pipeline

        conn = self.connection
        if not conn:
            conn = self.connection_pool.get_connection('MULTI',
                                                       self.shard_hint)
            # assign to self.connection so reset() releases the connection
            # back to the pool after we're done
            self.connection = conn

        try:
            return execute(conn, stack, raise_on_error)
        except (ConnectionError, TimeoutError) as e:
            conn.disconnect()
            if not conn.retry_on_timeout and isinstance(e, TimeoutError):
                raise
            # if we were watching a variable, the watch is no longer valid
            # since this connection has died. raise a WatchError, which
            # indicates the user should retry his transaction. If this is more
            # than a temporary failure, the WATCH that the user next issues
            # will fail, propegating the real ConnectionError
            if self.watching:
                raise WatchError("A ConnectionError occured on while watching "
                                 "one or more keys")
            # otherwise, it's safe to retry since the transaction isn't
            # predicated on any state
            return execute(conn, stack, raise_on_error)
        finally:
            self.reset()

    def watch(self, *names):
        "Watches the values at keys ``names``"
        if self.explicit_transaction:
            raise RedisError('Cannot issue a WATCH after a MULTI')
        return self.execute_command('WATCH', *names)

    def unwatch(self):
        "Unwatches all previously specified keys"
        return self.watching and self.execute_command('UNWATCH') or True

    def script_load_for_pipeline(self, script):
        "Make sure scripts are loaded prior to pipeline execution"
        # we need the sha now so that Script.__call__ can use it to run
        # evalsha.
        if not script.sha:
            script.sha = self.immediate_execute_command('SCRIPT', 'LOAD',
                                                        script.script,
                                                        **{'parse': 'LOAD'})
        self.scripts.add(script)


class StrictPipeline(BasePipeline, StrictRedis):
    "Pipeline for the StrictRedis class"
    pass


class Pipeline(BasePipeline, Redis):
    "Pipeline for the Redis class"
    pass


class Script(object):
    "An executable Lua script object returned by ``register_script``"

    def __init__(self, registered_client, script):
        self.registered_client = registered_client
        self.script = script
        self.sha = ''

    def __call__(self, keys=[], args=[], client=None):
        "Execute the script, passing any required ``args``"
        if client is None:
            client = self.registered_client
        args = tuple(keys) + tuple(args)
        # make sure the Redis server knows about the script
        if isinstance(client, BasePipeline):
            # make sure this script is good to go on pipeline
            client.script_load_for_pipeline(self)
        try:
            return client.evalsha(self.sha, len(keys), *args)
        except NoScriptError:
            # Maybe the client is pointed to a differnet server than the client
            # that created this instance?
            self.sha = client.script_load(self.script)
            return client.evalsha(self.sha, len(keys), *args)


class LockError(RedisError):
    "Errors thrown from the Lock"
    pass


class Lock(object):
    """
    A shared, distributed Lock. Using Redis for locking allows the Lock
    to be shared across processes and/or machines.

    It's left to the user to resolve deadlock issues and make sure
    multiple clients play nicely together.
    """

    LOCK_FOREVER = float(2 ** 31 + 1)  # 1 past max unix time

    def __init__(self, redis, name, timeout=None, sleep=0.1):
        """
        Create a new Lock instance named ``name`` using the Redis client
        supplied by ``redis``.

        ``timeout`` indicates a maximum life for the lock.
        By default, it will remain locked until release() is called.

        ``sleep`` indicates the amount of time to sleep per loop iteration
        when the lock is in blocking mode and another client is currently
        holding the lock.

        Note: If using ``timeout``, you should make sure all the hosts
        that are running clients have their time synchronized with a network
        time service like ntp.
        """
        self.redis = redis
        self.name = name
        self.acquired_until = None
        self.timeout = timeout
        self.sleep = sleep
        if self.timeout and self.sleep > self.timeout:
            raise LockError("'sleep' must be less than 'timeout'")

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def acquire(self, blocking=True):
        """
        Use Redis to hold a shared, distributed lock named ``name``.
        Returns True once the lock is acquired.

        If ``blocking`` is False, always return immediately. If the lock
        was acquired, return True, otherwise return False.
        """
        sleep = self.sleep
        timeout = self.timeout
        while 1:
            unixtime = mod_time.time()
            if timeout:
                timeout_at = unixtime + timeout
            else:
                timeout_at = Lock.LOCK_FOREVER
            timeout_at = float(timeout_at)
            if self.redis.setnx(self.name, timeout_at):
                self.acquired_until = timeout_at
                return True
            # We want blocking, but didn't acquire the lock
            # check to see if the current lock is expired
            existing = float(self.redis.get(self.name) or 1)
            if existing < unixtime:
                # the previous lock is expired, attempt to overwrite it
                existing = float(self.redis.getset(self.name, timeout_at) or 1)
                if existing < unixtime:
                    # we successfully acquired the lock
                    self.acquired_until = timeout_at
                    return True
            if not blocking:
                return False
            mod_time.sleep(sleep)

    def release(self):
        "Releases the already acquired lock"
        if self.acquired_until is None:
            raise ValueError("Cannot release an unlocked lock")
        existing = float(self.redis.get(self.name) or 1)
        # if the lock time is in the future, delete the lock
        delete_lock = existing >= self.acquired_until
        self.acquired_until = None
        if delete_lock:
            self.redis.delete(self.name)

########NEW FILE########
__FILENAME__ = connection
from __future__ import with_statement
from distutils.version import StrictVersion
from itertools import chain
from select import select
import os
import socket
import sys
import threading
import warnings

try:
    import ssl
    ssl_available = True
except ImportError:
    ssl_available = False

from redis._compat import (b, xrange, imap, byte_to_chr, unicode, bytes, long,
                           BytesIO, nativestr, basestring, iteritems,
                           LifoQueue, Empty, Full, urlparse, parse_qs)
from redis.exceptions import (
    RedisError,
    ConnectionError,
    TimeoutError,
    BusyLoadingError,
    ResponseError,
    InvalidResponse,
    AuthenticationError,
    NoScriptError,
    ExecAbortError,
    ReadOnlyError
)
from redis.utils import HIREDIS_AVAILABLE
if HIREDIS_AVAILABLE:
    import hiredis

    hiredis_version = StrictVersion(hiredis.__version__)
    HIREDIS_SUPPORTS_CALLABLE_ERRORS = \
        hiredis_version >= StrictVersion('0.1.3')

    if not HIREDIS_SUPPORTS_CALLABLE_ERRORS:
        msg = ("redis-py works best with hiredis >= 0.1.3. You're running "
               "hiredis %s. Please consider upgrading." % hiredis.__version__)
        warnings.warn(msg)

SYM_STAR = b('*')
SYM_DOLLAR = b('$')
SYM_CRLF = b('\r\n')
SYM_EMPTY = b('')


class Token(object):
    """
    Literal strings in Redis commands, such as the command names and any
    hard-coded arguments are wrapped in this class so we know not to apply
    and encoding rules on them.
    """
    def __init__(self, value):
        if isinstance(value, Token):
            value = value.value
        self.value = value

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


class BaseParser(object):
    EXCEPTION_CLASSES = {
        'ERR': ResponseError,
        'EXECABORT': ExecAbortError,
        'LOADING': BusyLoadingError,
        'NOSCRIPT': NoScriptError,
        'READONLY': ReadOnlyError,
    }

    def parse_error(self, response):
        "Parse an error response"
        error_code = response.split(' ')[0]
        if error_code in self.EXCEPTION_CLASSES:
            response = response[len(error_code) + 1:]
            return self.EXCEPTION_CLASSES[error_code](response)
        return ResponseError(response)


class SocketBuffer(object):
    def __init__(self, socket, socket_read_size):
        self._sock = socket
        self.socket_read_size = socket_read_size
        self._buffer = BytesIO()
        # number of bytes written to the buffer from the socket
        self.bytes_written = 0
        # number of bytes read from the buffer
        self.bytes_read = 0

    @property
    def length(self):
        return self.bytes_written - self.bytes_read

    def _read_from_socket(self, length=None):
        socket_read_size = self.socket_read_size
        buf = self._buffer
        buf.seek(self.bytes_written)
        marker = 0

        try:
            while True:
                data = self._sock.recv(socket_read_size)
                # an empty string indicates the server shutdown the socket
                if isinstance(data, str) and len(data) == 0:
                    raise socket.error("Connection closed by remote server.")
                buf.write(data)
                data_length = len(data)
                self.bytes_written += data_length
                marker += data_length

                if length is not None and length > marker:
                    continue
                break
        except socket.timeout:
            raise TimeoutError("Timeout reading from socket")
        except socket.error:
            e = sys.exc_info()[1]
            raise ConnectionError("Error while reading from socket: %s" %
                                  (e.args,))

    def read(self, length):
        length = length + 2  # make sure to read the \r\n terminator
        # make sure we've read enough data from the socket
        if length > self.length:
            self._read_from_socket(length - self.length)

        self._buffer.seek(self.bytes_read)
        data = self._buffer.read(length)
        self.bytes_read += len(data)

        # purge the buffer when we've consumed it all so it doesn't
        # grow forever
        if self.bytes_read == self.bytes_written:
            self.purge()

        return data[:-2]

    def readline(self):
        buf = self._buffer
        buf.seek(self.bytes_read)
        data = buf.readline()
        while not data.endswith(SYM_CRLF):
            # there's more data in the socket that we need
            self._read_from_socket()
            buf.seek(self.bytes_read)
            data = buf.readline()

        self.bytes_read += len(data)

        # purge the buffer when we've consumed it all so it doesn't
        # grow forever
        if self.bytes_read == self.bytes_written:
            self.purge()

        return data[:-2]

    def purge(self):
        self._buffer.seek(0)
        self._buffer.truncate()
        self.bytes_written = 0
        self.bytes_read = 0

    def close(self):
        self.purge()
        self._buffer.close()
        self._buffer = None
        self._sock = None


class PythonParser(BaseParser):
    "Plain Python parsing class"
    encoding = None

    def __init__(self, socket_read_size):
        self.socket_read_size = socket_read_size
        self._sock = None
        self._buffer = None

    def __del__(self):
        try:
            self.on_disconnect()
        except Exception:
            pass

    def on_connect(self, connection):
        "Called when the socket connects"
        self._sock = connection._sock
        self._buffer = SocketBuffer(self._sock, self.socket_read_size)
        if connection.decode_responses:
            self.encoding = connection.encoding

    def on_disconnect(self):
        "Called when the socket disconnects"
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        if self._buffer is not None:
            self._buffer.close()
            self._buffer = None
        self.encoding = None

    def can_read(self):
        return self._buffer and bool(self._buffer.length)

    def read_response(self):
        response = self._buffer.readline()
        if not response:
            raise ConnectionError("Socket closed on remote end")

        byte, response = byte_to_chr(response[0]), response[1:]

        if byte not in ('-', '+', ':', '$', '*'):
            raise InvalidResponse("Protocol Error: %s, %s" %
                                  (str(byte), str(response)))

        # server returned an error
        if byte == '-':
            response = nativestr(response)
            error = self.parse_error(response)
            # if the error is a ConnectionError, raise immediately so the user
            # is notified
            if isinstance(error, ConnectionError):
                raise error
            # otherwise, we're dealing with a ResponseError that might belong
            # inside a pipeline response. the connection's read_response()
            # and/or the pipeline's execute() will raise this error if
            # necessary, so just return the exception instance here.
            return error
        # single value
        elif byte == '+':
            pass
        # int value
        elif byte == ':':
            response = long(response)
        # bulk response
        elif byte == '$':
            length = int(response)
            if length == -1:
                return None
            response = self._buffer.read(length)
        # multi-bulk response
        elif byte == '*':
            length = int(response)
            if length == -1:
                return None
            response = [self.read_response() for i in xrange(length)]
        if isinstance(response, bytes) and self.encoding:
            response = response.decode(self.encoding)
        return response


class HiredisParser(BaseParser):
    "Parser class for connections using Hiredis"
    def __init__(self, socket_read_size):
        if not HIREDIS_AVAILABLE:
            raise RedisError("Hiredis is not installed")
        self.socket_read_size = socket_read_size

    def __del__(self):
        try:
            self.on_disconnect()
        except Exception:
            pass

    def on_connect(self, connection):
        self._sock = connection._sock
        kwargs = {
            'protocolError': InvalidResponse,
            'replyError': self.parse_error,
        }

        # hiredis < 0.1.3 doesn't support functions that create exceptions
        if not HIREDIS_SUPPORTS_CALLABLE_ERRORS:
            kwargs['replyError'] = ResponseError

        if connection.decode_responses:
            kwargs['encoding'] = connection.encoding
        self._reader = hiredis.Reader(**kwargs)
        self._next_response = False

    def on_disconnect(self):
        self._sock = None
        self._reader = None
        self._next_response = False

    def can_read(self):
        if not self._reader:
            raise ConnectionError("Socket closed on remote end")

        if self._next_response is False:
            self._next_response = self._reader.gets()
        return self._next_response is not False

    def read_response(self):
        if not self._reader:
            raise ConnectionError("Socket closed on remote end")

        # _next_response might be cached from a can_read() call
        if self._next_response is not False:
            response = self._next_response
            self._next_response = False
            return response

        response = self._reader.gets()
        socket_read_size = self.socket_read_size
        while response is False:
            try:
                buffer = self._sock.recv(socket_read_size)
                # an empty string indicates the server shutdown the socket
                if isinstance(buffer, str) and len(buffer) == 0:
                    raise socket.error("Connection closed by remote server.")
            except socket.timeout:
                raise TimeoutError("Timeout reading from socket")
            except socket.error:
                e = sys.exc_info()[1]
                raise ConnectionError("Error while reading from socket: %s" %
                                      (e.args,))
            if not buffer:
                raise ConnectionError("Socket closed on remote end")
            self._reader.feed(buffer)
            # proactively, but not conclusively, check if more data is in the
            # buffer. if the data received doesn't end with \r\n, there's more.
            if not buffer.endswith(SYM_CRLF):
                continue
            response = self._reader.gets()
        # if an older version of hiredis is installed, we need to attempt
        # to convert ResponseErrors to their appropriate types.
        if not HIREDIS_SUPPORTS_CALLABLE_ERRORS:
            if isinstance(response, ResponseError):
                response = self.parse_error(response.args[0])
            elif isinstance(response, list) and response and \
                    isinstance(response[0], ResponseError):
                response[0] = self.parse_error(response[0].args[0])
        # if the response is a ConnectionError or the response is a list and
        # the first item is a ConnectionError, raise it as something bad
        # happened
        if isinstance(response, ConnectionError):
            raise response
        elif isinstance(response, list) and response and \
                isinstance(response[0], ConnectionError):
            raise response[0]
        return response

if HIREDIS_AVAILABLE:
    DefaultParser = HiredisParser
else:
    DefaultParser = PythonParser


class Connection(object):
    "Manages TCP communication to and from a Redis server"
    description_format = "Connection<host=%(host)s,port=%(port)s,db=%(db)s>"

    def __init__(self, host='localhost', port=6379, db=0, password=None,
                 socket_timeout=None, socket_connect_timeout=None,
                 socket_keepalive=False, socket_keepalive_options=None,
                 retry_on_timeout=False, encoding='utf-8',
                 encoding_errors='strict', decode_responses=False,
                 parser_class=DefaultParser, socket_read_size=65536):
        self.pid = os.getpid()
        self.host = host
        self.port = int(port)
        self.db = db
        self.password = password
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout or socket_timeout
        self.socket_keepalive = socket_keepalive
        self.socket_keepalive_options = socket_keepalive_options or {}
        self.retry_on_timeout = retry_on_timeout
        self.encoding = encoding
        self.encoding_errors = encoding_errors
        self.decode_responses = decode_responses
        self._sock = None
        self._parser = parser_class(socket_read_size=socket_read_size)
        self._description_args = {
            'host': self.host,
            'port': self.port,
            'db': self.db,
        }
        self._connect_callbacks = []

    def __repr__(self):
        return self.description_format % self._description_args

    def __del__(self):
        try:
            self.disconnect()
        except Exception:
            pass

    def register_connect_callback(self, callback):
        self._connect_callbacks.append(callback)

    def clear_connect_callbacks(self):
        self._connect_callbacks = []

    def connect(self):
        "Connects to the Redis server if not already connected"
        if self._sock:
            return
        try:
            sock = self._connect()
        except socket.error:
            e = sys.exc_info()[1]
            raise ConnectionError(self._error_message(e))

        self._sock = sock
        try:
            self.on_connect()
        except RedisError:
            # clean up after any error in on_connect
            self.disconnect()
            raise

        # run any user callbacks. right now the only internal callback
        # is for pubsub channel/pattern resubscription
        for callback in self._connect_callbacks:
            callback(self)

    def _connect(self):
        "Create a TCP socket connection"
        # we want to mimic what socket.create_connection does to support
        # ipv4/ipv6, but we want to set options prior to calling
        # socket.connect()
        err = None
        for res in socket.getaddrinfo(self.host, self.port, 0,
                                      socket.SOCK_STREAM):
            family, socktype, proto, canonname, socket_address = res
            sock = None
            try:
                sock = socket.socket(family, socktype, proto)
                # TCP_NODELAY
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                # TCP_KEEPALIVE
                if self.socket_keepalive:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    for k, v in iteritems(self.socket_keepalive_options):
                        sock.setsockopt(socket.SOL_TCP, k, v)

                # set the socket_connect_timeout before we connect
                sock.settimeout(self.socket_connect_timeout)

                # connect
                sock.connect(socket_address)

                # set the socket_timeout now that we're connected
                sock.settimeout(self.socket_timeout)
                return sock

            except socket.error as _:
                err = _
                if sock is not None:
                    sock.close()

        if err is not None:
            raise err
        raise socket.error("socket.getaddrinfo returned an empty list")

    def _error_message(self, exception):
        # args for socket.error can either be (errno, "message")
        # or just "message"
        if len(exception.args) == 1:
            return "Error connecting to %s:%s. %s." % \
                (self.host, self.port, exception.args[0])
        else:
            return "Error %s connecting to %s:%s. %s." % \
                (exception.args[0], self.host, self.port, exception.args[1])

    def on_connect(self):
        "Initialize the connection, authenticate and select a database"
        self._parser.on_connect(self)

        # if a password is specified, authenticate
        if self.password:
            self.send_command('AUTH', self.password)
            if nativestr(self.read_response()) != 'OK':
                raise AuthenticationError('Invalid Password')

        # if a database is specified, switch to it
        if self.db:
            self.send_command('SELECT', self.db)
            if nativestr(self.read_response()) != 'OK':
                raise ConnectionError('Invalid Database')

    def disconnect(self):
        "Disconnects from the Redis server"
        self._parser.on_disconnect()
        if self._sock is None:
            return
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
        except socket.error:
            pass
        self._sock = None

    def send_packed_command(self, command):
        "Send an already packed command to the Redis server"
        if not self._sock:
            self.connect()
        try:
            if isinstance(command, str):
                command = [command]
            for item in command:
                self._sock.sendall(item)
        except socket.timeout:
            self.disconnect()
            raise TimeoutError("Timeout writing to socket")
        except socket.error:
            e = sys.exc_info()[1]
            self.disconnect()
            if len(e.args) == 1:
                _errno, errmsg = 'UNKNOWN', e.args[0]
            else:
                _errno, errmsg = e.args
            raise ConnectionError("Error %s while writing to socket. %s." %
                                  (_errno, errmsg))
        except:
            self.disconnect()
            raise

    def send_command(self, *args):
        "Pack and send a command to the Redis server"
        self.send_packed_command(self.pack_command(*args))

    def can_read(self):
        "Poll the socket to see if there's data that can be read."
        sock = self._sock
        if not sock:
            self.connect()
            sock = self._sock
        return bool(select([sock], [], [], 0)[0]) or self._parser.can_read()

    def read_response(self):
        "Read the response from a previously sent command"
        try:
            response = self._parser.read_response()
        except:
            self.disconnect()
            raise
        if isinstance(response, ResponseError):
            raise response
        return response

    def encode(self, value):
        "Return a bytestring representation of the value"
        if isinstance(value, Token):
            return b(value.value)
        elif isinstance(value, bytes):
            return value
        elif isinstance(value, (int, long)):
            value = b(str(value))
        elif isinstance(value, float):
            value = b(repr(value))
        elif not isinstance(value, basestring):
            value = str(value)
        if isinstance(value, unicode):
            value = value.encode(self.encoding, self.encoding_errors)
        return value

    def pack_command(self, *args):
        "Pack a series of arguments into the Redis protocol"
        output = []
        # the client might have included 1 or more literal arguments in
        # the command name, e.g., 'CONFIG GET'. The Redis server expects these
        # arguments to be sent separately, so split the first argument
        # manually. All of these arguements get wrapped in the Token class
        # to prevent them from being encoded.
        command = args[0]
        if ' ' in command:
            args = tuple([Token(s) for s in command.split(' ')]) + args[1:]
        else:
            args = (Token(command),) + args[1:]

        buff = SYM_EMPTY.join(
            (SYM_STAR, b(str(len(args))), SYM_CRLF))

        for arg in imap(self.encode, args):
            # to avoid large string mallocs, chunk the command into the
            # output list if we're sending large values
            if len(buff) > 6000 or len(arg) > 6000:
                buff = SYM_EMPTY.join(
                    (buff, SYM_DOLLAR, b(str(len(arg))), SYM_CRLF))
                output.append(buff)
                output.append(arg)
                buff = SYM_CRLF
            else:
                buff = SYM_EMPTY.join((buff, SYM_DOLLAR, b(str(len(arg))),
                                       SYM_CRLF, arg, SYM_CRLF))
        output.append(buff)
        return output


class SSLConnection(Connection):
    description_format = "SSLConnection<host=%(host)s,port=%(port)s,db=%(db)s>"

    def __init__(self, ssl_keyfile=None, ssl_certfile=None, ssl_cert_reqs=None,
                 ssl_ca_certs=None, **kwargs):
        if not ssl_available:
            raise RedisError("Python wasn't built with SSL support")

        super(SSLConnection, self).__init__(**kwargs)

        self.keyfile = ssl_keyfile
        self.certfile = ssl_certfile
        if ssl_cert_reqs is None:
            ssl_cert_reqs = ssl.CERT_NONE
        elif isinstance(ssl_cert_reqs, basestring):
            CERT_REQS = {
                'none': ssl.CERT_NONE,
                'optional': ssl.CERT_OPTIONAL,
                'required': ssl.CERT_REQUIRED
            }
            if ssl_cert_reqs not in CERT_REQS:
                raise RedisError(
                    "Invalid SSL Certificate Requirements Flag: %s" %
                    ssl_cert_reqs)
            ssl_cert_reqs = CERT_REQS[ssl_cert_reqs]
        self.cert_reqs = ssl_cert_reqs
        self.ca_certs = ssl_ca_certs

    def _connect(self):
        "Wrap the socket with SSL support"
        sock = super(SSLConnection, self)._connect()
        sock = ssl.wrap_socket(sock,
                               cert_reqs=self.cert_reqs,
                               keyfile=self.keyfile,
                               certfile=self.certfile,
                               ca_certs=self.ca_certs)
        return sock


class UnixDomainSocketConnection(Connection):
    description_format = "UnixDomainSocketConnection<path=%(path)s,db=%(db)s>"

    def __init__(self, path='', db=0, password=None,
                 socket_timeout=None, encoding='utf-8',
                 encoding_errors='strict', decode_responses=False,
                 retry_on_timeout=False,
                 parser_class=DefaultParser, socket_read_size=65536):
        self.pid = os.getpid()
        self.path = path
        self.db = db
        self.password = password
        self.socket_timeout = socket_timeout
        self.retry_on_timeout = retry_on_timeout
        self.encoding = encoding
        self.encoding_errors = encoding_errors
        self.decode_responses = decode_responses
        self._sock = None
        self._parser = parser_class(socket_read_size=socket_read_size)
        self._description_args = {
            'path': self.path,
            'db': self.db,
        }
        self._connect_callbacks = []

    def _connect(self):
        "Create a Unix domain socket connection"
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.socket_timeout)
        sock.connect(self.path)
        return sock

    def _error_message(self, exception):
        # args for socket.error can either be (errno, "message")
        # or just "message"
        if len(exception.args) == 1:
            return "Error connecting to unix socket: %s. %s." % \
                (self.path, exception.args[0])
        else:
            return "Error %s connecting to unix socket: %s. %s." % \
                (exception.args[0], self.path, exception.args[1])


class ConnectionPool(object):
    "Generic connection pool"
    @classmethod
    def from_url(cls, url, db=None, **kwargs):
        """
        Return a connection pool configured from the given URL.

        For example::

            redis://[:password]@localhost:6379/0
            rediss://[:password]@localhost:6379/0
            unix://[:password]@/path/to/socket.sock?db=0

        Three URL schemes are supported:
            redis:// creates a normal TCP socket connection
            rediss:// creates a SSL wrapped TCP socket connection
            unix:// creates a Unix Domain Socket connection

        There are several ways to specify a database number. The parse function
        will return the first specified option:
            1. A ``db`` querystring option, e.g. redis://localhost?db=0
            2. If using the redis:// scheme, the path argument of the url, e.g.
               redis://localhost/0
            3. The ``db`` argument to this function.

        If none of these options are specified, db=0 is used.

        Any additional querystring arguments and keyword arguments will be
        passed along to the ConnectionPool class's initializer. In the case
        of conflicting arguments, querystring arguments always win.
        """
        url_string = url
        url = urlparse(url)
        qs = ''

        # in python2.6, custom URL schemes don't recognize querystring values
        # they're left as part of the url.path.
        if '?' in url.path and not url.query:
            # chop the querystring including the ? off the end of the url
            # and reparse it.
            qs = url.path.split('?', 1)[1]
            url = urlparse(url_string[:-(len(qs) + 1)])
        else:
            qs = url.query

        url_options = {}

        for name, value in iteritems(parse_qs(qs)):
            if value and len(value) > 0:
                url_options[name] = value[0]

        # We only support redis:// and unix:// schemes.
        if url.scheme == 'unix':
            url_options.update({
                'password': url.password,
                'path': url.path,
                'connection_class': UnixDomainSocketConnection,
            })

        else:
            url_options.update({
                'host': url.hostname,
                'port': int(url.port or 6379),
                'password': url.password,
            })

            # If there's a path argument, use it as the db argument if a
            # querystring value wasn't specified
            if 'db' not in url_options and url.path:
                try:
                    url_options['db'] = int(url.path.replace('/', ''))
                except (AttributeError, ValueError):
                    pass

            if url.scheme == 'rediss':
                url_options['connection_class'] = SSLConnection

        # last shot at the db value
        url_options['db'] = int(url_options.get('db', db or 0))

        # update the arguments from the URL values
        kwargs.update(url_options)
        return cls(**kwargs)

    def __init__(self, connection_class=Connection, max_connections=None,
                 **connection_kwargs):
        """
        Create a connection pool. If max_connections is set, then this
        object raises redis.ConnectionError when the pool's limit is reached.

        By default, TCP connections are created connection_class is specified.
        Use redis.UnixDomainSocketConnection for unix sockets.

        Any additional keyword arguments are passed to the constructor of
        connection_class.
        """
        max_connections = max_connections or 2 ** 31
        if not isinstance(max_connections, (int, long)) or max_connections < 0:
            raise ValueError('"max_connections" must be a positive integer')

        self.connection_class = connection_class
        self.connection_kwargs = connection_kwargs
        self.max_connections = max_connections

        self.reset()

    def __repr__(self):
        return "%s<%s>" % (
            type(self).__name__,
            self.connection_class.description_format % self.connection_kwargs,
        )

    def reset(self):
        self.pid = os.getpid()
        self._created_connections = 0
        self._available_connections = []
        self._in_use_connections = set()
        self._check_lock = threading.Lock()

    def _checkpid(self):
        if self.pid != os.getpid():
            with self._check_lock:
                if self.pid == os.getpid():
                    # another thread already did the work while we waited
                    # on the lock.
                    return
                self.disconnect()
                self.reset()

    def get_connection(self, command_name, *keys, **options):
        "Get a connection from the pool"
        self._checkpid()
        try:
            connection = self._available_connections.pop()
        except IndexError:
            connection = self.make_connection()
        self._in_use_connections.add(connection)
        return connection

    def make_connection(self):
        "Create a new connection"
        if self._created_connections >= self.max_connections:
            raise ConnectionError("Too many connections")
        self._created_connections += 1
        return self.connection_class(**self.connection_kwargs)

    def release(self, connection):
        "Releases the connection back to the pool"
        self._checkpid()
        if connection.pid != self.pid:
            return
        self._in_use_connections.remove(connection)
        self._available_connections.append(connection)

    def disconnect(self):
        "Disconnects all connections in the pool"
        all_conns = chain(self._available_connections,
                          self._in_use_connections)
        for connection in all_conns:
            connection.disconnect()


class BlockingConnectionPool(ConnectionPool):
    """
    Thread-safe blocking connection pool::

        >>> from redis.client import Redis
        >>> client = Redis(connection_pool=BlockingConnectionPool())

    It performs the same function as the default
    ``:py:class: ~redis.connection.ConnectionPool`` implementation, in that,
    it maintains a pool of reusable connections that can be shared by
    multiple redis clients (safely across threads if required).

    The difference is that, in the event that a client tries to get a
    connection from the pool when all of connections are in use, rather than
    raising a ``:py:class: ~redis.exceptions.ConnectionError`` (as the default
    ``:py:class: ~redis.connection.ConnectionPool`` implementation does), it
    makes the client wait ("blocks") for a specified number of seconds until
    a connection becomes available.

    Use ``max_connections`` to increase / decrease the pool size::

        >>> pool = BlockingConnectionPool(max_connections=10)

    Use ``timeout`` to tell it either how many seconds to wait for a connection
    to become available, or to block forever:

        # Block forever.
        >>> pool = BlockingConnectionPool(timeout=None)

        # Raise a ``ConnectionError`` after five seconds if a connection is
        # not available.
        >>> pool = BlockingConnectionPool(timeout=5)
    """
    def __init__(self, max_connections=50, timeout=20,
                 connection_class=Connection, queue_class=LifoQueue,
                 **connection_kwargs):

        self.queue_class = queue_class
        self.timeout = timeout
        super(BlockingConnectionPool, self).__init__(
            connection_class=connection_class,
            max_connections=max_connections,
            **connection_kwargs)

    def reset(self):
        self.pid = os.getpid()
        self._check_lock = threading.Lock()

        # Create and fill up a thread safe queue with ``None`` values.
        self.pool = self.queue_class(self.max_connections)
        while True:
            try:
                self.pool.put_nowait(None)
            except Full:
                break

        # Keep a list of actual connection instances so that we can
        # disconnect them later.
        self._connections = []

    def make_connection(self):
        "Make a fresh connection."
        connection = self.connection_class(**self.connection_kwargs)
        self._connections.append(connection)
        return connection

    def get_connection(self, command_name, *keys, **options):
        """
        Get a connection, blocking for ``self.timeout`` until a connection
        is available from the pool.

        If the connection returned is ``None`` then creates a new connection.
        Because we use a last-in first-out queue, the existing connections
        (having been returned to the pool after the initial ``None`` values
        were added) will be returned before ``None`` values. This means we only
        create new connections when we need to, i.e.: the actual number of
        connections will only increase in response to demand.
        """
        # Make sure we haven't changed process.
        self._checkpid()

        # Try and get a connection from the pool. If one isn't available within
        # self.timeout then raise a ``ConnectionError``.
        connection = None
        try:
            connection = self.pool.get(block=True, timeout=self.timeout)
        except Empty:
            # Note that this is not caught by the redis client and will be
            # raised unless handled by application code. If you want never to
            raise ConnectionError("No connection available.")

        # If the ``connection`` is actually ``None`` then that's a cue to make
        # a new connection to add to the pool.
        if connection is None:
            connection = self.make_connection()

        return connection

    def release(self, connection):
        "Releases the connection back to the pool."
        # Make sure we haven't changed process.
        self._checkpid()
        if connection.pid != self.pid:
            return

        # Put the connection back into the pool.
        try:
            self.pool.put_nowait(connection)
        except Full:
            # perhaps the pool has been reset() after a fork? regardless,
            # we don't want this connection
            pass

    def disconnect(self):
        "Disconnects all connections in the pool."
        for connection in self._connections:
            connection.disconnect()

########NEW FILE########
__FILENAME__ = exceptions
"Core exceptions raised by the Redis client"
from redis._compat import unicode


class RedisError(Exception):
    pass


# python 2.5 doesn't implement Exception.__unicode__. Add it here to all
# our exception types
if not hasattr(RedisError, '__unicode__'):
    def __unicode__(self):
        if isinstance(self.args[0], unicode):
            return self.args[0]
        return unicode(self.args[0])
    RedisError.__unicode__ = __unicode__


class AuthenticationError(RedisError):
    pass


class ConnectionError(RedisError):
    pass


class TimeoutError(RedisError):
    pass


class BusyLoadingError(ConnectionError):
    pass


class InvalidResponse(RedisError):
    pass


class ResponseError(RedisError):
    pass


class DataError(RedisError):
    pass


class PubSubError(RedisError):
    pass


class WatchError(RedisError):
    pass


class NoScriptError(ResponseError):
    pass


class ExecAbortError(ResponseError):
    pass


class ReadOnlyError(ResponseError):
    pass

########NEW FILE########
__FILENAME__ = sentinel
import os
import random
import weakref

from redis.client import StrictRedis
from redis.connection import ConnectionPool, Connection
from redis.exceptions import ConnectionError, ResponseError, ReadOnlyError
from redis._compat import iteritems, nativestr, xrange


class MasterNotFoundError(ConnectionError):
    pass


class SlaveNotFoundError(ConnectionError):
    pass


class SentinelManagedConnection(Connection):
    def __init__(self, **kwargs):
        self.connection_pool = kwargs.pop('connection_pool')
        super(SentinelManagedConnection, self).__init__(**kwargs)

    def __repr__(self):
        pool = self.connection_pool
        s = '%s<service=%s%%s>' % (type(self).__name__, pool.service_name)
        if self.host:
            host_info = ',host=%s,port=%s' % (self.host, self.port)
            s = s % host_info
        return s

    def connect_to(self, address):
        self.host, self.port = address
        super(SentinelManagedConnection, self).connect()
        if self.connection_pool.check_connection:
            self.send_command('PING')
            if nativestr(self.read_response()) != 'PONG':
                raise ConnectionError('PING failed')

    def connect(self):
        if self._sock:
            return  # already connected
        if self.connection_pool.is_master:
            self.connect_to(self.connection_pool.get_master_address())
        else:
            for slave in self.connection_pool.rotate_slaves():
                try:
                    return self.connect_to(slave)
                except ConnectionError:
                    continue
            raise SlaveNotFoundError  # Never be here

    def send_command(self, *args):
        try:
            super(SentinelManagedConnection, self).send_command(*args)
        except ReadOnlyError:
            if self.connection_pool.is_master:
                # When talking to a master, a ReadOnlyError when likely
                # indicates that the previous master that we're still connected
                # to has been demoted to a slave and there's a new master.
                # calling disconnect will force the connection to re-query
                # sentinel during the next connect() attempt.
                self.disconnect()
                raise ConnectionError('The previous master is now a slave')
            raise


class SentinelConnectionPool(ConnectionPool):
    """
    Sentinel backed connection pool.

    If ``check_connection`` flag is set to True, SentinelManagedConnection
    sends a PING command right after establishing the connection.
    """

    def __init__(self, service_name, sentinel_manager, **kwargs):
        kwargs['connection_class'] = kwargs.get(
            'connection_class', SentinelManagedConnection)
        self.is_master = kwargs.pop('is_master', True)
        self.check_connection = kwargs.pop('check_connection', False)
        super(SentinelConnectionPool, self).__init__(**kwargs)
        self.connection_kwargs['connection_pool'] = weakref.proxy(self)
        self.service_name = service_name
        self.sentinel_manager = sentinel_manager

    def __repr__(self):
        return "%s<service=%s(%s)" % (
            type(self).__name__,
            self.service_name,
            self.is_master and 'master' or 'slave',
        )

    def reset(self):
        super(SentinelConnectionPool, self).reset()
        self.master_address = None
        self.slave_rr_counter = None

    def get_master_address(self):
        master_address = self.sentinel_manager.discover_master(
            self.service_name)
        if self.is_master:
            if self.master_address is None:
                self.master_address = master_address
            elif master_address != self.master_address:
                # Master address changed, disconnect all clients in this pool
                self.disconnect()
        return master_address

    def rotate_slaves(self):
        "Round-robin slave balancer"
        slaves = self.sentinel_manager.discover_slaves(self.service_name)
        if slaves:
            if self.slave_rr_counter is None:
                self.slave_rr_counter = random.randint(0, len(slaves) - 1)
            for _ in xrange(len(slaves)):
                self.slave_rr_counter = (
                    self.slave_rr_counter + 1) % len(slaves)
                slave = slaves[self.slave_rr_counter]
                yield slave
        # Fallback to the master connection
        try:
            yield self.get_master_address()
        except MasterNotFoundError:
            pass
        raise SlaveNotFoundError('No slave found for %r' % (self.service_name))

    def _checkpid(self):
        if self.pid != os.getpid():
            self.disconnect()
            self.reset()
            self.__init__(self.service_name, self.sentinel_manager,
                          connection_class=self.connection_class,
                          max_connections=self.max_connections,
                          **self.connection_kwargs)


class Sentinel(object):
    """
    Redis Sentinel cluster client

    >>> from redis.sentinel import Sentinel
    >>> sentinel = Sentinel([('localhost', 26379)], socket_timeout=0.1)
    >>> master = sentinel.master_for('mymaster', socket_timeout=0.1)
    >>> master.set('foo', 'bar')
    >>> slave = sentinel.slave_for('mymaster', socket_timeout=0.1)
    >>> slave.get('foo')
    'bar'

    ``sentinels`` is a list of sentinel nodes. Each node is represented by
    a pair (hostname, port).

    ``min_other_sentinels`` defined a minimum number of peers for a sentinel.
    When querying a sentinel, if it doesn't meet this threshold, responses
    from that sentinel won't be considered valid.

    ``sentinel_kwargs`` is a dictionary of connection arguments used when
    connecting to sentinel instances. Any argument that can be passed to
    a normal Redis connection can be specified here. If ``sentinel_kwargs`` is
    not specified, any socket_timeout and socket_keepalive options specified
    in ``connection_kwargs`` will be used.

    ``connection_kwargs`` are keyword arguments that will be used when
    establishing a connection to a Redis server.
    """

    def __init__(self, sentinels, min_other_sentinels=0, sentinel_kwargs=None,
                 **connection_kwargs):
        # if sentinel_kwargs isn't defined, use the socket_* options from
        # connection_kwargs
        if sentinel_kwargs is None:
            sentinel_kwargs = dict([(k, v)
                                    for k, v in iteritems(connection_kwargs)
                                    if k.startswith('socket_')
                                    ])
        self.sentinel_kwargs = sentinel_kwargs

        self.sentinels = [StrictRedis(hostname, port, **self.sentinel_kwargs)
                          for hostname, port in sentinels]
        self.min_other_sentinels = min_other_sentinels
        self.connection_kwargs = connection_kwargs

    def __repr__(self):
        sentinel_addresses = []
        for sentinel in self.sentinels:
            sentinel_addresses.append('%s:%s' % (
                sentinel.connection_pool.connection_kwargs['host'],
                sentinel.connection_pool.connection_kwargs['port'],
            ))
        return '%s<sentinels=[%s]>' % (
            type(self).__name__,
            ','.join(sentinel_addresses))

    def check_master_state(self, state, service_name):
        if not state['is_master'] or state['is_sdown'] or state['is_odown']:
            return False
        # Check if our sentinel doesn't see other nodes
        if state['num-other-sentinels'] < self.min_other_sentinels:
            return False
        return True

    def discover_master(self, service_name):
        """
        Asks sentinel servers for the Redis master's address corresponding
        to the service labeled ``service_name``.

        Returns a pair (address, port) or raises MasterNotFoundError if no
        master is found.
        """
        for sentinel_no, sentinel in enumerate(self.sentinels):
            try:
                masters = sentinel.sentinel_masters()
            except ConnectionError:
                continue
            state = masters.get(service_name)
            if state and self.check_master_state(state, service_name):
                # Put this sentinel at the top of the list
                self.sentinels[0], self.sentinels[sentinel_no] = (
                    sentinel, self.sentinels[0])
                return state['ip'], state['port']
        raise MasterNotFoundError("No master found for %r" % (service_name,))

    def filter_slaves(self, slaves):
        "Remove slaves that are in an ODOWN or SDOWN state"
        slaves_alive = []
        for slave in slaves:
            if slave['is_odown'] or slave['is_sdown']:
                continue
            slaves_alive.append((slave['ip'], slave['port']))
        return slaves_alive

    def discover_slaves(self, service_name):
        "Returns a list of alive slaves for service ``service_name``"
        for sentinel in self.sentinels:
            try:
                slaves = sentinel.sentinel_slaves(service_name)
            except (ConnectionError, ResponseError):
                continue
            slaves = self.filter_slaves(slaves)
            if slaves:
                return slaves
        return []

    def master_for(self, service_name, redis_class=StrictRedis,
                   connection_pool_class=SentinelConnectionPool, **kwargs):
        """
        Returns a redis client instance for the ``service_name`` master.

        A SentinelConnectionPool class is used to retrive the master's
        address before establishing a new connection.

        NOTE: If the master's address has changed, any cached connections to
        the old master are closed.

        By default clients will be a redis.StrictRedis instance. Specify a
        different class to the ``redis_class`` argument if you desire
        something different.

        The ``connection_pool_class`` specifies the connection pool to use.
        The SentinelConnectionPool will be used by default.

        All other keyword arguments are merged with any connection_kwargs
        passed to this class and passed to the connection pool as keyword
        arguments to be used to initialize Redis connections.
        """
        kwargs['is_master'] = True
        connection_kwargs = dict(self.connection_kwargs)
        connection_kwargs.update(kwargs)
        return redis_class(connection_pool=connection_pool_class(
            service_name, self, **connection_kwargs))

    def slave_for(self, service_name, redis_class=StrictRedis,
                  connection_pool_class=SentinelConnectionPool, **kwargs):
        """
        Returns redis client instance for the ``service_name`` slave(s).

        A SentinelConnectionPool class is used to retrive the slave's
        address before establishing a new connection.

        By default clients will be a redis.StrictRedis instance. Specify a
        different class to the ``redis_class`` argument if you desire
        something different.

        The ``connection_pool_class`` specifies the connection pool to use.
        The SentinelConnectionPool will be used by default.

        All other keyword arguments are merged with any connection_kwargs
        passed to this class and passed to the connection pool as keyword
        arguments to be used to initialize Redis connections.
        """
        kwargs['is_master'] = False
        connection_kwargs = dict(self.connection_kwargs)
        connection_kwargs.update(kwargs)
        return redis_class(connection_pool=connection_pool_class(
            service_name, self, **connection_kwargs))

########NEW FILE########
__FILENAME__ = utils
from contextlib import contextmanager


try:
    import hiredis
    HIREDIS_AVAILABLE = True
except ImportError:
    HIREDIS_AVAILABLE = False


def from_url(url, db=None, **kwargs):
    """
    Returns an active Redis client generated from the given database URL.

    Will attempt to extract the database id from the path url fragment, if
    none is provided.
    """
    from redis.client import Redis
    return Redis.from_url(url, db, **kwargs)


@contextmanager
def pipeline(redis_obj):
    p = redis_obj.pipeline()
    yield p
    p.execute()

########NEW FILE########
__FILENAME__ = _compat
"""Internal module for Python 2 backwards compatibility."""
import sys


if sys.version_info[0] < 3:
    from urlparse import parse_qs, urlparse
    from itertools import imap, izip
    from string import letters as ascii_letters
    from Queue import Queue
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

    iteritems = lambda x: x.iteritems()
    iterkeys = lambda x: x.iterkeys()
    itervalues = lambda x: x.itervalues()
    nativestr = lambda x: \
        x if isinstance(x, str) else x.encode('utf-8', 'replace')
    u = lambda x: x.decode()
    b = lambda x: x
    next = lambda x: x.next()
    byte_to_chr = lambda x: x
    unichr = unichr
    xrange = xrange
    basestring = basestring
    unicode = unicode
    bytes = str
    long = long
else:
    from urllib.parse import parse_qs, urlparse
    from io import BytesIO
    from string import ascii_letters
    from queue import Queue

    iteritems = lambda x: iter(x.items())
    iterkeys = lambda x: iter(x.keys())
    itervalues = lambda x: iter(x.values())
    byte_to_chr = lambda x: chr(x)
    nativestr = lambda x: \
        x if isinstance(x, str) else x.decode('utf-8', 'replace')
    u = lambda x: x
    b = lambda x: x.encode('latin-1') if not isinstance(x, bytes) else x
    next = next
    unichr = chr
    imap = map
    izip = zip
    xrange = range
    basestring = str
    unicode = str
    bytes = bytes
    long = int

try:  # Python 3
    from queue import LifoQueue, Empty, Full
except ImportError:
    from Queue import Empty, Full
    try:  # Python 2.6 - 2.7
        from Queue import LifoQueue
    except ImportError:  # Python 2.5
        from Queue import Queue
        # From the Python 2.7 lib. Python 2.5 already extracted the core
        # methods to aid implementating different queue organisations.

        class LifoQueue(Queue):
            "Override queue methods to implement a last-in first-out queue."

            def _init(self, maxsize):
                self.maxsize = maxsize
                self.queue = []

            def _qsize(self, len=len):
                return len(self.queue)

            def _put(self, item):
                self.queue.append(item)

            def _get(self):
                return self.queue.pop()

########NEW FILE########
__FILENAME__ = conftest
import pytest
import redis

from distutils.version import StrictVersion


_REDIS_VERSIONS = {}


def get_version(**kwargs):
    params = {'host': 'localhost', 'port': 6379, 'db': 9}
    params.update(kwargs)
    key = '%s:%s' % (params['host'], params['port'])
    if key not in _REDIS_VERSIONS:
        client = redis.Redis(**params)
        _REDIS_VERSIONS[key] = client.info()['redis_version']
        client.connection_pool.disconnect()
    return _REDIS_VERSIONS[key]


def _get_client(cls, request=None, **kwargs):
    params = {'host': 'localhost', 'port': 6379, 'db': 9}
    params.update(kwargs)
    client = cls(**params)
    client.flushdb()
    if request:
        def teardown():
            client.flushdb()
            client.connection_pool.disconnect()
        request.addfinalizer(teardown)
    return client


def skip_if_server_version_lt(min_version):
    check = StrictVersion(get_version()) < StrictVersion(min_version)
    return pytest.mark.skipif(check, reason="")


@pytest.fixture()
def r(request, **kwargs):
    return _get_client(redis.Redis, request, **kwargs)


@pytest.fixture()
def sr(request, **kwargs):
    return _get_client(redis.StrictRedis, request, **kwargs)

########NEW FILE########
__FILENAME__ = test_commands
from __future__ import with_statement
import binascii
import datetime
import pytest
import redis
import time

from redis._compat import (unichr, u, b, ascii_letters, iteritems, iterkeys,
                           itervalues)
from redis.client import parse_info
from redis import exceptions

from .conftest import skip_if_server_version_lt


@pytest.fixture()
def slowlog(request, r):
    current_config = r.config_get()
    old_slower_than_value = current_config['slowlog-log-slower-than']
    old_max_legnth_value = current_config['slowlog-max-len']

    def cleanup():
        r.config_set('slowlog-log-slower-than', old_slower_than_value)
        r.config_set('slowlog-max-len', old_max_legnth_value)
    request.addfinalizer(cleanup)

    r.config_set('slowlog-log-slower-than', 0)
    r.config_set('slowlog-max-len', 128)


def redis_server_time(client):
    seconds, milliseconds = client.time()
    timestamp = float('%s.%s' % (seconds, milliseconds))
    return datetime.datetime.fromtimestamp(timestamp)


# RESPONSE CALLBACKS
class TestResponseCallbacks(object):
    "Tests for the response callback system"

    def test_response_callbacks(self, r):
        assert r.response_callbacks == redis.Redis.RESPONSE_CALLBACKS
        assert id(r.response_callbacks) != id(redis.Redis.RESPONSE_CALLBACKS)
        r.set_response_callback('GET', lambda x: 'static')
        r['a'] = 'foo'
        assert r['a'] == 'static'


class TestRedisCommands(object):

    def test_command_on_invalid_key_type(self, r):
        r.lpush('a', '1')
        with pytest.raises(redis.ResponseError):
            r['a']

    # SERVER INFORMATION
    def test_client_list(self, r):
        clients = r.client_list()
        assert isinstance(clients[0], dict)
        assert 'addr' in clients[0]

    @skip_if_server_version_lt('2.6.9')
    def test_client_getname(self, r):
        assert r.client_getname() is None

    @skip_if_server_version_lt('2.6.9')
    def test_client_setname(self, r):
        assert r.client_setname('redis_py_test')
        assert r.client_getname() == 'redis_py_test'

    def test_config_get(self, r):
        data = r.config_get()
        assert 'maxmemory' in data
        assert data['maxmemory'].isdigit()

    def test_config_resetstat(self, r):
        r.ping()
        prior_commands_processed = int(r.info()['total_commands_processed'])
        assert prior_commands_processed >= 1
        r.config_resetstat()
        reset_commands_processed = int(r.info()['total_commands_processed'])
        assert reset_commands_processed < prior_commands_processed

    def test_config_set(self, r):
        data = r.config_get()
        rdbname = data['dbfilename']
        try:
            assert r.config_set('dbfilename', 'redis_py_test.rdb')
            assert r.config_get()['dbfilename'] == 'redis_py_test.rdb'
        finally:
            assert r.config_set('dbfilename', rdbname)

    def test_dbsize(self, r):
        r['a'] = 'foo'
        r['b'] = 'bar'
        assert r.dbsize() == 2

    def test_echo(self, r):
        assert r.echo('foo bar') == b('foo bar')

    def test_info(self, r):
        r['a'] = 'foo'
        r['b'] = 'bar'
        info = r.info()
        assert isinstance(info, dict)
        assert info['db9']['keys'] == 2

    def test_lastsave(self, r):
        assert isinstance(r.lastsave(), datetime.datetime)

    def test_object(self, r):
        r['a'] = 'foo'
        assert isinstance(r.object('refcount', 'a'), int)
        assert isinstance(r.object('idletime', 'a'), int)
        assert r.object('encoding', 'a') == b('raw')
        assert r.object('idletime', 'invalid-key') is None

    def test_ping(self, r):
        assert r.ping()

    def test_slowlog_get(self, r, slowlog):
        assert r.slowlog_reset()
        unicode_string = unichr(3456) + u('abcd') + unichr(3421)
        r.get(unicode_string)
        slowlog = r.slowlog_get()
        assert isinstance(slowlog, list)
        commands = [log['command'] for log in slowlog]

        get_command = b(' ').join((b('GET'), unicode_string.encode('utf-8')))
        assert get_command in commands
        assert b('SLOWLOG RESET') in commands
        # the order should be ['GET <uni string>', 'SLOWLOG RESET'],
        # but if other clients are executing commands at the same time, there
        # could be commands, before, between, or after, so just check that
        # the two we care about are in the appropriate order.
        assert commands.index(get_command) < commands.index(b('SLOWLOG RESET'))

        # make sure other attributes are typed correctly
        assert isinstance(slowlog[0]['start_time'], int)
        assert isinstance(slowlog[0]['duration'], int)

    def test_slowlog_get_limit(self, r, slowlog):
        assert r.slowlog_reset()
        r.get('foo')
        r.get('bar')
        slowlog = r.slowlog_get(1)
        assert isinstance(slowlog, list)
        commands = [log['command'] for log in slowlog]
        assert b('GET foo') not in commands
        assert b('GET bar') in commands

    def test_slowlog_length(self, r, slowlog):
        r.get('foo')
        assert isinstance(r.slowlog_len(), int)

    @skip_if_server_version_lt('2.6.0')
    def test_time(self, r):
        t = r.time()
        assert len(t) == 2
        assert isinstance(t[0], int)
        assert isinstance(t[1], int)

    # BASIC KEY COMMANDS
    def test_append(self, r):
        assert r.append('a', 'a1') == 2
        assert r['a'] == b('a1')
        assert r.append('a', 'a2') == 4
        assert r['a'] == b('a1a2')

    @skip_if_server_version_lt('2.6.0')
    def test_bitcount(self, r):
        r.setbit('a', 5, True)
        assert r.bitcount('a') == 1
        r.setbit('a', 6, True)
        assert r.bitcount('a') == 2
        r.setbit('a', 5, False)
        assert r.bitcount('a') == 1
        r.setbit('a', 9, True)
        r.setbit('a', 17, True)
        r.setbit('a', 25, True)
        r.setbit('a', 33, True)
        assert r.bitcount('a') == 5
        assert r.bitcount('a', 0, -1) == 5
        assert r.bitcount('a', 2, 3) == 2
        assert r.bitcount('a', 2, -1) == 3
        assert r.bitcount('a', -2, -1) == 2
        assert r.bitcount('a', 1, 1) == 1

    @skip_if_server_version_lt('2.6.0')
    def test_bitop_not_empty_string(self, r):
        r['a'] = ''
        r.bitop('not', 'r', 'a')
        assert r.get('r') is None

    @skip_if_server_version_lt('2.6.0')
    def test_bitop_not(self, r):
        test_str = b('\xAA\x00\xFF\x55')
        correct = ~0xAA00FF55 & 0xFFFFFFFF
        r['a'] = test_str
        r.bitop('not', 'r', 'a')
        assert int(binascii.hexlify(r['r']), 16) == correct

    @skip_if_server_version_lt('2.6.0')
    def test_bitop_not_in_place(self, r):
        test_str = b('\xAA\x00\xFF\x55')
        correct = ~0xAA00FF55 & 0xFFFFFFFF
        r['a'] = test_str
        r.bitop('not', 'a', 'a')
        assert int(binascii.hexlify(r['a']), 16) == correct

    @skip_if_server_version_lt('2.6.0')
    def test_bitop_single_string(self, r):
        test_str = b('\x01\x02\xFF')
        r['a'] = test_str
        r.bitop('and', 'res1', 'a')
        r.bitop('or', 'res2', 'a')
        r.bitop('xor', 'res3', 'a')
        assert r['res1'] == test_str
        assert r['res2'] == test_str
        assert r['res3'] == test_str

    @skip_if_server_version_lt('2.6.0')
    def test_bitop_string_operands(self, r):
        r['a'] = b('\x01\x02\xFF\xFF')
        r['b'] = b('\x01\x02\xFF')
        r.bitop('and', 'res1', 'a', 'b')
        r.bitop('or', 'res2', 'a', 'b')
        r.bitop('xor', 'res3', 'a', 'b')
        assert int(binascii.hexlify(r['res1']), 16) == 0x0102FF00
        assert int(binascii.hexlify(r['res2']), 16) == 0x0102FFFF
        assert int(binascii.hexlify(r['res3']), 16) == 0x000000FF

    def test_decr(self, r):
        assert r.decr('a') == -1
        assert r['a'] == b('-1')
        assert r.decr('a') == -2
        assert r['a'] == b('-2')
        assert r.decr('a', amount=5) == -7
        assert r['a'] == b('-7')

    def test_delete(self, r):
        assert r.delete('a') == 0
        r['a'] = 'foo'
        assert r.delete('a') == 1

    def test_delete_with_multiple_keys(self, r):
        r['a'] = 'foo'
        r['b'] = 'bar'
        assert r.delete('a', 'b') == 2
        assert r.get('a') is None
        assert r.get('b') is None

    def test_delitem(self, r):
        r['a'] = 'foo'
        del r['a']
        assert r.get('a') is None

    @skip_if_server_version_lt('2.6.0')
    def test_dump_and_restore(self, r):
        r['a'] = 'foo'
        dumped = r.dump('a')
        del r['a']
        r.restore('a', 0, dumped)
        assert r['a'] == b('foo')

    def test_exists(self, r):
        assert not r.exists('a')
        r['a'] = 'foo'
        assert r.exists('a')

    def test_exists_contains(self, r):
        assert 'a' not in r
        r['a'] = 'foo'
        assert 'a' in r

    def test_expire(self, r):
        assert not r.expire('a', 10)
        r['a'] = 'foo'
        assert r.expire('a', 10)
        assert 0 < r.ttl('a') <= 10
        assert r.persist('a')
        assert not r.ttl('a')

    def test_expireat_datetime(self, r):
        expire_at = redis_server_time(r) + datetime.timedelta(minutes=1)
        r['a'] = 'foo'
        assert r.expireat('a', expire_at)
        assert 0 < r.ttl('a') <= 61

    def test_expireat_no_key(self, r):
        expire_at = redis_server_time(r) + datetime.timedelta(minutes=1)
        assert not r.expireat('a', expire_at)

    def test_expireat_unixtime(self, r):
        expire_at = redis_server_time(r) + datetime.timedelta(minutes=1)
        r['a'] = 'foo'
        expire_at_seconds = int(time.mktime(expire_at.timetuple()))
        assert r.expireat('a', expire_at_seconds)
        assert 0 < r.ttl('a') <= 61

    def test_get_and_set(self, r):
        # get and set can't be tested independently of each other
        assert r.get('a') is None
        byte_string = b('value')
        integer = 5
        unicode_string = unichr(3456) + u('abcd') + unichr(3421)
        assert r.set('byte_string', byte_string)
        assert r.set('integer', 5)
        assert r.set('unicode_string', unicode_string)
        assert r.get('byte_string') == byte_string
        assert r.get('integer') == b(str(integer))
        assert r.get('unicode_string').decode('utf-8') == unicode_string

    def test_getitem_and_setitem(self, r):
        r['a'] = 'bar'
        assert r['a'] == b('bar')

    def test_getitem_raises_keyerror_for_missing_key(self, r):
        with pytest.raises(KeyError):
            r['a']

    def test_get_set_bit(self, r):
        # no value
        assert not r.getbit('a', 5)
        # set bit 5
        assert not r.setbit('a', 5, True)
        assert r.getbit('a', 5)
        # unset bit 4
        assert not r.setbit('a', 4, False)
        assert not r.getbit('a', 4)
        # set bit 4
        assert not r.setbit('a', 4, True)
        assert r.getbit('a', 4)
        # set bit 5 again
        assert r.setbit('a', 5, True)
        assert r.getbit('a', 5)

    def test_getrange(self, r):
        r['a'] = 'foo'
        assert r.getrange('a', 0, 0) == b('f')
        assert r.getrange('a', 0, 2) == b('foo')
        assert r.getrange('a', 3, 4) == b('')

    def test_getset(self, r):
        assert r.getset('a', 'foo') is None
        assert r.getset('a', 'bar') == b('foo')
        assert r.get('a') == b('bar')

    def test_incr(self, r):
        assert r.incr('a') == 1
        assert r['a'] == b('1')
        assert r.incr('a') == 2
        assert r['a'] == b('2')
        assert r.incr('a', amount=5) == 7
        assert r['a'] == b('7')

    def test_incrby(self, r):
        assert r.incrby('a') == 1
        assert r.incrby('a', 4) == 5
        assert r['a'] == b('5')

    @skip_if_server_version_lt('2.6.0')
    def test_incrbyfloat(self, r):
        assert r.incrbyfloat('a') == 1.0
        assert r['a'] == b('1')
        assert r.incrbyfloat('a', 1.1) == 2.1
        assert float(r['a']) == float(2.1)

    def test_keys(self, r):
        assert r.keys() == []
        keys_with_underscores = set([b('test_a'), b('test_b')])
        keys = keys_with_underscores.union(set([b('testc')]))
        for key in keys:
            r[key] = 1
        assert set(r.keys(pattern='test_*')) == keys_with_underscores
        assert set(r.keys(pattern='test*')) == keys

    def test_mget(self, r):
        assert r.mget(['a', 'b']) == [None, None]
        r['a'] = '1'
        r['b'] = '2'
        r['c'] = '3'
        assert r.mget('a', 'other', 'b', 'c') == [b('1'), None, b('2'), b('3')]

    def test_mset(self, r):
        d = {'a': b('1'), 'b': b('2'), 'c': b('3')}
        assert r.mset(d)
        for k, v in iteritems(d):
            assert r[k] == v

    def test_mset_kwargs(self, r):
        d = {'a': b('1'), 'b': b('2'), 'c': b('3')}
        assert r.mset(**d)
        for k, v in iteritems(d):
            assert r[k] == v

    def test_msetnx(self, r):
        d = {'a': b('1'), 'b': b('2'), 'c': b('3')}
        assert r.msetnx(d)
        d2 = {'a': b('x'), 'd': b('4')}
        assert not r.msetnx(d2)
        for k, v in iteritems(d):
            assert r[k] == v
        assert r.get('d') is None

    def test_msetnx_kwargs(self, r):
        d = {'a': b('1'), 'b': b('2'), 'c': b('3')}
        assert r.msetnx(**d)
        d2 = {'a': b('x'), 'd': b('4')}
        assert not r.msetnx(**d2)
        for k, v in iteritems(d):
            assert r[k] == v
        assert r.get('d') is None

    @skip_if_server_version_lt('2.6.0')
    def test_pexpire(self, r):
        assert not r.pexpire('a', 60000)
        r['a'] = 'foo'
        assert r.pexpire('a', 60000)
        assert 0 < r.pttl('a') <= 60000
        assert r.persist('a')
        assert r.pttl('a') is None

    @skip_if_server_version_lt('2.6.0')
    def test_pexpireat_datetime(self, r):
        expire_at = redis_server_time(r) + datetime.timedelta(minutes=1)
        r['a'] = 'foo'
        assert r.pexpireat('a', expire_at)
        assert 0 < r.pttl('a') <= 61000

    @skip_if_server_version_lt('2.6.0')
    def test_pexpireat_no_key(self, r):
        expire_at = redis_server_time(r) + datetime.timedelta(minutes=1)
        assert not r.pexpireat('a', expire_at)

    @skip_if_server_version_lt('2.6.0')
    def test_pexpireat_unixtime(self, r):
        expire_at = redis_server_time(r) + datetime.timedelta(minutes=1)
        r['a'] = 'foo'
        expire_at_seconds = int(time.mktime(expire_at.timetuple())) * 1000
        assert r.pexpireat('a', expire_at_seconds)
        assert 0 < r.pttl('a') <= 61000

    @skip_if_server_version_lt('2.6.0')
    def test_psetex(self, r):
        assert r.psetex('a', 1000, 'value')
        assert r['a'] == b('value')
        assert 0 < r.pttl('a') <= 1000

    @skip_if_server_version_lt('2.6.0')
    def test_psetex_timedelta(self, r):
        expire_at = datetime.timedelta(milliseconds=1000)
        assert r.psetex('a', expire_at, 'value')
        assert r['a'] == b('value')
        assert 0 < r.pttl('a') <= 1000

    def test_randomkey(self, r):
        assert r.randomkey() is None
        for key in ('a', 'b', 'c'):
            r[key] = 1
        assert r.randomkey() in (b('a'), b('b'), b('c'))

    def test_rename(self, r):
        r['a'] = '1'
        assert r.rename('a', 'b')
        assert r.get('a') is None
        assert r['b'] == b('1')

    def test_renamenx(self, r):
        r['a'] = '1'
        r['b'] = '2'
        assert not r.renamenx('a', 'b')
        assert r['a'] == b('1')
        assert r['b'] == b('2')

    @skip_if_server_version_lt('2.6.0')
    def test_set_nx(self, r):
        assert r.set('a', '1', nx=True)
        assert not r.set('a', '2', nx=True)
        assert r['a'] == b('1')

    @skip_if_server_version_lt('2.6.0')
    def test_set_xx(self, r):
        assert not r.set('a', '1', xx=True)
        assert r.get('a') is None
        r['a'] = 'bar'
        assert r.set('a', '2', xx=True)
        assert r.get('a') == b('2')

    @skip_if_server_version_lt('2.6.0')
    def test_set_px(self, r):
        assert r.set('a', '1', px=10000)
        assert r['a'] == b('1')
        assert 0 < r.pttl('a') <= 10000
        assert 0 < r.ttl('a') <= 10

    @skip_if_server_version_lt('2.6.0')
    def test_set_px_timedelta(self, r):
        expire_at = datetime.timedelta(milliseconds=1000)
        assert r.set('a', '1', px=expire_at)
        assert 0 < r.pttl('a') <= 1000
        assert 0 < r.ttl('a') <= 1

    @skip_if_server_version_lt('2.6.0')
    def test_set_ex(self, r):
        assert r.set('a', '1', ex=10)
        assert 0 < r.ttl('a') <= 10

    @skip_if_server_version_lt('2.6.0')
    def test_set_ex_timedelta(self, r):
        expire_at = datetime.timedelta(seconds=60)
        assert r.set('a', '1', ex=expire_at)
        assert 0 < r.ttl('a') <= 60

    @skip_if_server_version_lt('2.6.0')
    def test_set_multipleoptions(self, r):
        r['a'] = 'val'
        assert r.set('a', '1', xx=True, px=10000)
        assert 0 < r.ttl('a') <= 10

    def test_setex(self, r):
        assert r.setex('a', '1', 60)
        assert r['a'] == b('1')
        assert 0 < r.ttl('a') <= 60

    def test_setnx(self, r):
        assert r.setnx('a', '1')
        assert r['a'] == b('1')
        assert not r.setnx('a', '2')
        assert r['a'] == b('1')

    def test_setrange(self, r):
        assert r.setrange('a', 5, 'foo') == 8
        assert r['a'] == b('\0\0\0\0\0foo')
        r['a'] = 'abcdefghijh'
        assert r.setrange('a', 6, '12345') == 11
        assert r['a'] == b('abcdef12345')

    def test_strlen(self, r):
        r['a'] = 'foo'
        assert r.strlen('a') == 3

    def test_substr(self, r):
        r['a'] = '0123456789'
        assert r.substr('a', 0) == b('0123456789')
        assert r.substr('a', 2) == b('23456789')
        assert r.substr('a', 3, 5) == b('345')
        assert r.substr('a', 3, -2) == b('345678')

    def test_type(self, r):
        assert r.type('a') == b('none')
        r['a'] = '1'
        assert r.type('a') == b('string')
        del r['a']
        r.lpush('a', '1')
        assert r.type('a') == b('list')
        del r['a']
        r.sadd('a', '1')
        assert r.type('a') == b('set')
        del r['a']
        r.zadd('a', **{'1': 1})
        assert r.type('a') == b('zset')

    # LIST COMMANDS
    def test_blpop(self, r):
        r.rpush('a', '1', '2')
        r.rpush('b', '3', '4')
        assert r.blpop(['b', 'a'], timeout=1) == (b('b'), b('3'))
        assert r.blpop(['b', 'a'], timeout=1) == (b('b'), b('4'))
        assert r.blpop(['b', 'a'], timeout=1) == (b('a'), b('1'))
        assert r.blpop(['b', 'a'], timeout=1) == (b('a'), b('2'))
        assert r.blpop(['b', 'a'], timeout=1) is None
        r.rpush('c', '1')
        assert r.blpop('c', timeout=1) == (b('c'), b('1'))

    def test_brpop(self, r):
        r.rpush('a', '1', '2')
        r.rpush('b', '3', '4')
        assert r.brpop(['b', 'a'], timeout=1) == (b('b'), b('4'))
        assert r.brpop(['b', 'a'], timeout=1) == (b('b'), b('3'))
        assert r.brpop(['b', 'a'], timeout=1) == (b('a'), b('2'))
        assert r.brpop(['b', 'a'], timeout=1) == (b('a'), b('1'))
        assert r.brpop(['b', 'a'], timeout=1) is None
        r.rpush('c', '1')
        assert r.brpop('c', timeout=1) == (b('c'), b('1'))

    def test_brpoplpush(self, r):
        r.rpush('a', '1', '2')
        r.rpush('b', '3', '4')
        assert r.brpoplpush('a', 'b') == b('2')
        assert r.brpoplpush('a', 'b') == b('1')
        assert r.brpoplpush('a', 'b', timeout=1) is None
        assert r.lrange('a', 0, -1) == []
        assert r.lrange('b', 0, -1) == [b('1'), b('2'), b('3'), b('4')]

    def test_brpoplpush_empty_string(self, r):
        r.rpush('a', '')
        assert r.brpoplpush('a', 'b') == b('')

    def test_lindex(self, r):
        r.rpush('a', '1', '2', '3')
        assert r.lindex('a', '0') == b('1')
        assert r.lindex('a', '1') == b('2')
        assert r.lindex('a', '2') == b('3')

    def test_linsert(self, r):
        r.rpush('a', '1', '2', '3')
        assert r.linsert('a', 'after', '2', '2.5') == 4
        assert r.lrange('a', 0, -1) == [b('1'), b('2'), b('2.5'), b('3')]
        assert r.linsert('a', 'before', '2', '1.5') == 5
        assert r.lrange('a', 0, -1) == \
            [b('1'), b('1.5'), b('2'), b('2.5'), b('3')]

    def test_llen(self, r):
        r.rpush('a', '1', '2', '3')
        assert r.llen('a') == 3

    def test_lpop(self, r):
        r.rpush('a', '1', '2', '3')
        assert r.lpop('a') == b('1')
        assert r.lpop('a') == b('2')
        assert r.lpop('a') == b('3')
        assert r.lpop('a') is None

    def test_lpush(self, r):
        assert r.lpush('a', '1') == 1
        assert r.lpush('a', '2') == 2
        assert r.lpush('a', '3', '4') == 4
        assert r.lrange('a', 0, -1) == [b('4'), b('3'), b('2'), b('1')]

    def test_lpushx(self, r):
        assert r.lpushx('a', '1') == 0
        assert r.lrange('a', 0, -1) == []
        r.rpush('a', '1', '2', '3')
        assert r.lpushx('a', '4') == 4
        assert r.lrange('a', 0, -1) == [b('4'), b('1'), b('2'), b('3')]

    def test_lrange(self, r):
        r.rpush('a', '1', '2', '3', '4', '5')
        assert r.lrange('a', 0, 2) == [b('1'), b('2'), b('3')]
        assert r.lrange('a', 2, 10) == [b('3'), b('4'), b('5')]
        assert r.lrange('a', 0, -1) == [b('1'), b('2'), b('3'), b('4'), b('5')]

    def test_lrem(self, r):
        r.rpush('a', '1', '1', '1', '1')
        assert r.lrem('a', '1', 1) == 1
        assert r.lrange('a', 0, -1) == [b('1'), b('1'), b('1')]
        assert r.lrem('a', '1') == 3
        assert r.lrange('a', 0, -1) == []

    def test_lset(self, r):
        r.rpush('a', '1', '2', '3')
        assert r.lrange('a', 0, -1) == [b('1'), b('2'), b('3')]
        assert r.lset('a', 1, '4')
        assert r.lrange('a', 0, 2) == [b('1'), b('4'), b('3')]

    def test_ltrim(self, r):
        r.rpush('a', '1', '2', '3')
        assert r.ltrim('a', 0, 1)
        assert r.lrange('a', 0, -1) == [b('1'), b('2')]

    def test_rpop(self, r):
        r.rpush('a', '1', '2', '3')
        assert r.rpop('a') == b('3')
        assert r.rpop('a') == b('2')
        assert r.rpop('a') == b('1')
        assert r.rpop('a') is None

    def test_rpoplpush(self, r):
        r.rpush('a', 'a1', 'a2', 'a3')
        r.rpush('b', 'b1', 'b2', 'b3')
        assert r.rpoplpush('a', 'b') == b('a3')
        assert r.lrange('a', 0, -1) == [b('a1'), b('a2')]
        assert r.lrange('b', 0, -1) == [b('a3'), b('b1'), b('b2'), b('b3')]

    def test_rpush(self, r):
        assert r.rpush('a', '1') == 1
        assert r.rpush('a', '2') == 2
        assert r.rpush('a', '3', '4') == 4
        assert r.lrange('a', 0, -1) == [b('1'), b('2'), b('3'), b('4')]

    def test_rpushx(self, r):
        assert r.rpushx('a', 'b') == 0
        assert r.lrange('a', 0, -1) == []
        r.rpush('a', '1', '2', '3')
        assert r.rpushx('a', '4') == 4
        assert r.lrange('a', 0, -1) == [b('1'), b('2'), b('3'), b('4')]

    # SCAN COMMANDS
    @skip_if_server_version_lt('2.8.0')
    def test_scan(self, r):
        r.set('a', 1)
        r.set('b', 2)
        r.set('c', 3)
        cursor, keys = r.scan()
        assert cursor == 0
        assert set(keys) == set([b('a'), b('b'), b('c')])
        _, keys = r.scan(match='a')
        assert set(keys) == set([b('a')])

    @skip_if_server_version_lt('2.8.0')
    def test_scan_iter(self, r):
        r.set('a', 1)
        r.set('b', 2)
        r.set('c', 3)
        keys = list(r.scan_iter())
        assert set(keys) == set([b('a'), b('b'), b('c')])
        keys = list(r.scan_iter(match='a'))
        assert set(keys) == set([b('a')])

    @skip_if_server_version_lt('2.8.0')
    def test_sscan(self, r):
        r.sadd('a', 1, 2, 3)
        cursor, members = r.sscan('a')
        assert cursor == 0
        assert set(members) == set([b('1'), b('2'), b('3')])
        _, members = r.sscan('a', match=b('1'))
        assert set(members) == set([b('1')])

    @skip_if_server_version_lt('2.8.0')
    def test_sscan_iter(self, r):
        r.sadd('a', 1, 2, 3)
        members = list(r.sscan_iter('a'))
        assert set(members) == set([b('1'), b('2'), b('3')])
        members = list(r.sscan_iter('a', match=b('1')))
        assert set(members) == set([b('1')])

    @skip_if_server_version_lt('2.8.0')
    def test_hscan(self, r):
        r.hmset('a', {'a': 1, 'b': 2, 'c': 3})
        cursor, dic = r.hscan('a')
        assert cursor == 0
        assert dic == {b('a'): b('1'), b('b'): b('2'), b('c'): b('3')}
        _, dic = r.hscan('a', match='a')
        assert dic == {b('a'): b('1')}

    @skip_if_server_version_lt('2.8.0')
    def test_hscan_iter(self, r):
        r.hmset('a', {'a': 1, 'b': 2, 'c': 3})
        dic = dict(r.hscan_iter('a'))
        assert dic == {b('a'): b('1'), b('b'): b('2'), b('c'): b('3')}
        dic = dict(r.hscan_iter('a', match='a'))
        assert dic == {b('a'): b('1')}

    @skip_if_server_version_lt('2.8.0')
    def test_zscan(self, r):
        r.zadd('a', 'a', 1, 'b', 2, 'c', 3)
        cursor, pairs = r.zscan('a')
        assert cursor == 0
        assert set(pairs) == set([(b('a'), 1), (b('b'), 2), (b('c'), 3)])
        _, pairs = r.zscan('a', match='a')
        assert set(pairs) == set([(b('a'), 1)])

    @skip_if_server_version_lt('2.8.0')
    def test_zscan_iter(self, r):
        r.zadd('a', 'a', 1, 'b', 2, 'c', 3)
        pairs = list(r.zscan_iter('a'))
        assert set(pairs) == set([(b('a'), 1), (b('b'), 2), (b('c'), 3)])
        pairs = list(r.zscan_iter('a', match='a'))
        assert set(pairs) == set([(b('a'), 1)])

    # SET COMMANDS
    def test_sadd(self, r):
        members = set([b('1'), b('2'), b('3')])
        r.sadd('a', *members)
        assert r.smembers('a') == members

    def test_scard(self, r):
        r.sadd('a', '1', '2', '3')
        assert r.scard('a') == 3

    def test_sdiff(self, r):
        r.sadd('a', '1', '2', '3')
        assert r.sdiff('a', 'b') == set([b('1'), b('2'), b('3')])
        r.sadd('b', '2', '3')
        assert r.sdiff('a', 'b') == set([b('1')])

    def test_sdiffstore(self, r):
        r.sadd('a', '1', '2', '3')
        assert r.sdiffstore('c', 'a', 'b') == 3
        assert r.smembers('c') == set([b('1'), b('2'), b('3')])
        r.sadd('b', '2', '3')
        assert r.sdiffstore('c', 'a', 'b') == 1
        assert r.smembers('c') == set([b('1')])

    def test_sinter(self, r):
        r.sadd('a', '1', '2', '3')
        assert r.sinter('a', 'b') == set()
        r.sadd('b', '2', '3')
        assert r.sinter('a', 'b') == set([b('2'), b('3')])

    def test_sinterstore(self, r):
        r.sadd('a', '1', '2', '3')
        assert r.sinterstore('c', 'a', 'b') == 0
        assert r.smembers('c') == set()
        r.sadd('b', '2', '3')
        assert r.sinterstore('c', 'a', 'b') == 2
        assert r.smembers('c') == set([b('2'), b('3')])

    def test_sismember(self, r):
        r.sadd('a', '1', '2', '3')
        assert r.sismember('a', '1')
        assert r.sismember('a', '2')
        assert r.sismember('a', '3')
        assert not r.sismember('a', '4')

    def test_smembers(self, r):
        r.sadd('a', '1', '2', '3')
        assert r.smembers('a') == set([b('1'), b('2'), b('3')])

    def test_smove(self, r):
        r.sadd('a', 'a1', 'a2')
        r.sadd('b', 'b1', 'b2')
        assert r.smove('a', 'b', 'a1')
        assert r.smembers('a') == set([b('a2')])
        assert r.smembers('b') == set([b('b1'), b('b2'), b('a1')])

    def test_spop(self, r):
        s = [b('1'), b('2'), b('3')]
        r.sadd('a', *s)
        value = r.spop('a')
        assert value in s
        assert r.smembers('a') == set(s) - set([value])

    def test_srandmember(self, r):
        s = [b('1'), b('2'), b('3')]
        r.sadd('a', *s)
        assert r.srandmember('a') in s

    @skip_if_server_version_lt('2.6.0')
    def test_srandmember_multi_value(self, r):
        s = [b('1'), b('2'), b('3')]
        r.sadd('a', *s)
        randoms = r.srandmember('a', number=2)
        assert len(randoms) == 2
        assert set(randoms).intersection(s) == set(randoms)

    def test_srem(self, r):
        r.sadd('a', '1', '2', '3', '4')
        assert r.srem('a', '5') == 0
        assert r.srem('a', '2', '4') == 2
        assert r.smembers('a') == set([b('1'), b('3')])

    def test_sunion(self, r):
        r.sadd('a', '1', '2')
        r.sadd('b', '2', '3')
        assert r.sunion('a', 'b') == set([b('1'), b('2'), b('3')])

    def test_sunionstore(self, r):
        r.sadd('a', '1', '2')
        r.sadd('b', '2', '3')
        assert r.sunionstore('c', 'a', 'b') == 3
        assert r.smembers('c') == set([b('1'), b('2'), b('3')])

    # SORTED SET COMMANDS
    def test_zadd(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        assert r.zrange('a', 0, -1) == [b('a1'), b('a2'), b('a3')]

    def test_zcard(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        assert r.zcard('a') == 3

    def test_zcount(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        assert r.zcount('a', '-inf', '+inf') == 3
        assert r.zcount('a', 1, 2) == 2
        assert r.zcount('a', 10, 20) == 0

    def test_zincrby(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        assert r.zincrby('a', 'a2') == 3.0
        assert r.zincrby('a', 'a3', amount=5) == 8.0
        assert r.zscore('a', 'a2') == 3.0
        assert r.zscore('a', 'a3') == 8.0

    @skip_if_server_version_lt('2.8.9')
    def test_zlexcount(self, r):
        r.zadd('a', a=0, b=0, c=0, d=0, e=0, f=0, g=0)
        assert r.zlexcount('a', '-', '+') == 7
        assert r.zlexcount('a', '[b', '[f') == 5

    def test_zinterstore_sum(self, r):
        r.zadd('a', a1=1, a2=1, a3=1)
        r.zadd('b', a1=2, a2=2, a3=2)
        r.zadd('c', a1=6, a3=5, a4=4)
        assert r.zinterstore('d', ['a', 'b', 'c']) == 2
        assert r.zrange('d', 0, -1, withscores=True) == \
            [(b('a3'), 8), (b('a1'), 9)]

    def test_zinterstore_max(self, r):
        r.zadd('a', a1=1, a2=1, a3=1)
        r.zadd('b', a1=2, a2=2, a3=2)
        r.zadd('c', a1=6, a3=5, a4=4)
        assert r.zinterstore('d', ['a', 'b', 'c'], aggregate='MAX') == 2
        assert r.zrange('d', 0, -1, withscores=True) == \
            [(b('a3'), 5), (b('a1'), 6)]

    def test_zinterstore_min(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        r.zadd('b', a1=2, a2=3, a3=5)
        r.zadd('c', a1=6, a3=5, a4=4)
        assert r.zinterstore('d', ['a', 'b', 'c'], aggregate='MIN') == 2
        assert r.zrange('d', 0, -1, withscores=True) == \
            [(b('a1'), 1), (b('a3'), 3)]

    def test_zinterstore_with_weight(self, r):
        r.zadd('a', a1=1, a2=1, a3=1)
        r.zadd('b', a1=2, a2=2, a3=2)
        r.zadd('c', a1=6, a3=5, a4=4)
        assert r.zinterstore('d', {'a': 1, 'b': 2, 'c': 3}) == 2
        assert r.zrange('d', 0, -1, withscores=True) == \
            [(b('a3'), 20), (b('a1'), 23)]

    def test_zrange(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        assert r.zrange('a', 0, 1) == [b('a1'), b('a2')]
        assert r.zrange('a', 1, 2) == [b('a2'), b('a3')]

        # withscores
        assert r.zrange('a', 0, 1, withscores=True) == \
            [(b('a1'), 1.0), (b('a2'), 2.0)]
        assert r.zrange('a', 1, 2, withscores=True) == \
            [(b('a2'), 2.0), (b('a3'), 3.0)]

        # custom score function
        assert r.zrange('a', 0, 1, withscores=True, score_cast_func=int) == \
            [(b('a1'), 1), (b('a2'), 2)]

    @skip_if_server_version_lt('2.8.9')
    def test_zrangebylex(self, r):
        r.zadd('a', a=0, b=0, c=0, d=0, e=0, f=0, g=0)
        assert r.zrangebylex('a', '-', '[c') == [b('a'), b('b'), b('c')]
        assert r.zrangebylex('a', '-', '(c') == [b('a'), b('b')]
        assert r.zrangebylex('a', '[aaa', '(g') == \
            [b('b'), b('c'), b('d'), b('e'), b('f')]
        assert r.zrangebylex('a', '[f', '+') == [b('f'), b('g')]
        assert r.zrangebylex('a', '-', '+', start=3, num=2) == [b('d'), b('e')]

    def test_zrangebyscore(self, r):
        r.zadd('a', a1=1, a2=2, a3=3, a4=4, a5=5)
        assert r.zrangebyscore('a', 2, 4) == [b('a2'), b('a3'), b('a4')]

        # slicing with start/num
        assert r.zrangebyscore('a', 2, 4, start=1, num=2) == \
            [b('a3'), b('a4')]

        # withscores
        assert r.zrangebyscore('a', 2, 4, withscores=True) == \
            [(b('a2'), 2.0), (b('a3'), 3.0), (b('a4'), 4.0)]

        # custom score function
        assert r.zrangebyscore('a', 2, 4, withscores=True,
                               score_cast_func=int) == \
            [(b('a2'), 2), (b('a3'), 3), (b('a4'), 4)]

    def test_zrank(self, r):
        r.zadd('a', a1=1, a2=2, a3=3, a4=4, a5=5)
        assert r.zrank('a', 'a1') == 0
        assert r.zrank('a', 'a2') == 1
        assert r.zrank('a', 'a6') is None

    def test_zrem(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        assert r.zrem('a', 'a2') == 1
        assert r.zrange('a', 0, -1) == [b('a1'), b('a3')]
        assert r.zrem('a', 'b') == 0
        assert r.zrange('a', 0, -1) == [b('a1'), b('a3')]

    def test_zrem_multiple_keys(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        assert r.zrem('a', 'a1', 'a2') == 2
        assert r.zrange('a', 0, 5) == [b('a3')]

    @skip_if_server_version_lt('2.8.9')
    def test_zremrangebylex(self, r):
        r.zadd('a', a=0, b=0, c=0, d=0, e=0, f=0, g=0)
        assert r.zremrangebylex('a', '-', '[c') == 3
        assert r.zrange('a', 0, -1) == [b('d'), b('e'), b('f'), b('g')]
        assert r.zremrangebylex('a', '[f', '+') == 2
        assert r.zrange('a', 0, -1) == [b('d'), b('e')]
        assert r.zremrangebylex('a', '[h', '+') == 0
        assert r.zrange('a', 0, -1) == [b('d'), b('e')]

    def test_zremrangebyrank(self, r):
        r.zadd('a', a1=1, a2=2, a3=3, a4=4, a5=5)
        assert r.zremrangebyrank('a', 1, 3) == 3
        assert r.zrange('a', 0, 5) == [b('a1'), b('a5')]

    def test_zremrangebyscore(self, r):
        r.zadd('a', a1=1, a2=2, a3=3, a4=4, a5=5)
        assert r.zremrangebyscore('a', 2, 4) == 3
        assert r.zrange('a', 0, -1) == [b('a1'), b('a5')]
        assert r.zremrangebyscore('a', 2, 4) == 0
        assert r.zrange('a', 0, -1) == [b('a1'), b('a5')]

    def test_zrevrange(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        assert r.zrevrange('a', 0, 1) == [b('a3'), b('a2')]
        assert r.zrevrange('a', 1, 2) == [b('a2'), b('a1')]

        # withscores
        assert r.zrevrange('a', 0, 1, withscores=True) == \
            [(b('a3'), 3.0), (b('a2'), 2.0)]
        assert r.zrevrange('a', 1, 2, withscores=True) == \
            [(b('a2'), 2.0), (b('a1'), 1.0)]

        # custom score function
        assert r.zrevrange('a', 0, 1, withscores=True,
                           score_cast_func=int) == \
            [(b('a3'), 3.0), (b('a2'), 2.0)]

    def test_zrevrangebyscore(self, r):
        r.zadd('a', a1=1, a2=2, a3=3, a4=4, a5=5)
        assert r.zrevrangebyscore('a', 4, 2) == [b('a4'), b('a3'), b('a2')]

        # slicing with start/num
        assert r.zrevrangebyscore('a', 4, 2, start=1, num=2) == \
            [b('a3'), b('a2')]

        # withscores
        assert r.zrevrangebyscore('a', 4, 2, withscores=True) == \
            [(b('a4'), 4.0), (b('a3'), 3.0), (b('a2'), 2.0)]

        # custom score function
        assert r.zrevrangebyscore('a', 4, 2, withscores=True,
                                  score_cast_func=int) == \
            [(b('a4'), 4), (b('a3'), 3), (b('a2'), 2)]

    def test_zrevrank(self, r):
        r.zadd('a', a1=1, a2=2, a3=3, a4=4, a5=5)
        assert r.zrevrank('a', 'a1') == 4
        assert r.zrevrank('a', 'a2') == 3
        assert r.zrevrank('a', 'a6') is None

    def test_zscore(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        assert r.zscore('a', 'a1') == 1.0
        assert r.zscore('a', 'a2') == 2.0
        assert r.zscore('a', 'a4') is None

    def test_zunionstore_sum(self, r):
        r.zadd('a', a1=1, a2=1, a3=1)
        r.zadd('b', a1=2, a2=2, a3=2)
        r.zadd('c', a1=6, a3=5, a4=4)
        assert r.zunionstore('d', ['a', 'b', 'c']) == 4
        assert r.zrange('d', 0, -1, withscores=True) == \
            [(b('a2'), 3), (b('a4'), 4), (b('a3'), 8), (b('a1'), 9)]

    def test_zunionstore_max(self, r):
        r.zadd('a', a1=1, a2=1, a3=1)
        r.zadd('b', a1=2, a2=2, a3=2)
        r.zadd('c', a1=6, a3=5, a4=4)
        assert r.zunionstore('d', ['a', 'b', 'c'], aggregate='MAX') == 4
        assert r.zrange('d', 0, -1, withscores=True) == \
            [(b('a2'), 2), (b('a4'), 4), (b('a3'), 5), (b('a1'), 6)]

    def test_zunionstore_min(self, r):
        r.zadd('a', a1=1, a2=2, a3=3)
        r.zadd('b', a1=2, a2=2, a3=4)
        r.zadd('c', a1=6, a3=5, a4=4)
        assert r.zunionstore('d', ['a', 'b', 'c'], aggregate='MIN') == 4
        assert r.zrange('d', 0, -1, withscores=True) == \
            [(b('a1'), 1), (b('a2'), 2), (b('a3'), 3), (b('a4'), 4)]

    def test_zunionstore_with_weight(self, r):
        r.zadd('a', a1=1, a2=1, a3=1)
        r.zadd('b', a1=2, a2=2, a3=2)
        r.zadd('c', a1=6, a3=5, a4=4)
        assert r.zunionstore('d', {'a': 1, 'b': 2, 'c': 3}) == 4
        assert r.zrange('d', 0, -1, withscores=True) == \
            [(b('a2'), 5), (b('a4'), 12), (b('a3'), 20), (b('a1'), 23)]

    # HYPERLOGLOG TESTS
    @skip_if_server_version_lt('2.8.9')
    def test_pfadd(self, r):
        members = set([b('1'), b('2'), b('3')])
        assert r.pfadd('a', *members) == 1
        assert r.pfadd('a', *members) == 0
        assert r.pfcount('a') == len(members)

    @skip_if_server_version_lt('2.8.9')
    def test_pfcount(self, r):
        members = set([b('1'), b('2'), b('3')])
        r.pfadd('a', *members)
        assert r.pfcount('a') == len(members)

    @skip_if_server_version_lt('2.8.9')
    def test_pfmerge(self, r):
        mema = set([b('1'), b('2'), b('3')])
        memb = set([b('2'), b('3'), b('4')])
        memc = set([b('5'), b('6'), b('7')])
        r.pfadd('a', *mema)
        r.pfadd('b', *memb)
        r.pfadd('c', *memc)
        r.pfmerge('d', 'c', 'a')
        assert r.pfcount('d') == 6
        r.pfmerge('d', 'b')
        assert r.pfcount('d') == 7

    # HASH COMMANDS
    def test_hget_and_hset(self, r):
        r.hmset('a', {'1': 1, '2': 2, '3': 3})
        assert r.hget('a', '1') == b('1')
        assert r.hget('a', '2') == b('2')
        assert r.hget('a', '3') == b('3')

        # field was updated, redis returns 0
        assert r.hset('a', '2', 5) == 0
        assert r.hget('a', '2') == b('5')

        # field is new, redis returns 1
        assert r.hset('a', '4', 4) == 1
        assert r.hget('a', '4') == b('4')

        # key inside of hash that doesn't exist returns null value
        assert r.hget('a', 'b') is None

    def test_hdel(self, r):
        r.hmset('a', {'1': 1, '2': 2, '3': 3})
        assert r.hdel('a', '2') == 1
        assert r.hget('a', '2') is None
        assert r.hdel('a', '1', '3') == 2
        assert r.hlen('a') == 0

    def test_hexists(self, r):
        r.hmset('a', {'1': 1, '2': 2, '3': 3})
        assert r.hexists('a', '1')
        assert not r.hexists('a', '4')

    def test_hgetall(self, r):
        h = {b('a1'): b('1'), b('a2'): b('2'), b('a3'): b('3')}
        r.hmset('a', h)
        assert r.hgetall('a') == h

    def test_hincrby(self, r):
        assert r.hincrby('a', '1') == 1
        assert r.hincrby('a', '1', amount=2) == 3
        assert r.hincrby('a', '1', amount=-2) == 1

    @skip_if_server_version_lt('2.6.0')
    def test_hincrbyfloat(self, r):
        assert r.hincrbyfloat('a', '1') == 1.0
        assert r.hincrbyfloat('a', '1') == 2.0
        assert r.hincrbyfloat('a', '1', 1.2) == 3.2

    def test_hkeys(self, r):
        h = {b('a1'): b('1'), b('a2'): b('2'), b('a3'): b('3')}
        r.hmset('a', h)
        local_keys = list(iterkeys(h))
        remote_keys = r.hkeys('a')
        assert (sorted(local_keys) == sorted(remote_keys))

    def test_hlen(self, r):
        r.hmset('a', {'1': 1, '2': 2, '3': 3})
        assert r.hlen('a') == 3

    def test_hmget(self, r):
        assert r.hmset('a', {'a': 1, 'b': 2, 'c': 3})
        assert r.hmget('a', 'a', 'b', 'c') == [b('1'), b('2'), b('3')]

    def test_hmset(self, r):
        h = {b('a'): b('1'), b('b'): b('2'), b('c'): b('3')}
        assert r.hmset('a', h)
        assert r.hgetall('a') == h

    def test_hsetnx(self, r):
        # Initially set the hash field
        assert r.hsetnx('a', '1', 1)
        assert r.hget('a', '1') == b('1')
        assert not r.hsetnx('a', '1', 2)
        assert r.hget('a', '1') == b('1')

    def test_hvals(self, r):
        h = {b('a1'): b('1'), b('a2'): b('2'), b('a3'): b('3')}
        r.hmset('a', h)
        local_vals = list(itervalues(h))
        remote_vals = r.hvals('a')
        assert sorted(local_vals) == sorted(remote_vals)

    # SORT
    def test_sort_basic(self, r):
        r.rpush('a', '3', '2', '1', '4')
        assert r.sort('a') == [b('1'), b('2'), b('3'), b('4')]

    def test_sort_limited(self, r):
        r.rpush('a', '3', '2', '1', '4')
        assert r.sort('a', start=1, num=2) == [b('2'), b('3')]

    def test_sort_by(self, r):
        r['score:1'] = 8
        r['score:2'] = 3
        r['score:3'] = 5
        r.rpush('a', '3', '2', '1')
        assert r.sort('a', by='score:*') == [b('2'), b('3'), b('1')]

    def test_sort_get(self, r):
        r['user:1'] = 'u1'
        r['user:2'] = 'u2'
        r['user:3'] = 'u3'
        r.rpush('a', '2', '3', '1')
        assert r.sort('a', get='user:*') == [b('u1'), b('u2'), b('u3')]

    def test_sort_get_multi(self, r):
        r['user:1'] = 'u1'
        r['user:2'] = 'u2'
        r['user:3'] = 'u3'
        r.rpush('a', '2', '3', '1')
        assert r.sort('a', get=('user:*', '#')) == \
            [b('u1'), b('1'), b('u2'), b('2'), b('u3'), b('3')]

    def test_sort_get_groups_two(self, r):
        r['user:1'] = 'u1'
        r['user:2'] = 'u2'
        r['user:3'] = 'u3'
        r.rpush('a', '2', '3', '1')
        assert r.sort('a', get=('user:*', '#'), groups=True) == \
            [(b('u1'), b('1')), (b('u2'), b('2')), (b('u3'), b('3'))]

    def test_sort_groups_string_get(self, r):
        r['user:1'] = 'u1'
        r['user:2'] = 'u2'
        r['user:3'] = 'u3'
        r.rpush('a', '2', '3', '1')
        with pytest.raises(exceptions.DataError):
            r.sort('a', get='user:*', groups=True)

    def test_sort_groups_just_one_get(self, r):
        r['user:1'] = 'u1'
        r['user:2'] = 'u2'
        r['user:3'] = 'u3'
        r.rpush('a', '2', '3', '1')
        with pytest.raises(exceptions.DataError):
            r.sort('a', get=['user:*'], groups=True)

    def test_sort_groups_no_get(self, r):
        r['user:1'] = 'u1'
        r['user:2'] = 'u2'
        r['user:3'] = 'u3'
        r.rpush('a', '2', '3', '1')
        with pytest.raises(exceptions.DataError):
            r.sort('a', groups=True)

    def test_sort_groups_three_gets(self, r):
        r['user:1'] = 'u1'
        r['user:2'] = 'u2'
        r['user:3'] = 'u3'
        r['door:1'] = 'd1'
        r['door:2'] = 'd2'
        r['door:3'] = 'd3'
        r.rpush('a', '2', '3', '1')
        assert r.sort('a', get=('user:*', 'door:*', '#'), groups=True) == \
            [
                (b('u1'), b('d1'), b('1')),
                (b('u2'), b('d2'), b('2')),
                (b('u3'), b('d3'), b('3'))
            ]

    def test_sort_desc(self, r):
        r.rpush('a', '2', '3', '1')
        assert r.sort('a', desc=True) == [b('3'), b('2'), b('1')]

    def test_sort_alpha(self, r):
        r.rpush('a', 'e', 'c', 'b', 'd', 'a')
        assert r.sort('a', alpha=True) == \
            [b('a'), b('b'), b('c'), b('d'), b('e')]

    def test_sort_store(self, r):
        r.rpush('a', '2', '3', '1')
        assert r.sort('a', store='sorted_values') == 3
        assert r.lrange('sorted_values', 0, -1) == [b('1'), b('2'), b('3')]

    def test_sort_all_options(self, r):
        r['user:1:username'] = 'zeus'
        r['user:2:username'] = 'titan'
        r['user:3:username'] = 'hermes'
        r['user:4:username'] = 'hercules'
        r['user:5:username'] = 'apollo'
        r['user:6:username'] = 'athena'
        r['user:7:username'] = 'hades'
        r['user:8:username'] = 'dionysus'

        r['user:1:favorite_drink'] = 'yuengling'
        r['user:2:favorite_drink'] = 'rum'
        r['user:3:favorite_drink'] = 'vodka'
        r['user:4:favorite_drink'] = 'milk'
        r['user:5:favorite_drink'] = 'pinot noir'
        r['user:6:favorite_drink'] = 'water'
        r['user:7:favorite_drink'] = 'gin'
        r['user:8:favorite_drink'] = 'apple juice'

        r.rpush('gods', '5', '8', '3', '1', '2', '7', '6', '4')
        num = r.sort('gods', start=2, num=4, by='user:*:username',
                     get='user:*:favorite_drink', desc=True, alpha=True,
                     store='sorted')
        assert num == 4
        assert r.lrange('sorted', 0, 10) == \
            [b('vodka'), b('milk'), b('gin'), b('apple juice')]


class TestStrictCommands(object):

    def test_strict_zadd(self, sr):
        sr.zadd('a', 1.0, 'a1', 2.0, 'a2', a3=3.0)
        assert sr.zrange('a', 0, -1, withscores=True) == \
            [(b('a1'), 1.0), (b('a2'), 2.0), (b('a3'), 3.0)]

    def test_strict_lrem(self, sr):
        sr.rpush('a', 'a1', 'a2', 'a3', 'a1')
        sr.lrem('a', 0, 'a1')
        assert sr.lrange('a', 0, -1) == [b('a2'), b('a3')]

    def test_strict_setex(self, sr):
        assert sr.setex('a', 60, '1')
        assert sr['a'] == b('1')
        assert 0 < sr.ttl('a') <= 60

    def test_strict_ttl(self, sr):
        assert not sr.expire('a', 10)
        sr['a'] = '1'
        assert sr.expire('a', 10)
        assert 0 < sr.ttl('a') <= 10
        assert sr.persist('a')
        assert sr.ttl('a') == -1

    @skip_if_server_version_lt('2.6.0')
    def test_strict_pttl(self, sr):
        assert not sr.pexpire('a', 10000)
        sr['a'] = '1'
        assert sr.pexpire('a', 10000)
        assert 0 < sr.pttl('a') <= 10000
        assert sr.persist('a')
        assert sr.pttl('a') == -1


class TestBinarySave(object):
    def test_binary_get_set(self, r):
        assert r.set(' foo bar ', '123')
        assert r.get(' foo bar ') == b('123')

        assert r.set(' foo\r\nbar\r\n ', '456')
        assert r.get(' foo\r\nbar\r\n ') == b('456')

        assert r.set(' \r\n\t\x07\x13 ', '789')
        assert r.get(' \r\n\t\x07\x13 ') == b('789')

        assert sorted(r.keys('*')) == \
            [b(' \r\n\t\x07\x13 '), b(' foo\r\nbar\r\n '), b(' foo bar ')]

        assert r.delete(' foo bar ')
        assert r.delete(' foo\r\nbar\r\n ')
        assert r.delete(' \r\n\t\x07\x13 ')

    def test_binary_lists(self, r):
        mapping = {
            b('foo bar'): [b('1'), b('2'), b('3')],
            b('foo\r\nbar\r\n'): [b('4'), b('5'), b('6')],
            b('foo\tbar\x07'): [b('7'), b('8'), b('9')],
        }
        # fill in lists
        for key, value in iteritems(mapping):
            r.rpush(key, *value)

        # check that KEYS returns all the keys as they are
        assert sorted(r.keys('*')) == sorted(list(iterkeys(mapping)))

        # check that it is possible to get list content by key name
        for key, value in iteritems(mapping):
            assert r.lrange(key, 0, -1) == value

    def test_22_info(self, r):
        """
        Older Redis versions contained 'allocation_stats' in INFO that
        was the cause of a number of bugs when parsing.
        """
        info = "allocation_stats:6=1,7=1,8=7141,9=180,10=92,11=116,12=5330," \
               "13=123,14=3091,15=11048,16=225842,17=1784,18=814,19=12020," \
               "20=2530,21=645,22=15113,23=8695,24=142860,25=318,26=3303," \
               "27=20561,28=54042,29=37390,30=1884,31=18071,32=31367,33=160," \
               "34=169,35=201,36=10155,37=1045,38=15078,39=22985,40=12523," \
               "41=15588,42=265,43=1287,44=142,45=382,46=945,47=426,48=171," \
               "49=56,50=516,51=43,52=41,53=46,54=54,55=75,56=647,57=332," \
               "58=32,59=39,60=48,61=35,62=62,63=32,64=221,65=26,66=30," \
               "67=36,68=41,69=44,70=26,71=144,72=169,73=24,74=37,75=25," \
               "76=42,77=21,78=126,79=374,80=27,81=40,82=43,83=47,84=46," \
               "85=114,86=34,87=37,88=7240,89=34,90=38,91=18,92=99,93=20," \
               "94=18,95=17,96=15,97=22,98=18,99=69,100=17,101=22,102=15," \
               "103=29,104=39,105=30,106=70,107=22,108=21,109=26,110=52," \
               "111=45,112=33,113=67,114=41,115=44,116=48,117=53,118=54," \
               "119=51,120=75,121=44,122=57,123=44,124=66,125=56,126=52," \
               "127=81,128=108,129=70,130=50,131=51,132=53,133=45,134=62," \
               "135=12,136=13,137=7,138=15,139=21,140=11,141=20,142=6,143=7," \
               "144=11,145=6,146=16,147=19,148=1112,149=1,151=83,154=1," \
               "155=1,156=1,157=1,160=1,161=1,162=2,166=1,169=1,170=1,171=2," \
               "172=1,174=1,176=2,177=9,178=34,179=73,180=30,181=1,185=3," \
               "187=1,188=1,189=1,192=1,196=1,198=1,200=1,201=1,204=1,205=1," \
               "207=1,208=1,209=1,214=2,215=31,216=78,217=28,218=5,219=2," \
               "220=1,222=1,225=1,227=1,234=1,242=1,250=1,252=1,253=1," \
               ">=256=203"
        parsed = parse_info(info)
        assert 'allocation_stats' in parsed
        assert '6' in parsed['allocation_stats']
        assert '>=256' in parsed['allocation_stats']

    def test_large_responses(self, r):
        "The PythonParser has some special cases for return values > 1MB"
        # load up 5MB of data into a key
        data = ''.join([ascii_letters] * (5000000 // len(ascii_letters)))
        r['a'] = data
        assert r['a'] == b(data)

    def test_floating_point_encoding(self, r):
        """
        High precision floating point values sent to the server should keep
        precision.
        """
        timestamp = 1349673917.939762
        r.zadd('a', 'a1', timestamp)
        assert r.zscore('a', 'a1') == timestamp

########NEW FILE########
__FILENAME__ = test_connection_pool
from __future__ import with_statement
import os
import pytest
import redis
import time
import re

from threading import Thread
from redis.connection import ssl_available
from .conftest import skip_if_server_version_lt


class DummyConnection(object):
    description_format = "DummyConnection<>"

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.pid = os.getpid()


class TestConnectionPool(object):
    def get_pool(self, connection_kwargs=None, max_connections=None,
                 connection_class=DummyConnection):
        connection_kwargs = connection_kwargs or {}
        pool = redis.ConnectionPool(
            connection_class=connection_class,
            max_connections=max_connections,
            **connection_kwargs)
        return pool

    def test_connection_creation(self):
        connection_kwargs = {'foo': 'bar', 'biz': 'baz'}
        pool = self.get_pool(connection_kwargs=connection_kwargs)
        connection = pool.get_connection('_')
        assert isinstance(connection, DummyConnection)
        assert connection.kwargs == connection_kwargs

    def test_multiple_connections(self):
        pool = self.get_pool()
        c1 = pool.get_connection('_')
        c2 = pool.get_connection('_')
        assert c1 != c2

    def test_max_connections(self):
        pool = self.get_pool(max_connections=2)
        pool.get_connection('_')
        pool.get_connection('_')
        with pytest.raises(redis.ConnectionError):
            pool.get_connection('_')

    def test_reuse_previously_released_connection(self):
        pool = self.get_pool()
        c1 = pool.get_connection('_')
        pool.release(c1)
        c2 = pool.get_connection('_')
        assert c1 == c2

    def test_repr_contains_db_info_tcp(self):
        connection_kwargs = {'host': 'localhost', 'port': 6379, 'db': 1}
        pool = self.get_pool(connection_kwargs=connection_kwargs,
                             connection_class=redis.Connection)
        expected = 'ConnectionPool<Connection<host=localhost,port=6379,db=1>>'
        assert repr(pool) == expected

    def test_repr_contains_db_info_unix(self):
        connection_kwargs = {'path': '/abc', 'db': 1}
        pool = self.get_pool(connection_kwargs=connection_kwargs,
                             connection_class=redis.UnixDomainSocketConnection)
        expected = 'ConnectionPool<UnixDomainSocketConnection<path=/abc,db=1>>'
        assert repr(pool) == expected


class TestBlockingConnectionPool(object):
    def get_pool(self, connection_kwargs=None, max_connections=10, timeout=20):
        connection_kwargs = connection_kwargs or {}
        pool = redis.BlockingConnectionPool(connection_class=DummyConnection,
                                            max_connections=max_connections,
                                            timeout=timeout,
                                            **connection_kwargs)
        return pool

    def test_connection_creation(self):
        connection_kwargs = {'foo': 'bar', 'biz': 'baz'}
        pool = self.get_pool(connection_kwargs=connection_kwargs)
        connection = pool.get_connection('_')
        assert isinstance(connection, DummyConnection)
        assert connection.kwargs == connection_kwargs

    def test_multiple_connections(self):
        pool = self.get_pool()
        c1 = pool.get_connection('_')
        c2 = pool.get_connection('_')
        assert c1 != c2

    def test_connection_pool_blocks_until_timeout(self):
        "When out of connections, block for timeout seconds, then raise"
        pool = self.get_pool(max_connections=1, timeout=0.1)
        pool.get_connection('_')

        start = time.time()
        with pytest.raises(redis.ConnectionError):
            pool.get_connection('_')
        # we should have waited at least 0.1 seconds
        assert time.time() - start >= 0.1

    def connection_pool_blocks_until_another_connection_released(self):
        """
        When out of connections, block until another connection is released
        to the pool
        """
        pool = self.get_pool(max_connections=1, timeout=2)
        c1 = pool.get_connection('_')

        def target():
            time.sleep(0.1)
            pool.release(c1)

        Thread(target=target).start()
        start = time.time()
        pool.get_connection('_')
        assert time.time() - start >= 0.1

    def test_reuse_previously_released_connection(self):
        pool = self.get_pool()
        c1 = pool.get_connection('_')
        pool.release(c1)
        c2 = pool.get_connection('_')
        assert c1 == c2

    def test_repr_contains_db_info_tcp(self):
        pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
        expected = 'ConnectionPool<Connection<host=localhost,port=6379,db=0>>'
        assert repr(pool) == expected

    def test_repr_contains_db_info_unix(self):
        pool = redis.ConnectionPool(
            connection_class=redis.UnixDomainSocketConnection,
            path='abc',
            db=0,
        )
        expected = 'ConnectionPool<UnixDomainSocketConnection<path=abc,db=0>>'
        assert repr(pool) == expected


class TestConnectionPoolURLParsing(object):
    def test_defaults(self):
        pool = redis.ConnectionPool.from_url('redis://localhost')
        assert pool.connection_class == redis.Connection
        assert pool.connection_kwargs == {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None,
        }

    def test_hostname(self):
        pool = redis.ConnectionPool.from_url('redis://myhost')
        assert pool.connection_class == redis.Connection
        assert pool.connection_kwargs == {
            'host': 'myhost',
            'port': 6379,
            'db': 0,
            'password': None,
        }

    def test_port(self):
        pool = redis.ConnectionPool.from_url('redis://localhost:6380')
        assert pool.connection_class == redis.Connection
        assert pool.connection_kwargs == {
            'host': 'localhost',
            'port': 6380,
            'db': 0,
            'password': None,
        }

    def test_password(self):
        pool = redis.ConnectionPool.from_url('redis://:mypassword@localhost')
        assert pool.connection_class == redis.Connection
        assert pool.connection_kwargs == {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': 'mypassword',
        }

    def test_db_as_argument(self):
        pool = redis.ConnectionPool.from_url('redis://localhost', db='1')
        assert pool.connection_class == redis.Connection
        assert pool.connection_kwargs == {
            'host': 'localhost',
            'port': 6379,
            'db': 1,
            'password': None,
        }

    def test_db_in_path(self):
        pool = redis.ConnectionPool.from_url('redis://localhost/2', db='1')
        assert pool.connection_class == redis.Connection
        assert pool.connection_kwargs == {
            'host': 'localhost',
            'port': 6379,
            'db': 2,
            'password': None,
        }

    def test_db_in_querystring(self):
        pool = redis.ConnectionPool.from_url('redis://localhost/2?db=3',
                                             db='1')
        assert pool.connection_class == redis.Connection
        assert pool.connection_kwargs == {
            'host': 'localhost',
            'port': 6379,
            'db': 3,
            'password': None,
        }

    def test_extra_querystring_options(self):
        pool = redis.ConnectionPool.from_url('redis://localhost?a=1&b=2')
        assert pool.connection_class == redis.Connection
        assert pool.connection_kwargs == {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None,
            'a': '1',
            'b': '2'
        }

    def test_calling_from_subclass_returns_correct_instance(self):
        pool = redis.BlockingConnectionPool.from_url('redis://localhost')
        assert isinstance(pool, redis.BlockingConnectionPool)

    def test_client_creates_connection_pool(self):
        r = redis.StrictRedis.from_url('redis://myhost')
        assert r.connection_pool.connection_class == redis.Connection
        assert r.connection_pool.connection_kwargs == {
            'host': 'myhost',
            'port': 6379,
            'db': 0,
            'password': None,
        }


class TestConnectionPoolUnixSocketURLParsing(object):
    def test_defaults(self):
        pool = redis.ConnectionPool.from_url('unix:///socket')
        assert pool.connection_class == redis.UnixDomainSocketConnection
        assert pool.connection_kwargs == {
            'path': '/socket',
            'db': 0,
            'password': None,
        }

    def test_password(self):
        pool = redis.ConnectionPool.from_url('unix://:mypassword@/socket')
        assert pool.connection_class == redis.UnixDomainSocketConnection
        assert pool.connection_kwargs == {
            'path': '/socket',
            'db': 0,
            'password': 'mypassword',
        }

    def test_db_as_argument(self):
        pool = redis.ConnectionPool.from_url('unix:///socket', db=1)
        assert pool.connection_class == redis.UnixDomainSocketConnection
        assert pool.connection_kwargs == {
            'path': '/socket',
            'db': 1,
            'password': None,
        }

    def test_db_in_querystring(self):
        pool = redis.ConnectionPool.from_url('unix:///socket?db=2', db=1)
        assert pool.connection_class == redis.UnixDomainSocketConnection
        assert pool.connection_kwargs == {
            'path': '/socket',
            'db': 2,
            'password': None,
        }

    def test_extra_querystring_options(self):
        pool = redis.ConnectionPool.from_url('unix:///socket?a=1&b=2')
        assert pool.connection_class == redis.UnixDomainSocketConnection
        assert pool.connection_kwargs == {
            'path': '/socket',
            'db': 0,
            'password': None,
            'a': '1',
            'b': '2'
        }


class TestSSLConnectionURLParsing(object):
    @pytest.mark.skipif(not ssl_available, reason="SSL not installed")
    def test_defaults(self):
        pool = redis.ConnectionPool.from_url('rediss://localhost')
        assert pool.connection_class == redis.SSLConnection
        assert pool.connection_kwargs == {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None,
        }

    @pytest.mark.skipif(not ssl_available, reason="SSL not installed")
    def test_cert_reqs_options(self):
        import ssl
        pool = redis.ConnectionPool.from_url('rediss://?ssl_cert_reqs=none')
        assert pool.get_connection('_').cert_reqs == ssl.CERT_NONE

        pool = redis.ConnectionPool.from_url(
            'rediss://?ssl_cert_reqs=optional')
        assert pool.get_connection('_').cert_reqs == ssl.CERT_OPTIONAL

        pool = redis.ConnectionPool.from_url(
            'rediss://?ssl_cert_reqs=required')
        assert pool.get_connection('_').cert_reqs == ssl.CERT_REQUIRED


class TestConnection(object):
    def test_on_connect_error(self):
        """
        An error in Connection.on_connect should disconnect from the server
        see for details: https://github.com/andymccurdy/redis-py/issues/368
        """
        # this assumes the Redis server being tested against doesn't have
        # 9999 databases ;)
        bad_connection = redis.Redis(db=9999)
        # an error should be raised on connect
        with pytest.raises(redis.RedisError):
            bad_connection.info()
        pool = bad_connection.connection_pool
        assert len(pool._available_connections) == 1
        assert not pool._available_connections[0]._sock

    @skip_if_server_version_lt('2.8.8')
    def test_busy_loading_disconnects_socket(self, r):
        """
        If Redis raises a LOADING error, the connection should be
        disconnected and a BusyLoadingError raised
        """
        with pytest.raises(redis.BusyLoadingError):
            r.execute_command('DEBUG', 'ERROR', 'LOADING fake message')
        pool = r.connection_pool
        assert len(pool._available_connections) == 1
        assert not pool._available_connections[0]._sock

    @skip_if_server_version_lt('2.8.8')
    def test_busy_loading_from_pipeline_immediate_command(self, r):
        """
        BusyLoadingErrors should raise from Pipelines that execute a
        command immediately, like WATCH does.
        """
        pipe = r.pipeline()
        with pytest.raises(redis.BusyLoadingError):
            pipe.immediate_execute_command('DEBUG', 'ERROR',
                                           'LOADING fake message')
        pool = r.connection_pool
        assert not pipe.connection
        assert len(pool._available_connections) == 1
        assert not pool._available_connections[0]._sock

    @skip_if_server_version_lt('2.8.8')
    def test_busy_loading_from_pipeline(self, r):
        """
        BusyLoadingErrors should be raised from a pipeline execution
        regardless of the raise_on_error flag.
        """
        pipe = r.pipeline()
        pipe.execute_command('DEBUG', 'ERROR', 'LOADING fake message')
        with pytest.raises(redis.BusyLoadingError):
            pipe.execute()
        pool = r.connection_pool
        assert not pipe.connection
        assert len(pool._available_connections) == 1
        assert not pool._available_connections[0]._sock

    @skip_if_server_version_lt('2.8.8')
    def test_read_only_error(self, r):
        "READONLY errors get turned in ReadOnlyError exceptions"
        with pytest.raises(redis.ReadOnlyError):
            r.execute_command('DEBUG', 'ERROR', 'READONLY blah blah')

    def test_connect_from_url_tcp(self):
        connection = redis.Redis.from_url('redis://localhost')
        pool = connection.connection_pool

        assert re.match('(.*)<(.*)<(.*)>>', repr(pool)).groups() == (
            'ConnectionPool',
            'Connection',
            'host=localhost,port=6379,db=0',
        )

    def test_connect_from_url_unix(self):
        connection = redis.Redis.from_url('unix:///path/to/socket')
        pool = connection.connection_pool

        assert re.match('(.*)<(.*)<(.*)>>', repr(pool)).groups() == (
            'ConnectionPool',
            'UnixDomainSocketConnection',
            'path=/path/to/socket,db=0',
        )

########NEW FILE########
__FILENAME__ = test_encoding
from __future__ import with_statement
import pytest

from redis._compat import unichr, u, unicode
from .conftest import r as _redis_client


class TestEncoding(object):
    @pytest.fixture()
    def r(self, request):
        return _redis_client(request=request, decode_responses=True)

    def test_simple_encoding(self, r):
        unicode_string = unichr(3456) + u('abcd') + unichr(3421)
        r['unicode-string'] = unicode_string
        cached_val = r['unicode-string']
        assert isinstance(cached_val, unicode)
        assert unicode_string == cached_val

    def test_list_encoding(self, r):
        unicode_string = unichr(3456) + u('abcd') + unichr(3421)
        result = [unicode_string, unicode_string, unicode_string]
        r.rpush('a', *result)
        assert r.lrange('a', 0, -1) == result


class TestCommandsAndTokensArentEncoded(object):
    @pytest.fixture()
    def r(self, request):
        return _redis_client(request=request, charset='utf-16')

    def test_basic_command(self, r):
        r.set('hello', 'world')

########NEW FILE########
__FILENAME__ = test_lock
from __future__ import with_statement
import pytest
import time

from redis.client import Lock, LockError


class TestLock(object):

    def test_lock(self, r):
        lock = r.lock('foo')
        assert lock.acquire()
        assert r['foo'] == str(Lock.LOCK_FOREVER).encode()
        lock.release()
        assert r.get('foo') is None

    def test_competing_locks(self, r):
        lock1 = r.lock('foo')
        lock2 = r.lock('foo')
        assert lock1.acquire()
        assert not lock2.acquire(blocking=False)
        lock1.release()
        assert lock2.acquire()
        assert not lock1.acquire(blocking=False)
        lock2.release()

    def test_timeouts(self, r):
        lock1 = r.lock('foo', timeout=1)
        lock2 = r.lock('foo')
        assert lock1.acquire()
        now = time.time()
        assert now < lock1.acquired_until < now + 1
        assert lock1.acquired_until == float(r['foo'])
        assert not lock2.acquire(blocking=False)
        time.sleep(2)  # need to wait up to 2 seconds for lock to timeout
        assert lock2.acquire(blocking=False)
        lock2.release()

    def test_non_blocking(self, r):
        lock1 = r.lock('foo')
        assert lock1.acquire(blocking=False)
        assert lock1.acquired_until
        lock1.release()
        assert lock1.acquired_until is None

    def test_context_manager(self, r):
        with r.lock('foo'):
            assert r['foo'] == str(Lock.LOCK_FOREVER).encode()
        assert r.get('foo') is None

    def test_float_timeout(self, r):
        lock1 = r.lock('foo', timeout=1.5)
        lock2 = r.lock('foo', timeout=1.5)
        assert lock1.acquire()
        assert not lock2.acquire(blocking=False)
        lock1.release()

    def test_high_sleep_raises_error(self, r):
        "If sleep is higher than timeout, it should raise an error"
        with pytest.raises(LockError):
            r.lock('foo', timeout=1, sleep=2)

########NEW FILE########
__FILENAME__ = test_pipeline
from __future__ import with_statement
import pytest

import redis
from redis._compat import b, u, unichr, unicode


class TestPipeline(object):
    def test_pipeline(self, r):
        with r.pipeline() as pipe:
            pipe.set('a', 'a1').get('a').zadd('z', z1=1).zadd('z', z2=4)
            pipe.zincrby('z', 'z1').zrange('z', 0, 5, withscores=True)
            assert pipe.execute() == \
                [
                    True,
                    b('a1'),
                    True,
                    True,
                    2.0,
                    [(b('z1'), 2.0), (b('z2'), 4)],
                ]

    def test_pipeline_length(self, r):
        with r.pipeline() as pipe:
            # Initially empty.
            assert len(pipe) == 0
            assert not pipe

            # Fill 'er up!
            pipe.set('a', 'a1').set('b', 'b1').set('c', 'c1')
            assert len(pipe) == 3
            assert pipe

            # Execute calls reset(), so empty once again.
            pipe.execute()
            assert len(pipe) == 0
            assert not pipe

    def test_pipeline_no_transaction(self, r):
        with r.pipeline(transaction=False) as pipe:
            pipe.set('a', 'a1').set('b', 'b1').set('c', 'c1')
            assert pipe.execute() == [True, True, True]
            assert r['a'] == b('a1')
            assert r['b'] == b('b1')
            assert r['c'] == b('c1')

    def test_pipeline_no_transaction_watch(self, r):
        r['a'] = 0

        with r.pipeline(transaction=False) as pipe:
            pipe.watch('a')
            a = pipe.get('a')

            pipe.multi()
            pipe.set('a', int(a) + 1)
            assert pipe.execute() == [True]

    def test_pipeline_no_transaction_watch_failure(self, r):
        r['a'] = 0

        with r.pipeline(transaction=False) as pipe:
            pipe.watch('a')
            a = pipe.get('a')

            r['a'] = 'bad'

            pipe.multi()
            pipe.set('a', int(a) + 1)

            with pytest.raises(redis.WatchError):
                pipe.execute()

            assert r['a'] == b('bad')

    def test_exec_error_in_response(self, r):
        """
        an invalid pipeline command at exec time adds the exception instance
        to the list of returned values
        """
        r['c'] = 'a'
        with r.pipeline() as pipe:
            pipe.set('a', 1).set('b', 2).lpush('c', 3).set('d', 4)
            result = pipe.execute(raise_on_error=False)

            assert result[0]
            assert r['a'] == b('1')
            assert result[1]
            assert r['b'] == b('2')

            # we can't lpush to a key that's a string value, so this should
            # be a ResponseError exception
            assert isinstance(result[2], redis.ResponseError)
            assert r['c'] == b('a')

            # since this isn't a transaction, the other commands after the
            # error are still executed
            assert result[3]
            assert r['d'] == b('4')

            # make sure the pipe was restored to a working state
            assert pipe.set('z', 'zzz').execute() == [True]
            assert r['z'] == b('zzz')

    def test_exec_error_raised(self, r):
        r['c'] = 'a'
        with r.pipeline() as pipe:
            pipe.set('a', 1).set('b', 2).lpush('c', 3).set('d', 4)
            with pytest.raises(redis.ResponseError) as ex:
                pipe.execute()
            assert unicode(ex.value).startswith('Command # 3 (LPUSH c 3) of '
                                                'pipeline caused error: ')

            # make sure the pipe was restored to a working state
            assert pipe.set('z', 'zzz').execute() == [True]
            assert r['z'] == b('zzz')

    def test_parse_error_raised(self, r):
        with r.pipeline() as pipe:
            # the zrem is invalid because we don't pass any keys to it
            pipe.set('a', 1).zrem('b').set('b', 2)
            with pytest.raises(redis.ResponseError) as ex:
                pipe.execute()

            assert unicode(ex.value).startswith('Command # 2 (ZREM b) of '
                                                'pipeline caused error: ')

            # make sure the pipe was restored to a working state
            assert pipe.set('z', 'zzz').execute() == [True]
            assert r['z'] == b('zzz')

    def test_watch_succeed(self, r):
        r['a'] = 1
        r['b'] = 2

        with r.pipeline() as pipe:
            pipe.watch('a', 'b')
            assert pipe.watching
            a_value = pipe.get('a')
            b_value = pipe.get('b')
            assert a_value == b('1')
            assert b_value == b('2')
            pipe.multi()

            pipe.set('c', 3)
            assert pipe.execute() == [True]
            assert not pipe.watching

    def test_watch_failure(self, r):
        r['a'] = 1
        r['b'] = 2

        with r.pipeline() as pipe:
            pipe.watch('a', 'b')
            r['b'] = 3
            pipe.multi()
            pipe.get('a')
            with pytest.raises(redis.WatchError):
                pipe.execute()

            assert not pipe.watching

    def test_unwatch(self, r):
        r['a'] = 1
        r['b'] = 2

        with r.pipeline() as pipe:
            pipe.watch('a', 'b')
            r['b'] = 3
            pipe.unwatch()
            assert not pipe.watching
            pipe.get('a')
            assert pipe.execute() == [b('1')]

    def test_transaction_callable(self, r):
        r['a'] = 1
        r['b'] = 2
        has_run = []

        def my_transaction(pipe):
            a_value = pipe.get('a')
            assert a_value in (b('1'), b('2'))
            b_value = pipe.get('b')
            assert b_value == b('2')

            # silly run-once code... incr's "a" so WatchError should be raised
            # forcing this all to run again. this should incr "a" once to "2"
            if not has_run:
                r.incr('a')
                has_run.append('it has')

            pipe.multi()
            pipe.set('c', int(a_value) + int(b_value))

        result = r.transaction(my_transaction, 'a', 'b')
        assert result == [True]
        assert r['c'] == b('4')

    def test_exec_error_in_no_transaction_pipeline(self, r):
        r['a'] = 1
        with r.pipeline(transaction=False) as pipe:
            pipe.llen('a')
            pipe.expire('a', 100)

            with pytest.raises(redis.ResponseError) as ex:
                pipe.execute()

            assert unicode(ex.value).startswith('Command # 1 (LLEN a) of '
                                                'pipeline caused error: ')

        assert r['a'] == b('1')

    def test_exec_error_in_no_transaction_pipeline_unicode_command(self, r):
        key = unichr(3456) + u('abcd') + unichr(3421)
        r[key] = 1
        with r.pipeline(transaction=False) as pipe:
            pipe.llen(key)
            pipe.expire(key, 100)

            with pytest.raises(redis.ResponseError) as ex:
                pipe.execute()

            expected = unicode('Command # 1 (LLEN %s) of pipeline caused '
                               'error: ') % key
            assert unicode(ex.value).startswith(expected)

        assert r[key] == b('1')

########NEW FILE########
__FILENAME__ = test_pubsub
from __future__ import with_statement
import pytest
import time

import redis
from redis.exceptions import ConnectionError
from redis._compat import basestring, u, unichr

from .conftest import r as _redis_client


def wait_for_message(pubsub, timeout=0.1, ignore_subscribe_messages=False):
    now = time.time()
    timeout = now + timeout
    while now < timeout:
        message = pubsub.get_message(
            ignore_subscribe_messages=ignore_subscribe_messages)
        if message is not None:
            return message
        time.sleep(0.01)
        now = time.time()
    return None


def make_message(type, channel, data, pattern=None):
    return {
        'type': type,
        'pattern': pattern and pattern.encode('utf-8') or None,
        'channel': channel.encode('utf-8'),
        'data': data.encode('utf-8') if isinstance(data, basestring) else data
    }


def make_subscribe_test_data(pubsub, type):
    if type == 'channel':
        return {
            'p': pubsub,
            'sub_type': 'subscribe',
            'unsub_type': 'unsubscribe',
            'sub_func': pubsub.subscribe,
            'unsub_func': pubsub.unsubscribe,
            'keys': ['foo', 'bar', u('uni') + unichr(4456) + u('code')]
        }
    elif type == 'pattern':
        return {
            'p': pubsub,
            'sub_type': 'psubscribe',
            'unsub_type': 'punsubscribe',
            'sub_func': pubsub.psubscribe,
            'unsub_func': pubsub.punsubscribe,
            'keys': ['f*', 'b*', u('uni') + unichr(4456) + u('*')]
        }
    assert False, 'invalid subscribe type: %s' % type


class TestPubSubSubscribeUnsubscribe(object):

    def _test_subscribe_unsubscribe(self, p, sub_type, unsub_type, sub_func,
                                    unsub_func, keys):
        for key in keys:
            assert sub_func(key) is None

        # should be a message for each channel/pattern we just subscribed to
        for i, key in enumerate(keys):
            assert wait_for_message(p) == make_message(sub_type, key, i + 1)

        for key in keys:
            assert unsub_func(key) is None

        # should be a message for each channel/pattern we just unsubscribed
        # from
        for i, key in enumerate(keys):
            i = len(keys) - 1 - i
            assert wait_for_message(p) == make_message(unsub_type, key, i)

    def test_channel_subscribe_unsubscribe(self, r):
        kwargs = make_subscribe_test_data(r.pubsub(), 'channel')
        self._test_subscribe_unsubscribe(**kwargs)

    def test_pattern_subscribe_unsubscribe(self, r):
        kwargs = make_subscribe_test_data(r.pubsub(), 'pattern')
        self._test_subscribe_unsubscribe(**kwargs)

    def _test_resubscribe_on_reconnection(self, p, sub_type, unsub_type,
                                          sub_func, unsub_func, keys):

        for key in keys:
            assert sub_func(key) is None

        # should be a message for each channel/pattern we just subscribed to
        for i, key in enumerate(keys):
            assert wait_for_message(p) == make_message(sub_type, key, i + 1)

        # manually disconnect
        p.connection.disconnect()

        # calling get_message again reconnects and resubscribes
        # note, we may not re-subscribe to channels in exactly the same order
        # so we have to do some extra checks to make sure we got them all
        messages = []
        for i in range(len(keys)):
            messages.append(wait_for_message(p))

        unique_channels = set()
        assert len(messages) == len(keys)
        for i, message in enumerate(messages):
            assert message['type'] == sub_type
            assert message['data'] == i + 1
            assert isinstance(message['channel'], bytes)
            channel = message['channel'].decode('utf-8')
            unique_channels.add(channel)

        assert len(unique_channels) == len(keys)
        for channel in unique_channels:
            assert channel in keys

    def test_resubscribe_to_channels_on_reconnection(self, r):
        kwargs = make_subscribe_test_data(r.pubsub(), 'channel')
        self._test_resubscribe_on_reconnection(**kwargs)

    def test_resubscribe_to_patterns_on_reconnection(self, r):
        kwargs = make_subscribe_test_data(r.pubsub(), 'pattern')
        self._test_resubscribe_on_reconnection(**kwargs)

    def _test_subscribed_property(self, p, sub_type, unsub_type, sub_func,
                                  unsub_func, keys):

        assert p.subscribed is False
        sub_func(keys[0])
        # we're now subscribed even though we haven't processed the
        # reply from the server just yet
        assert p.subscribed is True
        assert wait_for_message(p) == make_message(sub_type, keys[0], 1)
        # we're still subscribed
        assert p.subscribed is True

        # unsubscribe from all channels
        unsub_func()
        # we're still technically subscribed until we process the
        # response messages from the server
        assert p.subscribed is True
        assert wait_for_message(p) == make_message(unsub_type, keys[0], 0)
        # now we're no longer subscribed as no more messages can be delivered
        # to any channels we were listening to
        assert p.subscribed is False

        # subscribing again flips the flag back
        sub_func(keys[0])
        assert p.subscribed is True
        assert wait_for_message(p) == make_message(sub_type, keys[0], 1)

        # unsubscribe again
        unsub_func()
        assert p.subscribed is True
        # subscribe to another channel before reading the unsubscribe response
        sub_func(keys[1])
        assert p.subscribed is True
        # read the unsubscribe for key1
        assert wait_for_message(p) == make_message(unsub_type, keys[0], 0)
        # we're still subscribed to key2, so subscribed should still be True
        assert p.subscribed is True
        # read the key2 subscribe message
        assert wait_for_message(p) == make_message(sub_type, keys[1], 1)
        unsub_func()
        # haven't read the message yet, so we're still subscribed
        assert p.subscribed is True
        assert wait_for_message(p) == make_message(unsub_type, keys[1], 0)
        # now we're finally unsubscribed
        assert p.subscribed is False

    def test_subscribe_property_with_channels(self, r):
        kwargs = make_subscribe_test_data(r.pubsub(), 'channel')
        self._test_subscribed_property(**kwargs)

    def test_subscribe_property_with_patterns(self, r):
        kwargs = make_subscribe_test_data(r.pubsub(), 'pattern')
        self._test_subscribed_property(**kwargs)

    def test_ignore_all_subscribe_messages(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)

        checks = (
            (p.subscribe, 'foo'),
            (p.unsubscribe, 'foo'),
            (p.psubscribe, 'f*'),
            (p.punsubscribe, 'f*'),
        )

        assert p.subscribed is False
        for func, channel in checks:
            assert func(channel) is None
            assert p.subscribed is True
            assert wait_for_message(p) is None
        assert p.subscribed is False

    def test_ignore_individual_subscribe_messages(self, r):
        p = r.pubsub()

        checks = (
            (p.subscribe, 'foo'),
            (p.unsubscribe, 'foo'),
            (p.psubscribe, 'f*'),
            (p.punsubscribe, 'f*'),
        )

        assert p.subscribed is False
        for func, channel in checks:
            assert func(channel) is None
            assert p.subscribed is True
            message = wait_for_message(p, ignore_subscribe_messages=True)
            assert message is None
        assert p.subscribed is False


class TestPubSubMessages(object):
    def setup_method(self, method):
        self.message = None

    def message_handler(self, message):
        self.message = message

    def test_published_message_to_channel(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)
        p.subscribe('foo')
        assert r.publish('foo', 'test message') == 1

        message = wait_for_message(p)
        assert isinstance(message, dict)
        assert message == make_message('message', 'foo', 'test message')

    def test_published_message_to_pattern(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)
        p.subscribe('foo')
        p.psubscribe('f*')
        # 1 to pattern, 1 to channel
        assert r.publish('foo', 'test message') == 2

        message1 = wait_for_message(p)
        message2 = wait_for_message(p)
        assert isinstance(message1, dict)
        assert isinstance(message2, dict)

        expected = [
            make_message('message', 'foo', 'test message'),
            make_message('pmessage', 'foo', 'test message', pattern='f*')
        ]

        assert message1 in expected
        assert message2 in expected
        assert message1 != message2

    def test_channel_message_handler(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)
        p.subscribe(foo=self.message_handler)
        assert r.publish('foo', 'test message') == 1
        assert wait_for_message(p) is None
        assert self.message == make_message('message', 'foo', 'test message')

    def test_pattern_message_handler(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)
        p.psubscribe(**{'f*': self.message_handler})
        assert r.publish('foo', 'test message') == 1
        assert wait_for_message(p) is None
        assert self.message == make_message('pmessage', 'foo', 'test message',
                                            pattern='f*')

    def test_unicode_channel_message_handler(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)
        channel = u('uni') + unichr(4456) + u('code')
        channels = {channel: self.message_handler}
        p.subscribe(**channels)
        assert r.publish(channel, 'test message') == 1
        assert wait_for_message(p) is None
        assert self.message == make_message('message', channel, 'test message')

    def test_unicode_pattern_message_handler(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)
        pattern = u('uni') + unichr(4456) + u('*')
        channel = u('uni') + unichr(4456) + u('code')
        p.psubscribe(**{pattern: self.message_handler})
        assert r.publish(channel, 'test message') == 1
        assert wait_for_message(p) is None
        assert self.message == make_message('pmessage', channel,
                                            'test message', pattern=pattern)


class TestPubSubAutoDecoding(object):
    "These tests only validate that we get unicode values back"

    channel = u('uni') + unichr(4456) + u('code')
    pattern = u('uni') + unichr(4456) + u('*')
    data = u('abc') + unichr(4458) + u('123')

    def make_message(self, type, channel, data, pattern=None):
        return {
            'type': type,
            'channel': channel,
            'pattern': pattern,
            'data': data
        }

    def setup_method(self, method):
        self.message = None

    def message_handler(self, message):
        self.message = message

    @pytest.fixture()
    def r(self, request):
        return _redis_client(request=request, decode_responses=True)

    def test_channel_subscribe_unsubscribe(self, r):
        p = r.pubsub()
        p.subscribe(self.channel)
        assert wait_for_message(p) == self.make_message('subscribe',
                                                        self.channel, 1)

        p.unsubscribe(self.channel)
        assert wait_for_message(p) == self.make_message('unsubscribe',
                                                        self.channel, 0)

    def test_pattern_subscribe_unsubscribe(self, r):
        p = r.pubsub()
        p.psubscribe(self.pattern)
        assert wait_for_message(p) == self.make_message('psubscribe',
                                                        self.pattern, 1)

        p.punsubscribe(self.pattern)
        assert wait_for_message(p) == self.make_message('punsubscribe',
                                                        self.pattern, 0)

    def test_channel_publish(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)
        p.subscribe(self.channel)
        r.publish(self.channel, self.data)
        assert wait_for_message(p) == self.make_message('message',
                                                        self.channel,
                                                        self.data)

    def test_pattern_publish(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)
        p.psubscribe(self.pattern)
        r.publish(self.channel, self.data)
        assert wait_for_message(p) == self.make_message('pmessage',
                                                        self.channel,
                                                        self.data,
                                                        pattern=self.pattern)

    def test_channel_message_handler(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)
        p.subscribe(**{self.channel: self.message_handler})
        r.publish(self.channel, self.data)
        assert wait_for_message(p) is None
        assert self.message == self.make_message('message', self.channel,
                                                 self.data)

        # test that we reconnected to the correct channel
        p.connection.disconnect()
        assert wait_for_message(p) is None  # should reconnect
        new_data = self.data + u('new data')
        r.publish(self.channel, new_data)
        assert wait_for_message(p) is None
        assert self.message == self.make_message('message', self.channel,
                                                 new_data)

    def test_pattern_message_handler(self, r):
        p = r.pubsub(ignore_subscribe_messages=True)
        p.psubscribe(**{self.pattern: self.message_handler})
        r.publish(self.channel, self.data)
        assert wait_for_message(p) is None
        assert self.message == self.make_message('pmessage', self.channel,
                                                 self.data,
                                                 pattern=self.pattern)

        # test that we reconnected to the correct pattern
        p.connection.disconnect()
        assert wait_for_message(p) is None  # should reconnect
        new_data = self.data + u('new data')
        r.publish(self.channel, new_data)
        assert wait_for_message(p) is None
        assert self.message == self.make_message('pmessage', self.channel,
                                                 new_data,
                                                 pattern=self.pattern)


class TestPubSubRedisDown(object):

    def test_channel_subscribe(self, r):
        r = redis.Redis(host='localhost', port=6390)
        p = r.pubsub()
        with pytest.raises(ConnectionError):
            p.subscribe('foo')

########NEW FILE########
__FILENAME__ = test_scripting
from __future__ import with_statement
import pytest

from redis import exceptions
from redis._compat import b


multiply_script = """
local value = redis.call('GET', KEYS[1])
value = tonumber(value)
return value * ARGV[1]"""


class TestScripting(object):
    @pytest.fixture(autouse=True)
    def reset_scripts(self, r):
        r.script_flush()

    def test_eval(self, r):
        r.set('a', 2)
        # 2 * 3 == 6
        assert r.eval(multiply_script, 1, 'a', 3) == 6

    def test_evalsha(self, r):
        r.set('a', 2)
        sha = r.script_load(multiply_script)
        # 2 * 3 == 6
        assert r.evalsha(sha, 1, 'a', 3) == 6

    def test_evalsha_script_not_loaded(self, r):
        r.set('a', 2)
        sha = r.script_load(multiply_script)
        # remove the script from Redis's cache
        r.script_flush()
        with pytest.raises(exceptions.NoScriptError):
            r.evalsha(sha, 1, 'a', 3)

    def test_script_loading(self, r):
        # get the sha, then clear the cache
        sha = r.script_load(multiply_script)
        r.script_flush()
        assert r.script_exists(sha) == [False]
        r.script_load(multiply_script)
        assert r.script_exists(sha) == [True]

    def test_script_object(self, r):
        r.set('a', 2)
        multiply = r.register_script(multiply_script)
        assert not multiply.sha
        # test evalsha fail -> script load + retry
        assert multiply(keys=['a'], args=[3]) == 6
        assert multiply.sha
        assert r.script_exists(multiply.sha) == [True]
        # test first evalsha
        assert multiply(keys=['a'], args=[3]) == 6

    def test_script_object_in_pipeline(self, r):
        multiply = r.register_script(multiply_script)
        assert not multiply.sha
        pipe = r.pipeline()
        pipe.set('a', 2)
        pipe.get('a')
        multiply(keys=['a'], args=[3], client=pipe)
        # even though the pipeline wasn't executed yet, we made sure the
        # script was loaded and got a valid sha
        assert multiply.sha
        assert r.script_exists(multiply.sha) == [True]
        # [SET worked, GET 'a', result of multiple script]
        assert pipe.execute() == [True, b('2'), 6]

        # purge the script from redis's cache and re-run the pipeline
        # the multiply script object knows it's sha, so it shouldn't get
        # reloaded until pipe.execute()
        r.script_flush()
        pipe = r.pipeline()
        pipe.set('a', 2)
        pipe.get('a')
        assert multiply.sha
        multiply(keys=['a'], args=[3], client=pipe)
        assert r.script_exists(multiply.sha) == [False]
        # [SET worked, GET 'a', result of multiple script]
        assert pipe.execute() == [True, b('2'), 6]

########NEW FILE########
__FILENAME__ = test_sentinel
from __future__ import with_statement
import pytest

from redis import exceptions
from redis.sentinel import (Sentinel, SentinelConnectionPool,
                            MasterNotFoundError, SlaveNotFoundError)
from redis._compat import next
import redis.sentinel


class SentinelTestClient(object):
    def __init__(self, cluster, id):
        self.cluster = cluster
        self.id = id

    def sentinel_masters(self):
        self.cluster.connection_error_if_down(self)
        return {self.cluster.service_name: self.cluster.master}

    def sentinel_slaves(self, master_name):
        self.cluster.connection_error_if_down(self)
        if master_name != self.cluster.service_name:
            return []
        return self.cluster.slaves


class SentinelTestCluster(object):
    def __init__(self, service_name='mymaster', ip='127.0.0.1', port=6379):
        self.clients = {}
        self.master = {
            'ip': ip,
            'port': port,
            'is_master': True,
            'is_sdown': False,
            'is_odown': False,
            'num-other-sentinels': 0,
        }
        self.service_name = service_name
        self.slaves = []
        self.nodes_down = set()

    def connection_error_if_down(self, node):
        if node.id in self.nodes_down:
            raise exceptions.ConnectionError

    def client(self, host, port, **kwargs):
        return SentinelTestClient(self, (host, port))


@pytest.fixture()
def cluster(request):
    def teardown():
        redis.sentinel.StrictRedis = saved_StrictRedis
    cluster = SentinelTestCluster()
    saved_StrictRedis = redis.sentinel.StrictRedis
    redis.sentinel.StrictRedis = cluster.client
    request.addfinalizer(teardown)
    return cluster


@pytest.fixture()
def sentinel(request, cluster):
    return Sentinel([('foo', 26379), ('bar', 26379)])


def test_discover_master(sentinel):
    address = sentinel.discover_master('mymaster')
    assert address == ('127.0.0.1', 6379)


def test_discover_master_error(sentinel):
    with pytest.raises(MasterNotFoundError):
        sentinel.discover_master('xxx')


def test_discover_master_sentinel_down(cluster, sentinel):
    # Put first sentinel 'foo' down
    cluster.nodes_down.add(('foo', 26379))
    address = sentinel.discover_master('mymaster')
    assert address == ('127.0.0.1', 6379)
    # 'bar' is now first sentinel
    assert sentinel.sentinels[0].id == ('bar', 26379)


def test_master_min_other_sentinels(cluster):
    sentinel = Sentinel([('foo', 26379)], min_other_sentinels=1)
    # min_other_sentinels
    with pytest.raises(MasterNotFoundError):
        sentinel.discover_master('mymaster')
    cluster.master['num-other-sentinels'] = 2
    address = sentinel.discover_master('mymaster')
    assert address == ('127.0.0.1', 6379)


def test_master_odown(cluster, sentinel):
    cluster.master['is_odown'] = True
    with pytest.raises(MasterNotFoundError):
        sentinel.discover_master('mymaster')


def test_master_sdown(cluster, sentinel):
    cluster.master['is_sdown'] = True
    with pytest.raises(MasterNotFoundError):
        sentinel.discover_master('mymaster')


def test_discover_slaves(cluster, sentinel):
    assert sentinel.discover_slaves('mymaster') == []

    cluster.slaves = [
        {'ip': 'slave0', 'port': 1234, 'is_odown': False, 'is_sdown': False},
        {'ip': 'slave1', 'port': 1234, 'is_odown': False, 'is_sdown': False},
    ]
    assert sentinel.discover_slaves('mymaster') == [
        ('slave0', 1234), ('slave1', 1234)]

    # slave0 -> ODOWN
    cluster.slaves[0]['is_odown'] = True
    assert sentinel.discover_slaves('mymaster') == [
        ('slave1', 1234)]

    # slave1 -> SDOWN
    cluster.slaves[1]['is_sdown'] = True
    assert sentinel.discover_slaves('mymaster') == []

    cluster.slaves[0]['is_odown'] = False
    cluster.slaves[1]['is_sdown'] = False

    # node0 -> DOWN
    cluster.nodes_down.add(('foo', 26379))
    assert sentinel.discover_slaves('mymaster') == [
        ('slave0', 1234), ('slave1', 1234)]


def test_master_for(cluster, sentinel):
    master = sentinel.master_for('mymaster', db=9)
    assert master.ping()
    assert master.connection_pool.master_address == ('127.0.0.1', 6379)

    # Use internal connection check
    master = sentinel.master_for('mymaster', db=9, check_connection=True)
    assert master.ping()


def test_slave_for(cluster, sentinel):
    cluster.slaves = [
        {'ip': '127.0.0.1', 'port': 6379,
         'is_odown': False, 'is_sdown': False},
    ]
    slave = sentinel.slave_for('mymaster', db=9)
    assert slave.ping()


def test_slave_for_slave_not_found_error(cluster, sentinel):
    cluster.master['is_odown'] = True
    slave = sentinel.slave_for('mymaster', db=9)
    with pytest.raises(SlaveNotFoundError):
        slave.ping()


def test_slave_round_robin(cluster, sentinel):
    cluster.slaves = [
        {'ip': 'slave0', 'port': 6379, 'is_odown': False, 'is_sdown': False},
        {'ip': 'slave1', 'port': 6379, 'is_odown': False, 'is_sdown': False},
    ]
    pool = SentinelConnectionPool('mymaster', sentinel)
    rotator = pool.rotate_slaves()
    assert next(rotator) in (('slave0', 6379), ('slave1', 6379))
    assert next(rotator) in (('slave0', 6379), ('slave1', 6379))
    # Fallback to master
    assert next(rotator) == ('127.0.0.1', 6379)
    with pytest.raises(SlaveNotFoundError):
        next(rotator)

########NEW FILE########
