__FILENAME__ = check_zookeeper
#! /usr/bin/env python
""" Check Zookeeper Cluster

Generic monitoring script that could be used with multiple platforms (Ganglia, Nagios, Cacti).

It requires ZooKeeper 3.4.0 or greater. The script needs the 'mntr' 4letter word 
command (patch ZOOKEEPER-744) that was now commited to the trunk.
The script also works with ZooKeeper 3.3.x but in a limited way.
"""

import sys
import socket
import logging
import re
import subprocess

from StringIO import StringIO
from optparse import OptionParser, OptionGroup

__version__ = (0, 1, 0)

log = logging.getLogger()
logging.basicConfig(level=logging.ERROR)

class NagiosHandler(object):

    @classmethod
    def register_options(cls, parser):
        group = OptionGroup(parser, 'Nagios specific options')

        group.add_option('-w', '--warning', dest='warning')
        group.add_option('-c', '--critical', dest='critical')

        parser.add_option_group(group)

    def analyze(self, opts, cluster_stats):
        try:
            warning = int(opts.warning)
            critical = int(opts.critical)

        except (TypeError, ValueError):
            print >>sys.stderr, 'Invalid values for "warning" and "critical".'
            return 2

        if opts.key is None:
            print >>sys.stderr, 'You should specify a key name.'
            return 2

        warning_state, critical_state, values = [], [], []
        for host, stats in cluster_stats.items():
            if opts.key in stats:

                value = stats[opts.key]
                values.append('%s=%s;%s;%s' % (host, value, warning, critical))

                if warning >= value > critical or warning <= value < critical:
                    warning_state.append(host)

                elif (warning < critical and critical <= value) or (warning > critical and critical >= value):
                    critical_state.append(host)

        values = ' '.join(values)
        if critical_state:
            print 'Critical "%s" %s!|%s' % (opts.key, ', '.join(critical_state), values)
            return 2
        
        elif warning_state:
            print 'Warning "%s" %s!|%s' % (opts.key, ', '.join(warning_state), values)
            return 1

        else:
            print 'Ok "%s"!|%s' % (opts.key, values)
            return 0

class CactiHandler(object):

    @classmethod
    def register_options(cls, parser):
        group = OptionGroup(parser, 'Cacti specific options')
        
        group.add_option('-l', '--leader', dest='leader', 
            action="store_true", help="only query the cluster leader")

        parser.add_option_group(group)

    def analyze(self, opts, cluster_stats):
        if opts.key is None:
            print >>sys.stderr, 'The key name is mandatory.'
            return 1

        if opts.leader is True:
            try:
                leader = [x for x in cluster_stats.values() \
                    if x.get('zk_server_state', '') == 'leader'][0] 

            except IndexError:
                print >>sys.stderr, 'No leader found.'
                return 3

            if opts.key in leader:
                print leader[opts.key]
                return 0

            else:
                print >>sys.stderr, 'Unknown key: "%s"' % opts.key
                return 2
        else:
            for host, stats in cluster_stats.items():
                if opts.key not in stats: 
                    continue

                host = host.replace(':', '_')
                print '%s:%s' % (host, stats[opts.key]),


class GangliaHandler(object):

    @classmethod
    def register_options(cls, parser):
        group = OptionGroup(parser, 'Ganglia specific options')

        group.add_option('-g', '--gmetric', dest='gmetric', 
            default='/usr/bin/gmetric', help='ganglia gmetric binary '\
            'location: /usr/bin/gmetric')

        parser.add_option_group(group)

    def call(self, *args, **kwargs):
        subprocess.call(*args, **kwargs)

    def analyze(self, opts, cluster_stats):
        if len(cluster_stats) != 1:
            print >>sys.stderr, 'Only allowed to monitor a single node.'
            return 1

        for host, stats in cluster_stats.items():
            for k, v in stats.items():
                try:
                    self.call([opts.gmetric, '-n', k, '-v', str(int(v)), '-t', 'uint32'])
                except (TypeError, ValueError):
                    pass

class ZooKeeperServer(object):

    def __init__(self, host='localhost', port='2181', timeout=1):
        self._address = (host, int(port))
        self._timeout = timeout

    def get_stats(self):
        """ Get ZooKeeper server stats as a map """
        data = self._send_cmd('mntr')
        if data:
            return self._parse(data)
        else:
            data = self._send_cmd('stat')
            return self._parse_stat(data)

    def _create_socket(self):
        return socket.socket()

    def _send_cmd(self, cmd):
        """ Send a 4letter word command to the server """
        s = self._create_socket()
        s.settimeout(self._timeout)

        s.connect(self._address)
        s.send(cmd)

        data = s.recv(2048)
        s.close()

        return data

    def _parse(self, data):
        """ Parse the output from the 'mntr' 4letter word command """
        h = StringIO(data)
        
        result = {}
        for line in h.readlines():
            try:
                key, value = self._parse_line(line)
                result[key] = value
            except ValueError:
                pass # ignore broken lines

        return result

    def _parse_stat(self, data):
        """ Parse the output from the 'stat' 4letter word command """
        h = StringIO(data)

        result = {}
        
        version = h.readline()
        if version:
            result['zk_version'] = version[version.index(':')+1:].strip()

        # skip all lines until we find the empty one
        while h.readline().strip(): pass

        for line in h.readlines():
            m = re.match('Latency min/avg/max: (\d+)/(\d+)/(\d+)', line)
            if m is not None:
                result['zk_min_latency'] = int(m.group(1))
                result['zk_avg_latency'] = int(m.group(2))
                result['zk_max_latency'] = int(m.group(3))
                continue

            m = re.match('Received: (\d+)', line)
            if m is not None:
                result['zk_packets_received'] = int(m.group(1))
                continue

            m = re.match('Sent: (\d+)', line)
            if m is not None:
                result['zk_packets_sent'] = int(m.group(1))
                continue

            m = re.match('Outstanding: (\d+)', line)
            if m is not None:
                result['zk_outstanding_requests'] = int(m.group(1))
                continue

            m = re.match('Mode: (.*)', line)
            if m is not None:
                result['zk_server_state'] = m.group(1)
                continue

            m = re.match('Node count: (\d+)', line)
            if m is not None:
                result['zk_znode_count'] = int(m.group(1))
                continue

        return result 

    def _parse_line(self, line):
        try:
            key, value = map(str.strip, line.split('\t'))
        except ValueError:
            raise ValueError('Found invalid line: %s' % line)

        if not key:
            raise ValueError('The key is mandatory and should not be empty')

        try:
            value = int(value)
        except (TypeError, ValueError):
            pass

        return key, value

def main():
    opts, args = parse_cli()

    cluster_stats = get_cluster_stats(opts.servers)
    if opts.output is None:
        dump_stats(cluster_stats)
        return 0

    handler = create_handler(opts.output)
    if handler is None:
        log.error('undefined handler: %s' % opts.output)
        sys.exit(1)

    return handler.analyze(opts, cluster_stats)

def create_handler(name):
    """ Return an instance of a platform specific analyzer """
    try:
        return globals()['%sHandler' % name.capitalize()]()
    except KeyError:
        return None

def get_all_handlers():
    """ Get a list containing all the platform specific analyzers """
    return [NagiosHandler, CactiHandler, GangliaHandler]

def dump_stats(cluster_stats):
    """ Dump cluster statistics in an user friendly format """
    for server, stats in cluster_stats.items():
        print 'Server:', server

        for key, value in stats.items():
            print "%30s" % key, ' ', value
        print

def get_cluster_stats(servers):
    """ Get stats for all the servers in the cluster """
    stats = {}
    for host, port in servers:
        try:
            zk = ZooKeeperServer(host, port)
            stats["%s:%s" % (host, port)] = zk.get_stats()

        except socket.error, e:
            # ignore because the cluster can still work even 
            # if some servers fail completely

            # this error should be also visible in a variable
            # exposed by the server in the statistics

            logging.info('unable to connect to server '\
                '"%s" on port "%s"' % (host, port))

    return stats


def get_version():
    return '.'.join(map(str, __version__))


def parse_cli():
    parser = OptionParser(usage='./check_zookeeper.py <options>', version=get_version())

    parser.add_option('-s', '--servers', dest='servers', 
        help='a list of SERVERS', metavar='SERVERS')

    parser.add_option('-o', '--output', dest='output', 
        help='output HANDLER: nagios, ganglia, cacti', metavar='HANDLER')

    parser.add_option('-k', '--key', dest='key')

    for handler in get_all_handlers():
        handler.register_options(parser)

    opts, args = parser.parse_args()

    if opts.servers is None:
        parser.error('The list of servers is mandatory')

    opts.servers = [s.split(':') for s in opts.servers.split(',')]

    return (opts, args)


if __name__ == '__main__':
    sys.exit(main())


########NEW FILE########
__FILENAME__ = zookeeper_ganglia
""" Python Ganglia Module for ZooKeeper monitoring

Inspired by: http://gist.github.com/448007

Copy this file to /usr/lib/ganglia/python_plugins

"""

import sys
import socket
import time
import re
import copy

from StringIO import StringIO

TIME_BETWEEN_QUERIES = 20
ZK_METRICS = {
    'time' : 0,
    'data' : {}
}
ZK_LAST_METRICS = copy.deepcopy(ZK_METRICS)


class ZooKeeperServer(object):

    def __init__(self, host='localhost', port='2181', timeout=1):
        self._address = (host, int(port))
        self._timeout = timeout

    def get_stats(self):
        """ Get ZooKeeper server stats as a map """
        global ZK_METRICS, ZK_LAST_METRICS
        # update cache
        ZK_METRICS = {
          'time' : time.time(),
          'data' : {}
        }
        data = self._send_cmd('mntr')
        if data:
            parsed_data =  self._parse(data)
        else:
            data = self._send_cmd('stat')
            parsed_data = self._parse_stat(data)
        ZK_METRICS['data'] = parsed_data
        ZK_LAST_METRICS = copy.deepcopy(ZK_METRICS)
        return parsed_data

    def _create_socket(self):
        return socket.socket()

    def _send_cmd(self, cmd):
        """ Send a 4letter word command to the server """
        s = self._create_socket()
        s.settimeout(self._timeout)

        s.connect(self._address)
        s.send(cmd)

        # read all the data until the socket closes
        data = ""
        newdata = s.recv(2048)
        while newdata:
            data += newdata
            newdata = s.recv(2048)

        s.close()

        return data

    def _parse(self, data):
        """ Parse the output from the 'mntr' 4letter word command """
        h = StringIO(data)

        result = {}
        for line in h.readlines():
            try:
                key, value = self._parse_line(line)
                result[key] = value
            except ValueError:
                pass # ignore broken lines

        return result

    def _parse_stat(self, data):
        """ Parse the output from the 'stat' 4letter word command """
        global ZK_METRICS, ZK_LAST_METRICS

        h = StringIO(data)

        result = {}

        version = h.readline()
        if version:
            result['zk_version'] = version[version.index(':')+1:].strip()

        # skip all lines until we find the empty one
        while h.readline().strip(): pass

        for line in h.readlines():
            m = re.match('Latency min/avg/max: (\d+)/(\d+)/(\d+)', line)
            if m is not None:
                result['zk_min_latency'] = int(m.group(1))
                result['zk_avg_latency'] = int(m.group(2))
                result['zk_max_latency'] = int(m.group(3))
                continue

            m = re.match('Received: (\d+)', line)
            if m is not None:
                cur_packets = int(m.group(1))
                packet_delta = cur_packets - ZK_LAST_METRICS['data'].get('zk_packets_received_total', cur_packets)
                time_delta = ZK_METRICS['time'] - ZK_LAST_METRICS['time']
                time_delta = 10.0
                try:
                    result['zk_packets_received_total'] = cur_packets
                    result['zk_packets_received'] = packet_delta / float(time_delta)
                except ZeroDivisionError:
                    result['zk_packets_received'] = 0
                continue

            m = re.match('Sent: (\d+)', line)
            if m is not None:
                cur_packets = int(m.group(1))
                packet_delta = cur_packets - ZK_LAST_METRICS['data'].get('zk_packets_sent_total', cur_packets)
                time_delta = ZK_METRICS['time'] - ZK_LAST_METRICS['time']
                try:
                    result['zk_packets_sent_total'] = cur_packets
                    result['zk_packets_sent'] = packet_delta / float(time_delta)
                except ZeroDivisionError:
                    result['zk_packets_sent'] = 0
                continue

            m = re.match('Outstanding: (\d+)', line)
            if m is not None:
                result['zk_outstanding_requests'] = int(m.group(1))
                continue

            m = re.match('Mode: (.*)', line)
            if m is not None:
                result['zk_server_state'] = m.group(1)
                continue

            m = re.match('Node count: (\d+)', line)
            if m is not None:
                result['zk_znode_count'] = int(m.group(1))
                continue

        return result

    def _parse_line(self, line):
        try:
            key, value = map(str.strip, line.split('\t'))
        except ValueError:
            raise ValueError('Found invalid line: %s' % line)

        if not key:
            raise ValueError('The key is mandatory and should not be empty')

        try:
            value = int(value)
        except (TypeError, ValueError):
            pass

        return key, value

def metric_handler(name):
    if time.time() - ZK_LAST_METRICS['time'] > TIME_BETWEEN_QUERIES:
        zk = ZooKeeperServer(metric_handler.host, metric_handler.port, 5)
        try:
            metric_handler.info = zk.get_stats()
        except Exception, e:
            print >>sys.stderr, e
            metric_handler.info = {}

    return metric_handler.info.get(name, 0)

def metric_init(params=None):
    params = params or {}

    metric_handler.host = params.get('host', 'localhost')
    metric_handler.port = int(params.get('port', 2181))
    metric_handler.timestamp = 0

    metrics = {
        'zk_avg_latency': {'units': 'ms'},
        'zk_max_latency': {'units': 'ms'},
        'zk_min_latency': {'units': 'ms'},
        'zk_packets_received': {
            'units': 'pps',
            'value_type': 'float',
            'format': '%f'
        },
        'zk_packets_sent': {
            'units': 'pps',
            'value_type': 'double',
            'format': '%f'
        },
        'zk_outstanding_requests': {'units': 'connections'},
        'zk_znode_count': {'units': 'znodes'},
        'zk_watch_count': {'units': 'watches'},
        'zk_ephemerals_count': {'units': 'znodes'},
        'zk_approximate_data_size': {'units': 'bytes'},
        'zk_open_file_descriptor_count': {'units': 'descriptors'},
        'zk_max_file_descriptor_count': {'units': 'descriptors'},
        'zk_followers': {'units': 'nodes'},
        'zk_synced_followers': {'units': 'nodes'},
        'zk_pending_syncs': {'units': 'syncs'}
    }
    metric_handler.descriptors = {}
    for name, updates in metrics.iteritems():
        descriptor = {
            'name': name,
            'call_back': metric_handler,
            'time_max': 90,
            'value_type': 'int',
            'units': '',
            'slope': 'both',
            'format': '%d',
            'groups': 'zookeeper',
        }
        descriptor.update(updates)
        metric_handler.descriptors[name] = descriptor

    return metric_handler.descriptors.values()

def metric_cleanup():
    pass


if __name__ == '__main__':
    ds = metric_init({'host':'localhost', 'port': '2181'})
    while True:
        for d in ds:
            print "%s=%s" % (d['name'], metric_handler(d['name']))
        time.sleep(10)



########NEW FILE########
__FILENAME__ = test
#! /usr/bin/env python

import unittest
import socket
import sys

from StringIO import StringIO

from check_zookeeper import ZooKeeperServer, NagiosHandler, CactiHandler, GangliaHandler

ZK_MNTR_OUTPUT = """zk_version\t3.4.0--1, built on 06/19/2010 15:07 GMT
zk_avg_latency\t1
zk_max_latency\t132
zk_min_latency\t0
zk_packets_received\t640
zk_packets_sent\t639
zk_outstanding_requests\t0
zk_server_state\tfollower
zk_znode_count\t4
zk_watch_count\t0
zk_ephemerals_count\t0
zk_approximate_data_size\t27
zk_open_file_descriptor_count\t22
zk_max_file_descriptor_count\t1024
"""

ZK_MNTR_OUTPUT_WITH_BROKEN_LINES = """zk_version\t3.4.0
zk_avg_latency\t23
broken-line

"""

ZK_STAT_OUTPUT = """Zookeeper version: 3.3.0-943314, built on 05/11/2010 22:20 GMT
Clients:
 /0:0:0:0:0:0:0:1:34564[0](queued=0,recved=1,sent=0)

Latency min/avg/max: 0/40/121
Received: 11
Sent: 10
Outstanding: 0
Zxid: 0x700000003
Mode: follower
Node count: 4
"""

class SocketMock(object):
    def __init__(self):
        self.sent = []

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect(self, address):
        self.address = address

    def send(self, data):
        self.sent.append(data)
        return len(data)

    def recv(self, size):
        return ZK_MNTR_OUTPUT[:size]

    def close(self): pass

class ZK33xSocketMock(SocketMock):
    def __init__(self):
        SocketMock.__init__(self)
        self.got_stat_cmd = False

    def recv(self, size):
        if 'stat' in self.sent:
            return ZK_STAT_OUTPUT[:size]
        else:
            return ''

class UnableToConnectSocketMock(SocketMock):
    def connect(self, _):
        raise socket.error('[Errno 111] Connection refused')

def create_server_mock(socket_class):
    class ZooKeeperServerMock(ZooKeeperServer):
        def _create_socket(self):
            return socket_class()
    return ZooKeeperServerMock()

class TestCheckZookeeper(unittest.TestCase):

    def setUp(self):
        self.zk = ZooKeeperServer()
    
    def test_parse_valid_line(self):
        key, value = self.zk._parse_line('something\t5')

        self.assertEqual(key, 'something')
        self.assertEqual(value, 5)

    def test_parse_line_raises_exception_on_invalid_output(self):
        invalid_lines = ['something', '', 'a\tb\tc', '\t1']
        for line in invalid_lines:
            self.assertRaises(ValueError, self.zk._parse_line, line)

    def test_parser_on_valid_output(self):
        data = self.zk._parse(ZK_MNTR_OUTPUT)

        self.assertEqual(len(data), 14)
        self.assertEqual(data['zk_znode_count'], 4)
        
    def test_parse_should_ignore_invalid_lines(self):
        data = self.zk._parse(ZK_MNTR_OUTPUT_WITH_BROKEN_LINES)

        self.assertEqual(len(data), 2)

    def test_parse_stat_valid_output(self):
        data = self.zk._parse_stat(ZK_STAT_OUTPUT)

        result = {
            'zk_version' : '3.3.0-943314, built on 05/11/2010 22:20 GMT',
            'zk_min_latency' : 0,
            'zk_avg_latency' : 40,
            'zk_max_latency' : 121,
            'zk_packets_received': 11,
            'zk_packets_sent': 10,
            'zk_server_state': 'follower',
            'zk_znode_count': 4
        }
        for k, v in result.iteritems():
            self.assertEqual(v, data[k])

    def test_recv_valid_output(self):
        zk = create_server_mock(SocketMock)

        data = zk.get_stats()
        self.assertEqual(len(data), 14)
        self.assertEqual(data['zk_znode_count'], 4)

    def test_socket_unable_to_connect(self):
        zk = create_server_mock(UnableToConnectSocketMock)

        self.assertRaises(socket.error, zk.get_stats)

    def test_use_stat_cmd_if_mntr_is_not_available(self):
        zk = create_server_mock(ZK33xSocketMock)

        data = zk.get_stats()
        self.assertEqual(data['zk_version'], '3.3.0-943314, built on 05/11/2010 22:20 GMT')

class HandlerTestCase(unittest.TestCase):
    
    def setUp(self):
        try:
            sys._stdout
        except:
            sys._stdout = sys.stdout
        
        sys.stdout = StringIO()

    def tearDown(self):
        sys.stdout = sys._stdout

    def output(self):
        sys.stdout.seek(0)
        return sys.stdout.read()


class TestNagiosHandler(HandlerTestCase):

    def _analyze(self, w, c, k, stats):
        class Opts(object):
            warning = w
            critical = c
            key = k

        return NagiosHandler().analyze(Opts(), {'localhost:2181':stats})

    def test_ok_status(self):
        r = self._analyze(10, 20, 'a', {'a': 5})

        self.assertEqual(r, 0)
        self.assertEqual(self.output(), 'Ok "a"!|localhost:2181=5;10;20\n')

        r = self._analyze(20, 10, 'a', {'a': 30})
        self.assertEqual(r, 0)

    def test_warning_status(self):
        r = self._analyze(10, 20, 'a', {'a': 15})
        self.assertEqual(r, 1)
        self.assertEqual(self.output(), 
            'Warning "a" localhost:2181!|localhost:2181=15;10;20\n')

        r = self._analyze(20, 10, 'a', {'a': 15})
        self.assertEqual(r, 1)

    def test_critical_status(self):
        r = self._analyze(10, 20, 'a', {'a': 30})
        self.assertEqual(r, 2)
        self.assertEqual(self.output(),
            'Critical "a" localhost:2181!|localhost:2181=30;10;20\n')

        r = self._analyze(20, 10, 'a', {'a': 5})
        self.assertEqual(r, 2)

    def test_check_a_specific_key_on_all_hosts(self):
        class Opts(object):
            warning = 10
            critical = 20
            key = 'latency'

        r = NagiosHandler().analyze(Opts(), {
            's1:2181': {'latency': 5},
            's2:2181': {'latency': 15},
            's3:2181': {'latency': 35},
        })
        self.assertEqual(r, 2)
        self.assertEqual(self.output(), 
            'Critical "latency" s3:2181!|s1:2181=5;10;20 '\
            's3:2181=35;10;20 s2:2181=15;10;20\n')

class TestCactiHandler(HandlerTestCase):
    class Opts(object):
        key = 'a'
        leader = False

        def __init__(self, leader=False):
            self.leader = leader

    def test_output_values_for_all_hosts(self):
        r = CactiHandler().analyze(TestCactiHandler.Opts(), {
            's1:2181':{'a':1},
            's2:2181':{'a':2, 'b':3}
        })
        self.assertEqual(r, None)
        self.assertEqual(self.output(), 's1_2181:1 s2_2181:2')
    
    def test_output_single_value_for_leader(self):
        r = CactiHandler().analyze(TestCactiHandler.Opts(leader=True), {
            's1:2181': {'a':1, 'zk_server_state': 'leader'},
            's2:2181': {'a':2}
        })
        self.assertEqual(r, 0)
        self.assertEqual(self.output(), '1\n')


class TestGangliaHandler(unittest.TestCase):

    class TestableGangliaHandler(GangliaHandler):
        def __init__(self):
            GangliaHandler.__init__(self)
            self.cli_calls = []
    
        def call(self, cli):
            self.cli_calls.append(' '.join(cli))
            
    def test_send_single_metric(self):
        class Opts(object):
            @property
            def gmetric(self): return '/usr/bin/gmetric'
        opts = Opts()
        
        h = TestGangliaHandler.TestableGangliaHandler()
        h.analyze(opts, {'localhost:2181':{'latency':10}})

        cmd = "%s -n latency -v 10 -t uint32" % opts.gmetric
        assert cmd in h.cli_calls

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
