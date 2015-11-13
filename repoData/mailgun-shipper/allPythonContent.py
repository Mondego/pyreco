__FILENAME__ = auto
"""
Copyright [2013] [Rackspace]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import inspect
from collections import namedtuple

Arg = namedtuple("Arg", "name default")
NoDefault = object()


def generate(parser, *fn):
    subparsers = parser.add_subparsers(help="Yo")
    for fn in fn:
        _from_function(subparsers, fn)


def _from_function(subparsers, fn):
    arguments = _inspect_arguments(fn)
    parser = subparsers.add_parser(fn.__name__, help=fn.__doc__)
    parser.set_defaults(fn=fn)
    for a in arguments:
        if a.default is NoDefault:
            parser.add_argument(a.name)
        else:
            if a.default in (True, False):
                parser.add_argument(
                    "--{}".format(a.name),
                    choices=["yes", "no"],
                    default="yes" if a.default else "no")
            else:
                parser.add_argument("--{}".format(a.name), default=a.default)

    def call(args):
        kwargs = {}
        for a in arguments:
            kwargs[a.name] = getattr(args, a.name)
            if a.default in (True, False):
                kwargs[a.name] = kwargs[a.name].lower().strip() == "yes"
        return fn(**kwargs)

    parser.set_defaults(fn=call)


def _inspect_arguments(fn):
    spec = inspect.getargspec(fn)
    sdefaults = list(spec.defaults or [])
    defaults = ([NoDefault] * (len(spec.args) - len(sdefaults))) + sdefaults
    parsed = []
    for arg, default in zip(spec.args, defaults):
        parsed.append(Arg(name=arg, default=default))

    return parsed

########NEW FILE########
__FILENAME__ = build
"""
Copyright [2013] [Rackspace]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os.path
import tarfile

from StringIO import StringIO


class DockerFile(object):
    """Represents the docker file that can be either
    * a remote http, https, or git url
    * a local url
    * or a local tar archive
    """
    def __init__(self, path=None, fobj=None):
        self.archive, self.url = _parse_build(path, fobj)

    @property
    def is_remote(self):
        return bool(self.url)

    @property
    def is_local(self):
        return self.archive is not None


def _parse_build(path=None, fobj=None):
    """Parses build parameters. Returns tuple
    (archive, remote)

    Where archive is a tar archive and remote is remote url if set.
    One of the tuple elements will be null

    """
    if path:
        for prefix in ('http://', 'https://', 'github.com/', 'git://'):
            if path.startswith(prefix):
                return None, path
        if path.startswith("~"):
            path = os.path.expanduser(path)
        return _archive_from_folder(path), None
    else:
        if not fobj:
            raise ValueError("Set path or fobj")
        return _archive_from_file(fobj), None


def _archive_from_folder(path):
    memfile = StringIO()
    try:
        t = tarfile.open(mode='w', fileobj=memfile)
        t.add(path, arcname='.')
        return memfile.getvalue()
    finally:
        memfile.close()


def _archive_from_file(dockerfile):
    memfile = StringIO()
    try:
        t = tarfile.open(mode='w', fileobj=memfile)
        if isinstance(dockerfile, StringIO):
            dfinfo = tarfile.TarInfo('Dockerfile')
            dfinfo.size = dockerfile.len
        else:
            dfinfo = t.gettarinfo(fileobj=dockerfile, arcname='Dockerfile')
        t.addfile(dfinfo, dockerfile)
        return memfile.getvalue()
    finally:
        memfile.close()

########NEW FILE########
__FILENAME__ = client
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

"""Twisted based client with paralell execution in mind and fixes
quirks of the official docker-py client.
"""
import re
import json
import logging
import logging.handlers
from copy import copy

from twisted.internet import reactor
from twisted.web.client import HTTPConnectionPool
from twisted.internet.defer import Deferred, succeed
from twisted.internet.protocol import Protocol
from twisted.web.client import ResponseDone
import treq
from .errors import assert_code


class Client(object):
    """A generic twisted-based docker client that supports all sorts of
    docker magic like streaming replies and http session hijacking on
    container attach.
    """

    pool = None
    log = None

    def __init__(self, version="1.6", timeout=None, log=None, pool=None):
        self.pool = pool or HTTPConnectionPool(reactor, persistent=False)
        self.version = version
        self.timeout = timeout
        self.log = log or logging.getLogger(__name__)

    def build(self, host, dockerfile, tag=None, quiet=False,
              nocache=False, rm=False):
        """Run build of a container from buildfile
        that can be passed as local/remote path or file object(fobj)
        """
        params = {
            'q': quiet,
            'nocache': nocache,
            'rm': rm
        }

        if dockerfile.is_remote:
            params['remote'] = dockerfile.url
        if tag:
            params['t'] = tag

        headers = {}
        if not dockerfile.is_remote:
            headers = {'Content-Type': 'application/tar'}

        container = []
        result = Deferred()

        def on_content(line):
            if line:
                self.log.debug("{}: {}".format(host, line.strip()))
                match = re.search(r'Successfully built ([0-9a-f]+)', line)
                if match:
                    container.append(match.group(1))

        d = treq.post(
            url=self._make_url(host.url, 'build'),
            data=dockerfile.archive,
            params=params,
            headers=headers,
            pool=self.pool)

        def on_done(*args, **kwargs):
            if not container:
                result.errback(RuntimeError("Build failed"))
            else:
                result.callback(container[0])

        d.addCallback(treq.collect, on_content)
        d.addBoth(on_done)
        return result

    def images(self, host, name=None, quiet=False,
               all=False, viz=False, pretty=False):
        path = "images/viz" if viz else "images/json"
        params = {
            'only_ids': 1 if quiet else 0,
            'all': 1 if all else 0,
            'params': name
        }

        return self.request(treq.get, host, path,
                            params=params,
                            expect_json=not viz)

    def containers(self, host,
                   quiet=False, all=False, trunc=True, latest=False,
                   since=None, before=None, limit=-1, pretty=False,
                   running=None, image=None):
        params = {
            'limit': 1 if latest else limit,
            'only_ids': 1 if quiet else 0,
            'all': 1 if all else 0,
            'trunc_cmd': 1 if trunc else 0,
            'since': since,
            'before': before
        }
        return self.get(host, 'containers/ps', params=params)

    def create_container(self, host, config, name=None):
        params = {}
        if name:
            params['name'] = name
        return self.post(
            host,
            "containers/create",
            params=params,
            data=config.to_json(),
            post_json=True)

    def inspect(self, host, container):
        return self.get(
            host, "containers/{}/json".format(container.id),
            expect_json=True)

    def start(self, host, container, binds=None, port_binds=None, links=[]):
        self.log.debug("Starting {} {} {}".format(container,
                                                  binds, port_binds))
        data = {}
        if binds:
            data['Binds'] = binds
        if port_binds:
            data['PortBindings'] = port_binds
        if links:
            data['Links'] = links

        return self.post(
            host, "containers/{}/start".format(container.id),
            data=data,
            post_json=True,
            expect_json=False)

    def stop(self, host, container, wait_seconds=5):
        self.log.debug("Stopping {}".format(container))
        return self.post(host, "containers/{}/stop".format(container.id),
                         params={'t': wait_seconds},
                         expect_json=False)

    def attach(self, host, container, **kwargs):
        def c(v):
            return 1 if kwargs.get(v) else 0
        params = {
            'logs': c('logs'),
            'stream': c('stream'),
            'stdin': 0,
            'stdout': c('stdout'),
            'stderr': c('stderr')
        }

        result = Deferred()

        def on_content(line):
            if line:
                self.log.debug("{}: {}".format(host, line.strip()))

        url = self._make_url(
            host.url, 'containers/{}/attach'.format(container.id))
        d = treq.post(
            url=url,
            params=params,
            pool=self.pool)

        d.addCallback(_Reader.listen, kwargs.get('stop_line'))

        def on_error(failure):
            pass
        d.addErrback(on_error)
        return result

    def wait(self, host, container):
        """Waits for the container to stop and gets the exit code"""

        def log_results(results):
            self.log.debug("{0} has stopped with exit code {1}".format(
                container, results['StatusCode']))
            return results

        d = self.post(
            host, "containers/{}/wait".format(container.id),
            expect_json=True)

        d.addCallback(log_results)
        return d

    def request(self, method, host, path, **kwargs):

        kwargs = copy(kwargs)
        kwargs['params'] = _remove_empty(kwargs.get('params'))
        kwargs['pool'] = self.pool

        post_json = kwargs.pop('post_json', False)
        if post_json:
            headers = kwargs.setdefault('headers', {})
            headers['Content-Type'] = ['application/json']
            kwargs['data'] = json.dumps(kwargs['data'])

        kwargs['url'] = self._make_url(host.url, path)
        expect_json = kwargs.pop('expect_json', True)

        result = Deferred()
        d = method(**kwargs)

        def content(response):
            content = []
            cd = treq.collect(response, content.append)
            cd.addCallback(lambda _: ''.join(content))
            cd.addCallback(done, response)
            return cd

        def done(content, response):
            assert_code(response.code, content)
            if expect_json:
                content = json.loads(content)
            return content

        d.addCallback(content)
        d.addCallback(result.callback)
        d.addErrback(result.errback)

        return result

    def get(self, host, path, **kwargs):
        return self.request(treq.get, host, path, **kwargs)

    def post(self, host, path, **kwargs):
        return self.request(treq.post, host, path, **kwargs)

    def delete(self, host, path, **kwargs):
        return self.request(treq.post, host, path, **kwargs)

    def _make_url(self, url, method):
        return "{}/v{}/{}".format(url, self.version, method)


def _remove_empty(params):
    params = params or {}
    clean_params = copy(params)
    for key, val in params.iteritems():
        if val is None:
            del clean_params[key]
    return clean_params


class _Reader(Protocol):
    def __init__(self, finished, stop_line):
        self.finished = finished
        if stop_line:
            self.stop_line = re.compile(stop_line, re.I)
        else:
            self.stop_line = None

    def dataReceived(self, data):
        if self.stop_line and self.stop_line.search(data):
            self.transport._producer.looseConnection()

    def connectionLost(self, reason):
        if reason.check(ResponseDone):
            self.finished.callback(None)
            return
        self.finished.errback(reason)

    @classmethod
    def listen(cls, response, data):
        if response.length == 0:
            return succeed(None)
        d = Deferred()
        response.deliverBody(cls(d, data))
        return d

########NEW FILE########
__FILENAME__ = container
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

import six
import shlex

from .utils import from_epoch, parse_ports


class ContainerConfig(dict):
    """Container configuration helper.
    """
    def __init__(self, image, command, **kwargs):
        dict.__init__(self)
        self.host = None

        if isinstance(command, six.string_types):
            command = shlex.split(command)

        get = kwargs.get
        exposed_ports, _ = parse_ports(get('ports', []))
        self.update({
            'Hostname': get('hostname'),
            'ExposedPorts': exposed_ports,
            'User': get('user'),
            'Tty': get('tty', False),
            'OpenStdin': get('open_stdin', False),
            'Memory': get('mem_limit', 0),
            'AttachStdin': get('stdin', False),
            'AttachStdout': get('stdout', False),
            'AttachStderr': get('stderr', False),
            'Env': get('environment'),
            'Cmd': command,
            'Dns': get('dns'),
            'Image': image,
            'Volumes': get('volumes'),
            'VolumesFrom': get('volumes_from'),
            'StdinOnce': get('stdin_once', False)
        })

    def to_json(self):
        return self


class Container(dict):
    """Helper wrapper around container dictionary
    to ease access to certain properties
    """
    def __init__(self, host, values):
        dict.__init__(self)
        self.host = host
        self.update(values)

    def __str__(self):
        return "Container(host={}, {})".format(
            self.host, dict.__str__(self))

    @property
    def id(self):
        return self.get('Id')

    @property
    def command(self):
        return (self.get('Command') or "").strip()

    @property
    def is_running(self):
        return self.status.startswith("Up")

    @property
    def is_stopped(self):
        return self.status.startswith("Exit")

    @property
    def image(self):
        return (self.get('Image') or "").strip()

    @property
    def created(self):
        return from_epoch(self['Created'])

    @property
    def status(self):
        return self.get("Status") or ""

    @property
    def ports(self):
        return self['Ports']

    @property
    def ip(self):
        return self['NetworkSettings']['IPAddress']

########NEW FILE########
__FILENAME__ = errors
"""
Copyright [2013] [Rackspace]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


def assert_code(code, message):
    """Raises stored :class:`HTTPError`, if one occurred."""

    if 400 <= code < 500:
        raise RuntimeError('{} Client Error: {}'.format(
            code, message))

    elif 500 <= code < 600:
        raise RuntimeError('{} Server Error: {}'.format(
            code, message))

########NEW FILE########
__FILENAME__ = host
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

import re
from urlparse import urlparse, urlunparse


def parse_hosts(hosts, default_port=4243):
    """Converts hosts in free form to list of urls
    """
    out = []
    for param in (hosts or []):

        if isinstance(param, (tuple, list)):
            if len(param) != 2:
                raise ValueError("Param should be (host, port)")
            host, port = param
            out.append(Host("http://{}:{}".format(host, port)))

        elif isinstance(param, str):
            if not (param.startswith("http://") or
                    param.startswith("https://")):
                param = "http://{}".format(param)

            if not re.search(r":\d+", param):
                param = "{}:{}".format(param, default_port)
            out.append(Host(param))
        else:
            raise ValueError(
                "Unsupported parameter type: {}".format(type(param)))
    return out


class Host(object):
    """Represents docker-enabled host.
    Is hasheable, can be put into dictionaries.
    """
    def __init__(self, url):
        self.a = urlparse(url)

    @property
    def url(self):
        return urlunparse(self.a)

    def __str__(self):
        return "Host({})".format(self.a.netloc)

    def __repr__(self):
        return "Host({})".format(self.a.netloc)

    def __hash__(self):
        return hash(str(self.a))

    def __eq__(self, other):
        return str(self.a) == other

########NEW FILE########
__FILENAME__ = image
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

from .utils import from_epoch


class Image(dict):
    def __init__(self, host, values):
        dict.__init__(self)
        self.update(values)
        self.host = host

    def __str__(self):
        return "Image(host={}, values={})".format(
            self.host, dict.__str__(self))

    @property
    def repository(self):
        return self.get('Repository') or ''

    @property
    def tag(self):
        return self.get('Tag') or ''

    @property
    def created(self):
        return from_epoch(self['Created'])

    @property
    def id(self):
        return self.get('Id')

    @property
    def size(self):
        return self['Size']

########NEW FILE########
__FILENAME__ = pretty
"""Pretty printing for containers and images
"""
from StringIO import StringIO
from contextlib import closing

from texttable import Texttable as TextTable

from .utils import time_ago, human_size


def images_to_ascii_table(images):
    """Just a method that formats the images to ascii table.
    Expects dictionary {host: [images]}
    and prints multiple tables
    """
    with closing(StringIO()) as out:
        for host, values in images.iteritems():
            out.write(str(host) + "\n")
            t = TextTable()
            t.set_deco(TextTable.HEADER)
            t.set_cols_dtype(['t'] * 5)
            t.set_cols_align(["l"] * 5)
            rows = []
            rows.append(['Repository', 'Tag', 'Id', 'Created', 'Size'])
            for image in values:
                rows.append([
                    image.repository or '<none>',
                    image.tag or '<none>',
                    image.id[:12],
                    time_ago(image.created),
                    human_size(image.size)
                ])
            t.add_rows(rows)
            out.write(t.draw() + "\n\n")
        return out.getvalue()


def containers_to_ascii_table(containers):
    """Just a method that formats the images to ascii table.
    Expects dictionary {host: [images]}
    and prints multiple tables
    """
    with closing(StringIO()) as out:
        for host, values in containers.iteritems():
            out.write("[" + str(host) + "] \n")
            t = TextTable(max_width=400)
            t.set_deco(TextTable.HEADER)
            t.set_cols_dtype(['t'] * 6)
            t.set_cols_align(["l"] * 6)
            t.set_cols_width([12, 25, 25, 15, 20, 15])
            rows = []
            rows.append(
                ['Id', 'Image', 'Command', 'Created', 'Status', 'Ports'])
            for container in values:
                rows.append([
                    container.id[:12],
                    container.image,
                    container.command[:20],
                    time_ago(container.created),
                    container.status,
                    container.ports
                ])
            t.add_rows(rows)
            out.write(t.draw() + "\n\n")
        return out.getvalue()

########NEW FILE########
__FILENAME__ = runner
"""
Copyright [2013] [Rackspace]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import inspect
import logging
from threading import Thread

from twisted.internet import reactor

from . import auto
from . import Shipper

functions = []


def command(fn):
    """Decorator that just register the function
    as the command for the runner
    """
    functions.append(fn)
    return fn


def run(*args):
    """Gets the functions directly via arguments, or indirectly
    via command decorator and builds command line utility
    executing the functions as command line parameters.
    """
    global functions
    functions = functions + list(args)

    parser = argparse.ArgumentParser(
        description=_info())

    auto.generate(parser, *functions)

    args = parser.parse_args()
    function = args.fn

    Shipper.startup()
    log = logging.getLogger(__name__)
    failed = []

    def call(*args, **kwargs):
        try:
            function(*args, **kwargs)
        except:
            log.exception("Exception calling shipper!")
            failed.append(True)
        else:
            failed.append(False)

    t = Thread(target=call, args=(args,))
    t.daemon = True
    t.start()

    def waiter(th):
        th.join()
        Shipper.shutdown()
        reactor.callFromThread(reactor.stop)

    w = Thread(target=waiter, args=(t,))
    w.daemon = True
    w.start()

    reactor.run()

    if failed[0]:
        log.error("Shipper call resulted in failure")
        exit(-1)
    else:
        log.error("Shipper executed successfully")


def _info():
    """Returns the module doc string"""
    frm = inspect.stack()[-1]
    mod = inspect.getmodule(frm[0])
    return mod.__doc__ or ""

########NEW FILE########
__FILENAME__ = shipper
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

"""Twisted based client with paralell execution in mind and fixes
quirks of the official docker-py client.
"""

import re
import logging
import logging.handlers
import socket
from copy import copy
from collections import namedtuple

from twisted.internet import reactor
from twisted.web.client import HTTPConnectionPool
from twisted.internet import threads
from twisted.internet import defer

from .utils import parse_volumes, parse_ports
from .container import Container, ContainerConfig
from .image import Image
from .host import parse_hosts
from .pretty import images_to_ascii_table, containers_to_ascii_table
from .client import Client
from .build import DockerFile


class Shipper(object):
    """Shipper is a class providing parallelized operations
    docker client on multiple hosts and various shortcuts and
    convenience methods on top of the raw docker client.
    """

    pool = None
    log = None

    @classmethod
    def startup(cls):
        """Initiates connection pool and logging.

        We can not use persisten connections here as docker server
        has some troubles with those
        """
        cls.pool = HTTPConnectionPool(reactor, persistent=False)
        cls._init_logging()

    @classmethod
    def shutdown(cls):
        """Shuts down connection pool"""
        threads.blockingCallFromThread(
            reactor, cls.pool.closeCachedConnections)

    def __init__(self, hosts=None, version="1.6", timeout=None,
                 client_builder=None):
        self.hosts = parse_hosts(hosts or ["localhost"])

        if client_builder is None:
            client_builder = Client
        self.c = client_builder(
            version, timeout, log=self.log, pool=self.pool)

        self.version = version
        self.timeout = timeout

    def build(self, path=None, fobj=None, tag=None,
              quiet=False, nocache=False, rm=False):
        """Run build of a container from buildfile
        that can be passed as local/remote path or file object(fobj)
        """
        dockerfile = DockerFile(path, fobj)

        def call():
            deferreds = []
            for host in self.hosts:
                deferreds.append(
                    self.c.build(
                        host, dockerfile, tag=tag, quiet=quiet,
                        nocache=nocache, rm=rm))
            return defer.gatherResults(deferreds, consumeErrors=True)

        responses = threads.blockingCallFromThread(reactor, call)
        return [Response(h, 200, r) for h, r in zip(self.hosts, responses)]

    def parallel(self, method, params):
        def call():
            if isinstance(params, dict):
                # we assume that it's all the same call to all default hosts
                # with the same arguments
                deferreds = [method(h, **copy(params)) for h in self.hosts]
            elif isinstance(params, list):
                # we assume that it's a list of tuples (host, kwargs)
                # (useful in case if you have parallel calls to
                # different endpoints)
                deferreds = []
                for host, kwargs in params:
                    deferreds.append(method(host, **copy(kwargs)))

            return defer.gatherResults(deferreds, consumeErrors=True)

        return threads.blockingCallFromThread(reactor, call)

    def images(self, **kwargs):
        pretty = kwargs.pop('pretty', False)
        responses = self.parallel(self.c.images, kwargs)

        images = _flatten(responses, self.hosts, Image)
        if pretty:
            return images_to_ascii_table(_grouped_by_host(images))
        else:
            return images

    def containers(self, **kwargs):
        pretty = kwargs.pop('pretty', False)
        running = kwargs.pop('running', True)
        image = kwargs.pop('image', None)
        command = kwargs.pop('command', None)
        responses = self.parallel(self.c.containers, kwargs)

        containers = _flatten(responses, self.hosts, Container)

        if running is not None:
            if running:
                f = lambda x: x.is_running
            else:
                f = lambda x: x.is_stopped
            containers = filter(f, containers)

        if image is not None:
            f = lambda x: re.match(image, x.image)
            containers = filter(f, containers)

        if command is not None:
            f = lambda x: re.match(command, x.command)
            containers = filter(f, containers)

        if pretty:
            return containers_to_ascii_table(_grouped_by_host(containers))
        else:
            return containers

    def create_container(self, config, hosts=None, name=None):
        hosts = hosts or self.hosts
        kwargs = [(host, {"config": config, "name": name}) for host in hosts]
        responses = self.parallel(self.c.create_container, kwargs)
        return _flatten(responses, hosts, Container)

    def start(self, *containers, **kwargs):
        self.log.debug("Starting {}".format(containers))
        _, port_binds = parse_ports(kwargs.get('ports', []))
        kwargs = [(c.host, {"container": c,
                            "binds": kwargs.get("binds"),
                            "port_binds": port_binds,
                            "links": kwargs.get("links", [])})
                  for c in containers]
        self.parallel(self.c.start, kwargs)

    def stop(self, *containers, **kwargs):
        self.log.debug("Stopping {}".format(containers))
        stop_args = [(c.host,
                      {"container": c,
                       "wait_seconds": kwargs.get('wait_seconds', 5)})
                     for c in containers]
        self.parallel(self.c.stop, stop_args)
        return containers

    def attach(self, *containers, **kwargs):
        self.log.debug("Attaching to {}".format(containers))
        calls = []
        for c in containers:
            kw = copy(kwargs)
            kw['container'] = c
            calls.append((c.host, kw))
        self.parallel(self.c.attach, calls)
        return containers

    def wait(self, *containers):
        """
        Blocks until all the container stop, and returns a list of
        tuples of the container and a JSON blob containing its status code.
        """
        calls = []
        hosts = []
        for c in containers:
            calls.append((c.host, {'container': c}))
            hosts.append(c.host)
        responses = self.parallel(self.c.wait, calls)
        return zip(containers, responses)

    def inspect(self, *containers):
        calls = []
        hosts = []
        for c in containers:
            calls.append((c.host, {'container': c}))
            hosts.append(c.host)
        responses = self.parallel(self.c.inspect, calls)
        return _flatten(responses, hosts, Container)

    def run(self, image, command, **kwargs):
        """Creates a container and runs it
        """
        hosts = copy(self.hosts)
        once = kwargs.pop('once', False)
        detailed = kwargs.pop('detailed', False)
        if once:
            containers = self.containers(
                image=image, command=command, running=True)
            for host, values in _grouped_by_host(containers).iteritems():
                if len(values):
                    hosts.remove(host)
                    self.log.debug(
                        "Container {} {} is already running on {}".format(
                            image, host, command))
        if not hosts:
            return []

        volumes, binds = parse_volumes(kwargs.pop('volumes', []))
        kwargs['volumes'] = volumes
        config = ContainerConfig(image, command, **kwargs)
        containers = self.create_container(
            config, hosts=hosts, name=kwargs.get('name'))

        self.start(*containers,
                   binds=binds,
                   ports=kwargs.get('ports', []),
                   links=kwargs.get('links', []))
        self.log.debug("Containers({}) {} {} started".format(
            containers, image, command))

        if detailed:
            return self.inspect(*containers)
        return containers

    @classmethod
    def _init_logging(cls, **kwargs):
        cls.log = logging.getLogger("shipper")
        cls.log.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(levelname)-5.5s PID:%(process)d [%(name)s] %(message)s")
        cls._add_console_output(cls.log, formatter)
        cls._add_syslog_output(cls.log, formatter)

    @classmethod
    def _add_console_output(cls, log, formatter):
        # create console handler and set level to debug
        h = logging.StreamHandler()
        h.setLevel(logging.DEBUG)

        # create formatter
        h.setFormatter(formatter)
        log.addHandler(h)

    @classmethod
    def _add_syslog_output(cls, log, formatter):
        try:
            h = logging.handlers.SysLogHandler(address='/dev/log')
            h.setLevel(logging.DEBUG)

            h.setFormatter(formatter)
            log.addHandler(h)
        except socket.error:
            # Skip setting up syslog if /dev/log doesn't exist
            pass


Response = namedtuple("Response", "host code content")


def _grouped_by_host(values):
    grouped = {}
    for v in values:
        grouped.setdefault(v.host, []).append(v)
    return grouped


def _flatten(values, hosts, cls):
    out = []
    for h, host_values in zip(hosts, values):
        if not isinstance(host_values, list):
            host_values = [host_values]
        for value in host_values:
            out.append(cls(h, value))
    return out

########NEW FILE########
__FILENAME__ = test_client
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

import json
import mock
import treq

from twisted.python.failure import Failure
from twisted.internet.defer import succeed
from twisted.trial.unittest import TestCase
from twisted.web.client import ResponseDone

from shipper.client import Client


class _Response(object):
    """
    A fake response (not a verified fake - does not contain every attribute
    and method of a true Response - missing headers, for instance) that can
    also fake delivering a body

    The status code accepted is an int, and the body either None or a
    json blob (which will be converted to a string).
    """
    def __init__(self, status_code=204, body=None):
        self.code = status_code
        self._body = json.dumps(body)

        self.length = len(self._body)

    def deliverBody(self, iproducer):
        # replicate the same brokeness in Twisted:  if the status code is 204,
        # dataReceived and connectionLost are never called
        iproducer.dataReceived(self._body)
        iproducer.connectionLost(Failure(ResponseDone()))


class ClientCommands(TestCase):
    """
    Tests commands (methods on Client)
    """
    def setUp(self):
        """
        Wraps treq so that actual calls are mostly made, but that certain
        results can be stubbed out
        """
        self.treq = mock.patch('shipper.client.treq', wraps=treq).start()
        self.addCleanup(mock.patch.stopall)

    def test_wait(self):
        """
        The correct parameters are passed to treq.post, and the JSON result is
        returned as a dict
        """
        self.treq.post.return_value = succeed(
            _Response(200, {'StatusCode': 0}))

        d = Client().wait(host=mock.Mock(url='http://localhost'),
                          container=mock.Mock(id='__id__'))

        self.treq.post.assert_called_once_with(
            url="http://localhost/v1.6/containers/__id__/wait",
            params={},
            pool=mock.ANY)

        self.assertEqual({'StatusCode': 0}, self.successResultOf(d))

########NEW FILE########
__FILENAME__ = test_container
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

from twisted.trial import unittest
from shipper.container import ContainerConfig


class ShipperContainerTestCase(unittest.TestCase):
    """
    Tests container wrappers
    """

    def test_container_config_defaults(self):
        """Makes sure defaults for container config function
        are sane.
        """
        config = ContainerConfig("shipper/base", "echo 'hi'")
        expected = {
            'AttachStderr': False,
            'AttachStdin': False,
            'AttachStdout': False,
            'Cmd': ['echo', 'hi'],
            'Dns': None,
            'Env': None,
            'Hostname': None,
            'Image': 'shipper/base',
            'Memory': 0,
            'OpenStdin': False,
            'StdinOnce': False,
            'ExposedPorts': {},
            'Tty': False,
            'User': None,
            'Volumes': None,
            'VolumesFrom': None
        }
        self.assertEqual(expected, config)

    def test_container_config(self):
        """Make sure all parameters are converted
        properly and to the right properties.
        """
        config = ContainerConfig(
            "shipper/base",
            "echo 'hi'",
            hostname="localhost",
            user="username",
            open_stdin=True,
            stderr=True,
            stdout=True,
            stdin=True,
            tty=True,
            mem_limit=1024,
            ports=["27017:27017"],
            environment=["a=b", "b=c"],
            dns=["8.8.8.8", "127.0.0.1"],
            volumes={"/home": {}},
            volumes_from="container")

        expected = {
            'AttachStderr': True,
            'AttachStdin': True,
            'AttachStdout': True,
            'Cmd': ['echo', 'hi'],
            'Dns': ['8.8.8.8', '127.0.0.1'],
            'Env': ['a=b', 'b=c'],
            'Hostname': 'localhost',
            'Image': 'shipper/base',
            'Memory': 1024,
            'OpenStdin': True,
            'StdinOnce': False,
            'ExposedPorts': {'27017/tcp': {}},
            'Tty': True,
            'User': 'username',
            'Volumes': {'/home': {}},
            'VolumesFrom': 'container'
        }
        self.assertEqual(expected, config)

########NEW FILE########
__FILENAME__ = test_host
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

from twisted.trial import unittest
from shipper.host import Host, parse_hosts


class ShipperHostTestCase(unittest.TestCase):
    """
    Tests for the various utils
    """

    def test_host_comparison(self):
        """Ensure that hosts can be compared"""
        H = Host

        self.assertEqual(H("http://localhost"), H("http://localhost"))
        self.assertEqual(
            H("https://localhost:1234"), H("https://localhost:1234"))
        self.assertEqual(
            hash(H("https://localhost")), hash(H("https://localhost")))
        self.assertNotEqual(
            H("https://google.com:1234"), H("http://google.com:1234"))

        self.assertEqual(
            "http://google.com:1234", H("http://google.com:1234").url)

    def test_host_mapping(self):
        """Ensure that hosts can be used in hashes
        """
        H = Host
        a, b = H("http://google.com"), H("http://yahoo.com")
        vals = {a: 1, b: 2}
        self.assertEqual(1, vals[a])
        self.assertEqual(2, vals[b])

    def test_parse_hosts_invalid(self):
        """Invalid hosts of all sorts should be handled corectly
        """
        self.assertEqual([], parse_hosts(None))
        self.assertEqual([], parse_hosts(""))

    def test_parse_hosts(self):
        """Parse hosts strings into structured objects"""
        H = Host
        ph = parse_hosts

        self.assertEqual(
            [H("http://google.com:1234")],
            ph(["google.com"], default_port=1234))

        self.assertEqual(
            [H("http://google.com:1389")],
            ph(["google.com:1389"]))

        self.assertEqual(
            [H("http://google.com:1871")],
            ph([("google.com", 1871)]))

        self.assertEqual(
            [H("https://google.com:123")],
            ph(["https://google.com"], default_port=123))

########NEW FILE########
__FILENAME__ = test_pretty
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

from twisted.trial import unittest


class ShipperPrettyTestCase(unittest.TestCase):
    """
    Tests pretty printing of images and containers
    """

    def test_pretty_print_images(self):
        pass

########NEW FILE########
__FILENAME__ = test_shipper
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

import mock

from twisted.internet.defer import maybeDeferred, succeed
from twisted.trial.unittest import TestCase

from shipper.client import Client
from shipper.container import Container
from shipper.shipper import Shipper


class ShipperCommands(TestCase):
    """
    Tests commands (methods on Shipper)
    """
    def setUp(self):
        """
        Wraps treq so that actual calls are mostly made, but that certain
        results can be stubbed out
        """
        self.client = mock.Mock(Client)
        self.shipper = Shipper(
            client_builder=lambda *args, **kwargs: self.client)

        # this just runs the call and returns the result of the deferred
        def _fake_blocking_call_from_thread(reactor, call, *args, **kwargs):
            d = maybeDeferred(call, *args, **kwargs)
            return self.successResultOf(d)

        self.blocking_call = mock.patch(
            'shipper.shipper.threads.blockingCallFromThread',
            side_effect=_fake_blocking_call_from_thread).start()
        self.addCleanup(mock.patch.stopall)

    def test_wait(self):
        """
        Client.wait is called for every for every container passed to
        Shipper.wait.  The result is a list tuples of container: results
        for all the containers.
        """
        self.client.wait.side_effect = (
            lambda *args, **kwargs: succeed('wait_success'))

        containers = [Container('localhost:1234', {'Id': '1'}),
                      Container('localhost:2345', {'Id': '2'})]
        result = self.shipper.wait(*containers)

        self.client.wait.assert_has_calls([
            mock.call('localhost:1234', container=containers[0]),
            mock.call('localhost:2345', container=containers[1])])

        self.assertEqual(
            [(container, 'wait_success') for container in containers],
            result)

########NEW FILE########
__FILENAME__ = test_utils
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

from twisted.trial import unittest
from datetime import datetime
from shipper import utils
from calendar import timegm
import mock


class ShipperUtilsTestCase(unittest.TestCase):
    """
    Tests for the various utils
    """

    def test_from_epoch(self):
        """
        Test conversion from unix epoch seconds to
        reasonable times
        """
        # invalid leads to none value?
        self.assertRaises(ValueError, utils.from_epoch, 'invalid')

        now = datetime(2013, 3, 4, 1, 2, 3, 0)
        epoch_now = timegm(now.timetuple())
        self.assertEqual(now, utils.from_epoch(epoch_now))

    def test_human_size(self):
        """
        Makes sure human_size converts properly
        """
        self.assertEquals("0 bytes", utils.human_size(0))
        self.assertEquals("1 byte", utils.human_size(1))
        self.assertEquals("5 bytes", utils.human_size(5))
        self.assertEquals("1023 bytes", utils.human_size(1023))
        self.assertEquals("1 KB", utils.human_size(1024))
        self.assertEquals("1.5 KB", utils.human_size(1024 * 1.5))
        self.assertEquals("1.7 MB", utils.human_size(1024 * 1024 * 1.7))
        self.assertEquals("5.2 GB", utils.human_size(1024 * 1024 * 1024 * 5.2))
        self.assertEquals(
            "1.2 TB", utils.human_size(1024 * 1024 * 1024 * 1024 * 1.2))

    @mock.patch('shipper.utils.datetime')
    def test_time_ago(self, m):
        """Testing sane formatting for times
        """
        m.utcnow = mock.Mock(return_value=datetime(2013, 3, 4, 1, 2, 3, 0))
        self.assertEqual(
            "59 days ago", utils.time_ago(datetime(2013, 1, 4, 1, 2, 3, 0)))

    def test_parse_volumes_invalid_params(self):
        self.assertEquals(
            ({}, []), utils.parse_volumes(None))

        self.assertEquals(
            ({}, []), utils.parse_volumes(""))

    def test_parse_volumes(self):
        """Parsing volumes parameter
        """
        volumes, binds = utils.parse_volumes(["/home/local:/home/container"])
        self.assertEquals({"/home/container": {}}, volumes)
        self.assertEquals(["/home/local:/home/container"], binds)

        volumes, binds = utils.parse_volumes(
            ["/home/local:/home/container", "/container"])
        self.assertEquals(
            {"/home/container", "/container"}, set(volumes.keys()))
        self.assertEquals(["/home/local:/home/container"], binds)

    def test_parse_ports(self):
        """Parsing port mappings
        """
        exposed, binds = utils.parse_ports(["80:80"])
        self.assertEquals(
            {'80/tcp': [{'HostIp': '', 'HostPort': '80'}]}, binds)
        self.assertEquals({'80/tcp': {}}, exposed)

        exposed, binds = utils.parse_ports(["8125:8125/udp"])
        self.assertEquals(
            {'8125/udp': [{'HostIp': '', 'HostPort': '8125'}]}, binds)
        self.assertEquals({'8125/udp': {}}, exposed)

########NEW FILE########
__FILENAME__ = utils
# coding: utf-8
# Licensed under the Apache License, Version 2.0 (the "License")
# See LICENSE for details

import time
import os.path
from datetime import datetime

import ago


def from_epoch(seconds):
    '''
    Converts epoch time (seconds since Jan 1, 1970) into a datetime object

    >>> from_epoch(1309856559)
    datetime.datetime(2011, 7, 5, 9, 2, 39)

    Returns None if 'seconds' value is not valid
    '''
    try:
        tm = time.gmtime(float(seconds))
        return datetime(
            tm.tm_year, tm.tm_mon, tm.tm_mday,
            tm.tm_hour, tm.tm_min, tm.tm_sec)
    except:
        raise ValueError(u"Invalid parameter: {}".format(seconds))


def human_size(num):
    """Converts bytes to human readable bytes reprsentation
    """
    if num == 0:
        return "0 bytes"
    if num == 1:
        return "1 byte"

    for x in ['bytes', 'KB', 'MB', 'GB']:
        if -1024.0 < num < 1024.0:
            if round(num) == num:
                return "%d %s" % (num, x)
            else:
                return "%3.1f %s" % (num, x)
        num /= 1024.0

    return "%3.1f %s" % (num, 'TB')


def time_ago(dt):
    """Returns human readable string saying how long
    ago the event happened, e.g. "1 hour ago"
    """
    diff = datetime.utcnow() - dt
    return ago.human(diff, precision=1)


def parse_volumes(vals):
    """Parses volumes into volumes to attach and binds from list
    of strings. Returns tuple with
    * {} - volumes to create on a container
    * [] - list of binds
    """
    volumes = {}
    binds = []
    for string in (vals or []):
        out = string.split(":", 1)
        if len(out) == 2:
            if string.startswith("~"):
                string = os.path.expanduser(string)
            binds.append(string)
            destination = out[1]
            volumes[destination] = {}
        else:
            volumes[string] = {}
    return volumes, binds


def parse_ports(vals):
    """
    Parses ports from format "hostPort:containerPort"
    into ExposedPorts and PortBindings tuples
    """
    exposed = {}
    bindings = {}

    for pair in vals:
        ports = pair.split(":")
        if len(ports) != 2:
            raise ValueError("Unspported format")

        host_port, container_port = ports
        if "/" in container_port:
            with_protocol = container_port.split("/")
            if len(with_protocol) != 2:
                raise ValueError("Unspported format")
            container_port, protocol = with_protocol
        else:
            protocol = "tcp"

        container_key = "{}/{}".format(container_port, protocol)
        exposed[container_key] = {}
        bindings.setdefault(container_key, []).append(
            {"HostIp": "", "HostPort": host_port})

    return (exposed, bindings)

########NEW FILE########
