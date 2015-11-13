__FILENAME__ = daemon
"""A generic daemon class. Subclass and override the run() method.

Based on http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
"""

import atexit
import os
from signal import SIGTERM
import sys
import time


class Daemon(object):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        """UNIX double-fork magic."""
        try:
            pid = os.fork()
            if pid > 0:
                # First parent; exit.
                sys.exit(0)
        except OSError as e:
            sys.stderr.write('Could not fork! %d (%s)\n' %
                             (e.errno, e.strerror))
            sys.exit(1)

        # Disconnect from parent environment.
        os.chdir('/')
        os.setsid()
        os.umask(0o022)

        # Fork again.
        try:
            pid = os.fork()
            if pid > 0:
                # Second parent; exit.
                sys.exit(0)
        except OSError as e:
            sys.stderr.write('Could not fork (2nd)! %d (%s)\n' %
                             (e.errno, e.strerror))
            sys.exit(1)

        # Redirect file descriptors.
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # Write the pidfile.
        atexit.register(self.delpid)
        pid = str(os.getpid())
        with open(self.pidfile, 'w+') as fp:
            fp.write('%s\n' % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def start(self, *args, **kw):
        """Start the daemon."""
        pid = None
        if os.path.exists(self.pidfile):
            with open(self.pidfile, 'r') as fp:
                pid = int(fp.read().strip())

        if pid:
            msg = 'pidfile (%s) exists. Daemon already running?\n'
            sys.stderr.write(msg % self.pidfile)
            sys.exit(1)

        self.daemonize()
        self.run(*args, **kw)

    def stop(self):
        """Stop the daemon."""
        pid = None
        if os.path.exists(self.pidfile):
            with open(self.pidfile, 'r') as fp:
                pid = int(fp.read().strip())

        if not pid:
            msg = 'pidfile (%s) does not exist. Daemon not running?\n'
            sys.stderr.write(msg % self.pidfile)
            return

        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError as e:
            e = str(e)
            if e.find('No such process') > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
                else:
                    print(e)
                    sys.exit(1)

    def restart(self, *args, **kw):
        """Restart the daemon."""
        self.stop()
        self.start(*args, **kw)

    def run(self, *args, **kw):
        """Override this method."""

########NEW FILE########
__FILENAME__ = gmetric
#!/usr/bin/env python

# This is the MIT License
# http://www.opensource.org/licenses/mit-license.php
#
# Copyright (c) 2007,2008 Nick Galbreath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

#
# Version 1.0 - 21-Apr-2007
#   initial
# Version 2.0 - 16-Nov-2008
#   made class Gmetric thread safe
#   made gmetrix xdr writers _and readers_
#   Now this only works for gmond 2.X packets, not tested with 3.X
#
# Version 3.0 - 09-Jan-2011 Author: Vladimir Vuksan
#   Made it work with the Ganglia 3.1 data format
#
# Version 3.1 - 30-Apr-2011 Author: Adam Tygart
#   Added Spoofing support


from xdrlib import Packer, Unpacker
import socket

slope_str2int = {'zero':0,
                 'positive':1,
                 'negative':2,
                 'both':3,
                 'unspecified':4}

# could be autogenerated from previous but whatever
slope_int2str = {0: 'zero',
                 1: 'positive',
                 2: 'negative',
                 3: 'both',
                 4: 'unspecified'}


class Gmetric:
    """
    Class to send gmetric/gmond 2.X packets

    Thread safe
    """

    type = ('', 'string', 'uint16', 'int16', 'uint32', 'int32', 'float',
            'double', 'timestamp')
    protocol = ('udp', 'multicast')

    def __init__(self, host, port, protocol):
        if protocol not in self.protocol:
            raise ValueError("Protocol must be one of: " + str(self.protocol))

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if protocol == 'multicast':
            self.socket.setsockopt(socket.IPPROTO_IP,
                                   socket.IP_MULTICAST_TTL, 20)
        self.hostport = (host, int(port))
        #self.socket.connect(self.hostport)

    def send(self, NAME, VAL, TYPE='', UNITS='', SLOPE='both',
             TMAX=60, DMAX=0, GROUP="", SPOOF=""):
        if SLOPE not in slope_str2int:
            raise ValueError("Slope must be one of: " + str(list(self.slope.keys())))
        if TYPE not in self.type:
            raise ValueError("Type must be one of: " + str(self.type))
        if len(NAME) == 0:
            raise ValueError("Name must be non-empty")

        ( meta_msg, data_msg )  = gmetric_write(NAME, VAL, TYPE, UNITS, SLOPE, TMAX, DMAX, GROUP, SPOOF)
        # print msg

        self.socket.sendto(bytes(bytearray(meta_msg, "utf-8")), self.hostport)
        self.socket.sendto(bytes(bytearray(data_msg, "utf-8")), self.hostport)

def gmetric_write(NAME, VAL, TYPE, UNITS, SLOPE, TMAX, DMAX, GROUP, SPOOF):
    """
    Arguments are in all upper-case to match XML
    """
    packer = Packer()
    HOSTNAME="test"
    if SPOOF == "":
        SPOOFENABLED=0
    else :
        SPOOFENABLED=1
    # Meta data about a metric
    packer.pack_int(128)
    if SPOOFENABLED == 1:
        packer.pack_string(SPOOF)
    else:
        packer.pack_string(HOSTNAME)
    packer.pack_string(NAME)
    packer.pack_int(SPOOFENABLED)
    packer.pack_string(TYPE)
    packer.pack_string(NAME)
    packer.pack_string(UNITS)
    packer.pack_int(slope_str2int[SLOPE]) # map slope string to int
    packer.pack_uint(int(TMAX))
    packer.pack_uint(int(DMAX))
    # Magic number. Indicates number of entries to follow. Put in 1 for GROUP
    if GROUP == "":
        packer.pack_int(0)
    else:
        packer.pack_int(1)
        packer.pack_string("GROUP")
        packer.pack_string(GROUP)

    # Actual data sent in a separate packet
    data = Packer()
    data.pack_int(128+5)
    if SPOOFENABLED == 1:
        data.pack_string(SPOOF)
    else:
        data.pack_string(HOSTNAME)
    data.pack_string(NAME)
    data.pack_int(SPOOFENABLED)
    data.pack_string("%s")
    data.pack_string(str(VAL))

    return ( packer.get_buffer() ,  data.get_buffer() )

def gmetric_read(msg):
    unpacker = Unpacker(msg)
    values = dict()
    unpacker.unpack_int()
    values['TYPE'] = unpacker.unpack_string()
    values['NAME'] = unpacker.unpack_string()
    values['VAL'] = unpacker.unpack_string()
    values['UNITS'] = unpacker.unpack_string()
    values['SLOPE'] = slope_int2str[unpacker.unpack_int()]
    values['TMAX'] = unpacker.unpack_uint()
    values['DMAX'] = unpacker.unpack_uint()
    unpacker.done()
    return values


if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("", "--protocol", dest="protocol", default="udp",
                      help="The gmetric internet protocol, either udp or multicast, default udp")
    parser.add_option("", "--host",  dest="host",  default="127.0.0.1",
                      help="GMond aggregator hostname to send data to")
    parser.add_option("", "--port",  dest="port",  default="8649",
                      help="GMond aggregator port to send data to")
    parser.add_option("", "--name",  dest="name",  default="",
                      help="The name of the metric")
    parser.add_option("", "--value", dest="value", default="",
                      help="The value of the metric")
    parser.add_option("", "--units", dest="units", default="",
                      help="The units for the value, e.g. 'kb/sec'")
    parser.add_option("", "--slope", dest="slope", default="both",
                      help="The sign of the derivative of the value over time, one of zero, positive, negative, both, default both")
    parser.add_option("", "--type",  dest="type",  default="",
                      help="The value data type, one of string, int8, uint8, int16, uint16, int32, uint32, float, double")
    parser.add_option("", "--tmax",  dest="tmax",  default="60",
                      help="The maximum time in seconds between gmetric calls, default 60")
    parser.add_option("", "--dmax",  dest="dmax",  default="0",
                      help="The lifetime in seconds of this metric, default=0, meaning unlimited")
    parser.add_option("", "--group",  dest="group",  default="",
                      help="Group metric belongs to. If not specified Ganglia will show it as no_group")
    parser.add_option("", "--spoof",  dest="spoof",  default="",
                      help="the address to spoof (ip:host). If not specified the metric will not be spoofed")
    (options,args) = parser.parse_args()

    g = Gmetric(options.host, options.port, options.protocol)
    g.send(options.name, options.value, options.type, options.units,
           options.slope, options.tmax, options.dmax, options.group, options.spoof)

########NEW FILE########
__FILENAME__ = server
import re
import socket
import threading
import time
import types
import logging
from . import gmetric
from subprocess import call
from warnings import warn
# from xdrlib import Packer, Unpacker

log = logging.getLogger(__name__)

try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = None

from .daemon import Daemon


__all__ = ['Server']


def _clean_key(k):
    return re.sub(
        r'[^a-zA-Z_\-0-9\.]',
        '',
        re.sub(
            r'\s+',
            '_',
            k.replace('/', '-').replace(' ', '_')
        )
    )



TIMER_MSG = '''%(prefix)s.%(key)s.lower %(min)s %(ts)s
%(prefix)s.%(key)s.count %(count)s %(ts)s
%(prefix)s.%(key)s.mean %(mean)s %(ts)s
%(prefix)s.%(key)s.upper %(max)s %(ts)s
%(prefix)s.%(key)s.upper_%(pct_threshold)s %(max_threshold)s %(ts)s
'''


class Server(object):

    def __init__(self, pct_threshold=90, debug=False, transport='graphite',
                 ganglia_host='localhost', ganglia_port=8649,
                 ganglia_spoof_host='statsd:statsd',
                 gmetric_exec='/usr/bin/gmetric', gmetric_options = '-d',
                 graphite_host='localhost', graphite_port=2003, global_prefix=None, 
                 flush_interval=10000,
                 no_aggregate_counters=False, counters_prefix='stats',
                 timers_prefix='stats.timers', expire=0):
        self.buf = 8192
        self.flush_interval = flush_interval
        self.pct_threshold = pct_threshold
        self.transport = transport
        # Embedded Ganglia library options specific settings
        self.ganglia_host = ganglia_host
        self.ganglia_port = ganglia_port
        self.ganglia_protocol = "udp"
        # Use gmetric
        self.gmetric_exec = gmetric_exec
        self.gmetric_options = gmetric_options
        # Set DMAX to flush interval plus 20%. That should avoid metrics to prematurely expire if there is
        # some type of a delay when flushing
        self.dmax = int(self.flush_interval * 1.2)
        # What hostname should these metrics be attached to.
        self.ganglia_spoof_host = ganglia_spoof_host

        # Graphite specific settings
        self.graphite_host = graphite_host
        self.graphite_port = graphite_port
        self.no_aggregate_counters = no_aggregate_counters
        self.counters_prefix = counters_prefix
        self.timers_prefix = timers_prefix
        self.debug = debug
        self.expire = expire

        # For services like Hosted Graphite, etc.
        self.global_prefix = global_prefix

        self.counters = {}
        self.timers = {}
        self.gauges = {}
        self.flusher = 0

    def send_to_ganglia_using_gmetric(self,k,v,group, units):
        call([self.gmetric_exec, self.gmetric_options, "-u", units, "-g", group, "-t", "double", "-n",  k, "-v", str(v) ])


    def process(self, data):
        # the data is a sequence of newline-delimited metrics
        # a metric is in the form "name:value|rest"  (rest may have more pipes)
        data.rstrip('\n')

        for metric in data.split('\n'):
            match = re.match('\A([^:]+):([^|]+)\|(.+)', metric)

            if match == None:
                warn("Skipping malformed metric: <%s>" % (metric))
                continue

            key   = _clean_key( match.group(1) )
            value = match.group(2)
            rest  = match.group(3).split('|')
            mtype = rest.pop(0)

            if   (mtype == 'ms'): self.__record_timer(key, value, rest)
            elif (mtype == 'g' ): self.__record_gauge(key, value, rest)
            elif (mtype == 'c' ): self.__record_counter(key, value, rest)
            else:
                warn("Encountered unknown metric type in <%s>" % (metric))

    def __record_timer(self, key, value, rest):
        ts = int(time.time())
        timer = self.timers.setdefault(key, [ [], ts ])
        timer[0].append(float(value or 0))
        timer[1] = ts

    def __record_gauge(self, key, value, rest):
        ts = int(time.time())
        self.gauges[key] = [ float(value), ts ]

    def __record_counter(self, key, value, rest):
        ts = int(time.time())
        sample_rate = 1.0
        if len(rest) == 1:
            sample_rate = float(re.match('^@([\d\.]+)', rest[0]).group(1))
            if sample_rate == 0:
                warn("Ignoring counter with sample rate of zero: <%s>" % (metric))
                return

        counter = self.counters.setdefault(key, [ 0, ts ])
        counter[0] += float(value or 1) * (1 / sample_rate)
        counter[1] = ts

    def on_timer(self):
        """Executes flush(). Ignores any errors to make sure one exception
        doesn't halt the whole flushing process.
        """
        try:
            self.flush()
        except Exception as e:
            log.exception('Error while flushing: %s', e)
        self._set_timer()

    def flush(self):
        ts = int(time.time())
        stats = 0

        if self.transport == 'graphite':
            stat_string = ''
        elif self.transport == 'ganglia':
            g = gmetric.Gmetric(self.ganglia_host, self.ganglia_port, self.ganglia_protocol)

        for k, (v, t) in self.counters.items():
            if self.expire > 0 and t + self.expire < ts:
                if self.debug:
                    print("Expiring counter %s (age: %s)" % (k, ts -t))
                del(self.counters[k])
                continue
            v = float(v)
            v = v if self.no_aggregate_counters else v / (self.flush_interval / 1000)

            if self.debug:
                print("Sending %s => count=%s" % (k, v))

            if self.transport == 'graphite':
                msg = '%s.%s %s %s\n' % (self.counters_prefix, k, v, ts)
                stat_string += msg
            elif self.transport == 'ganglia':
                # We put counters in _counters group. Underscore is to make sure counters show up
                # first in the GUI. Change below if you disagree
                g.send(k, v, "double", "count", "both", 60, self.dmax, "_counters", self.ganglia_spoof_host)
            elif self.transport == 'ganglia-gmetric':
                self.send_to_ganglia_using_gmetric(k,v, "_counters", "count")

            # Clear the counter once the data is sent
            del(self.counters[k])
            stats += 1

        for k, (v, t) in self.gauges.items():
            if self.expire > 0 and t + self.expire < ts:
                if self.debug:
                    print("Expiring gauge %s (age: %s)" % (k, ts - t))
                del(self.gauges[k])
                continue
            v = float(v)

            if self.debug:
                print("Sending %s => value=%s" % (k, v))

            if self.transport == 'graphite':
                # note: counters and gauges implicitly end up in the same namespace
                msg = '%s.%s %s %s\n' % (self.counters_prefix, k, v, ts)
                stat_string += msg
            elif self.transport == 'ganglia':
                g.send(k, v, "double", "count", "both", 60, self.dmax, "_gauges", self.ganglia_spoof_host)
            elif self.transport == 'ganglia-gmetric':
                self.send_to_ganglia_using_gmetric(k,v, "_gauges", "gauge")

            stats += 1

        for k, (v, t) in self.timers.items():
            if self.expire > 0 and t + self.expire < ts:
                if self.debug:
                    print("Expiring timer %s (age: %s)" % (k, ts - t))
                del(self.timers[k])
                continue
            if len(v) > 0:
                # Sort all the received values. We need it to extract percentiles
                v.sort()
                count = len(v)
                min = v[0]
                max = v[-1]

                mean = min
                max_threshold = max

                if count > 1:
                    thresh_index = int((self.pct_threshold / 100.0) * count)
                    max_threshold = v[thresh_index - 1]
                    total = sum(v)
                    mean = total / count

                del(self.timers[k])

                if self.debug:
                    print("Sending %s ====> lower=%s, mean=%s, upper=%s, %dpct=%s, count=%s" \
                        % (k, min, mean, max, self.pct_threshold, max_threshold, count))

                if self.transport == 'graphite':

                    stat_string += TIMER_MSG % {
                        'prefix': self.timers_prefix,
                        'key': k,
                        'mean': mean,
                        'max': max,
                        'min': min,
                        'count': count,
                        'max_threshold': max_threshold,
                        'pct_threshold': self.pct_threshold,
                        'ts': ts,
                    }

                elif self.transport == 'ganglia':
                    # We are gonna convert all times into seconds, then let rrdtool add proper SI unit. This avoids things like
                    # 3521 k ms which is 3.521 seconds
                    # What group should these metrics be in. For the time being we'll set it to the name of the key
                    group = k
                    g.send(k + "_min", min / 1000, "double", "seconds", "both", 60, self.dmax, group, self.ganglia_spoof_host)
                    g.send(k + "_mean", mean / 1000, "double", "seconds", "both", 60, self.dmax, group, self.ganglia_spoof_host)
                    g.send(k + "_max", max / 1000, "double", "seconds", "both", 60, self.dmax, group, self.ganglia_spoof_host)
                    g.send(k + "_count", count, "double", "count", "both", 60, self.dmax, group, self.ganglia_spoof_host)
                    g.send(k + "_" + str(self.pct_threshold) + "pct", max_threshold / 1000, "double", "seconds", "both", 60, self.dmax, group, self.ganglia_spoof_host)
                elif self.transport == 'ganglia-gmetric':
                    # We are gonna convert all times into seconds, then let rrdtool add proper SI unit. This avoids things like
                    # 3521 k ms which is 3.521 seconds
                    group = k
                    self.send_to_ganglia_using_gmetric(k + "_mean", mean / 1000, group, "seconds")
                    self.send_to_ganglia_using_gmetric(k + "_min",  min / 1000 , group, "seconds")
                    self.send_to_ganglia_using_gmetric(k + "_max",  max / 1000, group, "seconds")
                    self.send_to_ganglia_using_gmetric(k + "_count", count , group, "count")
                    self.send_to_ganglia_using_gmetric(k + "_" + str(self.pct_threshold) + "pct",  max_threshold / 1000, group, "seconds")

                stats += 1

        if self.transport == 'graphite':

            stat_string += "statsd.numStats %s %d\n" % (stats, ts)

            # Prepend stats with Hosted Graphite API key if necessary
            if self.global_prefix:
                stat_string = '\n'.join([
                    '%s.%s' % (self.global_prefix, s) for s in stat_string.split('\n')[:-1]
                ])

            graphite = socket.socket()
            try:
                graphite.connect((self.graphite_host, self.graphite_port))
                graphite.sendall(bytes(bytearray(stat_string, "utf-8")))
                graphite.close()
            except socket.error as e:
                log.error("Error communicating with Graphite: %s" % e)
                if self.debug:
                    print("Error communicating with Graphite: %s" % e)

        if self.debug:
            print("\n================== Flush completed. Waiting until next flush. Sent out %d metrics =======" \
                % (stats))

    def _set_timer(self):
        self._timer = threading.Timer(self.flush_interval / 1000, self.on_timer)
        self._timer.daemon = True
        self._timer.start()

    def serve(self, hostname='', port=8125):
        assert type(port) is int, 'port is not an integer: %s' % (port)
        addr = (hostname, port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(addr)

        import signal

        def signal_handler(signal, frame):
                self.stop()
        signal.signal(signal.SIGINT, signal_handler)

        self._set_timer()
        while 1:
            data, addr = self._sock.recvfrom(self.buf)
            try:
                self.process(data)
            except Exception as error:
                log.error("Bad data from %s: %s",addr,error) 


    def stop(self):
        self._timer.cancel()
        self._sock.close()


class ServerDaemon(Daemon):
    def run(self, options):
        if setproctitle:
            setproctitle('pystatsd')
        server = Server(pct_threshold=options.pct,
                        debug=options.debug,
                        transport=options.transport,
                        graphite_host=options.graphite_host,
                        graphite_port=options.graphite_port,
                        global_prefix=options.global_prefix,
                        ganglia_host=options.ganglia_host,
                        ganglia_spoof_host=options.ganglia_spoof_host,
                        ganglia_port=options.ganglia_port,
                        gmetric_exec=options.gmetric_exec,
                        gmetric_options=options.gmetric_options,
                        flush_interval=options.flush_interval,
                        no_aggregate_counters=options.no_aggregate_counters,
                        counters_prefix=options.counters_prefix,
                        timers_prefix=options.timers_prefix,
                        expire=options.expire)

        server.serve(options.name, options.port)


def run_server():
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='debug mode', default=False)
    parser.add_argument('-n', '--name', dest='name', help='hostname to run on ', default='')
    parser.add_argument('-p', '--port', dest='port', help='port to run on (default: 8125)', type=int, default=8125)
    parser.add_argument('-r', '--transport', dest='transport', help='transport to use graphite, ganglia (uses embedded library) or ganglia-gmetric (uses gmetric)', type=str, default="graphite")
    parser.add_argument('--graphite-port', dest='graphite_port', help='port to connect to graphite on (default: 2003)', type=int, default=2003)
    parser.add_argument('--graphite-host', dest='graphite_host', help='host to connect to graphite on (default: localhost)', type=str, default='localhost')
    # Uses embedded Ganglia Library
    parser.add_argument('--ganglia-port', dest='ganglia_port', help='Unicast port to connect to ganglia on', type=int, default=8649)
    parser.add_argument('--ganglia-host', dest='ganglia_host', help='Unicast host to connect to ganglia on', type=str, default='localhost')
    parser.add_argument('--ganglia-spoof-host', dest='ganglia_spoof_host', help='host to report metrics as to ganglia', type=str, default='statsd:statsd')
    # Use gmetric
    parser.add_argument('--ganglia-gmetric-exec', dest='gmetric_exec', help='Use gmetric executable. Defaults to /usr/bin/gmetric', type=str, default="/usr/bin/gmetric")
    parser.add_argument('--ganglia-gmetric-options', dest='gmetric_options', help='Options to pass to gmetric. Defaults to -d 60', type=str, default="-d 60")
    # 
    parser.add_argument('--flush-interval', dest='flush_interval', help='how often to send data to graphite in millis (default: 10000)', type=int, default=10000)
    parser.add_argument('--no-aggregate-counters', dest='no_aggregate_counters', help='should statsd report counters as absolute instead of count/sec', action='store_true')
    parser.add_argument('--global-prefix', dest='global_prefix', help='prefix to append to all stats sent to graphite. Useful for hosted services (ex: Hosted Graphite) or stats namespacing (default: None)', type=str, default=None)
    parser.add_argument('--counters-prefix', dest='counters_prefix', help='prefix to append before sending counter data to graphite (default: stats)', type=str, default='stats')
    parser.add_argument('--timers-prefix', dest='timers_prefix', help='prefix to append before sending timing data to graphite (default: stats.timers)', type=str, default='stats.timers')
    parser.add_argument('-t', '--pct', dest='pct', help='stats pct threshold (default: 90)', type=int, default=90)
    parser.add_argument('-D', '--daemon', dest='daemonize', action='store_true', help='daemonize', default=False)
    parser.add_argument('--pidfile', dest='pidfile', action='store', help='pid file', default='/var/run/pystatsd.pid')
    parser.add_argument('--restart', dest='restart', action='store_true', help='restart a running daemon', default=False)
    parser.add_argument('--stop', dest='stop', action='store_true', help='stop a running daemon', default=False)
    parser.add_argument('--expire', dest='expire', help='time-to-live for old stats (in secs)', type=int, default=0)
    options = parser.parse_args(sys.argv[1:])

    log_level = logging.DEBUG if options.debug else logging.INFO
    logging.basicConfig(level=log_level,format='%(asctime)s [%(levelname)s] %(message)s')

    daemon = ServerDaemon(options.pidfile)
    if options.daemonize:
        daemon.start(options)
    elif options.restart:
        daemon.restart(options)
    elif options.stop:
        daemon.stop()
    else:
        daemon.run(options)

if __name__ == '__main__':
    run_server()

########NEW FILE########
__FILENAME__ = statsd
# statsd.py

# Steve Ivy <steveivy@gmail.com>
# http://monkinetic.com

import logging
import socket
import random
import time


# Sends statistics to the stats daemon over UDP
class Client(object):

    def __init__(self, host='localhost', port=8125, prefix=None):
        """
        Create a new Statsd client.
        * host: the host where statsd is listening, defaults to localhost
        * port: the port where statsd is listening, defaults to 8125

        >>> from pystatsd import statsd
        >>> stats_client = statsd.Statsd(host, port)
        """
        self.host = host
        self.port = int(port)
        self.addr = (socket.gethostbyname(self.host), self.port)
        self.prefix = prefix
        self.log = logging.getLogger("pystatsd.client")
        self.log.addHandler(logging.StreamHandler())
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def timing_since(self, stat, start, sample_rate=1):
        """
        Log timing information as the number of microseconds since the provided time float
        >>> start = time.time()
        >>> # do stuff
        >>> statsd_client.timing_since('some.time', start)
        """
        self.timing(stat, int((time.time() - start) * 1000000), sample_rate)

    def timing(self, stat, time, sample_rate=1):
        """
        Log timing information for a single stat
        >>> statsd_client.timing('some.time',500)
        """
        stats = {stat: "%f|ms" % time}
        self.send(stats, sample_rate)

    def gauge(self, stat, value, sample_rate=1):
        """
        Log gauge information for a single stat
        >>> statsd_client.gauge('some.gauge',42)
        """
        stats = {stat: "%f|g" % value}
        self.send(stats, sample_rate)

    def increment(self, stats, sample_rate=1):
        """
        Increments one or more stats counters
        >>> statsd_client.increment('some.int')
        >>> statsd_client.increment('some.int',0.5)
        """
        self.update_stats(stats, 1, sample_rate=sample_rate)

    # alias
    incr = increment

    def decrement(self, stats, sample_rate=1):
        """
        Decrements one or more stats counters
        >>> statsd_client.decrement('some.int')
        """
        self.update_stats(stats, -1, sample_rate=sample_rate)

    # alias
    decr = decrement

    def update_stats(self, stats, delta, sample_rate=1):
        """
        Updates one or more stats counters by arbitrary amounts
        >>> statsd_client.update_stats('some.int',10)
        """
        if not isinstance(stats, list):
            stats = [stats]

        data = dict((stat, "%s|c" % delta) for stat in stats)
        self.send(data, sample_rate)

    def send(self, data, sample_rate=1):
        """
        Squirt the metrics over UDP
        """

        if self.prefix:
            data = dict((".".join((self.prefix, stat)), value) for stat, value in data.items())

        if sample_rate < 1:
            if random.random() > sample_rate:
                return
            sampled_data = dict((stat, "%s|@%s" % (value, sample_rate))
                                for stat, value in data.items())
        else:
            sampled_data = data

        try:
            [self.udp_sock.sendto(bytes(bytearray("%s:%s" % (stat, value),
                                                  "utf-8")), self.addr)
             for stat, value in sampled_data.items()]
        except:
            self.log.exception("unexpected error")

    def __repr__(self):
        return "<pystatsd.statsd.Client addr=%s prefix=%s>" % (self.addr, self.prefix)

########NEW FILE########
__FILENAME__ = statsd_test
#!/usr/bin/env python

from pystatsd import Client, Server

sc = Client('localhost', 8125)

sc.timing('python_test.time', 500)
sc.increment('python_test.inc_int')
sc.decrement('python_test.decr_int')
sc.gauge('python_test.gauge', 42)

srvr = Server(debug=True)
srvr.serve()

########NEW FILE########
__FILENAME__ = client
import time
import unittest
import mock
import socket
import sys

from pystatsd.statsd import Client


if sys.version_info[0] < 3:
    def bytes(s, encode):
        return s


class ClientBasicsTestCase(unittest.TestCase):
    """
    Tests the basic operations of the client
    """
    def setUp(self):
        self.patchers = []

        socket_patcher = mock.patch('pystatsd.statsd.socket.socket')
        self.mock_socket = socket_patcher.start()
        self.patchers.append(socket_patcher)

        self.client = Client()
        self.addr = (socket.gethostbyname(self.client.host), self.client.port)

    def test_client_create(self):
        host, port = ('example.com', 8888)

        client = Client(
            host=host,
            port=port,
            prefix='pystatsd.tests')
        self.assertEqual(client.host, host)
        self.assertEqual(client.port, port)
        self.assertEqual(client.prefix, 'pystatsd.tests')
        self.assertEqual(client.addr, (socket.gethostbyname(host), port))

    def test_basic_client_incr(self):
        stat = 'pystatsd.unittests.test_basic_client_incr'
        stat_str = stat + ':1|c'

        self.client.increment(stat)

        # thanks tos9 in #python for 'splaining the return_value bit.
        self.mock_socket.return_value.sendto.assert_called_with(
            bytes(stat_str, 'utf-8'), self.addr)

    def test_basic_client_decr(self):
        stat = 'pystatsd.unittests.test_basic_client_decr'
        stat_str = stat + ':-1|c'

        self.client.decrement(stat)

        # thanks tos9 in #python for 'splaining the return_value bit.
        self.mock_socket.return_value.sendto.assert_called_with(
            bytes(stat_str, 'utf-8'), self.addr)

    def test_basic_client_update_stats(self):
        stat = 'pystatsd.unittests.test_basic_client_update_stats'
        stat_str = stat + ':5|c'

        self.client.update_stats(stat, 5)

        # thanks tos9 in #python for 'splaining the return_value bit.
        self.mock_socket.return_value.sendto.assert_called_with(
            bytes(stat_str, 'utf-8'), self.addr)

    def test_basic_client_update_stats_multi(self):
        stats = [
            'pystatsd.unittests.test_basic_client_update_stats',
            'pystatsd.unittests.test_basic_client_update_stats_multi'
        ]

        data = dict((stat, "%s|c" % '5') for stat in stats)

        self.client.update_stats(stats, 5)

        for stat, value in data.items():
            stat_str = stat + value
            # thanks tos9 in #python for 'splaining the return_value bit.
            self.mock_socket.return_value.sendto.assert_call_any(
                bytes(stat_str, 'utf-8'), self.addr)

    def test_basic_client_timing(self):
        stat = 'pystatsd.unittests.test_basic_client_timing.time'
        stat_str = stat + ':5.000000|ms'

        self.client.timing(stat, 5)

        # thanks tos9 in #python for 'splaining the return_value bit.
        self.mock_socket.return_value.sendto.assert_called_with(
            bytes(stat_str, 'utf-8'), self.addr)

    def test_basic_client_timing_since(self):
        ts = (1971, 6, 29, 4, 13, 0, 0, 0, -1)
        now = time.mktime(ts)
        # add 5 seconds
        ts = (1971, 6, 29, 4, 13, 5, 0, 0, -1)
        then = time.mktime(ts)
        mock_time_patcher = mock.patch('time.time', return_value=now)
        mock_time_patcher.start()

        stat = 'pystatsd.unittests.test_basic_client_timing_since.time'
        stat_str = stat + ':-5000000.000000|ms'

        self.client.timing_since(stat, then)

        # thanks tos9 in #python for 'splaining the return_value bit.
        self.mock_socket.return_value.sendto.assert_called_with(
            bytes(stat_str, 'utf-8'), self.addr)

        mock_time_patcher.stop()

    def tearDown(self):
        for patcher in self.patchers:
            patcher.stop()

########NEW FILE########
__FILENAME__ = server
import unittest
import mock

# from pystatsd.statsd import Client
from pystatsd.server import Server


class ServerBasicsTestCase(unittest.TestCase):
    """
    Tests the basic operations of the client
    """
    def setUp(self):
        self.patchers = []

        socket_patcher = mock.patch('pystatsd.statsd.socket.socket')
        self.mock_socket = socket_patcher.start()
        self.patchers.append(socket_patcher)

    def test_server_create(self):
        server = Server()

        if getattr(self, "assertIsNotNone", False):
            self.assertIsNotNone(server)
        else:
            assert server is not None

########NEW FILE########
