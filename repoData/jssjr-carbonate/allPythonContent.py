__FILENAME__ = aggregation
#!/usr/bin/env python

import logging
import os
import whisper

AGGREGATION = {
    'last': 'last',
    'g': 'last',

    'sum': 'sum',
    'c': 'sum',
    'C': 'sum',

    'average': None,  # set by graphite
    'ms': None,       # set by graphite
    'h': None,        # set by graphite
    'internal': None
}


def setAggregation(path, mode):

    if not mode:
        return 0

    if not os.path.exists(path):
        return 0

    try:
        whisper.setAggregationMethod(path, mode)
        return 1
    except whisper.WhisperException, exc:
        logging.warning("%s failed (%s)" % (path, str(exc)))

########NEW FILE########
__FILENAME__ = cli
import argparse
import errno
import fileinput
import logging
import os
import sys

from time import time

from .aggregation import setAggregation, AGGREGATION
from .fill import fill_archives
from .list import listMetrics
from .lookup import lookup
from .sieve import filterMetrics
from .sync import run_batch
from .util import local_addresses, common_parser

from .config import Config
from .cluster import Cluster


def carbon_hosts():
    parser = common_parser('Return the addresses for all nodes in a cluster')

    args = parser.parse_args()

    config = Config(args.config_file)
    cluster = Cluster(config, args.cluster)

    cluster_hosts = [d[0] for d in cluster.destinations]

    print "\n".join(cluster_hosts)


def carbon_list():
    parser = common_parser('List the metrics this carbon node contains')

    parser.add_argument(
        '-d', '--storage-dir',
        default='/opt/graphite/storage/whisper',
        help='Storage dir')

    args = parser.parse_args()

    try:
        for m in listMetrics(args.storage_dir):
            print m
    except IOError as e:
        if e.errno == errno.EPIPE:
            pass  # we got killed, lol
        else:
            raise SystemExit(e)
    except KeyboardInterrupt:
        sys.exit(1)


def carbon_lookup():
    parser = common_parser('Lookup where a metric lives in a carbon cluster')

    parser.add_argument(
        'metric', metavar='METRIC', nargs=1,
        type=str,
        help='Full metric name to search for')

    parser.add_argument(
        '-s', '--short',
        action='store_true',
        help='Only display the address, without port and cluster name')

    args = parser.parse_args()

    config = Config(args.config_file)
    cluster = Cluster(config, args.cluster)

    results = lookup(str(args.metric[0]), cluster)

    if args.short:
        for i, _ in enumerate(results):
            results[i] = results[i].split(':')[0]

    print "\n".join(results)


def carbon_sieve():
    parser = common_parser(
        'Given a list of metrics, output those that belong to a node')

    parser.add_argument(
        '-f', '--metrics-file',
        default='-',
        help='File containing metric names to filter, or \'-\' ' +
             'to read from STDIN')

    parser.add_argument(
        '-n', '--node',
        default="self",
        help='Filter for metrics belonging to this node')

    parser.add_argument(
        '-I', '--invert',
        action='store_true',
        help='Invert the sieve, match metrics that do NOT belong to a node')

    args = parser.parse_args()

    config = Config(args.config_file)
    cluster = Cluster(config, args.cluster)
    invert = args.invert

    if args.metrics_file and args.metrics_file[0] != '-':
        fi = args.metrics_file
    else:
        fi = []

    if args.node:
        match_dests = [args.node]
    else:
        match_dests = local_addresses()

    try:
        for metric in fileinput.input(fi):
            m = metric.strip()
            for match in filterMetrics([m], match_dests, cluster, invert):
                print metric.strip()
    except KeyboardInterrupt:
        sys.exit(1)


def carbon_sync():
    parser = common_parser(
        'Sync local metrics using remote nodes in the cluster'
        )

    parser.add_argument(
        '-f', '--metrics-file',
        default='-',
        help='File containing metric names to filter, or \'-\' ' +
             'to read from STDIN')

    parser.add_argument(
        '-s', '--source-node',
        required=True,
        help='Override the source for metrics data')

    parser.add_argument(
        '-d', '--storage-dir',
        default='/opt/graphite/storage/whisper',
        help='Storage dir')

    parser.add_argument(
        '-b', '--batch-size',
        default=1000,
        help='Batch size for the rsync job')

    parser.add_argument(
        '--source-storage-dir',
        default='/opt/graphite/storage/whisper',
        help='Source storage dir')

    parser.add_argument(
        '--rsync-options',
        default='-azpS',
        help='Pass option(s) to rsync. Make sure to use ' +
        '"--rsync-options=" if option starts with \'-\'')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.metrics_file and args.metrics_file[0] != '-':
        fi = args.metrics_file
    else:
        fi = []

    config = Config(args.config_file)

    user = config.ssh_user()
    remote_ip = args.source_node
    remote = "%s@%s:%s/" % (user, remote_ip, args.source_storage_dir)

    metrics_to_sync = []

    start = time()
    total_metrics = 0
    batch_size = int(args.batch_size)

    for metric in fileinput.input(fi):
        total_metrics += 1
        metric = metric.strip()
        mpath = metric.replace('.', '/') + "." + "wsp"

        metrics_to_sync.append(mpath)

        if total_metrics % batch_size == 0:
            print "* Running batch %s-%s" \
                  % (total_metrics-batch_size+1, total_metrics)
            run_batch(metrics_to_sync, remote,
                      args.storage_dir, args.rsync_options)
            metrics_to_sync = []

    if len(metrics_to_sync) > 0:
        print "* Running batch %s-%s" \
              % (total_metrics-len(metrics_to_sync)+1, total_metrics)
        run_batch(metrics_to_sync, remote,
                  args.storage_dir, args.rsync_options)

    elapsed = (time() - start)

    print ""
    print "* Sync Report"
    print "  ========================================"
    print "  Total metrics synced: %s" % total_metrics
    print "  Total time: %ss" % elapsed


def whisper_aggregate():
    parser = argparse.ArgumentParser(
        description='Set aggregation for whisper-backed metrics this carbon ' +
                    'instance contains',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        '-f', '--metrics-file',
        default='-',
        help='File containing metric names and aggregation modes, or \'-\' ' +
             'to read from STDIN')

    parser.add_argument(
        '-d', '--storage-dir',
        default='/opt/graphite/storage/whisper',
        help='Whisper storage directory')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.metrics_file and args.metrics_file[0] != '-':
        fi = args.metrics_file
        metrics = map(lambda s: s.strip(), fileinput.input(fi))
    else:
        metrics = map(lambda s: s.strip(), fileinput.input([]))

    metrics_count = 0

    for metric in metrics:
        name, t = metric.strip().split('|')

        mode = AGGREGATION[t]
        if mode is not None:
            cname = name.replace('.', '/')
            path = os.path.join(args.storage_dir, cname + '.wsp')
            metrics_count = metrics_count + setAggregation(path, mode)

    logging.info('Successfully set aggregation mode for ' +
                 '%d of %d metrics' % (metrics_count, len(metrics)))


def whisper_fill():
    parser = argparse.ArgumentParser(
        description='Backfill datapoints from one whisper file into another',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        'source',
        metavar='SRC',
        help='Whisper source file')

    parser.add_argument(
        'dest',
        metavar='DST',
        help='Whisper destination file')

    args = parser.parse_args()

    src = args.source
    dst = args.dest

    if not os.path.isfile(src):
        raise SystemExit('Source file not found.')

    if not os.path.isfile(dst):
        raise SystemExit('Destination file not found.')

    startFrom = time()

    fill_archives(src, dst, startFrom)

########NEW FILE########
__FILENAME__ = cluster
import sys

# Inject the graphite libs into the system path
sys.path.insert(0, '/opt/graphite/lib')

# We're going to use carbon's libs directly to do things
try:
    from carbon import util
    from carbon.routers import ConsistentHashingRouter
except ImportError as e:
    raise SystemExit("No bueno. Can't import carbon! (" + str(e) + ")")


class Cluster():
    def __init__(self, config, cluster='main'):
        self.ring = ConsistentHashingRouter(config.replication_factor(cluster))

        try:
            dest_list = config.destinations(cluster)
            self.destinations = util.parseDestinations(dest_list)
        except ValueError as e:
            raise SystemExit("Unable to parse destinations!" + str(e))

        for d in self.destinations:
            self.ring.addDestination(d)

    def getDestinations(self, metric):
        return self.ring.getDestinations(metric)

########NEW FILE########
__FILENAME__ = config
import os
import pwd
from ConfigParser import RawConfigParser, NoOptionError


class Config():

    """
    Load and access the carbonate configuration.
    """

    def __init__(self, config_file):
        self.config_file = config_file
        self.config = RawConfigParser()
        self.config.read(config_file)

    def clusters(self):
        """Return the clusters defined in the config file."""
        return self.config.sections()

    def destinations(self, cluster='main'):
        """Return a list of destinations for a cluster."""
        if not self.config.has_section(cluster):
            raise SystemExit("Cluster '%s' not defined in %s"
                             % (cluster, self.config_file))
        destinations = self.config.get(cluster, 'destinations')
        return destinations.replace(' ', '').split(',')

    def replication_factor(self, cluster='main'):
        """Return the replication factor for a cluster as an integer."""
        if not self.config.has_section(cluster):
            raise SystemExit("Cluster '%s' not defined in %s"
                             % (cluster, self.config_file))
        return int(self.config.get(cluster, 'replication_factor'))

    def ssh_user(self, cluster='main'):
        """Return the ssh user for a cluster or current user if undefined."""
        if not self.config.has_section(cluster):
            raise SystemExit("Cluster '%s' not defined in %s"
                             % (cluster, self.config_file))
        try:
            return self.config.get(cluster, 'ssh_user')
        except NoOptionError:
            return pwd.getpwuid(os.getuid()).pw_name

########NEW FILE########
__FILENAME__ = fill
# original work: https://github.com/graphite-project/whisper/issues/22

# whisper-fill: unlike whisper-merge, don't overwrite data that's
# already present in the target file, but instead, only add the missing
# data (e.g. where the gaps in the target file are).  Because no values
# are overwritten, no data or precision gets lost.  Also, unlike
# whisper-merge, try to take the highest-precision archive to provide
# the data, instead of the one with the largest retention.
# Using this script, reconciliation between two replica instances can be
# performed by whisper-fill-ing the data of the other replica with the
# data that exists locally, without introducing the quite remarkable
# gaps that whisper-merge leaves behind (filling a higher precision
# archive with data from a lower precision one)

# Work performed by author while working at Booking.com.

from whisper import info, fetch, update_many

try:
    from whisper import operator
    HAS_OPERATOR = True
except ImportError:
    HAS_OPERATOR = False

import itertools
import time


def itemgetter(*items):
    if HAS_OPERATOR:
        return operator.itemgetter(*items)
    else:
        if len(items) == 1:
            item = items[0]

            def g(obj):
                return obj[item]
        else:

            def g(obj):
                return tuple(obj[item] for item in items)
        return g


def fill(src, dst, tstart, tstop):
    # fetch range start-stop from src, taking values from the highest
    # precision archive, thus optionally requiring multiple fetch + merges
    srcHeader = info(src)

    srcArchives = srcHeader['archives']
    srcArchives.sort(key=itemgetter('retention'))

    # find oldest point in time, stored by both files
    srcTime = int(time.time()) - srcHeader['maxRetention']

    if tstart < srcTime and tstop < srcTime:
        return

    # we want to retain as much precision as we can, hence we do backwards
    # walk in time

    # skip forward at max 'step' points at a time
    for archive in srcArchives:
        # skip over archives that don't have any data points
        rtime = time.time() - archive['retention']
        if tstop <= rtime:
            continue

        untilTime = tstop
        fromTime = rtime if rtime > tstart else tstart

        (timeInfo, values) = fetch(src, fromTime, untilTime)
        (start, end, archive_step) = timeInfo
        pointsToWrite = list(itertools.ifilter(
            lambda points: points[1] is not None,
            itertools.izip(xrange(start, end, archive_step), values)))
        # order points by timestamp, newest first
        pointsToWrite.sort(key=lambda p: p[0], reverse=True)
        update_many(dst, pointsToWrite)

        tstop = fromTime

        # can stop when there's nothing to fetch any more
        if tstart == tstop:
            return


def fill_archives(src, dst, startFrom):
    header = info(dst)
    archives = header['archives']
    archives = sorted(archives, key=lambda t: t['retention'])

    for archive in archives:
        fromTime = time.time() - archive['retention']
        if fromTime >= startFrom:
            continue

        (timeInfo, values) = fetch(dst, fromTime, startFrom)
        (start, end, step) = timeInfo
        gapstart = None
        for v in values:
            if not v and not gapstart:
                gapstart = start
            elif v and gapstart:
                # ignore single units lost
                if (start - gapstart) > archive['secondsPerPoint']:
                    fill(src, dst, gapstart - step, start)
                gapstart = None
            elif gapstart and start == end - step:
                fill(src, dst, gapstart - step, start)

            start += step

        startFrom = fromTime

########NEW FILE########
__FILENAME__ = list
import os
import re


def listMetrics(storage_dir, metric_suffix='wsp'):
    metric_regex = re.compile(".*\.%s$" % metric_suffix)

    storage_dir = storage_dir.rstrip(os.sep)

    for root, dirnames, filenames in os.walk(storage_dir):
        for filename in filenames:
            if metric_regex.match(filename):
                root_path = root[len(storage_dir) + 1:]
                m_path = os.path.join(root_path, filename)
                m_name, m_ext = os.path.splitext(m_path)
                m_name = m_name.replace('/', '.')
                yield m_name

########NEW FILE########
__FILENAME__ = lookup
def lookup(metric, cluster):
    hosts = []
    metric_destinations = cluster.getDestinations(metric)
    for d in metric_destinations:
        hosts.append(':'.join(map(str, d)))
    return hosts

########NEW FILE########
__FILENAME__ = sieve
from functools import partial

map_long = partial(map, lambda m: ':'.join(map(str, m)))
map_short = partial(map, lambda m: m[0])


def filterMetrics(inputs, node, cluster, invert=False, filter_long=False):
    if isinstance(node, basestring):
        match = [node]
    else:
        match = node

    for metric_name in inputs:
        dests = list(cluster.getDestinations(metric_name))
        dests = set(map_long(dests)) | set(map_short(dests))

        if dests & set(match):
            if not invert:
                yield metric_name
        else:
            if invert:
                yield metric_name

########NEW FILE########
__FILENAME__ = sync
import os
import sys
import logging
import shutil
import subprocess
from time import time
from datetime import timedelta
from tempfile import mkdtemp, NamedTemporaryFile
from shutil import rmtree
from whisper import CorruptWhisperFile

from .fill import fill_archives


def sync_from_remote(sync_file, remote, staging, rsync_options):
    try:
        try:
            os.makedirs(os.path.dirname(staging))
        except OSError:
            pass

        cmd = " ".join(['rsync', rsync_options, '--files-from',
                        sync_file.name, remote, staging
                        ])

        print "  - Rsyncing metrics"

        proc = subprocess.Popen(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        for l in iter(proc.stdout.readline, b''):
            sys.stdout.write(l)
            sys.stdout.flush()
    except subprocess.CalledProcessError as e:
        logging.warn("Failed to sync from %s! %s" % (remote, e))


def sync_batch(metrics_to_heal):
    batch_start = time()
    sync_count = 0
    sync_total = len(metrics_to_heal)
    sync_avg = 0.1
    sync_remain = 'n/a'

    for (staging, local) in metrics_to_heal:
        sync_count += 1
        sync_start = time()
        sync_percent = float(sync_count) / sync_total * 100
        status_line = "  - Syncing %d of %d metrics. " \
                      "Avg: %fs  Time Left: %ss (%d%%)" \
                      % (sync_count, sync_total, sync_avg,
                         sync_remain, sync_percent)
        print status_line

        heal_metric(staging, local)

        sync_elapsed = time() - sync_start
        sync_avg = sync_elapsed / sync_count
        sync_remain_s = sync_avg * (sync_total - sync_count)
        sync_remain = str(timedelta(seconds=sync_remain_s))

    batch_elapsed = time() - batch_start
    return batch_elapsed


def heal_metric(source, dest):
    try:
        with open(dest):
            try:
                fill_archives(source, dest, time())
            except CorruptWhisperFile as e:
                logging.warn("Overwriting corrupt file %s!" % dest)
                try:
                    os.makedirs(os.path.dirname(dest))
                except os.error:
                    pass
                try:
                    shutil.copyfile(source, dest)
                except IOError as e:
                    logging.warn("Failed to copy %s! %s" % (dest, e))
    except IOError:
        try:
            os.makedirs(os.path.dirname(dest))
        except os.error:
            pass
        try:
            shutil.copyfile(source, dest)
        except IOError as e:
            logging.warn("Failed to copy %s! %s" % (dest, e))


def run_batch(metrics_to_sync, remote, local_storage, rsync_options):
    staging_dir = mkdtemp()
    sync_file = NamedTemporaryFile(delete=False)

    metrics_to_heal = []

    staging = "%s/" % (staging_dir)

    for metric in metrics_to_sync:
        staging_file = "%s/%s" % (staging_dir, metric)
        local_file = "%s/%s" % (local_storage, metric)
        metrics_to_heal.append((staging_file, local_file))

    sync_file.write("\n".join(metrics_to_sync))
    sync_file.flush()

    rsync_start = time()

    sync_from_remote(sync_file, remote, staging, rsync_options)

    rsync_elapsed = (time() - rsync_start)

    merge_elapsed = sync_batch(metrics_to_heal)

    total_time = rsync_elapsed + merge_elapsed

    print "    --------------------------------------"
    print "    Rsync time: %ss" % rsync_elapsed
    print "    Merge time: %ss" % merge_elapsed
    print "    Total time: %ss" % total_time

    # Cleanup
    rmtree(staging_dir)
    os.unlink(sync_file.name)

########NEW FILE########
__FILENAME__ = util
import socket
import argparse


def local_addresses():
    ips = socket.gethostbyname_ex(socket.gethostname())[2]
    return set([ip for ip in ips if not ip.startswith("127.")][:1])


def common_parser(description='untitled'):
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        '-c', '--config-file',
        default='/opt/graphite/conf/carbonate.conf',
        help='Config file to use')

    parser.add_argument(
        '-C', '--cluster',
        default='main',
        help='Cluster name')

    return parser

########NEW FILE########
__FILENAME__ = test_cluster
import unittest
from mock import Mock

from carbonate.cluster import Cluster


class ClusterTest(unittest.TestCase):

    def setUp(self):
        self.config = Mock()

    def test_parse_destinations(self):
        self.config.replication_factor = Mock(return_value=2)
        self.config.destinations = Mock(
            return_value=['192.168.9.13:2124:0', '192.168.9.15:2124:0',
                          '192.168.6.20:2124:0', '192.168.6.19:2124:0',
                          '192.168.6.16:2124:0']
            )

        self.cluster = Cluster(self.config)
        assert self.cluster.ring

    def test_failed_parse_destinations(self):
        self.config.replication_factor = Mock(return_value=2)
        self.config.destinations = Mock(
            return_value=['192.168.9.13:2124;0', '192.168.9.15:2124:0']
            )

        self.assertRaises(SystemExit, lambda: list(Cluster(self.config)))

########NEW FILE########
__FILENAME__ = test_config
import os
import pwd
import unittest

from carbonate import config


class ConfigTest(unittest.TestCase):

    simple_config = "tests/conf/simple.conf"
    real_config = "tests/conf/realistic.conf"

    def test_config_replication_factor(self):
        c = config.Config(self.simple_config)

        self.assertEqual(c.replication_factor(), 1)

    def test_config_destinations(self):
        c = config.Config(self.simple_config)

        expected = ['1.1.1.1:2003:0', '2.2.2.2:2003:0']
        self.assertEqual(c.destinations(), expected)

    def test_config_multiple_clusters(self):
        c = config.Config(self.real_config)

        expected = ['main', 'standalone']
        self.assertEqual(set(c.clusters()), set(expected))

    def test_config_ssh_user(self):
        c = config.Config(self.real_config)

        expected = 'carbonate'
        self.assertEqual(c.ssh_user('standalone'), expected)

    def test_config_ssh_user_default(self):
        c = config.Config(self.simple_config)

        expected = pwd.getpwuid(os.getuid()).pw_name
        self.assertEqual(c.ssh_user(), expected)

########NEW FILE########
__FILENAME__ = test_fill
import unittest
import os
import whisper
import time
import random

from carbonate.fill import fill_archives


class FillTest(unittest.TestCase):

    db = "db.wsp"

    @classmethod
    def setUpClass(cls):
        cls._removedb()

    @classmethod
    def _removedb(cls):
        try:
            if os.path.exists(cls.db):
                os.unlink(cls.db)
        except (IOError, OSError):
            pass


    def test_fill_empty(self):
        testdb = "test-%s" % self.db
        self._removedb()

        try:
            os.unlink(testdb)
        except (IOError, OSError):
            pass

        schema = [(1, 20)]
        emptyData = []
        startTime = time.time()
        self._createdb(self.db, schema)
        self._createdb(testdb, schema, emptyData)

        fill_archives(self.db, testdb, startTime)

        original_data = whisper.fetch(self.db, 0)
        filled_data = whisper.fetch(testdb, 0)
        self.assertEqual(original_data, filled_data)


    def test_fill_should_not_override_destination(self):
        testdb = "test-%s" % self.db
        self._removedb()

        try:
            os.unlink(testdb)
        except (IOError, OSError):
            pass

        schema = [(1, 20)]
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

        end = int(time.time()) + schema[0][0]
        start = end - (schema[0][1] * schema[0][0])
        times = range(start, end, schema[0][0])

        override_data = zip(times, data)

        emptyData = [data]
        startTime = time.time()
        self._createdb(self.db, schema)
        self._createdb(testdb, schema, override_data)

        fill_archives(self.db, testdb, startTime)

        original_data = whisper.fetch(self.db, 0)
        filled_data = whisper.fetch(testdb, 0)
        self.assertEqual(data, filled_data[1])


    def test_fill_should_handle_gaps(self):
        testdb = "test-%s" % self.db
        self._removedb()

        try:
            os.unlink(testdb)
        except (IOError, OSError):
            pass

        schema = [(1, 20)]
        complete = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                    11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        holes = [1, 2, 3, 4, 5, 6, None, None, None, None,
                 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

        end = int(time.time()) + schema[0][0]
        start = end - (schema[0][1] * schema[0][0])
        times = range(start, end, schema[0][0])

        complete_data = zip(times, complete)

        holes_data = [t for t in zip(times, holes) if t[1] is not None]
        self._createdb(self.db, schema, complete_data)
        self._createdb(testdb, schema, holes_data)

        fill_archives(self.db, testdb, time.time())

        original_data = whisper.fetch(self.db, 0)
        filled_data = whisper.fetch(testdb, 0)
        self.assertEqual(original_data, filled_data)


    def _createdb(self, wsp, schema=[(1, 20)], data=None):
        whisper.create(wsp, schema)
        if data is None:
            tn = time.time() - 20
            data = []
            for i in range(20):
                data.append((tn + 1 + i, random.random() * 10))
        whisper.update_many(wsp, data)
        return data

    @classmethod
    def tearDownClass(cls):
        try:
            cls._removedb()
            os.unlink("test-%s" % cls.db)
        except (IOError, OSError):
            pass

########NEW FILE########
__FILENAME__ = test_list
import os
import unittest

from carbonate.list import listMetrics


class ListTest(unittest.TestCase):

    metrics_tree = ["foo",
                    "foo/sprockets.wsp",
                    "foo/widgets.wsp",
                    "ham",
                    "ham/bones.wsp",
                    "ham/hocks.wsp"]

    expected_metrics = ["foo.sprockets",
                        "foo.widgets",
                        "ham.bones",
                        "ham.hocks"]

    rootdir = os.path.join(os.curdir, 'test_storage')

    @classmethod
    def setUpClass(cls):
        os.system("rm -rf %s" % cls.rootdir)
        os.mkdir(cls.rootdir)
        for f in cls.metrics_tree:
            if f.endswith('wsp'):
                open(os.path.join(cls.rootdir, f), 'w').close()
            else:
                os.mkdir(os.path.join(cls.rootdir, f))

    def test_list(self):
        res = sorted(list(listMetrics(self.rootdir)))
        self.assertEqual(res, self.expected_metrics)

    def test_list_with_trailing_slash(self):
        res = sorted(list(listMetrics(self.rootdir + '/')))
        self.assertEqual(res, self.expected_metrics)

    @classmethod
    def tearDownClass(cls):
        os.system("rm -rf %s" % cls.rootdir)

########NEW FILE########
__FILENAME__ = test_lookup
import unittest
from mock import Mock

from carbonate.cluster import Cluster
from carbonate.lookup import lookup


class LookupTest(unittest.TestCase):

    def setUp(self):
        self.config = Mock()

    def test_lookup(self):
        self.config.replication_factor = Mock(return_value=2)
        self.config.destinations = Mock(
            return_value=['192.168.9.13:2124:0', '192.168.9.15:2124:0',
                          '192.168.6.20:2124:0', '192.168.6.19:2124:0',
                          '192.168.6.16:2124:0']
            )

        self.cluster = Cluster(self.config)

        assert lookup('metric.one', self.cluster) == \
            ['192.168.6.16:2124:0', '192.168.6.19:2124:0']

########NEW FILE########
__FILENAME__ = test_sieve
import unittest
import carbonate.sieve


class FilterTest(unittest.TestCase):

    def setUp(self):
        config_file = "tests/conf/simple.conf"
        config = carbonate.config.Config(config_file)
        self.cluster = carbonate.cluster.Cluster(config)

    def test_sieve(self):
        inputs = ['metric.100',
                  'metric.101',
                  'metric.102',
                  'metric.103',
                  'metric.104',
                  'metric.105',
                  'metric.106',
                  'metric.107',
                  'metric.108',
                  'metric.109']

        node = '1.1.1.1'
        node_long = '1.1.1.1:2003:0'
        output = ['metric.101',
                  'metric.102',
                  'metric.103',
                  'metric.105',
                  'metric.107',
                  'metric.108']
        f = list(carbonate.sieve.filterMetrics(inputs, node, self.cluster))
        self.assertEqual(f, output)
        f = list(carbonate.sieve.filterMetrics(inputs, node_long, self.cluster))
        self.assertEqual(f, output)

        node = '2.2.2.2'
        node_long = '2.2.2.2:2003:0'
        output = ['metric.100',
                  'metric.104',
                  'metric.106',
                  'metric.109']
        f = list(carbonate.sieve.filterMetrics(inputs, node, self.cluster))
        self.assertEqual(f, output)
        f = list(carbonate.sieve.filterMetrics(inputs, node_long, self.cluster))
        self.assertEqual(f, output)

########NEW FILE########
