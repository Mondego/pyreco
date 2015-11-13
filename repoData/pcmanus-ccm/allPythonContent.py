__FILENAME__ = bulkloader
# ccm node
from __future__ import with_statement

import os
import tempfile

from ccmlib import common
from ccmlib.node import Node

# We reuse Node because the bulkloader basically needs all the same files,
# even though this is not a real node. But truth is, this is an afterthough,
# so be careful when using this object. This will need some cleanup someday
class BulkLoader(Node):
    def __init__(self, cluster):
        # A lot of things are wrong in that method. It assumes that the ip
        # 127.0.0.<nbnode> is free and use standard ports without asking.
        # It should problably be fixed, but will be good enough for now.
        addr = '127.0.0.%d' % (len(cluster.nodes) + 1)
        self.path = tempfile.mkdtemp(prefix='bulkloader-')
        Node.__init__(self, 'bulkloader', cluster, False, (addr, 9160), (addr, 7000), str(9042), 2000, None)

    def get_path(self):
        return os.path.join(self.path, self.name)

    def load(self, options):
        for itf in self.network_interfaces.values():
            if itf:
                common.check_socket_available(itf)

        cdir = self.get_cassandra_dir()
        loader_bin = common.join_bin(cdir, 'bin', 'sstableloader')
        env = common.make_cassandra_env(cdir, self.get_path())
        if not "-d" in options:
            l = [ node.network_interfaces['storage'][0] for node in self.cluster.nodes.values() if node.is_live() ]
            options = [ "-d",  ",".join(l) ] + options
        #print "Executing with", options
        os.execve(loader_bin, [ common.platform_binary('sstableloader') ] + options, env)

########NEW FILE########
__FILENAME__ = cli_session
import sys
from threading  import Thread
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

ON_POSIX = 'posix' in sys.builtin_module_names

class CliSession():
    def __init__(self, process):
        self.process = process
        self.stdout = Queue()
        self.stderr = Queue()
        self.thread_out = Thread(target=self.__enqueue_output, args=(process.stdout, self.stdout))
        self.thread_err = Thread(target=self.__enqueue_output, args=(process.stderr, self.stderr))
        for t in [ self.thread_out, self.thread_err ]:
            t.daemon = True
            t.start()
        self.__outputs = []
        self.__errors = []

    def do(self, query):
        # Reads whatever remains in stdout/stderr
        self.__read_all()
        self.process.stdin.write(query + ';\n')
        return self

    def last_output(self):
        self.__read_output()
        return self.__outputs[-1]

    def last_error(self):
        self.__read_errors()
        return self.__errors[-1]

    def outputs(self):
        self.__read_output()
        return self.__outputs

    def errors(self):
        self.__read_errors()
        return self.__errors

    def has_errors(self):
        self.__read_errors()
        for err in self.__errors:
            if 'WARNING' not in err and err != '': 
                return True
        return False

    def close(self):
        self.process.stdin.write('quit;\n')
        self.process.wait()

    def __read_all(self):
        self.__read_output()
        self.__read_errors()

    def __read_output(self):
        r = self.__read(self.stdout)
        if r:
            self.__outputs.append(r)

    def __read_errors(self):
        r = self.__read(self.stderr)
        if r:
            self.__errors.append(r)

    def __read(self, queue):
        output = None
        while True:
            try:
                line = queue.get(timeout=.2)
            except Empty:
                return output
            else:
                output = line if output is None else output + line

    def __enqueue_output(self, out, queue):
        for line in iter(out.readline, ''):
            queue.put(line)
        out.close()

########NEW FILE########
__FILENAME__ = cluster
# ccm clusters

from six import print_, iteritems
from six.moves import xrange

import yaml
import os
import re
import subprocess
import shutil
import time

from ccmlib import common, repository
from ccmlib.node import Node, NodeError
from ccmlib.bulkloader import BulkLoader

class Cluster():
    def __init__(self, path, name, partitioner=None, cassandra_dir=None, create_directory=True, cassandra_version=None, verbose=False):
        self.name = name
        self.nodes = {}
        self.seeds = []
        self.partitioner = partitioner
        self._config_options = {}
        self.__log_level = "INFO"
        self.__path = path
        self.__version = None
        if create_directory:
            # we create the dir before potentially downloading to throw an error sooner if need be
            os.mkdir(self.get_path())

        try:
            if cassandra_version is None:
                # at this point, cassandra_dir should always not be None, but
                # we keep this for backward compatibility (in loading old cluster)
                if cassandra_dir is not None:
                    if common.is_win():
                        self.__cassandra_dir = cassandra_dir
                    else:
                        self.__cassandra_dir = os.path.abspath(cassandra_dir)
                    self.__version = self.__get_version_from_build()
            else:
                dir, v = repository.setup(cassandra_version, verbose)
                self.__cassandra_dir = dir
                self.__version = v if v is not None else self.__get_version_from_build()

            if create_directory:
                common.validate_cassandra_dir(self.__cassandra_dir)
                self.__update_config()
        except:
            if create_directory:
                shutil.rmtree(self.get_path())
            raise

    def set_partitioner(self, partitioner):
        self.partitioner = partitioner
        self.__update_config()
        return self

    def set_cassandra_dir(self, cassandra_dir=None, cassandra_version=None, verbose=False):
        if cassandra_version is None:
            self.__cassandra_dir = cassandra_dir
            common.validate_cassandra_dir(cassandra_dir)
            self.__version = self.__get_version_from_build()
        else:
            dir, v = repository.setup(cassandra_version, verbose)
            self.__cassandra_dir = dir
            self.__version = v if v is not None else self.__get_version_from_build()
        self.__update_config()
        for node in list(self.nodes.values()):
            node.import_config_files()
        
        # if any nodes have a data center, let's update the topology
        if any( [node.data_center for node in self.nodes.values()] ):
            self.__update_topology_files()
        
        return self

    def get_cassandra_dir(self):
        common.validate_cassandra_dir(self.__cassandra_dir)
        return self.__cassandra_dir

    def nodelist(self):
        return [ self.nodes[name] for name in sorted(self.nodes.keys()) ]

    def version(self):
        return self.__version

    @staticmethod
    def load(path, name):
        cluster_path = os.path.join(path, name)
        filename = os.path.join(cluster_path, 'cluster.conf')
        with open(filename, 'r') as f:
            data = yaml.load(f)
        try:
            cassandra_dir = None
            if 'cassandra_dir' in data:
                cassandra_dir = data['cassandra_dir']
                repository.validate(cassandra_dir)

            cluster = Cluster(path, data['name'], cassandra_dir=cassandra_dir, create_directory=False)
            node_list = data['nodes']
            seed_list = data['seeds']
            if 'partitioner' in data:
                cluster.partitioner = data['partitioner']
            if 'config_options' in data:
                cluster._config_options = data['config_options']
            if 'log_level' in data:
                cluster.__log_level = data['log_level']
        except KeyError as k:
            raise common.LoadError("Error Loading " + filename + ", missing property:" + k)

        for node_name in node_list:
            cluster.nodes[node_name] = Node.load(cluster_path, node_name, cluster)
        for seed_name in seed_list:
            cluster.seeds.append(cluster.nodes[seed_name])

        return cluster

    def add(self, node, is_seed, data_center=None):
        if node.name in self.nodes:
            raise common.ArgumentError('Cannot create existing node %s' % node.name)
        self.nodes[node.name] = node
        if is_seed:
            self.seeds.append(node)
        self.__update_config()
        node.data_center = data_center
        node.set_log_level(self.__log_level)
        node._save()
        if data_center is not None:
            self.__update_topology_files()
        return self

    def populate(self, nodes, debug=False, tokens=None, use_vnodes=False, ipprefix='127.0.0.'):
        node_count = nodes
        dcs = []
        if isinstance(nodes, list):
            self.set_configuration_options(values={'endpoint_snitch' : 'org.apache.cassandra.locator.PropertyFileSnitch'})
            node_count = 0
            i = 0
            for c in nodes:
                i = i + 1
                node_count = node_count + c
                for x in xrange(0, c):
                    dcs.append('dc%d' % i)

        if node_count < 1:
            raise common.ArgumentError('invalid node count %s' % nodes)

        for i in xrange(1, node_count + 1):
            if 'node%s' % i in list(self.nodes.values()):
                raise common.ArgumentError('Cannot create existing node node%s' % i)

        if tokens is None and not use_vnodes:
            tokens = self.balanced_tokens(node_count)

        for i in xrange(1, node_count + 1):
            tk = None
            if tokens is not None and i-1 < len(tokens):
                tk = tokens[i-1]
            dc = dcs[i-1] if i-1 < len(dcs) else None

            binary = None
            if self.version() >= '1.2':
                binary = ('%s%s' % (ipprefix, i), 9042)
            node = Node('node%s' % i,
                        self,
                        False,
                        ('%s%s' % (ipprefix, i), 9160),
                        ('%s%s' % (ipprefix, i), 7000),
                        str(7000 + i * 100),
                        (str(0),  str(2000 + i * 100))[debug == True],
                        tk,
                        binary_interface=binary)
            self.add(node, True, dc)
            self.__update_config()
        return self

    def balanced_tokens(self, node_count):
        if self.version() >= '1.2' and not self.partitioner:
            ptokens = [(i*(2**64//node_count)) for i in xrange(0, node_count)]
            return [int(t - 2**63) for t in ptokens]
        return [ int(i*(2**127//node_count)) for i in range(0, node_count) ]

    def remove(self, node=None):
        if node is not None:
            if not node.name in self.nodes:
                return

            del self.nodes[node.name]
            if node in self.seeds:
                self.seeds.remove(node)
            self.__update_config()
            node.stop(gently=False)
            shutil.rmtree(node.get_path())
        else:
            self.stop(gently=False)
            shutil.rmtree(self.get_path())

    def clear(self):
        self.stop()
        for node in list(self.nodes.values()):
            node.clear()

    def get_path(self):
        return os.path.join(self.__path, self.name)

    def get_seeds(self):
        return [ s.network_interfaces['storage'][0] for s in self.seeds ]

    def show(self, verbose):
        if len(list(self.nodes.values())) == 0:
            print_("No node in this cluster yet")
            return
        for node in list(self.nodes.values()):
            if (verbose):
                node.show(show_cluster=False)
                print_("")
            else:
                node.show(only_status=True)

    def start(self, no_wait=False, verbose=False, wait_for_binary_proto=False, jvm_args=[], profile_options=None):
        started = []
        for node in list(self.nodes.values()):
            if not node.is_running():
                mark = 0
                if os.path.exists(node.logfilename()):
                    mark = node.mark_log()

                p = node.start(update_pid=False, jvm_args=jvm_args, profile_options=profile_options)
                started.append((node, p, mark))

        if no_wait and not verbose:
            time.sleep(2) # waiting 2 seconds to check for early errors and for the pid to be set
        else:
            for node, p, mark in started:
                try:
                    node.watch_log_for("Listening for thrift clients...", process=p, verbose=verbose, from_mark=mark)
                except RuntimeError:
                    return None

        self.__update_pids(started)

        for node, p, _ in started:
            if not node.is_running():
                raise NodeError("Error starting {0}.".format(node.name), p)

        if not no_wait and self.version() >= "0.8":
            # 0.7 gossip messages seems less predictible that from 0.8 onwards and
            # I don't care enough
            for node, _, mark in started:
                for other_node, _, _ in started:
                    if other_node is not node:
                        node.watch_log_for_alive(other_node, from_mark=mark)

        if wait_for_binary_proto:
            for node, _, mark in started:
                node.watch_log_for("Starting listening for CQL clients", process=p, verbose=verbose, from_mark=mark)
            time.sleep(0.2)

        return started

    def stop(self, wait=True, gently=True):
        not_running = []
        for node in list(self.nodes.values()):
            if not node.stop(wait, gently=gently):
                not_running.append(node)
        return not_running

    def set_log_level(self, new_level, class_name=None):
        known_level = [ 'TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR' ]
        if new_level not in known_level:
            raise common.ArgumentError("Unknown log level %s (use one of %s)" % (new_level, " ".join(known_level)))

        self.__log_level = new_level
        self.__update_config()

        for node in self.nodelist():
            node.set_log_level(new_level, class_name)

    def nodetool(self, nodetool_cmd):
        for node in list(self.nodes.values()):
            if node.is_running():
                node.nodetool(nodetool_cmd)
        return self

    def stress(self, stress_options):
        stress = common.get_stress_bin(self.get_cassandra_dir())
        livenodes = [ node.network_interfaces['storage'][0] for node in list(self.nodes.values()) if node.is_live() ]
        if len(livenodes) == 0:
            print_("No live node")
            return
        args = [ stress, '-d', ",".join(livenodes) ] + stress_options
        try:
            # need to set working directory for env on Windows
            if common.is_win():
                subprocess.call(args, cwd=common.parse_path(stress))
            else:
                subprocess.call(args)
        except KeyboardInterrupt:
            pass
        return self

    def run_cli(self, cmds=None, show_output=False, cli_options=[]):
        livenodes = [ node for node in list(self.nodes.values()) if node.is_live() ]
        if len(livenodes) == 0:
            raise common.ArgumentError("No live node")
        livenodes[0].run_cli(cmds, show_output, cli_options)

    def set_configuration_options(self, values=None, batch_commitlog=None):
        if values is not None:
            for k, v in iteritems(values):
                self._config_options[k] = v
        if batch_commitlog is not None:
            if batch_commitlog:
                self._config_options["commitlog_sync"] = "batch"
                self._config_options["commitlog_sync_batch_window_in_ms"] = 5
                self._config_options["commitlog_sync_period_in_ms"] = None
            else:
                self._config_options["commitlog_sync"] = "periodic"
                self._config_options["commitlog_sync_period_in_ms"] = 10000
                self._config_options["commitlog_sync_batch_window_in_ms"] = None

        self.__update_config()
        for node in list(self.nodes.values()):
            node.import_config_files()
        return self

    def flush(self):
        self.nodetool("flush")

    def compact(self):
        self.nodetool("compact")

    def drain(self):
        self.nodetool("drain")

    def repair(self):
        self.nodetool("repair")

    def cleanup(self):
        self.nodetool("cleanup")

    def decommission(self):
        for node in list(self.nodes.values()):
            if node.is_running():
                node.decommission()

    def removeToken(self, token):
        self.nodetool("removeToken " + str(token))

    def bulkload(self, options):
        loader = BulkLoader(self)
        loader.load(options)

    def scrub(self, options):
        for node in list(self.nodes.values()):
            node.scrub(options)

    def update_log4j(self, new_log4j_config):
        # iterate over all nodes
        for node in self.nodelist():
            node.update_log4j(new_log4j_config)

    def update_logback(self, new_logback_config):
        # iterate over all nodes
        for node in self.nodelist():
            node.update_logback(new_logback_config)

    def __get_version_from_build(self):
        cassandra_dir = self.get_cassandra_dir()
        build = os.path.join(cassandra_dir, 'build.xml')
        with open(build) as f:
            for line in f:
                match = re.search('name="base\.version" value="([0-9.]+)[^"]*"', line)
                if match:
                    return match.group(1)
        raise common.CCMError("Cannot find version")

    def __update_config(self):
        node_list = [ node.name for node in list(self.nodes.values()) ]
        seed_list = [ node.name for node in self.seeds ]
        filename = os.path.join(self.__path, self.name, 'cluster.conf')
        with open(filename, 'w') as f:
            yaml.safe_dump({
                'name' : self.name,
                'nodes' : node_list,
                'seeds' : seed_list,
                'partitioner' : self.partitioner,
                'cassandra_dir' : self.__cassandra_dir,
                'config_options' : self._config_options,
                'log_level' : self.__log_level
            }, f)

    def __update_pids(self, started):
        for node, p, _ in started:
            node._update_pid(p)

    def __update_topology_files(self):
        dcs = [('default', 'dc1')]
        for node in self.nodelist():
            if node.data_center is not None:
                dcs.append((node.address(), node.data_center))

        content = ""
        for k, v in dcs:
            content = "%s%s=%s:r1\n" % (content, k, v)

        for node in self.nodelist():
            topology_file = os.path.join(node.get_conf_dir(), 'cassandra-topology.properties')
            with open(topology_file, 'w') as f:
                f.write(content)

########NEW FILE########
__FILENAME__ = cluster_cmds
import os
import sys

from six import print_

from ccmlib import common, repository
from ccmlib.node import Node, NodeError
from ccmlib.cluster import Cluster
from ccmlib.cmds.command import Cmd

def cluster_cmds():
    return [
        "create",
        "add",
        "populate",
        "list",
        "switch",
        "status",
        "remove",
        "clear",
        "liveset",
        "start",
        "stop",
        "flush",
        "compact",
        "stress",
        "updateconf",
        "updatelog4j",
        "cli",
        "setdir",
        "bulkload",
        "setlog",
        "scrub",
    ]

def parse_populate_count(v):
    if v is None:
        return None
    tmp = v.split(':')
    if len(tmp) == 1:
        return int(tmp[0])
    else:
        return [ int(t) for t in tmp ]

class ClusterCreateCmd(Cmd):
    def description(self):
        return "Create a new cluster"

    def get_parser(self):
        usage = "usage: ccm create [options] cluster_name"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('--no-switch', action="store_true", dest="no_switch",
            help="Don't switch to the newly created cluster", default=False)
        parser.add_option('-p', '--partitioner', type="string", dest="partitioner",
            help="Set the cluster partitioner class")
        parser.add_option('-v', "--cassandra-version", type="string", dest="cassandra_version",
            help="Download and use provided cassandra version. If version is of the form 'git:<branch name>', then the specified branch will be downloaded from the git repo and compiled. (takes precedence over --cassandra-dir)", default=None)
        parser.add_option("--cassandra-dir", type="string", dest="cassandra_dir",
            help="Path to the cassandra directory to use [default %default]", default="./")
        parser.add_option('-n', '--nodes', type="string", dest="nodes",
            help="Populate the new cluster with that number of nodes (a single int or a colon-separate list of ints for multi-dc setups)")
        parser.add_option('-i', '--ipprefix', type="string", dest="ipprefix", default="127.0.0.",
            help="Ipprefix to use to create the ip of a node while populating")
        parser.add_option('-s', "--start", action="store_true", dest="start_nodes",
            help="Start nodes added through -s", default=False)
        parser.add_option('-d', "--debug", action="store_true", dest="debug",
            help="If -s is used, show the standard output when starting the nodes", default=False)
        parser.add_option('-b', "--binary-protocol", action="store_true", dest="binary_protocol",
            help="Enable the binary protocol (starting from C* 1.2.5 the binary protocol is started by default and this option is a no-op)", default=False)
        parser.add_option('-D', "--debug-log", action="store_true", dest="debug_log",
            help="With -n, sets debug logging on the new nodes", default=False)
        parser.add_option('-T', "--trace-log", action="store_true", dest="trace_log",
            help="With -n, sets trace logging on the new nodes", default=False)
        parser.add_option("--vnodes", action="store_true", dest="vnodes",
            help="Use vnodes (256 tokens)", default=False)
        parser.add_option('--jvm_arg', action="append", dest="jvm_args",
            help="Specify a JVM argument", default=[])
        parser.add_option('--profile', action="store_true", dest="profile",
            help="Start the nodes with yourkit agent (only valid with -s)", default=False)
        parser.add_option('--profile-opts', type="string", action="store", dest="profile_options",
            help="Yourkit options when profiling", default=None)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, cluster_name=True)
        self.nodes = parse_populate_count(options.nodes)

    def run(self):
        try:
            cluster = Cluster(self.path, self.name, cassandra_dir=self.options.cassandra_dir, cassandra_version=self.options.cassandra_version, verbose=True)
        except OSError as e:
            cluster_dir = os.path.join(self.path, self.name)
            import traceback
            print_('Cannot create cluster: %s\n%s' % (str(e), traceback.format_exc()), file=sys.stderr)
            exit(1)

        if self.options.partitioner:
            cluster.set_partitioner(self.options.partitioner)

        if cluster.version() >= "1.2.5":
            self.options.binary_protocol = True
        if self.options.binary_protocol:
            cluster.set_configuration_options({ 'start_native_transport' : True })

        if cluster.version() >= "1.2" and self.options.vnodes:
            cluster.set_configuration_options({ 'num_tokens' : 256 })

        if not self.options.no_switch:
            common.switch_cluster(self.path, self.name)
            print_('Current cluster is now: %s' % self.name)

        if self.nodes is not None:
            try:
                if self.options.debug_log:
                    cluster.set_log_level("DEBUG")
                if self.options.trace_log:
                    cluster.set_log_level("TRACE")
                cluster.populate(self.nodes, use_vnodes=self.options.vnodes, ipprefix=self.options.ipprefix)
                if self.options.start_nodes:
                    profile_options = None
                    if self.options.profile:
                        profile_options = {}
                        if self.options.profile_options:
                            profile_options['options'] = self.options.profile_options
                    if cluster.start(verbose=self.options.debug, wait_for_binary_proto=self.options.binary_protocol, jvm_args=self.options.jvm_args, profile_options=profile_options) is None:
                        details = ""
                        if not self.options.debug:
                            details = " (you can use --debug for more information)"
                        print_("Error starting nodes, see above for details%s" % details, file=sys.stderr)
            except common.ArgumentError as e:
                print_(str(e), file=sys.stderr)
                exit(1)

class ClusterAddCmd(Cmd):
    def description(self):
        return "Add a new node to the current cluster"

    def get_parser(self):
        usage = "usage: ccm add [options] node_name"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('-b', '--auto-boostrap', action="store_true", dest="boostrap",
            help="Set auto bootstrap for the node", default=False)
        parser.add_option('-s', '--seeds', action="store_true", dest="is_seed",
            help="Configure this node as a seed", default=False)
        parser.add_option('-i', '--itf', type="string", dest="itfs",
            help="Set host and port for thrift, the binary protocol and storage (format: host[:port])")
        parser.add_option('-t', '--thrift-itf', type="string", dest="thrift_itf",
            help="Set the thrift host and port for the node (format: host[:port])")
        parser.add_option('-l', '--storage-itf', type="string", dest="storage_itf",
            help="Set the storage (cassandra internal) host and port for the node (format: host[:port])")
        parser.add_option('--binary-itf', type="string", dest="binary_itf",
            help="Set the binary protocol host and port for the node (format: host[:port]).")
        parser.add_option('-j', '--jmx-port', type="string", dest="jmx_port",
            help="JMX port for the node", default="7199")
        parser.add_option('-r', '--remote-debug-port', type="string", dest="remote_debug_port",
            help="Remote Debugging Port for the node", default="2000")
        parser.add_option('-n', '--token', type="string", dest="initial_token",
            help="Initial token for the node", default=None)
        parser.add_option('-d', '--data-center', type="string", dest="data_center",
            help="Datacenter name this node is part of", default=None)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True, load_node=False)

        if options.itfs is None and (options.thrift_itf is None or options.storage_itf is None or options.binary_itf is None):
            print_('Missing thrift and/or storage and/or binary protocol interfaces or jmx port', file=sys.stderr)
            parser.print_help()
            exit(1)

        if options.thrift_itf is None:
            options.thrift_itf = options.itfs
        if options.storage_itf is None:
            options.storage_itf = options.itfs
        if options.binary_itf is None:
            options.binary_itf = options.itfs

        self.thrift = common.parse_interface(options.thrift_itf, 9160)
        self.storage = common.parse_interface(options.storage_itf, 7000)
        self.binary = common.parse_interface(options.binary_itf, 9042)

        if self.binary[0] != self.thrift[0]:
            print_('Cannot set a binary address different from the thrift one', file=sys.stderr)
            exit(1)


        self.jmx_port = options.jmx_port
        self.remote_debug_port = options.remote_debug_port
        self.initial_token = options.initial_token


    def run(self):
        try:
            node = Node(self.name, self.cluster, self.options.boostrap, self.thrift, self.storage, self.jmx_port, self.remote_debug_port, self.initial_token, binary_interface=self.binary)
            self.cluster.add(node, self.options.is_seed, self.options.data_center)
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

class ClusterPopulateCmd(Cmd):
    def description(self):
        return "Add a group of new nodes with default options"

    def get_parser(self):
        usage = "usage: ccm populate -n <node count> {-d}"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('-n', '--nodes', type="string", dest="nodes",
            help="Number of nodes to populate with (a single int or a colon-separate list of ints for multi-dc setups)")
        parser.add_option('-d', '--debug', action="store_true", dest="debug",
            help="Enable remote debugging options", default=False)
        parser.add_option('--vnodes', action="store_true", dest="vnodes",
            help="Populate using vnodes", default=False)
        parser.add_option('-i', '--ipprefix', type="string", dest="ipprefix", default="127.0.0.",
            help="Ipprefix to use to create the ip of a node")
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)
        self.nodes = parse_populate_count(options.nodes)

    def run(self):
        try:
            if self.cluster.version() >= "1.2" and self.options.vnodes:
                self.cluster.set_configuration_options({ 'num_tokens' : 256 })

            self.cluster.populate(self.nodes, self.options.debug, use_vnodes=self.options.vnodes, ipprefix=self.options.ipprefix)
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

class ClusterListCmd(Cmd):
    def description(self):
        return "List existing clusters"

    def get_parser(self):
        usage = "usage: ccm list [options]"
        return self._get_default_parser(usage, self.description())

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args)

    def run(self):
        try:
            current = common.current_cluster_name(self.path)
        except Exception as e:
            current = ''

        for dir in os.listdir(self.path):
            if os.path.exists(os.path.join(self.path, dir, 'cluster.conf')):
                print_(" %s%s" % ('*' if current == dir else ' ', dir))

class ClusterSwitchCmd(Cmd):
    def description(self):
        return "Switch of current (active) cluster"

    def get_parser(self):
        usage = "usage: ccm switch [options] cluster_name"
        return self._get_default_parser(usage, self.description())

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, cluster_name=True)
        if not os.path.exists(os.path.join(self.path, self.name, 'cluster.conf')):
            print_("%s does not appear to be a valid cluster (use ccm cluster list to view valid cluster)" % self.name, file=sys.stderr)
            exit(1)

    def run(self):
        common.switch_cluster(self.path, self.name)

class ClusterStatusCmd(Cmd):
    def description(self):
        return "Display status on the current cluster"

    def get_parser(self):
        usage = "usage: ccm status [options]"
        parser =  self._get_default_parser(usage, self.description())
        parser.add_option('-v', '--verbose', action="store_true", dest="verbose",
                help="Print full information on all nodes", default=False)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)

    def run(self):
        self.cluster.show(self.options.verbose)

class ClusterRemoveCmd(Cmd):
    def description(self):
        return "Remove the current or specified cluster (delete all data)"

    def get_parser(self):
        usage = "usage: ccm remove [options] [cluster_name]"
        parser =  self._get_default_parser(usage, self.description())
        return parser

    def validate(self, parser, options, args):
        self.other_cluster = None
        if len(args) > 0:
            # Setup to remove the specified cluster:
            Cmd.validate(self, parser, options, args)
            self.other_cluster = args[0]
            if not os.path.exists(os.path.join(
                    self.path, self.other_cluster, 'cluster.conf')):
                print_("%s does not appear to be a valid cluster" \
                    " (use ccm cluster list to view valid cluster)" \
                    % self.other_cluster, file=sys.stderr)
                exit(1)
        else:
            # Setup to remove the current cluster:
            Cmd.validate(self, parser, options, args, load_cluster=True)


    def run(self):
        if self.other_cluster:
            # Remove the specified cluster:
            cluster = Cluster.load(self.path, self.other_cluster)
            cluster.remove()
            # Remove CURRENT flag if the specified cluster is the current cluster:
            if self.other_cluster == common.current_cluster_name(self.path):
                os.remove(os.path.join(self.path, 'CURRENT'))
        else:
            # Remove the current cluster:
            self.cluster.remove()
            os.remove(os.path.join(self.path, 'CURRENT'))

class ClusterClearCmd(Cmd):
    def description(self):
        return "Clear the current cluster data (and stop all nodes)"

    def get_parser(self):
        usage = "usage: ccm clear [options]"
        parser =  self._get_default_parser(usage, self.description())
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)

    def run(self):
        self.cluster.clear()

class ClusterLivesetCmd(Cmd):
    def description(self):
        return "Print a comma-separated list of addresses of running nodes (handful in scripts)"

    def get_parser(self):
        usage = "usage: ccm liveset [options]"
        parser =  self._get_default_parser(usage, self.description())
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)

    def run(self):
        l = [ node.network_interfaces['storage'][0] for node in list(self.cluster.nodes.values()) if node.is_live() ]
        print_(",".join(l))

class ClusterSetdirCmd(Cmd):
    def description(self):
        return "Set the cassandra directory to use"

    def get_parser(self):
        usage = "usage: ccm setdir [options]"
        parser =  self._get_default_parser(usage, self.description())
        parser.add_option('-v', "--cassandra-version", type="string", dest="cassandra_version",
            help="Download and use provided cassandra version. If version is of the form 'git:<branch name>', then the specified branch will be downloaded from the git repo and compiled. (takes precedence over --cassandra-dir)", default=None)
        parser.add_option("--cassandra-dir", type="string", dest="cassandra_dir",
            help="Path to the cassandra directory to use [default %default]", default="./")
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)

    def run(self):
        try:
            self.cluster.set_cassandra_dir(cassandra_dir=self.options.cassandra_dir, cassandra_version=self.options.cassandra_version, verbose=True)
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

class ClusterClearrepoCmd(Cmd):
    def description(self):
        return "Cleanup downloaded cassandra sources"

    def get_parser(self):
        usage = "usage: ccm clearrepo [options]"
        parser =  self._get_default_parser(usage, self.description())
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args)

    def run(self):
        repository.clean_all()

class ClusterStartCmd(Cmd):
    def description(self):
        return "Start all the non started nodes of the current cluster"

    def get_parser(self):
        usage = "usage: ccm cluster start [options]"
        parser =  self._get_default_parser(usage, self.description())
        parser.add_option('-v', '--verbose', action="store_true", dest="verbose",
            help="Print standard output of cassandra process", default=False)
        parser.add_option('--no-wait', action="store_true", dest="no_wait",
            help="Do not wait for cassandra node to be ready", default=False)
        parser.add_option('--jvm_arg', action="append", dest="jvm_args",
            help="Specify a JVM argument", default=[])
        parser.add_option('--profile', action="store_true", dest="profile",
            help="Start the nodes with yourkit agent (only valid with -s)", default=False)
        parser.add_option('--profile-opts', type="string", action="store", dest="profile_options",
            help="Yourkit options when profiling", default=None)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)

    def run(self):
        try:
            profile_options = None
            if self.options.profile:
                profile_options = {}
                if self.options.profile_options:
                    profile_options['options'] = self.options.profile_options
            if self.cluster.start(no_wait=self.options.no_wait, verbose=self.options.verbose, jvm_args=self.options.jvm_args, profile_options=profile_options) is None:
                details = ""
                if not self.options.verbose:
                    details = " (you can use --verbose for more information)"
                print_("Error starting nodes, see above for details%s" % details, file=sys.stderr)
        except NodeError as e:
            print_(str(e), file=sys.stderr)
            print_("Standard error output is:", file=sys.stderr)
            for line in e.process.stderr:
                print_(line.rstrip('\n'), file=sys.stderr)
            exit(1)

class ClusterStopCmd(Cmd):
    def description(self):
        return "Stop all the nodes of the cluster"

    def get_parser(self):
        usage = "usage: ccm cluster stop [options] name"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('-v', '--verbose', action="store_true", dest="verbose",
                help="Print nodes that were not running", default=False)
        parser.add_option('--no-wait', action="store_true", dest="no_wait",
            help="Do not wait for the node to be stopped", default=False)
        parser.add_option('-g', '--gently', action="store_true", dest="gently",
            help="Shut down gently (default)", default=True)
        parser.add_option('--not-gently', action="store_false", dest="gently",
            help="Shut down immediately (kill -9)", default=True)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)

    def run(self):
        try:
            not_running = self.cluster.stop(not self.options.no_wait, gently=self.options.gently)
            if self.options.verbose and len(not_running) > 0:
                sys.out.write("The following nodes were not running: ")
                for node in not_running:
                    sys.out.write(node.name + " ")
                print_("")
        except NodeError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

class _ClusterNodetoolCmd(Cmd):
    def get_parser(self):
        parser = self._get_default_parser(self.usage, self.description())
        return parser

    def description(self):
        return self.descr_text

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)

    def run(self):
        self.cluster.nodetool(self.nodetool_cmd)

class ClusterFlushCmd(_ClusterNodetoolCmd):
    usage = "usage: ccm cluster flush [options] name"
    nodetool_cmd = 'flush'
    descr_text = "Flush all (running) nodes of the cluster"

class ClusterCompactCmd(_ClusterNodetoolCmd):
    usage = "usage: ccm cluster compact [options] name"
    nodetool_cmd = 'compact'
    descr_text = "Compact all (running) node of the cluster"

class ClusterDrainCmd(_ClusterNodetoolCmd):
    usage = "usage: ccm cluster drain [options] name"
    nodetool_cmd = 'drain'
    descr_text = "Drain all (running) node of the cluster"

class ClusterStressCmd(Cmd):
    def description(self):
        return "Run stress using all live nodes"

    def get_parser(self):
        usage = "usage: ccm stress [options] [stress_options]"
        parser = self._get_default_parser(usage, self.description(), ignore_unknown_options=True)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)
        self.stress_options = parser.get_ignored() + args

    def run(self):
        try:
            self.cluster.stress(self.stress_options)
        except Exception as e:
            print_(e, file=sys.stderr)

class ClusterUpdateconfCmd(Cmd):
    def description(self):
        return "Update the cassandra config files for all nodes"

    def get_parser(self):
        usage = "usage: ccm updateconf [options] [ new_setting | ...  ], where new_setting should be a string of the form 'compaction_throughput_mb_per_sec: 32'"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('--no-hh', '--no-hinted-handoff', action="store_false",
            dest="hinted_handoff", default=True, help="Disable hinted handoff")
        parser.add_option('--batch-cl', '--batch-commit-log', action="store_true",
            dest="cl_batch", default=False, help="Set commit log to batch mode")
        parser.add_option('--rt', '--rpc-timeout', action="store", type='int',
            dest="rpc_timeout", help="Set rpc timeout")
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)
        try:
            self.setting = common.parse_settings(args)
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

    def run(self):
        self.setting['hinted_handoff_enabled'] = self.options.hinted_handoff
        if self.options.rpc_timeout is not None:
            if self.cluster.version() < "1.2":
                self.setting['rpc_timeout_in_ms'] = self.options.rpc_timeout
            else:
                self.setting['read_request_timeout_in_ms'] = self.options.rpc_timeout
                self.setting['range_request_timeout_in_ms'] = self.options.rpc_timeout
                self.setting['write_request_timeout_in_ms'] = self.options.rpc_timeout
                self.setting['truncate_request_timeout_in_ms'] = self.options.rpc_timeout
                self.setting['request_timeout_in_ms'] = self.options.rpc_timeout

        self.cluster.set_configuration_options(values=self.setting, batch_commitlog=self.options.cl_batch)

#
# Class implementens the functionality of updating log4j-server.properties 
# on ALL nodes by copying the given config into 
# ~/.ccm/name-of-cluster/nodeX/conf/log4j-server.properties
#
class ClusterUpdatelog4jCmd(Cmd):
    def description(self):
        return "Update the Cassandra log4j-server.properties configuration file on all nodes"

    def get_parser(self):
        usage = "usage: ccm updatelog4j -p <log4j config>"
        parser = self._get_default_parser(usage, self.description(), ignore_unknown_options=True)
        parser.add_option('-p', '--path', type="string", dest="log4jpath",
            help="Path to new Cassandra log4j configuration file")
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)
        try:
            self.log4jpath = options.log4jpath
            if self.log4jpath is None:
                raise KeyError("[Errno] -p or --path <path of new log4j congiguration file> is not provided") 
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)
        except KeyError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

    def run(self):
        try:
            self.cluster.update_log4j(self.log4jpath)
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

class ClusterCliCmd(Cmd):
    def description(self):
        return "Launch cassandra cli connected to some live node (if any)"

    def get_parser(self):
        usage = "usage: ccm cli [options] [cli_options]"
        parser = self._get_default_parser(usage, self.description(), ignore_unknown_options=True)
        parser.add_option('-x', '--exec', type="string", dest="cmds", default=None,
            help="Execute the specified commands and exit")
        parser.add_option('-v', '--verbose', action="store_true", dest="verbose",
            help="With --exec, show cli output after completion", default=False)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)
        self.cli_options = parser.get_ignored() + args[1:]

    def run(self):
        self.cluster.run_cli(self.options.cmds, self.options.verbose, self.cli_options)

class ClusterBulkloadCmd(Cmd):
    def description(self):
        return "Bulkload files into the cluster"

    def get_parser(self):
        usage = "usage: ccm bulkload [options] [sstable_dir]"
        parser = self._get_default_parser(usage, self.description(), ignore_unknown_options=True)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)
        self.loader_options = parser.get_ignored() + args

    def run(self):
        self.cluster.bulkload(self.loader_options)

class ClusterScrubCmd(Cmd):
    def description(self):
        return "Scrub files"

    def get_parser(self):
        usage = "usage: ccm scrub [options] <keyspace> <cf>"
        parser = self._get_default_parser(usage, self.description(), ignore_unknown_options=True)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)
        self.scrub_options = parser.get_ignored() + args

    def run(self):
        self.cluster.scrub(self.scrub_options)

class ClusterSetlogCmd(Cmd):
    def description(self):
        return "Set log level (INFO, DEBUG, ...) with/without Java class for all node of the cluster - require a node restart"


    def get_parser(self):
        usage = "usage: ccm setlog [options] level"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('-c', '--class', type="string", dest="class_name", default=None,
            help="Optional java class/package. Logging will be set for only this class/package if set")
        return parser


    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, load_cluster=True)
        if len(args) == 0:
            print_('Missing log level', file=sys.stderr)
            parser.print_help()
            exit(1)
        self.level = args[0]

    def run(self):
        try:
            self.cluster.set_log_level(self.level, self.options.class_name)
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

########NEW FILE########
__FILENAME__ = command
import sys

from six import print_

from optparse import OptionParser, BadOptionError, Option

from ccmlib import common
from ccmlib.cluster import Cluster

# This is fairly fragile, but handy for now
class ForgivingParser(OptionParser):
    def __init__(self, usage=None, option_list=None, option_class=Option, version=None, conflict_handler="error", description=None, formatter=None, add_help_option=True, prog=None, epilog=None):
        OptionParser.__init__(self, usage, option_list, option_class, version, conflict_handler, description, formatter, add_help_option, prog, epilog)
        self.ignored = []

    def _process_short_opts(self, rargs, values):
        opt = rargs[0]
        try:
            OptionParser._process_short_opts(self, rargs, values)
        except BadOptionError as e:
            self.ignored.append(opt)
            self.eat_args(rargs)

    def _process_long_opt(self, rargs, values):
        opt = rargs[0]
        try:
            OptionParser._process_long_opt(self, rargs, values)
        except BadOptionError as e:
            self.ignored.append(opt)
            self.eat_args(rargs)

    def eat_args(self, rargs):
        while len(rargs) > 0 and rargs[0][0] != '-':
            self.ignored.append(rargs.pop(0))

    def get_ignored(self):
        return self.ignored

class Cmd(object):
    def get_parser(self):
        pass

    def validate(self, parser, options, args, cluster_name=False, node_name=False, load_cluster=False, load_node=True):
        self.options = options
        self.args = args
        if options.config_dir is None:
            self.path = common.get_default_path()
        else:
            self.path = options.config_dir

        if cluster_name:
          if len(args) == 0:
              print_('Missing cluster name', file=sys.stderr)
              parser.print_help()
              exit(1)
          self.name = args[0]
        if node_name:
          if len(args) == 0:
              print_('Missing node name', file=sys.stderr)
              parser.print_help()
              exit(1)
          self.name = args[0]

        if load_cluster:
            self.cluster = self._load_current_cluster()
            if node_name and load_node:
                try:
                    self.node = self.cluster.nodes[self.name]
                except KeyError:
                    print_('Unknown node %s in cluster %s' % (self.name, self.cluster.name), file=sys.stderr)
                    exit(1)

    def run(self):
        pass

    def _get_default_parser(self, usage, description, ignore_unknown_options=False):
        if ignore_unknown_options:
            parser = ForgivingParser(usage=usage, description=description)
        else:
            parser = OptionParser(usage=usage, description=description)
        parser.add_option('--config-dir', type="string", dest="config_dir",
            help="Directory for the cluster files [default to ~/.ccm]")
        return parser

    def description():
        return ""

    def _load_current_cluster(self):
        name = common.current_cluster_name(self.path)
        if name is None:
            print_('No currently active cluster (use ccm cluster switch)')
            exit(1)
        try:
            return Cluster.load(self.path, name)
        except common.LoadError as e:
            print_(str(e))
            exit(1)

########NEW FILE########
__FILENAME__ = node_cmds
import os
import sys

from six import print_

from ccmlib import common
from ccmlib.node import NodeError
from ccmlib.cmds.command import Cmd

def node_cmds():
    return [
        "show",
        "remove",
        "showlog",
        "setlog",
        "start",
        "stop",
        "ring",
        "flush",
        "compact",
        "drain",
        "cleanup",
        "repair",
        "scrub",
        "shuffle",
        "sstablesplit",
        "decommission",
        "json",
        "updateconf",
        "updatelog4j",
        "stress",
        "cli",
        "cqlsh",
        "scrub",
        "status",
        "setdir",
        "version",
        "nodetool"
    ]

class NodeShowCmd(Cmd):
    def description(self):
        return "Display information on a node"

    def get_parser(self):
        usage = "usage: ccm node_name show [options]"
        return self._get_default_parser(usage, self.description())

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)

    def run(self):
        self.node.show()

class NodeRemoveCmd(Cmd):
    def description(self):
        return "Remove a node (stopping it if necessary and deleting all its data)"

    def get_parser(self):
        usage = "usage: ccm node_name remove [options]"
        return self._get_default_parser(usage, self.description())

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)

    def run(self):
        self.cluster.remove(self.node)

class NodeShowlogCmd(Cmd):
    def description(self):
        return "Show the log of node name (runs your $PAGER on its system.log)"

    def get_parser(self):
        usage = "usage: ccm node_name showlog [options]"
        return self._get_default_parser(usage, self.description())

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)

    def run(self):
        log = self.node.logfilename()
        pager = os.environ.get('PAGER', common.platform_pager())
        os.execvp(pager, (pager, log))

class NodeSetlogCmd(Cmd):
    def description(self):
        return "Set node name log level (INFO, DEBUG, ...) with/without Java class - require a node restart"

    def get_parser(self):
        usage = "usage: ccm node_name setlog [options] level"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('-c', '--class', type="string", dest="class_name", default=None,
            help="Optional java class/package. Logging will be set for only this class/package if set")
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)
        if len(args) == 1:
            print_('Missing log level', file=sys.stderr)
            parser.print_help()
        self.level = args[1]

        try:
            self.class_name = options.class_name
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

    def run(self):
        try:
            self.node.set_log_level(self.level, self.class_name)

        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

class NodeClearCmd(Cmd):
    def description(self):
        return "Clear the node data & logs (and stop the node)"

    def get_parser(self):
        usage = "usage: ccm node_name_clear [options]"
        parser =  self._get_default_parser(usage, self.description())
        parser.add_option('-a', '--all', action="store_true", dest="all",
                help="Also clear the saved cache and node log files", default=False)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)

    def run(self):
        self.node.stop()
        self.node.clear(self.options.all)

class NodeStartCmd(Cmd):
    def description(self):
        return "Start a node"

    def get_parser(self):
        usage = "usage: ccm node start [options] name"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('-v', '--verbose', action="store_true", dest="verbose",
            help="Print standard output of cassandra process", default=False)
        parser.add_option('--no-wait', action="store_true", dest="no_wait",
            help="Do not wait for cassandra node to be ready", default=False)
        parser.add_option('-j', '--dont-join-ring', action="store_true", dest="no_join_ring",
            help="Launch the instance without joining the ring", default=False)
        parser.add_option('--replace-address', type="string", dest="replace_address", default=None,
            help="Replace a node in the ring through the cassandra.replace_address option")
        parser.add_option('--jvm_arg', action="append", dest="jvm_args",
            help="Specify a JVM argument", default=[])
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)

    def run(self):
        try:
            self.node.start(not self.options.no_join_ring,
                            no_wait=self.options.no_wait,
                            verbose=self.options.verbose,
                            replace_address=self.options.replace_address,
                            jvm_args=self.options.jvm_args)
        except NodeError as e:
            print_(str(e), file=sys.stderr)
            print_("Standard error output is:", file=sys.stderr)
            for line in e.process.stderr:
                print_(line.rstrip('\n'), file=sys.stderr)
            exit(1)

class NodeStopCmd(Cmd):
    def description(self):
        return "Stop a node"

    def get_parser(self):
        usage = "usage: ccm node stop [options] name"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('--no-wait', action="store_true", dest="no_wait",
            help="Do not wait for the node to be stopped", default=False)
        parser.add_option('-g', '--gently', action="store_true", dest="gently",
            help="Shut down gently (default)", default=True)
        parser.add_option('--not-gently', action="store_false", dest="gently",
            help="Shut down immediately (kill -9)", default=True)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)

    def run(self):
        try:
            if not self.node.stop(not self.options.no_wait, gently=self.options.gently):
                print_("%s is not running" % self.name, file=sys.stderr)
                exit(1)
        except NodeError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

class _NodeToolCmd(Cmd):
    def get_parser(self):
        parser = self._get_default_parser(self.usage, self.description())
        return parser

    def description(self):
        return self.descr_text

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)

    def run(self):
        self.node.nodetool(self.nodetool_cmd)

class NodeNodetoolCmd(_NodeToolCmd):
    usage = "usage: ccm node_name nodetool [options]"
    descr_text = "Run nodetool (connecting to node name)"

    def run(self):
        self.node.nodetool(" ".join(self.args[1:]))

class NodeRingCmd(_NodeToolCmd):
    usage = "usage: ccm node_name ring [options]"
    nodetool_cmd = 'ring'
    descr_text = "Print ring (connecting to node name)"

class NodeStatusCmd(_NodeToolCmd):
    usage = "usage: ccm node_name status [options]"
    nodetool_cmd = 'status'
    descr_text = "Print status (connecting to node name)"

class NodeFlushCmd(_NodeToolCmd):
    usage = "usage: ccm node_name flush [options]"
    nodetool_cmd = 'flush'
    descr_text = "Flush node name"

class NodeCompactCmd(_NodeToolCmd):
    usage = "usage: ccm node_name compact [options]"
    nodetool_cmd = 'compact'
    descr_text = "Compact node name"

class NodeDrainCmd(_NodeToolCmd):
    usage = "usage: ccm node_name drain [options]"
    nodetool_cmd = 'drain'
    descr_text = "Drain node name"

class NodeCleanupCmd(_NodeToolCmd):
    usage = "usage: ccm node_name cleanup [options]"
    nodetool_cmd = 'cleanup'
    descr_text = "Run cleanup on node name"

class NodeRepairCmd(_NodeToolCmd):
    usage = "usage: ccm node_name repair [options]"
    nodetool_cmd = 'repair'
    descr_text = "Run repair on node name"

class NodeVersionCmd(_NodeToolCmd):
    usage = "usage: ccm node_name version"
    nodetool_cmd = 'version'
    descr_text = "Get the cassandra version of node"

class NodeDecommissionCmd(_NodeToolCmd):
    usage = "usage: ccm node_name decommission [options]"
    nodetool_cmd = 'decommission'
    descr_text = "Run decommission on node name"

    def run(self):
        self.node.decommission()

class NodeScrubCmd(_NodeToolCmd):
    usage = "usage: ccm node_name scrub [options]"
    nodetool_cmd = 'scrub'
    descr_text = "Run scrub on node name"

class NodeCliCmd(Cmd):
    def description(self):
        return "Launch a cassandra cli connected to this node"

    def get_parser(self):
        usage = "usage: ccm node_name cli [options] [cli_options]"
        parser = self._get_default_parser(usage, self.description(), ignore_unknown_options=True)
        parser.add_option('-x', '--exec', type="string", dest="cmds", default=None,
            help="Execute the specified commands and exit")
        parser.add_option('-v', '--verbose', action="store_true", dest="verbose",
            help="With --exec, show cli output after completion", default=False)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)
        self.cli_options = parser.get_ignored() + args[1:]

    def run(self):
        self.node.run_cli(self.options.cmds, self.options.verbose, self.cli_options)

class NodeCqlshCmd(Cmd):
    def description(self):
        return "Launch a cqlsh session connected to this node"

    def get_parser(self):
        usage = "usage: ccm node_name cqlsh [options] [cli_options]"
        parser = self._get_default_parser(usage, self.description(), ignore_unknown_options=True)
        parser.add_option('-x', '--exec', type="string", dest="cmds", default=None,
            help="Execute the specified commands and exit")
        parser.add_option('-v', '--verbose', action="store_true", dest="verbose",
            help="With --exec, show cli output after completion", default=False)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)
        self.cqlsh_options = parser.get_ignored() + args[1:]

    def run(self):
        self.node.run_cqlsh(self.options.cmds, self.options.verbose, self.cqlsh_options)

class NodeScrubCmd(Cmd):
    def description(self):
        return "Scrub files"

    def get_parser(self):
        usage = "usage: ccm node_name scrub [options] <keyspace> <cf>"
        parser = self._get_default_parser(usage, self.description(), ignore_unknown_options=True)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)
        self.scrub_options = parser.get_ignored() + args[1:]

    def run(self):
        self.node.scrub(self.scrub_options)

class NodeJsonCmd(Cmd):
    def description(self):
        return "Call sstable2json on the sstables of this node"

    def get_parser(self):
        usage = "usage: ccm node_name json [options] [file]"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('-k', '--keyspace', type="string", dest="keyspace", default=None,
            help="The keyspace to use [use all keyspaces by default]")
        parser.add_option('-c', '--column-families', type="string", dest="cfs", default=None,
            help="Comma separated list of column families to use (requires -k to be set)")
        parser.add_option('-e', '--enumerate-keys', action="store_true", dest="enumerate_keys",
            help="Only enumerate keys (i.e, call sstable2keys)", default=False)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)
        self.keyspace = options.keyspace
        self.column_families = None
        self.datafile = None
        if len(args) > 1:
            self.datafile = args[1]
            if self.keyspace is None:
                print_("You need a keyspace specified (option -k) if you specify a file", file=sys.stderr)
                exit(1)
        elif options.cfs is not None:
            if self.keyspace is None:
                print_("You need a keyspace specified (option -k) if you specify column families", file=sys.stderr)
                exit(1)
            self.column_families = options.cfs.split(',')

    def run(self):
        try:
            self.node.run_sstable2json(self.keyspace, self.datafile, self.column_families, self.options.enumerate_keys)
        except common.ArgumentError as e:
            print_(e, file=sys.stderr)

class NodeSstablesplitCmd(Cmd):
    def description(self):
        return "Run sstablesplit on the sstables of this node"

    def get_parser(self):
        usage = "usage: ccm node_name sstablesplit [options] [file]"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('-k', '--keyspace', type="string", dest="keyspace", default=None,
                          help="The keyspace to use [use all keyspaces by default]")
        parser.add_option('-c', '--column-families', type="string", dest='cfs', default=None,
                          help="Comma seperated list of column families ut use (requires -k to be set)")
        parser.add_option('-s', '--size', type='int', dest="size", default=None,
                          help="Maximum size in MB for the output sstables (default: 50 MB)")
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)
        self.keyspace = options.keyspace
        self.size = options.size
        self.column_families = None
        self.datafile = None

        if len(args) > 1:
            self.datafile = args[1]
        else:
            if options.cfs is not None:
                if self.keyspace is None:
                    print_("You need a keyspace (option -k) if you specify column families", file=sys.stderr)
                    exit(1)
                    self.column_families = options.cfs.split(',')

    def run(self):
        if self.datafile is not None:
            self.node.run_sstablesplit(datafile=self.datafile, size=self.size)
        else:
            self.node.run_sstablesplit(keyspace=self.keyspace, column_families=self.column_families, size=self.size)

class NodeUpdateconfCmd(Cmd):
    def description(self):
        return "Update the cassandra config files for this node (useful when updating cassandra)"

    def get_parser(self):
        usage = "usage: ccm node_name updateconf [options] [ new_setting | ...  ], where new_setting should be a string of the form 'compaction_throughput_mb_per_sec: 32'"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('--no-hh', '--no-hinted-handoff', action="store_false",
            dest="hinted_handoff", default=True, help="Disable hinted handoff")
        parser.add_option('--batch-cl', '--batch-commit-log', action="store_true",
            dest="cl_batch", default=False, help="Set commit log to batch mode")
        parser.add_option('--rt', '--rpc-timeout', action="store", type='int',
            dest="rpc_timeout", help="Set rpc timeout")
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)
        args = args[1:]
        try:
            self.setting = common.parse_settings(args)
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

    def run(self):
        self.setting['hinted_handoff_enabled'] = self.options.hinted_handoff
        if self.options.rpc_timeout is not None:
            if self.node.cluster.version() < "1.2":
                self.setting['rpc_timeout_in_ms'] = self.options.rpc_timeout
            else:
                self.setting['read_request_timeout_in_ms'] = self.options.rpc_timeout
                self.setting['range_request_timeout_in_ms'] = self.options.rpc_timeout
                self.setting['write_request_timeout_in_ms'] = self.options.rpc_timeout
                self.setting['truncate_request_timeout_in_ms'] = self.options.rpc_timeout
                self.setting['request_timeout_in_ms'] = self.options.rpc_timeout
        self.node.set_configuration_options(values=self.setting, batch_commitlog=self.options.cl_batch)


#
# Class implementens the functionality of updating log4j-server.properties
# on the given node by copying the given config into
# ~/.ccm/name-of-cluster/nodeX/conf/log4j-server.properties
#

class NodeUpdatelog4jCmd(Cmd):
    def description(self):
        return "Update the Cassandra log4j-server.properties configuration file under given node"

    def get_parser(self):
        usage = "usage: ccm node_name updatelog4j -p <log4j config>"
        parser = self._get_default_parser(usage, self.description())
        parser.add_option('-p', '--path', type="string", dest="log4jpath",
            help="Path to new Cassandra log4j configuration file")
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)
        try:
            self.log4jpath = options.log4jpath
            if self.log4jpath is None:
                raise KeyError("[Errno] -p or --path <path of new log4j configuration file> is not provided")
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)
        except KeyError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

    def run(self):
        try:
            self.node.update_log4j(self.log4jpath)
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)

class NodeStressCmd(Cmd):
    def description(self):
        return "Run stress on a node"

    def get_parser(self):
        usage = "usage: ccm node_name stress [options] [stress_options]"
        parser = self._get_default_parser(usage, self.description(), ignore_unknown_options=True)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)
        self.stress_options = parser.get_ignored() + args[1:]

    def run(self):
        try:
            self.node.stress(self.stress_options)
        except OSError:
            print_("Could not find stress binary (you may need to build it)", file=sys.stderr)

class NodeShuffleCmd(Cmd):
    def description(self):
        return "Run shuffle on a node"

    def get_parser(self):
        usage = "usage: ccm node_name shuffle [options] [shuffle_cmds]"
        parser = self._get_default_parser(usage, self.description(), ignore_unknown_options=True)
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)
        self.shuffle_cmd =  args[1]

    def run(self):
        self.node.shuffle( self.shuffle_cmd )

class NodeSetdirCmd(Cmd):
    def description(self):
        return "Set the cassandra directory to use for the node"

    def get_parser(self):
        usage = "usage: ccm node_name setdir [options]"
        parser =  self._get_default_parser(usage, self.description())
        parser.add_option('-v', "--cassandra-version", type="string", dest="cassandra_version",
            help="Download and use provided cassandra version. If version is of the form 'git:<branch name>', then the specified branch will be downloaded from the git repo and compiled. (takes precedence over --cassandra-dir)", default=None)
        parser.add_option("--cassandra-dir", type="string", dest="cassandra_dir",
            help="Path to the cassandra directory to use [default %default]", default="./")
        return parser

    def validate(self, parser, options, args):
        Cmd.validate(self, parser, options, args, node_name=True, load_cluster=True)

    def run(self):
        try:
            self.node.set_cassandra_dir(cassandra_dir=self.options.cassandra_dir, cassandra_version=self.options.cassandra_version, verbose=True)
        except common.ArgumentError as e:
            print_(str(e), file=sys.stderr)
            exit(1)


########NEW FILE########
__FILENAME__ = common
#
# Cassandra Cluster Management lib
#

import os
import re
import shutil
import socket
import stat
import subprocess
import sys
from six import print_
import time
import yaml

CASSANDRA_BIN_DIR= "bin"
CASSANDRA_CONF_DIR= "conf"

CASSANDRA_CONF = "cassandra.yaml"
LOG4J_CONF = "log4j-server.properties"
LOG4J_TOOL_CONF = "log4j-tools.properties"
LOGBACK_CONF = "logback.xml"
CASSANDRA_ENV = "cassandra-env.sh"
CASSANDRA_SH = "cassandra.in.sh"

CONFIG_FILE = "config"

class CCMError(Exception):
    pass

class LoadError(CCMError):
    pass

class ArgumentError(CCMError):
    pass

class UnavailableSocketError(CCMError):
    pass

def get_default_path():
    default_path = os.path.join(get_user_home(), '.ccm')
    if not os.path.exists(default_path):
        os.mkdir(default_path)
    return default_path

def get_user_home():
    if is_win():
        if sys.platform == "cygwin":
            # Need the fully qualified directory
            output = subprocess.Popen(["cygpath", "-m", os.path.expanduser('~')], stdout = subprocess.PIPE, stderr = subprocess.STDOUT).communicate()[0].rstrip()
            return output
        else:
            return os.environ['USERPROFILE']
    else:
        return os.path.expanduser('~')

def get_config():
    config_path = os.path.join(get_default_path(), CONFIG_FILE)
    if not os.path.exists(config_path):
        return {}

    with open(config_path, 'r') as f:
        return yaml.load(f)

def now_ms():
    return int(round(time.time() * 1000))

def parse_interface(itf, default_port):
    i = itf.split(':')
    if len(i) == 1:
        return (i[0].strip(), default_port)
    elif len(i) == 2:
        return (i[0].strip(), int(i[1].strip()))
    else:
        raise ValueError("Invalid interface definition: " + itf)

def current_cluster_name(path):
    try:
        with open(os.path.join(path, 'CURRENT'), 'r') as f:
            return f.readline().strip()
    except IOError:
        return None

def switch_cluster(path, new_name):
    with open(os.path.join(path, 'CURRENT'), 'w') as f:
        f.write(new_name + '\n')

def replace_in_file(file, regexp, replace):
    replaces_in_file(file, [(regexp, replace)])

def replaces_in_file(file, replacement_list):
    rs = [ (re.compile(regexp), repl) for (regexp, repl) in replacement_list]
    file_tmp = file + ".tmp"
    with open(file, 'r') as f:
        with open(file_tmp, 'w') as f_tmp:
            for line in f:
                for r, replace in rs:
                    match = r.search(line)
                    if match:
                        line = replace + "\n"
                f_tmp.write(line)
    shutil.move(file_tmp, file)

def replace_or_add_into_file_tail(file, regexp, replace):
    replaces_or_add_into_file_tail(file, [(regexp, replace)])

def replaces_or_add_into_file_tail(file, replacement_list):
    rs = [ (re.compile(regexp), repl) for (regexp, repl) in replacement_list]
    is_line_found = False
    file_tmp = file + ".tmp"
    with open(file, 'r') as f:
        with open(file_tmp, 'w') as f_tmp:
            for line in f:
                for r, replace in rs:
                    match = r.search(line)
                    if match:
                        line = replace + "\n"
                        is_line_found = True
                f_tmp.write(line)
            # In case, entry is not found, and need to be added
            if is_line_found == False:
                f_tmp.write('\n'+ replace + "\n")

    shutil.move(file_tmp, file)

def make_cassandra_env(cassandra_dir, node_path):
    sh_file = os.path.join(CASSANDRA_BIN_DIR, CASSANDRA_SH)
    orig = os.path.join(cassandra_dir, sh_file)
    dst = os.path.join(node_path, sh_file)
    shutil.copy(orig, dst)
    replacements = [
        ('CASSANDRA_HOME=', '\tCASSANDRA_HOME=%s' % cassandra_dir),
        ('CASSANDRA_CONF=', '\tCASSANDRA_CONF=%s' % os.path.join(node_path, 'conf'))
    ]
    replaces_in_file(dst, replacements)

    # If a cluster-wide cassandra.in.sh file exists in the parent
    # directory, append it to the node specific one:
    cluster_sh_file = os.path.join(node_path, os.path.pardir, 'cassandra.in.sh')
    if os.path.exists(cluster_sh_file):
        append = open(cluster_sh_file).read()
        with open(dst, 'a') as f:
            f.write('\n\n### Start Cluster wide config ###\n')
            f.write(append)
            f.write('\n### End Cluster wide config ###\n\n')

    env = os.environ.copy()
    env['CASSANDRA_INCLUDE'] = os.path.join(dst)
    return env

def check_win_requirements():
    if is_win():
        # Make sure ant.bat is in the path and executable before continuing
        try:
            process = subprocess.Popen('ant.bat', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as e:
            sys.exit("ERROR!  Could not find or execute ant.bat.  Please fix this before attempting to run ccm on Windows.")

def is_win():
    return True if sys.platform == "cygwin" or sys.platform == "win32" else False

def join_bin(root, dir, executable):
    return os.path.join(root, dir, platform_binary(executable))

def platform_binary(input):
    return input + ".bat" if is_win() else input

def platform_pager():
    return "more" if sys.platform == "win32" else "less"

def add_exec_permission(path, executable):
    # 1) os.chmod on Windows can't add executable permissions
    # 2) chmod from other folders doesn't work in cygwin, so we have to navigate the shell
    # to the folder with the executable with it and then chmod it from there
    if sys.platform == "cygwin":
        cmd = "cd " + path + "; chmod u+x " + executable
        os.system(cmd)

def parse_path(executable):
    sep = os.sep
    if sys.platform == "win32":
        sep = "\\\\"
    tokens = re.split(sep, executable)
    del tokens[-1]
    return os.sep.join(tokens)

def parse_bin(executable):
    tokens = re.split(os.sep, executable)
    return tokens[-1]

def get_stress_bin(cassandra_dir):
    candidates = [
        os.path.join(cassandra_dir, 'contrib', 'stress', 'bin', 'stress'),
        os.path.join(cassandra_dir, 'tools', 'stress', 'bin', 'stress'),
        os.path.join(cassandra_dir, 'tools', 'bin', 'stress'),
        os.path.join(cassandra_dir, 'tools', 'bin', 'cassandra-stress')
    ]
    candidates = [platform_binary(s) for s in candidates]

    for candidate in candidates:
        if os.path.exists(candidate):
            stress = candidate
            break
    else:
        raise Exception("Cannot find stress binary (maybe it isn't compiled)")

    # make sure it's executable -> win32 doesn't care
    if sys.platform == "cygwin":
        # Yes, we're unwinding the path join from above.
        path = parse_path(stress)
        short_bin = parse_bin(stress)
        add_exec_permission(path, short_bin)
    elif not os.access(stress, os.X_OK):
        try:
            # try to add user execute permissions
            # os.chmod doesn't work on Windows and isn't necessary unless in cygwin...
            if sys.platform == "cygwin":
                add_exec_permission(path, stress)
            else:
                os.chmod(stress, os.stat(stress).st_mode | stat.S_IXUSR)
        except:
            raise Exception("stress binary is not executable: %s" % (stress,))

    return stress

def validate_cassandra_dir(cassandra_dir):
    if cassandra_dir is None:
        raise ArgumentError('Undefined cassandra directory')

    # Windows requires absolute pathing on cassandra dir - abort if specified cygwin style
    if is_win():
        if ':' not in cassandra_dir:
            raise ArgumentError('%s does not appear to be a cassandra source directory.  Please use absolute pathing (e.g. C:/cassandra.' % cassandra_dir)

    bin_dir = os.path.join(cassandra_dir, CASSANDRA_BIN_DIR)
    conf_dir = os.path.join(cassandra_dir, CASSANDRA_CONF_DIR)
    cnd = os.path.exists(bin_dir)
    cnd = cnd and os.path.exists(conf_dir)
    cnd = cnd and os.path.exists(os.path.join(conf_dir, CASSANDRA_CONF))
    if not cnd:
        raise ArgumentError('%s does not appear to be a cassandra source directory' % cassandra_dir)

def check_socket_available(itf):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(itf)
        s.close()
    except socket.error as msg:
        s.close()
        addr, port = itf
        raise UnavailableSocketError("Inet address %s:%s is not available: %s" % (addr, port, msg))

def parse_settings(args):
    settings = {}
    for s in args:
        splitted = s.split(':')
        if len(splitted) != 2:
            raise ArgumentError("A new setting should be of the form 'key: value', got" + s)
        val = splitted[1].strip()
        # ok, that's not super beautiful
        if val.lower() == "true":
            val = True
        if val.lower() == "false":
            val = True
        try:
            val = int(val)
        except ValueError:
            pass
        settings[splitted[0].strip()] = val
    return settings

#
# Copy file from source to destination with reasonable error handling
#
def copy_file(src_file, dst_file):
    try:
        shutil.copy2(src_file, dst_file)
    except (IOError, shutil.Error) as e:
        print_(str(e), file=sys.stderr)
        exit(1)


########NEW FILE########
__FILENAME__ = node
# ccm node
from __future__ import with_statement

from six import print_, iteritems, string_types
from six.moves import xrange

import errno
import glob
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import yaml

from ccmlib.repository import setup
from ccmlib.cli_session import CliSession
from ccmlib import common

class Status():
    UNINITIALIZED = "UNINITIALIZED"
    UP = "UP"
    DOWN = "DOWN"
    DECOMMISIONNED = "DECOMMISIONNED"

class NodeError(Exception):
    def __init__(self, msg, process=None):
        Exception.__init__(self, msg)
        self.process = process

class TimeoutError(Exception):
    def __init__(self, data):
        Exception.__init__(self, str(data))

# Groups: 1 = cf, 2 = tmp or none, 3 = suffix (Compacted or Data.db)
_sstable_regexp = re.compile('(?P<cf>[\S]+)+-(?P<tmp>tmp-)?[\S]+-(?P<suffix>[a-zA-Z.]+)')

class Node():
    """
    Provides interactions to a Cassandra node.
    """

    def __init__(self, name, cluster, auto_bootstrap, thrift_interface, storage_interface, jmx_port, remote_debug_port, initial_token, save=True, binary_interface=None):
        """
        Create a new Node.
          - name: the name for that node
          - cluster: the cluster this node is part of
          - auto_boostrap: whether or not this node should be set for auto-boostrap
          - thrift_interface: the (host, port) tuple for thrift
          - storage_interface: the (host, port) tuple for internal cluster communication
          - jmx_port: the port for JMX to bind to
          - remote_debug_port: the port for remote debugging
          - initial_token: the token for this node. If None, use Cassandra token auto-assigment
          - save: copy all data useful for this node to the right position.  Leaving this true
            is almost always the right choice.
        """
        self.name = name
        self.cluster = cluster
        self.status = Status.UNINITIALIZED
        self.auto_bootstrap = auto_bootstrap
        self.network_interfaces = { 'thrift' : thrift_interface, 'storage' : storage_interface, 'binary' : binary_interface }
        self.jmx_port = jmx_port
        self.remote_debug_port = remote_debug_port
        self.initial_token = initial_token
        self.pid = None
        self.data_center = None
        self.__config_options = {}
        self.__cassandra_dir = None
        self.__global_log_level = None
        self.__classes_log_level = {}
        if save:
            self.import_config_files()
            self.import_bin_files()
            if common.is_win:
                self.__clean_bat()

    @staticmethod
    def load(path, name, cluster):
        """
        Load a node from from the path on disk to the config files, the node name and the
        cluster the node is part of.
        """
        node_path = os.path.join(path, name)
        filename = os.path.join(node_path, 'node.conf')
        with open(filename, 'r') as f:
            data = yaml.load(f)
        try:
            itf = data['interfaces']
            initial_token = None
            if 'initial_token' in data:
                initial_token = data['initial_token']
            remote_debug_port = 2000
            if 'remote_debug_port' in data:
                remote_debug_port = data['remote_debug_port']
            binary_interface = None
            if 'binary' in itf and itf['binary'] is not None:
                binary_interface = tuple(itf['binary'])
            node = Node(data['name'], cluster, data['auto_bootstrap'], tuple(itf['thrift']), tuple(itf['storage']), data['jmx_port'], remote_debug_port, initial_token, save=False, binary_interface=binary_interface)
            node.status = data['status']
            if 'pid' in data:
                node.pid = int(data['pid'])
            if 'cassandra_dir' in data:
                node.__cassandra_dir = data['cassandra_dir']
            if 'config_options' in data:
                node.__config_options = data['config_options']
            if 'data_center' in data:
                node.data_center = data['data_center']
            return node
        except KeyError as k:
            raise common.LoadError("Error Loading " + filename + ", missing property: " + str(k))

    def get_path(self):
        """
        Returns the path to this node top level directory (where config/data is stored)
        """
        return os.path.join(self.cluster.get_path(), self.name)

    def get_bin_dir(self):
        """
        Returns the path to the directory where Cassandra scripts are located
        """
        return os.path.join(self.get_path(), 'bin')

    def get_conf_dir(self):
        """
        Returns the path to the directory where Cassandra config are located
        """
        return os.path.join(self.get_path(), 'conf')

    def address(self):
        """
        Returns the IP use by this node for internal communication
        """
        return self.network_interfaces['storage'][0]

    def get_cassandra_dir(self):
        """
        Returns the path to the cassandra source directory used by this node.
        """
        if self.__cassandra_dir is None:
            return self.cluster.get_cassandra_dir()
        else:
            common.validate_cassandra_dir(self.__cassandra_dir)
            return self.__cassandra_dir

    def set_cassandra_dir(self, cassandra_dir=None, cassandra_version=None, verbose=False):
        """
        Sets the path to the cassandra source directory for use by this node.
        """
        if cassandra_version is None:
            self.__cassandra_dir = cassandra_dir
            if cassandra_dir is not None:
                common.validate_cassandra_dir(cassandra_dir)
        else:
            dir, v = setup(cassandra_version, verbose=verbose)
            self.__cassandra_dir = dir
        self.import_config_files()
        return self

    def set_configuration_options(self, values=None, batch_commitlog=None):
        """
        Set Cassandra configuration options.
        ex:
            node.set_configuration_options(values={
                'hinted_handoff_enabled' : True,
                'concurrent_writes' : 64,
            })
        The batch_commitlog option gives an easier way to switch to batch
        commitlog (since it requires setting 2 options and unsetting one).
        """
        if values is not None:
            for k, v in iteritems(values):
                self.__config_options[k] = v
        if batch_commitlog is not None:
            if batch_commitlog:
                self.__config_options["commitlog_sync"] = "batch"
                self.__config_options["commitlog_sync_batch_window_in_ms"] = 5
                self.__config_options["commitlog_sync_period_in_ms"] = None
            else:
                self.__config_options["commitlog_sync"] = "periodic"
                self.__config_options["commitlog_sync_period_in_ms"] = 10000
                self.__config_options["commitlog_sync_batch_window_in_ms"] = None

        self.import_config_files()

    def show(self, only_status=False, show_cluster=True):
        """
        Print infos on this node configuration.
        """
        self.__update_status()
        indent = ''.join([ " " for i in xrange(0, len(self.name) + 2) ])
        print_("%s: %s" % (self.name, self.__get_status_string()))
        if not only_status:
            if show_cluster:
                print_("%s%s=%s" % (indent, 'cluster', self.cluster.name))
            print_("%s%s=%s" % (indent, 'auto_bootstrap', self.auto_bootstrap))
            print_("%s%s=%s" % (indent, 'thrift', self.network_interfaces['thrift']))
            if self.network_interfaces['binary'] is not None:
                print_("%s%s=%s" % (indent, 'binary', self.network_interfaces['binary']))
            print_("%s%s=%s" % (indent, 'storage', self.network_interfaces['storage']))
            print_("%s%s=%s" % (indent, 'jmx_port', self.jmx_port))
            print_("%s%s=%s" % (indent, 'remote_debug_port', self.remote_debug_port))
            print_("%s%s=%s" % (indent, 'initial_token', self.initial_token))
            if self.pid:
                print_("%s%s=%s" % (indent, 'pid', self.pid))

    def is_running(self):
        """
        Return true if the node is running
        """
        self.__update_status()
        return self.status == Status.UP or self.status == Status.DECOMMISIONNED

    def is_live(self):
        """
        Return true if the node is live (it's run and is not decommissionned).
        """
        self.__update_status()
        return self.status == Status.UP

    def logfilename(self):
        """
        Return the path to the current Cassandra log of this node.
        """
        return os.path.join(self.get_path(), 'logs', 'system.log')

    def grep_log(self, expr):
        """
        Returns a list of lines matching the regular expression in parameter
        in the Cassandra log of this node
        """
        matchings = []
        pattern = re.compile(expr)
        with open(self.logfilename()) as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    matchings.append((line, m))
        return matchings

    def mark_log(self):
        """
        Returns "a mark" to the current position of this node Cassandra log.
        This is for use with the from_mark parameter of watch_log_for_* methods,
        allowing to watch the log from the position when this method was called.
        """
        if not os.path.exists(self.logfilename()):
            return 0
        with open(self.logfilename()) as f:
            f.seek(0, os.SEEK_END)
            return f.tell()

    def print_process_output(self, name, proc, verbose=False):
        if verbose:
            for line in proc.stdout:
                print_("[%s] %s" % (name, line.rstrip('\n')))
        for line in proc.stderr:
            print_("[%s ERROR] %s" % (name, line.rstrip('\n')))


    # This will return when exprs are found or it timeouts
    def watch_log_for(self, exprs, from_mark=None, timeout=600, process=None, verbose=False):
        """
        Watch the log until one or more (regular) expression are found.
        This methods when all the expressions have been found or the method
        timeouts (a TimeoutError is then raised). On successful completion,
        a list of pair (line matched, match object) is returned.
        """
        elapsed = 0
        tofind = [exprs] if isinstance(exprs, string_types) else exprs
        tofind = [ re.compile(e) for e in tofind ]
        matchings = []
        reads = ""
        if len(tofind) == 0:
            return None

        while not os.path.exists(self.logfilename()):
            time.sleep(.5)
            if process:
                process.poll()
                if process.returncode is not None:
                    self.print_process_output(self.name, process, verbose)
                    if process.returncode != 0:
                        raise RuntimeError() # Shouldn't reuse RuntimeError but I'm lazy

        with open(self.logfilename()) as f:
            if from_mark:
                f.seek(from_mark)

            while True:
                # First, if we have a process to check, then check it.
                # Skip on Windows - stdout/stderr is cassandra.bat
                if not common.is_win():
                    if process:
                        process.poll()
                        if process.returncode is not None:
                            self.print_process_output(self.name, process, verbose)
                            if process.returncode != 0:
                                raise RuntimeError() # Shouldn't reuse RuntimeError but I'm lazy

                line = f.readline()
                if line:
                    reads = reads + line
                    for e in tofind:
                        m = e.search(line)
                        if m:
                            matchings.append((line, m))
                            tofind.remove(e)
                            if len(tofind) == 0:
                                return matchings[0] if isinstance(exprs, string_types) else matchings
                else:
                    # yep, it's ugly
                    time.sleep(1)
                    elapsed = elapsed + 1
                    if elapsed > timeout:
                        raise TimeoutError(time.strftime("%d %b %Y %H:%M:%S", time.gmtime()) + " [" + self.name + "] Missing: " + str([e.pattern for e in tofind]) + ":\n" + reads)

                if process:
                    process.poll()
                    if process.returncode is not None and process.returncode == 0:
                        return None

    def watch_log_for_death(self, nodes, from_mark=None, timeout=600):
        """
        Watch the log of this node until it detects that the provided other
        nodes are marked dead. This method returns nothing but throw a
        TimeoutError if all the requested node have not been found to be
        marked dead before timeout sec.
        A mark as returned by mark_log() can be used as the from_mark
        parameter to start watching the log from a given position. Otherwise
        the log is watched from the beginning.
        """
        tofind = nodes if isinstance(nodes, list) else [nodes]
        tofind = [ "%s is now [dead|DOWN]" % node.address() for node in tofind ]
        self.watch_log_for(tofind, from_mark=from_mark, timeout=timeout)

    def watch_log_for_alive(self, nodes, from_mark=None, timeout=120):
        """
        Watch the log of this node until it detects that the provided other
        nodes are marked UP. This method works similarily to watch_log_for_death.
        """
        tofind = nodes if isinstance(nodes, list) else [nodes]
        tofind = [ "%s.* now UP" % node.address() for node in tofind ]
        self.watch_log_for(tofind, from_mark=from_mark, timeout=timeout)

    def start(self,
              join_ring=True,
              no_wait=False,
              verbose=False,
              update_pid=True,
              wait_other_notice=False,
              replace_token=None,
              replace_address=None,
              jvm_args=[],
              wait_for_binary_proto=False,
              profile_options=None,
              use_jna=False):
        """
        Start the node. Options includes:
          - join_ring: if false, start the node with -Dcassandra.join_ring=False
          - no_wait: by default, this method returns when the node is started and listening to clients.
            If no_wait=True, the method returns sooner.
          - wait_other_notice: if True, this method returns only when all other live node of the cluster
            have marked this node UP.
          - replace_token: start the node with the -Dcassandra.replace_token option.
          - replace_address: start the node with the -Dcassandra.replace_address option.
        """
        if self.is_running():
            raise NodeError("%s is already running" % self.name)

        for itf in list(self.network_interfaces.values()):
            if itf is not None and replace_address is None:
                common.check_socket_available(itf)

        if wait_other_notice:
            marks = [ (node, node.mark_log()) for node in list(self.cluster.nodes.values()) if node.is_running() ]

        cdir = self.get_cassandra_dir()
        cass_bin = common.join_bin(cdir, 'bin', 'cassandra')

        # Copy back the cassandra scripts since profiling may have modified it the previous time
        shutil.copy(cass_bin, self.get_bin_dir())
        cass_bin = common.join_bin(self.get_path(), 'bin', 'cassandra')

        # If Windows, change entries in .bat file to split conf from binaries
        if common.is_win():
            self.__clean_bat()

        if profile_options is not None:
            config = common.get_config()
            if not 'yourkit_agent' in config:
                raise NodeError("Cannot enable profile. You need to set 'yourkit_agent' to the path of your agent in a ~/.ccm/config")
            cmd = '-agentpath:%s' % config['yourkit_agent']
            if 'options' in profile_options:
                cmd = cmd + '=' + profile_options['options']
            print_(cmd)
            # Yes, it's fragile as shit
            pattern=r'cassandra_parms="-Dlog4j.configuration=log4j-server.properties -Dlog4j.defaultInitOverride=true'
            common.replace_in_file(cass_bin, pattern, '    ' + pattern + ' ' + cmd + '"')

        os.chmod(cass_bin, os.stat(cass_bin).st_mode | stat.S_IEXEC)

        env = common.make_cassandra_env(cdir, self.get_path())
        pidfile = os.path.join(self.get_path(), 'cassandra.pid')
        args = [ cass_bin, '-p', pidfile, '-Dcassandra.join_ring=%s' % str(join_ring) ]
        if replace_token is not None:
            args.append('-Dcassandra.replace_token=%s' % str(replace_token))
        if replace_address is not None:
            args.append('-Dcassandra.replace_address=%s' % str(replace_address))
        if use_jna is False:
            args.append('-Dcassandra.boot_without_jna=true')
        args = args + jvm_args

        process = None
        if common.is_win():
            # clean up any old dirty_pid files from prior runs
            if (os.path.isfile(self.get_path() + "/dirty_pid.tmp")):
                os.remove(self.get_path() + "/dirty_pid.tmp")
            process = subprocess.Popen(args, cwd=self.get_bin_dir(), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            process = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Our modified batch file writes a dirty output with more than just the pid - clean it to get in parity
        # with *nix operation here.
        if common.is_win():
            self.__clean_win_pid()
            self._update_pid(process)
        elif update_pid:
            if no_wait:
                time.sleep(2) # waiting 2 seconds nevertheless to check for early errors and for the pid to be set
            else:
                for line in process.stdout:
                    if verbose:
                        print_(line.rstrip('\n'))

            self._update_pid(process)

            if not self.is_running():
                raise NodeError("Error starting node %s" % self.name, process)

        if wait_other_notice:
            for node, mark in marks:
                node.watch_log_for_alive(self, from_mark=mark)

        if wait_for_binary_proto:
            self.watch_log_for("Starting listening for CQL clients")
            # we're probably fine at that point but just wait some tiny bit more because
            # the msg is logged just before starting the binary protocol server
            time.sleep(0.2)

        return process

    def stop(self, wait=True, wait_other_notice=False, gently=True):
        """
        Stop the node.
          - wait: if True (the default), wait for the Cassandra process to be
            really dead. Otherwise return after having sent the kill signal.
          - wait_other_notice: return only when the other live nodes of the
            cluster have marked this node has dead.
          - gently: Let Cassandra clean up and shut down properly. Otherwise do
            a 'kill -9' which shuts down faster.
        """
        if self.is_running():
            if wait_other_notice:
                #tstamp = time.time()
                marks = [ (node, node.mark_log()) for node in list(self.cluster.nodes.values()) if node.is_running() and node is not self ]

            if common.is_win():
                # Gentle on Windows is relative.  WM_CLOSE is the best we get without external scripting
                if gently:
                    os.system("taskkill /PID " + str(self.pid))
                else:
                    os.system("taskkill /F /PID " + str(self.pid))

                # no graceful shutdown on windows means it should be immediate
                cmd = 'tasklist /fi "PID eq ' + str(self.pid) + '"'
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

                found = False
                for line in proc.stdout:
                    if re.match("Image", line):
                        found = True
                if found:
                    return False
                else:
                    return True
            else:
                if gently:
                    os.kill(self.pid, signal.SIGTERM)
                else:
                    os.kill(self.pid, signal.SIGKILL)

            if wait_other_notice:
                for node, mark in marks:
                    node.watch_log_for_death(self, from_mark=mark)
                    #print node.name, "has marked", self.name, "down in " + str(time.time() - tstamp) + "s"
            else:
                time.sleep(.1)

            still_running = self.is_running()
            if still_running and wait:
                wait_time_sec = 1
                for i in xrange(0, 7):
                    # we'll double the wait time each try and cassandra should
                    # not take more than 1 minute to shutdown
                    time.sleep(wait_time_sec)
                    if not self.is_running():
                        return True
                    wait_time_sec = wait_time_sec * 2
                raise NodeError("Problem stopping node %s" % self.name)
            else:
                return True
        else:
            return False

    def nodetool(self, cmd):
        cdir = self.get_cassandra_dir()
        nodetool = common.join_bin(cdir, 'bin', 'nodetool')
        env = common.make_cassandra_env(cdir, self.get_path())
        host = self.address()
        args = [ nodetool, '-h', host, '-p', str(self.jmx_port)]
        args += cmd.split()
        p = subprocess.Popen(args, env=env)
        p.wait()

    def scrub(self, options):
        cdir = self.get_cassandra_dir()
        scrub_bin = common.join_bin(cdir, 'bin', 'sstablescrub')
        env = common.make_cassandra_env(cdir, self.get_path())
        os.execve(scrub_bin, [ common.platform_binary('sstablescrub') ] + options, env)

    def run_cli(self, cmds=None, show_output=False, cli_options=[]):
        cdir = self.get_cassandra_dir()
        cli = common.join_bin(cdir, 'bin', 'cassandra-cli')
        env = common.make_cassandra_env(cdir, self.get_path())
        host = self.network_interfaces['thrift'][0]
        port = self.network_interfaces['thrift'][1]
        args = [ '-h', host, '-p', str(port) , '--jmxport', str(self.jmx_port) ] + cli_options
        sys.stdout.flush()
        if cmds is None:
            os.execve(cli, [ common.platform_binary('cassandra-cli') ] + args, env)
        else:
            p = subprocess.Popen([ cli ] + args, env=env, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            for cmd in cmds.split(';'):
                p.stdin.write(cmd + ';\n')
            p.stdin.write("quit;\n")
            p.wait()
            for err in p.stderr:
                print_("(EE) ", err, end='')
            if show_output:
                i = 0
                for log in p.stdout:
                    # first four lines are not interesting
                    if i >= 4:
                        print_(log, end='')
                    i = i + 1

    def run_cqlsh(self, cmds=None, show_output=False, cqlsh_options=[]):
        cdir = self.get_cassandra_dir()
        cli = common.join_bin(cdir, 'bin', 'cqlsh')
        env = common.make_cassandra_env(cdir, self.get_path())
        host = self.network_interfaces['thrift'][0]
        if self.cluster.version() >= "2.1":
            port = self.network_interfaces['binary'][1]
        else:
            port = self.network_interfaces['thrift'][1]
        args = cqlsh_options + [ host, str(port) ]
        sys.stdout.flush()
        if cmds is None:
            os.execve(cli, [ common.platform_binary('cqlsh') ] + args, env)
        else:
            p = subprocess.Popen([ cli ] + args, env=env, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            for cmd in cmds.split(';'):
                p.stdin.write(cmd + ';\n')
            p.stdin.write("quit;\n")
            p.wait()
            for err in p.stderr:
                print_("(EE) ", err, end='')
            if show_output:
                i = 0
                for log in p.stdout:
                    # first four lines are not interesting
                    if i >= 4:
                        print_(log, end='')
                    i = i + 1

    def cli(self):
        cdir = self.get_cassandra_dir()
        cli = common.join_bin(cdir, 'bin', 'cassandra-cli')
        env = common.make_cassandra_env(cdir, self.get_path())
        host = self.network_interfaces['thrift'][0]
        port = self.network_interfaces['thrift'][1]
        args = [ '-h', host, '-p', str(port) , '--jmxport', str(self.jmx_port) ]
        return CliSession(subprocess.Popen([ cli ] + args, env=env, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE))

    def set_log_level(self, new_level, class_name=None):
        known_level = [ 'TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR' ]
        if new_level not in known_level:
            raise common.ArgumentError("Unknown log level %s (use one of %s)" % (new_level, " ".join(known_level)))

        if class_name:
            self.__classes_log_level[class_name] = new_level
        else:
            self.__global_log_level = new_level
        version = self.cluster.version()
        #loggers changed > 2.1
        if float(version[:version.index('.')+2]) < 2.1:
            self.__update_log4j()
        else:
            self.__update_logback()
        return self

    #
    # Update log4j config: copy new log4j-server.properties into
    # ~/.ccm/name-of-cluster/nodeX/conf/log4j-server.properties
    #
    def update_log4j(self, new_log4j_config):
        cassandra_conf_dir = os.path.join(self.get_conf_dir(),
                                           'log4j-server.properties')
        common.copy_file(new_log4j_config, cassandra_conf_dir)

    #
    # Update logback config: copy new logback.xml into
    # ~/.ccm/name-of-cluster/nodeX/conf/logback.xml
    #
    def update_logback(self, new_logback_config):
        cassandra_conf_dir = os.path.join(self.get_conf_dir(),
                                           'logback.xml')
        common.copy_file(new_logback_config, cassandra_conf_dir)

    def clear(self, clear_all = False, only_data = False):
        data_dirs = [ 'data' ]
        if not only_data:
            data_dirs.append("commitlogs")
            if clear_all:
                data_dirs.extend(['saved_caches', 'logs'])
        for d in data_dirs:
            full_dir = os.path.join(self.get_path(), d)
            if only_data:
                for dir in os.listdir(full_dir):
                    keyspace_dir = os.path.join(full_dir, dir)
                    if os.path.isdir(keyspace_dir) and dir != "system":
                        for f in os.listdir(keyspace_dir):
                            full_path = os.path.join(keyspace_dir, f)
                            if os.path.isfile(full_path):
                                os.remove(full_path)
            else:
                shutil.rmtree(full_dir)
                os.mkdir(full_dir)

    def run_sstable2json(self, keyspace=None, datafile=None, column_families=None, enumerate_keys=False):
        cdir = self.get_cassandra_dir()
        sstable2json = common.join_bin(cdir, 'bin', 'sstable2json')
        env = common.make_cassandra_env(cdir, self.get_path())
        datafiles = self.__gather_sstables(datafile,keyspace,column_families)

        for file in datafiles:
            print_("-- {0} -----".format(os.path.basename(file)))
            args = [ sstable2json , file ]
            if enumerate_keys:
                args = args + ["-e"]
            subprocess.call(args, env=env)
            print_("")

    def run_sstablesplit(self, datafile=None,  size=None, keyspace=None, column_families=None):
        cdir = self.get_cassandra_dir()
        sstablesplit = common.join_bin(cdir, 'bin', 'sstablesplit')
        env = common.make_cassandra_env(cdir, self.get_path())
        datafiles = self.__gather_sstables(datafile, keyspace, column_families)

        def do_split(f):
            print_("-- {0}-----".format(os.path.basename(f)))
            if size is not None:
                subprocess.call( [sstablesplit, '-s', str(size), f], cwd=os.path.join(cdir, 'bin'), env=env )
            else:
                subprocess.call( [sstablesplit, f], cwd=os.path.join(cdir, 'bin'), env=env )

        for datafile in datafiles:
            do_split(datafile)

    def list_keyspaces(self):
        keyspaces = os.listdir(os.path.join(self.get_path(), 'data'))
        keyspaces.remove('system')
        return keyspaces

    def get_sstables(self, keyspace, column_family):
        keyspace_dir = os.path.join(self.get_path(), 'data', keyspace)
        if not os.path.exists(keyspace_dir):
            raise common.ArgumentError("Unknown keyspace {0}".format(keyspace))

        version = self.cluster.version()
        # data directory layout is changed from 1.1
        if float(version[:version.index('.')+2]) < 1.1:
            files = glob.glob(os.path.join(keyspace_dir, "{0}*-Data.db".format(column_family)))
        else:
            files = glob.glob(os.path.join(keyspace_dir, column_family or "*", "%s-%s*-Data.db" % (keyspace, column_family)))
        for f in files:
            if os.path.exists(f.replace('Data.db', 'Compacted')):
                files.remove(f)
        return files

    def stress(self, stress_options):
        stress = common.get_stress_bin(self.get_cassandra_dir())
        args = [ stress ] + stress_options
        try:
            subprocess.call(args, cwd=common.parse_path(stress))
        except KeyboardInterrupt:
            pass

    def shuffle(self, cmd):
        cdir = self.get_cassandra_dir()
        shuffle = common.join_bin(cdir, 'bin', 'cassandra-shuffle')
        host = self.address()
        args = [ shuffle, '-h', host, '-p', str(self.jmx_port) ] + [ cmd ]
        try:
            subprocess.call(args)
        except KeyboardInterrupt:
            pass

    def data_size(self, live_data=True):
        size = 0
        if live_data:
            for ks in self.list_keyspaces():
                size += sum((os.path.getsize(path) for path in self.get_sstables(ks, "")))
        else:
            for ks in self.list_keyspaces():
                for root, dirs, files in os.walk(os.path.join(self.get_path(), 'data', ks)):
                    size += sum((os.path.getsize(os.path.join(root, f)) for f in files if os.path.isfile(os.path.join(root, f))))
        return size

    def flush(self):
        self.nodetool("flush")

    def compact(self):
        self.nodetool("compact")

    def drain(self):
        self.nodetool("drain")

    def repair(self):
        self.nodetool("repair")

    def move(self, new_token):
        self.nodetool("move " + str(new_token))

    def cleanup(self):
        self.nodetool("cleanup")

    def version(self):
        self.nodetool("version");

    def decommission(self):
        self.nodetool("decommission")
        self.status = Status.DECOMMISIONNED
        self.__update_config()

    def removeToken(self, token):
        self.nodetool("removeToken " + str(token))

    def import_config_files(self):
        self.__update_config()

        conf_dir = os.path.join(self.get_cassandra_dir(), 'conf')
        for name in os.listdir(conf_dir):
            filename = os.path.join(conf_dir, name)
            if os.path.isfile(filename):
                shutil.copy(filename, self.get_conf_dir())

        self.__update_yaml()
        version = self.cluster.version()
        #loggers changed > 2.1
        if float(version[:version.index('.')+2]) < 2.1:
            self.__update_log4j()
        else:
            self.__update_logback()
        self.__update_envfile()

    def import_bin_files(self):
        bin_dir = os.path.join(self.get_cassandra_dir(), 'bin')
        for name in os.listdir(bin_dir):
            filename = os.path.join(bin_dir, name)
            if os.path.isfile(filename):
                shutil.copy(filename, self.get_bin_dir())
                common.add_exec_permission(bin_dir, name)

    def __clean_bat(self):
        # While the Windows specific changes to the batch files to get them to run are
        # fairly extensive and thus pretty brittle, all the changes are very unique to
        # the needs of ccm and shouldn't be pushed into the main repo.

        # Change the nodes to separate jmx ports
        bin_dir = os.path.join(self.get_path(), 'bin')
        jmx_port_pattern="-Dcom.sun.management.jmxremote.port="
        bat_file = os.path.join(bin_dir, "cassandra.bat");
        common.replace_in_file(bat_file, jmx_port_pattern, " " + jmx_port_pattern + self.jmx_port + "^")

        # Split binaries from conf
        home_pattern="if NOT DEFINED CASSANDRA_HOME set CASSANDRA_HOME=%CD%"
        common.replace_in_file(bat_file, home_pattern, "set CASSANDRA_HOME=" + self.get_cassandra_dir())

        classpath_pattern="set CLASSPATH=\\\"%CASSANDRA_HOME%\\\\conf\\\""
        common.replace_in_file(bat_file, classpath_pattern, "set CLASSPATH=\"" + self.get_conf_dir() + "\"")

        # background the server process and grab the pid
        run_text="\"%JAVA_HOME%\\bin\\java\" %JAVA_OPTS% %CASSANDRA_PARAMS% -cp %CASSANDRA_CLASSPATH% \"%CASSANDRA_MAIN%\""
        run_pattern=".*-cp.*"
        common.replace_in_file(bat_file, run_pattern, "wmic process call create '" + run_text + "' > \"" + self.get_path() + "/dirty_pid.tmp\"\n")

    def _save(self):
        self.__update_yaml()
        version = self.cluster.version()
        #loggers changed > 2.1
        if float(version[:version.index('.')+2]) < 2.1:
            self.__update_log4j()
        else:
            self.__update_logback()
        self.__update_envfile()

    def __update_config(self):
        dir_name = self.get_path()
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
            for dir in self.__get_diretories():
                os.mkdir(os.path.join(dir_name, dir))

        filename = os.path.join(dir_name, 'node.conf')
        values = {
            'name' : self.name,
            'status' : self.status,
            'auto_bootstrap' : self.auto_bootstrap,
            'interfaces' : self.network_interfaces,
            'jmx_port' : self.jmx_port,
            'config_options' : self.__config_options,
        }
        if self.pid:
            values['pid'] = self.pid
        if self.initial_token:
            values['initial_token'] = self.initial_token
        if self.__cassandra_dir is not None:
            values['cassandra_dir'] = self.__cassandra_dir
        if self.data_center:
            values['data_center'] = self.data_center
        if self.remote_debug_port:
            values['remote_debug_port'] = self.remote_debug_port
        with open(filename, 'w') as f:
            yaml.safe_dump(values, f)

    def __update_yaml(self):
        conf_file = os.path.join(self.get_conf_dir(), common.CASSANDRA_CONF)
        with open(conf_file, 'r') as f:
            data = yaml.load(f)

        data['cluster_name'] = self.cluster.name
        data['auto_bootstrap'] = self.auto_bootstrap
        data['initial_token'] = self.initial_token
        if 'seeds' in data:
            # cassandra 0.7
            data['seeds'] = self.cluster.get_seeds()
        else:
            # cassandra 0.8
            data['seed_provider'][0]['parameters'][0]['seeds'] = ','.join(self.cluster.get_seeds())
        data['listen_address'], data['storage_port'] = self.network_interfaces['storage']
        data['rpc_address'], data['rpc_port'] = self.network_interfaces['thrift']
        if self.network_interfaces['binary'] is not None and self.cluster.version() >= "1.2":
            _, data['native_transport_port'] = self.network_interfaces['binary']

        data['data_file_directories'] = [ os.path.join(self.get_path(), 'data') ]
        data['commitlog_directory'] = os.path.join(self.get_path(), 'commitlogs')
        data['saved_caches_directory'] = os.path.join(self.get_path(), 'saved_caches')

        if self.cluster.partitioner:
            data['partitioner'] = self.cluster.partitioner

        full_options = dict(list(self.cluster._config_options.items()) + list(self.__config_options.items())) # last win and we want node options to win
        for name in full_options:
            value = full_options[name]
            if value is None:
                try:
                    del data[name]
                except KeyError:
                    # it is fine to remove a key not there:w
                    pass
            else:
                data[name] = full_options[name]

        with open(conf_file, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)

    def __update_log4j(self):
        append_pattern='log4j.appender.R.File='
        conf_file = os.path.join(self.get_conf_dir(), common.LOG4J_CONF)
        log_file = os.path.join(self.get_path(), 'logs', 'system.log')
        # log4j isn't partial to Windows \.  I can't imagine why not.
        if common.is_win():
            log_file = re.sub("\\\\", "/", log_file)
        common.replace_in_file(conf_file, append_pattern, append_pattern + log_file)

        # Setting the right log level

        # Replace the global log level
        if self.__global_log_level is not None:
            append_pattern='log4j.rootLogger='
            common.replace_in_file(conf_file, append_pattern, append_pattern + self.__global_log_level + ',stdout,R')

        # Class specific log levels
        for class_name in self.__classes_log_level:
            logger_pattern='log4j.logger'
            full_logger_pattern = logger_pattern + '.' + class_name + '='
            common.replace_or_add_into_file_tail(conf_file, full_logger_pattern, full_logger_pattern + self.__classes_log_level[class_name])

    def __update_logback(self):
        append_pattern='<file>.*</file>'
        conf_file = os.path.join(self.get_conf_dir(), common.LOGBACK_CONF)
        log_file = os.path.join(self.get_path(), 'logs', 'system.log')
        common.replace_in_file(conf_file, append_pattern, '<file>' + log_file + '</file>')

        append_pattern='<fileNamePattern>.*</fileNamePattern>'
        common.replace_in_file(conf_file, append_pattern, '<fileNamePattern>' + log_file + '.%i.zip</fileNamePattern>')

        # Setting the right log level

        # Replace the global log level
        if self.__global_log_level is not None:
            append_pattern='<root level=".*">'
            common.replace_in_file(conf_file, append_pattern, '<root level="' + self.__global_log_level + '">')

        # Class specific log levels
        for class_name in self.__classes_log_level:
            logger_pattern='\t<logger name="'
            full_logger_pattern = logger_pattern + class_name + '" level=".*"/>'
            common.replace_or_add_into_file_tail(conf_file, full_logger_pattern, logger_pattern + class_name + '" level="' + self.__classes_log_level[class_name] + '"/>')

    def __update_envfile(self):
        jmx_port_pattern='JMX_PORT='
        remote_debug_port_pattern='-Xrunjdwp:transport=dt_socket,server=y,suspend=n,address='
        conf_file = os.path.join(self.get_conf_dir(), common.CASSANDRA_ENV)
        common.replace_in_file(conf_file, jmx_port_pattern, jmx_port_pattern + self.jmx_port)
        if self.remote_debug_port != '0':
            common.replace_in_file(conf_file, remote_debug_port_pattern, 'JVM_OPTS="$JVM_OPTS -Xdebug -Xnoagent -Xrunjdwp:transport=dt_socket,server=y,suspend=n,address=' + str(self.remote_debug_port) + '"')

        if self.cluster.version() < '2.0.1':
            common.replace_in_file(conf_file, "-Xss", '    JVM_OPTS="$JVM_OPTS -Xss228k"')

    def __update_status(self):
        if self.pid is None:
            if self.status == Status.UP or self.status == Status.DECOMMISIONNED:
                self.status = Status.DOWN
            return

        old_status = self.status

        # os.kill on windows doesn't allow us to ping a process
        if common.is_win():
            self.__update_status_win()
        else:
            try:
                os.kill(self.pid, 0)
            except OSError as err:
                if err.errno == errno.ESRCH:
                    # not running
                    if self.status == Status.UP or self.status == Status.DECOMMISIONNED:
                        self.status = Status.DOWN
                elif err.errno == errno.EPERM:
                    # no permission to signal this process
                    if self.status == Status.UP or self.status == Status.DECOMMISIONNED:
                        self.status = Status.DOWN
                else:
                    # some other error
                    raise err
            else:
                if self.status == Status.DOWN or self.status == Status.UNINITIALIZED:
                    self.status = Status.UP

        if not old_status == self.status:
            if old_status == Status.UP and self.status == Status.DOWN:
                self.pid = None
            self.__update_config()

    def __update_status_win(self):
        cmd = 'tasklist /fi "PID eq ' + str(self.pid) + '"'
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

        found = False
        for line in proc.stdout:
            if re.match("Image", line):
                found = True
        if not found:
            self.status = Status.DOWN
        else:
            if self.status == Status.DOWN or self.status == Status.UNINITIALIZED:
                self.status = Status.UP

    def __get_diretories(self):
        dirs = {}
        for i in ['data', 'commitlogs', 'saved_caches', 'logs', 'conf', 'bin']:
            dirs[i] = os.path.join(self.get_path(), i)
        return dirs

    def __get_status_string(self):
        if self.status == Status.UNINITIALIZED:
            return "%s (%s)" % (Status.DOWN, "Not initialized")
        else:
            return self.status

    def __clean_win_pid(self):
        start = common.now_ms()
        try:
            # Spin for 500ms waiting for .bat to write the dirty_pid file
            while (not os.path.isfile(self.get_path() + "/dirty_pid.tmp")):
                now = common.now_ms()
                if (now - start > 500):
                    raise Exception('Timed out waiting for dirty_pid file.')
                else:
                    time.sleep(.001)

            with open(self.get_path() + "/dirty_pid.tmp", 'r') as f:
                found = False
                process_regex = re.compile('ProcessId')

                readStart = common.now_ms()
                readEnd = common.now_ms()
                while (found == False and readEnd - readStart < 500):
                    line = f.read()
                    if (line):
                        m = process_regex.search(line)
                        if (m):
                            found = True
                            linesub = line.split('=')
                            pidchunk = linesub[1].split(';')
                            win_pid = pidchunk[0].lstrip()
                            with open (self.get_path() + "/cassandra.pid", 'w') as pidfile:
                                found = True
                                pidfile.write(win_pid)
                        readEnd = common.now_ms()
                    else:
                        time.sleep(.001)
                if not found:
                    raise Exception('Node: %s  Failed to find pid in ' +
                                    self.get_path() +
                                    '/dirty_pid.tmp. Manually kill it and check logs - ccm will be out of sync.')
        except Exception as e:
            print_("ERROR: Problem starting " + self.name + " (" + str(e) + ")")
            raise Exception('Error while parsing <node>/dirty_pid.tmp in path: ' + self.get_path())

    def _update_pid(self, process):
        pidfile = os.path.join(self.get_path(), 'cassandra.pid')
        try:
            with open(pidfile, 'r') as f:
                self.pid = int(f.readline().strip())
        except IOError:
            raise NodeError('Problem starting node %s' % self.name, process)
        self.__update_status()

    def __gather_sstables(self, datafile=None, keyspace=None, columnfamilies=None):
        datafiles = []
        if keyspace is None:
            for k in self.list_keyspaces():
                datafiles = datafiles + self.get_sstables(k, "")
        elif datafile is None:
            if columnfamilies is None:
                datafiles = datafiles + self.get_sstables(keyspace, "")
            else:
                for cf in columnfamilies:
                    datafiles = datafiles + self.get_sstables(keyspace, cf)
        else:
            keyspace_dir = os.path.join(self.get_path(), 'data', keyspace)
            datafiles = [ os.path.join(keyspace_dir, datafile) ]

        return datafiles

########NEW FILE########
__FILENAME__ = repository
# downloaded sources handling
from __future__ import with_statement

from six import print_
from six.moves import urllib

import os
import shutil
import subprocess
import stat
import sys
import tarfile
import tempfile
import time

from ccmlib.common import (ArgumentError, CCMError, get_default_path,
                           platform_binary, validate_cassandra_dir)

ARCHIVE="http://archive.apache.org/dist/cassandra"
GIT_REPO="http://git-wip-us.apache.org/repos/asf/cassandra.git"

def setup(version, verbose=False):
    if version.startswith('git:'):
        clone_development(version, verbose=verbose)
        return (version_directory(version), None)
    else:
        cdir = version_directory(version)
        if cdir is None:
            download_version(version, verbose=verbose)
            cdir = version_directory(version)
        return (cdir, version)

def validate(path):
    if path.startswith(__get_dir()):
        _, version = os.path.split(os.path.normpath(path))
        setup(version)

def clone_development(version, verbose=False):
    local_git_cache = os.path.join(__get_dir(), '_git_cache')
    target_dir = os.path.join(__get_dir(), version.replace(':', '_')) # handle git branches like 'git:trunk'.
    git_branch = version[4:] # the part of the version after the 'git:'
    logfile = os.path.join(__get_dir(), "last.log")
    with open(logfile, 'w') as lf:
        try:
            #Checkout/fetch a local repository cache to reduce the number of
            #remote fetches we need to perform:
            if not os.path.exists(local_git_cache):
                if verbose:
                    print_("Cloning Cassandra...")
                out = subprocess.call(
                    ['git', 'clone', '--mirror', GIT_REPO, local_git_cache],
                    cwd=__get_dir(), stdout=lf, stderr=lf)
                assert out == 0, "Could not do a git clone"
            else:
                if verbose:
                    print_("Fetching Cassandra updates...")
                out = subprocess.call(
                    ['git', 'fetch', '-fup', 'origin', '+refs/*:refs/*'],
                    cwd=local_git_cache, stdout=lf, stderr=lf)

            #Checkout the version we want from the local cache:
            if not os.path.exists(target_dir):
                # development branch doesn't exist. Check it out.
                if verbose:
                    print_("Cloning Cassandra (from local cache)")

                # git on cygwin appears to be adding `cwd` to the commands which is breaking clone
                if sys.platform == "cygwin":
                    local_split = local_git_cache.split(os.sep)
                    target_split = target_dir.split(os.sep)
                    subprocess.call(['git', 'clone', local_split[-1], target_split[-1]], cwd=__get_dir(), stdout=lf, stderr=lf)
                else:
                    subprocess.call(['git', 'clone', local_git_cache, target_dir], cwd=__get_dir(), stdout=lf, stderr=lf)

                # now check out the right version
                if verbose:
                    print_("Checking out requested branch (%s)" % git_branch)
                out = subprocess.call(['git', 'checkout', git_branch], cwd=target_dir, stdout=lf, stderr=lf)
                if int(out) != 0:
                    raise CCMError("Could not check out git branch %s. Is this a valid branch name? (see last.log for details)" % git_branch)
                # now compile
                compile_version(git_branch, target_dir, verbose)
            else: # branch is already checked out. See if it is behind and recompile if needed.
                out = subprocess.call(['git', 'fetch', 'origin'], cwd=target_dir, stdout=lf, stderr=lf)
                assert out == 0, "Could not do a git fetch"
                status = subprocess.Popen(['git', 'status', '-sb'], cwd=target_dir, stdout=subprocess.PIPE, stderr=lf).communicate()[0]
                if status.find('[behind') > -1:
                    if verbose:
                        print_("Branch is behind, recompiling")
                    out = subprocess.call(['git', 'pull'], cwd=target_dir, stdout=lf, stderr=lf)
                    assert out == 0, "Could not do a git pull"
                    out = subprocess.call([platform_binary('ant'), 'realclean'], cwd=target_dir, stdout=lf, stderr=lf)
                    assert out == 0, "Could not run 'ant realclean'"

                    # now compile
                    compile_version(git_branch, target_dir, verbose)
        except:
            # wipe out the directory if anything goes wrong. Otherwise we will assume it has been compiled the next time it runs.
            try:
                shutil.rmtree(target_dir)
            except: pass
            raise


def download_version(version, url=None, verbose=False):
    u = "%s/%s/apache-cassandra-%s-src.tar.gz" % (ARCHIVE, version.split('-')[0], version) if url is None else url
    _, target = tempfile.mkstemp(suffix=".tar.gz", prefix="ccm-")
    try:
        __download(u, target, show_progress=verbose)
        if verbose:
            print_("Extracting %s as version %s ..." % (target, version))
        tar = tarfile.open(target)
        dir = tar.next().name.split("/")[0]
        tar.extractall(path=__get_dir())
        tar.close()
        target_dir = os.path.join(__get_dir(), version)
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        shutil.move(os.path.join(__get_dir(), dir), target_dir)

        compile_version(version, target_dir, verbose=verbose)

    except urllib.error.URLError as e:
        msg = "Invalid version %s" % version if url is None else "Invalid url %s" % url
        msg = msg + " (underlying error is: %s)" % str(e)
        raise ArgumentError(msg)
    except tarfile.ReadError as e:
        raise ArgumentError("Unable to uncompress downloaded file: %s" % str(e))

def compile_version(version, target_dir, verbose=False):
    # compiling cassandra and the stress tool
    logfile = os.path.join(__get_dir(), "last.log")
    if verbose:
        print_("Compiling Cassandra %s ..." % version)
    with open(logfile, 'w') as lf:
        lf.write("--- Cassandra build -------------------\n")
        try:
            # Patch for pending Cassandra issue: https://issues.apache.org/jira/browse/CASSANDRA-5543
            # Similar patch seen with buildbot
            attempt = 0
            ret_val = 1
            while attempt < 3 and ret_val is not 0:
                if attempt > 0:
                    lf.write("\n\n`ant jar` failed. Retry #%s...\n\n" % attempt)
                ret_val = subprocess.call([platform_binary('ant'),'jar'], cwd=target_dir, stdout=lf, stderr=lf)
                attempt += 1
            if ret_val is not 0:
                raise CCMError("Error compiling Cassandra. See %s for details" % logfile)
        except OSError as e:
            raise CCMError("Error compiling Cassandra. Is ant installed? See %s for details" % logfile)

        lf.write("\n\n--- cassandra/stress build ------------\n")
        stress_dir = os.path.join(target_dir, "tools", "stress") if (
                version >= "0.8.0") else \
                os.path.join(target_dir, "contrib", "stress")

        build_xml = os.path.join(stress_dir, 'build.xml')
        if os.path.exists(build_xml): # building stress separately is only necessary pre-1.1
            try:
                # set permissions correctly, seems to not always be the case
                stress_bin_dir = os.path.join(stress_dir, 'bin')
                for f in os.listdir(stress_bin_dir):
                    full_path = os.path.join(stress_bin_dir, f)
                    os.chmod(full_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

                if subprocess.call([platform_binary('ant'), 'build'], cwd=stress_dir, stdout=lf, stderr=lf) is not 0:
                    if subprocess.call([platform_binary('ant'), 'stress-build'], cwd=target_dir, stdout=lf, stderr=lf) is not 0:
                        raise CCMError("Error compiling Cassandra stress tool.  "
                                "See %s for details (you will still be able to use ccm "
                                "but not the stress related commands)" % logfile)
            except IOError as e:
                raise CCMError("Error compiling Cassandra stress tool: %s (you will "
                "still be able to use ccm but not the stress related commands)" % str(e))

def version_directory(version):
    version = version.replace(':', '_') # handle git branches like 'git:trunk'.
    dir = os.path.join(__get_dir(), version)
    if os.path.exists(dir):
        try:
            validate_cassandra_dir(dir)
            return dir
        except ArgumentError as e:
            shutil.rmtree(dir)
            return None
    else:
        return None

def clean_all():
    shutil.rmtree(__get_dir())

def __download(url, target, show_progress=False):
    u = urllib.request.urlopen(url)
    f = open(target, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    if show_progress:
        print_("Downloading %s to %s (%.3fMB)" % (url, target, float(file_size) / (1024 * 1024)))

    file_size_dl = 0
    block_sz = 8192
    status = None
    attempts = 0
    while file_size_dl < file_size:
        buffer = u.read(block_sz)
        if not buffer:
            attempts = attempts + 1
            if attempts >= 5:
                raise CCMError("Error downloading file (nothing read after %i attempts, downloded only %i of %i bytes)" % (attempts, file_size_dl, file_size))
            time.sleep(0.5 * attempts)
            continue;
        else:
            attempts = 0

        file_size_dl += len(buffer)
        f.write(buffer)
        if show_progress:
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = chr(8)*(len(status)+1) + status
            print_(status, end='')

    if show_progress:
        print_("")
    f.close()
    u.close()

def __get_dir():
    repo = os.path.join(get_default_path(), 'repository')
    if not os.path.exists(repo):
        os.mkdir(repo)
    return repo

########NEW FILE########
__FILENAME__ = test_lib
import sys
sys.path = [".."] + sys.path

from . import TEST_DIR
from ccmlib.cluster import Cluster

CLUSTER_PATH = TEST_DIR


def test1():
    cluster = Cluster(CLUSTER_PATH, "test1", cassandra_version='2.0.3')
    cluster.show(False)
    cluster.populate(2)
    cluster.set_partitioner("Murmur3")
    cluster.start()
    cluster.set_configuration_options(None, None)
    cluster.set_configuration_options({}, True)
    cluster.set_configuration_options({"a": "b"}, False)

    [node1, node2] = cluster.nodelist()
    node2.compact()
    cluster.flush()
    cluster.remove()
    cluster.stop()


def test2():
    cluster = Cluster(CLUSTER_PATH, "test2", cassandra_version='2.0.3')
    cluster.populate(2)
    cluster.start()

    cluster.set_log_level("ERROR")

    class FakeNode:
        name = "non-existing node"

    cluster.remove(FakeNode())
    [node1, node2] = cluster.nodelist()
    cluster.remove(node1)
    cluster.show(True)
    cluster.show(False)

    #cluster.stress([])
    cluster.compact()
    cluster.drain()
    cluster.stop()


def test3():
    cluster = Cluster(CLUSTER_PATH, "test3", cassandra_version='2.0.3')
    cluster.populate(2)
    cluster.start()
    cluster.cleanup()

    cluster.clear()
    cluster.stop()

########NEW FILE########
