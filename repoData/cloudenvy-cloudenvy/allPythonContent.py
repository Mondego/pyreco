__FILENAME__ = ec2
import collections
import time
import urlparse

import boto.ec2.connection


Server = collections.namedtuple('Server', ['id', 'name'])
Image = collections.namedtuple('Image', ['id', 'name'])


class CloudAPI(object):
    def __init__(self, config):
        self._client = None
        self.config = config

        ec2_endpoint = self.config.user_config['cloud'].get('ec2_endpoint', None)
        self.endpoint = urlparse.urlparse(ec2_endpoint)
        self.access_key = self.config.user_config['cloud'].get('ec2_access_key', None)
        self.secret_key = self.config.user_config['cloud'].get('ec2_secret_key', None)
        self.region_name = self.config.user_config['cloud'].get('ec2_region_name', 'RegionOne')

    @property
    def client(self):
        if not self._client:
            region = boto.ec2.regioninfo.RegionInfo(
                    name=self.region_name, endpoint=self.endpoint.hostname)

            kwargs = {
                'aws_access_key_id': self.access_key,
                'aws_secret_access_key': self.secret_key,
                'is_secure': self.endpoint.scheme == 'https',
                'host': self.endpoint.hostname,
                #'port': self.endpoint.port,
                'path': self.endpoint.path,
                'validate_certs': False,
                'region': region,
            }
            self._client = boto.ec2.connection.EC2Connection(**kwargs)
        return self._client

    @staticmethod
    def _instance_to_dict(instance):
        return Server(id=instance.id, name=instance.tags.get('Name', ''))

    @staticmethod
    def _image_to_dict(image):
        return Image(id=image.id, name=image.id)

    def is_server_active(self, server_id):
        inst = self._get_server(server_id)
        return inst.state == 'running'

    def is_network_active(self, server_id):
        inst = self._get_server(server_id)
        return bool(inst.ip_address)

    def list_servers(self):
        instances = self.client.get_only_instances(filters={'instance-state-name': 'running'})
        return [self._instance_to_dict(inst) for inst in instances]

    def find_server(self, name):
        servers = self.list_servers()
        for server in servers:
            if server.name == name:
                return server

    def _get_server(self, server_id):
        instances = self.client.get_only_instances([server_id])
        return instances[0] if instances else None

    def get_server(self, server_id):
        inst = self._get_server(server_id)
        return self._instance_to_dict(inst) if inst else None

    def create_server(self, *args, **kwargs):
        name = kwargs.pop('name')
        image = kwargs.pop('image')
        flavor = kwargs.pop('flavor')
        meta = kwargs.pop('meta', {})
        security_groups = kwargs.pop('security_groups')
        key_name = kwargs.pop('key_name')

        _kwargs = {
            'key_name': key_name,
            'security_groups': security_groups,
            'instance_type': flavor,
        }

        image = self._find_image(image.id)
        reservation = image.run(**_kwargs)
        instance = reservation.instances[0]
        status = instance.update()

        for i in xrange(60):
            status = instance.update()
            if status == 'running':
                break
            time.sleep(1)
        else:
            raise

        instance.add_tag('Name', name)

        return self._instance_to_dict(instance)

    def setup_network(self, server_id):
        #NOTE(bcwaldon): We depend on EC2 to do this for us today
        return

    def find_ip(self, server_id):
        instance = self._get_server(server_id)
        return instance.ip_address

    def _find_image(self, image_id):
        #NOTE(bcwaldon): This only works with image ids for now
        return self.client.get_image(image_id)

    def find_image(self, search_str):
        image = self._find_image(search_str)
        return self._image_to_dict(image)

    def snapshot(self, server, name):
        raise NotImplementedError()

    def find_flavor(self, name):
        return name

    def _find_security_group(self, name):
        try:
            return self.client.get_all_security_groups([name])[0]
        except boto.exception.EC2ResponseError:
            return None

    def find_security_group(self, name):
        sg = self._find_security_group(name)
        return name if sg else None

    def create_security_group(self, name):
        self.client.create_security_group(name, name)
        return name

    def create_security_group_rule(self, name, rule):
        sg = self._find_security_group(name)
        if not sg:
            raise

        try:
            sg.authorize(*rule)
        except boto.exception.EC2ResponseError:
            pass

    def find_keypair(self, name):
        return self.client.get_key_pair(name)

    def create_keypair(self, name, key_data):
        self.client.import_key_pair(name, key_data)

    def delete_server(self, server):
        self.client.terminate_instances([server.id])

########NEW FILE########
__FILENAME__ = openstack
# vim: tabstop=4 shiftwidth=4 softtabstop=4
import functools
import getpass
import logging
import time
import uuid

import novaclient.exceptions
import novaclient.client

from cloudenvy import exceptions

def not_found(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except novaclient.exceptions.NotFound:
            return None
    return wrapped


def bad_request(func):
    """decorator to wrap novaclient functions that may return a
    400 'BadRequest' exception when the endpoint is unavailable or
    unable to be resolved.
    """
    #novaclient.exceptions.BadRequest
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except novaclient.exceptions.BadRequest as xcpt:
            logging.error("Unable to communicate with endpoints: "
                          "Received 400/Bad Request from OpenStack: " +
                          str(xcpt))
            exit()
    return wrapped


def retry_on_overlimit(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except novaclient.exceptions.OverLimit as exc:
            retry_time = getattr(exc, 'retry_after', 0)
            if not retry_time:
                logging.fatal('Unable to allocate resource: %s' % exc.message)
                raise SystemExit()

            logging.debug('Request was limited, retrying in %s seconds: %s'
                          % (retry_time, exc.message))
            time.sleep(retry_time)

            try:
                return func(*args, **kwargs)
            except novaclient.exceptions.OverLimit as exc:
                logging.fatal('Unable to allocate resource: %s' % exc.message)
                raise SystemExit()

    return wrapped


class CloudAPI(object):
    def __init__(self, config):
        self._client = None
        self.config = config

        #NOTE(bcwaldon): This was just dumped here to make room for EC2.
        # Clean it up!
        for item in ['os_username', 'os_tenant_name', 'os_auth_url']:
            try:
                config.user_config['cloud'][item]
            except KeyError:
                raise SystemExit("Ensure '%s' is set in user config" % item)

        try:
            password = config.user_config['cloud']['os_password']
        except KeyError:
            username = config.user_config['cloud']['os_username']
            prompt = "Password for account '%s': " % username
            password = getpass.getpass(prompt)
            config.user_config['cloud']['os_password'] = password

        # OpenStack Auth Items
        self.user = self.config.user_config['cloud'].get('os_username', None)
        self.password = self.config.user_config['cloud'].get('os_password', None)
        self.tenant_name = self.config.user_config['cloud'].get('os_tenant_name',
                                                         None)
        self.auth_url = self.config.user_config['cloud'].get('os_auth_url', None)
        self.region_name = self.config.user_config['cloud'].get('os_region_name',
                                                         None)

    @property
    def client(self):
        if not self._client:
            self._client = novaclient.client.Client(
                '2',
                self.user,
                self.password,
                self.tenant_name,
                self.auth_url,
                no_cache=True,
                region_name=self.region_name)
        return self._client

    def is_server_active(self, server_id):
        server = self.get_server(server_id)
        return server.status == 'ACTIVE'

    def is_network_active(self, server_id):
        server = self.get_server(server_id)
        return len(server.networks) > 0

    @bad_request
    def list_servers(self):
        return self.client.servers.list()

    @bad_request
    @not_found
    def find_server(self, name):
        return self.client.servers.find(name=name)

    @bad_request
    @not_found
    def get_server(self, server_id):
        return self.client.servers.get(server_id)

    @retry_on_overlimit
    @bad_request
    def create_server(self, *args, **kwargs):
        kwargs.setdefault('meta', {})
        #TODO(gabrielhurley): Allow user-defined server metadata, see
        #https://github.com/cloudenvy/cloudenvy/issues/125 for more info.
        kwargs['meta']['os_auth_url'] = self.auth_url

        return self.client.servers.create(*args, **kwargs)

    def setup_network(self, server_id):
        server = self.get_server(server_id)

        try:
            floating_ip = self._find_free_ip()
        except exceptions.NoIPsAvailable:
            logging.info('Allocating a new floating ip to project.')
            self._allocate_floating_ip()
            floating_ip = self._find_free_ip()

        logging.info('Assigning floating ip %s to server.', floating_ip)
        self._assign_ip(server, floating_ip)

    @bad_request
    def _find_free_ip(self):
        fips = self.client.floating_ips.list()
        for fip in fips:
            if not fip.instance_id:
                return fip.ip
        raise exceptions.NoIPsAvailable()

    @bad_request
    def find_ip(self, server_id):
        fips = self.client.floating_ips.list()
        for fip in fips:
            if fip.instance_id == server_id:
                return fip.ip

    @retry_on_overlimit
    @bad_request
    def _assign_ip(self, server, ip):
        server.add_floating_ip(ip)

    @bad_request
    @not_found
    def find_image(self, search_str):
        try:
            return self.client.images.find(name=search_str)
        except novaclient.exceptions.NotFound:
            pass

        try:
            #NOTE(bcwaldon): We can't guarantee all images use UUID4 for their
            # image ID format, but this is the only way to get around issue
            # 69 (https://github.com/cloudenvy/cloudenvy/issues/69) for now.
            # Novaclient should really block us from requesting an image by
            # ID that's actually a human-readable name (with spaces in it).
            uuid.UUID(search_str)
            return self.client.images.get(search_str)
        except (ValueError, novaclient.exceptions.NotFound):
            raise SystemExit('Image `%s` could not be found.' % search_str)

    @retry_on_overlimit
    @bad_request
    def snapshot(self, server, name):
        return self.client.servers.create_image(server, name)

    @bad_request
    @not_found
    def find_flavor(self, name):
        return self.client.flavors.find(name=name)

    @bad_request
    @not_found
    def find_security_group(self, name):
        return self.client.security_groups.find(name=name)

    @retry_on_overlimit
    @bad_request
    @not_found
    def create_security_group(self, name):
        return self.client.security_groups.create(name, name)

    @retry_on_overlimit
    def create_security_group_rule(self, security_group, rule):
        try:
            return self.client.security_group_rules.create(
                security_group.id, *rule)
        except novaclient.exceptions.BadRequest:
            logging.info('Security Group Rule "%s" already exists.' %
                         str(rule))

    @retry_on_overlimit
    @bad_request
    def _allocate_floating_ip(self):
        return self.client.floating_ips.create()

    @bad_request
    @not_found
    def find_keypair(self, name):
        return self.client.keypairs.find(name=name)

    @retry_on_overlimit
    @bad_request
    def create_keypair(self, name, key_data):
        return self.client.keypairs.create(name, public_key=key_data)

    def delete_server(self, server):
        server.delete()

########NEW FILE########
__FILENAME__ = destroy
import logging

import cloudenvy.core


class Destroy(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Destroy an Envy.'
        subparser = subparsers.add_parser('destroy', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')

        #TODO(bcwaldon): design a better method for command aliases
        help_str = 'Alias for destroy command.'
        subparser = subparsers.add_parser('down', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')

        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if envy.find_server():
            envy.delete_server()
            logging.info('Deletion of Envy \'%s\' was triggered.' % envy.name)
            while envy.find_server():
                logging.info("... still waiting")
            logging.info("Done!")

        else:
            logging.error('Could not find Envy named \'%s\'.' % envy.name)

########NEW FILE########
__FILENAME__ = dotfiles
import logging
import tarfile
import tempfile
import os

import fabric.api
import fabric.operations

import cloudenvy.core


class Dotfiles(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Upload dotfiles from your local machine to an Envy.'
        subparser = subparsers.add_parser('dotfiles', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')
        subparser.add_argument('-f', '--files', action='store',
                               help='Limit operation to a specific list of '
                                    'comma-separated files.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if envy.ip():
            host_string = '%s@%s' % (envy.config.remote_user, envy.ip())

            temp_tar = tempfile.NamedTemporaryFile(delete=True)

            with fabric.api.settings(host_string=host_string):
                if args.files:
                    dotfiles = args.files.split(',')
                else:
                    dotfiles = config['defaults']['dotfiles'].split(',')

                dotfiles = [dotfile.strip() for dotfile in dotfiles]

                with tarfile.open(temp_tar.name, 'w') as archive:
                    for dotfile in dotfiles:
                        path = os.path.expanduser('~/%s' % dotfile)
                        if os.path.exists(path):
                            if not os.path.islink(path):
                                archive.add(path, arcname=dotfile)

                fabric.operations.put(temp_tar, '~/dotfiles.tar')
                fabric.operations.run('tar -xvf ~/dotfiles.tar')
        else:
            logging.error('Could not determine IP.')

########NEW FILE########
__FILENAME__ = files
import logging
import time
import os

import fabric.api
import fabric.operations

import cloudenvy.core


class Files(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Upload arbitrary files from your local machine to an ' \
                   'Envy. Uses the `files` hash in your Envyfile. Mirrors ' \
                   'the local mode of the file.'
        subparser = subparsers.add_parser('files', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if envy.ip():
            host_string = '%s@%s' % (envy.config.remote_user, envy.ip())

            with fabric.api.settings(host_string=host_string):
                use_sudo = envy.config.project_config.get('files_use_sudo', True)
                files = envy.config.project_config.get('files', {}).items()
                files = [(os.path.expanduser(loc), rem) for loc, rem in files]

                for local_path, remote_path in files:
                    logging.info("Copying file from '%s' to '%s'",
                                 local_path, remote_path)

                    if not os.path.exists(local_path):
                        logging.error("Local file '%s' not found.", local_path)

                    dest_dir = _parse_directory(remote_path)
                    if dest_dir:
                        self._create_directory(dest_dir)
                    self._put_file(local_path, remote_path, use_sudo)

        else:
            logging.error('Could not determine IP.')

    def _create_directory(self, remote_dir):
        for i in range(24):
            try:
                fabric.operations.run('mkdir -p %s' % remote_dir)
                break
            except fabric.exceptions.NetworkError:
                logging.debug("Unable to create directory '%s'. "
                              "Trying again in 10 seconds." % remote_dir)
                time.sleep(10)

    def _put_file(self, local_path, remote_path, use_sudo):
        for i in range(24):
            try:
                fabric.operations.put(local_path, remote_path,
                                      mirror_local_mode=True,
                                      use_sudo=use_sudo)
                break
            except fabric.exceptions.NetworkError as err:
                logging.debug("Unable to upload the file from '%s': %s. "
                              "Trying again in 10 seconds." %
                              (local_path, err))
                time.sleep(10)


def _parse_directory(path):
    """Given a valid unix path, return the directory

    This will not expand a ~ to a home directory or
    prepend that home directory to a relative path.
    """
    if path is None or '/' not in path:
        return None
    else:
        return os.path.dirname(path)

########NEW FILE########
__FILENAME__ = init
import logging
import os

import cloudenvy.core


project_file = """project_config:
  name: %(name)s

  # ID or name of image
  image: %(image)s

  # Remote VM user
  #remote_user: ubuntu

  # Compute flavor to use
  #flavor_name: m1.small

  # Control automatic provisioning of environment
  #auto_provision: False

  # List of scripts used to provision environment
  #provision_scripts:
  #  - provision.sh
"""


class Init(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Initialize a new cloudenvy project.'
        subparser = subparsers.add_parser('init', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument(
            '-n', '--name', required=True,
            help='Name of new cloudenvy project'
        )
        subparser.add_argument(
            '-i', '--image', required=True,
            help='Name or ID of image to use for cloudenvy project'
        )

        return subparser

    def run(self, config, args):
        paths = [
            'Envyfile',
            'Envyfile.yml',
        ]

        for path in paths:
            if os.path.isfile(path):
                logging.error("A project file already exists. Please "
                              "remove %s it and run init again." % path)

        with open('Envyfile.yml', 'w') as fap:
            fap.write(project_file % {'name': args.name, 'image': args.image})

        logging.info("Created Envyfile.yml for new project '%s'", args.name)

########NEW FILE########
__FILENAME__ = ip
import logging

import cloudenvy.core


class Ip(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Print IPv4 address of Envy.'
        subparser = subparsers.add_parser('ip', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if not envy.server():
            logging.error('Envy is not running.')
        elif envy.ip():
            print envy.ip()
        else:
            logging.error('Could not determine IP.')

########NEW FILE########
__FILENAME__ = list
import cloudenvy.core


class List(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'List all Envys in your current project.'
        subparser = subparsers.add_parser('list', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        for server in envy.list_servers():
            if server.name.startswith(envy.name):
                print server.name[len(envy.name)+1:] or '(default)'

########NEW FILE########
__FILENAME__ = provision
import logging
import os
import time

import fabric.api
import fabric.operations

import cloudenvy.core


class Provision(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Upload and execute script(s) in your Envy.'
        subparser = subparsers.add_parser('provision', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')
        subparser.add_argument('-s', '--scripts', nargs='*', metavar='PATH',
                               help='Specify one or more scripts.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        logging.info('Running provision scripts for Envy \'%s\'.' %
                     envy.name)
        if not envy.ip():
            logging.error('Could not determine IP.')
            return

        with fabric.api.settings(
                host_string=envy.ip(), user=envy.config.remote_user,
                forward_agent=True, disable_known_hosts=True):

            if args.scripts:
                scripts = [os.path.expanduser(script) for
                           script in args.scripts]
            elif 'provision_scripts' in envy.config.project_config:
                scripts = [os.path.expanduser(script) for script in
                           envy.config.project_config['provision_scripts']]
            elif 'provision_script_path' in envy.config.project_config:
                provision_script = envy.config.project_config['provision_script_path']
                scripts = [os.path.expanduser(provision_script)]
            else:
                raise SystemExit('Please specify the path to your provision '
                                 'script(s) by either using the `--scripts` '
                                 'flag, or by defining the `provision_scripts`'
                                 ' config option in your Envyfile.')

            for script in scripts:
                logging.info('Running provision script from \'%s\'', script)

                for i in range(24):
                    try:
                        path = script
                        filename = os.path.basename(script)
                        remote_path = '~/%s' % filename
                        fabric.operations.put(path, remote_path, mode=0755)
                        fabric.operations.run(remote_path)
                        break
                    except fabric.exceptions.NetworkError:
                        logging.debug(
                            'Unable to upload the provision script '
                            'from `%s`. Trying again in 10 seconds.' % path
                        )
                        time.sleep(10)
                logging.info('Provision script \'%s\' finished.' % path)

########NEW FILE########
__FILENAME__ = run
import logging

import fabric.api
import fabric.operations

import cloudenvy.core


class Run(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Execute a command in your Envy.'
        subparser = subparsers.add_parser('run', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('command', help='Command to execute remotely.')
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if envy.ip():
            host_string = '%s@%s' % (envy.config.remote_user, envy.ip())
            with fabric.api.settings(host_string=host_string):
                fabric.operations.run(args.command)
        else:
            logging.error('Could not determine IP.')

########NEW FILE########
__FILENAME__ = scp
import logging

import fabric.api
import fabric.operations
import os

import cloudenvy.core


class Scp(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Copy file(s) into your Envy.'
        subparser = subparsers.add_parser('scp', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument(
            'source', nargs='?', default=os.getcwd(),
            help='Local path to copy into your Envy.'
        )
        subparser.add_argument(
            'target', nargs='?', default='~/',
            help='Location in your Envy to place file(s). Non-absolute '
            'paths are interpreted relative to remote_user homedir.'
        )
        subparser.add_argument(
            '-n', '--name', action='store', default='',
            help='Specify custom name for an Envy.'
        )
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if not envy.ip():
            logging.error('Could not determine IP.')
            return

        host_string = '%s@%s' % (envy.config.remote_user, envy.ip())

        with fabric.api.settings(host_string=host_string):
            fabric.operations.put(
                args.source, args.target, mirror_local_mode=True
            )

########NEW FILE########
__FILENAME__ = snapshot
import cloudenvy.core


class Snapshot(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Snapshot your Envy.'
        subparser = subparsers.add_parser('snapshot', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')

        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)
        envy.snapshot('%s-snapshot' % envy.name)

########NEW FILE########
__FILENAME__ = ssh
import logging

import fabric.api
import fabric.operations

import cloudenvy.core


class Ssh(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'SSH into your Envy.'
        subparser = subparsers.add_parser('ssh', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if envy.ip():
            disable_known_hosts = ('-o UserKnownHostsFile=/dev/null'
                                   ' -o StrictHostKeyChecking=no')
            forward_agent = '-o ForwardAgent=yes'

            options = [disable_known_hosts]
            if envy.config.forward_agent:
                options.append(forward_agent)

            fabric.operations.local('ssh %s %s@%s' % (' '.join(options),
                                                      envy.config.remote_user,
                                                      envy.ip()))
        else:
            logging.error('Could not determine IP.')

########NEW FILE########
__FILENAME__ = up
import logging

from cloudenvy import exceptions
import cloudenvy.core


class Up(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Create and optionally provision an Envy.'
        subparser = subparsers.add_parser('up', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')
        subparser.add_argument('-s', '--scripts', nargs='*', metavar='PATH',
                               default=None,
                               help='Override provision_script_paths option '
                                    'in project config.')
        subparser.add_argument('--no-files', action='store_true',
                               help='Prevent files from being uploaded')
        subparser.add_argument('--no-provision', action='store_true',
                               help='Prevent provision scripts from running.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if not envy.server():
            logging.info('Triggering Envy boot.')
            try:
                envy.build_server()
            except exceptions.ImageNotFound:
                logging.error('Could not find image.')
                return
            except exceptions.NoIPsAvailable:
                logging.error('Could not find available IP.')
                return
        if not args.no_files:
            self.commands['files'].run(config, args)
        if not args.no_provision \
                and (envy.config.project_config.get("auto_provision", True)
                     and 'provision_scripts' in envy.config.project_config):
            try:
                self.commands['provision'].run(config, args)
            except SystemExit:
                raise SystemExit('You have not specified any provision '
                                 'scripts in your Envyfile. '
                                 'If you would like to run your Envy '
                                 'without a provision script; use the '
                                 '`--no-provision` command line flag.')
        if envy.ip():
            print envy.ip()
        else:
            logging.error('Could not determine IP.')

########NEW FILE########
__FILENAME__ = config
import getpass
import logging
import os
import sys
import os.path
import yaml

CONFIG_DEFAULTS = {
    'defaults': {
        'keypair_name': getpass.getuser(),
        'keypair_location': os.path.expanduser('~/.ssh/id_rsa.pub'),
        'flavor_name': 'm1.small',
        'remote_user': 'ubuntu',
        'auto_provision': False,
        'forward_agent': True,
        'default_cloud': None,
        'dotfiles': '.vimrc, .gitconfig, .gitignore, .screenrc',
        'sec_groups': [
            'icmp, -1, -1, 0.0.0.0/0',
            'tcp, 22, 22, 0.0.0.0/0',
        ]
    }
}


class EnvyConfig(object):

    def __init__(self, config):
        self.base_name = config['project_config'].get('base_name')
        self.config = config
        self.user_config = config['cloudenvy']
        self.project_config = config['project_config']
        self.default_config = config['defaults']

        image_name = self.project_config.get('image_name')
        image_id = self.project_config.get('image_id', None)
        image = self.project_config.get('image')
        self.image = image_name or image_id or image

        self.flavor = self.project_config.get(
            'flavor_name', self.default_config['flavor_name'])
        self.remote_user = self.project_config.get(
            'remote_user', self.default_config['remote_user'])
        self.auto_provision = self.project_config.get('auto_provision', False)
        self.sec_group_name = self.project_config.get('sec_group_name',
                                                      self.base_name)

        self.keypair_name = self._get_config('keypair_name')
        self.keypair_location = self._get_config('keypair_location')
        self.forward_agent = self._get_config('forward_agent')

        self.cloud_type = 'openstack' if 'os_auth_url' in self.user_config['cloud'] else 'ec2'

    def _get_config(self, name, default=None):
        """Traverse the various config files in order of specificity.

        The order is as follows, most important (specific) to least:
            Project
            Cloud
            User
            Default
        """
        value = self.project_config.get(
            name,
            self.user_config['cloud'].get(
                name,
                self.user_config.get(
                    name,
                    self.default_config.get(name,
                                            default))))
        return value


class Config(object):
    """Base class for envy commands"""

    def __init__(self, args):
        self.args = args
        self.config = None

    def __getitem__(self, item):
        if not self.config:
            self.config = self.get_config()
        return self.config[item]

    def __setitem__(self, item, value):
        if not self.config:
            self.config = self.get_config()
        self.config[item] = value

    def _set_working_cloud(self, cloud_name, config):
        """Sets which cloud to operate on based on config values and parameters
        """
        try:
            known_clouds = config['cloudenvy']['clouds'].keys()
        except (KeyError, AttributeError):
            logging.error('No clouds defined in config file')
            sys.exit(1)

        if cloud_name in known_clouds:
            config['cloudenvy'].update(
                {'cloud': config['cloudenvy']['clouds'][cloud_name]})
        else:
            logging.error("Cloud %s is not found in your config" % cloud_name)
            logging.debug(
                "Clouds Found %s" % ", ".join(
                    config['cloudenvy']['clouds'].keys()
                )
            )
            sys.exit(1)

    def get_config(self):
        args = self.args

        #NOTE(jakedahn): By popular request yml file extension is supported,
        #                but optional... for now.
        if os.path.isfile(os.path.expanduser('~/.cloudenvy')):
            user_config_path = os.path.expanduser('~/.cloudenvy')
        else:
            user_config_path = os.path.expanduser('~/.cloudenvy.yml')

        if os.path.isfile('./Envyfile'):
            project_config_path = './Envyfile'
        else:
            project_config_path = './Envyfile.yml'

        self._check_config_files(user_config_path, project_config_path)

        user_config = yaml.load(open(user_config_path))
        project_config = yaml.load(open(project_config_path))

        config = dict(CONFIG_DEFAULTS.items() + project_config.items()
                      + user_config.items())

        #TODO(jakedahn): I think this is stupid, there is probably a better way
        # Update config dict with which cloud to use.
        if args.cloud:
            # If a specific cloud is requested, use it.
            self._set_working_cloud(args.cloud, config)
        elif config['cloudenvy'].get('default_cloud'):
            # If no specific cloud is requested, try the default.
            cloud_name = config['cloudenvy']['default_cloud']
            self._set_working_cloud(cloud_name, config)
        else:
            try:
                num_clouds = len(config['cloudenvy']['clouds'].keys())
            except (KeyError, TypeError, AttributeError):
                logging.error('Unable to parse clouds from config file')
                sys.exit(1)

            if num_clouds == 0:
                logging.error('No clouds defined in config file')
                sys.exit(1)
            elif num_clouds > 1:
                logging.error('Define default_cloud in your cloudenvy config '
                              'or specify the --cloud flag')
                sys.exit(1)

            # No explicit cloud defined, but there's only one so we can
            # safely default to that.
            cloud_name = config['cloudenvy']['clouds'].keys()[0]
            self._set_working_cloud(cloud_name, config)

        self._validate_config(config, user_config_path, project_config_path)

        base_name = config['project_config']['name']
        try:
            envy_name = args.name
            assert envy_name
        except (AssertionError, AttributeError):
            pass
        else:
            config['project_config']['name'] = '%s-%s' % (base_name, envy_name)
        finally:
            config['project_config']['base_name'] = base_name

        if 'keypair_location' in config['cloudenvy']:
            full_path = os.path.expanduser(
                config['cloudenvy']['keypair_location']
            )
            config['cloudenvy']['keypair_location'] = full_path

        return config

    def _validate_config(self, config, user_config_path, project_config_path):
        if 'image_name' in config['project_config']:
            logging.warning(
                'Please note that using `image_name` option in your Envyfile '
                'has been deprecated. Please use the `image` option instead. '
                '`image_name` will no longer be supported as of December 01, '
                '2012.'
            )
        if 'image_id' in config['project_config']:
            logging.warning(
                'Please note that using `image_id` option in your Envyfile '
                'has been deprecated. Please use the `image` option instead. '
                '`image_id` will no longer be supported as of December 01, '
                ' 2012.'
            )

        try:
            config['project_config']['name']
        except KeyError:
            raise SystemExit("Ensure 'name' is set in %s"
                             % project_config_path)

    def _check_config_files(self, user_config_path, project_config_path):
        if not os.path.exists(user_config_path):
            raise SystemExit('Could not read `%s`. Make sure '
                             '~/.cloudenvy has the proper configuration.'
                             % user_config_path)
        if not os.path.exists(project_config_path):
            raise SystemExit('Could not read `%s`. Make sure you '
                             'have an Envyfile in your current directory.'
                             % project_config_path)

########NEW FILE########
__FILENAME__ = core
# vim: tabstop=4 shiftwidth=4 softtabstop=4
import logging
import novaclient
import time

import cloudenvy.clouds
from cloudenvy import exceptions


class Envy(object):
    def __init__(self, config):
        self.config = config
        self.name = config.project_config.get('name')

        cls = cloudenvy.clouds.get_api_cls(self.config.cloud_type)
        self.cloud_api = cls(config)

        self._server = None
        self._ip = None

    def list_servers(self):
        return self.cloud_api.list_servers()

    def find_server(self):
        return self.cloud_api.find_server(self.name)

    def delete_server(self):
        self.cloud_api.delete_server(self.server())
        self._server = None

    def server(self):
        if not self._server:
            self._server = self.find_server()
        return self._server

    def ip(self):
        if self.server():
            if not self._ip:
                self._ip = self.cloud_api.find_ip(self.server().id)
            return self._ip
        else:
            raise SystemExit('The ENVy you specified (`%s`) does not exist. '
                             'Try using the -n flag to specify an ENVy name.'
                             % self.name)

    def build_server(self):
        logging.info("Using image: %s" % self.config.image)
        try:
            image = self.cloud_api.find_image(self.config.image)
        except novaclient.exceptions.NoUniqueMatch:
            msg = ('There are more than one images named %s. Please specify '
                   'image id in your config.')
            raise SystemExit(msg % self.config.image)
        if not image:
            raise SystemExit('The image %s does not exist.' %
                             self.config.image)
        flavor = self.cloud_api.find_flavor(self.config.flavor)
        if not flavor:
            raise SystemExit('The flavor %s does not exist.' %
                             self.config.flavor)
        build_kwargs = {
            'name': self.name,
            'image': image,
            'flavor': flavor,
        }

        logging.info('Using security group: %s', self.config.sec_group_name)
        self._ensure_sec_group_exists(self.config.sec_group_name)
        build_kwargs['security_groups'] = [self.config.sec_group_name]

        if self.config.keypair_name is not None:
            logging.info('Using keypair: %s', self.config.keypair_name)
            self._ensure_keypair_exists(self.config.keypair_name,
                                        self.config.keypair_location)
            build_kwargs['key_name'] = self.config.keypair_name

        #TODO(jakedahn): Reintroduce this as a 'cloudconfigdrive' config flag.
        # if self.project_config['userdata_path']:
        #     userdata_path = self.project_config['userdata_path']
        #     logging.info('Using userdata from: %s', userdata_path)
        #     build_kwargs['user_data'] = userdata_path

        logging.info('Creating server...')
        server = self.cloud_api.create_server(**build_kwargs)

        server_id = server.id

        def server_ready(server):
            return self.cloud_api.is_server_active(server.id)

        def network_ready(server):
            return self.cloud_api.is_network_active(server.id)

        def wait_for_condition(condition_func, fail_msg):
            for i in xrange(60):
                _server = self.cloud_api.get_server(server_id)
                if condition_func(_server):
                    return True
                else:
                    time.sleep(1)
            else:
                raise exceptions.Error(fail_msg)

        wait_for_condition(server_ready, 'Server was not ready in time')

        self.cloud_api.setup_network(server_id)

        wait_for_condition(network_ready, 'Network was not ready in time')

    def _ensure_sec_group_exists(self, name):
        sec_group = self.cloud_api.find_security_group(name)

        if not sec_group:
            try:
                sec_group = self.cloud_api.create_security_group(name)
            except novaclient.exceptions.BadRequest:
                logging.error('Security Group "%s" already exists.' % name)

        if 'sec_groups' in self.config.project_config:
            rules = [tuple(rule.split(', ')) for rule in
                     self.config.project_config['sec_groups']]
        else:
            rules = [tuple(rule.split(', ')) for rule in
                     self.config.default_config['sec_groups']]
        for rule in rules:
            logging.debug('... adding rule: %s', rule)
            logging.info('Creating Security Group Rule %s' % str(rule))
            self.cloud_api.create_security_group_rule(sec_group, rule)

        logging.info('...done.')

    def _ensure_keypair_exists(self, name, pubkey_location):
        if not self.cloud_api.find_keypair(name):
            logging.info('No keypair named %s found, creating...', name)
            logging.debug('...using key at %s', pubkey_location)
            fap = open(pubkey_location, 'r')
            data = fap.read()
            logging.debug('...contents:\n%s', data)
            fap.close()
            self.cloud_api.create_keypair(name, data)
            logging.info('...done.')

    def snapshot(self, name):
        if not self.server():
            logging.error('Environment has not been created.\n'
                          'Try running `envy up` first?')
        else:
            logging.info('Creating snapshot %s...', name)
            self.cloud_api.snapshot(self.server(), name)
            logging.info('...done.')
            print name


class Command(object):

    def __init__(self, argparser, commands):
        self.commands = commands
        self._build_subparser(argparser)

    def _build_subparser(self, subparser):
        return subparser

    def run(self, config, args):
        return

########NEW FILE########
__FILENAME__ = exceptions
# vim: tabstop=4 shiftwidth=4 softtabstop=4


class Error(RuntimeError):
    pass


class ImageNotFound(Error):
    pass


class SnapshotFailure(Error):
    pass


class FixedIPAssignFailure(Error):
    pass


class FloatingIPAssignFailure(Error):
    pass


class NoIPsAvailable(Error):
    pass


class UserConfigNotPresent(Error):
    pass

########NEW FILE########
__FILENAME__ = main
# vim: tabstop=4 shiftwidth=4 softtabstop=4

import argparse
import logging
import pkgutil
import string

from cloudenvy.config import EnvyConfig,Config

import cloudenvy.commands


#TODO(bcwaldon): replace this with entry points!
def _load_commands():
    """Iterate through modules in command and import suspected command classes

    This looks for a class in each module in cloudenvy.commands that has the
    same name as its module with the first character uppercased. For example,
    the cloudenvy.commands.up module should have a class Up within it.
    """
    modlist = list(pkgutil.iter_modules(cloudenvy.commands.__path__))
    #NOTE(bcwaldon): this parses out a string representation of each
    # individual command module. For example, if we had a single command
    # in cloudenvy.commands named 'up', this list would look like ['up]
    commands = [_[1] for _ in modlist]
    for command in commands:
        #NOTE(bcwaldon): the __import__ statement returns a handle on the
        # top-level 'cloudenvy' package, so we must iterate down through
        # each sub-package to get a handle on our module
        module_name = 'cloudenvy.commands.{0}'.format(command)
        _cloudenvy = __import__(module_name, globals(), locals(), [], -1)
        module = getattr(_cloudenvy.commands, command)

        command_class = getattr(module, string.capitalize(command))
        yield (command, command_class)


def _build_parser():
    parser = argparse.ArgumentParser(
        description='Launch a virtual machine on an OpenStack cloud.')
    parser.add_argument('-v', '--verbosity', action='count',
                        help='Increase output verbosity.')
    parser.add_argument('-c', '--cloud', action='store',
                        help='Specify which cloud to use.')
    return parser


def _init_help_command(parser, subparser):

    def find_command_help(config, args):
        if args.command:
            subparser.choices[args.command].print_help()
        else:
            parser.print_help()

    help_cmd = subparser.add_parser(
        'help', help='Display help information for a specfiic command.'
    )
    help_cmd.add_argument(
        'command', action='store', nargs='?',
        help='Specific command to describe.'
    )
    help_cmd.set_defaults(func=find_command_help)

    return parser


def _init_commands(commands, parser):
    _commands = {}
    for (command, command_class) in commands:
        _commands[command] = command_class(parser, _commands)


def main():
    parser = _build_parser()
    command_subparser = parser.add_subparsers(title='Available commands')
    _init_help_command(parser, command_subparser)

    commands = _load_commands()
    _init_commands(commands, command_subparser)

    args = parser.parse_args()
    config = Config(args)
    config = EnvyConfig(config)

    if args.verbosity == 3:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('novaclient').setLevel(logging.DEBUG)
    elif args.verbosity == 2:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('novaclient').setLevel(logging.INFO)
    elif args.verbosity == 1:
        logging.getLogger().setLevel(logging.INFO)

    args.func(config, args)

########NEW FILE########
__FILENAME__ = metadata
VERSION = '0.8.0'

########NEW FILE########
