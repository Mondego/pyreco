__FILENAME__ = couchbase
#!/usr/bin/env python

"""
Couchbase collector

Refer to the following cbstats documentation for more details:

http://docs.couchbase.com/couchbase-manual-2.1/#cbstats-tool
"""

import os
import sys
import time
import subprocess
import re

from collectors.lib import utils

COLLECTION_INTERVAL = 15
COUCHBASE_INITFILE = "/etc/init.d/couchbase-server"

KEYS = frozenset( [
                  'bucket_active_conns',
                  'cas_hits',
                  'cas_misses',
                  'cmd_get',
                  'cmd_set',
                  'curr_connections',
                  'curr_conns_on_port_11209',
                  'curr_conns_on_port_11210',
                  'ep_queue_size',
                  'ep_num_value_ejects',
                  'ep_num_eject_failures',
                  'ep_oom_errors',
                  'ep_tmp_oom_errors',
                  'get_hits',
                  'get_misses',
                  'mem_used',
                  'total_connections',
                  'total_heap_bytes',
                  'total_free_bytes',
                  'total_allocated_bytes',
                  'total_fragmentation_bytes',
                  'tcmalloc_current_thread_cache_bytes',
                  'tcmalloc_max_thread_cache_bytes',
                  'tcmalloc_unmapped_bytes',
                  ] )

def err(e):
  print >>sys.stderr, e

def find_couchbase_pid():
  """Find out the pid of couchbase"""
  if not os.path.isfile(COUCHBASE_INITFILE):
    return

  try:
    fd = open(COUCHBASE_INITFILE)
    for line in fd:
      if line.startswith("exec"):
        init_script = line.split()[1]
    fd.close()
  except IOError:
    err("Check permission of file (%s)" % COUCHBASE_INITFILE)
    return

  try:
    fd = open(init_script)
    for line in fd:
      if line.startswith("PIDFILE"):
        pid_file = line.split("=")[1].rsplit()[0]
    fd.close()
  except IOError:
    err("Check permission of file (%s)" % init_script)
    return

  try:
    fd = open(pid_file)
    pid = fd.read()
    fd.close()
  except IOError:
    err("Couchbase-server is not running, since no pid file exists")
    return

  return pid.split()[0]

def find_conf_file(pid):
  """Returns config file for couchbase-server."""
  try:
    fd = open('/proc/%s/cmdline' % pid)
  except IOError, e:
    err("Couchbase (pid %s) went away ? %s" % (pid, e))
    return
  try:
    config = fd.read().split("config_path")[1].split("\"")[1]
    return config
  finally:
    fd.close()

def find_bindir_path(config_file):
  """Returns the bin directory path"""
  try:
    fd = open(config_file)
  except IOError, e:
    err("Error for Config file (%s): %s" % (config_file, e))
    return None
  try:
    for line in fd:
      if line.startswith("{path_config_bindir"):
        return line.split(",")[1].split("\"")[1]
  finally:
    fd.close()

def list_bucket(bin_dir):
  """Returns the list of memcached or membase buckets"""
  buckets = []
  if not os.path.isfile("%s/couchbase-cli" % bin_dir):
    return buckets
  cli = ("%s/couchbase-cli" % bin_dir)
  try:
    buck = subprocess.check_output([cli, "bucket-list", "--cluster",
                                    "localhost:8091"])
  except subprocess.CalledProcessError:
    return buckets
  regex = re.compile("[\s\w]+:[\s\w]+$")
  for i in buck.splitlines():
    if not regex.match(i):
      buckets.append(i)
  return buckets

def collect_stats(bin_dir, bucket):
  """Returns statistics related to a particular bucket"""
  if not os.path.isfile("%s/cbstats" % bin_dir):
    return
  cli = ("%s/cbstats" % bin_dir)
  try:
    ts = time.time()
    stats = subprocess.check_output([cli, "localhost:11211", "-b", bucket,
                                     "all"])
  except subprocess.CalledProcessError:
    return
  for stat in stats.splitlines():
    metric = stat.split(":")[0].lstrip(" ")
    value = stat.split(":")[1].lstrip(" \t")
    if metric in KEYS:
      print ("couchbase.%s %i %s bucket=%s" % (metric, ts, value, bucket))

def main():
  utils.drop_privileges()
  pid = find_couchbase_pid()
  if not pid:
    err("Error: Either couchbase-server is not running or file (%s)"
        " doesn't exist" % COUCHBASE_INITFILE)
    return 13

  conf_file = find_conf_file(pid)
  if not conf_file:
    err("Error: Can't find config file (%s)" % conf_file)
    return 13

  bin_dir = find_bindir_path(conf_file)
  if not bin_dir:
    err("Error: Can't find bindir path in config file")
    return 13

  while True:
    # Listing bucket everytime so as to start collecting datapoints
    # of any new bucket.
    buckets = list_bucket(bin_dir)
    for b in buckets:
      collect_stats(bin_dir, b)
    time.sleep(COLLECTION_INTERVAL)

if __name__ == "__main__":
  sys.exit(main())

########NEW FILE########
__FILENAME__ = dfstat
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010-2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
"""disk space and inode counts for TSDB """
#
# dfstat.py
#
# df.bytes.total        total size of fs
# df.bytes.used         bytes used
# df.bytes.percentused  percentage of bytes used
# df.bytes.free         bytes free
# df.inodes.total       number of inodes
# df.inodes.used        number of inodes
# df.inodes.percentused percentage of inodes used
# df.inodes.free        number of inodes

# All metrics are tagged with mount= and fstype=
# This makes it easier to exclude stuff like
# tmpfs mounts from disk usage reports.


import os
import sys
import time

from collectors.lib import utils

COLLECTION_INTERVAL = 60  # seconds

# File system types to ignore
FSTYPE_IGNORE = frozenset([
  "cgroup",
  "debugfs",
  "devtmpfs",
  "rpc_pipefs",
  "rootfs",
])

def main():
  """dfstats main loop"""
  try:
    f_mounts = open("/proc/mounts", "r")
  except IOError, e:
    utils.err("error: can't open /proc/mounts: %s" % e)
    return 13 # Ask tcollector to not respawn us

  utils.drop_privileges()

  while True:
    devices = []
    f_mounts.seek(0)
    ts = int(time.time())

    for line in f_mounts:
      # Docs come from the fstab(5)
      # fs_spec     # Mounted block special device or remote filesystem
      # fs_file     # Mount point
      # fs_vfstype  # File system type
      # fs_mntops   # Mount options
      # fs_freq     # Dump(8) utility flags
      # fs_passno   # Order in which filesystem checks are done at reboot time
      try:
        fs_spec, fs_file, fs_vfstype, fs_mntops, fs_freq, fs_passno = line.split(None)
      except ValueError, e:
        utils.err("error: can't parse line at /proc/mounts: %s" % e)
        continue

      if fs_spec == "none":
        continue
      if fs_vfstype in FSTYPE_IGNORE or fs_vfstype.startswith("fuse."):
        continue
      if fs_file.startswith(("/dev", "/sys", "/proc", "/lib")):
        continue

      # keep /dev/xxx device with shorter fs_file (remove mount binds)
      device_found = False
      if fs_spec.startswith("/dev"):
        for device in devices:
          if fs_spec == device[0]:
            device_found = True
            if len(fs_file) < len(device[1]):
              device[1] = fs_file
            break
        if not device_found:
          devices.append([fs_spec, fs_file, fs_vfstype])
      else:
        devices.append([fs_spec, fs_file, fs_vfstype])


    for device in devices:
      fs_spec, fs_file, fs_vfstype = device
      try:
        r = os.statvfs(fs_file)
      except OSError, e:
        utils.err("error: can't get info for mount point: %s" % fs_file)
        continue

      used = r.f_blocks - r.f_bfree
      percent_used = 100 if r.f_blocks == 0 else used * 100.0 / r.f_blocks
      print("df.bytes.total %d %s mount=%s fstype=%s"
            % (ts, r.f_frsize * r.f_blocks, fs_file, fs_vfstype))
      print("df.bytes.used %d %s mount=%s fstype=%s"
            % (ts, r.f_frsize * used, fs_file, fs_vfstype))
      print("df.bytes.percentused %d %s mount=%s fstype=%s"
            % (ts, percent_used, fs_file, fs_vfstype))
      print("df.bytes.free %d %s mount=%s fstype=%s"
            % (ts, r.f_frsize * r.f_bfree, fs_file, fs_vfstype))

      used = r.f_files - r.f_ffree
      percent_used = 100 if r.f_files == 0 else used * 100.0 / r.f_files
      print("df.inodes.total %d %s mount=%s fstype=%s"
            % (ts, r.f_files, fs_file, fs_vfstype))
      print("df.inodes.used %d %s mount=%s fstype=%s"
            % (ts, used, fs_file, fs_vfstype))
      print("df.inodes.percentused %d %s mount=%s fstype=%s"
            % (ts, percent_used,  fs_file, fs_vfstype))
      print("df.inodes.free %d %s mount=%s fstype=%s"
            % (ts, r.f_ffree, fs_file, fs_vfstype))

    sys.stdout.flush()
    time.sleep(COLLECTION_INTERVAL)


if __name__ == "__main__":
  sys.stdin.close()
  sys.exit(main())

########NEW FILE########
__FILENAME__ = elasticsearch
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2011-2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

"""ElasticSearch collector"""  # Because ES is cool, bonsai cool.
# Tested with ES 0.16.5, 0.17.x, 0.90.1 .

import errno
import httplib
try:
  import json
except ImportError:
  json = None  # Handled gracefully in main.  Not available by default in <2.6
import socket
import sys
import time
import re

from collectors.lib import utils


COLLECTION_INTERVAL = 15  # seconds
DEFAULT_TIMEOUT = 10.0    # seconds
ES_HOST = "localhost"
ES_PORT = 9200  # TCP port on which ES listens.

# regexes to separate differences in version numbers
PRE_VER1 = re.compile(r'^0\.')
VER1 = re.compile(r'^1\.')

STATUS_MAP = {
  "green": 0,
  "yellow": 1,
  "red": 2,
}

def err(msg):
  print >>sys.stderr, msg


class ESError(RuntimeError):
  """Exception raised if we don't get a 200 OK from ElasticSearch."""

  def __init__(self, resp):
    RuntimeError.__init__(self, str(resp))
    self.resp = resp


def request(server, uri):
  """Does a GET request of the given uri on the given HTTPConnection."""
  server.request("GET", uri)
  resp = server.getresponse()
  if resp.status != httplib.OK:
    raise ESError(resp)
  return json.loads(resp.read())


def cluster_health(server):
  return request(server, "/_cluster/health")


def cluster_state(server):
  return request(server, "/_cluster/state"
                 + "?filter_routing_table=true&filter_metadata=true&filter_blocks=true")


def node_status(server):
  return request(server, "/")


def node_stats(server, version):
  # API changed in v1.0
  if PRE_VER1.match(version):
    url = "/_cluster/nodes/_local/stats"
  # elif VER1.match(version):
  #   url = "/_nodes/_local/stats"
  else:
    url = "/_nodes/_local/stats"
  return request(server, url)


def main(argv):
  utils.drop_privileges()
  socket.setdefaulttimeout(DEFAULT_TIMEOUT)
  server = httplib.HTTPConnection(ES_HOST, ES_PORT)
  try:
    server.connect()
  except socket.error, (erno, e):
    if erno == errno.ECONNREFUSED:
      return 13  # No ES running, ask tcollector to not respawn us.
    raise
  if json is None:
    err("This collector requires the `json' Python module.")
    return 1

  status = node_status(server)
  version = status["version"]["number"]
  nstats = node_stats(server, version)
  cluster_name = nstats["cluster_name"]
  nodeid, nstats = nstats["nodes"].popitem()

  ts = None
  def printmetric(metric, value, **tags):
    if tags:
      tags = " " + " ".join("%s=%s" % (name, value)
                            for name, value in tags.iteritems())
    else:
      tags = ""
    print ("elasticsearch.%s %d %s cluster=%s%s"
           % (metric, ts, value, cluster_name, tags))

  while True:
    ts = int(time.time())
    nstats = node_stats(server, version)
    # Check that the node's identity hasn't changed in the mean time.
    if nstats["cluster_name"] != cluster_name:
      err("cluster_name changed from %r to %r"
          % (cluster_name, nstats["cluster_name"]))
      return 1
    this_nodeid, nstats = nstats["nodes"].popitem()
    if this_nodeid != nodeid:
      err("node ID changed from %r to %r" % (nodeid, this_nodeid))
      return 1

    is_master = nodeid == cluster_state(server)["master_node"]
    printmetric("is_master", int(is_master))
    if is_master:
      ts = int(time.time())  # In case last call took a while.
      cstats = cluster_health(server)
      for stat, value in cstats.iteritems():
        if stat == "status":
          value = STATUS_MAP.get(value, -1)
        elif not utils.is_numeric(value):
          continue
        printmetric("cluster." + stat, value)

    if "os" in nstats:
       ts = nstats["os"]["timestamp"] / 1000  # ms -> s
    if "timestamp" in nstats:
       ts = nstats["timestamp"] / 1000  # ms -> s

    if "indices" in nstats:
       indices = nstats["indices"]
       if  "docs" in indices:
          printmetric("num_docs", indices["docs"]["count"])
       if  "store" in indices:
          printmetric("indices.size", indices["store"]["size_in_bytes"])
       if  "indexing" in indices:
          d = indices["indexing"]
          printmetric("indexing.index_total", d["index_total"])
          printmetric("indexing.index_time", d["index_time_in_millis"])
          printmetric("indexing.index_current", d["index_current"])
          printmetric("indexing.delete_total", d["delete_total"])
          printmetric("indexing.delete_time_in_millis", d["delete_time_in_millis"])
          printmetric("indexing.delete_current", d["delete_current"])
          del d
       if  "get" in indices:
          d = indices["get"]
          printmetric("get.total", d["total"])
          printmetric("get.time", d["time_in_millis"])
          printmetric("get.exists_total", d["exists_total"])
          printmetric("get.exists_time", d["exists_time_in_millis"])
          printmetric("get.missing_total", d["missing_total"])
          printmetric("get.missing_time", d["missing_time_in_millis"])
          del d
       if  "search" in indices:
          d = indices["search"]
          printmetric("search.query_total", d["query_total"])
          printmetric("search.query_time", d["query_time_in_millis"])
          printmetric("search.query_current", d["query_current"])
          printmetric("search.fetch_total", d["fetch_total"])
          printmetric("search.fetch_time", d["fetch_time_in_millis"])
          printmetric("search.fetch_current", d["fetch_current"])
          del d
       if "cache" in indices:
          d = indices["cache"]
          printmetric("cache.field.evictions", d["field_evictions"])
          printmetric("cache.field.size", d["field_size_in_bytes"])
          printmetric("cache.filter.count", d["filter_count"])
          printmetric("cache.filter.evictions", d["filter_evictions"])
          printmetric("cache.filter.size", d["filter_size_in_bytes"])
          del d
       if "merges" in indices:
          d = indices["merges"]
          printmetric("merges.current", d["current"])
          printmetric("merges.total", d["total"])
          printmetric("merges.total_time", d["total_time_in_millis"] / 1000.)
          del d
       del indices
    if "process" in nstats:
       process = nstats["process"]
       ts = process["timestamp"] / 1000  # ms -> s
       open_fds = process.get("open_file_descriptors")  # ES 0.17
       if open_fds is None:
         open_fds = process.get("fd")  # ES 0.16
         if open_fds is not None:
           open_fds = open_fds["total"]
       if open_fds is not None:
         printmetric("process.open_file_descriptors", open_fds)
       if "cpu" in process:
          d = process["cpu"]
          printmetric("process.cpu.percent", d["percent"])
          printmetric("process.cpu.sys", d["sys_in_millis"] / 1000.)
          printmetric("process.cpu.user", d["user_in_millis"] / 1000.)
          del d
       if "mem" in process:
          d = process["mem"]
          printmetric("process.mem.resident", d["resident_in_bytes"])
          printmetric("process.mem.shared", d["share_in_bytes"])
          printmetric("process.mem.total_virtual", d["total_virtual_in_bytes"])
          del d
       del process
    if "jvm" in nstats:
       jvm = nstats["jvm"]
       ts = jvm["timestamp"] / 1000  # ms -> s
       if "mem" in jvm:
          d = jvm["mem"]
          printmetric("jvm.mem.heap_used", d["heap_used_in_bytes"])
          printmetric("jvm.mem.heap_committed", d["heap_committed_in_bytes"])
          printmetric("jvm.mem.non_heap_used", d["non_heap_used_in_bytes"])
          printmetric("jvm.mem.non_heap_committed", d["non_heap_committed_in_bytes"])
          del d
       if "threads" in jvm:
          d = jvm["threads"]
          printmetric("jvm.threads.count", d["count"])
          printmetric("jvm.threads.peak_count", d["peak_count"])
          del d
       for gc, d in jvm["gc"]["collectors"].iteritems():
         printmetric("jvm.gc.collection_count", d["collection_count"], gc=gc)
         printmetric("jvm.gc.collection_time",
                     d["collection_time_in_millis"] / 1000., gc=gc)
       del jvm
       del d
    if "network" in nstats:
       for stat, value in nstats["network"]["tcp"].iteritems():
         if utils.is_numeric(value):
           printmetric("network.tcp." + stat, value)
       for stat, value in nstats["transport"].iteritems():
         if utils.is_numeric(value):
           printmetric("transport." + stat, value)
    # New in ES 0.17:
    for stat, value in nstats.get("http", {}).iteritems():
      if utils.is_numeric(value):
        printmetric("http." + stat, value)
    del nstats
    time.sleep(COLLECTION_INTERVAL)


if __name__ == "__main__":
  sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = graphite_bridge
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
"""Listens on a local TCP socket for incoming metrics in the graphite protocol."""

from __future__ import print_function

import sys
from collectors.lib import utils
import SocketServer
import threading

try:
  from collectors.etc import graphite_bridge_conf
except ImportError:
  graphite_bridge_conf = None

HOST = '127.0.0.1'
PORT = 2003
SIZE = 8192

class GraphiteServer(SocketServer.ThreadingTCPServer):
    allow_reuse_address = True

    print_lock = threading.Lock()

class GraphiteHandler(SocketServer.BaseRequestHandler):

    def handle_line(self, line):
        line_parts = line.split()
        with self.server.print_lock:
            if len(line_parts) != 3:
                print("Bad data:", line, file=sys.stderr)
            else:
                print(line_parts[0], line_parts[2], line_parts[1])


    def handle(self):
        data = ''
        while True:
            new_data = self.request.recv(SIZE)
            if not new_data:
                break
            data += new_data

            if "\n" in data:
                line_data, data = data.rsplit("\n", 1)
                lines = line_data.splitlines()

                for line in lines:
                    self.handle_line(line)

        self.request.close()


def main():
    if not (graphite_bridge_conf and graphite_bridge_conf.enabled()):
      sys.exit(13)
    utils.drop_privileges()

    server = GraphiteServer((HOST, PORT), GraphiteHandler)
    server.daemon_threads = True
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()

sys.exit(0)

########NEW FILE########
__FILENAME__ = hadoop_datanode
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

import sys
import time

try:
    import json
except ImportError:
    json = None

from collectors.lib import utils
from collectors.lib.hadoop_http import HadoopHttp


REPLACEMENTS = {
    "datanodeactivity-": ["activity"],
    "fsdatasetstate-ds-": ["fs_data_set_state"],
    "rpcdetailedactivityforport": ["rpc_activity"],
    "rpcactivityforport": ["rpc_activity"]
}


class HadoopDataNode(HadoopHttp):
    """
    Class that will retrieve metrics from an Apache Hadoop DataNode's jmx page.

    This requires Apache Hadoop 1.0+ or Hadoop 2.0+.
    Anything that has the jmx page will work but the best results will com from Hadoop 2.1.0+
    """

    def __init__(self):
        super(HadoopDataNode, self).__init__('hadoop', 'datanode', 'localhost', 50075)

    def emit(self):
        current_time = int(time.time())
        metrics = self.poll()
        for context, metric_name, value in metrics:
            for k, v in REPLACEMENTS.iteritems():
                if any(c.startswith(k) for c in context):
                    context = v
            self.emit_metric(context, current_time, metric_name, value)


def main(args):
    utils.drop_privileges()
    if json is None:
        utils.err("This collector requires the `json' Python module.")
        return 13  # Ask tcollector not to respawn us
    datanode_service = HadoopDataNode()
    while True:
        datanode_service.emit()
        time.sleep(15)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))


########NEW FILE########
__FILENAME__ = hadoop_namenode
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

import sys
import time

try:
    import json
except ImportError:
    json = None

from collectors.lib import utils
from collectors.lib.hadoop_http import HadoopHttp


REPLACEMENTS = {
    "rpcdetailedactivityforport": ["rpc_activity"],
    "rpcactivityforport": ["rpc_activity"]
}


class HadoopNameNode(HadoopHttp):
    """
    Class that will retrieve metrics from an Apache Hadoop DataNode's jmx page.

    This requires Apache Hadoop 1.0+ or Hadoop 2.0+.
    Anything that has the jmx page will work but the best results will com from Hadoop 2.1.0+
    """

    def __init__(self):
        super(HadoopNameNode, self).__init__('hadoop', 'namenode', 'localhost', 50070)

    def emit(self):
        current_time = int(time.time())
        metrics = self.poll()
        for context, metric_name, value in metrics:
            for k, v in REPLACEMENTS.iteritems():
                if any(c.startswith(k) for c in context):
                    context = v
            self.emit_metric(context, current_time, metric_name, value)


def main(args):
    utils.drop_privileges()
    if json is None:
        utils.err("This collector requires the `json' Python module.")
        return 13  # Ask tcollector not to respawn us
    name_node_service = HadoopNameNode()
    while True:
        name_node_service.emit()
        time.sleep(90)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))


########NEW FILE########
__FILENAME__ = haproxy
#!/usr/bin/env python
# This file is part of tcollector.
# Copyright (C) 2013 The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details. You should have received a copy
# of the GNU Lesser General Public License along with this program. If not,
# see <http://www.gnu.org/licenses/>.

# Script uses UNIX socket opened by haproxy, you need to setup one with
# "stats socket" config parameter.
#
# You need to ensure that "stats timeout" (socket timeout) is big
# enough to work well with collector COLLECTION_INTERVAL constant.
# The default timeout on the "stats socket" is set to 10 seconds!
#
# See haproxy documentation for details:
# http://haproxy.1wt.eu/download/1.4/doc/configuration.txt
# section 3.1. Process management and security.

"""HAproxy collector """

import os
import socket
import sys
import time
import stat
import subprocess
from collectors.lib import utils

COLLECTION_INTERVAL = 15

def haproxy_pid():
  """Finds out the pid of haproxy process"""
  try:
     pid = subprocess.check_output(["pidof", "haproxy"])
  except subprocess.CalledProcessError:
     return None
  return pid.rstrip()

def find_conf_file(pid):
  """Returns the conf file of haproxy."""
  try:
     output = subprocess.check_output(["ps", "--no-headers", "-o", "cmd", pid])
  except subprocess.CalledProcessError, e:
     utils.err("HAProxy (pid %s) went away? %s" % (pid, e))
     return None
  return output.split("-f")[1].split()[0]

def find_sock_file(conf_file):
  """Returns the unix socket file of haproxy."""
  try:
    fd = open(conf_file)
  except IOError, e:
    utils.err("Error: %s. Config file path is relative: %s" % (e, conf_file))
    return None
  try:
    for line in fd:
      if line.lstrip(" \t").startswith("stats socket"):
        sock_file = line.split()[2]
        if utils.is_sockfile(sock_file):
          return sock_file
  finally:
    fd.close()

def collect_stats(sock):
  """Collects stats from haproxy unix domain socket"""
  sock.send("show stat\n")
  stats = sock.recv(10240)

  ts = time.time()
  for line in stats.split("\n"):
    var = line.split(",")
    if var[0]:
      # skip ready for next command value "> "
      if var[0] == "> ":
        continue
      if var[1] in ("svname", "BACKEND", "FRONTEND"):
        continue
      print ("haproxy.current_sessions %i %s server=%s cluster=%s"
             % (ts, var[4], var[1], var[0]))
      print ("haproxy.session_rate %i %s server=%s cluster=%s"
             % (ts, var[33], var[1], var[0]))

def main():
  pid = haproxy_pid()
  if not pid:
    utils.err("Error: HAProxy is not running")
    return 13  # Ask tcollector to not respawn us.

  conf_file = find_conf_file(pid)
  if not conf_file:
    return 13

  sock_file = find_sock_file(conf_file)
  if sock_file is None:
    utils.err("Error: HAProxy is not listening on any unix domain socket")
    return 13

  sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
  sock.connect(sock_file)

  # put haproxy to interactive mode, otherwise haproxy closes
  # connection after first command.
  # See haproxy documentation section 9.2. Unix Socket commands.
  sock.send("prompt\n")

  while True:
    collect_stats(sock)
    time.sleep(COLLECTION_INTERVAL)

if __name__ == "__main__":
  sys.exit(main())

########NEW FILE########
__FILENAME__ = hbase_master
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

import sys
import time

try:
    import json
except ImportError:
    json = None

from collectors.lib import utils
from collectors.lib.hadoop_http import HadoopHttp


EXCLUDED_CONTEXTS = ('regionserver', 'regions', )


class HBaseMaster(HadoopHttp):
    """
    Class to get metrics from Apache HBase's master

    Require HBase 0.96.0+
    """

    def __init__(self):
        super(HBaseMaster, self).__init__('hbase', 'master', 'localhost', 60010)

    def emit(self):
        current_time = int(time.time())
        metrics = self.poll()
        for context, metric_name, value in metrics:
            if any(c in EXCLUDED_CONTEXTS for c in context):
                continue
            self.emit_metric(context, current_time, metric_name, value)


def main(args):
    utils.drop_privileges()
    if json is None:
        utils.err("This collector requires the `json' Python module.")
        return 13  # Ask tcollector not to respawn us
    hbase_service = HBaseMaster()
    while True:
        hbase_service.emit()
        time.sleep(90)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))


########NEW FILE########
__FILENAME__ = hbase_regionserver
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

import time
import re

try:
    import json
except ImportError:
    json = None

from collectors.lib import utils
from collectors.lib.hadoop_http import HadoopHttp

EMIT_REGION = True

EXCLUDED_CONTEXTS = ("master")
REGION_METRIC_PATTERN = re.compile(r"[N|n]amespace_(.*)_table_(.*)_region_(.*)_metric_(.*)")

class HBaseRegionserver(HadoopHttp):
    def __init__(self):
        super(HBaseRegionserver, self).__init__("hbase", "regionserver", "localhost", 60030)

    def emit_region_metric(self, context, current_time, full_metric_name, value):
	match = REGION_METRIC_PATTERN.match(full_metric_name)
        if not match:
            utils.err("Error splitting %s" % full_metric_name)
            return

        namespace = match.group(1)
        table = match.group(2)
        region = match.group(3)
        metric_name = match.group(4)
        tag_dict = {"namespace": namespace, "table": table, "region": region}

        if any( not v for k,v in tag_dict.iteritems()):
            utils.err("Error splitting %s", full_metric_name)
        else:
            self.emit_metric(context, current_time, metric_name, value, tag_dict)

    def emit(self):
        """
        Emit metrics from a HBase regionserver.

        This will only emit per region metrics is EMIT_REGION is set to true
        """
        current_time = int(time.time())
        metrics = self.poll()
        for context, metric_name, value in metrics:
            if any( c in EXCLUDED_CONTEXTS for c in context):
                continue

            if any(c == "regions" for c in context):
                if EMIT_REGION:
                    self.emit_region_metric(context, current_time, metric_name, value)
            else:
                self.emit_metric(context, current_time, metric_name, value)


def main(args):
    utils.drop_privileges()
    if json is None:
        utils.err("This collector requires the `json' Python module.")
        return 13  # Ask tcollector not to respawn us
    hbase_service = HBaseRegionserver()
    while True:
        hbase_service.emit()
        time.sleep(15)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))


########NEW FILE########
__FILENAME__ = ifstat
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010-2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#
"""network interface stats for TSDB"""

import sys
import time
import re

from collectors.lib import utils

interval = 15 # seconds

# /proc/net/dev has 16 fields, 8 for receive and 8 for transmit,
# defined below.
# So we can aggregate up the total bytes, packets, etc
# we tag each metric with direction=in or =out
# and iface=

# The new naming scheme of network interfaces
# Lan-On-Motherboard interfaces
# em<port number>_< virtual function instance / NPAR Index >
#
# PCI add-in interfaces
# p<slot number>p<port number>_<virtual function instance / NPAR Index>


FIELDS = ("bytes", "packets", "errs", "dropped",
          "fifo.errs", "frame.errs", "compressed", "multicast",
          "bytes", "packets", "errs", "dropped",
          "fifo.errs", "collisions", "carrier.errs", "compressed")


def main():
    """ifstat main loop"""

    f_netdev = open("/proc/net/dev")
    utils.drop_privileges()

    # We just care about ethN and emN interfaces.  We specifically
    # want to avoid bond interfaces, because interface
    # stats are still kept on the child interfaces when
    # you bond.  By skipping bond we avoid double counting.
    while True:
        f_netdev.seek(0)
        ts = int(time.time())
        for line in f_netdev:
            m = re.match("\s+(eth\d+|em\d+_\d+/\d+|em\d+_\d+|em\d+|"
                         "p\d+p\d+_\d+/\d+|p\d+p\d+_\d+|p\d+p\d+):(.*)", line)
            if not m:
                continue
            intf = m.group(1)
            stats = m.group(2).split(None)
            def direction(i):
                if i >= 8:
                    return "out"
                return "in"
            for i in xrange(16):
                print ("proc.net.%s %d %s iface=%s direction=%s"
                       % (FIELDS[i], ts, stats[i], intf, direction(i)))

        sys.stdout.flush()
        time.sleep(interval)

if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = iostat
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

"""iostat statistics for TSDB"""

# data is from /proc/diskstats

# Calculate disk statistics.  We handle 2.6 kernel output only, both
# pre-2.6.25 and post (which added back per-partition disk stats).
# (diskstats output significantly changed from 2.4).
# The fields (from iostats.txt) are mainly rate counters
# (either number of operations or number of milliseconds doing a
# particular operation), so let's just let TSD do the rate
# calculation for us.
#
# /proc/diskstats has 11 stats for a given device
# these are all rate counters except ios_in_progress
# .read_requests       Number of reads completed
# .read_merged         Number of reads merged
# .read_sectors        Number of sectors read
# .msec_read           Time in msec spent reading
# .write_requests      Number of writes completed
# .write_merged        Number of writes merged
# .write_sectors       Number of sectors written
# .msec_write          Time in msec spent writing
# .ios_in_progress     Number of I/O operations in progress
# .msec_total          Time in msec doing I/O
# .msec_weighted_total Weighted time doing I/O (multiplied by ios_in_progress)

# in 2.6.25 and later, by-partition stats are reported same as disks
# in 2.6 before 2.6.25, partitions have 4 stats per partition
# .read_issued
# .read_sectors
# .write_issued
# .write_sectors
# For partitions, these *_issued are counters collected before
# requests are merged, so aren't the same as *_requests (which is
# post-merge, which more closely represents represents the actual
# number of disk transactions).

# Given that diskstats provides both per-disk and per-partition data,
# for TSDB purposes we want to put them under different metrics (versus
# the same metric and different tags).  Otherwise, if you look at a
# given metric, the data for a given box will be double-counted, since
# a given operation will increment both the disk series and the
# partition series.  To fix this, we output by-disk data to iostat.disk.*
# and by-partition data to iostat.part.*.

# TODO: Add additional tags to map partitions/disks back to mount
# points/swap so you can (for example) plot just swap partition
# activity or /var/lib/mysql partition activity no matter which
# disk/partition this happens to be.  This is nontrivial, especially
# when you have to handle mapping of /dev/mapper to dm-N, pulling out
# swap partitions from /proc/swaps, etc.

# TODO: add some generated stats from iostat -x like svctm, await,
# %util.  These need to pull in cpu idle counters from /proc.


import sys
import time
import os
import re

from collectors.lib import utils

COLLECTION_INTERVAL = 60  # seconds

# Docs come from the Linux kernel's Documentation/iostats.txt
FIELDS_DISK = (
    "read_requests",        # Total number of reads completed successfully.
    "read_merged",          # Adjacent read requests merged in a single req.
    "read_sectors",         # Total number of sectors read successfully.
    "msec_read",            # Total number of ms spent by all reads.
    "write_requests",       # total number of writes completed successfully.
    "write_merged",         # Adjacent write requests merged in a single req.
    "write_sectors",        # total number of sectors written successfully.
    "msec_write",           # Total number of ms spent by all writes.
    "ios_in_progress",      # Number of actual I/O requests currently in flight.
    "msec_total",           # Amount of time during which ios_in_progress >= 1.
    "msec_weighted_total",  # Measure of recent I/O completion time and backlog.
    )

FIELDS_PART = ("read_issued",
               "read_sectors",
               "write_issued",
               "write_sectors",
              )

def read_uptime():
    try:
        f_uptime = open("/proc/uptime", "r")
        line = f_uptime.readline()

        return line.split(None)
    finally:
        f_uptime.close();

def get_system_hz():
    """Return system hz use SC_CLK_TCK."""
    ticks = os.sysconf(os.sysconf_names['SC_CLK_TCK'])

    if ticks == -1:
        return 100
    else:
        return ticks

def is_device(device_name, allow_virtual):
    """Test whether given name is a device or a partition, using sysfs."""
    device_name = re.sub('/', '!', device_name)

    if allow_virtual:
        devicename = "/sys/block/" + device_name + "/device"
    else:
        devicename = "/sys/block/" + device_name

    return (os.access(devicename, os.F_OK))

def main():
    """iostats main loop."""
    f_diskstats = open("/proc/diskstats", "r")
    HZ = get_system_hz()
    itv = 1.0
    utils.drop_privileges()

    while True:
        f_diskstats.seek(0)
        ts = int(time.time())
        itv = read_uptime()[1]
        for line in f_diskstats:
            # maj, min, devicename, [list of stats, see above]
            values = line.split(None)
            # shortcut the deduper and just skip disks that
            # haven't done a single read.  This elimiates a bunch
            # of loopback, ramdisk, and cdrom devices but still
            # lets us report on the rare case that we actually use
            # a ramdisk.
            if values[3] == "0":
                continue

            if int(values[1]) % 16 == 0 and int(values[0]) > 1:
                metric = "iostat.disk."
            else:
                metric = "iostat.part."

            device = values[2]
            if len(values) == 14:
                # full stats line
                for i in range(11):
                    print ("%s%s %d %s dev=%s"
                           % (metric, FIELDS_DISK[i], ts, values[i+3],
                              device))

                ret = is_device(device, 0)
                if ret:
                    stats = dict(zip(FIELDS_DISK, values[3:]))
                    nr_ios = float(stats.get("read_requests")) + float(stats.get("write_requests"))
                    tput = ((nr_ios) * float(HZ) / float(itv))
                    util = (float(stats.get("msec_total")) * float(HZ) / float(itv))
                    if tput:
                        svctm = util / tput
                    else:
                        svctm = 0.00
                    print ("%s%s %d %.2f dev=%s" % (metric, "svctm", ts, svctm, device))

            elif len(values) == 7:
                # partial stats line
                for i in range(4):
                    print ("%s%s %d %s dev=%s"
                           % (metric, FIELDS_PART[i], ts, values[i+3],
                              device))
            else:
                print >> sys.stderr, "Cannot parse /proc/diskstats line: ", line
                continue

        sys.stdout.flush()
        time.sleep(COLLECTION_INTERVAL)



if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = mongo
#!/usr/bin/python
#
# mongo.py -- a MongoDB collector for tcollector/OpenTSDB
# Copyright (C) 2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

import sys
import time
try:
    import pymongo
except ImportError:
    pymongo = None  # This is handled gracefully in main()

from collectors.lib import utils

HOST = 'localhost'
PORT = 27017
INTERVAL = 15
METRICS = (
    'backgroundFlushing.average_ms',
    'backgroundFlushing.flushes',
    'backgroundFlushing.total_ms',
    'connections.available',
    'connections.current',
    'cursors.totalOpen',
    'cursors.timedOut',
    'dur.commits',
    'dur.commitsInWriteLock',
    'dur.compression',
    'dur.earlyCommits',
    'dur.journaledMB',
    'dur.writeToDataFilesMB',
    'extra_info.heap_usage_bytes',
    'extra_info.page_faults',
    'globalLock.lockTime',
    'globalLock.totalTime',
    'indexCounters.btree.accesses',
    'indexCounters.btree.hits',
    'indexCounters.btree.missRatio',
    'indexCounters.btree.misses',
    'indexCounters.btree.resets',
    'mem.resident',
    'mem.virtual',
    'mem.mapped',
    'network.bytesIn',
    'network.bytesOut',
    'network.numRequests',
)
TAG_METRICS = (
    ('asserts',     ('msg', 'regular', 'user', 'warning')),
    ('opcounters',  ('command', 'delete', 'getmore', 'insert', 'query', 'update')),
)

def main():
    utils.drop_privileges()
    if pymongo is None:
       print >>sys.stderr, "error: Python module `pymongo' is missing"
       return 13

    c = pymongo.Connection(host=HOST, port=PORT)

    while True:
        res = c.admin.command('serverStatus')
        ts = int(time.time())

        for base_metric, tags in TAG_METRICS:
            for tag in tags:
                print 'mongo.%s %d %s type=%s' % (base_metric, ts,
                                                  res[base_metric][tag], tag)
        for metric in METRICS:
            cur = res
            try:
                for m in metric.split('.'):
                    cur = cur[m]
            except KeyError:
                continue
            print 'mongo.%s %d %s' % (metric, ts, cur)

        sys.stdout.flush()
        time.sleep(INTERVAL)

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = mysql
#!/usr/bin/env python
# This file is part of tcollector.
# Copyright (C) 2011  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
"""Collector for MySQL."""

import errno
import os
import re
import socket
import sys
import time

try:
  import MySQLdb
except ImportError:
  MySQLdb = None  # This is handled gracefully in main()

from collectors.etc import mysqlconf
from collectors.lib import utils

COLLECTION_INTERVAL = 15  # seconds
CONNECT_TIMEOUT = 2  # seconds
# How frequently we try to find new databases.
DB_REFRESH_INTERVAL = 60  # seconds
# Usual locations where to find the default socket file.
DEFAULT_SOCKFILES = set([
  "/tmp/mysql.sock",                  # MySQL's own default.
  "/var/lib/mysql/mysql.sock",        # RH-type / RPM systems.
  "/var/run/mysqld/mysqld.sock",      # Debian-type systems.
])
# Directories under which to search additional socket files.
SEARCH_DIRS = [
  "/var/lib/mysql",
]

class DB(object):
  """Represents a MySQL server (as we can monitor more than 1 MySQL)."""

  def __init__(self, sockfile, dbname, db, cursor, version):
    """Constructor.

    Args:
      sockfile: Path to the socket file.
      dbname: Name of the database for that socket file.
      db: A MySQLdb connection opened to that socket file.
      cursor: A cursor acquired from that connection.
      version: What version is this MySQL running (from `SELECT VERSION()').
    """
    self.sockfile = sockfile
    self.dbname = dbname
    self.db = db
    self.cursor = cursor
    self.version = version
    self.master = None
    self.slave_bytes_executed = None
    self.relay_bytes_relayed = None

    version = version.split(".")
    try:
      self.major = int(version[0])
      self.medium = int(version[1])
    except (ValueError, IndexError), e:
      self.major = self.medium = 0

  def __str__(self):
    return "DB(%r, %r, version=%r)" % (self.sockfile, self.dbname,
                                       self.version)

  def __repr__(self):
    return self.__str__()

  def isShowGlobalStatusSafe(self):
    """Returns whether or not SHOW GLOBAL STATUS is safe to run."""
    # We can't run SHOW GLOBAL STATUS on versions prior to 5.1 because it
    # locks the entire database for too long and severely impacts traffic.
    return self.major > 5 or (self.major == 5 and self.medium >= 1)

  def query(self, sql):
    """Executes the given SQL statement and returns a sequence of rows."""
    assert self.cursor, "%s already closed?" % (self,)
    try:
      self.cursor.execute(sql)
    except MySQLdb.OperationalError, (errcode, msg):
      if errcode != 2006:  # "MySQL server has gone away"
        raise
      self._reconnect()
    return self.cursor.fetchall()

  def close(self):
    """Closes the connection to this MySQL server."""
    if self.cursor:
      self.cursor.close()
      self.cursor = None
    if self.db:
      self.db.close()
      self.db = None

  def _reconnect(self):
    """Reconnects to this MySQL server."""
    self.close()
    self.db = mysql_connect(self.sockfile)
    self.cursor = self.db.cursor()


def mysql_connect(sockfile):
  """Connects to the MySQL server using the specified socket file."""
  user, passwd = mysqlconf.get_user_password(sockfile)
  return MySQLdb.connect(unix_socket=sockfile,
                         connect_timeout=CONNECT_TIMEOUT,
                         user=user, passwd=passwd)


def todict(db, row):
  """Transforms a row (returned by DB.query) into a dict keyed by column names.

  Args:
    db: The DB instance from which this row was obtained.
    row: A row as returned by DB.query
  """
  d = {}
  for i, field in enumerate(db.cursor.description):
    column = field[0].lower()  # Lower-case to normalize field names.
    d[column] = row[i]
  return d

def get_dbname(sockfile):
  """Returns the name of the DB based on the path to the socket file."""
  if sockfile in DEFAULT_SOCKFILES:
    return "default"
  m = re.search("/mysql-(.+)/[^.]+\.sock$", sockfile)
  if not m:
    utils.err("error: couldn't guess the name of the DB for " + sockfile)
    return None
  return m.group(1)


def find_sockfiles():
  """Returns a list of paths to socket files to monitor."""
  paths = []
  # Look for socket files.
  for dir in SEARCH_DIRS:
    if not os.path.isdir(dir):
      continue
    for name in os.listdir(dir):
      subdir = os.path.join(dir, name)
      if not os.path.isdir(subdir):
        continue
      for subname in os.listdir(subdir):
        path = os.path.join(subdir, subname)
        if utils.is_sockfile(path):
          paths.append(path)
          break  # We only expect 1 socket file per DB, so get out.
  # Try the default locations.
  for sockfile in DEFAULT_SOCKFILES:
    if not utils.is_sockfile(sockfile):
      continue
    paths.append(sockfile)
  return paths


def find_databases(dbs=None):
  """Returns a map of dbname (string) to DB instances to monitor.

  Args:
    dbs: A map of dbname (string) to DB instances already monitored.
      This map will be modified in place if it's not None.
  """
  sockfiles = find_sockfiles()
  if dbs is None:
    dbs = {}
  for sockfile in sockfiles:
    dbname = get_dbname(sockfile)
    if dbname in dbs:
      continue
    if not dbname:
      continue
    try:
      db = mysql_connect(sockfile)
      cursor = db.cursor()
      cursor.execute("SELECT VERSION()")
    except (EnvironmentError, EOFError, RuntimeError, socket.error,
            MySQLdb.MySQLError), e:
      utils.err("Couldn't connect to %s: %s" % (sockfile, e))
      continue
    version = cursor.fetchone()[0]
    dbs[dbname] = DB(sockfile, dbname, db, cursor, version)
  return dbs


def now():
  return int(time.time())


def isyes(s):
  if s.lower() == "yes":
    return 1
  return 0


def collectInnodbStatus(db):
  """Collects and prints InnoDB stats about the given DB instance."""
  ts = now()
  def printmetric(metric, value, tags=""):
    print "mysql.%s %d %s schema=%s%s" % (metric, ts, value, db.dbname, tags)

  innodb_status = db.query("SHOW ENGINE INNODB STATUS")[0][2]
  m = re.search("^(\d{6}\s+\d{1,2}:\d\d:\d\d) INNODB MONITOR OUTPUT$",
                innodb_status, re.M)
  if m:  # If we have it, try to use InnoDB's own timestamp.
    ts = int(time.mktime(time.strptime(m.group(1), "%y%m%d %H:%M:%S")))

  line = None
  def match(regexp):
    return re.match(regexp, line)

  for line in innodb_status.split("\n"):
    # SEMAPHORES
    m = match("OS WAIT ARRAY INFO: reservation count (\d+), signal count (\d+)")
    if m:
      printmetric("innodb.oswait_array.reservation_count", m.group(1))
      printmetric("innodb.oswait_array.signal_count", m.group(2))
      continue
    m = match("Mutex spin waits (\d+), rounds (\d+), OS waits (\d+)")
    if m:
      printmetric("innodb.locks.spin_waits", m.group(1), " type=mutex")
      printmetric("innodb.locks.rounds", m.group(2), " type=mutex")
      printmetric("innodb.locks.os_waits", m.group(3), " type=mutex")
      continue
    m = match("RW-shared spins (\d+), OS waits (\d+);"
              " RW-excl spins (\d+), OS waits (\d+)")
    if m:
      printmetric("innodb.locks.spin_waits", m.group(1), " type=rw-shared")
      printmetric("innodb.locks.os_waits", m.group(2), " type=rw-shared")
      printmetric("innodb.locks.spin_waits", m.group(3), " type=rw-exclusive")
      printmetric("innodb.locks.os_waits", m.group(4), " type=rw-exclusive")
      continue
    # INSERT BUFFER AND ADAPTIVE HASH INDEX
    # TODO(tsuna): According to the code in ibuf0ibuf.c, this line and
    # the following one can appear multiple times.  I've never seen this.
    # If that happens, we need to aggregate the values here instead of
    # printing them directly.
    m = match("Ibuf: size (\d+), free list len (\d+), seg size (\d+),")
    if m:
      printmetric("innodb.ibuf.size", m.group(1))
      printmetric("innodb.ibuf.free_list_len", m.group(2))
      printmetric("innodb.ibuf.seg_size", m.group(3))
      continue
    m = match("(\d+) inserts, (\d+) merged recs, (\d+) merges")
    if m:
      printmetric("innodb.ibuf.inserts", m.group(1))
      printmetric("innodb.ibuf.merged_recs", m.group(2))
      printmetric("innodb.ibuf.merges", m.group(3))
      continue
    # ROW OPERATIONS
    m = match("\d+ queries inside InnoDB, (\d+) queries in queue")
    if m:
      printmetric("innodb.queries_queued", m.group(1))
      continue
    m = match("(\d+) read views open inside InnoDB")
    if m:
      printmetric("innodb.opened_read_views", m.group(1))
      continue
    # TRANSACTION
    m = match("History list length (\d+)")
    if m:
      printmetric("innodb.history_list_length", m.group(1))
      continue


def collect(db):
  """Collects and prints stats about the given DB instance."""

  ts = now()
  def printmetric(metric, value, tags=""):
    print "mysql.%s %d %s schema=%s%s" % (metric, ts, value, db.dbname, tags)

  has_innodb = False
  if db.isShowGlobalStatusSafe():
    for metric, value in db.query("SHOW GLOBAL STATUS"):
      try:
        if "." in value:
          value = float(value)
        else:
          value = int(value)
      except ValueError:
        continue
      metric = metric.lower()
      has_innodb = has_innodb or metric.startswith("innodb")
      printmetric(metric, value)

  if has_innodb:
    collectInnodbStatus(db)

  if has_innodb and False:  # Disabled because it's too expensive for InnoDB.
    waits = {}  # maps a mutex name to the number of waits
    ts = now()
    for engine, mutex, status in db.query("SHOW ENGINE INNODB MUTEX"):
      if not status.startswith("os_waits"):
        continue
      m = re.search("&(\w+)(?:->(\w+))?$", mutex)
      if not m:
        continue
      mutex, kind = m.groups()
      if kind:
        mutex += "." + kind
      wait_count = int(status.split("=", 1)[1])
      waits[mutex] = waits.get(mutex, 0) + wait_count
    for mutex, wait_count in waits.iteritems():
      printmetric("innodb.locks", wait_count, " mutex=" + mutex)

  ts = now()

  mysql_slave_status = db.query("SHOW SLAVE STATUS")
  if mysql_slave_status:
    slave_status = todict(db, mysql_slave_status[0])
    master_host = slave_status["master_host"]
  else:
    master_host = None

  if master_host and master_host != "None":
    sbm = slave_status.get("seconds_behind_master")
    if isinstance(sbm, (int, long)):
      printmetric("slave.seconds_behind_master", sbm)
    printmetric("slave.bytes_executed", slave_status["exec_master_log_pos"])
    printmetric("slave.bytes_relayed", slave_status["read_master_log_pos"])
    printmetric("slave.thread_io_running",
                isyes(slave_status["slave_io_running"]))
    printmetric("slave.thread_sql_running",
                isyes(slave_status["slave_sql_running"]))

  states = {}  # maps a connection state to number of connections in that state
  for row in db.query("SHOW PROCESSLIST"):
    id, user, host, db_, cmd, time, state = row[:7]
    states[cmd] = states.get(cmd, 0) + 1
  for state, count in states.iteritems():
    state = state.lower().replace(" ", "_")
    printmetric("connection_states", count, " state=%s" % state)


def main(args):
  """Collects and dumps stats from a MySQL server."""
  if not find_sockfiles():  # Nothing to monitor.
    return 13               # Ask tcollector to not respawn us.
  if MySQLdb is None:
    utils.err("error: Python module `MySQLdb' is missing")
    return 1

  last_db_refresh = now()
  dbs = find_databases()
  while True:
    ts = now()
    if ts - last_db_refresh >= DB_REFRESH_INTERVAL:
      find_databases(dbs)
      last_db_refresh = ts

    errs = []
    for dbname, db in dbs.iteritems():
      try:
        collect(db)
      except (EnvironmentError, EOFError, RuntimeError, socket.error,
              MySQLdb.MySQLError), e:
        if isinstance(e, IOError) and e[0] == errno.EPIPE:
          # Exit on a broken pipe.  There's no point in continuing
          # because no one will read our stdout anyway.
          return 2
        utils.err("error: failed to collect data from %s: %s" % (db, e))
        errs.append(dbname)

    for dbname in errs:
      del dbs[dbname]

    sys.stdout.flush()
    time.sleep(COLLECTION_INTERVAL)


if __name__ == "__main__":
  sys.stdin.close()
  sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = netstat
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2011  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

# Note: I spent many hours reading the Linux kernel's source code to infer the
# exact meaning of some of the obscure but useful metrics it exposes.  The
# description of the metrics are correct to the best of my knowledge, but it's
# not always to make sense of the Linux kernel's code.  Please report any
# inaccuracy you find.  -- tsuna.
"""Socket allocation and network statistics for TSDB.

Metrics from /proc/net/sockstat:
  - net.sockstat.num_sockets: Number of sockets allocated (only TCP).
  - net.sockstat.num_timewait: Number of TCP sockets currently in
    TIME_WAIT state.
  - net.sockstat.sockets_inuse: Number of sockets in use (TCP/UDP/raw).
  - net.sockstat.num_orphans: Number of orphan TCP sockets (not attached
    to any file descriptor).
  - net.sockstat.memory: Memory allocated for this socket type (in bytes).
  - net.sockstat.ipfragqueues: Number of IP flows for which there are
    currently fragments queued for reassembly.

Metrics from /proc/net/netstat (`netstat -s' command):
  - net.stat.tcp.abort: Number of connections that the kernel had to abort.
    type=memory is especially bad, the kernel had to drop a connection due to
    having too many orphaned sockets.  Other types are normal (e.g. timeout).
  - net.stat.tcp.abort.failed: Number of times the kernel failed to abort a
    connection because it didn't even have enough memory to reset it (bad).
  - net.stat.tcp.congestion.recovery: Number of times the kernel detected
    spurious retransmits and was able to recover part or all of the CWND.
  - net.stat.tcp.delayedack: Number of delayed ACKs sent of different types.
  - net.stat.tcp.failed_accept: Number of times a connection had to be dropped
    after the 3WHS.  reason=full_acceptq indicates that the application isn't
    accepting connections fast enough.  You should see SYN cookies too.
  - net.stat.tcp.invalid_sack: Number of invalid SACKs we saw of diff types.
    (requires Linux v2.6.24-rc1 or newer)
  - net.stat.tcp.memory.pressure: Number of times a socket entered the
    "memory pressure" mode (not great).
  - net.stat.tcp.memory.prune: Number of times a socket had to discard
    received data due to low memory conditions (bad).
  - net.stat.tcp.packetloss.recovery: Number of times we recovered from packet
    loss by type of recovery (e.g. fast retransmit vs SACK).
  - net.stat.tcp.receive.queue.full: Number of times a received packet had to
    be dropped because the socket's receive queue was full.
    (requires Linux v2.6.34-rc2 or newer)
  - net.stat.tcp.reording: Number of times we detected re-ordering and how.
  - net.stat.tcp.syncookies: SYN cookies (both sent & received).
"""

import re
import resource
import sys
import time

from collectors.lib import utils


def main():
    """Main loop"""
    sys.stdin.close()

    interval = 15
    page_size = resource.getpagesize()

    try:
        sockstat = open("/proc/net/sockstat")
        netstat = open("/proc/net/netstat")
        snmp = open("/proc/net/snmp")
    except IOError, e:
        print >>sys.stderr, "open failed: %s" % e
        return 13  # Ask tcollector to not re-start us.
    utils.drop_privileges()

    # Note: up until v2.6.37-rc2 most of the values were 32 bits.
    # The first value is pretty useless since it accounts for some
    # socket types but not others.  So we don't report it because it's
    # more confusing than anything else and it's not well documented
    # what type of sockets are or aren't included in this count.
    regexp = re.compile("sockets: used \d+\n"
                        "TCP: inuse (?P<tcp_inuse>\d+) orphan (?P<orphans>\d+)"
                        " tw (?P<tw_count>\d+) alloc (?P<tcp_sockets>\d+)"
                        " mem (?P<tcp_pages>\d+)\n"
                        "UDP: inuse (?P<udp_inuse>\d+)"
                        # UDP memory accounting was added in v2.6.25-rc1
                        "(?: mem (?P<udp_pages>\d+))?\n"
                        # UDP-Lite (RFC 3828) was added in v2.6.20-rc2
                        "(?:UDPLITE: inuse (?P<udplite_inuse>\d+)\n)?"
                        "RAW: inuse (?P<raw_inuse>\d+)\n"
                        "FRAG: inuse (?P<ip_frag_nqueues>\d+)"
                        " memory (?P<ip_frag_mem>\d+)\n")

    def print_sockstat(metric, value, tags=""):  # Note: tags must start with ' '
        if value is not None:
            print "net.sockstat.%s %d %s%s" % (metric, ts, value, tags)


    # If a line in /proc/net/{netstat,snmp} doesn't start with a word in that
    # dict, we'll ignore it.  We use the value to build the metric name.
    known_statstypes = {
        "TcpExt:": "tcp",
        "IpExt:": "ip",  # We don't collect anything from here for now.
        "Ip:": "ip",  # We don't collect anything from here for now.
        "Icmp:": "icmp",  # We don't collect anything from here for now.
        "IcmpMsg:": "icmpmsg",  # We don't collect anything from here for now.
        "Tcp:": "tcp",  # We don't collect anything from here for now.
        "Udp:": "udp",
        "UdpLite:": "udplite",  # We don't collect anything from here for now.
        }

    # Any stat in /proc/net/{netstat,snmp} that doesn't appear in this dict will
    # be ignored.  If we find a match, we'll use the (metricname, tags).
    tcp_stats = {
        # An application wasn't able to accept a connection fast enough, so
        # the kernel couldn't store an entry in the queue for this connection.
        # Instead of dropping it, it sent a cookie to the client.
        "SyncookiesSent": ("syncookies", "type=sent"),
        # After sending a cookie, it came back to us and passed the check.
        "SyncookiesRecv": ("syncookies", "type=received"),
        # After sending a cookie, it came back to us but looked invalid.
        "SyncookiesFailed": ("syncookies", "type=failed"),
        # When a socket is using too much memory (rmem), the kernel will first
        # discard any out-of-order packet that has been queued (with SACK).
        "OfoPruned": ("memory.prune", "type=drop_ofo_queue"),
        # If the kernel is really really desperate and cannot give more memory
        # to this socket even after dropping the ofo queue, it will simply
        # discard the packet it received.  This is Really Bad.
        "RcvPruned": ("memory.prune", "type=drop_received"),
        # We waited for another packet to send an ACK, but didn't see any, so
        # a timer ended up sending a delayed ACK.
        "DelayedACKs": ("delayedack", "type=sent"),
        # We wanted to send a delayed ACK but failed because the socket was
        # locked.  So the timer was reset.
        "DelayedACKLocked": ("delayedack", "type=locked"),
        # We sent a delayed and duplicated ACK because the remote peer
        # retransmitted a packet, thinking that it didn't get to us.
        "DelayedACKLost": ("delayedack", "type=lost"),
        # We completed a 3WHS but couldn't put the socket on the accept queue,
        # so we had to discard the connection.
        "ListenOverflows": ("failed_accept", "reason=full_acceptq"),
        # We couldn't accept a connection because one of: we had no route to
        # the destination, we failed to allocate a socket, we failed to
        # allocate a new local port bind bucket.  Note: this counter
        # also include all the increments made to ListenOverflows...
        "ListenDrops": ("failed_accept", "reason=other"),
        # A packet was lost and we used Forward RTO-Recovery to retransmit.
        "TCPForwardRetrans": ("retransmit", "type=forward"),
        # A packet was lost and we fast-retransmitted it.
        "TCPFastRetrans": ("retransmit", "type=fast"),
        # A packet was lost and we retransmitted after a slow start.
        "TCPSlowStartRetrans": ("retransmit", "type=slowstart"),
        # A packet was lost and we recovered after a fast retransmit.
        "TCPRenoRecovery": ("packetloss.recovery", "type=fast_retransmit"),
        # A packet was lost and we recovered by using selective
        # acknowledgements.
        "TCPSackRecovery": ("packetloss.recovery", "type=sack"),
        # We detected re-ordering using FACK (Forward ACK -- the highest
        # sequence number known to have been received by the peer when using
        # SACK -- FACK is used during congestion control).
        "TCPFACKReorder": ("reording", "detectedby=fack"),
        # We detected re-ordering using SACK.
        "TCPSACKReorder": ("reording", "detectedby=sack"),
        # We detected re-ordering using fast retransmit.
        "TCPRenoReorder": ("reording", "detectedby=fast_retransmit"),
        # We detected re-ordering using the timestamp option.
        "TCPTSReorder": ("reording", "detectedby=timestamp"),
        # We detected some erroneous retransmits and undid our CWND reduction.
        "TCPFullUndo": ("congestion.recovery", "type=full_undo"),
        # We detected some erroneous retransmits, a partial ACK arrived while
        # we were fast retransmitting, so we were able to partially undo some
        # of our CWND reduction.
        "TCPPartialUndo": ("congestion.recovery", "type=hoe_heuristic"),
        # We detected some erroneous retransmits, a D-SACK arrived and ACK'ed
        # all the retransmitted data, so we undid our CWND reduction.
        "TCPDSACKUndo": ("congestion.recovery", "type=sack"),
        # We detected some erroneous retransmits, a partial ACK arrived, so we
        # undid our CWND reduction.
        "TCPLossUndo": ("congestion.recovery", "type=ack"),
        # We received an unexpected SYN so we sent a RST to the peer.
        "TCPAbortOnSyn": ("abort", "type=unexpected_syn"),
        # We were in FIN_WAIT1 yet we received a data packet with a sequence
        # number that's beyond the last one for this connection, so we RST'ed.
        "TCPAbortOnData": ("abort", "type=data_after_fin_wait1"),
        # We received data but the user has closed the socket, so we have no
        # wait of handing it to them, so we RST'ed.
        "TCPAbortOnClose": ("abort", "type=data_after_close"),
        # This is Really Bad.  It happens when there are too many orphaned
        # sockets (not attached a FD) and the kernel has to drop a connection.
        # Sometimes it will send a reset to the peer, sometimes it wont.
        "TCPAbortOnMemory": ("abort", "type=out_of_memory"),
        # The connection timed out really hard.
        "TCPAbortOnTimeout": ("abort", "type=timeout"),
        # We killed a socket that was closed by the application and lingered
        # around for long enough.
        "TCPAbortOnLinger": ("abort", "type=linger"),
        # We tried to send a reset, probably during one of teh TCPABort*
        # situations above, but we failed e.g. because we couldn't allocate
        # enough memory (very bad).
        "TCPAbortFailed": ("abort.failed", None),
        # Number of times a socket was put in "memory pressure" due to a non
        # fatal memory allocation failure (reduces the send buffer size etc).
        "TCPMemoryPressures": ("memory.pressure", None),
        # We got a completely invalid SACK block and discarded it.
        "TCPSACKDiscard": ("invalid_sack", "type=invalid"),
        # We got a duplicate SACK while retransmitting so we discarded it.
        "TCPDSACKIgnoredOld": ("invalid_sack", "type=retransmit"),
        # We got a duplicate SACK and discarded it.
        "TCPDSACKIgnoredNoUndo": ("invalid_sack", "type=olddup"),
        # We received something but had to drop it because the socket's
        # receive queue was full.
        "TCPBacklogDrop": ("receive.queue.full", None),
    }
    known_stats = {
        "tcp": tcp_stats,
        "ip": {
        },
        "icmp": {
        },
        "icmpmsg": {
        },
        "udp": {
            # Total UDP datagrams received by this host
            "InDatagrams": ("datagrams", "direction=in"),
            # UDP datagrams received on a port with no listener
            "NoPorts": ("errors", "direction=in reason=noport"),
            # Total UDP datagrams that could not be delivered to an application
            # Note: this counter also increments for RcvbufErrors
            "InErrors": ("errors", "direction=in reason=other"),
            # Total UDP datagrams sent from this host
            "OutDatagrams": ("datagrams", "direction=out"),
            # Datagrams for which not enough socket buffer memory to receive
            "RcvbufErrors": ("errors", "direction=in reason=nomem"),
            # Datagrams for which not enough socket buffer memory to transmit
            "SndbufErrors": ("errors", "direction=out reason=nomem"),
        },
        "udplite": {
        },
    }


    def print_netstat(statstype, metric, value, tags=""):
        if tags:
            space = " "
        else:
            tags = space = ""
        print "net.stat.%s.%s %d %s%s%s" % (statstype, metric, ts, value,
                                            space, tags)

    def parse_stats(stats, filename):
        statsdikt = {}
        # /proc/net/{netstat,snmp} have a retarded column-oriented format.  It
        # looks like this:
        #   Header: SomeMetric OtherMetric
        #   Header: 1 2
        #   OtherHeader: ThirdMetric FooBar
        #   OtherHeader: 42 51
        #   OtherHeader: FourthMetric
        #   OtherHeader: 4
        # We first pair the lines together, then create a dict for each type:
        #   {"SomeMetric": "1", "OtherMetric": "2"}
        lines = stats.splitlines()
        assert len(lines) % 2 == 0, repr(lines)
        for header, data in zip(*(iter(lines),) * 2):
            header = header.split()
            data = data.split()
            assert header[0] == data[0], repr((header, data))
            assert len(header) == len(data), repr((header, data))
            if header[0] not in known_statstypes:
                print >>sys.stderr, ("Unrecoginized line in %s:"
                                     " %r (file=%r)" % (filename, header, stats))
                continue
            statstype = header.pop(0)
            data.pop(0)
            stats = dict(zip(header, data))
            statsdikt.setdefault(known_statstypes[statstype], {}).update(stats)
        for statstype, stats in statsdikt.iteritems():
            # Undo the kernel's double counting
            if "ListenDrops" in stats:
                stats["ListenDrops"] = int(stats["ListenDrops"]) - int(stats.get("ListenOverflows", 0))
            elif "RcvbufErrors" in stats:
                stats["InErrors"] = int(stats.get("InErrors", 0)) - int(stats["RcvbufErrors"])
            for stat, (metric, tags) in known_stats[statstype].iteritems():
                value = stats.get(stat)
                if value is not None:
                    print_netstat(statstype, metric, value, tags)

    while True:
        ts = int(time.time())
        sockstat.seek(0)
        netstat.seek(0)
        snmp.seek(0)
        data = sockstat.read()
        netstats = netstat.read()
        snmpstats = snmp.read()
        m = re.match(regexp, data)
        if not m:
            print >>sys.stderr, "Cannot parse sockstat: %r" % data
            return 13

        # The difference between the first two values is the number of
        # sockets allocated vs the number of sockets actually in use.
        print_sockstat("num_sockets",   m.group("tcp_sockets"),   " type=tcp")
        print_sockstat("num_timewait",  m.group("tw_count"))
        print_sockstat("sockets_inuse", m.group("tcp_inuse"),     " type=tcp")
        print_sockstat("sockets_inuse", m.group("udp_inuse"),     " type=udp")
        print_sockstat("sockets_inuse", m.group("udplite_inuse"), " type=udplite")
        print_sockstat("sockets_inuse", m.group("raw_inuse"),     " type=raw")

        print_sockstat("num_orphans", m.group("orphans"))
        print_sockstat("memory", int(m.group("tcp_pages")) * page_size,
                       " type=tcp")
        if m.group("udp_pages") is not None:
          print_sockstat("memory", int(m.group("udp_pages")) * page_size,
                         " type=udp")
        print_sockstat("memory", m.group("ip_frag_mem"), " type=ipfrag")
        print_sockstat("ipfragqueues", m.group("ip_frag_nqueues"))

        parse_stats(netstats, netstat.name)
        parse_stats(snmpstats, snmp.name)

        sys.stdout.flush()
        time.sleep(interval)

if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = nfsstat
#!/usr/bin/python
#
# Copyright (C) 2012  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#
"""Imports NFS stats from /proc."""

import sys
import time

from collectors.lib import utils

COLLECTION_INTERVAL = 15  # seconds

nfs_client_proc_names = {
    "proc4": (
        # list of ops taken from nfs-utils / nfsstat.c
        "null", "read", "write", "commit", "open", "open_conf", "open_noat",
        "open_dgrd", "close", "setattr", "fsinfo", "renew", "setclntid", "confirm",
        "lock", "lockt", "locku", "access", "getattr", "lookup", "lookup_root",
        "remove", "rename", "link", "symlink", "create", "pathconf", "statfs",
        "readlink", "readdir", "server_caps", "delegreturn", "getacl", "setacl",
        "fs_locations", "rel_lkowner", "secinfo",
        # nfsv4.1 client ops
        "exchange_id", "create_ses", "destroy_ses", "sequence", "get_lease_t",
        "reclaim_comp", "layoutget", "getdevinfo", "layoutcommit", "layoutreturn",
        "getdevlist",
    ),
    "proc3": (
        "null", "getattr", "setattr", "lookup", "access", "readlink",
        "read", "write", "create", "mkdir", "symlink", "mknod",
        "remove", "rmdir", "rename", "link", "readdir", "readdirplus",
        "fsstat", "fsinfo", "pathconf", "commit",
    ),
}


def main():
    """nfsstat main loop"""

    try:
        f_nfs = open("/proc/net/rpc/nfs")
    except IOError, e:
        print >>sys.stderr, "Failed to open input file: %s" % (e,)
        return 13  # Ask tcollector to not re-start us immediately.

    utils.drop_privileges()
    while True:
        f_nfs.seek(0)
        ts = int(time.time())
        for line in f_nfs:
            fields = line.split()
            if fields[0] in nfs_client_proc_names.keys():
                # NFSv4
                # first entry should equal total count of subsequent entries
                assert int(fields[1]) == len(fields[2:]), (
                    "reported count (%d) does not equal list length (%d)"
                    % (int(fields[1]), len(fields[2:])))
                for idx, val in enumerate(fields[2:]):
                    try:
                        print ("nfs.client.rpc %d %s op=%s version=%s"
                               % (ts, int(val), nfs_client_proc_names[fields[0]][idx], fields[0][4:]))
                    except IndexError:
                        print >> sys.stderr, ("Warning: name lookup failed"
                                              " at position %d" % idx)
            elif fields[0] == "rpc":
                # RPC
                calls = int(fields[1])
                retrans = int(fields[2])
                authrefrsh = int(fields[3])
                print "nfs.client.rpc.stats %d %d type=calls" % (ts, calls)
                print "nfs.client.rpc.stats %d %d type=retrans" % (ts, retrans)
                print ("nfs.client.rpc.stats %d %d type=authrefrsh"
                       % (ts, authrefrsh))

        sys.stdout.flush()
        time.sleep(COLLECTION_INTERVAL)

if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = postgresql
#!/usr/bin/env python
# This file is part of tcollector.
# Copyright (C) 2013 The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details. You should have received a copy
# of the GNU Lesser General Public License along with this program. If not,
# see <http://www.gnu.org/licenses/>.
"""
Collector for PostgreSQL.

Please, set login/password at etc/postgresql.conf .
Collector uses socket file for DB connection so set 'unix_socket_directory'
at postgresql.conf .
"""

import sys
import os
import time
import socket
import errno

try:
  import psycopg2
except ImportError:
  psycopg2 = None # handled in main()

COLLECTION_INTERVAL = 15 # seconds
CONNECT_TIMEOUT = 2 # seconds

from collectors.lib import utils
from collectors.etc import postgresqlconf

# Directories under which to search socket files
SEARCH_DIRS = frozenset([
  "/var/run/postgresql", # Debian default
  "/var/pgsql_socket", # MacOS default
  "/usr/local/var/postgres", # custom compilation
  "/tmp", # custom compilation
])

def find_sockdir():
  """Returns a path to PostgreSQL socket file to monitor."""
  for dir in SEARCH_DIRS:
    for dirpath, dirnames, dirfiles in os.walk(dir, followlinks=True):
      for name in dirfiles:
        # ensure selection of PostgreSQL socket only
	if (utils.is_sockfile(os.path.join(dirpath, name))
	    and "PGSQL" in name):
          return(dirpath)

def postgres_connect(sockdir):
  """Connects to the PostgreSQL server using the specified socket file."""
  user, password = postgresqlconf.get_user_password()

  try:
    return psycopg2.connect("host='%s' user='%s' password='%s' "
                            "connect_timeout='%s' dbname=postgres"
                            % (sockdir, user, password,
                            CONNECT_TIMEOUT))
  except (EnvironmentError, EOFError, RuntimeError, socket.error), e:
    utils.err("Couldn't connect to DB :%s" % (e))

def collect(db):
  """
  Collects and prints stats.

  Here we collect only general info, for full list of data for collection
  see http://www.postgresql.org/docs/9.2/static/monitoring-stats.html
  """

  try:
    cursor = db.cursor()

    # general statics
    cursor.execute("SELECT pg_stat_database.*, pg_database_size"
                   " (pg_database.datname) AS size FROM pg_database JOIN"
                   " pg_stat_database ON pg_database.datname ="
                   " pg_stat_database.datname WHERE pg_stat_database.datname"
                   " NOT IN ('template0', 'template1', 'postgres')")
    ts = time.time()
    stats = cursor.fetchall()

#  datid |  datname   | numbackends | xact_commit | xact_rollback | blks_read  |  blks_hit   | tup_returned | tup_fetched | tup_inserted | tup_updated | tup_deleted | conflicts | temp_files |  temp_bytes  | deadlocks | blk_read_time | blk_write_time |          stats_reset          |     size     
    result = {}
    for stat in stats:
      database = stat[1]
      result[database] = stat

    for database in result:
      for i in range(2,len(cursor.description)):
        metric = cursor.description[i].name
        value = result[database][i]
        try:
          if metric in ("stats_reset"):
            continue
          print ("postgresql.%s %i %s database=%s"
                 % (metric, ts, value, database))
        except:
          err("got here")
          continue

    # connections
    cursor.execute("SELECT datname, count(datname) FROM pg_stat_activity"
                   " GROUP BY pg_stat_activity.datname")
    ts = time.time()
    connections = cursor.fetchall()

    for database, connection in connections:
      print ("postgresql.connections %i %s database=%s"
             % (ts, connection, database))

  except (EnvironmentError, EOFError, RuntimeError, socket.error), e:
    if isinstance(e, IOError) and e[0] == errno.EPIPE:
      # exit on a broken pipe. There is no point in continuing
      # because no one will read our stdout anyway.
      return 2
    utils.err("error: failed to collect data: %s" % e)

def main(args):
  """Collects and dumps stats from a PostgreSQL server."""

  if psycopg2 is None:
    utils.err("error: Python module 'psycopg2' is missing")
    return 13 # Ask tcollector to not respawn us

  sockdir = find_sockdir()
  if not sockdir: # Nothing to monitor
    utils.err("error: Can't find postgresql socket file")
    return 13 # Ask tcollector to not respawn us

  db = postgres_connect(sockdir)
  db.autocommit=True

  while True:
    collect(db)
    sys.stdout.flush()
    time.sleep(COLLECTION_INTERVAL)

if __name__ == "__main__":
  sys.stdin.close()
  sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = procnettcp
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

"""TCP socket state data for TSDB"""
#
# Read /proc/net/tcp, which gives netstat -a type
# data for all TCP sockets.

# Note this collector generates a lot of lines, given that there are
#  lots of tcp states and given the number of subcollections we do.
#  We rely heavily on tcollector's deduping.  We could be lazy and
#  just output values only for which we have data, except if we do
#  this then any counters for which we had data would never reach
#  zero since our state machine never enters this condition.

# Metric: proc.net.tcp

# For each run, we classify each connection and generate subtotals.
#   TSD will automatically total these up when displaying
#   the graph, but you can drill down for each possible total or a
#   particular one.  This does generate a large amount of datapoints,
#   as the number of points is (S*(U+1)*V) (currently ~400), where
#   S=number of TCP states, U=Number of users to track, and
#   V=number of services (collections of ports)
# The deduper does dedup this down very well, as only 3 of the 10
# TCP states are generally ever seen, and most servers only run one
# service under one user.  On a typical server this dedups down to
# under 10 values per interval.

# Each connection is broken down with a tag for user=username (see
#   "users" list below) or put under "other" if not in the list.
#   Expand this for any users you care about.
# It is also broken down for each state (state=).
# It is also broken down into services (collections of ports)

# Note that once a connection is closed, Linux seems to forget who
# opened/handled the connection.  For connections in time_wait, for
# example, they will always show user=root.

import os
import pwd
import sys
import time

from collectors.lib import utils


USERS = ("root", "www-data", "mysql")

# Note if a service runs on multiple ports and you
# want to collectively map them up to a single service,
# just give them the same name below

PORTS = {
    80: "http",
    443: "https",
    3001: "http-varnish",
    3002: "http-varnish",
    3003: "http-varnish",
    3004: "http-varnish",
    3005: "http-varnish",
    3006: "http-varnish",
    3007: "http-varnish",
    3008: "http-varnish",
    3009: "http-varnish",
    3010: "http-varnish",
    3011: "http-varnish",
    3012: "http-varnish",
    3013: "http-varnish",
    3014: "http-varnish",
    3306: "mysql",
    3564: "mysql",
    9000: "namenode",
    9090: "thriftserver",
    11211: "memcache",
    11212: "memcache",
    11213: "memcache",
    11214: "memcache",
    11215: "memcache",
    11216: "memcache",
    11217: "memcache",
    11218: "memcache",
    11219: "memcache",
    11220: "memcache",
    11221: "memcache",
    11222: "memcache",
    11223: "memcache",
    11224: "memcache",
    11225: "memcache",
    11226: "memcache",
    50020: "datanode",
    60020: "hregionserver",
    }

SERVICES = tuple(set(PORTS.itervalues()))

TCPSTATES = {
    "01": "established",
    "02": "syn_sent",
    "03": "syn_recv",
    "04": "fin_wait1",
    "05": "fin_wait2",
    "06": "time_wait",
    "07": "close",
    "08": "close_wait",
    "09": "last_ack",
    "0A": "listen",
    "0B": "closing",
    }


def is_public_ip(ipstr):
    """
    Take a /proc/net/tcp encoded src or dest string
    Return True if it is coming from public IP space
    (i.e. is not RFC1918, loopback, or broadcast).
    This string is the hex ip:port of the connection.
    (ip is reversed)
    """
    addr = ipstr.split(":")[0]
    addr = int(addr, 16)
    byte1 = addr & 0xFF
    byte2 = (addr >> 8) & 0xFF
    if byte1 in (10, 0, 127):
        return False
    if byte1 == 172 and byte2 > 16:
        return False
    if byte1 == 192 and byte2 == 168:
        return False
    return True


def main(unused_args):
    """procnettcp main loop"""
    try:           # On some Linux kernel versions, with lots of connections
      os.nice(19)  # this collector can be very CPU intensive.  So be nicer.
    except OSError, e:
      print >>sys.stderr, "warning: failed to self-renice:", e

    interval = 60

    # resolve the list of users to match on into UIDs
    uids = {}
    for user in USERS:
        try:
            uids[str(pwd.getpwnam(user)[2])] = user
        except KeyError:
            continue

    try:
        tcp = open("/proc/net/tcp")
        # if IPv6 is enabled, even IPv4 connections will also
        # appear in tcp6. It has the same format, apart from the
        # address size
        try:
            tcp6 = open("/proc/net/tcp6")
        except IOError, (errno, msg):
            if errno == 2:  # No such file => IPv6 is disabled.
                tcp6 = None
            else:
                raise
    except IOError, e:
        print >>sys.stderr, "Failed to open input file: %s" % (e,)
        return 13  # Ask tcollector to not re-start us immediately.

    utils.drop_privileges()
    while True:
        counter = {}

        for procfile in (tcp, tcp6):
            if procfile is None:
                continue
            procfile.seek(0)
            ts = int(time.time())
            for line in procfile:
                try:
                    # pylint: disable=W0612
                    (num, src, dst, state, queue, when, retrans,
                     uid, timeout, inode) = line.split(None, 9)
                except ValueError:  # Malformed line
                    continue

                if num == "sl":  # header
                    continue

                srcport = src.split(":")[1]
                dstport = dst.split(":")[1]
                srcport = int(srcport, 16)
                dstport = int(dstport, 16)
                service = PORTS.get(srcport, "other")
                service = PORTS.get(dstport, service)

                if is_public_ip(dst) or is_public_ip(src):
                    endpoint = "external"
                else:
                    endpoint = "internal"


                user = uids.get(uid, "other")

                key = "state=" + TCPSTATES[state] + " endpoint=" + endpoint + \
                      " service=" + service + " user=" + user
                if key in counter:
                    counter[key] += 1
                else:
                    counter[key] = 1

        # output the counters
        for state in TCPSTATES:
            for service in SERVICES + ("other",):
                for user in USERS + ("other",):
                    for endpoint in ("internal", "external"):
                        key = ("state=%s endpoint=%s service=%s user=%s"
                               % (TCPSTATES[state], endpoint, service, user))
                        if key in counter:
                            print "proc.net.tcp", ts, counter[key], key
                        else:
                            print "proc.net.tcp", ts, "0", key

        sys.stdout.flush()
        time.sleep(interval)

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = procstats
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#
"""import various /proc stats from /proc into TSDB"""

import os
import re
import sys
import time
import glob

from collectors.lib import utils

COLLECTION_INTERVAL = 15  # seconds
NUMADIR = "/sys/devices/system/node"


def open_sysfs_numa_stats():
    """Returns a possibly empty list of opened files."""
    try:
        nodes = os.listdir(NUMADIR)
    except OSError, (errno, msg):
        if errno == 2:  # No such file or directory
            return []   # We don't have NUMA stats.
        raise

    nodes = [node for node in nodes if node.startswith("node")]
    numastats = []
    for node in nodes:
        try:
            numastats.append(open(os.path.join(NUMADIR, node, "numastat")))
        except OSError, (errno, msg):
            if errno == 2:  # No such file or directory
                continue
            raise
    return numastats


def print_numa_stats(numafiles):
    """From a list of opened files, extracts and prints NUMA stats."""
    for numafile in numafiles:
        numafile.seek(0)
        node_id = int(numafile.name[numafile.name.find("/node/node")+10:-9])
        ts = int(time.time())
        stats = dict(line.split() for line in numafile.read().splitlines())
        for stat, tag in (# hit: process wanted memory from this node and got it
                          ("numa_hit", "hit"),
                          # miss: process wanted another node and got it from
                          # this one instead.
                          ("numa_miss", "miss")):
            print ("sys.numa.zoneallocs %d %s node=%d type=%s"
                   % (ts, stats[stat], node_id, tag))
        # Count this one as a separate metric because we can't sum up hit +
        # miss + foreign, this would result in double-counting of all misses.
        # See `zone_statistics' in the code of the kernel.
        # foreign: process wanted memory from this node but got it from
        # another node.  So maybe this node is out of free pages.
        print ("sys.numa.foreign_allocs %d %s node=%d"
               % (ts, stats["numa_foreign"], node_id))
        # When is memory allocated to a node that's local or remote to where
        # the process is running.
        for stat, tag in (("local_node", "local"),
                          ("other_node", "remote")):
            print ("sys.numa.allocation %d %s node=%d type=%s"
                   % (ts, stats[stat], node_id, tag))
        # Pages successfully allocated with the interleave policy.
        print ("sys.numa.interleave %d %s node=%d type=hit"
               % (ts, stats["interleave_hit"], node_id))


def main():
    """procstats main loop"""

    f_uptime = open("/proc/uptime", "r")
    f_meminfo = open("/proc/meminfo", "r")
    f_vmstat = open("/proc/vmstat", "r")
    f_stat = open("/proc/stat", "r")
    f_loadavg = open("/proc/loadavg", "r")
    f_entropy_avail = open("/proc/sys/kernel/random/entropy_avail", "r")
    f_interrupts = open("/proc/interrupts", "r")

    f_scaling = "/sys/devices/system/cpu/cpu%s/cpufreq/cpuinfo_%s_freq"
    f_scaling_min  = dict([])
    f_scaling_max  = dict([])
    f_scaling_cur  = dict([])
    for cpu in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/cpuinfo_cur_freq"):
        m = re.match("/sys/devices/system/cpu/cpu([0-9]*)/cpufreq/cpuinfo_cur_freq", cpu)
        if not m:
            continue
        cpu_no = m.group(1)
        sys.stderr.write(f_scaling % (cpu_no,"min"))
        f_scaling_min[cpu_no] = open(f_scaling % (cpu_no,"min"), "r")
        f_scaling_max[cpu_no] = open(f_scaling % (cpu_no,"max"), "r")
        f_scaling_cur[cpu_no] = open(f_scaling % (cpu_no,"cur"), "r")

    numastats = open_sysfs_numa_stats()
    utils.drop_privileges()

    while True:
        # proc.uptime
        f_uptime.seek(0)
        ts = int(time.time())
        for line in f_uptime:
            m = re.match("(\S+)\s+(\S+)", line)
            if m:
                print "proc.uptime.total %d %s" % (ts, m.group(1))
                print "proc.uptime.now %d %s" % (ts, m.group(2))

        # proc.meminfo
        f_meminfo.seek(0)
        ts = int(time.time())
        for line in f_meminfo:
            m = re.match("(\w+):\s+(\d+)\s+(\w+)", line)
            if m:
                if m.group(3).lower() == 'kb':
                    # convert from kB to B for easier graphing
                    value = str(int(m.group(2)) * 1000)
                else:
                    value = m.group(2)
                print ("proc.meminfo.%s %d %s"
                        % (m.group(1).lower(), ts, value))

        # proc.vmstat
        f_vmstat.seek(0)
        ts = int(time.time())
        for line in f_vmstat:
            m = re.match("(\w+)\s+(\d+)", line)
            if not m:
                continue
            if m.group(1) in ("pgpgin", "pgpgout", "pswpin",
                              "pswpout", "pgfault", "pgmajfault"):
                print "proc.vmstat.%s %d %s" % (m.group(1), ts, m.group(2))

        # proc.stat
        f_stat.seek(0)
        ts = int(time.time())
        for line in f_stat:
            m = re.match("(\w+)\s+(.*)", line)
            if not m:
                continue
            if m.group(1).startswith("cpu"):
                cpu_m = re.match("cpu(\d+)", m.group(1))
                if cpu_m:
                    metric_percpu = '.percpu'
                    tags = ' cpu=%s' % cpu_m.group(1)
                else:
                    metric_percpu = ''
                    tags = ''
                fields = m.group(2).split()
                cpu_types = ['user', 'nice', 'system', 'idle', 'iowait',
                    'irq', 'softirq', 'guest', 'guest_nice']

                # We use zip to ignore fields that don't exist.
                for value, field_name in zip(fields, cpu_types):
                    print "proc.stat.cpu%s %d %s type=%s%s" % (metric_percpu,
                        ts, value, field_name, tags)
            elif m.group(1) == "intr":
                print ("proc.stat.intr %d %s"
                        % (ts, m.group(2).split()[0]))
            elif m.group(1) == "ctxt":
                print "proc.stat.ctxt %d %s" % (ts, m.group(2))
            elif m.group(1) == "processes":
                print "proc.stat.processes %d %s" % (ts, m.group(2))
            elif m.group(1) == "procs_blocked":
                print "proc.stat.procs_blocked %d %s" % (ts, m.group(2))

        f_loadavg.seek(0)
        ts = int(time.time())
        for line in f_loadavg:
            m = re.match("(\S+)\s+(\S+)\s+(\S+)\s+(\d+)/(\d+)\s+", line)
            if not m:
                continue
            print "proc.loadavg.1min %d %s" % (ts, m.group(1))
            print "proc.loadavg.5min %d %s" % (ts, m.group(2))
            print "proc.loadavg.15min %d %s" % (ts, m.group(3))
            print "proc.loadavg.runnable %d %s" % (ts, m.group(4))
            print "proc.loadavg.total_threads %d %s" % (ts, m.group(5))

        f_entropy_avail.seek(0)
        ts = int(time.time())
        for line in f_entropy_avail:
            print "proc.kernel.entropy_avail %d %s" % (ts, line.strip())

        f_interrupts.seek(0)
        ts = int(time.time())
        # Get number of CPUs from description line.
        num_cpus = len(f_interrupts.readline().split())
        for line in f_interrupts:
            cols = line.split()

            irq_type = cols[0].rstrip(":")
            if irq_type.isalnum():
                if irq_type.isdigit():
                    if cols[-2] == "PCI-MSI-edge" and "eth" in cols[-1]:
                        irq_type = cols[-1]
                    else:
                        continue  # Interrupt type is just a number, ignore.
                for i, val in enumerate(cols[1:]):
                    if i >= num_cpus:
                        # All values read, remaining cols contain textual
                        # description
                        break
                    if not val.isdigit():
                        # something is weird, there should only be digit values
                        sys.stderr.write("Unexpected interrupts value %r in"
                                         " %r: " % (val, cols))
                        break
                    print ("proc.interrupts %s %s type=%s cpu=%s"
                           % (ts, val, irq_type, i))

        print_numa_stats(numastats)

        # Print scaling stats
        ts = int(time.time())
        for cpu_no in f_scaling_min.keys():
            f = f_scaling_min[cpu_no]
            f.seek(0)
            for line in f:
                print "proc.scaling.min %d %s cpu=%s" % (ts, line.rstrip('\n'), cpu_no)
        ts = int(time.time())
        for cpu_no in f_scaling_max.keys():
            f = f_scaling_max[cpu_no]
            f.seek(0)
            for line in f:
                print "proc.scaling.max %d %s cpu=%s" % (ts, line.rstrip('\n'), cpu_no)
        ts = int(time.time())
        for cpu_no in f_scaling_cur.keys():
            f = f_scaling_cur[cpu_no]
            f.seek(0)
            for line in f:
                print "proc.scaling.cur %d %s cpu=%s" % (ts, line.rstrip('\n'), cpu_no)

        sys.stdout.flush()
        time.sleep(COLLECTION_INTERVAL)

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = redis-stats
#!/usr/bin/python
#
# Copyright (C) 2011  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#
# Written by Mark Smith <mark@qq.is>.
#

"""Statistics from a Redis instance.

Note: this collector parses your Redis configuration files to determine what cluster
this instance is part of.  If you want the cluster tag to be accurate, please edit
your Redis configuration file and add a comment like this somewhere in the file:

# tcollector.cluster = main

You can name the cluster anything that matches the regex [a-z0-9-_]+.

This collector outputs the following metrics:

 - redis.bgrewriteaof_in_progress
 - redis.bgsave_in_progress
 - redis.blocked_clients
 - redis.changes_since_last_save
 - redis.client_biggest_input_buf
 - redis.client_longest_output_list
 - redis.connected_clients
 - redis.connected_slaves
 - redis.expired_keys
 - redis.evicted_keys
 - redis.hash_max_zipmap_entries
 - redis.hash_max_zipmap_value
 - redis.keyspace_hits
 - redis.keyspace_misses
 - redis.mem_fragmentation_ratio
 - redis.pubsub_channels
 - redis.pubsub_patterns
 - redis.total_commands_processed
 - redis.total_connections_received
 - redis.uptime_in_seconds
 - redis.used_cpu_sys
 - redis.used_cpu_user
 - redis.used_memory
 - redis.used_memory_rss

For more information on these values, see this (not very useful) documentation:

    http://redis.io/commands/info
"""

import re
import subprocess
import sys
import time

try:
    import redis
    has_redis = True
except ImportError:
    has_redis = False

from collectors.lib import utils

# If we are root, drop privileges to this user, if necessary.  NOTE: if this is
# not root, this MUST be the user that you run redis-server under.  If not, we
# will not be able to find your Redis instances.
USER = "root"

# Every SCAN_INTERVAL seconds, we look for new redis instances.  Prevents the
# situation where you put up a new instance and we never notice.
SCAN_INTERVAL = 300

# these are the things in the info struct that we care about
KEYS = [
    'pubsub_channels', 'bgrewriteaof_in_progress', 'connected_slaves', 'connected_clients', 'keyspace_misses',
    'used_memory', 'total_commands_processed', 'used_memory_rss', 'total_connections_received', 'pubsub_patterns',
    'used_cpu_sys', 'blocked_clients', 'used_cpu_user', 'expired_keys', 'bgsave_in_progress', 'hash_max_zipmap_entries',
    'hash_max_zipmap_value', 'client_longest_output_list', 'client_biggest_input_buf', 'uptime_in_seconds',
    'changes_since_last_save', 'mem_fragmentation_ratio', 'keyspace_hits', 'evicted_keys'
];


def main():
    """Main loop"""

    if USER != "root":
        utils.drop_privileges(user=USER)
    sys.stdin.close()

    interval = 15

    # we scan for instances here to see if there are any redis servers
    # running on this machine...
    last_scan = time.time()
    instances = scan_for_instances()  # port:name
    if not len(instances):
        return 13
    if not has_redis:
        sys.stderr.write("Found %d instance(s) to monitor, but the Python"
                         " Redis module isn't installed.\n" % len(instances))
        return 1

    def print_stat(metric, value, tags=""):
        if value is not None:
            print "redis.%s %d %s %s" % (metric, ts, value, tags)

    dbre = re.compile("^db\d+$")

    while True:
        ts = int(time.time())

        # if we haven't looked for redis instances recently, let's do that
        if ts - last_scan > SCAN_INTERVAL:
            instances = scan_for_instances()
            last_scan = ts

        # now iterate over every instance and gather statistics
        for port in instances:
            tags = "cluster=%s port=%d" % (instances[port], port)

            # connect to the instance and attempt to gather info
            r = redis.Redis(host="127.0.0.1", port=port)
            info = r.info()
            for key in KEYS:
                if key in info:
                    print_stat(key, info[key], tags)

            # per database metrics
            for db in filter(dbre.match, info.keys()):
                for db_metric in info[db].keys():
                    print_stat(db_metric, info[db][db_metric], "%s db=%s" % (tags, db))

            # get some instant latency information
            # TODO: might be nice to get 95th, 99th, etc here?
            start_time = time.time()
            r.ping()
            print_stat("latency", time.time() - start_time, tags)

        sys.stdout.flush()
        time.sleep(interval)


def scan_for_instances():
    """Use netstat to find instances of Redis listening on the local machine, then
    figure out what configuration file they're using to name the cluster."""

    out = {}
    tcre = re.compile(r"^\s*#\s*tcollector.(\w+)\s*=\s*(.+)$")

    ns_proc = subprocess.Popen(["netstat", "-tnlp"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, _ = ns_proc.communicate()
    if ns_proc.returncode != 0:
        print >> sys.stderr, "failed to find instances %r" % ns_proc.returncode
        return {}

    for line in stdout.split("\n"):
        if not (line and 'redis-server' in line):
            continue
        pid = int(line.split()[6].split("/")[0])
        port = int(line.split()[3].split(":")[1])

        # now we have to get the command line.  we look in the redis config file for
        # a special line that tells us what cluster this is.  else we default to using
        # the port number which should work.
        cluster = "port-%d" % port
        try:
            f = open("/proc/%d/cmdline" % pid)
            cfg = f.readline().split("\0")[-2]
            f.close()

            f = open(cfg)
            for cfgline in f:
                result = tcre.match(cfgline)
                if result and result.group(1).lower() == "cluster":
                    cluster = result.group(2).lower()
        except EnvironmentError:
            # use the default cluster name if anything above failed.
            pass

        out[port] = cluster
    return out


if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = riak
#!/usr/bin/python
#
# Copyright (C) 2011  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#
# Written by Mark Smith <mark@qq.is>.
#

"""A collector to gather statistics from a Riak node.

The following all have tags of 'type' which can be 'get' or 'put'.  Latency
is measured in fractional seconds.  All latency values are calculated over the
last 60 seconds and are moving values.

 - riak.vnode.requests
 - riak.node.requests
 - riak.node.latency.mean
 - riak.node.latency.median
 - riak.node.latency.95th
 - riak.node.latency.99th
 - riak.node.latency.100th

These metrics have no tags and are global:

 - riak.memory.total
 - riak.memory.allocated
 - riak.executing_mappers
 - riak.sys_process_count
 - riak.read_repairs
 - riak.connections
 - riak.connected_nodes
"""

import json
import os
import sys
import time
import urllib2

from collectors.lib import utils

MAP = {
    'vnode_gets_total': ('vnode.requests', 'type=get'),
    'vnode_puts_total': ('vnode.requests', 'type=put'),
    'node_gets_total': ('node.requests', 'type=get'),
    'node_puts_total': ('node.requests', 'type=put'),
    'node_get_fsm_time_mean': ('node.latency.mean', 'type=get'),
    'node_get_fsm_time_median': ('node.latency.median', 'type=get'),
    'node_get_fsm_time_95': ('node.latency.95th', 'type=get'),
    'node_get_fsm_time_99': ('node.latency.99th', 'type=get'),
    'node_get_fsm_time_100': ('node.latency.100th', 'type=get'),
    'node_put_fsm_time_mean': ('node.latency.mean', 'type=put'),
    'node_put_fsm_time_median': ('node.latency.median', 'type=put'),
    'node_put_fsm_time_95': ('node.latency.95th', 'type=put'),
    'node_put_fsm_time_99': ('node.latency.99th', 'type=put'),
    'node_put_fsm_time_100': ('node.latency.100th', 'type=put'),
    'pbc_connects_total': ('connections', ''),
    'read_repairs_total': ('read_repairs', ''),
    'sys_process_count': ('sys_process_count', ''),
    'executing_mappers': ('executing_mappers', ''),
    'mem_allocated': ('memory.allocated', ''),
    'mem_total': ('memory.total', ''),
    #connected_nodes is calculated
}


def main():
    """Main loop"""

    # don't run if we're not a riak node
    if not os.path.exists("/usr/lib/riak"):
        sys.exit(13)

    utils.drop_privileges()
    sys.stdin.close()

    interval = 15

    def print_stat(metric, value, tags=""):
        if value is not None:
            print "riak.%s %d %s %s" % (metric, ts, value, tags)

    while True:
        ts = int(time.time())

        req = urllib2.urlopen("http://localhost:8098/stats")
        if req is not None:
            obj = json.loads(req.read())
            for key in obj:
                if key not in MAP:
                    continue
                # this is a hack, but Riak reports latencies in microseconds.  they're fairly useless
                # to our human operators, so we're going to convert them to seconds.
                if 'latency' in MAP[key][0]:
                    obj[key] = obj[key] / 1000000.0
                print_stat(MAP[key][0], obj[key], MAP[key][1])
            if 'connected_nodes' in obj:
                print_stat('connected_nodes', len(obj['connected_nodes']), '')
        req.close()

        sys.stdout.flush()
        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = smart-stats
#! /usr/bin/python

# This file is part of tcollector.
# Copyright (C) 2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#
"""SMART disk stats for TSDB"""

import glob
import os
import signal
import subprocess
import sys
import time

TWCLI = "/usr/sbin/tw_cli"
ARCCONF = "/usr/local/bin/arcconf"
ARCCONF_ARGS = "GETVERSION 1"
NO_CONTROLLER = "Controllers found: 0"
BROKEN_DRIVER_VERSIONS = ("1.1-5",)

SMART_CTL = "smartctl"
SLEEP_BETWEEN_POLLS = 60
COMMAND_TIMEOUT = 10

# Common smart attributes, add more to this list if you start seeing
# numbers instead of attribute names in TSD results.
ATTRIBUTE_MAP = {
  "1": "raw_read_error_rate",
  "2": "throughput_performance",
  "3": "spin_up_time",
  "4": "start_stop_count",
  "5": "reallocated_sector_ct",
  "7": "seek_error_rate",
  "8": "seek_time_performance",
  "9": "power_on_hours",
  "10": "spin_retry_count",
  "11": "recalibration_retries",
  "12": "power_cycle_count",
  "13": "soft_read_error_rate",
  "175": "program_fail_count_chip",
  "176": "erase_fail_count_chip",
  "177": "wear_leveling_count",
  "178": "used_rsvd_blk_cnt_chip",
  "179": "used_rsvd_blk_cnt_tot",
  "180": "unused_rsvd_blk_cnt_tot",
  "181": "program_fail_cnt_total",
  "182": "erase_fail_count_total",
  "183": "runtime_bad_block",
  "184": "end_to_end_error",
  "187": "reported_uncorrect",
  "188": "command_timeout",
  "189": "high_fly_writes",
  "190": "airflow_temperature_celsius",
  "191": "g_sense_error_rate",
  "192": "power-off_retract_count",
  "193": "load_cycle_count",
  "194": "temperature_celsius",
  "195": "hardware_ecc_recovered",
  "196": "reallocated_event_count",
  "197": "current_pending_sector",
  "198": "offline_uncorrectable",
  "199": "udma_crc_error_count",
  "200": "write_error_rate",
  "233": "media_wearout_indicator",
  "240": "transfer_error_rate",
  "241": "total_lba_writes",
  "242": "total_lba_read",
  }


class Alarm(RuntimeError):
  pass


def alarm_handler(signum, frame):
  print >>sys.stderr, ("Program took too long to run, "
                       "consider increasing its timeout.")
  raise Alarm()


def smart_is_broken(drives):
  """Determines whether SMART can be used.

  Args:
    drives: A list of device names on which we intend to use SMART.

  Returns:
    True if SMART is available, False otherwise.
  """
  if os.path.exists(ARCCONF):
    return is_adaptec_driver_broken()
  if os.path.exists(TWCLI):
    return is_3ware_driver_broken(drives)
  return False


def is_adaptec_driver_broken():
  signal.alarm(COMMAND_TIMEOUT)
  arcconf = subprocess.Popen("%s %s" % (ARCCONF, ARCCONF_ARGS),
                             shell=True,
                             stdout=subprocess.PIPE)
  arcconf_output = arcconf.communicate()[0]
  signal.alarm(0)
  if arcconf.returncode != 0:
    if arcconf_output and arcconf_output.startswith(NO_CONTROLLER):
      # No controller => no problem.
      return False
    if arcconf.returncode == 127:
      # arcconf doesn't even work on this system, so assume we're safe
      return False
    print >>sys.stderr, ("arcconf unexpected error %s" % arcconf.returncode)
    return True
  for line in arcconf_output.split("\n"):
    fields = [x for x in line.split(" ") if x]
    if fields[0] == "Driver" and fields[2] in BROKEN_DRIVER_VERSIONS:
      print >>sys.stderr, ("arcconf indicates broken driver version %s"
                           % fields[2])
      return True
  return False

def is_3ware_driver_broken(drives):
  # Apparently 3ware controllers can't report SMART stats from SAS drives. WTF.
  # See also http://sourceforge.net/apps/trac/smartmontools/ticket/161
  for i in reversed(xrange(len(drives))):
    drive = drives[i]
    signal.alarm(COMMAND_TIMEOUT)
    smart_ctl = subprocess.Popen(SMART_CTL + " -i /dev/" + drive,
                                 shell=True, stdout=subprocess.PIPE)
    smart_output = smart_ctl.communicate()[0]
    if "supports SMART and is Disabled" in smart_output:
      print >>sys.stderr, "SMART is disabled for %s" % drive
      del drives[i]  # We're iterating from the end of the list so this is OK.
    signal.alarm(0)
  if not drives:
    print >>sys.stderr, "None of the drives support SMART. Are they SAS drives?"
    return True
  return False


def process_output(drive, smart_output):
  """Print formatted SMART output for the drive"""
  ts = int(time.time())
  smart_output = smart_output.split("\n")
  # Set data_marker to 0, so we skip stuff until we see a line
  # beginning with ID# in the output.  Start processing rows after
  # that point.
  data_marker = False
  is_seagate = False

  for line in smart_output:
    if data_marker:
      fields = line.split()
      if len(fields) < 2:
        continue
      field = fields[0]
      if len(fields) > 2 and field in ATTRIBUTE_MAP:
        metric = ATTRIBUTE_MAP[field]
        value = fields[9].split()[0]
        print ("smart.%s %d %s disk=%s" % (metric, ts, value, drive))
        if is_seagate and metric in ("seek_error_rate", "raw_read_error_rate"):
          # It appears that some Seagate drives (and possibly some Western
          # Digital ones too) use the first 16 bits to store error counts,
          # and the low 32 bits to store operation counts, out of these 48
          # bit values.  So try to be helpful and extract these here.
          value = int(value)
          print ("smart.%s %d %d disk=%s"
                 % (metric.replace("error_rate", "count"), ts,
                    value & 0xFFFFFFFF, drive))
          print ("smart.%s %d %d disk=%s"
                 % (metric.replace("error_rate", "errors"), ts,
                    (value & 0xFFFF00000000) >> 32, drive))
    elif line.startswith("ID#"):
      data_marker = True
    elif line.startswith("Device Model:"):
      model = line.split(None, 2)[2]
      # Rough approximation to detect Seagate drives.
      is_seagate = model.startswith("ST")


def main():
  """main loop for SMART collector"""

  # Get the list of block devices.
  drives = [dev[5:] for dev in glob.glob("/dev/[hs]d[a-z]")]
  # Exit gracefully if no block devices found
  if not drives:
    sys.exit(13)


  # to make sure we are done with smartctl in COMMAND_TIMEOUT seconds
  signal.signal(signal.SIGALRM, alarm_handler)

  if smart_is_broken(drives):
    sys.exit(13)

  while True:
    for drive in drives:
      signal.alarm(COMMAND_TIMEOUT)
      smart_ctl = subprocess.Popen(SMART_CTL + " -i -A /dev/" + drive,
                                   shell=True, stdout=subprocess.PIPE)
      smart_output = smart_ctl.communicate()[0]
      signal.alarm(0)
      if smart_ctl.returncode != 0:
        if smart_ctl.returncode == 127:
          sys.exit(13)
        else:
          print >>sys.stderr, "Command exited with: %d" % smart_ctl.returncode
      process_output(drive, smart_output)

    sys.stdout.flush()
    time.sleep(SLEEP_BETWEEN_POLLS)


if __name__ == "__main__":
  main()

########NEW FILE########
__FILENAME__ = udp_bridge
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
"""Listens on a local UDP socket for incoming Metrics """

import socket
import sys
from collectors.lib import utils

try:
  from collectors.etc import udp_bridge_conf
except ImportError:
  udp_bridge_conf = None

HOST = '127.0.0.1'
PORT = 8953
SIZE = 8192
TIMEOUT = 1

def main():
    if not (udp_bridge_conf and udp_bridge_conf.enabled()):
      sys.exit(13)
    utils.drop_privileges()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
    except socket.error as msg:
        sys.stderr.write('could not open socket: %s\n' % msg)
        sys.exit(1)

    try:
        while 1:
            data, address = sock.recvfrom(SIZE)
            if not data:
                sys.stderr.write("invalid data\n")
                break
            print data
    except KeyboardInterrupt:
        sys.stderr.write("keyboard interrupt, exiting\n")
    finally:
        sock.close()

if __name__ == "__main__":
    main()

sys.exit(0)

########NEW FILE########
__FILENAME__ = varnishstat
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
"""Send varnishstat counters to TSDB"""

# Please note, varnish 3.0.3 and above is necessary to run this script,
# earlier versions don't support json output.

import json
import subprocess
import sys
import time
import re

from collectors.lib import utils

interval = 10 # seconds

# If you would rather use the timestamp returned by varnishstat instead of a
# local timestamp, then change this value to "True"
use_varnishstat_timestamp = False

# This prefix will be prepended to all metric names before being sent
metric_prefix = "varnish"

# Add any additional tags you would like to include into this array as strings
#
# tags = ["production=false", "cloud=amazon"]
tags = []

# Collect all metrics
vstats = "all"

# Collect metrics a la carte
# vstats = frozenset([
#   "client_conn",
#   "client_drop",
#   "client_req",
#   "cache_hit",
#   "cache_hitpass",
#   "cache_miss"
# ])

def main():
 utils.drop_privileges()
 bad_regex = re.compile("[,()]+")  # avoid forbidden by TSD symbols

 while True:
    try:
      if vstats == "all":
        stats = subprocess.Popen(
          ["varnishstat", "-1", "-j"],
          stdout=subprocess.PIPE,
        )
      else:
        fields = ",".join(vstats)
        stats = subprocess.Popen(
          ["varnishstat", "-1", "-f" + fields, "-j"],
          stdout=subprocess.PIPE,
        )
    except OSError, e:
      # Die and signal to tcollector not to run this script.
      sys.stderr.write("Error: %s\n" % e)
      sys.exit(13)

    metrics = ""
    for line in stats.stdout.readlines():
      metrics += line
    metrics = json.loads(metrics)

    timestamp = ""
    if use_varnishstat_timestamp:
      pattern = "%Y-%m-%dT%H:%M:%S"
      timestamp = int(time.mktime(time.strptime(metrics['timestamp'], pattern)))
    else:
      timestamp = time.time()

    for k, v in metrics.iteritems():
      if k != "timestamp" and None == bad_regex.search(k):
        metric_name = metric_prefix + "." + k
        print "%s %d %s %s" % \
          (metric_name, timestamp, v['value'], ",".join(tags))

    sys.stdout.flush()
    time.sleep(interval)

if __name__ == "__main__":
  sys.exit(main())

########NEW FILE########
__FILENAME__ = zfsiostats
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2012  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#

import errno
import sys
import time
import subprocess
import re
import signal
import os


'''
ZFS I/O and disk space statistics for TSDB

This plugin tracks, for all pools:

- I/O
  zfs.io.pool.{read_issued, write_issued}
  zfs.io.pool.{read_sectors, write_sectors}
  zfs.io.device.{read_issued, write_issued}
  zfs.io.device.{read_sectors, write_sectors}
- disk space
  zfs.df.pool.1kblocks.{total, used, available}
  zfs.df.device.1kblocks.{total, used, available}

Sectors are always 512 bytes.  Disk space usage is given in 1K blocks.
Values delivered to standard output are already normalized to be per second.
'''

def convert_to_bytes(string):
    """Take a string in the form 1234K, and convert to bytes"""
    factors = {
       "K": 1024,
       "M": 1024 * 1024,
       "G": 1024 * 1024 * 1024,
       "T": 1024 * 1024 * 1024 * 1024,
       "P": 1024 * 1024 * 1024 * 1024 * 1024,
    }
    if string == "-": return 0
    for f, fm in factors.items():
        if string.endswith(f):
            number = float(string[:-1])
            number = number * fm
            return long(number)
    return long(string)

def extract_info(line):
    (poolname,
        alloc, free,
        read_issued, write_issued,
        read_sectors, write_sectors) = line.split()

    s_df = {}
    # 1k blocks
    s_df["used"] = convert_to_bytes(alloc) / 1024
    s_df["available"] = convert_to_bytes(free) / 1024
    s_df["total"] = s_df["used"] + s_df["available"]

    s_io = {}
    # magnitudeless variable
    s_io["read_issued"] = read_issued
    s_io["write_issued"] = write_issued
    # 512 byte sectors
    s_io["read_sectors"] = convert_to_bytes(read_sectors) / 512
    s_io["write_sectors"] = convert_to_bytes(write_sectors) / 512

    return poolname, s_df, s_io

T_START = 1
T_HEADERS = 2
T_SEPARATOR = 3
T_POOL = 4
T_DEVICE = 5
T_EMPTY = 6
T_LEG = 7

signal_received = None
def handlesignal(signum, stack):
    global signal_received
    signal_received = signum

def main():
    """zfsiostats main loop"""
    global signal_received
    interval = 15
    # shouldn't the interval be determined by the daemon itself, and commu-
    # nicated to the collector somehow (signals seem like a reasonable protocol
    # whereas command-line parameters also sound reasonable)?

    signal.signal(signal.SIGTERM, handlesignal)
    signal.signal(signal.SIGINT, handlesignal)

    try:
        p_zpool = subprocess.Popen(
            ["zpool", "iostat", "-v", str(interval)],
            stdout=subprocess.PIPE,
        )
    except OSError, e:
        if e.errno == errno.ENOENT:
            # it makes no sense to run this collector here
            sys.exit(13) # we signal tcollector to not run us
        raise

    firstloop = True
    lastleg = 0
    ltype = None
    timestamp = int(time.time())
    capacity_stats_pool = {}
    capacity_stats_device = {}
    io_stats_pool = {}
    io_stats_device = {}
    start_re = re.compile(".*capacity.*operations.*bandwidth")
    headers_re = re.compile(".*pool.*alloc.*free.*read.*write.*read.*write")
    separator_re = re.compile(".*-----.*-----.*-----")
    while signal_received is None:
        try:
            line = p_zpool.stdout.readline()
        except (IOError, OSError), e:
            if e.errno in (errno.EINTR, errno.EAGAIN):
                break
            raise

        if not line:
            # end of the program, die
            break

        if start_re.match(line):
            assert ltype in (None, T_EMPTY), \
                "expecting last state T_EMPTY or None, now got %s" % ltype
            ltype = T_START
        elif headers_re.match(line):
            assert ltype == T_START, \
                "expecting last state T_START, now got %s" % ltype
            ltype = T_HEADERS
        elif separator_re.match(line):
            assert ltype in (T_DEVICE, T_HEADERS), \
                "expecting last state T_DEVICE or T_HEADERS, now got %s" % ltype
            ltype = T_SEPARATOR
        elif len(line) < 2:
            assert ltype == T_SEPARATOR, \
                "expecting last state T_SEPARATOR, now got %s" % ltype
            ltype = T_EMPTY
        elif line.startswith("  mirror"):
            assert ltype in (T_POOL, T_DEVICE), \
                "expecting last state T_POOL or T_DEVICE, now got %s" % ltype
            ltype = T_LEG
        elif line.startswith("  "):
            assert ltype in (T_POOL, T_DEVICE, T_LEG), \
                "expecting last state T_POOL or T_DEVICE or T_LEG, now got %s" % ltype
            ltype = T_DEVICE
        else:
            # must be a pool name
            assert ltype == T_SEPARATOR, \
                "expecting last state T_SEPARATOR, now got %s" % ltype
            ltype = T_POOL

        if ltype == T_START:
            for x in (
                      capacity_stats_pool, capacity_stats_device,
                      io_stats_pool, io_stats_device,
                      ):
                x.clear()
            timestamp = int(time.time())

        elif ltype == T_POOL:
            line = line.strip()
            poolname, s_df, s_io = extract_info(line)
            capacity_stats_pool[poolname] = s_df
            io_stats_pool[poolname] = s_io
            # marker for leg
            last_leg = 0

        elif ltype == T_LEG:
            last_leg = last_leg + 1
            line = line.strip()
            devicename, s_df, s_io = extract_info(line)
            capacity_stats_device["%s %s%s" % (poolname, devicename, last_leg)] = s_df
            io_stats_device["%s %s%s" % (poolname, devicename, last_leg)] = s_io

        elif ltype == T_DEVICE:
            line = line.strip()
            devicename, s_df, s_io = extract_info(line)
            capacity_stats_device["%s %s" % (poolname, devicename)] = s_df
            io_stats_device["%s %s" % (poolname, devicename)] = s_io

        elif ltype == T_EMPTY:
            if firstloop:
                firstloop = False
            else:
                # this flag prevents printing out of the data in the first loop
                # which is a since-boot summary similar to iostat
                # and is useless to us
                for poolname, stats in capacity_stats_pool.items():
                    fm = "zfs.df.pool.1kblocks.%s %d %s poolname=%s"
                    for statname, statnumber in stats.items():
                        print fm % (statname, timestamp, statnumber, poolname)
                for poolname, stats in io_stats_pool.items():
                    fm = "zfs.io.pool.%s %d %s poolname=%s"
                    for statname, statnumber in stats.items():
                        print fm % (statname, timestamp, statnumber, poolname)
                for devicename, stats in capacity_stats_device.items():
                    fm = "zfs.df.device.1kblocks.%s %d %s devicename=%s poolname=%s"
                    poolname, devicename = devicename.split(" ", 1)
                    for statname, statnumber in stats.items():
                        print fm % (statname, timestamp, statnumber,
                                    devicename, poolname)
                for devicename, stats in io_stats_device.items():
                    fm = "zfs.io.device.%s %d %s devicename=%s poolname=%s"
                    poolname, devicename = devicename.split(" ", 1)
                    for statname, statnumber in stats.items():
                        print fm % (statname, timestamp, statnumber,
                                    devicename, poolname)
                sys.stdout.flush()
                # if this was the first loop, well, we're onto the second loop
                # so we turh the flag off

    if signal_received is None:
        signal_received = signal.SIGTERM
    try:
        os.kill(p_zpool.pid, signal_received)
    except Exception:
        pass
    p_zpool.wait()

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = zfskernstats
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2012  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#

import errno
import re
import sys
import time

'''
ZFS kernel memory statistics for TSDB

This plugin tracks kernel memory for both:

- the SPL and its allocated slabs backing ZFS memory
  zfs.mem.slab
- the ARC and its various values
  zfs.mem.arc
'''

# /proc/spl/slab has several fields.  we only care about the sizes
# and the allocation sizes for the slabs
# /proc/spl/kstat/zfs/arcstats is a table.  we only care about the data column

def main():
    """zfsstat main loop"""
    interval = 15
    typere = re.compile("(^.*)_[0-9]+$")

    try:
        f_slab = open("/proc/spl/kmem/slab", "r")
        f_arcstats = open("/proc/spl/kstat/zfs/arcstats", "r")
    except IOError, e:
        if e.errno == errno.ENOENT:
            # it makes no sense to run this collector here
            sys.exit(13) # we signal tcollector to not run us
        raise

    while True:
        f_slab.seek(0)
        f_arcstats.seek(0)
        ts = int(time.time())

        for n, line in enumerate(f_slab):
            if n < 2:
                continue
            line = line.split()
            name, _, size, alloc, _, objsize = line[0:6]
            size, alloc, objsize = int(size), int(alloc), int(objsize)
            typ = typere.match(name)
            if typ:
                typ = typ.group(1)
            else:
                typ = name
            print ("zfs.mem.slab.size %d %d type=%s objsize=%d" %
                  (ts, size, typ, objsize)
            )
            print ("zfs.mem.slab.alloc %d %d type=%s objsize=%d" %
                  (ts, alloc, typ, objsize)
            )

        for n, line in enumerate(f_arcstats):
            if n < 2:
                continue
            line = line.split()
            name, _, data = line
            data = int(data)
            print ("zfs.mem.arc.%s %d %d" %
                  (name, ts, data)
            )

        sys.stdout.flush()
        time.sleep(interval)

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = zookeeper
#!/usr/bin/python

""" 
Zookeeper collector

Refer to the following zookeeper commands documentation for details:
http://zookeeper.apache.org/doc/trunk/zookeeperAdmin.html#sc_zkCommands
"""

import sys
import socket
import time
import subprocess
import re
from collectors.lib import utils

COLLECTION_INTERVAL = 15  # seconds

# Every SCAN_INTERVAL seconds, we look for new zookeeper instances.
# Prevents the situation where you put up a new instance and we never notice.
SCAN_INTERVAL = 600

# If we are root, drop privileges to this user, if necessary.
# NOTE: if this is not root, this MUST be the user that you run zookeeper
# server under. If not, we will not be able to find your Zookeeper instances.
USER = "root"

KEYS = frozenset([
    "zk_avg_latency",
    "zk_max_latency",
    "zk_min_latency",
    "zk_packets_received",
    "zk_packets_sent",
    "zk_num_alive_connections",
    "zk_outstanding_requests",
    "zk_approximate_data_size",
    "zk_open_file_descriptor_count",
    ])

def err(e):
    print >> sys.stderr, e

def scan_zk_instances():
    """ 
    Finding out all the running instances of zookeeper
    - Using netstat, finds out all listening java processes.	 
    - Figures out ZK instances among java processes by looking for the 
      string "org.apache.zookeeper.server.quorum.QuorumPeerMain" in cmdline.
    """

    instances = []
    try:
        listen_sock = subprocess.check_output(["netstat", "-lnpt"], stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        err("netstat directory doesn't exist in PATH variable")
        return instances

    for line in listen_sock.split("\n"):
        if not "java" in line:
            continue
        listen_sock = line.split()[3]
        tcp_version = line.split()[0]

        m = re.match("(.+):(\d+)", listen_sock)
        ip = m.group(1)
        port = int(m.group(2))

        pid = int(line.split()[6].split("/")[0])
        try:
            fd = open("/proc/%d/cmdline" % pid)
            cmdline = fd.readline()
            if "org.apache.zookeeper.server.quorum.QuorumPeerMain" in cmdline:
                try:
                    if tcp_version == "tcp6":
                        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    else:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    sock.connect((ip, port))
                    sock.send("ruok\n")
                    data = sock.recv(1024)
                except:
                    pass
                finally:
                    sock.close()
                if data == "imok":	
                    instances.append([ip, port, tcp_version])
                    data = ""
        except:
            continue
        finally:
            fd.close()
    return instances 

def print_stat(metric, ts, value, tags=""):
    if value is not None:
        print "zookeeper.%s %i %s %s" % (metric, ts, value, tags)

def main():
    if USER != "root":
        utils.drop_privileges(user=USER)

    last_scan = time.time()
    instances = scan_zk_instances()

    while True:
        ts = time.time()

        # We haven't looked for zookeeper instance recently, let's do that
        if ts - last_scan > SCAN_INTERVAL:
            instances = scan_zk_instances()
            last_scan = ts

        if not instances:
            return 13  # Ask tcollector not to respawn us

        # Iterate over every zookeeper instance and get statistics
        for ip, port, tcp_version in instances:
            tags = "port=%s" % port
            if tcp_version == "tcp6":
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((ip, port))
            except:
                err("ZK Instance listening at port %d went away" % port)
                instances.remove([ip, port, tcp_version])
                break

            sock.send("mntr\n")
            data = sock.recv(1024)
            for stat in data.splitlines():
                metric = stat.split()[0]
                value = stat.split()[1]
                if metric in KEYS:
                    print_stat(metric, ts, value, tags)
            sock.close()

        time.sleep(COLLECTION_INTERVAL)

if __name__ == "__main__":
    sys.exit(main())	

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

# This 'onload' function will be called by tcollector when it starts up.
# You can put any code here that you want to load inside the tcollector.
# This also gives you a chance to override the options from the command
# line or to add custom sanity checks on their values.
# You can also use this to change the global tags that will be added to
# every single data point.  For instance if you have multiple different
# pools or clusters of machines, you might wanna lookup the name of the
# pool or cluster the current host belongs to and add it to the tags.
# Throwing an exception here will cause the tcollector to die before it
# starts doing any work.
# Python files in this directory that don't have an "onload" function
# will be imported by tcollector too, but no function will be called.
# When this file executes, you can assume that its directory is in
# sys.path, so you can import other Python modules from this directory
# or its subdirectories.

def onload(options, tags):
  """Function called by tcollector when it starts up.

  Args:
    options: The options as returned by the OptionParser.
    tags: A dictionnary that maps tag names to tag values.
  """
  pass

########NEW FILE########
__FILENAME__ = graphite_bridge_conf
#!/usr/bin/env python

def enabled():
  return False

########NEW FILE########
__FILENAME__ = mysqlconf
#!/usr/bin/env python

def get_user_password(sockfile):
  """Given the path of a socket file, returns a tuple (user, password)."""
  return ("root", "")

########NEW FILE########
__FILENAME__ = postgresqlconf
#!/usr/bin/env python

def get_user_password():
  """Returns a tuple (user, password)."""
  # ensure that user has enough power to get data from DB
  return ("root", "")

########NEW FILE########
__FILENAME__ = udp_bridge_conf
#!/usr/bin/env python

def enabled():
  return False

########NEW FILE########
__FILENAME__ = hadoop_http
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2011-2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

import httplib
try:
    import json
except ImportError:
    json = None
try:
    from collections import OrderedDict  # New in Python 2.7
except ImportError:
    from ordereddict import OrderedDict  # Can be easy_install'ed for <= 2.6
from collectors.lib.utils import is_numeric

EXCLUDED_KEYS = (
    "Name",
    "name"
)

class HadoopHttp(object):
    def __init__(self, service, daemon, host, port, uri="/jmx"):
        self.service = service
        self.daemon = daemon
        self.port = port
        self.host = host
        self.uri = uri
        self.server = httplib.HTTPConnection(self.host, self.port)
        self.server.connect()

    def request(self):
        self.server.request('GET', self.uri)
        resp = self.server.getresponse()
        return json.loads(resp.read())

    def poll(self):
        """
        Get metrics from the http server's /jmx page, and transform them into normalized tupes

        @return: array of tuples ([u'Context', u'Array'], u'metricName', value)
        """
        json_arr = self.request()['beans']
        kept = []
        for bean in json_arr:
            if (not bean['name']) or (not "name=" in bean['name']):
                continue
            #split the name string
            context = bean['name'].split("name=")[1].split(",sub=")
            # Create a set that keeps the first occurrence
            context = OrderedDict.fromkeys(context).keys()
            # lower case and replace spaces.
            context = [c.lower().replace(" ", "_") for c in context]
            # don't want to include the service or daemon twice
            context = [c for c in context if c != self.service and c != self.daemon]

            for key, value in bean.iteritems():
                if key in EXCLUDED_KEYS:
                    continue
                if not is_numeric(value):
                    continue
                kept.append((context, key, value))
        return kept

    def emit_metric(self, context, current_time, metric_name, value, tag_dict=None):
        if not tag_dict:
            print "%s.%s.%s.%s %d %d" % (self.service, self.daemon, ".".join(context), metric_name, current_time, value)
        else:
            tag_string = " ".join([k + "=" + v for k, v in tag_dict.iteritems()])
            print "%s.%s.%s.%s %d %d %s" % \
                  (self.service, self.daemon, ".".join(context), metric_name, current_time, value, tag_string)

    def emit(self):
        pass

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

"""Common utility functions shared for Python collectors"""

import os
import stat
import pwd
import errno
import sys

# If we're running as root and this user exists, we'll drop privileges.
USER = "nobody"


def drop_privileges(user=USER):
    """Drops privileges if running as root."""
    try:
        ent = pwd.getpwnam(user)
    except KeyError:
        return

    if os.getuid() != 0:
        return

    os.setgid(ent.pw_gid)
    os.setuid(ent.pw_uid)


def is_sockfile(path):
    """Returns whether or not the given path is a socket file."""
    try:
        s = os.stat(path)
    except OSError, (no, e):
        if no == errno.ENOENT:
            return False
        err("warning: couldn't stat(%r): %s" % (path, e))
        return None
    return s.st_mode & stat.S_IFSOCK == stat.S_IFSOCK


def err(msg):
    print >> sys.stderr, msg


def is_numeric(value):
    return isinstance(value, (int, long, float))
########NEW FILE########
__FILENAME__ = tcollector
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#
# tcollector.py
#
"""Simple manager for collection scripts that run and gather data.
   The tcollector gathers the data and sends it to the TSD for storage."""
#
# by Mark Smith <msmith@stumbleupon.com>.
#

import atexit
import errno
import fcntl
import logging
import os
import random
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from Queue import Queue
from Queue import Empty
from Queue import Full
from optparse import OptionParser


# global variables.
COLLECTORS = {}
GENERATION = 0
DEFAULT_LOG = '/var/log/tcollector.log'
LOG = logging.getLogger('tcollector')
ALIVE = True
# If the SenderThread catches more than this many consecutive uncaught
# exceptions, something is not right and tcollector will shutdown.
# Hopefully some kind of supervising daemon will then restart it.
MAX_UNCAUGHT_EXCEPTIONS = 100
DEFAULT_PORT = 4242
MAX_REASONABLE_TIMESTAMP = 1600000000  # Good until September 2020 :)
# How long to wait for datapoints before assuming
# a collector is dead and restarting it
ALLOWED_INACTIVITY_TIME = 600  # seconds
MAX_SENDQ_SIZE = 10000
MAX_READQ_SIZE = 100000


def register_collector(collector):
    """Register a collector with the COLLECTORS global"""

    assert isinstance(collector, Collector), "collector=%r" % (collector,)
    # store it in the global list and initiate a kill for anybody with the
    # same name that happens to still be hanging around
    if collector.name in COLLECTORS:
        col = COLLECTORS[collector.name]
        if col.proc is not None:
            LOG.error('%s still has a process (pid=%d) and is being reset,'
                      ' terminating', col.name, col.proc.pid)
            col.shutdown()

    COLLECTORS[collector.name] = collector


class ReaderQueue(Queue):
    """A Queue for the reader thread"""

    def nput(self, value):
        """A nonblocking put, that simply logs and discards the value when the
           queue is full, and returns false if we dropped."""
        try:
            self.put(value, False)
        except Full:
            LOG.error("DROPPED LINE: %s", value)
            return False
        return True


class Collector(object):
    """A Collector is a script that is run that gathers some data
       and prints it out in standard TSD format on STDOUT.  This
       class maintains all of the state information for a given
       collector and gives us utility methods for working with
       it."""

    def __init__(self, colname, interval, filename, mtime=0, lastspawn=0):
        """Construct a new Collector."""
        self.name = colname
        self.interval = interval
        self.filename = filename
        self.lastspawn = lastspawn
        self.proc = None
        self.nextkill = 0
        self.killstate = 0
        self.dead = False
        self.mtime = mtime
        self.generation = GENERATION
        self.buffer = ""
        self.datalines = []
        # Maps (metric, tags) to (value, repeated, line, timestamp) where:
        #  value: Last value seen.
        #  repeated: boolean, whether the last value was seen more than once.
        #  line: The last line that was read from that collector.
        #  timestamp: Time at which we saw the value for the first time.
        # This dict is used to keep track of and remove duplicate values.
        # Since it might grow unbounded (in case we see many different
        # combinations of metrics and tags) someone needs to regularly call
        # evict_old_keys() to remove old entries.
        self.values = {}
        self.lines_sent = 0
        self.lines_received = 0
        self.lines_invalid = 0
        self.last_datapoint = int(time.time())

    def read(self):
        """Read bytes from our subprocess and store them in our temporary
           line storage buffer.  This needs to be non-blocking."""

        # we have to use a buffer because sometimes the collectors
        # will write out a bunch of data points at one time and we
        # get some weird sized chunk.  This read call is non-blocking.

        # now read stderr for log messages, we could buffer here but since
        # we're just logging the messages, I don't care to
        try:
            out = self.proc.stderr.read()
            if out:
                LOG.debug('reading %s got %d bytes on stderr',
                          self.name, len(out))
                for line in out.splitlines():
                    LOG.warning('%s: %s', self.name, line)
        except IOError, (err, msg):
            if err != errno.EAGAIN:
                raise
        except:
            LOG.exception('uncaught exception in stderr read')

        # we have to use a buffer because sometimes the collectors will write
        # out a bunch of data points at one time and we get some weird sized
        # chunk.  This read call is non-blocking.
        try:
            self.buffer += self.proc.stdout.read()
            if len(self.buffer):
                LOG.debug('reading %s, buffer now %d bytes',
                          self.name, len(self.buffer))
        except IOError, (err, msg):
            if err != errno.EAGAIN:
                raise
        except:
            # sometimes the process goes away in another thread and we don't
            # have it anymore, so log an error and bail
            LOG.exception('uncaught exception in stdout read')
            return

        # iterate for each line we have
        while self.buffer:
            idx = self.buffer.find('\n')
            if idx == -1:
                break

            # one full line is now found and we can pull it out of the buffer
            line = self.buffer[0:idx].strip()
            if line:
                self.datalines.append(line)
                self.last_datapoint = int(time.time())
            self.buffer = self.buffer[idx+1:]

    def collect(self):
        """Reads input from the collector and returns the lines up to whomever
           is calling us.  This is a generator that returns a line as it
           becomes available."""

        while self.proc is not None:
            self.read()
            if not len(self.datalines):
                return
            while len(self.datalines):
                yield self.datalines.pop(0)

    def shutdown(self):
        """Cleanly shut down the collector"""

        if not self.proc:
            return
        try:
            if self.proc.poll() is None:
                kill(self.proc)
                for attempt in range(5):
                    if self.proc.poll() is not None:
                        return
                    LOG.info('Waiting %ds for PID %d (%s) to exit...'
                             % (5 - attempt, self.proc.pid, self.name))
                    time.sleep(1)
                kill(self.proc, signal.SIGKILL)
                self.proc.wait()
        except:
            # we really don't want to die as we're trying to exit gracefully
            LOG.exception('ignoring uncaught exception while shutting down')

    def evict_old_keys(self, cut_off):
        """Remove old entries from the cache used to detect duplicate values.

        Args:
          cut_off: A UNIX timestamp.  Any value that's older than this will be
            removed from the cache.
        """
        for key in self.values.keys():
            time = self.values[key][3]
            if time < cut_off:
                del self.values[key]


class StdinCollector(Collector):
    """A StdinCollector simply reads from STDIN and provides the
       data.  This collector presents a uniform interface for the
       ReaderThread, although unlike a normal collector, read()/collect()
       will be blocking."""

    def __init__(self):
        super(StdinCollector, self).__init__('stdin', 0, '<stdin>')

        # hack to make this work.  nobody else will rely on self.proc
        # except as a test in the stdin mode.
        self.proc = True

    def read(self):
        """Read lines from STDIN and store them.  We allow this to
           be blocking because there should only ever be one
           StdinCollector and no normal collectors, so the ReaderThread
           is only serving us and we're allowed to block it."""

        global ALIVE
        line = sys.stdin.readline()
        if line:
            self.datalines.append(line.rstrip())
        else:
            ALIVE = False


    def shutdown(self):

        pass


class ReaderThread(threading.Thread):
    """The main ReaderThread is responsible for reading from the collectors
       and assuring that we always read from the input no matter what.
       All data read is put into the self.readerq Queue, which is
       consumed by the SenderThread."""

    def __init__(self, dedupinterval, evictinterval):
        """Constructor.
            Args:
              dedupinterval: If a metric sends the same value over successive
                intervals, suppress sending the same value to the TSD until
                this many seconds have elapsed.  This helps graphs over narrow
                time ranges still see timeseries with suppressed datapoints.
              evictinterval: In order to implement the behavior above, the
                code needs to keep track of the last value seen for each
                combination of (metric, tags).  Values older than
                evictinterval will be removed from the cache to save RAM.
                Invariant: evictinterval > dedupinterval
        """
        assert evictinterval > dedupinterval, "%r <= %r" % (evictinterval,
                                                            dedupinterval)
        super(ReaderThread, self).__init__()

        self.readerq = ReaderQueue(MAX_READQ_SIZE)
        self.lines_collected = 0
        self.lines_dropped = 0
        self.dedupinterval = dedupinterval
        self.evictinterval = evictinterval

    def run(self):
        """Main loop for this thread.  Just reads from collectors,
           does our input processing and de-duping, and puts the data
           into the queue."""

        LOG.debug("ReaderThread up and running")

        lastevict_time = 0
        # we loop every second for now.  ideally we'll setup some
        # select or other thing to wait for input on our children,
        # while breaking out every once in a while to setup selects
        # on new children.
        while ALIVE:
            for col in all_living_collectors():
                for line in col.collect():
                    self.process_line(col, line)

            if self.dedupinterval != 0:  # if 0 we do not use dedup
                now = int(time.time())
                if now - lastevict_time > self.evictinterval:
                    lastevict_time = now
                    now -= self.evictinterval
                    for col in all_collectors():
                        col.evict_old_keys(now)

            # and here is the loop that we really should get rid of, this
            # just prevents us from spinning right now
            time.sleep(1)

    def process_line(self, col, line):
        """Parses the given line and appends the result to the reader queue."""

        self.lines_collected += 1

        col.lines_received += 1
        if len(line) >= 1024:  # Limit in net.opentsdb.tsd.PipelineFactory
            LOG.warning('%s line too long: %s', col.name, line)
            col.lines_invalid += 1
            return
        parsed = re.match('^([-_./a-zA-Z0-9]+)\s+' # Metric name.
                          '(\d+)\s+'               # Timestamp.
                          '(\S+?)'                 # Value (int or float).
                          '((?:\s+[-_./a-zA-Z0-9]+=[-_./a-zA-Z0-9]+)*)$', # Tags
                          line)
        if parsed is None:
            LOG.warning('%s sent invalid data: %s', col.name, line)
            col.lines_invalid += 1
            return
        metric, timestamp, value, tags = parsed.groups()
        timestamp = int(timestamp)

        # De-dupe detection...  To reduce the number of points we send to the
        # TSD, we suppress sending values of metrics that don't change to
        # only once every 10 minutes (which is also when TSD changes rows
        # and how much extra time the scanner adds to the beginning/end of a
        # graph interval in order to correctly calculate aggregated values).
        # When the values do change, we want to first send the previous value
        # with what the timestamp was when it first became that value (to keep
        # slopes of graphs correct).
        #
        if self.dedupinterval != 0:  # if 0 we do not use dedup
            key = (metric, tags)
            if key in col.values:
                # if the timestamp isn't > than the previous one, ignore this value
                if timestamp <= col.values[key][3]:
                    LOG.error("Timestamp out of order: metric=%s%s,"
                              " old_ts=%d >= new_ts=%d - ignoring data point"
                              " (value=%r, collector=%s)", metric, tags,
                              col.values[key][3], timestamp, value, col.name)
                    col.lines_invalid += 1
                    return
                elif timestamp >= MAX_REASONABLE_TIMESTAMP:
                    LOG.error("Timestamp is too far out in the future: metric=%s%s"
                              " old_ts=%d, new_ts=%d - ignoring data point"
                              " (value=%r, collector=%s)", metric, tags,
                              col.values[key][3], timestamp, value, col.name)
                    return

                # if this data point is repeated, store it but don't send.
                # store the previous timestamp, so when/if this value changes
                # we send the timestamp when this metric first became the current
                # value instead of the last.  Fall through if we reach
                # the dedup interval so we can print the value.
                if (col.values[key][0] == value and
                    (timestamp - col.values[key][3] < self.dedupinterval)):
                    col.values[key] = (value, True, line, col.values[key][3])
                    return

                # we might have to append two lines if the value has been the same
                # for a while and we've skipped one or more values.  we need to
                # replay the last value we skipped (if changed) so the jumps in
                # our graph are accurate,
                if ((col.values[key][1] or
                    (timestamp - col.values[key][3] >= self.dedupinterval))
                    and col.values[key][0] != value):
                    col.lines_sent += 1
                    if not self.readerq.nput(col.values[key][2]):
                        self.lines_dropped += 1

            # now we can reset for the next pass and send the line we actually
            # want to send
            # col.values is a dict of tuples, with the key being the metric and
            # tags (essentially the same as wthat TSD uses for the row key).
            # The array consists of:
            # [ the metric's value, if this value was repeated, the line of data,
            #   the value's timestamp that it last changed ]
            col.values[key] = (value, False, line, timestamp)

        col.lines_sent += 1
        if not self.readerq.nput(line):
            self.lines_dropped += 1


class SenderThread(threading.Thread):
    """The SenderThread is responsible for maintaining a connection
       to the TSD and sending the data we're getting over to it.  This
       thread is also responsible for doing any sort of emergency
       buffering we might need to do if we can't establish a connection
       and we need to spool to disk.  That isn't implemented yet."""

    def __init__(self, reader, dryrun, hosts, self_report_stats, tags):
        """Constructor.

        Args:
          reader: A reference to a ReaderThread instance.
          dryrun: If true, data points will be printed on stdout instead of
            being sent to the TSD.
          hosts: List of (host, port) tuples defining list of TSDs
          self_report_stats: If true, the reader thread will insert its own
            stats into the metrics reported to TSD, as if those metrics had
            been read from a collector.
          tags: A dictionary of tags to append for every data point.
        """
        super(SenderThread, self).__init__()

        self.dryrun = dryrun
        self.reader = reader
        self.tags = sorted(tags.items())
        self.hosts = hosts  # A list of (host, port) pairs.
        # Randomize hosts to help even out the load.
        random.shuffle(self.hosts)
        self.blacklisted_hosts = set()  # The 'bad' (host, port) pairs.
        self.current_tsd = -1  # Index in self.hosts where we're at.
        self.host = None  # The current TSD host we've selected.
        self.port = None  # The port of the current TSD.
        self.tsd = None   # The socket connected to the aforementioned TSD.
        self.last_verify = 0
        self.sendq = []
        self.self_report_stats = self_report_stats

    def pick_connection(self):
        """Picks up a random host/port connection."""
        # Try to get the next host from the list, until we find a host that
        # isn't in the blacklist, or until we run out of hosts (i.e. they
        # are all blacklisted, which typically happens when we lost our
        # connectivity to the outside world).
        for self.current_tsd in xrange(self.current_tsd + 1, len(self.hosts)):
            hostport = self.hosts[self.current_tsd]
            if hostport not in self.blacklisted_hosts:
                break
        else:
            LOG.info('No more healthy hosts, retry with previously blacklisted')
            random.shuffle(self.hosts)
            self.blacklisted_hosts.clear()
            self.current_tsd = 0
            hostport = self.hosts[self.current_tsd]

        self.host, self.port = hostport
        LOG.info('Selected connection: %s:%d', self.host, self.port)

    def blacklist_connection(self):
        """Marks the current TSD host we're trying to use as blacklisted.

           Blacklisted hosts will get another chance to be elected once there
           will be no more healthy hosts."""
        # FIXME: Enhance this naive strategy.
        LOG.info('Blacklisting %s:%s for a while', self.host, self.port)
        self.blacklisted_hosts.add((self.host, self.port))

    def run(self):
        """Main loop.  A simple scheduler.  Loop waiting for 5
           seconds for data on the queue.  If there's no data, just
           loop and make sure our connection is still open.  If there
           is data, wait 5 more seconds and grab all of the pending data and
           send it.  A little better than sending every line as its
           own packet."""

        errors = 0  # How many uncaught exceptions in a row we got.
        while ALIVE:
            try:
                self.maintain_conn()
                try:
                    line = self.reader.readerq.get(True, 5)
                except Empty:
                    continue
                self.sendq.append(line)
                time.sleep(5)  # Wait for more data
                while True:
                    # prevents self.sendq fast growing in case of sending fails
                    # in send_data()
                    if len(self.sendq) > MAX_SENDQ_SIZE:
                        break
                    try:
                        line = self.reader.readerq.get(False)
                    except Empty:
                        break
                    self.sendq.append(line)

                self.send_data()
                errors = 0  # We managed to do a successful iteration.
            except (ArithmeticError, EOFError, EnvironmentError, LookupError,
                    ValueError), e:
                errors += 1
                if errors > MAX_UNCAUGHT_EXCEPTIONS:
                    shutdown()
                    raise
                LOG.exception('Uncaught exception in SenderThread, ignoring')
                time.sleep(1)
                continue
            except:
                LOG.exception('Uncaught exception in SenderThread, going to exit')
                shutdown()
                raise

    def verify_conn(self):
        """Periodically verify that our connection to the TSD is OK
           and that the TSD is alive/working."""
        if self.tsd is None:
            return False

        # if the last verification was less than a minute ago, don't re-verify
        if self.last_verify > time.time() - 60:
            return True

        # we use the version command as it is very low effort for the TSD
        # to respond
        LOG.debug('verifying our TSD connection is alive')
        try:
            self.tsd.sendall('version\n')
        except socket.error, msg:
            self.tsd = None
            self.blacklist_connection()
            return False

        bufsize = 4096
        while ALIVE:
            # try to read as much data as we can.  at some point this is going
            # to block, but we have set the timeout low when we made the
            # connection
            try:
                buf = self.tsd.recv(bufsize)
            except socket.error, msg:
                self.tsd = None
                self.blacklist_connection()
                return False

            # If we don't get a response to the `version' request, the TSD
            # must be dead or overloaded.
            if not buf:
                self.tsd = None
                self.blacklist_connection()
                return False

            # Woah, the TSD has a lot of things to tell us...  Let's make
            # sure we read everything it sent us by looping once more.
            if len(buf) == bufsize:
                continue

            # If everything is good, send out our meta stats.  This
            # helps to see what is going on with the tcollector.
            if self.self_report_stats:
                strs = [
                        ('reader.lines_collected',
                         '', self.reader.lines_collected),
                        ('reader.lines_dropped',
                         '', self.reader.lines_dropped)
                       ]

                for col in all_living_collectors():
                    strs.append(('collector.lines_sent', 'collector='
                                 + col.name, col.lines_sent))
                    strs.append(('collector.lines_received', 'collector='
                                 + col.name, col.lines_received))
                    strs.append(('collector.lines_invalid', 'collector='
                                 + col.name, col.lines_invalid))

                ts = int(time.time())
                strout = ["tcollector.%s %d %d %s"
                          % (x[0], ts, x[2], x[1]) for x in strs]
                for string in strout:
                    self.sendq.append(string)

            break  # TSD is alive.

        # if we get here, we assume the connection is good
        self.last_verify = time.time()
        return True

    def maintain_conn(self):
        """Safely connect to the TSD and ensure that it's up and
           running and that we're not talking to a ghost connection
           (no response)."""

        # dry runs are always good
        if self.dryrun:
            return

        # connection didn't verify, so create a new one.  we might be in
        # this method for a long time while we sort this out.
        try_delay = 1
        while ALIVE:
            if self.verify_conn():
                return

            # increase the try delay by some amount and some random value,
            # in case the TSD is down for a while.  delay at most
            # approximately 10 minutes.
            try_delay *= 1 + random.random()
            if try_delay > 600:
                try_delay *= 0.5
            LOG.debug('SenderThread blocking %0.2f seconds', try_delay)
            time.sleep(try_delay)

            # Now actually try the connection.
            self.pick_connection()
            try:
                addresses = socket.getaddrinfo(self.host, self.port,
                                               socket.AF_UNSPEC,
                                               socket.SOCK_STREAM, 0)
            except socket.gaierror, e:
                # Don't croak on transient DNS resolution issues.
                if e[0] in (socket.EAI_AGAIN, socket.EAI_NONAME,
                            socket.EAI_NODATA):
                    LOG.debug('DNS resolution failure: %s: %s', self.host, e)
                    continue
                raise
            for family, socktype, proto, canonname, sockaddr in addresses:
                try:
                    self.tsd = socket.socket(family, socktype, proto)
                    self.tsd.settimeout(15)
                    self.tsd.connect(sockaddr)
                    # if we get here it connected
                    break
                except socket.error, msg:
                    LOG.warning('Connection attempt failed to %s:%d: %s',
                                self.host, self.port, msg)
                self.tsd.close()
                self.tsd = None
            if not self.tsd:
                LOG.error('Failed to connect to %s:%d', self.host, self.port)
                self.blacklist_connection()

    def add_tags_to_line(self, line):
        for tag, value in self.tags:
            if ' %s=' % tag not in line:
                line += ' %s=%s' % (tag, value)
        return line

    def send_data(self):
        """Sends outstanding data in self.sendq to the TSD in one operation."""

        # construct the output string
        out = ''

        # in case of logging we use less efficient variant
        if LOG.level == logging.DEBUG:
            for line in self.sendq:
                line = "put %s" % self.add_tags_to_line(line)
                out += line + "\n"
                LOG.debug('SENDING: %s', line)
        else:
            out = "".join("put %s\n" % self.add_tags_to_line(line) for line in self.sendq)

        if not out:
            LOG.debug('send_data no data?')
            return

        # try sending our data.  if an exception occurs, just error and
        # try sending again next time.
        try:
            if self.dryrun:
                print out
            else:
                self.tsd.sendall(out)
            self.sendq = []
        except socket.error, msg:
            LOG.error('failed to send data: %s', msg)
            try:
                self.tsd.close()
            except socket.error:
                pass
            self.tsd = None
            self.blacklist_connection()

        # FIXME: we should be reading the result at some point to drain
        # the packets out of the kernel's queue


def setup_logging(logfile=DEFAULT_LOG, max_bytes=None, backup_count=None):
    """Sets up logging and associated handlers."""

    LOG.setLevel(logging.INFO)
    if backup_count is not None and max_bytes is not None:
        assert backup_count > 0
        assert max_bytes > 0
        ch = RotatingFileHandler(logfile, 'a', max_bytes, backup_count)
    else:  # Setup stream handler.
        ch = logging.StreamHandler(sys.stdout)

    ch.setFormatter(logging.Formatter('%(asctime)s %(name)s[%(process)d] '
                                      '%(levelname)s: %(message)s'))
    LOG.addHandler(ch)


def parse_cmdline(argv):
    """Parses the command-line."""

    # get arguments
    default_cdir = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])),
                                'collectors')
    parser = OptionParser(description='Manages collectors which gather '
                                       'data and report back.')
    parser.add_option('-c', '--collector-dir', dest='cdir', metavar='DIR',
                      default=default_cdir,
                      help='Directory where the collectors are located.')
    parser.add_option('-d', '--dry-run', dest='dryrun', action='store_true',
                      default=False,
                      help='Don\'t actually send anything to the TSD, '
                           'just print the datapoints.')
    parser.add_option('-D', '--daemonize', dest='daemonize', action='store_true',
                      default=False, help='Run as a background daemon.')
    parser.add_option('-H', '--host', dest='host', default='localhost',
                      metavar='HOST',
                      help='Hostname to use to connect to the TSD.')
    parser.add_option('-L', '--hosts-list', dest='hosts', default=False,
                      metavar='HOSTS',
                      help='List of host:port to connect to tsd\'s (comma separated).')
    parser.add_option('--no-tcollector-stats', dest='no_tcollector_stats',
                      default=False, action='store_true',
                      help='Prevent tcollector from reporting its own stats to TSD')
    parser.add_option('-s', '--stdin', dest='stdin', action='store_true',
                      default=False,
                      help='Run once, read and dedup data points from stdin.')
    parser.add_option('-p', '--port', dest='port', type='int',
                      default=DEFAULT_PORT, metavar='PORT',
                      help='Port to connect to the TSD instance on. '
                           'default=%default')
    parser.add_option('-v', dest='verbose', action='store_true', default=False,
                      help='Verbose mode (log debug messages).')
    parser.add_option('-t', '--tag', dest='tags', action='append',
                      default=[], metavar='TAG',
                      help='Tags to append to all timeseries we send, '
                           'e.g.: -t TAG=VALUE -t TAG2=VALUE')
    parser.add_option('-P', '--pidfile', dest='pidfile',
                      default='/var/run/tcollector.pid',
                      metavar='FILE', help='Write our pidfile')
    parser.add_option('--dedup-interval', dest='dedupinterval', type='int',
                      default=300, metavar='DEDUPINTERVAL',
                      help='Number of seconds in which successive duplicate '
                           'datapoints are suppressed before sending to the TSD. '
                           'Use zero to disable. '
                           'default=%default')
    parser.add_option('--evict-interval', dest='evictinterval', type='int',
                      default=6000, metavar='EVICTINTERVAL',
                      help='Number of seconds after which to remove cached '
                           'values of old data points to save memory. '
                           'default=%default')
    parser.add_option('--max-bytes', dest='max_bytes', type='int',
                      default=64 * 1024 * 1024,
                      help='Maximum bytes per a logfile.')
    parser.add_option('--backup-count', dest='backup_count', type='int',
                      default=0, help='Maximum number of logfiles to backup.')
    parser.add_option('--logfile', dest='logfile', type='str',
                      default=DEFAULT_LOG,
                      help='Filename where logs are written to.')
    (options, args) = parser.parse_args(args=argv[1:])
    if options.dedupinterval < 0:
        parser.error('--dedup-interval must be at least 0 seconds')
    if options.evictinterval <= options.dedupinterval:
        parser.error('--evict-interval must be strictly greater than '
                     '--dedup-interval')
    # We cannot write to stdout when we're a daemon.
    if (options.daemonize or options.max_bytes) and not options.backup_count:
        options.backup_count = 1
    return (options, args)


def daemonize():
    """Performs the necessary dance to become a background daemon."""
    if os.fork():
        os._exit(0)
    os.chdir("/")
    os.umask(022)
    os.setsid()
    os.umask(0)
    if os.fork():
        os._exit(0)
    stdin = open(os.devnull)
    stdout = open(os.devnull, 'w')
    os.dup2(stdin.fileno(), 0)
    os.dup2(stdout.fileno(), 1)
    os.dup2(stdout.fileno(), 2)
    stdin.close()
    stdout.close()
    for fd in xrange(3, 1024):
        try:
            os.close(fd)
        except OSError:  # This FD wasn't opened...
            pass         # ... ignore the exception.


def setup_python_path(collector_dir):
    """Sets up PYTHONPATH so that collectors can easily import common code."""
    mydir = os.path.dirname(collector_dir)
    libdir = os.path.join(mydir, 'collectors', 'lib')
    if not os.path.isdir(libdir):
        return
    pythonpath = os.environ.get('PYTHONPATH', '')
    if pythonpath:
        pythonpath += ':'
    pythonpath += mydir
    os.environ['PYTHONPATH'] = pythonpath
    LOG.debug('Set PYTHONPATH to %r', pythonpath)


def main(argv):
    """The main tcollector entry point and loop."""

    options, args = parse_cmdline(argv)
    if options.daemonize:
        daemonize()
    setup_logging(options.logfile, options.max_bytes or None,
                  options.backup_count or None)

    if options.verbose:
        LOG.setLevel(logging.DEBUG)  # up our level

    if options.pidfile:
        write_pid(options.pidfile)

    # validate everything
    tags = {}
    for tag in options.tags:
        if re.match('^[-_.a-z0-9]+=\S+$', tag, re.IGNORECASE) is None:
            assert False, 'Tag string "%s" is invalid.' % tag
        k, v = tag.split('=', 1)
        if k in tags:
            assert False, 'Tag "%s" already declared.' % k
        tags[k] = v

    if not 'host' in tags and not options.stdin:
        tags['host'] = socket.gethostname()
        LOG.warning('Tag "host" not specified, defaulting to %s.', tags['host'])

    options.cdir = os.path.realpath(options.cdir)
    if not os.path.isdir(options.cdir):
        LOG.fatal('No such directory: %s', options.cdir)
        return 1
    modules = load_etc_dir(options, tags)

    setup_python_path(options.cdir)

    # gracefully handle death for normal termination paths and abnormal
    atexit.register(shutdown)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, shutdown_signal)

    # at this point we're ready to start processing, so start the ReaderThread
    # so we can have it running and pulling in data for us
    reader = ReaderThread(options.dedupinterval, options.evictinterval)
    reader.start()

    # prepare list of (host, port) of TSDs given on CLI
    if not options.hosts:
        options.hosts = [(options.host, options.port)]
    else:
        def splitHost(hostport):
            if ":" in hostport:
                # Check if we have an IPv6 address.
                if hostport[0] == "[" and "]:" in hostport:
                    host, port = hostport.split("]:")
                    host = host[1:]
                else:
                    host, port = hostport.split(":")
                return (host, int(port))
            return (hostport, DEFAULT_PORT)
        options.hosts = [splitHost(host) for host in options.hosts.split(",")]
        if options.host != "localhost" or options.port != DEFAULT_PORT:
            options.hosts.append((options.host, options.port))

    # and setup the sender to start writing out to the tsd
    sender = SenderThread(reader, options.dryrun, options.hosts,
                          not options.no_tcollector_stats, tags)
    sender.start()
    LOG.info('SenderThread startup complete')

    # if we're in stdin mode, build a stdin collector and just join on the
    # reader thread since there's nothing else for us to do here
    if options.stdin:
        register_collector(StdinCollector())
        stdin_loop(options, modules, sender, tags)
    else:
        sys.stdin.close()
        main_loop(options, modules, sender, tags)

    # We're exiting, make sure we don't leave any collector behind.
    for col in all_living_collectors():
      col.shutdown()
    LOG.debug('Shutting down -- joining the reader thread.')
    reader.join()
    LOG.debug('Shutting down -- joining the sender thread.')
    sender.join()

def stdin_loop(options, modules, sender, tags):
    """The main loop of the program that runs when we are in stdin mode."""

    global ALIVE
    next_heartbeat = int(time.time() + 600)
    while ALIVE:
        time.sleep(15)
        reload_changed_config_modules(modules, options, sender, tags)
        now = int(time.time())
        if now >= next_heartbeat:
            LOG.info('Heartbeat (%d collectors running)'
                     % sum(1 for col in all_living_collectors()))
            next_heartbeat = now + 600

def main_loop(options, modules, sender, tags):
    """The main loop of the program that runs when we're not in stdin mode."""

    next_heartbeat = int(time.time() + 600)
    while ALIVE:
        populate_collectors(options.cdir)
        reload_changed_config_modules(modules, options, sender, tags)
        reap_children()
        check_children()
        spawn_children()
        time.sleep(15)
        now = int(time.time())
        if now >= next_heartbeat:
            LOG.info('Heartbeat (%d collectors running)'
                     % sum(1 for col in all_living_collectors()))
            next_heartbeat = now + 600


def list_config_modules(etcdir):
    """Returns an iterator that yields the name of all the config modules."""
    if not os.path.isdir(etcdir):
        return iter(())  # Empty iterator.
    return (name for name in os.listdir(etcdir)
            if (name.endswith('.py')
                and os.path.isfile(os.path.join(etcdir, name))))


def load_etc_dir(options, tags):
    """Loads any Python module from tcollector's own 'etc' directory.

    Returns: A dict of path -> (module, timestamp).
    """

    etcdir = os.path.join(options.cdir, 'etc')
    sys.path.append(etcdir)  # So we can import modules from the etc dir.
    modules = {}  # path -> (module, timestamp)
    for name in list_config_modules(etcdir):
        path = os.path.join(etcdir, name)
        module = load_config_module(name, options, tags)
        modules[path] = (module, os.path.getmtime(path))
    return modules


def load_config_module(name, options, tags):
    """Imports the config module of the given name

    The 'name' argument can be a string, in which case the module will be
    loaded by name, or it can be a module object, in which case the module
    will get reloaded.

    If the module has an 'onload' function, calls it.
    Returns: the reference to the module loaded.
    """

    if isinstance(name, str):
      LOG.info('Loading %s', name)
      d = {}
      # Strip the trailing .py
      module = __import__(name[:-3], d, d)
    else:
      module = reload(name)
    onload = module.__dict__.get('onload')
    if callable(onload):
        try:
            onload(options, tags)
        except:
            LOG.fatal('Exception while loading %s', name)
            raise
    return module


def reload_changed_config_modules(modules, options, sender, tags):
    """Reloads any changed modules from the 'etc' directory.

    Args:
      cdir: The path to the 'collectors' directory.
      modules: A dict of path -> (module, timestamp).
    Returns: whether or not anything has changed.
    """

    etcdir = os.path.join(options.cdir, 'etc')
    current_modules = set(list_config_modules(etcdir))
    current_paths = set(os.path.join(etcdir, name)
                        for name in current_modules)
    changed = False

    # Reload any module that has changed.
    for path, (module, timestamp) in modules.iteritems():
        if path not in current_paths:  # Module was removed.
            continue
        mtime = os.path.getmtime(path)
        if mtime > timestamp:
            LOG.info('Reloading %s, file has changed', path)
            module = load_config_module(module, options, tags)
            modules[path] = (module, mtime)
            changed = True

    # Remove any module that has been removed.
    for path in set(modules).difference(current_paths):
        LOG.info('%s has been removed, tcollector should be restarted', path)
        del modules[path]
        changed = True

    # Check for any modules that may have been added.
    for name in current_modules:
        path = os.path.join(etcdir, name)
        if path not in modules:
            module = load_config_module(name, options, tags)
            modules[path] = (module, os.path.getmtime(path))
            changed = True

    return changed


def write_pid(pidfile):
    """Write our pid to a pidfile."""
    f = open(pidfile, "w")
    try:
        f.write(str(os.getpid()))
    finally:
        f.close()


def all_collectors():
    """Generator to return all collectors."""

    return COLLECTORS.itervalues()


# collectors that are not marked dead
def all_valid_collectors():
    """Generator to return all defined collectors that haven't been marked
       dead in the past hour, allowing temporarily broken collectors a
       chance at redemption."""

    now = int(time.time())
    for col in all_collectors():
        if not col.dead or (now - col.lastspawn > 3600):
            yield col


# collectors that have a process attached (currenty alive)
def all_living_collectors():
    """Generator to return all defined collectors that have
       an active process."""

    for col in all_collectors():
        if col.proc is not None:
            yield col


def shutdown_signal(signum, frame):
    """Called when we get a signal and need to terminate."""
    LOG.warning("shutting down, got signal %d", signum)
    shutdown()


def kill(proc, signum=signal.SIGTERM):
  os.killpg(proc.pid, signum)


def shutdown():
    """Called by atexit and when we receive a signal, this ensures we properly
       terminate any outstanding children."""

    global ALIVE
    # prevent repeated calls
    if not ALIVE:
        return
    # notify threads of program termination
    ALIVE = False

    LOG.info('shutting down children')

    # tell everyone to die
    for col in all_living_collectors():
        col.shutdown()

    LOG.info('exiting')
    sys.exit(1)


def reap_children():
    """When a child process dies, we have to determine why it died and whether
       or not we need to restart it.  This method manages that logic."""

    for col in all_living_collectors():
        now = int(time.time())
        # FIXME: this is not robust.  the asyncproc module joins on the
        # reader threads when you wait if that process has died.  this can cause
        # slow dying processes to hold up the main loop.  good for now though.
        status = col.proc.poll()
        if status is None:
            continue
        col.proc = None

        # behavior based on status.  a code 0 is normal termination, code 13
        # is used to indicate that we don't want to restart this collector.
        # any other status code is an error and is logged.
        if status == 13:
            LOG.info('removing %s from the list of collectors (by request)',
                      col.name)
            col.dead = True
        elif status != 0:
            LOG.warning('collector %s terminated after %d seconds with '
                        'status code %d, marking dead',
                        col.name, now - col.lastspawn, status)
            col.dead = True
        else:
            register_collector(Collector(col.name, col.interval, col.filename,
                                         col.mtime, col.lastspawn))

def check_children():
    """When a child process hasn't received a datapoint in a while,
       assume it's died in some fashion and restart it."""

    for col in all_living_collectors():
        now = int(time.time())

        if col.last_datapoint < (now - ALLOWED_INACTIVITY_TIME):
            # It's too old, kill it
            LOG.warning('Terminating collector %s after %d seconds of inactivity',
                        col.name, now - col.last_datapoint)
            col.shutdown()
            register_collector(Collector(col.name, col.interval, col.filename,
                                         col.mtime, col.lastspawn))


def set_nonblocking(fd):
    """Sets the given file descriptor to non-blocking mode."""
    fl = fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, fl)


def spawn_collector(col):
    """Takes a Collector object and creates a process for it."""

    LOG.info('%s (interval=%d) needs to be spawned', col.name, col.interval)

    # FIXME: do custom integration of Python scripts into memory/threads
    # if re.search('\.py$', col.name) is not None:
    #     ... load the py module directly instead of using a subprocess ...
    try:
        col.proc = subprocess.Popen(col.filename, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    close_fds=True,
                                    preexec_fn=os.setsid)
    except OSError, e:
        LOG.error('Failed to spawn collector %s: %s' % (col.filename, e))
        return
    # The following line needs to move below this line because it is used in
    # other logic and it makes no sense to update the last spawn time if the
    # collector didn't actually start.
    col.lastspawn = int(time.time())
    set_nonblocking(col.proc.stdout.fileno())
    set_nonblocking(col.proc.stderr.fileno())
    if col.proc.pid > 0:
        col.dead = False
        LOG.info('spawned %s (pid=%d)', col.name, col.proc.pid)
        return
    # FIXME: handle errors better
    LOG.error('failed to spawn collector: %s', col.filename)


def spawn_children():
    """Iterates over our defined collectors and performs the logic to
       determine if we need to spawn, kill, or otherwise take some
       action on them."""

    if not ALIVE:
        return

    for col in all_valid_collectors():
        now = int(time.time())
        if col.interval == 0:
            if col.proc is None:
                spawn_collector(col)
        elif col.interval <= now - col.lastspawn:
            if col.proc is None:
                spawn_collector(col)
                continue

            # I'm not very satisfied with this path.  It seems fragile and
            # overly complex, maybe we should just reply on the asyncproc
            # terminate method, but that would make the main tcollector
            # block until it dies... :|
            if col.nextkill > now:
                continue
            if col.killstate == 0:
                LOG.warning('warning: %s (interval=%d, pid=%d) overstayed '
                            'its welcome, SIGTERM sent',
                            col.name, col.interval, col.proc.pid)
                kill(col.proc)
                col.nextkill = now + 5
                col.killstate = 1
            elif col.killstate == 1:
                LOG.error('error: %s (interval=%d, pid=%d) still not dead, '
                           'SIGKILL sent',
                           col.name, col.interval, col.proc.pid)
                kill(col.proc, signal.SIGKILL)
                col.nextkill = now + 5
                col.killstate = 2
            else:
                LOG.error('error: %s (interval=%d, pid=%d) needs manual '
                           'intervention to kill it',
                           col.name, col.interval, col.proc.pid)
                col.nextkill = now + 300


def populate_collectors(coldir):
    """Maintains our internal list of valid collectors.  This walks the
       collector directory and looks for files.  In subsequent calls, this
       also looks for changes to the files -- new, removed, or updated files,
       and takes the right action to bring the state of our running processes
       in line with the filesystem."""

    global GENERATION
    GENERATION += 1

    # get numerics from scriptdir, we're only setup to handle numeric paths
    # which define intervals for our monitoring scripts
    for interval in os.listdir(coldir):
        if not interval.isdigit():
            continue
        interval = int(interval)

        for colname in os.listdir('%s/%d' % (coldir, interval)):
            if colname.startswith('.'):
                continue

            filename = '%s/%d/%s' % (coldir, interval, colname)
            if os.path.isfile(filename) and os.access(filename, os.X_OK):
                mtime = os.path.getmtime(filename)

                # if this collector is already 'known', then check if it's
                # been updated (new mtime) so we can kill off the old one
                # (but only if it's interval 0, else we'll just get
                # it next time it runs)
                if colname in COLLECTORS:
                    col = COLLECTORS[colname]

                    # if we get a dupe, then ignore the one we're trying to
                    # add now.  there is probably a more robust way of doing
                    # this...
                    if col.interval != interval:
                        LOG.error('two collectors with the same name %s and '
                                   'different intervals %d and %d',
                                   colname, interval, col.interval)
                        continue

                    # we have to increase the generation or we will kill
                    # this script again
                    col.generation = GENERATION
                    if col.mtime < mtime:
                        LOG.info('%s has been updated on disk', col.name)
                        col.mtime = mtime
                        if not col.interval:
                            col.shutdown()
                            LOG.info('Respawning %s', col.name)
                            register_collector(Collector(colname, interval,
                                                         filename, mtime))
                else:
                    register_collector(Collector(colname, interval, filename,
                                                 mtime))

    # now iterate over everybody and look for old generations
    to_delete = []
    for col in all_collectors():
        if col.generation < GENERATION:
            LOG.info('collector %s removed from the filesystem, forgetting',
                      col.name)
            col.shutdown()
            to_delete.append(col.name)
    for name in to_delete:
        del COLLECTORS[name]


if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

import sys
import unittest

import tcollector

class SenderThreadTests(unittest.TestCase):

    def setUp(self):
        # Stub out the randomness
        self.random_shuffle = tcollector.random.shuffle
        tcollector.random.shuffle = lambda x: x

    def tearDown(self):
        tcollector.random.shuffle = self.random_shuffle

    def mkSenderThread(self, tsds):
        return tcollector.SenderThread(None, True, tsds, False, {})

    def test_blacklistOneConnection(self):
        tsd = ("localhost", 4242)
        sender = self.mkSenderThread([tsd])
        sender.pick_connection()
        self.assertEqual(tsd, (sender.host, sender.port))
        sender.blacklist_connection()
        sender.pick_connection()
        self.assertEqual(tsd, (sender.host, sender.port))

    def test_blacklistTwoConnections(self):
        tsd1 = ("localhost", 4242)
        tsd2 = ("localhost", 4243)
        sender = self.mkSenderThread([tsd1, tsd2])
        sender.pick_connection()
        self.assertEqual(tsd1, (sender.host, sender.port))
        sender.blacklist_connection()
        sender.pick_connection()
        self.assertEqual(tsd2, (sender.host, sender.port))
        sender.blacklist_connection()
        sender.pick_connection()
        self.assertEqual(tsd1, (sender.host, sender.port))

    def test_doublePickOneConnection(self):
        tsd = ("localhost", 4242)
        sender = self.mkSenderThread([tsd])
        sender.pick_connection()
        self.assertEqual(tsd, (sender.host, sender.port))
        sender.pick_connection()
        self.assertEqual(tsd, (sender.host, sender.port))

    def test_doublePickTwoConnections(self):
        tsd1 = ("localhost", 4242)
        tsd2 = ("localhost", 4243)
        sender = self.mkSenderThread([tsd1, tsd2])
        sender.pick_connection()
        self.assertEqual(tsd1, (sender.host, sender.port))
        sender.pick_connection()
        self.assertEqual(tsd2, (sender.host, sender.port))
        sender.pick_connection()
        self.assertEqual(tsd1, (sender.host, sender.port))

if __name__ == '__main__':
    tcollector.setup_logging()
    sys.exit(unittest.main())

########NEW FILE########
