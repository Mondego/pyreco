__FILENAME__ = api
# vim: tabstop=4 shiftwidth=4 softtabstop=4

import functools
import hashlib
import httplib
import urllib
import json

import glance.openstack.common.log as logging
from glance.openstack.common import timeutils


LOG = logging.getLogger(__name__)
IMAGES_CACHE = []


def log_call(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        LOG.info(_('Calling %(funcname)s: args=%(args)s, kwargs=%(kwargs)s') %
                 {"funcname": func.__name__,
                  "args": args,
                  "kwargs": kwargs})
        try:
            output = func(*args, **kwargs)
            LOG.info(_('Returning %(funcname)s: %(output)s') %
                     {"funcname": func.__name__,
                      "output": output})
            return output
        except Exception as e:
            LOG.exception(type(e))
    return wrapped


def _make_uuid(val):
    """ Generate a fake UUID from a string to be compliant with the API
        It uses a MD5 to return the same UUID for a given string.
    """
    h = hashlib.md5(val).hexdigest()
    return '{0}-{1}-{2}-{3}-{4}'.format(
            h[:8], h[8:12], h[12:16], h[16:20], h[20:])


def _image_format(image_name, **values):
    dt = timeutils.utcnow()
    image = {
        'id': _make_uuid(image_name),
        'name': image_name,
        'owner': None,
        'locations': [],
        'status': 'active',
        'protected': False,
        'is_public': True,
        'container_format': 'docker',
        'disk_format': 'docker',
        'min_ram': 0,
        'min_disk': 0,
        'size': 0,
        'checksum': None,
        'tags': [],
        'created_at': dt,
        'updated_at': dt,
        'deleted_at': None,
        'deleted': False,
    }
    properties = values.pop('properties', {})
    properties = [{'name': k,
                   'value': v,
                   'deleted': False} for k, v in properties.items()]
    image['properties'] = properties
    image.update(values)
    return image


def _docker_search(term):
    """ Interface to the Docker search API """
    http_conn = httplib.HTTPConnection('localhost', 4243)
    http_conn.request('GET',
            '/images/search?term={0}'.format(urllib.quote(term)))
    resp = http_conn.getresponse()
    data = resp.read()
    if resp.status != 200:
        return []
    return [repos['Name'] for repos in json.loads(data)]


def _init_cache():
    global IMAGES_CACHE
    if not IMAGES_CACHE:
        IMAGES_CACHE = _docker_search('library')


def reset():
    pass


def setup_db_env(*args, **kwargs):
    pass


@log_call
def image_get(context, image_id, session=None, force_show_deleted=False):
    images = [_image_format(i) for i in IMAGES_CACHE]
    for i in images:
        if i['id'] == image_id:
            return i


@log_call
def image_get_all(context, filters=None, marker=None, limit=None,
                  sort_key='created_at', sort_dir='desc',
                  member_status='accepted', is_public=None,
                  admin_as_user=False):
    _init_cache()
    return [_image_format(i) for i in IMAGES_CACHE]


@log_call
def image_property_create(context, values):
    pass


@log_call
def image_property_delete(context, prop_ref, session=None):
    pass


@log_call
def image_member_find(context, image_id=None, member=None, status=None):
    pass


@log_call
def image_member_create(context, values):
    pass


@log_call
def image_member_update(context, member_id, values):
    pass


@log_call
def image_member_delete(context, member_id):
    pass


@log_call
def image_create(context, image_values):
    global IMAGES_CACHE
    _init_cache()
    name = image_values.get('name')
    if not name:
        return
    if '/' in name:
        IMAGES_CACHE.append(name)
    else:
        images = _docker_search(name)
        if not images:
            return
        for i in images:
            if i not in IMAGES_CACHE:
                IMAGES_CACHE.append(i)
    return _image_format(name)


@log_call
def image_update(context, image_id, image_values, purge_props=False):
    pass


@log_call
def image_destroy(context, image_id):
    pass


@log_call
def image_tag_get_all(context, image_id):
    pass


@log_call
def image_tag_get(context, image_id, value):
    pass


@log_call
def image_tag_set_all(context, image_id, values):
    pass


@log_call
def image_tag_create(context, image_id, value):
    pass


@log_call
def image_tag_delete(context, image_id, value):
    pass


def is_image_mutable(context, image):
    return False


def is_image_sharable(context, image, **kwargs):
    return True


def is_image_visible(context, image, status=None):
    return True

########NEW FILE########
__FILENAME__ = client
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2013 dotCloud, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import functools
import socket

from eventlet.green import httplib

from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging


LOG = logging.getLogger(__name__)


def filter_data(f):
    """Decorator that post-processes data returned by Docker to avoid any
       surprises with different versions of Docker
    """
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        out = f(*args, **kwds)

        def _filter(obj):
            if isinstance(obj, list):
                new_list = []
                for o in obj:
                    new_list.append(_filter(o))
                obj = new_list
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(k, basestring):
                        obj[k.lower()] = _filter(v)
            return obj
        return _filter(out)
    return wrapper


class Response(object):
    def __init__(self, http_response, skip_body=False):
        self._response = http_response
        self.code = int(http_response.status)
        self.data = http_response.read()
        self.json = self._decode_json(self.data)

    def read(self, size=None):
        return self._response.read(size)

    @filter_data
    def _decode_json(self, data):
        if self._response.getheader('Content-Type') != 'application/json':
            return
        try:
            return jsonutils.loads(self.data)
        except ValueError:
            return


class UnixHTTPConnection(httplib.HTTPConnection):
    def __init__(self):
        httplib.HTTPConnection.__init__(self, 'localhost')
        self.unix_socket = '/var/run/docker.sock'

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.unix_socket)
        self.sock = sock


class DockerHTTPClient(object):
    def __init__(self, connection=None):
        self._connection = connection

    @property
    def connection(self):
        if self._connection:
            return self._connection
        else:
            return UnixHTTPConnection()

    def make_request(self, *args, **kwargs):
        headers = {}
        if 'headers' in kwargs and kwargs['headers']:
            headers = kwargs['headers']
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
            kwargs['headers'] = headers
        conn = self.connection
        conn.request(*args, **kwargs)
        return Response(conn.getresponse())

    def list_containers(self, _all=True):
        resp = self.make_request(
            'GET',
            '/v1.4/containers/ps?all={0}&limit=50'.format(int(_all)))
        return resp.json

    def create_container(self, args):
        data = {
            'Hostname': '',
            'User': '',
            'Memory': 0,
            'MemorySwap': 0,
            'AttachStdin': False,
            'AttachStdout': False,
            'AttachStderr': False,
            'PortSpecs': [],
            'Tty': True,
            'OpenStdin': True,
            'StdinOnce': False,
            'Env': None,
            'Cmd': [],
            'Dns': None,
            'Image': None,
            'Volumes': {},
            'VolumesFrom': '',
        }
        data.update(args)
        resp = self.make_request(
            'POST',
            '/v1.4/containers/create',
            body=jsonutils.dumps(data))
        if resp.code != 201:
            return
        obj = jsonutils.loads(resp.data)
        for k, v in obj.iteritems():
            if k.lower() == 'id':
                return v

    def start_container(self, container_id):
        resp = self.make_request(
            'POST',
            '/v1.4/containers/{0}/start'.format(container_id),
            body='{}')
        return (resp.code == 200)

    def inspect_image(self, image_name):
        resp = self.make_request(
            'GET',
            '/v1.4/images/{0}/json'.format(image_name))
        if resp.code != 200:
            return
        return resp.json

    def inspect_container(self, container_id):
        resp = self.make_request(
            'GET',
            '/v1.4/containers/{0}/json'.format(container_id))
        if resp.code != 200:
            return
        return resp.json

    def stop_container(self, container_id):
        timeout = 5
        resp = self.make_request(
            'POST',
            '/v1.4/containers/{0}/stop?t={1}'.format(container_id, timeout))
        return (resp.code == 204)

    def destroy_container(self, container_id):
        resp = self.make_request(
            'DELETE',
            '/v1.4/containers/{0}'.format(container_id))
        return (resp.code == 204)

    def pull_repository(self, name):
        parts = name.rsplit(':', 1)
        url = '/v1.4/images/create?fromImage={0}'.format(parts[0])
        if len(parts) > 1:
            url += '&tag={0}'.format(parts[1])
        resp = self.make_request('POST', url)
        while True:
            buf = resp.read(1024)
            if not buf:
                # Image pull completed
                break
        return (resp.code == 200)

    def push_repository(self, name, headers=None):
        url = '/v1.4/images/{0}/push'.format(name)
        # NOTE(samalba): docker requires the credentials fields even if
        # they're not needed here.
        body = ('{"username":"foo","password":"bar",'
                '"auth":"","email":"foo@bar.bar"}')
        resp = self.make_request('POST', url, headers=headers, body=body)
        while True:
            buf = resp.read(1024)
            if not buf:
                # Image push completed
                break
        return (resp.code == 200)

    def commit_container(self, container_id, name):
        parts = name.rsplit(':', 1)
        url = '/v1.4/commit?container={0}&repo={1}'.format(container_id,
                                                           parts[0])
        if len(parts) > 1:
            url += '&tag={0}'.format(parts[1])
        resp = self.make_request('POST', url)
        return (resp.code == 201)

    def get_container_logs(self, container_id):
        resp = self.make_request(
            'POST',
            ('/v1.4/containers/{0}/attach'
             '?logs=1&stream=0&stdout=1&stderr=1').format(container_id))
        if resp.code != 200:
            return
        return resp.data

########NEW FILE########
__FILENAME__ = driver
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2013 dotCloud, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
A Docker Hypervisor which allows running Linux Containers instead of VMs.
"""

import os
import random
import socket
import time

from oslo.config import cfg

from nova.compute import power_state
from nova.compute import task_states
from nova import exception
from nova.image import glance
from nova.openstack.common.gettextutils import _
from nova.openstack.common import jsonutils
from nova.openstack.common import log
from nova import utils
import nova.virt.docker.client
from nova.virt.docker import hostinfo
from nova.virt import driver


docker_opts = [
    cfg.IntOpt('docker_registry_default_port',
               default=5042,
               help=_('Default TCP port to find the '
                      'docker-registry container')),
]

CONF = cfg.CONF
CONF.register_opts(docker_opts)
CONF.import_opt('my_ip', 'nova.netconf')

LOG = log.getLogger(__name__)


class DockerDriver(driver.ComputeDriver):
    """Docker hypervisor driver."""

    capabilities = {
        'has_imagecache': True,
        'supports_recreate': True,
    }

    def __init__(self, virtapi):
        super(DockerDriver, self).__init__(virtapi)
        self._docker = None

    @property
    def docker(self):
        if self._docker is None:
            self._docker = nova.virt.docker.client.DockerHTTPClient()
        return self._docker

    def init_host(self, host):
        if self.is_daemon_running() is False:
            raise exception.NovaException(_('Docker daemon is not running or '
                'is not reachable (check the rights on /var/run/docker.sock)'))

    def is_daemon_running(self):
        try:
            self.docker.list_containers()
            return True
        except socket.error:
            # NOTE(samalba): If the daemon is not running, we'll get a socket
            # error. The list_containers call is safe to call often, there
            # is an internal hard limit in docker if the amount of containers
            # is huge.
            return False

    def list_instances(self, inspect=False):
        res = []
        for container in self.docker.list_containers():
            info = self.docker.inspect_container(container['id'])
            if inspect:
                res.append(info)
            else:
                res.append(info['Config'].get('Hostname'))
        return res

    def plug_vifs(self, instance, network_info):
        """Plug VIFs into networks."""
        pass

    def unplug_vifs(self, instance, network_info):
        """Unplug VIFs from networks."""
        pass

    def find_container_by_name(self, name):
        for info in self.list_instances(inspect=True):
            if info['Config'].get('Hostname') == name:
                return info
        return {}

    def get_info(self, instance):
        container = self.find_container_by_name(instance['name'])
        if not container:
            raise exception.InstanceNotFound(instance_id=instance['name'])
        running = container['State'].get('Running')
        info = {
            'max_mem': 0,
            'mem': 0,
            'num_cpu': 1,
            'cpu_time': 0
        }
        info['state'] = power_state.RUNNING if running \
            else power_state.SHUTDOWN
        return info

    def get_host_stats(self, refresh=False):
        hostname = socket.gethostname()
        memory = hostinfo.get_memory_usage()
        disk = hostinfo.get_disk_usage()
        stats = self.get_available_resource(hostname)
        stats['hypervisor_hostname'] = hostname
        stats['host_hostname'] = hostname
        stats['host_name_label'] = hostname
        return stats

    def get_available_resource(self, nodename):
        memory = hostinfo.get_memory_usage()
        disk = hostinfo.get_disk_usage()
        stats = {
            'vcpus': 1,
            'vcpus_used': 0,
            'memory_mb': memory['total'] / (1024 ** 2),
            'memory_mb_used': memory['used'] / (1024 ** 2),
            'local_gb': disk['total'] / (1024 ** 3),
            'local_gb_used': disk['used'] / (1024 ** 3),
            'disk_available_least': disk['available'] / (1024 ** 3),
            'hypervisor_type': 'docker',
            'hypervisor_version': '1.0',
            'hypervisor_hostname': nodename,
            'cpu_info': '?',
            'supported_instances': jsonutils.dumps([
                    ('i686', 'docker', 'lxc'),
                    ('x86_64', 'docker', 'lxc')
                ])
        }
        return stats

    def _find_cgroup_devices_path(self):
        for ln in open('/proc/mounts'):
            if ln.startswith('cgroup ') and 'devices' in ln:
                return ln.split(' ')[1]

    def _find_container_pid(self, container_id):
        cgroup_path = self._find_cgroup_devices_path()
        lxc_path = os.path.join(cgroup_path, 'lxc')
        tasks_path = os.path.join(lxc_path, container_id, 'tasks')
        n = 0
        while True:
            # NOTE(samalba): We wait for the process to be spawned inside the
            # container in order to get the the "container pid". This is
            # usually really fast. To avoid race conditions on a slow
            # machine, we allow 10 seconds as a hard limit.
            if n > 20:
                return
            try:
                with open(tasks_path) as f:
                    pids = f.readlines()
                    if pids:
                        return int(pids[0].strip())
            except IOError:
                pass
            time.sleep(0.5)
            n += 1

    def _find_fixed_ip(self, subnets):
        for subnet in subnets:
            for ip in subnet['ips']:
                if ip['type'] == 'fixed' and ip['address']:
                    return ip['address']

    def _setup_network(self, instance, network_info):
        if not network_info:
            return
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        network_info = network_info[0]['network']
        netns_path = '/var/run/netns'
        if not os.path.exists(netns_path):
            utils.execute(
                'mkdir', '-p', netns_path, run_as_root=True)
        nspid = self._find_container_pid(container_id)
        if not nspid:
            msg = _('Cannot find any PID under container "{0}"')
            raise RuntimeError(msg.format(container_id))
        netns_path = os.path.join(netns_path, container_id)
        utils.execute(
            'ln', '-sf', '/proc/{0}/ns/net'.format(nspid),
            '/var/run/netns/{0}'.format(container_id),
            run_as_root=True)
        rand = random.randint(0, 100000)
        if_local_name = 'pvnetl{0}'.format(rand)
        if_remote_name = 'pvnetr{0}'.format(rand)
        bridge = network_info['bridge']
        ip = self._find_fixed_ip(network_info['subnets'])
        if not ip:
            raise RuntimeError(_('Cannot set fixed ip'))
        undo_mgr = utils.UndoManager()
        try:
            utils.execute(
                'ip', 'link', 'add', 'name', if_local_name, 'type',
                'veth', 'peer', 'name', if_remote_name,
                run_as_root=True)
            undo_mgr.undo_with(lambda: utils.execute(
                'ip', 'link', 'delete', if_local_name, run_as_root=True))
            # NOTE(samalba): Deleting the interface will delete all associated
            # resources (remove from the bridge, its pair, etc...)
            utils.execute(
                'brctl', 'addif', bridge, if_local_name,
                run_as_root=True)
            utils.execute(
                'ip', 'link', 'set', if_local_name, 'up',
                run_as_root=True)
            utils.execute(
                'ip', 'link', 'set', if_remote_name, 'netns', nspid,
                run_as_root=True)
            utils.execute(
                'ip', 'netns', 'exec', container_id, 'ifconfig',
                if_remote_name, ip,
                run_as_root=True)
        except Exception:
            msg = _('Failed to setup the network, rolling back')
            undo_mgr.rollback_and_reraise(msg=msg, instance=instance)

    def _get_memory_limit_bytes(self, instance):
        for metadata in instance.get('system_metadata', []):
            if metadata['deleted']:
                continue
            if metadata['key'] == 'instance_type_memory_mb':
                return int(metadata['value']) * 1024 * 1024
        return 0

    def _get_image_name(self, context, instance, image):
        fmt = image['container_format']
        if fmt != 'docker':
            msg = _('Image container format not supported ({0})')
            raise exception.InstanceDeployFailure(msg.format(fmt),
                instance_id=instance['name'])
        registry_port = self._get_registry_port()
        return '{0}:{1}/{2}'.format(CONF.my_ip,
                                    registry_port,
                                    image['name'])

    def _get_default_cmd(self, image_name):
        default_cmd = ['sh']
        info = self.docker.inspect_image(image_name)
        if not info:
            return default_cmd
        if not info['container_config']['Cmd']:
            return default_cmd

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        image_name = self._get_image_name(context, instance, image_meta)
        args = {
            'Hostname': instance['name'],
            'Image': image_name,
            'Memory': self._get_memory_limit_bytes(instance)
        }
        default_cmd = self._get_default_cmd(image_name)
        if default_cmd:
            args['Cmd'] = default_cmd
        container_id = self.docker.create_container(args)
        if not container_id:
            msg = _('Image name "{0}" does not exist, fetching it...')
            LOG.info(msg.format(image_name))
            res = self.docker.pull_repository(image_name)
            if res is False:
                raise exception.InstanceDeployFailure(
                    _('Cannot pull missing image'),
                    instance_id=instance['name'])
            container_id = self.docker.create_container(args)
            if not container_id:
                raise exception.InstanceDeployFailure(
                    _('Cannot create container'),
                    instance_id=instance['name'])
        self.docker.start_container(container_id)
        try:
            self._setup_network(instance, network_info)
        except Exception as e:
            msg = _('Cannot setup network: {0}')
            raise exception.InstanceDeployFailure(msg.format(e),
                                                  instance_id=instance['name'])

    def destroy(self, instance, network_info, block_device_info=None,
                destroy_disks=True):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        self.docker.stop_container(container_id)
        self.docker.destroy_container(container_id)

    def reboot(self, context, instance, network_info, reboot_type,
               block_device_info=None, bad_volumes_callback=None):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        if not self.docker.stop_container(container_id):
            LOG.warning(_('Cannot stop the container, '
                          'please check docker logs'))
        if not self.docker.start_container(container_id):
            LOG.warning(_('Cannot restart the container, '
                          'please check docker logs'))

    def power_on(self, context, instance, network_info, block_device_info):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        self.docker.start_container(container_id)

    def power_off(self, instance):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        self.docker.stop_container(container_id)

    def get_console_output(self, instance):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        return self.docker.get_container_logs(container_id)

    def _get_registry_port(self):
        default_port = CONF.docker_registry_default_port
        registry = None
        for container in self.docker.list_containers(_all=False):
            container = self.docker.inspect_container(container['id'])
            if 'docker-registry' in container['Path']:
                registry = container
                break
        if not registry:
            return default_port
        # NOTE(samalba): The registry service always binds on port 5000 in the
        # container
        try:
            return container['NetworkSettings']['PortMapping']['Tcp']['5000']
        except (KeyError, TypeError):
            # NOTE(samalba): Falling back to a default port allows more
            # flexibility (run docker-registry outside a container)
            return default_port

    def snapshot(self, context, instance, image_href, update_task_state):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            raise exception.InstanceNotRunning(instance_id=instance['uuid'])
        update_task_state(task_state=task_states.IMAGE_PENDING_UPLOAD)
        (image_service, image_id) = glance.get_remote_image_service(
            context, image_href)
        image = image_service.show(context, image_id)
        registry_port = self._get_registry_port()
        name = image['name']
        default_tag = (':' not in name)
        name = '{0}:{1}/{2}'.format(CONF.my_ip,
                                    registry_port,
                                    name)
        commit_name = name if not default_tag else name + ':latest'
        self.docker.commit_container(container_id, commit_name)
        update_task_state(task_state=task_states.IMAGE_UPLOADING,
                          expected_state=task_states.IMAGE_PENDING_UPLOAD)
        headers = {'X-Meta-Glance-Image-Id': image_href}
        self.docker.push_repository(name, headers=headers)

########NEW FILE########
__FILENAME__ = hostinfo
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2013 dotCloud, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os


def statvfs():
    docker_path = '/var/lib/docker'
    if not os.path.exists(docker_path):
        docker_path = '/'
    return os.statvfs(docker_path)


def get_meminfo():
    with open('/proc/meminfo') as f:
        return f.readlines()


def get_disk_usage():
    # This is the location where Docker stores its containers. It's currently
    # hardcoded in Docker so it's not configurable yet.
    st = statvfs()
    return {
        'total': st.f_blocks * st.f_frsize,
        'available': st.f_bavail * st.f_frsize,
        'used': (st.f_blocks - st.f_bfree) * st.f_frsize
    }


def parse_meminfo():
    meminfo = {}
    for ln in get_meminfo():
        parts = ln.split(':')
        if len(parts) < 2:
            continue
        key = parts[0].lower()
        value = parts[1].strip()
        parts = value.split(' ')
        value = parts[0]
        if not value.isdigit():
            continue
        value = int(parts[0])
        if len(parts) > 1 and parts[1] == 'kB':
            value *= 1024
        meminfo[key] = value
    return meminfo


def get_memory_usage():
    meminfo = parse_meminfo()
    total = meminfo.get('memtotal', 0)
    free = meminfo.get('memfree', 0)
    free += meminfo.get('cached', 0)
    free += meminfo.get('buffers', 0)
    return {
        'total': total,
        'free': free,
        'used': total - free
    }

########NEW FILE########
__FILENAME__ = mock_client
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2013 dotCloud, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time
import uuid

from nova.openstack.common import timeutils
import nova.virt.docker.client


class MockClient(object):
    def __init__(self, endpoint=None):
        self._containers = {}

    def _fake_id(self):
        return uuid.uuid4().hex + uuid.uuid4().hex

    def is_daemon_running(self):
        return True

    @nova.virt.docker.client.filter_data
    def list_containers(self, _all=True):
        containers = []
        for container_id in self._containers.iterkeys():
            containers.append({
                'Status': 'Exit 0',
                'Created': int(time.time()),
                'Image': 'ubuntu:12.04',
                'Ports': '',
                'Command': 'bash ',
                'Id': container_id
            })
        return containers

    def create_container(self, args):
        data = {
            'Hostname': '',
            'User': '',
            'Memory': 0,
            'MemorySwap': 0,
            'AttachStdin': False,
            'AttachStdout': False,
            'AttachStderr': False,
            'PortSpecs': None,
            'Tty': True,
            'OpenStdin': True,
            'StdinOnce': False,
            'Env': None,
            'Cmd': [],
            'Dns': None,
            'Image': None,
            'Volumes': {},
            'VolumesFrom': ''
        }
        data.update(args)
        container_id = self._fake_id()
        self._containers[container_id] = {
            'id': container_id,
            'running': False,
            'config': args
        }
        return container_id

    def start_container(self, container_id):
        if container_id not in self._containers:
            return False
        self._containers[container_id]['running'] = True
        return True

    @nova.virt.docker.client.filter_data
    def inspect_image(self, image_name):
        return {'container_config': {'Cmd': None}}

    @nova.virt.docker.client.filter_data
    def inspect_container(self, container_id):
        if container_id not in self._containers:
            return
        container = self._containers[container_id]
        info = {
            'Args': [],
            'Config': container['config'],
            'Created': str(timeutils.utcnow()),
            'ID': container_id,
            'Image': self._fake_id(),
            'NetworkSettings': {
                'Bridge': '',
                'Gateway': '',
                'IPAddress': '',
                'IPPrefixLen': 0,
                'PortMapping': None
            },
            'Path': 'bash',
            'ResolvConfPath': '/etc/resolv.conf',
            'State': {
                'ExitCode': 0,
                'Ghost': False,
                'Pid': 0,
                'Running': container['running'],
                'StartedAt': str(timeutils.utcnow())
            },
            'SysInitPath': '/tmp/docker',
            'Volumes': {},
        }
        return info

    def stop_container(self, container_id, timeout=None):
        if container_id not in self._containers:
            return False
        self._containers[container_id]['running'] = False
        return True

    def destroy_container(self, container_id):
        if container_id not in self._containers:
            return False
        del self._containers[container_id]
        return True

    def pull_repository(self, name):
        return True

    def push_repository(self, name, headers=None):
        return True

    def commit_container(self, container_id, name):
        if container_id not in self._containers:
            return False
        return True

    def get_container_logs(self, container_id):
        if container_id not in self._containers:
            return False
        return '\n'.join([
            'Lorem ipsum dolor sit amet, consectetur adipiscing elit. ',
            'Vivamus ornare mi sit amet orci feugiat, nec luctus magna ',
            'vehicula. Quisque diam nisl, dictum vitae pretium id, ',
            'consequat eget sapien. Ut vehicula tortor non ipsum ',
            'consectetur, at tincidunt elit posuere. In ut ligula leo. ',
            'Donec eleifend accumsan mi, in accumsan metus. Nullam nec ',
            'nulla eu risus vehicula porttitor. Sed purus ligula, ',
            'placerat nec metus a, imperdiet viverra turpis. Praesent ',
            'dapibus ornare massa. Nam ut hendrerit nunc. Interdum et ',
            'malesuada fames ac ante ipsum primis in faucibus. ',
            'Fusce nec pellentesque nisl.'])

########NEW FILE########
__FILENAME__ = test_docker_client
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2013 dotCloud, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mox

from nova import test
import nova.virt.docker.client
from nova.openstack.common import jsonutils


class FakeResponse(object):
    def __init__(self, status, data='', headers=None):
        self.status = status
        self._data = data
        self._headers = headers or {}

    def read(self, _size=None):
        return self._data

    def getheader(self, key):
        return self._headers.get(key)


class DockerHTTPClientTestCase(test.TestCase):

    def test_list_containers(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('GET', '/v1.4/containers/ps?all=1&limit=50',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(200, data='[]',
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        containers = client.list_containers()
        self.assertEqual([], containers)

        self.mox.VerifyAll()

    def test_create_container(self):
        mock_conn = self.mox.CreateMockAnything()

        expected_body = jsonutils.dumps({
            'Hostname': '',
            'User': '',
            'Memory': 0,
            'MemorySwap': 0,
            'AttachStdin': False,
            'AttachStdout': False,
            'AttachStderr': False,
            'PortSpecs': [],
            'Tty': True,
            'OpenStdin': True,
            'StdinOnce': False,
            'Env': None,
            'Cmd': [],
            'Dns': None,
            'Image': None,
            'Volumes': {},
            'VolumesFrom': '',
        })
        mock_conn.request('POST', '/v1.4/containers/create',
                          body=expected_body,
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(201, data='{"id": "XXX"}',
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        container_id = client.create_container({})
        self.assertEqual('XXX', container_id)

        self.mox.VerifyAll()

    def test_create_container_with_args(self):
        mock_conn = self.mox.CreateMockAnything()

        expected_body = jsonutils.dumps({
            'Hostname': 'marco',
            'User': '',
            'Memory': 512,
            'MemorySwap': 0,
            'AttachStdin': False,
            'AttachStdout': False,
            'AttachStderr': False,
            'PortSpecs': [],
            'Tty': True,
            'OpenStdin': True,
            'StdinOnce': False,
            'Env': None,
            'Cmd': [],
            'Dns': None,
            'Image': 'example',
            'Volumes': {},
            'VolumesFrom': '',
        })
        mock_conn.request('POST', '/v1.4/containers/create',
                          body=expected_body,
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(201, data='{"id": "XXX"}',
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        args = {
            'Hostname': 'marco',
            'Memory': 512,
            'Image': 'example',
        }
        container_id = client.create_container(args)
        self.assertEqual('XXX', container_id)

        self.mox.VerifyAll()

    def test_create_container_no_id_in_response(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('POST', '/v1.4/containers/create',
                          body=mox.IgnoreArg(),
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(201, data='{"ping": "pong"}',
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        container_id = client.create_container({})
        self.assertEqual(None, container_id)

        self.mox.VerifyAll()

    def test_create_container_bad_return_code(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('POST', '/v1.4/containers/create',
                          body=mox.IgnoreArg(),
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(400)
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        container_id = client.create_container({})
        self.assertEqual(None, container_id)

        self.mox.VerifyAll()

    def test_start_container(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('POST', '/v1.4/containers/XXX/start',
                          body='{}',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(200,
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(True, client.start_container('XXX'))

        self.mox.VerifyAll()

    def test_start_container_bad_return_code(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('POST', '/v1.4/containers/XXX/start',
                          body='{}',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(400)
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(False, client.start_container('XXX'))

        self.mox.VerifyAll()

    def test_inspect_image(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('GET', '/v1.4/images/XXX/json',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(200, data='{"name": "XXX"}',
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        image = client.inspect_image('XXX')
        self.assertEqual({'name': 'XXX'}, image)

        self.mox.VerifyAll()

    def test_inspect_image_bad_return_code(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('GET', '/v1.4/images/XXX/json',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(404)
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        image = client.inspect_image('XXX')
        self.assertEqual(None, image)

        self.mox.VerifyAll()

    def test_inspect_container(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('GET', '/v1.4/containers/XXX/json',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(200, data='{"id": "XXX"}',
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        container = client.inspect_container('XXX')
        self.assertEqual({'id': 'XXX'}, container)

        self.mox.VerifyAll()

    def test_inspect_container_bad_return_code(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('GET', '/v1.4/containers/XXX/json',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(404)
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        container = client.inspect_container('XXX')
        self.assertEqual(None, container)

        self.mox.VerifyAll()

    def test_stop_container(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('POST', '/v1.4/containers/XXX/stop?t=5',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(204,
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(True, client.stop_container('XXX'))

        self.mox.VerifyAll()

    def test_stop_container_bad_return_code(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('POST', '/v1.4/containers/XXX/stop?t=5',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(400)
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(False, client.stop_container('XXX'))

        self.mox.VerifyAll()

    def test_destroy_container(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('DELETE', '/v1.4/containers/XXX',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(204,
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(True, client.destroy_container('XXX'))

        self.mox.VerifyAll()

    def test_destroy_container_bad_return_code(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('DELETE', '/v1.4/containers/XXX',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(400)
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(False, client.destroy_container('XXX'))

        self.mox.VerifyAll()

    def test_pull_repository(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('POST', '/v1.4/images/create?fromImage=ping',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(200,
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(True, client.pull_repository('ping'))

        self.mox.VerifyAll()

    def test_pull_repository_tag(self):
        mock_conn = self.mox.CreateMockAnything()

        url = '/v1.4/images/create?fromImage=ping&tag=pong'
        mock_conn.request('POST', url,
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(200,
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(True, client.pull_repository('ping:pong'))

        self.mox.VerifyAll()

    def test_pull_repository_bad_return_code(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('POST', '/v1.4/images/create?fromImage=ping',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(400,
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(False, client.pull_repository('ping'))

        self.mox.VerifyAll()

    def test_push_repository(self):
        mock_conn = self.mox.CreateMockAnything()

        body = ('{"username":"foo","password":"bar",'
                '"auth":"","email":"foo@bar.bar"}')
        mock_conn.request('POST', '/v1.4/images/ping/push',
                          headers={'Content-Type': 'application/json'},
                          body=body)
        response = FakeResponse(200,
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(True, client.push_repository('ping'))

        self.mox.VerifyAll()

    def test_push_repository_bad_return_code(self):
        mock_conn = self.mox.CreateMockAnything()

        body = ('{"username":"foo","password":"bar",'
                '"auth":"","email":"foo@bar.bar"}')
        mock_conn.request('POST', '/v1.4/images/ping/push',
                          headers={'Content-Type': 'application/json'},
                          body=body)
        response = FakeResponse(400,
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(False, client.push_repository('ping'))

        self.mox.VerifyAll()

    def test_commit_container(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('POST', '/v1.4/commit?container=XXX&repo=ping',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(201,
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(True, client.commit_container('XXX', 'ping'))

        self.mox.VerifyAll()

    def test_commit_container_bad_return_code(self):
        mock_conn = self.mox.CreateMockAnything()

        mock_conn.request('POST', '/v1.4/commit?container=XXX&repo=ping',
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(400,
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        self.assertEqual(False, client.commit_container('XXX', 'ping'))

        self.mox.VerifyAll()

    def test_get_container_logs(self):
        mock_conn = self.mox.CreateMockAnything()

        url = '/v1.4/containers/XXX/attach?logs=1&stream=0&stdout=1&stderr=1'
        mock_conn.request('POST', url,
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(200, data='ping pong',
                                headers={'Content-Type': 'application/json'})
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        logs = client.get_container_logs('XXX')
        self.assertEqual('ping pong', logs)

        self.mox.VerifyAll()

    def test_get_container_logs_bad_return_code(self):
        mock_conn = self.mox.CreateMockAnything()

        url = '/v1.4/containers/XXX/attach?logs=1&stream=0&stdout=1&stderr=1'
        mock_conn.request('POST', url,
                          headers={'Content-Type': 'application/json'})
        response = FakeResponse(404)
        mock_conn.getresponse().AndReturn(response)

        self.mox.ReplayAll()

        client = nova.virt.docker.client.DockerHTTPClient(mock_conn)
        logs = client.get_container_logs('XXX')
        self.assertEqual(None, logs)

        self.mox.VerifyAll()

########NEW FILE########
__FILENAME__ = test_driver
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2013 dotCloud, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from nova import test
from nova.tests import utils
import nova.tests.virt.docker.mock_client
from nova.tests.virt.test_virt_drivers import _VirtDriverTestCase


class DockerDriverTestCase(_VirtDriverTestCase, test.TestCase):

    driver_module = 'nova.virt.docker.DockerDriver'

    def setUp(self):
        super(DockerDriverTestCase, self).setUp()

        self.stubs.Set(nova.virt.docker.driver.DockerDriver,
                       'docker',
                       nova.tests.virt.docker.mock_client.MockClient())

        def fake_setup_network(self, instance, network_info):
            return

        self.stubs.Set(nova.virt.docker.driver.DockerDriver,
                       '_setup_network',
                       fake_setup_network)

        def fake_get_registry_port(self):
            return 5042

        self.stubs.Set(nova.virt.docker.driver.DockerDriver,
                       '_get_registry_port',
                       fake_get_registry_port)

    #NOTE(bcwaldon): This exists only because _get_running_instance on the
    # base class will not let us set a custom disk/container_format.
    def _get_running_instance(self):
        instance_ref = utils.get_test_instance()
        network_info = utils.get_test_network_info()
        network_info[0]['network']['subnets'][0]['meta']['dhcp_server'] = \
            '1.1.1.1'
        image_info = utils.get_test_image_info(None, instance_ref)
        image_info['disk_format'] = 'raw'
        image_info['container_format'] = 'docker'
        self.connection.spawn(self.ctxt, instance_ref, image_info,
                              [], 'herp', network_info=network_info)
        return instance_ref, network_info

########NEW FILE########
__FILENAME__ = test_hostinfo
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2013 dotCloud, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import posix

from nova import test
from nova.virt.docker import hostinfo


class HostInfoTestCase(test.TestCase):

    def setUp(self):
        super(HostInfoTestCase, self).setUp()
        hostinfo.get_meminfo = self.get_meminfo
        hostinfo.statvfs = self.statvfs

    def get_meminfo(self):
        data = ['MemTotal:        1018784 kB\n',
                'MemFree:          220060 kB\n',
                'Buffers:           21640 kB\n',
                'Cached:            63364 kB\n']
        return data

    def statvfs(self):
        seq = (4096, 4096, 10047582, 7332259, 6820195,
               2564096, 2271310, 2271310, 1024, 255)
        return posix.statvfs_result(sequence=seq)

    def test_get_disk_usage(self):
        disk_usage = hostinfo.get_disk_usage()
        self.assertEqual(disk_usage['total'], 41154895872)
        self.assertEqual(disk_usage['available'], 27935518720)
        self.assertEqual(disk_usage['used'], 11121963008)

    def test_parse_meminfo(self):
        meminfo = hostinfo.parse_meminfo()
        self.assertEqual(meminfo['memtotal'], 1043234816)
        self.assertEqual(meminfo['memfree'], 225341440)
        self.assertEqual(meminfo['cached'], 64884736)
        self.assertEqual(meminfo['buffers'], 22159360)

    def test_get_memory_usage(self):
        usage = hostinfo.get_memory_usage()
        self.assertEqual(usage['total'], 1043234816)
        self.assertEqual(usage['used'], 730849280)
        self.assertEqual(usage['free'], 312385536)

########NEW FILE########
