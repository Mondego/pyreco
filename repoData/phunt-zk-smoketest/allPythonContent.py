__FILENAME__ = zk-latencies
#!/usr/bin/env python

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime, time, os
from optparse import OptionParser

import zkclient
from zkclient import ZKClient, CountingWatcher, zookeeper

usage = "usage: %prog [options]"
parser = OptionParser(usage=usage)
parser.add_option("", "--servers", dest="servers",
                  default="localhost:2181", help="comma separated list of host:port (default %default), test each in turn")
parser.add_option("", "--cluster", dest="cluster",
                  default=None, help="comma separated list of host:port, test as a cluster, alternative to --servers")
parser.add_option("", "--config",
                  dest="configfile", default=None,
                  help="zookeeper configuration file to lookup cluster from")
parser.add_option("", "--timeout", dest="timeout", type="int",
                  default=5000, help="session timeout in milliseconds (default %default)")
parser.add_option("", "--root_znode", dest="root_znode",
                  default="/zk-latencies", help="root for the test, will be created as part of test (default /zk-latencies)")
parser.add_option("", "--znode_size", dest="znode_size", type="int",
                  default=25, help="data size when creating/setting znodes (default %default)")
parser.add_option("", "--znode_count", dest="znode_count", default=10000, type="int",
                  help="the number of znodes to operate on in each performance section (default %default)")
parser.add_option("", "--watch_multiple", dest="watch_multiple", default=1, type="int",
                  help="number of watches to put on each znode (default %default)")

parser.add_option("", "--force",
                  action="store_true", dest="force", default=False,
                  help="force the test to run, even if root_znode exists - WARNING! don't run this on a real znode or you'll lose it!!!")

parser.add_option("", "--synchronous",
                  action="store_true", dest="synchronous", default=False,
                  help="by default asynchronous ZK api is used, this forces synchronous calls")

parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="verbose output, include more detail")
parser.add_option("-q", "--quiet",
                  action="store_true", dest="quiet", default=False,
                  help="quiet output, basically just success/failure")

(options, args) = parser.parse_args()

zkclient.options = options

zookeeper.set_log_stream(open("cli_log_%d.txt" % (os.getpid()),"w"))

class SmokeError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def print_elap(start, msg, count):
    elapms = (time.time() - start) * 1000
    if int(elapms) != 0:
        print("%s in %6d ms (%f ms/op %f/sec)"
              % (msg, int(elapms), elapms/count, count/(elapms/1000.0)))
    else:
        print("%s in %6d ms (included in prior)" % (msg, int(elapms)))

def timer(ops, msg, count=options.znode_count):
    start = time.time()
    for op in ops:
        pass
    print_elap(start, msg, count)

def timer2(func, msg, count=options.znode_count):
    start = time.time()
    func()
    print_elap(start, msg, count)

def child_path(i):
    return "%s/session_%d" % (options.root_znode, i)

def synchronous_latency_test(s, data):
    # create znode_count znodes (perm)
    timer((s.create(child_path(j), data)
           for j in xrange(options.znode_count)),
          "created %7d permanent znodes " % (options.znode_count))

    # set znode_count znodes
    timer((s.set(child_path(j), data)
           for j in xrange(options.znode_count)),
          "set     %7d           znodes " % (options.znode_count))

    # get znode_count znodes
    timer((s.get(child_path(j))
           for j in xrange(options.znode_count)),
          "get     %7d           znodes " % (options.znode_count))

    # delete znode_count znodes
    timer((s.delete(child_path(j))
           for j in xrange(options.znode_count)),
          "deleted %7d permanent znodes " % (options.znode_count))

    # create znode_count znodes (ephemeral)
    timer((s.create(child_path(j), data, zookeeper.EPHEMERAL)
           for j in xrange(options.znode_count)),
          "created %7d ephemeral znodes " % (options.znode_count))

    # watch znode_count znodes
    watches = [CountingWatcher() for x in xrange(options.watch_multiple)]
    def watch(j):
        for watch in watches:
            s.exists(child_path(j), watch)
    timer((watch(j) for j in xrange(options.znode_count)),
          "watched %7d           znodes " %
          (options.watch_multiple * options.znode_count),
          options.watch_multiple * options.znode_count)

    # # delete znode_count znodes
    timer((s.delete(child_path(j))
           for j in xrange(options.znode_count)),
          "deleted %7d ephemeral znodes " % (options.znode_count))

    start = time.time()
    for watch in watches:
        if watch.waitForExpected(options.znode_count, 60000) != options.znode_count:
            raise SmokeError("wrong number of watches: %d" %
                             (watch.count))
    print_elap(start,
               "notif   %7d           watches" % (options.watch_multiple * options.znode_count),
               (options.watch_multiple * options.znode_count))

def asynchronous_latency_test(s, data):
    # create znode_count znodes (perm)
    def func():
        callbacks = []
        for j in xrange(options.znode_count):
            cb = zkclient.CreateCallback()
            cb.cv.acquire()
            s.acreate(child_path(j), cb, data)
            callbacks.append(cb)

        for j, cb in enumerate(callbacks):
            cb.waitForSuccess()
            if cb.path != child_path(j):
                raise SmokeError("invalid path %s for operation %d on handle %d" %
                                 (cb.path, j, cb.handle))

    timer2(func, "created %7d permanent znodes " % (options.znode_count))

    # set znode_count znodes
    def func():
        callbacks = []
        for j in xrange(options.znode_count):
            cb = zkclient.SetCallback()
            cb.cv.acquire()
            s.aset(child_path(j), cb, data)
            callbacks.append(cb)

        for cb in callbacks:
            cb.waitForSuccess()

    timer2(func, "set     %7d           znodes " % (options.znode_count))

    # get znode_count znodes
    def func():
        callbacks = []
        for j in xrange(options.znode_count):
            cb = zkclient.GetCallback()
            cb.cv.acquire()
            s.aget(child_path(j), cb)
            callbacks.append(cb)

        for cb in callbacks:
            cb.waitForSuccess()
            if cb.value != data:
                raise SmokeError("invalid data %s for operation %d on handle %d" %
                                 (cb.value, j, cb.handle))

    timer2(func, "get     %7d           znodes " % (options.znode_count))


    # delete znode_count znodes (perm)
    def func():
        callbacks = []
        for j in xrange(options.znode_count):
            cb = zkclient.DeleteCallback()
            cb.cv.acquire()
            s.adelete(child_path(j), cb)
            callbacks.append(cb)

        for cb in callbacks:
            cb.waitForSuccess()

    timer2(func, "deleted %7d permanent znodes " % (options.znode_count))

    # create znode_count znodes (ephemeral)
    def func():
        callbacks = []
        for j in xrange(options.znode_count):
            cb = zkclient.CreateCallback()
            cb.cv.acquire()
            s.acreate(child_path(j), cb, data, zookeeper.EPHEMERAL)
            callbacks.append(cb)

        for j, cb in enumerate(callbacks):
            cb.waitForSuccess()
            if cb.path != child_path(j):
                raise SmokeError("invalid path %s for operation %d on handle %d" %
                                 (cb.path, j, cb.handle))

    timer2(func, "created %7d ephemeral znodes " % (options.znode_count))

    watches = [CountingWatcher() for x in xrange(options.watch_multiple)]

    # watched znode_count znodes
    def func():
        callbacks = []
        for watch in watches:
            for j in xrange(options.znode_count):
                cb = zkclient.ExistsCallback()
                cb.cv.acquire()
                s.aexists(child_path(j), cb, watch)
                callbacks.append(cb)

        for cb in callbacks:
            cb.waitForSuccess()

    timer2(func, "watched %7d           znodes " %
           (options.watch_multiple * options.znode_count),
           options.watch_multiple * options.znode_count)

    # delete znode_count znodes (ephemeral)
    def func():
        callbacks = []
        for j in xrange(options.znode_count):
            cb = zkclient.DeleteCallback()
            cb.cv.acquire()
            s.adelete(child_path(j), cb)
            callbacks.append(cb)

        for cb in callbacks:
            cb.waitForSuccess()

    timer2(func, "deleted %7d ephemeral znodes " % (options.znode_count))

    start = time.time()
    for watch in watches:
        if watch.waitForExpected(options.znode_count, 60000) != options.znode_count:
            raise SmokeError("wrong number of watches: %d" %
                             (watch.count))
    print_elap(start,
               "notif   %7d           watches" % (options.watch_multiple * options.znode_count),
               (options.watch_multiple * options.znode_count))

def read_zk_config(filename):
    with open(filename) as f:
        config = dict(tuple(line.rstrip().split('=', 1)) for line in f if line.rstrip())
        return config

def get_zk_servers(filename):
    if options.cluster:
        return [options.cluster]
    elif filename:
        config = read_zk_config(options.configfile)
        client_port = config['clientPort']
        return [",".join("%s:%s" % (v.split(':', 1)[0], client_port)
                        for k, v in config.items() if k.startswith('server.'))]
    else:
        return options.servers.split(",")

if __name__ == '__main__':
    data = options.znode_size * "x"
    servers = get_zk_servers(options.configfile)

    # create all the sessions first to ensure that all servers are
    # at least available & quorum has been formed. otw this will 
    # fail right away (before we start creating nodes)
    sessions = []
    # create one session to each of the servers in the ensemble
    for server in servers:
        sessions.append(ZKClient(server, options.timeout))

    # ensure root_znode doesn't exist
    if sessions[0].exists(options.root_znode):
        # unless forced by user
        if not options.force:
            raise SmokeError("Node %s already exists!" % (options.root_znode))

        children = sessions[0].get_children(options.root_znode)
        for child in children:
            sessions[0].delete("%s/%s" % (options.root_znode, child))
    else:
        sessions[0].create(options.root_znode,
                           "smoketest root, delete after test done, created %s" %
                           (datetime.datetime.now().ctime()))

    for i, s in enumerate(sessions):
        if options.synchronous:
            type = "syncronous" 
        else:
            type = "asynchronous"
        print("Testing latencies on server %s using %s calls" %
              (servers[i], type))

        if options.synchronous:
            synchronous_latency_test(s, data)
        else:
            asynchronous_latency_test(s, data)

    sessions[0].delete(options.root_znode)

    # close sessions
    for s in sessions:
        s.close()

    print("Latency test complete")

########NEW FILE########
__FILENAME__ = zk-smoketest
#!/usr/bin/env python

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime, os
from optparse import OptionParser

import zkclient
from zkclient import ZKClient, SequentialCountingWatcher, zookeeper

usage = "usage: %prog [options]"
parser = OptionParser(usage=usage)
parser.add_option("", "--servers", dest="servers",
                  default="localhost:2181", help="comma separated list of host:port (default %default)")
parser.add_option("", "--config",
                  dest="configfile", default=None,
                  help="zookeeper configuration file to lookup servers from")
parser.add_option("", "--timeout", dest="timeout", type="int",
                  default=5000, help="session timeout in milliseconds (default %default)")
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="verbose output, include more detail")
parser.add_option("-q", "--quiet",
                  action="store_true", dest="quiet", default=False,
                  help="quiet output, basically just success/failure")

(options, args) = parser.parse_args()

zkclient.options = options

zookeeper.set_log_stream(open("cli_log_%d.txt" % (os.getpid()),"w"))

class SmokeError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


def read_zk_config(filename):
    with open(filename) as f:
        config = dict(tuple(line.rstrip().split('=', 1)) for line in f if line.rstrip())
        return config

def get_zk_servers(filename):
    if filename:
        config = read_zk_config(options.configfile)
        client_port = config['clientPort']
        return ["%s:%s" % (v.split(':', 1)[0], client_port)
                        for k, v in config.items() if k.startswith('server.')]
    else:
        return options.servers.split(",")

if __name__ == '__main__':
    servers = get_zk_servers(options.configfile)

    # create all the sessions first to ensure that all servers are
    # at least available & quorum has been formed. otw this will 
    # fail right away (before we start creating nodes)
    sessions = []
    # create one session to each of the servers in the ensemble
    for i, server in enumerate(servers):
        sessions.append(ZKClient(server, options.timeout))

    # create on first server
    zk = ZKClient(servers[0], options.timeout)

    rootpath = "/zk-smoketest"

    if zk.exists(rootpath):
        if not options.quiet:
            print("Node %s already exists, attempting reuse" % (rootpath))
    else:
        zk.create(rootpath,
                  "smoketest root, delete after test done, created %s" %
                  (datetime.datetime.now().ctime()))

    # make sure previous cleaned up properly
    children = zk.get_children(rootpath)
    if len(children) > 0:
        raise SmokeError("there should not be children in %s"
                         "root data is: %s, count is %d"
                         % (rootpath, zk.get(rootpath), len(children)))

    zk.close()

    def child_path(i):
        return "%s/session_%d" % (rootpath, i)

    # create znodes, one znode per session (client), one session per server
    for i, server in enumerate(servers):
        # ensure this server is up to date with leader
        sessions[i].async()

        ## create child znode
        sessions[i].create(child_path(i), "", zookeeper.EPHEMERAL)

    watchers = []
    for i, server in enumerate(servers):
        # ensure this server is up to date with leader
        sessions[i].async()

        children = sessions[i].get_children(rootpath)
        if len(children) != len(sessions):
            raise SmokeError("server %s wrong number of children: %d" %
                             (server, len(children)))

        watchers.append(SequentialCountingWatcher(child_path))
        for child in children:
            sessions[i].get(rootpath + "/" + child, watchers[i])

    # trigger watches
    for i, server in enumerate(servers):
        sessions[i].delete(child_path(i))

    # check all watches fired
    for i, watcher in enumerate(watchers):
        # ensure this server is up to date with leader
        sessions[i].async()
        if watcher.waitForExpected(len(sessions), options.timeout) != len(sessions):
            raise SmokeError("server %s wrong number of watches: %d" %
                             (server, watcher.count))

    # close sessions
    for i, server in enumerate(servers):
        # ephemerals will be deleted automatically
        sessions[i].close()

    # cleanup root node
    zk = ZKClient(servers[-1], options.timeout)
    # ensure this server is up to date with leader (ephems)
    zk.async()
    zk.delete(rootpath)

    zk.close()

    print("Smoke test successful")

########NEW FILE########
__FILENAME__ = zkclient
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import zookeeper, time, threading

DEFAULT_TIMEOUT = 30000

ZOO_OPEN_ACL_UNSAFE = {"perms":0x1f, "scheme":"world", "id" :"anyone"}

class ZKClientError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class ZKClient(object):
    def __init__(self, servers, timeout=DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.connected = False
        self.conn_cv = threading.Condition( )
        self.handle = -1

        self.conn_cv.acquire()
        if not options.quiet: print("Connecting to %s" % (servers))
        start = time.time()
        self.handle = zookeeper.init(servers, self.connection_watcher, timeout)
        self.conn_cv.wait(timeout/1000)
        self.conn_cv.release()

        if not self.connected:
            raise ZKClientError("Unable to connect to %s" % (servers))

        if not options.quiet:
            print("Connected in %d ms, handle is %d"
                  % (int((time.time() - start) * 1000), self.handle))

    def connection_watcher(self, h, type, state, path):
        self.handle = h
        self.conn_cv.acquire()
        self.connected = True
        self.conn_cv.notifyAll()
        self.conn_cv.release()

    def close(self):
        return zookeeper.close(self.handle)
    
    def create(self, path, data="", flags=0, acl=[ZOO_OPEN_ACL_UNSAFE]):
        start = time.time()
        result = zookeeper.create(self.handle, path, data, acl, flags)
        if options.verbose:
            print("Node %s created in %d ms"
                  % (path, int((time.time() - start) * 1000)))
        return result

    def delete(self, path, version=-1):
        start = time.time()
        result = zookeeper.delete(self.handle, path, version)
        if options.verbose:
            print("Node %s deleted in %d ms"
                  % (path, int((time.time() - start) * 1000)))
        return result

    def get(self, path, watcher=None):
        return zookeeper.get(self.handle, path, watcher)

    def exists(self, path, watcher=None):
        return zookeeper.exists(self.handle, path, watcher)

    def set(self, path, data="", version=-1):
        return zookeeper.set(self.handle, path, data, version)

    def set2(self, path, data="", version=-1):
        return zookeeper.set2(self.handle, path, data, version)


    def get_children(self, path, watcher=None):
        return zookeeper.get_children(self.handle, path, watcher)

    def async(self, path = "/"):
        return zookeeper.async(self.handle, path)

    def acreate(self, path, callback, data="", flags=0, acl=[ZOO_OPEN_ACL_UNSAFE]):
        result = zookeeper.acreate(self.handle, path, data, acl, flags, callback)
        return result

    def adelete(self, path, callback, version=-1):
        return zookeeper.adelete(self.handle, path, version, callback)

    def aget(self, path, callback, watcher=None):
        return zookeeper.aget(self.handle, path, watcher, callback)

    def aexists(self, path, callback, watcher=None):
        return zookeeper.aexists(self.handle, path, watcher, callback)

    def aset(self, path, callback, data="", version=-1):
        return zookeeper.aset(self.handle, path, data, version, callback)

watch_count = 0

"""Callable watcher that counts the number of notifications"""
class CountingWatcher(object):
    def __init__(self):
        self.count = 0
        global watch_count
        self.id = watch_count
        watch_count += 1

    def waitForExpected(self, count, maxwait):
        """Wait up to maxwait for the specified count,
        return the count whether or not maxwait reached.

        Arguments:
        - `count`: expected count
        - `maxwait`: max milliseconds to wait
        """
        waited = 0
        while (waited < maxwait):
            if self.count >= count:
                return self.count
            time.sleep(1.0);
            waited += 1000
        return self.count

    def __call__(self, handle, typ, state, path):
        self.count += 1
        if options.verbose:
            print("handle %d got watch for %s in watcher %d, count %d" %
                  (handle, path, self.id, self.count))

"""Callable watcher that counts the number of notifications
and verifies that the paths are sequential"""
class SequentialCountingWatcher(CountingWatcher):
    def __init__(self, child_path):
        CountingWatcher.__init__(self)
        self.child_path = child_path

    def __call__(self, handle, typ, state, path):
        if not self.child_path(self.count) == path:
            raise ZKClientError("handle %d invalid path order %s" % (handle, path))
        CountingWatcher.__call__(self, handle, typ, state, path)

class Callback(object):
    def __init__(self):
        self.cv = threading.Condition()
        self.callback_flag = False
        self.rc = -1

    def callback(self, handle, rc, handler):
        self.cv.acquire()
        self.callback_flag = True
        self.handle = handle
        self.rc = rc
        handler()
        self.cv.notify()
        self.cv.release()

    def waitForSuccess(self):
        while not self.callback_flag:
            self.cv.wait()
        self.cv.release()

        if not self.callback_flag == True:
            raise ZKClientError("asynchronous operation timed out on handle %d" %
                             (self.handle))
        if not self.rc == zookeeper.OK:
            raise ZKClientError(
                "asynchronous operation failed on handle %d with rc %d" %
                (self.handle, self.rc))


class GetCallback(Callback):
    def __init__(self):
        Callback.__init__(self)

    def __call__(self, handle, rc, value, stat):
        def handler():
            self.value = value
            self.stat = stat
        self.callback(handle, rc, handler)

class SetCallback(Callback):
    def __init__(self):
        Callback.__init__(self)

    def __call__(self, handle, rc, stat):
        def handler():
            self.stat = stat
        self.callback(handle, rc, handler)

class ExistsCallback(SetCallback):
    pass

class CreateCallback(Callback):
    def __init__(self):
        Callback.__init__(self)

    def __call__(self, handle, rc, path):
        def handler():
            self.path = path
        self.callback(handle, rc, handler)

class DeleteCallback(Callback):
    def __init__(self):
        Callback.__init__(self)

    def __call__(self, handle, rc):
        def handler():
            pass
        self.callback(handle, rc, handler)

########NEW FILE########
