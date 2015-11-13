__FILENAME__ = colors
from __future__ import unicode_literals
NAMES = [
    'grey',
    'red',
    'green',
    'yellow',
    'blue',
    'magenta',
    'cyan',
    'white'
]


def get_pairs():
    for i, name in enumerate(NAMES):
        yield(name, str(30 + i))
        yield('intense_' + name, str(30 + i) + ';1')


def ansi(code):
    return '\033[{0}m'.format(code)


def ansi_color(code, s):
    return '{0}{1}{2}'.format(ansi(code), s, ansi(0))


def make_color_fn(code):
    return lambda s: ansi_color(code, s)


for (name, code) in get_pairs():
    globals()[name] = make_color_fn(code)


def rainbow():
    cs = ['cyan', 'yellow', 'green', 'magenta', 'red', 'blue',
          'intense_cyan', 'intense_yellow', 'intense_green',
          'intense_magenta', 'intense_red', 'intense_blue']

    for c in cs:
        yield globals()[c]

########NEW FILE########
__FILENAME__ = command
from __future__ import unicode_literals
from __future__ import absolute_import
from ..packages.docker import Client
from requests.exceptions import ConnectionError
import errno
import logging
import os
import re
import yaml
from ..packages import six
import sys

from ..project import Project
from ..service import ConfigError
from .docopt_command import DocoptCommand
from .formatter import Formatter
from .utils import cached_property, docker_url, call_silently, is_mac, is_ubuntu
from . import errors

log = logging.getLogger(__name__)

class Command(DocoptCommand):
    base_dir = '.'

    def __init__(self):
        self.yaml_path = os.environ.get('FIG_FILE', None)
        self.explicit_project_name = None

    def dispatch(self, *args, **kwargs):
        try:
            super(Command, self).dispatch(*args, **kwargs)
        except ConnectionError:
            if call_silently(['which', 'docker']) != 0:
                if is_mac():
                    raise errors.DockerNotFoundMac()
                elif is_ubuntu():
                    raise errors.DockerNotFoundUbuntu()
                else:
                    raise errors.DockerNotFoundGeneric()
            elif call_silently(['which', 'docker-osx']) == 0:
                raise errors.ConnectionErrorDockerOSX()
            else:
                raise errors.ConnectionErrorGeneric(self.client.base_url)

    def perform_command(self, options, *args, **kwargs):
        if options['--file'] is not None:
            self.yaml_path = os.path.join(self.base_dir, options['--file'])
        if options['--project-name'] is not None:
            self.explicit_project_name = options['--project-name']
        return super(Command, self).perform_command(options, *args, **kwargs)

    @cached_property
    def client(self):
        return Client(docker_url())

    @cached_property
    def project(self):
        try:
            yaml_path = self.yaml_path
            if yaml_path is None:
                yaml_path = self.check_yaml_filename()
            config = yaml.load(open(yaml_path))
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise errors.FigFileNotFound(os.path.basename(e.filename))
            raise errors.UserError(six.text_type(e))

        try:
            return Project.from_config(self.project_name, config, self.client)
        except ConfigError as e:
            raise errors.UserError(six.text_type(e))

    @cached_property
    def project_name(self):
        project = os.path.basename(os.getcwd())
        if self.explicit_project_name is not None:
            project = self.explicit_project_name
        project = re.sub(r'[^a-zA-Z0-9]', '', project)
        if not project:
            project = 'default'
        return project

    @cached_property
    def formatter(self):
        return Formatter()

    def check_yaml_filename(self):
        if os.path.exists(os.path.join(self.base_dir, 'fig.yaml')):

            log.warning("Fig just read the file 'fig.yaml' on startup, rather than 'fig.yml'")
            log.warning("Please be aware that fig.yml the expected extension in most cases, and using .yaml can cause compatibility issues in future")

            return os.path.join(self.base_dir, 'fig.yaml')
        else:
            return os.path.join(self.base_dir, 'fig.yml')

########NEW FILE########
__FILENAME__ = docopt_command
from __future__ import unicode_literals
from __future__ import absolute_import
import sys

from inspect import getdoc
from docopt import docopt, DocoptExit


def docopt_full_help(docstring, *args, **kwargs):
    try:
        return docopt(docstring, *args, **kwargs)
    except DocoptExit:
        raise SystemExit(docstring)


class DocoptCommand(object):
    def docopt_options(self):
        return {'options_first': True}

    def sys_dispatch(self):
        self.dispatch(sys.argv[1:], None)

    def dispatch(self, argv, global_options):
        self.perform_command(*self.parse(argv, global_options))

    def perform_command(self, options, command, handler, command_options):
        handler(command_options)

    def parse(self, argv, global_options):
        options = docopt_full_help(getdoc(self), argv, **self.docopt_options())
        command = options['COMMAND']

        if command is None:
            raise SystemExit(getdoc(self))

        if not hasattr(self, command):
            raise NoSuchCommand(command, self)

        handler = getattr(self, command)
        docstring = getdoc(handler)

        if docstring is None:
            raise NoSuchCommand(command, self)

        command_options = docopt_full_help(docstring, options['ARGS'], options_first=True)
        return (options, command, handler, command_options)


class NoSuchCommand(Exception):
    def __init__(self, command, supercommand):
        super(NoSuchCommand, self).__init__("No such command: %s" % command)

        self.command = command
        self.supercommand = supercommand

########NEW FILE########
__FILENAME__ = errors
from __future__ import absolute_import
from textwrap import dedent


class UserError(Exception):
    def __init__(self, msg):
        self.msg = dedent(msg).strip()

    def __unicode__(self):
        return self.msg


class DockerNotFoundMac(UserError):
    def __init__(self):
        super(DockerNotFoundMac, self).__init__("""
        Couldn't connect to Docker daemon. You might need to install docker-osx:

        https://github.com/noplay/docker-osx
        """)


class DockerNotFoundUbuntu(UserError):
    def __init__(self):
        super(DockerNotFoundUbuntu, self).__init__("""
        Couldn't connect to Docker daemon. You might need to install Docker:

        http://docs.docker.io/en/latest/installation/ubuntulinux/
        """)


class DockerNotFoundGeneric(UserError):
    def __init__(self):
        super(DockerNotFoundGeneric, self).__init__("""
        Couldn't connect to Docker daemon. You might need to install Docker:

        http://docs.docker.io/en/latest/installation/
        """)


class ConnectionErrorDockerOSX(UserError):
    def __init__(self):
        super(ConnectionErrorDockerOSX, self).__init__("""
        Couldn't connect to Docker daemon - you might need to run `docker-osx shell`.
        """)


class ConnectionErrorGeneric(UserError):
    def __init__(self, url):
        super(ConnectionErrorGeneric, self).__init__("""
        Couldn't connect to Docker daemon at %s - is it running?

        If it's at a non-standard location, specify the URL with the DOCKER_HOST environment variable.
        """ % url)


class FigFileNotFound(UserError):
    def __init__(self, filename):
        super(FigFileNotFound, self).__init__("""
        Can't find %s. Are you in the right directory?
        """ % filename)

########NEW FILE########
__FILENAME__ = formatter
from __future__ import unicode_literals
from __future__ import absolute_import
import os
import texttable


class Formatter(object):
    def table(self, headers, rows):
        height, width = os.popen('stty size', 'r').read().split()

        table = texttable.Texttable(max_width=width)
        table.set_cols_dtype(['t' for h in headers])
        table.add_rows([headers] + rows)
        table.set_deco(table.HEADER)
        table.set_chars(['-', '|', '+', '-'])

        return table.draw()

########NEW FILE########
__FILENAME__ = log_printer
from __future__ import unicode_literals
from __future__ import absolute_import
import sys

from itertools import cycle

from .multiplexer import Multiplexer, STOP
from . import colors
from .utils import split_buffer


class LogPrinter(object):
    def __init__(self, containers, attach_params=None):
        self.containers = containers
        self.attach_params = attach_params or {}
        self.prefix_width = self._calculate_prefix_width(containers)
        self.generators = self._make_log_generators()

    def run(self):
        mux = Multiplexer(self.generators)
        for line in mux.loop():
            sys.stdout.write(line.encode(sys.__stdout__.encoding or 'utf-8'))

    def _calculate_prefix_width(self, containers):
        """
        Calculate the maximum width of container names so we can make the log
        prefixes line up like so:

        db_1  | Listening
        web_1 | Listening
        """
        prefix_width = 0
        for container in containers:
            prefix_width = max(prefix_width, len(container.name_without_project))
        return prefix_width

    def _make_log_generators(self):
        color_fns = cycle(colors.rainbow())
        generators = []

        for container in self.containers:
            color_fn = color_fns.next()
            generators.append(self._make_log_generator(container, color_fn))

        return generators

    def _make_log_generator(self, container, color_fn):
        prefix = color_fn(self._generate_prefix(container))
        # Attach to container before log printer starts running
        line_generator = split_buffer(self._attach(container), '\n')

        for line in line_generator:
            yield prefix + line.decode('utf-8')

        exit_code = container.wait()
        yield color_fn("%s exited with code %s\n" % (container.name, exit_code))
        yield STOP

    def _generate_prefix(self, container):
        """
        Generate the prefix for a log line without colour
        """
        name = container.name_without_project
        padding = ' ' * (self.prefix_width - len(name))
        return ''.join([name, padding, ' | '])

    def _attach(self, container):
        params = {
            'stdout': True,
            'stderr': True,
            'stream': True,
        }
        params.update(self.attach_params)
        params = dict((name, 1 if value else 0) for (name, value) in list(params.items()))
        return container.attach(**params)

########NEW FILE########
__FILENAME__ = main
from __future__ import print_function
from __future__ import unicode_literals
import logging
import sys
import re
import signal

from inspect import getdoc

from .. import __version__
from ..project import NoSuchService, ConfigurationError
from ..service import BuildError, CannotBeScaledError
from .command import Command
from .formatter import Formatter
from .log_printer import LogPrinter
from .utils import yesno

from ..packages.docker.errors import APIError
from .errors import UserError
from .docopt_command import NoSuchCommand
from .socketclient import SocketClient

log = logging.getLogger(__name__)


def main():
    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.INFO)
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)

    # Disable requests logging
    logging.getLogger("requests").propagate = False

    try:
        command = TopLevelCommand()
        command.sys_dispatch()
    except KeyboardInterrupt:
        log.error("\nAborting.")
        sys.exit(1)
    except (UserError, NoSuchService, ConfigurationError) as e:
        log.error(e.msg)
        sys.exit(1)
    except NoSuchCommand as e:
        log.error("No such command: %s", e.command)
        log.error("")
        log.error("\n".join(parse_doc_section("commands:", getdoc(e.supercommand))))
        sys.exit(1)
    except APIError as e:
        log.error(e.explanation)
        sys.exit(1)
    except BuildError as e:
        log.error("Service '%s' failed to build: %s" % (e.service.name, e.reason))
        sys.exit(1)


# stolen from docopt master
def parse_doc_section(name, source):
    pattern = re.compile('^([^\n]*' + name + '[^\n]*\n?(?:[ \t].*?(?:\n|$))*)',
                         re.IGNORECASE | re.MULTILINE)
    return [s.strip() for s in pattern.findall(source)]


class TopLevelCommand(Command):
    """Punctual, lightweight development environments using Docker.

    Usage:
      fig [options] [COMMAND] [ARGS...]
      fig -h|--help

    Options:
      --verbose                 Show more output
      --version                 Print version and exit
      -f, --file FILE           Specify an alternate fig file (default: fig.yml)
      -p, --project-name NAME   Specify an alternate project name (default: directory name)

    Commands:
      build     Build or rebuild services
      help      Get help on a command
      kill      Kill containers
      logs      View output from containers
      ps        List containers
      rm        Remove stopped containers
      run       Run a one-off command
      scale     Set number of containers for a service
      start     Start services
      stop      Stop services
      up        Create and start containers

    """
    def docopt_options(self):
        options = super(TopLevelCommand, self).docopt_options()
        options['version'] = "fig %s" % __version__
        return options

    def build(self, options):
        """
        Build or rebuild services.

        Services are built once and then tagged as `project_service`,
        e.g. `figtest_db`. If you change a service's `Dockerfile` or the
        contents of its build directory, you can run `fig build` to rebuild it.

        Usage: build [SERVICE...]
        """
        self.project.build(service_names=options['SERVICE'])

    def help(self, options):
        """
        Get help on a command.

        Usage: help COMMAND
        """
        command = options['COMMAND']
        if not hasattr(self, command):
            raise NoSuchCommand(command, self)
        raise SystemExit(getdoc(getattr(self, command)))

    def kill(self, options):
        """
        Force stop service containers.

        Usage: kill [SERVICE...]
        """
        self.project.kill(service_names=options['SERVICE'])

    def logs(self, options):
        """
        View output from containers.

        Usage: logs [SERVICE...]
        """
        containers = self.project.containers(service_names=options['SERVICE'], stopped=True)
        print("Attaching to", list_containers(containers))
        LogPrinter(containers, attach_params={'logs': True}).run()

    def ps(self, options):
        """
        List containers.

        Usage: ps [options] [SERVICE...]

        Options:
            -q    Only display IDs
        """
        containers = self.project.containers(service_names=options['SERVICE'], stopped=True) + self.project.containers(service_names=options['SERVICE'], one_off=True)

        if options['-q']:
            for container in containers:
                print(container.id)
        else:
            headers = [
                'Name',
                'Command',
                'State',
                'Ports',
            ]
            rows = []
            for container in containers:
                command = container.human_readable_command
                if len(command) > 30:
                    command = '%s ...' % command[:26]
                rows.append([
                    container.name,
                    command,
                    container.human_readable_state,
                    container.human_readable_ports,
                ])
            print(Formatter().table(headers, rows))

    def rm(self, options):
        """
        Remove stopped service containers.

        Usage: rm [options] [SERVICE...]

        Options:
            --force   Don't ask to confirm removal
            -v        Remove volumes associated with containers
        """
        all_containers = self.project.containers(service_names=options['SERVICE'], stopped=True)
        stopped_containers = [c for c in all_containers if not c.is_running]

        if len(stopped_containers) > 0:
            print("Going to remove", list_containers(stopped_containers))
            if options.get('--force') \
                    or yesno("Are you sure? [yN] ", default=False):
                self.project.remove_stopped(
                    service_names=options['SERVICE'],
                    v=options.get('-v', False)
                )
        else:
            print("No stopped containers")

    def run(self, options):
        """
        Run a one-off command on a service.

        For example:

            $ fig run web python manage.py shell

        Note that this will not start any services that the command's service
        links to. So if, for example, your one-off command talks to your
        database, you will need to run `fig up -d db` first.

        Usage: run [options] SERVICE COMMAND [ARGS...]

        Options:
            -d    Detached mode: Run container in the background, print new
                  container name
            -T    Disable pseudo-tty allocation. By default `fig run`
                  allocates a TTY.
            --rm  Remove container after run. Ignored in detached mode.
        """
        service = self.project.get_service(options['SERVICE'])

        tty = True
        if options['-d'] or options['-T'] or not sys.stdin.isatty():
            tty = False

        container_options = {
            'command': [options['COMMAND']] + options['ARGS'],
            'tty': tty,
            'stdin_open': not options['-d'],
        }
        container = service.create_container(one_off=True, **container_options)
        if options['-d']:
            service.start_container(container, ports=None, one_off=True)
            print(container.name)
        else:
            with self._attach_to_container(container.id, raw=tty) as c:
                service.start_container(container, ports=None, one_off=True)
                c.run()
            exit_code = container.wait()
            if options['--rm']:
                log.info("Removing %s..." % container.name)
                self.client.remove_container(container.id)
            sys.exit(exit_code)

    def scale(self, options):
        """
        Set number of containers to run for a service.

        Numbers are specified in the form `service=num` as arguments.
        For example:

            $ fig scale web=2 worker=3

        Usage: scale [SERVICE=NUM...]
        """
        for s in options['SERVICE=NUM']:
            if '=' not in s:
                raise UserError('Arguments to scale should be in the form service=num')
            service_name, num = s.split('=', 1)
            try:
                num = int(num)
            except ValueError:
                raise UserError('Number of containers for service "%s" is not a number' % service)
            try:
                self.project.get_service(service_name).scale(num)
            except CannotBeScaledError:
                raise UserError('Service "%s" cannot be scaled because it specifies a port on the host. If multiple containers for this service were created, the port would clash.\n\nRemove the ":" from the port definition in fig.yml so Docker can choose a random port for each container.' % service_name)


    def start(self, options):
        """
        Start existing containers.

        Usage: start [SERVICE...]
        """
        self.project.start(service_names=options['SERVICE'])

    def stop(self, options):
        """
        Stop running containers without removing them.

        They can be started again with `fig start`.

        Usage: stop [SERVICE...]
        """
        self.project.stop(service_names=options['SERVICE'])

    def up(self, options):
        """
        Build, (re)create, start and attach to containers for a service.

        By default, `fig up` will aggregate the output of each container, and
        when it exits, all containers will be stopped. If you run `fig up -d`,
        it'll start the containers in the background and leave them running.

        If there are existing containers for a service, `fig up` will stop
        and recreate them (preserving mounted volumes with volumes-from),
        so that changes in `fig.yml` are picked up.

        Usage: up [options] [SERVICE...]

        Options:
            -d    Detached mode: Run containers in the background, print new
                  container names
        """
        detached = options['-d']

        to_attach = self.project.up(service_names=options['SERVICE'])

        if not detached:
            print("Attaching to", list_containers(to_attach))
            log_printer = LogPrinter(to_attach, attach_params={"logs": True})

            try:
                log_printer.run()
            finally:
                def handler(signal, frame):
                    self.project.kill(service_names=options['SERVICE'])
                    sys.exit(0)
                signal.signal(signal.SIGINT, handler)

                print("Gracefully stopping... (press Ctrl+C again to force)")
                self.project.stop(service_names=options['SERVICE'])

    def _attach_to_container(self, container_id, raw=False):
        socket_in = self.client.attach_socket(container_id, params={'stdin': 1, 'stream': 1})
        socket_out = self.client.attach_socket(container_id, params={'stdout': 1, 'logs': 1, 'stream': 1})
        socket_err = self.client.attach_socket(container_id, params={'stderr': 1, 'logs': 1, 'stream': 1})

        return SocketClient(
            socket_in=socket_in,
            socket_out=socket_out,
            socket_err=socket_err,
            raw=raw,
        )

def list_containers(containers):
    return ", ".join(c.name for c in containers)

########NEW FILE########
__FILENAME__ = multiplexer
from __future__ import absolute_import
from threading import Thread

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # Python 3.x


# Yield STOP from an input generator to stop the
# top-level loop without processing any more input.
STOP = object()


class Multiplexer(object):
    def __init__(self, generators):
        self.generators = generators
        self.queue = Queue()

    def loop(self):
        self._init_readers()

        while True:
            try:
                item = self.queue.get(timeout=0.1)
                if item is STOP:
                    break
                else:
                    yield item
            except Empty:
                pass

    def _init_readers(self):
        for generator in self.generators:
            t = Thread(target=_enqueue_output, args=(generator, self.queue))
            t.daemon = True
            t.start()


def _enqueue_output(generator, queue):
    for item in generator:
        queue.put(item)

########NEW FILE########
__FILENAME__ = socketclient
from __future__ import print_function
# Adapted from https://github.com/benthor/remotty/blob/master/socketclient.py

import sys
import tty
import fcntl
import os
import termios
import threading
import errno

import logging
log = logging.getLogger(__name__)


class SocketClient:
    def __init__(self,
        socket_in=None,
        socket_out=None,
        socket_err=None,
        raw=True,
    ):
        self.socket_in = socket_in
        self.socket_out = socket_out
        self.socket_err = socket_err
        self.raw = raw

        self.stdin_fileno = sys.stdin.fileno()

    def __enter__(self):
        self.create()
        return self

    def __exit__(self, type, value, trace):
        self.destroy()

    def create(self):
        if os.isatty(sys.stdin.fileno()):
            self.settings = termios.tcgetattr(sys.stdin.fileno())
        else:
            self.settings = None

        if self.socket_in is not None:
            self.set_blocking(sys.stdin, False)
            self.set_blocking(sys.stdout, True)
            self.set_blocking(sys.stderr, True)

        if self.raw:
            tty.setraw(sys.stdin.fileno())

    def set_blocking(self, file, blocking):
        fd = file.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        flags = (flags & ~os.O_NONBLOCK) if blocking else (flags | os.O_NONBLOCK)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)

    def run(self):
        if self.socket_in is not None:
            self.start_background_thread(target=self.send, args=(self.socket_in, sys.stdin))

        recv_threads = []

        if self.socket_out is not None:
            recv_threads.append(self.start_background_thread(target=self.recv, args=(self.socket_out, sys.stdout)))

        if self.socket_err is not None:
            recv_threads.append(self.start_background_thread(target=self.recv, args=(self.socket_err, sys.stderr)))

        for t in recv_threads:
            t.join()

    def start_background_thread(self, **kwargs):
        thread = threading.Thread(**kwargs)
        thread.daemon = True
        thread.start()
        return thread

    def recv(self, socket, stream):
        try:
            while True:
                chunk = socket.recv(4096)

                if chunk:
                    stream.write(chunk.encode(stream.encoding or 'utf-8'))
                    stream.flush()
                else:
                    break
        except Exception as e:
            log.debug(e)

    def send(self, socket, stream):
        while True:
            chunk = stream.read(1)

            if chunk == '':
                socket.close()
                break
            else:
                try:
                    socket.send(chunk)
                except Exception as e:
                    if hasattr(e, 'errno') and e.errno == errno.EPIPE:
                        break
                    else:
                        raise e

    def destroy(self):
        if self.settings is not None:
            termios.tcsetattr(self.stdin_fileno, termios.TCSADRAIN, self.settings)

        sys.stdout.flush()

if __name__ == '__main__':
    import websocket

    if len(sys.argv) != 2:
        sys.stderr.write("Usage: python socketclient.py WEBSOCKET_URL\n")
        sys.exit(1)

    url = sys.argv[1]
    socket = websocket.create_connection(url)

    print("connected\r")

    with SocketClient(socket, interactive=True) as client:
        client.run()

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division
import datetime
import os
import subprocess
import platform


def cached_property(f):
    """
    returns a cached property that is calculated by function f
    http://code.activestate.com/recipes/576563-cached-property/
    """
    def get(self):
        try:
            return self._property_cache[f]
        except AttributeError:
            self._property_cache = {}
            x = self._property_cache[f] = f(self)
            return x
        except KeyError:
            x = self._property_cache[f] = f(self)
            return x

    return property(get)


def yesno(prompt, default=None):
    """
    Prompt the user for a yes or no.

    Can optionally specify a default value, which will only be
    used if they enter a blank line.

    Unrecognised input (anything other than "y", "n", "yes",
    "no" or "") will return None.
    """
    answer = raw_input(prompt).strip().lower()

    if answer == "y" or answer == "yes":
        return True
    elif answer == "n" or answer == "no":
        return False
    elif answer == "":
        return default
    else:
        return None


# http://stackoverflow.com/a/5164027
def prettydate(d):
    diff = datetime.datetime.utcnow() - d
    s = diff.seconds
    if diff.days > 7 or diff.days < 0:
        return d.strftime('%d %b %y')
    elif diff.days == 1:
        return '1 day ago'
    elif diff.days > 1:
        return '{0} days ago'.format(diff.days)
    elif s <= 1:
        return 'just now'
    elif s < 60:
        return '{0} seconds ago'.format(s)
    elif s < 120:
        return '1 minute ago'
    elif s < 3600:
        return '{0} minutes ago'.format(s/60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{0} hours ago'.format(s/3600)


def mkdir(path, permissions=0o700):
    if not os.path.exists(path):
        os.mkdir(path)

    os.chmod(path, permissions)

    return path


def docker_url():
    return os.environ.get('DOCKER_HOST')


def split_buffer(reader, separator):
    """
    Given a generator which yields strings and a separator string,
    joins all input, splits on the separator and yields each chunk.

    Unlike string.split(), each chunk includes the trailing
    separator, except for the last one if none was found on the end
    of the input.
    """
    buffered = str('')
    separator = str(separator)

    for data in reader:
        buffered += data
        while True:
            index = buffered.find(separator)
            if index == -1:
                break
            yield buffered[:index+1]
            buffered = buffered[index+1:]

    if len(buffered) > 0:
        yield buffered


def call_silently(*args, **kwargs):
    """
    Like subprocess.call(), but redirects stdout and stderr to /dev/null.
    """
    with open(os.devnull, 'w') as shutup:
        return subprocess.call(*args, stdout=shutup, stderr=shutup, **kwargs)


def is_mac():
    return platform.system() == 'Darwin'


def is_ubuntu():
    return platform.system() == 'Linux' and platform.linux_distribution()[0] == 'Ubuntu'

########NEW FILE########
__FILENAME__ = container
from __future__ import unicode_literals
from __future__ import absolute_import

class Container(object):
    """
    Represents a Docker container, constructed from the output of
    GET /containers/:id:/json.
    """
    def __init__(self, client, dictionary, has_been_inspected=False):
        self.client = client
        self.dictionary = dictionary
        self.has_been_inspected = has_been_inspected

    @classmethod
    def from_ps(cls, client, dictionary, **kwargs):
        """
        Construct a container object from the output of GET /containers/json.
        """
        new_dictionary = {
            'ID': dictionary['Id'],
            'Image': dictionary['Image'],
        }
        for name in dictionary.get('Names', []):
            if len(name.split('/')) == 2:
                new_dictionary['Name'] = name
        return cls(client, new_dictionary, **kwargs)

    @classmethod
    def from_id(cls, client, id):
        return cls(client, client.inspect_container(id))

    @classmethod
    def create(cls, client, **options):
        response = client.create_container(**options)
        return cls.from_id(client, response['Id'])

    @property
    def id(self):
        return self.dictionary['ID']

    @property
    def image(self):
        return self.dictionary['Image']

    @property
    def short_id(self):
        return self.id[:10]

    @property
    def name(self):
        return self.dictionary['Name'][1:]

    @property
    def name_without_project(self):
        return '_'.join(self.dictionary['Name'].split('_')[1:])

    @property
    def number(self):
        try:
            return int(self.name.split('_')[-1])
        except ValueError:
            return None

    @property
    def human_readable_ports(self):
        self.inspect_if_not_inspected()
        if not self.dictionary['NetworkSettings']['Ports']:
            return ''
        ports = []
        for private, public in list(self.dictionary['NetworkSettings']['Ports'].items()):
            if public:
                ports.append('%s->%s' % (public[0]['HostPort'], private))
            else:
                ports.append(private)
        return ', '.join(ports)

    @property
    def human_readable_state(self):
        self.inspect_if_not_inspected()
        if self.dictionary['State']['Running']:
            if self.dictionary['State'].get('Ghost'):
                return 'Ghost'
            else:
                return 'Up'
        else:
            return 'Exit %s' % self.dictionary['State']['ExitCode']

    @property
    def human_readable_command(self):
        self.inspect_if_not_inspected()
        if self.dictionary['Config']['Cmd']:
            return ' '.join(self.dictionary['Config']['Cmd'])
        else:
            return ''

    @property
    def environment(self):
        self.inspect_if_not_inspected()
        out = {}
        for var in self.dictionary.get('Config', {}).get('Env', []):
            k, v = var.split('=', 1)
            out[k] = v
        return out

    @property
    def is_running(self):
        self.inspect_if_not_inspected()
        return self.dictionary['State']['Running']

    def start(self, **options):
        return self.client.start(self.id, **options)

    def stop(self, **options):
        return self.client.stop(self.id, **options)

    def kill(self):
        return self.client.kill(self.id)

    def remove(self, **options):
        return self.client.remove_container(self.id, **options)

    def inspect_if_not_inspected(self):
        if not self.has_been_inspected:
            self.inspect()

    def wait(self):
        return self.client.wait(self.id)

    def logs(self, *args, **kwargs):
        return self.client.logs(self.id, *args, **kwargs)

    def inspect(self):
        self.dictionary = self.client.inspect_container(self.id)
        return self.dictionary

    def links(self):
        links = []
        for container in self.client.containers():
            for name in container['Names']:
                bits = name.split('/')
                if len(bits) > 2 and bits[1] == self.name:
                    links.append(bits[2])
        return links

    def attach(self, *args, **kwargs):
        return self.client.attach(self.id, *args, **kwargs)

    def attach_socket(self, **kwargs):
        return self.client.attach_socket(self.id, **kwargs)

    def __repr__(self):
        return '<Container: %s>' % self.name

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return self.id == other.id

########NEW FILE########
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

from fig.packages import six

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

import requests
import requests.exceptions
from fig.packages import six

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
                          cpu_shares=None, working_dir=None, domainname=None):
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

        if volumes_from and not isinstance(volumes_from, six.string_types):
            volumes_from = ','.join(volumes_from)

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
            'WorkingDir': working_dir
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
              nocache=False, rm=False, stream=False, timeout=None):
        remote = context = headers = None
        if path is None and fileobj is None:
            raise TypeError("Either path or fileobj needs to be provided.")

        if fileobj is not None:
            context = utils.mkbuildcontext(fileobj)
        elif path.startswith(('http://', 'https://', 'git://', 'github.com/')):
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
                         cpu_shares=None, working_dir=None, domainname=None):

        config = self._container_config(
            image, command, hostname, user, detach, stdin_open, tty, mem_limit,
            ports, environment, dns, volumes, volumes_from, network_disabled,
            entrypoint, cpu_shares, working_dir, domainname
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

    def logs(self, container, stdout=True, stderr=True, stream=False):
        return self.attach(
            container,
            stdout=stdout,
            stderr=stderr,
            stream=stream,
            logs=True
        )

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

    def remove_container(self, container, v=False, link=False):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'v': v, 'link': link}
        res = self._delete(self._url("/containers/" + container),
                           params=params)
        self._raise_for_status(res)

    def remove_image(self, image):
        res = self._delete(self._url("/images/" + image))
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

    def start(self, container, binds=None, volumes_from=None, port_bindings=None,
              lxc_conf=None, publish_all_ports=False, links=None, privileged=False):
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
            bind_pairs = [
                '%s:%s:%s' % (
                    h, d['bind'],
                    'ro' if 'ro' in d and d['ro'] else 'rw'
                ) for h, d in binds.items()
            ]

            start_config['Binds'] = bind_pairs

        if volumes_from and not isinstance(volumes_from, six.string_types):
            volumes_from = ','.join(volumes_from)

        start_config['VolumesFrom'] = volumes_from

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
from fig.packages import six

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
from fig.packages import six


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
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2013 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.3.0"


# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
            del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules[__name__ + ".moves"] = _MovedItems("moves")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    int2byte = chr
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})

########NEW FILE########
__FILENAME__ = project
from __future__ import unicode_literals
from __future__ import absolute_import
import logging
from .service import Service

log = logging.getLogger(__name__)


def sort_service_dicts(services):
    # Topological sort (Cormen/Tarjan algorithm).
    unmarked = services[:]
    temporary_marked = set()
    sorted_services = []

    get_service_names = lambda links: [link.split(':')[0] for link in links]

    def visit(n):
        if n['name'] in temporary_marked:
            if n['name'] in get_service_names(n.get('links', [])):
                raise DependencyError('A service can not link to itself: %s' % n['name'])
            else:
                raise DependencyError('Circular import between %s' % ' and '.join(temporary_marked))
        if n in unmarked:
            temporary_marked.add(n['name'])
            dependents = [m for m in services if n['name'] in get_service_names(m.get('links', []))]
            for m in dependents:
                visit(m)
            temporary_marked.remove(n['name'])
            unmarked.remove(n)
            sorted_services.insert(0, n)

    while unmarked:
        visit(unmarked[-1])

    return sorted_services

class Project(object):
    """
    A collection of services.
    """
    def __init__(self, name, services, client):
        self.name = name
        self.services = services
        self.client = client

    @classmethod
    def from_dicts(cls, name, service_dicts, client):
        """
        Construct a ServiceCollection from a list of dicts representing services.
        """
        project = cls(name, [], client)
        for service_dict in sort_service_dicts(service_dicts):
            # Reference links by object
            links = []
            if 'links' in service_dict:
                for link in service_dict.get('links', []):
                    if ':' in link:
                        service_name, link_name = link.split(':', 1)
                    else:
                        service_name, link_name = link, None
                    try:
                        links.append((project.get_service(service_name), link_name))
                    except NoSuchService:
                        raise ConfigurationError('Service "%s" has a link to service "%s" which does not exist.' % (service_dict['name'], service_name))

                del service_dict['links']
            project.services.append(Service(client=client, project=name, links=links, **service_dict))
        return project

    @classmethod
    def from_config(cls, name, config, client):
        dicts = []
        for service_name, service in list(config.items()):
            if not isinstance(service, dict):
                raise ConfigurationError('Service "%s" doesn\'t have any configuration options. All top level keys in your fig.yml must map to a dictionary of configuration options.')
            service['name'] = service_name
            dicts.append(service)
        return cls.from_dicts(name, dicts, client)

    def get_service(self, name):
        """
        Retrieve a service by name. Raises NoSuchService
        if the named service does not exist.
        """
        for service in self.services:
            if service.name == name:
                return service

        raise NoSuchService(name)

    def get_services(self, service_names=None):
        """
        Returns a list of this project's services filtered
        by the provided list of names, or all services if
        service_names is None or [].

        Preserves the original order of self.services.

        Raises NoSuchService if any of the named services
        do not exist.
        """
        if service_names is None or len(service_names) == 0:
            return self.services
        else:
            unsorted = [self.get_service(name) for name in service_names]
            return [s for s in self.services if s in unsorted]

    def start(self, service_names=None, **options):
        for service in self.get_services(service_names):
            service.start(**options)

    def stop(self, service_names=None, **options):
        for service in reversed(self.get_services(service_names)):
            service.stop(**options)

    def kill(self, service_names=None, **options):
        for service in reversed(self.get_services(service_names)):
            service.kill(**options)

    def build(self, service_names=None, **options):
        for service in self.get_services(service_names):
            if service.can_be_built():
                service.build(**options)
            else:
                log.info('%s uses an image, skipping' % service.name)

    def up(self, service_names=None):
        new_containers = []

        for service in self.get_services(service_names):
            for (_, new) in service.recreate_containers():
                new_containers.append(new)

        return new_containers

    def remove_stopped(self, service_names=None, **options):
        for service in self.get_services(service_names):
            service.remove_stopped(**options)

    def containers(self, service_names=None, *args, **kwargs):
        l = []
        for service in self.get_services(service_names):
            for container in service.containers(*args, **kwargs):
                l.append(container)
        return l


class NoSuchService(Exception):
    def __init__(self, name):
        self.name = name
        self.msg = "No such service: %s" % self.name

    def __str__(self):
        return self.msg


class ConfigurationError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

class DependencyError(ConfigurationError):
    pass


########NEW FILE########
__FILENAME__ = service
from __future__ import unicode_literals
from __future__ import absolute_import
from .packages.docker.errors import APIError
import logging
import re
import os
import sys
import json
from .container import Container

log = logging.getLogger(__name__)


DOCKER_CONFIG_KEYS = ['image', 'command', 'hostname', 'user', 'detach', 'stdin_open', 'tty', 'mem_limit', 'ports', 'environment', 'dns', 'volumes', 'volumes_from', 'entrypoint', 'privileged']
DOCKER_CONFIG_HINTS = {
    'link'      : 'links',
    'port'      : 'ports',
    'privilege' : 'privileged',
    'priviliged': 'privileged',
    'privilige' : 'privileged',
    'volume'    : 'volumes',
}


class BuildError(Exception):
    def __init__(self, service, reason):
        self.service = service
        self.reason = reason


class CannotBeScaledError(Exception):
    pass


class ConfigError(ValueError):
    pass


class Service(object):
    def __init__(self, name, client=None, project='default', links=[], **options):
        if not re.match('^[a-zA-Z0-9]+$', name):
            raise ConfigError('Invalid name: %s' % name)
        if not re.match('^[a-zA-Z0-9]+$', project):
            raise ConfigError('Invalid project: %s' % project)
        if 'image' in options and 'build' in options:
            raise ConfigError('Service %s has both an image and build path specified. A service can either be built to image or use an existing image, not both.' % name)

        supported_options = DOCKER_CONFIG_KEYS + ['build', 'expose']

        for k in options:
            if k not in supported_options:
                msg = "Unsupported config option for %s service: '%s'" % (name, k)
                if k in DOCKER_CONFIG_HINTS:
                    msg += " (did you mean '%s'?)" % DOCKER_CONFIG_HINTS[k]
                raise ConfigError(msg)

        self.name = name
        self.client = client
        self.project = project
        self.links = links or []
        self.options = options

    def containers(self, stopped=False, one_off=False):
        l = []
        for container in self.client.containers(all=stopped):
            name = get_container_name(container)
            if not name or not is_valid_name(name, one_off):
                continue
            project, name, number = parse_name(name)
            if project == self.project and name == self.name:
                l.append(Container.from_ps(self.client, container))
        return l

    def start(self, **options):
        for c in self.containers(stopped=True):
            if not c.is_running:
                log.info("Starting %s..." % c.name)
                self.start_container(c, **options)

    def stop(self, **options):
        for c in self.containers():
            log.info("Stopping %s..." % c.name)
            c.stop(**options)

    def kill(self, **options):
        for c in self.containers():
            log.info("Killing %s..." % c.name)
            c.kill(**options)

    def scale(self, desired_num):
        """
        Adjusts the number of containers to the specified number and ensures they are running.

        - creates containers until there are at least `desired_num`
        - stops containers until there are at most `desired_num` running
        - starts containers until there are at least `desired_num` running
        - removes all stopped containers
        """
        if not self.can_be_scaled():
            raise CannotBeScaledError()

        # Create enough containers
        containers = self.containers(stopped=True)
        while len(containers) < desired_num:
            containers.append(self.create_container())

        running_containers = []
        stopped_containers = []
        for c in containers:
            if c.is_running:
                running_containers.append(c)
            else:
                stopped_containers.append(c)
        running_containers.sort(key=lambda c: c.number)
        stopped_containers.sort(key=lambda c: c.number)

        # Stop containers
        while len(running_containers) > desired_num:
            c = running_containers.pop()
            log.info("Stopping %s..." % c.name)
            c.stop(timeout=1)
            stopped_containers.append(c)

        # Start containers
        while len(running_containers) < desired_num:
            c = stopped_containers.pop(0)
            log.info("Starting %s..." % c.name)
            self.start_container(c)
            running_containers.append(c)

        self.remove_stopped()


    def remove_stopped(self, **options):
        for c in self.containers(stopped=True):
            if not c.is_running:
                log.info("Removing %s..." % c.name)
                c.remove(**options)

    def create_container(self, one_off=False, **override_options):
        """
        Create a container for this service. If the image doesn't exist, attempt to pull
        it.
        """
        container_options = self._get_container_create_options(override_options, one_off=one_off)
        try:
            return Container.create(self.client, **container_options)
        except APIError as e:
            if e.response.status_code == 404 and e.explanation and 'No such image' in str(e.explanation):
                log.info('Pulling image %s...' % container_options['image'])
                output = self.client.pull(container_options['image'], stream=True)
                stream_output(output, sys.stdout)
                return Container.create(self.client, **container_options)
            raise

    def recreate_containers(self, **override_options):
        """
        If a container for this service doesn't exist, create and start one. If there are
        any, stop them, create+start new ones, and remove the old containers.
        """
        containers = self.containers(stopped=True)

        if len(containers) == 0:
            log.info("Creating %s..." % self.next_container_name())
            container = self.create_container(**override_options)
            self.start_container(container)
            return [(None, container)]
        else:
            tuples = []

            for c in containers:
                log.info("Recreating %s..." % c.name)
                tuples.append(self.recreate_container(c, **override_options))

            return tuples

    def recreate_container(self, container, **override_options):
        if container.is_running:
            container.stop(timeout=1)

        intermediate_container = Container.create(
            self.client,
            image=container.image,
            volumes_from=container.id,
            entrypoint=['echo'],
            command=[],
        )
        intermediate_container.start(volumes_from=container.id)
        intermediate_container.wait()
        container.remove()

        options = dict(override_options)
        options['volumes_from'] = intermediate_container.id
        new_container = self.create_container(**options)
        self.start_container(new_container, volumes_from=intermediate_container.id)

        intermediate_container.remove()

        return (intermediate_container, new_container)

    def start_container(self, container=None, volumes_from=None, **override_options):
        if container is None:
            container = self.create_container(**override_options)

        options = self.options.copy()
        options.update(override_options)

        port_bindings = {}

        if options.get('ports', None) is not None:
            for port in options['ports']:
                port = str(port)
                if ':' in port:
                    external_port, internal_port = port.split(':', 1)
                else:
                    external_port, internal_port = (None, port)

                port_bindings[internal_port] = external_port

        volume_bindings = {}

        if options.get('volumes', None) is not None:
            for volume in options['volumes']:
                if ':' in volume:
                    external_dir, internal_dir = volume.split(':')
                    volume_bindings[os.path.abspath(external_dir)] = {
                        'bind': internal_dir,
                        'ro': False,
                    }

        privileged = options.get('privileged', False)

        container.start(
            links=self._get_links(link_to_self=override_options.get('one_off', False)),
            port_bindings=port_bindings,
            binds=volume_bindings,
            volumes_from=volumes_from,
            privileged=privileged,
        )
        return container

    def next_container_name(self, one_off=False):
        bits = [self.project, self.name]
        if one_off:
            bits.append('run')
        return '_'.join(bits + [str(self.next_container_number(one_off=one_off))])

    def next_container_number(self, one_off=False):
        numbers = [parse_name(c.name)[2] for c in self.containers(stopped=True, one_off=one_off)]

        if len(numbers) == 0:
            return 1
        else:
            return max(numbers) + 1

    def _get_links(self, link_to_self):
        links = []
        for service, link_name in self.links:
            for container in service.containers():
                if link_name:
                    links.append((container.name, link_name))
                links.append((container.name, container.name))
                links.append((container.name, container.name_without_project))
        if link_to_self:
            for container in self.containers():
                links.append((container.name, container.name))
                links.append((container.name, container.name_without_project))
        return links

    def _get_container_create_options(self, override_options, one_off=False):
        container_options = dict((k, self.options[k]) for k in DOCKER_CONFIG_KEYS if k in self.options)
        container_options.update(override_options)

        container_options['name'] = self.next_container_name(one_off)

        if 'ports' in container_options or 'expose' in self.options:
            ports = []
            all_ports = container_options.get('ports', []) + self.options.get('expose', [])
            for port in all_ports:
                port = str(port)
                if ':' in port:
                    port = port.split(':')[-1]
                if '/' in port:
                    port = tuple(port.split('/'))
                ports.append(port)
            container_options['ports'] = ports

        if 'volumes' in container_options:
            container_options['volumes'] = dict((split_volume(v)[1], {}) for v in container_options['volumes'])

        if self.can_be_built():
            if len(self.client.images(name=self._build_tag_name())) == 0:
                self.build()
            container_options['image'] = self._build_tag_name()

        # Priviliged is only required for starting containers, not for creating them
        if 'privileged' in container_options:
            del container_options['privileged']

        return container_options

    def build(self):
        log.info('Building %s...' % self.name)

        build_output = self.client.build(
            self.options['build'],
            tag=self._build_tag_name(),
            stream=True,
            rm=True
        )

        try:
            all_events = stream_output(build_output, sys.stdout)
        except StreamOutputError, e:
            raise BuildError(self, unicode(e))

        image_id = None

        for event in all_events:
            if 'stream' in event:
                match = re.search(r'Successfully built ([0-9a-f]+)', event.get('stream', ''))
                if match:
                    image_id = match.group(1)

        if image_id is None:
            raise BuildError(self)

        return image_id

    def can_be_built(self):
        return 'build' in self.options

    def _build_tag_name(self):
        """
        The tag to give to images built for this service.
        """
        return '%s_%s' % (self.project, self.name)

    def can_be_scaled(self):
        for port in self.options.get('ports', []):
            if ':' in str(port):
                return False
        return True


class StreamOutputError(Exception):
    pass


def stream_output(output, stream):
    is_terminal = hasattr(stream, 'fileno') and os.isatty(stream.fileno())
    all_events = []
    lines = {}
    diff = 0

    for chunk in output:
        event = json.loads(chunk)
        all_events.append(event)

        if 'progress' in event or 'progressDetail' in event:
            image_id = event['id']

            if image_id in lines:
                diff = len(lines) - lines[image_id]
            else:
                lines[image_id] = len(lines)
                stream.write("\n")
                diff = 0

            if is_terminal:
                # move cursor up `diff` rows
                stream.write("%c[%dA" % (27, diff))

        print_output_event(event, stream, is_terminal)

        if 'id' in event and is_terminal:
            # move cursor back down
            stream.write("%c[%dB" % (27, diff))

        stream.flush()

    return all_events

def print_output_event(event, stream, is_terminal):
    if 'errorDetail' in event:
        raise StreamOutputError(event['errorDetail']['message'])

    terminator = ''

    if is_terminal and 'stream' not in event:
        # erase current line
        stream.write("%c[2K\r" % 27)
        terminator = "\r"
        pass
    elif 'progressDetail' in event:
        return

    if 'time' in event:
        stream.write("[%s] " % event['time'])

    if 'id' in event:
        stream.write("%s: " % event['id'])

    if 'from' in event:
        stream.write("(from %s) " % event['from'])

    status = event.get('status', '')

    if 'progress' in event:
        stream.write("%s %s%s" % (status, event['progress'], terminator))
    elif 'progressDetail' in event:
        detail = event['progressDetail']
        if 'current' in detail:
            percentage = float(detail['current']) / float(detail['total']) * 100
            stream.write('%s (%.1f%%)%s' % (status, percentage, terminator))
        else:
            stream.write('%s%s' % (status, terminator))
    elif 'stream' in event:
        stream.write("%s%s" % (event['stream'], terminator))
    else:
        stream.write("%s%s\n" % (status, terminator))


NAME_RE = re.compile(r'^([^_]+)_([^_]+)_(run_)?(\d+)$')


def is_valid_name(name, one_off=False):
    match = NAME_RE.match(name)
    if match is None:
        return False
    if one_off:
        return match.group(3) == 'run_'
    else:
        return match.group(3) is None


def parse_name(name, one_off=False):
    match = NAME_RE.match(name)
    (project, service_name, _, suffix) = match.groups()
    return (project, service_name, int(suffix))


def get_container_name(container):
    if not container.get('Name') and not container.get('Names'):
        return None
    # inspect
    if 'Name' in container:
        return container['Name']
    # ps
    for name in container['Names']:
        if len(name.split('/')) == 2:
            return name[1:]


def split_volume(v):
    """
    If v is of the format EXTERNAL:INTERNAL, returns (EXTERNAL, INTERNAL).
    If v is of the format INTERNAL, returns (None, INTERNAL).
    """
    if ':' in v:
        return v.split(':', 1)
    else:
        return (None, v)

########NEW FILE########
__FILENAME__ = cli_test
from __future__ import unicode_literals
from __future__ import absolute_import
from .testcases import DockerClientTestCase
from mock import patch
from fig.cli.main import TopLevelCommand
from fig.packages.six import StringIO

class CLITestCase(DockerClientTestCase):
    def setUp(self):
        super(CLITestCase, self).setUp()
        self.command = TopLevelCommand()
        self.command.base_dir = 'tests/fixtures/simple-figfile'

    def tearDown(self):
        self.command.project.kill()
        self.command.project.remove_stopped()

    @patch('sys.stdout', new_callable=StringIO)
    def test_ps(self, mock_stdout):
        self.command.project.get_service('simple').create_container()
        self.command.dispatch(['ps'], None)
        self.assertIn('fig_simple_1', mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_ps_default_figfile(self, mock_stdout):
        self.command.base_dir = 'tests/fixtures/multiple-figfiles'
        self.command.dispatch(['up', '-d'], None)
        self.command.dispatch(['ps'], None)

        output = mock_stdout.getvalue()
        self.assertIn('fig_simple_1', output)
        self.assertIn('fig_another_1', output)
        self.assertNotIn('fig_yetanother_1', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_ps_alternate_figfile(self, mock_stdout):
        self.command.base_dir = 'tests/fixtures/multiple-figfiles'
        self.command.dispatch(['-f', 'fig2.yml', 'up', '-d'], None)
        self.command.dispatch(['-f', 'fig2.yml', 'ps'], None)

        output = mock_stdout.getvalue()
        self.assertNotIn('fig_simple_1', output)
        self.assertNotIn('fig_another_1', output)
        self.assertIn('fig_yetanother_1', output)

    def test_rm(self):
        service = self.command.project.get_service('simple')
        service.create_container()
        service.kill()
        self.assertEqual(len(service.containers(stopped=True)), 1)
        self.command.dispatch(['rm', '--force'], None)
        self.assertEqual(len(service.containers(stopped=True)), 0)

    def test_scale(self):
        project = self.command.project

        self.command.scale({'SERVICE=NUM': ['simple=1']})
        self.assertEqual(len(project.get_service('simple').containers()), 1)

        self.command.scale({'SERVICE=NUM': ['simple=3', 'another=2']})
        self.assertEqual(len(project.get_service('simple').containers()), 3)
        self.assertEqual(len(project.get_service('another').containers()), 2)

        self.command.scale({'SERVICE=NUM': ['simple=1', 'another=1']})
        self.assertEqual(len(project.get_service('simple').containers()), 1)
        self.assertEqual(len(project.get_service('another').containers()), 1)

        self.command.scale({'SERVICE=NUM': ['simple=1', 'another=1']})
        self.assertEqual(len(project.get_service('simple').containers()), 1)
        self.assertEqual(len(project.get_service('another').containers()), 1)

        self.command.scale({'SERVICE=NUM': ['simple=0', 'another=0']})
        self.assertEqual(len(project.get_service('simple').containers()), 0)
        self.assertEqual(len(project.get_service('another').containers()), 0)

########NEW FILE########
__FILENAME__ = project_test
from __future__ import unicode_literals
from fig.project import Project, ConfigurationError
from .testcases import DockerClientTestCase


class ProjectTest(DockerClientTestCase):
    def test_start_stop_kill_remove(self):
        web = self.create_service('web')
        db = self.create_service('db')
        project = Project('figtest', [web, db], self.client)

        project.start()

        self.assertEqual(len(web.containers()), 0)
        self.assertEqual(len(db.containers()), 0)

        web_container_1 = web.create_container()
        web_container_2 = web.create_container()
        db_container = db.create_container()

        project.start(service_names=['web'])
        self.assertEqual(set(c.name for c in project.containers()), set([web_container_1.name, web_container_2.name]))

        project.start()
        self.assertEqual(set(c.name for c in project.containers()), set([web_container_1.name, web_container_2.name, db_container.name]))

        project.stop(service_names=['web'], timeout=1)
        self.assertEqual(set(c.name for c in project.containers()), set([db_container.name]))

        project.kill(service_names=['db'])
        self.assertEqual(len(project.containers()), 0)
        self.assertEqual(len(project.containers(stopped=True)), 3)

        project.remove_stopped(service_names=['web'])
        self.assertEqual(len(project.containers(stopped=True)), 1)

        project.remove_stopped()
        self.assertEqual(len(project.containers(stopped=True)), 0)

    def test_project_up(self):
        web = self.create_service('web')
        db = self.create_service('db', volumes=['/var/db'])
        project = Project('figtest', [web, db], self.client)
        project.start()
        self.assertEqual(len(project.containers()), 0)

        project.up(['db'])
        self.assertEqual(len(project.containers()), 1)
        old_db_id = project.containers()[0].id
        db_volume_path = project.containers()[0].inspect()['Volumes']['/var/db']

        project.up()
        self.assertEqual(len(project.containers()), 2)

        db_container = [c for c in project.containers() if 'db' in c.name][0]
        self.assertNotEqual(c.id, old_db_id)
        self.assertEqual(c.inspect()['Volumes']['/var/db'], db_volume_path)

        project.kill()
        project.remove_stopped()

    def test_unscale_after_restart(self):
        web = self.create_service('web')
        project = Project('figtest', [web], self.client)

        project.start()

        service = project.get_service('web')
        service.scale(1)
        self.assertEqual(len(service.containers()), 1)
        service.scale(3)
        self.assertEqual(len(service.containers()), 3)
        project.up()
        service = project.get_service('web')
        self.assertEqual(len(service.containers()), 3)
        service.scale(1)
        self.assertEqual(len(service.containers()), 1)
        project.up()
        service = project.get_service('web')
        self.assertEqual(len(service.containers()), 1)
        # does scale=0 ,makes any sense? after recreating at least 1 container is running
        service.scale(0)
        project.up()
        service = project.get_service('web')
        self.assertEqual(len(service.containers()), 1)
        project.kill()
        project.remove_stopped()

########NEW FILE########
__FILENAME__ = service_test
from __future__ import unicode_literals
from __future__ import absolute_import
from fig import Service
from fig.service import CannotBeScaledError
from fig.packages.docker.errors import APIError
from .testcases import DockerClientTestCase

class ServiceTest(DockerClientTestCase):
    def test_containers(self):
        foo = self.create_service('foo')
        bar = self.create_service('bar')

        foo.start_container()

        self.assertEqual(len(foo.containers()), 1)
        self.assertEqual(foo.containers()[0].name, 'figtest_foo_1')
        self.assertEqual(len(bar.containers()), 0)

        bar.start_container()
        bar.start_container()

        self.assertEqual(len(foo.containers()), 1)
        self.assertEqual(len(bar.containers()), 2)

        names = [c.name for c in bar.containers()]
        self.assertIn('figtest_bar_1', names)
        self.assertIn('figtest_bar_2', names)

    def test_containers_one_off(self):
        db = self.create_service('db')
        container = db.create_container(one_off=True)
        self.assertEqual(db.containers(stopped=True), [])
        self.assertEqual(db.containers(one_off=True, stopped=True), [container])

    def test_project_is_added_to_container_name(self):
        service = self.create_service('web')
        service.start_container()
        self.assertEqual(service.containers()[0].name, 'figtest_web_1')

    def test_start_stop(self):
        service = self.create_service('scalingtest')
        self.assertEqual(len(service.containers(stopped=True)), 0)

        service.create_container()
        self.assertEqual(len(service.containers()), 0)
        self.assertEqual(len(service.containers(stopped=True)), 1)

        service.start()
        self.assertEqual(len(service.containers()), 1)
        self.assertEqual(len(service.containers(stopped=True)), 1)

        service.stop(timeout=1)
        self.assertEqual(len(service.containers()), 0)
        self.assertEqual(len(service.containers(stopped=True)), 1)

        service.stop(timeout=1)
        self.assertEqual(len(service.containers()), 0)
        self.assertEqual(len(service.containers(stopped=True)), 1)

    def test_kill_remove(self):
        service = self.create_service('scalingtest')

        service.start_container()
        self.assertEqual(len(service.containers()), 1)

        service.remove_stopped()
        self.assertEqual(len(service.containers()), 1)

        service.kill()
        self.assertEqual(len(service.containers()), 0)
        self.assertEqual(len(service.containers(stopped=True)), 1)

        service.remove_stopped()
        self.assertEqual(len(service.containers(stopped=True)), 0)

    def test_create_container_with_one_off(self):
        db = self.create_service('db')
        container = db.create_container(one_off=True)
        self.assertEqual(container.name, 'figtest_db_run_1')

    def test_create_container_with_one_off_when_existing_container_is_running(self):
        db = self.create_service('db')
        db.start()
        container = db.create_container(one_off=True)
        self.assertEqual(container.name, 'figtest_db_run_1')

    def test_create_container_with_unspecified_volume(self):
        service = self.create_service('db', volumes=['/var/db'])
        container = service.create_container()
        service.start_container(container)
        self.assertIn('/var/db', container.inspect()['Volumes'])

    def test_create_container_with_specified_volume(self):
        service = self.create_service('db', volumes=['/tmp:/host-tmp'])
        container = service.create_container()
        service.start_container(container)
        self.assertIn('/host-tmp', container.inspect()['Volumes'])

    def test_recreate_containers(self):
        service = self.create_service(
            'db',
            environment={'FOO': '1'},
            volumes=['/var/db'],
            entrypoint=['ps'],
            command=['ax']
        )
        old_container = service.create_container()
        self.assertEqual(old_container.dictionary['Config']['Entrypoint'], ['ps'])
        self.assertEqual(old_container.dictionary['Config']['Cmd'], ['ax'])
        self.assertIn('FOO=1', old_container.dictionary['Config']['Env'])
        self.assertEqual(old_container.name, 'figtest_db_1')
        service.start_container(old_container)
        volume_path = old_container.inspect()['Volumes']['/var/db']

        num_containers_before = len(self.client.containers(all=True))

        service.options['environment']['FOO'] = '2'
        tuples = service.recreate_containers()
        self.assertEqual(len(tuples), 1)

        intermediate_container = tuples[0][0]
        new_container = tuples[0][1]
        self.assertEqual(intermediate_container.dictionary['Config']['Entrypoint'], ['echo'])

        self.assertEqual(new_container.dictionary['Config']['Entrypoint'], ['ps'])
        self.assertEqual(new_container.dictionary['Config']['Cmd'], ['ax'])
        self.assertIn('FOO=2', new_container.dictionary['Config']['Env'])
        self.assertEqual(new_container.name, 'figtest_db_1')
        self.assertEqual(new_container.inspect()['Volumes']['/var/db'], volume_path)

        self.assertEqual(len(self.client.containers(all=True)), num_containers_before)
        self.assertNotEqual(old_container.id, new_container.id)
        self.assertRaises(APIError, lambda: self.client.inspect_container(intermediate_container.id))

    def test_start_container_passes_through_options(self):
        db = self.create_service('db')
        db.start_container(environment={'FOO': 'BAR'})
        self.assertEqual(db.containers()[0].environment['FOO'], 'BAR')

    def test_start_container_inherits_options_from_constructor(self):
        db = self.create_service('db', environment={'FOO': 'BAR'})
        db.start_container()
        self.assertEqual(db.containers()[0].environment['FOO'], 'BAR')

    def test_start_container_creates_links(self):
        db = self.create_service('db')
        web = self.create_service('web', links=[(db, None)])
        db.start_container()
        web.start_container()
        self.assertIn('figtest_db_1', web.containers()[0].links())
        self.assertIn('db_1', web.containers()[0].links())

    def test_start_container_creates_links_with_names(self):
        db = self.create_service('db')
        web = self.create_service('web', links=[(db, 'custom_link_name')])
        db.start_container()
        web.start_container()
        self.assertIn('custom_link_name', web.containers()[0].links())

    def test_start_normal_container_does_not_create_links_to_its_own_service(self):
        db = self.create_service('db')
        c1 = db.start_container()
        c2 = db.start_container()
        self.assertNotIn(c1.name, c2.links())

    def test_start_one_off_container_creates_links_to_its_own_service(self):
        db = self.create_service('db')
        c1 = db.start_container()
        c2 = db.start_container(one_off=True)
        self.assertIn(c1.name, c2.links())

    def test_start_container_builds_images(self):
        service = Service(
            name='test',
            client=self.client,
            build='tests/fixtures/simple-dockerfile',
            project='figtest',
        )
        container = service.start_container()
        container.wait()
        self.assertIn('success', container.logs())
        self.assertEqual(len(self.client.images(name='figtest_test')), 1)

    def test_start_container_uses_tagged_image_if_it_exists(self):
        self.client.build('tests/fixtures/simple-dockerfile', tag='figtest_test')
        service = Service(
            name='test',
            client=self.client,
            build='this/does/not/exist/and/will/throw/error',
            project='figtest',
        )
        container = service.start_container()
        container.wait()
        self.assertIn('success', container.logs())

    def test_start_container_creates_ports(self):
        service = self.create_service('web', ports=[8000])
        container = service.start_container().inspect()
        self.assertEqual(list(container['NetworkSettings']['Ports'].keys()), ['8000/tcp'])
        self.assertNotEqual(container['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort'], '8000')

    def test_start_container_stays_unpriviliged(self):
        service = self.create_service('web')
        container = service.start_container().inspect()
        self.assertEqual(container['HostConfig']['Privileged'], False)

    def test_start_container_becomes_priviliged(self):
        service = self.create_service('web', privileged = True)
        container = service.start_container().inspect()
        self.assertEqual(container['HostConfig']['Privileged'], True)

    def test_expose_does_not_publish_ports(self):
        service = self.create_service('web', expose=[8000])
        container = service.start_container().inspect()
        self.assertEqual(container['NetworkSettings']['Ports'], {'8000/tcp': None})

    def test_start_container_creates_port_with_explicit_protocol(self):
        service = self.create_service('web', ports=['8000/udp'])
        container = service.start_container().inspect()
        self.assertEqual(list(container['NetworkSettings']['Ports'].keys()), ['8000/udp'])

    def test_start_container_creates_fixed_external_ports(self):
        service = self.create_service('web', ports=['8000:8000'])
        container = service.start_container().inspect()
        self.assertIn('8000/tcp', container['NetworkSettings']['Ports'])
        self.assertEqual(container['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort'], '8000')

    def test_start_container_creates_fixed_external_ports_when_it_is_different_to_internal_port(self):
        service = self.create_service('web', ports=['8001:8000'])
        container = service.start_container().inspect()
        self.assertIn('8000/tcp', container['NetworkSettings']['Ports'])
        self.assertEqual(container['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort'], '8001')

    def test_scale(self):
        service = self.create_service('web')
        service.scale(1)
        self.assertEqual(len(service.containers()), 1)
        service.scale(3)
        self.assertEqual(len(service.containers()), 3)
        service.scale(1)
        self.assertEqual(len(service.containers()), 1)
        service.scale(0)
        self.assertEqual(len(service.containers()), 0)

    def test_scale_on_service_that_cannot_be_scaled(self):
        service = self.create_service('web', ports=['8000:8000'])
        self.assertRaises(CannotBeScaledError, lambda: service.scale(1))

    def test_scale_sets_ports(self):
        service = self.create_service('web', ports=['8000'])
        service.scale(2)
        containers = service.containers()
        self.assertEqual(len(containers), 2)
        for container in containers:
            self.assertEqual(list(container.inspect()['HostConfig']['PortBindings'].keys()), ['8000/tcp'])

########NEW FILE########
__FILENAME__ = testcases
from __future__ import unicode_literals
from __future__ import absolute_import
from fig.packages.docker import Client
from fig.service import Service
from fig.cli.utils import docker_url
from .. import unittest


class DockerClientTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = Client(docker_url())
        cls.client.pull('ubuntu', tag='latest')

    def setUp(self):
        for c in self.client.containers(all=True):
            if c['Names'] and 'figtest' in c['Names'][0]:
                self.client.kill(c['Id'])
                self.client.remove_container(c['Id'])
        for i in self.client.images():
            if isinstance(i.get('Tag'), basestring) and 'figtest' in i['Tag']:
                self.client.remove_image(i)

    def create_service(self, name, **kwargs):
        if 'command' not in kwargs:
            kwargs['command'] = ["/bin/sleep", "300"]
        return Service(
            project='figtest',
            name=name,
            client=self.client,
            image="ubuntu",
            **kwargs
        )




########NEW FILE########
__FILENAME__ = cli_test
from __future__ import unicode_literals
from __future__ import absolute_import
from .. import unittest
from fig.cli.main import TopLevelCommand
from fig.packages.six import StringIO

class CLITestCase(unittest.TestCase):
    def test_yaml_filename_check(self):
        command = TopLevelCommand()
        command.base_dir = 'tests/fixtures/longer-filename-figfile'
        self.assertTrue(command.project.get_service('definedinyamlnotyml'))

    def test_help(self):
        command = TopLevelCommand()
        with self.assertRaises(SystemExit):
            command.dispatch(['-h'], None)

########NEW FILE########
__FILENAME__ = container_test
from __future__ import unicode_literals
from .. import unittest
from fig.container import Container

class ContainerTest(unittest.TestCase):
    def test_from_ps(self):
        container = Container.from_ps(None, {
            "Id":"abc",
            "Image":"ubuntu:12.04",
            "Command":"sleep 300",
            "Created":1387384730,
            "Status":"Up 8 seconds",
            "Ports":None,
            "SizeRw":0,
            "SizeRootFs":0,
            "Names":["/figtest_db_1"]
        }, has_been_inspected=True)
        self.assertEqual(container.dictionary, {
            "ID": "abc",
            "Image":"ubuntu:12.04",
            "Name": "/figtest_db_1",
        })

    def test_environment(self):
        container = Container(None, {
            'ID': 'abc',
            'Config': {
                'Env': [
                    'FOO=BAR',
                    'BAZ=DOGE',
                ]
            }
        }, has_been_inspected=True)
        self.assertEqual(container.environment, {
            'FOO': 'BAR',
            'BAZ': 'DOGE',
        })

    def test_number(self):
        container = Container.from_ps(None, {
            "Id":"abc",
            "Image":"ubuntu:12.04",
            "Command":"sleep 300",
            "Created":1387384730,
            "Status":"Up 8 seconds",
            "Ports":None,
            "SizeRw":0,
            "SizeRootFs":0,
            "Names":["/figtest_db_1"]
        }, has_been_inspected=True)
        self.assertEqual(container.number, 1)

    def test_name(self):
        container = Container.from_ps(None, {
            "Id":"abc",
            "Image":"ubuntu:12.04",
            "Command":"sleep 300",
            "Names":["/figtest_db_1"]
        }, has_been_inspected=True)
        self.assertEqual(container.name, "figtest_db_1")

    def test_name_without_project(self):
        container = Container.from_ps(None, {
            "Id":"abc",
            "Image":"ubuntu:12.04",
            "Command":"sleep 300",
            "Names":["/figtest_db_1"]
        }, has_been_inspected=True)
        self.assertEqual(container.name_without_project, "db_1")

########NEW FILE########
__FILENAME__ = project_test
from __future__ import unicode_literals
from .. import unittest
from fig.service import Service
from fig.project import Project, ConfigurationError

class ProjectTest(unittest.TestCase):
    def test_from_dict(self):
        project = Project.from_dicts('figtest', [
            {
                'name': 'web',
                'image': 'ubuntu'
            },
            {
                'name': 'db',
                'image': 'ubuntu'
            }
        ], None)
        self.assertEqual(len(project.services), 2)
        self.assertEqual(project.get_service('web').name, 'web')
        self.assertEqual(project.get_service('web').options['image'], 'ubuntu')
        self.assertEqual(project.get_service('db').name, 'db')
        self.assertEqual(project.get_service('db').options['image'], 'ubuntu')

    def test_from_dict_sorts_in_dependency_order(self):
        project = Project.from_dicts('figtest', [
            {
                'name': 'web',
                'image': 'ubuntu',
                'links': ['db'],
            },
            {
                'name': 'db',
                'image': 'ubuntu'
            }
        ], None)

        self.assertEqual(project.services[0].name, 'db')
        self.assertEqual(project.services[1].name, 'web')

    def test_from_config(self):
        project = Project.from_config('figtest', {
            'web': {
                'image': 'ubuntu',
            },
            'db': {
                'image': 'ubuntu',
            },
        }, None)
        self.assertEqual(len(project.services), 2)
        self.assertEqual(project.get_service('web').name, 'web')
        self.assertEqual(project.get_service('web').options['image'], 'ubuntu')
        self.assertEqual(project.get_service('db').name, 'db')
        self.assertEqual(project.get_service('db').options['image'], 'ubuntu')

    def test_from_config_throws_error_when_not_dict(self):
        with self.assertRaises(ConfigurationError):
            project = Project.from_config('figtest', {
                'web': 'ubuntu',
            }, None)

    def test_get_service(self):
        web = Service(
            project='figtest',
            name='web',
            client=None,
            image="ubuntu",
        )
        project = Project('test', [web], None)
        self.assertEqual(project.get_service('web'), web)

########NEW FILE########
__FILENAME__ = service_test
from __future__ import unicode_literals
from __future__ import absolute_import
from .. import unittest
from fig import Service
from fig.service import ConfigError

class ServiceTest(unittest.TestCase):
    def test_name_validations(self):
        self.assertRaises(ConfigError, lambda: Service(name=''))

        self.assertRaises(ConfigError, lambda: Service(name=' '))
        self.assertRaises(ConfigError, lambda: Service(name='/'))
        self.assertRaises(ConfigError, lambda: Service(name='!'))
        self.assertRaises(ConfigError, lambda: Service(name='\xe2'))
        self.assertRaises(ConfigError, lambda: Service(name='_'))
        self.assertRaises(ConfigError, lambda: Service(name='____'))
        self.assertRaises(ConfigError, lambda: Service(name='foo_bar'))
        self.assertRaises(ConfigError, lambda: Service(name='__foo_bar__'))

        Service('a')
        Service('foo')

    def test_project_validation(self):
        self.assertRaises(ConfigError, lambda: Service(name='foo', project='_'))
        Service(name='foo', project='bar')

    def test_config_validation(self):
        self.assertRaises(ConfigError, lambda: Service(name='foo', port=['8000']))
        Service(name='foo', ports=['8000'])

########NEW FILE########
__FILENAME__ = sort_service_test
from fig.project import sort_service_dicts, DependencyError
from .. import unittest


class SortServiceTest(unittest.TestCase):
    def test_sort_service_dicts_1(self):
        services = [
            {
                'links': ['redis'],
                'name': 'web'
            },
            {
                'name': 'grunt'
            },
            {
                'name': 'redis'
            }
        ]

        sorted_services = sort_service_dicts(services)
        self.assertEqual(len(sorted_services), 3)
        self.assertEqual(sorted_services[0]['name'], 'grunt')
        self.assertEqual(sorted_services[1]['name'], 'redis')
        self.assertEqual(sorted_services[2]['name'], 'web')

    def test_sort_service_dicts_2(self):
        services = [
            {
                'links': ['redis', 'postgres'],
                'name': 'web'
            },
            {
                'name': 'postgres',
                'links': ['redis']
            },
            {
                'name': 'redis'
            }
        ]

        sorted_services = sort_service_dicts(services)
        self.assertEqual(len(sorted_services), 3)
        self.assertEqual(sorted_services[0]['name'], 'redis')
        self.assertEqual(sorted_services[1]['name'], 'postgres')
        self.assertEqual(sorted_services[2]['name'], 'web')

    def test_sort_service_dicts_3(self):
        services = [
            {
                'name': 'child'
            },
            {
                'name': 'parent',
                'links': ['child']
            },
            {
                'links': ['parent'],
                'name': 'grandparent'
            },
        ]

        sorted_services = sort_service_dicts(services)
        self.assertEqual(len(sorted_services), 3)
        self.assertEqual(sorted_services[0]['name'], 'child')
        self.assertEqual(sorted_services[1]['name'], 'parent')
        self.assertEqual(sorted_services[2]['name'], 'grandparent')

    def test_sort_service_dicts_circular_imports(self):
        services = [
            {
                'links': ['redis'],
                'name': 'web'
            },
            {
                'name': 'redis',
                'links': ['web']
            },
        ]

        try:
            sort_service_dicts(services)
        except DependencyError as e:
            self.assertIn('redis', e.msg)
            self.assertIn('web', e.msg)
        else:
            self.fail('Should have thrown an DependencyError')

    def test_sort_service_dicts_circular_imports_2(self):
        services = [
            {
                'links': ['postgres', 'redis'],
                'name': 'web'
            },
            {
                'name': 'redis',
                'links': ['web']
            },
            {
                'name': 'postgres'
            }
        ]

        try:
            sort_service_dicts(services)
        except DependencyError as e:
            self.assertIn('redis', e.msg)
            self.assertIn('web', e.msg)
        else:
            self.fail('Should have thrown an DependencyError')

    def test_sort_service_dicts_circular_imports_3(self):
        services = [
            {
                'links': ['b'],
                'name': 'a'
            },
            {
                'name': 'b',
                'links': ['c']
            },
            {
                'name': 'c',
                'links': ['a']
            }
        ]

        try:
            sort_service_dicts(services)
        except DependencyError as e:
            self.assertIn('a', e.msg)
            self.assertIn('b', e.msg)
        else:
            self.fail('Should have thrown an DependencyError')

    def test_sort_service_dicts_self_imports(self):
        services = [
            {
                'links': ['web'],
                'name': 'web'
            },
        ]

        try:
            sort_service_dicts(services)
        except DependencyError as e:
            self.assertIn('web', e.msg)
        else:
            self.fail('Should have thrown an DependencyError')

########NEW FILE########
__FILENAME__ = split_buffer_test
from __future__ import unicode_literals
from __future__ import absolute_import
from fig.cli.utils import split_buffer
from .. import unittest

class SplitBufferTest(unittest.TestCase):
    def test_single_line_chunks(self):
        def reader():
            yield "abc\n"
            yield "def\n"
            yield "ghi\n"

        self.assertEqual(list(split_buffer(reader(), '\n')), ["abc\n", "def\n", "ghi\n"])

    def test_no_end_separator(self):
        def reader():
            yield "abc\n"
            yield "def\n"
            yield "ghi"

        self.assertEqual(list(split_buffer(reader(), '\n')), ["abc\n", "def\n", "ghi"])

    def test_multiple_line_chunk(self):
        def reader():
            yield "abc\ndef\nghi"

        self.assertEqual(list(split_buffer(reader(), '\n')), ["abc\n", "def\n", "ghi"])

    def test_chunked_line(self):
        def reader():
            yield "a"
            yield "b"
            yield "c"
            yield "\n"
            yield "d"

        self.assertEqual(list(split_buffer(reader(), '\n')), ["abc\n", "d"])

########NEW FILE########
