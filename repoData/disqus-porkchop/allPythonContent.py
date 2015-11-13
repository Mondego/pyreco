__FILENAME__ = backend
"""
porkchop.backend
~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""
import socket
import struct
import time
import cPickle


class Carbon(object):
    def __init__(self, host, port, logger):
        self.data = {}
        self.host = host
        self.port = port
        self.logger = logger
        try:
            self.sock = self._connect()
        except socket.error:
            self.logger.fatal('Unable to connect to carbon.')

    def _connect(self, waittime=5):
        self.logger.info('Connecting to carbon on %s:%d', self.host, self.port)
        try:
            sock = socket.socket()
            sock.connect((self.host, self.port))
        except socket.error:
            self.logger.info('Unable to connect to carbon, retrying in %d seconds', waittime)
            time.sleep(waittime)
            self._connect(waittime + 5)

        return sock

    def _send(self, data):
        try:
            self.sock.sendall(self._serialize(data.items()))
        except socket.error:
            raise

    def _serialize(self, data):
        serialized = cPickle.dumps(data, protocol=-1)
        prefix = struct.pack('!L', len(serialized))
        return prefix + serialized

    def send(self):
        """ self.data format: {metric_name: [(t1, val1), (t2, val2)]} """
        buf_sz = 500
        to_send = {}

        for mn in self.data.iterkeys():
            while len(self.data[mn]) > 0:
                l = len(to_send)
                if l < buf_sz:
                    to_send.setdefault(mn, [])
                    to_send[mn].append(self.data[mn].pop())
                else:
                    try:
                        self._send(to_send)
                        to_send = {}
                        to_send.setdefault(mn, [])
                        to_send[mn].append(self.data[mn].pop())
                    except socket.error:
                        self.logger.error('Error sending to carbon, trying to reconnect.')
                        self.sock = self._connect()

                        # we failed to send, so put it back in the stack and try later
                        for ent in to_send:
                            self.data[ent[0]].append(ent[1])

        try:
            self._send(to_send)
        except socket.error:
            self.logger.error('Error sending to carbon, trying to reconnect.')
            self.sock = self._connect()

        # we failed to send, so put it back in the stack and try later
        for ent in to_send:
            self.data[ent[0]].append(ent[1])

########NEW FILE########
__FILENAME__ = commandline
"""
porkchop.commandline
~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""
import logging
import socket
from optparse import OptionParser

from porkchop.plugin import PorkchopPluginHandler


def coerce_number(s):
    try:
        return int(s)
    except:
        return float(s)


def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def main():
    from porkchop.server import GetHandler, ThreadedHTTPServer
    config_dir = '/etc/porkchop.d'
    plugin_dir = '/usr/share/porkchop/plugins'
    listen_address = ''
    listen_port = 5000

    parser = OptionParser()
    parser.add_option('-c', dest='config_dir',
                      default=config_dir,
                      help='Load configs from DIR (default: %s)' % config_dir,
                      metavar='DIR')
    parser.add_option('-d', dest='plugin_dir',
                      default=plugin_dir,
                      help='Load plugins from DIR (default: %s)' % plugin_dir,
                      metavar='DIR')
    parser.add_option('-s', dest='listen_address',
                      default=listen_address,
                      help='Bind to ADDRESS', metavar='ADDRESS')
    parser.add_option('-p', type="int", dest='listen_port',
                      default=listen_port,
                      help='Bind to PORT (default: %d)' % listen_port,
                      metavar='PORT')

    (options, args) = parser.parse_args()

    socket.setdefaulttimeout(3)
    PorkchopPluginHandler(options.config_dir, options.plugin_dir)
    server = ThreadedHTTPServer((options.listen_address, options.listen_port),
                                GetHandler)
    server.serve_forever()


def collector():
    import requests
    import sys
    import time

    from porkchop.backend import Carbon
    from porkchop.util import PorkchopUtil

    carbon_host = 'localhost'
    carbon_port = 2004
    data = {}
    porkchop_url = 'http://localhost:5000/'

    interval = 60
    prefix = 'porkchop.%s' % socket.gethostname().split('.')[0].replace('.', '_')

    parser = OptionParser()
    parser.add_option('--carbon-host', dest='carbon_host',
                      default=carbon_host,
                      help='Connect to carbon on HOST (default: %s)' % carbon_host,
                      metavar='HOST')
    parser.add_option('--carbon-port', type='int', dest='carbon_port',
                      default=carbon_port,
                      help='Connect to carbon on PORT (default: %d)' % carbon_port,
                      metavar='PORT')
    parser.add_option('--porkchop-url', dest='porkchop_url',
                      default=porkchop_url,
                      help='Connect to porkchop on URL (default: %s)' % porkchop_url,
                      metavar='URL')
    parser.add_option('-i', type='int', dest='interval',
                      default=interval,
                      help='Fetch data at INTERVAL seconds (default: %d)' % interval,
                      metavar='INTERVAL')
    parser.add_option('-n', dest='noop',
                      default=False,
                      help='Don\'t actually send to graphite',
                      action='store_true')
    parser.add_option('-P', dest='prefix',
                      default=prefix,
                      help='Graphite prefix (default: %s)' % prefix)
    parser.add_option('-v', dest='verbose',
                      default=False,
                      help='Verbose logging',
                      action='store_true')

    (options, args) = parser.parse_args()

    if options.verbose:
        logger = get_logger('porkchop-collector', logging.DEBUG)
    else:
        logger = get_logger('porkchop-collector')

    if not options.noop:
        carbon = Carbon(options.carbon_host, options.carbon_port, logger)

    while True:
        now = int(time.time())
        try:
            logger.debug('Fetching porkchop data from %s', options.porkchop_url)
            r = requests.get(options.porkchop_url,
                             timeout=options.interval,
                             headers={'x-porkchop-refresh': 'true'})
            r.raise_for_status()
        except:
            logger.error('Got bad response code from porkchop: %s', sys.exc_info()[1])

        for line in r.content.strip('\n').splitlines():
            (key, val) = line.lstrip('/').split(' ', 1)
            key = PorkchopUtil.char_filter(key)
            key = '.'.join([options.prefix, key.replace('/', '.')])
            data.setdefault(key, [])

            try:
                data[key].append((now, coerce_number(val)))

                for met in data.keys():
                    for datapoint in data[met]:
                        logger.debug('Sending: %s %s %s', met, datapoint[0], datapoint[1])

                if not options.noop:
                    carbon.data = data
                    carbon.send()
            except:
                pass

        sleep_time = options.interval - (int(time.time()) - now)
        if sleep_time > 0:
            logger.info('Sleeping for %d seconds', sleep_time)
            time.sleep(sleep_time)

########NEW FILE########
__FILENAME__ = plugin
"""
porkchop.plugin
~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""
from collections import defaultdict
import glob
import imp
import inspect
import os
import sys
import socket
import time

from porkchop.util import PorkchopUtil


class InfiniteDict(defaultdict):
    def __init__(self, type=None, *args, **kwargs):
        super(InfiniteDict, self).__init__(type or self.__class__)


class DotDict(defaultdict):
    def __init__(self):
        defaultdict.__init__(self, DotDict)
    def __setitem__(self, key, value):
        keys = key.split('.')
        for key in keys[:-1]:
            self = self[key]
        defaultdict.__setitem__(self, keys[-1], value)


class PorkchopPlugin(object):
    config_file = None
    __delta = None
    __prev = None
    __cache = None
    __data = {}
    __lastrefresh = 0
    refresh = 60
    force_refresh = False

    def __init__(self, handler):
        self.handler = handler

    @property
    def data(self):
        if self.should_refresh():
            self.config = PorkchopUtil.parse_config(self.config_file)
            if self.prev_data is None:
                self.__class__.__delta = 1
                self.prev_data = self.get_data()
                time.sleep(1)
            else:
                self.prev_data = self.__class__.__data
            self.data = self.get_data()

        result = self.format_data(self.__class__.__data)
        if not result:
            return result
        result['refreshtime'] = self.__class__.__lastrefresh
        return result

    @data.setter
    def data(self, value):
        now = time.time()
        self.__class__.__data = value
        self.__class__.__delta = int(now - self.__class__.__lastrefresh)
        self.__class__.__lastrefresh = now
        self.force_refresh = False

    @property
    def delta(self):
        return self.__class__.__delta

    @property
    def prev_data(self):
        return self.__class__.__prev

    @prev_data.setter
    def prev_data(self, value):
        self.__class__.__prev = value

    def format_data(self, data):
        return data

    def gendict(self, type='infinite'):
        if type.lower() == 'dot':
            return DotDict()
        return InfiniteDict()

    def rateof(self, a, b, ival=None):
        if ival is None:
            ival = self.delta

        a = float(a)
        b = float(b)

        try:
            return (b - a) / ival if (b - a) != 0 else 0
        except ZeroDivisionError:
            if a:
                return -a
            return b

    def should_refresh(self):
        if self.force_refresh:
            return True

        if self.__class__.__lastrefresh != 0:
            return time.time() - self.__class__.__lastrefresh > self.refresh
        return True

    def tcp_socket(self, host, port):
        sock = socket.socket()
        sock.connect((host, port))

        return sock

    def unix_socket(self, path):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(path)

        return sock

    def log_error(self, *args, **kwargs):
        return self.handler.log_error(*args, **kwargs)


class PorkchopPluginHandler(object):
    plugins = {}

    def __init__(self, config_dir, directory=None):
        self.config_dir = config_dir
        self.config = PorkchopUtil.parse_config(os.path.join(self.config_dir,
            'porkchop.ini'))

        if directory:
            self.__class__.plugins.update(self.load_plugins(directory))

        self.__class__.plugins.update(
            self.load_plugins(
                os.path.join(os.path.dirname(__file__), 'plugins')
            )
        )

    def load_plugins(self, directory):
        plugins = {}
        sys.path.insert(0, directory)

        try:
            to_load = [p.strip() for p in self.config['porkchop']['plugins'].split(',')]
        except:
            to_load = []

        for infile in glob.glob(os.path.join(directory, '*.py')):
            module_name = os.path.splitext(os.path.split(infile)[1])[0]

            if os.path.basename(infile) == '__init__.py':
                continue
            if to_load and module_name not in to_load:
                continue

            try:
                module = imp.load_source(module_name, infile)
                for namek, klass in inspect.getmembers(module):
                    if inspect.isclass(klass) \
                       and issubclass(klass, PorkchopPlugin) \
                       and klass is not PorkchopPlugin:

                        if hasattr(klass, '__metric_name__'):
                            plugin_name = klass.__metric_name__
                        else:
                            plugin_name = module_name

                        plugins[plugin_name] = klass
                        plugins[plugin_name].config_file = os.path.join(
                            self.config_dir,
                            '%s.ini' % plugin_name
                        )

                        # Only one plugin per module.
                        break

            except ImportError:
                print 'Unable to load plugin %r' % infile
                import traceback
                traceback.print_exc()

        return plugins

########NEW FILE########
__FILENAME__ = server
"""
porkchop.server
~~~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
import json
import traceback
import urlparse

from porkchop.plugin import PorkchopPluginHandler


class GetHandler(BaseHTTPRequestHandler):
    def format_output(self, fmt, data):
        if fmt == 'json':
            return json.dumps(data)
        else:
            return '\n'.join(self.json_path(data))

    def json_path(self, data):
        results = []

        def path_helper(data, path, results):
            for key, val in data.iteritems():
                if isinstance(val,  dict):
                    path_helper(val, '/'.join((path, key)), results)
                else:
                    results.append(('%s %s' % (('/'.join((path, key)))\
                           .replace('.', '_'), val)))

        path_helper(data, '', results)
        return results

    def do_GET(self):
        data = {}
        formats = {'json': 'application/json', 'text': 'text/plain'}
        request = urlparse.urlparse(self.path)

        try:
            (path, fmt) = request.path.split('.')
            if fmt not in formats.keys():
                fmt = 'text'
        except ValueError:
            path = request.path
            if self.headers.get('accept', False) == 'application/json':
                fmt = 'json'
            else:
                fmt = 'text'

        if self.headers.get('x-porkchop-refresh', False):
            force_refresh = True
        else:
            force_refresh = False

        module = path.split('/')[1]

        try:
            if module:
                plugin = PorkchopPluginHandler.plugins[module](self)
                plugin.force_refresh = force_refresh
                self.log_message('Calling plugin: %s with force=%s' % (module, force_refresh))
                data.update({module: plugin.data})
            else:
                for plugin_name, plugin in PorkchopPluginHandler.plugins.iteritems():
                    try:
                        plugin.force_refresh = force_refresh
                        self.log_message('Calling plugin: %s with force=%s' % (plugin_name, force_refresh))
                        # if the plugin has no data, it'll only have one key:
                        # refreshtime
                        result = plugin(self).data
                        if len(result) > 1:
                            data.update({plugin_name: result})
                    except Exception, e:
                        self.log_error('Error loading plugin: name=%s exception=%s, traceback=%s', plugin_name, e,
                                       traceback.format_exc())

            if len(data):
                self.send_response(200)
                self.send_header('Content-Type', formats[fmt])
                self.end_headers()
                self.wfile.write(self.format_output(fmt, data) + '\n')
            else:
                raise Exception('Unable to load any plugins')
        except Exception, e:
            self.log_error('Error: %s\n%s', e, traceback.format_exc())
            self.send_response(404)
            self.send_header('Content-Type', formats[fmt])
            self.end_headers()
            self.wfile.write(self.format_output(fmt, {}))


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

########NEW FILE########
__FILENAME__ = util
"""
porkchop.util
~~~~~~~~~~~~~

:copyright: (c) 2011-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""
import ConfigParser


class PorkchopUtil(object):
    @classmethod
    def parse_config(self, path):
        config = {}
        cp = ConfigParser.ConfigParser()
        cp.read(path)

        for s in cp.sections():
            config.setdefault(s, {})
            for o in cp.options(s):
                config[s][o] = cp.get(s, o)

        return config


    @classmethod
    def char_filter(cls, s):
        import string

        wanted = string.letters + string.digits + string.punctuation
        return "".join(c for c in s if c in wanted and not c == '.')

########NEW FILE########
