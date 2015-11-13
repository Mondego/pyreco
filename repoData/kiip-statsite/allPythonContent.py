__FILENAME__ = aggregator
"""
This module implements the aggregator which is
used to collect statistics over a given time interval,
aggregate and then submit to Graphite.
"""
import logging
import time
import metrics

class Aggregator(object):
    def __init__(self, metrics_store, metrics_settings={}):
        """
        An aggregator accumulates metrics via the :meth:`add_metrics()` call
        until :meth:`flush()` is called. Flushing will be initiated in a new
        thread by the caller. Once flush is called, :meth:`add_metrics()` is
        guaranteed to never be called again. :meth:`flush()` is expected to
        send the aggregated metrics to the metrics store.

        Aggregators currently do not need to be thread safe. Only a single
        thread will call :meth:`add_metric()` at any given time.

        :Parameters:
            - `metrics_store`: The metrics storage instance to flush to.
        """
        self.metrics_store = metrics_store
        self.metrics_settings = self._load_metric_settings(metrics_settings)

    def add_metrics(self, metrics):
        """
        Add a collection of metrics to be aggregated in the next flushing
        period.
        """
        raise NotImplementedError()

    def flush(self):
        """
        This method will be called to run in a specific thread. It is responsible
        for flushing the collected metrics to the metrics store.
        """
        raise NotImplementedError()

    def _load_metric_settings(self, settings):
        """
        This method takes a list of settings set by the Statsite program,
        in the format of a dictionary keyed by the shorthand for the metric,
        example:

            { "ms": { "percentile": 80 } }

        And it turns it into a fast lookup based on the class that that
        setting actually represents:

            { Timer: { "percentile": 80 } }

        This format is much more efficient for ``_fold_metrics``.
        """
        result = {}
        for metric_type,metric_settings in settings.iteritems():
            result[metrics.METRIC_TYPES[metric_type]] = metric_settings

        return result

    def _fold_metrics(self, metrics):
        """
        This method will go over an array of metric objects and fold them into
        a list of data.
        """
        # Store the metrics as a dictionary by queue type
        metrics_by_type = {}
        for metric in metrics:
            key = type(metric)
            metrics_by_type.setdefault(key, [])
            metrics_by_type[key].append(metric)

        # Fold over the metrics
        data = []
        now = time.time()
        for cls,metrics in metrics_by_type.iteritems():
            data.extend(cls.fold(metrics, now, **self.metrics_settings.get(cls, {})))

        return data

class DefaultAggregator(Aggregator):
    def __init__(self, *args, **kwargs):
        super(DefaultAggregator, self).__init__(*args, **kwargs)

        self.metrics_queue = []
        self.logger = logging.getLogger("statsite.aggregator.default")

    def add_metrics(self, metrics):
        self.metrics_queue.extend(metrics)

    def flush(self):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("Aggregating data...")

            for metric in self.metrics_queue:
                self.logger.debug("Metric: %s" % repr(metric))

        try:
            data = self._fold_metrics(self.metrics_queue)
        except:
            self.logger.exception("Failed to fold metrics data")

        try:
            if data:
                self.metrics_store.flush(data)
        except:
            self.logger.exception("Failed to flush data")

        self.logger.debug("Aggregation complete.")

########NEW FILE########
__FILENAME__ = aliveness
"""
Contains classes which handle the TCP aliveness check.
"""

import logging
import SocketServer

LOGGER = logging.getLogger("statsite.aliveness")

class AlivenessHandler(SocketServer.BaseRequestHandler):
    """
    This is the TCP handler which responds to any aliveness checks
    to Statsite. This handler simply responds to every packet received
    with the contents of "YES" (all caps). This is so that in the future
    if smarter checks are done, "NO" could possibly respond as well.
    """

    def handle(self):
        LOGGER.debug("Aliveness check from: %s" % self.client_address[0])
        self.request.send("YES")

########NEW FILE########
__FILENAME__ = statsite
#!/usr/bin/env python
"""statsite

.. program:: statsite

"""

import logging
import logging.handlers
import signal
import sys
import threading
import ConfigParser
from optparse import OptionParser
from ..statsite import Statsite

class StatsiteCommandError(Exception):
    """
    This is the exception that will be raised if something goes wrong
    executing the Statsite command.
    """
    pass

class StatsiteCommand(object):
    TOPLEVEL_CONFIG_SECTION = "statsite"
    """
    This is the section to use in the configuration file if you wish to
    modify the top-level configuration.
    """

    def __init__(self, args=None):
        # Define and parse the command line options
        parser = OptionParser()
        parser.add_option("-c", "--config", action="append", dest="config_files",
                          default=[], help="path to a configuration file")
        parser.add_option("-l", "--log-level", action="store", dest="log_level",
                          default=None, help="log level")
        parser.add_option("-s", "--setting", action="append", dest="settings",
                          default=[], help="set a setting, e.g. collector.host=0.0.0.0")
        (self.options, _) = parser.parse_args(args)

        # Defaults
        self.statsite = None

        # Parse the settings from file, and then from the command line,
        # since the command line trumps any file-based settings
        self.settings = {}
        if len(self.options.config_files) > 0:
            self._parse_settings_from_file(self.options.config_files)

        self._parse_settings_from_options()

        # Setup the logger
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(lineno)s %(message)s"))

        logger = logging.getLogger("statsite")
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, self.settings["log_level"].upper()))

    def start(self):
        """
        Runs the statiste application.
        """
        signal.signal(signal.SIGINT, self._on_sigint)
        self.statsite = Statsite(self.settings)

        # Run Statsite in a separate thread so that signal handlers can
        # properly shut it down.
        thread = threading.Thread(target=self.statsite.start)
        thread.daemon = True
        thread.start()

        # Apparently `thread.join` blocks the main thread and makes it
        # _uninterruptable_, so we need to do this loop so that the main
        # thread can respond to signal handlers.
        while thread.isAlive():
            thread.join(0.2)

    def _on_sigint(self, signal, frame):
        """
        Called when a SIGINT is sent to cleanly shutdown the statsite server.
        """
        if self.statsite:
            self.statsite.shutdown()

    def _parse_settings_from_file(self, paths):
        """
        Parses settings from a configuration file.
        """
        config = ConfigParser.RawConfigParser()
        if config.read(paths) != paths:
            raise StatsiteCommandError, "Failed to parse configuration files."

        for section in config.sections():
            settings_section = section if section != self.TOPLEVEL_CONFIG_SECTION else None
            for (key, value) in config.items(section):
                self._add_setting(settings_section, key, value)

    def _parse_settings_from_options(self):
        """
        Parses settings from the command line options.
        """
        # Set the log level up
        self.settings.setdefault("log_level", "info")
        if self.options.log_level:
            self.settings["log_level"] = self.options.log_level

        # Set the generic options
        for setting in self.options.settings:
            key, value = setting.split("=", 2)
            section, key = key.split(".", 2)
            self._add_setting(section, key, value)

    def _add_setting(self, section, key, value):
        """
        Adds settings to a specific section.
        """
        if section is None:
            # If section is 'None' then we put the key/value
            # in the top-level settings
            current = self.settings
        else:
            # Otherwise we put it in the proper section...
            self.settings.setdefault(section, {})

            # Split the key by "." characters and make sure
            # that each character nests the dictionary further
            current = self.settings[section]
            parts = key.split(".")
            for part in parts[:-1]:
                current.setdefault(part, {})
                current = current[part]

            # The key is now the last of the dot-separated parts
            key = parts[-1]

        # Finally set the value onto the settings
        current[key] = value

def main():
    "The main entrypoint for the statsite command line program."
    try:
        command = StatsiteCommand()
        command.start()
    except StatsiteCommandError, e:
        sys.stderr.write("Error: %s\n" % e.message)
        sys.exit(1)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = collector
"""
Contains the base class for collectors as well as the built-in UDP
collector.
"""

import logging
import socket
import SocketServer

import metrics
import parser

class Collector(object):
    """
    Collectors should inherit from this class, which provides the
    necessary interface and helpers for implementing a collector.
    """

    def __init__(self, aggregator):
        """
        Initializes a collector. Subclasses can override this with custom
        parameters if they want, but they _must_ call the superclass
        init method.
        """
        self.logger = logging.getLogger("statsite.collector")
        self.aggregator = aggregator

    def start(self):
        """
        This method must be implemented by collectors, and is called
        when the collector should be started. This method should block
        forever while the collector runs.
        """
        raise NotImplementedError("run must be implemented")

    def shutdown(self):
        """
        This method will be called by a second thread to notify the
        collector to shutdown, which it should immediately and gracefully.
        """
        raise NotImplementedError("shutdown must be implemented")

    def set_aggregator(self, aggregator):
        """
        This method may be periodically called to change the aggregator
        underneath the collector object.
        """
        self.aggregator = aggregator

    def _parse_metrics(self, message):
        """
        Given a raw message of metrics split by newline characters, this will
        parse the metrics and return an array of metric objects.

        This will raise a :exc:`ValueError` if any metrics are invalid, unless
        ``ignore_errors`` is set to True.
        """
        results = []
        for line in message.split("\n"):
            # If the line is blank, we ignore it
            if len(line) == 0: continue

            # Parse the line, and skip it if its invalid
            try:
                (key, value, metric_type, flag) = parser.parse_line(line)
            except ValueError:
                self.logger.error("Invalid line syntax: %s" % line)
                continue

            # Create the metric and store it in our results
            if metric_type in metrics.METRIC_TYPES:
                # Create and store the metric object
                metric = metrics.METRIC_TYPES[metric_type](key, value, flag)
                results.append(metric)
            else:
                # Ignore the bad invalid metric, but log it
                self.logger.error("Invalid metric '%s' in line: %s" % (metric_type, line))

        return results

    def _add_metrics(self, metrics):
        """
        Adds the given array of metrics to the aggregator.
        """
        self.aggregator.add_metrics(metrics)

class UDPCollector(Collector):
    """
    This is a collector which listens for UDP packets, parses them,
    and adds them to the aggregator.
    """

    def __init__(self, host="0.0.0.0", port=8125, **kwargs):
        super(UDPCollector, self).__init__(**kwargs)

        self.server = UDPCollectorSocketServer((host, int(port)),
                                               UDPCollectorSocketHandler,
                                               collector=self)
        self.logger = logging.getLogger("statsite.udpcollector")

    def start(self):
        # Run the main server forever, blocking this thread
        self.logger.debug("UDPCollector starting")
        self.server.serve_forever()

    def shutdown(self):
        # Tell the main server to stop
        self.logger.debug("UDPCollector shutting down")
        self.server.shutdown()

class UDPCollectorSocketServer(SocketServer.UDPServer):
    """
    The SocketServer implementation for the UDP collector.
    """

    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        self.collector = kwargs["collector"]
        del kwargs["collector"]
        SocketServer.UDPServer.__init__(self, *args, **kwargs)
        self._setup_socket_buffers()

    def _setup_socket_buffers(self):
        "Increases the receive buffer sizes"
        # Try to set the buffer size to 4M, 2M, 1M, and 512K
        for buff_size in (4*1024**2,2*1024**2,1024**2,512*1024):
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buff_size)
                return
            except:
                pass

class UDPCollectorSocketHandler(SocketServer.BaseRequestHandler):
    """
    Simple handler that receives UDP packets, parses them, and adds
    them to the aggregator.
    """

    def handle(self):
        try:
            # Get the message
            message, _ = self.request

            # Add the parsed metrics to the aggregator
            metrics = self.server.collector._parse_metrics(message)
            self.server.collector._add_metrics(metrics)
        except Exception:
            self.server.collector.logger.exception("Exception during processing UDP packet")


class TCPCollector(Collector):
    """
    This is a collector which listens for TCP connections,
    spawns a thread for each one, parses incoming metrics,
    and adds them to the aggregator.
    """

    def __init__(self, host="0.0.0.0", port=8125, **kwargs):
        super(TCPCollector, self).__init__(**kwargs)

        self.server = TCPCollectorSocketServer((host, int(port)),
                                               TCPCollectorSocketHandler,
                                               collector=self)
        self.logger = logging.getLogger("statsite.tcpcollector")

    def start(self):
        # Run the main server forever, blocking this thread
        self.logger.debug("TCPCollector starting")
        self.server.serve_forever()

    def shutdown(self):
        # Tell the main server to stop
        self.logger.debug("TCPCollector shutting down")
        self.server.shutdown()


class TCPCollectorSocketServer(SocketServer.ThreadingTCPServer):
    """
    The SocketServer implementation for the UDP collector.
    """
    allow_reuse_address = True
    request_queue_size = 50 # Allow more waiting connections
    daemon_threads = True # Gracefully exit if our request handler threads are around
    timeout = 10          # Use a default timeout for connections

    def __init__(self, *args, **kwargs):
        self.collector = kwargs["collector"]
        del kwargs["collector"]
        SocketServer.TCPServer.__init__(self, *args, **kwargs)
        self._setup_socket_buffers()

    def _setup_socket_buffers(self):
        "Increases the receive buffer sizes"
        # Try to set the buffer size to 4M, 2M, 1M, and 512K
        for buff_size in (4*1024**2,2*1024**2,1024**2,512*1024):
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buff_size)
                return
            except:
                pass


class TCPCollectorSocketHandler(SocketServer.StreamRequestHandler):
    """
    Simple handler that receives TCP connections, parses them, and adds
    them to the aggregator.
    """
    daemon_threads = True # Gracefully exit if our request handler threads are around
    timeout = 10          # Use a default timeout for connections

    def handle(self):
        while True:
            try:
                # Read a line of input
                line = self.rfile.readline()
                if not line: break

                # Add the parsed metrics to the aggregator
                metrics = self.server.collector._parse_metrics(line)
                self.server.collector._add_metrics(metrics)
            except Exception:
                self.server.collector.logger.exception("Exception during processing TCP connection")
                break


########NEW FILE########
__FILENAME__ = metrics
"""
The module implements the Metric class and its
sub-classes. These are used to wrap the values in the
incoming messages, and contain them in classes of
the proper type.
"""
import math
import time

class Metric(object):
    def __init__(self, key, value, flag=None):
        """
        Represents a base metric. This is not used directly,
        and is instead invoked from sub-classes that are typed
        by the metric.

        Each sub-class must implement a class method :meth:`fold()`
        which takes a list of objects of the same type and returns a list
        of (key,value,timestamp) pairs.

        :Parameters:
            - `key` : The key of the metric
            - `value` : The metric value
            - `flag` (optional) : An optional metric flag. This is specific
            to the flag and has no inherint meaning. For example the Counter
            metric uses this to indicate a sampling rate.
        """
        self.key = key
        self.value = value
        self.flag = flag

    @classmethod
    def fold(cls, lst, now):
        """
        Takes a list of the metrics objects and emits lists of (key,value,timestamp)
        pairs.

        :Parameters:
            - `lst` : A list of metrics objects
            - `now` : The time at which folding started
        """
        return [(o.key,o.value,o.flag if o.flag else now) for o in lst]

    def __eq__(self, other):
        """
        Equality check for metrics. This does a basic check to make sure
        key, value, and flag are equivalent.
        """
        return isinstance(other, Metric) and \
            self.key == other.key and \
            self.value == other.value and \
            self.flag == other.flag

class Counter(Metric):
    """
    Represents counter metrics, provided by 'c' type.
    """
    @classmethod
    def fold(cls, lst, now):
        accumulator = {}
        for item in lst: item._fold(accumulator)
        return [("counts.%s" % key,value,now) for key,value in accumulator.iteritems()]

    def _fold(self, accum):
        accum.setdefault(self.key, 0)
        sample_rate = self.flag if self.flag else 1.0
        accum[self.key] += self.value / (1 / sample_rate)


class Timer(Metric):
    """
    Represents timing metrics, provided by the 'ms' type.
    """
    @classmethod
    def fold(cls, lst, now, percentile=90):
        accumulator = {}
        for item in lst: item._fold(accumulator)

        outputs = []
        for key,vals in accumulator.iteritems():
            # Sort the values
            vals.sort()

            val_count = len(vals)
            val_sum = sum(vals)
            val_avg = float(val_sum) / val_count
            val_min = vals[0]
            val_max = vals[-1]
            val_stdev = cls._stdev(vals, val_avg)

            # Calculate the inner percentile
            inner_indexes = int(len(vals) * (percentile / 100.0))
            lower_idx = (len(vals) - inner_indexes) / 2
            upper_idx = lower_idx + inner_indexes

            # If we only have one item, then the percentile is just the
            # values itself, otherwise the lower_idx:upper_idx slice returns
            # an empty list.
            if len(vals) == 1:
                vals_pct = vals
            else:
                vals_pct = vals[lower_idx:upper_idx]

            val_sum_pct = sum(vals_pct)
            val_avg_pct = val_sum_pct / inner_indexes if inner_indexes > 0 else val_sum_pct
            val_min_pct = vals[lower_idx]
            val_max_pct = vals[upper_idx]
            val_stdev_pct = cls._stdev(vals_pct, val_avg_pct)

            outputs.append(("timers.%s.sum" % key, val_sum, now))
            outputs.append(("timers.%s.mean" % key, val_avg, now))
            outputs.append(("timers.%s.lower" % key, val_min, now))
            outputs.append(("timers.%s.upper" % key, val_max, now))
            outputs.append(("timers.%s.count" % key, val_count, now))
            outputs.append(("timers.%s.stdev" % key, val_stdev, now))

            outputs.append(("timers.%s.sum_%d" % (key, percentile), val_sum_pct, now))
            outputs.append(("timers.%s.mean_%d" % (key, percentile), val_avg_pct, now))
            outputs.append(("timers.%s.lower_%d" % (key, percentile), val_min_pct, now))
            outputs.append(("timers.%s.upper_%d" % (key, percentile), val_max_pct, now))
            outputs.append(("timers.%s.count_%d" % (key, percentile), inner_indexes, now))
            outputs.append(("timers.%s.stdev_%d" % (key, percentile), val_stdev_pct, now))

        return outputs

    @classmethod
    def _stdev(cls, lst, lst_avg):
        # Sample size is N-1
        sample_size = float(len(lst) - 1)
        if sample_size == 0 : return 0

        # Calculate the sum of the difference from the
        # mean squared
        diff_sq = sum([(v-lst_avg)**2 for v in lst])

        # Take the sqrt of the ratio, that is the stdev
        return math.sqrt(diff_sq / sample_size)

    def _fold(self, accum):
        accum.setdefault(self.key, [])
        accum[self.key].append(self.value)

class KeyValue(Metric):
    """
    Represents a key/value metric, provided by the 'kv' type.
    """
    def __init__(self,key, value, flag=None):
        super(KeyValue, self).__init__(key,value,flag)

        # Set the flag to the current time if not set
        if flag is None: self.flag = time.time()

    @classmethod
    def fold(cls, lst, now):
        """
        Takes a list of the metrics objects and emits lists of (key,value,timestamp)
        pairs. Adds the kv prefix to all the keys so as not to pollute the main namespace.
        """
        return [("kv.%s" % o.key,o.value,o.flag if o.flag else now) for o in lst]


METRIC_TYPES = {
    "c": Counter,
    "ms": Timer,
    "kv": KeyValue,
}
"""
This dictionary maps the metric type short names
which are specified in the incoming messages to a
class which implements that Metric type. If a short
code is not in this dictionary it is not supported.
"""


########NEW FILE########
__FILENAME__ = metrics_store
"""
Contains the base metrics store class and default metrics store class.
"""

import socket
import threading
import logging

class MetricsStore(object):
    """
    This is the base class for all metric stores. There is only one
    main method that metric stores must implement: :meth:`flush()`
    which is called from time to time to flush data out to the
    backing store.

    Metrics stores _must_ be threadsafe, since :meth:`flush()` could
    potentially be called by multiple flushing aggregators.
    """

    def flush(self, metrics):
        """
        This method is called by aggregators when flushing data.
        This must be thread-safe.
        """
        raise NotImplementedError("flush not implemented")

class GraphiteStore(MetricsStore):
    def __init__(self, host="localhost", port=2003, prefix="statsite", attempts=3):
        """
        Implements a metrics store interface that allows metrics to
        be persisted to Graphite. Raises a :class:`ValueError` on bad arguments.

        :Parameters:
            - `host` : The hostname of the graphite server.
            - `port` : The port of the graphite server
            - `prefix` (optional) : A prefix to add to the keys. Defaults to 'statsite'
            - `attempts` (optional) : The number of re-connect retries before failing.
        """
        # Convert the port to an int since its coming from a configuration file
        port = int(port)

        if port <= 0: raise ValueError, "Port must be positive!"
        if attempts <= 1: raise ValueError, "Must have at least 1 attempt!"

        self.host = host
        self.port = port
        self.prefix = prefix
        self.attempts = attempts
        self.sock_lock = threading.Lock()
        self.sock = self._create_socket()
        self.logger = logging.getLogger("statsite.graphitestore")

    def flush(self, metrics):
        """
        Flushes the metrics provided to Graphite.

       :Parameters:
        - `metrics` : A list of (key,value,timestamp) tuples.
        """
        # Construct the output
        data = "\n".join(["%s.%s %s %d" % (self.prefix,k,v,ts) for k,v,ts in metrics]) + "\n"

        # Serialize writes to the socket
        self.sock_lock.acquire()
        try:
            self._write_metric(data)
        except:
            self.logger.exception("Failed to write out the metrics!")
        finally:
            self.sock_lock.release()

    def close(self):
        """
        Closes the connection. The socket will be recreated on the next
        flush.
        """
        self.sock.close()

    def _create_socket(self):
        """Creates a socket and connects to the graphite server"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host,self.port))
        return sock

    def _write_metric(self, metric):
        """Tries to write a string to the socket, reconnecting on any errors"""
        for attempt in xrange(self.attempts):
            try:
                self.sock.sendall(metric)
                return
            except socket.error:
                self.logger.exception("Error while flushing to graphite. Reattempting...")
                self.sock = self._create_socket()

        self.logger.critical("Failed to flush to Graphite! Gave up after %d attempts." % self.attempts)

########NEW FILE########
__FILENAME__ = parser
"""
This module implements simple utility functions for
parsing incoming messages.
"""
import re

LINE_REGEX = re.compile("^([a-zA-Z0-9-_.]+):(-?[0-9.]+)\|([a-z]+)(?:\|@([0-9.]+))?$")
"""
Simple Regex used to match stats lines inside incoming messages.
"""

def parse_line(line):
    """
    Utility function to parse an incoming line in a message.

    Raises :exc:`ValueError` if the line is invalid or the
    message type if not valid.

    Returns a :class:`Metric` object of the proper subclass.
    """
    match = LINE_REGEX.match(line)
    if match is None:
        raise ValueError, "Invalid line: '%s'" % line

    key, value, metric_type, flag = match.groups()

    # Do type conversion to either float or int
    value = float(value) if "." in value else int(value)
    if flag is not None:
        flag = float(flag) if "." in flag else int(flag)

    # Return the metric object
    return (key, value, metric_type, flag)


########NEW FILE########
__FILENAME__ = statsite
"""
Contains the main Statsite class which is what should be instantiated
for running a server.
"""
import logging
import pprint
import SocketServer
import threading

from . import __version__
from aggregator import DefaultAggregator
from aliveness import AlivenessHandler
from collector import UDPCollector
from metrics_store import GraphiteStore
from util import deep_merge, resolve_class_string

BANNER = """
Statsite v%(version)s

[components]
  . collector: %(collector_cls)s
  . aggregator: %(aggregator_cls)s
  . store:      %(store_cls)s

[configuration]
%(configuration)s
"""

class Statsite(object):
    """
    Statsite is the main entrypoint class for instantiating, configuring,
    and running a Statsite server.
    """

    DEFAULT_SETTINGS = {
        "flush_interval": 10,
        "aggregator": {
            "class": "aggregator.DefaultAggregator"
        },
        "aliveness_check": {
            "enabled": False,
            "host": "0.0.0.0",
            "port": 8325
        },
        "collector": {
            "class": "collector.UDPCollector"
        },
        "store": {
            "class": "metrics_store.GraphiteStore"
        },
        "metrics": {}
    }

    def __init__(self, settings={}):
        """
        Initializes a new Statsite server instance. All configuration
        must be done during instantiate. If configuration changes in the
        future, a new statsite class must be created.
        """
        super(Statsite, self).__init__()

        # Deep merge the default settings with the given settings
        self.settings = deep_merge(self.DEFAULT_SETTINGS, settings)

        # Resolve the classes for each component
        for component in ["aggregator", "collector", "store"]:
            key   = "_%s_cls" % component
            value = resolve_class_string(self.settings[component]["class"])

            # Delete the class from the settings, since the settings are also
            # used for initialization, and components don't expect "class"
            # kwarg.
            del self.settings[component]["class"]

            # Set the attribute on ourself for use everywhere else
            setattr(self, key, value)

        # Setup the logger
        self.logger = logging.getLogger("statsite.statsite")
        self.logger.info(BANNER % {
                "version": __version__,
                "collector_cls": self._collector_cls,
                "aggregator_cls": self._aggregator_cls,
                "store_cls": self._store_cls,
                "configuration": pprint.pformat(self.settings, width=60, indent=2)
        })

        # Setup the store
        self.logger.debug("Initializing metrics store: %s" % self._store_cls)
        self.store = self._store_cls(**self.settings["store"])

        # Setup the aggregator, provide the store
        self.settings["aggregator"]["metrics_store"] = self.store
        self.logger.debug("Initializing aggregator: %s" % self._aggregator_cls)
        self.aggregator = self._create_aggregator()

        # Setup the collector, provide the aggregator
        self.settings["collector"]["aggregator"] = self.aggregator
        self.logger.debug("Initializing collector: %s" % self._collector_cls)
        self.collector = self._collector_cls(**self.settings["collector"])

        # Setup defaults
        self.aliveness_check = None
        self.timer = None

    def start(self):
        """
        This starts the actual statsite server. This will run in a
        separate thread and return immediately.
        """
        self.logger.info("Statsite starting")
        self._reset_timer()

        if self.settings["aliveness_check"]["enabled"]:
            self._enable_aliveness_check()

        self.collector.start()

    def shutdown(self):
        """
        This shuts down the server by gracefully exiting the flusher,
        aggregator, and collector. Exact behavior of "gracefully" exit
        is up to the various components used, but by default this
        will throw away any data received during the current flush
        period, rather than immediately flushing it, since this can cause
        inaccurate statistics.
        """
        self.logger.info("Statsite shutting down")
        if self.timer:
            self.timer.cancel()

        self._disable_aliveness_check()
        self.collector.shutdown()

    def _enable_aliveness_check(self):
        """
        This enables the TCP aliveness check, which is useful for tools
        such as Monit, Nagios, etc. to verify that Statsite is still
        alive.
        """
        if self.aliveness_check:
            self.aliveness_check.shutdown()

        self.logger.debug("Aliveness check starting")

        # Settings
        host = self.settings["aliveness_check"]["host"]
        port = int(self.settings["aliveness_check"]["port"])

        # Create the server
        self.aliveness_check = SocketServer.TCPServer((host, port), AlivenessHandler)

        # Run the aliveness check in a thread
        thread = threading.Thread(target=self.aliveness_check.serve_forever)
        thread.daemon = True
        thread.start()

    def _disable_aliveness_check(self):
        """
        This shuts down the TCP aliveness check.
        """
        self.logger.debug("Aliveness check stopping")
        if self.aliveness_check:
            self.aliveness_check.shutdown()
            self.aliveness_check = None

    def _on_timer(self):
        """
        This is the callback called every flush interval, and is responsible
        for initiating the aggregator flush.
        """
        self._reset_timer()
        self._flush_and_switch_aggregator()

    def _flush_and_switch_aggregator(self):
        """
        This is called periodically to flush the aggregator and switch
        the collector to a new aggregator.
        """
        self.logger.debug("Flushing and switching aggregator...")

        # Create a new aggregator and tell the collection to begin using
        # it immediately.
        old_aggregator = self.aggregator
        self.aggregator = self._create_aggregator()
        self.collector.set_aggregator(self.aggregator)

        # Flush the old aggregator in it's own thread
        thread = threading.Thread(target=old_aggregator.flush)
        thread.daemon = True
        thread.start()

    def _create_aggregator(self):
        """
        Returns a new aggregator with the settings given at initialization.
        """
        return self._aggregator_cls(metrics_settings=self.settings["metrics"], **self.settings["aggregator"])

    def _reset_timer(self):
        """
        Resets the flush timer.
        """
        if self.timer:
            self.timer.cancel()

        self.timer = threading.Timer(int(self.settings["flush_interval"]), self._on_timer)
        self.timer.start()

########NEW FILE########
__FILENAME__ = util
"""
Contains utility functions.
"""

import collections
import copy

def quacks_like_dict(object):
    """Check if object is dict-like"""
    return isinstance(object, collections.Mapping)

def deep_merge(a, b):
    """Merge two deep dicts non-destructively

    Uses a stack to avoid maximum recursion depth exceptions

    >>> a = {'a': 1, 'b': {1: 1, 2: 2}, 'd': 6}
    >>> b = {'c': 3, 'b': {2: 7}, 'd': {'z': [1, 2, 3]}}
    >>> c = merge(a, b)
    >>> from pprint import pprint; pprint(c)
    {'a': 1, 'b': {1: 1, 2: 7}, 'c': 3, 'd': {'z': [1, 2, 3]}}
    """
    assert quacks_like_dict(a), quacks_like_dict(b)
    dst = copy.deepcopy(a)

    stack = [(dst, b)]
    while stack:
        current_dst, current_src = stack.pop()
        for key in current_src:
            if key not in current_dst:
                current_dst[key] = current_src[key]
            else:
                if quacks_like_dict(current_src[key]) and quacks_like_dict(current_dst[key]) :
                    stack.append((current_dst[key], current_src[key]))
                else:
                    current_dst[key] = current_src[key]
    return dst

def resolve_class_string(full_string):
    """
    Given a string such as "foo.bar.Baz" this will properly
    import the "Baz" class from the "foo.bar" module.
    """
    module_string, _, cls_string = full_string.rpartition(".")
    if module_string == "":
        raise ValueError, "Must specify a module for class: %s" % full_string
    elif cls_string == "":
        raise ValueError, "Must specify a class for module: %s" % full_string

    module = __import__(module_string, globals(), locals(), [cls_string], -1)
    if not hasattr(module, cls_string):
        raise ImportError, "Class not found in module: %s" % full_string

    return getattr(module, cls_string)

########NEW FILE########
__FILENAME__ = base
"""
Contains the basic classes for test classes.
"""

import errno
import random
import socket
import tempfile
import time
import threading

from statsite.statsite import Statsite

from graphite import GraphiteServer, GraphiteHandler
from helpers import DumbAggregator, DumbMetricsStore

class TestBase(object):
    """
    This is the base class for unit tests of statsite.
    """

    DEFAULT_INTERVAL = 1
    "The default flush interval for Statsite servers."

    def pytest_funcarg__aggregator(self, request):
        """
        This creates a fake aggregator instance and returns it.
        """
        return DumbAggregator(request.getfuncargvalue("metrics_store"), metrics_settings={})

    def pytest_funcarg__metrics_store(self, request):
        """
        This creates a fake metrics store instance and returns it.
        """
        return DumbMetricsStore()

    def pytest_funcarg__servers(self, request):
        """
        This creates a pytest funcarg for a client to a running Statsite
        server.
        """
        # Instantiate a graphite server
        graphite = request.getfuncargvalue("graphite")

        # Instantiate server
        settings = {
            "flush_interval": self.DEFAULT_INTERVAL,
            "collector": {
                "host": "localhost",
                "port": graphite.port + 1
             },
            "store": {
                "host": "localhost",
                "port": graphite.port,
                "prefix": "foobar"
             }
        }

        # Take override settings if they exist
        if hasattr(request.function, "statsite_settings"):
            settings = dict(settings.items() + request.function.statsite_settings.items())

        server = Statsite(settings)
        thread = threading.Thread(target=server.start)
        thread.start()

        # Add a finalizer to make sure the server is properly shutdown
        request.addfinalizer(lambda: server.shutdown())

        # Create the UDP client connected to the statsite server
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.connect((settings["collector"]["host"], settings["collector"]["port"]))

        return (client, server, graphite)

    def pytest_funcarg__servers_tcp(self, request):
        """
        This creates a pytest funcarg for a client to a running Statsite
        server. In this configuration, the server listens on TCP and the client
        is a TCP socket.
        """
        # Instantiate a graphite server
        graphite = request.getfuncargvalue("graphite")

        # Instantiate server
        settings = {
            "flush_interval": self.DEFAULT_INTERVAL,
            "collector": {
                "host": "localhost",
                "port": graphite.port + 1,
                "class": "collector.TCPCollector"
             },
            "store": {
                "host": "localhost",
                "port": graphite.port,
                "prefix": "foobar"
             }
        }

        # Take override settings if they exist
        if hasattr(request.function, "statsite_settings"):
            settings = dict(settings.items() + request.function.statsite_settings.items())

        server = Statsite(settings)
        thread = threading.Thread(target=server.start)
        thread.start()

        # Add a finalizer to make sure the server is properly shutdown
        request.addfinalizer(lambda: server.shutdown())

        # Create the UDP client connected to the statsite server
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((settings["collector"]["host"], settings["collector"]["port"]))

        return (client, server, graphite)

    def pytest_funcarg__graphite(self, request):
        """
        This creates a pytest funcarg for a fake Graphite server.
        """
        host = "localhost"

        # Instantiate the actual TCP server by trying random ports
        # to make sure they don't stomp on each other.
        while True:
            try:
                port = random.randint(2048, 32768)
                server = GraphiteServer((host, port), GraphiteHandler)
                break
            except socket.error, e:
                if e[0] != errno.EADDRINUSE:
                    raise e

        # Create the thread to run the server and start it up
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        # Add a finalizer to make sure our server is properly
        # shutdown after every test
        request.addfinalizer(lambda: server.shutdown())

        return server

    def pytest_funcarg__tempfile(self, request):
        return tempfile.NamedTemporaryFile()

    def after_flush_interval(self, callback, interval=None):
        """
        This waits the configured flush interval prior to calling
        the callback.
        """
        # Wait the given interval
        interval = self.DEFAULT_INTERVAL if interval is None else interval
        interval += 0.5
        time.sleep(interval)

        # Call the callback
        callback()

########NEW FILE########
__FILENAME__ = test_aliveness
"""
Contains tests to test the aliveness check of Statsite.
"""

import socket
import time
from tests.base import TestBase
from tests.helpers import statsite_settings

class TestBasic(TestBase):
    @statsite_settings({
        "aliveness_check": {
            "enabled": True
        }
    })
    def test_default_aliveness(self, servers):
        """
        Tests that the default aliveness check works.
        """
        socket = self._socket()
        socket.sendall("hello?")
        data = socket.recv(1024)
        socket.close()

        assert "YES" == data

    def _socket(self, host="localhost", port=8325):
        """
        Returns a TCP socket to talk to the aliveness check.
        """
        # Create a socket (SOCK_STREAM means a TCP socket)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set a timeout so that a proper exception is raised if things
        # take too long
        sock.settimeout(1.0)

        # Connect to server and send data
        sock.connect((host, port))

        return sock

########NEW FILE########
__FILENAME__ = test_basic
"""
Contains integration tests to test the basic functionality of
Statsite: simply collecting key/value pairs.
"""

import time
from tests.base import TestBase

class TestBasic(TestBase):
    def test_single_key_value(self, servers):
        """
        Tests that basic key/value pairs are successfully flushed
        to Graphite.
        """
        client, server, graphite = servers

        key = "answer"
        value = 42
        timestamp = int(time.time())

        def check():
            message = "%s.kv.%s %s %s" % (server.settings["store"]["prefix"], key, value, timestamp)
            assert [message] == graphite.messages

        client.send("%s:%s|kv|@%d" % (key, value, timestamp))
        self.after_flush_interval(check)

    def test_multiple_key_value(self, servers):
        """
        Tests that multiple basic key/value pairs can be send to
        Statsite, and that they will all be flushed during the flush
        interval.
        """
        client, server, graphite = servers
        prefix = server.settings["store"]["prefix"]

        messages = [("answer", 42, int(time.time())),
                    ("another", 84, int(time.time()) - 5)]

        # The test method
        def check():
            raw_messages = ["%s.kv.%s %s %s" % (prefix,k,v,ts) for k,v,ts in messages]
            assert raw_messages == graphite.messages

        # Send all the messages
        for message in messages:
            client.send("%s:%s|kv|@%d" % message)

        # Verify they were properly received
        self.after_flush_interval(check)

    def test_clears_after_flush_interval(self, servers):
        """
        Tests that after the flush interval, the data is cleared and
        only new data is sent to the graphite server.
        """
        client, server, graphite = servers
        prefix = server.settings["store"]["prefix"]

        messages = [("k", 1, int(time.time())), ("j", 2, int(time.time()))]

        # Send the first message and wait the flush interval
        client.send("%s:%s|kv|@%d" % messages[0])
        self.after_flush_interval(lambda: None)

        # Send the second message
        client.send("%s:%s|kv|@%d" % messages[1])

        # Check the results after the flush interval
        def check():
            raw_messages = ["%s.kv.%s %s %s" % (prefix,k,v,ts) for k,v,ts in messages]
            assert raw_messages == graphite.messages

        self.after_flush_interval(check)

    def test_no_data_before_flush_interval(self, servers):
        """
        Tests that the data is flushed on the flush interval.
        """
        statsite_init_time = time.time()
        client, server, graphite = servers

        # Send some data to graphite and wait the flush interval
        client.send("k:1|kv")
        self.after_flush_interval(lambda: None)

        # Verify that the data was received at least after the
        # flush interval
        duration = graphite.last_receive - statsite_init_time
        epsilon  = 0.1
        assert abs(int(self.DEFAULT_INTERVAL) - duration) <= epsilon

class TestBasicTCP(TestBase):
    def test_single_key_value(self, servers_tcp):
        """
        Tests that basic key/value pairs are successfully flushed
        to Graphite.
        """
        client, server, graphite = servers_tcp

        key = "answer"
        value = 42
        timestamp = int(time.time())

        def check():
            message = "%s.kv.%s %s %s" % (server.settings["store"]["prefix"], key, value, timestamp)
            assert [message] == graphite.messages

        client.sendall("%s:%s|kv|@%d\n" % (key, value, timestamp))
        self.after_flush_interval(check)

    def test_multiple_key_value(self, servers_tcp):
        """
        Tests that multiple basic key/value pairs can be send to
        Statsite, and that they will all be flushed during the flush
        interval.
        """
        client, server, graphite = servers_tcp
        prefix = server.settings["store"]["prefix"]

        messages = [("answer", 42, int(time.time())),
                    ("another", 84, int(time.time()) - 5)]

        # The test method
        def check():
            raw_messages = ["%s.kv.%s %s %s" % (prefix,k,v,ts) for k,v,ts in messages]
            assert raw_messages == graphite.messages

        # Send all the messages
        for message in messages:
            client.sendall("%s:%s|kv|@%d\n" % message)

        # Verify they were properly received
        self.after_flush_interval(check)

    def test_clears_after_flush_interval(self, servers_tcp):
        """
        Tests that after the flush interval, the data is cleared and
        only new data is sent to the graphite server.
        """
        client, server, graphite = servers_tcp
        prefix = server.settings["store"]["prefix"]

        messages = [("k", 1, int(time.time())), ("j", 2, int(time.time()))]

        # Send the first message and wait the flush interval
        client.sendall("%s:%s|kv|@%d\n" % messages[0])
        self.after_flush_interval(lambda: None)

        # Send the second message
        client.sendall("%s:%s|kv|@%d\n" % messages[1])

        # Check the results after the flush interval
        def check():
            raw_messages = ["%s.kv.%s %s %s" % (prefix,k,v,ts) for k,v,ts in messages]
            assert raw_messages == graphite.messages

        self.after_flush_interval(check)

    def test_no_data_before_flush_interval(self, servers_tcp):
        """
        Tests that the data is flushed on the flush interval.
        """
        statsite_init_time = time.time()
        client, server, graphite = servers_tcp

        # Send some data to graphite and wait the flush interval
        client.sendall("k:1|kv\n")
        self.after_flush_interval(lambda: None)

        # Verify that the data was received at least after the
        # flush interval
        duration = graphite.last_receive - statsite_init_time
        epsilon  = 0.1
        assert abs(int(self.DEFAULT_INTERVAL) - duration) <= epsilon


########NEW FILE########
__FILENAME__ = graphite
"""
Contains a fake Graphite stub which can be used to test what
Statsite is sending to Graphite.
"""

import SocketServer
import time

class GraphiteServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    """
    A fake Graphite server. This server stores all the messages received
    by Graphite in the `messages` list.
    """

    allow_reuse_address = True

    def __init__(self, address, *args, **kwargs):
        SocketServer.TCPServer.__init__(self, address, *args, **kwargs)

        # Store the host/port data and messages for users of the server
        self.host, self.port = address
        self.messages = []
        self.last_receive = None

class GraphiteHandler(SocketServer.StreamRequestHandler):
    """
    TCP handler for the fake graphite server. This receives messages
    and aggregates them on the server.
    """

    def handle(self):
        # Read all the lines from the input and append them to the
        # messages the server has seen. This is how we "fake" a
        # Graphite server. The tests are simply expected to test the
        # order and values of the messages themselves.
        while True:
            line = self.rfile.readline()
            if not line:
                break

            self.server.messages.append(line.rstrip("\n"))
            self.server.last_receive = time.time()

########NEW FILE########
__FILENAME__ = helpers
"""
Contains helper classes and methods for tests.
"""

from statsite.aggregator import Aggregator
from statsite.collector import Collector
from statsite.metrics_store import MetricsStore

class DumbAggregator(Aggregator):
    def __init__(self, *args, **kwargs):
        super(DumbAggregator, self).__init__(*args, **kwargs)

        self.flushed = False
        self.metrics = []

    def add_metrics(self, metrics):
        self.metrics.extend(metrics)

    def flush(self):
        self.flushed = True

class DumbCollector(Collector):
    # Note that the host/port arguments are to avoid exceptions when
    # setting the settings in the "servers" funcarg
    def __init__(self, host=None, port=None, aggregator=None):
        super(DumbCollector, self).__init__(aggregator)

    pass

class DumbMetricsStore(MetricsStore):
    # Note that the host/port arguments are to avoid exceptions when
    # setting the settings in the "servers" funcarg
    def __init__(self, host=None, port=None, prefix=None):
        self.data = []

    def flush(self, data):
        self.data.extend(data)

def statsite_settings(settings):
    """
    Decorator to set the settings for Statsite for the "servers"
    funcarg.
    """
    def decorator(func):
        func.func_dict["statsite_settings"] = settings
        return func

    return decorator

########NEW FILE########
__FILENAME__ = test_statsite
"""
Contains tests for the `statsite` binary program.
"""

import pytest
from tests.base import TestBase
from statsite.bin.statsite import StatsiteCommand, StatsiteCommandError

class TestStatsiteBin(TestBase):
    def test_has_default_log_level(self):
        """
        Tests that the log level by default is "info"
        """
        command = StatsiteCommand([])
        assert "info" == command.settings["log_level"]

    def test_parse_nonexistent_file(self):
        with pytest.raises(StatsiteCommandError):
            StatsiteCommand(["-c", "/tmp/zomgthisshouldnevereverexiststatsitenope"])

    def test_parse_top_level_settings_from_file(self, tempfile):
        """
        Tests that the statsite command can properly read top-level
        settings from a configuration file.
        """
        tempfile.write("""
[statsite]
flush_interval=20
log_level=error
""")
        tempfile.flush()

        command = StatsiteCommand(["-c", tempfile.name])
        assert "20" == command.settings["flush_interval"]
        assert "error" == command.settings["log_level"]

    def test_parse_settings_from_file(self, tempfile):
        """
        Tests that the statsite command can properly read settings
        from a configuration file.
        """
        tempfile.write("""
[collection]
key=value
""")
        tempfile.flush()

        command = StatsiteCommand(["-c", tempfile.name])
        assert "value" == command.settings["collection"]["key"]

    def test_parse_settings_from_options(self):
        """
        Tests that the statsite can read options from the command
        line.
        """
        command = StatsiteCommand(["-s", "collection.key=value"])
        assert "value" == command.settings["collection"]["key"]

    def test_parse_command_line_over_file(self, tempfile):
        """
        Tests that command line options override file options.
        """
        tempfile.write("""
[collection]
key=value
key2=value2
""")
        tempfile.flush()

        command = StatsiteCommand(["-c", tempfile.name, "-s", "collection.key2=bam"])
        assert "value" == command.settings["collection"]["key"]
        assert "bam" == command.settings["collection"]["key2"]

    def test_parse_dot_settings_from_file(self, tempfile):
        """
        Tests that settings separated by dots are properly stored
        from a file.
        """
        tempfile.write("""
[collection]
key.sub=value
""")
        tempfile.flush()

        command = StatsiteCommand(["-c", tempfile.name])
        assert "value" == command.settings["collection"]["key"]["sub"]

    def test_syntax_error_in_configuration_file(self, tempfile):
        """
        Tests that a syntax error in a configuration file raises a
        proper error.
        """
        tempfile.write("I'm invalid!")
        tempfile.flush()

        # TODO: This should raise a proper exception
        # StatsiteCommand(["-c", tempfile.name])

########NEW FILE########
__FILENAME__ = test_aggregator
"""
Contains tests for the statistics aggregator base class as well
as the default aggregator class.
"""

import time
from tests.base import TestBase
from statsite.aggregator import Aggregator, DefaultAggregator
from statsite.metrics import Counter, KeyValue, Timer

class TestAggregator(TestBase):
    def test_fold_metrics_works(self, monkeypatch):
        """
        Tests that aggregators can fold metrics properly.
        """
        now = 12
        monkeypatch.setattr(time, 'time', lambda: now)
        metrics  = [KeyValue("k", 1, now), Counter("j", 2)]
        result   = Aggregator(None)._fold_metrics(metrics)

        assert 1 == result.count(("kv.k", 1, now))
        assert 1 == result.count(("counts.j", 2, now))

    def test_fold_metrics_passes_metric_settings(self, monkeypatch):
        """
        Tests that aggregators pass the proper metric settings when
        folding over.
        """
        now = 12
        settings = { "ms": { "percentile": 80 } }
        metrics  = [Timer("k", 20, now)]

        monkeypatch.setattr(time, 'time', lambda: now)
        result = Aggregator(None, metrics_settings=settings)._fold_metrics(metrics)
        print repr(result)
        assert 1 == result.count(("timers.k.sum_80", 20, now))

class TestDefaultAggregator(TestBase):
    def test_flushes_collected_metrics(self, metrics_store):
        """
        Tests that the default aggregator properly flushes the
        collected metrics to the metric store.
        """
        now = 17
        agg = DefaultAggregator(metrics_store)
        agg.add_metrics([KeyValue("k", 1, now)])
        agg.add_metrics([KeyValue("k", 2, now)])
        agg.flush()

        assert [("kv.k", 1, now), ("kv.k", 2, now)] == metrics_store.data

########NEW FILE########
__FILENAME__ = test_collector
"""
Contains tests for the collector base class.
"""

import pytest
from tests.base import TestBase
from statsite.metrics import Counter, KeyValue, Timer
from statsite.collector import Collector

class TestCollector(TestBase):
    def test_stores_aggregator(self):
        """
        Tests that collectors will store aggregator objects.
        """
        agg = object()
        assert agg is Collector(agg).aggregator

    def test_parse_metrics_succeeds(self):
        """
        Tests that parsing metrics succeeds and returns an array
        of proper metric objects.
        """
        message = "\n".join(["k:1|kv", "j:27|ms"])
        results = Collector(None)._parse_metrics(message)

        assert isinstance(results[0], KeyValue)
        assert isinstance(results[1], Timer)

    def test_parse_metrics_suppress_error(self):
        """
        Tests that parsing metrics will suppress errors if requested.
        """
        message = "k:1|nope"
        results = Collector(None)._parse_metrics(message)

        assert 0 == len(results)

    def test_parse_metrics_keeps_good_metrics(self, aggregator):
        """
        Tests that parse_metrics will keep the good metrics in the face
        of an error.
        """
        message = "\n".join(["k::1|c",
                             "j:2|nope",
                             "k:2|ms"])
        results = Collector(aggregator)._parse_metrics(message)

        assert [Timer("k", 2)] == results

    def test_parse_metrics_ignores_blank_lines(self, aggregator):
        """
        Tests that parse_metrics will properly ignore blank lines.
        """
        message = "\n".join(["", "k:2|ms"])
        assert [Timer("k", 2)] == Collector(aggregator)._parse_metrics(message)

    def test_add_metrics(self, aggregator):
        """
        Tests that add_metrics successfully adds an array of metrics to
        the configured aggregator.
        """
        now = 17
        metrics = [KeyValue("k", 1, now), Counter("j", 2)]
        Collector(aggregator)._add_metrics(metrics)

        assert metrics == aggregator.metrics

    def test_set_aggregator(self, aggregator):
        """
        Tests that setting an aggregator properly works.
        """
        coll    = Collector(aggregator)
        new_agg = object()

        assert aggregator is coll.aggregator
        coll.set_aggregator(new_agg)
        assert new_agg is coll.aggregator

########NEW FILE########
__FILENAME__ = test_metric
"""
Contains tests for the base metric class.
"""

from statsite.metrics import Metric

class TestMetric(object):
    def test_fold_basic(self):
        """Tests folding over a normal metric returns the key/value
        using the flag as the timestamp."""
        metrics = [Metric("k", 27, 123456)]
        assert [("k", 27, 123456)] == Metric.fold(metrics, 0)

    def test_fold_uses_now(self):
        """
        Tests that folding over a normal metric with no flag will use
        the "now" time as the timestamp.
        """
        metrics = [Metric("k", 27, None)]
        assert [("k", 27, 123456)] == Metric.fold(metrics, 123456)

########NEW FILE########
__FILENAME__ = test_metrics_store
"""
Contains metric store tests.
"""

import pytest
from tests.base import TestBase
from statsite.metrics_store import GraphiteStore, MetricsStore

class TestMetricsStore(TestBase):
    """
    Tests the metrics store base class, but there are no real
    tests for this at the moment since there is only one method
    and it is abstract.
    """
    pass

class TestGraphiteStore(TestBase):
    def test_flushes(self, graphite):
        """
        Tests that metrics are properly flushed to a graphite server.
        """
        store = GraphiteStore(graphite.host, graphite.port, prefix="foobar")
        metrics = [("k", 1, 10), ("j", 2, 20)]

        # Flush the metrics and verify that graphite sees the
        # proper results
        store.flush(metrics)
        store.close()

        # Check that we get the proper results after a specific
        # flush interval to give the test time to send the data
        def check():
            metric_strings = ["foobar.%s %s %s" % metric for metric in metrics]
            assert metric_strings == graphite.messages

        self.after_flush_interval(check, interval=1)

########NEW FILE########
__FILENAME__ = test_metric_counter
"""
Contains tests for the Counter metric.
"""

from statsite.metrics import Counter

class TestCounterMetric(object):
    def test_fold(self):
        """
        Tests that counter folding places the sum into a
        unique key for each counter.
        """
        metrics = [Counter("k", 10),
                   Counter("k", 15),
                   Counter("j", 5),
                   Counter("j", 15)]
        expected = [("counts.k", 25, 0), ("counts.j", 20, 0)]

        result = Counter.fold(metrics, 0)
        assert expected == result

########NEW FILE########
__FILENAME__ = test_metric_kv
"""
Contains tests for the key/value metric class.
"""

import time
from statsite.metrics import KeyValue

class TestKeyValue(object):
    def test_fold_basic(self):
        """Tests folding over a normal metric returns the key/value
        using the flag as the timestamp."""
        metrics = [KeyValue("k", 27, 123456)]
        assert [("kv.k", 27, 123456)] == KeyValue.fold(metrics, 0)

    def test_defaults_flag_to_now(self, monkeypatch):
        """Tests that the flag is defaulted to the time of instantiation
        if no flag is given."""
        now = 27
        monkeypatch.setattr(time, 'time', lambda: now)
        metrics = [KeyValue("k", 27)]
        assert [("kv.k", 27, now)] == KeyValue.fold(metrics, 0)

########NEW FILE########
__FILENAME__ = test_metric_timer
"""
Contains tests for the timer metric.
"""

from statsite.metrics import Timer

class TestTimerMetric(object):
    def test_fold_sum(self):
        """
        Tests that folding generates a sum of the timers.
        """
        now = 10
        metrics = [Timer("k", 10),
                   Timer("k", 15),
                   Timer("j", 7.4),
                   Timer("j", 8.6)]
        result = Timer.fold(metrics, now)

        assert ("timers.k.sum", 25, now) == self._get_metric("timers.k.sum", result)
        assert ("timers.j.sum", 16.0, now) == self._get_metric("timers.j.sum", result)

    def test_fold_mean(self):
        """
        Tests that the mean is properly generated for the
        timers.
        """
        now = 10
        metrics = [Timer("k", 10),
                   Timer("k", 15),
                   Timer("j", 7),
                   Timer("j", 8)]
        result = Timer.fold(metrics, now)

        assert ("timers.k.mean", 12.5, now) == self._get_metric("timers.k.mean", result)
        assert ("timers.j.mean", 7.5, now) == self._get_metric("timers.j.mean", result)

    def test_fold_lower(self):
        """
        Tests that the lower bound for the timers is properly computed.
        """
        now = 10
        metrics = [Timer("k", 10),
                   Timer("k", 15),
                   Timer("j", 7.9),
                   Timer("j", 8)]
        result = Timer.fold(metrics, now)

        assert ("timers.k.lower", 10, now) == self._get_metric("timers.k.lower", result)
        assert ("timers.j.lower", 7.9, now) == self._get_metric("timers.j.lower", result)

    def test_fold_upper(self):
        """
        Tests that the upper bound for the timers is properly computed.
        """
        now = 10
        metrics = [Timer("k", 10),
                   Timer("k", 15),
                   Timer("j", 7.9),
                   Timer("j", 8)]
        result = Timer.fold(metrics, now)

        assert ("timers.k.upper", 15, now) == self._get_metric("timers.k.upper", result)
        assert ("timers.j.upper", 8, now) == self._get_metric("timers.j.upper", result)

    def test_fold_count(self):
        """
        Tests the counter of timers is properly computed.
        """
        now = 10
        metrics = [Timer("k", 10),
                   Timer("k", 15),
                   Timer("j", 7.9),
                   Timer("j", 8)]
        result = Timer.fold(metrics, now)

        assert ("timers.k.count", 2, now) == self._get_metric("timers.k.count", result)
        assert ("timers.j.count", 2, now) == self._get_metric("timers.j.count", result)

    def test_fold_stdev(self):
        """
        Tests the standard deviations of counters is properly computed.
        """
        now = 10
        metrics = [Timer("k", 10),
                   Timer("k", 15),
                   Timer("j", 7.9),
                   Timer("j", 8)]
        result = Timer.fold(metrics, now)

        assert ("timers.k.stdev", Timer._stdev([10, 15], 12.5), now) == self._get_metric("timers.k.stdev", result)
        assert ("timers.j.stdev", Timer._stdev([7.9, 8], 7.95), now) == self._get_metric("timers.j.stdev", result)

    def test_sum_percentile(self):
        """
        Tests the percentile sum is properly counted.
        """
        now = 10
        result = Timer.fold(self._100_timers, now)
        assert ("timers.k.sum_90", 4545, now) == self._get_metric("timers.k.sum_90", result)

    def test_mean_percentile(self):
        """
        Tests the percentile sum is properly counted.
        """
        now = 10
        result = Timer.fold(self._100_timers, now)
        assert ("timers.k.mean_90", 50, now) == self._get_metric("timers.k.mean_90", result)

    def test_stdev(self):
        """
        Tests that the standard deviation is properly computed.
        """
        numbers = [0.331002, 0.591082, 0.668996, 0.422566, 0.458904,
                   0.868717, 0.30459, 0.513035, 0.900689, 0.655826]
        average = sum(numbers) / len(numbers)

        assert int(0.205767 * 10000) == int(Timer._stdev(numbers, average) * 10000)

    def _get_metric(self, key, metrics):
        """
        This will extract a specific metric out of an array of metrics.
        """
        for metric in metrics:
            if metric[0] == key:
                return metric

        return None

    @property
    def _100_timers(self):
        result = []
        for i in xrange(1, 101):
            result.append(Timer("k", i))

        return result

########NEW FILE########
__FILENAME__ = test_parser
"""
Contains tests to test the parsing of messages sent to
Statsite.
"""

import pytest
import statsite.parser as p

class TestParser(object):
    def test_parse_line_basic(self):
        """Tests the basic line type of: k:v|type"""
        assert ("k", 27, "kv", None) == p.parse_line("k:27|kv")

    def test_parses_flag(self):
        """Tests that lines with flags (@ parameters) can be parsed
        properly."""
        assert ("k", 27, "ms", 123456) == p.parse_line("k:27|ms|@123456")

    def test_parses_negative_value(self):
        """Tests that lines can contain negative numbers as values."""
        assert ("k", -27, "ms", None) == p.parse_line("k:-27|ms")

    def test_parses_float_value(self):
        """Tests that float values can be parsed."""
        assert ("k", 3.14, "ms", None) == p.parse_line("k:3.14|ms")

    def test_parses_float_flag(self):
        """Tests that float flags can be parsed."""
        assert ("k", 3, "ms", 0.1) == p.parse_line("k:3|ms|@0.1")

    def test_fails_no_value(self):
        """Tests that parsing fails for lines with no
        value (or key, depending on how you look at it)"""
        with pytest.raises(ValueError):
            p.parse_line("k|kv")

    def test_fails_no_type(self):
        """Tests that parsing fails for lines with no
        metric type."""
        with pytest.raises(ValueError):
            p.parse_line("k:27")

    def test_fails_negative_flag(self):
        """Tests that negative flags can not be parsed."""
        with pytest.raises(ValueError):
            p.parse_line("k:27|ms|@-24")

    def test_parse_line_with_underscores(self):
        """
        Tests that this line can properly pass. This was found to
        fail at some point in production.
        """
        p.parse_line("hosts.lucid64.bi.metrics.tasks.update_session_create_counts:6.330013|ms")

########NEW FILE########
__FILENAME__ = test_statsite
"""
Contains tests for the Statsite class.
"""

import time
from tests.base import TestBase
from tests.helpers import DumbCollector, DumbAggregator, DumbMetricsStore
from statsite.statsite import Statsite

class TestStatsite(TestBase):
    def pytest_funcarg__statsite_dummy(self, request):
        """
        Returns a Statsite instance where every component is a test dummy.
        """
        settings = {
            "aggregator": {
                "class": "tests.helpers.DumbAggregator"
            },
            "collector": {
                "class": "tests.helpers.DumbCollector"
            },
            "store": {
                "class": "tests.helpers.DumbMetricsStore"
            }
        }

        return Statsite(settings)

    def test_initialization(self, statsite_dummy):
        """
        Tests that initialization properly initializes all the pieces
        of the Statsite architecture.
        """
        assert statsite_dummy.collector
        assert statsite_dummy.aggregator is statsite_dummy.collector.aggregator
        assert statsite_dummy.store is statsite_dummy.aggregator.metrics_store

    def test_flush_and_switch_aggregator(self, statsite_dummy):
        """
        Tests that flushing and switching the aggregator properly
        works.
        """
        original = statsite_dummy.aggregator
        statsite_dummy._flush_and_switch_aggregator()

        # Sleep some time to allow time for other thread to start
        time.sleep(0.2)

        # Verify the switch worked
        assert statsite_dummy.aggregator is statsite_dummy.collector.aggregator
        assert original is not statsite_dummy.aggregator
        assert original.flushed

########NEW FILE########
__FILENAME__ = test_util
"""
Contains tests for utility functions.
"""

import pytest
from tests.base import TestBase

import statsite.util

class TestMerge(TestBase):
    def test_merge(self):
        """
        Tests that dictionary deep merging works properly.
        """
        a = {'a': 1, 'b': {1: 1, 2: 2}, 'd': 6}
        b = {'c': 3, 'b': {2: 7}, 'd': {'z': [1, 2, 3]}}
        result = statsite.util.deep_merge(a, b)
        expected = {'a': 1, 'b': {1: 1, 2: 7}, 'c': 3, 'd': {'z': [1, 2, 3]}}

        assert expected == result

    def test_non_destructive(self):
        """
        Tests that the merging is non-destructive for the source
        dictionary.
        """
        a = {'a': { 'b': False } }
        b = {'a': { 'b': True } }
        result = statsite.util.deep_merge(a, b)

        # Assert that it was not changed
        assert { 'a': { 'b': False } } == a

class TestResolveClassString(TestBase):
    def test_resolve_no_module(self):
        """
        Tests that resolving without a module fails.
        """
        with pytest.raises(ValueError):
            statsite.util.resolve_class_string("Foo")

    def test_resolve_no_class(self):
        """
        Tests that resolving without a class fails.
        """
        with pytest.raises(ValueError):
            statsite.util.resolve_class_string("foo.")

    def test_resolve_nonexistent_class(self):
        """
        Tests that resolving a class which doesn't exist
        fails.
        """
        with pytest.raises(ImportError):
            statsite.util.resolve_class_string("os.getloginn")

    def test_resolve_correct_class(self):
        """
        Tests that resolving an item with valid parameters
        results in a valid result.
        """
        result = statsite.util.resolve_class_string("os.getlogin")
        assert callable(result)

########NEW FILE########
