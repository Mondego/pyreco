__FILENAME__ = deis
#!/usr/bin/env python
"""
The Deis command-line client issues API calls to a Deis controller.

Usage: deis <command> [<args>...]

Auth commands::

  register      register a new user with a controller
  login         login to a controller
  logout        logout from the current controller

Subcommands, use ``deis help [subcommand]`` to learn more::

  apps          manage applications used to provide services
  clusters      manage clusters used to host applications
  ps            manage processes inside an app container
  config        manage environment variables that define app config
  domains       manage and assign domain names to your applications
  builds        manage builds created using `git push`
  releases      manage releases of an application

  keys          manage ssh keys used for `git push` deployments
  perms         manage permissions for shared apps and clusters

Developer shortcut commands::

  create        create a new application
  scale         scale processes by type (web=2, worker=1)
  info          view information about the current app
  open          open a URL to the app in a browser
  logs          view aggregated log info for the app
  run           run a command in an ephemeral app container
  destroy       destroy an application

Use ``git push deis master`` to deploy to an application.

"""

from __future__ import print_function
from collections import namedtuple
from collections import OrderedDict
from cookielib import MozillaCookieJar
from datetime import datetime
from getpass import getpass
from itertools import cycle
from threading import Event
from threading import Thread
import base64
import glob
import json
import locale
import os.path
import re
import subprocess
import sys
import time
import urlparse
import webbrowser

from dateutil import parser
from dateutil import relativedelta
from dateutil import tz
from docopt import docopt
from docopt import DocoptExit
import requests
import yaml

__version__ = '0.9.0'


locale.setlocale(locale.LC_ALL, '')


class Session(requests.Session):
    """
    Session for making API requests and interacting with the filesystem
    """

    def __init__(self):
        super(Session, self).__init__()
        self.trust_env = False
        cookie_file = os.path.expanduser('~/.deis/cookies.txt')
        cookie_dir = os.path.dirname(cookie_file)
        self.cookies = MozillaCookieJar(cookie_file)
        # Create the $HOME/.deis dir if it doesn't exist
        if not os.path.isdir(cookie_dir):
            os.mkdir(cookie_dir, 0700)
        # Load existing cookies if the cookies.txt exists
        if os.path.isfile(cookie_file):
            self.cookies.load()
            self.cookies.clear_expired_cookies()

    def clear(self, domain):
        """Clear cookies for the specified domain."""
        try:
            self.cookies.clear(domain)
            self.cookies.save()
        except KeyError:
            pass

    def git_root(self):
        """
        Return the absolute path from the git repository root

        If no git repository exists, raise an EnvironmentError
        """
        try:
            git_root = subprocess.check_output(
                ['git', 'rev-parse', '--show-toplevel'],
                stderr=subprocess.PIPE).strip('\n')
        except subprocess.CalledProcessError:
            raise EnvironmentError('Current directory is not a git repository')
        return git_root

    def get_app(self):
        """
        Return the application name for the current directory

        The application is determined by parsing `git remote -v` output.
        If no application is found, raise an EnvironmentError.
        """
        git_root = self.git_root()
        # try to match a deis remote
        remotes = subprocess.check_output(['git', 'remote', '-v'],
                                          cwd=git_root)
        m = re.search(r'^deis\W+(?P<url>\S+)\W+\(', remotes, re.MULTILINE)
        if not m:
            raise EnvironmentError(
                'Could not find deis remote in `git remote -v`')
        url = m.groupdict()['url']
        m = re.match('\S+/(?P<app>[a-z0-9-]+)(.git)?$', url)
        if not m:
            raise EnvironmentError("Could not parse: {url}".format(**locals()))
        return m.groupdict()['app']

    app = property(get_app)

    def request(self, *args, **kwargs):
        """
        Issue an HTTP request with proper cookie handling including
        `Django CSRF tokens <https://docs.djangoproject.com/en/dev/ref/contrib/csrf/>`
        """
        for cookie in self.cookies:
            if cookie.name == 'csrftoken':
                if 'headers' in kwargs:
                    kwargs['headers']['X-CSRFToken'] = cookie.value
                else:
                    kwargs['headers'] = {'X-CSRFToken': cookie.value}
                break
        response = super(Session, self).request(*args, **kwargs)
        self.cookies.save()
        return response


class Settings(dict):
    """
    Settings backed by a file in the user's home directory

    On init, settings are loaded from ~/.deis/client.yaml
    """

    def __init__(self):
        path = os.path.expanduser('~/.deis')
        if not os.path.exists(path):
            os.mkdir(path)
        self._path = os.path.join(path, 'client.yaml')
        if not os.path.exists(self._path):
            with open(self._path, 'w') as f:
                f.write(yaml.safe_dump({}))
        # load initial settings
        self.load()

    def load(self):
        """
        Deserialize and load settings from the filesystem
        """
        with open(self._path) as f:
            data = f.read()
        settings = yaml.safe_load(data)
        self.update(settings)
        return settings

    def save(self):
        """
        Serialize and save settings to the filesystem
        """
        data = yaml.safe_dump(dict(self))
        with open(self._path, 'w') as f:
            f.write(data)
        return data


_counter = 0


def _newname(template="Thread-{}"):
    """Generate a new thread name."""
    global _counter
    _counter += 1
    return template.format(_counter)


FRAMES = {
    'arrow': ['^', '>', 'v', '<'],
    'dots': ['...', 'o..', '.o.', '..o'],
    'ligatures': ['bq', 'dp', 'qb', 'pd'],
    'lines': [' ', '-', '=', '#', '=', '-'],
    'slash': ['-', '\\', '|', '/'],
}


class TextProgress(Thread):
    """Show progress for a long-running operation on the command-line."""

    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        name = name or _newname("TextProgress-Thread-{}")
        style = kwargs.get('style', 'dots')
        super(TextProgress, self).__init__(
            group, target, name, args, kwargs)
        self.daemon = True
        self.cancelled = Event()
        self.frames = cycle(FRAMES[style])

    def run(self):
        """Write ASCII progress animation frames to stdout."""
        if not os.environ.get('DEIS_HIDE_PROGRESS'):
            time.sleep(0.5)
            self._write_frame(self.frames.next(), erase=False)
            while not self.cancelled.is_set():
                time.sleep(0.4)
                self._write_frame(self.frames.next())
            # clear the animation
            sys.stdout.write('\b' * (len(self.frames.next()) + 2))
            sys.stdout.flush()

    def cancel(self):
        """Set the animation thread as cancelled."""
        self.cancelled.set()

    def _write_frame(self, frame, erase=True):
        if erase:
            backspaces = '\b' * (len(frame) + 2)
        else:
            backspaces = ''
        sys.stdout.write("{} {} ".format(backspaces, frame))
        # flush stdout or we won't see the frame
        sys.stdout.flush()


def dictify(args):
    """Converts a list of key=val strings into a python dict.

    >>> dictify(['MONGODB_URL=http://mongolabs.com/test', 'scale=5'])
    {'MONGODB_URL': 'http://mongolabs.com/test', 'scale': 5}
    """
    data = {}
    for arg in args:
        try:
            var, val = arg.split('=', 1)
        except ValueError:
            raise DocoptExit()
        # Try to coerce the value to an int since that's a common use case
        try:
            data[var] = int(val)
        except ValueError:
            data[var] = val
    return data


def readable_datetime(datetime_str):
    """
    Return a human-readable datetime string from an ECMA-262 (JavaScript)
    datetime string.
    """
    timezone = tz.tzlocal()
    dt = parser.parse(datetime_str).astimezone(timezone)
    now = datetime.now(timezone)
    delta = relativedelta.relativedelta(now, dt)
    # if it happened today, say "2 hours and 1 minute ago"
    if delta.days <= 1 and dt.day == now.day:
        if delta.hours == 0:
            hour_str = ''
        elif delta.hours == 1:
            hour_str = '1 hour '
        else:
            hour_str = "{} hours ".format(delta.hours)
        if delta.minutes == 0:
            min_str = ''
        elif delta.minutes == 1:
            min_str = '1 minute '
        else:
            min_str = "{} minutes ".format(delta.minutes)
        if not any((hour_str, min_str)):
            return 'Just now'
        else:
            return "{}{}ago".format(hour_str, min_str)
    # if it happened yesterday, say "yesterday at 3:23 pm"
    yesterday = now + relativedelta.relativedelta(days= -1)
    if delta.days <= 2 and dt.day == yesterday.day:
        return dt.strftime("Yesterday at %X")
    # otherwise return locale-specific date/time format
    else:
        return dt.strftime('%c %Z')


def trim(docstring):
    """
    Function to trim whitespace from docstring

    c/o PEP 257 Docstring Conventions
    <http://www.python.org/dev/peps/pep-0257/>
    """
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


class ResponseError(Exception):
    pass


class DeisClient(object):
    """
    A client which interacts with a Deis controller.
    """

    def __init__(self):
        self._session = Session()
        self._settings = Settings()

    def _dispatch(self, method, path, body=None,
                  headers={'content-type': 'application/json'}, **kwargs):
        """
        Dispatch an API request to the active Deis controller
        """
        func = getattr(self._session, method.lower())
        controller = self._settings['controller']
        if not controller:
            raise EnvironmentError(
                'No active controller. Use `deis login` or `deis register` to get started.')
        url = urlparse.urljoin(controller, path, **kwargs)
        response = func(url, data=body, headers=headers)
        return response

    def apps(self, args):
        """
        Valid commands for apps:

        apps:create        create a new application
        apps:list          list accessible applications
        apps:info          view info about an application
        apps:open          open the application in a browser
        apps:logs          view aggregated application logs
        apps:run           run a command in an ephemeral app container
        apps:destroy       destroy an application

        Use `deis help [command]` to learn more
        """
        return self.apps_list(args)

    def apps_create(self, args):
        """
        Create a new application

        If no ID is provided, one will be generated automatically.
        If no cluster is provided, a cluster named "dev" will be used.

        Usage: deis apps:create [<id> --cluster=<cluster> --no-remote] [options]

        Options

        --cluster=CLUSTER      target cluster to host application [default: dev]
        --no-remote            do not create a 'deis' git remote
        """
        try:
            self._session.git_root()  # check for a git repository
        except EnvironmentError:
            print('No git repository found, use `git init` to create one')
            sys.exit(1)
        try:
            self._session.get_app()
            print('Deis remote already exists')
            sys.exit(1)
        except EnvironmentError:
            pass
        body = {}
        app_name = args.get('<id>')
        if app_name:
            body.update({'id': app_name})
        cluster = args.get('--cluster')
        if cluster:
            body.update({'cluster': cluster})
        sys.stdout.write('Creating application... ')
        sys.stdout.flush()
        try:
            progress = TextProgress()
            progress.start()
            response = self._dispatch('post', '/api/apps',
                                      json.dumps(body))
        finally:
            progress.cancel()
            progress.join()
        if response.status_code == requests.codes.created:  # @UndefinedVariable
            data = response.json()
            app_id = data['id']
            print("done, created {}".format(app_id))
            # add a git remote
            # TODO: retrieve the hostname from service discovery
            hostname = urlparse.urlparse(self._settings['controller']).netloc.split(':')[0]
            git_remote = "ssh://git@{hostname}:2222/{app_id}.git".format(**locals())
            if args.get('--no-remote'):
                print('remote available at {}'.format(git_remote))
            else:
                try:
                    subprocess.check_call(
                        ['git', 'remote', 'add', '-f', 'deis', git_remote],
                        stdout=subprocess.PIPE)
                    print('Git remote deis added')
                except subprocess.CalledProcessError:
                    print('Could not create Deis remote')
                    sys.exit(1)
        else:
            raise ResponseError(response)

    def apps_destroy(self, args):
        """
        Destroy an application

        Usage: deis apps:destroy [--app=<id> --confirm=<confirm>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        confirm = args.get('--confirm')
        if confirm == app:
            pass
        else:
            print("""
 !    WARNING: Potentially Destructive Action
 !    This command will destroy the application: {app}
 !    To proceed, type "{app}" or re-run this command with --confirm={app}
""".format(**locals()))
            confirm = raw_input('> ').strip('\n')
            if confirm != app:
                print('Destroy aborted')
                return
        sys.stdout.write("Destroying {}... ".format(app))
        sys.stdout.flush()
        try:
            progress = TextProgress()
            progress.start()
            before = time.time()
            response = self._dispatch('delete', "/api/apps/{}".format(app))
        finally:
            progress.cancel()
            progress.join()
        if response.status_code in (requests.codes.no_content,  # @UndefinedVariable
                                    requests.codes.not_found):  # @UndefinedVariable
            print('done in {}s'.format(int(time.time() - before)))
            # If the requested app is in the current dir, delete the git remote
            try:
                if app == self._session.app:
                    subprocess.check_call(
                        ['git', 'remote', 'rm', 'deis'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    print('Git remote deis removed')
            except (EnvironmentError, subprocess.CalledProcessError):
                pass  # ignore error
        else:
            raise ResponseError(response)

    def apps_list(self, args):
        """
        List applications visible to the current user

        Usage: deis apps:list
        """
        response = self._dispatch('get', '/api/apps')
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            data = response.json()
            print('=== Apps')
            for item in data['results']:
                print('{id}'.format(**item))
        else:
            raise ResponseError(response)

    def apps_info(self, args):
        """
        Print info about the current application

        Usage: deis apps:info [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        response = self._dispatch('get', "/api/apps/{}".format(app))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            print("=== {} Application".format(app))
            print(json.dumps(response.json(), indent=2))
            print()
            self.ps_list(args)
            self.domains_list(args)
            print()
        else:
            raise ResponseError(response)

    def apps_open(self, args):
        """
        Open a URL to the application in a browser

        Usage: deis apps:open [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        # TODO: replace with a single API call to apps endpoint
        response = self._dispatch('get', "/api/apps/{}".format(app))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            cluster = response.json()['cluster']
        else:
            raise ResponseError(response)
        response = self._dispatch('get', "/api/clusters/{}".format(cluster))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            domain = response.json()['domain']
            # use the OS's default handler to open this URL
            webbrowser.open('http://{}.{}/'.format(app, domain))
            return domain
        else:
            raise ResponseError(response)

    def apps_logs(self, args):
        """
        Retrieve the most recent log events

        Usage: deis apps:logs [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        response = self._dispatch('post',
                                  "/api/apps/{}/logs".format(app))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            print(response.json())
        else:
            raise ResponseError(response)

    def apps_run(self, args):
        """
        Run a command inside an ephemeral app container

        Usage: deis apps:run <command>...
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        body = {'command': ' '.join(sys.argv[2:])}
        response = self._dispatch('post',
                                  "/api/apps/{}/run".format(app),
                                  json.dumps(body))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            rc, output = json.loads(response.content)
            sys.stdout.write(output)
            sys.stdout.flush()
            sys.exit(rc)
        else:
            raise ResponseError(response)

    def auth(self, args):
        """
        Valid commands for auth:

        auth:register          register a new user
        auth:cancel            remove the current account
        auth:login             authenticate against a controller
        auth:logout            clear the current user session

        Use `deis help [command]` to learn more
        """
        return

    def auth_register(self, args):
        """
        Register a new user with a Deis controller

        Usage: deis auth:register <controller> [options]

        Options:

        --username=USERNAME    provide a username for the new account
        --password=PASSWORD    provide a password for the new account
        --email=EMAIL          provide an email address
        """
        controller = args['<controller>']
        if not urlparse.urlparse(controller).scheme:
            controller = "http://{}".format(controller)
        username = args.get('--username')
        if not username:
            username = raw_input('username: ')
        password = args.get('--password')
        if not password:
            password = getpass('password: ')
            confirm = getpass('password (confirm): ')
            if password != confirm:
                print('Password mismatch, aborting registration.')
                sys.exit(1)
        email = args.get('--email')
        if not email:
            email = raw_input('email: ')
        url = urlparse.urljoin(controller, '/api/auth/register')
        payload = {'username': username, 'password': password, 'email': email}
        response = self._session.post(url, data=payload, allow_redirects=False)
        if response.status_code == requests.codes.created:  # @UndefinedVariable
            self._settings['controller'] = controller
            self._settings.save()
            print("Registered {}".format(username))
            login_args = {'--username': username, '--password': password,
                          '<controller>': controller}
            if self.auth_login(login_args) is False:
                print('Login failed')
        else:
            print('Registration failed', response.content)
            sys.exit(1)
        return True

    def auth_cancel(self, args):
        """
        Cancel and remove the current account.

        Usage: deis auth:cancel
        """
        controller = self._settings.get('controller')
        if not controller:
            print('Not logged in to a Deis controller')
            sys.exit(1)
        print('Please log in again in order to cancel this account')
        username = self.auth_login({'<controller>': controller})
        if username:
            confirm = raw_input("Cancel account \"{}\" at {}? (y/n) ".format(username, controller))
            if confirm == 'y':
                self._dispatch('delete', '/api/auth/cancel')
                self._session.cookies.clear()
                self._session.cookies.save()
                self._settings['controller'] = None
                self._settings.save()
                print('Account cancelled')
            else:
                print('Accont not changed')

    def auth_login(self, args):
        """
        Login by authenticating against a controller

        Usage: deis auth:login <controller> [--username=<username> --password=<password>]
        """
        controller = args['<controller>']
        if not urlparse.urlparse(controller).scheme:
            controller = "http://{}".format(controller)
        username = args.get('--username')
        headers = {}
        if not username:
            username = raw_input('username: ')
        password = args.get('--password')
        if not password:
            password = getpass('password: ')
        url = urlparse.urljoin(controller, '/api/auth/login/')
        payload = {'username': username, 'password': password}
        # clear any cookies for this controller's domain
        self._session.clear(urlparse.urlparse(url).netloc)
        # prime cookies for login
        self._session.get(url, headers=headers)
        # post credentials to the login URL
        response = self._session.post(url, data=payload, allow_redirects=False)
        if response.status_code == requests.codes.found:  # @UndefinedVariable
            self._settings['controller'] = controller
            self._settings.save()
            print("Logged in as {}".format(username))
            return username
        else:
            self._session.cookies.clear()
            self._session.cookies.save()
            raise ResponseError(response)

    def auth_logout(self, args):
        """
        Logout from a controller and clear the user session

        Usage: deis auth:logout
        """
        controller = self._settings.get('controller')
        if controller:
            self._dispatch('get', '/api/auth/logout/')
        self._session.cookies.clear()
        self._session.cookies.save()
        self._settings['controller'] = None
        self._settings.save()
        print('Logged out')

    def builds(self, args):
        """
        Valid commands for builds:

        builds:list        list build history for an application
        builds:create      coming soon!

        Use `deis help [command]` to learn more
        """
        return self.builds_list(args)

    def builds_create(self, args):
        """
        Create a new build of an application

        Usage: deis builds:create <image> [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        body = {'image': args['<image>']}
        sys.stdout.write('Creating build... ')
        sys.stdout.flush()
        try:
            progress = TextProgress()
            progress.start()
            response = self._dispatch('post', "/api/apps/{}/builds".format(app), json.dumps(body))
        finally:
            progress.cancel()
            progress.join()
        if response.status_code == requests.codes.created:  # @UndefinedVariable
            version = response.headers['x-deis-release']
            print("done, v{}".format(version))
        else:
            raise ResponseError(response)

    def builds_list(self, args):
        """
        List build history for an application

        Usage: deis builds:list [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        response = self._dispatch('get', "/api/apps/{}/builds".format(app))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            print("=== {} Builds".format(app))
            data = response.json()
            for item in data['results']:
                print("{0[uuid]:<23} {0[created]}".format(item))
        else:
            raise ResponseError(response)

    def clusters(self, args):
        """
        Valid commands for clusters:

        clusters:create        create a new cluster
        clusters:list          list accessible clusters
        clusters:update        update cluster fields
        clusters:info          print a represenation of the cluster
        clusters:destroy       destroy a cluster

        Use `deis help [command]` to learn more
        """
        return self.clusters_list(args)

    def clusters_create(self, args):
        """
        Create a new cluster

        A globally unique cluster ID must be provided.

        A domain field must also be provided to support multiple
        applications hosted on the cluster.  Note this requires
        wildcard DNS configuration on the domain.

        For example, a domain of "deisapp.com" requires that \\*.deisapp.com\\
        resolve to the cluster's router endpoints.

        Usage: deis clusters:create <id> <domain> --hosts=<hosts> --auth=<auth> [options]

        Parameters:

        <id>             a name for the cluster
        <domain>         a domain under which app hostnames will live
        <hosts>          a comma-separated list of cluster members
        <auth>           a path to an SSH private key used to connect to cluster members

        Options:

        --type=TYPE      cluster type [default: coreos]
        """
        body = {'id': args['<id>'], 'domain': args['<domain>'],
                'hosts': args['--hosts'], 'type': args['--type']}
        auth_path = os.path.expanduser(args['--auth'])
        if not os.path.exists(auth_path):
            print('Path to authentication credentials does not exist: {}'.format(auth_path))
            sys.exit(1)
        with open(auth_path) as f:
            data = f.read()
        body.update({'auth': base64.b64encode(data)})
        sys.stdout.write('Creating cluster... ')
        sys.stdout.flush()
        try:
            progress = TextProgress()
            progress.start()
            response = self._dispatch('post', '/api/clusters', json.dumps(body))
        finally:
            progress.cancel()
            progress.join()
        if response.status_code == requests.codes.created:  # @UndefinedVariable
            data = response.json()
            cluster = data['id']
            print("done, created {}".format(cluster))
        else:
            raise ResponseError(response)

    def clusters_info(self, args):
        """
        Print info about a cluster

        Usage: deis clusters:info <id>
        """
        cluster = args.get('<id>')
        response = self._dispatch('get', "/api/clusters/{}".format(cluster))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            print("=== {} Cluster".format(cluster))
            print(json.dumps(response.json(), indent=2))
            print()
        else:
            raise ResponseError(response)

    def clusters_list(self, args):
        """
        List available clusters

        Usage: deis clusters:list
        """
        response = self._dispatch('get', '/api/clusters')
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            data = response.json()
            print("=== Clusters")
            for item in data['results']:
                print("{id}".format(**item))
        else:
            raise ResponseError(response)

    def clusters_destroy(self, args):
        """
        Destroy a cluster

        Usage: deis clusters:destroy <id> [--confirm=<confirm>]
        """
        cluster = args.get('<id>')
        confirm = args.get('--confirm')
        if confirm == cluster:
            pass
        else:
            print("""
 !    WARNING: Potentially Destructive Action
 !    This command will destroy the cluster: {cluster}
 !    To proceed, type "{cluster}" or re-run this command with --confirm={cluster}
""".format(**locals()))
            confirm = raw_input('> ').strip('\n')
            if confirm != cluster:
                print('Destroy aborted')
                return
        sys.stdout.write("Destroying cluster... ".format(cluster))
        sys.stdout.flush()
        try:
            progress = TextProgress()
            progress.start()
            before = time.time()
            response = self._dispatch('delete', "/api/clusters/{}".format(cluster))
        finally:
            progress.cancel()
            progress.join()
        if response.status_code in (requests.codes.no_content,  # @UndefinedVariable
                                    requests.codes.not_found):  # @UndefinedVariable
            print('done in {}s'.format(int(time.time() - before)))
        else:
            raise ResponseError(response)

    def clusters_update(self, args):
        """
        Update cluster fields

        Usage: deis clusters:update <id> [--domain=<domain> --hosts=<hosts> --auth=<auth>] [options]

        Options:

        --type=TYPE      cluster type [default: coreos]
        """
        cluster = args['<id>']
        body = {}
        for k, arg in (('domain', '--domain'), ('hosts', '--hosts'),
                       ('auth', '--auth'), ('type', '--type')):
            v = args.get(arg)
            if v:
                body.update({k: v})
        response = self._dispatch('patch', '/api/clusters/{}'.format(cluster),
                                  json.dumps(body))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            print(json.dumps(response.json(), indent=2))
        else:
            raise ResponseError(response)

    def config(self, args):
        """
        Valid commands for config:

        config:list        list environment variables for an app
        config:set         set environment variables for an app
        config:unset       unset environment variables for an app

        Use `deis help [command]` to learn more
        """
        sys.argv[1] = 'config:list'
        args = docopt(self.config_list.__doc__)
        return self.config_list(args)

    def config_list(self, args):
        """
        List environment variables for an application

        Usage: deis config:list [--oneline] [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app

        oneline = args.get('--oneline')
        response = self._dispatch('get', "/api/apps/{}/config".format(app))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            config = response.json()
            values = json.loads(config['values'])
            print("=== {} Config".format(app))
            items = values.items()
            if len(items) == 0:
                print('No configuration')
                return
            keys = sorted(values)

            if not oneline:
                width = max(map(len, keys)) + 5
                for k in keys:
                    v = values[k]
                    print(("{k:<" + str(width) + "} {v}").format(**locals()))
            else:
                output = []
                for k in keys:
                    v = values[k]
                    output.append("{k}={v}".format(**locals()))
                print(' '.join(output))
        else:
            raise ResponseError(response)

    def config_set(self, args):
        """
        Set environment variables for an application

        Usage: deis config:set <var>=<value>... [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        body = {'values': json.dumps(dictify(args['<var>=<value>']))}
        sys.stdout.write('Creating config... ')
        sys.stdout.flush()
        try:
            progress = TextProgress()
            progress.start()
            response = self._dispatch('post', "/api/apps/{}/config".format(app), json.dumps(body))
        finally:
            progress.cancel()
            progress.join()
        if response.status_code == requests.codes.created:  # @UndefinedVariable
            version = response.headers['x-deis-release']
            print("done, v{}\n".format(version))
            config = response.json()
            values = json.loads(config['values'])
            print("=== {}".format(app))
            items = values.items()
            if len(items) == 0:
                print('No configuration')
                return
            for k, v in values.items():
                print("{k}: {v}".format(**locals()))
        else:
            raise ResponseError(response)

    def config_unset(self, args):
        """
        Unset an environment variable for an application

        Usage: deis config:unset <key>... [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        values = {}
        for k in args.get('<key>'):
            values[k] = None
        body = {'values': json.dumps(values)}
        sys.stdout.write('Creating config... ')
        sys.stdout.flush()
        try:
            progress = TextProgress()
            progress.start()
            response = self._dispatch('post', "/api/apps/{}/config".format(app), json.dumps(body))
        finally:
            progress.cancel()
            progress.join()
        if response.status_code == requests.codes.created:  # @UndefinedVariable
            version = response.headers['x-deis-release']
            print("done, v{}\n".format(version))
            config = response.json()
            values = json.loads(config['values'])
            print("=== {}".format(app))
            items = values.items()
            if len(items) == 0:
                print('No configuration')
                return
            for k, v in values.items():
                print("{k}: {v}".format(**locals()))
        else:
            raise ResponseError(response)

    def domains(self, args):
        """
        Valid commands for domains:

        domains:add           bind a domain to an application
        domains:list          list domains bound to an application
        domains:remove        unbind a domain from an application

        Use `deis help [command]` to learn more
        """
        return self.domains_list(args)

    def domains_add(self, args):
        """
        Bind a domain to an application

        Usage: deis domains:add <domain> [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        domain = args.get('<domain>')
        body = {'domain': domain}
        sys.stdout.write("Adding {domain} to {app}... ".format(**locals()))
        sys.stdout.flush()
        try:
            progress = TextProgress()
            progress.start()
            response = self._dispatch('post', "/api/apps/{app}/domains".format(app=app), json.dumps(body))
        finally:
            progress.cancel()
            progress.join()
        if response.status_code == requests.codes.created:  # @UndefinedVariable
            print("done")
        else:
            raise ResponseError(response)

    def domains_remove(self, args):
        """
        Unbind a domain for an application

        Usage: deis domains:remove <domain> [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        domain = args.get('<domain>')
        sys.stdout.write("Removing {domain} from {app}... ".format(**locals()))
        sys.stdout.flush()
        try:
            progress = TextProgress()
            progress.start()
            response = self._dispatch('delete', "/api/apps/{app}/domains/{domain}".format(**locals()))
        finally:
            progress.cancel()
            progress.join()
        if response.status_code == requests.codes.no_content:  # @UndefinedVariable
            print("done")
        else:
            raise ResponseError(response)

    def domains_list(self, args):
        """
        List domains bound to an application

        Usage: deis domains:list [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        response = self._dispatch(
            'get', "/api/apps/{app}/domains".format(app=app))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            domains = response.json()['results']
            print("=== {} Domains".format(app))
            if len(domains) == 0:
                print('No domains')
                return
            for domain in domains:
                print(domain['domain'])
        else:
            raise ResponseError(response)

    def ps(self, args):
        """
        Valid commands for processes:

        ps:list        list application processes
        ps:scale       scale processes (e.g. web=4 worker=2)

        Use `deis help [command]` to learn more
        """
        sys.argv[1] = 'ps:list'
        args = docopt(self.ps_list.__doc__)
        return self.ps_list(args)

    def ps_list(self, args, app=None):
        """
        List processes servicing an application

        Usage: deis ps:list [--app=<app>]
        """
        if not app:
            app = args.get('--app')
            if not app:
                app = self._session.app
        response = self._dispatch('get',
                                  "/api/apps/{}/containers".format(app))
        if response.status_code != requests.codes.ok:  # @UndefinedVariable
            raise ResponseError(response)
        processes = response.json()
        print("=== {} Processes".format(app))
        c_map = {}
        for item in processes['results']:
            c_map.setdefault(item['type'], []).append(item)
        print()
        for c_type in c_map.keys():
            print("--- {c_type}: ".format(**locals()))
            for c in c_map[c_type]:
                print("{type}.{num} {state} ({release})".format(**c))
            print()

    def ps_scale(self, args):
        """
        Scale an application's processes by type

        Example: deis ps:scale web=4 worker=2

        Usage: deis ps:scale <type=num>... [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.get_app()
        body = {}
        for type_num in args.get('<type=num>'):
            typ, count = type_num.split('=')
            body.update({typ: int(count)})
        print('Scaling processes... but first, coffee!')
        try:
            progress = TextProgress()
            progress.start()
            before = time.time()
            response = self._dispatch('post',
                                      "/api/apps/{}/scale".format(app),
                                      json.dumps(body))
        finally:
            progress.cancel()
            progress.join()
        if response.status_code == requests.codes.no_content:  # @UndefinedVariable
            print('done in {}s\n'.format(int(time.time() - before)))
            self.ps_list({}, app)
        else:
            raise ResponseError(response)

    def keys(self, args):
        """
        Valid commands for SSH keys:

        keys:list        list SSH keys for the logged in user
        keys:add         add an SSH key
        keys:remove      remove an SSH key

        Use `deis help [command]` to learn more
        """
        return self.keys_list(args)

    def keys_add(self, args):
        """
        Add SSH keys for the logged in user

        Usage: deis keys:add [<key>]
        """

        path = args.get('<key>')
        if not path:
            selected_key = self._ask_pubkey_interactively()
        else:
            # check the specified key format
            selected_key = self._parse_key(path)
            if not selected_key:
                return
        # Upload the key to Deis
        body = {
            'id': selected_key.id,
            'public': "{} {}".format(selected_key.type, selected_key.str)
        }
        sys.stdout.write("Uploading {} to Deis...".format(selected_key.id))
        sys.stdout.flush()
        response = self._dispatch('post', '/api/keys', json.dumps(body))
        if response.status_code == requests.codes.created:  # @UndefinedVariable
            print('done')
        else:
            raise ResponseError(response)

    def _parse_key(self, path):
        """Parse an SSH public key path into a Key namedtuple."""
        Key = namedtuple('Key', 'path name type str comment id')

        name = path.split(os.path.sep)[-1]
        with open(path) as f:
            data = f.read()
            match = re.match(r'^(ssh-...) ([^ ]+) ?(.*)', data)
            if not match:
                print("Could not parse SSH public key {0}".format(name))
                sys.exit(1)
            key_type, key_str, key_comment = match.groups()
            if key_comment:
                key_id = key_comment
            else:
                key_id = name.replace('.pub', '')
            return Key(path, name, key_type, key_str, key_comment, key_id)

    def _ask_pubkey_interactively(self):
        # find public keys and prompt the user to pick one
        ssh_dir = os.path.expanduser('~/.ssh')
        pubkey_paths = glob.glob(os.path.join(ssh_dir, '*.pub'))
        if not pubkey_paths:
            print('No SSH public keys found')
            return
        pubkeys_list = [self._parse_key(k) for k in pubkey_paths]
        print('Found the following SSH public keys:')
        for i, key_ in enumerate(pubkeys_list):
            print("{}) {} {}".format(i + 1, key_.name, key_.comment))
        print("0) Enter path to pubfile (or use keys:add <key_path>) ")
        inp = raw_input('Which would you like to use with Deis? ')
        try:
            if int(inp) != 0:
                selected_key = pubkeys_list[int(inp) - 1]
            else:
                selected_key_path = raw_input('Enter the path to the pubkey file: ')
                selected_key = self._parse_key(os.path.expanduser(selected_key_path))
        except:
            print('Aborting')
            return
        return selected_key

    def keys_list(self, args):
        """
        List SSH keys for the logged in user

        Usage: deis keys:list
        """
        response = self._dispatch('get', '/api/keys')
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            data = response.json()
            if data['count'] == 0:
                print('No keys found')
                return
            print("=== {owner} Keys".format(**data['results'][0]))
            for key in data['results']:
                public = key['public']
                print("{0} {1}...{2}".format(
                    key['id'], public[0:16], public[-10:]))
        else:
            raise ResponseError(response)

    def keys_remove(self, args):
        """
        Remove an SSH key for the logged in user

        Usage: deis keys:remove <key>
        """
        key = args.get('<key>')
        sys.stdout.write("Removing {} SSH Key... ".format(key))
        sys.stdout.flush()
        response = self._dispatch('delete', "/api/keys/{}".format(key))
        if response.status_code == requests.codes.no_content:  # @UndefinedVariable
            print('done')
        else:
            raise ResponseError(response)

    def perms(self, args):
        """
        Valid commands for perms:

        perms:list            list permissions granted on an app or cluster
        perms:create          create a new permission for a user
        perms:delete          delete a permission for a user

        Use `deis help perms:[command]` to learn more
        """
        # perms:transfer        transfer ownership of an app or cluster
        sys.argv[1] = 'perms:list'
        args = docopt(self.perms_list.__doc__)
        return self.perms_list(args)

    def perms_list(self, args):
        """
        List all users with permission to use an app, or list all users
        with system administrator privileges.

        Usage: deis perms:list [--app=<app>|--admin]
        """
        app, url = self._parse_perms_args(args)
        response = self._dispatch('get', url)
        if response.status_code == requests.codes.ok:
            print(json.dumps(response.json(), indent=2))
        else:
            raise ResponseError(response)

    def perms_create(self, args):
        """
        Give another user permission to use an app, or give another user
        system administrator privileges.

        Usage: deis perms:create <username> [--app=<app>|--admin]
        """
        app, url = self._parse_perms_args(args)
        username = args.get('<username>')
        body = {'username': username}
        if app:
            msg = "Adding {} to {} collaborators... ".format(username, app)
        else:
            msg = "Adding {} to system administrators... ".format(username)
        sys.stdout.write(msg)
        sys.stdout.flush()
        response = self._dispatch('post', url, json.dumps(body))
        if response.status_code == requests.codes.created:
            print('done')
        else:
            raise ResponseError(response)

    def perms_delete(self, args):
        """
        Revoke another user's permission to use an app, or revoke another
        user's system administrator privileges.

        Usage: deis perms:delete <username> [--app=<app>|--admin]
        """
        app, url = self._parse_perms_args(args)
        username = args.get('<username>')
        url = "{}/{}".format(url, username)
        if app:
            msg = "Removing {} from {} collaborators... ".format(username, app)
        else:
            msg = "Remove {} from system administrators... ".format(username)
        sys.stdout.write(msg)
        sys.stdout.flush()
        response = self._dispatch('delete', url)
        if response.status_code == requests.codes.no_content:
            print('done')
        else:
            raise ResponseError(response)

    def _parse_perms_args(self, args):
        app = args.get('--app'),
        admin = args.get('--admin')
        if admin:
            app = None
            url = '/api/admin/perms'
        else:
            app = app[0] or self._session.app
            url = "/api/apps/{}/perms".format(app)
        return app, url

    def releases(self, args):
        """
        Valid commands for releases:

        releases:list        list an application's release history
        releases:info        print information about a specific release
        releases:rollback    return to a previous release

        Use `deis help [command]` to learn more
        """
        return self.releases_list(args)

    def releases_info(self, args):
        """
        Print info about a particular release

        Usage: deis releases:info <version> [--app=<app>]
        """
        version = args.get('<version>')
        if not version.startswith('v'):
            version = 'v' + version
        app = args.get('--app')
        if not app:
            app = self._session.app
        response = self._dispatch(
            'get', "/api/apps/{app}/releases/{version}".format(**locals()))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            print(json.dumps(response.json(), indent=2))
        else:
            raise ResponseError(response)

    def releases_list(self, args):
        """
        List release history for an application

        Usage: deis releases:list [--app=<app>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        response = self._dispatch('get', "/api/apps/{app}/releases".format(**locals()))
        if response.status_code == requests.codes.ok:  # @UndefinedVariable
            print("=== {} Releases".format(app))
            data = response.json()
            for item in data['results']:
                item['created'] = readable_datetime(item['created'])
                print("v{version:<6} {created:<33} {summary}".format(**item))
        else:
            raise ResponseError(response)

    def releases_rollback(self, args):
        """
        Roll back to a previous application release.

        Usage: deis releases:rollback [--app=<app>] [<version>]
        """
        app = args.get('--app')
        if not app:
            app = self._session.app
        version = args.get('<version>')
        if version:
            if version.startswith('v'):
                version = version[1:]
            body = {'version': int(version)}
        else:
            body = {}
        url = "/api/apps/{app}/releases/rollback".format(**locals())
        response = self._dispatch('post', url, json.dumps(body))
        if response.status_code == requests.codes.created:
            print(response.json())
        else:
            raise ResponseError(response)

    def shortcuts(self, args):
        """
        Show valid shortcuts for client commands.

        Usage: deis shortcuts
        """
        print('Valid shortcuts are:\n')
        for shortcut, command in SHORTCUTS.items():
            if ':' not in shortcut:
                print("{:<10} -> {}".format(shortcut, command))
        print('\nUse `deis help [command]` to learn more')

SHORTCUTS = OrderedDict([
    ('create', 'apps:create'),
    ('destroy', 'apps:destroy'),
    ('init', 'clusters:create'),
    ('info', 'apps:info'),
    ('run', 'apps:run'),
    ('open', 'apps:open'),
    ('logs', 'apps:logs'),
    ('register', 'auth:register'),
    ('login', 'auth:login'),
    ('logout', 'auth:logout'),
    ('scale', 'ps:scale'),
    ('rollback', 'releases:rollback'),
    ('sharing', 'perms:list'),
    ('sharing:list', 'perms:list'),
    ('sharing:add', 'perms:create'),
    ('sharing:remove', 'perms:delete'),
])


def parse_args(cmd):
    """
    Parse command-line args applying shortcuts and looking for help flags
    """
    if cmd == 'help':
        cmd = sys.argv[-1]
        help_flag = True
    else:
        cmd = sys.argv[1]
        help_flag = False
    # swap cmd with shortcut
    if cmd in SHORTCUTS:
        cmd = SHORTCUTS[cmd]
        # change the cmdline arg itself for docopt
        if not help_flag:
            sys.argv[1] = cmd
        else:
            sys.argv[2] = cmd
    # convert : to _ for matching method names and docstrings
    if ':' in cmd:
        cmd = '_'.join(cmd.split(':'))
    return cmd, help_flag


def _dispatch_cmd(method, args):
    try:
        method(args)
    except requests.exceptions.ConnectionError as err:
        print("Couldn't connect to the Deis Controller. Make sure that the Controller URI is \
correct and the server is running.")
        sys.exit(1)
    except EnvironmentError as err:
        raise DocoptExit(err.message)
    except ResponseError as err:
        resp = err.message
        print('{} {}'.format(resp.status_code, resp.reason))
        try:
            msg = resp.json()
            if 'detail' in msg:
                msg = "Detail:\n{}".format(msg['detail'])
        except:
            msg = resp.text
        print(msg)
        sys.exit(1)


def main():
    """
    Create a client, parse the arguments received on the command line, and
    call the appropriate method on the client.
    """
    cli = DeisClient()
    args = docopt(__doc__, version='Deis CLI {}'.format(__version__),
                  options_first=True)
    cmd = args['<command>']
    cmd, help_flag = parse_args(cmd)
    # print help if it was asked for
    if help_flag:
        if cmd != 'help' and cmd in dir(cli):
            print(trim(getattr(cli, cmd).__doc__))
            return
        docopt(__doc__, argv=['--help'])
    # unless cmd needs to use sys.argv directly
    if hasattr(cli, cmd):
        method = getattr(cli, cmd)
    else:
        raise DocoptExit('Found no matching command, try `deis help`')
    # re-parse docopt with the relevant docstring unless it needs sys.argv
    if cmd not in ('apps_run',):
        docstring = trim(getattr(cli, cmd).__doc__)
        if 'Usage: ' in docstring:
            args.update(docopt(docstring))
    # dispatch the CLI command
    _dispatch_cmd(method, args)


if __name__ == '__main__':
    main()
    sys.exit(0)

########NEW FILE########
__FILENAME__ = test_apps
"""
Unit tests for the Deis CLI apps commands.

Run these tests with "python -m unittest client.tests.test_apps"
or with "./manage.py test client.AppsTest".
"""

from __future__ import unicode_literals
from unittest import TestCase
from uuid import uuid4
import json
import re

import pexpect

from .utils import DEIS
from .utils import DEIS_TEST_FLAVOR
from .utils import clone
from .utils import purge
from .utils import random_repo
from .utils import register


class AppsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.username, cls.password = register()
        # create a new formation
        cls.formation = "{}-test-formation-{}".format(
            cls.username, uuid4().hex[:4])
        child = pexpect.spawn("{} formations:create {} --flavor={}".format(
            DEIS, cls.formation, DEIS_TEST_FLAVOR))
        child.expect("created {}.*to scale a basic formation".format(
            cls.formation))
        child.expect(pexpect.EOF)
        repo_name, (repo_type, repo_url) = random_repo()
        # print repo_name, repo_type, repo_url
        clone(repo_url, repo_name)

    @classmethod
    def tearDownClass(cls):
        # delete the formation
        child = pexpect.spawn("{} formations:destroy {} --confirm={}".format(
            DEIS, cls.formation, cls.formation))
        child.expect('done in ', timeout=5 * 60)
        child.expect(pexpect.EOF)
        purge(cls.username, cls.password)

    def test_create(self):
        # create the app
        self.assertIsNotNone(self.formation)
        child = pexpect.spawn("{} create --formation={}".format(
            DEIS, self.formation))
        child.expect('done, created (?P<name>[-_\w]+)', timeout=5 * 60)
        app = child.match.group('name')
        child.expect('Git remote deis added')
        child.expect(pexpect.EOF)
        # check that it's in the list of apps
        child = pexpect.spawn("{} apps".format(DEIS))
        child.expect('=== Apps')
        child.expect(pexpect.EOF)
        apps = re.findall(r'([-_\w]+) {\w?}', child.before)
        self.assertIn(app, apps)
        # destroy the app
        child = pexpect.spawn("{} apps:destroy --confirm={}".format(DEIS, app),
                              timeout=5 * 60)
        child.expect('Git remote deis removed')
        child.expect(pexpect.EOF)

    def test_destroy(self):
        # create the app
        self.assertIsNotNone(self.formation)
        child = pexpect.spawn("{} apps:create --formation={}".format(
            DEIS, self.formation))
        child.expect('done, created ([-_\w]+)', timeout=5 * 60)
        app = child.match.group(1)
        child.expect(pexpect.EOF)
        # check that it's in the list of apps
        child = pexpect.spawn("{} apps".format(DEIS))
        child.expect('=== Apps')
        child.expect(pexpect.EOF)
        apps = re.findall(r'([-_\w]+) {\w?}', child.before)
        self.assertIn(app, apps)
        # destroy the app
        child = pexpect.spawn("{} destroy --confirm={}".format(DEIS, app))
        child.expect("Destroying {}".format(app))
        child.expect('done in \d+s')
        child.expect('Git remote deis removed')
        child.expect(pexpect.EOF)

    def test_list(self):
        # list apps and get their names
        child = pexpect.spawn("{} apps".format(DEIS))
        child.expect('=== Apps')
        child.expect(pexpect.EOF)
        apps_before = re.findall(r'([-_\w]+) {\w?}', child.before)
        # create a new app
        self.assertIsNotNone(self.formation)
        child = pexpect.spawn("{} apps:create --formation={}".format(
            DEIS, self.formation))
        child.expect('done, created ([-_\w]+)')
        app = child.match.group(1)
        child.expect(pexpect.EOF)
        # list apps and get their names
        child = pexpect.spawn("{} apps".format(DEIS))
        child.expect('=== Apps')
        child.expect(pexpect.EOF)
        apps = re.findall(r'([-_\w]+) {\w?}', child.before)
        # test that the set of names contains the previous set
        self.assertLess(set(apps_before), set(apps))
        # delete the app
        child = pexpect.spawn("{} apps:destroy --app={} --confirm={}".format(
            DEIS, app, app))
        child.expect('done in ', timeout=5 * 60)
        child.expect(pexpect.EOF)
        # list apps and get their names
        child = pexpect.spawn("{} apps:list".format(DEIS))
        child.expect('=== Apps')
        child.expect(pexpect.EOF)
        apps = re.findall(r'([-_\w]+) {\w?}', child.before)
        # test that the set of names is equal to the original set
        self.assertEqual(set(apps_before), set(apps))

    def test_info(self):
        # create a new app
        self.assertIsNotNone(self.formation)
        child = pexpect.spawn("{} create --formation={}".format(
            DEIS, self.formation))
        child.expect('done, created (?P<name>[-_\w]+)')
        app = child.match.group('name')
        child.expect('Git remote deis added')
        child.expect(pexpect.EOF)
        # get app info
        child = pexpect.spawn("{} info".format(DEIS))
        child.expect("=== {} Application".format(app))
        child.expect("=== {} Containers".format(app))
        response = json.loads(child.before)
        child.expect(pexpect.EOF)
        self.assertEqual(response['id'], app)
        self.assertEqual(response['formation'], self.formation)
        self.assertEqual(response['owner'], self.username)
        self.assertIn('uuid', response)
        self.assertIn('created', response)
        self.assertIn('containers', response)
        # delete the app
        child = pexpect.spawn("{} apps:destroy --app={} --confirm={}".format(
            DEIS, app, app))
        child.expect('done in ', timeout=5 * 60)
        child.expect(pexpect.EOF)

    # def test_calculate(self):
    #     pass

    # def test_open(self):
    #     pass

    # def test_logs(self):
    #     pass

    # def test_run(self):
    #     pass

########NEW FILE########
__FILENAME__ = test_auth
"""
Unit tests for the Deis CLI auth commands.

Run these tests with "python -m unittest client.tests.test_auth"
or with "./manage.py test client.AuthTest".
"""

from __future__ import unicode_literals
from unittest import TestCase

import pexpect

from .utils import DEIS
from .utils import DEIS_SERVER
from .utils import purge
from .utils import register


class AuthTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.username, cls.password = register()

    @classmethod
    def tearDownClass(cls):
        purge(cls.username, cls.password)

    def test_login(self):
        # log in the interactive way
        child = pexpect.spawn("{} login {}".format(DEIS, DEIS_SERVER))
        child.expect('username: ')
        child.sendline(self.username)
        child.expect('password: ')
        child.sendline(self.password)
        child.expect("Logged in as {}".format(self.username))
        child.expect(pexpect.EOF)

    def test_logout(self):
        child = pexpect.spawn("{} logout".format(DEIS))
        child.expect('Logged out')
        # log in the one-liner way
        child = pexpect.spawn("{} login {} --username={} --password={}".format(
            DEIS, DEIS_SERVER, self.username, self.password))
        child.expect("Logged in as {}".format(self.username))
        child.expect(pexpect.EOF)

########NEW FILE########
__FILENAME__ = test_builds
"""
Unit tests for the Deis CLI build commands.

Run these tests with "python -m unittest client.tests.test_builds"
or with "./manage.py test client.BuildsTest".
"""

from __future__ import unicode_literals
from unittest import TestCase


class BuildsTest(TestCase):

    pass


# class TestBuild(unittest.TestCase):

#     """Test builds."""

#     def setUp(self):
#         # TODO: set up the c3/api/fixtures/tests.json...somehow
#         child = pexpect.spawn('{} login {}'.format(CLI, CONTROLLER))
#         child.expect('username:')
#         child.sendline('autotest')
#         child.expect('password:')
#         child.sendline('password')
#         child.expect('Logged in as autotest')

#     def tearDown(self):
#         self.child = None

#     def test_build(self):
#         """Test that a user can publish a new build."""
#         _, temp = tempfile.mkstemp()
#         body = {
#             'sha': uuid.uuid4().hex,
#             'slug_size': 4096000,
#             'procfile': json.dumps({'web': 'node server.js'}),
#             'url':
#             'http://deis.local/slugs/1c52739bbf3a44d3bfb9a58f7bbdd5fb.tar.gz',
#             'checksum': uuid.uuid4().hex,
#         }
#         with open(temp, 'w') as f:
#             f.write(json.dumps(body))
#         child = pexpect.spawn(
#             'cat {} | {} builds:create - --app=test-app'.format(temp, CLI))
#         child.expect('Usage: ')

########NEW FILE########
__FILENAME__ = test_config
"""
Unit tests for the Deis CLI config commands.

Run these tests with "python -m unittest client.tests.test_config"
or with "./manage.py test client.ConfigTest".
"""

from __future__ import unicode_literals
from unittest import TestCase


class ConfigTest(TestCase):

    pass


# class TestConfig(unittest.TestCase):

#     """Test configuration docs and config values."""

#     def setUp(self):
#         # TODO: set up the c3/api/fixtures/tests.json...somehow
#         child = pexpect.spawn('{} login'.format(CLI))
#         child.expect('username:')
#         child.sendline('autotest')
#         child.expect('password:')
#         child.sendline('password')
#         child.expect('Logged in as autotest.')

#     def tearDown(self):
#         self.child = None

#     def test_config_syntax(self):
#         key, value = 'MONGODB_URL', 'http://mongolab.com/test'
#         # Test some invalid command line input
#         child = pexpect.spawn('{} config:set {}'.format(
#             CLI, key))
#         child.expect('Usage: ')
#         child = pexpect.spawn('{} config:set {} {}'.format(
#             CLI, key, value))
#         child.expect('Usage: ')
#         child = pexpect.spawn('{} config set {}={}'.format(
#             CLI, key, value))
#         child.expect('Usage: ')

#     def test_config(self):
#         """Test that a user can set a config value."""
#         key, value = 'MONGODB_URL', 'http://mongolab.com/test'
#         child = pexpect.spawn('{} config:set {}={}'.format(
#             CLI, key, value))
#         child.expect(pexpect.EOF)
#         child = pexpect.spawn('{} config:set {}={} DEBUG=True'.format(
#             CLI, key, value))
#         child.expect(pexpect.EOF)

########NEW FILE########
__FILENAME__ = test_containers
"""
Unit tests for the Deis CLI containers commands.

Run these tests with "python -m unittest client.tests.test_containers"
or with "./manage.py test client.ContainersTest".
"""

from __future__ import unicode_literals
from unittest import TestCase


class ContainersTest(TestCase):

    pass

########NEW FILE########
__FILENAME__ = test_examples
"""
Unit tests for the Deis example-[language] projects.

Run these tests with "python -m unittest client.tests.test_examples"
or with "./manage.py test client.ExamplesTest".
"""

from __future__ import unicode_literals
from unittest import TestCase
from uuid import uuid4

import pexpect
import time

from .utils import DEIS
from .utils import DEIS_TEST_FLAVOR
from .utils import EXAMPLES
from .utils import clone
from .utils import purge
from .utils import register


class ExamplesTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.username, cls.password = register()
        # create a new formation
        cls.formation = "{}-test-formation-{}".format(
            cls.username, uuid4().hex[:4])
        child = pexpect.spawn("{} formations:create {} --flavor={}".format(
            DEIS, cls.formation, DEIS_TEST_FLAVOR))
        child.expect("created {}.*to scale a basic formation".format(
            cls.formation))
        child.expect(pexpect.EOF)
        # scale the formation runtime=1
        child = pexpect.spawn("{} nodes:scale {} runtime=1".format(
            DEIS, cls.formation), timeout=10 * 60)
        child.expect('Scaling nodes...')
        child.expect(r'done in \d+s')
        child.expect(pexpect.EOF)

    @classmethod
    def tearDownClass(cls):
        # scale formation runtime=0
        child = pexpect.spawn("{} nodes:scale {} runtime=0".format(
            DEIS, cls.formation), timeout=3 * 60)
        child.expect('Scaling nodes...')
        child.expect(r'done in \d+s')
        child.expect(pexpect.EOF)
        # destroy the formation
        child = pexpect.spawn("{} formations:destroy {} --confirm={}".format(
            DEIS, cls.formation, cls.formation))
        child.expect('done in ', timeout=5 * 60)
        child.expect(pexpect.EOF)
        purge(cls.username, cls.password)

    def _test_example(self, repo_name, build_timeout=120, run_timeout=60):
        # `git clone` the example app repository
        _repo_type, repo_url = EXAMPLES[repo_name]
        # print repo_name, repo_type, repo_url
        clone(repo_url, repo_name)
        # create an App
        child = pexpect.spawn("{} create --formation={}".format(
            DEIS, self.formation))
        child.expect('done, created (?P<name>[-_\w]+)', timeout=60)
        app = child.match.group('name')
        try:
            child.expect('Git remote deis added')
            child.expect(pexpect.EOF)
            child = pexpect.spawn('git push deis master')
            # check git output for repo_type, e.g. "Clojure app detected"
            # TODO: for some reason, the next regex times out...
            # child.expect("{} app detected".format(repo_type), timeout=5 * 60)
            child.expect('Launching... ', timeout=build_timeout)
            child.expect('deployed to Deis(?P<url>.+)To learn more', timeout=run_timeout)
            url = child.match.group('url')
            child.expect(' -> master')
            child.expect(pexpect.EOF, timeout=10)
            # try to fetch the URL with curl a few times, ignoring 502's
            for _ in range(6):
                child = pexpect.spawn("curl -s {}".format(url))
                i = child.expect(['Powered by Deis', '502 Bad Gateway'], timeout=5)
                child.expect(pexpect.EOF)
                if i == 0:
                    break
                time.sleep(10)
            else:
                raise RuntimeError('Persistent 502 Bad Gateway')
            # `deis config:set POWERED_BY="Automated Testing"`
            child = pexpect.spawn(
                "{} config:set POWERED_BY='Automated Testing'".format(DEIS))
            child.expect(pexpect.EOF, timeout=3 * 60)
            # then re-fetch the URL with curl and recheck the output
            for _ in range(6):
                child = pexpect.spawn("curl -s {}".format(url))
                child.expect(['Powered by Automated Testing', '502 Bad Gateway'], timeout=5)
                child.expect(pexpect.EOF)
                if i == 0:
                    break
                time.sleep(10)
            else:
                raise RuntimeError('Config:set not working')
        finally:
            # destroy the app
            child = pexpect.spawn(
                "{} apps:destroy --app={} --confirm={}".format(DEIS, app, app),
                timeout=5 * 60)
            child.expect('Git remote deis removed')
            child.expect(pexpect.EOF)

    def test_clojure_ring(self):
        self._test_example('example-clojure-ring')

    def _test_dart(self):
        # TODO: fix broken buildpack / example app
        self._test_example('example-dart')

    def test_go(self):
        self._test_example('example-go')

    def test_java_jetty(self):
        self._test_example('example-java-jetty')

    def test_nodejs_express(self):
        self._test_example('example-nodejs-express')

    def test_perl(self):
        self._test_example('example-perl', build_timeout=600)

    def test_php(self):
        self._test_example('example-php')

    def _test_play(self):
        # TODO: fix broken buildpack / example app
        self._test_example('example-play', build_timeout=720)

    def test_python_flask(self):
        self._test_example('example-python-flask')

    def test_ruby_sinatra(self):
        self._test_example('example-ruby-sinatra')

    def test_scala(self):
        self._test_example('example-scala', build_timeout=720)

########NEW FILE########
__FILENAME__ = test_flavors
"""
Unit tests for the Deis CLI flavors commands.

Run these tests with "python -m unittest client.tests.test_flavors"
or with "./manage.py test client.FlavorsTest".
"""

from __future__ import unicode_literals
from unittest import TestCase
import re

import json
import pexpect
import random
from uuid import uuid4

from .utils import DEIS
from .utils import purge
from .utils import register


class FlavorsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.username, cls.password = register()

    @classmethod
    def tearDownClass(cls):
        purge(cls.username, cls.password)

    def test_create(self):
        # create a new flavor
        id_ = "test-flavor-{}".format(uuid4().hex[:4])
        child = pexpect.spawn("{} flavors:create {} --provider={} --params='{}'".format(
            DEIS, id_, 'ec2',
            '{"region":"ap-southeast-2","image":"ami-d5f66bef","zone":"any","size":"m1.medium"}'
        ))
        child.expect(id_)
        child.expect(pexpect.EOF)
        # list the flavors and make sure it's in there
        child = pexpect.spawn("{} flavors".format(DEIS))
        child.expect(pexpect.EOF)
        flavors = re.findall('([\w|-]+): .*', child.before)
        self.assertIn(id_, flavors)
        # delete the new flavor
        child = pexpect.spawn("{} flavors:delete {}".format(DEIS, id_))
        child.expect(pexpect.EOF)
        self.assertNotIn('Error', child.before)

    def test_update(self):
        # create a new flavor
        id_ = "test-flavor-{}".format(uuid4().hex[:4])
        child = pexpect.spawn("{} flavors:create {} --provider={} --params={}".format(
            DEIS, id_, 'mock', '{}'))
        child.expect(id_)
        child.expect(pexpect.EOF)
        # update the provider
        child = pexpect.spawn("{} flavors:update {} --provider={}".format(DEIS, id_, 'ec2'))
        child.expect(pexpect.EOF)
        # update the params
        child = pexpect.spawn("{} flavors:update {} {}".format(
            DEIS, id_, "'{\"key1\": \"val1\"}'"))
        child.expect(pexpect.EOF)
        # test the flavor contents
        child = pexpect.spawn("{} flavors:info {}".format(DEIS, id_))
        child.expect(pexpect.EOF)
        results = json.loads(child.before)
        self.assertEqual('ec2', results['provider'])
        self.assertIn('key1', results['params'])
        self.assertIn('val1', results['params'])
        # update the params and provider
        child = pexpect.spawn("{} flavors:update {} {} --provider={}".format(
            DEIS, id_, "'{\"key2\": \"val2\"}'", 'mock'))
        child.expect(pexpect.EOF)
        # test the flavor contents
        child = pexpect.spawn("{} flavors:info {}".format(DEIS, id_))
        child.expect(pexpect.EOF)
        results = json.loads(child.before)
        self.assertIn('key1', results['params'])
        self.assertIn('val1', results['params'])
        self.assertIn('key2', results['params'])
        self.assertIn('val2', results['params'])
        self.assertEqual('mock', results['provider'])
        # update the params to remove a value
        child = pexpect.spawn("{} flavors:update {} {}".format(
            DEIS, id_, "'{\"key1\": null}'"))
        child.expect(pexpect.EOF)
        # test the flavor contents
        child = pexpect.spawn("{} flavors:info {}".format(DEIS, id_))
        child.expect(pexpect.EOF)
        results = json.loads(child.before)
        self.assertNotIn('key1', results['params'])
        self.assertNotIn('val1', results['params'])
        self.assertIn('key2', results['params'])
        self.assertIn('val2', results['params'])
        # delete the new flavor
        child = pexpect.spawn("{} flavors:delete {}".format(DEIS, id_))
        child.expect(pexpect.EOF)
        self.assertNotIn('Error', child.before)

    def test_delete(self):
        # create a new flavor
        id_ = "test-flavor-{}".format(uuid4().hex[:4])
        child = pexpect.spawn("{} flavors:create {} --provider={} --params='{}'".format(
            DEIS, id_, 'ec2',
            '{"region":"ap-southeast-2","image":"ami-d5f66bef","zone":"any","size":"m1.medium"}'
        ))
        child.expect(id_)
        child.expect(pexpect.EOF)
        # delete the new flavor
        child = pexpect.spawn("{} flavors:delete {}".format(DEIS, id_))
        child.expect(pexpect.EOF)
        self.assertNotIn('Error', child.before)
        # list the flavors and make sure it's not in there
        child = pexpect.spawn("{} flavors".format(DEIS))
        child.expect(pexpect.EOF)
        flavors = re.findall('([\w|-]+): .*', child.before)
        self.assertNotIn(id_, flavors)

    def test_list(self):
        child = pexpect.spawn("{} flavors".format(DEIS))
        child.expect(pexpect.EOF)
        before = child.before
        flavors = re.findall('([\w|-]+): .*', before)
        # test that there were at least 3 flavors seeded
        self.assertGreaterEqual(len(flavors), 3)
        # test that "flavors" and "flavors:list" are equivalent
        child = pexpect.spawn("{} flavors:list".format(DEIS))
        child.expect(pexpect.EOF)
        self.assertEqual(before, child.before)

    def test_info(self):
        child = pexpect.spawn("{} flavors".format(DEIS))
        child.expect(pexpect.EOF)
        flavor = random.choice(re.findall('([\w|-]+): .*', child.before))
        child = pexpect.spawn("{} flavors:info {}".format(DEIS, flavor))
        child.expect(pexpect.EOF)
        # test that we received JSON results
        # TODO: There's some error here, but only when run as part of the
        # entire test suite?
        results = json.loads(child.before)
        self.assertIn('created', results)
        self.assertIn('updated', results)
        self.assertIn('provider', results)
        self.assertIn('id', results)
        self.assertIn('params', results)
        self.assertEqual(results['owner'], self.username)

########NEW FILE########
__FILENAME__ = test_formations
"""
Unit tests for the Deis CLI formations commands.

Run these tests with "python -m unittest client.tests.test_formations"
or with "./manage.py test client.FormationsTest".
"""

from __future__ import unicode_literals
from unittest import TestCase
from uuid import uuid4
import re

import pexpect

from .utils import DEIS
from .utils import DEIS_TEST_FLAVOR
from .utils import purge
from .utils import register


class FormationsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.username, cls.password = register()

    @classmethod
    def tearDownClass(cls):
        purge(cls.username, cls.password)

    def test_list(self):
        # list formations and get their names
        child = pexpect.spawn("{} formations".format(DEIS))
        child.expect('=== Formations')
        child.expect(pexpect.EOF)
        formations_before = re.findall(r'([-_\w]+) {\w?}', child.before)
        # create a new formation
        formation = "{}-test-formation-{}".format(self.username, uuid4().hex[:4])
        child = pexpect.spawn("{} formations:create {} --flavor={}".format(
            DEIS, formation, DEIS_TEST_FLAVOR))
        child.expect("created {}.*to scale a basic formation".format(formation))
        child.expect(pexpect.EOF)
        # list formations and get their names
        child = pexpect.spawn("{} formations".format(DEIS))
        child.expect('=== Formations')
        child.expect(pexpect.EOF)
        formations = re.findall(r'([-_\w]+) {\w?}', child.before)
        # test that the set of names contains the previous set
        self.assertLess(set(formations_before), set(formations))
        # delete the formation
        child = pexpect.spawn("{} formations:destroy {} --confirm={}".format(
            DEIS, formation, formation))
        child.expect('done in ', timeout=5*60)
        child.expect(pexpect.EOF)
        # list formations and get their names
        child = pexpect.spawn("{} formations:list".format(DEIS))
        child.expect('=== Formations')
        child.expect(pexpect.EOF)
        formations = re.findall(r'([-_\w]+) {\w?}', child.before)
        # test that the set of names is equal to the original set
        self.assertEqual(set(formations_before), set(formations))

    def test_create(self):
        formation = "{}-test-formation-{}".format(self.username, uuid4().hex[:4])
        child = pexpect.spawn("{} formations:create {} --flavor={}".format(
            DEIS, formation, DEIS_TEST_FLAVOR))
        child.expect("created {}.*to scale a basic formation".format(formation))
        child.expect(pexpect.EOF)
        # destroy formation the one-liner way
        child = pexpect.spawn("{} formations:destroy {} --confirm={}".format(
            DEIS, formation, formation))
        child.expect('done in ', timeout=5*60)
        child.expect(pexpect.EOF)

    def test_destroy(self):
        formation = "{}-test-formation-{}".format(self.username, uuid4().hex[:4])
        child = pexpect.spawn("{} formations:create {} --flavor={}".format(
            DEIS, formation, DEIS_TEST_FLAVOR))
        child.expect("created {}.*to scale a basic formation".format(formation))
        child.expect(pexpect.EOF)
        # destroy formation the interactive way
        child = pexpect.spawn("{} formations:destroy {}".format(DEIS, formation))
        child.expect('> ')
        child.sendline(formation)
        child.expect('done in ', timeout=5*60)
        child.expect(pexpect.EOF)

########NEW FILE########
__FILENAME__ = test_keys
"""
Unit tests for the Deis CLI keys commands.

Run these tests with "python -m unittest client.tests.test_keys"
or with "./manage.py test client.KeysTest".
"""

from __future__ import unicode_literals
from unittest import TestCase
import glob
import os.path

import pexpect

from .utils import DEIS
from .utils import purge
from .utils import register


class KeysTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.username, cls.password = register(False, False)

    @classmethod
    def tearDownClass(cls):
        purge(cls.username, cls.password)

    def test_add(self):
        # test adding a specified key--the "choose a key" path is well
        # covered in utils.register()
        ssh_dir = os.path.expanduser('~/.ssh')
        pubkey = glob.glob(os.path.join(ssh_dir, '*.pub'))[0]
        child = pexpect.spawn("{} keys:add {}".format(DEIS, pubkey))
        child.expect('Uploading')
        child.expect('...done')
        child.expect(pexpect.EOF)

########NEW FILE########
__FILENAME__ = test_layers
"""
Unit tests for the Deis CLI layers commands.

Run these tests with "python -m unittest client.tests.test_layers"
or with "./manage.py test client.LayersTest".
"""

from __future__ import unicode_literals
from unittest import TestCase


class LayersTest(TestCase):

    pass

########NEW FILE########
__FILENAME__ = test_misc
"""
Unit tests for the Deis CLI auth commands.

Run these tests with "python -m unittest client.tests.test_misc"
or with "./manage.py test client.HelpTest client.VersionTest".
"""

from __future__ import unicode_literals
from unittest import TestCase

import pexpect

from client.deis import __version__
from .utils import DEIS


class HelpTest(TestCase):
    """Test that the client can document its own behavior."""

    def test_deis(self):
        """Test that the `deis` command on its own returns usage."""
        child = pexpect.spawn(DEIS)
        child.expect('Usage: deis <command> \[<args>...\]')

    def test_help(self):
        """Test that the client reports its help message."""
        child = pexpect.spawn('{} --help'.format(DEIS))
        child.expect('The Deis command-line client.*to an application\.')
        child = pexpect.spawn('{} -h'.format(DEIS))
        child.expect('The Deis command-line client.*to an application\.')
        child = pexpect.spawn('{} help'.format(DEIS))
        child.expect('The Deis command-line client.*to an application\.')


class VersionTest(TestCase):
    """Test that the client can report its version string."""

    def test_version(self):
        """Test that the client reports its version string."""
        child = pexpect.spawn('{} --version'.format(DEIS))
        child.expect("Deis CLI {}".format(__version__))

########NEW FILE########
__FILENAME__ = test_nodes
"""
Unit tests for the Deis CLI nodes commands.

Run these tests with "python -m unittest client.tests.test_nodes"
or with "./manage.py test client.NodesTest".
"""

from __future__ import unicode_literals
from unittest import TestCase


class NodesTest(TestCase):

    pass

########NEW FILE########
__FILENAME__ = test_providers
"""
Unit tests for the Deis CLI providers commands.

Run these tests with "python -m unittest client.tests.test_providers"
or with "./manage.py test client.ProvidersTest".
"""

from __future__ import unicode_literals
from unittest import TestCase

import pexpect

from .utils import DEIS
from .utils import purge
from .utils import register


class ProvidersTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.username, cls.password = register()

    @classmethod
    def tearDownClass(cls):
        purge(cls.username, cls.password)

    def test_seeded(self):
        """Test that our autotest user has some providers auto-seeded."""
        child = pexpect.spawn("{} providers".format(DEIS))
        child.expect(".* => .*")
        child.expect(pexpect.EOF)

########NEW FILE########
__FILENAME__ = test_releases
"""
Unit tests for `git push deis master` and related commands.

Run these tests with "python -m unittest client.tests.test_releases"
or with "./manage.py test client.ReleasesTest".
"""

from __future__ import unicode_literals
from unittest import TestCase


class ReleasesTest(TestCase):

    pass

########NEW FILE########
__FILENAME__ = test_sharing
"""
Unit tests for the Deis example-[language] projects.

Run these tests with "python -m unittest client.tests.test_sharing"
or with "./manage.py test client.SharingTest".
"""

from __future__ import unicode_literals
from unittest import TestCase
from uuid import uuid4
import os

import pexpect
from .utils import DEIS
from .utils import DEIS_TEST_FLAVOR
from .utils import EXAMPLES
from .utils import clone
from .utils import login
from .utils import purge
from .utils import register


class SharingTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.username2, cls.password2 = register()
        cls.username, cls.password = register()
        # create a new formation
        cls.formation = "{}-test-formation-{}".format(
            cls.username, uuid4().hex[:4])
        child = pexpect.spawn("{} formations:create {} --flavor={}".format(
            DEIS, cls.formation, DEIS_TEST_FLAVOR))
        child.expect("created {}.*to scale a basic formation".format(
            cls.formation))
        child.expect(pexpect.EOF)

    @classmethod
    def tearDownClass(cls):
        purge(cls.username2, cls.password2)
        login(cls.username, cls.password)
        child = pexpect.spawn("{} formations:destroy {} --confirm={}".format(
            DEIS, cls.formation, cls.formation))
        child.expect('done in ', timeout=5 * 60)
        child.expect(pexpect.EOF)
        purge(cls.username, cls.password)

    def _test_sharing(self, repo_name):
        # `git clone` the example app repository
        repo_type, repo_url = EXAMPLES[repo_name]
        clone(repo_url, repo_name)
        # create an App
        child = pexpect.spawn("{} create --formation={}".format(
            DEIS, self.formation))
        child.expect('done, created (?P<name>[-_\w]+)', timeout=3 * 60)
        app = child.match.group('name')
        try:
            child.expect('Git remote deis added')
            child.expect(pexpect.EOF)
            home = os.environ['HOME']
            login(self.username2, self.password2)
            os.chdir(os.path.join(home, repo_name))
            child = pexpect.spawn('git push deis master')
            child.expect('access denied')
            child.expect(pexpect.EOF)
            login(self.username, self.password)
            os.chdir(os.path.join(home, repo_name))
            child = pexpect.spawn("{} sharing:add {} --app={}".format(
                DEIS, self.username2, app))
            child.expect('done')
            child.expect(pexpect.EOF)
            login(self.username2, self.password2)
            os.chdir(os.path.join(home, repo_name))
            child = pexpect.spawn('git push deis master')
            # check git output for repo_type, e.g. "Clojure app detected"
            # TODO: for some reason, the next regex times out...
            # child.expect("{} app detected".format(repo_type), timeout=5 * 60)
            child.expect('Launching... ', timeout=10 * 60)
            child.expect('deployed to Deis(?P<url>.+)To learn more', timeout=3 * 60)
            url = child.match.group('url')  # noqa
            child.expect(' -> master')
            child.expect(pexpect.EOF, timeout=2 * 60)
        finally:
            login(self.username, self.password)
            os.chdir(os.path.join(home, repo_name))
            # destroy the app
            child = pexpect.spawn(
                "{} apps:destroy --app={} --confirm={}".format(DEIS, app, app),
                timeout=5 * 60)
            child.expect('Git remote deis removed')
            child.expect(pexpect.EOF)

    def test_go(self):
        self._test_sharing('example-go')

########NEW FILE########
__FILENAME__ = utils
"""
Common code used by the Deis CLI unit tests.
"""

from __future__ import unicode_literals
import os.path
import random
import re
import stat
from urllib2 import urlparse
from uuid import uuid4

import pexpect


# Constants and data used throughout the test suite
DEIS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'deis.py'))
try:
    DEIS_SERVER = os.environ['DEIS_SERVER']
except KeyError:
    DEIS_SERVER = None
    print '\033[35mError: env var DEIS_SERVER must point to a Deis controller URL.\033[0m'
DEIS_TEST_FLAVOR = os.environ.get('DEIS_TEST_FLAVOR', 'vagrant-512')
EXAMPLES = {
    'example-clojure-ring': ('Clojure', 'https://github.com/opdemand/example-clojure-ring.git'),
    'example-dart': ('Dart', 'https://github.com/opdemand/example-dart.git'),
    'example-go': ('Go', 'https://github.com/opdemand/example-go.git'),
    'example-java-jetty': ('Java', 'https://github.com/opdemand/example-java-jetty.git'),
    'example-nodejs-express':
    ('Node.js', 'https://github.com/opdemand/example-nodejs-express.git'),
    'example-perl': ('Perl/PSGI', 'https://github.com/opdemand/example-perl.git'),
    'example-php': (r'PHP \(classic\)', 'https://github.com/opdemand/example-php.git'),
    'example-play': ('Play 2.x - Java', 'https://github.com/opdemand/example-play.git'),
    'example-python-flask': ('Python', 'https://github.com/opdemand/example-python-flask.git'),
    'example-ruby-sinatra': ('Ruby', 'https://github.com/opdemand/example-ruby-sinatra.git'),
    'example-scala': ('Scala', 'https://github.com/opdemand/example-scala.git'),
}


def clone(repo_url, repo_dir):
    """Clone a git repository into the $HOME dir and cd there."""
    os.chdir(os.environ['HOME'])
    child = pexpect.spawn("git clone {} {}".format(repo_url, repo_dir))
    child.expect(', done')
    child.expect(pexpect.EOF)
    os.chdir(repo_dir)


def login(username, password):
    """Login as an existing Deis user."""
    home = os.path.join('/tmp', username)
    os.environ['HOME'] = home
    os.chdir(home)
    git_ssh_path = os.path.expandvars("$HOME/git_ssh.sh")
    os.environ['GIT_SSH'] = git_ssh_path
    child = pexpect.spawn("{} login {}".format(DEIS, DEIS_SERVER))
    child.expect('username:')
    child.sendline(username)
    child.expect('password:')
    child.sendline(password)
    child.expect("Logged in as {}".format(username))
    child.expect(pexpect.EOF)


def purge(username, password):
    """Purge an existing Deis user."""
    child = pexpect.spawn("{} auth:cancel".format(DEIS))
    child.expect('username: ')
    child.sendline(username)
    child.expect('password: ')
    child.sendline(password)
    child.expect('\? \(y/n\) ')
    child.sendline('y')
    child.expect(pexpect.EOF)
    ssh_path = os.path.expanduser('~/.ssh')
    child = pexpect.spawn(os.path.expanduser(
        "rm -f {}/{}*".format(ssh_path, username)))
    child.expect(pexpect.EOF)


def random_repo():
    """Return an example Heroku-style repository name, (type, URL)."""
    name = random.choice(EXAMPLES.keys())
    return name, EXAMPLES[name]


def register(add_keys=True, add_providers=True):
    """Register a new Deis user from the command line."""
    username = "autotester-{}".format(uuid4().hex[:4])
    password = 'password'
    home = os.path.join('/tmp', username)
    os.environ['HOME'] = home
    os.mkdir(home)
    os.chdir(home)
    # generate an SSH key
    ssh_path = os.path.expandvars('$HOME/.ssh')
    os.mkdir(ssh_path, 0700)
    key_path = "/{}/{}".format(ssh_path, username)
    child = pexpect.spawn("ssh-keygen -f {} -t rsa -N '' -C {}".format(
        key_path, username))
    child.expect("Your public key has been saved")
    child.expect(pexpect.EOF)
    # write out ~/.ssh/config
    ssh_config_path = os.path.expandvars("$HOME/.ssh/config")
    with open(ssh_config_path, 'w') as ssh_config:
        # get hostname from DEIS_SERVER
        server = urlparse.urlparse(DEIS_SERVER).netloc
        ssh_config.write("""\
    Hostname {}
    IdentitiesOnly yes
    IdentityFile {}/.ssh/{}
""".format(server, home, username))
    # make a GIT_SSH script to enforce use of our key
    git_ssh_path = os.path.expandvars("$HOME/git_ssh.sh")
    with open(git_ssh_path, 'w') as git_ssh:
        git_ssh.write("""\
#!/bin/sh

SSH_ORIGINAL_COMMAND="ssh $@"
ssh -F {} "$@"
""".format(ssh_config_path))
    os.chmod(git_ssh_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
             | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    os.environ['GIT_SSH'] = git_ssh_path
    child = pexpect.spawn("{} register {}".format(DEIS, DEIS_SERVER))
    child.expect('username: ')
    child.sendline(username)
    child.expect('password: ')
    child.sendline(password)
    child.expect('password \(confirm\): ')
    child.sendline(password)
    child.expect('email: ')
    child.sendline('autotest@opdemand.com')
    child.expect("Registered {}".format(username))
    child.expect("Logged in as {}".format(username))
    child.expect(pexpect.EOF)
    # add keys
    if add_keys:
        child = pexpect.spawn("{} keys:add".format(DEIS))
        child.expect('Which would you like to use with Deis')
        for index, key in re.findall('(\d)\) ([ \S]+)', child.before):
            if username in key:
                child.sendline(index)
                break
        child.expect('Uploading')
        child.expect('...done')
        child.expect(pexpect.EOF)
    # discover providers
    if add_providers:
        child = pexpect.spawn("{} providers:discover".format(DEIS))
        opt = child.expect(['Import EC2 credentials\? \(y/n\) :',
                           'No EC2 credentials discovered.'])
        if opt == 0:
            child.sendline('y')
        opt = child.expect(['Import Rackspace credentials\? \(y/n\) :',
                           'No Rackspace credentials discovered.'])
        if opt == 0:
            child.sendline('y')
        opt = child.expect(['Import DigitalOcean credentials\? \(y/n\) :',
                           'No DigitalOcean credentials discovered.'])
        if opt == 0:
            child.sendline('y')
        child.expect(pexpect.EOF)
    return username, password

########NEW FILE########
__FILENAME__ = gen-json
#!/usr/bin/env python
import json
import os

template = json.load(open("deis.template",'r'))

with open('../coreos/user-data','r') as f:
  lines = f.readlines()

template['Resources']['CoreOSServerLaunchConfig']['Properties']['UserData']['Fn::Base64']['Fn::Join'] = [ '', lines ]
template['Parameters']['ClusterSize']['Default'] = str(os.getenv('DEIS_NUM_INSTANCES', 3))

print json.dumps(template)

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-

"""
Django admin app configuration for Deis API models.
"""

from __future__ import unicode_literals

from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from .models import App
from .models import Build
from .models import Cluster
from .models import Config
from .models import Container
from .models import Domain
from .models import Key
from .models import Release


class AppAdmin(GuardedModelAdmin):
    """Set presentation options for :class:`~api.models.App` models
    in the Django admin.
    """
    date_hierarchy = 'created'
    list_display = ('id', 'owner', 'cluster')
    list_filter = ('owner', 'cluster')
admin.site.register(App, AppAdmin)


class BuildAdmin(admin.ModelAdmin):
    """Set presentation options for :class:`~api.models.Build` models
    in the Django admin.
    """
    date_hierarchy = 'created'
    list_display = ('created', 'owner', 'app')
    list_filter = ('owner', 'app')
admin.site.register(Build, BuildAdmin)


class ClusterAdmin(admin.ModelAdmin):
    """Set presentation options for :class:`~api.models.Cluster` models
    in the Django admin.
    """
    date_hierarchy = 'created'
    list_display = ('id', 'owner', 'domain')
    list_filter = ('owner',)
admin.site.register(Cluster, ClusterAdmin)


class ConfigAdmin(admin.ModelAdmin):
    """Set presentation options for :class:`~api.models.Config` models
    in the Django admin.
    """
    date_hierarchy = 'created'
    list_display = ('created', 'owner', 'app')
    list_filter = ('owner', 'app')
admin.site.register(Config, ConfigAdmin)


class ContainerAdmin(admin.ModelAdmin):
    """Set presentation options for :class:`~api.models.Container` models
    in the Django admin.
    """
    date_hierarchy = 'created'
    list_display = ('short_name', 'owner', 'app', 'state')
    list_filter = ('owner', 'app', 'state')
admin.site.register(Container, ContainerAdmin)


class DomainAdmin(admin.ModelAdmin):
    """Set presentation options for :class:`~api.models.Domain` models
    in the Django admin.
    """
    date_hierarchy = 'created'
    list_display = ('owner', 'app', 'domain')
    list_filter = ('owner', 'app')
admin.site.register(Domain, DomainAdmin)


class KeyAdmin(admin.ModelAdmin):
    """Set presentation options for :class:`~api.models.Key` models
    in the Django admin.
    """
    date_hierarchy = 'created'
    list_display = ('id', 'owner', '__str__')
    list_filter = ('owner',)
admin.site.register(Key, KeyAdmin)


class ReleaseAdmin(admin.ModelAdmin):
    """Set presentation options for :class:`~api.models.Release` models
    in the Django admin.
    """
    date_hierarchy = 'created'
    list_display = ('created', 'version', 'owner', 'app')
    list_display_links = ('created', 'version')
    list_filter = ('owner', 'app')
admin.site.register(Release, ReleaseAdmin)

########NEW FILE########
__FILENAME__ = exceptions
"""
Deis API exception classes.
"""

from __future__ import unicode_literals

from rest_framework.exceptions import APIException


class AbstractDeisException(APIException):
    """
    Abstract class in which all Deis Exceptions and Errors should extend.

    This exception is subclassed from rest_framework's APIException so that
    subclasses can change the status code to something different than
    "500 SERVER ERROR."
    """

    def __init__(self, detail=None):
        self.detail = detail

    class Meta:
        abstract = True

########NEW FILE########
__FILENAME__ = fields
"""
Deis API custom fields for representing data in Django forms.
"""

from __future__ import unicode_literals
from uuid import uuid4

from django import forms
from django.db import models


class UuidField(models.CharField):
    """A univerally unique ID field."""

    description = __doc__

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('auto_created', True)
        kwargs.setdefault('editable', False)
        kwargs.setdefault('max_length', 32)
        kwargs.setdefault('unique', True)
        super(UuidField, self).__init__(*args, **kwargs)

    def db_type(self, connection=None):
        """Return the database column type for a UuidField."""
        if connection and 'postgres' in connection.vendor:
            return 'uuid'
        else:
            return "char({})".format(self.max_length)

    def pre_save(self, model_instance, add):
        """Initialize an empty field with a new UUID before it is saved."""
        value = getattr(model_instance, self.get_attname(), None)
        if not value and add:
            uuid = str(uuid4())
            setattr(model_instance, self.get_attname(), uuid)
            return uuid
        else:
            return super(UuidField, self).pre_save(model_instance, add)

    def formfield(self, **kwargs):
        """Tell forms how to represent this UuidField."""
        kwargs.update({
            'form_class': forms.CharField,
            'max_length': self.max_length,
        })
        return super(UuidField, self).formfield(**kwargs)


try:
    from south.modelsinspector import add_introspection_rules
    # Tell the South schema migration tool to handle our custom fields.
    add_introspection_rules([], [r'^api\.fields\.UuidField'])
except ImportError:  # pragma: no cover
    pass

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Key'
        db.create_table(u'api_key', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('public', self.gf('django.db.models.fields.TextField')(unique=True)),
        ))
        db.send_create_signal(u'api', ['Key'])

        # Adding unique constraint on 'Key', fields ['owner', 'id']
        db.create_unique(u'api_key', ['owner_id', 'id'])

        # Adding model 'Provider'
        db.create_table(u'api_provider', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.SlugField')(max_length=64)),
            ('type', self.gf('django.db.models.fields.SlugField')(max_length=16)),
            ('creds', self.gf('json_field.fields.JSONField')(default=u'null', blank=True)),
        ))
        db.send_create_signal(u'api', ['Provider'])

        # Adding unique constraint on 'Provider', fields ['owner', 'id']
        db.create_unique(u'api_provider', ['owner_id', 'id'])

        # Adding model 'Flavor'
        db.create_table(u'api_flavor', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.SlugField')(max_length=64)),
            ('provider', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Provider'])),
            ('params', self.gf('json_field.fields.JSONField')(default=u'null', blank=True)),
        ))
        db.send_create_signal(u'api', ['Flavor'])

        # Adding unique constraint on 'Flavor', fields ['owner', 'id']
        db.create_unique(u'api_flavor', ['owner_id', 'id'])

        # Adding model 'Formation'
        db.create_table(u'api_formation', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=64)),
            ('domain', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('nodes', self.gf('json_field.fields.JSONField')(default=u'{}', blank=True)),
        ))
        db.send_create_signal(u'api', ['Formation'])

        # Adding unique constraint on 'Formation', fields ['owner', 'id']
        db.create_unique(u'api_formation', ['owner_id', 'id'])

        # Adding model 'Layer'
        db.create_table(u'api_layer', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.SlugField')(max_length=64)),
            ('formation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Formation'])),
            ('flavor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Flavor'])),
            ('proxy', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('runtime', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('ssh_username', self.gf('django.db.models.fields.CharField')(default=u'ubuntu', max_length=64)),
            ('ssh_private_key', self.gf('django.db.models.fields.TextField')()),
            ('ssh_public_key', self.gf('django.db.models.fields.TextField')()),
            ('ssh_port', self.gf('django.db.models.fields.SmallIntegerField')(default=22)),
            ('config', self.gf('json_field.fields.JSONField')(default=u'{}', blank=True)),
        ))
        db.send_create_signal(u'api', ['Layer'])

        # Adding unique constraint on 'Layer', fields ['formation', 'id']
        db.create_unique(u'api_layer', ['formation_id', 'id'])

        # Adding model 'Node'
        db.create_table(u'api_node', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('formation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Formation'])),
            ('layer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Layer'])),
            ('num', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('provider_id', self.gf('django.db.models.fields.SlugField')(max_length=64, null=True, blank=True)),
            ('fqdn', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('status', self.gf('json_field.fields.JSONField')(default=u'null', null=True, blank=True)),
        ))
        db.send_create_signal(u'api', ['Node'])

        # Adding unique constraint on 'Node', fields ['formation', 'id']
        db.create_unique(u'api_node', ['formation_id', 'id'])

        # Adding model 'App'
        db.create_table(u'api_app', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=64)),
            ('formation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Formation'])),
            ('containers', self.gf('json_field.fields.JSONField')(default=u'{}', blank=True)),
        ))
        db.send_create_signal(u'api', ['App'])

        # Adding model 'Container'
        db.create_table(u'api_container', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('formation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Formation'])),
            ('node', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Node'])),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.App'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('num', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('port', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('status', self.gf('django.db.models.fields.CharField')(default=u'up', max_length=64)),
        ))
        db.send_create_signal(u'api', ['Container'])

        # Adding unique constraint on 'Container', fields ['app', 'type', 'num']
        db.create_unique(u'api_container', ['app_id', 'type', 'num'])

        # Adding unique constraint on 'Container', fields ['formation', 'port']
        db.create_unique(u'api_container', ['formation_id', 'port'])

        # Adding model 'Config'
        db.create_table(u'api_config', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.App'])),
            ('version', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('values', self.gf('json_field.fields.JSONField')(default=u'{}', blank=True)),
        ))
        db.send_create_signal(u'api', ['Config'])

        # Adding unique constraint on 'Config', fields ['app', 'version']
        db.create_unique(u'api_config', ['app_id', 'version'])

        # Adding model 'Build'
        db.create_table(u'api_build', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.App'])),
            ('sha', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('output', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('image', self.gf('django.db.models.fields.CharField')(default=u'deis/buildstep', max_length=256)),
            ('procfile', self.gf('json_field.fields.JSONField')(default=u'null', blank=True)),
            ('dockerfile', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('config', self.gf('json_field.fields.JSONField')(default=u'null', blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('size', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('checksum', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal(u'api', ['Build'])

        # Adding unique constraint on 'Build', fields ['app', 'uuid']
        db.create_unique(u'api_build', ['app_id', 'uuid'])

        # Adding model 'Release'
        db.create_table(u'api_release', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.App'])),
            ('version', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('config', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Config'])),
            ('build', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Build'], null=True, blank=True)),
        ))
        db.send_create_signal(u'api', ['Release'])

        # Adding unique constraint on 'Release', fields ['app', 'version']
        db.create_unique(u'api_release', ['app_id', 'version'])


    def backwards(self, orm):
        # Removing unique constraint on 'Release', fields ['app', 'version']
        db.delete_unique(u'api_release', ['app_id', 'version'])

        # Removing unique constraint on 'Build', fields ['app', 'uuid']
        db.delete_unique(u'api_build', ['app_id', 'uuid'])

        # Removing unique constraint on 'Config', fields ['app', 'version']
        db.delete_unique(u'api_config', ['app_id', 'version'])

        # Removing unique constraint on 'Container', fields ['formation', 'port']
        db.delete_unique(u'api_container', ['formation_id', 'port'])

        # Removing unique constraint on 'Container', fields ['app', 'type', 'num']
        db.delete_unique(u'api_container', ['app_id', 'type', 'num'])

        # Removing unique constraint on 'Node', fields ['formation', 'id']
        db.delete_unique(u'api_node', ['formation_id', 'id'])

        # Removing unique constraint on 'Layer', fields ['formation', 'id']
        db.delete_unique(u'api_layer', ['formation_id', 'id'])

        # Removing unique constraint on 'Formation', fields ['owner', 'id']
        db.delete_unique(u'api_formation', ['owner_id', 'id'])

        # Removing unique constraint on 'Flavor', fields ['owner', 'id']
        db.delete_unique(u'api_flavor', ['owner_id', 'id'])

        # Removing unique constraint on 'Provider', fields ['owner', 'id']
        db.delete_unique(u'api_provider', ['owner_id', 'id'])

        # Removing unique constraint on 'Key', fields ['owner', 'id']
        db.delete_unique(u'api_key', ['owner_id', 'id'])

        # Deleting model 'Key'
        db.delete_table(u'api_key')

        # Deleting model 'Provider'
        db.delete_table(u'api_provider')

        # Deleting model 'Flavor'
        db.delete_table(u'api_flavor')

        # Deleting model 'Formation'
        db.delete_table(u'api_formation')

        # Deleting model 'Layer'
        db.delete_table(u'api_layer')

        # Deleting model 'Node'
        db.delete_table(u'api_node')

        # Deleting model 'App'
        db.delete_table(u'api_app')

        # Deleting model 'Container'
        db.delete_table(u'api_container')

        # Deleting model 'Config'
        db.delete_table(u'api_config')

        # Deleting model 'Build'
        db.delete_table(u'api_build')

        # Deleting model 'Release'
        db.delete_table(u'api_release')


    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'containers': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'config': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dockerfile': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'default': "u'deis/buildstep'", 'max_length': '256'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'procfile': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'unique_together': "((u'app', u'type', u'num'), (u'formation', u'port'))", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Node']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "u'up'", 'max_length': '64'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.flavor': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Flavor'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'params': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Provider']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.formation': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Formation'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'nodes': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.layer': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Layer'},
            'config': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Flavor']"}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'proxy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'runtime': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ssh_port': ('django.db.models.fields.SmallIntegerField', [], {'default': '22'}),
            'ssh_private_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_public_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_username': ('django.db.models.fields.CharField', [], {'default': "u'ubuntu'", 'max_length': '64'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.node': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Node'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Layer']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'provider_id': ('django.db.models.fields.SlugField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'status': ('json_field.fields.JSONField', [], {'default': "u'null'", 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.provider': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Provider'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creds': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.SlugField', [], {'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']", 'null': 'True', 'blank': 'True'}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']
########NEW FILE########
__FILENAME__ = 0002_drop_djcelery
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.db.utils import ProgrammingError
from django.contrib.contenttypes.models import ContentType


class Migration(SchemaMigration):

    # Deleting content_types raises an error if guardian isn't yet installed.
    depends_on = (
        ('guardian', '0005_auto__chg_field_groupobjectpermission_object_pk__chg_field_userobjectp'),
    )

    def forwards(self, orm):
        "Drop django-celery tables."
        tables_to_drop = [
            'djcelery_taskstate',
            'djcelery_workerstate',
            'djcelery_periodictask',
            'djcelery_periodictasks',
            'djcelery_crontabschedule',
            'djcelery_intervalschedule',
            'celery_tasksetmeta',
            'celery_taskmeta',
        ]
        for table in tables_to_drop:
            if table in orm:
                db.delete_table(table)
        ContentType.objects.filter(app_label='djcelery').delete()

    def backwards(self, orm):
        raise RuntimeError('Cannot reverse this migration')

    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'containers': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'config': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dockerfile': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'default': "u'deis/buildstep'", 'max_length': '256'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'procfile': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'unique_together': "((u'app', u'type', u'num'), (u'formation', u'port'))", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Node']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "u'up'", 'max_length': '64'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.flavor': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Flavor'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'params': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Provider']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.formation': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Formation'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'nodes': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.layer': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Layer'},
            'config': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Flavor']"}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'proxy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'runtime': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ssh_port': ('django.db.models.fields.SmallIntegerField', [], {'default': '22'}),
            'ssh_private_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_public_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_username': ('django.db.models.fields.CharField', [], {'default': "u'ubuntu'", 'max_length': '64'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.node': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Node'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Layer']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'provider_id': ('django.db.models.fields.SlugField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'status': ('json_field.fields.JSONField', [], {'default': "u'null'", 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.provider': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Provider'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creds': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.SlugField', [], {'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']", 'null': 'True', 'blank': 'True'}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']

########NEW FILE########
__FILENAME__ = 0003_drop_socialaccount
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.conf import settings
from django.db import models
from django.contrib.auth.management import create_permissions
from django.contrib.contenttypes.models import ContentType


class Migration(DataMigration):

    depends_on = (
        ('guardian', '0005_auto__chg_field_groupobjectpermission_object_pk__chg_field_userobjectp'),
    )

    def forwards(self, orm):
        "Drop socialaccount tables."
        tables_to_drop = [
            'socialaccount_socialtoken',
            'socialaccount_socialaccount',
            'socialaccount_socialapp',
            'socialaccount_socialapp_sites',
        ]
        for table in tables_to_drop:
            if table in orm:
                db.delete_table(table)
        ContentType.objects.filter(app_label='socialaccount').delete()

    def backwards(self, orm):
        raise RuntimeError('Cannot reverse this migration')

    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'containers': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'config': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dockerfile': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'default': "u'deis/buildstep'", 'max_length': '256'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'procfile': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'unique_together': "((u'app', u'type', u'num'), (u'formation', u'port'))", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Node']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "u'up'", 'max_length': '64'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.flavor': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Flavor'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'params': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Provider']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.formation': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Formation'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'nodes': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.layer': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Layer'},
            'config': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Flavor']"}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'proxy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'runtime': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ssh_port': ('django.db.models.fields.SmallIntegerField', [], {'default': '22'}),
            'ssh_private_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_public_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_username': ('django.db.models.fields.CharField', [], {'default': "u'ubuntu'", 'max_length': '64'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.node': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Node'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Layer']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'provider_id': ('django.db.models.fields.SlugField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'status': ('json_field.fields.JSONField', [], {'default': "u'null'", 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.provider': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Provider'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creds': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.SlugField', [], {'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']", 'null': 'True', 'blank': 'True'}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['contenttypes', 'auth', 'api']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0004_add_custom_perms
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.conf import settings
from django.db import models
from django.contrib.auth.management import create_permissions


class Migration(DataMigration):

    def forwards(self, orm):
        "Create custom model permissions."
        create_permissions(models.get_app('api'), models.get_models(), 2 if settings.DEBUG else 0)

    def backwards(self, orm):
        raise RuntimeError('Cannot reverse this migration')


    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'containers': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'config': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dockerfile': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'default': "u'deis/buildstep'", 'max_length': '256'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'procfile': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'unique_together': "((u'app', u'type', u'num'), (u'formation', u'port'))", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Node']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "u'up'", 'max_length': '64'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.flavor': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Flavor'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'params': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Provider']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.formation': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Formation'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'nodes': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.layer': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Layer'},
            'config': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Flavor']"}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'proxy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'runtime': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ssh_port': ('django.db.models.fields.SmallIntegerField', [], {'default': '22'}),
            'ssh_private_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_public_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_username': ('django.db.models.fields.CharField', [], {'default': "u'ubuntu'", 'max_length': '64'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.node': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Node'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Layer']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'provider_id': ('django.db.models.fields.SlugField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'status': ('json_field.fields.JSONField', [], {'default': "u'null'", 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.provider': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Provider'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creds': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.SlugField', [], {'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']", 'null': 'True', 'blank': 'True'}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['contenttypes', 'auth', 'api']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0005_auto__add_push__add_unique_push_app_uuid
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Push'
        db.create_table(u'api_push', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.App'])),
            ('sha', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('fingerprint', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('receive_user', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('receive_repo', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('ssh_connection', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('ssh_original_command', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'api', ['Push'])

        # Adding unique constraint on 'Push', fields ['app', 'uuid']
        db.create_unique(u'api_push', ['app_id', 'uuid'])


    def backwards(self, orm):
        # Removing unique constraint on 'Push', fields ['app', 'uuid']
        db.delete_unique(u'api_push', ['app_id', 'uuid'])

        # Deleting model 'Push'
        db.delete_table(u'api_push')


    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'containers': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'config': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dockerfile': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'default': "u'deis/buildstep'", 'max_length': '256'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'procfile': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'unique_together': "((u'app', u'type', u'num'), (u'formation', u'port'))", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Node']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "u'up'", 'max_length': '64'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.flavor': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Flavor'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'params': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Provider']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.formation': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Formation'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'nodes': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.layer': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Layer'},
            'config': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Flavor']"}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'proxy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'runtime': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ssh_port': ('django.db.models.fields.SmallIntegerField', [], {'default': '22'}),
            'ssh_private_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_public_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_username': ('django.db.models.fields.CharField', [], {'default': "u'ubuntu'", 'max_length': '64'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.node': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Node'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Layer']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'provider_id': ('django.db.models.fields.SlugField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'status': ('json_field.fields.JSONField', [], {'default': "u'null'", 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.provider': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Provider'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creds': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.SlugField', [], {'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.push': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Push'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'receive_repo': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'receive_user': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'ssh_connection': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ssh_original_command': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']", 'null': 'True', 'blank': 'True'}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_release_summary
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Release.summary'
        db.add_column(u'api_release', 'summary',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Release.summary'
        db.delete_column(u'api_release', 'summary')


    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'containers': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'config': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dockerfile': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'default': "u'deis/slugbuilder'", 'max_length': '256'}),
            'output': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'procfile': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'unique_together': "((u'app', u'type', u'num'), (u'formation', u'port'))", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Node']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "u'up'", 'max_length': '64'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.flavor': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Flavor'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'params': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Provider']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.formation': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Formation'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'nodes': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.layer': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Layer'},
            'config': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Flavor']"}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'proxy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'runtime': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ssh_port': ('django.db.models.fields.SmallIntegerField', [], {'default': '22'}),
            'ssh_private_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_public_key': ('django.db.models.fields.TextField', [], {}),
            'ssh_username': ('django.db.models.fields.CharField', [], {'default': "u'ubuntu'", 'max_length': '64'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.node': {
            'Meta': {'unique_together': "((u'formation', u'id'),)", 'object_name': 'Node'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'formation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Formation']"}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Layer']"}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'provider_id': ('django.db.models.fields.SlugField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'status': ('json_field.fields.JSONField', [], {'default': "u'null'", 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.provider': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Provider'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creds': ('json_field.fields.JSONField', [], {'default': "u'null'", 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.SlugField', [], {'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.push': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Push'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'receive_repo': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'receive_user': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'ssh_connection': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ssh_original_command': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']", 'null': 'True', 'blank': 'True'}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'summary': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']
########NEW FILE########
__FILENAME__ = 0007_auto__del_flavor__del_unique_flavor_owner_id__del_layer__del_unique_la
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Container', fields ['formation', 'port']
        db.delete_unique(u'api_container', ['formation_id', 'port'])

        # Removing unique constraint on 'Container', fields ['app', 'type', 'num']
        db.delete_unique(u'api_container', ['app_id', 'type', 'num'])

        # Removing unique constraint on 'Config', fields ['app', 'version']
        db.delete_unique(u'api_config', ['app_id', 'version'])

        # Removing unique constraint on 'Formation', fields ['owner', 'id']
        db.delete_unique(u'api_formation', ['owner_id', 'id'])

        # Removing unique constraint on 'Node', fields ['formation', 'id']
        db.delete_unique(u'api_node', ['formation_id', 'id'])

        # Removing unique constraint on 'Provider', fields ['owner', 'id']
        db.delete_unique(u'api_provider', ['owner_id', 'id'])

        # Removing unique constraint on 'Layer', fields ['formation', 'id']
        db.delete_unique(u'api_layer', ['formation_id', 'id'])

        # Removing unique constraint on 'Flavor', fields ['owner', 'id']
        db.delete_unique(u'api_flavor', ['owner_id', 'id'])

        # Deleting model 'Flavor'
        db.delete_table(u'api_flavor')

        # Deleting model 'Layer'
        db.delete_table(u'api_layer')

        # Deleting model 'Provider'
        db.delete_table(u'api_provider')

        # Deleting model 'Node'
        db.delete_table(u'api_node')

        # Deleting model 'Formation'
        db.delete_table(u'api_formation')

        # Adding model 'Cluster'
        db.create_table(u'api_cluster', (
            ('uuid', self.gf('api.fields.UuidField')(unique=True, max_length=32, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('domain', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('hosts', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('auth', self.gf('django.db.models.fields.TextField')()),
            ('options', self.gf('json_field.fields.JSONField')(default=u'{}', blank=True)),
        ))
        db.send_create_signal(u'api', ['Cluster'])


        # Changing field 'Release.build'
        db.alter_column(u'api_release', 'build_id', self.gf('django.db.models.fields.related.ForeignKey')(default='5e5dba0d-a7fe-4019-b392-62b7b993f1a8', to=orm['api.Build']))
        # Deleting field 'Config.version'
        db.delete_column(u'api_config', 'version')

        # Adding unique constraint on 'Config', fields ['app', 'uuid']
        db.create_unique(u'api_config', ['app_id', 'uuid'])

        # Deleting field 'Container.node'
        db.delete_column(u'api_container', 'node_id')

        # Deleting field 'Container.status'
        db.delete_column(u'api_container', 'status')

        # Deleting field 'Container.formation'
        db.delete_column(u'api_container', 'formation_id')

        # Deleting field 'Container.port'
        db.delete_column(u'api_container', 'port')

        # Adding field 'Container.release'
        db.add_column(u'api_container', 'release',
                      self.gf('django.db.models.fields.related.ForeignKey')(default='5e5dba0d-a7fe-4019-b392-62b7b993f1a8', to=orm['api.Release']),
                      keep_default=False)

        # Adding field 'Container.state'
        db.add_column(u'api_container', 'state',
                      self.gf('django.db.models.fields.CharField')(default=u'initializing', max_length=64),
                      keep_default=False)

        # Deleting field 'Build.procfile'
        db.delete_column(u'api_build', 'procfile')

        # Deleting field 'Build.size'
        db.delete_column(u'api_build', 'size')

        # Deleting field 'Build.url'
        db.delete_column(u'api_build', 'url')

        # Deleting field 'Build.checksum'
        db.delete_column(u'api_build', 'checksum')

        # Deleting field 'Build.dockerfile'
        db.delete_column(u'api_build', 'dockerfile')

        # Deleting field 'Build.sha'
        db.delete_column(u'api_build', 'sha')

        # Deleting field 'Build.output'
        db.delete_column(u'api_build', 'output')

        # Deleting field 'Build.config'
        db.delete_column(u'api_build', 'config')

        # Deleting field 'App.formation'
        db.delete_column(u'api_app', 'formation_id')

        # Deleting field 'App.containers'
        db.delete_column(u'api_app', 'containers')

        # Adding field 'App.cluster'
        db.add_column(u'api_app', 'cluster',
                      self.gf('django.db.models.fields.related.ForeignKey')(default='5e5dba0d-a7fe-4019-b392-62b7b993f1a8', to=orm['api.Cluster']),
                      keep_default=False)

        # Adding field 'App.structure'
        db.add_column(u'api_app', 'structure',
                      self.gf('json_field.fields.JSONField')(default=u'{}', blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Removing unique constraint on 'Config', fields ['app', 'uuid']
        db.delete_unique(u'api_config', ['app_id', 'uuid'])

        # Adding model 'Flavor'
        db.create_table(u'api_flavor', (
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('params', self.gf('json_field.fields.JSONField')(default=u'null', blank=True)),
            ('uuid', self.gf('api.fields.UuidField')(max_length=32, unique=True, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('provider', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Provider'])),
            ('id', self.gf('django.db.models.fields.SlugField')(max_length=64)),
        ))
        db.send_create_signal(u'api', ['Flavor'])

        # Adding unique constraint on 'Flavor', fields ['owner', 'id']
        db.create_unique(u'api_flavor', ['owner_id', 'id'])

        # Adding model 'Layer'
        db.create_table(u'api_layer', (
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('ssh_port', self.gf('django.db.models.fields.SmallIntegerField')(default=22)),
            ('ssh_username', self.gf('django.db.models.fields.CharField')(default=u'ubuntu', max_length=64)),
            ('formation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Formation'])),
            ('proxy', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('flavor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Flavor'])),
            ('id', self.gf('django.db.models.fields.SlugField')(max_length=64)),
            ('uuid', self.gf('api.fields.UuidField')(max_length=32, unique=True, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('ssh_public_key', self.gf('django.db.models.fields.TextField')()),
            ('runtime', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('config', self.gf('json_field.fields.JSONField')(default=u'{}', blank=True)),
            ('ssh_private_key', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'api', ['Layer'])

        # Adding unique constraint on 'Layer', fields ['formation', 'id']
        db.create_unique(u'api_layer', ['formation_id', 'id'])

        # Adding model 'Provider'
        db.create_table(u'api_provider', (
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('uuid', self.gf('api.fields.UuidField')(max_length=32, unique=True, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('type', self.gf('django.db.models.fields.SlugField')(max_length=16)),
            ('id', self.gf('django.db.models.fields.SlugField')(max_length=64)),
            ('creds', self.gf('json_field.fields.JSONField')(default=u'null', blank=True)),
        ))
        db.send_create_signal(u'api', ['Provider'])

        # Adding unique constraint on 'Provider', fields ['owner', 'id']
        db.create_unique(u'api_provider', ['owner_id', 'id'])

        # Adding model 'Node'
        db.create_table(u'api_node', (
            ('status', self.gf('json_field.fields.JSONField')(default=u'null', null=True, blank=True)),
            ('layer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Layer'])),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('num', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('formation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Formation'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('uuid', self.gf('api.fields.UuidField')(max_length=32, unique=True, primary_key=True)),
            ('provider_id', self.gf('django.db.models.fields.SlugField')(max_length=64, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('fqdn', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
        ))
        db.send_create_signal(u'api', ['Node'])

        # Adding unique constraint on 'Node', fields ['formation', 'id']
        db.create_unique(u'api_node', ['formation_id', 'id'])

        # Adding model 'Formation'
        db.create_table(u'api_formation', (
            ('domain', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('uuid', self.gf('api.fields.UuidField')(max_length=32, unique=True, primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('nodes', self.gf('json_field.fields.JSONField')(default=u'{}', blank=True)),
            ('id', self.gf('django.db.models.fields.SlugField')(max_length=64, unique=True)),
        ))
        db.send_create_signal(u'api', ['Formation'])

        # Adding unique constraint on 'Formation', fields ['owner', 'id']
        db.create_unique(u'api_formation', ['owner_id', 'id'])

        # Deleting model 'Cluster'
        db.delete_table(u'api_cluster')


        # Changing field 'Release.build'
        db.alter_column(u'api_release', 'build_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Build'], null=True))

        # User chose to not deal with backwards NULL issues for 'Config.version'
        raise RuntimeError("Cannot reverse this migration. 'Config.version' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration        # Adding field 'Config.version'
        db.add_column(u'api_config', 'version',
                      self.gf('django.db.models.fields.PositiveIntegerField')(),
                      keep_default=False)

        # Adding unique constraint on 'Config', fields ['app', 'version']
        db.create_unique(u'api_config', ['app_id', 'version'])


        # User chose to not deal with backwards NULL issues for 'Container.node'
        raise RuntimeError("Cannot reverse this migration. 'Container.node' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration        # Adding field 'Container.node'
        db.add_column(u'api_container', 'node',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Node']),
                      keep_default=False)

        # Adding field 'Container.status'
        db.add_column(u'api_container', 'status',
                      self.gf('django.db.models.fields.CharField')(default=u'up', max_length=64),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Container.formation'
        raise RuntimeError("Cannot reverse this migration. 'Container.formation' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration        # Adding field 'Container.formation'
        db.add_column(u'api_container', 'formation',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Formation']),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Container.port'
        raise RuntimeError("Cannot reverse this migration. 'Container.port' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration        # Adding field 'Container.port'
        db.add_column(u'api_container', 'port',
                      self.gf('django.db.models.fields.PositiveIntegerField')(),
                      keep_default=False)

        # Deleting field 'Container.release'
        db.delete_column(u'api_container', 'release_id')

        # Deleting field 'Container.state'
        db.delete_column(u'api_container', 'state')

        # Adding unique constraint on 'Container', fields ['app', 'type', 'num']
        db.create_unique(u'api_container', ['app_id', 'type', 'num'])

        # Adding unique constraint on 'Container', fields ['formation', 'port']
        db.create_unique(u'api_container', ['formation_id', 'port'])

        # Adding field 'Build.procfile'
        db.add_column(u'api_build', 'procfile',
                      self.gf('json_field.fields.JSONField')(default=u'null', blank=True),
                      keep_default=False)

        # Adding field 'Build.size'
        db.add_column(u'api_build', 'size',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Build.url'
        raise RuntimeError("Cannot reverse this migration. 'Build.url' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration        # Adding field 'Build.url'
        db.add_column(u'api_build', 'url',
                      self.gf('django.db.models.fields.URLField')(max_length=200),
                      keep_default=False)

        # Adding field 'Build.checksum'
        db.add_column(u'api_build', 'checksum',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Build.dockerfile'
        db.add_column(u'api_build', 'dockerfile',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Build.sha'
        db.add_column(u'api_build', 'sha',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Build.output'
        db.add_column(u'api_build', 'output',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Build.config'
        db.add_column(u'api_build', 'config',
                      self.gf('json_field.fields.JSONField')(default=u'null', blank=True),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'App.formation'
        raise RuntimeError("Cannot reverse this migration. 'App.formation' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration        # Adding field 'App.formation'
        db.add_column(u'api_app', 'formation',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Formation']),
                      keep_default=False)

        # Adding field 'App.containers'
        db.add_column(u'api_app', 'containers',
                      self.gf('json_field.fields.JSONField')(default=u'{}', blank=True),
                      keep_default=False)

        # Deleting field 'App.cluster'
        db.delete_column(u'api_app', 'cluster_id')

        # Deleting field 'App.structure'
        db.delete_column(u'api_app', 'structure')


    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'cluster': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Cluster']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'structure': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.cluster': {
            'Meta': {'object_name': 'Cluster'},
            'auth': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'hosts': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'options': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Release']"}),
            'state': ('django.db.models.fields.CharField', [], {'default': "u'initializing'", 'max_length': '64'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.push': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Push'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'receive_repo': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'receive_user': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'ssh_connection': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ssh_original_command': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']"}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'summary': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']
########NEW FILE########
__FILENAME__ = 0008_auto__add_field_release_image
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Release.image'
        db.add_column(u'api_release', 'image',
                      self.gf('django.db.models.fields.CharField')(default='hi', max_length=256),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Release.image'
        db.delete_column(u'api_release', 'image')


    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'cluster': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Cluster']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'structure': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.cluster': {
            'Meta': {'object_name': 'Cluster'},
            'auth': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'hosts': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'options': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Release']"}),
            'state': ('django.db.models.fields.CharField', [], {'default': "u'initializing'", 'max_length': '64'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.push': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Push'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'receive_repo': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'receive_user': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'ssh_connection': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ssh_original_command': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']"}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'summary': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']
########NEW FILE########
__FILENAME__ = 0009_auto__chg_field_container_state
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Container.state'
        db.alter_column(u'api_container', 'state', self.gf('django_fsm.FSMField')(max_length=50))

    def backwards(self, orm):

        # Changing field 'Container.state'
        db.alter_column(u'api_container', 'state', self.gf('django.db.models.fields.CharField')(max_length=64))

    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'cluster': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Cluster']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'structure': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.cluster': {
            'Meta': {'object_name': 'Cluster'},
            'auth': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'hosts': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'options': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Release']"}),
            'state': ('django_fsm.FSMField', [], {'default': "u'initialized'", 'max_length': '50'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.push': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Push'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'receive_repo': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'receive_user': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'ssh_connection': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ssh_original_command': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']"}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'summary': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']

########NEW FILE########
__FILENAME__ = 0010_auto__add_field_build_sha__add_field_build_procfile__add_field_build_d
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Build.sha'
        db.add_column(u'api_build', 'sha',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=40, blank=True),
                      keep_default=False)

        # Adding field 'Build.procfile'
        db.add_column(u'api_build', 'procfile',
                      self.gf('json_field.fields.JSONField')(default=u'{}', blank=True),
                      keep_default=False)

        # Adding field 'Build.dockerfile'
        db.add_column(u'api_build', 'dockerfile',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Build.sha'
        db.delete_column(u'api_build', 'sha')

        # Deleting field 'Build.procfile'
        db.delete_column(u'api_build', 'procfile')

        # Deleting field 'Build.dockerfile'
        db.delete_column(u'api_build', 'dockerfile')


    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'cluster': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Cluster']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'structure': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dockerfile': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'procfile': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.cluster': {
            'Meta': {'object_name': 'Cluster'},
            'auth': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'hosts': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'options': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.CharField', [], {'default': "u'coreos'", 'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Release']"}),
            'state': ('django_fsm.FSMField', [], {'default': "u'initialized'", 'max_length': '50'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.push': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Push'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'receive_repo': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'receive_user': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'ssh_connection': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ssh_original_command': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']"}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'summary': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']


########NEW FILE########
__FILENAME__ = 0011_auto__add_domain
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Domain'
        db.create_table(u'api_domain', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.App'])),
            ('domain', self.gf('django.db.models.fields.TextField')(unique=True)),
        ))
        db.send_create_signal(u'api', ['Domain'])


    def backwards(self, orm):
        # Deleting model 'Domain'
        db.delete_table(u'api_domain')


    models = {
        u'api.app': {
            'Meta': {'object_name': 'App'},
            'cluster': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Cluster']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'structure': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.build': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.cluster': {
            'Meta': {'object_name': 'Cluster'},
            'auth': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'hosts': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'options': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'type': ('django.db.models.fields.CharField', [], {'default': "u'coreos'", 'max_length': '16'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.config': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Config'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'values': ('json_field.fields.JSONField', [], {'default': "u'{}'", 'blank': 'True'})
        },
        u'api.container': {
            'Meta': {'ordering': "[u'created']", 'object_name': 'Container'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Release']"}),
            'state': ('django_fsm.FSMField', [], {'default': "u'initialized'", 'max_length': '50'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.domain': {
            'Meta': {'object_name': 'Domain'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'api.key': {
            'Meta': {'unique_together': "((u'owner', u'id'),)", 'object_name': 'Key'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'public': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.push': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'uuid'),)", 'object_name': 'Push'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'receive_repo': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'receive_user': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'ssh_connection': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ssh_original_command': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'ordering': "[u'-created']", 'unique_together': "((u'app', u'version'),)", 'object_name': 'Release'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.App']"}),
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Build']"}),
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Config']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'summary': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('api.fields.UuidField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'version': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

"""
Data models for the Deis API.
"""

from __future__ import unicode_literals
import etcd
import importlib
import logging
import os
import subprocess

from celery.canvas import group
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models, connections
from django.db.models import Max
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.utils.encoding import python_2_unicode_compatible
from django_fsm import FSMField, transition
from django_fsm.signals import post_transition
from json_field.fields import JSONField

from api import fields, tasks
from registry import publish_release
from utils import dict_diff, fingerprint


logger = logging.getLogger(__name__)


def log_event(app, msg, level=logging.INFO):
    msg = "{}: {}".format(app.id, msg)
    logger.log(level, msg)


def close_db_connections(func, *args, **kwargs):
    """
    Decorator to close db connections during threaded execution

    Note this is necessary to work around:
    https://code.djangoproject.com/ticket/22420
    """
    def _inner(*args, **kwargs):
        func(*args, **kwargs)
        for conn in connections.all():
            conn.close()
    return _inner


class AuditedModel(models.Model):
    """Add created and updated fields to a model."""

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Mark :class:`AuditedModel` as abstract."""
        abstract = True


class UuidAuditedModel(AuditedModel):
    """Add a UUID primary key to an :class:`AuditedModel`."""

    uuid = fields.UuidField('UUID', primary_key=True)

    class Meta:
        """Mark :class:`UuidAuditedModel` as abstract."""
        abstract = True


@python_2_unicode_compatible
class Cluster(UuidAuditedModel):
    """
    Cluster used to run jobs
    """

    CLUSTER_TYPES = (('mock', 'Mock Cluster'),
                     ('coreos', 'CoreOS Cluster'),
                     ('faulty', 'Faulty Cluster'))

    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    id = models.CharField(max_length=128, unique=True)
    type = models.CharField(max_length=16, choices=CLUSTER_TYPES, default='coreos')

    domain = models.CharField(max_length=128)
    hosts = models.CharField(max_length=256)
    auth = models.TextField()
    options = JSONField(default='{}', blank=True)

    def __str__(self):
        return self.id

    def _get_scheduler(self, *args, **kwargs):
        module_name = 'scheduler.' + self.type
        mod = importlib.import_module(module_name)
        return mod.SchedulerClient(self.id, self.hosts, self.auth,
                                   self.domain, self.options)

    _scheduler = property(_get_scheduler)

    def create(self):
        """
        Initialize a cluster's router and log aggregator
        """
        return tasks.create_cluster.delay(self).get()

    def destroy(self):
        """
        Destroy a cluster's router and log aggregator
        """
        return tasks.destroy_cluster.delay(self).get()


@python_2_unicode_compatible
class App(UuidAuditedModel):
    """
    Application used to service requests on behalf of end-users
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    id = models.SlugField(max_length=64, unique=True)
    cluster = models.ForeignKey('Cluster')
    structure = JSONField(default='{}', blank=True)

    class Meta:
        permissions = (('use_app', 'Can use app'),)

    def __str__(self):
        return self.id

    def create(self, *args, **kwargs):
        config = Config.objects.create(owner=self.owner, app=self, values={})
        build = Build.objects.create(owner=self.owner, app=self, image=settings.DEFAULT_BUILD)
        Release.objects.create(version=1, owner=self.owner, app=self, config=config, build=build)

    def delete(self, *args, **kwargs):
        for c in self.container_set.all():
            c.destroy()
        return super(App, self).delete(*args, **kwargs)

    def deploy(self, release, initial=False):
        tasks.deploy_release.delay(self, release).get()
        if initial:
            # if there is no SHA, assume a docker image is being promoted
            if not release.build.sha:
                self.structure = {'cmd': 1}
            # if a dockerfile exists without a procfile, assume docker workflow
            elif release.build.dockerfile and not release.build.procfile:
                self.structure = {'cmd': 1}
            # if a procfile exists without a web entry, assume docker workflow
            elif release.build.procfile and not 'web' in release.build.procfile:
                self.structure = {'cmd': 1}
            # default to heroku workflow
            else:
                self.structure = {'web': 1}
            self.save()
            self.scale()

    def destroy(self, *args, **kwargs):
        return self.delete(*args, **kwargs)

    def scale(self, **kwargs):  # noqa
        """Scale containers up or down to match requested."""
        requested_containers = self.structure.copy()
        release = self.release_set.latest()
        # test for available process types
        available_process_types = release.build.procfile or {}
        for container_type in requested_containers.keys():
            if container_type == 'cmd':
                continue  # allow docker cmd types in case we don't have the image source
            if not container_type in available_process_types:
                raise EnvironmentError(
                    'Container type {} does not exist in application'.format(container_type))
        msg = 'Containers scaled ' + ' '.join(
            "{}={}".format(k, v) for k, v in requested_containers.items())
        # iterate and scale by container type (web, worker, etc)
        changed = False
        to_add, to_remove = [], []
        for container_type in requested_containers.keys():
            containers = list(self.container_set.filter(type=container_type).order_by('created'))
            # increment new container nums off the most recent container
            results = self.container_set.filter(type=container_type).aggregate(Max('num'))
            container_num = (results.get('num__max') or 0) + 1
            requested = requested_containers.pop(container_type)
            diff = requested - len(containers)
            if diff == 0:
                continue
            changed = True
            while diff < 0:
                c = containers.pop()
                to_remove.append(c)
                diff += 1
            while diff > 0:
                c = Container.objects.create(owner=self.owner,
                                             app=self,
                                             release=release,
                                             type=container_type,
                                             num=container_num)
                to_add.append(c)
                container_num += 1
                diff -= 1
        if changed:
            subtasks = []
            if to_add:
                subtasks.append(tasks.start_containers.s(to_add))
            if to_remove:
                subtasks.append(tasks.stop_containers.s(to_remove))
            group(*subtasks).apply_async().join()
            log_event(self, msg)
        return changed

    def logs(self):
        """Return aggregated log data for this application."""
        path = os.path.join(settings.DEIS_LOG_DIR, self.id + '.log')
        if not os.path.exists(path):
            raise EnvironmentError('Could not locate logs')
        data = subprocess.check_output(['tail', '-n', str(settings.LOG_LINES), path])
        return data

    def run(self, command):
        """Run a one-off command in an ephemeral app container."""
        # TODO: add support for interactive shell
        log_event(self, "deis run '{}'".format(command))
        c_num = max([c.num for c in self.container_set.filter(type='admin')] or [0]) + 1
        c = Container.objects.create(owner=self.owner,
                                     app=self,
                                     release=self.release_set.latest(),
                                     type='admin',
                                     num=c_num)
        rc, output = tasks.run_command.delay(c, command).get()
        return rc, output


@python_2_unicode_compatible
class Container(UuidAuditedModel):
    """
    Docker container used to securely host an application process.
    """
    INITIALIZED = 'initialized'
    CREATED = 'created'
    UP = 'up'
    DOWN = 'down'
    DESTROYED = 'destroyed'
    STATE_CHOICES = (
        (INITIALIZED, 'initialized'),
        (CREATED, 'created'),
        (UP, 'up'),
        (DOWN, 'down'),
        (DESTROYED, 'destroyed')
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    app = models.ForeignKey('App')
    release = models.ForeignKey('Release')
    type = models.CharField(max_length=128, blank=True)
    num = models.PositiveIntegerField()
    state = FSMField(default=INITIALIZED, choices=STATE_CHOICES, protected=True)

    def short_name(self):
        if self.type:
            return "{}.{}.{}".format(self.release.app.id, self.type, self.num)
        return "{}.{}".format(self.release.app.id, self.num)
    short_name.short_description = 'Name'

    def __str__(self):
        return self.short_name()

    class Meta:
        get_latest_by = '-created'
        ordering = ['created']

    def _get_job_id(self):
        app = self.app.id
        release = self.release
        version = "v{}".format(release.version)
        num = self.num
        c_type = self.type
        if not c_type:
            job_id = "{app}_{version}.{num}".format(**locals())
        else:
            job_id = "{app}_{version}.{c_type}.{num}".format(**locals())
        return job_id

    _job_id = property(_get_job_id)

    def _get_scheduler(self):
        return self.app.cluster._scheduler

    _scheduler = property(_get_scheduler)

    def _get_command(self):
        c_type = self.type
        if c_type:
            # handle special case for Dockerfile deployments
            if c_type == 'cmd':
                return ''
            else:
                return 'start {c_type}'
        else:
            return ''

    _command = property(_get_command)

    @close_db_connections
    @transition(field=state, source=INITIALIZED, target=CREATED)
    def create(self):
        image = self.release.image
        c_type = self.type
        self._scheduler.create(self._job_id, image, self._command.format(**locals()))

    @close_db_connections
    @transition(field=state,
                source=[CREATED, UP, DOWN],
                target=UP, crashed=DOWN)
    def start(self):
        self._scheduler.start(self._job_id)

    @close_db_connections
    @transition(field=state,
                source=[INITIALIZED, CREATED, UP, DOWN],
                target=UP,
                crashed=DOWN)
    def deploy(self, release):
        old_job_id = self._job_id
        # update release
        self.release = release
        self.save()
        # deploy new container
        new_job_id = self._job_id
        image = self.release.image
        c_type = self.type
        self._scheduler.create(new_job_id, image, self._command.format(**locals()))
        self._scheduler.start(new_job_id)
        # destroy old container
        self._scheduler.destroy(old_job_id)

    @close_db_connections
    @transition(field=state, source=UP, target=DOWN)
    def stop(self):
        self._scheduler.stop(self._job_id)

    @close_db_connections
    @transition(field=state,
                source=[INITIALIZED, CREATED, UP, DOWN],
                target=DESTROYED)
    def destroy(self):
        # TODO: add check for active connections before killing
        self._scheduler.destroy(self._job_id)

    @transition(field=state,
                source=[INITIALIZED, CREATED, DESTROYED],
                target=DESTROYED)
    def run(self, command):
        """Run a one-off command"""
        rc, output = self._scheduler.run(self._job_id, self.release.image, command)
        return rc, output


@python_2_unicode_compatible
class Push(UuidAuditedModel):
    """
    Instance of a push used to trigger an application build
    """
    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    app = models.ForeignKey('App')
    sha = models.CharField(max_length=40)

    fingerprint = models.CharField(max_length=255)
    receive_user = models.CharField(max_length=255)
    receive_repo = models.CharField(max_length=255)

    ssh_connection = models.CharField(max_length=255)
    ssh_original_command = models.CharField(max_length=255)

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']
        unique_together = (('app', 'uuid'),)

    def __str__(self):
        return "{0}-{1}".format(self.app.id, self.sha[:7])


@python_2_unicode_compatible
class Build(UuidAuditedModel):
    """
    Instance of a software build used by runtime nodes
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    app = models.ForeignKey('App')
    image = models.CharField(max_length=256)

    # optional fields populated by builder
    sha = models.CharField(max_length=40, blank=True)
    procfile = JSONField(default='{}', blank=True)
    dockerfile = models.TextField(blank=True)

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']
        unique_together = (('app', 'uuid'),)

    def __str__(self):
        return "{0}-{1}".format(self.app.id, self.uuid[:7])


@python_2_unicode_compatible
class Config(UuidAuditedModel):
    """
    Set of configuration values applied as environment variables
    during runtime execution of the Application.
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    app = models.ForeignKey('App')
    values = JSONField(default='{}', blank=True)

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']
        unique_together = (('app', 'uuid'),)

    def __str__(self):
        return "{}-{}".format(self.app.id, self.uuid[:7])


@python_2_unicode_compatible
class Release(UuidAuditedModel):
    """
    Software release deployed by the application platform

    Releases contain a :class:`Build` and a :class:`Config`.
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    app = models.ForeignKey('App')
    version = models.PositiveIntegerField()
    summary = models.TextField(blank=True, null=True)

    config = models.ForeignKey('Config')
    build = models.ForeignKey('Build')
    # NOTE: image contains combined build + config, ready to run
    image = models.CharField(max_length=256)

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']
        unique_together = (('app', 'version'),)

    def __str__(self):
        return "{0}-v{1}".format(self.app.id, self.version)

    def new(self, user, config=None, build=None, summary=None):
        """
        Create a new application release using the provided Build and Config
        on behalf of a user.

        Releases start at v1 and auto-increment.
        """
        if not config:
            config = self.config
        if not build:
            build = self.build
        # prepare release tag
        new_version = self.version + 1
        tag = 'v{}'.format(new_version)
        image = build.image + ':{tag}'.format(**locals())
        # create new release and auto-increment version
        release = Release.objects.create(
            owner=user, app=self.app, config=config,
            build=build, version=new_version, image=image, summary=summary)
        # publish release to registry as new docker image
        repository_path = self.app.id
        publish_release(repository_path, config.values, tag)
        return release

    def previous(self):
        """
        Return the previous Release to this one.

        :return: the previous :class:`Release`, or None
        """
        releases = self.app.release_set
        if self.pk:
            releases = releases.exclude(pk=self.pk)
        try:
            # Get the Release previous to this one
            prev_release = releases.latest()
        except Release.DoesNotExist:
            prev_release = None
        return prev_release

    def save(self, *args, **kwargs):
        if not self.summary:
            self.summary = ''
            prev_release = self.previous()
            # compare this build to the previous build
            old_build = prev_release.build if prev_release else None
            # if the build changed, log it and who pushed it
            if self.build != old_build:
                if self.build.sha:
                    self.summary += "{} deployed {}".format(self.build.owner, self.build.sha[:7])
                else:
                    self.summary += "{} deployed {}".format(self.build.owner, self.build.image)
            # compare this config to the previous config
            old_config = prev_release.config if prev_release else None
            # if the config data changed, log the dict diff
            if self.config != old_config:
                dict1 = self.config.values
                dict2 = old_config.values if old_config else {}
                diff = dict_diff(dict1, dict2)
                # try to be as succinct as possible
                added = ', '.join(k for k in diff.get('added', {}))
                added = 'added ' + added if added else ''
                changed = ', '.join(k for k in diff.get('changed', {}))
                changed = 'changed ' + changed if changed else ''
                deleted = ', '.join(k for k in diff.get('deleted', {}))
                deleted = 'deleted ' + deleted if deleted else ''
                changes = ', '.join(i for i in (added, changed, deleted) if i)
                if changes:
                    if self.summary:
                        self.summary += ' and '
                    self.summary += "{} {}".format(self.config.owner, changes)
                if not self.summary:
                    if self.version == 1:
                        self.summary = "{} created the initial release".format(self.owner)
                    else:
                        self.summary = "{} changed nothing".format(self.owner)
        super(Release, self).save(*args, **kwargs)


@python_2_unicode_compatible
class Domain(AuditedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    app = models.ForeignKey('App')
    domain = models.TextField(blank=False, null=False, unique=True)

    def __str__(self):
        return self.domain


@python_2_unicode_compatible
class Key(UuidAuditedModel):
    """An SSH public key."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    id = models.CharField(max_length=128)
    public = models.TextField(unique=True)

    class Meta:
        verbose_name = 'SSH Key'
        unique_together = (('owner', 'id'))

    def __str__(self):
        return "{}...{}".format(self.public[:18], self.public[-31:])


# define update/delete callbacks for synchronizing
# models with the configuration management backend

def _log_build_created(**kwargs):
    if kwargs.get('created'):
        build = kwargs['instance']
        log_event(build.app, "Build {} created".format(build))


def _log_release_created(**kwargs):
    if kwargs.get('created'):
        release = kwargs['instance']
        log_event(release.app, "Release {} created".format(release))


def _log_config_updated(**kwargs):
    config = kwargs['instance']
    log_event(config.app, "Config {} updated".format(config))


def _log_domain_added(**kwargs):
    domain = kwargs['instance']
    log_event(domain.app, "Domain {} added".format(domain))


def _log_domain_removed(**kwargs):
    domain = kwargs['instance']
    log_event(domain.app, "Domain {} removed".format(domain))


def _etcd_publish_key(**kwargs):
    key = kwargs['instance']
    _etcd_client.write('/deis/builder/users/{}/{}'.format(
        key.owner.username, fingerprint(key.public)), key.public)


def _etcd_purge_key(**kwargs):
    key = kwargs['instance']
    _etcd_client.delete('/deis/builder/users/{}/{}'.format(
        key.owner.username, fingerprint(key.public)))


def _etcd_purge_user(**kwargs):
    username = kwargs['instance'].username
    _etcd_client.delete('/deis/builder/users/{}'.format(username), dir=True, recursive=True)


def _etcd_publish_domains(**kwargs):
    app = kwargs['instance'].app
    app_domains = app.domain_set.all()
    if app_domains:
        _etcd_client.write('/deis/domains/{}'.format(app),
                           ' '.join(str(d.domain) for d in app_domains))
    else:
        _etcd_client.delete('/deis/domains/{}'.format(app))


# Log significant app-related events
post_save.connect(_log_build_created, sender=Build, dispatch_uid='api.models.log')
post_save.connect(_log_release_created, sender=Release, dispatch_uid='api.models.log')
post_save.connect(_log_config_updated, sender=Config, dispatch_uid='api.models.log')
post_save.connect(_log_domain_added, sender=Domain, dispatch_uid='api.models.log')
post_delete.connect(_log_domain_removed, sender=Domain, dispatch_uid='api.models.log')


# save FSM transitions as they happen
def _save_transition(**kwargs):
    kwargs['instance'].save()

post_transition.connect(_save_transition)

# wire up etcd publishing if we can connect
try:
    _etcd_client = etcd.Client(host=settings.ETCD_HOST, port=int(settings.ETCD_PORT))
    _etcd_client.get('/deis')
except etcd.EtcdException:
    logger.log(logging.WARNING, 'Cannot synchronize with etcd cluster')
    _etcd_client = None

if _etcd_client:
    post_save.connect(_etcd_publish_key, sender=Key, dispatch_uid='api.models')
    post_delete.connect(_etcd_purge_key, sender=Key, dispatch_uid='api.models')
    post_delete.connect(_etcd_purge_user, sender=User, dispatch_uid='api.models')
    post_save.connect(_etcd_publish_domains, sender=Domain, dispatch_uid='api.models')
    post_delete.connect(_etcd_publish_domains, sender=Domain, dispatch_uid='api.models')

########NEW FILE########
__FILENAME__ = routers
"""
REST framework URL routing classes.
"""

from __future__ import unicode_literals

from rest_framework.routers import DefaultRouter
from rest_framework.routers import Route


class ApiRouter(DefaultRouter):
    """Generate URL patterns for list, detail, and viewset-specific
    HTTP routes.
    """

    routes = [
        # List route.
        Route(
            url=r"^{prefix}/?$",
            mapping={
                'get': 'list',
                'post': 'create'
            },
            name="{basename}-list",
            initkwargs={'suffix': 'List'}
        ),
        # Detail route.
        Route(
            url=r"^{prefix}/{lookup}/?$",
            mapping={
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            name="{basename}-detail",
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamically generated routes, from @action or @link decorators
        # on methods of the viewset.
        Route(
            url=r"^{prefix}/{lookup}/{methodname}/?$",
            mapping={
                "{httpmethod}": "{methodname}",
            },
            name="{basename}-{methodnamehyphen}",
            initkwargs={}
        ),
    ]

########NEW FILE########
__FILENAME__ = serializers
"""
Classes to serialize the RESTful representation of Deis API models.
"""

from __future__ import unicode_literals

import re

from django.contrib.auth.models import User
from rest_framework import serializers

from api import models
from api import utils


class OwnerSlugRelatedField(serializers.SlugRelatedField):
    """Filter queries by owner as well as slug_field."""

    def from_native(self, data):
        """Fetch model object from its 'native' representation.
        TODO: request.user is not going to work in a team environment...
        """
        self.queryset = self.queryset.filter(owner=self.context['request'].user)
        return serializers.SlugRelatedField.from_native(self, data)


class UserSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.User` model."""

    class Meta:
        """Metadata options for a UserSerializer."""
        model = User
        read_only_fields = ('is_superuser', 'is_staff', 'groups',
                            'user_permissions', 'last_login', 'date_joined')

    @property
    def data(self):
        """Custom data property that removes secure user fields"""
        d = super(UserSerializer, self).data
        for f in ('password',):
            if f in d:
                del d[f]
        return d


class AdminUserSerializer(serializers.ModelSerializer):
    """Serialize admin status for a :class:`~api.models.User` model."""

    class Meta:
        model = User
        fields = ('username', 'is_superuser')
        read_only_fields = ('username',)


class ClusterSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.Cluster` model."""

    owner = serializers.Field(source='owner.username')

    class Meta:
        """Metadata options for a :class:`ClusterSerializer`."""
        model = models.Cluster
        read_only_fields = ('created', 'updated')


class PushSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.Push` model."""

    owner = serializers.Field(source='owner.username')
    app = serializers.SlugRelatedField(slug_field='id')

    class Meta:
        """Metadata options for a :class:`PushSerializer`."""
        model = models.Push
        read_only_fields = ('uuid', 'created', 'updated')


class BuildSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.Build` model."""

    owner = serializers.Field(source='owner.username')
    app = serializers.SlugRelatedField(slug_field='id')

    class Meta:
        """Metadata options for a :class:`BuildSerializer`."""
        model = models.Build
        read_only_fields = ('uuid', 'created', 'updated')


class ConfigSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.Config` model."""

    owner = serializers.Field(source='owner.username')
    app = serializers.SlugRelatedField(slug_field='id')
    values = serializers.ModelField(
        model_field=models.Config()._meta.get_field('values'), required=False)

    class Meta:
        """Metadata options for a :class:`ConfigSerializer`."""
        model = models.Config
        read_only_fields = ('uuid', 'created', 'updated')


class ReleaseSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.Release` model."""

    owner = serializers.Field(source='owner.username')
    app = serializers.SlugRelatedField(slug_field='id')
    config = serializers.SlugRelatedField(slug_field='uuid')
    build = serializers.SlugRelatedField(slug_field='uuid')

    class Meta:
        """Metadata options for a :class:`ReleaseSerializer`."""
        model = models.Release
        read_only_fields = ('uuid', 'created', 'updated')


class AppSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.App` model."""

    owner = serializers.Field(source='owner.username')
    id = serializers.SlugField(default=utils.generate_app_name)
    cluster = serializers.SlugRelatedField(slug_field='id')

    class Meta:
        """Metadata options for a :class:`AppSerializer`."""
        model = models.App
        read_only_fields = ('created', 'updated')

    def validate_id(self, attrs, source):
        """
        Check that the ID is all lowercase and not 'deis'
        """
        value = attrs[source]
        match = re.match(r'^[a-z0-9-]+$', value)
        if not match:
            raise serializers.ValidationError("App IDs can only contain [a-z0-9-]")
        if value == 'deis':
            raise serializers.ValidationError("App IDs cannot be 'deis'")
        return attrs


class ContainerSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.Container` model."""

    owner = serializers.Field(source='owner.username')
    app = OwnerSlugRelatedField(slug_field='id')
    release = serializers.SlugRelatedField(slug_field='uuid')

    class Meta:
        """Metadata options for a :class:`ContainerSerializer`."""
        model = models.Container
        read_only_fields = ('created', 'updated')

    def transform_release(self, obj, value):
        return "v{}".format(obj.release.version)


class KeySerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.Key` model."""

    owner = serializers.Field(source='owner.username')

    class Meta:
        """Metadata options for a KeySerializer."""
        model = models.Key
        read_only_fields = ('created', 'updated')


class DomainSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.Domain` model."""

    owner = serializers.Field(source='owner.username')
    app = serializers.SlugRelatedField(slug_field='id')

    class Meta:
        """Metadata options for a :class:`DomainSerializer`."""
        model = models.Domain
        fields = ('domain', 'owner', 'created', 'updated', 'app')
        read_only_fields = ('created', 'updated')

    def validate_domain(self, attrs, source):
        """
        Check that the hostname is valid
        """
        value = attrs[source]
        match = re.match(r'^(\*\.)?([a-z0-9-]+\.)*([a-z0-9-]+)\.([a-z0-9]{2,})$', value)
        if not match:
            raise serializers.ValidationError(
                "Hostname does not look like a valid hostname. "
                "Only lowercase characters are allowed.")

        if models.Domain.objects.filter(domain=value).exists():
            raise serializers.ValidationError(
                "The domain {} is already in use by another app".format(value))

        domain_parts = value.split('.')
        if domain_parts[0] == '*':
            raise serializers.ValidationError(
                "Adding a wildcard subdomain is currently not supported".format(value))

        return attrs

########NEW FILE########
__FILENAME__ = tasks
"""
Long-running tasks for the Deis Controller API

This module orchestrates the real "heavy lifting" of Deis, and as such these
functions are decorated to run as asynchronous celery tasks.
"""

from __future__ import unicode_literals

import threading

from celery import task


@task
def create_cluster(cluster):
    cluster._scheduler.setUp()


@task
def destroy_cluster(cluster):
    for app in cluster.app_set.all():
        app.destroy()
    cluster._scheduler.tearDown()


@task
def deploy_release(app, release):
    containers = app.container_set.all()
    threads = []
    for c in containers:
        threads.append(threading.Thread(target=c.deploy, args=(release,)))
    [t.start() for t in threads]
    [t.join() for t in threads]


@task
def start_containers(containers):
    create_threads = []
    start_threads = []
    for c in containers:
        create_threads.append(threading.Thread(target=c.create))
        start_threads.append(threading.Thread(target=c.start))
    [t.start() for t in create_threads]
    [t.join() for t in create_threads]
    [t.start() for t in start_threads]
    [t.join() for t in start_threads]


@task
def stop_containers(containers):
    destroy_threads = []
    delete_threads = []
    for c in containers:
        destroy_threads.append(threading.Thread(target=c.destroy))
        delete_threads.append(threading.Thread(target=c.delete))
    [t.start() for t in destroy_threads]
    [t.join() for t in destroy_threads]
    [t.start() for t in delete_threads]
    [t.join() for t in delete_threads]


@task
def run_command(c, command):
    release = c.release
    version = release.version
    image = release.image
    try:
        # pull the image first
        rc, pull_output = c.run("docker pull {image}".format(**locals()))
        if rc != 0:
            raise EnvironmentError('Could not pull image: {pull_image}'.format(**locals()))
        # run the command
        docker_args = ' '.join(['-a', 'stdout', '-a', 'stderr', '--rm', image])
        env_args = ' '.join(["-e '{k}={v}'".format(**locals())
                             for k, v in release.config.values.items()])
        command = "docker run {env_args} {docker_args} {command}".format(**locals())
        return c.run(command)
    finally:
        c.delete()

########NEW FILE########
__FILENAME__ = test_app
"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""

from __future__ import unicode_literals

import json
import os.path

from django.test import TestCase
from django.test.utils import override_settings

from django.conf import settings


@override_settings(CELERY_ALWAYS_EAGER=True)
class AppTest(TestCase):

    """Tests creation of applications"""

    fixtures = ['tests.json']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='autotest', password='password'))
        body = {'id': 'autotest', 'domain': 'autotest.local', 'type': 'mock',
                'hosts': 'host1,host2', 'auth': 'base64string', 'options': {}}
        response = self.client.post('/api/clusters', json.dumps(body),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_app(self):
        """
        Test that a user can create, read, update and delete an application
        """
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']  # noqa
        self.assertIn('cluster', response.data)
        self.assertIn('id', response.data)
        response = self.client.get('/api/apps')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        url = '/api/apps/{app_id}'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        body = {'id': 'new'}
        response = self.client.patch(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 405)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

    def test_app_override_id(self):
        body = {'cluster': 'autotest', 'id': 'myid'}
        response = self.client.post('/api/apps', json.dumps(body),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        body = {'cluster': response.data['cluster'], 'id': response.data['id']}
        response = self.client.post('/api/apps', json.dumps(body),
                                    content_type='application/json')
        self.assertContains(response, 'App with this Id already exists.', status_code=400)
        return response

    def test_app_actions(self):
        url = '/api/apps'
        body = {'cluster': 'autotest', 'id': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']  # noqa
        # test logs
        if not os.path.exists(settings.DEIS_LOG_DIR):
            os.mkdir(settings.DEIS_LOG_DIR)
        path = os.path.join(settings.DEIS_LOG_DIR, app_id + '.log')
        if os.path.exists(path):
            os.remove(path)
        url = '/api/apps/{app_id}/logs'.format(**locals())
        response = self.client.post(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, 'No logs for {}'.format(app_id))
        # write out some fake log data and try again
        with open(path, 'w') as f:
            f.write(FAKE_LOG_DATA)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, FAKE_LOG_DATA)
        # test run
        url = '/api/apps/{app_id}/run'.format(**locals())
        body = {'command': 'ls -al'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0], 0)

    def test_app_errors(self):
        cluster_id, app_id = 'autotest', 'autotest-errors'
        url = '/api/apps'
        body = {'cluster': cluster_id, 'id': 'camelCase'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertContains(response, 'App IDs can only contain [a-z0-9-]', status_code=400)
        url = '/api/apps'
        body = {'cluster': cluster_id, 'id': 'deis'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertContains(response, "App IDs cannot be 'deis'", status_code=400)
        body = {'cluster': cluster_id, 'id': app_id}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']  # noqa
        url = '/api/apps/{app_id}'.format(**locals())
        response = self.client.delete(url)
        self.assertEquals(response.status_code, 204)
        for endpoint in ('containers', 'config', 'releases', 'builds'):
            url = '/api/apps/{app_id}/{endpoint}'.format(**locals())
            response = self.client.get(url)
            self.assertEquals(response.status_code, 404)


FAKE_LOG_DATA = """
2013-08-15 12:41:25 [33454] [INFO] Starting gunicorn 17.5
2013-08-15 12:41:25 [33454] [INFO] Listening at: http://0.0.0.0:5000 (33454)
2013-08-15 12:41:25 [33454] [INFO] Using worker: sync
2013-08-15 12:41:25 [33457] [INFO] Booting worker with pid 33457
"""

########NEW FILE########
__FILENAME__ = test_auth
"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""

from __future__ import unicode_literals

import json
import urllib

from django.test import TestCase
from django.test.utils import override_settings


class AuthTest(TestCase):

    fixtures = ['test_auth.json']

    """Tests user registration, authentication and authorization"""

    def test_auth(self):
        """
        Test that a user can register using the API, login and logout
        """
        # make sure logging in with an invalid username/password
        # results in a 200 login page
        url = '/api/auth/login/'
        body = {'username': 'fail', 'password': 'this'}
        response = self.client.post(url, data=json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        # test registration workflow
        username, password = 'newuser', 'password'
        first_name, last_name = 'Otto', 'Test'
        email = 'autotest@deis.io'
        submit = {
            'username': username,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            # try to abuse superuser/staff level perms (not the first signup!)
            'is_superuser': True,
            'is_staff': True,
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['username'], username)
        self.assertNotIn('password', response.data)
        self.assertEqual(response.data['email'], email)
        self.assertEqual(response.data['first_name'], first_name)
        self.assertEqual(response.data['last_name'], last_name)
        self.assertTrue(response.data['is_active'])
        self.assertFalse(response.data['is_superuser'])
        self.assertFalse(response.data['is_staff'])
        self.assertTrue(
            self.client.login(username=username, password=password))
        # test logout and login
        url = '/api/auth/logout/'
        response = self.client.post(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        url = '/api/auth/login/'
        payload = urllib.urlencode({'username': username, 'password': password})
        response = self.client.post(url, data=payload,
                                    content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 302)

    @override_settings(REGISTRATION_ENABLED=False)
    def test_auth_registration_disabled(self):
        """test that a new user cannot register when registration is disabled."""
        url = '/api/auth/register'
        submit = {
            'username': 'testuser',
            'password': 'password',
            'first_name': 'test',
            'last_name': 'user',
            'email': 'test@user.com',
            'is_superuser': False,
            'is_staff': False,
        }
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_cancel(self):
        """Test that a registered user can cancel her account."""
        # test registration workflow
        username, password = 'newuser', 'password'
        first_name, last_name = 'Otto', 'Test'
        email = 'autotest@deis.io'
        submit = {
            'username': username,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            # try to abuse superuser/staff level perms
            'is_superuser': True,
            'is_staff': True,
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            self.client.login(username=username, password=password))
        # cancel the account
        url = '/api/auth/cancel'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            self.client.login(username=username, password=password))

########NEW FILE########
__FILENAME__ = test_build
"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""

from __future__ import unicode_literals

import json

from django.test import TransactionTestCase
from django.test.utils import override_settings

from api.models import Build


@override_settings(CELERY_ALWAYS_EAGER=True)
class BuildTest(TransactionTestCase):

    """Tests build notification from build system"""

    fixtures = ['tests.json']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='autotest', password='password'))
        body = {'id': 'autotest', 'domain': 'autotest.local', 'type': 'mock',
                'hosts': 'host1,host2', 'auth': 'base64string', 'options': {}}
        response = self.client.post('/api/clusters', json.dumps(body),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_build(self):
        """
        Test that a null build is created and that users can post new builds
        """
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # check to see that an initial build was created
        url = "/api/apps/{app_id}/builds".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        # post a new build
        body = {'image': 'autotest/example'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        build_id = response.data['uuid']
        build1 = response.data
        self.assertEqual(response.data['image'], body['image'])
        # read the build
        url = "/api/apps/{app_id}/builds/{build_id}".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        build2 = response.data
        self.assertEqual(build1, build2)
        # post a new build
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('x-deis-release', response._headers)
        build3 = response.data
        self.assertEqual(response.data['image'], body['image'])
        self.assertNotEqual(build2['uuid'], build3['uuid'])
        # disallow put/patch/delete
        self.assertEqual(self.client.put(url).status_code, 405)
        self.assertEqual(self.client.patch(url).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_build_default_containers(self):
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # post an image as a build
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = "/api/apps/{app_id}/containers/cmd".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        container = response.data['results'][0]
        self.assertEqual(container['type'], 'cmd')
        self.assertEqual(container['num'], 1)
        # start with a new app
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # post a new build with procfile
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example',
                'sha': 'a'*40,
                'dockerfile': "FROM scratch"}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = "/api/apps/{app_id}/containers/cmd".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        container = response.data['results'][0]
        self.assertEqual(container['type'], 'cmd')
        self.assertEqual(container['num'], 1)
        # start with a new app
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # post a new build with procfile
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example',
                'sha': 'a'*40,
                'dockerfile': "FROM scratch",
                'procfile': {'worker': 'node worker.js'}}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = "/api/apps/{app_id}/containers/cmd".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        container = response.data['results'][0]
        self.assertEqual(container['type'], 'cmd')
        self.assertEqual(container['num'], 1)
        # start with a new app
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # post a new build with procfile
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example',
                'sha': 'a'*40,
                'procfile': json.dumps({'web': 'node server.js',
                                        'worker': 'node worker.js'})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = "/api/apps/{app_id}/containers/web".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        container = response.data['results'][0]
        self.assertEqual(container['type'], 'web')
        self.assertEqual(container['num'], 1)

    def test_build_str(self):
        """Test the text representation of a build."""
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # post a new build
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        build = Build.objects.get(uuid=response.data['uuid'])
        self.assertEqual(str(build), "{}-{}".format(
                         response.data['app'], response.data['uuid'][:7]))

########NEW FILE########
__FILENAME__ = test_cluster
"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""

from __future__ import unicode_literals

import json

from django.test import TestCase
from django.test.utils import override_settings


@override_settings(CELERY_ALWAYS_EAGER=True)
class ClusterTest(TestCase):

    """Tests cluster management"""

    fixtures = ['tests.json']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='autotest', password='password'))

    def test_cluster(self):
        """
        Test that an administrator can create, read, update and delete a cluster
        """
        url = '/api/clusters'
        options = {'key': 'val'}
        body = {'id': 'autotest', 'domain': 'autotest.local', 'type': 'mock',
                'hosts': 'host1,host2', 'auth': 'base64string', 'options': options}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        cluster_id = response.data['id']  # noqa
        self.assertIn('owner', response.data)
        self.assertIn('id', response.data)
        self.assertIn('domain', response.data)
        self.assertIn('hosts', response.data)
        self.assertIn('auth', response.data)
        self.assertIn('options', response.data)
        self.assertEqual(response.data['hosts'], 'host1,host2')
        self.assertEqual(json.loads(response.data['options']), {'key': 'val'})
        response = self.client.get('/api/clusters')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        # ensure we can delete the cluster with an app
        # see https://github.com/deis/deis/issues/927
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = '/api/clusters/{cluster_id}'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        new_hosts, new_options = 'host2,host3', {'key': 'val2'}
        body = {'hosts': new_hosts, 'options': new_options}
        response = self.client.patch(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['hosts'], new_hosts)
        self.assertEqual(json.loads(response.data['options']), new_options)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

    def test_cluster_perms_denied(self):
        """
        Test that a user cannot make changes to a cluster
        """
        url = '/api/clusters'
        options = {'key': 'val'}
        self.client.login(username='autotest2', password='password')
        body = {'id': 'autotest2', 'domain': 'autotest.local', 'type': 'mock',
                'hosts': 'host1,host2', 'auth': 'base64string', 'options': options}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 403)

########NEW FILE########
__FILENAME__ = test_config
"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""

from __future__ import unicode_literals

import json

from django.test import TransactionTestCase
from django.test.utils import override_settings

from api.models import Config


@override_settings(CELERY_ALWAYS_EAGER=True)
class ConfigTest(TransactionTestCase):

    """Tests setting and updating config values"""

    fixtures = ['tests.json']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='autotest', password='password'))
        body = {'id': 'autotest', 'domain': 'autotest.local', 'type': 'mock',
                'hosts': 'host1,host2', 'auth': 'base64string', 'options': {}}
        response = self.client.post('/api/clusters', json.dumps(body),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_config(self):
        """
        Test that config is auto-created for a new app and that
        config can be updated using a PATCH
        """
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # check to see that an initial/empty config was created
        url = "/api/apps/{app_id}/config".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('values', response.data)
        self.assertEqual(response.data['values'], json.dumps({}))
        config1 = response.data
        # set an initial config value
        body = {'values': json.dumps({'NEW_URL1': 'http://localhost:8080/'})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('x-deis-release', response._headers)
        config2 = response.data
        self.assertNotEqual(config1['uuid'], config2['uuid'])
        self.assertIn('NEW_URL1', json.loads(response.data['values']))
        # read the config
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        config3 = response.data
        self.assertEqual(config2, config3)
        self.assertIn('NEW_URL1', json.loads(response.data['values']))
        # set an additional config value
        body = {'values': json.dumps({'NEW_URL2': 'http://localhost:8080/'})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        config3 = response.data
        self.assertNotEqual(config2['uuid'], config3['uuid'])
        self.assertIn('NEW_URL1', json.loads(response.data['values']))
        self.assertIn('NEW_URL2', json.loads(response.data['values']))
        # read the config again
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        config4 = response.data
        self.assertEqual(config3, config4)
        self.assertIn('NEW_URL1', json.loads(response.data['values']))
        self.assertIn('NEW_URL2', json.loads(response.data['values']))
        # unset a config value
        body = {'values': json.dumps({'NEW_URL2': None})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        config5 = response.data
        self.assertNotEqual(config4['uuid'], config5['uuid'])
        self.assertNotIn('NEW_URL2', json.dumps(response.data['values']))
        # unset all config values
        body = {'values': json.dumps({'NEW_URL1': None})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('NEW_URL1', json.dumps(response.data['values']))
        # disallow put/patch/delete
        self.assertEqual(self.client.put(url).status_code, 405)
        self.assertEqual(self.client.patch(url).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        return config5

    def test_config_set_same_key(self):
        """
        Test that config sets on the same key function properly
        """
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        url = "/api/apps/{app_id}/config".format(**locals())
        # set an initial config value
        body = {'values': json.dumps({'PORT': '5000'})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('PORT', json.loads(response.data['values']))
        # reset same config value
        body = {'values': json.dumps({'PORT': '5001'})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('PORT', json.loads(response.data['values']))
        self.assertEqual(json.loads(response.data['values'])['PORT'], '5001')

    def test_config_str(self):
        """Test the text representation of a node."""
        config5 = self.test_config()
        config = Config.objects.get(uuid=config5['uuid'])
        self.assertEqual(str(config), "{}-{}".format(config5['app'], config5['uuid'][:7]))

########NEW FILE########
__FILENAME__ = test_container
"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""

from __future__ import unicode_literals

import json

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.test.utils import override_settings

from django_fsm import TransitionNotAllowed

from api.models import Container, App


@override_settings(CELERY_ALWAYS_EAGER=True)
class ContainerTest(TransactionTestCase):

    """Tests creation of containers on nodes"""

    fixtures = ['tests.json']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='autotest', password='password'))
        body = {'id': 'autotest', 'domain': 'autotest.local', 'type': 'mock',
                'hosts': 'host1,host2', 'auth': 'base64string', 'options': {}}
        response = self.client.post('/api/clusters', json.dumps(body),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # create a malicious scheduler as well
        body['id'] = 'autotest2'
        body['type'] = 'faulty'
        response = self.client.post('/api/clusters', json.dumps(body),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_container_state_good(self):
        """Test that the finite state machine transitions with a good scheduler"""
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # create a container
        c = Container.objects.create(owner=User.objects.get(username='autotest'),
                                     app=App.objects.get(id=app_id),
                                     release=App.objects.get(id=app_id).release_set.latest(),
                                     type='web',
                                     num=1)
        self.assertEqual(c.state, 'initialized')
        # test an illegal transition
        self.assertRaises(TransitionNotAllowed, lambda: c.start())
        c.create()
        self.assertEqual(c.state, 'created')
        c.start()
        self.assertEqual(c.state, 'up')
        c.deploy(App.objects.get(id=app_id).release_set.latest())
        self.assertEqual(c.state, 'up')
        c.destroy()
        self.assertEqual(c.state, 'destroyed')

    def test_container_state_bad(self):
        """Test that the finite state machine transitions with a faulty scheduler"""
        url = '/api/apps'
        body = {'cluster': 'autotest2'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # create a container
        c = Container.objects.create(owner=User.objects.get(username='autotest'),
                                     app=App.objects.get(id=app_id),
                                     release=App.objects.get(id=app_id).release_set.latest(),
                                     type='web',
                                     num=1)
        self.assertEqual(c.state, 'initialized')
        self.assertRaises(Exception, lambda: c.create())
        self.assertEqual(c.state, 'initialized')
        # test an illegal transition
        self.assertRaises(TransitionNotAllowed, lambda: c.start())
        self.assertEqual(c.state, 'initialized')
        self.assertRaises(
            Exception,
            lambda: c.deploy(
                App.objects.get(id=app_id).release_set.latest()
            )
        )
        self.assertEqual(c.state, 'down')
        self.assertRaises(Exception, lambda: c.destroy())
        self.assertEqual(c.state, 'down')
        self.assertRaises(Exception, lambda: c.run('echo hello world'))
        self.assertEqual(c.state, 'down')

    def test_container_state_protected(self):
        """Test that you cannot directly modify the state"""
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        c = Container.objects.create(owner=User.objects.get(username='autotest'),
                                     app=App.objects.get(id=app_id),
                                     release=App.objects.get(id=app_id).release_set.latest(),
                                     type='web',
                                     num=1)
        self.assertRaises(AttributeError, lambda: setattr(c, 'state', 'up'))

    def test_container_api_heroku(self):
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # should start with zero
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        # post a new build
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example', 'sha': 'a'*40,
                'procfile': json.dumps({'web': 'node server.js', 'worker': 'node worker.js'})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # scale up
        url = "/api/apps/{app_id}/scale".format(**locals())
        body = {'web': 4, 'worker': 2}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 204)
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 6)
        url = "/api/apps/{app_id}".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # test listing/retrieving container info
        url = "/api/apps/{app_id}/containers/web".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 4)
        num = response.data['results'][0]['num']
        url = "/api/apps/{app_id}/containers/web/{num}".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['num'], num)
        # scale down
        url = "/api/apps/{app_id}/scale".format(**locals())
        body = {'web': 2, 'worker': 1}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 204)
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(max(c['num'] for c in response.data['results']), 2)
        url = "/api/apps/{app_id}".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # scale down to 0
        url = "/api/apps/{app_id}/scale".format(**locals())
        body = {'web': 0, 'worker': 0}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 204)
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        url = "/api/apps/{app_id}".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_container_api_docker(self):
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # should start with zero
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        # post a new build
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example', 'dockerfile': "FROM busybox\nCMD /bin/true"}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # scale up
        url = "/api/apps/{app_id}/scale".format(**locals())
        body = {'cmd': 6}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 204)
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 6)
        url = "/api/apps/{app_id}".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # test listing/retrieving container info
        url = "/api/apps/{app_id}/containers/cmd".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 6)
        # scale down
        url = "/api/apps/{app_id}/scale".format(**locals())
        body = {'cmd': 3}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 204)
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(max(c['num'] for c in response.data['results']), 3)
        url = "/api/apps/{app_id}".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # scale down to 0
        url = "/api/apps/{app_id}/scale".format(**locals())
        body = {'cmd': 0}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 204)
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        url = "/api/apps/{app_id}".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_container_release(self):
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # should start with zero
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        # post a new build
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example', 'sha': 'a'*40,
                'procfile': json.dumps({'web': 'node server.js', 'worker': 'node worker.js'})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # scale up
        url = "/api/apps/{app_id}/scale".format(**locals())
        body = {'web': 1}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 204)
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['release'], 'v2')
        # post a new build
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['image'], body['image'])
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['release'], 'v3')
        # post new config
        url = "/api/apps/{app_id}/config".format(**locals())
        body = {'values': json.dumps({'KEY': 'value'})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['release'], 'v4')

    def test_container_errors(self):
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        url = "/api/apps/{app_id}/scale".format(**locals())
        body = {'web': 'not_an_int'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertContains(response, 'Invalid scaling format', status_code=400)
        body = {'invalid': 1}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertContains(response, 'Container type invalid', status_code=400)

    def test_container_str(self):
        """Test the text representation of a container."""
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # post a new build
        url = "/api/apps/{app_id}/builds".format(**locals())
        body = {'image': 'autotest/example', 'sha': 'a'*40,
                'procfile': json.dumps({'web': 'node server.js', 'worker': 'node worker.js'})}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # scale up
        url = "/api/apps/{app_id}/scale".format(**locals())
        body = {'web': 4, 'worker': 2}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 204)
        # should start with zero
        url = "/api/apps/{app_id}/containers".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 6)
        uuid = response.data['results'][0]['uuid']
        container = Container.objects.get(uuid=uuid)
        self.assertEqual(container.short_name(),
                         "{}.{}.{}".format(container.app, container.type, container.num))
        self.assertEqual(str(container),
                         "{}.{}.{}".format(container.app, container.type, container.num))

########NEW FILE########
__FILENAME__ = test_domain
"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""

from __future__ import unicode_literals

import json

from django.test import TestCase
from django.test.utils import override_settings


@override_settings(CELERY_ALWAYS_EAGER=True)
class DomainTest(TestCase):

    """Tests creation of domains"""

    fixtures = ['tests.json']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='autotest', password='password'))
        body = {
            'id': 'autotest',
            'domain': 'autotest.local',
            'type': 'mock',
            'hosts': 'host1,host2',
            'auth': 'base64string',
            'options': {},
        }
        response = self.client.post('/api/clusters', json.dumps(body),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.app_id = response.data['id']  # noqa

    def test_manage_domain(self):
        url = '/api/apps/{app_id}/domains'.format(app_id=self.app_id)
        body = {'domain': 'test-domain.example.com'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = '/api/apps/{app_id}/domains'.format(app_id=self.app_id)
        response = self.client.get(url, content_type='application/json')
        result = response.data['results'][0]
        self.assertEqual('test-domain.example.com', result['domain'])
        url = '/api/apps/{app_id}/domains/{hostname}'.format(hostname='test-domain.example.com',
                                                             app_id=self.app_id)
        response = self.client.delete(url, content_type='application/json')
        self.assertEqual(response.status_code, 204)
        url = '/api/apps/{app_id}/domains'.format(app_id=self.app_id)
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(0, response.data['count'])

    def test_manage_domain_invalid_app(self):
        url = '/api/apps/{app_id}/domains'.format(app_id="this-app-does-not-exist")
        body = {'domain': 'test-domain.example.com'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 404)
        url = '/api/apps/{app_id}/domains'.format(app_id='this-app-does-not-exist')
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_manage_domain_perms_on_app(self):
        self.client.logout()
        self.assertTrue(
            self.client.login(username='autotest2', password='password'))
        url = '/api/apps/{app_id}/domains'.format(app_id=self.app_id)
        body = {'domain': 'test-domain2.example.com'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_manage_domain_invalid_domain(self):
        url = '/api/apps/{app_id}/domains'.format(app_id=self.app_id)
        body = {'domain': 'this_is_an.invalid.domain'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        url = '/api/apps/{app_id}/domains'.format(app_id=self.app_id)
        body = {'domain': 'this-is-an.invalid.a'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        url = '/api/apps/{app_id}/domains'.format(app_id=self.app_id)
        body = {'domain': 'domain'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_manage_domain_wildcard(self):
        # Wildcards are not allowed for now.
        url = '/api/apps/{app_id}/domains'.format(app_id=self.app_id)
        body = {'domain': '*.deis.example.com'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 400)

########NEW FILE########
__FILENAME__ = test_hooks
"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""

from __future__ import unicode_literals

import json

from django.test import TransactionTestCase
from django.test.utils import override_settings

from django.conf import settings


@override_settings(CELERY_ALWAYS_EAGER=True)
class HookTest(TransactionTestCase):

    """Tests API hooks used to trigger actions from external components"""

    fixtures = ['tests.json']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='autotest', password='password'))
        body = {'id': 'autotest', 'domain': 'autotest.local', 'type': 'mock',
                'hosts': 'host1,host2', 'auth': 'base64string', 'options': {}}
        response = self.client.post('/api/clusters', json.dumps(body),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_push_hook(self):
        """Test creating a Push via the API"""
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # prepare a push body
        body = {
            'sha': 'df1e628f2244b73f9cdf944f880a2b3470a122f4',
            'fingerprint': '88:25:ed:67:56:91:3d:c6:1b:7f:42:c6:9b:41:24:80',
            'receive_user': 'autotest',
            'receive_repo': '{app_id}'.format(**locals()),
            'ssh_connection': '10.0.1.10 50337 172.17.0.143 22',
            'ssh_original_command': "git-receive-pack '{app_id}.git'".format(**locals()),
        }
        # post a request without the auth header
        url = "/api/hooks/push".format(**locals())
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        # now try with the builder key in the special auth header
        response = self.client.post(url, json.dumps(body), content_type='application/json',
                                    HTTP_X_DEIS_BUILDER_AUTH=settings.BUILDER_KEY)
        self.assertEqual(response.status_code, 201)
        for k in ('owner', 'app', 'sha', 'fingerprint', 'receive_repo', 'receive_user',
                  'ssh_connection', 'ssh_original_command'):
            self.assertIn(k, response.data)

    def test_push_abuse(self):
        """Test a user pushing to an unauthorized application"""
        # create a legit app as "autotest"
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # register an evil user
        username, password = 'eviluser', 'password'
        first_name, last_name = 'Evil', 'User'
        email = 'evil@deis.io'
        submit = {
            'username': username,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # prepare a push body that simulates a git push
        body = {
            'sha': 'df1e628f2244b73f9cdf944f880a2b3470a122f4',
            'fingerprint': '88:25:ed:67:56:91:3d:c6:1b:7f:42:c6:9b:41:24:99',
            'receive_user': 'eviluser',
            'receive_repo': '{app_id}'.format(**locals()),
            'ssh_connection': '10.0.1.10 50337 172.17.0.143 22',
            'ssh_original_command': "git-receive-pack '{app_id}.git'".format(**locals()),
        }
        # try to push as "eviluser"
        url = "/api/hooks/push".format(**locals())
        response = self.client.post(url, json.dumps(body), content_type='application/json',
                                    HTTP_X_DEIS_BUILDER_AUTH=settings.BUILDER_KEY)
        self.assertEqual(response.status_code, 403)

    def test_build_hook(self):
        """Test creating a Build via an API Hook"""
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        build = {'username': 'autotest', 'app': app_id}
        url = '/api/hooks/builds'.format(**locals())
        body = {'receive_user': 'autotest',
                'receive_repo': app_id,
                'image': 'registry.local:5000/{app_id}:v2'.format(**locals())}
        # post the build without a session
        self.assertIsNone(self.client.logout())
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        # post the build with the builder auth key
        response = self.client.post(url, json.dumps(body), content_type='application/json',
                                    HTTP_X_DEIS_BUILDER_AUTH=settings.BUILDER_KEY)
        self.assertEqual(response.status_code, 200)
        self.assertIn('release', response.data)
        self.assertIn('version', response.data['release'])
        self.assertIn('domains', response.data)

    def test_build_hook_procfile(self):
        """Test creating a Procfile build via an API Hook"""
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        build = {'username': 'autotest', 'app': app_id}
        url = '/api/hooks/builds'.format(**locals())
        PROCFILE = {'web': 'node server.js', 'worker': 'node worker.js'}
        SHA = 'ecdff91c57a0b9ab82e89634df87e293d259a3aa'
        body = {'receive_user': 'autotest',
                'receive_repo': app_id,
                'image': 'registry.local:5000/{app_id}:v2'.format(**locals()),
                'sha': SHA,
                'procfile': PROCFILE}
        # post the build without a session
        self.assertIsNone(self.client.logout())
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        # post the build with the builder auth key
        response = self.client.post(url, json.dumps(body), content_type='application/json',
                                    HTTP_X_DEIS_BUILDER_AUTH=settings.BUILDER_KEY)
        self.assertEqual(response.status_code, 200)
        self.assertIn('release', response.data)
        self.assertIn('version', response.data['release'])
        self.assertIn('domains', response.data)
        # make sure build fields were populated
        self.assertTrue(
            self.client.login(username='autotest', password='password'))
        url = '/api/apps/{app_id}/builds'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        build = response.data['results'][0]
        self.assertEqual(build['sha'], SHA)
        self.assertEqual(build['procfile'], json.dumps(PROCFILE))
        # test listing/retrieving container info
        url = "/api/apps/{app_id}/containers/web".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        container = response.data['results'][0]
        self.assertEqual(container['type'], 'web')
        self.assertEqual(container['num'], 1)

    def test_build_hook_dockerfile(self):
        """Test creating a Dockerfile build via an API Hook"""
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        build = {'username': 'autotest', 'app': app_id}
        url = '/api/hooks/builds'.format(**locals())
        SHA = 'ecdff91c57a0b9ab82e89634df87e293d259a3aa'
        DOCKERFILE = """
        FROM busybox
        CMD /bin/true
        """
        body = {'receive_user': 'autotest',
                'receive_repo': app_id,
                'image': 'registry.local:5000/{app_id}:v2'.format(**locals()),
                'sha': SHA,
                'dockerfile': DOCKERFILE}
        # post the build without a session
        self.assertIsNone(self.client.logout())
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        # post the build with the builder auth key
        response = self.client.post(url, json.dumps(body), content_type='application/json',
                                    HTTP_X_DEIS_BUILDER_AUTH=settings.BUILDER_KEY)
        self.assertEqual(response.status_code, 200)
        self.assertIn('release', response.data)
        self.assertIn('version', response.data['release'])
        self.assertIn('domains', response.data)
        # make sure build fields were populated
        self.assertTrue(
            self.client.login(username='autotest', password='password'))
        url = '/api/apps/{app_id}/builds'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        build = response.data['results'][0]
        self.assertEqual(build['sha'], SHA)
        self.assertEqual(build['dockerfile'], DOCKERFILE)
        # test default container
        url = "/api/apps/{app_id}/containers/cmd".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        container = response.data['results'][0]
        self.assertEqual(container['type'], 'cmd')
        self.assertEqual(container['num'], 1)

    def test_config_hook(self):
        """Test reading Config via an API Hook"""
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        url = '/api/apps/{app_id}/config'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('values', response.data)
        values = response.data['values']
        # prepare the config hook
        config = {'username': 'autotest', 'app': app_id}
        url = '/api/hooks/config'.format(**locals())
        body = {'receive_user': 'autotest',
                'receive_repo': app_id}
        # post without a session
        self.assertIsNone(self.client.logout())
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        # post with the builder auth key
        response = self.client.post(url, json.dumps(body), content_type='application/json',
                                    HTTP_X_DEIS_BUILDER_AUTH=settings.BUILDER_KEY)
        self.assertEqual(response.status_code, 200)
        self.assertIn('values', response.data)
        self.assertEqual(values, response.data['values'])

########NEW FILE########
__FILENAME__ = test_key
"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""

from __future__ import unicode_literals

import json

from django.test import TestCase
from django.test.utils import override_settings

from api.models import Key
from api.utils import fingerprint


PUBKEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCfQkkUUoxpvcNMkvv7jqnfodgs37M2eBO" \
         "APgLK+KNBMaZaaKB4GF1QhTCMfFhoiTW3rqa0J75bHJcdkoobtTHlK8XUrFqsquWyg3XhsT" \
         "Yr/3RQQXvO86e2sF7SVDJqVtpnbQGc5SgNrHCeHJmf5HTbXSIjCO/AJSvIjnituT/SIAMGe" \
         "Bw0Nq/iSltwYAek1hiKO7wSmLcIQ8U4A00KEUtalaumf2aHOcfjgPfzlbZGP0S0cuBwSqLr" \
         "8b5XGPmkASNdUiuJY4MJOce7bFU14B7oMAy2xacODUs1momUeYtGI9T7X2WMowJaO7tP3Gl" \
         "sgBMP81VfYTfYChAyJpKp2yoP autotest@autotesting comment"


@override_settings(CELERY_ALWAYS_EAGER=True)
class KeyTest(TestCase):

    """Tests cloud provider credentials"""

    fixtures = ['tests.json']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='autotest', password='password'))

    def test_key(self):
        """
        Test that a user can add, remove and manage their SSH public keys
        """
        url = '/api/keys'
        body = {'id': 'mykey@box.local', 'public': PUBKEY}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        key_id = response.data['id']
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        url = '/api/keys/{key_id}'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body['id'], response.data['id'])
        self.assertEqual(body['public'], response.data['public'])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

    def test_key_duplicate(self):
        """
        Test that a user cannot add a duplicate key
        """
        url = '/api/keys'
        body = {'id': 'mykey@box.local', 'public': PUBKEY}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_key_str(self):
        """Test the text representation of a key"""
        url = '/api/keys'
        body = {'id': 'autotest', 'public':
                'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDzqPAwHN70xsB0LXG//KzO'
                'gcPikyhdN/KRc4x3j/RA0pmFj63Ywv0PJ2b1LcMSqfR8F11WBlrW8c9xFua0'
                'ZAKzI+gEk5uqvOR78bs/SITOtKPomW4e/1d2xEkJqOmYH30u94+NZZYwEBqY'
                'aRb34fhtrnJS70XeGF0RhXE5Qea5eh7DBbeLxPfSYd8rfHgzMSb/wmx3h2vm'
                'HdQGho20pfJktNu7DxeVkTHn9REMUphf85su7slTgTlWKq++3fASE8PdmFGz'
                'b6PkOR4c+LS5WWXd2oM6HyBQBxxiwXbA2lSgQxOdgDiM2FzT0GVSFMUklkUH'
                'MdsaG6/HJDw9QckTS0vN autotest@deis.io'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        key = Key.objects.get(uuid=response.data['uuid'])
        self.assertEqual(str(key), 'ssh-rsa AAAAB3NzaC.../HJDw9QckTS0vN autotest@deis.io')

    def test_key_fingerprint(self):
        fp = fingerprint(PUBKEY)
        self.assertEquals(fp, '54:6d:da:1f:91:b5:2b:6f:a2:83:90:c4:f9:73:76:f5')

########NEW FILE########
__FILENAME__ = test_perm

from __future__ import unicode_literals
import json

from django.test import TestCase
from django.test.utils import override_settings


@override_settings(CELERY_ALWAYS_EAGER=True)
class TestAdminPerms(TestCase):

    def test_first_signup(self):
        # register a first user
        username, password = 'firstuser', 'password'
        email = 'autotest@deis.io'
        submit = {
            'username': username,
            'password': password,
            'email': email,
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['is_superuser'])
        # register a second user
        username, password = 'seconduser', 'password'
        email = 'autotest@deis.io'
        submit = {
            'username': username,
            'password': password,
            'email': email,
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['is_superuser'])

    def test_list(self):
        submit = {
            'username': 'firstuser',
            'password': 'password',
            'email': 'autotest@deis.io',
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['is_superuser'])
        self.assertTrue(
            self.client.login(username='firstuser', password='password'))
        response = self.client.get('/api/admin/perms', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'firstuser')
        self.assertTrue(response.data['results'][0]['is_superuser'])
        # register a non-superuser
        submit = {
            'username': 'seconduser',
            'password': 'password',
            'email': 'autotest@deis.io',
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['is_superuser'])
        self.assertTrue(
            self.client.login(username='seconduser', password='password'))
        response = self.client.get('/api/admin/perms', content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('You do not have permission', response.data['detail'])

    def test_create(self):
        submit = {
            'username': 'first',
            'password': 'password',
            'email': 'autotest@deis.io',
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['is_superuser'])
        submit = {
            'username': 'second',
            'password': 'password',
            'email': 'autotest@deis.io',
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['is_superuser'])
        self.assertTrue(
            self.client.login(username='first', password='password'))
        # grant user 2 the superuser perm
        url = '/api/admin/perms'
        body = {'username': 'second'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertIn('second', str(response.data['results']))

    def test_delete(self):
        submit = {
            'username': 'first',
            'password': 'password',
            'email': 'autotest@deis.io',
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['is_superuser'])
        submit = {
            'username': 'second',
            'password': 'password',
            'email': 'autotest@deis.io',
        }
        url = '/api/auth/register'
        response = self.client.post(url, json.dumps(submit), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['is_superuser'])
        self.assertTrue(
            self.client.login(username='first', password='password'))
        # grant user 2 the superuser perm
        url = '/api/admin/perms'
        body = {'username': 'second'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # revoke the superuser perm
        response = self.client.delete(url + '/second')
        self.assertEqual(response.status_code, 204)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertNotIn('two', str(response.data['results']))


@override_settings(CELERY_ALWAYS_EAGER=True)
class TestAppPerms(TestCase):

    fixtures = ['test_sharing.json']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='autotest-1', password='password'))

    def test_create(self):
        # check that user 1 sees her lone app
        response = self.client.get('/api/apps')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        app_id = response.data['results'][0]['id']
        # check that user 2 can't see any apps
        self.assertTrue(
            self.client.login(username='autotest-2', password='password'))
        response = self.client.get('/api/apps')
        self.assertEqual(len(response.data['results']), 0)
        # TODO: test that git pushing to the app fails
        # give user 2 permission to user 1's app
        self.assertTrue(
            self.client.login(username='autotest-1', password='password'))
        url = "/api/apps/{}/perms".format(app_id)
        body = {'username': 'autotest-2'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # check that user 2 can see the app
        self.assertTrue(
            self.client.login(username='autotest-2', password='password'))
        response = self.client.get('/api/apps')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        # TODO:  check that user 2 can git push the app

    def test_create_errors(self):
        # check that user 1 sees her lone app
        response = self.client.get('/api/apps')
        app_id = response.data['results'][0]['id']
        # check that user 2 can't create a permission
        self.assertTrue(
            self.client.login(username='autotest-2', password='password'))
        url = "/api/apps/{}/perms".format(app_id)
        body = {'username': 'autotest-2'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_delete(self):
        # give user 2 permission to user 1's app
        self.assertTrue(
            self.client.login(username='autotest-1', password='password'))
        response = self.client.get('/api/apps')
        app_id = response.data['results'][0]['id']
        url = "/api/apps/{}/perms".format(app_id)
        body = {'username': 'autotest-2'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # check that user 2 can see the app
        self.assertTrue(
            self.client.login(username='autotest-2', password='password'))
        response = self.client.get('/api/apps')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        # try to delete the permission as user 2
        url = "/api/apps/{}/perms/{}".format(app_id, 'autotest-2')
        response = self.client.delete(url, content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(response.data)
        # delete permission to user 1's app
        self.assertTrue(
            self.client.login(username='autotest-1', password='password'))
        response = self.client.delete(url, content_type='application/json')
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(response.data)
        # check that user 2 can't see any apps
        self.assertTrue(
            self.client.login(username='autotest-2', password='password'))
        response = self.client.get('/api/apps')
        self.assertEqual(len(response.data['results']), 0)
        # delete permission to user 1's app again, expecting an error
        self.assertTrue(
            self.client.login(username='autotest-1', password='password'))
        response = self.client.delete(url, content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_list(self):
        # check that user 1 sees her lone app
        response = self.client.get('/api/apps')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        app_id = response.data['results'][0]['id']
        # create a new object permission
        url = "/api/apps/{}/perms".format(app_id)
        body = {'username': 'autotest-2'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # list perms on the app
        response = self.client.get(
            "/api/apps/{}/perms".format(app_id), content_type='application/json')
        self.assertEqual(response.data, {'users': ['autotest-2']})

    def test_list_errors(self):
        response = self.client.get('/api/apps')
        app_id = response.data['results'][0]['id']
        # login as user 2
        self.assertTrue(
            self.client.login(username='autotest-2', password='password'))
        # list perms on the app
        response = self.client.get(
            "/api/apps/{}/perms".format(app_id), content_type='application/json')
        self.assertEqual(response.status_code, 403)

########NEW FILE########
__FILENAME__ = test_release
"""
Unit tests for the Deis api app.

Run the tests with "./manage.py test api"
"""

from __future__ import unicode_literals

import json

from django.test import TransactionTestCase
from django.test.utils import override_settings

from api.models import Release


@override_settings(CELERY_ALWAYS_EAGER=True)
class ReleaseTest(TransactionTestCase):

    """Tests push notification from build system"""

    fixtures = ['tests.json']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='autotest', password='password'))
        body = {'id': 'autotest', 'domain': 'autotest.local', 'type': 'mock',
                'hosts': 'host1,host2', 'auth': 'base64string', 'options': {}}
        response = self.client.post('/api/clusters', json.dumps(body),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_release(self):
        """
        Test that a release is created when a cluster is created, and
        that updating config or build or triggers a new release
        """
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # check that updating config rolls a new release
        url = '/api/apps/{app_id}/config'.format(**locals())
        body = {'values': json.dumps({'NEW_URL1': 'http://localhost:8080/'})}
        response = self.client.post(
            url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('NEW_URL1', json.loads(response.data['values']))
        # check to see that an initial release was created
        url = '/api/apps/{app_id}/releases'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # account for the config release as well
        self.assertEqual(response.data['count'], 2)
        url = '/api/apps/{app_id}/releases/v1'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        release1 = response.data
        self.assertIn('config', response.data)
        self.assertIn('build', response.data)
        self.assertEquals(release1['version'], 1)
        # check to see that a new release was created
        url = '/api/apps/{app_id}/releases/v2'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        release2 = response.data
        self.assertNotEqual(release1['uuid'], release2['uuid'])
        self.assertNotEqual(release1['config'], release2['config'])
        self.assertEqual(release1['build'], release2['build'])
        self.assertEquals(release2['version'], 2)
        # check that updating the build rolls a new release
        url = '/api/apps/{app_id}/builds'.format(**locals())
        build_config = json.dumps({'PATH': 'bin:/usr/local/bin:/usr/bin:/bin'})
        body = {'image': 'autotest/example'}
        response = self.client.post(
            url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['image'], body['image'])
        # check to see that a new release was created
        url = '/api/apps/{app_id}/releases/v3'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        release3 = response.data
        self.assertNotEqual(release2['uuid'], release3['uuid'])
        self.assertNotEqual(release2['build'], release3['build'])
        self.assertEquals(release3['version'], 3)
        # check that we can fetch a previous release
        url = '/api/apps/{app_id}/releases/v2'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        release2 = response.data
        self.assertNotEqual(release2['uuid'], release3['uuid'])
        self.assertNotEqual(release2['build'], release3['build'])
        self.assertEquals(release2['version'], 2)
        # disallow post/put/patch/delete
        url = '/api/apps/{app_id}/releases'.format(**locals())
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.put(url).status_code, 405)
        self.assertEqual(self.client.patch(url).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        return release3

    def test_release_rollback(self):
        url = '/api/apps'
        body = {'cluster': 'autotest'}
        response = self.client.post(url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        app_id = response.data['id']
        # try to rollback with only 1 release extant, expecting 404
        url = "/api/apps/{app_id}/releases/rollback/".format(**locals())
        response = self.client.post(url, content_type='application/json')
        self.assertEqual(response.status_code, 404)
        # update config to roll a new release
        url = '/api/apps/{app_id}/config'.format(**locals())
        body = {'values': json.dumps({'NEW_URL1': 'http://localhost:8080/'})}
        response = self.client.post(
            url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # update the build to roll a new release
        url = '/api/apps/{app_id}/builds'.format(**locals())
        build_config = json.dumps({'PATH': 'bin:/usr/local/bin:/usr/bin:/bin'})
        body = {'image': 'autotest/example'}
        response = self.client.post(
            url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # rollback and check to see that a 4th release was created
        # with the build and config of release #2
        url = "/api/apps/{app_id}/releases/rollback/".format(**locals())
        response = self.client.post(url, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = '/api/apps/{app_id}/releases'.format(**locals())
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        url = '/api/apps/{app_id}/releases/v2'.format(**locals())
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        release2 = response.data
        self.assertEquals(release2['version'], 2)
        url = '/api/apps/{app_id}/releases/v4'.format(**locals())
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        release4 = response.data
        self.assertEquals(release4['version'], 4)
        self.assertNotEqual(release2['uuid'], release4['uuid'])
        self.assertEqual(release2['build'], release4['build'])
        self.assertEqual(release2['config'], release4['config'])
        # rollback explicitly to release #1 and check that a 5th release
        # was created with the build and config of release #1
        url = "/api/apps/{app_id}/releases/rollback/".format(**locals())
        body = {'version': 1}
        response = self.client.post(
            url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = '/api/apps/{app_id}/releases'.format(**locals())
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 5)
        url = '/api/apps/{app_id}/releases/v1'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        release1 = response.data
        url = '/api/apps/{app_id}/releases/v5'.format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        release5 = response.data
        self.assertEqual(release5['version'], 5)
        self.assertNotEqual(release1['uuid'], release5['uuid'])
        self.assertEqual(release1['build'], release5['build'])
        self.assertEqual(release1['config'], release5['config'])
        # check to see that the current config is actually the initial one
        url = "/api/apps/{app_id}/config".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['values'], json.dumps({}))
        # rollback to #3 and see that it has the correct config
        url = "/api/apps/{app_id}/releases/rollback/".format(**locals())
        body = {'version': 3}
        response = self.client.post(
            url, json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        url = "/api/apps/{app_id}/config".format(**locals())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        values = json.loads(response.data['values'])
        self.assertIn('NEW_URL1', values)
        self.assertEqual('http://localhost:8080/', values['NEW_URL1'])

    def test_release_str(self):
        """Test the text representation of a release."""
        release3 = self.test_release()
        release = Release.objects.get(uuid=release3['uuid'])
        self.assertEqual(str(release), "{}-v3".format(release3['app']))

    def test_release_summary(self):
        """Test the text summary of a release."""
        release3 = self.test_release()
        release = Release.objects.get(uuid=release3['uuid'])
        # check that the release has push and env change messages
        self.assertIn('autotest deployed ', release.summary)

########NEW FILE########
__FILENAME__ = urls
"""
RESTful URL patterns and routing for the Deis API app.


Clusters
========

.. http:get:: /api/clusters/(string:id)/

  Retrieve a :class:`~api.models.Cluster` by its `id`.

.. http:delete:: /api/clusters/(string:id)/

  Destroy a :class:`~api.models.Cluster` by its `id`.

.. http:get:: /api/clusters/

  List all :class:`~api.models.Cluster`\s.

.. http:post:: /api/clusters/

  Create a new :class:`~api.models.Cluster`.


Applications
============

.. http:get:: /api/apps/(string:id)/

  Retrieve a :class:`~api.models.Application` by its `id`.

.. http:delete:: /api/apps/(string:id)/

  Destroy a :class:`~api.models.App` by its `id`.

.. http:get:: /api/apps/

  List all :class:`~api.models.App`\s.

.. http:post:: /api/apps/

  Create a new :class:`~api.models.App`.


Application Release Components
------------------------------

.. http:get:: /api/apps/(string:id)/config/

  List all :class:`~api.models.Config`\s.

.. http:post:: /api/apps/(string:id)/config/

  Create a new :class:`~api.models.Config`.

.. http:get:: /api/apps/(string:id)/builds/(string:uuid)/

  Retrieve a :class:`~api.models.Build` by its `uuid`.

.. http:get:: /api/apps/(string:id)/builds/

  List all :class:`~api.models.Build`\s.

.. http:post:: /api/apps/(string:id)/builds/

  Create a new :class:`~api.models.Build`.

.. http:get:: /api/apps/(string:id)/releases/(int:version)/

  Retrieve a :class:`~api.models.Release` by its `version`.

.. http:get:: /api/apps/(string:id)/releases/

  List all :class:`~api.models.Release`\s.

.. http:post:: /api/apps/(string:id)/releases/rollback/

  Rollback to a previous :class:`~api.models.Release`.


Application Infrastructure
--------------------------

.. http:get:: /api/apps/(string:id)/containers/(string:type)/(int:num)/

  List all :class:`~api.models.Container`\s.

.. http:get:: /api/apps/(string:id)/containers/(string:type)/

  List all :class:`~api.models.Container`\s.

.. http:get:: /api/apps/(string:id)/containers/

  List all :class:`~api.models.Container`\s.


Application Domains
-------------------


.. http:delete:: /api/apps/(string:id)/domains/(string:hostname)

  Destroy a :class:`~api.models.Domain` by its `hostname`

.. http:get:: /api/apps/(string:id)/domains/

  List all :class:`~api.models.Domain`\s.

.. http:post:: /api/apps/(string:id)/domains/

  Create a new :class:`~api.models.Domain`\s.


Application Actions
-------------------

.. http:post:: /api/apps/(string:id)/scale/

  See also
  :meth:`AppViewSet.scale() <api.views.AppViewSet.scale>`

.. http:post:: /api/apps/(string:id)/logs/

  See also
  :meth:`AppViewSet.logs() <api.views.AppViewSet.logs>`

.. http:post:: /api/apps/(string:id)/run/

  See also
  :meth:`AppViewSet.run() <api.views.AppViewSet.run>`

.. http:post:: /api/apps/(string:id)/calculate/

  See also
  :meth:`AppViewSet.calculate() <api.views.AppViewSet.calculate>`


Application Sharing
===================

.. http:delete:: /api/apps/(string:id)/perms/(string:username)/

  Destroy an app permission by its `username`.

.. http:get:: /api/apps/(string:id)/perms/

  List all permissions granted to this app.

.. http:post:: /api/apps/(string:id)/perms/

  Create a new app permission.


Keys
====

.. http:get:: /api/keys/(string:id)/

  Retrieve a :class:`~api.models.Key` by its `id`.

.. http:delete:: /api/keys/(string:id)/

  Destroy a :class:`~api.models.Key` by its `id`.

.. http:get:: /api/keys/

  List all :class:`~api.models.Key`\s.

.. http:post:: /api/keys/

  Create a new :class:`~api.models.Key`.


API Hooks
=========

.. http:post:: /api/hooks/push/

  Create a new :class:`~api.models.Push`.

.. http:post:: /api/hooks/build/

  Create a new :class:`~api.models.Build`.

.. http:post:: /api/hooks/config/

  Retrieve latest application :class:`~api.models.Config`.


Auth
====

.. http:post:: /api/auth/register/

  Create a new :class:`~django.contrib.auth.models.User`.

.. http:delete:: /api/auth/register/

  Destroy the logged-in :class:`~django.contrib.auth.models.User`.

.. http:post:: /api/auth/login

  Authenticate for the REST framework.

.. http:post:: /api/auth/logout

  Clear authentication for the REST framework.

.. http:get:: /api/generate-api-key/

  Generate an API key.


Admin Sharing
=============

.. http:delete:: /api/admin/perms/(string:username)/

  Destroy an admin permission by its `username`.

.. http:get:: /api/admin/perms/

  List all admin permissions granted.

.. http:post:: /api/admin/perms/

  Create a new admin permission.

"""

from __future__ import unicode_literals

from django.conf.urls import include
from django.conf.urls import patterns
from django.conf.urls import url

from api import routers
from api import views


router = routers.ApiRouter()

# Add the generated REST URLs and login/logout endpoint
urlpatterns = patterns(
    '',
    url(r'^', include(router.urls)),
    # clusters
    url(r'^clusters/(?P<id>[-_\w]+)/?',
        views.ClusterViewSet.as_view({
            'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'})),
    url(r'^clusters/?',
        views.ClusterViewSet.as_view({'get': 'list', 'post': 'create'})),
    # application release components
    url(r'^apps/(?P<id>[-_\w]+)/config/?',
        views.AppConfigViewSet.as_view({'get': 'retrieve', 'post': 'create'})),
    url(r'^apps/(?P<id>[-_\w]+)/builds/(?P<uuid>[-_\w]+)/?',
        views.AppBuildViewSet.as_view({'get': 'retrieve'})),
    url(r'^apps/(?P<id>[-_\w]+)/builds/?',
        views.AppBuildViewSet.as_view({'get': 'list', 'post': 'create'})),
    url(r'^apps/(?P<id>[-_\w]+)/releases/v(?P<version>[0-9]+)/?',
        views.AppReleaseViewSet.as_view({'get': 'retrieve'})),
    url(r'^apps/(?P<id>[-_\w]+)/releases/rollback/?',
        views.AppReleaseViewSet.as_view({'post': 'rollback'})),
    url(r'^apps/(?P<id>[-_\w]+)/releases/?',
        views.AppReleaseViewSet.as_view({'get': 'list'})),
    # application infrastructure
    url(r'^apps/(?P<id>[-_\w]+)/containers/(?P<type>[-_\w]+)/(?P<num>[-_\w]+)/?',
        views.AppContainerViewSet.as_view({'get': 'retrieve'})),
    url(r'^apps/(?P<id>[-_\w]+)/containers/(?P<type>[-_\w.]+)/?',
        views.AppContainerViewSet.as_view({'get': 'list'})),
    url(r'^apps/(?P<id>[-_\w]+)/containers/?',
        views.AppContainerViewSet.as_view({'get': 'list'})),
    # application domains
    url(r'^apps/(?P<id>[-_\w]+)/domains/(?P<domain>[-\._\w]+)/?',
        views.DomainViewSet.as_view({'delete': 'destroy'})),
    url(r'^apps/(?P<id>[-_\w]+)/domains/?',
        views.DomainViewSet.as_view({'post': 'create', 'get': 'list'})),
    # application actions
    url(r'^apps/(?P<id>[-_\w]+)/scale/?',
        views.AppViewSet.as_view({'post': 'scale'})),
    url(r'^apps/(?P<id>[-_\w]+)/logs/?',
        views.AppViewSet.as_view({'post': 'logs'})),
    url(r'^apps/(?P<id>[-_\w]+)/run/?',
        views.AppViewSet.as_view({'post': 'run'})),
    url(r'^apps/(?P<id>[-_\w]+)/calculate/?',
        views.AppViewSet.as_view({'post': 'calculate'})),
    # apps sharing
    url(r'^apps/(?P<id>[-_\w]+)/perms/(?P<username>[-_\w]+)/?',
        views.AppPermsViewSet.as_view({'delete': 'destroy'})),
    url(r'^apps/(?P<id>[-_\w]+)/perms/?',
        views.AppPermsViewSet.as_view({'get': 'list', 'post': 'create'})),
    # apps base endpoint
    url(r'^apps/(?P<id>[-_\w]+)/?',
        views.AppViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'})),
    url(r'^apps/?',
        views.AppViewSet.as_view({'get': 'list', 'post': 'create'})),
    # key
    url(r'^keys/(?P<id>.+)/?',
        views.KeyViewSet.as_view({
            'get': 'retrieve', 'delete': 'destroy'})),
    url(r'^keys/?',
        views.KeyViewSet.as_view({'get': 'list', 'post': 'create'})),
    # hooks
    url(r'^hooks/push/?',
        views.PushHookViewSet.as_view({'post': 'create'})),
    url(r'^hooks/build/?',
        views.BuildHookViewSet.as_view({'post': 'create'})),
    url(r'^hooks/config/?',
        views.ConfigHookViewSet.as_view({'post': 'create'})),
    # authn / authz
    url(r'^auth/register/?',
        views.UserRegistrationView.as_view({'post': 'create'})),
    url(r'^auth/cancel/?',
        views.UserCancellationView.as_view({'delete': 'destroy'})),
    url(r'^auth/',
        include('rest_framework.urls', namespace='rest_framework')),
    url(r'^generate-api-key/',
        'rest_framework.authtoken.views.obtain_auth_token'),
    # admin sharing
    url(r'^admin/perms/(?P<username>[-_\w]+)/?',
        views.AdminPermsViewSet.as_view({'delete': 'destroy'})),
    url(r'^admin/perms/?',
        views.AdminPermsViewSet.as_view({'get': 'list', 'post': 'create'})),
)

########NEW FILE########
__FILENAME__ = utils
"""
Helper functions used by the Deis server.
"""
import base64
import hashlib
import random


def generate_app_name():
    """Return a randomly-generated memorable name."""
    adjectives = [
        'ablest', 'absurd', 'actual', 'allied', 'artful', 'atomic', 'august',
        'bamboo', 'benign', 'blonde', 'blurry', 'bolder', 'breezy', 'bubbly',
        'candid', 'casual', 'cheery', 'classy', 'clever', 'convex', 'cubist',
        'dainty', 'dapper', 'decent', 'deluxe', 'docile', 'dogged', 'drafty',
        'earthy', 'easier', 'edible', 'elfish', 'excess', 'exotic', 'expert',
        'fabled', 'famous', 'feline', 'finest', 'flaxen', 'folksy', 'frozen',
        'gaslit', 'gentle', 'gifted', 'ginger', 'global', 'golden', 'grassy',
        'hearty', 'hidden', 'hipper', 'honest', 'humble', 'hungry', 'hushed',
        'iambic', 'iconic', 'indoor', 'inward', 'ironic', 'island', 'italic',
        'jagged', 'jangly', 'jaunty', 'jiggly', 'jovial', 'joyful', 'junior',
        'kabuki', 'karmic', 'keener', 'kindly', 'kingly', 'klutzy', 'knotty',
        'lambda', 'leader', 'linear', 'lively', 'lonely', 'loving', 'luxury',
        'madras', 'marble', 'mellow', 'metric', 'modest', 'molten', 'mystic',
        'native', 'nearby', 'nested', 'newish', 'nickel', 'nimbus', 'nonfat',
        'oblong', 'offset', 'oldest', 'onside', 'orange', 'outlaw', 'owlish',
        'padded', 'peachy', 'pepper', 'player', 'preset', 'proper', 'pulsar',
        'quacky', 'quaint', 'quartz', 'queens', 'quinoa', 'quirky',
        'racing', 'rental', 'rising', 'rococo', 'rubber', 'rugged', 'rustic',
        'sanest', 'scenic', 'shadow', 'skiing', 'stable', 'steely', 'syrupy',
        'taller', 'tender', 'timely', 'trendy', 'triple', 'truthy', 'twenty',
        'ultima', 'unbent', 'unisex', 'united', 'upbeat', 'uphill', 'usable',
        'valued', 'vanity', 'velcro', 'velvet', 'verbal', 'violet', 'vulcan',
        'webbed', 'wicker', 'wiggly', 'wilder', 'wonder', 'wooden', 'woodsy',
        'yearly', 'yeasty', 'yeoman', 'yogurt', 'yonder', 'youthy', 'yuppie',
        'zaftig', 'zanier', 'zephyr', 'zeroed', 'zigzag', 'zipped', 'zircon',
    ]
    nouns = [
        'anaconda', 'airfield', 'aqualung', 'armchair', 'asteroid', 'autoharp',
        'babushka', 'bagpiper', 'barbecue', 'bookworm', 'bullfrog', 'buttress',
        'caffeine', 'chinbone', 'countess', 'crawfish', 'cucumber', 'cutpurse',
        'daffodil', 'darkroom', 'doghouse', 'dragster', 'drumroll', 'duckling',
        'earthman', 'eggplant', 'electron', 'elephant', 'espresso', 'eyetooth',
        'falconer', 'farmland', 'ferryman', 'fireball', 'footwear', 'frosting',
        'gadabout', 'gasworks', 'gatepost', 'gemstone', 'goldfish', 'greenery',
        'handbill', 'hardtack', 'hawthorn', 'headwind', 'henhouse', 'huntress',
        'icehouse', 'idealist', 'inchworm', 'inventor', 'insignia', 'ironwood',
        'jailbird', 'jamboree', 'jerrycan', 'jetliner', 'jokester', 'joyrider',
        'kangaroo', 'kerchief', 'keypunch', 'kingfish', 'knapsack', 'knothole',
        'ladybird', 'lakeside', 'lambskin', 'larkspur', 'lollipop', 'lungfish',
        'macaroni', 'mackinaw', 'magician', 'mainsail', 'mongoose', 'moonrise',
        'nailhead', 'nautilus', 'neckwear', 'newsreel', 'novelist', 'nuthatch',
        'occupant', 'offering', 'offshoot', 'original', 'organism', 'overalls',
        'painting', 'pamphlet', 'paneling', 'pendulum', 'playroom', 'ponytail',
        'quacking', 'quadrant', 'queendom', 'question', 'quilting', 'quotient',
        'rabbitry', 'radiator', 'renegade', 'ricochet', 'riverbed', 'rucksack',
        'sailfish', 'sandwich', 'sculptor', 'seashore', 'seedcake', 'stickpin',
        'tabletop', 'tailbone', 'teamwork', 'teaspoon', 'traverse', 'turbojet',
        'umbrella', 'underdog', 'undertow', 'unicycle', 'universe', 'uptowner',
        'vacation', 'vagabond', 'valkyrie', 'variable', 'villager', 'vineyard',
        'waggoner', 'waxworks', 'waterbed', 'wayfarer', 'whitecap', 'woodshed',
        'yachting', 'yardbird', 'yearbook', 'yearling', 'yeomanry', 'yodeling',
        'zaniness', 'zeppelin', 'ziggurat', 'zirconia', 'zoologer', 'zucchini',
    ]
    return "{}-{}".format(
        random.choice(adjectives), random.choice(nouns))


def dict_diff(dict1, dict2):
    """
    Returns the added, changed, and deleted items in dict1 compared with dict2.

    :param dict1: a python dict
    :param dict2: an earlier version of the same python dict
    :return: a new dict, with 'added', 'changed', and 'removed' items if
             any were found.

    >>> d1 = {1: 'a'}
    >>> dict_diff(d1, d1)
    {}
    >>> d2 = {1: 'a', 2: 'b'}
    >>> dict_diff(d2, d1)
    {'added': {2: 'b'}}
    >>> d3 = {2: 'B', 3: 'c'}
    >>> expected = {'added': {3: 'c'}, 'changed': {2: 'B'}, 'deleted': {1: 'a'}}
    >>> dict_diff(d3, d2) == expected
    True
    """
    diff = {}
    set1, set2 = set(dict1), set(dict2)
    # Find items that were added to dict2
    diff['added'] = {k: dict1[k] for k in (set1 - set2)}
    # Find common items whose values differ between dict1 and dict2
    diff['changed'] = {
        k: dict1[k] for k in (set1 & set2) if dict1[k] != dict2[k]
    }
    # Find items that were deleted from dict2
    diff['deleted'] = {k: dict2[k] for k in (set2 - set1)}
    return {k: diff[k] for k in diff if diff[k]}


def fingerprint(key):
    """
    Return the fingerprint for an SSH Public Key
    """
    key = base64.b64decode(key.strip().split()[1].encode('ascii'))
    fp_plain = hashlib.md5(key).hexdigest()
    return ':'.join(a + b for a, b in zip(fp_plain[::2], fp_plain[1::2]))


if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = views
"""
RESTful view classes for presenting Deis API objects.
"""

from __future__ import absolute_import
from __future__ import unicode_literals
import json

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import User
from django.utils import timezone
from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import get_users_with_perms
from guardian.shortcuts import remove_perm
from rest_framework import permissions
from rest_framework import status
from rest_framework import viewsets
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from api import models, serializers

from django.conf import settings


class AnonymousAuthentication(BaseAuthentication):

    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        user = AnonymousUser()
        return user, None


class IsAnonymous(permissions.BasePermission):
    """
    View permission to allow anonymous users.
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return type(request.user) is AnonymousUser


class IsOwner(permissions.BasePermission):
    """
    Object-level permission to allow only owners of an object to access it.
    Assumes the model instance has an `owner` attribute.
    """

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        else:
            return False


class IsAppUser(permissions.BasePermission):
    """
    Object-level permission to allow owners or collaborators to access
    an app-related model.
    """
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, models.App) and obj.owner == request.user:
            return True
        elif hasattr(obj, 'app') and obj.app.owner == request.user:
            return True
        elif request.user.has_perm('use_app', obj):
            return request.method != 'DELETE'
        elif hasattr(obj, 'app') and request.user.has_perm('use_app', obj.app):
            return request.method != 'DELETE'
        else:
            return False


class IsAdmin(permissions.BasePermission):
    """
    View permission to allow only admins.
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.user.is_superuser


class IsAdminOrSafeMethod(permissions.BasePermission):
    """
    View permission to allow only admins to use unsafe methods
    including POST, PUT, DELETE.

    This allows
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.method in permissions.SAFE_METHODS or request.user.is_superuser


class HasRegistrationAuth(permissions.BasePermission):
    """
    Checks to see if registration is enabled
    """
    def has_permission(self, request, view):
        return settings.REGISTRATION_ENABLED


class HasBuilderAuth(permissions.BasePermission):
    """
    View permission to allow builder to perform actions
    with a special HTTP header
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        auth_header = request.environ.get('HTTP_X_DEIS_BUILDER_AUTH')
        if not auth_header:
            return False
        return auth_header == settings.BUILDER_KEY


class UserRegistrationView(viewsets.GenericViewSet,
                           viewsets.mixins.CreateModelMixin):
    model = User

    authentication_classes = (AnonymousAuthentication,)
    permission_classes = (IsAnonymous, HasRegistrationAuth)
    serializer_class = serializers.UserSerializer

    def pre_save(self, obj):
        """Replicate UserManager.create_user functionality."""
        now = timezone.now()
        obj.last_login = now
        obj.date_joined = now
        obj.is_active = True
        obj.email = User.objects.normalize_email(obj.email)
        obj.set_password(obj.password)
        # Make this first signup an admin / superuser
        if not User.objects.filter(is_superuser=True).exists():
            obj.is_superuser = obj.is_staff = True


class UserCancellationView(viewsets.GenericViewSet,
                           viewsets.mixins.DestroyModelMixin):
    model = User

    permission_classes = (permissions.IsAuthenticated,)

    def destroy(self, request, *args, **kwargs):
        obj = self.request.user
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OwnerViewSet(viewsets.ModelViewSet):
    """Scope views to an `owner` attribute."""

    permission_classes = (permissions.IsAuthenticated, IsOwner)

    def pre_save(self, obj):
        obj.owner = self.request.user

    def get_queryset(self, **kwargs):
        """Filter all querysets by an `owner` attribute.
        """
        return self.model.objects.filter(owner=self.request.user)


class ClusterViewSet(viewsets.ModelViewSet):
    """RESTful views for :class:`~api.models.Cluster`."""

    model = models.Cluster
    serializer_class = serializers.ClusterSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    lookup_field = 'id'

    def pre_save(self, obj):
        if not hasattr(obj, 'owner'):
            obj.owner = self.request.user

    def post_save(self, cluster, created=False, **kwargs):
        if created:
            cluster.create()

    def pre_delete(self, cluster):
        cluster.destroy()


class AppPermsViewSet(viewsets.ViewSet):
    """RESTful views for sharing apps with collaborators."""

    model = models.App  # models class
    perm = 'use_app'    # short name for permission

    def list(self, request, **kwargs):
        app = get_object_or_404(self.model, id=kwargs['id'])
        perm_name = "api.{}".format(self.perm)
        if request.user != app.owner and not request.user.has_perm(perm_name, app):
            return Response(status=status.HTTP_403_FORBIDDEN)
        usernames = [u.username for u in get_users_with_perms(app)
                     if u.has_perm(perm_name, app)]
        return Response({'users': usernames})

    def create(self, request, **kwargs):
        app = get_object_or_404(self.model, id=kwargs['id'])
        if request.user != app.owner:
            return Response(status=status.HTTP_403_FORBIDDEN)
        user = get_object_or_404(User, username=request.DATA['username'])
        assign_perm(self.perm, user, app)
        models.log_event(app, "User {} was granted access to {}".format(user, app))
        return Response(status=status.HTTP_201_CREATED)

    def destroy(self, request, **kwargs):
        app = get_object_or_404(self.model, id=kwargs['id'])
        if request.user != app.owner:
            return Response(status=status.HTTP_403_FORBIDDEN)
        user = get_object_or_404(User, username=kwargs['username'])
        if user.has_perm(self.perm, app):
            remove_perm(self.perm, user, app)
            models.log_event(app, "User {} was revoked access to {}".format(user, app))
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


class AdminPermsViewSet(viewsets.ModelViewSet):
    """RESTful views for sharing admin permissions with other users."""

    model = User
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (IsAdmin,)

    def get_queryset(self, **kwargs):
        return self.model.objects.filter(is_active=True, is_superuser=True)

    def create(self, request, **kwargs):
        user = get_object_or_404(User, username=request.DATA['username'])
        user.is_superuser = user.is_staff = True
        user.save(update_fields=['is_superuser', 'is_staff'])
        return Response(status=status.HTTP_201_CREATED)

    def destroy(self, request, **kwargs):
        user = get_object_or_404(User, username=kwargs['username'])
        user.is_superuser = user.is_staff = False
        user.save(update_fields=['is_superuser', 'is_staff'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AppViewSet(OwnerViewSet):
    """RESTful views for :class:`~api.models.App`."""

    model = models.App
    serializer_class = serializers.AppSerializer
    lookup_field = 'id'
    permission_classes = (permissions.IsAuthenticated, IsAppUser)

    def get_queryset(self, **kwargs):
        """
        Filter Apps by `owner` attribute or the `api.use_app` permission.
        """
        return super(AppViewSet, self).get_queryset(**kwargs) | \
            get_objects_for_user(self.request.user, 'api.use_app')

    def post_save(self, app, created=False, **kwargs):
        if created:
            app.create()

    def scale(self, request, **kwargs):
        new_structure = {}
        try:
            for target, count in request.DATA.items():
                new_structure[target] = int(count)
        except ValueError:
            return Response('Invalid scaling format',
                            status=status.HTTP_400_BAD_REQUEST)
        app = self.get_object()
        try:
            app.structure = new_structure
            app.scale()
        except EnvironmentError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT,
                        content_type='application/json')

    def logs(self, request, **kwargs):
        app = self.get_object()
        try:
            logs = app.logs()
        except EnvironmentError:
            return Response("No logs for {}".format(app.id),
                            status=status.HTTP_204_NO_CONTENT,
                            content_type='text/plain')
        return Response(logs, status=status.HTTP_200_OK,
                        content_type='text/plain')

    def run(self, request, **kwargs):
        app = self.get_object()
        command = request.DATA['command']
        try:
            output_and_rc = app.run(command)
        except EnvironmentError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        return Response(output_and_rc, status=status.HTTP_200_OK,
                        content_type='text/plain')


class BaseAppViewSet(viewsets.ModelViewSet):

    permission_classes = (permissions.IsAuthenticated, IsAppUser)

    def pre_save(self, obj):
        obj.owner = self.request.user

    def get_queryset(self, **kwargs):
        app = get_object_or_404(models.App, id=self.kwargs['id'])
        return self.model.objects.filter(app=app)

    def get_object(self, *args, **kwargs):
        obj = self.get_queryset().latest('created')
        user = self.request.user
        if user == obj.app.owner or user in get_users_with_perms(obj.app):
            return obj
        raise PermissionDenied()


class AppBuildViewSet(BaseAppViewSet):
    """RESTful views for :class:`~api.models.Build`."""

    model = models.Build
    serializer_class = serializers.BuildSerializer

    def post_save(self, build, created=False):
        if created:
            release = build.app.release_set.latest()
            self.release = release.new(self.request.user, build=build)
            initial = True if build.app.structure == {} else False
            build.app.deploy(self.release, initial=initial)

    def get_success_headers(self, data):
        headers = super(AppBuildViewSet, self).get_success_headers(data)
        headers.update({'X-Deis-Release': self.release.version})
        return headers

    def create(self, request, *args, **kwargs):
        app = get_object_or_404(models.App, id=self.kwargs['id'])
        request._data = request.DATA.copy()
        request.DATA['app'] = app
        return super(AppBuildViewSet, self).create(request, *args, **kwargs)


class AppConfigViewSet(BaseAppViewSet):
    """RESTful views for :class:`~api.models.Config`."""

    model = models.Config
    serializer_class = serializers.ConfigSerializer

    def get_object(self, *args, **kwargs):
        """Return the Config associated with the App's latest Release."""
        app = get_object_or_404(models.App, id=self.kwargs['id'])
        user = self.request.user
        if user == app.owner or user in get_users_with_perms(app):
            return app.release_set.latest().config
        raise PermissionDenied()

    def post_save(self, config, created=False):
        if created:
            release = config.app.release_set.latest()
            self.release = release.new(self.request.user, config=config)
            config.app.deploy(self.release)

    def get_success_headers(self, data):
        headers = super(AppConfigViewSet, self).get_success_headers(data)
        headers.update({'X-Deis-Release': self.release.version})
        return headers

    def create(self, request, *args, **kwargs):
        request._data = request.DATA.copy()
        # assume an existing config object exists
        obj = self.get_object()
        request.DATA['app'] = obj.app
        # merge config values
        values = obj.values.copy()
        provided = json.loads(request.DATA['values'])
        values.update(provided)
        # remove config keys if we provided a null value
        [values.pop(k) for k, v in provided.items() if v is None]
        request.DATA['values'] = values
        return super(AppConfigViewSet, self).create(request, *args, **kwargs)


class AppReleaseViewSet(BaseAppViewSet):
    """RESTful views for :class:`~api.models.Release`."""

    model = models.Release
    serializer_class = serializers.ReleaseSerializer

    def get_object(self, *args, **kwargs):
        """Get Release by version always."""
        return self.get_queryset(**kwargs).get(version=self.kwargs['version'])

    # TODO: move logic into model
    def rollback(self, request, *args, **kwargs):
        """
        Create a new release as a copy of the state of the compiled slug and
        config vars of a previous release.
        """
        app = get_object_or_404(models.App, id=self.kwargs['id'])
        release = app.release_set.latest()
        last_version = release.version
        version = int(request.DATA.get('version', last_version - 1))
        if version < 1:
            return Response(status=status.HTTP_404_NOT_FOUND)
        summary = "{} rolled back to v{}".format(request.user, version)
        prev = app.release_set.get(version=version)
        new_release = release.new(
            request.user, build=prev.build, config=prev.config, summary=summary)
        app.deploy(new_release)
        msg = "Rolled back to v{}".format(version)
        return Response(msg, status=status.HTTP_201_CREATED)


class AppContainerViewSet(OwnerViewSet):
    """RESTful views for :class:`~api.models.Container`."""

    model = models.Container
    serializer_class = serializers.ContainerSerializer

    def get_queryset(self, **kwargs):
        app = get_object_or_404(models.App, id=self.kwargs['id'])
        qs = self.model.objects.filter(app=app)
        container_type = self.kwargs.get('type')
        if container_type:
            qs = qs.filter(type=container_type)
        return qs

    def get_object(self, *args, **kwargs):
        qs = self.get_queryset(**kwargs)
        obj = qs.get(num=self.kwargs['num'])
        return obj


class KeyViewSet(OwnerViewSet):
    """RESTful views for :class:`~api.models.Key`."""

    model = models.Key
    serializer_class = serializers.KeySerializer
    lookup_field = 'id'


class DomainViewSet(OwnerViewSet):
    """RESTful views for :class:`~api.models.Domain`."""

    model = models.Domain
    serializer_class = serializers.DomainSerializer

    def create(self, request, *args, **kwargs):
        app = get_object_or_404(models.App, id=self.kwargs['id'])
        request._data = request.DATA.copy()
        request.DATA['app'] = app
        return super(DomainViewSet, self).create(request, *args, **kwargs)

    def get_queryset(self, **kwargs):
        app = get_object_or_404(models.App, id=self.kwargs['id'])
        qs = self.model.objects.filter(app=app)
        return qs

    def get_object(self, *args, **kwargs):
        qs = self.get_queryset(**kwargs)
        obj = qs.get(domain=self.kwargs['domain'])
        return obj


class BaseHookViewSet(viewsets.ModelViewSet):

    permission_classes = (HasBuilderAuth,)

    def pre_save(self, obj):
        # SECURITY: we trust the username field to map to the owner
        obj.owner = self.request.DATA['owner']


class PushHookViewSet(BaseHookViewSet):
    """API hook to create new :class:`~api.models.Push`"""

    model = models.Push
    serializer_class = serializers.PushSerializer

    def create(self, request, *args, **kwargs):
        app = get_object_or_404(models.App, id=request.DATA['receive_repo'])
        user = get_object_or_404(
            User, username=request.DATA['receive_user'])
        # check the user is authorized for this app
        if user == app.owner or user in get_users_with_perms(app):
            request._data = request.DATA.copy()
            request.DATA['app'] = app
            request.DATA['owner'] = user
            return super(PushHookViewSet, self).create(request, *args, **kwargs)
        raise PermissionDenied()


class BuildHookViewSet(BaseHookViewSet):
    """API hook to create new :class:`~api.models.Build`"""

    model = models.Build
    serializer_class = serializers.BuildSerializer

    def create(self, request, *args, **kwargs):
        app = get_object_or_404(models.App, id=request.DATA['receive_repo'])
        user = get_object_or_404(
            User, username=request.DATA['receive_user'])
        # check the user is authorized for this app
        if user == app.owner or user in get_users_with_perms(app):
            request._data = request.DATA.copy()
            request.DATA['app'] = app
            request.DATA['owner'] = user
            super(BuildHookViewSet, self).create(request, *args, **kwargs)
            # return the application databag
            response = {'release': {'version': app.release_set.latest().version},
                        'domains': ['.'.join([app.id, app.cluster.domain])]}
            return Response(response, status=status.HTTP_200_OK)
        raise PermissionDenied()

    def post_save(self, build, created=False):
        if created:
            release = build.app.release_set.latest()
            new_release = release.new(build.owner, build=build)
            initial = True if build.app.structure == {} else False
            build.app.deploy(new_release, initial=initial)


class ConfigHookViewSet(BaseHookViewSet):
    """API hook to grab latest :class:`~api.models.Config`"""

    model = models.Config
    serializer_class = serializers.ConfigSerializer

    def create(self, request, *args, **kwargs):
        app = get_object_or_404(models.App, id=request.DATA['receive_repo'])
        user = get_object_or_404(
            User, username=request.DATA['receive_user'])
        # check the user is authorized for this app
        if user == app.owner or user in get_users_with_perms(app):
            config = app.release_set.latest().config
            serializer = self.get_serializer(config)
            return Response(serializer.data, status=status.HTTP_200_OK)
        raise PermissionDenied()

########NEW FILE########
__FILENAME__ = celery
"""
Celery task queue setup for a Deis controller.
"""

from __future__ import absolute_import

import os

from celery import Celery
from django.conf import settings


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deis.settings')

app = Celery('deis')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

########NEW FILE########
__FILENAME__ = context_processors

from django.contrib.sites.models import get_current_site
from django.utils.functional import SimpleLazyObject


def site(request):
    return {
        'site': SimpleLazyObject(lambda: get_current_site(request)),
    }

########NEW FILE########
__FILENAME__ = settings
"""
Django settings for the Deis project.
"""

from __future__ import unicode_literals
import os.path
import sys
import tempfile

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

CONN_MAX_AGE = 60 * 3

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['localhost']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Denver'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.abspath(os.path.join(__file__, '..', '..', 'static'))

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = None  # @UnusedVariable

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "allauth.account.context_processors.account",
    "deis.context_processors.site",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'deis.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'deis.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates"
    # or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    PROJECT_ROOT + '/web/templates',
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    # Third-party apps
    'allauth',
    'allauth.account',
    'django_fsm',
    'guardian',
    'json_field',
    'gunicorn',
    'rest_framework',
    'south',
    # Deis apps
    'api',
    'web',
)

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

ANONYMOUS_USER_ID = -1
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_USERNAME_BLACKLIST = ['system']
LOGIN_REDIRECT_URL = '/dashboard/'


SOUTH_TESTS_MIGRATE = False

REST_FRAMEWORK = {
    'DEFAULT_MODEL_SERIALIZER_CLASS':
    'rest_framework.serializers.ModelSerializer',
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'PAGINATE_BY': 100,
}

# URLs that end with slashes are ugly
APPEND_SLASH = False

# Determine where to send syslog messages
if os.path.exists('/dev/log'):           # Linux rsyslog
    SYSLOG_ADDRESS = '/dev/log'
elif os.path.exists('/var/log/syslog'):  # Mac OS X syslog
    SYSLOG_ADDRESS = '/var/log/syslog'
else:                                    # default SysLogHandler address
    SYSLOG_ADDRESS = ('localhost', 514)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'rsyslog': {
            'class': 'logging.handlers.SysLogHandler',
            'address': SYSLOG_ADDRESS,
            'facility': 'local0',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': 'WARNING',
            'propagate': True,
        },
        'api': {
            'handlers': ['console', 'mail_admins', 'rsyslog'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}
TEST_RUNNER = 'api.tests.SilentDjangoTestSuiteRunner'

# celery settings
CELERY_ACCEPT_CONTENT = ['pickle', 'json']
CELERY_IMPORTS = ('api.tasks',)
BROKER_URL = 'redis://{}:{}/{}'.format(
             os.environ.get('CACHE_HOST', '127.0.0.1'),
             os.environ.get('CACHE_PORT', 6379),
             os.environ.get('CACHE_NAME', 0))
CELERY_RESULT_BACKEND = BROKER_URL
# this number should be equal to N+1, where
# N is number of nodes in largest formation
CELERYD_CONCURRENCY = 8

# etcd settings
ETCD_HOST, ETCD_PORT = os.environ.get('ETCD', '127.0.0.1:4001').split(',')[0].split(':')

# default deis settings
DEIS_LOG_DIR = os.path.abspath(os.path.join(__file__, '..', '..', 'logs'))
LOG_LINES = 1000
TEMPDIR = tempfile.mkdtemp(prefix='deis')
DEFAULT_BUILD = 'deis/helloworld'

# security keys and auth tokens
SECRET_KEY = os.environ.get('DEIS_SECRET_KEY', 'CHANGEME_sapm$s%upvsw5l_zuy_&29rkywd^78ff(qi')
BUILDER_KEY = os.environ.get('DEIS_BUILDER_KEY', 'CHANGEME_sapm$s%upvsw5l_zuy_&29rkywd^78ff(qi')

# registry settings
REGISTRY_MODULE = 'registry.mock'
REGISTRY_URL = os.environ.get('DEIS_REGISTRY_URL', None)

# check if we can register users with `deis register`
REGISTRATION_ENABLED = True

# default to sqlite3, but allow postgresql config through envvars
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.' + os.environ.get('DATABASE_ENGINE', 'postgresql_psycopg2'),
        'NAME': os.environ.get('DATABASE_NAME', 'deis'),
    }
}

# SECURITY: change this to allowed fqdn's to prevent host poisioning attacks
# see https://docs.djangoproject.com/en/1.5/ref/settings/#std:setting-ALLOWED_HOSTS
ALLOWED_HOSTS = ['*']

# Honor HTTPS from a trusted proxy
# see https://docs.djangoproject.com/en/1.6/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Create a file named "local_settings.py" to contain sensitive settings data
# such as database configuration, admin email, or passwords and keys. It
# should also be used for any settings which differ between development
# and production.
# The local_settings.py file should *not* be checked in to version control.
try:
    from .local_settings import *  # @UnusedWildImport # noqa
except ImportError:
    pass


# have confd_settings within container execution override all others
# including local_settings (which may end up in the container)
if os.path.exists('/templates/confd_settings.py'):
    sys.path.append('/templates')
    from confd_settings import *  # noqa

########NEW FILE########
__FILENAME__ = urls
"""
URL routing patterns for the Deis project.

This is the "master" urls.py which then includes the urls.py files of
installed apps.
"""

from __future__ import unicode_literals

from django.conf.urls import patterns, include, url
from django.contrib import admin


admin.autodiscover()


urlpatterns = patterns(
    '',
    url(r'^accounts/', include('allauth.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include('api.urls')),
    url(r'^', include('web.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for deis project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

"""

from __future__ import unicode_literals
import os

from django.core.wsgi import get_wsgi_application
import static


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deis.settings")


class Dispatcher(object):
    """
    Dispatches requests between two WSGI apps, a static file server and a
    Django server.
    """

    def __init__(self):
        self.django_handler = get_wsgi_application()
        self.static_handler = static.Cling(os.path.dirname(os.path.dirname(__file__)))

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'].startswith('/static'):
            return self.static_handler(environ, start_response)
        else:
            return self.django_handler(environ, start_response)


application = Dispatcher()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from __future__ import unicode_literals
import os
import sys


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deis.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = mock

def publish_release(repository_path, config, tag):
    """
    Publish a new release as a Docker image

    This is a mock implementation used for unit tests
    """
    return None

########NEW FILE########
__FILENAME__ = private
import cStringIO
import hashlib
import json
import requests
import tarfile
import urlparse
import uuid

from django.conf import settings


def publish_release(repository_path, config, tag):
    """
    Publish a new release as a Docker image

    Given a source repository path, a dictionary of environment variables
    and a target tag, create a new lightweight Docker image on the registry.

    For example, publish_release('gabrtv/myapp', {'ENVVAR': 'values'}, 'v23')
    results in a new Docker image at: <registry_url>/gabrtv/myapp:v23
    which contains the new configuration as ENV entries.
    """
    try:
        image_id = _get_tag(repository_path, 'latest')
    except RuntimeError:
        # no image exists yet, so let's build one!
        _put_first_image(repository_path)
        image_id = _get_tag(repository_path, 'latest')
    image = _get_image(image_id)
    # construct the new image
    image['parent'] = image['id']
    image['id'] = _new_id()
    image['config']['Env'] = _construct_env(image['config']['Env'], config)
    # update and tag the new image
    _commit(repository_path, image, _empty_tar_archive(), tag)


# registry access


def _commit(repository_path, image, layer, tag):
    _put_image(image)
    cookies = _put_layer(image['id'], layer)
    _put_checksum(image, cookies)
    _put_tag(image['id'], repository_path, tag)
    # point latest to the new tag
    _put_tag(image['id'], repository_path, 'latest')


def _put_first_image(repository_path):
    image = {
        'id': _new_id(),
        'parent': '',
        'config': {
            'Env': []
        }
    }
    # tag as v0 in the registry
    _commit(repository_path, image, _empty_tar_archive(), 'v0')


def _api_call(endpoint, data=None, headers={}, cookies=None, request_type='GET'):
    # FIXME: update API calls for docker 0.10.0+
    base_headers = {'user-agent': 'docker/0.9.0'}
    r = None
    if len(headers) > 0:
        for header, value in headers.iteritems():
            base_headers[header] = value
    if request_type == 'GET':
        r = requests.get(endpoint, headers=base_headers)
    elif request_type == 'PUT':
        r = requests.put(endpoint, data=data, headers=base_headers, cookies=cookies)
    else:
        raise AttributeError("request type not supported: {}".format(request_type))
    return r


def _get_tag(repository, tag):
    path = "/v1/repositories/{repository}/tags/{tag}".format(**locals())
    url = urlparse.urljoin(settings.REGISTRY_URL, path)
    r = _api_call(url)
    if not r.status_code == 200:
        raise RuntimeError("GET Image Error ({}: {})".format(r.status_code, r.text))
    print r.text
    return r.json()


def _get_image(image_id):
    path = "/v1/images/{image_id}/json".format(**locals())
    url = urlparse.urljoin(settings.REGISTRY_URL, path)
    r = _api_call(url)
    if not r.status_code == 200:
        raise RuntimeError("GET Image Error ({}: {})".format(r.status_code, r.text))
    return r.json()


def _put_image(image):
    path = "/v1/images/{id}/json".format(**image)
    url = urlparse.urljoin(settings.REGISTRY_URL, path)
    r = _api_call(url, data=json.dumps(image), request_type='PUT')
    if not r.status_code == 200:
        raise RuntimeError("PUT Image Error ({}: {})".format(r.status_code, r.text))
    return r.json()


def _put_layer(image_id, layer_fileobj):
    path = "/v1/images/{image_id}/layer".format(**locals())
    url = urlparse.urljoin(settings.REGISTRY_URL, path)
    r = _api_call(url, data=layer_fileobj.read(), request_type='PUT')
    if not r.status_code == 200:
        raise RuntimeError("PUT Layer Error ({}: {})".format(r.status_code, r.text))
    return r.cookies


def _put_checksum(image, cookies):
    path = "/v1/images/{id}/checksum".format(**image)
    url = urlparse.urljoin(settings.REGISTRY_URL, path)
    tarsum = TarSum(json.dumps(image)).compute()
    headers = {'X-Docker-Checksum': tarsum}
    r = _api_call(url, headers=headers, cookies=cookies, request_type='PUT')
    if not r.status_code == 200:
        raise RuntimeError("PUT Checksum Error ({}: {})".format(r.status_code, r.text))
    print r.json()


def _put_tag(image_id, repository_path, tag):
    path = "/v1/repositories/{repository_path}/tags/{tag}".format(**locals())
    url = urlparse.urljoin(settings.REGISTRY_URL, path)
    r = _api_call(url, data=json.dumps(image_id), request_type='PUT')
    if not r.status_code == 200:
        raise RuntimeError("PUT Tag Error ({}: {})".format(r.status_code, r.text))
    print r.json()


# utility functions


def _construct_env(env, config):
    "Update current environment with latest config"
    new_env = []
    # see if we need to update existing ENV vars
    for e in env:
        k, v = e.split('=', 1)
        if k in config:
            # update values defined by config
            v = config.pop(k)
            new_env.append("{}={}".format(k, v))
    # add other config ENV items
    for k, v in config.items():
        new_env.append("{}={}".format(k, v))
    return new_env


def _new_id():
    "Return 64-char UUID for use as Image ID"
    return ''.join(uuid.uuid4().hex * 2)


def _empty_tar_archive():
    "Return an empty tar archive (in memory)"
    data = cStringIO.StringIO()
    tar = tarfile.open(mode="w", fileobj=data)
    tar.close()
    data.seek(0)
    return data


#
# Below adapted from https://github.com/dotcloud/docker-registry/blob/master/lib/checksums.py
#

def sha256_file(fp, data=None):
    h = hashlib.sha256(data or '')
    if not fp:
        return h.hexdigest()
    while True:
        buf = fp.read(4096)
        if not buf:
            break
        h.update(buf)
    return h.hexdigest()


def sha256_string(s):
    return hashlib.sha256(s).hexdigest()


class TarSum(object):

    def __init__(self, json_data):
        self.json_data = json_data
        self.hashes = []
        self.header_fields = ('name', 'mode', 'uid', 'gid', 'size', 'mtime',
                              'type', 'linkname', 'uname', 'gname', 'devmajor',
                              'devminor')

    def append(self, member, tarobj):
        header = ''
        for field in self.header_fields:
            value = getattr(member, field)
            if field == 'type':
                field = 'typeflag'
            elif field == 'name':
                if member.isdir() and not value.endswith('/'):
                    value += '/'
            header += '{0}{1}'.format(field, value)
        h = None
        try:
            if member.size > 0:
                f = tarobj.extractfile(member)
                h = sha256_file(f, header)
            else:
                h = sha256_string(header)
        except KeyError:
            h = sha256_string(header)
        self.hashes.append(h)

    def compute(self):
        self.hashes.sort()
        data = self.json_data + ''.join(self.hashes)
        tarsum = 'tarsum+sha256:{0}'.format(sha256_string(data))
        return tarsum

########NEW FILE########
__FILENAME__ = coreos
from cStringIO import StringIO
import base64
import os
import random
import re
import subprocess
import time


ROOT_DIR = os.path.join(os.getcwd(), 'coreos')
if not os.path.exists(ROOT_DIR):
    os.mkdir(ROOT_DIR)

MATCH = re.compile('(?P<app>[a-z0-9-]+)_?(?P<version>v[0-9]+)?\.?(?P<c_type>[a-z]+)?.(?P<c_num>[0-9]+)')

class FleetClient(object):

    def __init__(self, cluster_name, hosts, auth, domain, options):
        self.name = cluster_name
        self.hosts = hosts
        self.domain = domain
        self.options = options
        self.auth = auth
        self.auth_path = os.path.join(ROOT_DIR, 'ssh-{cluster_name}'.format(**locals()))
        with open(self.auth_path, 'w') as f:
            f.write(base64.b64decode(auth))
            os.chmod(self.auth_path, 0600)

        self.env = {
            'PATH': '/usr/local/bin:/usr/bin:/bin:{}'.format(
                os.path.abspath(os.path.join(__file__, '..'))),
            'FLEETW_KEY': self.auth_path,
            'FLEETW_HOST': random.choice(self.hosts.split(','))}

    # scheduler setup / teardown

    def setUp(self):
        """
        Setup a CoreOS cluster including router and log aggregator
        """
        return

    def tearDown(self):
        """
        Tear down a CoreOS cluster including router and log aggregator
        """
        return

    # job api

    def create(self, name, image, command='', template=None):
        """
        Create a new job
        """
        print 'Creating {name}'.format(**locals())
        env = self.env.copy()
        self._create_container(name, image, command, template or CONTAINER_TEMPLATE, env)
        self._create_log(name, image, command, LOG_TEMPLATE, env)
        self._create_announcer(name, image, command, ANNOUNCE_TEMPLATE, env)

    def _create_container(self, name, image, command, template, env):
        l = locals().copy()
        l.update(re.match(MATCH, name).groupdict())
        env.update({'FLEETW_UNIT': name + '.service'})
        env.update({'FLEETW_UNIT_DATA': base64.b64encode(template.format(**l))})
        return subprocess.check_call('fleetctl.sh submit {name}.service'.format(**l),
                                     shell=True, env=env)

    def _create_announcer(self, name, image, command, template, env):
        l = locals().copy()
        l.update(re.match(MATCH, name).groupdict())
        env.update({'FLEETW_UNIT': name + '-announce' + '.service'})
        env.update({'FLEETW_UNIT_DATA': base64.b64encode(template.format(**l))})
        return subprocess.check_call('fleetctl.sh submit {name}-announce.service'.format(**l),  # noqa
                                     shell=True, env=env)

    def _create_log(self, name, image, command, template, env):
        l = locals().copy()
        l.update(re.match(MATCH, name).groupdict())
        env.update({'FLEETW_UNIT': name + '-log' + '.service'})
        env.update({'FLEETW_UNIT_DATA': base64.b64encode(template.format(**l))})
        return subprocess.check_call('fleetctl.sh submit {name}-log.service'.format(**locals()),  # noqa
                                     shell=True, env=env)

    def start(self, name):
        """
        Start an idle job
        """
        print 'Starting {name}'.format(**locals())
        env = self.env.copy()
        self._start_container(name, env)
        self._start_log(name, env)
        self._start_announcer(name, env)
        self._wait_for_announcer(name, env)

    def _start_log(self, name, env):
        subprocess.check_call(
            'fleetctl.sh start -no-block {name}-log.service'.format(**locals()),
            shell=True, env=env)

    def _start_container(self, name, env):
        return subprocess.check_call(
            'fleetctl.sh start -no-block {name}.service'.format(**locals()),
            shell=True, env=env)

    def _start_announcer(self, name, env):
        return subprocess.check_call(
            'fleetctl.sh start -no-block {name}-announce.service'.format(**locals()),
            shell=True, env=env)

    def _wait_for_announcer(self, name, env):
        status = None
        for _ in range(60):
            status = subprocess.check_output(
                "fleetctl.sh list-units | grep {name}-announce.service | awk '{{print $5}}'".format(**locals()),
                shell=True, env=env).strip('\n')
            if status == 'running':
                break
            time.sleep(1)
        else:
            raise RuntimeError('Container failed to start')

    def stop(self, name):
        """
        Stop a running job
        """
        print 'Stopping {name}'.format(**locals())
        env = self.env.copy()
        self._stop_announcer(name, env)
        self._stop_container(name, env)
        self._stop_log(name, env)

    def _stop_container(self, name, env):
        return subprocess.check_call(
            'fleetctl.sh stop -block-attempts=600 {name}.service'.format(**locals()),
            shell=True, env=env)

    def _stop_announcer(self, name, env):
        return subprocess.check_call(
            'fleetctl.sh stop -block-attempts=600 {name}-announce.service'.format(**locals()),
            shell=True, env=env)

    def _stop_log(self, name, env):
        return subprocess.check_call(
            'fleetctl.sh stop -block-attempts=600 {name}-log.service'.format(**locals()),
            shell=True, env=env)

    def destroy(self, name):
        """
        Destroy an existing job
        """
        print 'Destroying {name}'.format(**locals())
        env = self.env.copy()
        self._destroy_announcer(name, env)
        self._destroy_container(name, env)
        self._destroy_log(name, env)

    def _destroy_container(self, name, env):
        return subprocess.check_call(
            'fleetctl.sh destroy {name}.service'.format(**locals()),
            shell=True, env=env)

    def _destroy_announcer(self, name, env):
        return subprocess.check_call(
            'fleetctl.sh destroy {name}-announce.service'.format(**locals()),
            shell=True, env=env)

    def _destroy_log(self, name, env):
        return subprocess.check_call(
            'fleetctl.sh destroy {name}-log.service'.format(**locals()),
            shell=True, env=env)

    def run(self, name, image, command):
        """
        Run a one-off command
        """
        print 'Running {name}'.format(**locals())
        output = subprocess.PIPE
        p = subprocess.Popen('fleetrun.sh {command}'.format(**locals()), shell=True, env=self.env,
                             stdout=output, stderr=subprocess.STDOUT)
        rc = p.wait()
        return rc, p.stdout.read()

    def attach(self, name):
        """
        Attach to a job's stdin, stdout and stderr
        """
        return StringIO(), StringIO(), StringIO()

SchedulerClient = FleetClient


CONTAINER_TEMPLATE = """
[Unit]
Description={name}

[Service]
ExecStartPre=/usr/bin/docker pull {image}
ExecStartPre=/bin/sh -c "docker inspect {name} >/dev/null 2>&1 && docker rm -f {name} || true"
ExecStart=/bin/sh -c "port=$(docker inspect -f '{{{{range $k, $v := .config.ExposedPorts }}}}{{{{$k}}}}{{{{end}}}}' {image} | cut -d/ -f1) ; /usr/bin/docker run --name {name} -P -e PORT=$port {image} {command}"
ExecStartPost=/bin/sh -c "until docker inspect {name} >/dev/null 2>&1; do sleep 1; done"; \
    /bin/sh -c "arping -Idocker0 -c1 `docker inspect -f '{{{{ .NetworkSettings.IPAddress }}}}' {name}`"
ExecStop=/usr/bin/docker rm -f {name}
TimeoutStartSec=20m
"""

ANNOUNCE_TEMPLATE = """
[Unit]
Description={name} announce
BindsTo={name}.service

[Service]
EnvironmentFile=/etc/environment
ExecStartPre=/bin/sh -c "until docker inspect -f '{{{{range $i, $e := .HostConfig.PortBindings }}}}{{{{$p := index $e 0}}}}{{{{$p.HostPort}}}}{{{{end}}}}' {name} >/dev/null 2>&1; do sleep 2; done; port=$(docker inspect -f '{{{{range $i, $e := .HostConfig.PortBindings }}}}{{{{$p := index $e 0}}}}{{{{$p.HostPort}}}}{{{{end}}}}' {name}); echo Waiting for $port/tcp...; until netstat -lnt | grep :$port >/dev/null; do sleep 1; done"
ExecStart=/bin/sh -c "port=$(docker inspect -f '{{{{range $i, $e := .HostConfig.PortBindings }}}}{{{{$p := index $e 0}}}}{{{{$p.HostPort}}}}{{{{end}}}}' {name}); echo Connected to $COREOS_PRIVATE_IPV4:$port/tcp, publishing to etcd...; while netstat -lnt | grep :$port >/dev/null; do etcdctl set /deis/services/{app}/{name} $COREOS_PRIVATE_IPV4:$port --ttl 60 >/dev/null; sleep 45; done"
ExecStop=/usr/bin/etcdctl rm --recursive /deis/services/{app}/{name}

[X-Fleet]
X-ConditionMachineOf={name}.service
"""

LOG_TEMPLATE = """
[Unit]
Description={name} log
BindsTo={name}.service

[Service]
ExecStartPre=/bin/sh -c "until /usr/bin/docker inspect {name} >/dev/null 2>&1; do sleep 1; done"
ExecStart=/bin/sh -c "/usr/bin/docker logs -f {name} 2>&1 | logger -p local0.info -t {app}[{c_type}.{c_num}] --udp --server $(etcdctl get /deis/logs/host | cut -d ':' -f1) --port $(etcdctl get /deis/logs/port | cut -d ':' -f2)"

[X-Fleet]
X-ConditionMachineOf={name}.service
"""

########NEW FILE########
__FILENAME__ = faulty
class FaultyClient(object):
    """A faulty scheduler that will always fail"""

    def __init__(self, cluster_name, hosts, auth, domain, options):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def create(self, name, image, command='', template=None, port=5000):
        raise Exception()

    def start(self, name):
        raise Exception()

    def stop(self, name):
        raise Exception()

    def destroy(self, name):
        raise Exception()

    def run(self, name, image, command):
        raise Exception()

    def attach(self, name):
        raise Exception()

SchedulerClient = FaultyClient

########NEW FILE########
__FILENAME__ = mock
from cStringIO import StringIO


class MockSchedulerClient(object):

    def __init__(self, name, hosts, auth, domain, options):
        self.name = name
        self.hosts = hosts
        self.auth = auth
        self.domain = domain
        self.options = options

    # scheduler setup / teardown

    def setUp(self):
        """
        Setup a Cluster including router and log aggregator
        """
        return None

    def tearDown(self):
        """
        Tear down a cluster including router and log aggregator
        """
        return None

    # job api

    def create(self, name, image, command):
        """
        Create a new job
        """
        return {'state': 'inactive'}

    def start(self, name):
        """
        Start an idle job
        """
        return {'state': 'active'}

    def stop(self, name):
        """
        Stop a running job
        """
        return {'state': 'inactive'}

    def destroy(self, name):
        """
        Destroy an existing job
        """
        return {'state': 'inactive'}

    def run(self, name, image, command):
        """
        Run a one-off command
        """
        return 0, ''

    def attach(self, name):
        """
        Attach to a job's stdin, stdout and stderr
        """
        return StringIO(), StringIO(), StringIO()

SchedulerClient = MockSchedulerClient

########NEW FILE########
__FILENAME__ = confd_settings
# security keys and auth tokens
SECRET_KEY = '{{ .deis_controller_secretKey }}'
BUILDER_KEY = '{{ .deis_controller_builderKey }}'

# use the private registry module
REGISTRY_MODULE = 'registry.private'
REGISTRY_URL = '{{ .deis_registry_protocol }}://{{ .deis_registry_host }}:{{ .deis_registry_port }}'  # noqa

# default to sqlite3, but allow postgresql config through envvars
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.{{ .deis_database_engine }}',
        'NAME': '{{ .deis_database_name }}',
        'USER': '{{ .deis_database_user }}',
        'PASSWORD': '{{ .deis_database_password }}',
        'HOST': '{{ .deis_database_host }}',
        'PORT': '{{ .deis_database_port }}',
    }
}

# configure cache
BROKER_URL = 'redis://{{ .deis_cache_host }}:{{ .deis_cache_port }}/0'
CELERY_RESULT_BACKEND = BROKER_URL

# move log directory out of /app/deis
DEIS_LOG_DIR = '/var/log/deis'

{{ if .deis_controller_registrationEnabled }}
REGISTRATION_ENABLED = bool({{ .deis_controller_registrationEnabled }})
{{ end }}

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = gravatar_tags

import hashlib
import urllib

from django import template


register = template.Library()


class GravatarUrlNode(template.Node):

    def __init__(self, email):
        self.email = template.Variable(email)

    def render(self, context):
        try:
            email = self.email.resolve(context)
        except template.VariableDoesNotExist:
            return ''
        # default = 'http://example.com/static/images/defaultavatar.jpg'
        default = 'mm'  # Mystery Man
        size = 24
        return '//www.gravatar.com/avatar/{}?{}'.format(
            hashlib.md5(email.lower()).hexdigest(),
            urllib.urlencode({'d': default, 's': str(size)}))


@register.tag
def gravatar_url(_parser, token):
    try:
        _tag_name, email = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            '{} tag requires a single argument'.format(
                token.contents.split()[0]))
    return GravatarUrlNode(email)

########NEW FILE########
__FILENAME__ = tests
"""
Unit tests for the Deis web app.

Run the tests with "./manage.py test web"
"""

from __future__ import unicode_literals

from django.template import Context
from django.template import Template
from django.template import TemplateSyntaxError
from django.test import TestCase


class WebViewsTest(TestCase):

    fixtures = ['test_web.json']

    def setUp(self):
        self.client.login(username='autotest-1', password='password')

    def test_account(self):
        response = self.client.get('/account/')
        self.assertContains(response, '<title>Deis | Account</title>', html=True)
        self.assertContains(response, 'autotest-1')
        self.assertContains(response, '<img src="//www.gravatar.com/avatar')
        self.assertContains(
            response, '<form method="post" action="/accounts/logout/">')

    def test_dashboard(self):
        response = self.client.get('/')
        self.assertContains(response, '<title>Deis | Dashboard</title>', html=True)
        self.assertContains(
            response,
            r'You have <a href="/clusters/">one cluster</a> and <a href="/apps/">one app</a>.')

    def test_clusters(self):
        response = self.client.get('/clusters/')
        self.assertContains(response, '<title>Deis | Clusters</title>', html=True)
        self.assertContains(response, '<h1>One Cluster</h1>')
        self.assertContains(response, '<h3>autotest-1</h3>')
        self.assertContains(response, '<dt>Owned by</dt>')
        self.assertContains(response, '<dd>autotest-1</dd>')

    def test_apps(self):
        response = self.client.get('/apps/')
        self.assertContains(response, '<title>Deis | Apps</title>', html=True)
        self.assertContains(response, '<h1>One App</h1>')
        self.assertContains(response, '<h3>autotest-1-app</h3>')

    def test_support(self):
        response = self.client.get('/support/')
        self.assertContains(response, '<title>Deis | Support</title>', html=True)
        self.assertContains(response, '<div class="forkImage">')
        self.assertContains(response, '<h2>IRC</h2>')
        self.assertContains(response, '<h2>GitHub</h2>')


class GravatarTagsTest(TestCase):

    def _render_template(self, t, ctx=None):
        """Test that the tag renders a gravatar URL."""
        tmpl = Template(t)
        return tmpl.render(Context(ctx)).strip()

    def test_render(self):
        tmpl = """\
{% load gravatar_tags %}
{% gravatar_url email %}
"""
        rendered = self._render_template(tmpl, {'email': 'github@deis.io'})
        self.assertEquals(
            rendered,
            r'//www.gravatar.com/avatar/058ff74579b6a8fa1e10ab98c990e945?s=24&d=mm')

    def test_render_syntax_error(self):
        """Test that the tag requires one argument."""
        tmpl = """
{% load gravatar_tags %}
{% gravatar_url %}
"""
        self.assertRaises(TemplateSyntaxError, self._render_template, tmpl)

    def test_render_context_error(self):
        """Test that an empty email returns an empty string."""
        tmpl = """
{% load gravatar_tags %}
{% gravatar_url email %}
"""
        rendered = self._render_template(tmpl, {})
        self.assertEquals(rendered, '')

########NEW FILE########
__FILENAME__ = urls
"""
URL patterns and routing for the Deis web app.
"""

from __future__ import unicode_literals

from django.conf.urls import patterns
from django.conf.urls import url


urlpatterns = patterns(
    'web.views',
    url(r'^$', 'dashboard', name='dashboard'),
    url(r'^account/$', 'account', name='account'),
    url(r'^apps/$', 'apps', name='apps'),
    url(r'^clusters/$', 'clusters', name='clusters'),
    url(r'^support/$', 'support', name='support'),
)

########NEW FILE########
__FILENAME__ = views
"""
View classes for presenting Deis web pages.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from api.models import App, Cluster
from deis import __version__


@login_required
def account(request):
    """Return the user's account web page."""
    return render(request, 'web/account.html', {
        'page': 'account',
    })


@login_required
def dashboard(request):
    """Return the user's dashboard web page."""
    apps = App.objects.filter(owner=request.user)
    clusters = Cluster.objects.filter(owner=request.user)
    return render(request, 'web/dashboard.html', {
        'page': 'dashboard',
        'apps': apps,
        'clusters': clusters,
        'version': __version__,
    })


@login_required
def clusters(request):
    """Return the user's clusters web page."""
    clusters = Cluster.objects.filter(owner=request.user)
    return render(request, 'web/clusters.html', {
        'page': 'clusters',
        'clusters': clusters,
    })


@login_required
def apps(request):
    """Return the user's apps web page."""
    apps = App.objects.filter(owner=request.user)
    return render(request, 'web/apps.html', {
        'page': 'apps',
        'apps': apps,
    })


@login_required
def support(request):
    """Return the support ticket system home page."""
    return render(request, 'web/support.html', {
        'page': 'support',
    })

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# deis documentation build configuration file, created by
# sphinx-quickstart on Fri Jul 26 12:12:00 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

# Some hackery here to get deis.py to be importable as client.deis
open(os.path.join('..', '__init__.py'), 'a')
sys.path.insert(0, os.path.abspath(os.path.join('..')))
sys.path.insert(0, os.path.abspath(os.path.join('..', 'controller')))
# create local_settings.py for SECRET_KEY if necessary
local_settings_path = os.path.abspath(
    os.path.join('..', 'controller', 'deis', 'local_settings.py'))
if not os.path.exists(local_settings_path):
    with open(local_settings_path, 'w') as local_settings:
        local_settings.write("SECRET_KEY = 'DummySecretKey'\n")
# set up Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'deis.settings'
from django.conf import settings  # noqa

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.autosummary',
              'sphinx.ext.viewcode', 'sphinxcontrib.httpdomain']

# default flags for auto-generated python code documetation
autodoc_default_flags = ['members', 'undoc-members']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'toctree'

# General information about the project.
project = u'deis'
copyright = u'2013, OpDemand LLC'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
from deis import __version__

# The short X.Y version.
version = __version__.rsplit('.', 1)[0]
# The full version, including alpha/beta/rc tags.
release = __version__

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
exclude_patterns = ['_build', 'venv']

# The reST default role (used for this markup: `text`) to use for all documents.
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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'deis'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['theme']

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
html_static_path = ['../controller/web/static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

html_add_permalinks = True

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
htmlhelp_basename = 'deisdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ('index', 'deis.tex', u'deis Documentation',
     u'Author', 'manual'),
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


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'deis', u'deis Documentation',
     [u'Author'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'deis', u'deis Documentation',
     u'Author', 'deis', 'One line description of project.',
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


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'deis'
epub_author = u'OpDemand LLC'
epub_publisher = u'OpDemand LLC'
epub_copyright = u'2013, OpDemand LLC'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# A sequence of (type, uri, title) tuples for the guide element of content.opf.
#epub_guide = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

# Fix unsupported image types using the PIL.
#epub_fix_images = False

# Scale large images.
#epub_max_image_width = 0

# If 'no', URL addresses will not be shown.
#epub_show_urls = 'inline'

# If false, no index is generated.
#epub_use_index = True

########NEW FILE########
