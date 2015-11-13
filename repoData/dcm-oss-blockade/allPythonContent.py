__FILENAME__ = cli
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import sys
import argparse
import traceback
import errno
import json

import yaml
from clint.textui import puts, puts_err, colored, columns

from .errors import BlockadeError
from .core import Blockade
from .state import BlockadeStateFactory
from .config import BlockadeConfig
from .net import BlockadeNetwork


def load_config(opts):
    error = None
    paths = (opts.config,) if opts.config else ("blockade.yaml",
                                                "blockade.yml")
    try:
        for path in paths:
            try:
                with open(path) as f:
                    d = yaml.safe_load(f)
                    return BlockadeConfig.from_dict(d)
            except IOError as e:
                if e.errno != errno.ENOENT:
                    raise
    except Exception as e:
        error = e
    raise BlockadeError("Failed to load config (from --config, "
                        "./blockade.yaml, or ./blockade.yml)" +
                        (str(error) if error else ""))


def get_blockade(config):
    return Blockade(config, BlockadeStateFactory, BlockadeNetwork(config))


def print_containers(containers, to_json=False):
    containers = sorted(containers, key=lambda c: c.name)

    if to_json:
        d = [c.to_dict() for c in containers]
        puts(json.dumps(d, indent=2, sort_keys=True, separators=(',', ': ')))

    else:
        puts(colored.blue(columns(["NODE",               15],
                                  ["CONTAINER ID",       15],
                                  ["STATUS",              7],
                                  ["IP",                 15],
                                  ["NETWORK",            10],
                                  ["PARTITION",          10])))
        for container in containers:
            partition = container.partition
            partition = "" if partition is None else str(partition)
            puts(columns([container.name,                15],
                         [container.container_id[:12],   15],
                         [container.state,                7],
                         [container.ip_address or "",    15],
                         [container.network_state,       10],
                         [partition,                     10]))


def _add_output_options(parser):
    parser.add_argument('--json', action='store_true',
                        help='Output in JSON format')


def _add_container_selection_options(parser):
    parser.add_argument('containers', metavar='CONTAINER', nargs='*',
                        help='Container to select')
    parser.add_argument('--all', action='store_true',
                        help='Select all containers')


def _check_container_selections(opts):
    if opts.containers and opts.all:
        raise BlockadeError("Either specify individual containers "
                            "or --all, but not both")
    elif not (opts.containers or opts.all):
        raise BlockadeError("Specify individual containers or --all")

    return (opts.containers or None, opts.all)


def cmd_up(opts):
    """Start the containers and link them together
    """
    config = load_config(opts)
    b = get_blockade(config)
    containers = b.create()
    print_containers(containers, opts.json)


def cmd_destroy(opts):
    """Destroy all containers and restore networks
    """
    config = load_config(opts)
    b = get_blockade(config)
    b.destroy()


def cmd_status(opts):
    """Print status of containers and networks
    """
    config = load_config(opts)
    b = get_blockade(config)
    containers = b.status()
    print_containers(containers, opts.json)


def cmd_flaky(opts):
    """Make the network flaky for some or all containers
    """
    containers, select_all = _check_container_selections(opts)
    config = load_config(opts)
    b = get_blockade(config)
    b.flaky(containers, select_all)


def cmd_slow(opts):
    """Make the network slow for some or all containers
    """
    containers, select_all = _check_container_selections(opts)
    config = load_config(opts)
    b = get_blockade(config)
    b.slow(containers, select_all)


def cmd_fast(opts):
    """Restore network speed and reliability for some or all containers
    """
    containers, select_all = _check_container_selections(opts)
    config = load_config(opts)
    b = get_blockade(config)
    b.fast(containers, select_all)


def cmd_partition(opts):
    """Partition the network between containers

    Replaces any existing partitions outright. Any containers NOT specified
    in arguments will be globbed into a single implicit partition. For
    example if you have three containers: c1, c2, and c3 and you run:

        blockade partition c1

    The result will be a partition with just c1 and another partition with
    c2 and c3.
    """
    partitions = []
    for partition in opts.partitions:
        names = []
        for name in partition.split(","):
            name = name.strip()
            if name:
                names.append(name)
        partitions.append(names)
    config = load_config(opts)
    b = get_blockade(config)
    b.partition(partitions)


def cmd_join(opts):
    """Restore full networking between containers
    """
    config = load_config(opts)
    b = get_blockade(config)
    b.join()


def cmd_logs(opts):
    """Fetch the logs of a container
    """
    config = load_config(opts)
    b = get_blockade(config)
    puts(b.logs(opts.container))


_CMDS = (("up", cmd_up), ("destroy", cmd_destroy), ("status", cmd_status),
         ("logs", cmd_logs), ("flaky", cmd_flaky), ("slow", cmd_slow),
         ("fast", cmd_fast), ("partition", cmd_partition), ("join", cmd_join))


def setup_parser():
    parser = argparse.ArgumentParser(description='Blockade')
    parser.add_argument("--config", "-c", metavar="blockade.yaml",
                        help="Config YAML. Looks in CWD if not specified.")

    subparsers = parser.add_subparsers(title="commands")

    command_parsers = {}
    for command, func in _CMDS:
        subparser = subparsers.add_parser(
            command,
            description=func.__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=func)
        command_parsers[command] = subparser

    # add additional parameters to some commands
    _add_output_options(command_parsers["up"])
    _add_output_options(command_parsers["status"])
    _add_container_selection_options(command_parsers["flaky"])
    _add_container_selection_options(command_parsers["slow"])
    _add_container_selection_options(command_parsers["fast"])

    command_parsers["logs"].add_argument("container", metavar='CONTAINER',
                                         help="Container to fetch logs for")
    command_parsers["partition"].add_argument(
        'partitions', nargs='+', metavar='PARTITION',
        help='Comma-separated partition')

    return parser


def main(args=None):
    parser = setup_parser()
    opts = parser.parse_args(args=args)

    rc = 0

    try:
        opts.func(opts)
    except BlockadeError as e:
        puts_err(colored.red("\nError:\n") + str(e) + "\n")
        rc = 1

    except KeyboardInterrupt:
        puts_err(colored.red("Caught Ctrl-C. exiting!"))

    except:
        puts_err(
            colored.red("\nUnexpected error! This may be a Blockade bug.\n"))
        traceback.print_exc()
        rc = 2

    sys.exit(rc)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = config
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import collections

from .errors import BlockadeConfigError


class BlockadeContainerConfig(object):
    @staticmethod
    def from_dict(name, d):
        return BlockadeContainerConfig(
            name, d['image'],
            command=d.get('command'), links=d.get('links'),
            lxc_conf=d.get('lxc_conf'), volumes=d.get('volumes'),
            ports=d.get('ports'), environment=d.get('environment'))

    def __init__(self, name, image, command=None, links=None, lxc_conf=None,
                 volumes=None, ports=None, environment=None):
        self.name = name
        self.image = image
        self.command = command
        self.links = _dictify(links, "links")
        self.lxc_conf = dict(lxc_conf or {})
        self.volumes = _dictify(volumes, "volumes")
        self.ports = _dictify(ports, "ports")
        self.environment = dict(environment or {})


_DEFAULT_NETWORK_CONFIG = {
    "flaky": "30%",
    "slow": "75ms 100ms distribution normal",
}


class BlockadeConfig(object):
    @staticmethod
    def from_dict(d):
        try:
            containers = d['containers']
            parsed_containers = {}
            for name, container_dict in containers.items():
                try:
                    container = BlockadeContainerConfig.from_dict(
                        name, container_dict)
                    parsed_containers[name] = container

                except Exception as e:
                    raise BlockadeConfigError(
                        "Container '%s' config problem: %s" % (name, e))

            network = d.get('network')
            if network:
                defaults = _DEFAULT_NETWORK_CONFIG.copy()
                defaults.update(network)
                network = defaults

            else:
                network = _DEFAULT_NETWORK_CONFIG.copy()

            return BlockadeConfig(parsed_containers, network=network)

        except KeyError as e:
            raise BlockadeConfigError("Config missing value: " + str(e))

        except Exception as e:
            # TODO log this to some debug stream?
            raise BlockadeConfigError("Failed to load config: " + str(e))

    def __init__(self, containers, network=None):
        self.containers = containers
        self.sorted_containers = dependency_sorted(containers)
        self.network = network or {}


def _dictify(data, name="input"):
    if data:
        if isinstance(data, collections.Sequence):
            return dict((str(v), str(v)) for v in data)
        elif isinstance(data, collections.Mapping):
            return dict((str(k), str(v or k)) for k, v in list(data.items()))
        else:
            raise BlockadeConfigError("invalid %s: need list or map"
                                      % (name,))
    else:
        return {}


def dependency_sorted(containers):
    """Sort a dictionary or list of containers into dependency order

    Returns a sequence
    """
    if not isinstance(containers, collections.Mapping):
        containers = dict((c.name, c) for c in containers)

    container_links = dict((name, set(c.links.keys()))
                           for name, c in containers.items())
    sorted_names = _resolve(container_links)
    return [containers[name] for name in sorted_names]


def _resolve(d):
    all_keys = frozenset(d.keys())
    result = []
    resolved_keys = set()

    while d:
        resolved_this_round = set()
        for name, links in list(d.items()):
            # containers with no links can be started in any order.
            # containers whose parent containers have already been resolved
            # can be added now too.
            if not links or links <= resolved_keys:
                result.append(name)
                resolved_this_round.add(name)
                del d[name]

            # guard against containers which link to unknown containers
            unknown = links - all_keys
            if len(unknown) == 1:
                raise BlockadeConfigError(
                    "container %s links to unknown container %s" %
                    (name, list(unknown)[0]))
            elif len(unknown) > 1:
                raise BlockadeConfigError(
                    "container %s links to unknown containers %s" %
                    (name, unknown))

        # if we made no progress this round, we have a circular dep
        if not resolved_this_round:
            raise BlockadeConfigError("containers have circular links!")

        resolved_keys.update(resolved_this_round)

    return result

########NEW FILE########
__FILENAME__ = core
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from copy import deepcopy

import docker

from .errors import BlockadeError
from .net import NetworkState, BlockadeNetwork
from .state import BlockadeStateFactory


class Blockade(object):
    def __init__(self, config, state_factory=None, network=None,
                 docker_client=None):
        self.config = config
        self.state_factory = state_factory or BlockadeStateFactory()
        self.network = network or BlockadeNetwork(config)
        self.docker_client = docker_client or docker.Client()

    def create(self):
        container_state = {}
        for container in self.config.sorted_containers:
            veth_device = self.network.new_veth_device_name()
            container_state[container.name] = {"veth_device": veth_device}

        # generate blockade ID and persist
        state = self.state_factory.initialize(container_state)

        container_descriptions = []
        for container in self.config.sorted_containers:
            veth_device = container_state[container.name]['veth_device']
            container_id = self._start_container(state.blockade_id, container,
                                                 veth_device)
            description = self._get_container_description(
                state, container.name, container_id)
            container_descriptions.append(description)

        return container_descriptions

    def _start_container(self, blockade_id, container, veth_device):
        container_name = docker_container_name(blockade_id, container.name)
        volumes = list(container.volumes.values()) or None
        response = self.docker_client.create_container(
            container.image, command=container.command, name=container_name,
            ports=container.ports, volumes=volumes, hostname=container.name,
            environment=container.environment)
        container_id = response['Id']

        links = dict((docker_container_name(blockade_id, link), alias)
                     for link, alias in container.links.items())

        lxc_conf = deepcopy(container.lxc_conf)
        lxc_conf['lxc.network.veth.pair'] = veth_device
        self.docker_client.start(container_id, lxc_conf=lxc_conf, links=links,
                                 binds=container.volumes)
        return container_id

    def _get_container_description(self, state, name, container_id,
                                   network_state=True, ip_partitions=None):
        try:
            container = self.docker_client.inspect_container(container_id)
        except docker.APIError as e:
            if e.response.status_code == 404:
                return Container(name, container_id, ContainerState.MISSING)
            else:
                raise

        state_dict = container.get('State')
        if state_dict and state_dict.get('Running'):
            container_state = ContainerState.UP
        else:
            container_state = ContainerState.DOWN

        extras = {}
        network = container.get('NetworkSettings')
        ip = None
        if network:
            ip = network.get('IPAddress')
            if ip:
                extras['ip_address'] = ip

        if (network_state and name in state.containers
                and container_state == ContainerState.UP):
            device = state.containers[name]['veth_device']
            extras['veth_device'] = device
            extras['network_state'] = self.network.network_state(device)

            # include partition ID if we were provided a map of them
            if ip_partitions and ip:
                extras['partition'] = ip_partitions.get(ip)
        else:
            extras['network_state'] = NetworkState.UNKNOWN
            extras['veth_device'] = None

        return Container(name, container_id, container_state, **extras)

    def destroy(self, force=False):
        state = self.state_factory.load()

        containers = self._get_docker_containers(state.blockade_id)
        for container in list(containers.values()):
            container_id = container['Id']
            self.docker_client.stop(container_id, timeout=3)
            self.docker_client.remove_container(container_id)

        self.network.restore(state.blockade_id)
        self.state_factory.destroy()

    def _get_docker_containers(self, blockade_id):
        # look for containers prefixed with our blockade ID
        prefix = "/" + blockade_id + "-"
        d = {}
        for container in self.docker_client.containers(all=True):
            for name in container['Names']:
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    d[name] = container
                    break
        return d

    def _get_all_containers(self, state):
        containers = []
        ip_partitions = self.network.get_ip_partitions(state.blockade_id)
        docker_containers = self._get_docker_containers(state.blockade_id)
        for name, container in docker_containers.items():
            containers.append(self._get_container_description(state, name,
                              container['Id'], ip_partitions=ip_partitions))
        return containers

    def status(self):
        state = self.state_factory.load()
        return self._get_all_containers(state)

    def _get_running_containers(self, container_names=None, state=None):
        state = state or self.state_factory.load()
        containers = self._get_all_containers(state)

        running = dict((c.name, c) for c in containers
                       if c.state == ContainerState.UP)
        if container_names is None:
            return list(running.values())

        found = []
        for name in container_names:
            container = running.get(name)
            if not container:
                raise BlockadeError("Container %s is not found or not running"
                                    % (name,))
            found.append(container)
        return found

    def _get_running_container(self, container_name, state=None):
        return self._get_running_containers((container_name,), state)[0]

    def flaky(self, container_names=None, include_all=False):
        if include_all:
            container_names = None
        containers = self._get_running_containers(container_names)
        for container in containers:
            self.network.flaky(container.veth_device)

    def slow(self, container_names=None, include_all=False):
        if include_all:
            container_names = None
        containers = self._get_running_containers(container_names)
        for container in containers:
            self.network.slow(container.veth_device)

    def fast(self, container_names=None, include_all=False):
        if include_all:
            container_names = None
        containers = self._get_running_containers(container_names)
        for container in containers:
            self.network.fast(container.veth_device)

    def partition(self, partitions):
        state = self.state_factory.load()
        containers = self._get_running_containers(state=state)
        container_dict = dict((c.name, c) for c in containers)
        partitions = expand_partitions(list(container_dict.keys()), partitions)

        container_partitions = []
        for partition in partitions:
            container_partitions.append([container_dict[c] for c in partition])

        self.network.partition_containers(state.blockade_id,
                                          container_partitions)

    def join(self):
        state = self.state_factory.load()
        self.network.restore(state.blockade_id)

    def logs(self, container_name):
        container = self._get_running_container(container_name)
        return self.docker_client.logs(container.container_id)


class Container(object):
    ip_address = None
    veth_device = None
    network_state = NetworkState.NORMAL
    partition = None

    def __init__(self, name, container_id, state, **kwargs):
        self.name = name
        self.container_id = container_id
        self.state = state
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        return dict(name=self.name, container_id=self.container_id,
                    state=self.state, ip_address=self.ip_address,
                    veth_device=self.veth_device,
                    network_state=self.network_state,
                    partition=self.partition)


class ContainerState(object):
    UP = "UP"
    DOWN = "DOWN"
    MISSING = "MISSING"


def docker_container_name(blockade_id, name):
    return '-'.join((blockade_id, name))


def expand_partitions(containers, partitions):
    """Validate the partitions of containers. If there are any containers
    not in any partition, place them in an new partition.
    """
    all_names = frozenset(containers)
    partitions = [frozenset(p) for p in partitions]

    unknown = set()
    overlap = set()
    union = set()

    for index, partition in enumerate(partitions):
        unknown.update(partition - all_names)
        union.update(partition)

        for other in partitions[index+1:]:
            overlap.update(partition.intersection(other))

    if unknown:
        raise BlockadeError("Partitions have unknown containers: %s" %
                            list(unknown))

    if overlap:
        raise BlockadeError("Partitions have overlapping containers: %s" %
                            list(overlap))

    # put any leftover containers in an implicit partition
    leftover = all_names.difference(union)
    if leftover:
        partitions.append(leftover)

    return partitions

########NEW FILE########
__FILENAME__ = errors
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


class BlockadeError(Exception):
    """Expected error within Blockade
    """


class BlockadeConfigError(BlockadeError):
    """Error in configuration
    """


class AlreadyInitializedError(BlockadeError):
    """Blockade already created in this context
    """


class NotInitializedError(BlockadeError):
    """Blockade not created in this context
    """


class InconsistentStateError(BlockadeError):
    """Blockade state is inconsistent (partially created or destroyed)
    """

########NEW FILE########
__FILENAME__ = net
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import random
import string
import subprocess

from .errors import BlockadeError
import collections


class NetworkState(object):
    NORMAL = "NORMAL"
    SLOW = "SLOW"
    FLAKY = "FLAKY"
    UNKNOWN = "UNKNOWN"


class BlockadeNetwork(object):
    def __init__(self, config):
        self.config = config

    def new_veth_device_name(self):
        chars = string.ascii_letters + string.digits
        return "veth" + "".join(random.choice(chars) for _ in range(8))

    def network_state(self, device):
        return network_state(device)

    def flaky(self, device):
        flaky_config = self.config.network['flaky'].split()
        traffic_control_netem(device, ["loss"] + flaky_config)

    def slow(self, device):
        slow_config = self.config.network['slow'].split()
        traffic_control_netem(device, ["delay"] + slow_config)

    def fast(self, device):
        traffic_control_restore(device)

    def restore(self, blockade_id):
        clear_iptables(blockade_id)

    def partition_containers(self, blockade_id, partitions):
        clear_iptables(blockade_id)
        partition_containers(blockade_id, partitions)

    def get_ip_partitions(self, blockade_id):
        return iptables_get_source_chains(blockade_id)


def parse_partition_index(blockade_id, chain):
    prefix = "%s-p" % (blockade_id,)
    if chain and chain.startswith(prefix):
        try:
            return int(chain[len(prefix):])
        except ValueError:
            pass
    raise ValueError("chain %s is not a blockade partition" % (chain,))


def partition_chain_name(blockade_id, partition_index):
    return "%s-p%s" % (blockade_id, partition_index)


def iptables_call_output(*args):
    cmd = ["iptables", "-n"] + list(args)
    try:
        output = subprocess.check_output(cmd)
        return output.decode().split("\n")
    except subprocess.CalledProcessError:
        raise BlockadeError("Problem calling '%s'" % " ".join(cmd))


def iptables_call(*args):
    cmd = ["iptables"] + list(args)
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        raise BlockadeError("Problem calling '%s'" % " ".join(cmd))


def iptables_get_chain_rules(chain):
    if not chain:
        raise ValueError("invalid chain")
    lines = iptables_call_output("-L", chain)
    if len(lines) < 2:
        raise BlockadeError("Can't understand iptables output: \n%s" %
                            "\n".join(lines))

    chain_line, header_line = lines[:2]
    if not (chain_line.startswith("Chain " + chain) and
            header_line.startswith("target")):
        raise BlockadeError("Can't understand iptables output: \n%s" %
                            "\n".join(lines))
    return lines[2:]


def iptables_get_source_chains(blockade_id):
    """Get a map of blockade chains IDs -> list of IPs targeted at them

    For figuring out which container is in which partition
    """
    result = {}
    if not blockade_id:
        raise ValueError("invalid blockade_id")
    lines = iptables_get_chain_rules("FORWARD")

    for line in lines:
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            partition_index = parse_partition_index(blockade_id, parts[0])
        except ValueError:
            continue  # not a rule targetting a blockade chain

        source = parts[3]
        if source:
            result[source] = partition_index
    return result


def iptables_delete_rules(chain, predicate):
    if not chain:
        raise ValueError("invalid chain")
    if not isinstance(predicate, collections.Callable):
        raise ValueError("invalid predicate")

    lines = iptables_get_chain_rules(chain)

    # TODO this is susceptible to check-then-act races.
    # better to ultimately switch to python-iptables if it becomes less buggy
    for index, line in reversed(list(enumerate(lines, 1))):
        line = line.strip()
        if line and predicate(line):
            iptables_call("-D", chain, str(index))


def iptables_delete_blockade_rules(blockade_id):
    def predicate(rule):
        target = rule.split()[0]
        try:
            parse_partition_index(blockade_id, target)
        except ValueError:
            return False
        return True
    iptables_delete_rules("FORWARD", predicate)


def iptables_delete_blockade_chains(blockade_id):
    if not blockade_id:
        raise ValueError("invalid blockade_id")

    lines = iptables_call_output("-L")
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "Chain":
            chain = parts[1]
            try:
                parse_partition_index(blockade_id, chain)
            except ValueError:
                continue
            # if we are a valid blockade chain, flush and delete
            iptables_call("-F", chain)
            iptables_call("-X", chain)


def iptables_insert_rule(chain, src=None, dest=None, target=None):
    """Insert a new rule in the chain
    """
    if not chain:
        raise ValueError("Invalid chain")
    if not target:
        raise ValueError("Invalid target")
    if not (src or dest):
        raise ValueError("Need src, dest, or both")

    args = ["-I", chain]
    if src:
        args += ["-s", src]
    if dest:
        args += ["-d", dest]
    args += ["-j", target]
    iptables_call(*args)


def iptables_create_chain(chain):
    """Create a new chain
    """
    if not chain:
        raise ValueError("Invalid chain")
    iptables_call("-N", chain)


def clear_iptables(blockade_id):
    """Remove all iptables rules and chains related to this blockade
    """
    # first remove refererences to our custom chains
    iptables_delete_blockade_rules(blockade_id)

    # then remove the chains themselves
    iptables_delete_blockade_chains(blockade_id)


def partition_containers(blockade_id, partitions):
    if not partitions or len(partitions) == 1:
        return
    for index, partition in enumerate(partitions, 1):
        chain_name = partition_chain_name(blockade_id, index)

        # create chain for partition and block traffic TO any other partition
        iptables_create_chain(chain_name)
        for other in partitions:
            if partition is other:
                continue
            for container in other:
                if container.ip_address:
                    iptables_insert_rule(chain_name, dest=container.ip_address,
                                         target="DROP")

        # direct traffic FROM any container in the partition to the new chain
        for container in partition:
            iptables_insert_rule("FORWARD", src=container.ip_address,
                                 target=chain_name)


def traffic_control_restore(device):
    cmd = ["tc", "qdisc", "del", "dev", device, "root"]

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    _, stderr = p.communicate()
    stderr = stderr.decode()

    if p.returncode != 0:
        if p.returncode == 2 and stderr:
            if "No such file or directory" in stderr:
                return

        # TODO log error somewhere?
        raise BlockadeError("Problem calling traffic control: " +
                            " ".join(cmd))


def traffic_control_netem(device, params):
    try:
        cmd = ["tc", "qdisc", "replace", "dev", device,
               "root", "netem"] + params
        subprocess.check_call(cmd)

    except subprocess.CalledProcessError:
        # TODO log error somewhere?
        raise BlockadeError("Problem calling traffic control: " +
                            " ".join(cmd))


def network_state(device):
    try:
        output = subprocess.check_output(
            ["tc", "qdisc", "show", "dev", device]).decode()
        # sloppy but good enough for now
        if " delay " in output:
            return NetworkState.SLOW
        if " loss " in output:
            return NetworkState.FLAKY
        return NetworkState.NORMAL

    except subprocess.CalledProcessError:
        # TODO log error somewhere?
        return NetworkState.UNKNOWN

########NEW FILE########
__FILENAME__ = state
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import uuid
import os
import errno
from copy import deepcopy

import yaml

from .errors import AlreadyInitializedError, NotInitializedError, \
    InconsistentStateError

BLOCKADE_STATE_DIR = ".blockade"
BLOCKADE_STATE_FILE = ".blockade/state.yml"
BLOCKADE_ID_PREFIX = "blockade-"
BLOCKADE_STATE_VERSION = 1


def _assure_dir():
    try:
        os.mkdir(BLOCKADE_STATE_DIR)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def _state_delete():
    try:
        os.remove(BLOCKADE_STATE_FILE)
    except OSError as e:
        if e.errno not in (errno.EPERM, errno.ENOENT):
            raise

    try:
        os.rmdir(BLOCKADE_STATE_DIR)
    except OSError as e:
        if e.errno not in (errno.ENOTEMPTY, errno.ENOENT):
            raise


def _base_state(blockade_id, containers):
    return dict(blockade_id=blockade_id, containers=containers,
                version=BLOCKADE_STATE_VERSION)


class BlockadeState(object):
    def __init__(self, blockade_id, containers):
        self._blockade_id = blockade_id
        self._containers = containers

    @property
    def blockade_id(self):
        return self._blockade_id

    @property
    def containers(self):
        return deepcopy(self._containers)


class BlockadeStateFactory(object):
    # annoyed with how this ended up structured, and that I called it
    # a factory, but fuckit..

    @staticmethod
    def initialize(containers, blockade_id=None):
        if blockade_id is None:
            blockade_id = BLOCKADE_ID_PREFIX + uuid.uuid4().hex[:10]
        containers = deepcopy(containers)

        f = None
        path = BLOCKADE_STATE_FILE
        _assure_dir()
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            with os.fdopen(os.open(path, flags), "w") as f:
                yaml.dump(_base_state(blockade_id, containers), f)
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise AlreadyInitializedError(
                    "Path %s exists. "
                    "You may need to destroy a previous blockade." % path)
            raise
        except Exception:
            # clean up our created file
            _state_delete()
            raise
        return BlockadeState(blockade_id, containers)

    @staticmethod
    def load():
        try:
            with open(BLOCKADE_STATE_FILE) as f:
                state = yaml.safe_load(f)
                return BlockadeState(state['blockade_id'], state['containers'])

        except (IOError, OSError) as e:
            if e.errno == errno.ENOENT:
                raise NotInitializedError("No blockade exists in this context")
            raise InconsistentStateError("Failed to load Blockade state: "
                                         + str(e))

        except Exception as e:
            raise InconsistentStateError("Failed to load Blockade state: "
                                         + str(e))

    @staticmethod
    def destroy():
        _state_delete()

########NEW FILE########
__FILENAME__ = test_cli
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from blockade.tests import unittest
from blockade import cli


class CommandLineTests(unittest.TestCase):

    def test_parser(self):
        # just make sure we don't have any typos for now
        cli.setup_parser()

########NEW FILE########
__FILENAME__ = test_config
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from blockade.tests import unittest
from blockade.errors import BlockadeConfigError
from blockade.config import BlockadeConfig, BlockadeContainerConfig, \
    dependency_sorted


class ConfigTests(unittest.TestCase):

    def test_parse_1(self):
        containers = {
            "c1": {"image": "image1", "command": "/bin/bash"},
            "c2": {"image": "image2", "links": ["c1"]}
        }
        d = dict(containers=containers)

        config = BlockadeConfig.from_dict(d)
        self.assertEqual(len(config.containers), 2)
        self.assertEqual(config.containers["c1"].name, "c1")
        self.assertEqual(config.containers["c1"].image, "image1")
        self.assertEqual(config.containers["c1"].command, "/bin/bash")
        self.assertEqual(config.containers["c2"].name, "c2")
        self.assertEqual(config.containers["c2"].image, "image2")

    def test_parse_2(self):
        containers = {
            "c1": {"image": "image1", "command": "/bin/bash"}
        }
        network = {"flaky": "61%"}
        d = dict(containers=containers, network=network)

        config = BlockadeConfig.from_dict(d)
        # default value should be there
        self.assertIn("flaky", config.network)
        self.assertEqual(config.network['flaky'], "61%")
        # default value should be there
        self.assertIn("slow", config.network)

    def test_parse_with_volumes_1(self):
        containers = {
            "c1": {"image": "image1", "command": "/bin/bash",
                   "volumes": {"/some/mount": "/some/place"}}
        }
        network = {}
        d = dict(containers=containers, network=network)

        config = BlockadeConfig.from_dict(d)
        # default value should be there
        self.assertEqual(len(config.containers), 1)
        c1 = config.containers['c1']
        self.assertEqual(c1.volumes, {"/some/mount": "/some/place"})

    def test_parse_with_volumes_2(self):
        containers = {
            "c1": {"image": "image1", "command": "/bin/bash",
                   "volumes": ["/some/mount"]}
        }
        network = {}
        d = dict(containers=containers, network=network)

        config = BlockadeConfig.from_dict(d)
        # default value should be there
        self.assertEqual(len(config.containers), 1)
        c1 = config.containers['c1']
        self.assertEqual(c1.volumes, {"/some/mount": "/some/mount"})

    def test_parse_with_volumes_3(self):
        containers = {
            "c1": {"image": "image1", "command": "/bin/bash",
                   "volumes": {"/some/mount": ""}}
        }
        network = {}
        d = dict(containers=containers, network=network)

        config = BlockadeConfig.from_dict(d)
        # default value should be there
        self.assertEqual(len(config.containers), 1)
        c1 = config.containers['c1']
        self.assertEqual(c1.volumes, {"/some/mount": "/some/mount"})

    def test_parse_with_volumes_4(self):
        containers = {
            "c1": {"image": "image1", "command": "/bin/bash",
                   "volumes": {"/some/mount": None}}
        }
        network = {}
        d = dict(containers=containers, network=network)

        config = BlockadeConfig.from_dict(d)
        # default value should be there
        self.assertEqual(len(config.containers), 1)
        c1 = config.containers['c1']
        self.assertEqual(c1.volumes, {"/some/mount": "/some/mount"})

    def test_parse_with_env_1(self):
        containers = {
            "c1": {"image": "image1", "command": "/bin/bash",
                   "environment": {"HATS": 4, "JACKETS": "some"}}
        }
        d = dict(containers=containers, network={})

        config = BlockadeConfig.from_dict(d)
        self.assertEqual(len(config.containers), 1)
        c1 = config.containers['c1']
        self.assertEqual(c1.environment, {"HATS": 4, "JACKETS": "some"})

    def test_parse_with_numeric_port(self):
        containers = {
            "c1": {"image": "image1", "command": "/bin/bash",
                   "ports": [10000]}
        }
        d = dict(containers=containers, network={})

        config = BlockadeConfig.from_dict(d)
        self.assertEqual(len(config.containers), 1)
        c1 = config.containers['c1']
        self.assertEqual(c1.ports, {"10000": "10000"})

    def test_parse_fail_1(self):
        containers = {
            "c1": {"image": "image1", "command": "/bin/bash"},
            "c2": {"image": "image2", "links": ["c1"]}
        }
        d = dict(contianers=containers)
        with self.assertRaises(BlockadeConfigError):
            BlockadeConfig.from_dict(d)

    def test_parse_fail_2(self):
        containers = {
            "c1": {"ima": "image1", "command": "/bin/bash"},
            "c2": {"image": "image2", "links": ["c1"]}
        }
        d = dict(containers=containers)
        with self.assertRaises(BlockadeConfigError):
            BlockadeConfig.from_dict(d)

    def test_link_ordering_1(self):
        containers = [BlockadeContainerConfig("c1", "image"),
                      BlockadeContainerConfig("c2", "image"),
                      BlockadeContainerConfig("c3", "image")]
        ordered = dependency_sorted(containers)
        ordered_names = [c.name for c in ordered]
        self.assertDependencyLevels(ordered_names, ["c1", "c2", "c3"])

    def test_link_ordering_2(self):
        containers = [BlockadeContainerConfig("c1", "image"),
                      BlockadeContainerConfig("c2", "image",
                                              links={"c1": "c1"}),
                      BlockadeContainerConfig("c3", "image")]
        ordered = dependency_sorted(containers)
        ordered_names = [c.name for c in ordered]
        self.assertDependencyLevels(ordered_names,
                                    ["c1", "c3"],
                                    ["c2"])

    def test_link_ordering_3(self):
        containers = [BlockadeContainerConfig("c1", "image"),
                      BlockadeContainerConfig("c2", "image",
                                              links={"c1": "c1"}),
                      BlockadeContainerConfig("c3", "image",
                                              links={"c1": "c1"})]
        ordered = dependency_sorted(containers)
        ordered_names = [c.name for c in ordered]
        self.assertDependencyLevels(ordered_names, ["c1"], ["c2", "c3"])

    def test_link_ordering_4(self):
        containers = [BlockadeContainerConfig("c1", "image"),
                      BlockadeContainerConfig("c2", "image", links=["c1"]),
                      BlockadeContainerConfig("c3", "image", links=["c1"]),
                      BlockadeContainerConfig("c4", "image",
                                              links=["c1", "c3"]),
                      BlockadeContainerConfig("c5", "image",
                                              links=["c2", "c3"]),
                      ]
        ordered = dependency_sorted(containers)
        ordered_names = [c.name for c in ordered]
        self.assertDependencyLevels(ordered_names, ["c1"], ["c2", "c3"],
                                    ["c4", "c5"])

    def test_link_ordering_unknown_1(self):
        containers = [BlockadeContainerConfig("c1", "image"),
                      BlockadeContainerConfig("c2", "image", links=["c6"]),
                      BlockadeContainerConfig("c3", "image", links=["c1"])]
        with self.assertRaisesRegexp(BlockadeConfigError, "unknown"):
            dependency_sorted(containers)

    def test_link_ordering_unknown_2(self):
        containers = [BlockadeContainerConfig("c1", "image"),
                      BlockadeContainerConfig("c2", "image",
                                              links=["c6", "c7"]),
                      BlockadeContainerConfig("c3", "image", links=["c1"])]
        with self.assertRaisesRegexp(BlockadeConfigError, "unknown"):
            dependency_sorted(containers)

    def test_link_ordering_circular_1(self):
        containers = [BlockadeContainerConfig("c1", "image"),
                      BlockadeContainerConfig("c2", "image", links=["c1"]),
                      BlockadeContainerConfig("c3", "image", links=["c3"])]

        with self.assertRaisesRegexp(BlockadeConfigError, "circular"):
            dependency_sorted(containers)

    def test_link_ordering_circular_2(self):
        containers = [BlockadeContainerConfig("c1", "image"),
                      BlockadeContainerConfig("c2", "image",
                                              links=["c1", "c3"]),
                      BlockadeContainerConfig("c3", "image", links=["c2"])]

        with self.assertRaisesRegexp(BlockadeConfigError, "circular"):
            dependency_sorted(containers)

    def assertDependencyLevels(self, seq, *levels):
        self.assertEquals(len(seq), sum(len(l) for l in levels))

        for index, level in enumerate(levels):
            expected = set(level)
            actual = set(seq[:len(level)])
            if expected != actual:
                self.fail("Expected dep level #%d %s but got %s. Sequence: %s" % (index+1, expected, actual, seq))
            seq = seq[len(level):]


########NEW FILE########
__FILENAME__ = test_core
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import mock

from blockade.tests import unittest
from blockade.core import Blockade, expand_partitions
from blockade.errors import BlockadeError
from blockade.config import BlockadeContainerConfig, BlockadeConfig
from blockade.state import BlockadeState


class BlockadeCoreTests(unittest.TestCase):

    def setUp(self):
        self.network = mock.Mock()

        self.state_factory = mock.Mock()
        self.docker_client = mock.Mock()

    def test_create(self):
        containers = [BlockadeContainerConfig("c1", "image"),
                      BlockadeContainerConfig("c2", "image"),
                      BlockadeContainerConfig("c3", "image")]
        config = BlockadeConfig(containers)

        self.network.new_veth_device_name.side_effect = ["veth1", "veth2",
                                                         "veth3"]
        initialize = lambda x: BlockadeState("ourblockadeid", x)
        self.state_factory.initialize.side_effect = initialize
        self.docker_client.create_container.side_effect = [
            {"Id": "container1"},
            {"Id": "container2"},
            {"Id": "container3"}]

        b = Blockade(config, self.state_factory, self.network,
                     self.docker_client)
        b.create()

        self.assertEqual(self.state_factory.initialize.call_count, 1)
        self.assertEqual(self.docker_client.create_container.call_count, 3)

    def test_expand_partitions(self):
        containers = ["c1", "c2", "c3", "c4", "c5"]

        partitions = expand_partitions(containers, [["c1", "c3"]])
        self.assert_partitions(partitions, [["c1", "c3"], ["c2", "c4", "c5"]])

        partitions = expand_partitions(containers, [["c1", "c3"], ["c4"]])
        self.assert_partitions(partitions, [["c1", "c3"], ["c2", "c5"],
                                            ["c4"]])

        with self.assertRaisesRegexp(BlockadeError, "unknown"):
            expand_partitions(containers, [["c1"], ["c100"]])

        with self.assertRaisesRegexp(BlockadeError, "overlap"):
            expand_partitions(containers, [["c1"], ["c1", "c2"]])

    def assert_partitions(self, partitions1, partitions2):
        setofsets1 = frozenset(frozenset(n) for n in partitions1)
        setofsets2 = frozenset(frozenset(n) for n in partitions2)
        self.assertEqual(setofsets1, setofsets2)

########NEW FILE########
__FILENAME__ = test_integration
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import sys
import tempfile
import shutil
import traceback
import json
from io import StringIO

import six
import mock
from clint.textui.colored import ColoredString

from blockade.tests import unittest
import blockade.cli


INT_ENV = "BLOCKADE_INTEGRATION_TESTS"
INT_SKIP = (not os.getenv(INT_ENV), "export %s=1 to run" % INT_ENV)


class FakeExit(BaseException):
    def __init__(self, rc):
        self.rc = rc


def example_config_path(filename):
    example_dir = os.path.join(os.path.dirname(__file__), "../..", "examples")
    example_dir = os.path.abspath(example_dir)
    if not os.path.exists(example_dir):
        raise Exception("example config directory not found: %s" % example_dir)

    config_path = os.path.join(example_dir, filename)
    if not os.path.exists(config_path):
        raise Exception("example config not found: %s" % config_path)
    return config_path


def coerce_output(s):
    if isinstance(s, ColoredString):
        return six.u(str(s))
    elif isinstance(s, six.binary_type):
        return six.u(s)
    else:
        return s


class IntegrationTests(unittest.TestCase):
    """Integration tests that run the full CLI args down.

    Tests that are Linux and Docker only should be decorated with:
        @unittest.skipIf(*INT_SKIP)

    They will only be run when BLOCKADE_INTEGRATION_TESTS=1 env is set.
    """

    sysexit_patch = None
    stderr_patch = None
    tempdir = None
    oldcwd = None

    def setUp(self):
        self.sysexit_patch = mock.patch("sys.exit")
        self.mock_sysexit = self.sysexit_patch.start()

        def exit(rc):
            raise FakeExit(rc)

        self.mock_sysexit.side_effect = exit

        self.tempdir = tempfile.mkdtemp()
        self.oldcwd = os.getcwd()
        os.chdir(self.tempdir)

    def tearDown(self):
        if self.sysexit_patch:
            self.sysexit_patch.stop()

        if self.oldcwd:
            os.chdir(self.oldcwd)
        if self.tempdir:
            try:
                shutil.rmtree(self.tempdir)
            except Exception:
                pass

    def call_blockade(self, *args):
        stdout = StringIO()
        stderr = StringIO()
        with mock.patch("blockade.cli.puts") as mock_puts:
            mock_puts.side_effect = lambda s: stdout.write(coerce_output(s))

            with mock.patch("blockade.cli.puts_err") as mock_puts_err:
                mock_puts_err.side_effect = lambda s: stderr.write(
                    coerce_output(s))

                try:
                    blockade.cli.main(args)
                except FakeExit as e:
                    if e.rc != 0:
                        raise
                return (stdout.getvalue(), stderr.getvalue())

    def test_badargs(self):
        with mock.patch("sys.stderr"):
            with self.assertRaises(FakeExit) as cm:
                self.call_blockade("--notarealarg")

            self.assertEqual(cm.exception.rc, 2)

    @unittest.skipIf(*INT_SKIP)
    def test_containers(self):
        config_path = example_config_path("sleep/blockade.yaml")

        # TODO make this better. so far we just walk through all
        # the major operations, but don't really assert anything
        # other than exit code.
        try:
            self.call_blockade("-c", config_path, "up")

            self.call_blockade("-c", config_path, "status")
            stdout, _ = self.call_blockade("-c", config_path, "status",
                                           "--json")
            parsed = json.loads(stdout)
            self.assertEqual(len(parsed), 3)

            self.call_blockade("-c", config_path, "flaky", "c1")
            self.call_blockade("-c", config_path, "slow", "c2", "c3")
            self.call_blockade("-c", config_path, "fast", "c3")

            # make sure it is harmless for call fast when nothing is slow
            self.call_blockade("-c", config_path, "fast", "--all")

            with self.assertRaises(FakeExit):
                self.call_blockade("-c", config_path, "slow", "notarealnode")

            self.call_blockade("-c", config_path, "partition", "c1,c2", "c3")
            self.call_blockade("-c", config_path, "join")

            stdout, _ = self.call_blockade("-c", config_path, "logs", "c1")
            self.assertEquals("I am c1", stdout.strip())

        finally:
            try:
                self.call_blockade("-c", config_path, "destroy")
            except Exception:
                print("Failed to destroy Blockade!")
                traceback.print_exc(file=sys.stdout)

    @unittest.skipIf(*INT_SKIP)
    def test_ping_link_ordering(self):
        config_path = example_config_path("ping/blockade.yaml")

        try:
            self.call_blockade("-c", config_path, "up")

            self.call_blockade("-c", config_path, "status")
            stdout, _ = self.call_blockade("-c", config_path, "status",
                                           "--json")
            parsed = json.loads(stdout)
            self.assertEqual(len(parsed), 3)

            # we just want to make sure everything came up ok -- that
            # containers were started in the right order.
            for container in parsed:
                self.assertEqual(container['state'], "UP")

            # could actually try to parse out the logs here and assert that
            # network filters are working.

        finally:
            try:
                self.call_blockade("-c", config_path, "destroy")
            except Exception:
                print("Failed to destroy Blockade!")
                traceback.print_exc(file=sys.stdout)

########NEW FILE########
__FILENAME__ = test_net
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import mock
import subprocess

from blockade.tests import unittest
import blockade.net
from blockade.net import NetworkState, BlockadeNetwork, \
    parse_partition_index, partition_chain_name

# NOTE these values are "byte strings" -- to depict output we would see
# from subprocess calls. We need to make sure we properly decode them
# in Python3.

NORMAL_QDISC_SHOW = b"qdisc pfifo_fast 0: root refcnt 2 bands 3 priomap\n"
SLOW_QDISC_SHOW = b"qdisc netem 8011: root refcnt 2 limit 1000 delay 50.0ms\n"
FLAKY_QDISC_SHOW = b"qdisc netem 8011: root refcnt 2 limit 1000 loss 50%\n"

QDISC_DEL_NOENT = b"RTNETLINK answers: No such file or directory"


_IPTABLES_LIST_FORWARD_1 = b"""Chain FORWARD (policy ACCEPT)
target     prot opt source               destination
blockade-aa43racd2-p1  all  --  172.17.0.16         anywhere
blockade-4eraffr-p1  all  --  172.17.0.17         anywhere
blockade-e5dcf85cd2-p1  all  --  172.17.0.162         anywhere
blockade-e5dcf85cd2-p1  all  --  172.17.0.164         anywhere
ACCEPT     tcp  --  172.17.0.162         172.17.0.164         tcp spt:8000
ACCEPT     tcp  --  172.17.0.164         172.17.0.162         tcp dpt:8000
ACCEPT     tcp  --  172.17.0.162         172.17.0.163         tcp spt:8000
ACCEPT     tcp  --  172.17.0.163         172.17.0.162         tcp dpt:8000
ACCEPT     all  --  anywhere             anywhere
ACCEPT     all  --  anywhere             anywhere
"""

_IPTABLES_LIST_FORWARD_2 = b"""Chain FORWARD (policy ACCEPT)
target     prot opt source               destination
"""

_IPTABLES_LIST_1 = b"""Chain INPUT (policy ACCEPT)
target     prot opt source               destination

Chain FORWARD (policy ACCEPT)
target     prot opt source               destination
blockade-e5dcf85cd2-p1  all  --  172.17.0.162         anywhere
blockade-e5dcf85cd2-p1  all  --  172.17.0.164         anywhere
ACCEPT     tcp  --  172.17.0.162         172.17.0.164         tcp spt:8000
ACCEPT     tcp  --  172.17.0.164         172.17.0.162         tcp dpt:8000
ACCEPT     tcp  --  172.17.0.162         172.17.0.163         tcp spt:8000
ACCEPT     tcp  --  172.17.0.163         172.17.0.162         tcp dpt:8000
ACCEPT     all  --  anywhere             anywhere
ACCEPT     all  --  anywhere             anywhere

Chain OUTPUT (policy ACCEPT)
target     prot opt source               destination

Chain blockade-e5dcf85cd2-p1 (2 references)
target     prot opt source               destination
DROP       all  --  anywhere             172.17.0.163

Chain blockade-e5dcf85cd2-p2 (0 references)
target     prot opt source               destination
DROP       all  --  anywhere             172.17.0.162
DROP       all  --  anywhere             172.17.0.164
"""

_IPTABLES_LIST_2 = b"""Chain INPUT (policy ACCEPT)
target     prot opt source               destination

Chain FORWARD (policy ACCEPT)
target     prot opt source               destination
ACCEPT     tcp  --  172.17.0.162         172.17.0.164         tcp spt:8000
ACCEPT     tcp  --  172.17.0.164         172.17.0.162         tcp dpt:8000
ACCEPT     tcp  --  172.17.0.162         172.17.0.163         tcp spt:8000
ACCEPT     tcp  --  172.17.0.163         172.17.0.162         tcp dpt:8000
ACCEPT     all  --  anywhere             anywhere
ACCEPT     all  --  anywhere             anywhere

Chain OUTPUT (policy ACCEPT)
target     prot opt source               destination
"""


class NetTests(unittest.TestCase):
    def test_iptables_get_blockade_chains(self):
        blockade_id = "blockade-e5dcf85cd2"
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            mock_check_output = mock_subprocess.check_output
            mock_check_output.return_value = _IPTABLES_LIST_FORWARD_1
            result = blockade.net.iptables_get_source_chains(blockade_id)

            self.assertEqual(mock_subprocess.check_output.call_count, 1)
            self.assertEqual(result, {"172.17.0.162": 1, "172.17.0.164": 1})

    def test_iptables_delete_blockade_rules_1(self):
        blockade_id = "blockade-e5dcf85cd2"
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            mock_check_output = mock_subprocess.check_output
            mock_check_output.return_value = _IPTABLES_LIST_FORWARD_1
            blockade.net.iptables_delete_blockade_rules(blockade_id)

            self.assertEqual(mock_subprocess.check_output.call_count, 1)

            # rules should be removed in reverse order
            expected_calls = [mock.call(["iptables", "-D", "FORWARD", "4"]),
                              mock.call(["iptables", "-D", "FORWARD", "3"])]
            self.assertEqual(mock_subprocess.check_call.call_args_list,
                             expected_calls)

    def test_iptables_delete_blockade_rules_2(self):
        blockade_id = "blockade-e5dcf85cd2"
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            mock_check_output = mock_subprocess.check_output
            mock_check_output.return_value = _IPTABLES_LIST_FORWARD_2
            blockade.net.iptables_delete_blockade_rules(blockade_id)

            self.assertEqual(mock_subprocess.check_output.call_count, 1)
            self.assertEqual(mock_subprocess.check_call.call_count, 0)

    def test_iptables_delete_blockade_chains_1(self):
        blockade_id = "blockade-e5dcf85cd2"
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            mock_subprocess.check_output.return_value = _IPTABLES_LIST_1
            blockade.net.iptables_delete_blockade_chains(blockade_id)

            self.assertEqual(mock_subprocess.check_output.call_count, 1)

            expected_calls = [
                mock.call(["iptables", "-F", "blockade-e5dcf85cd2-p1"]),
                mock.call(["iptables", "-X", "blockade-e5dcf85cd2-p1"]),
                mock.call(["iptables", "-F", "blockade-e5dcf85cd2-p2"]),
                mock.call(["iptables", "-X", "blockade-e5dcf85cd2-p2"])]
            self.assertEqual(mock_subprocess.check_call.call_args_list,
                             expected_calls)

    def test_iptables_delete_blockade_chains_2(self):
        blockade_id = "blockade-e5dcf85cd2"
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            mock_subprocess.check_output.return_value = _IPTABLES_LIST_2
            blockade.net.iptables_delete_blockade_chains(blockade_id)

            self.assertEqual(mock_subprocess.check_output.call_count, 1)
            self.assertEqual(mock_subprocess.check_call.call_count, 0)

    def test_iptables_insert_rule_1(self):
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            blockade.net.iptables_insert_rule("FORWARD", src="192.168.0.1",
                                              target="DROP")
            mock_subprocess.check_call.assert_called_once_with(
                ["iptables", "-I", "FORWARD", "-s", "192.168.0.1",
                 "-j", "DROP"])

    def test_iptables_insert_rule_2(self):
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            blockade.net.iptables_insert_rule("FORWARD", src="192.168.0.1",
                                              dest="192.168.0.2",
                                              target="DROP")
            mock_subprocess.check_call.assert_called_once_with(
                ["iptables", "-I", "FORWARD", "-s", "192.168.0.1", "-d",
                 "192.168.0.2", "-j", "DROP"])

    def test_iptables_insert_rule_3(self):
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            blockade.net.iptables_insert_rule("FORWARD", dest="192.168.0.2",
                                              target="DROP")
            mock_subprocess.check_call.assert_called_once_with(
                ["iptables", "-I", "FORWARD", "-d", "192.168.0.2",
                 "-j", "DROP"])

    def test_iptables_create_chain(self):
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            blockade.net.iptables_create_chain("hats")
            mock_subprocess.check_call.assert_called_once_with(
                ["iptables", "-N", "hats"])

    def test_partition_chain_parse(self):
        blockade_id = "abc123"
        self.assertEqual(partition_chain_name(blockade_id, 1), "abc123-p1")
        self.assertEqual(partition_chain_name(blockade_id, 2), "abc123-p2")

        index = parse_partition_index(blockade_id,
                                      partition_chain_name(blockade_id, 1))
        self.assertEqual(index, 1)

        with self.assertRaises(ValueError):
            parse_partition_index(blockade_id, "notablockade")
        with self.assertRaises(ValueError):
            parse_partition_index(blockade_id, "abc123-1")
        with self.assertRaises(ValueError):
            parse_partition_index(blockade_id, "abc123-p")
        with self.assertRaises(ValueError):
            parse_partition_index(blockade_id, "abc123-notanumber")

    def test_network_already_normal(self):
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            mock_process = mock_subprocess.Popen.return_value = mock.Mock()
            mock_process.communicate.return_value = "", QDISC_DEL_NOENT
            mock_process.returncode = 2

            net = BlockadeNetwork(mock.Mock())

            # ensure we don't raise an error
            net.fast('somedevice')
            self.assertIn('somedevice',
                          mock_subprocess.Popen.call_args[0][0])

    def test_network_state_slow(self):
        self._network_state(NetworkState.SLOW, SLOW_QDISC_SHOW)

    def test_network_state_normal(self):
        self._network_state(NetworkState.NORMAL, NORMAL_QDISC_SHOW)

    def test_network_state_flaky(self):
        self._network_state(NetworkState.FLAKY, FLAKY_QDISC_SHOW)

    def _network_state(self, state, output):
        with mock.patch('blockade.net.subprocess') as mock_subprocess:
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError
            mock_subprocess.check_output.return_value = output

            net = BlockadeNetwork(mock.Mock())
            self.assertEqual(net.network_state('somedevice'), state)
            self.assertIn('somedevice',
                          mock_subprocess.check_output.call_args[0][0])

########NEW FILE########
__FILENAME__ = test_state
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import shutil
import tempfile

from blockade.tests import unittest
from blockade.state import BlockadeStateFactory
from blockade.errors import NotInitializedError


class BlockadeStateTests(unittest.TestCase):
    tempdir = None
    oldcwd = None

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.oldcwd = os.getcwd()
        os.chdir(self.tempdir)

    def tearDown(self):
        if self.oldcwd:
            os.chdir(self.oldcwd)
        if self.tempdir:
            try:
                shutil.rmtree(self.tempdir)
            except Exception:
                pass

    def test_state_initialize(self):

        containers = {"n1": {"a": 1}, "n2": {"a": 4}}
        state = BlockadeStateFactory.initialize(containers=containers)

        self.assertTrue(os.path.exists(".blockade/state.yml"))

        self.assertEqual(state.containers, containers)
        self.assertIsNot(state.containers, containers)
        self.assertIsNot(state.containers["n2"], containers["n2"])

        self.assertRegexpMatches(state.blockade_id, "^blockade-")

        state2 = BlockadeStateFactory.load()
        self.assertEqual(state2.containers, state.containers)
        self.assertIsNot(state2.containers, state.containers)
        self.assertIsNot(state2.containers["n2"], state.containers["n2"])
        self.assertEqual(state2.blockade_id, state.blockade_id)

        BlockadeStateFactory.destroy()
        self.assertFalse(os.path.exists(".blockade/state.yml"))
        self.assertFalse(os.path.exists(".blockade"))

    def test_state_uninitialized(self):
        with self.assertRaises(NotInitializedError):
            BlockadeStateFactory.load()

########NEW FILE########
__FILENAME__ = version
#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# WARNING: place nothing else into this file. It is directly exec'd by
# setup.py.

__version__ = "0.1.2"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# blockade documentation build configuration file, created by
# sphinx-quickstart on Fri Feb  7 13:21:50 2014.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'blockade'
copyright = u'2014, Dell Cloud Manager'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1.0'
# The full version, including alpha/beta/rc tags.
release = '0.1.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'blockadedoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'blockade.tex', u'blockade Documentation',
   u'Dell Cloud Manager', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'blockade', u'blockade Documentation',
     [u'Dell Cloud Manager'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'blockade', u'blockade Documentation',
   u'Dell Cloud Manager', 'blockade', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
