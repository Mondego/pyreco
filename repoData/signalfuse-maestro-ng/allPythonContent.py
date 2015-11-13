__FILENAME__ = entities
# Copyright (C) 2013 SignalFuse, Inc.
#
# Docker container orchestration utility.

import docker
import multiprocessing.dummy as multiprocessing
import re
import six

from . import exceptions
from . import lifecycle


class Entity:
    """Base class for named entities in the orchestrator."""
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        """Get the name of this entity."""
        return self._name

    def __repr__(self):
        return self._name


class Ship(Entity):
    """A Ship that can host and run Containers.

    Ships are hosts in the infrastructure. A Docker daemon is expected to be
    running on each ship, providing control over the containers that will be
    executed there.
    """

    DEFAULT_DOCKER_PORT = 4243
    DEFAULT_DOCKER_VERSION = '1.8'
    DEFAULT_DOCKER_TIMEOUT = 5

    def __init__(self, name, ip, docker_port=DEFAULT_DOCKER_PORT,
                 timeout=None, docker_endpoint=None):
        """Instantiate a new ship.

        Args:
            name (string): the name of the ship.
            ip (string): the IP address of resolvable host name of the host.
            docker_port (int): the port the Docker daemon listens on.
            docker_endpoint (url): endpoint to access the docker api
        """
        Entity.__init__(self, name)
        self._ip = ip
        self._docker_port = docker_port
        if docker_endpoint:
            self._backend_url = docker_endpoint
        else:
            self._backend_url = 'http://{:s}:{:d}'.format(ip, docker_port)
        self._backend = docker.Client(
            base_url=self._backend_url,
            version=Ship.DEFAULT_DOCKER_VERSION,
            timeout=timeout or Ship.DEFAULT_DOCKER_TIMEOUT)

    @property
    def ip(self):
        """Returns this host's IP address or hostname."""
        return self._ip

    @property
    def backend(self):
        """Returns the Docker client wrapper to talk to the Docker daemon on
        this host."""
        return self._backend

    @property
    def docker_endpoint(self):
        """Returns the Docker daemon endpoint location on that ship."""
        return 'tcp://%s:%d' % (self._ip, self._docker_port)

    def __repr__(self):
        return '<ship:%s [%s:%d]>' % (self.name, self._ip, self._docker_port)


class Service(Entity):
    """A Service is a collection of Containers running on one or more Ships
    that constitutes a logical grouping of containers that make up an
    infrastructure service.

    Services may depend on each other. This dependency tree is honored when
    services need to be started.
    """

    def __init__(self, name, image, env=None):
        """Instantiate a new named service/component of the platform using a
        given Docker image.

        By default, a service has no dependencies. Dependencies are resolved
        and added once all Service objects have been instantiated.

        Args:
            name (string): the name of this service.
            image (string): the name of the Docker image the instances of this
                service should use.
            env (dict): a dictionary of environment variables to use as the
                base environment for all instances of this service.
        """
        Entity.__init__(self, name)
        self._image = image
        self.env = env or {}
        self._requires = set([])
        self._wants_info = set([])
        self._needed_for = set([])
        self._containers = {}

    def __repr__(self):
        return '<service:%s [%d instances]>' % (self.name,
                                                len(self._containers))

    @property
    def image(self):
        """Return the full name and tag of the image used by instances of this
        service."""
        return self._image

    def get_image_details(self):
        """Return a dictionary detailing the image used by this service, with
        its repository name and the requested tag (defaulting to latest if not
        specified)."""
        p = self._image.rsplit(':', 1)
        if len(p) > 1 and '/' in p[1]:
            p[0] = self._image
            p.pop()
        return {'repository': p[0], 'tag': len(p) > 1 and p[1] or 'latest'}

    @property
    def requires(self):
        """Returns the full set of direct and indirect dependencies of this
        service."""
        dependencies = self._requires
        for dep in dependencies:
            dependencies = dependencies.union(dep.requires)
        return dependencies

    @property
    def wants_info(self):
        """Returns the full set of "soft" dependencies this service wants
        information about through link environment variables."""
        return self._wants_info

    @property
    def needed_for(self):
        """Returns the full set of direct and indirect dependents (aka services
        that depend on this service)."""
        dependents = self._needed_for
        for dep in dependents:
            dependents = dependents.union(dep.needed_for)
        return dependents

    @property
    def containers(self):
        """Return an ordered list of instance containers for this service, by
        instance name."""
        return map(lambda c: self._containers[c],
                   sorted(self._containers.keys()))

    def add_dependency(self, service):
        """Declare that this service depends on the passed service."""
        self._requires.add(service)

    def add_dependent(self, service):
        """Declare that the passed service depends on this service."""
        self._needed_for.add(service)

    def add_wants_info(self, service):
        """Declare that this service wants information about the passed service
        via link environment variables."""
        self._wants_info.add(service)

    def register_container(self, container):
        """Register a new instance container as part of this service."""
        self._containers[container.name] = container

    def get_link_variables(self, add_internal=False):
        """Return the dictionary of all link variables from each container of
        this service. An additional variable, named '<service_name>_INSTANCES',
        contain the list of container/instance names of the service."""
        basename = re.sub(r'[^\w]', '_', self.name).upper()
        links = {}
        for c in self._containers.values():
            for name, value in c.get_link_variables(add_internal).items():
                links['{}_{}'.format(basename, name)] = value
        links['{}_INSTANCES'.format(basename)] = \
            ','.join(self._containers.keys())
        return links


class Container(Entity):
    """A Container represents an instance of a particular service that will be
    executed inside a Docker container on its target ship/host."""

    def __init__(self, name, ship, service, config, env_name='local'):
        """Create a new Container object.

        Args:
            name (string): the instance name (should be unique).
            ship (Ship): the Ship object representing the host this container
                is expected to be executed on.
            service (Service): the Service this container is an instance of.
            config (dict): the YAML-parsed dictionary containing this
                instance's configuration (ports, environment, volumes, etc.)
            env_name (string): the name of the Maestro environment.
        """
        Entity.__init__(self, name)
        self._status = None  # The container's status, cached.
        self._ship = ship
        self._service = service

        # Register this instance container as being part of its parent service.
        self._service.register_container(self)

        # Get command
        self.cmd = config.get('cmd', None)

        # Parse the port specs.
        self.ports = self._parse_ports(config.get('ports', {}))

        # Get environment variables.
        self.env = dict(service.env)
        self.env.update(config.get('env', {}))

        def env_list_expand(elt):
            return type(elt) != list and elt \
                or ' '.join(map(env_list_expand, elt))

        for k, v in self.env.items():
            if type(v) == list:
                self.env[k] = env_list_expand(v)

        # If no volume source is specified, we assume it's the same path as the
        # destination inside the container.
        self.volumes = dict(
            (src or dst, dst) for dst, src in
            config.get('volumes', {}).items())

        # Should this container run with -privileged?
        self.privileged = config.get('privileged', False)

        # Stop timeout
        self.stop_timeout = config.get('stop_timeout', 10)

        # Get limits
        limits = config.get('limits', {})
        self.cpu_shares = limits.get('cpu')
        self.mem_limit = limits.get('memory')
        if isinstance(self.mem_limit, six.string_types):
            units = {'k': 1024,
                     'm': 1024*1024,
                     'g': 1024*1024*1024}
            suffix = self.mem_limit[-1].lower()
            if suffix in units.keys():
                self.mem_limit = int(self.mem_limit[:-1]) * units[suffix]
        # TODO: add swap limit support when it will be available in docker-py
        # self.swap_limit = limits.get('swap')

        # Seed the service name, container name and host address as part of the
        # container's environment.
        self.env['MAESTRO_ENVIRONMENT_NAME'] = env_name
        self.env['SERVICE_NAME'] = self.service.name
        self.env['CONTAINER_NAME'] = self.name
        self.env['CONTAINER_HOST_ADDRESS'] = self.ship.ip

        # With everything defined, build lifecycle state helpers as configured
        self._lifecycle = self._parse_lifecycle(config.get('lifecycle', {}))

    @property
    def ship(self):
        """Returns the Ship this container runs on."""
        return self._ship

    @property
    def service(self):
        """Returns the Service this container is an instance of."""
        return self._service

    @property
    def id(self):
        """Returns the ID of this container given by the Docker daemon, or None
        if the container doesn't exist."""
        status = self.status()
        return status and status['ID'] or None

    def status(self, refresh=False):
        """Retrieve the details about this container from the Docker daemon, or
        None if the container doesn't exist."""
        if refresh or not self._status:
            try:
                self._status = self.ship.backend.inspect_container(self.name)
            except docker.client.APIError:
                pass

        return self._status

    def get_link_variables(self, add_internal=False):
        """Build and return a dictionary of environment variables providing
        linking information to this container.

        Variables are named
        '<service_name>_<container_name>_{HOST,PORT,INTERNAL_PORT}'.
        """
        basename = re.sub(r'[^\w]', '_', self.name).upper()

        port_number = lambda p: p.split('/')[0]

        links = {'{}_HOST'.format(basename): self.ship.ip}
        for name, spec in self.ports.items():
            links['{}_{}_PORT'.format(basename, name.upper())] = \
                port_number(spec['external'][1])
            if add_internal:
                links['{}_{}_INTERNAL_PORT'.format(basename, name.upper())] = \
                    port_number(spec['exposed'])
        return links

    def check_for_state(self, state):
        """Check if a particular lifecycle state has been reached by executing
        all its defined checks. If not checks are defined, it is assumed the
        state is reached immediately."""

        if state not in self._lifecycle:
            # Return None to indicate no checks were performed.
            return None

        pool = multiprocessing.Pool(len(self._lifecycle[state]))
        return reduce(lambda x, y: x and y,
                      pool.map(lambda check: check.test(),
                               self._lifecycle[state]))

    def ping_port(self, port):
        """Ping a single port, by its given name in the port mappings. Returns
        True if the port is opened and accepting connections, False
        otherwise."""
        parts = self.ports[port]['external'][1].split('/')
        if parts[1] == 'udp':
            return False

        return lifecycle.TCPPortPinger(self.ship.ip, int(parts[0])).test()

    def _parse_ports(self, ports):
        """Parse port mapping specifications for this container."""

        def validate_proto(port):
            parts = str(port).split('/')
            if len(parts) == 1:
                return '{:d}/tcp'.format(int(parts[0]))
            elif len(parts) == 2:
                try:
                    int(parts[0])
                    if parts[1] in ['tcp', 'udp']:
                        return port
                except ValueError:
                    pass
            raise exceptions.InvalidPortSpecException(
                ('Invalid port specification {}! ' +
                 'Expected format is <port> or <port>/{tcp,udp}.').format(
                    port))

        result = {}
        for name, spec in ports.items():
            # Single number, interpreted as being a TCP port number and to be
            # the same for the exposed port and external port bound on all
            # interfaces.
            if type(spec) == int:
                result[name] = {
                    'exposed': validate_proto(spec),
                    'external': ('0.0.0.0', validate_proto(spec)),
                }

            # Port spec is a string. This means either a protocol was specified
            # with /tcp or /udp, or that a mapping was provided, with each side
            # of the mapping optionally specifying the protocol.
            # External port is assumed to be bound on all interfaces as well.
            elif type(spec) == str:
                parts = list(map(validate_proto, spec.split(':')))
                if len(parts) == 1:
                    # If only one port number is provided, assumed external =
                    # exposed.
                    parts.append(parts[0])
                elif len(parts) > 2:
                    raise exceptions.InvalidPortSpecException(
                        ('Invalid port spec {} for port {} of {}! ' +
                         'Format should be "name: external:exposed".').format(
                            spec, name, self))

                if parts[0][-4:] != parts[1][-4:]:
                    raise exceptions.InvalidPortSpecException(
                        'Mismatched protocols between {} and {}!'.format(
                            parts[0], parts[1]))

                result[name] = {
                    'exposed': parts[0],
                    'external': ('0.0.0.0', parts[1]),
                }

            # Port spec is fully specified.
            elif type(spec) == dict and \
                    'exposed' in spec and 'external' in spec:
                spec['exposed'] = validate_proto(spec['exposed'])

                if type(spec['external']) != list:
                    spec['external'] = ('0.0.0.0', spec['external'])
                spec['external'] = (spec['external'][0],
                                    validate_proto(spec['external'][1]))

                result[name] = spec

            else:
                raise exceptions.InvalidPortSpecException(
                    'Invalid port spec {} for port {} of {}!'.format(
                        spec, name, self))

        return result

    def _parse_lifecycle(self, lifecycles):
        """Parse the lifecycle checks configured for this container and
        instantiate the corresponding check helpers, as configured."""
        return dict([
            (state, map(
                lambda c: (lifecycle.LifecycleHelperFactory
                           .from_config(self, c)),
                checks)) for state, checks in lifecycles.items()])

    def __repr__(self):
        return '<container:%s/%s [on %s]>' % \
            (self.name, self.service.name, self.ship.name)

    def __lt__(self, other):
        return self.name < other.name

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

########NEW FILE########
__FILENAME__ = exceptions
# Copyright (C) 2013 SignalFuse, Inc.
#
# Docker container orchestration utility.


class MaestroException(Exception):
    """Base class for Maestro exceptions."""
    pass


class DependencyException(MaestroException):
    """Dependency resolution error."""
    pass


class ParameterException(MaestroException):
    """Invalid parameter passed to Maestro."""
    pass


class OrchestrationException(MaestroException):
    """Error during the execution of the orchestration score."""
    pass


class InvalidPortSpecException(MaestroException):
    "Error thrown when a port spec is in an invalid format."""
    pass


class InvalidLifecycleCheckConfigurationException(MaestroException):
    "Error thrown when a lifecycle check isn't configured properly."""
    pass

########NEW FILE########
__FILENAME__ = logstash
#!/usr/bin/env python

# Copyright (C) 2014 SignalFuse, Inc.

# Maestro extension that can be used for wrapping the execution of a
# long-running service with log management scaffolding, potentially sending the
# log output to a file, or through Pipestash, or both, depending on the use
# case and parameters.

import os
import random
import signal
import subprocess

from ...guestutils import get_container_name, get_service_name, get_node_list


def run_service(cmd, logtype='log', logbase=None, logtarget=None):
    """Wrap the execution of a service with the necessary logging nets.

    If logbase is provided (it is by default), log output will be redirected
    (or teed) to a file named after the container executing the service inside
    the logbase directory.

    If Redis nodes are available in the environment as referenced by the given
    logtarget, log output will be streamed via pipestash to one of the
    available node containers, chosen at random when the service starts.

    The way this is accomplished varied on whether logbase is provided or not,
    and whether Redis nodes are available:

        - if neither, log output flows to stdout and will be captured by
          Docker;
        - if logbase is provided, but no Redis nodes are available, the
          output of the service is directly redirected to the log file;
        - if logbase is not provided, but Redis nodes are available, the
          output of the service is piped to pipestash;
        - if logbase is provided and Redis nodes are available, the output
          of the service is piped to a tee that will write the log file, and
          the output of the tee is piped to pipestash.

    The whole pipeline, whatever its construct is, waits for the service to
    terminate. SIGTERM is also redirected from the parent to the service.
    """
    if type(cmd) == str:
        cmd = cmd.split(' ')

    log = logbase \
        and os.path.join(logbase, '{}.log'.format(get_container_name())) \
        or None
    if logbase and not os.path.exists(logbase):
        os.makedirs(logbase)

    redis = logtarget \
        and get_node_list(logtarget, ports=['redis'], minimum=0) \
        or None
    stdout = redis and subprocess.PIPE or (log and open(log, 'w+') or None)

    # Start the service with the provided command.
    service = subprocess.Popen(cmd, stdout=stdout,
                               stderr=subprocess.STDOUT)
    last = service

    # Connect SIGTERM to the service process.
    signal.signal(signal.SIGTERM, lambda signum, frame: service.terminate())

    if redis:
        if log:
            # Tee to a local log file.
            tee = subprocess.Popen(['tee', log], stdin=last.stdout,
                                   stdout=subprocess.PIPE)
            last.stdout.close()
            last = tee

        pipestash = subprocess.Popen(
            ['pipestash', '-t', logtype,
             '-r', 'redis://{}/0'.format(random.choice(redis)),
             '-R', 'logstash',
             '-f', 'service={}'.format(get_service_name()),
             '-S', get_container_name()],
            stdin=last.stdout)
        last.stdout.close()
        last = pipestash

    # Wait for the service to exit and return its return code.
    last.communicate()
    return service.wait()

########NEW FILE########
__FILENAME__ = guestutils
#!/usr/bin/env python

# Copyright (C) 2013 SignalFuse, Inc.
# Utility functions for service start scripts that help work with Maestro
# orchestration.

import os
import re

from . import entities


class MaestroEnvironmentError(Exception):
    pass


def get_environment_name():
    """Return the name of the environment the container calling this in a part
    of."""
    return os.environ.get('MAESTRO_ENVIRONMENT_NAME', 'local')


def get_service_name():
    """Returns the service name of the container calling it."""
    name = os.environ.get('SERVICE_NAME', '')
    if not name:
        raise MaestroEnvironmentError('Service name was not defined')
    return name


def get_container_name():
    """Returns the name of the container calling it."""
    name = os.environ.get('CONTAINER_NAME', '')
    if not name:
        raise MaestroEnvironmentError('Container name was not defined')
    return name


def get_container_host_address():
    """Return the publicly-addressable IP address of the host of the
    container."""
    address = os.environ.get('CONTAINER_HOST_ADDRESS', '')
    if not address:
        raise MaestroEnvironmentError('Container host address was not defined')
    return address


def get_container_internal_address():
    """Return the internal, private IP address assigned to the container."""
    ship = entities.Ship('host', get_container_host_address())
    details = ship.backend.inspect_container(get_container_name())
    return str(details['NetworkSettings']['IPAddress'])


def get_port(name, default=None):
    """Return the exposed (internal) port number for the given port, or the
    given default if not found."""
    return get_specific_exposed_port(
        get_service_name(),
        get_container_name(),
        name, default)


def get_specific_host(service, container):
    """Return the hostname/address of a specific container/instance of the
    given service."""
    try:
        return os.environ['{}_{}_HOST'.format(_to_env_var_name(service),
                                              _to_env_var_name(container))]
    except:
        raise MaestroEnvironmentError(
            'No host defined for container {} of service {}'
            .format(container, service))


def get_specific_exposed_port(service, container, port, default=None):
    """Return the exposed (internal) port number of a specific port of a
    specific container from a given service."""
    try:
        return int(os.environ.get(
            '{}_{}_{}_INTERNAL_PORT'.format(_to_env_var_name(service),
                                            _to_env_var_name(container),
                                            _to_env_var_name(port)).upper(),
            default))
    except:
        raise MaestroEnvironmentError(
            'No internal port {} defined for container {} of service {}'
            .format(port, container, service))


def get_specific_port(service, container, port, default=None):
    """Return the external port number of a specific port of a specific
    container from a given service."""
    try:
        return int(os.environ.get(
            '{}_{}_{}_PORT'.format(_to_env_var_name(service),
                                   _to_env_var_name(container),
                                   _to_env_var_name(port)).upper(),
            default))
    except:
        raise MaestroEnvironmentError(
            'No port {} defined for container {} of service {}'
            .format(port, container, service))


def get_node_list(service, ports=[], minimum=1):
    """Build a list of nodes for the given service from the environment,
    eventually adding the ports from the list of port names. The resulting
    entries will be of the form 'host[:port1[:port2]]' and sorted by container
    name."""
    nodes = []

    for container in _get_service_instance_names(service):
        node = get_specific_host(service, container)
        for port in ports:
            node = '{}:{}'.format(node,
                                  get_specific_port(service, container, port))
        nodes.append(node)

    if len(nodes) < minimum:
        raise MaestroEnvironmentError(
            'No or not enough {} nodes configured'.format(service))
    return nodes


def _to_env_var_name(s):
    """Transliterate a service or container name into the form used for
    environment variable names."""
    return re.sub(r'[^\w]', '_', s).upper()


def _get_service_instance_names(service):
    """Return the list of container/instance names for the given service."""
    key = '{}_INSTANCES'.format(_to_env_var_name(service))
    if key not in os.environ:
        return []
    return os.environ[key].split(',')

########NEW FILE########
__FILENAME__ = lifecycle
# Copyright (C) 2014 SignalFuse, Inc.
#
# Docker container orchestration utility.

import socket
import subprocess
import time

from . import exceptions


class BaseLifecycleHelper:
    """Base class for lifecycle helpers."""

    def test(self):
        """State helpers must implement this method to perform the state test.
        The method must return True if the test succeeds, False otherwise."""
        raise NotImplementedError


class TCPPortPinger(BaseLifecycleHelper):
    """
    Lifecycle state helper that "pings" a particular TCP port.
    """

    DEFAULT_MAX_WAIT = 60

    def __init__(self, host, port, attempts=1):
        """Create a new TCP port pinger for the given host and port. The given
        number of attempts will be made, until the port is open or we give
        up."""
        self.host = host
        self.port = int(port)
        self.attempts = int(attempts)

    def __repr__(self):
        return 'PortPing(tcp://{}:{}, {} attempts)'.format(
            self.host, self.port, self.attempts)

    def __ping_port(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((self.host, self.port))
            s.close()
            return True
        except Exception:
            return False

    def test(self):
        retries = self.attempts
        while retries > 0:
            if self.__ping_port():
                return True

            retries -= 1
            if retries > 0:
                time.sleep(1)
        return False

    @staticmethod
    def from_config(container, config):
        if config['port'] not in container.ports:
            raise exceptions.InvalidLifecycleCheckConfigurationException(
                'Port {} is not defined by {}!'.format(
                    config['port'], container.name))

        parts = container.ports[config['port']]['external'][1].split('/')
        if parts[1] == 'udp':
            raise exceptions.InvalidLifecycleCheckConfigurationException(
                'Port {} is not TCP!'.format(config['port']))

        return TCPPortPinger(
            container.ship.ip, int(parts[0]),
            attempts=config.get('max_wait', TCPPortPinger.DEFAULT_MAX_WAIT))


class ScriptExecutor(BaseLifecycleHelper):
    """
    Lifecycle state helper that executes a script and uses the exit code as the
    success value.
    """

    def __init__(self, command):
        self.command = command

    def __repr__(self):
        return 'ScriptExec({})'.format(self.command)

    def test(self):
        return subprocess.call(self.command, shell=True) == 0

    @staticmethod
    def from_config(container, config):
        return ScriptExecutor(config['command'])


class LifecycleHelperFactory:

    HELPERS = {
        'tcp': TCPPortPinger,
        'exec': ScriptExecutor,
    }

    @staticmethod
    def from_config(container, config):
        return (LifecycleHelperFactory.HELPERS[config['type']]
                .from_config(container, config))

########NEW FILE########
__FILENAME__ = maestro
# Copyright (C) 2013 SignalFuse, Inc.
#
# Docker container orchestration utility.

from . import entities
from . import exceptions
from . import plays


class Conductor:
    """The Maestro; the Conductor.

    The conductor is in charge of parsing and analyzing the environment
    description and carrying out the orchestration plays to act on the services
    and containers described in the environment.
    """

    def __init__(self, config):
        self._config = config

        # Create container ships.
        self._ships = dict(
            (k, entities.Ship(
                k, v['ip'],
                docker_port=v.get('docker_port',
                                  entities.Ship.DEFAULT_DOCKER_PORT),
                docker_endpoint=v.get('docker_endpoint'),
                timeout=v.get('timeout')))
            for k, v in self._config['ships'].items())

        # Register defined private Docker registries authentications
        self._registries = self._config.get('registries') or {}
        for name, registry in self._registries.items():
            if 'username' not in registry or 'password' not in registry:
                raise exceptions.OrchestrationException(
                    'Incomplete registry auth data for {}!'.format(name))

        # Build all the entities.
        self._services = {}
        self._containers = {}

        for kind, service in self._config['services'].items():
            self._services[kind] = entities.Service(kind, service['image'],
                                                    service.get('env', {}))

            for name, instance in service['instances'].items():
                self._containers[name] = \
                    entities.Container(name,
                                       self._ships[instance['ship']],
                                       self._services[kind],
                                       instance,
                                       self._config['name'])

        # Resolve dependencies between services.
        for kind, service in self._config['services'].items():
            for dependency in service.get('requires', []):
                self._services[kind].add_dependency(self._services[dependency])
                self._services[dependency].add_dependent(self._services[kind])
            for wants_info in service.get('wants_info', []):
                self._services[kind].add_wants_info(self._services[wants_info])

        # Provide link environment variables to each container of each service
        # that requires it or wants it.
        for service in self._services.values():
            for container in service.containers:
                # Containers always know about their peers in the same service.
                container.env.update(service.get_link_variables(True))
                # Containers also get links from the service's dependencies.
                for dependency in service.requires.union(service.wants_info):
                    container.env.update(dependency.get_link_variables())

    @property
    def registries(self):
        """Returns the list of registries known to this conductor."""
        return list(self._registries.keys())

    @property
    def services(self):
        """Returns the names of all the services defined in the environment."""
        return list(self._services.keys())

    @property
    def containers(self):
        """Returns the names of all the containers defined in the
        environment."""
        return list(self._containers.keys())

    def get_registry(self, name):
        """Returns a registry, by name."""
        return self._registries[name]

    def get_service(self, name):
        """Returns a service, by name."""
        return self._services[name]

    def get_container(self, name):
        """Returns a container, by name."""
        return self._containers[name]

    def _order_dependencies(self, pending=[], ordered=[], forward=True):
        """Order the given set of containers into an order respecting the
        service dependencies in the given direction.

        The list of containers to order should be passed in the pending
        parameter. The ordered list will be returned by the function (the
        ordered parameter is for internal recursion use only).

        The direction of the dependencies controls whether the ordering should
        be constructed for startup (dependencies first) or shutdown (dependents
        first).
        """
        wait = []
        for container in pending:
            deps = self._gather_dependencies([container], forward)
            if deps and not deps.issubset(set(ordered + [container])):
                wait.append(container)
            else:
                ordered.append(container)

        # If wait and pending are not empty and have the same length, it means
        # we were not able to order any container from the pending list (they
        # all went to the wait list). This means the dependency tree cannot be
        # resolved and an error should be raised.
        if wait and pending and len(wait) == len(pending):
            raise exceptions.DependencyException(
                'Cannot resolve dependencies for containers {}!'.format(
                    map(lambda x: x.name, wait)))

        # As long as 'wait' has elements, keep recursing to resolve
        # dependencies. Otherwise, returned the ordered list, which should now
        # be final.
        return wait and self._order_dependencies(wait, ordered, forward) \
            or ordered

    def _gather_dependencies(self, containers, forward=True):
        """Transitively gather all containers from the dependencies or
        dependents (depending on the value of the forward parameter) services
        that the services the given containers are members of."""
        result = set(containers or self._containers.values())
        for container in result:
            deps = container.service.requires if forward \
                else container.service.needed_for
            deps = reduce(lambda x, y: x.union(y),
                          map(lambda s: s.containers, deps),
                          set([]))
            result = result.union(deps)
        return result

    def _to_containers(self, things):
        """Transform a list of "things", container names or service names, to
        an expended list of Container objects."""
        def parse_thing(s):
            if s in self._containers:
                return [self._containers[s]]
            elif s in self._services:
                return self._services[s].containers
            raise exceptions.OrchestrationException(
                '{} is neither a service nor a container!'.format(s))
        return reduce(lambda x, y: x+y, map(parse_thing, things), [])

    def _ordered_containers(self, things, forward=True):
        """Return the ordered list of containers from the list of names passed
        to it (either container names or service names).

        Args:
            things (list<string>):
            forward (boolean): controls the direction of the dependency tree.
        """
        return self._order_dependencies(
            sorted(self._gather_dependencies(self._to_containers(things),
                                             forward)),
            forward=forward)

    def status(self, things=[], only=False, **kwargs):
        """Display the status of the given services and containers, but only
        looking at the container's state, not the application availability.

        Args:
            things (set<string>): The things to show the status of.
            only (boolean): Whether to only show the status of the specified
                things, or their dependencies as well.
        """
        containers = self._ordered_containers(things) \
            if not only else self._to_containers(things)
        plays.Status(containers).run()

    def fullstatus(self, things=[], only=False, **kwargs):
        """Display the status of the given services and containers, pinging for
        application availability (slower).

        Args:
            things (set<string>): The things to show the status of.
            only (boolean): Whether to only show the status of the specified
                things, or their dependencies as well.
        """
        containers = self._ordered_containers(things) \
            if not only else self._to_containers(things)
        plays.FullStatus(containers).run()

    def start(self, things=[], refresh_images=False, only=False, **kwargs):
        """Start the given container(s) and services(s). Dependencies of the
        requested containers and services are started first.

        Args:
            things (set<string>): The list of things to start.
            refresh_images (boolean): Whether to force an image pull for each
                container or not.
            only (boolean): Whether to act on only the specified things, or
                their dependencies as well.
        """
        containers = self._ordered_containers(things) \
            if not only else self._to_containers(things)
        plays.Start(containers, self._registries, refresh_images).run()

    def restart(self, things=[], refresh_images=False, only=False, **kwargs):
        """Restart the given container(s) and services(s). Dependencies of the
        requested containers and services are started first.

        Args:
            things (set<string>): The list of things to start.
            refresh_images (boolean): Whether to force an image pull for each
                container or not before starting it.
            only (boolean): Whether to act on only the specified things, or
                their dependencies as well.
        """
        containers = self._ordered_containers(things) \
            if not only else self._to_containers(things)
        plays.Stop(containers).run()
        plays.Start(containers, self._registries, refresh_images).run()

    def stop(self, things=[], only=False, **kwargs):
        """Stop the given container(s) and service(s).

        This one is a bit more tricky because we don't want to look at the
        dependencies of the containers and services we want to stop, but at
        which services depend on the containers and services we want to stop.
        Unless of course the only parameter is set to True.

        Args:
            things (set<string>): The list of things to stop.
            only (boolean): Whether to act on only the specified things, or
                their dependencies as well.
        """
        containers = self._ordered_containers(things, False) \
            if not only else self._to_containers(things)
        plays.Stop(containers).run()

    def logs(self, things=[], **kwargs):
        """Display the logs of the given container."""
        containers = self._to_containers(things)
        if len(containers) != 1:
            raise exceptions.ParameterException(
                'Logs can only be shown for a single container!')

        container = containers[0]

        o = plays.OutputFormatter()
        o.pending('Inspecting container status...')
        status = container.status()
        if not status:
            return

        try:
            stream = status['State']['Running'] and kwargs.get('follow')
            if stream:
                o.pending(
                    'Now streaming logs for {}. New output will appear below.'
                    .format(container.name))
                logs = container.ship.backend.attach(container.id, stream=True)
            else:
                o.pending(
                    'Requesting logs for {}. This may take a while...'
                    .format(container.name))
                logs = container.ship.backend.logs(container.id).split('\n')
                logs = logs[-int(kwargs.get('n', len(logs))):]

            o.pending('\033[2K')
            for line in logs:
                print(line.rstrip())
        except:
            pass

########NEW FILE########
__FILENAME__ = plays
# Copyright (C) 2013 SignalFuse, Inc.
#
# Docker container orchestration utility.

from __future__ import print_function

import collections
import json
import sys
import time

from . import exceptions


# Some utility functions for output.
def color(cond):
    """Returns 32 (green) or 31 (red) depending on the validity of the given
    condition."""
    return cond and 32 or 31


def up(cond):
    """Returns 'up' or 'down' depending on the validity of the given
    condition."""
    return cond and 'up' or 'down'


class BaseOrchestrationPlay:
    """Base class for orchestration plays, holds the ordered list containers to
    act on."""

    def __init__(self, containers=[]):
        self._containers = containers

    def run(self):
        raise NotImplementedError


class OutputFormatter:
    """Output formatter for nice, progressive terminal output.

    Manages the output of a progressively updated terminal line, with "in
    progress" labels and a "committed" base label.
    """
    def __init__(self, prefix=None):
        self._committed = prefix

    def commit(self, s=None):
        if self._committed and s:
            self._committed = '{} {}'.format(self._committed, s)
        elif not self._committed and s:
            self._committed = s
        print('{}\033[K\r'.format(self._committed), end='')
        sys.stdout.flush()

    def pending(self, s):
        if self._committed and s:
            print('{} {}\033[K\r'.format(self._committed, s), end='')
        elif not self._committed and s:
            print('{}\033[K\r'.format(s), end='')
        sys.stdout.flush()

    def end(self):
        print('')
        sys.stdout.flush()


class FullStatus(BaseOrchestrationPlay):
    """A Maestro orchestration play that displays the status of the given
    services and/or instance containers."""

    def __init__(self, containers=[]):
        BaseOrchestrationPlay.__init__(self, containers)

    def run(self):
        print('{:>3s}  {:<20s} {:<15s} {:<20s} {:<15s} {:<10s}'.format(
            '  #', 'INSTANCE', 'SERVICE', 'SHIP', 'CONTAINER', 'STATUS'))

        for order, container in enumerate(self._containers, 1):
            o = OutputFormatter(
                ('{:>3d}. \033[;1m{:<20.20s}\033[;0m {:<15.15s} ' +
                 '{:<20.20s}').format(order,
                                      container.name,
                                      container.service.name,
                                      container.ship.name))

            try:
                o.pending('checking container...')
                status = container.status()
                o.commit('\033[{:d};1m{:<15s}\033[;0m'.format(
                    color(status and status['State']['Running']),
                    (status and status['State']['Running']
                        and container.id[:7] or 'down')))

                o.pending('checking service...')
                running = status and status['State']['Running']
                o.commit('\033[{:d};1m{:<4.4s}\033[;0m'.format(color(running),
                                                               up(running)))

                for name, port in container.ports.iteritems():
                    o.end()
                    o = OutputFormatter('     >>')
                    o.pending('{:>9.9s}:{:s}'.format(port['external'][1],
                                                     name))
                    ping = container.ping_port(name)
                    o.commit('\033[{:d};1m{:>9.9s}\033[;0m:{:s}'.format(
                        color(ping), port['external'][1], name))
            except Exception:
                o.commit('\033[31;1m{:<15s} {:<10s}\033[;0m'.format(
                    'host down', 'down'))
            o.end()


class Status(BaseOrchestrationPlay):
    """A less advanced, but faster status display orchestration play that only
    looks at the presence and status of the containers. Status information is
    bulk-polled from each ship's Docker daemon."""

    def __init__(self, containers=[]):
        BaseOrchestrationPlay.__init__(self, containers)

    def run(self):
        status = {}
        o = OutputFormatter()
        for ship in set([container.ship for container in self._containers]):
            o.pending('Gathering container information from {} ({})...'.format(
                ship.name, ship.ip))
            try:
                status.update(dict((c['Names'][0][1:], c)
                              for c in ship.backend.containers()))
            except:
                pass

        o.commit('{:>3s}  {:<20s} {:<15s} {:<20s} {:<15s}'.format(
            '  #', 'INSTANCE', 'SERVICE', 'SHIP', 'CONTAINER'))
        o.end()

        for order, container in enumerate(self._containers, 1):
            o = OutputFormatter(
                ('{:>3d}. \033[;1m{:<20.20s}\033[;0m {:<15.15s} ' +
                 '{:<20.20s}').format(order,
                                      container.name,
                                      container.service.name,
                                      container.ship.name))

            s = status.get(container.name)
            if s and s['Status'].startswith('Up'):
                cid = s.get('ID', s.get('Id', None))
                o.commit('\033[32;1m{}\033[;0m'.format(cid[:7]))
            else:
                o.commit('\033[31;1mdown\033[;0m')
            o.end()


class Start(BaseOrchestrationPlay):
    """A Maestro orchestration play that will execute the start sequence of the
    requested services, starting each container for each instance of the
    services, in the given start order, waiting for each container's
    application to become available before moving to the next one."""

    def __init__(self, containers=[], registries={}, refresh_images=False):
        BaseOrchestrationPlay.__init__(self, containers)
        self._registries = registries
        self._refresh_images = refresh_images

    def run(self):
        print('{:>3s}  {:<20s} {:<15s} {:<20s} {:<15s} {:<10s}'.format(
            '  #', 'INSTANCE', 'SERVICE', 'SHIP', 'CONTAINER', 'STATUS'))

        for order, container in enumerate(self._containers, 1):
            o = OutputFormatter(
                ('{:>3d}. \033[;1m{:<20.20s}\033[;0m {:<15.15s} ' +
                 '{:<20.20s}').format(order,
                                      container.name,
                                      container.service.name,
                                      container.ship.name))

            error = None
            try:
                # TODO: None is used to indicate that no action was performed
                # because the container and its application were already
                # running. This makes the following code not very nice and this
                # could be improved.
                result = self._start_container(o, container)
                o.commit('\033[{:d};1m{:<10s}\033[;0m'.format(
                    color(result is not False),
                    result is None and 'up' or
                        (result and 'started' or
                            'service did not start!')))
                if result is False:
                    error = [
                        ('Halting start sequence because {} failed to start!'
                            .format(container)),
                        container.ship.backend.logs(container.id)]
                    raise exceptions.OrchestrationException('\n'.join(error))
            except Exception:
                o.commit('\033[31;1mfailed to start container!\033[;0m')
                raise
            finally:
                o.end()

    def _update_pull_progress(self, progress, last):
        """Update an image pull progress map with latest download progress
        information for one of the image layers, and return the average of the
        download progress of all layers as an indication of the overall
        progress of the pull."""
        try:
            last = json.loads(last)
            progress[last['id']] = last['status'] == 'Download complete' \
                and 100 \
                or (100.0 * last['progressDetail']['current'] /
                    last['progressDetail']['total'])
        except:
            pass

        return reduce(lambda x, y: x+y, progress.values()) / len(progress) \
            if progress else 0

    def _wait_for_status(self, container, cond, retries=10):
        while retries >= 0:
            status = container.status(refresh=True)
            if cond(status):
                return True
            time.sleep(0.5)
            retries -= 1
        return False

    def _login_to_registry(self, o, container):
        """Extract the registry name from the image needed for the container,
        and if authentication data is provided for that registry, login to it
        so a subsequent pull operation can be performed."""
        image = container.service.get_image_details()
        if image['repository'].find('/') <= 0:
            return

        registry, repo_name = image['repository'].split('/', 1)
        if registry not in self._registries:
            return

        o.pending('logging in to {}...'.format(registry))
        try:
            container.ship.backend.login(**self._registries[registry])
        except Exception as e:
            raise exceptions.OrchestrationException(
                'Login to {} failed: {}'.format(registry, e))

    def _start_container(self, o, container):
        """Start the given container.

        If the container and its application are already running, no action is
        performed and the function returns None to indicate that. Otherwise, a
        new container must be created and started. To achieve this, any
        existing container of the same name is first removed. Then, if
        necessary or if requested, the container image is pulled from its
        registry. Finally, the container is created and started, configured as
        necessary. We then wait for the application to start and return True or
        False depending on whether the start was successful."""
        o.pending('checking service...')
        status = container.status(refresh=True)

        if status and status['State']['Running']:
            o.commit('\033[34;0m{:<15s}\033[;0m'.format(container.id[:7]))
            # We use None as a special marker showing the container and the
            # application were already running.
            return None

        # Otherwise we need to start it.
        if container.id:
            o.pending('removing old container {}...'.format(container.id[:7]))
            container.ship.backend.remove_container(container.id)

        # Check if the image is available, or if we need to pull it down.
        image = container.service.get_image_details()
        if self._refresh_images or \
                not filter(lambda i: container.service.image in i['RepoTags'],
                           container.ship.backend.images(image['repository'])):
            # First, attempt to login if we can/need to.
            self._login_to_registry(o, container)
            o.pending('pulling image {}...'.format(container.service.image))
            progress = {}
            for dlstatus in container.ship.backend.pull(stream=True, **image):
                o.pending('... {:.1f}%'.format(
                    self._update_pull_progress(progress, dlstatus)))

        # Create and start the container.
        o.pending('creating container from {}...'.format(
            container.service.image))
        ports = container.ports \
            and map(lambda p: tuple(p['exposed'].split('/')),
                    container.ports.itervalues()) \
            or None
        container.ship.backend.create_container(
            image=container.service.image,
            hostname=container.name,
            name=container.name,
            environment=container.env,
            volumes=container.volumes.values(),
            mem_limit=container.mem_limit,
            cpu_shares=container.cpu_shares,
            ports=ports,
            detach=True,
            command=container.cmd)

        o.pending('waiting for container creation...')
        if not self._wait_for_status(container, lambda x: x):
            raise exceptions.OrchestrationException(
                'Container status could not be obtained after creation!')
        o.commit('\033[32;1m{:<15s}\033[;0m'.format(container.id[:7]))

        o.pending('starting container {}...'.format(container.id[:7]))
        ports = collections.defaultdict(list) if container.ports else None
        if ports is not None:
            for port in container.ports.values():
                ports[port['exposed']].append(
                    (port['external'][0], port['external'][1].split('/')[0]))
        container.ship.backend.start(container.id,
                                     binds=container.volumes,
                                     port_bindings=ports,
                                     privileged=container.privileged)

        # Waiting one second and checking container state again to make sure
        # initialization didn't fail.
        o.pending('waiting for container initialization...')
        if not self._wait_for_status(container,
                                     lambda x: x and x['State']['Running']):
            raise exceptions.OrchestrationException(
                'Container status could not be obtained after start!')

        # Wait up for the container's application to come online.
        o.pending('waiting for service...')
        return container.check_for_state('running') is not False


class Stop(BaseOrchestrationPlay):
    """A Maestro orchestration play that will stop and remove the containers of
    the requested services. The list of containers should be provided reversed
    so that dependent services are stopped first."""

    def __init__(self, containers=[]):
        BaseOrchestrationPlay.__init__(self, containers)

    def run(self):
        print('{:>3s}  {:<20s} {:<15s} {:<20s} {:<15s} {:<10s}'.format(
            '  #', 'INSTANCE', 'SERVICE', 'SHIP', 'CONTAINER', 'STATUS'))

        for order, container in enumerate(self._containers):
            o = OutputFormatter(
                ('{:>3d}. \033[;1m{:<20.20s}\033[;0m {:<15.15s} ' +
                 '{:<20.20s}').format(len(self._containers) - order,
                                      container.name,
                                      container.service.name,
                                      container.ship.name))

            o.pending('checking container...')
            try:
                status = container.status(refresh=True)
                if not status or not status['State']['Running']:
                    o.commit('{:<15s} {:<10s}'.format('n/a', 'already down'))
                    o.end()
                    continue
            except:
                o.commit('\033[31;1m{:<15s} {:<10s}\033[;0m'.format(
                    'host down', 'down'))
                o.end()
                continue

            o.commit('{:<15s}'.format(container.id[:7]))

            try:
                o.pending('stopping service...')
                container.ship.backend.stop(container.id,
                                            timeout=container.stop_timeout)
                container.check_for_state('stopped')
                o.commit('\033[32;1mstopped\033[;0m')
            except:
                o.commit('\033[31;1mfail!\033[;0m')

            o.end()

########NEW FILE########
__FILENAME__ = version
name = 'maestro'
version = '0.1.8'

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python

# Copyright (C) 2013 SignalFuse, Inc.
#
# Docker container orchestration utility.

import argparse
import jinja2
import logging
import sys
import os
import yaml

from . import exceptions, maestro

# Define the commands
ACCEPTED_COMMANDS = ['status', 'fullstatus', 'start', 'stop', 'restart',
                     'logs']


def load_config(options):
    """Preprocess the input config file through Jinja2 before loading it as
    JSON."""
    if options.file == '-':
        template = jinja2.Template(sys.stdin.read())
    else:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(options.file)),
            extensions=['jinja2.ext.with_'])
        template = env.get_template(os.path.basename(options.file))

    return yaml.load(template.render(env=os.environ))


def create_parser():
    parser = argparse.ArgumentParser(
        prog='maestro',
        description='Docker container orchestrator.')
    parser.add_argument('command', nargs='?',
                        choices=ACCEPTED_COMMANDS,
                        default='status',
                        help='orchestration command to execute')
    parser.add_argument('things', nargs='*', metavar='thing',
                        help='container(s) or service(s) to act on')
    parser.add_argument('-f', '--file', nargs='?', default='-', metavar='FILE',
                        help=('read environment description from FILE ' +
                              '(use - for stdin)'))
    parser.add_argument('-c', '--completion', metavar='CMD',
                        help=('list commands, services or containers in ' +
                              'environment based on CMD'))
    parser.add_argument('-r', '--refresh-images', action='store_const',
                        const=True, default=False,
                        help='force refresh of container images from registry')
    parser.add_argument('-F', '--follow', action='store_const',
                        const=True, default=False,
                        help='follow logs as they are generated')
    parser.add_argument('-n', metavar='LINES', default=15,
                        help='Only show the last LINES lines for logs')
    parser.add_argument('-o', '--only', action='store_const',
                        const=True, default=False,
                        help='only affect the selected container or service')

    return parser


def main(args=None):
    options = create_parser().parse_args(args)
    config = load_config(options)

    # Shutup urllib3, wherever it comes from.
    (logging.getLogger('requests.packages.urllib3.connectionpool')
            .setLevel(logging.WARN))
    (logging.getLogger('urllib3.connectionpool')
            .setLevel(logging.WARN))

    c = maestro.Conductor(config)
    if options.completion is not None:
        args = filter(lambda x: not x.startswith('-'),
                      options.completion.split(' '))
        if len(args) == 2:
            prefix = args[1]
            choices = ACCEPTED_COMMANDS
        elif len(args) >= 3:
            prefix = args[len(args)-1]
            choices = c.services + c.containers
        else:
            return 0

        print(' '.join(filter(lambda x: x.startswith(prefix), set(choices))))
        return 0

    try:
        options.things = set(options.things)
        getattr(c, options.command)(**vars(options))
    except exceptions.MaestroException as e:
        sys.stderr.write('{}\n'.format(e))
        return 1
    except KeyboardInterrupt:
        return 1


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = unittests
#!/usr/bin/env python

import os
import unittest

from maestro import entities, exceptions, maestro, lifecycle
from maestro.__main__ import load_config, create_parser

class EntityTest(unittest.TestCase):

    def test_get_name(self):
        self.assertEqual(entities.Entity('foo').name, 'foo')

class ServiceTest(unittest.TestCase):

    def test_get_image(self):
        service = entities.Service('foo', 'stackbrew/ubuntu:13.10')
        self.assertEqual(service.image, 'stackbrew/ubuntu:13.10')

    def test_get_image_details_basic(self):
        service = entities.Service('foo', 'stackbrew/ubuntu:13.10')
        d = service.get_image_details()
        self.assertEqual(d['repository'], 'stackbrew/ubuntu')
        self.assertEqual(d['tag'], '13.10')

    def test_get_image_details_notag(self):
        service = entities.Service('foo', 'stackbrew/ubuntu')
        d = service.get_image_details()
        self.assertEqual(d['repository'], 'stackbrew/ubuntu')
        self.assertEqual(d['tag'], 'latest')

    def test_get_image_details_custom_registry(self):
        service = entities.Service('foo', 'quay.io/foo/bar:13.10')
        d = service.get_image_details()
        self.assertEqual(d['repository'], 'quay.io/foo/bar')
        self.assertEqual(d['tag'], '13.10')

    def test_get_image_details_custom_port(self):
        service = entities.Service('foo', 'quay.io:8081/foo/bar:13.10')
        d = service.get_image_details()
        self.assertEqual(d['repository'], 'quay.io:8081/foo/bar')
        self.assertEqual(d['tag'], '13.10')

    def test_get_image_details_custom_port_notag(self):
        service = entities.Service('foo', 'quay.io:8081/foo/bar')
        d = service.get_image_details()
        self.assertEqual(d['repository'], 'quay.io:8081/foo/bar')
        self.assertEqual(d['tag'], 'latest')


class ContainerTest(unittest.TestCase):

    def test_env_propagates_from_service(self):
        service_env = {'ENV_VAR': 'value'}
        container_env = {'OTHER_ENV_VAR': 'other-value'}
        service = entities.Service('foo', 'stackbrew/ubuntu', service_env)
        container = entities.Container('foo1', entities.Ship('ship', 'shipip'),
                                       service, config={'env': container_env})
        for k, v in service_env.items():
            self.assertIn(k, container.env)
            self.assertEqual(v, container.env[k])
        for k, v in container_env.items():
            self.assertIn(k, container.env)
            self.assertEqual(v, container.env[k])


class BaseConfigUsingTest(unittest.TestCase):

    def _get_config(self, name):
        return load_config(
            create_parser().parse_args([
                '-f',
                os.path.join(os.path.dirname(__file__),
                             'yaml/{}.yaml'.format(name))
            ])
        )


class ConductorTest(BaseConfigUsingTest):

    def test_empty_registry_list(self):
        config = self._get_config('empty_registries')
        c = maestro.Conductor(config)
        self.assertIsNot(c.registries, None)
        self.assertEqual(c.registries, [])


class ConfigTest(BaseConfigUsingTest):

    def test_yaml_parsing_test1(self):
        """Make sure the env variables are working."""
        os.environ['BAR'] = 'bar'
        config = self._get_config('test_env')
        self.assertEqual('bar', config['foo'])


class LifecycleHelperTest(unittest.TestCase):

    def _get_container(self):
        ship = entities.Ship('ship', 'ship.ip')
        service = entities.Service('foo', 'stackbrew/ubuntu')
        return entities.Container('foo1', ship, service,
            config={'ports': {'server': '4242/tcp', 'data': '4243/udp'}})

    def test_parse_checker_exec(self):
        container = self._get_container()
        c = lifecycle.LifecycleHelperFactory.from_config(container,
            {'type': 'exec', 'command': 'exit 1'})
        self.assertIsNot(c, None)
        self.assertIsInstance(c, lifecycle.ScriptExecutor)
        self.assertEqual(c.command, 'exit 1')

    def test_parse_checker_tcp(self):
        container = self._get_container()
        c = lifecycle.LifecycleHelperFactory.from_config(container,
            {'type': 'tcp', 'port': 'server'})
        self.assertIsInstance(c, lifecycle.TCPPortPinger)
        self.assertEqual(c.host, container.ship.ip)
        self.assertEqual(c.port, 4242)
        self.assertEqual(c.attempts, lifecycle.TCPPortPinger.DEFAULT_MAX_WAIT)

    def test_parse_checker_tcp(self):
        container = self._get_container()
        c = lifecycle.LifecycleHelperFactory.from_config(container,
            {'type': 'tcp', 'port': 'server', 'max_wait': 2})
        self.assertIsInstance(c, lifecycle.TCPPortPinger)
        self.assertEqual(c.host, container.ship.ip)
        self.assertEqual(c.port, 4242)
        self.assertEqual(c.attempts, 2)

    def test_parse_checker_tcp_unknown_port(self):
        container = self._get_container()
        self.assertRaises(exceptions.InvalidLifecycleCheckConfigurationException,
            lifecycle.LifecycleHelperFactory.from_config,
            container, {'type': 'tcp', 'port': 'test-does-not-exist'})

    def test_parse_checker_tcp_invalid_port(self):
        container = self._get_container()
        self.assertRaises(exceptions.InvalidLifecycleCheckConfigurationException,
            lifecycle.LifecycleHelperFactory.from_config,
            container, {'type': 'tcp', 'port': 'data'})

    def test_parse_unknown_checker_type(self):
        self.assertRaises(KeyError,
            lifecycle.LifecycleHelperFactory.from_config,
            self._get_container(), {'type': 'test-does-not-exist'})

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
