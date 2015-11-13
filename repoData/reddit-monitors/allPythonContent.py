__FILENAME__ = alerts
#!/usr/bin/python

import ConfigParser
import logging
import logging.handlers
import os
import sys
import time
import socket

import wessex
from zenoss import Zenoss

__all__ = ["harold", "config", "zenoss"]

harold = None
graphite = None
zenoss = None
config = None

def init(config_path='production.ini'):
    global config, harold, zenoss
    config = load_config(path=config_path)
    if config.has_section('logging'):
        configure_logging(config)
    if config.has_section('graphite'):
        configure_graphite(config)
    if config.has_section('harold'):
        harold = get_harold(config)
    if config.has_section('zenoss'):
        zenoss = get_zenoss(config)

def load_config(path='production.ini'):
    config = ConfigParser.RawConfigParser()
    config.read([path])
    return config

def get_harold(config):
    harold_host = config.get('harold', 'host')
    harold_port = config.getint('harold', 'port')
    harold_secret = config.get('harold', 'secret')
    return wessex.Harold(
        host=harold_host, port=harold_port, secret=harold_secret)

def get_zenoss(config):
    host = config.get('zenoss', 'host')
    port = config.getint('zenoss', 'port')
    user = config.get('zenoss', 'user')
    password = config.get('zenoss', 'password')
    return Zenoss('http://%s:%s/' % (host, port), user, password)

class StreamLoggingFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        timestamp = time.strftime(datefmt)
        return timestamp % dict(ms=(1000 * record.created) % 1000)

def _get_logging_handler(config):
    mode = config.get('logging', 'mode')
    if mode == 'file':
        return logging.FileHandler(config.get('logging', 'file'))
    elif mode == 'stderr':
        return logging.StreamHandler()
    elif mode == 'syslog':
        return logging.handlers.SysLogHandler(
            config.get('logging', 'syslog_addr'))
    else:
        raise ValueError('unsupported logging mode: %r' % mode)

def _get_logging_formatter(config):
    mode = config.get('logging', 'mode')
    if mode == 'syslog':
        app_name = os.path.basename(sys.argv[0])
        return logging.Formatter(
            '%s: [%%(levelname)s] %%(message)s' % app_name)
    else:
        return StreamLoggingFormatter(
            '%(levelname).1s%(asctime)s: %(message)s',
            '%m%d %H:%M:%S.%%(ms)03d')

def _get_logging_level(config):
    if config.has_option('logging', 'level'):
        return config.get('logging', 'level')
    else:
        return logging.INFO

def configure_logging(config):
    ch = _get_logging_handler(config)
    ch.setFormatter(_get_logging_formatter(config))
    logger = logging.getLogger()
    logger.setLevel(_get_logging_level(config))
    logger.addHandler(ch)
    return logger

def _parse_addr(addr):
    host, port_str = addr.split(':', 1)
    return host, int(port_str)

class Graphite(object):
    """Send data to graphite in a fault-tolerant manner.

    Provides a single public method - send_values() - which adds to and
    flushes an internal queue of messages. Should delivery to graphite fail,
    messages are queued until the next invocation of send_values(). Up to
    MAX_QUEUE_SIZE messages are kept, after which the oldest are dropped. This
    class is not thread-safe.

    """
    MAX_QUEUE_SIZE = 1000

    def __init__(self, address):
        self.address = address
        self.send_queue = []

    def _send_message(self, msg):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.address)
        sock.send(msg + '\n')
        sock.close()

    def send_values(self, items):
        messages = []
        timestamp = str(time.time())
        for key, value in items.iteritems():
            messages.append(" ".join((key, str(value), timestamp)))
        self.send_queue.extend(messages)
        if self.send_queue:
            try:
                self._send_message("\n".join(self.send_queue))
                del self.send_queue[:]
            except socket.error as e:
                logging.warning(
                    "Error while flushing to graphite. Queue size: %d",
                    len(self.send_queue)
                )
            finally:
                if len(self.send_queue) > Graphite.MAX_QUEUE_SIZE:
                    logging.warning(
                        "Discarding %d messages",
                        len(self.send_queue) - Graphite.MAX_QUEUE_SIZE
                    )
                    self.send_queue = self.send_queue[-Graphite.MAX_QUEUE_SIZE:]


def configure_graphite(config):
    global graphite

    address_text = config.get('graphite', 'graphite_addr')
    address = _parse_addr(address_text)
    graphite = Graphite(address)

########NEW FILE########
__FILENAME__ = alerts_test
#!/usr/bin/env python

import ConfigParser
import logging
import tempfile
import unittest

import alerts

class ConfigureLoggingTest(unittest.TestCase):
    @staticmethod
    def _config(**data):
        config = ConfigParser.RawConfigParser()
        config.add_section('logging')
        for k, v in data.iteritems():
            config.set('logging', k, v)
        return config

    def test_get_logging_handler(self):
        def assertHandler(mode, expected_class):
            with tempfile.NamedTemporaryFile() as f:
                config = self._config(mode=mode, file=f.name,
                                      syslog_addr='/dev/log')
                self.assertTrue(
                    isinstance(
                        alerts._get_logging_handler(config), expected_class))

        assertHandler('file', logging.FileHandler)
        assertHandler('stderr', logging.StreamHandler)
        # we can count on the alerts module importing logging.handlers
        assertHandler('syslog', logging.handlers.SysLogHandler)

        self.assertRaises(ValueError, assertHandler, 'asdf', None)

    def test_get_logging_formatter(self):
        f = alerts._get_logging_formatter(self._config(mode='syslog'))
        self.assertFalse(isinstance(f, alerts.StreamLoggingFormatter))
        f = alerts._get_logging_formatter(self._config(mode='not-syslog'))
        self.assertTrue(isinstance(f, alerts.StreamLoggingFormatter))

    def test_get_logging_level(self):
        config = self._config()
        self.assertEquals(logging.INFO, alerts._get_logging_level(config))
        config = self._config(level='DEBUG')
        self.assertEquals('DEBUG', alerts._get_logging_level(config))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = cassandra
#!/usr/bin/python

import sys
import time
import urllib2
import urlparse
import platform
from paramiko import SSHClient, SSHException, AutoAddPolicy

import alerts


INTERVAL  = 10  # seconds
THRESHOLD = 3   # recent failures

# The command should be forced through authorized_keys, so this is just a reference
CASS_CMD  = "/usr/local/bin/ringstat -d"

class DownedNodeException(Exception):
    def __init__(self, node):
        self.node = node
    def __str__(self):
        return "%s is down in the ring" % self.node

class CassandraMonitor():
    def __init__(self, server):
        self.server = server
        self.recent_failures = 0
    def __str__(self):
        return "CassandraMonitor for %s with %i failures" % (self.server, self.recent_failures)
    def mark_error(self, tag, message):
        self.recent_failures += 1
        if self.recent_failures > THRESHOLD:
            alerts.harold.alert(tag, message)
            self.recent_failures = THRESHOLD
    def clear_error(self):
        self.recent_failures = max(self.recent_failures - 1, 0)
    def start_monitor(self):
        local_name = platform.node()
        print "Starting Cassandra Monitor for %s" % self.server
        while True:
            try:
                ssh = SSHClient()
                ssh.load_system_host_keys()
                ssh.set_missing_host_key_policy(AutoAddPolicy())
                ssh.connect(self.server, timeout=5, allow_agent=False)
                stdin, stdout, stderr = ssh.exec_command(CASS_CMD)
                stdin.close()
                for line in stdout:
                    # Any line that shows up will be a downed server
                    # server datacenter rack status state load owns token
                    downed_node = line.split()
                    raise DownedNodeException(downed_node[0])
                stdout.close()
                err = stderr.read()
                if err:
                    raise Exception("Unknown error: %s" % err)
                stderr.close()
                ssh.close()
            except DownedNodeException as e:
                self.mark_error(e.node, e)
            except SSHException as e:
                self.mark_error(self.server, "%s could not connect to %s: %s" % (local_name, self.server, e))
            except Exception as e:
                self.mark_error(local_name, "Unknown error: %s" % e)
            else:
                self.clear_error()
            time.sleep(INTERVAL)

if __name__ == "__main__":
    alerts.init()
    server = sys.argv[1]
    monitor = CassandraMonitor(server)
    monitor.start_monitor()

########NEW FILE########
__FILENAME__ = haproxy
#!/usr/bin/python

import csv
import urllib2
import urlparse
import collections
import time

import alerts


TIMEOUT = 6  # seconds
CONFIG_SECTION = "haproxy"


def fetch_queue_lengths_by_pool(haproxy_stats_urls):
    pools = collections.Counter()

    for url in haproxy_stats_urls:
        try:
            csv_data = urllib2.urlopen(url, timeout=TIMEOUT)
            reader = csv.reader(csv_data)

            reader.next()  # skip the header
            for row in reader:
                proxy_name, server_name, queue_length = row[:3]
                if server_name != "BACKEND":
                    continue
                pools[proxy_name] += int(queue_length)
        except urllib2.URLError as e:
            host = urlparse.urlparse(url).hostname
            alerts.harold.alert(host, "couldn't connect to haproxy: %s" % e)

    return pools


def watch_request_queues(haproxy_urls, threshold, check_interval):
    queued_pools = set()

    while True:
        # this *should* die if unable to talk to haproxy, then we'll
        # get heartbeat-failure alerts
        pools = fetch_queue_lengths_by_pool(haproxy_urls)

        # alert where necessary
        for pool, queue_length in pools.iteritems():
            if queue_length > threshold:
                if pool in queued_pools:
                    alerts.harold.alert("queuing-%s" % pool,
                                        "%s pool is queuing (%d)" %
                                        (pool, queue_length))
                queued_pools.add(pool)
            else:
                if pool in queued_pools:
                    queued_pools.remove(pool)

        # check in then sleep 'til we're needed again
        alerts.harold.heartbeat("monitor_haproxy", check_interval * 2)
        time.sleep(check_interval)


def main():
    # expects a config section like the following
    # [haproxy]
    # threshold = 200
    # interval = 30
    # url.* = url
    alerts.init()
    haproxy_urls = [value for key, value in
                    alerts.config.items(CONFIG_SECTION)
                    if key.startswith("url")]
    threshold = alerts.config.getint(CONFIG_SECTION, "threshold")
    interval = alerts.config.getint(CONFIG_SECTION, "interval")

    watch_request_queues(haproxy_urls, threshold, interval)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = queues
#!/usr/bin/env python

'''Provides a monitor that polls queue lengths using rabbitmqctl.

Run this as a script in the same directory as a production.ini file that looks
like this:

[harold]
host = localhost
port = 8888
secret = haroldsecret

[queues]
# check queue lengths with this frequency (seconds)
poll_interval = 1

# These two settings control alert noisiness. The grace period is how long a
# queue must show an overrun (in seconds) before an alert is raised. The rate
# limit is how long (in seconds) it must be since the last alert was raised
# before we'll raise another one (per queue).
alert_grace_period = 5
alert_rate_limit = 15

# tell harold we're alive at this frequency (seconds)
heartbeat_interval = 60

# multiply by heartbeat_interval to tell harold how long to wait before deciding
# we're "dead"
heartbeat_timeout_factor = 3

# send messages to graphite at this address
graphite_addr = localhost:2003

# poll queue lengths using the rabbitmq management API at this URL
rabbitmq_url = http://guest:guest@localhost:55672/api/queues

[queue_limits]
# list queue names with alerting thresholds for queue length here
# queues not mentioned here will still have stats recorded in graphite, but
# won't be alerted on

commentstree_q = 1000
newcomments_q = 200
vote_comment_q = 10000
vote_link_q = 10000
# etc.
'''

import json
import logging
import socket
import subprocess
import sys
import time
import urllib

import alerts

def parse_addr(addr):
    host, port_str = addr.split(':', 1)
    return host, int(port_str)

class QueueMonitor:
    '''Polls "rabbitmqctl list_queues" to report on queue lengths.

    @attr overruns: dict, maps queue name to timestamp of when current overrun
        status began
    @attr recent_alerts: dict, maps queue name to timestamp of most recent alert
    @attr last_heartbeat: float, timestamp of last heartbeat sent to harold
    '''
    def __init__(self):
        self.config = alerts.config
        self.harold = alerts.harold
        self.overruns = {}
        self.recent_alerts = {}
        self.last_heartbeat = 0
        self._load_from_config()

    def _load_from_config(self):
        config = self.config
        self.heartbeat_interval = config.getfloat(
            'queues', 'heartbeat_interval')
        self.heartbeat_timeout_factor = config.getfloat(
            'queues', 'heartbeat_timeout_factor')
        self.rabbitmq_url = config.get('queues', 'rabbitmq_url')
        self.graphite_host, self.graphite_port = parse_addr(
            config.get('queues', 'graphite_addr'))
        self.alert_grace_period = config.getfloat(
            'queues', 'alert_grace_period')
        self.alert_rate_limit = config.getfloat('queues', 'alert_rate_limit')
        self.poll_interval = config.getfloat('queues', 'poll_interval')

        if config.has_section('queue_limits'):
            self.queue_limits = dict((q, config.getint('queue_limits', q))
                                    for q in config.options('queue_limits'))
        else:
            self.queue_limits = {}

    def get_queue_lengths(self):
        f = urllib.urlopen(self.rabbitmq_url)
        data = json.loads(f.read())
        return dict((item['name'], item['messages']) for item in data)

    def send_heartbeat(self):
        self.last_heartbeat = time.time()
        interval = self.heartbeat_interval * self.heartbeat_timeout_factor
        # harold expects the interval to be given as an int
        self.harold.heartbeat('monitor_queues', int(interval))

    def send_graphite_message(self, msg):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.graphite_host, self.graphite_port))
        sock.send(msg + '\n')
        sock.close()

    def send_queue_stats(self, queue_lengths):
        stat_msgs = []
        now = time.time()
        for name, length in queue_lengths.iteritems():
            stat_msgs.append('stats.queue.%s.length %d %d'
                             % (name, length, now))
        if not stat_msgs:
            return
        self.send_graphite_message('\n'.join(stat_msgs))

    def send_queue_alert(self, queue_name, queue_length, alert_threshold):
        alert = dict(
            tag=queue_name,
            message='%s is too long (%d/%d)' % (
                queue_name, queue_length, alert_threshold)
        )
        logging.warn('ALERT on %(tag)s: %(message)s' % alert)
        self.harold.alert(**alert)

    def update_queue_status(self, queue_name, queue_length, alert_threshold):
        if queue_length <= alert_threshold:
            if queue_name in self.overruns:
                del self.overruns[queue_name]
            return False
        else:
            now = time.time()
            self.overruns.setdefault(queue_name, now)
            if (now - self.overruns[queue_name] >= self.alert_grace_period
                and self.recent_alerts.get(queue_name, 0)
                    + self.alert_rate_limit <= now):
                self.send_queue_alert(queue_name, queue_length, alert_threshold)
                self.recent_alerts[queue_name] = now
                return True
            else:
                logging.warn('suppressing continued alert on %s', queue_name)
                return False

    def check_queues(self):
        queue_lengths = self.get_queue_lengths()
        for name, length in queue_lengths.iteritems():
            self.update_queue_status(name, length,
                                     self.queue_limits.get(name, sys.maxint))
        self.send_queue_stats(queue_lengths)
        if time.time() - self.last_heartbeat >= self.heartbeat_interval:
            self.send_heartbeat()

    def poll(self):
        while True:
            logging.info('checking on queues')
            try:
                self.check_queues()
            except:
                logging.exception('exception raised in check_queues')
            time.sleep(self.poll_interval)

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
    )
    alerts.init()
    monitor = QueueMonitor()
    monitor.poll()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = queues_test
#!/usr/bin/env python

import json
import StringIO
import subprocess
import sys
import time
import unittest
import urllib

import alerts
import queues
import testing

class QueueMonitorTest(unittest.TestCase):
    HEARTBEAT_INTERVAL = 5
    HEARTBEAT_TIMEOUT_FACTOR = 2
    RABBITMQ_URL = 'http://localhost:55555'
    GRAPHITE_HOST = 'localhost'
    GRAPHITE_PORT = 22003
    ALERT_GRACE_PERIOD = 15
    ALERT_RATE_LIMIT = 60
    POLL_INTERVAL = 1

    def setUp(self):
        testing.init_alerts(
            queues=dict(
                heartbeat_interval=self.HEARTBEAT_INTERVAL,
                heartbeat_timeout_factor=self.HEARTBEAT_TIMEOUT_FACTOR,
                rabbitmq_url=self.RABBITMQ_URL,
                graphite_addr='%s:%d' % (
                    self.GRAPHITE_HOST, self.GRAPHITE_PORT),
                alert_grace_period=self.ALERT_GRACE_PERIOD,
                alert_rate_limit=self.ALERT_RATE_LIMIT,
                poll_interval=self.POLL_INTERVAL,
            ),
            queue_limits=dict(q1=1, q2=2),
        )
        self.monitor = queues.QueueMonitor()

    @testing.stub(urllib, 'urlopen')
    def test_get_queue_lengths(self):
        data = [
            {'name': 'A', 'messages': 1},
            {'name': 'B', 'messages': 2},
        ]
        urllib.urlopen = lambda u: StringIO.StringIO(json.dumps(data))
        self.assertEquals(dict(A=1, B=2), self.monitor.get_queue_lengths())

    @testing.stub(time, 'time')
    def test_send_queue_stats(self):
        sent_messages = set()
        time.time = lambda: 1000
        self.monitor.send_graphite_message = (
            lambda msg: sent_messages.update(msg.split('\n')))
        self.monitor.send_queue_stats(dict(a=1, b=2))
        expected_messages = set([
            'stats.queue.a.length 1 1000',
            'stats.queue.b.length 2 1000',
        ])
        self.assertEquals(expected_messages, sent_messages)

    def test_send_queue_alert(self):
        self.monitor.send_queue_alert('A', 2, 1)
        self.assertEquals(
            [(['alert'], dict(tag='A', message='A is too long (2/1)'))],
            alerts.harold.post_log)

    @testing.stub(time, 'time')
    def test_update_queue_status(self):
        now = 1000
        alerts = []
        time.time = lambda: now
        self.monitor.send_queue_alert = (
            lambda q, l, t: alerts.append((q, l, t)))

        # Non-alerting conditions.
        self.assertFalse(self.monitor.update_queue_status('A', 1, 2))
        self.assertFalse(self.monitor.update_queue_status('A', 1, 1))

        # Initial overrun condition for A should not fire alert.
        self.assertFalse(self.monitor.update_queue_status('A', 9, 1))
        now += self.ALERT_GRACE_PERIOD - 1
        self.assertFalse(self.monitor.update_queue_status('A', 9, 1))

        # If overrun condition outlives the grace period, alert should raise.
        now += 1
        self.assertTrue(self.monitor.update_queue_status('A', 2, 1))
        self.assertEquals(('A', 2, 1), alerts[-1])

        # Spammy alert should be suppressed but eventually refire.
        now += self.ALERT_RATE_LIMIT - 1
        self.assertFalse(self.monitor.update_queue_status('A', 9, 1))
        now += 1
        self.assertTrue(self.monitor.update_queue_status('A', 3, 1))
        self.assertEquals(('A', 3, 1), alerts[-1])

        # Non-overrun condition should reset grace period.
        now += self.ALERT_RATE_LIMIT
        self.assertFalse(self.monitor.update_queue_status('A', 1, 1))
        self.assertFalse(self.monitor.update_queue_status('A', 9, 1))
        now += self.ALERT_GRACE_PERIOD - 1
        self.assertFalse(self.monitor.update_queue_status('A', 9, 1))
        now += 1
        self.assertTrue(self.monitor.update_queue_status('A', 4, 1))
        self.assertEquals(('A', 4, 1), alerts[-1])

    @testing.stub(time, 'time')
    def test_check_queues(self):
        now = 1000
        expected_queue_lengths = dict(q1=1, q2=2, q3=3)

        time.time = lambda: now
        self.monitor.get_queue_lengths = lambda: expected_queue_lengths

        queue_statuses = {}
        def stub_update_queue_status(n, l, t):
            queue_statuses[n] = (l, t)
        self.monitor.update_queue_status = stub_update_queue_status

        queue_lengths = {}
        self.monitor.send_queue_stats = lambda ql: queue_lengths.update(ql)

        # First run should emit heartbeat.
        self.monitor.check_queues()
        self.assertEquals(expected_queue_lengths, queue_lengths)
        self.assertEquals(
            dict(q1=(1, 1), q2=(2, 2), q3=(3, sys.maxint)), queue_statuses)
        self.assertEquals(
            [(['heartbeat'],
              dict(tag='monitor_queues',
                   interval=self.HEARTBEAT_INTERVAL
                       * self.HEARTBEAT_TIMEOUT_FACTOR))],
            alerts.harold.post_log)
        self.assertTrue(
            isinstance(alerts.harold.post_log[0][1]['interval'], int))
        self.assertEquals(now, self.monitor.last_heartbeat)

        # Second run within heartbeat interval, no heartbeat emitted.
        last_heartbeat = now
        now += self.HEARTBEAT_INTERVAL - 1
        self.monitor.check_queues()
        self.assertEquals(last_heartbeat, self.monitor.last_heartbeat)

        # Third run when next heartbeat should be sent.
        now += 1
        self.monitor.check_queues()
        self.assertEquals(now, self.monitor.last_heartbeat)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = site_up
#!/usr/bin/python

import sys
import time
import urllib2
import urlparse
import platform
import socket

import alerts


INTERVAL = 10  # seconds
TIMEOUT = 30  # seconds
THRESHOLD = 3  # recent failures


def monitor_site(url):
    tag = urlparse.urlparse(url).hostname
    local_name = platform.node()

    recent_failures = 0
    while True:
        try:
            request = urllib2.Request(url)
            request.add_header("User-Agent", "site-up monitor by /u/spladug")
            urllib2.urlopen(request, timeout=TIMEOUT)
        except (urllib2.URLError, socket.timeout):
            recent_failures += 1

            if recent_failures > THRESHOLD:
                alerts.harold.alert(tag, "[%s] %s is down" % (local_name, tag))
                recent_failures = THRESHOLD
        else:
            recent_failures = max(recent_failures - 1, 0)

        time.sleep(INTERVAL)
        alerts.harold.heartbeat("monitor_%s_%s" % (tag, local_name),
                                max(INTERVAL, TIMEOUT) * 2)


if __name__ == "__main__":
    alerts.init()
    url = sys.argv[1]
    monitor_site(url)

########NEW FILE########
__FILENAME__ = tallier
#!/usr/bin/env python

"""
Server that aggregates stats from many clients and flushes to graphite.

This service is meant to support hundreds of clients feeding in a total of
thousands of sample points per second via UDP. It can fork into multiple
processes to utilize additional processors/cores.

The architecture comprises:

  - Master: entry point of the server, spins off server processes and polls
      them for aggregate data to flush periodically to graphite.

  - Controller: the main thread of each server process; starts up and shuts down
      the Listener; communicates with the Master; swaps out the Listener's data
      accumulation dict on flush requests, returning the former dict to the
      Master.

  - Listener: a thread of the server process; simply receives data over the
      datagram socket and accumulates it in a dict.

Configuration is through .ini file. Example:

[harold]
host = localhost
port = 8888
secret = haroldsecret

[graphite]
graphite_addr = localhost:2003

[tallier]

# receive datagrams on this port
port = 8125

# consume datagrams with this many processes
num_workers = 3

# sample stats at this frequency (seconds); this is how often data is pushed to
# graphite
flush_interval = 10
"""

from __future__ import division

import collections
import logging
import multiprocessing
import os
import re
import signal
import socket
import threading
import time
import urllib2

import alerts

FLUSH = 'flush'
SHUTDOWN = 'shutdown'

class Master:
    """Entry point of the tally service.

    Spins off server processes and polls them for aggregate data to flush
    periodically to graphite.
    """

    @classmethod
    def from_config(cls, config, harold=None):
        """Instantiate the tally service from a parsed config file."""
        if config.has_option('tallier', 'flush_interval'):
            flush_interval = config.getfloat('tallier', 'flush_interval')
        else:
            flush_interval = 10.0
        if config.has_option('tallier', 'interface'):
            iface = config.get('tallier', 'interface')
        else:
            iface = ''
        port = config.getint('tallier', 'port')
        num_workers = config.getint('tallier', 'num_workers')
        graphite_addr = config.get('graphite', 'graphite_addr')
        if (config.has_option('tallier', 'enable_heartbeat')
            and not config.getboolean('tallier', 'enable_heartbeat')):
            harold = None
        return cls(iface, port, num_workers, flush_interval=flush_interval,
                   graphite_addr=graphite_addr, harold=harold)

    def __init__(self, iface, port, num_workers, flush_interval=10,
                 graphite_addr='localhost:2003', harold=None):
        """Constructor.

        Args:
          - iface: str, address to bind to when the service starts (or '' for
                INADDR_ANY).
          - port: int, port to bind to.
          - num_workers: int, size of datagram receiving pool (processes); must
                be >= 1.
          - flush_interval: float, time (in seconds) between each flush
          - graphite_addr: str, graphite address for reporting collected samples
          - harold: wessex.Harold, optional harold client instance for sending
                heartbeats
        """
        assert num_workers >= 1
        self.iface = iface
        self.port = port
        self.num_workers = num_workers
        self.flush_interval = flush_interval
        self.graphite_host, self.graphite_port = graphite_addr.split(':')
        self.graphite_port = int(self.graphite_port)
        self.harold = harold

        # The following are all set up by the start() method.
        self.next_flush_time = None
        self.last_flush_time = None
        self.sock = None
        self.pipes = None
        self.controllers = None
        self.num_stats = None

    def _bind(self):
        assert self.sock is None, 'Master.start() should only be invoked once'
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.iface, self.port))

    def _create_controllers(self):
        assert self.controllers is None, (
            'Master.start() should only be invoked once')
        assert self.pipes is None, (
            'Master.start() should only be invoked once')
        assert self.num_workers >= 1
        self.pipes = [multiprocessing.Pipe() for _ in xrange(self.num_workers)]

        # Set up the controllers to run in child processes (but do not start
        # them up yet).
        self.controllers = [
            multiprocessing.Process(
                target=Controller.launch, args=(i, self.sock, pipe[1]))
            for i, pipe in enumerate(self.pipes)]

    def _shutdown(self):
        logging.info('Closing socket...')
        self.sock.close()
        self.sock = None
        logging.info('Sending shutdown command...')
        results = self._command_all(SHUTDOWN)
        logging.info('Messages: %r (total = %d)', results, sum(results))
        logging.info('Terminating child processes...')
        for controller in self.controllers:
            controller.terminate()
        for controller in self.controllers:
            controller.join()
        self.pipes = None
        self.controllers = None
        self.next_flush_time = None
        self.last_flush_time = None
        logging.info('Shutdown complete.')

    def _flush(self):
        results = self._command_all(FLUSH)
        agg_counters = collections.defaultdict(float)
        agg_timers = {}
        total_message_count = 0
        total_byte_count = 0
        for counters, timers in results:
            for key, value in counters.iteritems():
                agg_counters[key] += value
                if key.startswith('tallier.messages.child_'):
                    total_message_count += value
                elif key.startswith('tallier.bytes.child_'):
                    total_byte_count += value
            for key, values in timers.iteritems():
                agg_timers.setdefault(key, []).extend(values)

        agg_counters['tallier.messages.total'] = total_message_count
        agg_counters['tallier.bytes.total'] = total_byte_count

        msgs = self._build_graphite_report(agg_counters, agg_timers)
        return self._send_to_graphite(msgs)

    def _build_graphite_report(self, agg_counters, agg_timers):
        now = time.time()
        interval = now - self.last_flush_time
        self.last_flush_time = now

        for key, value in agg_counters.iteritems():
            scaled_value = value / interval
            yield 'stats.%s %f %d' % (key, scaled_value, now)
            yield 'stats_counts.%s %f %d' % (key, value, now)

        for key, values in agg_timers.iteritems():
            # TODO: make the percentile configurable; for now fix to 90
            percentile = 90
            values.sort()
            yield 'stats.timers.%s.lower %f %d' % (key, values[0], now)
            yield 'stats.timers.%s.upper %f %d' % (key, values[-1], now)
            yield ('stats.timers.%s.upper_%d %f %d'
                   % (key, percentile,
                      values[int(len(values) * percentile / 100.0)], now))
            yield ('stats.timers.%s.mean %f %d'
                   % (key, sum(values) / len(values), now))
            yield 'stats.timers.%s.count %f %d' % (key, len(values), now)
            yield ('stats.timers.%s.rate %f %d'
                   % (key, len(values) / interval, now))

        # global 'self' stats
        self.num_stats += len(agg_counters) + len(agg_timers)
        yield 'stats.tallier.num_stats %f %d' % (self.num_stats, now)
        yield 'stats.tallier.num_workers %f %d' % (self.num_workers, now)

    def _send_to_graphite(self, msgs):
        logging.info('Connecting to graphite...')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.graphite_host, self.graphite_port))
        msg = '\n'.join(msgs) + '\n'
        sock.send(msg)
        sock.close()
        logging.info('Stats sent!')
        if self.harold:
            try:
                logging.info('Harold heartbeat.')
                self.harold.heartbeat('tallier', int(self.flush_interval * 3))
            except urllib2.URLError:
                logging.exception('Error sending heartbeat to harold!')

    def _command_all(self, cmd):
        for pipe in self.pipes:
            pipe[0].send(cmd)
        # TODO: should we worry about non-responsive children?
        return [pipe[0].recv() for pipe in self.pipes]

    def start(self):
        """Sets up and starts the tally service (does not return)."""
        self._bind()
        self._create_controllers()
        logging.info('Starting up child processes...')
        for controller in self.controllers:
            controller.daemon = True
            controller.start()
        self.last_flush_time = time.time()
        self.next_flush_time = self.last_flush_time + self.flush_interval
        self.num_stats = 0
        logging.info('Running.')
        try:
            while True:
                # sleep until next flush time
                sleep_time = self.next_flush_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self._flush()
                self.next_flush_time += self.flush_interval
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown()

class Controller:
    """The main thread of each server process.

    The Controller manages a Listener and communicates with the Master. On
    command from the Master it will swap out the Listener's data accumulation
    dict, returning the former dict to the Master. It will also shut down the
    Listener at the Master's request.
    """

    def __init__(self, controller_id, sock, conn):
        """Constructor.

        Args:
          - sock: socket.Socket, bound datagram socket
          - conn: multiprocessing.Connection, for communication with the Master
        """
        self.controller_id = controller_id
        self.sock = sock
        self.conn = conn

        # The following are all set up by the start() method.
        self.listener = None

    @classmethod
    def launch(cls, controller_id, sock, conn):
        """Initialize and start up a Controller (does not return)."""
        controller = cls(controller_id, sock, conn)
        controller.start()

    def _create_listener(self):
        assert self.listener is None, (
            'Controller.start() should only be invoked once')
        self.listener = Listener(self.controller_id, self.sock)

    def _flush(self):
        self.conn.send(self.listener.flush())

    def _shutdown(self):
        # TODO: clean shutdown for listener threads?
        #self.listener.stop()
        logging.info('sending back message count...')
        self.conn.send(self.listener.message_count)
        self.listener = None

    def start(self):
        """Starts the Controller (does not return)."""
        self._create_listener()
        self.listener.start()
        try:
            while True:
                cmd = self.conn.recv()
                if cmd == FLUSH:
                    self._flush()
                elif cmd == SHUTDOWN:
                    self._shutdown()
                    break
                else:
                    logging.info(
                        'controller reporting bad command from master: %s', cmd)
        except KeyboardInterrupt:
            self._shutdown()
        logging.info('controller stopped.')

class Listener(threading.Thread):
    """A thread that receives stats from a datagram socket.

    The stats are accumulated in a dict that can be swapped out at any time.
    """

    def __init__(self, listener_id, sock):
        """Constructor.

        Args:
          - sock: socket.Socket, bound datagram socket
        """
        super(Listener, self).__init__()
        self.listener_id = listener_id
        self.sock = sock

        # The following are all set up by the start() method.
        self.current_samples = None
        self.message_count = None
        self.last_message_count = None
        self.byte_count = None
        self.last_byte_count = None

    def start(self):
        """Creates the Listener thread, starts up the Listener, and returns."""
        assert self.current_samples is None, (
            'Listener.start() should only be invoked once')
        self.daemon = True
        self.current_samples = (collections.defaultdict(float), {})
        self.message_count = 0
        self.last_message_count = 0
        self.byte_count = 0
        self.last_byte_count = 0
        super(Listener, self).start()

    def run(self):
        """Runs the main loop of the Listener (does not return)."""
        while True:
            datagram, addr = self.sock.recvfrom(1024)
            self._handle_datagram(datagram)

    def _handle_datagram(self, datagram):
        samples = Sample.parse(datagram)
        for sample in samples:
            self._handle_sample(sample)
        self.message_count += 1
        self.byte_count += len(datagram)

    def _handle_sample(self, sample):
        key = sample.key
        value = sample.value
        if sample.value_type is Sample.COUNTER:
            self.current_samples[0][key] += value / sample.sample_rate
        else:
            self.current_samples[1].setdefault(key, []).append(value)

    def flush(self):
        samples, self.current_samples = (
            self.current_samples, (collections.defaultdict(float), {}))

        # Include count of messages/bytes received by this listener process
        # since the last flush.
        mc = self.message_count
        samples[0]['tallier.messages.child_%s' % self.listener_id] = (
            mc - self.last_message_count)
        self.last_message_count = mc

        bc = self.byte_count
        samples[0]['tallier.bytes.child_%s' % self.listener_id] = (
            bc - self.last_byte_count)
        self.last_byte_count = bc

        return samples

class Sample:
    """A key, value, value type, and sample rate."""

    COUNTER = 'counter'
    TIMER = 'timer'

    _VALID_CHAR_PATTERN = re.compile(r'[A-Za-z0-9._-]')

    def __init__(self, key, value, value_type, sample_rate):
        self.key = key
        self.value = value
        self.value_type = value_type
        self.sample_rate = sample_rate

    def __str__(self):
        return '%s:%f@%s|%f' % (
            self.key, self.value,
            'ms' if self.value_type is self.TIMER else 'c',
            self.sample_rate)

    @classmethod
    def parse(cls, datagram):
        """Parses a datagram into a list of Sample values."""
        samples = []
        previous = ''
        for metric in datagram.splitlines():
            if len(metric) > 2 and metric[0] == '^':
                try:
                    prefix_len = int(metric[1:3], 16)
                except ValueError:
                    continue
                metric = previous[:prefix_len] + metric[3:]
            previous = metric
            parts = metric.split(':')
            if parts:
                key = cls._normalize_key(parts.pop(0))
                for part in parts:
                    try:
                        samples.append(cls._parse_part(key, part))
                    except ValueError:
                        continue
        return samples

    @classmethod
    def _normalize_key(cls, key):
        key = '_'.join(key.split()).replace('\\', '-')
        return ''.join(cls._VALID_CHAR_PATTERN.findall(key))

    @classmethod
    def _parse_part(cls, key, part):
        # format: <value> '|' <value_type> ('@' <sample_rate>)?
        fields = part.split('|')
        if len(fields) != 2:
            raise ValueError
        value = float(fields[0])
        if '@' in fields[1]:
            fields[1], sample_rate = fields[1].split('@', 1)
            sample_rate = float(sample_rate)
            if not (0.0 < sample_rate <= 1.0):
                raise ValueError
        else:
            sample_rate = 1.0
        if fields[1] == 'ms':
            value_type = cls.TIMER
        else:
            value_type = cls.COUNTER
        return cls(key, value, value_type, sample_rate)

if __name__ == '__main__':
    alerts.init()
    master = Master.from_config(alerts.config, alerts.harold)
    logging.info('Serving...')
    master.start()
    logging.info('Done!')

########NEW FILE########
__FILENAME__ = tallier_test
#!/usr/bin/env python

import collections
import ConfigParser
import time
import unittest

import tallier
import testing

def build_config(**sections):
    config = ConfigParser.RawConfigParser()
    for section, data in sections.iteritems():
        config.add_section(section)
        for name, value in data.iteritems():
            config.set(section, name, value)
    return config

class MasterTest(unittest.TestCase):
    def test_from_config(self):
        # underspecified
        harold = dict(host='localhost', port=8888, secret='secret')
        graphite = dict(graphite_addr='localhost:9999')
        t = dict(port=7777, num_workers=1)
        config = build_config(harold=harold, graphite=graphite, tallier=t)
        master = tallier.Master.from_config(config, harold='stub')
        self.assertEquals('', master.iface)
        self.assertEquals(7777, master.port)
        self.assertEquals(1, master.num_workers)
        self.assertEquals(10.0, master.flush_interval)
        self.assertEquals('localhost', master.graphite_host)
        self.assertEquals(9999, master.graphite_port)
        self.assertTrue(master.harold is not None)

        # fully specified
        t.update(flush_interval=5.0, interface='localhost',
                 enable_heartbeat='true')
        config = build_config(harold=harold, graphite=graphite, tallier=t)
        master = tallier.Master.from_config(config, harold='stub')
        self.assertEquals(5.0, master.flush_interval)
        self.assertEquals('localhost', master.iface)
        self.assertTrue(master.harold is not None)

        # disable heartbeats
        t.update(enable_heartbeat='false')
        config = build_config(harold=harold, graphite=graphite, tallier=t)
        master = tallier.Master.from_config(config, harold='stub')
        self.assertTrue(master.harold is None)

    @testing.stub(time, 'time')
    def test_build_graphite_report(self):
        now = 1000
        time.time = lambda: now
        master = tallier.Master('', 0, 1, flush_interval=2.0)
        master.last_flush_time = now - 2
        master.num_stats = 0

        agg_counters = dict(a=1, b=2, c=3)
        agg_timers = dict(
            a=range(100),  # mean=49.5
        )

        m = lambda k, v: '%s %f %d' % (k, v, now)

        msgs = list(master._build_graphite_report(agg_counters, agg_timers))
        self.assertEquals(
            sorted([
                m('stats.a', 0.5),
                m('stats_counts.a', 1),
                m('stats.b', 1),
                m('stats_counts.b', 2),
                m('stats.c', 1.5),
                m('stats_counts.c', 3),
                m('stats.timers.a.lower', 0),
                m('stats.timers.a.upper', 99),
                m('stats.timers.a.upper_90', 90),
                m('stats.timers.a.mean', 49.5),
                m('stats.timers.a.count', 100),
                m('stats.timers.a.rate', 50),
                m('stats.tallier.num_workers', 1),
                m('stats.tallier.num_stats', 4),
            ]), sorted(msgs))

    def test_flush(self):
        child_reports = [
            ({'a': 1}, {'t1': [1, 2, 3]}),
            ({'b': 2}, {'t2': [2, 3, 4]}),
            ({'a': 3, 'b': 4}, {'t1': [5, 6], 't2': [6, 7]}),
        ]
        master = tallier.Master('', 0, 1)
        master._command_all = lambda cmd: child_reports
        master._build_graphite_report = lambda x, y: (
            x, dict((k, list(sorted(v))) for k, v in y.iteritems()))
        master._send_to_graphite = lambda x: x

        agg_counters, agg_timers = master._flush()
        self.assertEquals(
            {'a': 4,
             'b': 6,
             'tallier.messages.total': 0,
             'tallier.bytes.total': 0},
             agg_counters)
        self.assertEquals(
            {'t1': [1, 2, 3, 5, 6], 't2': [2, 3, 4, 6, 7]}, agg_timers)

class ListenerTest(unittest.TestCase):
    def test_handle_sample(self):
        listener = tallier.Listener(0, None)
        listener.current_samples = (collections.defaultdict(float), {})

        s = tallier.Sample(
            key='key', value=1.0, value_type=tallier.Sample.COUNTER,
            sample_rate=0.5)
        listener._handle_sample(s)
        self.assertEquals(2.0, listener.current_samples[0]['key'])

        s.sample_rate = 1.0
        listener._handle_sample(s)
        self.assertEquals(3.0, listener.current_samples[0]['key'])

        s.value_type = tallier.Sample.TIMER
        for i in xrange(3):
            s.value = i
            listener._handle_sample(s)
        self.assertEquals(range(3), listener.current_samples[1]['key'])

    def test_flush(self):
        listener = tallier.Listener(0, None)
        listener.message_count = 0
        listener.last_message_count = 0
        listener.byte_count = 0
        listener.last_byte_count = 0
        listener.current_samples = (collections.defaultdict(float), {})
        dgram = 'key:1|c:2|c:3|c:4|ms:5|ms:6|ms'
        listener._handle_datagram(dgram)
        expected_data = (
            {'key': 6},
            {'key': [4, 5, 6]})
        self.assertEquals(expected_data, listener.current_samples)
        expected_data[0]['tallier.messages.child_0'] = 1
        expected_data[0]['tallier.bytes.child_0'] = len(dgram)
        self.assertEquals(expected_data, listener.flush())
        self.assertEquals(({}, {}), listener.current_samples)

class SampleTest(unittest.TestCase):
    def test_normalize_key(self):
        n = tallier.Sample._normalize_key
        self.assertEquals('test', n('test'))
        self.assertEquals('test_1', n('test_1'))
        self.assertEquals('test_1-2', n('test 1\\2'))
        self.assertEquals('test1-2', n('[()@test#@&$^@&#*^1-2'))

    def test_parse_part(self):
        p = tallier.Sample._parse_part
        k = 'key'
        self.assertRaises(ValueError, p, k, '123')

        s = p(k, '123|c')
        self.assertEquals(k, s.key)
        self.assertEquals(123.0, s.value)
        self.assertEquals(tallier.Sample.COUNTER, s.value_type)
        self.assertEquals(1.0, s.sample_rate)

        s = p(k, '123|c@0.5')
        self.assertEquals(k, s.key)
        self.assertEquals(123.0, s.value)
        self.assertEquals(tallier.Sample.COUNTER, s.value_type)
        self.assertEquals(0.5, s.sample_rate)

        s = p(k, '123.45|ms')
        self.assertEquals(k, s.key)
        self.assertEquals(123.45, s.value)
        self.assertEquals(tallier.Sample.TIMER, s.value_type)
        self.assertEquals(1.0, s.sample_rate)

    def test_parse(self):
        self.assertEquals([], tallier.Sample.parse('a:b:c'))

        (s,) = tallier.Sample.parse('key:123.45|ms@0.5')
        self.assertEquals('key', s.key)
        self.assertEquals(123.45, s.value)
        self.assertEquals(tallier.Sample.TIMER, s.value_type)
        self.assertEquals(0.5, s.sample_rate)

        ss = tallier.Sample.parse('key1:1|c:2|c:3|c')
        self.assertEquals(3, len(ss))
        self.assertEquals('key1', ss[0].key)
        self.assertEquals('key1', ss[1].key)
        self.assertEquals(1, ss[0].value)
        self.assertEquals(2, ss[1].value)
        self.assertEquals(3, ss[2].value)

        multisample = tallier.Sample.parse('key1:1|c\nkey2:9|c')
        self.assertEquals(2, len(multisample))
        self.assertEquals('key1', multisample[0].key)
        self.assertEquals('key2', multisample[1].key)
        self.assertEquals(1, multisample[0].value)
        self.assertEquals(9, multisample[1].value)

    def test_parse_decompression(self):
        ss = tallier.Sample.parse('^03abc:1|c\n^02def:2|c\n^08:3|c')
        self.assertEquals(4, len(ss))
        self.assertEquals('abc', ss[0].key)
        self.assertEquals(1, ss[0].value)
        self.assertEquals('abdef', ss[1].key)
        self.assertEquals(2, ss[1].value)
        self.assertEquals('abdef', ss[2].key)
        self.assertEquals(2, ss[2].value)
        self.assertEquals('abdef', ss[3].key)
        self.assertEquals(3, ss[3].value)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testing
import tempfile

import wessex

import alerts

def stub(namespace, name):
    '''Allows a function to override a value and restore it upon returning.'''
    def decorator(f):
        def wrapped(*args, **kwargs):
            try:
                orig_value = getattr(namespace, name)
                has_orig_value = True
            except AttributeError:
                has_orig_value = False
            try:
                return f(*args, **kwargs)
            finally:
                if has_orig_value:
                    setattr(namespace, name, orig_value)
                else:
                    try:
                        delattr(namespace, name)
                    except AttributeError:
                        pass
        return wrapped
    return decorator

class TestingHarold(wessex.Harold):
    def __init__(self, *args, **kwargs):
        super(TestingHarold, self).__init__(*args, **kwargs)
        self.reset_for_testing()

    def _post_to_harold(self, path, data):
        self.post_log.append((path, data))

    def reset_for_testing(self):
        self.post_log = []

@stub(wessex, 'Harold')
def init_alerts(**sections):
    wessex.Harold = TestingHarold
    config = dict(
        harold=dict(host='localhost', port=8888, secret='secret'),
    )
    config.update(sections)
    with tempfile.NamedTemporaryFile() as f:
        for section, data in config.iteritems():
            f.write('[%s]\n' % section)
            for name, value in data.iteritems():
                f.write('%s = %s\n' % (name, value))
            f.write('\n')
        f.flush()
        alerts.init(config_path=f.name)



########NEW FILE########
__FILENAME__ = testing_test
import unittest

import alerts
import testing

class StubTest(unittest.TestCase):
    def setUp(self):
        class Object:
            x = 'x'
        self.object = Object()

    def test_return(self):
        @testing.stub(self.object, 'x')
        def test():
            self.assertEquals('x', self.object.x)
            self.object.x = 'y'
            return self.object.x
        self.assertEquals('y', test())
        self.assertEquals('x', self.object.x)

    def test_raise(self):
        @testing.stub(self.object, 'x')
        def test():
            self.object.x = 'y'
            self.assertEquals('y', self.object.x)
            raise RuntimeError
        self.assertRaises(RuntimeError, test)
        self.assertEquals('x', self.object.x)

    def test_undefined(self):
        @testing.stub(self.object, 'undef1')
        @testing.stub(self.object, 'undef2')
        def test():
            self.assertRaises(AttributeError, lambda: self.object.undef1)
            self.object.undef1 = 1
            self.assertEquals(1, self.object.undef1)
            self.assertRaises(AttributeError, lambda: self.object.undef2)
        test()
        self.assertRaises(AttributeError, lambda: self.object.undef1)
        self.assertRaises(AttributeError, lambda: self.object.undef2)

class InitAlertsTest(unittest.TestCase):
    def test_init(self):
        testing.init_alerts(
            custom1=dict(a=1, b='two'),
            custom2=dict(c='c'),
        )
        self.assertEquals('localhost', alerts.harold.host)
        self.assertEquals(8888, alerts.harold.port)
        self.assertEquals('secret', alerts.harold.secret)
        self.assertEquals(1, alerts.config.getint('custom1', 'a'))
        self.assertTrue(isinstance(alerts.harold, testing.TestingHarold))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utilization
#!/usr/bin/python

from __future__ import division

import csv
import urllib2
import collections
import time

import alerts


def fetch_session_counts(haproxy_stats_urls):
    current = collections.Counter()
    limit = collections.Counter()
    queue = {}

    for url in haproxy_stats_urls:
        csv_data = urllib2.urlopen(url, timeout=3)
        reader = csv.DictReader(csv_data)

        for i, row in enumerate(reader):
            if i == 0: continue

            proxy_name = row["# pxname"]
            service_name = row["svname"]
            q_cur = row["qcur"]
            s_cur = row["scur"]
            s_lim = row["slim"]
            status = row["status"]

            if service_name == "BACKEND":
                queue[proxy_name] = int(q_cur)

            if service_name in ("FRONTEND", "BACKEND"):
                continue

            if status != "UP":
                continue

            current[proxy_name] += int(s_cur)
            limit[proxy_name] += int(s_lim)

    return [(pool, current[pool], capacity, queue[pool])
            for pool, capacity in limit.most_common()]


def notify_graphite(usage):
    values = {}
    for pool, cur, limit, queue in usage:
        values["stats.utilization.%s.current" % pool] = cur
        values["stats.utilization.%s.capacity" % pool] = limit
        values["stats.utilization.%s.queue" % pool] = queue
    alerts.graphite.send_values(values)


def pretty_print(usage):
    print "%20s%20s%10s" % ("", "sessions", "")
    print "%20s%10s%10s%10s%10s" % ("pool", "cur", "max", "% util", "queue")
    print "-" * 60
    for pool, cur, limit, queue in usage:
        print "%20s%10d%10d%10.2f%10d" % (pool, cur, limit, cur / limit * 100.0, queue)


def main():
    alerts.init()

    haproxy_urls = [value for key, value in
                    alerts.config.items("haproxy")
                    if key.startswith("url")]

    while True:
        try:
            usage_by_pool = fetch_session_counts(haproxy_urls)
        except urllib2.URLError:
            pass
        else:
            notify_graphite(usage_by_pool)
            pretty_print(usage_by_pool)

        time.sleep(1)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = zenoss
import re
import json
import logging
import requests

log = logging.getLogger(__name__)

ROUTERS = {'MessagingRouter': 'messaging',
           'EventsRouter': 'evconsole',
           'ProcessRouter': 'process',
           'ServiceRouter': 'service',
           'DeviceRouter': 'device',
           'NetworkRouter': 'network',
           'TemplateRouter': 'template',
           'DetailNavRouter': 'detailnav',
           'ReportRouter': 'report',
           'MibRouter': 'mib',
           'ZenPackRouter': 'zenpack'}


class ZenossException(Exception):
    def __call__(self, *args):
        return self.__class__(*(self.args + args))


class Zenoss(object):
    def __init__(self, host, username, password, pem_path=None):
        self.__host = host
        self.__session = requests.Session()
        self.__session.auth = (username, password)
        self.__pem_path = pem_path
        self.__req_count = 0

    def __router_request(self, router, method, data=None):
        if router not in ROUTERS:
            raise Exception('Router "' + router + '" not available.')

        req_data = json.dumps([dict(
            action=router,
            method=method,
            data=data,
            type='rpc',
            tid=self.__req_count)])

        log.debug('Making request to router %s with method %s', router, method)
        uri = '%s/zport/dmd/%s_router' % (self.__host, ROUTERS[router])
        headers = {'Content-type': 'application/json; charset=utf-8'}
        response = self.__session.post(uri, data=req_data, headers=headers)
        self.__req_count += 1

        # The API returns a 200 response code even whe auth is bad.
        # With bad auth, the login page is displayed. Here I search for
        # an element on the login form to determine if auth failed.
        if re.search('name="__ac_name"', response.content):
            log.error('Request failed. Bad username/password.')
            raise ZenossException('Request failed. Bad username/password.')

        return json.loads(response.content)['result']

    def __rrd_request(self, device_uid, dsname):
        return self.__session.get('%s/%s/getRRDValue?dsname=%s' % (self.__host, device_uid, dsname)).content

    def get_devices(self, device_class='/zport/dmd/Devices', limit=None):
        """Get a list of all devices.

        """
        log.info('Getting all devices')
        return self.__router_request('DeviceRouter', 'getDevices',
                                     data=[{'uid': device_class, 'params': {}, 'limit': limit}])

    def find_device(self, device_name):
        """Find a device by name.

        """
        log.info('Finding device %s', device_name)
        all_devices = self.get_devices()

        try:
            device = [d for d in all_devices['devices'] if d['name'] == device_name][0]
            # We need to save the has for later operations
            device['hash'] = all_devices['hash']
            log.info('%s found', device_name)
            return device
        except IndexError:
            log.error('Cannot locate device %s', device_name)
            raise Exception('Cannot locate device %s' % device_name)

    def add_device(self, device_name, device_class, collector='localhost'):
        """Add a device.

        """
        log.info('Adding %s', device_name)
        data = dict(deviceName=device_name, deviceClass=device_class, model=True, collector=collector)
        return self.__router_request('DeviceRouter', 'addDevice', [data])

    def remove_device(self, device_name):
        """Remove a device.

        """
        log.info('Removing %s', device_name)
        device = self.find_device(device_name)
        data = dict(uids=[device['uid']], hashcheck=device['hash'], action='delete')
        return self.__router_request('DeviceRouter', 'removeDevices', [data])

    def move_device(self, device_name, organizer):
        """Move the device the organizer specified.

        """
        log.info('Moving %s to %s', device_name, organizer)
        device = self.find_device(device_name)
        data = dict(uids=[device['uid']], hashcheck=device['hash'], target=organizer)
        return self.__router_request('DeviceRouter', 'moveDevices', [data])

    def set_prod_state(self, device_name, prod_state):
        """Set the production state of a device.

        """
        log.info('Setting prodState on %s to %s', device_name, prod_state)
        device = self.find_device(device_name)
        data = dict(uids=[device['uid']], prodState=prod_state, hashcheck=device['hash'])
        return self.__router_request('DeviceRouter', 'setProductionState', [data])

    def set_maintenance(self, device_name):
        """Helper method to set prodState for device so that it does not alert.

        """
        return self.set_prod_state(device_name, 300)

    def set_production(self, device_name):
        """Helper method to set prodState for device so that it is back in production and alerting.

        """
        return self.set_prod_state(device_name, 1000)

    def set_product_info(self, device_name, hw_manufacturer, hw_product_name, os_manufacturer, os_product_name):
        """Set ProductInfo on a device.

        """
        log.info('Setting ProductInfo on %s', device_name)
        device = self.find_device(device_name)
        data = dict(uid=device['uid'],
                    hwManufacturer=hw_manufacturer,
                    hwProductName=hw_product_name,
                    osManufacturer=os_manufacturer,
                    osProductName=os_product_name)
        return self.__router_request('DeviceRouter', 'setProductInfo', [data])

    def set_rhel_release(self, device_name, release):
        """Sets the proper release of RedHat Enterprise Linux."""
        if type(release) is not float:
            log.error("RHEL release must be a float")
            return {u'success': False}
        log.info('Setting RHEL release on %s to %s', device_name, release)
        device = self.find_device(device_name)
        return self.set_product_info(device_name, device['hwManufacturer']['name'], device['hwModel']['name'], 'RedHat',
                                     'RHEL {}'.format(release))

    def set_device_info(self, device_name, data):
        """Set attributes on a device or device organizer.
            This method accepts any keyword argument for the property that you wish to set.

        """
        data['uid'] = self.find_device(device_name)['uid']
        return self.__router_request('DeviceRouter', 'setInfo', [data])

    def remodel_device(self, device_name):
        """Submit a job to have a device remodeled.

        """
        return self.__router_request('DeviceRouter', 'remodel', [dict(uid=self.find_device(device_name)['uid'])])

    def set_collector(self, device_name, collector):
        """Set collector for device.

        """
        device = self.find_device(device_name)
        data = dict(uids=[device['uid']], hashcheck=device['hash'], collector=collector)
        return self.__router_request('DeviceRouter', 'setCollector', [data])

    def rename_device(self, device_name, new_name):
        """Rename a device.

        """
        data = dict(uid=self.find_device(device_name)['uid'], newId=new_name)
        return self.__router_request('DeviceRouter', 'renameDevice', [data])

    def reset_ip(self, device_name, ip_address=''):
        """Reset IP address(es) of device to the results of a DNS lookup or a manually set address.

        """
        device = self.find_device(device_name)
        data = dict(uids=[device['uid']], hashcheck=device['hash'], ip=ip_address)
        return self.__router_request('DeviceRouter', 'resetIp', [data])

    def get_events(self, device=None, limit=100, component=None, event_class=None):
        """Find current events.

        """
        data = dict(start=0, limit=limit, dir='DESC', sort='severity')
        data['params'] = dict(severity=[5, 4, 3, 2], eventState=[0, 1])
        if device:
            data['params']['device'] = device
        if component:
            data['params']['component'] = component
        if event_class:
            data['params']['eventClass'] = event_class
        log.info('Getting events for %s', data)
        return self.__router_request('EventsRouter', 'query', [data])['events']

    def change_event_state(self, event_id, state):
        """Change the state of an event.

        """
        log.info('Changing eventState on %s to %s', event_id, state)
        return self.__router_request('EventsRouter', state, [{'evids': [event_id]}])

    def ack_event(self, event_id):
        """Helper method to set the event state to acknowledged.

        """
        return self.change_event_state(event_id, 'acknowledge')

    def close_event(self, event_id):
        """Helper method to set the event state to closed.

        """
        return self.change_event_state(event_id, 'close')

    def create_event_on_device(self, device_name, severity, summary, component='', evclasskey='', evclass=''):
        """Manually create a new event for the device specified.

        """
        log.info('Creating new event for %s with severity %s', device_name, severity)
        if severity not in ('Critical', 'Error', 'Warning', 'Info', 'Debug', 'Clear'):
            raise Exception('Severity %s is not valid.' % severity)
        data = dict(device=device_name, summary=summary, severity=severity, component=component, evclasskey=evclasskey, evclass=evclass)
        return self.__router_request('EventsRouter', 'add_event', [data])

    def get_load_average(self, device_name):
        """Returns the 5 minute load average for a device.
        """
        result = self.__rrd_request(self.find_device(device_name)['uid'], 'laLoadInt5_laLoadInt5')
        return round(float(result) / 100.0, 2)

########NEW FILE########
