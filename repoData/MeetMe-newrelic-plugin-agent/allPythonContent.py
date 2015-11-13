__FILENAME__ = agent
"""
Multiple Plugin Agent for the New Relic Platform

"""
import helper
import importlib
import json
import logging
import os
import requests
import socket
import sys
import Queue as queue
import threading
import time

from newrelic_plugin_agent import __version__
from newrelic_plugin_agent import plugins

LOGGER = logging.getLogger(__name__)


class NewRelicPluginAgent(helper.Controller):
    """The NewRelicPluginAgent class implements a agent that polls plugins
    every minute and reports the state to NewRelic.

    """
    IGNORE_KEYS = ['license_key', 'proxy', 'endpoint',
                   'poll_interval', 'wake_interval']
    MAX_METRICS_PER_REQUEST = 10000
    PLATFORM_URL = 'https://platform-api.newrelic.com/platform/v1/metrics'
    WAKE_INTERVAL = 60

    def __init__(self, args, operating_system):
        """Initialize the NewRelicPluginAgent object.

        :param argparse.Namespace args: Command line arguments
        :param str operating_system: The operating_system name

        """
        super(NewRelicPluginAgent, self).__init__(args, operating_system)
        self.derive_last_interval = dict()
        self.endpoint = self.PLATFORM_URL
        self.http_headers = {'Accept': 'application/json',
                             'Content-Type': 'application/json'}
        self.last_interval_start = None
        self.min_max_values = dict()
        self._wake_interval = (self.config.application.get('wake_interval') or
                               self.config.application.get('poll_interval') or
                               self.WAKE_INTERVAL)
        self.next_wake_interval = int(self._wake_interval)
        self.publish_queue = queue.Queue()
        self.threads = list()
        info = tuple([__version__] + list(self.system_platform))
        LOGGER.info('Agent v%s initialized, %s %s v%s', *info)

    def setup(self):
        """Setup the internal state for the controller class. This is invoked
        on Controller.run().

        Items requiring the configuration object should be assigned here due to
        startup order of operations.

        """
        if hasattr(self.config.application, 'endpoint'):
            self.endpoint = self.config.application.endpoint
        self.http_headers['X-License-Key'] = self.license_key
        self.last_interval_start = time.time()

    @property
    def agent_data(self):
        """Return the agent data section of the NewRelic Platform data payload

        :rtype: dict

        """
        return {'host': socket.gethostname(),
                'pid': os.getpid(),
                'version': __version__}

    @property
    def license_key(self):
        """Return the NewRelic license key from the configuration values.

        :rtype: str

        """
        return self.config.application.license_key

    def poll_plugin(self, plugin_name, plugin, config):
        """Kick off a background thread to run the processing task.

        :param newrelic_plugin_agent.plugins.base.Plugin plugin: The plugin
        :param dict config: The config for the plugin

        """

        if not isinstance(config, (list, tuple)):
            config = [config]

        for instance in config:
            thread = threading.Thread(target=self.thread_process,
                                      kwargs={'config': instance,
                                              'name': plugin_name,
                                              'plugin': plugin,
                                              'poll_interval':
                                                  int(self._wake_interval)})
            thread.run()
            self.threads.append(thread)

    def process(self):
        """This method is called after every sleep interval. If the intention
        is to use an IOLoop instead of sleep interval based daemon, override
        the run method.

        """
        start_time = time.time()
        self.start_plugin_polling()

        # Sleep for a second while threads are running
        while self.threads_running:
            time.sleep(1)

        self.threads = list()
        self.send_data_to_newrelic()
        duration = time.time() - start_time
        self.next_wake_interval = self._wake_interval - duration
        if self.next_wake_interval < 1:
            LOGGER.warning('Poll interval took greater than %i seconds',
                           duration)
            self.next_wake_interval = int(self._wake_interval)
        LOGGER.info('Stats processed in %.2f seconds, next wake in %i seconds',
                    duration, self.next_wake_interval)

    def process_min_max_values(self, component):
        """Agent keeps track of previous values, so compute the differences for
        min/max values.

        :param dict component: The component to calc min/max values for

        """
        guid = component['guid']
        name = component['name']

        if guid not in self.min_max_values.keys():
            self.min_max_values[guid] = dict()

        if name not in self.min_max_values[guid].keys():
            self.min_max_values[guid][name] = dict()

        for metric in component['metrics']:
            min_val, max_val = self.min_max_values[guid][name].get(metric,
                                                                   (None, None))
            value = component['metrics'][metric]['total']
            if min_val is not None and min_val > value:
                min_val = value

            if max_val is None or max_val < value:
                max_val = value

            if component['metrics'][metric]['min'] is None:
                component['metrics'][metric]['min'] = min_val or value

            if component['metrics'][metric]['max'] is None:
                component['metrics'][metric]['max'] = max_val

            self.min_max_values[guid][name][metric] = min_val, max_val

    @property
    def proxies(self):
        """Return the proxy used to access NewRelic.

        :rtype: dict

        """
        if 'proxy' in self.config.application:
            return {
                'http': self.config.application['proxy'],
                'https': self.config.application['proxy']
            }
        return None

    def send_data_to_newrelic(self):
        metrics = 0
        components = list()
        while self.publish_queue.qsize():
            (name, data, last_values) = self.publish_queue.get()
            self.derive_last_interval[name] = last_values
            if isinstance(data, list):
                for component in data:
                    self.process_min_max_values(component)
                    metrics += len(component['metrics'].keys())
                    if metrics >= self.MAX_METRICS_PER_REQUEST:
                        self.send_components(components, metrics)
                        components = list()
                        metrics = 0
                    components.append(component)

            elif isinstance(data, dict):
                self.process_min_max_values(data)
                metrics += len(data['metrics'].keys())
                if metrics >= self.MAX_METRICS_PER_REQUEST:
                    self.send_components(components, metrics)
                    components = list()
                    metrics = 0
                components.append(data)

        LOGGER.debug('Done, will send remainder of %i metrics', metrics)
        self.send_components(components, metrics)

    def send_components(self, components, metrics):
        """Create the headers and payload to send to NewRelic platform as a
        JSON encoded POST body.

        """
        if not metrics:
            LOGGER.warning('No metrics to send to NewRelic this interval')
            return

        LOGGER.info('Sending %i metrics to NewRelic', metrics)
        body = {'agent': self.agent_data, 'components': components}
        LOGGER.debug(body)
        try:
            response = requests.post(self.endpoint,
                                     headers=self.http_headers,
                                     proxies=self.proxies,
                                     data=json.dumps(body, ensure_ascii=False),
                                     timeout=self.config.get('newrelic_api_timeout', 10),
                                     verify=self.config.get('verify_ssl_cert',
                                                            True))
            LOGGER.debug('Response: %s: %r',
                         response.status_code,
                         response.content.strip())
        except requests.ConnectionError as error:
            LOGGER.error('Error reporting stats: %s', error)
        except requests.Timeout as error:
            LOGGER.error('TimeoutError reporting stats: %s', error)

    @staticmethod
    def _get_plugin(plugin_path):
        """Given a qualified class name (eg. foo.bar.Foo), return the class

        :rtype: object

        """
        try:
            package, class_name = plugin_path.rsplit('.', 1)
        except ValueError:
            return None

        try:
            module_handle = importlib.import_module(package)
            class_handle = getattr(module_handle, class_name)
            return class_handle
        except ImportError:
            LOGGER.exception('Attempting to import %s', plugin_path)
            return None

    def start_plugin_polling(self):
        """Iterate through each plugin and start the polling process."""
        for plugin in [key for key in self.config.application.keys()
                       if key not in self.IGNORE_KEYS]:
            LOGGER.info('Enabling plugin: %s', plugin)
            plugin_class = None

            # If plugin is part of the core agent plugin list
            if plugin in plugins.available:
                plugin_class = self._get_plugin(plugins.available[plugin])

            # If plugin is in config and a qualified class name
            elif '.' in plugin:
                plugin_class = self._get_plugin(plugin)

            # If plugin class could not be imported
            if not plugin_class:
                LOGGER.error('Enabled plugin %s not available', plugin)
                continue

            self.poll_plugin(plugin, plugin_class,
                             self.config.application.get(plugin))

    @property
    def threads_running(self):
        """Return True if any of the child threads are alive

        :rtype: bool

        """
        for thread in self.threads:
            if thread.is_alive():
                return True
        return False

    def thread_process(self, name, plugin, config, poll_interval):
        """Created a thread process for the given name, plugin class,
        config and poll interval. Process is added to a Queue object which
        used to maintain the stack of running plugins.

        :param str name: The name of the plugin
        :param newrelic_plugin_agent.plugin.Plugin plugin: The plugin class
        :param dict config: The plugin configuration
        :param int poll_interval: How often the plugin is invoked

        """
        instance_name = "%s:%s" % (name, config.get('name', 'unnamed'))
        obj = plugin(config, poll_interval,
                     self.derive_last_interval.get(instance_name))
        obj.poll()
        self.publish_queue.put((instance_name, obj.values(),
                                obj.derive_last_interval))

    @property
    def wake_interval(self):
        """Return the wake interval in seconds as the number of seconds
        until the next minute.

        :rtype: int

        """
        return self.next_wake_interval


def main():
    helper.parser.description('The NewRelic Plugin Agent polls various '
                              'services and sends the data to the NewRelic '
                              'Platform')
    helper.parser.name('newrelic_plugin_agent')
    argparse = helper.parser.get()
    argparse.add_argument('-C',
                          action='store_true',
                          dest='configure',
                          help='Run interactive configuration')
    args = helper.parser.parse()
    if args.configure:
        print('Configuration')
        sys.exit(0)
    helper.start(NewRelicPluginAgent)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()

########NEW FILE########
__FILENAME__ = apache_httpd
"""
ApacheHTTPD Support

"""
import logging
import re

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

PATTERN = re.compile(r'^([\w\s{1}]+):\s([\d\.{1}]+)', re.M)


class ApacheHTTPD(base.HTTPStatsPlugin):

    DEFAULT_QUERY = 'auto'
    GUID = 'com.meetme.newrelic_apache_httpd_agent'
    KEYS = {'Total Accesses': {'type': '',
                               'label': 'Totals/Requests',
                               'suffix': 'requests'},
            'BusyWorkers': {'type': 'gauge',
                            'label': 'Workers/Busy',
                            'suffix': 'workers'},
            'Total kBytes': {'type': '',
                             'label': 'Totals/Bytes Sent',
                             'suffix': 'kb'},
            'BytesPerSec': {'type': 'gauge',
                            'label': 'Bytes/Per Second',
                            'suffix': 'bytes/sec'},
            'BytesPerReq': {'type': 'gauge',
                            'label': 'Requests/Average Payload Size',
                            'suffix': 'bytes'},
            'IdleWorkers': {'type': 'gauge', 'label': 'Workers/Idle',
                            'suffix': 'workers'},
            'CPULoad': {'type': 'gauge', 'label': 'CPU Load',
                        'suffix': 'processes'},
            'ReqPerSec': {'type': 'gauge', 'label': 'Requests/Velocity',
                          'suffix': 'requests/sec'},
            'Uptime': {'type': 'gauge', 'label': 'Uptime', 'suffix': 'sec'},
            'ConnsTotal': {'type': 'gauge', 'label': 'Connections/Total', 'suffix': 'conns'},
            'ConnsAsyncWriting': {'type': 'gauge', 'label': 'Connections/AsyncWriting', 'suffix': 'conns'},
            'ConnsAsyncKeepAlive': {'type': 'gauge', 'label': 'Connections/AsyncKeepAlive', 'suffix': 'conns'},
            'ConnsAsyncClosing': {'type': 'gauge', 'label': 'Connections/AsyncClosing', 'suffix': 'conns'},
            '_': {'type': 'gauge', 'label': 'Scoreboard/Waiting For Conn', 'suffix': 'slots'},
            'S': {'type': 'gauge', 'label': 'Scoreboard/Starting Up', 'suffix': 'slots'},
            'R': {'type': 'gauge', 'label': 'Scoreboard/Reading Request', 'suffix': 'slots'},
            'W': {'type': 'gauge', 'label': 'Scoreboard/Sending Reply', 'suffix': 'slots'},
            'K': {'type': 'gauge', 'label': 'Scoreboard/Keepalive Read', 'suffix': 'slots'},
            'D': {'type': 'gauge', 'label': 'Scoreboard/DNS Lookup', 'suffix': 'slots'},
            'C': {'type': 'gauge', 'label': 'Scoreboard/Closing Conn', 'suffix': 'slots'},
            'L': {'type': 'gauge', 'label': 'Scoreboard/Logging', 'suffix': 'slots'},
            'G': {'type': 'gauge', 'label': 'Scoreboard/Gracefully Finishing', 'suffix': 'slots'},
            'I': {'type': 'gauge', 'label': 'Scoreboard/Idle Cleanup', 'suffix': 'slots'},
            '.': {'type': 'gauge', 'label': 'Scoreboard/Open Slot', 'suffix': 'slots'}}

    def error_message(self):
        LOGGER.error('Could not match any of the stats, please make ensure '
                     'Apache HTTPd is configured correctly. If you report '
                     'this as a bug, please include the full output of the '
                     'status page from %s in your ticket', self.stats_url)

    def get_scoreboard(self, data):
        """Fetch the scoreboard from the stats URL

        :rtype: str

        """
        keys = ['_', 'S', 'R', 'W', 'K', 'D', 'C', 'L', 'G', 'I', '.']
        values = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        score_out = dict(zip(keys, values))

        for line in data.splitlines():
            if line.find('Scoreboard') != -1:
                scoreboard = line.replace('Scoreboard: ','')
                for i in range(0, len(scoreboard)):
                    score_out[scoreboard[i]] += 1
        return score_out

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param str stats: The stats content from Apache as a string

        """
        matches = PATTERN.findall(stats or '')
        for key, value in matches:

            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    value = 0

            if key in self.KEYS:
                if self.KEYS[key].get('type') == 'gauge':
                    self.add_gauge_value(self.KEYS[key]['label'],
                                         self.KEYS[key].get('suffix', ''),
                                         value)
                else:
                    self.add_derive_value(self.KEYS[key]['label'],
                                          self.KEYS[key].get('suffix', ''),
                                          value)
            else:
                LOGGER.debug('Found unmapped key/value pair: %s = %s',
                             key, value)
        
        score_data = self.get_scoreboard(stats)
        for key, value in score_data.iteritems():
            if key in self.KEYS:
                if self.KEYS[key].get('type') == 'gauge':
                    self.add_gauge_value(self.KEYS[key]['label'],
                                         self.KEYS[key].get('suffix', ''),
                                         value)
                else:
                    self.add_derive_value(self.KEYS[key]['label'],
                                          self.KEYS[key].get('suffix', ''),
                                          value)
            else:
                LOGGER.debug('Found unmapped key/value pair: %s = %s',
                             key, value)


########NEW FILE########
__FILENAME__ = base
"""
Base Plugin Classes

"""
import csv
import logging
from os import path
import requests
import socket
import tempfile
import time
import urlparse

LOGGER = logging.getLogger(__name__)


class Plugin(object):

    GUID = 'com.meetme.newrelic_plugin_agent'
    MAX_VAL = 2147483647

    def __init__(self, config, poll_interval, last_interval_values=None):
        self.config = config
        LOGGER.debug('%s config: %r', self.__class__.__name__, self.config)
        self.poll_interval = poll_interval
        self.poll_start_time = 0

        self.derive_values = dict()
        self.derive_last_interval = last_interval_values or dict()
        self.gauge_values = dict()

    def add_datapoints(self, data):
        """Extend this method to process the data points retrieved during the
        poll process.

        :param mixed data: The data received during the poll process

        """
        raise NotImplementedError

    def add_derive_value(self, metric_name, units, value, count=None):
        """Add a value that will derive the current value from the difference
        between the last interval value and the current value.

        If this is the first time a stat is being added, it will report a 0
        value until the next poll interval and it is able to calculate the
        derivative value.

        :param str metric_name: The name of the metric
        :param str units: The unit type
        :param int value: The value to add
        :param int count: The number of items the timing is for

        """
        if value is None:
            value = 0
        metric = self.metric_name(metric_name, units)
        if metric not in self.derive_last_interval.keys():
            LOGGER.debug('Bypassing initial %s value for first run', metric)
            self.derive_values[metric] = self.metric_payload(0, count=0)
        else:
            cval = value - self.derive_last_interval[metric]
            self.derive_values[metric] = self.metric_payload(cval, count=count)
            LOGGER.debug('%s: Last: %r, Current: %r, Reporting: %r',
                         metric, self.derive_last_interval[metric], value,
                         self.derive_values[metric])
        self.derive_last_interval[metric] = value

    def add_derive_timing_value(self, metric_name, units, count, total_value,
                                last_value=None):
        """For timing based metrics that have a count of objects for the timing
        and an optional last value.

        :param str metric_name: The name of the metric
        :param str units: The unit type
        :param int count: The number of items the timing is for
        :param int total_value: The timing value
        :param int last_value: The last value

        """
        if last_value is None:
            return self.add_derive_value(metric_name, units,
                                         total_value, count)
        self.add_derive_value('%s/Total' % metric_name,
                              units, total_value, count)
        self.add_derive_value('%s/Last' % metric_name,
                              units, last_value, count)

    def add_gauge_value(self, metric_name, units, value,
                        min_val=None, max_val=None, count=None,
                        sum_of_squares=None):
        """Add a value that is not a rolling counter but rather an absolute
        gauge

        :param str metric_name: The name of the metric
        :param str units: The unit type
        :param int value: The value to add
        :param float value: The sum of squares for the values

        """
        metric = self.metric_name(metric_name, units)
        self.gauge_values[metric] = self.metric_payload(value,
                                                        min_val,
                                                        max_val,
                                                        count,
                                                        sum_of_squares)
        LOGGER.debug('%s: %r', metric_name, self.gauge_values[metric])

    def component_data(self):
        """Create the component section of the NewRelic Platform data payload
        message.

        :rtype: dict

        """
        metrics = dict()
        metrics.update(self.derive_values.items())
        metrics.update(self.gauge_values.items())
        return {'name': self.name,
                'guid': self.GUID,
                'duration': self.poll_interval,
                'metrics': metrics}

    def error_message(self):
        """Output an error message when stats collection fails"""
        LOGGER.error('Error collecting stats data from %s. Please check '
                     'configuration and sure it conforms with YAML '
                     'syntax', self.__class__.__name__)

    def finish(self):
        """Note the end of the stat collection run and let the user know of any
        errors.

        """
        if not self.derive_values and not self.gauge_values:
            self.error_message()
        else:
            LOGGER.info('%s poll successful, completed in %.2f seconds',
                        self.__class__.__name__,
                        time.time() - self.poll_start_time)

    def initialize(self):
        """Empty stats collection dictionaries for the polling interval"""
        self.poll_start_time = time.time()
        self.derive_values = dict()
        self.gauge_values = dict()

    def initialize_counters(self, keys):
        """Create a new set of counters for the given key list

        :param list keys: Keys to initialize in the counters
        :rtype: tuple

        """
        count, total, min_val, max_val, values = (dict(), dict(), dict(),
                                                  dict(), dict())
        for key in keys:
            (count[key], total[key], min_val[key],
             max_val[key], values[key]) = 0, 0, self.MAX_VAL, 0, list()
        return count, total, min_val, max_val, values

    def metric_name(self, metric, units):
        """Return the metric name in the format for the NewRelic platform

        :param str metric: The name of th metric
        :param str units: The unit name

        """
        if not units:
            return 'Component/%s' % metric
        return 'Component/%s[%s]' % (metric, units)

    def metric_payload(self, value, min_value=None, max_value=None, count=None,
                       squares=None):
        """Return the metric in the standard payload format for the NewRelic
        agent.

        :rtype: dict

        """
        if isinstance(value, basestring):
            value = 0

        sum_of_squares = int(squares or (value * value))
        if sum_of_squares > self.MAX_VAL:
            sum_of_squares = 0

        return {'min': min_value,
                'max': max_value,
                'total': value,
                'count': count or 1,
                'sum_of_squares': sum_of_squares}

    @property
    def name(self):
        """Return the name of the component

        :rtype: str

        """
        return self.config.get('name', socket.gethostname().split('.')[0])

    def poll(self):
        """Poll the server returning the results in the expected component
        format.

        """
        raise NotImplementedError

    def sum_of_squares(self, values):
        """Return the sum_of_squares for the given values

        :param list values: The values list
        :rtype: float

        """
        value_sum = sum(values)
        if not value_sum:
            return 0
        squares = list()
        for value in values:
            squares.append(value * value)
        return sum(squares) - float(value_sum * value_sum) / len(values)

    def values(self):
        """Return the poll results

        :rtype: dict

        """
        return self.component_data()


class SocketStatsPlugin(Plugin):
    """Connect to a socket and collect stats data"""
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 0
    SOCKET_RECV_MAX = 10485760

    def connect(self):
        """Top level interface to create a socket and connect it to the
        socket.

        :rtype: socket

        """
        try:
            connection = self.socket_connect()
        except socket.error as error:
            LOGGER.error('Error connecting to %s: %s',
                         self.__class__.__name__, error)
        else:
            return connection

    def fetch_data(self, connection, read_till_empty=False):
        """Read the data from the socket

        :param  socket connection: The connection

        """
        LOGGER.debug('Fetching data')
        received = connection.recv(self.SOCKET_RECV_MAX)
        while read_till_empty:
            chunk = connection.recv(self.SOCKET_RECV_MAX)
            if chunk:
                received += chunk
            else:
                break
        return received

    def poll(self):
        """This method is called after every sleep interval. If the intention
        is to use an IOLoop instead of sleep interval based daemon, override
        the run method.

        """
        LOGGER.info('Polling %s', self.__class__.__name__)
        self.initialize()

        # Fetch the data from the remote socket
        connection = self.connect()
        if not connection:
            LOGGER.error('%s could not connect, skipping poll interval',
                         self.__class__.__name__)
            return

        data = self.fetch_data(connection)
        connection.close()

        if data:
            self.add_datapoints(data)
            self.finish()
        else:
            self.error_message()

    def socket_connect(self):
        """Low level interface to create a socket and connect to it.

        :rtype: socket

        """
        if 'path' in self.config:
            if path.exists(self.config['path']):
                LOGGER.debug('Connecting to UNIX domain socket: %s',
                             self.config['path'])
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                connection.connect(self.config['path'])
            else:
                LOGGER.error('UNIX domain socket path does not exist: %s',
                             self.config['path'])
                return None
        else:
            remote_host = (self.config.get('host', self.DEFAULT_HOST),
                           self.config.get('port', self.DEFAULT_PORT))
            LOGGER.debug('Connecting to %r', remote_host)
            connection = socket.socket()
            connection.connect(remote_host)
        return connection


class HTTPStatsPlugin(Plugin):
    """Extend the Plugin class overriding poll for targets that provide data
    via HTTP protocol.

    """
    DEFAULT_PATH = '/'
    DEFAULT_QUERY = None

    def fetch_data(self):
        """Fetch the data from the stats URL

        :rtype: str

        """
        data = self.http_get()
        return data.content if data else ''

    def http_get(self):
        """Fetch the data from the stats URL

        :rtype: requests.models.Response

        """
        LOGGER.debug('Polling %s Stats at %s',
                     self.__class__.__name__, self.stats_url)
        try:
            response = requests.get(**self.request_kwargs)
        except requests.ConnectionError as error:
            LOGGER.error('Error polling stats: %s', error)
            return ''

        if response.status_code >= 300:
            LOGGER.error('Error response from %s (%s): %s', self.stats_url,
                         response.status_code, response.content)
            return None
        return response

    def poll(self):
        """Poll HTTP server for stats data"""
        self.initialize()
        data = self.fetch_data()
        if data:
            self.add_datapoints(data)
        self.finish()

    @property
    def stats_url(self):
        """Return the configured URL in a uniform way for all HTTP based data
        sources.

        :rtype: str

        """
        netloc = self.config.get('host', 'localhost')
        if self.config.get('port'):
            netloc += ':%s' % self.config['port']

        return urlparse.urlunparse((self.config.get('scheme', 'http'),
                                    netloc,
                                    self.config.get('path', self.DEFAULT_PATH),
                                    None,
                                    self.config.get('query',
                                                    self.DEFAULT_QUERY),
                                    None))

    @property
    def request_kwargs(self):
        """Return kwargs for a HTTP request.

        :rtype: dict

        """
        kwargs = {'url': self.stats_url}
        if self.config.get('scheme') == 'https':
            kwargs['verify'] = self.config.get('verify_ssl_cert', False)

        if 'username' in self.config and 'password' in self.config:
            kwargs['auth'] = (self.config['username'], self.config['password'])

        LOGGER.debug('Request kwargs: %r', kwargs)
        return kwargs


class CSVStatsPlugin(HTTPStatsPlugin):
    """Extend the Plugin overriding poll for targets that provide JSON output
    for stats collection

    """
    def fetch_data(self):
        """Fetch the data from the stats URL

        :rtype: dict

        """
        data = super(CSVStatsPlugin, self).fetch_data()
        if not data:
            return dict()
        temp = tempfile.TemporaryFile()
        temp.write(data)
        temp.seek(0)
        reader = csv.DictReader(temp)
        data = list()
        for row in reader:
            data.append(row)
        temp.close()
        return data

    def poll(self):
        """Poll HTTP JSON endpoint for stats data"""
        self.initialize()
        data = self.fetch_data()
        if data:
            self.add_datapoints(data)
        self.finish()


class JSONStatsPlugin(HTTPStatsPlugin):
    """Extend the Plugin overriding poll for targets that provide JSON output
    for stats collection

    """
    def fetch_data(self):
        """Fetch the data from the stats URL

        :rtype: dict

        """
        data = self.http_get()
        try:
            return data.json() if data else {}
        except Exception as error:
            LOGGER.error('JSON decoding error: %r', error)
        return {}

    def poll(self):
        """Poll HTTP JSON endpoint for stats data"""
        self.initialize()
        data = self.fetch_data()
        if data:
            self.add_datapoints(data)
        self.finish()

########NEW FILE########
__FILENAME__ = couchdb
"""
CouchDB

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class CouchDB(base.JSONStatsPlugin):

    DEFAULT_PATH = '/_stats'
    GUID = 'com.meetme.newrelic_couchdb_agent'

    HTTP_METHODS = ['COPY', 'DELETE', 'GET', 'HEAD', 'POST', 'PUT']
    STATUS_CODES = [200, 201, 202, 301, 304, 400, 401,
                    403, 404, 405, 409, 412, 500]

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        LOGGER.debug('Stats: %r', stats)
        self.add_database_stats(stats['couchdb'])
        self.add_request_methods(stats['httpd_request_methods'])
        self.add_request_stats(stats['couchdb'], stats['httpd'])
        self.add_response_code_stats(stats['httpd_status_codes'])

    def add_database_stats(self, stats):
        self.add_gauge_value('Database/Open', 'dbs',
                             stats['open_databases'].get('current', 0),
                             stats['open_databases'].get('min', 0),
                             stats['open_databases'].get('max', 0))
        self.add_derive_value('Database/IO/Reads', 'iops',
                              stats['database_reads'].get('current', 0))
        self.add_derive_value('Database/IO/Writes', 'iops',
                              stats['database_writes'].get('current', 0))
        self.add_gauge_value('Files/Open', 'files',
                             stats['open_os_files'].get('current', 0),
                             stats['open_os_files'].get('min', 0),
                             stats['open_os_files'].get('max', 0))

    def add_request_stats(self, couchdb, httpd):
        self.add_derive_value('Requests/Duration', 'seconds',
                              couchdb['request_time'].get('current', 0))
        self.add_derive_value('Requests/Type/Document', 'requests',
                              httpd['requests'].get('current', 0))
        self.add_derive_value('Requests/Type/Bulk', 'requests',
                              httpd['bulk_requests'].get('current', 0))
        self.add_derive_value('Requests/Type/View', 'requests',
                              httpd['view_reads'].get('current', 0))
        self.add_derive_value('Requests/Type/Temporary View', 'requests',
                              httpd['temporary_view_reads'].get('current', 0))

    def add_request_methods(self, stats):
        for method in self.HTTP_METHODS:
            self.add_derive_value('Requests/Method/%s' % method, 'requests',
                                  stats[method].get('current', 0))

    def add_response_code_stats(self, stats):
        for code in self.STATUS_CODES:
            self.add_derive_value('Requests/Response/%s' % code, 'requests',
                                  stats[str(code)].get('current', 0))

########NEW FILE########
__FILENAME__ = elasticsearch
"""
Elastic Search

"""
import logging
import requests

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class ElasticSearch(base.JSONStatsPlugin):

    DERIVE_PARTIAL = ['Opens', 'Errs', 'Segs']
    DERIVE_MATCH = ['total', 'completed', 'rejected',
                    'total_opened', 'collection_count']
    GAUGE_MATCH = ['Current']

    DEFAULT_HOST = 'localhost'
    DEFAULT_PATH = '/_nodes/stats?all'
    DEFAULT_PORT = 9200
    GUID = 'com.meetme.newrelic_elasticsearch_node_agent'

    def add_datapoints(self, stats):
        """Add all of the datapoints for the Elasticsearch poll

        :param dict stats: The stats to process for the values

        """
        totals = dict()
        for node in stats.get('nodes'):
            for key in stats['nodes'][node].keys():
                if isinstance(stats['nodes'][node][key], dict):
                    if key not in totals:
                        totals[key] = dict()
                    self.process_tree(totals[key],
                                      stats['nodes'][node][key])

        self.add_index_datapoints(totals)
        self.add_network_datapoints(totals)
        self.add_cluster_stats()

    def add_cluster_stats(self):
        """Add stats that go under Component/Cluster"""
        url = self.stats_url.replace(self.DEFAULT_PATH, '/_cluster/health')
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            self.add_gauge_value('Cluster/Nodes', 'nodes',
                                 data.get('number_of_nodes', 0))
            self.add_gauge_value('Cluster/Data Nodes', 'nodes',
                                 data.get('number_of_data_nodes', 0))
            self.add_gauge_value('Cluster/Shards/Active', 'shards',
                                 data.get('active_shards', 0))
            self.add_gauge_value('Cluster/Shards/Initializing', 'shards',
                                 data.get('initializing_shards', 0))
            self.add_gauge_value('Cluster/Shards/Primary', 'shards',
                                 data.get('active_primary_shards', 0))
            self.add_gauge_value('Cluster/Shards/Relocating', 'shards',
                                 data.get('relocating_shards', 0))
            self.add_gauge_value('Cluster/Shards/Unassigned', 'shards',
                                 data.get('unassigned_shards', 0))
        else:
            LOGGER.error('Error collecting cluster stats (%s): %s',
                         response.status_code, response.content)

    def add_index_datapoints(self, stats):
        """Add the data points for Component/Indices

        :param dict stats: The stats to process for the values

        """
        indices = stats.get('indices', dict())

        docs = indices.get('docs', dict())
        self.add_gauge_value('Indices/Documents/Count', 'docs',
                             docs.get('count', 0))
        self.add_derive_value('Indices/Documents/Added', 'docs',
                              docs.get('count', 0))
        self.add_derive_value('Indices/Documents/Deleted', 'docs',
                              docs.get('deleted', 0))

        store = indices.get('store', dict())
        self.add_gauge_value('Indices/Storage', 'bytes',
                             store.get('size_in_bytes', 0))
        self.add_derive_value('Indices/Storage Throttled', 'ms',
                              store.get('throttle_time_in_millis', 0))

        indexing = indices.get('indexing', dict())
        self.add_derive_value('Indices/Indexing', 'ms',
                              indexing.get('index_time_in_millis', 0))
        self.add_derive_value('Indices/Indexing', 'count',
                              indexing.get('index_total', 0))
        self.add_derive_value('Indices/Index Deletes', 'ms',
                              indexing.get('delete_time_in_millis', 0))
        self.add_derive_value('Indices/Index Deletes', 'count',
                              indexing.get('delete_total', 0))

        get_stats = indices.get('get', dict())
        self.add_derive_value('Indices/Get', 'count',
                             get_stats.get('total', 0))
        self.add_derive_value('Indices/Get', 'ms',
                              get_stats.get('time_in_millis', 0))
        self.add_derive_value('Indices/Get Hits', 'count',
                              get_stats.get('exists_total', 0))
        self.add_derive_value('Indices/Get Hits', 'ms',
                              get_stats.get('exists_time_in_millis', 0))
        self.add_derive_value('Indices/Get Misses', 'count',
                              get_stats.get('missing_total', 0))
        self.add_derive_value('Indices/Get Misses', 'ms',
                              get_stats.get('missing_time_in_millis', 0))

        search = indices.get('search', dict())
        self.add_gauge_value('Indices/Open Search Contexts', 'count',
                             search.get('open_contexts', 0))
        self.add_derive_value('Indices/Search Query', 'count',
                             search.get('query_total', 0))
        self.add_derive_value('Indices/Search Query', 'ms',
                              search.get('query_time_in_millis', 0))

        self.add_derive_value('Indices/Search Fetch', 'count',
                             search.get('fetch_total', 0))
        self.add_derive_value('Indices/Search Fetch', 'ms',
                              search.get('fetch_time_in_millis', 0))

        merge_stats = indices.get('merge', dict())
        self.add_derive_value('Indices/Merge', 'count',
                              merge_stats.get('total', 0))
        self.add_derive_value('Indices/Merge', 'ms',
                              merge_stats.get('total_time_in_millis', 0))

        flush_stats = indices.get('flush', dict())
        self.add_gauge_value('Indices/Flush', 'count',
                             flush_stats.get('total', 0))
        self.add_derive_value('Indices/Flush', 'ms',
                              flush_stats.get('total_time_in_millis', 0))

    def add_network_datapoints(self, stats):
        """Add the data points for Component/Network

        :param dict stats: The stats to process for the values

        """
        transport = stats.get('transport', dict())
        self.add_derive_value('Network/Traffic/Received', 'bytes',
                              transport.get('rx_size_in_bytes', 0))
        self.add_derive_value('Network/Traffic/Sent', 'bytes',
                              transport.get('tx_size_in_bytes', 0))

        network = stats.get('network', dict())
        self.add_derive_value('Network/Connections/Active', 'conn',
                              network.get('active_opens', 0))
        self.add_derive_value('Network/Connections/Passive', 'conn',
                              network.get('passive_opens', 0))
        self.add_derive_value('Network/Connections/Reset', 'conn',
                              network.get('estab_resets', 0))
        self.add_derive_value('Network/Connections/Failures', 'conn',
                              network.get('attempt_fails', 0))

        self.add_derive_value('Network/HTTP Connections', 'conn',
                              stats.get('http', dict()).get('total_opened', 0))

        self.add_derive_value('Network/Segments/In', 'seg',
                              network.get('in_seg', 0))
        self.add_derive_value('Network/Segments/In', 'errors',
                              network.get('in_errs', 0))
        self.add_derive_value('Network/Segments/Out', 'seg',
                              network.get('out_seg', 0))
        self.add_derive_value('Network/Segments/Retransmitted', 'seg',
                              network.get('retrans_segs', 0))

    def process_tree(self, tree, values):
        """Recursively combine all node stats into a single top-level value

        :param dict tree: The output values
        :param dict values: The input values

        """
        for key in values:
            if key == 'timestamp':
                continue
            if isinstance(values[key], dict):
                if key not in tree:
                    tree[key] = dict()
                    self.process_tree(tree[key], values[key])
            elif isinstance(values[key], int):
                if key not in tree:
                    tree[key] = 0
                tree[key] += values[key]

########NEW FILE########
__FILENAME__ = haproxy
"""
HAProxy Support

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class HAProxy(base.CSVStatsPlugin):

    DEFAULT_PATH = 'haproxy?stats;csv'
    GUID = 'com.meetme.newrelic_haproxy_agent'
    UNIT = {'Queue': {'Current': 'connections', 'Max': 'connections'},
            'Sessions': {'Current': 'sessions', 'Max': 'sessions',
                         'Total': 'sessions'},
            'Denied': {'Request': 'requests', 'Response': 'responses'},
            'Errors': {'Request': 'requests', 'Response': 'responses',
                       'Connections': 'connections'},
            'Warnings': {'Retry': 'retries', 'Redispatch': 'redispatches'},
            'Server': {'Downtime': 'ms'},
            'Bytes': {'In': 'bytes', 'Out': 'bytes'}}

    def sum_data(self, stats):
        """Return the summed data as a dict

        :rtype: dict

        """
        data = {'Queue': {'Current': 0, 'Max': 0},
                'Sessions': {'Current': 0, 'Max': 0, 'Total': 0},
                'Bytes': {'In': 0, 'Out': 0},
                'Denied': {'Request': 0, 'Response': 0},
                'Errors': {'Request': 0, 'Response': 0, 'Connections': 0},
                'Warnings': {'Retry': 0, 'Redispatch': 0},
                'Server': {'Downtime': 0}}
        for row in stats:
            data['Queue']['Current'] += int(row.get('qcur') or 0)
            data['Queue']['Max'] += int(row.get('qmax') or 0)
            data['Sessions']['Current'] += int(row.get('scur') or 0)
            data['Sessions']['Max'] += int(row.get('smax') or 0)
            data['Sessions']['Total'] += int(row.get('stot') or 0)
            data['Bytes']['In'] += int(row.get('bin') or 0)
            data['Bytes']['Out'] += int(row.get('bout') or 0)
            data['Denied']['Request'] += int(row.get('dreq') or 0)
            data['Denied']['Response'] += int(row.get('dresp') or 0)
            data['Errors']['Request'] += int(row.get('ereq') or 0)
            data['Errors']['Response'] += int(row.get('eresp') or 0)
            data['Errors']['Connections'] += int(row.get('econ') or 0)
            data['Warnings']['Retry'] += int(row.get('wretr') or 0)
            data['Warnings']['Redispatch'] += int(row.get('wredis') or 0)
            data['Server']['Downtime'] += int(row.get('downtime') or 0)
        return data

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param list stats: The parsed csv content

        """
        if not stats:
            return
        stats = self.sum_data(stats)

        for section in [key for key in stats.keys() if key != 'server']:
            for key in stats[section].keys():
                self.add_derive_value('%s/%s' % (section, key),
                                      self.UNIT.get(section,
                                                    dict()).get(key, ''),
                                      stats[section][key])
        self.add_gauge_value('Server/Downtime', 'ms',
                             stats['Server']['Downtime'])

########NEW FILE########
__FILENAME__ = memcached
"""
memcached

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class Memcached(base.SocketStatsPlugin):

    GUID = 'com.meetme.newrelic_memcached_agent'
    DEFAULT_PORT = 11211
    KEYS = ['curr_connections',
            'curr_items',
            'connection_structures',
            'cmd_get',
            'cmd_set',
            'cmd_flush',
            'get_hits',
            'get_misses',
            'delete_hits',
            'delete_misses',
            'incr_hits',
            'incr_misses',
            'decr_hits',
            'decr_misses',
            'cas_hits',
            'cas_misses',
            'cas_badval',
            'auth_cmds',
            'auth_errors',
            'bytes_read',
            'bytes_written',
            'bytes',
            'total_items',
            'evictions',
            'rusage_user',
            'conn_yields',
            'rusage_system']

    SOCKET_RECV_MAX = 32768

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.command_value('CAS', 'cas', stats)
        self.add_derive_value('Command/Requests/Flush', 'flush',
                              stats['cmd_flush'])
        self.add_derive_value('Command/Errors/CAS', 'errors',
                              stats['cas_badval'])
        self.command_value('Decr', 'decr', stats)
        self.command_value('Delete', 'delete', stats)
        self.command_value('Get', 'get', stats)
        self.command_value('Incr', 'incr', stats)
        self.add_derive_value('Command/Requests/Set', '', stats['cmd_set'])

        self.add_gauge_value('Connection/Count', 'connections',
                             stats['curr_connections'])
        self.add_gauge_value('Connection/Structures', 'connection structures',
                             stats['connection_structures'])
        self.add_derive_value('Connection/Yields', 'yields',
                              stats['conn_yields'])
        self.add_derive_value('Evictions', 'items', stats['evictions'])
        self.add_gauge_value('Items', 'items', stats['curr_items'])

        self.add_derive_value('Network/In', 'bytes', stats['bytes_read'])
        self.add_derive_value('Network/Out', 'bytes', stats['bytes_written'])

        self.add_derive_value('System/CPU/System', 'seconds',
                              stats['rusage_user'])
        self.add_derive_value('System/CPU/User', 'seconds',
                              stats['rusage_user'])
        self.add_gauge_value('System/Memory', 'bytes', stats['bytes'])

    def command_value(self, name, prefix, stats):
        """Process commands adding the command and the hit ratio.

        :param str name: The command name
        :param str prefix: The command prefix
        :param dict stats: The request stats

        """
        total = stats['%s_hits' % prefix] + stats['%s_misses' % prefix]
        if total > 0:
            ratio = (float(stats['%s_hits' % prefix]) / float(total)) * 100
        else:
            ratio = 0
        self.add_derive_value('Command/Requests/%s' % name, 'requests', total)
        self.add_gauge_value('Command/Hit Ratio/%s' % name, 'ratio', ratio)

    def fetch_data(self, connection):
        """Loop in and read in all the data until we have received it all.

        :param  socket connection: The connection

        """
        connection.send("stats\n")
        data = super(Memcached, self).fetch_data(connection)
        data_in = []
        for line in data.replace('\r', '').split('\n'):
            if line == 'END':
                return self.process_data(data_in)
            data_in.append(line.strip())
        return None

    def process_data(self, data):
        """Loop through all the rows and parse each line, looking to see if it
        is in the data points we would like to process, adding the key => value
        pair to values if it is.

        :param list data: The list of rows
        :returns: dict

        """
        values = dict()
        for row in data:
            parts = row.split(' ')
            if parts[1] in self.KEYS:
                try:
                    values[parts[1]] = int(parts[2])
                except ValueError:
                    try:
                        values[parts[1]] = float(parts[2])
                    except ValueError:
                        LOGGER.warning('Could not parse line: %r', parts)
                        values[parts[1]] = 0

        # Back fill any missed data
        for key in self.KEYS:
            if key not in values:
                LOGGER.info('Populating missing element with 0: %s', key)
                values[key] = 0

        # Return the values dict
        return values

########NEW FILE########
__FILENAME__ = mongodb
"""
MongoDB Support

"""
import datetime
from pymongo import errors
import logging
import pymongo

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class MongoDB(base.Plugin):

    GUID = 'com.meetme.newrelic_mongodb_plugin_agent'

    def add_datapoints(self, name, stats):
        """Add all of the data points for a database

        :param str name: The name of the database for the stats
        :param dict stats: The stats data to add

        """
        base_key = 'Database/%s' % name
        self.add_gauge_value('%s/Extents' % base_key, 'extents',
                             stats.get('extents', 0))
        self.add_gauge_value('%s/Size' % base_key, 'bytes',
                             stats.get('dataSize', 0) / 1048576)
        self.add_gauge_value('%s/File Size' % base_key, 'bytes',
                             stats.get('fileSize', 0) / 1048576)
        self.add_gauge_value('%s/Objects' % base_key, 'objects',
                             stats.get('objects', 0))
        self.add_gauge_value('%s/Collections' % base_key, 'collections',
                             stats.get('collections', 0))
        self.add_gauge_value('%s/Index/Count' % base_key, 'indexes',
                             stats.get('indexes', 0))
        self.add_gauge_value('%s/Index/Size' % base_key, 'bytes',
                             stats.get('indexSize', 0))

    def add_server_datapoints(self, stats):
        """Add all of the data points for a server

        :param dict stats: The stats data to add

        """
        asserts = stats.get('asserts', dict())
        self.add_derive_value('Asserts/Regular', 'asserts',
                              asserts.get('regular', 0))
        self.add_derive_value('Asserts/Warning', 'asserts',
                              asserts.get('warning', 0))
        self.add_derive_value('Asserts/Message', 'asserts',
                              asserts.get('msg', 0))
        self.add_derive_value('Asserts/User', 'asserts',
                              asserts.get('user', 0))
        self.add_derive_value('Asserts/Rollovers', 'asserts',
                              asserts.get('rollovers', 0))

        flush = stats.get('backgroundFlushing', dict())
        self.add_derive_timing_value('Background Flushes',
                                     'ms',
                                     flush.get('flushes', 0),
                                     flush.get('total_ms', 0),
                                     flush.get('last_ms', 0))
        self.add_gauge_value('Seconds since last flush',
                             'seconds',
                             (datetime.datetime.now() -
                              flush.get('last_finished',
                                        datetime.datetime.now())).seconds)

        conn = stats.get('connections', dict())
        self.add_gauge_value('Connections/Available', 'connections',
                             conn.get('available', 0))
        self.add_gauge_value('Connections/Current', 'connections',
                             conn.get('current', 0))

        cursors = stats.get('cursors', dict())
        self.add_gauge_value('Cursors/Open', 'cursors',
                             cursors.get('totalOpen', 0))
        self.add_derive_value('Cursors/Timed Out', 'cursors',
                              cursors.get('timedOut', 0))

        dur = stats.get('dur', dict())
        self.add_gauge_value('Durability/Commits in Write Lock', 'commits',
                             dur.get('commitsInWriteLock', 0))
        self.add_gauge_value('Durability/Early Commits', 'commits',
                             dur.get('earlyCommits', 0))
        self.add_gauge_value('Durability/Journal Commits', 'commits',
                             dur.get('commits', 0))
        self.add_gauge_value('Durability/Journal Bytes Written', 'bytes',
                             dur.get('journaledMB', 0) / 1048576)
        self.add_gauge_value('Durability/Data File Bytes Written', 'bytes',
                             dur.get('writeToDataFilesMB', 0) / 1048576)

        timems = dur.get('timeMs', dict())
        self.add_gauge_value('Durability/Timings/Duration Measured', 'ms',
                             timems.get('dt', 0))
        self.add_gauge_value('Durability/Timings/Log Buffer Preparation', 'ms',
                             timems.get('prepLogBuffer', 0))
        self.add_gauge_value('Durability/Timings/Write to Journal', 'ms',
                             timems.get('writeToJournal', 0))
        self.add_gauge_value('Durability/Timings/Write to Data Files', 'ms',
                             timems.get('writeToDataFiles', 0))
        self.add_gauge_value('Durability/Timings/Remaping Private View', 'ms',
                             timems.get('remapPrivateView', 0))

        locks = stats.get('globalLock', dict())
        self.add_derive_value('Global Locks/Held', 'ms',
                              locks.get('lockTime', 0) / 1000)
        self.add_derive_value('Global Locks/Ratio', 'ratio',
                              locks.get('ratio', 0))

        active = locks.get('activeClients', dict())
        self.add_derive_value('Global Locks/Active Clients/Total', 'clients',
                              active.get('total', 0))
        self.add_derive_value('Global Locks/Active Clients/Readers', 'clients',
                              active.get('readers', 0))
        self.add_derive_value('Global Locks/Active Clients/Writers', 'clients',
                              active.get('writers', 0))

        queue = locks.get('currentQueue', dict())
        self.add_derive_value('Global Locks/Queue/Total', 'locks',
                              queue.get('total', 0))
        self.add_derive_value('Global Locks/Queue/Readers', 'readers',
                              queue.get('readers', 0))
        self.add_derive_value('Global Locks/Queue/Writers', 'writers',
                              queue.get('writers', 0))

        index = stats.get('indexCounters', dict())
        btree_index = index.get('btree', dict())
        self.add_derive_value('Index/Accesses', 'accesses',
                              index.get('accesses', 0) +
                              btree_index.get('accesses', 0))
        self.add_derive_value('Index/Hits', 'hits',
                              index.get('hits', 0) +
                              btree_index.get('hits', 0))
        self.add_derive_value('Index/Misses', 'misses',
                              index.get('misses', 0) +
                              btree_index.get('misses', 0))
        self.add_derive_value('Index/Resets', 'resets',
                              index.get('resets', 0) +
                              btree_index.get('resets', 0))

        mem = stats.get('mem', dict())
        self.add_gauge_value('Memory/Mapped', 'bytes',
                             mem.get('mapped', 0) / 1048576)
        self.add_gauge_value('Memory/Mapped with Journal', 'bytes',
                             mem.get('mappedWithJournal', 0) / 1048576)
        self.add_gauge_value('Memory/Resident', 'bytes',
                             mem.get('resident', 0) / 1048576)
        self.add_gauge_value('Memory/Virtual', 'bytes',
                             mem.get('virtual', 0) / 1048576)

        net = stats.get('network', dict())
        self.add_derive_value('Network/Requests', 'requests',
                              net.get('numRequests', 0))
        self.add_derive_value('Network/Transfer/In', 'bytes',
                              net.get('bytesIn', 0))
        self.add_derive_value('Network/Transfer/Out', 'bytes',
                              net.get('bytesOut', 0))

        ops = stats.get('opcounters', dict())
        self.add_derive_value('Operations/Insert', 'ops', ops.get('insert', 0))
        self.add_derive_value('Operations/Query', 'ops', ops.get('query', 0))
        self.add_derive_value('Operations/Update', 'ops', ops.get('update', 0))
        self.add_derive_value('Operations/Delete', 'ops', ops.get('delete', 0))
        self.add_derive_value('Operations/Get More', 'ops',
                              ops.get('getmore', 0))
        self.add_derive_value('Operations/Command', 'ops',
                              ops.get('command', 0))

        extra = stats.get('extra_info', dict())
        self.add_gauge_value('System/Heap Usage', 'bytes',
                             extra.get('heap_usage_bytes', 0))
        self.add_derive_value('System/Page Faults', 'faults',
                              extra.get('page_faults', 0))

    def connect(self):
        kwargs = {'host': self.config.get('host', 'localhost'),
                  'port': self.config.get('port', 27017)}
        for key in ['ssl', 'ssl_keyfile', 'ssl_certfile',
                    'ssl_cert_reqs', 'ssl_ca_certs']:
            if key in self.config:
                kwargs[key] = self.config[key]
        try:
            return pymongo.MongoClient(**kwargs)
        except pymongo.errors.ConnectionFailure as error:
            LOGGER.error('Could not connect to MongoDB: %s', error)

    def get_and_add_db_stats(self):
        """Fetch the data from the MongoDB server and add the datapoints

        """
        databases = self.config.get('databases', list())
        if isinstance(databases, list):
            self.get_and_add_db_list(databases)
        else:
            self.get_and_add_db_dict(databases)

    def get_and_add_db_list(self, databases):
        """Handle the list of databases while supporting authentication for
        the admin if needed

        :param list databases: The database list

        """
        LOGGER.debug('Processing list of mongo databases')
        client = self.connect()
        if not client:
            return
        for database in databases:
            LOGGER.debug('Collecting stats for %s', database)
            db = client[database]
            try:
                self.add_datapoints(database, db.command('dbStats'))
            except errors.OperationFailure as error:
                LOGGER.critical('Could not fetch stats: %s', error)

    def get_and_add_db_dict(self, databases):
        """Handle the nested database structure with username and password.

        :param dict databases: The databases data structure

        """
        LOGGER.debug('Processing dict of mongo databases')
        client = self.connect()
        if not client:
            return
        db_names = databases.keys()
        for database in db_names:
            db = client[database]
            try:
                if 'username' in databases[database]:
                    db.authenticate(databases[database]['username'],
                                    databases[database].get('password'))
                self.add_datapoints(database, db.command('dbStats'))
                if 'username' in databases[database]:
                    db.logout()
            except errors.OperationFailure as error:
                LOGGER.critical('Could not fetch stats: %s', error)

    def get_and_add_server_stats(self):
        LOGGER.debug('Fetching server stats')
        client = self.connect()
        if not client:
            return
        if self.config.get('admin_username'):
            client.admin.authenticate(self.config['admin_username'],
                                   self.config.get('admin_password'))
        self.add_server_datapoints(client.db.command('serverStatus'))
        client.close()

    def poll(self):
        self.initialize()
        self.get_and_add_server_stats()
        self.get_and_add_db_stats()
        self.finish()

########NEW FILE########
__FILENAME__ = nginx
"""
Nginx Support

"""
import logging
import re

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

PATTERN = re.compile(r'^Active connections: (?P<connections>\d+)\s+[\w ]+\n'
                     r'\s+(?P<accepts>\d+)'
                     r'\s+(?P<handled>\d+)'
                     r'\s+(?P<requests>\d+)'
                     r'(\s+(?P<time>\d+)|)'
                     r'\s+Reading:\s+(?P<reading>\d+)'
                     r'\s+Writing:\s+(?P<writing>\d+)'
                     r'\s+Waiting:\s+(?P<waiting>\d+)')


class Nginx(base.HTTPStatsPlugin):

    DEFAULT_PATH = 'nginx_stub_status'
    GUID = 'com.meetme.newrelic_nginx_agent'

    GAUGES = ['connections', 'reading', 'writing', 'waiting']
    KEYS = {'connections': 'Totals/Connections',
            'requests': 'Totals/Requests',
            'accepts': 'Requests/Accepted',
            'handled': 'Requests/Handled',
            'time': 'Requests/Duration',
            'reading': 'Connections/Reading',
            'writing': 'Connections/Writing',
            'waiting': 'Connections/Waiting'}

    TYPES = {'connections': 'connections',
             'accepts': 'requests',
             'handled': 'requests',
             'requests': 'requests',
             'reading': 'connections',
             'time': 'seconds',
             'writing': 'connections',
             'waiting': 'connections'}

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param str stats: The stub stats content

        """
        if not stats:
            return
        matches = PATTERN.match(stats)
        if matches:
            for key in self.KEYS.keys():
                try:
                    value = int(matches.group(key) or 0)
                except (IndexError, ValueError):
                    value = 0
                if key in self.GAUGES:
                    self.add_gauge_value(self.KEYS[key],
                                         self.TYPES[key],
                                         value)
                else:
                    self.add_derive_value(self.KEYS[key],
                                          self.TYPES[key],
                                          value)
        else:
            LOGGER.debug('Stats output: %r', stats)

########NEW FILE########
__FILENAME__ = pgbouncer
"""
pgBouncer Plugin Support

"""
import logging

from newrelic_plugin_agent.plugins import postgresql

LOGGER = logging.getLogger(__name__)


class PgBouncer(postgresql.PostgreSQL):

    GUID = 'com.meetme.newrelic_pgbouncer_agent'
    MULTIROW = ['POOLS', 'STATS']

    def add_pgbouncer_stats(self, stats):

        self.add_gauge_value('Overview/Databases', 'databases',
                             stats['LISTS']['databases'])
        self.add_gauge_value('Overview/Pools', 'pools',
                             stats['LISTS']['pools'])
        self.add_gauge_value('Overview/Users', 'users',
                             stats['LISTS']['users'])

        self.add_gauge_value('Overview/Clients/Free', 'clients',
                             stats['LISTS']['free_clients'])
        self.add_gauge_value('Overview/Clients/Used', 'clients',
                             stats['LISTS']['used_clients'])
        self.add_gauge_value('Overview/Servers/Free', 'servers',
                             stats['LISTS']['free_servers'])
        self.add_gauge_value('Overview/Servers/Used', 'servers',
                             stats['LISTS']['used_servers'])

        requests = 0
        for database in stats['STATS']:
            metric = 'Database/%s' % database['database']
            self.add_derive_value('%s/Query Time' % metric, 'seconds',
                                  database['total_query_time'])
            self.add_derive_value('%s/Requests' % metric, 'requests',
                                  database['total_requests'])
            self.add_derive_value('%s/Data Sent' % metric, 'bytes',
                                  database['total_sent'])
            self.add_derive_value('%s/Data Received' % metric, 'bytes',
                                  database['total_received'])
            requests += database['total_requests']

        self.add_derive_value('Overview/Requests', 'requests', requests)

        for pool in stats['POOLS']:
            metric = 'Pools/%s' % pool['database']
            self.add_gauge_value('%s/Clients/Active' % metric, 'clients',
                                 pool['cl_active'])
            self.add_gauge_value('%s/Clients/Waiting' % metric, 'clients',
                                 pool['cl_waiting'])
            self.add_gauge_value('%s/Servers/Active' % metric, 'servers',
                                 pool['sv_active'])
            self.add_gauge_value('%s/Servers/Idle' % metric, 'servers',
                                 pool['sv_idle'])
            self.add_gauge_value('%s/Servers/Login' % metric, 'servers',
                                 pool['sv_login'])
            self.add_gauge_value('%s/Servers/Tested' % metric, 'servers',
                                 pool['sv_tested'])
            self.add_gauge_value('%s/Servers/Used' % metric, 'servers',
                                 pool['sv_used'])
            self.add_gauge_value('%s/Maximum Wait' % metric, 'seconds',
                                 pool['maxwait'])

    def add_stats(self, cursor):
        stats = dict()
        for key in self.MULTIROW:
            stats[key] = dict()
            cursor.execute('SHOW %s' % key)
            temp = cursor.fetchall()
            stats[key] = list()
            for row in temp:
                stats[key].append(dict(row))

        cursor.execute('SHOW LISTS')
        temp = cursor.fetchall()
        stats['LISTS'] = dict()
        for row in temp:
            stats['LISTS'][row['list']] = row['items']

        self.add_pgbouncer_stats(stats)

    @property
    def dsn(self):
        """Create a DSN to connect to

        :return str: The DSN to connect

        """
        dsn = "host='%(host)s' port=%(port)i dbname='pgbouncer' " \
              "user='%(user)s'" % self.config
        if self.config.get('password'):
            dsn += " password='%s'" % self.config['password']
        return dsn

########NEW FILE########
__FILENAME__ = php_apc
"""
PHP APC Support

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class APC(base.JSONStatsPlugin):

    GUID = 'com.meetme.newrelic_php_apc_agent'

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: The stats content from APC as a string

        """
        # APC Shared Memory Stats
        shared_memory = stats.get('shared_memory', dict())
        self.add_gauge_value('Shared Memory/Available', 'bytes',
                             shared_memory.get('avail_mem', 0))
        self.add_gauge_value('Shared Memory/Segment Size', 'bytes',
                             shared_memory.get('seg_size', 0))
        self.add_gauge_value('Shared Memory/Segment Count', 'segments',
                             shared_memory.get('nseg',
                                               shared_memory.get('num_seg',
                                                                 0)))

        # APC System Stats
        system_stats = stats.get('system_stats', dict())
        self.add_gauge_value('System Cache/Slots', 'slots',
                             system_stats.get('nslots',
                                              system_stats.get('num_slots',
                                                               0)))
        self.add_gauge_value('System Cache/Entries', 'files',
                             system_stats.get('nentries',
                                              system_stats.get('num_entries',
                                                               0)))
        self.add_gauge_value('System Cache/Size', 'bytes',
                             system_stats.get('mem_size', 0))
        self.add_gauge_value('System Cache/Expunges', 'files',
                             system_stats.get('nexpunges',
                                              system_stats.get('num_expunges',
                                                               0)))

        hits = system_stats.get('nhits', system_stats.get('num_hits', 0))
        misses = system_stats.get('nmisses', system_stats.get('num_misses', 0))
        total = hits + misses
        if total > 0:
            effectiveness = float(float(hits) / float(total)) * 100
        else:
            effectiveness = 0
        self.add_gauge_value('System Cache/Effectiveness', 'percent',
                             effectiveness)

        self.add_derive_value('System Cache/Hits', 'files', hits)
        self.add_derive_value('System Cache/Misses', 'files', misses)
        self.add_derive_value('System Cache/Inserts', 'files',
                              system_stats.get('ninserts',
                                               system_stats.get('num_inserts',
                                                                0)))

        # APC User Stats
        user_stats = stats.get('user_stats', dict())
        self.add_gauge_value('User Cache/Slots', 'slots',
                             user_stats.get('nslots',
                                            user_stats.get('num_slots', 0)))
        self.add_gauge_value('User Cache/Entries', 'keys',
                             user_stats.get('nentries',
                                            user_stats.get('num_entries', 0)))
        self.add_gauge_value('User Cache/Size', 'bytes',
                             user_stats.get('mem_size', 0))
        self.add_gauge_value('User Cache/Expunges', 'keys',
                             user_stats.get('nexpunges',
                                            user_stats.get('num_expunges', 0)))

        hits = user_stats.get('nhits', user_stats.get('num_hits', 0))
        misses = user_stats.get('nmisses', user_stats.get('num_misses', 0))
        total = hits + misses
        if total > 0:
            effectiveness = float(float(hits) / float(total)) * 100
        else:
            effectiveness = 0
        self.add_gauge_value('User Cache/Effectiveness', 'percent',
                             effectiveness)

        self.add_derive_value('User Cache/Hits', 'keys', hits)
        self.add_derive_value('User Cache/Misses', 'keys', misses)
        self.add_derive_value('User Cache/Inserts', 'keys',
                              user_stats.get('ninserts',
                                             user_stats.get('num_inserts',0)))

########NEW FILE########
__FILENAME__ = php_fpm
"""
PHP FPM Support

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class FPM(base.JSONStatsPlugin):

    GUID = 'com.meetme.newrelic_php_fpm_agent'

    def add_datapoints(self, stats):
        """Add all of the data points for a fpm-pool

        :param dict stats: Stats from php-fpm for a pool

        """
        self.add_derive_value('Connections/Accepted', 'connections',
                              stats.get('accepted conn', 0))

        self.add_gauge_value('Connections/Pending', 'connections',
                             stats.get('listen queue', 0),
                             max_val=stats.get('max listen queue', 0))

        self.add_gauge_value('Socket Queue', 'connections',
                             stats.get('listen queue len', 0))

        self.add_gauge_value('Processes/Active', 'processes',
                             stats.get('active processes', 0),
                             max_val=stats.get('max processes', 0))

        self.add_gauge_value('Processes/Idle', 'processes',
                             stats.get('idle processes', 0))

        self.add_derive_value('Process Limit Reached', 'processes',
                              stats.get('max children reached', 0))

        self.add_derive_value('Slow Requests', 'requests',
                              stats.get('slow requests', 0))

########NEW FILE########
__FILENAME__ = postgresql
"""
PostgreSQL Plugin

"""
import logging
import psycopg2
from psycopg2 import extensions
from psycopg2 import extras

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)

ARCHIVE = """SELECT CAST(COUNT(*) AS INT) AS file_count,
CAST(COALESCE(SUM(CAST(archive_file ~ $r$\.ready$$r$ as INT)), 0) AS INT)
AS ready_count,CAST(COALESCE(SUM(CAST(archive_file ~ $r$\.done$$r$ AS INT)),
0) AS INT) AS done_count FROM pg_catalog.pg_ls_dir('pg_xlog/archive_status')
AS archive_files (archive_file);"""
BACKENDS = """SELECT count(*) - ( SELECT count(*) FROM pg_stat_activity WHERE
current_query = '<IDLE>' ) AS backends_active, ( SELECT count(*) FROM
pg_stat_activity WHERE current_query = '<IDLE>' ) AS backends_idle
FROM pg_stat_activity;"""
BACKENDS_9_2 = """SELECT count(*) - ( SELECT count(*) FROM pg_stat_activity WHERE
state = 'idle' ) AS backends_active, ( SELECT count(*) FROM
pg_stat_activity WHERE state = 'idle' ) AS backends_idle
FROM pg_stat_activity;"""
TABLE_SIZE_ON_DISK = """SELECT ((sum(relpages)* 8) * 1024) AS
size_relations FROM pg_class WHERE relkind IN ('r', 't');"""
TABLE_COUNT = """SELECT count(1) as relations FROM pg_class WHERE
relkind IN ('r', 't');"""
INDEX_SIZE_ON_DISK = """SELECT ((sum(relpages)* 8) * 1024) AS
size_indexes FROM pg_class WHERE relkind = 'i';"""
INDEX_COUNT = """SELECT count(1) as indexes FROM pg_class WHERE
relkind = 'i';"""
TRANSACTIONS = """SELECT sum(xact_commit) AS transactions_committed,
sum(xact_rollback) AS transactions_rollback, sum(blks_read) AS blocks_read,
sum(blks_hit) AS blocks_hit, sum(tup_returned) AS tuples_returned,
sum(tup_fetched) AS tuples_fetched, sum(tup_inserted) AS tuples_inserted,
sum(tup_updated) AS tuples_updated, sum(tup_deleted) AS tuples_deleted
FROM pg_stat_database;"""
STATIO = """SELECT sum(heap_blks_read) AS heap_blocks_read, sum(heap_blks_hit)
AS heap_blocks_hit, sum(idx_blks_read) AS index_blocks_read, sum(idx_blks_hit)
AS index_blocks_hit, sum(toast_blks_read) AS toast_blocks_read,
sum(toast_blks_hit) AS toast_blocks_hit, sum(tidx_blks_read)
AS toastindex_blocks_read, sum(tidx_blks_hit) AS toastindex_blocks_hit
FROM pg_statio_all_tables WHERE schemaname <> 'pg_catalog';"""
BGWRITER = 'SELECT * FROM pg_stat_bgwriter;'
DATABASE = 'SELECT * FROM pg_stat_database;'
LOCKS = 'SELECT mode, count(mode) AS count FROM pg_locks ' \
        'GROUP BY mode ORDER BY mode;'

LOCK_MAP = {'AccessExclusiveLock': 'Locks/Access Exclusive',
            'AccessShareLock': 'Locks/Access Share',
            'ExclusiveLock': 'Locks/Exclusive',
            'RowExclusiveLock': 'Locks/Row Exclusive',
            'RowShareLock': 'Locks/Row Share',
            'ShareUpdateExclusiveLock': 'Locks/Update Exclusive Lock',
            'ShareLock': 'Locks/Share',
            'ShareRowExclusiveLock': 'Locks/Share Row Exclusive'}


class PostgreSQL(base.Plugin):

    GUID = 'com.meetme.newrelic_postgresql_agent'

    def add_stats(self, cursor):
        self.add_backend_stats(cursor)
        self.add_bgwriter_stats(cursor)
        self.add_database_stats(cursor)
        self.add_lock_stats(cursor)
        if self.config.get('relation_stats', True):
            self.add_index_stats(cursor)
            self.add_statio_stats(cursor)
            self.add_table_stats(cursor)
        self.add_transaction_stats(cursor)

        # add_wal_metrics needs superuser to get directory listings
        if self.config.get('superuser', True):
            self.add_wal_stats(cursor)

    def add_database_stats(self, cursor):
        cursor.execute(DATABASE)
        temp = cursor.fetchall()
        for row in temp:
            database = row['datname']
            self.add_gauge_value('Database/%s/Backends' % database, 'processes',
                                 row.get('numbackends', 0))
            self.add_derive_value('Database/%s/Transactions/Committed' %
                                  database, 'transactions',
                                  int(row.get('xact_commit', 0)))
            self.add_derive_value('Database/%s/Transactions/Rolled Back' %
                                  database, 'transactions',
                                  int(row.get('xact_rollback', 0)))
            self.add_derive_value('Database/%s/Tuples/Read from Disk' %
                                  database, 'tuples',
                                  int(row.get('blks_read', 0)))
            self.add_derive_value('Database/%s/Tuples/Read cache hit' %
                                  database, 'tuples',
                                  int(row.get('blks_hit', 0)))
            self.add_derive_value('Database/%s/Tuples/Returned/From Sequential '
                                  'Scan' % database, 'tuples',
                                  int(row.get('tup_returned', 0)))
            self.add_derive_value('Database/%s/Tuples/Returned/From Bitmap '
                                  'Scan' % database, 'tuples',
                                  int(row.get('tup_fetched', 0)))
            self.add_derive_value('Database/%s/Tuples/Writes/Inserts' %
                                  database, 'tuples',
                                  int(row.get('tup_inserted', 0)))
            self.add_derive_value('Database/%s/Tuples/Writes/Updates' %
                                  database, 'tuples',
                                  int(row.get('tup_updated', 0)))
            self.add_derive_value('Database/%s/Tuples/Writes/Deletes' %
                                  database, 'tuples',
                                  int(row.get('tup_deleted', 0)))
            self.add_derive_value('Database/%s/Conflicts' %
                                  database, 'tuples',
                                  int(row.get('conflicts', 0)))

    def add_backend_stats(self, cursor):
        if self.server_version < (9, 2, 0):
            cursor.execute(BACKENDS)
        else:
            cursor.execute(BACKENDS_9_2)
        temp = cursor.fetchone()
        self.add_gauge_value('Backends/Active', 'processes',
                             temp.get('backends_active', 0))
        self.add_gauge_value('Backends/Idle', 'processes',
                             temp.get('backends_idle', 0))

    def add_bgwriter_stats(self, cursor):
        cursor.execute(BGWRITER)
        temp = cursor.fetchone()
        self.add_derive_value('Background Writer/Checkpoints/Scheduled',
                              'checkpoints',
                              temp.get('checkpoints_timed', 0))
        self.add_derive_value('Background Writer/Checkpoints/Requested',
                              'checkpoints',
                              temp.get('checkpoints_requests', 0))

    def add_index_stats(self, cursor):
        cursor.execute(INDEX_COUNT)
        temp = cursor.fetchone()
        self.add_gauge_value('Objects/Indexes', 'indexes',
                             temp.get('indexes', 0))
        cursor.execute(INDEX_SIZE_ON_DISK)
        temp = cursor.fetchone()
        self.add_gauge_value('Disk Utilization/Indexes', 'bytes',
                             temp.get('size_indexes', 0))

    def add_lock_stats(self, cursor):
        cursor.execute(LOCKS)
        temp = cursor.fetchall()
        for lock in LOCK_MAP:
            found = False
            for row in temp:
                if row['mode'] == lock:
                    found = True
                    self.add_gauge_value(LOCK_MAP[lock], 'locks',
                                         int(row['count']))
            if not found:
                    self.add_gauge_value(LOCK_MAP[lock], 'locks', 0)

    def add_statio_stats(self, cursor):
        cursor.execute(STATIO)
        temp = cursor.fetchone()
        self.add_derive_value('IO Operations/Heap/Reads', 'iops',
                              int(temp.get('heap_blocks_read', 0)))
        self.add_derive_value('IO Operations/Heap/Hits', 'iops',
                              int(temp.get('heap_blocks_hit', 0)))
        self.add_derive_value('IO Operations/Index/Reads', 'iops',
                              int(temp.get('index_blocks_read', 0)))
        self.add_derive_value('IO Operations/Index/Hits', 'iops',
                              int(temp.get('index_blocks_hit', 0)))
        self.add_derive_value('IO Operations/Toast/Reads', 'iops',
                              int(temp.get('toast_blocks_read', 0)))
        self.add_derive_value('IO Operations/Toast/Hits', 'iops',
                              int(temp.get('toast_blocks_hit', 0)))
        self.add_derive_value('IO Operations/Toast Index/Reads', 'iops',
                              int(temp.get('toastindex_blocks_read', 0)))
        self.add_derive_value('IO Operations/Toast Index/Hits', 'iops',
                              int(temp.get('toastindex_blocks_hit', 0)))

    def add_table_stats(self, cursor):
        cursor.execute(TABLE_COUNT)
        temp = cursor.fetchone()
        self.add_gauge_value('Objects/Tables', 'tables',
                             temp.get('relations', 0))
        cursor.execute(TABLE_SIZE_ON_DISK)
        temp = cursor.fetchone()
        self.add_gauge_value('Disk Utilization/Tables', 'bytes',
                             temp.get('size_relations', 0))

    def add_transaction_stats(self, cursor):
        cursor.execute(TRANSACTIONS)
        temp = cursor.fetchone()
        self.add_derive_value('Transactions/Committed', 'transactions',
                              int(temp.get('transactions_committed', 0)))
        self.add_derive_value('Transactions/Rolled Back', 'transactions',
                              int(temp.get('transactions_rollback', 0)))

        self.add_derive_value('Tuples/Read from Disk', 'tuples',
                              int(temp.get('blocks_read', 0)))
        self.add_derive_value('Tuples/Read cache hit', 'tuples',
                              int(temp.get('blocks_hit', 0)))

        self.add_derive_value('Tuples/Returned/From Sequential Scan',
                              'tuples',
                              int(temp.get('tuples_returned', 0)))
        self.add_derive_value('Tuples/Returned/From Bitmap Scan',
                              'tuples',
                              int(temp.get('tuples_fetched', 0)))

        self.add_derive_value('Tuples/Writes/Inserts', 'tuples',
                              int(temp.get('tuples_inserted', 0)))
        self.add_derive_value('Tuples/Writes/Updates', 'tuples',
                              int(temp.get('tuples_updated', 0)))
        self.add_derive_value('Tuples/Writes/Deletes', 'tuples',
                              int(temp.get('tuples_deleted', 0)))

    def add_wal_stats(self, cursor):
        cursor.execute(ARCHIVE)
        temp = cursor.fetchone()
        self.add_derive_value('Archive Status/Total', 'files',
                              temp.get('file_count', 0))
        self.add_gauge_value('Archive Status/Ready', 'files',
                             temp.get('ready_count', 0))
        self.add_derive_value('Archive Status/Done', 'files',
                              temp.get('done_count', 0))


    def connect(self):
        """Connect to PostgreSQL, returning the connection object.

        :rtype: psycopg2.connection

        """
        conn = psycopg2.connect(**self.connection_arguments)
        conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        return conn

    @property
    def connection_arguments(self):
        """Create connection parameter dictionary for psycopg2.connect

        :return dict: The dictionary to be passed to psycopg2.connect
            via double-splat
        """
        filtered_args = ["name", "superuser", "relation_stats"]
        args = {}
        for key in set(self.config) - set(filtered_args):
            if key == 'dbname':
                args['database'] = self.config[key]
            else:
                args[key] = self.config[key]
        return args

    def poll(self):
        self.initialize()
        try:
            self.connection = self.connect()
        except psycopg2.OperationalError as error:
            LOGGER.critical('Could not connect to %s, skipping stats run: %s',
                            self.__class__.__name__, error)
            return
        cursor = self.connection.cursor(cursor_factory=extras.DictCursor)
        self.add_stats(cursor)
        cursor.close()
        self.connection.close()
        self.finish()

    @property
    def server_version(self):
        """Return connection server version in PEP 369 format

        :returns: tuple

        """
        return (self.connection.server_version % 1000000 / 10000,
                self.connection.server_version % 10000 / 100,
                self.connection.server_version % 100)

########NEW FILE########
__FILENAME__ = rabbitmq
"""
rabbitmq

"""
import logging
import requests
import time

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class RabbitMQ(base.Plugin):

    GUID = 'com.meetme.newrelic_rabbitmq_agent'

    DEFAULT_USER = 'guest'
    DEFAULT_PASSWORD = 'guest'
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 80
    DEFAULT_API_PATH = '/api'

    DUMMY_STATS = {'ack': 0,
                   'deliver': 0,
                   'deliver_no_ack': 0,
                   'get': 0,
                   'get_no_ack': 0,
                   'publish': 0,
                   'redeliver': 0}

    def add_node_datapoints(self, node_data, queue_data, channel_data):
        """Add all of the data points for a node

        :param list node_data: all of the nodes
        :param list queue_data: all of the queues
        :param list channel_data: all of the channels

        """
        channels = 0
        for node in node_data:
            name = node['name'].split('@')[-1]
            self.add_node_channel_datapoints(name, channel_data)
            self.add_node_message_datapoints(name, queue_data, channel_data)
            self.add_node_queue_datapoints(name, queue_data)

            count = 0
            for channel in channel_data:
                if channel['node'].split('@')[-1] == name:
                    count += 1
            channels += count

            base_name = 'Node/%s' % name
            self.add_gauge_value('%s/Channels/Open' % base_name,
                                 'channels', count)
            self.add_gauge_value('%s/Erlang Processes' % base_name, 'processes',
                                 node.get('proc_used', 0))
            self.add_gauge_value('%s/File Descriptors' % base_name, 'fds',
                                 node.get('fd_used', 0))
            self.add_gauge_value('%s/Memory' % base_name, 'bytes',
                                 node.get('mem_used', 0))
            self.add_gauge_value('%s/Sockets' % base_name, 'sockets',
                                 node.get('sockets_used', 0))

        # Summary stats
        self.add_gauge_value('Summary/Channels', 'channels', channels)
        self.add_gauge_value('Summary/Consumers', 'consumers', self.consumers)

    def add_node_channel_datapoints(self, node, channel_data):
        """Add datapoints for a node, creating summary values for top-level
        queue consumer counts and message counts.

        :param str node: The node name
        :param list channel_data: The full stack of queue metrics

        """
        channel_flow_blocked = 0
        for channel in channel_data:
            if channel['node'].split('@')[-1] == node:
                if channel.get('client_flow_blocked'):
                    channel_flow_blocked += 1

        self.add_gauge_value('Node/%s/Channels/Blocked' % node, 'channels',
                             channel_flow_blocked)

    def add_node_message_datapoints(self, node, queue_data, channel_data):
        """Add message stats for the node

        :param str node: The node name
        :param list queue_data: all of the queues
        :param list channel_data: all of the channels

        """
        base_name = 'Node/%s/Messages' % node

        # Top level message stats
        keys = self.DUMMY_STATS.keys()
        count, total, min_val, max_val, values = self.initialize_counters(keys)

        for channel in channel_data:
            if channel['node'].split('@')[-1] == node:
                for key in keys:
                    total[key] += channel.get(key, 0)

        # Per-Channel message Rates
        count, total, min_val, max_val, values = self.initialize_counters(keys)
        message_stats = list()
        for channel in channel_data:
            if channel['node'].split('@')[-1] == node:
                stats = channel.get('message_stats')
                if stats:
                    message_stats.append(stats)

        for stat_block in message_stats:
            for key in keys:
                total[key] += stat_block.get(key, 0)

        for key in keys:
            name = key
            if key == 'ack':
                name = 'Acknowledged'
            elif key == 'deliver':
                name = 'Delivered'
            elif key == 'deliver_get':
                name = 'Delivered (Total)'
            elif key == 'deliver_no_ack':
                name = 'Delivered No-Ack'
            elif key == 'get':
                name = 'Got'
            elif key == 'get_no_ack':
                name = 'Got No-Ack'
            elif key == 'publish':
                name = 'Published'
            elif key == 'redeliver':
                name = 'Redelivered'
            self.add_derive_value('%s/%s' % (base_name, name),
                                  'messages',
                                  total[key])

        keys = ['messages_ready', 'messages_unacknowledged']
        count, total, min_val, max_val, values = self.initialize_counters(keys)
        for queue in queue_data:
            if queue['node'].split('@')[-1] == node:
                for key in keys:
                    total[key] += queue.get(key, 0)

        self.add_gauge_value('%s Available' % base_name, 'messages',
                             total['messages_ready'])
        self.add_gauge_value('%s Unacknowledged' % base_name,
                             'messages',
                             total['messages_unacknowledged'])

    def add_node_queue_datapoints(self, node, queue_data):
        """Add datapoints for a node, creating summary values for top-level
        queue consumer counts and message counts.

        :param str node: The node name
        :param list queue_data: The full stack of queue metrics

        """
        keys = ['consumers', 'active_consumers', 'idle_consumers']
        count, total, min_val, max_val, values = self.initialize_counters(keys)
        del keys[2]
        for queue in queue_data:
            if queue['node'].split('@')[-1] == node:
                for key in keys:
                    count[key] += 1
                    value = queue.get(key, 0)
                    total[key] += value
                    values[key].append(value)

                # Inventing a new key here, so it's a manual override
                key = 'idle_consumers'
                count[key] += count['consumers']
                idle_count = total['consumers'] - total['active_consumers']
                total[key] += idle_count
                values[key].append(idle_count)

        base_name = 'Node/%s/Consumers' % node
        self.add_gauge_value('%s/Count' % base_name, 'consumers',
                             total['consumers'],
                             None,
                             None,
                             count['consumers'])

        self.consumers += total['consumers']

        self.add_gauge_value('%s/Active' % base_name, 'consumers',
                             total['active_consumers'],
                             None,
                             None,
                             count['active_consumers'])

        base_name = 'Node/%s/Consumers' % node
        self.add_gauge_value('%s/Idle' % base_name, 'consumers',
                             total['idle_consumers'],
                             None,
                             None,
                             count['idle_consumers'])

    def track_vhost_queue(self, vhost_name, queue_name):
        """ Checks whether the data for a vhost queue should be tracked or not
        The check is based on the user configs, no configs means track everything
        :param str vhost_name: the virtual host name
        :param str queue_name: the queue name
        """
        TRACK_EVERYTHING = dict()
        tracked_vhosts = self.config.get('vhosts', TRACK_EVERYTHING)
        vhost_settings = tracked_vhosts.get(vhost_name) or {}
        vhost_queues = vhost_settings.get('queues', [])
        if tracked_vhosts is TRACK_EVERYTHING:
            return True
        if vhost_name in tracked_vhosts and vhost_queues == []:
            return True
        return queue_name in vhost_queues

    def add_queue_datapoints(self, queue_data):
        """Add per-queue datapoints to the processing stack.

        :param list queue_data: The raw queue data list

        """
        count = 0
        available, consumers, deliver, publish, redeliver, unacked = \
            0, 0, 0, 0, 0, 0
        for count, queue in enumerate(queue_data):
            if queue['name'][0:6] == 'amq.gen':
                LOGGER.debug('Skipping auto-named queue: %s', queue['name'])
                continue

            message_stats = queue.get('message_stats', dict())
            if not message_stats:
                message_stats = self.DUMMY_STATS

            vhost = 'Default' if queue['vhost'] == '/' else queue['vhost']
            base_name = 'Queue/%s/%s' % (vhost, queue['name'])

            if not self.track_vhost_queue(vhost, queue['name']):
                continue

            self.add_gauge_value('%s/Consumers' % base_name, 'consumers',
                                 queue.get('consumers', 0))

            base_name = 'Queue/%s/%s/Messages' % (vhost, queue['name'])
            self.add_derive_value('%s/Acknowledged' % base_name, 'messages',
                                  message_stats.get('ack', 0))
            self.add_derive_value('%s/Delivered (All)' % base_name, 'messages',
                                  message_stats.get('deliver_get', 0))
            self.add_derive_value('%s/Delivered' % base_name, 'messages',
                                  message_stats.get('deliver', 0))
            self.add_derive_value('%s/Delivered No-Ack' % base_name, 'messages',
                                  message_stats.get('deliver_no_ack', 0))
            self.add_derive_value('%s/Get' % base_name, 'messages',
                                  message_stats.get('get', 0))
            self.add_derive_value('%s/Get No-Ack' % base_name, 'messages',
                                  message_stats.get('get_no_ack', 0))
            self.add_derive_value('%s/Published' % base_name, 'messages',
                                  message_stats.get('publish', 0))
            self.add_derive_value('%s/Redelivered' % base_name, 'messages',
                                  message_stats.get('redeliver', 0))

            self.add_gauge_value('%s Available' % base_name, 'messages',
                                 queue.get('messages_ready', 0))
            self.add_gauge_value('%s Unacknowledged' % base_name, 'messages',
                                 queue.get('messages_unacknowledged', 0))

            available += queue.get('messages_ready', 0)
            deliver += message_stats.get('deliver_get', 0)
            publish += message_stats.get('publish', 0)
            redeliver += message_stats.get('redeliver', 0)
            unacked += queue.get('messages_unacknowledged', 0)

        # Summary stats
        self.add_derive_value('Summary/Messages/Delivered', 'messages',
                              deliver, count=count)
        self.add_derive_value('Summary/Messages/Published', 'messages',
                              publish, count=count)
        self.add_derive_value('Summary/Messages/Redelivered', 'messages',
                              redeliver, count=count)

        self.add_gauge_value('Summary/Messages Available', 'messages',
                             available, count=count)
        self.add_gauge_value('Summary/Messages Unacknowledged', 'messages',
                             unacked, count=count)

    def http_get(self, url, params=None):
        """Make a HTTP request for the URL.

        :param str url: The URL to request
        :param dict params: Get query string parameters

        """
        kwargs = {'url': url,
                  'auth': (self.config.get('username', self.DEFAULT_USER),
                           self.config.get('password', self.DEFAULT_PASSWORD)),
                  'verify': self.config.get('verify_ssl_cert', True)}
        if params:
            kwargs['params'] = params

        try:
            return self.requests_session.get(**kwargs)
        except requests.ConnectionError as error:
            LOGGER.error('Error fetching data from %s: %s', url, error)
            return None

    def fetch_data(self, data_type, columns=None):
        """Fetch the data from the RabbitMQ server for the specified data type

        :param str data_type: The type of data to query
        :param list columns: Ask for specific columns
        :rtype: list

        """
        url = '%s/%s' % (self.rabbitmq_base_url, data_type)
        params = {'columns': ','.join(columns)} if columns else {}
        response = self.http_get(url, params)
        if not response or response.status_code != 200:
            if response:
                LOGGER.error('Error response from %s (%s): %s', url,
                             response.status_code, response.content)
            return list()
        try:
            return response.json()
        except Exception as error:
            LOGGER.error('JSON decoding error: %r', error)
            return list()

    def fetch_channel_data(self):
        """Return the channel data from the RabbitMQ server

        :rtype: list

        """
        return self.fetch_data('channels')

    def fetch_node_data(self):
        """Return the node data from the RabbitMQ server

        :rtype: list

        """
        return self.fetch_data('nodes')

    def fetch_queue_data(self):
        """Return the queue data from the RabbitMQ server

        :rtype: list

        """
        return self.fetch_data('queues')

    def poll(self):
        """Poll the RabbitMQ server"""
        LOGGER.info('Polling RabbitMQ via %s', self.rabbitmq_base_url)
        start_time = time.time()

        self.requests_session = requests.Session()

        # Initialize the values each iteration
        self.derive = dict()
        self.gauge = dict()
        self.rate = dict()
        self.consumers = 0

        # Fetch the data from RabbitMQ
        channel_data = self.fetch_channel_data()
        node_data = self.fetch_node_data()
        queue_data = self.fetch_queue_data()

        # Create all of the metrics
        self.add_queue_datapoints(queue_data)
        self.add_node_datapoints(node_data, queue_data, channel_data)
        LOGGER.info('Polling complete in %.2f seconds',
                    time.time() - start_time)

    @property
    def rabbitmq_base_url(self):
        """Return the fully composed RabbitMQ base URL

        :rtype: str

        """
        port = self.config.get('port', self.DEFAULT_PORT)
        secure = self.config.get('secure', False)
        host = self.config.get('host', self.DEFAULT_HOST)
        api_path = self.config.get('api_path', self.DEFAULT_API_PATH)
        scheme = 'https' if secure else 'http'

        return '{scheme}://{host}:{port}{api_path}'.format(
            scheme=scheme, host=host, port=port, api_path=api_path)

########NEW FILE########
__FILENAME__ = redis
"""
Redis plugin polls Redis for stats

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class Redis(base.SocketStatsPlugin):

    GUID = 'com.meetme.newrelic_redis_agent'

    DEFAULT_PORT = 6379

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.add_gauge_value('Clients/Blocked', 'clients',
                             stats.get('blocked_clients', 0))
        self.add_gauge_value('Clients/Connected', 'clients',
                             stats.get('connected_clients', 0))
        self.add_gauge_value('Slaves/Connected', 'slaves',
                             stats.get('connected_slaves', 0))
        self.add_gauge_value('Last master IO sync (lag time)', 'seconds',
                             stats.get('master_last_io_seconds_ago', 0))

        # must happen before saving the new values
        # but only if we have the previous values
        if ('Keys/Hit' in self.derive_last_interval.keys() and
                'Keys/Missed' in self.derive_last_interval.keys()):
            prev_hits = self.derive_last_interval['Keys/Hit']
            prev_misses = self.derive_last_interval['Keys/Missed']

            # hits and misses since the last measure
            hits = stats.get('keyspace_hits', 0) - prev_hits
            misses = stats.get('keyspace_misses', 0) - prev_misses

            # total queries since the last measure
            total = hits + misses

            if total > 0:
                self.add_gauge_value('Hits Ratio', 'ratio', 100 * hits / total)

        self.add_derive_value('Evictions', 'keys',
                              stats.get('evicted_keys', 0))
        self.add_derive_value('Expirations', 'keys',
                              stats.get('expired_keys', 0))
        self.add_derive_value('Keys Hit', 'keys',
                              stats.get('keyspace_hits', 0))
        self.add_derive_value('Keys Missed', 'keys',
                              stats.get('keyspace_misses', 0))

        self.add_derive_value('Commands Processed', 'commands',
                              stats.get('total_commands_processed', 0))
        self.add_derive_value('Connections', 'connections',
                              stats.get('total_connections_received', 0))
        self.add_derive_value('Changes Since Last Save', 'changes',
                              stats.get('rdb_changes_since_last_save', 0))
        self.add_derive_value('Last Save Time', 'seconds',
                              stats.get('rdb_last_bgsave_time_sec', 0))

        self.add_gauge_value('Pubsub/Commands', 'commands',
                             stats.get('pubsub_commands', 0))
        self.add_gauge_value('Pubsub/Patterns', 'patterns',
                             stats.get('pubsub_patterns', 0))

        self.add_derive_value('CPU/User/Self', 'seconds',
                              stats.get('used_cpu_user', 0))
        self.add_derive_value('CPU/System/Self', 'seconds',
                              stats.get('used_cpu_sys', 0))

        self.add_derive_value('CPU/User/Children', 'seconds',
                              stats.get('used_cpu_user_childrens', 0))

        self.add_derive_value('CPU/System/Children', 'seconds',
                              stats.get('used_cpu_sys_childrens', 0))

        self.add_gauge_value('Memory Use', 'bytes',
                             stats.get('used_memory', 0),
                             max_val=stats.get('used_memory_peak', 0 ))
        self.add_gauge_value('Memory Fragmentation', 'ratio',
                             stats.get('mem_fragmentation_ratio', 0))

        keys, expires = 0, 0
        for db in range(0, self.config.get('db_count', 16)):

            db_stats = stats.get('db%i' % db, dict())
            self.add_gauge_value('DB/%s/Expires' % db, 'keys',
                                db_stats.get('expires', 0))
            self.add_gauge_value('DB/%s/Keys' % db, 'keys',
                                 db_stats.get('keys', 0))
            keys += db_stats.get('keys', 0)
            expires += db_stats.get('expires', 0)

        self.add_gauge_value('Keys/Total', 'keys', keys)
        self.add_gauge_value('Keys/Will Expire', 'keys', expires)

    def connect(self):
        """Top level interface to create a socket and connect it to the
        redis daemon.

        :rtype: socket

        """
        connection = super(Redis, self).connect()
        if connection and self.config.get('password'):
            connection.send("*2\r\n$4\r\nAUTH\r\n$%i\r\n%s\r\n" %
                            (len(self.config['password']),
                             self.config['password']))
            buffer_value = connection.recv(self.SOCKET_RECV_MAX)
            if buffer_value == '+OK\r\n':
                return connection
            LOGGER.error('Authentication error: %s', buffer_value[4:].strip())
            return None
        return connection

    def fetch_data(self, connection):
        """Loop in and read in all the data until we have received it all.

        :param  socket connection: The connection
        :rtype: dict

        """
        connection.send("*0\r\ninfo\r\n")

        # Read in the first line $1437
        buffer_value = connection.recv(self.SOCKET_RECV_MAX)
        lines = buffer_value.split('\r\n')

        if lines[0][0] == '$':
            byte_size = int(lines[0][1:].strip())
        else:
            return None

        while len(buffer_value) < byte_size:
            buffer_value += connection.recv(self.SOCKET_RECV_MAX)

        lines = buffer_value.split('\r\n')
        values = dict()
        for line in lines:
            if ':' in line:
                key, value = line.strip().split(':')
                if key[:2] == 'db':
                    values[key] = dict()
                    subvalues = value.split(',')
                    for temp in subvalues:
                        subvalue = temp.split('=')
                        value = subvalue[-1]
                        try:
                            values[key][subvalue[0]] = int(value)
                        except ValueError:
                            try:
                                values[key][subvalue[0]] = float(value)
                            except ValueError:
                                values[key][subvalue[0]] = value
                    continue
                try:
                    values[key] = int(value)
                except ValueError:
                    try:
                        values[key] = float(value)
                    except ValueError:
                        values[key] = value
        return values

########NEW FILE########
__FILENAME__ = riak
"""
Riak Plugin

"""
import logging

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class Riak(base.JSONStatsPlugin):

    DEFAULT_PATH = '/stats'
    GUID = 'com.meetme.newrelic_riak_agent'

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.add_gauge_value('Delays/Convergence', 'us',
                             stats.get('converge_delay_total', 0),
                             min_val=stats.get('converge_delay_min', 0),
                             max_val=stats.get('converge_delay_max', 0))
        self.add_gauge_value('Delays/Rebalance', 'us',
                             stats.get('rebalance_delay_total', 0),
                             min_val=stats.get('rebalance_delay_min', 0),
                             max_val=stats.get('rebalance_delay_max', 0))

        self.add_gauge_value('FSM/Object Size/Mean', 'bytes',
                             stats.get('node_get_fsm_objsize_mean', 0))
        self.add_gauge_value('FSM/Object Size/Median', 'bytes',
                             stats.get('node_get_fsm_objsize_median', 0))
        self.add_gauge_value('FSM/Object Size/90th Percentile', 'bytes',
                             stats.get('node_get_fsm_objsize_90', 0))
        self.add_gauge_value('FSM/Object Size/95th Percentile', 'bytes',
                             stats.get('node_get_fsm_objsize_95', 0))
        self.add_gauge_value('FSM/Object Size/100th Percentile', 'bytes',
                             stats.get('node_get_fsm_objsize_100', 0))

        self.add_gauge_value('FSM/Siblings/Mean', 'siblings',
                             stats.get('node_get_fsm_siblings_mean', 0))
        self.add_gauge_value('FSM/Siblings/Mean', 'siblings',
                             stats.get('node_get_fsm_siblings_media', 0))
        self.add_gauge_value('FSM/Siblings/90th Percentile', 'siblings',
                             stats.get('node_get_fsm_siblings_90', 0))
        self.add_gauge_value('FSM/Siblings/95th Percentile', 'siblings',
                             stats.get('node_get_fsm_siblings_95', 0))
        self.add_gauge_value('FSM/Siblings/100th Percentile', 'siblings',
                             stats.get('node_get_fsm_siblings_100', 0))

        self.add_gauge_value('FSM/Time/Get/Mean', 'us',
                             stats.get('node_get_fsm_time_mean', 0))
        self.add_gauge_value('FSM/Time/Get/Median', 'us',
                             stats.get('node_get_fsm_time_media', 0))
        self.add_gauge_value('FSM/Time/Get/90th Percentile', 'us',
                             stats.get('node_get_fsm_time_90', 0))
        self.add_gauge_value('FSM/Time/Get/95th Percentile', 'us',
                             stats.get('node_get_fsm_time_95', 0))
        self.add_gauge_value('FSM/Time/Get/100th Percentile', 'us',
                             stats.get('node_get_fsm_time_100', 0))

        self.add_gauge_value('FSM/Time/Put/Mean', 'us',
                             stats.get('node_put_fsm_time_mean', 0))
        self.add_gauge_value('FSM/Time/Put/Median', 'us',
                             stats.get('node_put_fsm_time_media', 0))
        self.add_gauge_value('FSM/Time/Put/90th Percentile', 'us',
                             stats.get('node_put_fsm_time_90', 0))
        self.add_gauge_value('FSM/Time/Put/95th Percentile', 'us',
                             stats.get('node_put_fsm_time_95', 0))
        self.add_gauge_value('FSM/Time/Put/100th Percentile', 'us',
                             stats.get('node_put_fsm_time_100', 0))

        self.add_derive_value('Failures/Pre-commit', 'failures',
                              stats.get('precommit_fail', 0))
        self.add_derive_value('Failures/Post-commit', 'failures',
                              stats.get('postcommit_fail', 0))

        self.add_derive_value('Gossip/Ignored', 'gossip',
                              stats.get('ignored_gossip_total', 0))
        self.add_derive_value('Gossip/Received', 'gossip',
                              stats.get('gossip_received', 0))

        self.add_derive_value('Handoff Timeouts', '',
                              stats.get('handoff_timeouts', 0))

        self.add_gauge_value('Mappers/Executing', 'timeouts',
                             stats.get('executing_mappers', 0))

        self.add_gauge_value('Memory/Allocated', 'bytes',
                             stats.get('mem_allocated', 0))
        self.add_gauge_value('Memory/Total', 'bytes',
                             stats.get('mem_total', 0))
        self.add_gauge_value('Memory/Erlang/Atom/Allocated', 'bytes',
                             stats.get('memory_atom', 0))
        self.add_gauge_value('Memory/Erlang/Atom/Used', 'bytes',
                             stats.get('memory_atom_used', 0))
        self.add_gauge_value('Memory/Erlang/Binary', 'bytes',
                             stats.get('memory_binary', 0))
        self.add_gauge_value('Memory/Erlang/Code', 'bytes',
                             stats.get('memory_code', 0))
        self.add_gauge_value('Memory/Erlang/ETS', 'bytes',
                             stats.get('memory_ets', 0))
        self.add_gauge_value('Memory/Erlang/Processes/Allocated', 'bytes',
                             stats.get('memory_processes', 0))
        self.add_gauge_value('Memory/Erlang/Processes/Used', 'bytes',
                             stats.get('memory_processes_used', 0))
        self.add_gauge_value('Memory/Erlang/System', 'bytes',
                             stats.get('memory_system', 0))
        self.add_gauge_value('Memory/Erlang/Total', 'bytes',
                             stats.get('memory_total', 0))

        self.add_gauge_value('Nodes/Connected', 'nodes',
                             len(stats.get('connected_nodes', list())))

        self.add_gauge_value('Pipeline/Active', 'pipelines',
                             stats.get('pipeline_active', 0))
        self.add_derive_value('Pipeline/Created', 'pipelines',
                              stats.get('pipeline_create_count', 0))
        self.add_derive_value('Pipeline/Creation Errors', 'pipelines',
                              stats.get('pipeline_create_error_count', 0))

        self.add_gauge_value('Processes/OS', 'processes',
                             stats.get('cpu_nprocs', 0))

        self.add_gauge_value('Processes/Erlang', 'processes',
                             stats.get('cpu_nprocs', 0))

        self.add_gauge_value('Protocol Buffer Connections', 'active',
                             stats.get('pbc_active', 0))
        self.add_derive_value('Protocol Buffer Connections', 'total',
                              stats.get('pbc_connects_total', 0))

        self.add_derive_value('Read Repairs', 'reads',
                              stats.get('read_repairs_total', 0))

        self.add_derive_value('Requests/Gets', 'requests',
                              stats.get('node_gets_total', 0))
        self.add_derive_value('Requests/Puts', 'requests',
                              stats.get('node_puts_total', 0))
        self.add_derive_value('Requests/Redirected', 'requests',
                              stats.get('coord_redirs_total', 0))


        self.add_gauge_value('Ring/Members', 'members',
                             len(stats.get('ring_members', list())))
        self.add_gauge_value('Ring/Partitions', 'partitions',
                             stats.get('ring_num_partitions', 0))
        self.add_gauge_value('Ring/Size', 'members',
                             stats.get('ring_creation_size', 0))
        self.add_derive_value('Ring/Reconciled', 'members',
                              stats.get('rings_reconciled_total', 0))

        self.add_derive_value('VNodes/Gets', 'vnodes',
                              stats.get('vnode_gets_total', 0))
        self.add_derive_value('VNodes/Puts', 'vnodes',
                              stats.get('vnode_puts_total', 0))

        self.add_derive_value('VNodes/Index', 'deletes',
                              stats.get('vnode_index_deletes_total', 0))
        self.add_derive_value('VNodes/Index', 'delete-postings',
                              stats.get('vnode_index_deletes_postings_total',
                                        0))
        self.add_derive_value('VNodes/Index', 'reads',
                              stats.get('vnode_index_reads_total', 0))
        self.add_derive_value('VNodes/Index', 'writes',
                              stats.get('vnode_index_writes_total', 0))
        self.add_derive_value('VNodes/Index', 'postings',
                              stats.get('vnode_writes_postings_total', 0))

########NEW FILE########
__FILENAME__ = uwsgi
"""
uWSGI

"""
import json
import logging
import re

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)


class uWSGI(base.SocketStatsPlugin):

    GUID = 'com.meetme.newrelic_uwsgi_agent'

    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 1717

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        self.add_gauge_value('Listen Queue Size', 'connections',
                             stats.get('listen_queue', 0))
        self.add_gauge_value('Listen Queue Errors', 'errors',
                             stats.get('listen_queue_errors', 0))
        for lock in stats.get('locks', list()):
            lock_name = lock.keys()[0]
            self.add_gauge_value('Locks/%s' % lock_name, 'locks',
                                 lock[lock_name])

        exceptions = 0
        harakiris = 0
        requests = 0
        respawns = 0
        signals = 0

        apps = dict()

        for worker in stats.get('workers', list()):
            id = worker['id']

            # totals
            exceptions += worker.get('exceptions', 0)
            harakiris += worker.get('harakiri_count', 0)
            requests += worker.get('requests', 0)
            respawns += worker.get('respawn_count', 0)
            signals += worker.get('signals', 0)

            # Add the per worker
            self.add_derive_value('Worker/%s/Exceptions' % id, 'exceptions',
                                  worker.get('exceptions', 0))
            self.add_derive_value('Worker/%s/Harakiri' % id, 'harakiris',
                                  worker.get('harakiri_count', 0))
            self.add_derive_value('Worker/%s/Requests' % id, 'requests',
                                  worker.get('requests', 0))
            self.add_derive_value('Worker/%s/Respawns' % id, 'respawns',
                                  worker.get('respawn_count', 0))
            self.add_derive_value('Worker/%s/Signals' % id, 'signals',
                                  worker.get('signals', 0))

            for app in worker['apps']:
                if app['id'] not in apps:
                    apps[app['id']] = {'exceptions': 0,
                                       'requests': 0}
                apps[app['id']]['exceptions'] += app['exceptions']
                apps[app['id']]['requests'] += app['requests']

        for app in apps:
            self.add_derive_value('Application/%s/Exceptions' % app,
                                  'exceptions',
                                  apps[app].get('exceptions', 0))
            self.add_derive_value('Application/%s/Requests' % app, 'requests',
                                  apps[app].get('requests', 0))

        self.add_derive_value('Summary/Applications', 'applications', len(apps))
        self.add_derive_value('Summary/Exceptions', 'exceptions', exceptions)
        self.add_derive_value('Summary/Harakiris', 'harakiris', harakiris)
        self.add_derive_value('Summary/Requests', 'requests', requests)
        self.add_derive_value('Summary/Respawns', 'respawns', respawns)
        self.add_derive_value('Summary/Signals', 'signals', signals)
        self.add_derive_value('Summary/Workers', 'workers',
                              len(stats.get('workers', ())))

    def fetch_data(self, connection):
        """Read the data from the socket

        :param  socket connection: The connection
        :return: dict

        """
        data = super(uWSGI, self).fetch_data(connection, read_till_empty=True)
        if data:
            data = re.sub(r'"HTTP_COOKIE=[^"]*"', '""', data)
            return json.loads(data)
        return {}


########NEW FILE########
