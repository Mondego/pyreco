__FILENAME__ = auth
# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import base64
import fileinput
import json
import os

import six

from ..utils import utils
from .. import errors

INDEX_URL = 'https://index.docker.io/v1/'
DOCKER_CONFIG_FILENAME = '.dockercfg'


def swap_protocol(url):
    if url.startswith('http://'):
        return url.replace('http://', 'https://', 1)
    if url.startswith('https://'):
        return url.replace('https://', 'http://', 1)
    return url


def expand_registry_url(hostname):
    if hostname.startswith('http:') or hostname.startswith('https:'):
        if '/' not in hostname[9:]:
            hostname = hostname + '/v1/'
        return hostname
    if utils.ping('https://' + hostname + '/v1/_ping'):
        return 'https://' + hostname + '/v1/'
    return 'http://' + hostname + '/v1/'


def resolve_repository_name(repo_name):
    if '://' in repo_name:
        raise errors.InvalidRepository(
            'Repository name cannot contain a scheme ({0})'.format(repo_name))
    parts = repo_name.split('/', 1)
    if '.' not in parts[0] and ':' not in parts[0] and parts[0] != 'localhost':
        # This is a docker index repo (ex: foo/bar or ubuntu)
        return INDEX_URL, repo_name
    if len(parts) < 2:
        raise errors.InvalidRepository(
            'Invalid repository name ({0})'.format(repo_name))

    if 'index.docker.io' in parts[0]:
        raise errors.InvalidRepository(
            'Invalid repository name, try "{0}" instead'.format(parts[1]))

    return expand_registry_url(parts[0]), parts[1]


def resolve_authconfig(authconfig, registry=None):
    """Return the authentication data from the given auth configuration for a
    specific registry. We'll do our best to infer the correct URL for the
    registry, trying both http and https schemes. Returns an empty dictionnary
    if no data exists."""
    # Default to the public index server
    registry = registry or INDEX_URL

    # Ff its not the index server there are three cases:
    #
    # 1. this is a full config url -> it should be used as is
    # 2. it could be a full url, but with the wrong protocol
    # 3. it can be the hostname optionally with a port
    #
    # as there is only one auth entry which is fully qualified we need to start
    # parsing and matching
    if '/' not in registry:
        registry = registry + '/v1/'
    if not registry.startswith('http:') and not registry.startswith('https:'):
        registry = 'https://' + registry

    if registry in authconfig:
        return authconfig[registry]
    return authconfig.get(swap_protocol(registry), None)


def encode_auth(auth_info):
    return base64.b64encode(auth_info.get('username', '') + b':' +
                            auth_info.get('password', ''))


def decode_auth(auth):
    if isinstance(auth, six.string_types):
        auth = auth.encode('ascii')
    s = base64.b64decode(auth)
    login, pwd = s.split(b':')
    return login.decode('ascii'), pwd.decode('ascii')


def encode_header(auth):
    auth_json = json.dumps(auth).encode('ascii')
    return base64.b64encode(auth_json)


def encode_full_header(auth):
    """ Returns the given auth block encoded for the X-Registry-Config header.
    """
    return encode_header({'configs': auth})


def load_config(root=None):
    """Loads authentication data from a Docker configuration file in the given
    root directory."""
    conf = {}
    data = None

    config_file = os.path.join(root or os.environ.get('HOME', '.'),
                               DOCKER_CONFIG_FILENAME)

    # First try as JSON
    try:
        with open(config_file) as f:
            conf = {}
            for registry, entry in six.iteritems(json.load(f)):
                username, password = decode_auth(entry['auth'])
                conf[registry] = {
                    'username': username,
                    'password': password,
                    'email': entry['email'],
                    'serveraddress': registry,
                }
            return conf
    except:
        pass

    # If that fails, we assume the configuration file contains a single
    # authentication token for the public registry in the following format:
    #
    # auth = AUTH_TOKEN
    # email = email@domain.com
    try:
        data = []
        for line in fileinput.input(config_file):
            data.append(line.strip().split(' = ')[1])
        if len(data) < 2:
            # Not enough data
            raise errors.InvalidConfigFile(
                'Invalid or empty configuration file!')

        username, password = decode_auth(data[0])
        conf[INDEX_URL] = {
            'username': username,
            'password': password,
            'email': data[1],
            'serveraddress': INDEX_URL,
        }
        return conf
    except:
        pass

    # If all fails, return an empty config
    return {}

########NEW FILE########
__FILENAME__ = client
# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import json
import re
import shlex
import struct
import warnings

import requests
import requests.exceptions
import six

from .auth import auth
from .unixconn import unixconn
from .utils import utils
from . import errors

if not six.PY3:
    import websocket

DEFAULT_DOCKER_API_VERSION = '1.9'
DEFAULT_TIMEOUT_SECONDS = 60
STREAM_HEADER_SIZE_BYTES = 8


class Client(requests.Session):
    def __init__(self, base_url=None, version=DEFAULT_DOCKER_API_VERSION,
                 timeout=DEFAULT_TIMEOUT_SECONDS):
        super(Client, self).__init__()
        if base_url is None:
            base_url = "http+unix://var/run/docker.sock"
        if 'unix:///' in base_url:
            base_url = base_url.replace('unix:/', 'unix:')
        if base_url.startswith('unix:'):
            base_url = "http+" + base_url
        if base_url.startswith('tcp:'):
            base_url = base_url.replace('tcp:', 'http:')
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        self.base_url = base_url
        self._version = version
        self._timeout = timeout
        self._auth_configs = auth.load_config()

        self.mount('http+unix://', unixconn.UnixAdapter(base_url, timeout))

    def _set_request_timeout(self, kwargs):
        """Prepare the kwargs for an HTTP request by inserting the timeout
        parameter, if not already present."""
        kwargs.setdefault('timeout', self._timeout)
        return kwargs

    def _post(self, url, **kwargs):
        return self.post(url, **self._set_request_timeout(kwargs))

    def _get(self, url, **kwargs):
        return self.get(url, **self._set_request_timeout(kwargs))

    def _delete(self, url, **kwargs):
        return self.delete(url, **self._set_request_timeout(kwargs))

    def _url(self, path):
        return '{0}/v{1}{2}'.format(self.base_url, self._version, path)

    def _raise_for_status(self, response, explanation=None):
        """Raises stored :class:`APIError`, if one occurred."""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise errors.APIError(e, response, explanation=explanation)

    def _result(self, response, json=False, binary=False):
        assert not (json and binary)
        self._raise_for_status(response)

        if json:
            return response.json()
        if binary:
            return response.content
        return response.text

    def _container_config(self, image, command, hostname=None, user=None,
                          detach=False, stdin_open=False, tty=False,
                          mem_limit=0, ports=None, environment=None, dns=None,
                          volumes=None, volumes_from=None,
                          network_disabled=False, entrypoint=None,
                          cpu_shares=None, working_dir=None, domainname=None,
                          memswap_limit=0):
        if isinstance(command, six.string_types):
            command = shlex.split(str(command))
        if isinstance(environment, dict):
            environment = [
                '{0}={1}'.format(k, v) for k, v in environment.items()
            ]

        if isinstance(ports, list):
            exposed_ports = {}
            for port_definition in ports:
                port = port_definition
                proto = 'tcp'
                if isinstance(port_definition, tuple):
                    if len(port_definition) == 2:
                        proto = port_definition[1]
                    port = port_definition[0]
                exposed_ports['{0}/{1}'.format(port, proto)] = {}
            ports = exposed_ports

        if isinstance(volumes, list):
            volumes_dict = {}
            for vol in volumes:
                volumes_dict[vol] = {}
            volumes = volumes_dict

        if volumes_from:
            if not isinstance(volumes_from, six.string_types):
                volumes_from = ','.join(volumes_from)
        else:
            # Force None, an empty list or dict causes client.start to fail
            volumes_from = None

        attach_stdin = False
        attach_stdout = False
        attach_stderr = False
        stdin_once = False

        if not detach:
            attach_stdout = True
            attach_stderr = True

            if stdin_open:
                attach_stdin = True
                stdin_once = True

        if utils.compare_version('1.10', self._version) >= 0:
            message = ('{0!r} parameter has no effect on create_container().'
                       ' It has been moved to start()')
            if dns is not None:
                raise errors.DockerException(message.format('dns'))
            if volumes_from is not None:
                raise errors.DockerException(message.format('volumes_from'))

        return {
            'Hostname': hostname,
            'Domainname': domainname,
            'ExposedPorts': ports,
            'User': user,
            'Tty': tty,
            'OpenStdin': stdin_open,
            'StdinOnce': stdin_once,
            'Memory': mem_limit,
            'AttachStdin': attach_stdin,
            'AttachStdout': attach_stdout,
            'AttachStderr': attach_stderr,
            'Env': environment,
            'Cmd': command,
            'Dns': dns,
            'Image': image,
            'Volumes': volumes,
            'VolumesFrom': volumes_from,
            'NetworkDisabled': network_disabled,
            'Entrypoint': entrypoint,
            'CpuShares': cpu_shares,
            'WorkingDir': working_dir,
            'MemorySwap': memswap_limit
        }

    def _post_json(self, url, data, **kwargs):
        # Go <1.1 can't unserialize null to a string
        # so we do this disgusting thing here.
        data2 = {}
        if data is not None:
            for k, v in six.iteritems(data):
                if v is not None:
                    data2[k] = v

        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Content-Type'] = 'application/json'
        return self._post(url, data=json.dumps(data2), **kwargs)

    def _attach_params(self, override=None):
        return override or {
            'stdout': 1,
            'stderr': 1,
            'stream': 1
        }

    def _attach_websocket(self, container, params=None):
        if six.PY3:
            raise NotImplementedError("This method is not currently supported "
                                      "under python 3")
        url = self._url("/containers/{0}/attach/ws".format(container))
        req = requests.Request("POST", url, params=self._attach_params(params))
        full_url = req.prepare().url
        full_url = full_url.replace("http://", "ws://", 1)
        full_url = full_url.replace("https://", "wss://", 1)
        return self._create_websocket_connection(full_url)

    def _create_websocket_connection(self, url):
        return websocket.create_connection(url)

    def _get_raw_response_socket(self, response):
        self._raise_for_status(response)
        if six.PY3:
            return response.raw._fp.fp.raw._sock
        else:
            return response.raw._fp.fp._sock

    def _stream_helper(self, response):
        """Generator for data coming from a chunked-encoded HTTP response."""
        socket_fp = self._get_raw_response_socket(response)
        socket_fp.setblocking(1)
        socket = socket_fp.makefile()
        while True:
            # Because Docker introduced newlines at the end of chunks in v0.9,
            # and only on some API endpoints, we have to cater for both cases.
            size_line = socket.readline()
            if size_line == '\r\n':
                size_line = socket.readline()

            size = int(size_line, 16)
            if size <= 0:
                break
            data = socket.readline()
            if not data:
                break
            yield data

    def _multiplexed_buffer_helper(self, response):
        """A generator of multiplexed data blocks read from a buffered
        response."""
        buf = self._result(response, binary=True)
        walker = 0
        while True:
            if len(buf[walker:]) < 8:
                break
            _, length = struct.unpack_from('>BxxxL', buf[walker:])
            start = walker + STREAM_HEADER_SIZE_BYTES
            end = start + length
            walker = end
            yield str(buf[start:end])

    def _multiplexed_socket_stream_helper(self, response):
        """A generator of multiplexed data blocks coming from a response
        socket."""
        socket = self._get_raw_response_socket(response)

        def recvall(socket, size):
            blocks = []
            while size > 0:
                block = socket.recv(size)
                if not block:
                    return None

                blocks.append(block)
                size -= len(block)

            sep = bytes() if six.PY3 else str()
            data = sep.join(blocks)
            return data

        while True:
            socket.settimeout(None)
            header = recvall(socket, STREAM_HEADER_SIZE_BYTES)
            if not header:
                break
            _, length = struct.unpack('>BxxxL', header)
            if not length:
                break
            data = recvall(socket, length)
            if not data:
                break
            yield data

    def attach(self, container, stdout=True, stderr=True,
               stream=False, logs=False):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {
            'logs': logs and 1 or 0,
            'stdout': stdout and 1 or 0,
            'stderr': stderr and 1 or 0,
            'stream': stream and 1 or 0,
        }
        u = self._url("/containers/{0}/attach".format(container))
        response = self._post(u, params=params, stream=stream)

        # Stream multi-plexing was only introduced in API v1.6. Anything before
        # that needs old-style streaming.
        if utils.compare_version('1.6', self._version) < 0:
            def stream_result():
                self._raise_for_status(response)
                for line in response.iter_lines(chunk_size=1,
                                                decode_unicode=True):
                    # filter out keep-alive new lines
                    if line:
                        yield line

            return stream_result() if stream else \
                self._result(response, binary=True)

        return stream and self._multiplexed_socket_stream_helper(response) or \
            ''.join([x for x in self._multiplexed_buffer_helper(response)])

    def attach_socket(self, container, params=None, ws=False):
        if params is None:
            params = {
                'stdout': 1,
                'stderr': 1,
                'stream': 1
            }

        if ws:
            return self._attach_websocket(container, params)

        if isinstance(container, dict):
            container = container.get('Id')

        u = self._url("/containers/{0}/attach".format(container))
        return self._get_raw_response_socket(self.post(
            u, None, params=self._attach_params(params), stream=True))

    def build(self, path=None, tag=None, quiet=False, fileobj=None,
              nocache=False, rm=False, stream=False, timeout=None,
              custom_context=False, encoding=None):
        remote = context = headers = None
        if path is None and fileobj is None:
            raise TypeError("Either path or fileobj needs to be provided.")

        if custom_context:
            if not fileobj:
                raise TypeError("You must specify fileobj with custom_context")
            context = fileobj
        elif fileobj is not None:
            context = utils.mkbuildcontext(fileobj)
        elif path.startswith(('http://', 'https://',
                              'git://', 'github.com/')):
            remote = path
        else:
            context = utils.tar(path)

        if utils.compare_version('1.8', self._version) >= 0:
            stream = True

        u = self._url('/build')
        params = {
            't': tag,
            'remote': remote,
            'q': quiet,
            'nocache': nocache,
            'rm': rm
        }

        if context is not None:
            headers = {'Content-Type': 'application/tar'}
            if encoding:
                headers['Content-Encoding'] = encoding

        if utils.compare_version('1.9', self._version) >= 0:
            # If we don't have any auth data so far, try reloading the config
            # file one more time in case anything showed up in there.
            if not self._auth_configs:
                self._auth_configs = auth.load_config()

            # Send the full auth configuration (if any exists), since the build
            # could use any (or all) of the registries.
            if self._auth_configs:
                headers['X-Registry-Config'] = auth.encode_full_header(
                    self._auth_configs
                )

        response = self._post(
            u,
            data=context,
            params=params,
            headers=headers,
            stream=stream,
            timeout=timeout,
        )

        if context is not None:
            context.close()

        if stream:
            return self._stream_helper(response)
        else:
            output = self._result(response)
            srch = r'Successfully built ([0-9a-f]+)'
            match = re.search(srch, output)
            if not match:
                return None, output
            return match.group(1), output

    def commit(self, container, repository=None, tag=None, message=None,
               author=None, conf=None):
        params = {
            'container': container,
            'repo': repository,
            'tag': tag,
            'comment': message,
            'author': author
        }
        u = self._url("/commit")
        return self._result(self._post_json(u, data=conf, params=params),
                            json=True)

    def containers(self, quiet=False, all=False, trunc=True, latest=False,
                   since=None, before=None, limit=-1):
        params = {
            'limit': 1 if latest else limit,
            'all': 1 if all else 0,
            'trunc_cmd': 1 if trunc else 0,
            'since': since,
            'before': before
        }
        u = self._url("/containers/json")
        res = self._result(self._get(u, params=params), True)

        if quiet:
            return [{'Id': x['Id']} for x in res]
        return res

    def copy(self, container, resource):
        if isinstance(container, dict):
            container = container.get('Id')
        res = self._post_json(
            self._url("/containers/{0}/copy".format(container)),
            data={"Resource": resource},
            stream=True
        )
        self._raise_for_status(res)
        return res.raw

    def create_container(self, image, command=None, hostname=None, user=None,
                         detach=False, stdin_open=False, tty=False,
                         mem_limit=0, ports=None, environment=None, dns=None,
                         volumes=None, volumes_from=None,
                         network_disabled=False, name=None, entrypoint=None,
                         cpu_shares=None, working_dir=None, domainname=None,
                         memswap_limit=0):

        config = self._container_config(
            image, command, hostname, user, detach, stdin_open, tty, mem_limit,
            ports, environment, dns, volumes, volumes_from, network_disabled,
            entrypoint, cpu_shares, working_dir, domainname, memswap_limit
        )
        return self.create_container_from_config(config, name)

    def create_container_from_config(self, config, name=None):
        u = self._url("/containers/create")
        params = {
            'name': name
        }
        res = self._post_json(u, data=config, params=params)
        return self._result(res, True)

    def diff(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        return self._result(self._get(self._url("/containers/{0}/changes".
                            format(container))), True)

    def events(self):
        return self._stream_helper(self.get(self._url('/events'), stream=True))

    def export(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        res = self._get(self._url("/containers/{0}/export".format(container)),
                        stream=True)
        self._raise_for_status(res)
        return res.raw

    def history(self, image):
        res = self._get(self._url("/images/{0}/history".format(image)))
        self._raise_for_status(res)
        return self._result(res)

    def images(self, name=None, quiet=False, all=False, viz=False):
        if viz:
            if utils.compare_version('1.7', self._version) >= 0:
                raise Exception('Viz output is not supported in API >= 1.7!')
            return self._result(self._get(self._url("images/viz")))
        params = {
            'filter': name,
            'only_ids': 1 if quiet else 0,
            'all': 1 if all else 0,
        }
        res = self._result(self._get(self._url("/images/json"), params=params),
                           True)
        if quiet:
            return [x['Id'] for x in res]
        return res

    def import_image(self, src=None, repository=None, tag=None, image=None):
        u = self._url("/images/create")
        params = {
            'repo': repository,
            'tag': tag
        }

        if src:
            try:
                # XXX: this is ways not optimal but the only way
                # for now to import tarballs through the API
                fic = open(src)
                data = fic.read()
                fic.close()
                src = "-"
            except IOError:
                # file does not exists or not a file (URL)
                data = None
            if isinstance(src, six.string_types):
                params['fromSrc'] = src
                return self._result(self._post(u, data=data, params=params))
            return self._result(self._post(u, data=src, params=params))

        if image:
            params['fromImage'] = image
            return self._result(self._post(u, data=None, params=params))

        raise Exception("Must specify a src or image")

    def info(self):
        return self._result(self._get(self._url("/info")),
                            True)

    def insert(self, image, url, path):
        api_url = self._url("/images/" + image + "/insert")
        params = {
            'url': url,
            'path': path
        }
        return self._result(self._post(api_url, params=params))

    def inspect_container(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        return self._result(
            self._get(self._url("/containers/{0}/json".format(container))),
            True)

    def inspect_image(self, image_id):
        return self._result(
            self._get(self._url("/images/{0}/json".format(image_id))),
            True
        )

    def kill(self, container, signal=None):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url("/containers/{0}/kill".format(container))
        params = {}
        if signal is not None:
            params['signal'] = signal
        res = self._post(url, params=params)

        self._raise_for_status(res)

    def login(self, username, password=None, email=None, registry=None,
              reauth=False):
        # If we don't have any auth data so far, try reloading the config file
        # one more time in case anything showed up in there.
        if not self._auth_configs:
            self._auth_configs = auth.load_config()

        registry = registry or auth.INDEX_URL

        authcfg = auth.resolve_authconfig(self._auth_configs, registry)
        # If we found an existing auth config for this registry and username
        # combination, we can return it immediately unless reauth is requested.
        if authcfg and authcfg.get('username', None) == username \
                and not reauth:
            return authcfg

        req_data = {
            'username': username,
            'password': password,
            'email': email,
            'serveraddress': registry,
        }

        response = self._post_json(self._url('/auth'), data=req_data)
        if response.status_code == 200:
            self._auth_configs[registry] = req_data
        return self._result(response, json=True)

    def logs(self, container, stdout=True, stderr=True, stream=False,
             timestamps=False):
        if utils.compare_version('1.11', self._version) >= 0:
            params = {'stderr': stderr and 1 or 0,
                      'stdout': stdout and 1 or 0,
                      'timestamps': timestamps and 1 or 0,
                      'follow': stream and 1 or 0}
            url = self._url("/containers/{0}/logs".format(container))
            res = self._get(url, params=params, stream=stream)
            return stream and self._multiplexed_socket_stream_helper(res) or \
                ''.join([x for x in self._multiplexed_buffer_helper(res)])
        return self.attach(
            container,
            stdout=stdout,
            stderr=stderr,
            stream=stream,
            logs=True
        )

    def ping(self):
        return self._result(self._get(self._url('/_ping')))

    def port(self, container, private_port):
        if isinstance(container, dict):
            container = container.get('Id')
        res = self._get(self._url("/containers/{0}/json".format(container)))
        self._raise_for_status(res)
        json_ = res.json()
        s_port = str(private_port)
        h_ports = None

        h_ports = json_['NetworkSettings']['Ports'].get(s_port + '/udp')
        if h_ports is None:
            h_ports = json_['NetworkSettings']['Ports'].get(s_port + '/tcp')

        return h_ports

    def pull(self, repository, tag=None, stream=False):
        registry, repo_name = auth.resolve_repository_name(repository)
        if repo_name.count(":") == 1:
            repository, tag = repository.rsplit(":", 1)

        params = {
            'tag': tag,
            'fromImage': repository
        }
        headers = {}

        if utils.compare_version('1.5', self._version) >= 0:
            # If we don't have any auth data so far, try reloading the config
            # file one more time in case anything showed up in there.
            if not self._auth_configs:
                self._auth_configs = auth.load_config()
            authcfg = auth.resolve_authconfig(self._auth_configs, registry)

            # Do not fail here if no authentication exists for this specific
            # registry as we can have a readonly pull. Just put the header if
            # we can.
            if authcfg:
                headers['X-Registry-Auth'] = auth.encode_header(authcfg)

        response = self._post(self._url('/images/create'), params=params,
                              headers=headers, stream=stream, timeout=None)

        if stream:
            return self._stream_helper(response)
        else:
            return self._result(response)

    def push(self, repository, stream=False):
        registry, repo_name = auth.resolve_repository_name(repository)
        u = self._url("/images/{0}/push".format(repository))
        headers = {}

        if utils.compare_version('1.5', self._version) >= 0:
            # If we don't have any auth data so far, try reloading the config
            # file one more time in case anything showed up in there.
            if not self._auth_configs:
                self._auth_configs = auth.load_config()
            authcfg = auth.resolve_authconfig(self._auth_configs, registry)

            # Do not fail here if no authentication exists for this specific
            # registry as we can have a readonly pull. Just put the header if
            # we can.
            if authcfg:
                headers['X-Registry-Auth'] = auth.encode_header(authcfg)

            response = self._post_json(u, None, headers=headers, stream=stream)
        else:
            response = self._post_json(u, None, stream=stream)

        return stream and self._stream_helper(response) \
            or self._result(response)

    def remove_container(self, container, v=False, link=False, force=False):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'v': v, 'link': link, 'force': force}
        res = self._delete(self._url("/containers/" + container),
                           params=params)
        self._raise_for_status(res)

    def remove_image(self, image, force=False, noprune=False):
        params = {'force': force, 'noprune': noprune}
        res = self._delete(self._url("/images/" + image), params=params)
        self._raise_for_status(res)

    def restart(self, container, timeout=10):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'t': timeout}
        url = self._url("/containers/{0}/restart".format(container))
        res = self._post(url, params=params)
        self._raise_for_status(res)

    def search(self, term):
        return self._result(self._get(self._url("/images/search"),
                                      params={'term': term}),
                            True)

    def start(self, container, binds=None, port_bindings=None, lxc_conf=None,
              publish_all_ports=False, links=None, privileged=False,
              dns=None, dns_search=None, volumes_from=None, network_mode=None):
        if isinstance(container, dict):
            container = container.get('Id')

        if isinstance(lxc_conf, dict):
            formatted = []
            for k, v in six.iteritems(lxc_conf):
                formatted.append({'Key': k, 'Value': str(v)})
            lxc_conf = formatted

        start_config = {
            'LxcConf': lxc_conf
        }
        if binds:
            start_config['Binds'] = utils.convert_volume_binds(binds)

        if port_bindings:
            start_config['PortBindings'] = utils.convert_port_bindings(
                port_bindings
            )

        start_config['PublishAllPorts'] = publish_all_ports

        if links:
            if isinstance(links, dict):
                links = six.iteritems(links)

            formatted_links = [
                '{0}:{1}'.format(k, v) for k, v in sorted(links)
            ]

            start_config['Links'] = formatted_links

        start_config['Privileged'] = privileged

        if utils.compare_version('1.10', self._version) >= 0:
            if dns is not None:
                start_config['Dns'] = dns
            if volumes_from is not None:
                if isinstance(volumes_from, six.string_types):
                    volumes_from = volumes_from.split(',')
                start_config['VolumesFrom'] = volumes_from
        else:
            warning_message = ('{0!r} parameter is discarded. It is only'
                               ' available for API version greater or equal'
                               ' than 1.10')

            if dns is not None:
                warnings.warn(warning_message.format('dns'),
                              DeprecationWarning)
            if volumes_from is not None:
                warnings.warn(warning_message.format('volumes_from'),
                              DeprecationWarning)

        if dns_search:
            start_config['DnsSearch'] = dns_search

        if network_mode:
            start_config['NetworkMode'] = network_mode

        url = self._url("/containers/{0}/start".format(container))
        res = self._post_json(url, data=start_config)
        self._raise_for_status(res)

    def stop(self, container, timeout=10):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'t': timeout}
        url = self._url("/containers/{0}/stop".format(container))
        res = self._post(url, params=params,
                         timeout=max(timeout, self._timeout))
        self._raise_for_status(res)

    def tag(self, image, repository, tag=None, force=False):
        params = {
            'tag': tag,
            'repo': repository,
            'force': 1 if force else 0
        }
        url = self._url("/images/{0}/tag".format(image))
        res = self._post(url, params=params)
        self._raise_for_status(res)
        return res.status_code == 201

    def top(self, container):
        u = self._url("/containers/{0}/top".format(container))
        return self._result(self._get(u), True)

    def version(self):
        return self._result(self._get(self._url("/version")), True)

    def wait(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url("/containers/{0}/wait".format(container))
        res = self._post(url, timeout=None)
        self._raise_for_status(res)
        json_ = res.json()
        if 'StatusCode' in json_:
            return json_['StatusCode']
        return -1

########NEW FILE########
__FILENAME__ = errors
#    Copyright 2014 dotCloud inc.
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import requests


class APIError(requests.exceptions.HTTPError):
    def __init__(self, message, response, explanation=None):
        # requests 1.2 supports response as a keyword argument, but
        # requests 1.1 doesn't
        super(APIError, self).__init__(message)
        self.response = response

        self.explanation = explanation

        if self.explanation is None and response.content:
            self.explanation = response.content.strip()

    def __str__(self):
        message = super(APIError, self).__str__()

        if self.is_client_error():
            message = '%s Client Error: %s' % (
                self.response.status_code, self.response.reason)

        elif self.is_server_error():
            message = '%s Server Error: %s' % (
                self.response.status_code, self.response.reason)

        if self.explanation:
            message = '%s ("%s")' % (message, self.explanation)

        return message

    def is_client_error(self):
        return 400 <= self.response.status_code < 500

    def is_server_error(self):
        return 500 <= self.response.status_code < 600


class DockerException(Exception):
    pass


class InvalidRepository(DockerException):
    pass


class InvalidConfigFile(DockerException):
    pass

########NEW FILE########
__FILENAME__ = unixconn
# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
import six

if six.PY3:
    import http.client as httplib
else:
    import httplib
import requests.adapters
import socket

try:
    import requests.packages.urllib3.connectionpool as connectionpool
except ImportError:
    import urllib3.connectionpool as connectionpool


class UnixHTTPConnection(httplib.HTTPConnection, object):
    def __init__(self, base_url, unix_socket, timeout=60):
        httplib.HTTPConnection.__init__(self, 'localhost', timeout=timeout)
        self.base_url = base_url
        self.unix_socket = unix_socket
        self.timeout = timeout

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.base_url.replace("http+unix:/", ""))
        self.sock = sock

    def _extract_path(self, url):
        # remove the base_url entirely..
        return url.replace(self.base_url, "")

    def request(self, method, url, **kwargs):
        url = self._extract_path(self.unix_socket)
        super(UnixHTTPConnection, self).request(method, url, **kwargs)


class UnixHTTPConnectionPool(connectionpool.HTTPConnectionPool):
    def __init__(self, base_url, socket_path, timeout=60):
        connectionpool.HTTPConnectionPool.__init__(self, 'localhost',
                                                   timeout=timeout)
        self.base_url = base_url
        self.socket_path = socket_path
        self.timeout = timeout

    def _new_conn(self):
        return UnixHTTPConnection(self.base_url, self.socket_path,
                                  self.timeout)


class UnixAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, base_url, timeout=60):
        self.base_url = base_url
        self.timeout = timeout
        super(UnixAdapter, self).__init__()

    def get_connection(self, socket_path, proxies=None):
        return UnixHTTPConnectionPool(self.base_url, socket_path, self.timeout)

########NEW FILE########
__FILENAME__ = utils
# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import io
import tarfile
import tempfile
from distutils.version import StrictVersion

import requests
import six


def mkbuildcontext(dockerfile):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w', fileobj=f)
    if isinstance(dockerfile, io.StringIO):
        dfinfo = tarfile.TarInfo('Dockerfile')
        if six.PY3:
            raise TypeError('Please use io.BytesIO to create in-memory '
                            'Dockerfiles with Python 3')
        else:
            dfinfo.size = len(dockerfile.getvalue())
    elif isinstance(dockerfile, io.BytesIO):
        dfinfo = tarfile.TarInfo('Dockerfile')
        dfinfo.size = len(dockerfile.getvalue())
    else:
        dfinfo = t.gettarinfo(fileobj=dockerfile, arcname='Dockerfile')
    t.addfile(dfinfo, dockerfile)
    t.close()
    f.seek(0)
    return f


def tar(path):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w', fileobj=f)
    t.add(path, arcname='.')
    t.close()
    f.seek(0)
    return f


def compare_version(v1, v2):
    """Compare docker versions

    >>> v1 = '1.9'
    >>> v2 = '1.10'
    >>> compare_version(v1, v2)
    1
    >>> compare_version(v2, v1)
    -1
    >>> compare_version(v2, v2)
    0
    """
    s1 = StrictVersion(v1)
    s2 = StrictVersion(v2)
    if s1 == s2:
        return 0
    elif s1 > s2:
        return -1
    else:
        return 1


def ping(url):
    try:
        res = requests.get(url)
    except Exception:
        return False
    else:
        return res.status_code < 400


def _convert_port_binding(binding):
    result = {'HostIp': '', 'HostPort': ''}
    if isinstance(binding, tuple):
        if len(binding) == 2:
            result['HostPort'] = binding[1]
            result['HostIp'] = binding[0]
        elif isinstance(binding[0], six.string_types):
            result['HostIp'] = binding[0]
        else:
            result['HostPort'] = binding[0]
    else:
        result['HostPort'] = binding

    if result['HostPort'] is None:
        result['HostPort'] = ''
    else:
        result['HostPort'] = str(result['HostPort'])

    return result


def convert_port_bindings(port_bindings):
    result = {}
    for k, v in six.iteritems(port_bindings):
        key = str(k)
        if '/' not in key:
            key = key + '/tcp'
        if isinstance(v, list):
            result[key] = [_convert_port_binding(binding) for binding in v]
        else:
            result[key] = [_convert_port_binding(v)]
    return result


def convert_volume_binds(binds):
    result = []
    for k, v in binds.items():
        if isinstance(v, dict):
            result.append('%s:%s:%s' % (
                k, v['bind'], 'ro' if v.get('ro', False) else 'rw'
            ))
        else:
            result.append('%s:%s:rw' % (k, v))
    return result


def parse_repository_tag(repo):
    column_index = repo.rfind(':')
    if column_index < 0:
        return repo, ""
    tag = repo[column_index+1:]
    slash_index = tag.find('/')
    if slash_index < 0:
        return repo[:column_index], tag

    return repo, ""

########NEW FILE########
__FILENAME__ = version
version = "0.3.2-dev"

########NEW FILE########
__FILENAME__ = fake_api
# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

CURRENT_VERSION = 'v1.9'

FAKE_CONTAINER_ID = '3cc2351ab11b'
FAKE_IMAGE_ID = 'e9aa60c60128'
FAKE_IMAGE_NAME = 'test_image'
FAKE_TARBALL_PATH = '/path/to/tarball'
FAKE_REPO_NAME = 'repo'
FAKE_TAG_NAME = 'tag'
FAKE_FILE_NAME = 'file'
FAKE_URL = 'myurl'
FAKE_PATH = '/path'

# Each method is prefixed with HTTP method (get, post...)
# for clarity and readability


def get_fake_version():
    status_code = 200
    response = {'GoVersion': '1', 'Version': '1.1.1',
                'GitCommit': 'deadbeef+CHANGES'}
    return status_code, response


def get_fake_info():
    status_code = 200
    response = {'Containers': 1, 'Images': 1, 'Debug': False,
                'MemoryLimit': False, 'SwapLimit': False,
                'IPv4Forwarding': True}
    return status_code, response


def get_fake_search():
    status_code = 200
    response = [{'Name': 'busybox', 'Description': 'Fake Description'}]
    return status_code, response


def get_fake_images():
    status_code = 200
    response = [{
        'Id': FAKE_IMAGE_ID,
        'Created': '2 days ago',
        'Repository': 'busybox',
        'RepoTags': ['busybox:latest', 'busybox:1.0'],
    }]
    return status_code, response


def get_fake_image_history():
    status_code = 200
    response = [
        {
            "Id": "b750fe79269d",
            "Created": 1364102658,
            "CreatedBy": "/bin/bash"
        },
        {
            "Id": "27cf78414709",
            "Created": 1364068391,
            "CreatedBy": ""
        }
    ]

    return status_code, response


def post_fake_import_image():
    status_code = 200
    response = 'Import messages...'

    return status_code, response


def get_fake_containers():
    status_code = 200
    response = [{
        'Id': FAKE_CONTAINER_ID,
        'Image': 'busybox:latest',
        'Created': '2 days ago',
        'Command': 'true',
        'Status': 'fake status'
    }]
    return status_code, response


def post_fake_start_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_create_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def get_fake_inspect_container():
    status_code = 200
    response = {
        'Id': FAKE_CONTAINER_ID,
        'Config': {'Privileged': True},
        'ID': FAKE_CONTAINER_ID,
        'Image': 'busybox:latest',
        "State": {
            "Running": True,
            "Pid": 0,
            "ExitCode": 0,
            "StartedAt": "2013-09-25T14:01:18.869545111+02:00",
            "Ghost": False
        },
    }
    return status_code, response


def get_fake_inspect_image():
    status_code = 200
    response = {
        'id': FAKE_IMAGE_ID,
        'parent': "27cf784147099545",
        'created': "2013-03-23T22:24:18.818426-07:00",
        'container': FAKE_CONTAINER_ID,
        'container_config':
        {
            "Hostname": "",
            "User": "",
            "Memory": 0,
            "MemorySwap": 0,
            "AttachStdin": False,
            "AttachStdout": False,
            "AttachStderr": False,
            "PortSpecs": "",
            "Tty": True,
            "OpenStdin": True,
            "StdinOnce": False,
            "Env": "",
            "Cmd": ["/bin/bash"],
            "Dns": "",
            "Image": "base",
            "Volumes": "",
            "VolumesFrom": "",
            "WorkingDir": ""
        },
        'Size': 6823592
    }
    return status_code, response


def get_fake_port():
    status_code = 200
    response = {
        'HostConfig': {
            'Binds': None,
            'ContainerIDFile': '',
            'Links': None,
            'LxcConf': None,
            'PortBindings': {
                '1111': None,
                '1111/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '4567'}],
                '2222': None
            },
            'Privileged': False,
            'PublishAllPorts': False
        },
        'NetworkSettings': {
            'Bridge': 'docker0',
            'PortMapping': None,
            'Ports': {
                '1111': None,
                '1111/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '4567'}],
                '2222': None}
        }
    }
    return status_code, response


def get_fake_insert_image():
    status_code = 200
    response = {'StatusCode': 0}
    return status_code, response


def get_fake_wait():
    status_code = 200
    response = {'StatusCode': 0}
    return status_code, response


def get_fake_logs():
    status_code = 200
    response = 'Flowering Nights (Sakuya Iyazoi)'
    return status_code, response


def get_fake_diff():
    status_code = 200
    response = [{'Path': '/test', 'Kind': 1}]
    return status_code, response


def get_fake_export():
    status_code = 200
    response = 'Byte Stream....'
    return status_code, response


def post_fake_stop_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_kill_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_restart_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def delete_fake_remove_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_image_create():
    status_code = 200
    response = {'Id': FAKE_IMAGE_ID}
    return status_code, response


def delete_fake_remove_image():
    status_code = 200
    response = {'Id': FAKE_IMAGE_ID}
    return status_code, response


def post_fake_commit():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_push():
    status_code = 200
    response = {'Id': FAKE_IMAGE_ID}
    return status_code, response


def post_fake_build_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_tag_image():
    status_code = 200
    response = {'Id': FAKE_IMAGE_ID}
    return status_code, response


# Maps real api url to fake response callback
prefix = 'http+unix://var/run/docker.sock'
fake_responses = {
    '{1}/{0}/version'.format(CURRENT_VERSION, prefix):
    get_fake_version,
    '{1}/{0}/info'.format(CURRENT_VERSION, prefix):
    get_fake_info,
    '{1}/{0}/images/search'.format(CURRENT_VERSION, prefix):
    get_fake_search,
    '{1}/{0}/images/json'.format(CURRENT_VERSION, prefix):
    get_fake_images,
    '{1}/{0}/images/test_image/history'.format(CURRENT_VERSION, prefix):
    get_fake_image_history,
    '{1}/{0}/images/create'.format(CURRENT_VERSION, prefix):
    post_fake_import_image,
    '{1}/{0}/containers/json'.format(CURRENT_VERSION, prefix):
    get_fake_containers,
    '{1}/{0}/containers/3cc2351ab11b/start'.format(CURRENT_VERSION, prefix):
    post_fake_start_container,
    '{1}/{0}/containers/3cc2351ab11b/json'.format(CURRENT_VERSION, prefix):
    get_fake_inspect_container,
    '{1}/{0}/images/e9aa60c60128/tag'.format(CURRENT_VERSION, prefix):
    post_fake_tag_image,
    '{1}/{0}/containers/3cc2351ab11b/wait'.format(CURRENT_VERSION, prefix):
    get_fake_wait,
    '{1}/{0}/containers/3cc2351ab11b/attach'.format(CURRENT_VERSION, prefix):
    get_fake_logs,
    '{1}/{0}/containers/3cc2351ab11b/changes'.format(CURRENT_VERSION, prefix):
    get_fake_diff,
    '{1}/{0}/containers/3cc2351ab11b/export'.format(CURRENT_VERSION, prefix):
    get_fake_export,
    '{1}/{0}/containers/3cc2351ab11b/stop'.format(CURRENT_VERSION, prefix):
    post_fake_stop_container,
    '{1}/{0}/containers/3cc2351ab11b/kill'.format(CURRENT_VERSION, prefix):
    post_fake_kill_container,
    '{1}/{0}/containers/3cc2351ab11b/json'.format(CURRENT_VERSION, prefix):
    get_fake_port,
    '{1}/{0}/containers/3cc2351ab11b/restart'.format(CURRENT_VERSION, prefix):
    post_fake_restart_container,
    '{1}/{0}/containers/3cc2351ab11b'.format(CURRENT_VERSION, prefix):
    delete_fake_remove_container,
    '{1}/{0}/images/create'.format(CURRENT_VERSION, prefix):
    post_fake_image_create,
    '{1}/{0}/images/e9aa60c60128'.format(CURRENT_VERSION, prefix):
    delete_fake_remove_image,
    '{1}/{0}/images/test_image/json'.format(CURRENT_VERSION, prefix):
    get_fake_inspect_image,
    '{1}/{0}/images/test_image/insert'.format(CURRENT_VERSION, prefix):
    get_fake_insert_image,
    '{1}/{0}/images/test_image/push'.format(CURRENT_VERSION, prefix):
    post_fake_push,
    '{1}/{0}/commit'.format(CURRENT_VERSION, prefix):
    post_fake_commit,
    '{1}/{0}/containers/create'.format(CURRENT_VERSION, prefix):
    post_fake_create_container,
    '{1}/{0}/build'.format(CURRENT_VERSION, prefix):
    post_fake_build_container
}

########NEW FILE########
__FILENAME__ = integration_test
# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import time
import base64
import json
import io
import os
import signal
import tempfile
import unittest

import docker
import six

# FIXME: missing tests for
# export; history; import_image; insert; port; push; tag


class BaseTestCase(unittest.TestCase):
    tmp_imgs = []
    tmp_containers = []

    def setUp(self):
        self.client = docker.Client()
        self.client.pull('busybox')
        self.tmp_imgs = []
        self.tmp_containers = []

    def tearDown(self):
        for img in self.tmp_imgs:
            try:
                self.client.remove_image(img)
            except docker.errors.APIError:
                pass
        for container in self.tmp_containers:
            try:
                self.client.stop(container, timeout=1)
                self.client.remove_container(container)
            except docker.errors.APIError:
                pass

#########################
#   INFORMATION TESTS   #
#########################


class TestVersion(BaseTestCase):
    def runTest(self):
        res = self.client.version()
        self.assertIn('GoVersion', res)
        self.assertIn('Version', res)
        self.assertEqual(len(res['Version'].split('.')), 3)


class TestInfo(BaseTestCase):
    def runTest(self):
        res = self.client.info()
        self.assertIn('Containers', res)
        self.assertIn('Images', res)
        self.assertIn('Debug', res)


class TestSearch(BaseTestCase):
    def runTest(self):
        res = self.client.search('busybox')
        self.assertTrue(len(res) >= 1)
        base_img = [x for x in res if x['name'] == 'busybox']
        self.assertEqual(len(base_img), 1)
        self.assertIn('description', base_img[0])

###################
#  LISTING TESTS  #
###################


class TestImages(BaseTestCase):
    def runTest(self):
        res1 = self.client.images(all=True)
        self.assertIn('Id', res1[0])
        res10 = res1[0]
        self.assertIn('Created', res10)
        self.assertIn('RepoTags', res10)
        distinct = []
        for img in res1:
            if img['Id'] not in distinct:
                distinct.append(img['Id'])
        self.assertEqual(len(distinct), self.client.info()['Images'])


class TestImageIds(BaseTestCase):
    def runTest(self):
        res1 = self.client.images(quiet=True)
        self.assertEqual(type(res1[0]), six.text_type)


class TestListContainers(BaseTestCase):
    def runTest(self):
        res0 = self.client.containers(all=True)
        size = len(res0)
        res1 = self.client.create_container('busybox', 'true;')
        self.assertIn('Id', res1)
        self.client.start(res1['Id'])
        self.tmp_containers.append(res1['Id'])
        res2 = self.client.containers(all=True)
        self.assertEqual(size + 1, len(res2))
        retrieved = [x for x in res2 if x['Id'].startswith(res1['Id'])]
        self.assertEqual(len(retrieved), 1)
        retrieved = retrieved[0]
        self.assertIn('Command', retrieved)
        self.assertEqual(retrieved['Command'], 'true;')
        self.assertIn('Image', retrieved)
        self.assertEqual(retrieved['Image'], 'busybox:latest')
        self.assertIn('Status', retrieved)

#####################
#  CONTAINER TESTS  #
#####################


class TestCreateContainer(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])


class TestCreateContainerWithBinds(BaseTestCase):
    def runTest(self):
        mount_dest = '/mnt'
        mount_origin = '/tmp'

        filename = 'shared.txt'
        shared_file = os.path.join(mount_origin, filename)

        with open(shared_file, 'w'):
            container = self.client.create_container(
                'busybox',
                ['ls', mount_dest], volumes={mount_dest: {}}
            )
            container_id = container['Id']
            self.client.start(
                container_id,
                binds={
                    mount_origin: {
                        'bind': mount_dest,
                        'ro': False,
                    },
                },
            )
            self.tmp_containers.append(container_id)
            exitcode = self.client.wait(container_id)
            self.assertEqual(exitcode, 0)
            logs = self.client.logs(container_id)

        os.unlink(shared_file)
        self.assertIn(filename, logs)


class TestCreateContainerWithName(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true', name='foobar')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Name', inspect)
        self.assertEqual('/foobar', inspect['Name'])


class TestStartContainer(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('ID', inspect)
        self.assertTrue(inspect['ID'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)


class TestStartContainerWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res)
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('ID', inspect)
        self.assertTrue(inspect['ID'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)


class TestStartContainerPrivileged(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'], privileged=True)
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('ID', inspect)
        self.assertTrue(inspect['ID'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)
        # Since Nov 2013, the Privileged flag is no longer part of the
        # container's config exposed via the API (safety concerns?).
        #
        # self.assertEqual(inspect['Config']['Privileged'], True)


class TestWait(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', ['sleep', '10'])
        id = res['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        inspect = self.client.inspect_container(id)
        self.assertIn('Running', inspect['State'])
        self.assertEqual(inspect['State']['Running'], False)
        self.assertIn('ExitCode', inspect['State'])
        self.assertEqual(inspect['State']['ExitCode'], exitcode)


class TestWaitWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', ['sleep', '10'])
        id = res['Id']
        self.tmp_containers.append(id)
        self.client.start(res)
        exitcode = self.client.wait(res)
        self.assertEqual(exitcode, 0)
        inspect = self.client.inspect_container(res)
        self.assertIn('Running', inspect['State'])
        self.assertEqual(inspect['State']['Running'], False)
        self.assertIn('ExitCode', inspect['State'])
        self.assertEqual(inspect['State']['ExitCode'], exitcode)


class TestLogs(BaseTestCase):
    def runTest(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            'busybox', 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        logs = self.client.logs(id)
        self.assertEqual(logs, snippet + '\n')


class TestLogsStreaming(BaseTestCase):
    def runTest(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            'busybox', 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        logs = ''
        for chunk in self.client.logs(id, stream=True):
            logs += chunk

        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)

        self.assertEqual(logs, snippet + '\n')


class TestLogsWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            'busybox', 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        logs = self.client.logs(container)
        self.assertEqual(logs, snippet + '\n')


class TestDiff(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        diff = self.client.diff(id)
        test_diff = [x for x in diff if x.get('Path', None) == '/test']
        self.assertEqual(len(test_diff), 1)
        self.assertIn('Kind', test_diff[0])
        self.assertEqual(test_diff[0]['Kind'], 1)


class TestDiffWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        diff = self.client.diff(container)
        test_diff = [x for x in diff if x.get('Path', None) == '/test']
        self.assertEqual(len(test_diff), 1)
        self.assertIn('Kind', test_diff[0])
        self.assertEqual(test_diff[0]['Kind'], 1)


class TestStop(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.stop(id, timeout=2)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)


class TestStopWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        self.assertIn('Id', container)
        id = container['Id']
        self.client.start(container)
        self.tmp_containers.append(id)
        self.client.stop(container, timeout=2)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)


class TestKill(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(id)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)


class TestKillWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(container)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)


class TestKillWithSignal(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '60'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(id, signal=signal.SIGTERM)
        exitcode = self.client.wait(id)
        self.assertNotEqual(exitcode, 0)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False, state)


class TestPort(BaseTestCase):
    def runTest(self):

        port_bindings = {
            1111: ('127.0.0.1', '4567'),
            2222: ('127.0.0.1', '4568')
        }

        container = self.client.create_container(
            'busybox', ['sleep', '60'], ports=port_bindings.keys()
        )
        id = container['Id']

        self.client.start(container, port_bindings=port_bindings)

        # Call the port function on each biding and compare expected vs actual
        for port in port_bindings:
            actual_bindings = self.client.port(container, port)
            port_binding = actual_bindings.pop()

            ip, host_port = port_binding['HostIp'], port_binding['HostPort']

            self.assertEqual(ip, port_bindings[port][0])
            self.assertEqual(host_port, port_bindings[port][1])

        self.client.kill(id)


class TestRestart(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        info = self.client.inspect_container(id)
        self.assertIn('State', info)
        self.assertIn('StartedAt', info['State'])
        start_time1 = info['State']['StartedAt']
        self.client.restart(id, timeout=2)
        info2 = self.client.inspect_container(id)
        self.assertIn('State', info2)
        self.assertIn('StartedAt', info2['State'])
        start_time2 = info2['State']['StartedAt']
        self.assertNotEqual(start_time1, start_time2)
        self.assertIn('Running', info2['State'])
        self.assertEqual(info2['State']['Running'], True)
        self.client.kill(id)


class TestRestartWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        self.assertIn('Id', container)
        id = container['Id']
        self.client.start(container)
        self.tmp_containers.append(id)
        info = self.client.inspect_container(id)
        self.assertIn('State', info)
        self.assertIn('StartedAt', info['State'])
        start_time1 = info['State']['StartedAt']
        self.client.restart(container, timeout=2)
        info2 = self.client.inspect_container(id)
        self.assertIn('State', info2)
        self.assertIn('StartedAt', info2['State'])
        start_time2 = info2['State']['StartedAt']
        self.assertNotEqual(start_time1, start_time2)
        self.assertIn('Running', info2['State'])
        self.assertEqual(info2['State']['Running'], True)
        self.client.kill(id)


class TestRemoveContainer(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['true'])
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        self.client.remove_container(id)
        containers = self.client.containers(all=True)
        res = [x for x in containers if 'Id' in x and x['Id'].startswith(id)]
        self.assertEqual(len(res), 0)


class TestRemoveContainerWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['true'])
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        self.client.remove_container(container)
        containers = self.client.containers(all=True)
        res = [x for x in containers if 'Id' in x and x['Id'].startswith(id)]
        self.assertEqual(len(res), 0)


class TestStartContainerWithVolumesFrom(BaseTestCase):
    def runTest(self):
        vol_names = ['foobar_vol0', 'foobar_vol1']

        res0 = self.client.create_container(
            'busybox', 'true',
            name=vol_names[0])
        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id)

        res1 = self.client.create_container(
            'busybox', 'true',
            name=vol_names[1])
        container2_id = res1['Id']
        self.tmp_containers.append(container2_id)
        self.client.start(container2_id)

        res2 = self.client.create_container(
            'busybox', 'cat',
            detach=True, stdin_open=True,
            volumes_from=vol_names)
        container3_id = res2['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(container3_id)

        info = self.client.inspect_container(res2['Id'])
        self.assertEqual(info['Config']['VolumesFrom'], ','.join(vol_names))


class TestStartContainerWithLinks(BaseTestCase):
    def runTest(self):
        res0 = self.client.create_container(
            'busybox', 'cat',
            detach=True, stdin_open=True,
            environment={'FOO': '1'})

        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)

        self.client.start(container1_id)

        res1 = self.client.create_container(
            'busybox', 'cat',
            detach=True, stdin_open=True,
            environment={'FOO': '1'})

        container2_id = res1['Id']
        self.tmp_containers.append(container2_id)

        self.client.start(container2_id)

        # we don't want the first /
        link_path1 = self.client.inspect_container(container1_id)['Name'][1:]
        link_alias1 = 'mylink1'
        link_env_prefix1 = link_alias1.upper()

        link_path2 = self.client.inspect_container(container2_id)['Name'][1:]
        link_alias2 = 'mylink2'
        link_env_prefix2 = link_alias2.upper()

        res2 = self.client.create_container('busybox', 'env')
        container3_id = res2['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(
            container3_id,
            links={link_path1: link_alias1, link_path2: link_alias2}
        )
        self.assertEqual(self.client.wait(container3_id), 0)

        logs = self.client.logs(container3_id)
        self.assertIn('{0}_NAME='.format(link_env_prefix1), logs)
        self.assertIn('{0}_ENV_FOO=1'.format(link_env_prefix1), logs)
        self.assertIn('{0}_NAME='.format(link_env_prefix2), logs)
        self.assertIn('{0}_ENV_FOO=1'.format(link_env_prefix2), logs)

#################
#  LINKS TESTS  #
#################


class TestRemoveLink(BaseTestCase):
    def runTest(self):
        # Create containers
        container1 = self.client.create_container(
            'busybox', 'cat', detach=True, stdin_open=True)
        container1_id = container1['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id)

        # Create Link
        # we don't want the first /
        link_path = self.client.inspect_container(container1_id)['Name'][1:]
        link_alias = 'mylink'

        container2 = self.client.create_container('busybox', 'cat')
        container2_id = container2['Id']
        self.tmp_containers.append(container2_id)
        self.client.start(container2_id, links={link_path: link_alias})

        # Remove link
        linked_name = self.client.inspect_container(container2_id)['Name'][1:]
        link_name = '%s/%s' % (linked_name, link_alias)
        self.client.remove_container(link_name, link=True)

        # Link is gone
        containers = self.client.containers(all=True)
        retrieved = [x for x in containers if link_name in x['Names']]
        self.assertEqual(len(retrieved), 0)

        # Containers are still there
        retrieved = [
            x for x in containers if x['Id'].startswith(container1_id)
            or x['Id'].startswith(container2_id)
        ]
        self.assertEqual(len(retrieved), 2)

##################
#  IMAGES TESTS  #
##################


class TestPull(BaseTestCase):
    def runTest(self):
        try:
            self.client.remove_image('joffrey/test001')
            self.client.remove_image('376968a23351')
        except docker.errors.APIError:
            pass
        info = self.client.info()
        self.assertIn('Images', info)
        img_count = info['Images']
        res = self.client.pull('joffrey/test001')
        self.assertEqual(type(res), six.text_type)
        self.assertEqual(img_count + 3, self.client.info()['Images'])
        img_info = self.client.inspect_image('joffrey/test001')
        self.assertIn('id', img_info)
        self.tmp_imgs.append('joffrey/test001')
        self.tmp_imgs.append('376968a23351')


class TestPullStream(BaseTestCase):
    def runTest(self):
        try:
            self.client.remove_image('joffrey/test001')
            self.client.remove_image('376968a23351')
        except docker.errors.APIError:
            pass
        info = self.client.info()
        self.assertIn('Images', info)
        img_count = info['Images']
        stream = self.client.pull('joffrey/test001', stream=True)
        for chunk in stream:
            json.loads(chunk)  # ensure chunk is a single, valid JSON blob
        self.assertEqual(img_count + 3, self.client.info()['Images'])
        img_info = self.client.inspect_image('joffrey/test001')
        self.assertIn('id', img_info)
        self.tmp_imgs.append('joffrey/test001')
        self.tmp_imgs.append('376968a23351')


class TestCommit(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        res = self.client.commit(id)
        self.assertIn('Id', res)
        img_id = res['Id']
        self.tmp_imgs.append(img_id)
        img = self.client.inspect_image(img_id)
        self.assertIn('container', img)
        self.assertTrue(img['container'].startswith(id))
        self.assertIn('container_config', img)
        self.assertIn('Image', img['container_config'])
        self.assertEqual('busybox', img['container_config']['Image'])
        busybox_id = self.client.inspect_image('busybox')['id']
        self.assertIn('parent', img)
        self.assertEqual(img['parent'], busybox_id)


class TestRemoveImage(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        res = self.client.commit(id)
        self.assertIn('Id', res)
        img_id = res['Id']
        self.tmp_imgs.append(img_id)
        self.client.remove_image(img_id)
        images = self.client.images(all=True)
        res = [x for x in images if x['Id'].startswith(img_id)]
        self.assertEqual(len(res), 0)

#################
# BUILDER TESTS #
#################


class TestBuild(BaseTestCase):
    def runTest(self):
        if self.client._version >= 1.8:
            return
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        img, logs = self.client.build(fileobj=script)
        self.assertNotEqual(img, None)
        self.assertNotEqual(img, '')
        self.assertNotEqual(logs, '')
        container1 = self.client.create_container(img, 'test -d /tmp/test')
        id1 = container1['Id']
        self.client.start(id1)
        self.tmp_containers.append(id1)
        exitcode1 = self.client.wait(id1)
        self.assertEqual(exitcode1, 0)
        container2 = self.client.create_container(img, 'test -d /tmp/test')
        id2 = container2['Id']
        self.client.start(id2)
        self.tmp_containers.append(id2)
        exitcode2 = self.client.wait(id2)
        self.assertEqual(exitcode2, 0)
        self.tmp_imgs.append(img)


class TestBuildStream(BaseTestCase):
    def runTest(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        stream = self.client.build(fileobj=script, stream=True)
        logs = ''
        for chunk in stream:
            json.loads(chunk)  # ensure chunk is a single, valid JSON blob
            logs += chunk
        self.assertNotEqual(logs, '')


class TestBuildFromStringIO(BaseTestCase):
    def runTest(self):
        if six.PY3:
            return
        script = io.StringIO(u'\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]))
        stream = self.client.build(fileobj=script, stream=True)
        logs = ''
        for chunk in stream:
            logs += chunk
        self.assertNotEqual(logs, '')


class TestBuildWithAuth(BaseTestCase):
    def runTest(self):
        if self.client._version < 1.9:
            return

        k = 'K4104GON3P4Q6ZUJFZRRC2ZQTBJ5YT0UMZD7TGT7ZVIR8Y05FAH2TJQI6Y90SMIB'
        self.client.login('quay+fortesting', k, registry='https://quay.io/v1/',
                          email='')

        script = io.BytesIO('\n'.join([
            'FROM quay.io/quay/teststuff',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
        ]).encode('ascii'))

        stream = self.client.build(fileobj=script, stream=True)
        logs = ''
        for chunk in stream:
            logs += chunk

        self.assertNotEqual(logs, '')
        self.assertEqual(logs.find('HTTP code: 403'), -1)


#######################
#  PY SPECIFIC TESTS  #
#######################


class TestRunShlex(BaseTestCase):
    def runTest(self):
        commands = [
            'true',
            'echo "The Young Descendant of Tepes & Septette for the '
            'Dead Princess"',
            'echo -n "The Young Descendant of Tepes & Septette for the '
            'Dead Princess"',
            '/bin/sh -c "echo Hello World"',
            '/bin/sh -c \'echo "Hello World"\'',
            'echo "\"Night of Nights\""',
            'true && echo "Night of Nights"'
        ]
        for cmd in commands:
            container = self.client.create_container('busybox', cmd)
            id = container['Id']
            self.client.start(id)
            self.tmp_containers.append(id)
            exitcode = self.client.wait(id)
            self.assertEqual(exitcode, 0, msg=cmd)


class TestLoadConfig(BaseTestCase):
    def runTest(self):
        folder = tempfile.mkdtemp()
        f = open(os.path.join(folder, '.dockercfg'), 'w')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        f.write('auth = {0}\n'.format(auth_))
        f.write('email = sakuya@scarlet.net')
        f.close()
        cfg = docker.auth.load_config(folder)
        self.assertNotEqual(cfg[docker.auth.INDEX_URL], None)
        cfg = cfg[docker.auth.INDEX_URL]
        self.assertEqual(cfg['username'], b'sakuya')
        self.assertEqual(cfg['password'], b'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('Auth'), None)


class TestLoadJSONConfig(BaseTestCase):
    def runTest(self):
        folder = tempfile.mkdtemp()
        f = open(os.path.join(folder, '.dockercfg'), 'w')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        email_ = 'sakuya@scarlet.net'
        f.write('{{"{}": {{"auth": "{}", "email": "{}"}}}}\n'.format(
            docker.auth.INDEX_URL, auth_, email_))
        f.close()
        cfg = docker.auth.load_config(folder)
        self.assertNotEqual(cfg[docker.auth.INDEX_URL], None)
        cfg = cfg[docker.auth.INDEX_URL]
        self.assertEqual(cfg['username'], b'sakuya')
        self.assertEqual(cfg['password'], b'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('Auth'), None)


class TestConnectionTimeout(unittest.TestCase):
    def setUp(self):
        self.timeout = 0.5
        self.client = docker.client.Client(base_url='http://192.168.10.2:4243',
                                           timeout=self.timeout)

    def runTest(self):
        start = time.time()
        res = None
        # This call isn't supposed to complete, and it should fail fast.
        try:
            res = self.client.inspect_container('id')
        except:
            pass
        end = time.time()
        self.assertTrue(res is None)
        self.assertTrue(end - start < 2 * self.timeout)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test
# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import base64
import datetime
import io
import json
import os
import signal
import tempfile
import unittest
import gzip

import docker
import requests
import six

import fake_api


try:
    from unittest import mock
except ImportError:
    import mock


def response(status_code=200, content='', headers=None, reason=None, elapsed=0,
             request=None):
    res = requests.Response()
    res.status_code = status_code
    if not isinstance(content, six.string_types):
        content = json.dumps(content)
    if six.PY3:
        content = content.encode('ascii')
    res._content = content
    res.headers = requests.structures.CaseInsensitiveDict(headers or {})
    res.reason = reason
    res.elapsed = datetime.timedelta(elapsed)
    res.request = request
    return res


def fake_resp(url, data=None, **kwargs):
    status_code, content = fake_api.fake_responses[url]()
    return response(status_code=status_code, content=content)

fake_request = mock.Mock(side_effect=fake_resp)
url_prefix = 'http+unix://var/run/docker.sock/v{0}/'.format(
    docker.client.DEFAULT_DOCKER_API_VERSION)


@mock.patch.multiple('docker.Client', get=fake_request, post=fake_request,
                     put=fake_request, delete=fake_request)
class DockerClientTest(unittest.TestCase):
    def setUp(self):
        self.client = docker.Client()
        # Force-clear authconfig to avoid tampering with the tests
        self.client._cfg = {'Configs': {}}

    #########################
    #   INFORMATION TESTS   #
    #########################
    def test_version(self):
        try:
            self.client.version()
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'version',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_info(self):
        try:
            self.client.info()
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'info',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_search(self):
        try:
            self.client.search('busybox')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/search',
            params={'term': 'busybox'},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_viz(self):
        try:
            self.client.images('busybox', viz=True)
            self.fail('Viz output should not be supported!')
        except Exception:
            pass

    ###################
    #  LISTING TESTS  #
    ###################

    def test_images(self):
        try:
            self.client.images(all=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        fake_request.assert_called_with(
            url_prefix + 'images/json',
            params={'filter': None, 'only_ids': 0, 'all': 1},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_images_quiet(self):
        try:
            self.client.images(all=True, quiet=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        fake_request.assert_called_with(
            url_prefix + 'images/json',
            params={'filter': None, 'only_ids': 1, 'all': 1},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_ids(self):
        try:
            self.client.images(quiet=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/json',
            params={'filter': None, 'only_ids': 1, 'all': 0},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_list_containers(self):
        try:
            self.client.containers(all=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/json',
            params={
                'all': 1,
                'since': None,
                'limit': -1,
                'trunc_cmd': 1,
                'before': None
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    #####################
    #  CONTAINER TESTS  #
    #####################

    def test_create_container(self):
        try:
            self.client.create_container('busybox', 'true')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": false, "Memory": 0,
                             "AttachStderr": true, "AttachStdout": true,
                             "StdinOnce": false,
                             "OpenStdin": false, "NetworkDisabled": false,
                             "MemorySwap": 0}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_binds(self):
        mount_dest = '/mnt'

        try:
            self.client.create_container('busybox', ['ls', mount_dest],
                                         volumes=[mount_dest])
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls", "/mnt"], "AttachStdin": false,
                             "Volumes": {"/mnt": {}}, "Memory": 0,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "MemorySwap": 0}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_ports(self):
        try:
            self.client.create_container('busybox', 'ls',
                                         ports=[1111, (2222, 'udp'), (3333,)])
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls"], "AttachStdin": false,
                             "Memory": 0, "ExposedPorts": {
                                "1111/tcp": {},
                                "2222/udp": {},
                                "3333/tcp": {}
                             },
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "MemorySwap": 0}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_entrypoint(self):
        try:
            self.client.create_container('busybox', 'hello',
                                         entrypoint='cowsay')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["hello"], "AttachStdin": false,
                             "Memory": 0,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "Entrypoint": "cowsay",
                             "MemorySwap": 0}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_cpu_shares(self):
        try:
            self.client.create_container('busybox', 'ls',
                                         cpu_shares=5)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls"], "AttachStdin": false,
                             "Memory": 0,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "CpuShares": 5,
                             "MemorySwap": 0}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_working_dir(self):
        try:
            self.client.create_container('busybox', 'ls',
                                         working_dir='/root')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls"], "AttachStdin": false,
                             "Memory": 0,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "WorkingDir": "/root",
                             "MemorySwap": 0}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_stdin_open(self):
        try:
            self.client.create_container('busybox', 'true', stdin_open=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": true, "Memory": 0,
                             "AttachStderr": true, "AttachStdout": true,
                             "StdinOnce": true,
                             "OpenStdin": true, "NetworkDisabled": false,
                             "MemorySwap": 0}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_volumes_from(self):
        vol_names = ['foo', 'bar']
        try:
            self.client.create_container('busybox', 'true',
                                         volumes_from=vol_names)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        args = fake_request.call_args
        self.assertEqual(args[0][0], url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data'])['VolumesFrom'],
                         ','.join(vol_names))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_empty_volumes_from(self):
        try:
            self.client.create_container('busybox', 'true', volumes_from=[])
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        self.assertTrue('VolumesFrom' not in data)

    def test_create_named_container(self):
        try:
            self.client.create_container('busybox', 'true',
                                         name='marisa-kirisame')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": false, "Memory": 0,
                             "AttachStderr": true, "AttachStdout": true,
                             "StdinOnce": false,
                             "OpenStdin": false, "NetworkDisabled": false,
                             "MemorySwap": 0}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(args[1]['params'], {'name': 'marisa-kirisame'})

    def test_start_container(self):
        try:
            self.client.start(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            raise e
            self.fail('Command should not raise exception: {0}'.format(e))
        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {"PublishAllPorts": False, "Privileged": False}
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_lxc_conf(self):
        try:
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                lxc_conf={'lxc.conf.k': 'lxc.conf.value'}
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {"LxcConf": [{"Value": "lxc.conf.value", "Key": "lxc.conf.k"}],
             "PublishAllPorts": False, "Privileged": False}
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_lxc_conf_compat(self):
        try:
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                lxc_conf=[{'Key': 'lxc.conf.k', 'Value': 'lxc.conf.value'}]
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0], url_prefix +
                         'containers/3cc2351ab11b/start')
        self.assertEqual(
            json.loads(args[1]['data']),
            {
                "LxcConf": [{"Key": "lxc.conf.k", "Value": "lxc.conf.value"}],
                "PublishAllPorts": False,
                "Privileged": False,
            }
        )
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_binds_ro(self):
        try:
            mount_dest = '/mnt'
            mount_origin = '/tmp'
            self.client.start(fake_api.FAKE_CONTAINER_ID,
                              binds={mount_origin: {
                                  "bind": mount_dest,
                                  "ro": True
                              }})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0], url_prefix +
                         'containers/3cc2351ab11b/start')
        self.assertEqual(json.loads(args[1]['data']),
                         {"Binds": ["/tmp:/mnt:ro"],
                          "PublishAllPorts": False,
                          "Privileged": False})
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS)

    def test_start_container_with_binds_rw(self):
        try:
            mount_dest = '/mnt'
            mount_origin = '/tmp'
            self.client.start(fake_api.FAKE_CONTAINER_ID,
                              binds={mount_origin: {
                                     "bind": mount_dest, "ro": False}})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0], url_prefix +
                         'containers/3cc2351ab11b/start')
        self.assertEqual(json.loads(args[1]['data']),
                         {"Binds": ["/tmp:/mnt:rw"],
                          "PublishAllPorts": False,
                          "Privileged": False})
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_port_binds(self):
        self.maxDiff = None
        try:
            self.client.start(fake_api.FAKE_CONTAINER_ID, port_bindings={
                1111: None,
                2222: 2222,
                '3333/udp': (3333,),
                4444: ('127.0.0.1',),
                5555: ('127.0.0.1', 5555),
                6666: [('127.0.0.1',), ('192.168.0.1',)]
            })
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0], url_prefix +
                         'containers/3cc2351ab11b/start')
        data = json.loads(args[1]['data'])
        self.assertEqual(data['PublishAllPorts'], False)
        self.assertTrue('1111/tcp' in data['PortBindings'])
        self.assertTrue('2222/tcp' in data['PortBindings'])
        self.assertTrue('3333/udp' in data['PortBindings'])
        self.assertTrue('4444/tcp' in data['PortBindings'])
        self.assertTrue('5555/tcp' in data['PortBindings'])
        self.assertTrue('6666/tcp' in data['PortBindings'])
        self.assertEqual(
            [{"HostPort": "", "HostIp": ""}],
            data['PortBindings']['1111/tcp']
        )
        self.assertEqual(
            [{"HostPort": "2222", "HostIp": ""}],
            data['PortBindings']['2222/tcp']
        )
        self.assertEqual(
            [{"HostPort": "3333", "HostIp": ""}],
            data['PortBindings']['3333/udp']
        )
        self.assertEqual(
            [{"HostPort": "", "HostIp": "127.0.0.1"}],
            data['PortBindings']['4444/tcp']
        )
        self.assertEqual(
            [{"HostPort": "5555", "HostIp": "127.0.0.1"}],
            data['PortBindings']['5555/tcp']
        )
        self.assertEqual(len(data['PortBindings']['6666/tcp']), 2)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_links(self):
        # one link
        try:
            link_path = 'path'
            alias = 'alias'
            self.client.start(fake_api.FAKE_CONTAINER_ID,
                              links={link_path: alias})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {"PublishAllPorts": False, "Privileged": False,
             "Links": ["path:alias"]}
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )

    def test_start_container_with_multiple_links(self):
        try:
            link_path = 'path'
            alias = 'alias'
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                links={
                    link_path + '1': alias + '1',
                    link_path + '2': alias + '2'
                }
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {
                "PublishAllPorts": False,
                "Privileged": False,
                "Links": ["path1:alias1", "path2:alias2"]
            }
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )

    def test_start_container_with_links_as_list_of_tuples(self):
        # one link
        try:
            link_path = 'path'
            alias = 'alias'
            self.client.start(fake_api.FAKE_CONTAINER_ID,
                              links=[(link_path, alias)])
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {"PublishAllPorts": False, "Privileged": False,
             "Links": ["path:alias"]}
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )

    def test_start_container_privileged(self):
        try:
            self.client.start(fake_api.FAKE_CONTAINER_ID, privileged=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(json.loads(args[1]['data']),
                         {"PublishAllPorts": False, "Privileged": True})
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_dict_instead_of_id(self):
        try:
            self.client.start({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {"PublishAllPorts": False, "Privileged": False}
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_wait(self):
        try:
            self.client.wait(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/wait',
            timeout=None
        )

    def test_wait_with_dict_instead_of_id(self):
        try:
            self.client.wait({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            raise e
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/wait',
            timeout=None
        )

    def test_url_compatibility_unix(self):
        c = docker.Client(base_url="unix://socket")

        assert c.base_url == "http+unix://socket"

    def test_url_compatibility_unix_triple_slash(self):
        c = docker.Client(base_url="unix:///socket")

        assert c.base_url == "http+unix://socket"

    def test_url_compatibility_http_unix_triple_slash(self):
        c = docker.Client(base_url="http+unix:///socket")

        assert c.base_url == "http+unix://socket"

    def test_url_compatibility_http(self):
        c = docker.Client(base_url="http://hostname")

        assert c.base_url == "http://hostname"

    def test_url_compatibility_tcp(self):
        c = docker.Client(base_url="tcp://hostname")

        assert c.base_url == "http://hostname"

    def test_logs(self):
        try:
            self.client.logs(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/attach',
            params={'stream': 0, 'logs': 1, 'stderr': 1, 'stdout': 1},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS,
            stream=False
        )

    def test_logs_with_dict_instead_of_id(self):
        try:
            self.client.logs({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/attach',
            params={'stream': 0, 'logs': 1, 'stderr': 1, 'stdout': 1},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS,
            stream=False
        )

    def test_log_streaming(self):
        try:
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/attach',
            params={'stream': 1, 'logs': 1, 'stderr': 1, 'stdout': 1},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS,
            stream=True
        )

    def test_diff(self):
        try:
            self.client.diff(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/changes',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_diff_with_dict_instead_of_id(self):
        try:
            self.client.diff({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/changes',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_port(self):
        try:
            self.client.port({'Id': fake_api.FAKE_CONTAINER_ID}, 1111)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/json',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_stop_container(self):
        try:
            self.client.stop(fake_api.FAKE_CONTAINER_ID, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/stop',
            params={'t': 2},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_stop_container_with_dict_instead_of_id(self):
        try:
            self.client.stop({'Id': fake_api.FAKE_CONTAINER_ID}, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/stop',
            params={'t': 2},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_kill_container(self):
        try:
            self.client.kill(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/kill',
            params={},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_kill_container_with_dict_instead_of_id(self):
        try:
            self.client.kill({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/kill',
            params={},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_kill_container_with_signal(self):
        try:
            self.client.kill(fake_api.FAKE_CONTAINER_ID, signal=signal.SIGTERM)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/kill',
            params={'signal': signal.SIGTERM},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_restart_container(self):
        try:
            self.client.restart(fake_api.FAKE_CONTAINER_ID, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception : {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/restart',
            params={'t': 2},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_restart_container_with_dict_instead_of_id(self):
        try:
            self.client.restart({'Id': fake_api.FAKE_CONTAINER_ID}, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/restart',
            params={'t': 2},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_container(self):
        try:
            self.client.remove_container(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b',
            params={'v': False, 'link': False, 'force': False},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_container_with_dict_instead_of_id(self):
        try:
            self.client.remove_container({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b',
            params={'v': False, 'link': False, 'force': False},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_link(self):
        try:
            self.client.remove_container(fake_api.FAKE_CONTAINER_ID, link=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b',
            params={'v': False, 'link': True, 'force': False},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_export(self):
        try:
            self.client.export(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/export',
            stream=True,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_export_with_dict_instead_of_id(self):
        try:
            self.client.export({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/export',
            stream=True,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_inspect_container(self):
        try:
            self.client.inspect_container(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/json',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    ##################
    #  IMAGES TESTS  #
    ##################

    def test_pull(self):
        try:
            self.client.pull('joffrey/test001')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'images/create'
        )
        self.assertEqual(
            args[1]['params'],
            {'tag': None, 'fromImage': 'joffrey/test001'}
        )
        self.assertFalse(args[1]['stream'])

    def test_pull_stream(self):
        try:
            self.client.pull('joffrey/test001', stream=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'images/create'
        )
        self.assertEqual(
            args[1]['params'],
            {'tag': None, 'fromImage': 'joffrey/test001'}
        )
        self.assertTrue(args[1]['stream'])

    def test_commit(self):
        try:
            self.client.commit(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'commit',
            data='{}',
            headers={'Content-Type': 'application/json'},
            params={
                'repo': None,
                'comment': None,
                'tag': None,
                'container': '3cc2351ab11b',
                'author': None
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_image(self):
        try:
            self.client.remove_image(fake_api.FAKE_IMAGE_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/e9aa60c60128',
            params={'force': False, 'noprune': False},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_history(self):
        try:
            self.client.history(fake_api.FAKE_IMAGE_NAME)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/test_image/history',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_import_image(self):
        try:
            self.client.import_image(
                fake_api.FAKE_TARBALL_PATH,
                repository=fake_api.FAKE_REPO_NAME,
                tag=fake_api.FAKE_TAG_NAME
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/create',
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromSrc': fake_api.FAKE_TARBALL_PATH
            },
            data=None,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_import_image_from_file(self):
        buf = tempfile.NamedTemporaryFile(delete=False)
        try:
            # pretent the buffer is a file
            self.client.import_image(
                buf.name,
                repository=fake_api.FAKE_REPO_NAME,
                tag=fake_api.FAKE_TAG_NAME
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/create',
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromSrc': '-'
            },
            data='',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )
        buf.close()
        os.remove(buf.name)

    def test_import_image_from_image(self):
        try:
            self.client.import_image(
                image=fake_api.FAKE_IMAGE_NAME,
                repository=fake_api.FAKE_REPO_NAME,
                tag=fake_api.FAKE_TAG_NAME
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/create',
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromImage': fake_api.FAKE_IMAGE_NAME
            },
            data=None,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_inspect_image(self):
        try:
            self.client.inspect_image(fake_api.FAKE_IMAGE_NAME)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/test_image/json',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_insert_image(self):
        try:
            self.client.insert(fake_api.FAKE_IMAGE_NAME,
                               fake_api.FAKE_URL, fake_api.FAKE_PATH)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/test_image/insert',
            params={
                'url': fake_api.FAKE_URL,
                'path': fake_api.FAKE_PATH
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image(self):
        try:
            self.client.push(fake_api.FAKE_IMAGE_NAME)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/test_image/push',
            data='{}',
            headers={'Content-Type': 'application/json'},
            stream=False,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image_stream(self):
        try:
            self.client.push(fake_api.FAKE_IMAGE_NAME, stream=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/test_image/push',
            data='{}',
            headers={'Content-Type': 'application/json'},
            stream=True,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image(self):
        try:
            self.client.tag(fake_api.FAKE_IMAGE_ID, fake_api.FAKE_REPO_NAME)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/e9aa60c60128/tag',
            params={
                'tag': None,
                'repo': 'repo',
                'force': 0
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image_tag(self):
        try:
            self.client.tag(
                fake_api.FAKE_IMAGE_ID,
                fake_api.FAKE_REPO_NAME,
                tag=fake_api.FAKE_TAG_NAME
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/e9aa60c60128/tag',
            params={
                'tag': 'tag',
                'repo': 'repo',
                'force': 0
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image_force(self):
        try:
            self.client.tag(
                fake_api.FAKE_IMAGE_ID, fake_api.FAKE_REPO_NAME, force=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/e9aa60c60128/tag',
            params={
                'tag': None,
                'repo': 'repo',
                'force': 1
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    #################
    # BUILDER TESTS #
    #################

    def test_build_container(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        try:
            self.client.build(fileobj=script)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

    def test_build_container_stream(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        try:
            self.client.build(fileobj=script, stream=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

    def test_build_container_custom_context(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        context = docker.utils.mkbuildcontext(script)
        try:
            self.client.build(fileobj=context, custom_context=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

    def test_build_container_custom_context_gzip(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        context = docker.utils.mkbuildcontext(script)
        gz_context = gzip.GzipFile(fileobj=context)
        try:
            self.client.build(
                fileobj=gz_context,
                custom_context=True,
                encoding="gzip"
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

    #######################
    #  PY SPECIFIC TESTS  #
    #######################

    def test_load_config_no_file(self):
        folder = tempfile.mkdtemp()
        cfg = docker.auth.load_config(folder)
        self.assertTrue(cfg is not None)

    def test_load_config(self):
        folder = tempfile.mkdtemp()
        f = open(os.path.join(folder, '.dockercfg'), 'w')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        f.write('auth = {0}\n'.format(auth_))
        f.write('email = sakuya@scarlet.net')
        f.close()
        cfg = docker.auth.load_config(folder)
        self.assertTrue(docker.auth.INDEX_URL in cfg)
        self.assertNotEqual(cfg[docker.auth.INDEX_URL], None)
        cfg = cfg[docker.auth.INDEX_URL]
        self.assertEqual(cfg['username'], 'sakuya')
        self.assertEqual(cfg['password'], 'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('auth'), None)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils_test
import unittest

from docker.utils import parse_repository_tag


class UtilsTest(unittest.TestCase):

    def test_parse_repository_tag(self):
        self.assertEqual(parse_repository_tag("root"),
                         ("root", ""))
        self.assertEqual(parse_repository_tag("root:tag"),
                         ("root", "tag"))
        self.assertEqual(parse_repository_tag("user/repo"),
                         ("user/repo", ""))
        self.assertEqual(parse_repository_tag("user/repo:tag"),
                         ("user/repo", "tag"))
        self.assertEqual(parse_repository_tag("url:5000/repo"),
                         ("url:5000/repo", ""))
        self.assertEqual(parse_repository_tag("url:5000/repo:tag"),
                         ("url:5000/repo", "tag"))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
