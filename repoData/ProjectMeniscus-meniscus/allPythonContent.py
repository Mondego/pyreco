__FILENAME__ = build
import os
import os.path as path
import stat
import sys
import shutil
import tempfile
import subprocess
import urllib2
import tarfile
import logging
import zipfile

from pip.download import unpack_http_url
from pip.index import PackageFinder
from pip.req import InstallRequirement, RequirementSet
from pip.locations import build_prefix, src_prefix


PYTHONPATH = 'PYTHONPATH'


class BuildLocations(object):

    def __init__(self, ctx_root):
        self.root = mkdir(path.join(ctx_root, 'build'))
        self.dist = mkdir(path.join(ctx_root, 'dist'))
        self.dist_lib = mkdir(path.join(self.dist, 'lib'))
        self.dist_python = mkdir(path.join(self.dist_lib, 'python'))
        self.files = mkdir(path.join(ctx_root, 'files'))


class DeploymentLocations(object):

    def __init__(self, ctx_root, project_name):
        self.root = mkdir(path.join(ctx_root, 'layout'))

        self.usr = mkdir(path.join(self.root, 'usr'))
        self.usr_share = mkdir(path.join(self.usr, 'share'))
        self.project_share = mkdir(path.join(self.usr_share, project_name))
        self.etc = mkdir(path.join(self.root, 'etc'))


class BuildContext(object):

    def __init__(self, ctx_root, pkg_index, project_name):
        self.root = ctx_root
        self.pkg_index = pkg_index
        self.deploy = DeploymentLocations(ctx_root, project_name)
        self.build = BuildLocations(ctx_root)


def read(relative):
    contents = open(relative, 'r').read()
    return [l for l in contents.split('\n') if l != '']


def mkdir(location):
    if not path.exists(location):
        os.mkdir(location)
    return location


def download(url, dl_location):
    u = urllib2.urlopen(url)
    localFile = open(dl_location, 'w')
    localFile.write(u.read())
    localFile.close()


def run_python(bctx, cmd, cwd=None):
    env = os.environ.copy()
    env[PYTHONPATH] = bctx.build.dist_python
    run(cmd, cwd, env)


def run(cmd, cwd=None, env=None):
    print('>>> Exec: {}'.format(cmd))
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        close_fds=True)

    done = False
    while not done:
        line = proc.stdout.readline()
        if line:
            print(line.rstrip('\n'))
        else:
            done = True

    if proc.returncode and proc.returncode != 0:
        print('Failed with return code: {}'.format(proc.returncode))
        sys.exit(1)


def unpack(name, bctx, stage_hooks, filename, dl_target):
    if dl_target.endswith('.tar.gz') or dl_target.endswith('.tgz'):
        archive = tarfile.open(dl_target, mode='r|gz')
        build_location = path.join(
            bctx.build.root, filename.rstrip('.tar.gz'))
    elif dl_target.endswith('.zip'):
        archive = zipfile.ZipFile(dl_target, mode='r')
        build_location = path.join(bctx.build.root, filename.rstrip('.zip'))
    else:
        print('Unknown archive format: {}'.format(dl_target))
        raise Exception()

    archive.extractall(bctx.build.root)
    return build_location


def install_req(name, bctx, stage_hooks=None):
    req = InstallRequirement.from_line(name, None)
    found_req = bctx.pkg_index.find_requirement(req, False)
    dl_target = path.join(bctx.build.files, found_req.filename)

    # stages
    call_hook(name, 'download.before',
              stage_hooks, bctx=bctx, fetch_url=found_req.url)
    download(found_req.url, dl_target)
    call_hook(name, 'download.after',
              stage_hooks, bctx=bctx, archive=dl_target)

    call_hook(name, 'unpack.before',
              stage_hooks, bctx=bctx, archive=dl_target)
    build_location = unpack(
        name, bctx, stage_hooks, found_req.filename, dl_target)
    call_hook(name, 'unpack.after',
              stage_hooks, bctx=bctx, build_location=build_location)

    call_hook(name, 'build.before',
              stage_hooks, bctx=bctx, build_location=build_location)
    run_python(
        bctx,
        'python setup.py build'.format(build_location),
        build_location)
    call_hook(name, 'build.after',
              stage_hooks, bctx=bctx, build_location=build_location)

    call_hook(name, 'install.before',
              stage_hooks, bctx=bctx, build_location=build_location)
    run_python(
        bctx,
        'python setup.py install --home={}'.format(bctx.build.dist),
        build_location)
    call_hook(name, 'install.after',
              stage_hooks, bctx=bctx, build_location=build_location)


def call_hook(name, stage, stage_hooks, **kwargs):
    if stage_hooks:
        if name in stage_hooks:
            hooks = stage_hooks[name]
            if stage in hooks:
                hook = hooks[stage]
                print('Calling hook {} for stage {}'.format(hook, stage))
                hook(kwargs)


def read_requires(filename, bctx, pkg_index, hooks):
    lines = open(filename, 'r').read()

    ## TODO: Handle this exception better
    if not lines:
        raise Exception()

    for line in lines.split('\n'):
        if line and len(line) > 0:
            install_req(line, bctx, hooks)


def copytree(src, dst, symlinks=False):
    names = os.listdir(src)
    if not os.path.exists(dst):
        os.makedirs(dst)

    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)

        if symlinks and os.path.islink(srcname):
            linkto = os.readlink(srcname)
            os.symlink(linkto, dstname)
        elif os.path.isdir(srcname):
            copytree(srcname, dstname, symlinks)
        else:
            shutil.copy2(srcname, dstname)


def build(requirements_file, hooks, project_name, version):
    # Pip package finder is used to locate dependencies for downloading
    pkg_index = PackageFinder(
        find_links=[],
        index_urls=["http://pypi.python.org/simple/"])

    # Build context holds all of the directories and state information
    bctx = BuildContext(tempfile.mkdtemp(), pkg_index, project_name)

    # Build the project requirements and install them
    read_requires(requirements_file, bctx, pkg_index, hooks)

    # Build root after requirements are finished
    run_python(bctx, 'python setup.py build')
    run_python(bctx, 'python setup.py install --home={}'.format(
        bctx.build.dist))

    # Copy all of the important files into their intended destinations
    local_layout = path.join('.', 'pkg/layout')
    copytree(local_layout, bctx.deploy.root)

    # Copy the built virtualenv
    copytree(bctx.build.dist, bctx.deploy.project_share)

    # Let's build a tarfile
    tar_filename = '{}_{}.tar.gz'.format(project_name, version)
    tar_fpath = path.join(bctx.root, tar_filename)

    # Open the
    tarchive = tarfile.open(tar_fpath, 'w|gz')
    tarchive.add(bctx.deploy.root, arcname='')
    tarchive.close()

    # Copy the finished tafile
    shutil.copyfile(tar_fpath, path.join('.', tar_filename))

    # Clean the build dir
    print('Cleaning {}'.format(bctx.root))
    shutil.rmtree(bctx.root)


hooks = {
}

requirements_file = 'tools/pip-requires'

if len(sys.argv) != 2:
    print('usage: build.py <project-name>')
    exit(1)

version = read('VERSION')[0]

build(requirements_file, hooks, sys.argv[1], version)

########NEW FILE########
__FILENAME__ = resources
import falcon

from meniscus.api.tenant.resources import MESSAGE_TOKEN
from meniscus.api import (ApiResource, handle_api_exception)
from meniscus.correlation import correlator
from meniscus.api.validator_init import get_validator


class PublishMessageResource(ApiResource):

    @handle_api_exception(operation_name='Publish Message POST')
    @falcon.before(get_validator('correlation'))
    def on_post(self, req, resp, tenant_id, validated_body):
        """
        This method is passed log event data by a tenant. The request will
        have a message token and a tenant id which must be validated either
        by the local cache or by a call to this workers coordinator.
        """

        #Validate the tenant's JSON event log data as valid JSON.
        message = validated_body['log_message']

        #read message token from header
        message_token = req.get_header(MESSAGE_TOKEN, required=True)

        # Queue the message for correlation
        correlator.correlate_http_message.delay(tenant_id,
                                                message_token,
                                                message)

        resp.status = falcon.HTTP_202

########NEW FILE########
__FILENAME__ = resources
"""
The Status Resources module provides RESTful operations for managing
Worker status.  This includes the updating of a worker's status as well as the
retrieval of the status of a specified worker node, or all workers.
"""
import falcon

from meniscus import api
from meniscus.api.validator_init import get_validator
from meniscus.data.model.worker import SystemInfo
from meniscus.data.model import worker_util
from meniscus.data.model.worker import Worker


class WorkerStatusResource(api.ApiResource):
    """
    A resource for updating and retrieving data for a single worker node
    """

    @api.handle_api_exception(operation_name='WorkerStatus PUT')
    @falcon.before(get_validator('worker_status'))
    def on_put(self, req, resp, hostname, validated_body):
        """
        updates a worker's status or creates a new worker entry if not found
        """

        #load validated json payload in body
        body = validated_body['worker_status']

        #find the worker in db
        worker = worker_util.find_worker(hostname)

        if worker is None:
            #instantiate new worker object
            new_worker = Worker(**body)
            #persist the new worker
            worker_util.create_worker(new_worker)
            resp.status = falcon.HTTP_202
            return

        if 'status' in body:
            worker.status = body['status']

        if 'system_info' in body:
            worker.system_info = SystemInfo(**body['system_info'])

        worker_util.save_worker(worker)
        resp.status = falcon.HTTP_200

    @api.handle_api_exception(operation_name='WorkerStatus GET')
    def on_get(self, req, resp, hostname):
        """
        Retrieve the status of a specified worker node
        """
        #find the worker in db
        worker = worker_util.find_worker(hostname)

        if worker is None:
            api.abort(falcon.HTTP_404, 'Unable to locate worker.')

        resp.status = falcon.HTTP_200
        resp.body = api.format_response_body({'status': worker.get_status()})


class WorkersStatusResource(api.ApiResource):
    """
    A resource for retrieving data about all worker nodes in a meniscus cluster
    """

    @api.handle_api_exception(operation_name='WorkersStatus GET')
    def on_get(self, req, resp):
        """
        Retrieve the status of all workers in the meniscus cluster
        """

        workers = worker_util.retrieve_all_workers()

        workers_status = [
            worker.get_status()
            for worker in workers]

        resp.status = falcon.HTTP_200
        resp.body = api.format_response_body({'status': workers_status})

########NEW FILE########
__FILENAME__ = resources
"""
The Tenant Resources module provides RESTful operations for managing
Tenants and their configurations.  This includes the creating and updating
of new Tenants, creation, update and deletion of Event Producer definitions,
and the management of Tokens.
"""
import falcon

from meniscus import api
from meniscus.api.validator_init import get_validator
from meniscus.data.model import tenant_util
from meniscus.openstack.common.timeutils import parse_isotime
from meniscus.openstack.common.timeutils import isotime


MESSAGE_TOKEN = 'MESSAGE-TOKEN'
MIN_TOKEN_TIME_LIMIT_HRS = 3


def _tenant_not_found():
    """
    sends an http 404 response to the caller
    """
    api.abort(falcon.HTTP_404, 'Unable to locate tenant.')


def _producer_not_found():
    """
    sends an http 404 response to the caller
    """
    api.abort(falcon.HTTP_404, 'Unable to locate event producer.')


def _message_token_is_invalid():
    """
    sends an http 404 response to the caller
    """
    api.abort(falcon.HTTP_404)


def _token_time_limit_not_reached():
    """
    sends an http 409 response to the caller
    """
    api.abort(
        falcon.HTTP_409,
        'Message tokens can only be changed once every {0} hours'
        .format(MIN_TOKEN_TIME_LIMIT_HRS))


class TenantResource(api.ApiResource):
    """
    The tenant Resource allows for the creation of new tenants in the system.
    """

    @api.handle_api_exception(operation_name='TenantResource POST')
    @falcon.before(get_validator('tenant'))
    def on_post(self, req, resp, validated_body):
        """
        Create a new tenant when a HTTP POST is received
        """

        body = validated_body['tenant']
        tenant_id = str(body['tenant_id'])

        tenant_name = body.get('tenant_name', tenant_id)

        #validate that tenant does not already exists
        tenant = tenant_util.find_tenant(tenant_id=tenant_id)
        if tenant:
            api.abort(falcon.HTTP_400, 'Tenant with tenant_id {0} '
                      'already exists'.format(tenant_id))

        tenant_util.create_tenant(tenant_id=tenant_id, tenant_name=tenant_name)

        resp.status = falcon.HTTP_201
        resp.set_header('Location', '/v1/{0}'.format(tenant_id))


class UserResource(api.ApiResource):
    """
    User Resource allows for retrieval of existing tenants.
    """

    @api.handle_api_exception(operation_name='UserResource GET')
    def on_get(self, req, resp, tenant_id):
        """
        Retrieve a specified tenant when a HTTP GET is received
        """
        tenant = tenant_util.find_tenant(
            tenant_id=tenant_id, create_on_missing=True)

        if not tenant:
            _tenant_not_found()

        resp.status = falcon.HTTP_200
        resp.body = api.format_response_body({'tenant': tenant.format()})


class EventProducersResource(api.ApiResource):
    """
    The Event Producer resource allows for the creation of new Event Producers
    and retrieval of all Event Producers for a Tenant
    """

    @api.handle_api_exception(operation_name='Event Producers GET')
    def on_get(self, req, resp, tenant_id):
        """
        Retrieve a list of all Event Producers for a specified Tenant
        """
        tenant = tenant_util.find_tenant(tenant_id=tenant_id)

        if not tenant:
            _tenant_not_found()

        resp.status = falcon.HTTP_200
        resp.body = api.format_response_body(
            {'event_producers': [p.format() for p in tenant.event_producers]})

    @api.handle_api_exception(operation_name='Event Producers POST')
    @falcon.before(get_validator('tenant'))
    def on_post(self, req, resp, tenant_id, validated_body):
        """
        Create a a new event Producer for a specified Tenant
        when an HTTP Post is received
        """
        body = validated_body['event_producer']

        tenant = tenant_util.find_tenant(tenant_id=tenant_id)

        if not tenant:
            _tenant_not_found()

        event_producer_name = body['name']
        event_producer_pattern = body['pattern']

        #if durable or encrypted aren't specified, set to False
        if 'durable' in body.keys():
            event_producer_durable = body['durable']
        else:
            event_producer_durable = False

        if 'encrypted' in body.keys():
            event_producer_encrypted = body['encrypted']
        else:
            event_producer_encrypted = False

        if 'sinks' in body.keys():
            event_producer_sinks = body['sinks']
        else:
            event_producer_sinks = None

        # Check if the tenant already has an event producer with this name
        producer = tenant_util.find_event_producer(
            tenant, producer_name=event_producer_name)
        if producer:
            api.abort(
                falcon.HTTP_400,
                'Event producer with name {0} already exists with id={1}.'
                .format(producer.name, producer.get_id()))

        # Create the new profile for the host
        producer_id = tenant_util.create_event_producer(
            tenant,
            event_producer_name,
            event_producer_pattern,
            event_producer_durable,
            event_producer_encrypted,
            event_producer_sinks)

        resp.status = falcon.HTTP_201
        resp.set_header('Location',
                        '/v1/{0}/producers/{1}'
                        .format(tenant_id, producer_id))


class EventProducerResource(api.ApiResource):
    """
    EventProducer Resource allows for the retrieval and update of a
    specified Event Producer for a Tenant.
    """

    @api.handle_api_exception(operation_name='Event Producer GET')
    def on_get(self, req, resp, tenant_id, event_producer_id):
        """
        Retrieve a specified Event Producer from a Tenant
        when an HTTP GET is received
        """
        #verify the tenant exists
        tenant = tenant_util.find_tenant(tenant_id=tenant_id)

        if not tenant:
            _tenant_not_found()

        #verify the event_producer exists and belongs to the tenant
        event_producer = tenant_util.find_event_producer(
            tenant, producer_id=event_producer_id)
        if not event_producer:
            _producer_not_found()

        resp.status = falcon.HTTP_200
        resp.body = api.format_response_body(
            {'event_producer': event_producer.format()})

    @api.handle_api_exception(operation_name='Event Producer PUT')
    @falcon.before(get_validator('tenant'))
    def on_put(self, req, resp, tenant_id, event_producer_id, validated_body):
        """
        Make an update to a specified Event Producer's configuration
        when an HTTP PUT is received
        """

        body = validated_body['event_producer']

        #verify the tenant exists
        tenant = tenant_util.find_tenant(tenant_id=tenant_id)

        if not tenant:
            _tenant_not_found()

        #verify the event_producer exists and belongs to the tenant
        event_producer = tenant_util.find_event_producer(
            tenant, producer_id=event_producer_id)
        if not event_producer:
            _producer_not_found()

        #if a key is present, update the event_producer with the value
        if 'name' in body.keys() and event_producer.name != body['name']:
            #if the tenant already has a profile with this name then abort
            duplicate_producer = tenant_util.find_event_producer(
                tenant,  producer_name=body['name'])
            if duplicate_producer:
                api.abort(
                    falcon.HTTP_400,
                    'EventProducer with name {0} already exists with id={1}.'
                    .format(duplicate_producer.name,
                            duplicate_producer.get_id()))
            event_producer.name = body['name']

        if 'pattern' in body:
            event_producer.pattern = str(body['pattern'])

        if 'durable' in body:
            event_producer.durable = body['durable']

        if 'encrypted' in body:
            event_producer.encrypted = body['encrypted']

        if 'sinks' in body:
            event_producer.sinks = body['sinks']

        #save the tenant document
        tenant_util.save_tenant(tenant)

        resp.status = falcon.HTTP_200

    @api.handle_api_exception(operation_name='Event Producer DELETE')
    def on_delete(self, req, resp, tenant_id, event_producer_id):
        """
        Delete a specified Event Producer from a Tenant's configuration
        when an HTTP DELETE is received
        """
        #verify the tenant exists
        tenant = tenant_util.find_tenant(tenant_id=tenant_id)

        if not tenant:
            _tenant_not_found()

        #verify the event_producer exists and belongs to the tenant
        event_producer = tenant_util.find_event_producer(
            tenant, producer_id=event_producer_id)
        if not event_producer:
            _producer_not_found()

        tenant_util.delete_event_producer(tenant, event_producer)

        resp.status = falcon.HTTP_200


class TokenResource(api.ApiResource):
    """
    The Token Resource manages Tokens for a tenant
    and provides validation operations.
    """

    @api.handle_api_exception(operation_name='Token HEAD')
    def on_head(self, req, resp, tenant_id):
        """
        Validates a token for a specified tenant
        when an HTTP HEAD call is received
        """

        #get message token, or abort if token is not in header
        message_token = req.get_header(MESSAGE_TOKEN, required=True)

        #verify the tenant exists
        tenant = tenant_util.find_tenant(tenant_id=tenant_id)

        if not tenant:
            _tenant_not_found()

        if not tenant.token.validate_token(message_token):
            _message_token_is_invalid()

        resp.status = falcon.HTTP_200

    @api.handle_api_exception(operation_name='Token GET')
    def on_get(self, req, resp, tenant_id):
        """
        Retrieves Token information for a specified Tenant
        when an HTTP GET call is received
        """

        #verify the tenant exists
        tenant = tenant_util.find_tenant(tenant_id=tenant_id)

        if not tenant:
            _tenant_not_found()

        resp.status = falcon.HTTP_200
        resp.body = api.format_response_body({'token': tenant.token.format()})

    def _validate_token_min_time_limit_reached(self, token):
        """
        Tokens are giving a minimum time limit between resets.  This private
        method validates that the time limit has been reached.
        """
        #get the token create time and the current time as datetime objects
        token_created = parse_isotime(token.last_changed)
        current_time = parse_isotime(isotime(subsecond=True))

        #get a datetime.timedelta object that represents the difference
        time_diff = current_time - token_created
        hours_diff = time_diff.total_seconds() / 3600

        #if the time limit has not been reached, abort and alert the caller
        if hours_diff < MIN_TOKEN_TIME_LIMIT_HRS:
            _token_time_limit_not_reached()

        return True

    @api.handle_api_exception(operation_name='Token POST')
    @falcon.before(get_validator('tenant'))
    def on_post(self, req, resp, tenant_id, validated_body):
        """
        This method resets a token when an HTTP POST is received.  There is
        a minimum time limit that must be reached before resetting a token,
        unless the call is made  with the "invalidate_now: true" option.
        """

        body = validated_body['token']

        #verify the tenant exists
        tenant = tenant_util.find_tenant(tenant_id=tenant_id)

        if not tenant:
            _tenant_not_found()

        invalidate_now = body['invalidate_now']

        if invalidate_now:
            #immediately invalidate the token
            tenant.token.reset_token_now()

        else:
            self._validate_token_min_time_limit_reached(tenant.token)
            tenant.token.reset_token()

        #save the tenant document
        tenant_util.save_tenant(tenant)

        resp.status = falcon.HTTP_203
        resp.set_header('Location', '/v1/{0}/token'.format(tenant_id))

########NEW FILE########
__FILENAME__ = request
import requests

from meniscus import env


_LOG = env.get_logger(__name__)


HTTP_VERBS = (
    'GET',
    'POST',
    'DELETE',
    'PUT',
    'HEAD'
)


def http_request(url, add_headers=None, json_payload='{}', http_verb='GET',
                 request_timeout=1.0):
    headers = {'content-type': 'application/json'}

    if add_headers:
        headers.update(add_headers)
    http_verb = str(http_verb).upper()

    if not http_verb in HTTP_VERBS:
        raise ValueError(
            'Invalid HTTP verb supplied: {0}'.format(http_verb))

    try:
        if http_verb == 'GET':
            return requests.get(url, headers=headers, timeout=request_timeout)
        elif http_verb == 'POST':
            return requests.post(url, data=json_payload, headers=headers,
                                 timeout=request_timeout)
        elif http_verb == 'DELETE':
            return requests.delete(url, data=json_payload, headers=headers,
                                   timeout=request_timeout)
        elif http_verb == 'PUT':
            return requests.put(url, data=json_payload, headers=headers,
                                timeout=request_timeout)
        elif http_verb == 'HEAD':
            return requests.head(url, headers=headers, timeout=request_timeout)

    except requests.ConnectionError as conn_err:
        _LOG.exception(conn_err.message)
        raise conn_err
    except requests.HTTPError as http_err:
        _LOG.exception(http_err.message)
        raise http_err
    except requests.RequestException as req_err:
        _LOG.exception(req_err.message)
        raise req_err

########NEW FILE########
__FILENAME__ = sys_assist
import fcntl
import multiprocessing
import os
import socket
import struct
import subprocess
import sys

from oslo.config import cfg

from meniscus import env
from meniscus import config


_LOG = env.get_logger(__name__)


_network_interface_group = cfg.OptGroup(
    name='network_interface',
    title='Default network interface name'
)
config.get_config().register_group(_network_interface_group)

_network_interface_options = [
    cfg.StrOpt('default_ifname',
               default='eth0',
               help="""The default network interface to pull the IP from"""
               )
]

config.get_config().register_opts(
    _network_interface_options,
    group=_network_interface_group
)

try:
    config.init_config()
except config.cfg.ConfigFilesNotFoundError as ex:
    _LOG.exception(ex.message)

conf = config.get_config()

DEFAULT_NETWORK_IFNAME = conf.network_interface.default_ifname


def get_sys_mem_total_kB():
    memory_total = None
    if 'linux' in sys.platform:
        memory_line = None
        for line in open("/proc/meminfo"):
            if 'MemTotal:' in line:
                memory_line = line
                break

        if memory_line:
            memory_line = memory_line.replace('MemTotal:', '').strip()
            memory_line = memory_line.replace('kB', '')
            memory_line = memory_line.strip()
            memory_total = int(memory_line)

    return memory_total


def get_sys_mem_total_MB():
    memory_total_kb = get_sys_mem_total_kB()
    if memory_total_kb:
        memory_total_mb = memory_total_kb / 1024
        return memory_total_mb


def get_disk_size_GB(file_sys='/'):
    disk_size = None
    if 'linux' in sys.platform:
        file_system = os.statvfs(file_sys)
        disk_size = (file_system.f_blocks * file_system.f_frsize) / (1024 ** 3)

    return disk_size


def get_disk_usage():

    def get_size_in_GB(disk_size):
        if 'G' in disk_size:
            return float(disk_size.replace('G', ''))
        if 'M' in disk_size:
            return float(disk_size.replace('M', '')) / 1024
        if 'K' in disk_size:
            return float(disk_size.replace('K', '')) / (1024 ** 2)
        return 0

    disk_usage = dict()

    if 'linux' in sys.platform:
        df_command = subprocess.Popen(["df", "-h"], stdout=subprocess.PIPE)
        df_output = df_command.communicate()[0]
        disk_usage = list()
        for file_system in df_output.split("\n")[1:]:
            if 'none'not in file_system:
                try:
                    name,  size, used, avail, use, mount = file_system.split()
                    device = {
                        'device': name,
                        'total': get_size_in_GB(size),
                        'used': get_size_in_GB(used)}
                    disk_usage.append(device)
                except ValueError:
                    pass
    return disk_usage


def get_interface_ip(ifname=DEFAULT_NETWORK_IFNAME):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(
            fcntl.ioctl(s.fileno(), 0x8915,
                        struct.pack('256s', ifname[:15]))[20:24])
    except IOError:
        pass

    try:
        return socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        return '127.0.0.1'


def get_cpu_core_count():
    return multiprocessing.cpu_count()


def get_load_average():
    load_average = os.getloadavg()
    return {
        '1': load_average[0],
        '5': load_average[1],
        '15': load_average[2]
    }

########NEW FILE########
__FILENAME__ = validator_init
import os

from oslo.config import cfg

import meniscus
from meniscus.validation import jsonv
import meniscus.config as config
from meniscus import env
from meniscus.validation.integration.falcon_hooks import validation_hook


_LOG = env.get_logger(__name__)

# Celery configuration options
_JSON_SCHEMA_GROUP = cfg.OptGroup(
    name='json_schema', title='Json Schema Options')
config.get_config().register_group(_JSON_SCHEMA_GROUP)

default_schema_path = '{0}etc/meniscus/schemas/'.format(
    os.path.dirname(meniscus.__file__).rstrip('meniscus'))

_JSON_SCHEMA = [
    cfg.StrOpt('schema_dir',
               default=default_schema_path,
               help="""directory holding json schema files"""
               )
]

config.get_config().register_opts(_JSON_SCHEMA, group=_JSON_SCHEMA_GROUP)

try:
    config.init_config()
except config.cfg.ConfigFilesNotFoundError as ex:
    _LOG.exception(ex.message)

conf = config.get_config()

_schema_loader = jsonv.DirectorySchemaLoader(conf.json_schema.schema_dir)
_validation_factory = jsonv.JsonSchemaValidatorFactory(_schema_loader)


def get_validator(schema_name):
    return validation_hook(_validation_factory.get_validator(schema_name))

########NEW FILE########
__FILENAME__ = resources
import falcon

from meniscus.api import ApiResource
from meniscus.api import format_response_body


class VersionResource(ApiResource):
    """ Return the current version of the API """

    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.body = format_response_body({'v1': 'current'})

########NEW FILE########
__FILENAME__ = app
import platform

from oslo.config import cfg

from meniscus.config import get_config
from meniscus.config import init_config
from meniscus.data.cache_handler import ConfigCache
from meniscus.data.model.worker import WorkerConfiguration
from meniscus.ext.plugin import import_module
from meniscus import env
from meniscus.openstack.common import log


log.setup('meniscus')
_LOG = env.get_logger(__name__)

# default configuration options
_node_group = cfg.OptGroup(name='node', title='Node')
get_config().register_group(_node_group)

_NODE_OPTIONS = [
    cfg.StrOpt('personality',
               default='worker',
               help="""The personality to load"""
               ),
    cfg.StrOpt('coordinator_uri',
               default='http://localhost:8080/v1',
               help="""The URI of the Coordinator (can be a load balancer)"""
               )
]

get_config().register_opts(_NODE_OPTIONS, group=_node_group)
try:
    init_config()
    conf = get_config()
except cfg.ConfigFilesNotFoundError:
    conf = get_config()

PERSONALITY = conf.node.personality
COORDINATOR_URI = conf.node.coordinator_uri

config_cache = ConfigCache()


def bootstrap_api():
    # Persist the coordinator_uri and personality to ConfigCache
    config = WorkerConfiguration(PERSONALITY, platform.node(),
                                 COORDINATOR_URI)
    config_cache.set_config(config)

    personality_module = 'meniscus.personas.{0}.app'.format(PERSONALITY)
    _LOG.info('loading default personality module: {0}'
        .format(personality_module))

    #load the personality module as a plug in
    plugin_mod = import_module(personality_module)

    #start up the api from the specified personality_module
    return plugin_mod.start_up()

application = bootstrap_api()

########NEW FILE########
__FILENAME__ = config
import os
from oslo.config import cfg


def _get(name, default=None):
    value = os.environ.get(name)
    return value if value else default


_DEFAULT_CONFIG_ARGS = [
    '--config-file',
    _get('CONFIG_FILE', '/etc/meniscus/meniscus.conf')
]

_config_opts = cfg.ConfigOpts()


def get_config():
    return _config_opts


def init_config(cfg_args=_DEFAULT_CONFIG_ARGS):
    _config_opts(args=cfg_args)

########NEW FILE########
__FILENAME__ = correlator
"""
This Module is a pipeline of correlation related methods used to validate and
format incoming messages. Entry points into the correlation pipeline have been
implemented as asynchronous tasks. This allows for failures due to network
communications or heavy load to be retried, and also allows for messages to be
persisted in case of a service restart.

There are 2 entry points into the pipeline, one for messages that are received
from a syslog parser, and another entry point for messages posted to the
http_log endpoint.

Case 1 - Syslog: Entry point - correlate_src_syslog_message

    calls method to format syslog message to CEE
    before following the same pipeline as the HTTP entry point

Case 2 - HTTP: Entry point - correlate_src_http_message

    Token Validation - messages contain a tenant_id and message token which
    are used to validate a message. Previously validated tokens are stored in
    a local cache for faster processing. Message validation is first attempted
    by looking up information in the local cache. If the cache does not contain
    the necessary information to validate the message, the the message
    validation is attempted by making http calls to the Tenant API hosted on
    the coordinator.

    Add Tenant Data to Message - After validating the message, configuration
    data from the tenant used for processing the message are added to the
    message dictionary

    Normalization or Storage - The data added to the message is used to decide
    whether the message should be queued for normalization or for storage.
"""

import httplib
import requests

from meniscus import env
from meniscus.api.tenant.resources import MESSAGE_TOKEN
from meniscus.api.utils.request import http_request
from meniscus.correlation import errors
from meniscus.data import cache_handler
from meniscus.data.model.tenant import EventProducer
from meniscus.data.model import tenant_util
from meniscus.normalization import normalizer
from meniscus.openstack.common import timeutils
from meniscus.queue import celery
from meniscus import sinks

_LOG = env.get_logger(__name__)


@celery.task(acks_late=True, max_retries=None,
             ignore_result=True, serializer="json")
def correlate_syslog_message(message):
    """
    Entry point into correlation pipeline for messages received from the
    syslog parser after being converted to JSON. These messages must be
    converted into CEE format for processing.

    This entry point is implemented as a queued task. The parameters in the
    task decorator allow for the task to be retried indefinitely int he event
    of network failure (store & forward). Exceptions thrown from failed
    validation or a malformed message do not initiate a retry but instead
    allow the task to fail.
    """
    try:
        _format_message_cee(message)

    # Catch all CoordinationCommunicationErrors and retry the task.
    # All other Exceptions will fail the task.
    except errors.CoordinatorCommunicationError as ex:
        _LOG.exception(ex.message)
        raise correlate_syslog_message.retry()


@celery.task(acks_late=True, max_retries=None,
             ignore_result=True, serializer="json")
def correlate_http_message(tenant_id, message_token, message):
    """
    Entry point into correlation pipeline for messages received from the
    PublishMessage resource. These messages should already comply with CEE
    format as this is enforced when the message is posted to the endpoint.

    This entry point is implemented as a queued task. The parameters in the
    task decorator allow for the task to be retried indefinitely int he event
    of network failure (store & forward). Exceptions thrown from failed
    validation or a malformed message do not initiate a retry but instead allow
    the task to fail.
    """
    try:
        #enter the pipeline by beginning mesage validation
        _validate_token_from_cache(tenant_id, message_token, message)

    # Catch all CoordinationCommunicationErrors and retry the task.
    # All other Exceptions will fail the task.
    except errors.CoordinatorCommunicationError as ex:
        _LOG.exception(ex.message)
        raise correlate_http_message.retry()


def _format_message_cee(message):
    """
    Format message as CEE and begin message validation. The incoming message
    originates a syslog message (RFC 5424) that has been received on the syslog
    endpoint and parsed into the following JSON format:

        {
            "PRIORITY": "{RFC 5424 PRI}",
            "VERSION": "{RFC 5424 VERSION}",
            "ISODATE": "{RFC 5424 TIMESTAMP}",
            "HOST": "{RFC 5424 HOSTNAME}",
            "PROGRAM": "{RFC 5424 APPNAME}",
            "PID": "{RFC 5424 PROCID}",
            "MSGID": "{RFC 5424 MSGID}",
            "SDATA": {
            "meniscus": {
            "tenant": "{tenantid}",
            "token": "{message-token}"
        },
            "any client_data": {}
        }
            "MESSAGE": "{RFC 5424 MSG}"
        }

        After conversion to CEE, the message will have the following format:

        {
            "pri": "{PRIORITY}",
            "ver": "{VERSION}",
            "time": "{ISODATE}",
            "host": "{HOST}",
            "pname": "{PROGRAM}",
            "pid": "{PID}",
            "msgid": "{MSGID}",
            "msg": "{MSG}",
            "native": "{_SDATA}"
        }
    """
    try:
        meniscus_sd = message['_SDATA']['meniscus']
        tenant_id = meniscus_sd['tenant']
        message_token = meniscus_sd['token']

    #if there is a key error then the syslog message did
    #not contain necessary credential information
    except KeyError:
        error_message = 'tenant_id or message token not provided'
        _LOG.debug('Message validation failed: {0}'.format(error_message))
        raise errors.MessageValidationError(error_message)

    # format to CEE
    cee_message = dict()

    cee_message['time'] = message.get('ISODATE', '-')
    cee_message['host'] = message.get('HOST', '-')
    cee_message['pname'] = message.get('PROGRAM', '-')
    cee_message['pri'] = message.get('PRIORITY', '-')
    cee_message['ver'] = message.get('VERSION', "1")
    cee_message['pid'] = message.get('PID', '-')
    cee_message['msgid'] = message.get('MSGID', '-')
    cee_message['msg'] = message.get('MESSAGE', '-')
    cee_message['native'] = message.get('_SDATA', {})

    #send the new cee_message to be validated
    _validate_token_from_cache(tenant_id, message_token, cee_message)


def _validate_token_from_cache(tenant_id, message_token, message):
    """
    validate token from cache:
        Attempt to validate the message against the local cache.
        If successful, send off to retrieve the tenant information.
        If the token does not exist in the cache, send off to validate with
        the coordinator.
    """

    token_cache = cache_handler.TokenCache()
    token = token_cache.get_token(tenant_id)

    if token:
        #validate token
        if not token.validate_token(message_token):
            raise errors.MessageAuthenticationError(
                'Message not authenticated, check your tenant id '
                'and or message token for validity')

        # hand off the message to retrieve tenant information
        _get_tenant_from_cache(tenant_id, message_token, message)
    else:
        # hand off the message to validate the token with the coordinator
        _validate_token_with_coordinator(tenant_id, message_token, message)


def _get_tenant_from_cache(tenant_id, message_token, message):
    """
    Retrieve tenant information from local cache. If tenant data exists in
    local cache, hand off message to be packed with correlation data. If the
    tenant data is not in cache, hand off message for tenant data to be
    retrieved from coordinator
    """
    tenant_cache = cache_handler.TenantCache()
    #get the tenant object from cache
    tenant = tenant_cache.get_tenant(tenant_id)

    if not tenant:
        _get_tenant_from_coordinator(tenant_id, message_token, message)
    else:
        _add_correlation_info_to_message(tenant, message)


def _validate_token_with_coordinator(tenant_id, message_token, message):
    """
    Call coordinator to validate the message token. If token is validated,
    persist the token in the local cache for future lookups, and hand off
    message to retrieve tenant information.
    """

    config = _get_config_from_cache()
    try:
        resp = http_request(
            '{0}/tenant/{1}/token'.format(config.coordinator_uri, tenant_id),
            {MESSAGE_TOKEN: message_token, 'hostname': config.hostname},
            http_verb='HEAD')

    except requests.RequestException as ex:
        _LOG.exception(ex.message)
        raise errors.CoordinatorCommunicationError

    if resp.status_code != httplib.OK:
        raise errors.MessageAuthenticationError(
            'Message not authenticated, check your tenant id '
            'and or message token for validity')

    # hand off the message to validate the tenant with the coordinator
    _get_tenant_from_coordinator(tenant_id, message_token, message)


def _get_tenant_from_coordinator(tenant_id, message_token, message):
    """
    This method retrieves tenant data from the coordinator, and persists the
    tenant data in the local cache for future lookups. The message is then
    handed off to be packed with correlation data.
    """

    config = _get_config_from_cache()

    try:
        resp = http_request(
            '{0}/tenant/{1}'.format(config.coordinator_uri, tenant_id),
            {MESSAGE_TOKEN: message_token, 'hostname': config.hostname},
            http_verb='GET')

    except requests.RequestException as ex:
        _LOG.exception(ex.message)
        raise errors.CoordinatorCommunicationError

    if resp.status_code == httplib.OK:
        response_body = resp.json()

        #load new tenant data from response body
        tenant = tenant_util.load_tenant_from_dict(response_body['tenant'])

        # update the cache with new tenant info
        _save_tenant_to_cache(tenant_id, tenant)

        # add correlation to message
        _add_correlation_info_to_message(tenant, message)

    elif resp.status_code == httplib.NOT_FOUND:
        error_message = 'unable to locate tenant.'
        _LOG.debug(error_message)
        raise errors.ResourceNotFoundError(error_message)
    else:
        #coordinator responds, but coordinator datasink could be unreachable
        raise errors.CoordinatorCommunicationError


def _add_correlation_info_to_message(tenant, message):
    """
    Pack the message with correlation data. The message will be update by
    adding a dictionary named "meniscus" that contains tenant specific
    information used in processing the message.
    """
    #match the producer by the message pname
    producer = tenant_util.find_event_producer(tenant,
                                               producer_name=message['pname'])

    #if the producer is not found, create a default producer
    if not producer:
        producer = EventProducer(_id=None, name="default", pattern="default")

    #create correlation dictionary
    correlation_dict = {
        'tenant_name': tenant.tenant_name,
        'ep_id': producer.get_id(),
        'pattern': producer.pattern,
        'durable': producer.durable,
        'encrypted': producer.encrypted,
        '@timestamp': timeutils.utcnow(),
        'sinks': producer.sinks,
        "destinations": dict()
    }

    #configure sink dispatch
    for sink in producer.sinks:
        correlation_dict["destinations"][sink] = {'transaction_id': None,
                                                  'transaction_time': None}

    # After successful correlation remove meniscus information from structured
    # data so that the client's token is scrubbed form the message.
    message['native'].pop('meniscus', None)
    message.update({'meniscus': {'tenant': tenant.tenant_id,
                                 'correlation': correlation_dict}})

    # If the message data indicates that the message has normalization rules
    # that apply, Queue the message for normalization processing
    if normalizer.should_normalize(message):
        # send the message to normalization then route to sink
        normalizer.normalize_message.delay(message)
    else:
        # Queue the message for indexing/storage
        sinks.route_message(message)


def _save_tenant_to_cache(tenant_id, tenant):
    """
    saves validated tenant and token to cache to reduce validation calls to the
    coordinator
    """
    tenant_cache = cache_handler.TenantCache()
    token_cache = cache_handler.TokenCache()

    #save token and tenant information to cache
    token_cache.set_token(tenant_id, tenant.token)
    tenant_cache.set_tenant(tenant)


def _get_config_from_cache():
    config_cache = cache_handler.ConfigCache()
    return config_cache.get_config()

########NEW FILE########
__FILENAME__ = errors
class PublishMessageError(Exception):
    def __init__(self, msg=str()):
        self.msg = msg
        super(PublishMessageError, self).__init__(self.msg)


class MessageValidationError(PublishMessageError):
    pass


class MessageAuthenticationError(PublishMessageError):
    pass


class ResourceNotFoundError(PublishMessageError):
    pass


class CoordinatorCommunicationError(PublishMessageError):
    pass

########NEW FILE########
__FILENAME__ = receiver
from meniscus import env
from meniscus.correlation import correlator
from meniscus import transport

from meniscus.normalization.normalizer import *

_LOG = env.get_logger(__name__)


class CorrelationInputServer(transport.ZeroMQInputServer):

    def process_msg(self):
        msg = self._get_msg()

        try:
            #Queue the message for correlation
            correlator.correlate_syslog_message.delay(msg)
        except Exception:
            _LOG.exception('unable to place persist_message task on queue')


def new_correlation_input_server():
    """
    Create a correlation input server for receiving json messages form the
    syslog parser of ZeroMQ
    """
    zmq_receiver = transport.new_zmq_receiver()
    return CorrelationInputServer(zmq_receiver)

########NEW FILE########
__FILENAME__ = cache_handler
from oslo.config import cfg

from meniscus.config import get_config
from meniscus.config import init_config
from meniscus.data.model.tenant import (
    load_tenant_from_dict, load_token_from_dict)
from meniscus.data.model.worker import WorkerConfiguration
from meniscus.openstack.common import jsonutils
from meniscus.proxy import NativeProxy


# cache configuration options
_cache_group = cfg.OptGroup(name='cache', title='Cache Options')
get_config().register_group(_cache_group)

_CACHE_OPTIONS = [
    cfg.IntOpt('default_expires',
               default=3600,
               help="""default time to keep items in cache"""
               ),
    cfg.IntOpt('config_expires',
               default=0,
               help="""Default time to keep worker config items in cache."""
               ),
    cfg.StrOpt('cache_config',
               default='cache-config',
               help="""The name of the cache to store worker config values"""
               ),
    cfg.StrOpt('cache_tenant',
               default='cache-tenant',
               help="""The name of the cache to store worker config values"""
               ),
    cfg.StrOpt('cache_token',
               default='cache-token',
               help="""The name of the cache to store worker config values"""
               )
]

get_config().register_opts(_CACHE_OPTIONS, group=_cache_group)
try:
    init_config()
    conf = get_config()
except cfg.ConfigFilesNotFoundError:
    conf = get_config()

DEFAULT_EXPIRES = conf.cache.default_expires
CONFIG_EXPIRES = conf.cache.config_expires
CACHE_CONFIG = conf.cache.cache_config
CACHE_TENANT = conf.cache.cache_tenant
CACHE_TOKEN = conf.cache.cache_token


class Cache(object):
    def __init__(self):
        self.cache = NativeProxy()

    def clear(self):
        raise NotImplementedError


class ConfigCache(Cache):
    def clear(self):
        self.cache.cache_clear(CACHE_CONFIG)

    def set_config(self, worker_config):
        if self.cache.cache_exists('worker_configuration', CACHE_CONFIG):
            self.cache.cache_update(
                'worker_configuration',
                jsonutils.dumps(worker_config.format()),
                CONFIG_EXPIRES, CACHE_CONFIG)
        else:
            self.cache.cache_set(
                'worker_configuration',
                jsonutils.dumps(worker_config.format()),
                CONFIG_EXPIRES, CACHE_CONFIG)

    def get_config(self):
        if self.cache.cache_exists('worker_configuration', CACHE_CONFIG):
            config = jsonutils.loads(
                self.cache.cache_get('worker_configuration', CACHE_CONFIG))
            worker_config = WorkerConfiguration(**config)
            return worker_config
        return None

    def delete_config(self):
        if self.cache.cache_exists('worker_configuration', CACHE_CONFIG):
            self.cache.cache_del('worker_configuration', CACHE_CONFIG)


class TenantCache(Cache):
    def clear(self):
        self.cache.cache_clear(CACHE_TENANT)

    def set_tenant(self, tenant):
        if self.cache.cache_exists(tenant.tenant_id, CACHE_TENANT):
            self.cache.cache_update(
                tenant.tenant_id, jsonutils.dumps(tenant.format()),
                DEFAULT_EXPIRES, CACHE_TENANT)
        else:
            self.cache.cache_set(
                tenant.tenant_id, jsonutils.dumps(tenant.format()),
                DEFAULT_EXPIRES, CACHE_TENANT)

    def get_tenant(self, tenant_id):
        if self.cache.cache_exists(tenant_id, CACHE_TENANT):
            tenant_dict = jsonutils.loads(
                self.cache.cache_get(tenant_id, CACHE_TENANT))
            tenant = load_tenant_from_dict(tenant_dict)
            return tenant

        return None

    def delete_tenant(self, tenant_id):
        if self.cache.cache_exists(tenant_id, CACHE_TENANT):
            self.cache.cache_del(tenant_id, CACHE_TENANT)


class TokenCache(Cache):
    def clear(self):
        self.cache.cache_clear(CACHE_TOKEN)

    def set_token(self, tenant_id, token):

        if self.cache.cache_exists(tenant_id, CACHE_TOKEN):
            self.cache.cache_update(
                tenant_id, jsonutils.dumps(token.format()),
                DEFAULT_EXPIRES, CACHE_TOKEN)
        else:
            self.cache.cache_set(
                tenant_id, jsonutils.dumps(token.format()),
                DEFAULT_EXPIRES, CACHE_TOKEN)

    def get_token(self, tenant_id):
        if self.cache.cache_exists(tenant_id, CACHE_TOKEN):
            token_dict = jsonutils.loads(
                self.cache.cache_get(tenant_id, CACHE_TOKEN))
            token = load_token_from_dict(token_dict)
            return token
        return None

    def delete_token(self, tenant_id):
        if self.cache.cache_exists(tenant_id, CACHE_TOKEN):
            self.cache.cache_del(tenant_id, CACHE_TOKEN)

########NEW FILE########
__FILENAME__ = base
import abc


class DataHandlerError(Exception):
    """
    base class to be used for data handler errors
    """
    def __init__(self, msg):
        self.msg = msg
        super(DataHandlerError, self).__init__(self.msg)


class DataHandlerBase:
    """
    Abstract Base Class for implementing data drivers
    """
    __metaclass__ = abc.ABCMeta

    STATUS_NEW = 'NEW'
    STATUS_CONNECTED = 'CONNECTED'
    STATUS_CLOSED = 'CLOSED'

    def status(self):
        return self.status

    @abc.abstractmethod
    def connect(self):
        raise NotImplementedError

    @abc.abstractmethod
    def close(self):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = driver
from elasticsearch import Elasticsearch, ElasticsearchException
from oslo.config import cfg
from meniscus.data.handlers import base
from meniscus import config
from meniscus import env


_LOG = env.get_logger(__name__)


#Register options for Elasticsearch
elasticsearch_group = cfg.OptGroup(
    name="elasticsearch",
    title='Elasticsearch Configuration Options')

config.get_config().register_group(elasticsearch_group)

elasticsearch_options = [
    cfg.ListOpt('servers',
                default=['localhost:9200'],
                help="""hostname:port for db servers
                    """
                ),
    cfg.IntOpt('bulk_size',
               default=100,
               help="""Amount of records to transmit in bulk
                    """
               ),
    cfg.StrOpt('ttl',
               default="30d",
               help="""default time to live for documents
                    inserted into the default store
                    """
               )
]

config.get_config().register_opts(
    elasticsearch_options, group=elasticsearch_group)

try:
    config.init_config()
except config.cfg.ConfigFilesNotFoundError as ex:
    _LOG.exception(ex.message)


class ElasticsearchHandlerError(base.DataHandlerError):
    pass


class ElasticsearchHandler(base.DataHandlerBase):

    def __init__(self, conf):
        """
        Initialize a data handler for elasticsearch
        from settings in the meniscus config.
        es_servers: a list[] of {"host": "hostname", "port": "port"} for
        elasticsearch servers
        bulk_size: hom may records are held before performing a bulk flush
        ttl: the default length of time a document should live when indexed
        status: the status of the current es connection
        """
        self.es_servers = [{
            "host": server.split(":")[0],
            "port": server.split(":")[1]
            } for server in conf.servers
        ]

        if conf.bulk_size < 1:
            raise ElasticsearchHandlerError(
                "bulk size must be at least 1, bulk size given is {0}".format(
                    conf.bulk_size)
            )
        self.bulk_size = conf.bulk_size

        self.ttl = conf.ttl
        self.status = ElasticsearchHandler.STATUS_NEW

    def _check_connection(self):
        """
        Check that a pyES connection has been created,
        if not, raise an exception
        """
        if self.status != ElasticsearchHandler.STATUS_CONNECTED:
            raise ElasticsearchHandlerError('Database not connected.')

    def connect(self):
        """
        Create a connection to elasticsearch.
        """
        self.connection = Elasticsearch(hosts=self.es_servers)
        self.status = ElasticsearchHandler.STATUS_CONNECTED

    def close(self):
        """
        Close the connection to elasticsearch
        """
        self.connection = None
        self.status = ElasticsearchHandler.STATUS_CLOSED

    def create_index(self, index, mapping=None):
        """
        Creates a new index on the elasticsearch cluster.
        :param index: the name of the index to create
        :param mapping: a mapping to apply to the index
        """
        self._check_connection()
        self.connection.indices.create(index=index, body=mapping)

    def put_mapping(self, index, doc_type, mapping):
        """
        Create a mapping for a doc_type on a specified index
        """
        self._check_connection()
        self.connection.indices.put_mapping(
            index=index, doc_type=doc_type, body=mapping)


def get_handler():
    """
    factory method that returns an instance of ElasticsearchHandler
    """
    conf = config.get_config()
    es_handler = ElasticsearchHandler(conf.elasticsearch)
    es_handler.connect()
    return es_handler

########NEW FILE########
__FILENAME__ = mapping_tasks
"""
The mapping_tasks module is used for configuring elasticsearch indexes and
doc_types with field mappings using async tasks that retry on failure
"""

from meniscus.data.handlers import elasticsearch
from meniscus import env
from meniscus.queue import celery


_LOG = env.get_logger(__name__)

_es_handler = elasticsearch.get_handler()


@celery.task(acks_late=True, max_retries=None, ignore_result=True)
def create_index(tenant_id):
    """
    A celery task to create a new index in elasticsearch, and then create
    a default field mapping.  The task will retry any failed attempts to
    create the index
    """
    try:
        _es_handler.create_index(index=tenant_id, mapping=DEFAULT_MAPPING)
    except Exception as ex:
        _LOG.exception(ex.message)
        create_index.retry()


@celery.task(acks_late=True, max_retries=None, ignore_result=True)
def create_ttl_mapping(tenant_id, producer_pattern):
    """
    A celery task to create a new mapping on a specified index/doc_type
    that enables time to live.  The task will retry until successful.
    """
    try:
        _es_handler.put_mapping(
            index=tenant_id, doc_type=producer_pattern, mapping=TTL_MAPPING)
    except Exception as ex:
        _LOG.exception(ex.message)
        create_ttl_mapping.retry()


#the default ttl time for an index if one is not specified in the document
DEFAULT_TTL = 7776000000

#es mapping for enabling TTL
TTL_MAPPING = {
    "_ttl": {
        "enabled": True,
        "default": DEFAULT_TTL
    }
}

#default es mapping for log messages
DEFAULT_MAPPING = {
    "mappings": {
        "default": {
            "_ttl": {
                "enabled": True,
                "default": DEFAULT_TTL
            },
            "properties": {
                "host": {
                    "type": "string"
                },
                "meniscus": {
                    "properties": {
                        "correlation": {
                            "properties": {
                                "@timestamp": {
                                    "type": "date",
                                    "format": "dateOptionalTime"
                                },
                                "destinations": {
                                    "properties": {
                                        "elasticsearch": {
                                            "type": "object"
                                        }
                                    }
                                },
                                "durable": {
                                    "type": "boolean"
                                },
                                "encrypted": {
                                    "type": "boolean"
                                },
                                "pattern": {
                                    "type": "string"
                                },
                                "sinks": {
                                    "type": "string"
                                },
                                "tenant_name": {
                                    "type": "string"
                                }
                            }
                        },
                        "tenant": {
                            "type": "string"
                        }
                    }
                },
                "msg": {
                    "type": "string"
                },
                "msgid": {
                    "type": "string"
                },
                "pid": {
                    "type": "string"
                },
                "pname": {
                    "type": "string"
                },
                "pri": {
                    "type": "string"
                },
                "time": {
                    "type": "date",
                    "format": "dateOptionalTime"
                },
                "ver": {
                    "type": "string"
                }
            }
        }
    }
}

########NEW FILE########
__FILENAME__ = driver
from pymongo import MongoClient, errors
from oslo.config import cfg
from meniscus.data.handlers import base
from meniscus import config
from meniscus import env


_LOG = env.get_logger(__name__)

#Register options for MongoDB
mongodb_group = cfg.OptGroup(
    name="mongodb", title='MongoDB Configuration Options')
config.get_config().register_group(mongodb_group)

mongodb_options = [
    cfg.ListOpt('servers',
                default=['localhost:27017'],
                help="""hostname:port for db servers
                    """
                ),
    cfg.StrOpt('database',
               default='test',
               help="""database name
                    """
               ),
    cfg.StrOpt('username',
               default='test',
               help="""db username
                    """
               ),
    cfg.StrOpt('password',
               default='test',
               help="""db password
                    """
               )
]

config.get_config().register_opts(
    mongodb_options, group=mongodb_group)

try:
    config.init_config()
except config.cfg.ConfigFilesNotFoundError as ex:
    _LOG.exception(ex.message)


class MongoDBHandlerError(base.DataHandlerError):
    pass


class MongoDBHandler(base.DataHandlerBase):

    def __init__(self, conf):
        self.mongo_servers = conf.servers
        self.database_name = conf.database
        self.username = conf.username
        self.password = conf.password
        self.connection = None
        self.status = MongoDBHandler.STATUS_NEW

    def _check_connection(self):
        """
        Check that a pyMongo connection has been created,
        if not, raise an exception
        """
        if self.status != self.STATUS_CONNECTED:
            raise MongoDBHandlerError('Database not connected.')

    def connect(self):
        """
        Create a connection to mongodb
        """
        try:
            self.connection = MongoClient(self.mongo_servers, slave_okay=True)
            self.database = self.connection[self.database_name]

            if self.username and self.password:
                self.database.authenticate(self.username, self.password)

            self.status = MongoDBHandler.STATUS_CONNECTED
        except errors.PyMongoError as ex:
            _LOG.exception(ex)
            raise MongoDBHandlerError("failure connecting")

    def close(self):
        """
        Close the connection to mongodb
        """
        self.connection.close()
        self.status = MongoDBHandler.STATUS_CLOSED

    def create_sequence(self, sequence_name):
        self._check_connection()
        sequence = self.find_one('counters', {'name': sequence_name})

        if not sequence:
            self.put('counters', {'name': sequence_name, 'seq': 1})

    def delete_sequence(self, sequence_name):
        self._check_connection()
        self.delete('counters', {'name': sequence_name})

    def next_sequence_value(self, sequence_name):
        self._check_connection()
        return self.database['counters'].find_and_modify(
            {'name': sequence_name}, {'$inc': {'seq': 1}})['seq']

    def find(self, object_name, query_filter=None, projection=None):
        if query_filter is None:
            query_filter = dict()

        self._check_connection()
        return self.database[object_name].find(query_filter, projection)

    def find_one(self, object_name, query_filter=None):
        if query_filter is None:
            query_filter = dict()
        self._check_connection()
        return self.database[object_name].find_one(query_filter)

    def put(self, object_name, document=None):
        if document is None:
            document = dict()
        self._check_connection()
        self.database[object_name].insert(document)

    def update(self, object_name, document=None):
        if document is None or '_id' not in document:
            raise MongoDBHandlerError(
                'The document must have a field "_id" in its root in '
                'order to perform an update operation.')

        self._check_connection()
        self.database[object_name].save(document)

    def set_field(self, object_name, update_fields, query_filter=None):
        '''
        Updates the given field with a new value for all documents that match
        the query filter

        :param object_name: represents the mongo collection
        :param update_fields: dict of fields to update and their new values
        :param query_filter: represents field/value to query by

        '''
        if query_filter is None:
            query_filter = dict()
        self._check_connection()

        set_statement = {"$set": update_fields}

        self.database[object_name].update(
            query_filter, set_statement, multi=True)

    def remove_field(self, object_name, update_fields, query_filter=None):
        '''
        Updates the given field with a new value for all documents that match
        the query filter

        :param object_name: represents the mongo collection
        :param update_fields: dict of fields to remove from the collection
        :param value: the new value for the field
        :param query_filter: represents field/value to query by

        '''
        if query_filter is None:
            query_filter = dict()
        self._check_connection()

        set_statement = {"$unset": update_fields}

        self.database[object_name].update(
            query_filter, set_statement, multi=True)

    def delete(self, object_name, query_filter=None, limit_one=False):
        if query_filter is None:
            query_filter = dict()
        self.database[object_name].remove(query_filter, True)


def get_handler():
    """
    factory method that returns an instance of MongoDBHandler
    """
    conf = config.get_config()
    mongo_handler = MongoDBHandler(conf.mongodb)
    try:
        mongo_handler.connect()
    except MongoDBHandlerError as ex:
        _LOG.exception(ex)
    return mongo_handler

########NEW FILE########
__FILENAME__ = tenant
from uuid import uuid4
from meniscus.openstack.common.timeutils import isotime
from meniscus.sinks import DEFAULT_SINK


class EventProducer(object):
    """
    An event producer is a nicer way of describing a parsing template
    for a producer of events. Event producer definitions should be
    reusable and not specific to any one host. While this may not
    always be the case, it should be considered for each event producer
    described.
    """

    def __init__(self, _id, name, pattern, durable=False,
                 encrypted=False, sinks=None):

        if not sinks:
            self.sinks = [DEFAULT_SINK]
        else:
            self.sinks = sinks

        self._id = _id
        self.name = name
        self.pattern = pattern
        self.durable = durable
        self.encrypted = encrypted

    def get_id(self):
        return self._id

    def format(self):
        return {'id': self._id, 'name': self.name, 'pattern': self.pattern,
                'durable': self.durable, 'encrypted': self.encrypted,
                'sinks': self.sinks}


class Token(object):
    """
    Token is an object used to authenticate messages from a tenant.
    """

    def __init__(self, valid=None, previous=None, last_changed=None):
        if not valid:
            valid = str(uuid4())
        if not last_changed:
            last_changed = isotime(subsecond=True)

        self.valid = valid
        self.previous = previous
        self.last_changed = last_changed

    def reset_token(self):
        """
        Resets a token by creating a new valid token,
        and saves the current token as previous.
        """
        self.previous = self.valid
        self.valid = str(uuid4())
        self.last_changed = isotime(subsecond=True)

    def reset_token_now(self):
        """
        Completely resets token values leaving no previous token.
        """
        self.__init__()

    def validate_token(self, message_token):
        """
        Validates a token as True if the message_token matches
        the current valid token or the previous token.
        """
        if not message_token:
            return False

        if message_token == self.valid or message_token == self.previous:
            return True

        return False

    def format(self):
        return {'valid': self.valid,
                'previous': self.previous,
                'last_changed': self.last_changed,
                }


class Tenant(object):
    """
    Tenants are users of the environments being monitored for
    application events.
    """

    def __init__(self, tenant_id, token, event_producers=None,
                 _id=None, tenant_name=None):

        if event_producers is None:
            event_producers = list()

        if tenant_name is None:
            tenant_name = tenant_id

        self._id = _id
        self.tenant_id = str(tenant_id)
        self.token = token
        self.event_producers = event_producers
        self.tenant_name = tenant_name

    def get_id(self):
        return self._id

    def format(self):
        return {'tenant_id': self.tenant_id,
                'tenant_name': self.tenant_name,
                'event_producers':
                [p.format() for p in self.event_producers],
                'token': self.token.format()}

    def format_for_save(self):
        tenant_dict = self.format()
        tenant_dict['_id'] = self._id
        return tenant_dict


def load_tenant_from_dict(tenant_dict):
    """
    Create a Tenant Object from a dictionary
    """
    #Create a list of EventProducer objects from the dictionary
    event_producers = [
        EventProducer(
            e['id'], e['name'], e['pattern'],
            e['durable'], e['encrypted'], e['sinks']
        )
        for e in tenant_dict['event_producers']
    ]

    token = load_token_from_dict(tenant_dict['token'])

    _id = None
    if "_id" in tenant_dict.keys():
        _id = tenant_dict['_id']

    #Return the tenant object
    return Tenant(
        tenant_dict['tenant_id'], token,
        event_producers=event_producers,
        _id=_id, tenant_name=tenant_dict['tenant_name'])


def load_token_from_dict(token_dict):
    """
    Create a Token object from a dictionary
    """
    return Token(
        token_dict['valid'],
        token_dict['previous'],
        token_dict['last_changed'])

########NEW FILE########
__FILENAME__ = tenant_util
"""
The tenant_util module provides an abstraction of database operations used
with instances of the Tenant class and its member objects
"""

from meniscus.data.handlers import mongodb
from meniscus.data.handlers.elasticsearch import mapping_tasks
from meniscus.data.model.tenant import EventProducer
from meniscus.data.model.tenant import (
    load_tenant_from_dict, Tenant, Token)

_db_handler = mongodb.get_handler()


def find_tenant(tenant_id, create_on_missing=False):
    """
    Retrieves a dictionary describing a tenant object and its EventProducers
    and maps them to a tenant object.  If the "create_on_missing" param is set
    a new tenant will be created of the specified tenant is not found in the
    datastore
    """
    # get the tenant dictionary from the data source
    tenant = retrieve_tenant(tenant_id)

    if tenant is None:
    #if the create_on_missing parameter us set, create the new tenant,
    # then retrieve it from the data store and return
        if create_on_missing:
            create_tenant(tenant_id)
            tenant = retrieve_tenant(tenant_id)

    return tenant


def create_tenant(tenant_id, tenant_name=None):
    """
    Creates a new tenant and and persists to the datastore
    """
    #create new token for the tenant
    new_token = Token()
    new_tenant = Tenant(tenant_id, new_token, tenant_name=tenant_name)

    #save the new tenant to the datastore
    _db_handler.put('tenant', new_tenant.format())
    #create a new sequence for the tenant for creation of IDs on child objects
    _db_handler.create_sequence(new_tenant.tenant_id)

    #create an index for the tenant in the default sink
    # and enables time to live for the default doc_type
    mapping_tasks.create_index.delay(tenant_id)


def retrieve_tenant(tenant_id):
    """
    Retrieve the specified tenant form the datastore
    """
    tenant_dict = _db_handler.find_one('tenant', {'tenant_id': tenant_id})
    #return the tenant object
    if tenant_dict:
        return load_tenant_from_dict(tenant_dict)

    return None


def save_tenant(tenant):
    """
    Update an existing tenant in the datastore
    """
    _db_handler.update('tenant', tenant.format_for_save())


def create_event_producer(tenant, name, pattern, durable, encrypted, sinks):
    """
    Creates an Event Producer object, assigns it to a tenant, and updates the
    tenant in the datastore.
    """
    new_event_producer = EventProducer(
        _db_handler.next_sequence_value(tenant.tenant_id),
        name,
        pattern,
        durable,
        encrypted,
        sinks)
    #add the event_producer to the tenant
    tenant.event_producers.append(new_event_producer)
    #save the tenant's data
    save_tenant(tenant)

    #create a new mapping for the producer in the default
    # sink to enable time_to_live
    mapping_tasks.create_ttl_mapping.delay(
        tenant_id=tenant.tenant_id,
        producer_pattern=new_event_producer.pattern)

    #return the id of the newly created producer
    return new_event_producer.get_id()


def delete_event_producer(tenant, event_producer):
    """
    Removes a specified Event producer from the tenant object, and updates
    the tenant in the datastore
    """
    #remove any references to the event producer being deleted
    tenant.event_producers.remove(event_producer)
    #save the tenant document
    save_tenant(tenant)


def find_event_producer(tenant, producer_id=None, producer_name=None):
    """
    searches the given tenant for a producer matching either the id or name
    """
    if producer_id:
        producer_id = int(producer_id)
        for producer in tenant.event_producers:
            if producer_id == producer.get_id():
                return producer

    if producer_name:
        for producer in tenant.event_producers:
            if producer_name == producer.name:
                return producer

    return None

########NEW FILE########
__FILENAME__ = worker
"""
This Module contains classes that define different data structures used to
represent meniscus worker nodes and their registration, configuration, and
system status.
"""

import platform

import meniscus.api.utils.sys_assist as sys_assist
from meniscus.openstack.common import timeutils


class Worker(object):
    """
    Class that represents the data structure of worker node in a meniscus
    cluster.  The data contains basic identification and system info.
    """
    def __init__(self, personality='worker', **kwargs):
        """
        The init function accepts **kwargs so that a Worker object can be
        constructed from its dictionary representation or from a
        WorkerRegistration object's dictionary representation.
        """

        if kwargs:
            self._id = kwargs.get('_id')
            self.hostname = kwargs['hostname']
            self.ip_address_v4 = kwargs['ip_address_v4']
            self.ip_address_v6 = kwargs['ip_address_v6']
            self.personality = personality
            self.status = kwargs['status']
            self.system_info = SystemInfo(**kwargs['system_info'])
        else:
            self.hostname = platform.node()
            self.ip_address_v4 = sys_assist.get_interface_ip()
            self.ip_address_v6 = ""
            self.personality = personality
            self.status = "online"
            self.system_info = SystemInfo()

    def format(self):
        """
        Format an instance of the Worker object as a dictionary
        """
        return{
            'hostname': self.hostname,
            'ip_address_v4': self.ip_address_v4,
            'ip_address_v6': self.ip_address_v6,
            'personality': self.personality,
            'status': self.status,
            'system_info': self.system_info.format()
        }

    def format_for_save(self):
        """
        Format an instance of the Worker object with its internal _id
        for persistence in the datastore
        """
        worker_dict = self.format()
        worker_dict['_id'] = self._id
        return worker_dict

    def get_status(self):
        """
        Return a dictionary defining a worker node's system status
        """
        return{
            'hostname': self.hostname,
            'ip_address_v4': self.ip_address_v4,
            'ip_address_v6': self.ip_address_v6,
            'personality': self.personality,
            'status': self.status,
            'system_info': self.system_info.format()
        }


class SystemInfo(object):
    """
    A class defining the data structure for system stats for a worker node.
    """
    def __init__(self, **kwargs):
        """
        An object can be initialized by passing in a dictionary representation
        of the data as **kwargs.  Otherwise the constructor will retrieve
        system stats from the machine it is executing on.
        """
        if kwargs:
            self.cpu_cores = kwargs['cpu_cores']
            self.os_type = kwargs['os_type']
            self.memory_mb = kwargs['memory_mb']
            self.architecture = kwargs['architecture']
            self.load_average = kwargs['load_average']
            self.disk_usage = kwargs['disk_usage']
            self.timestamp = kwargs['timestamp']
        else:
            self.cpu_cores = sys_assist.get_cpu_core_count()
            self.os_type = platform.platform()
            self.memory_mb = sys_assist.get_sys_mem_total_MB()
            self.architecture = platform.machine()
            self.load_average = sys_assist.get_load_average()
            self.disk_usage = sys_assist.get_disk_usage()
            self.timestamp = str(timeutils.utcnow())

    def format(self):
        """
        Formats an instance of a SystemInfo object as a dictionary
        """
        return {
            'cpu_cores': self.cpu_cores,
            'os_type': self.os_type,
            'memory_mb': self.memory_mb,
            'architecture': self.architecture,
            'load_average': self.load_average,
            'disk_usage': self.disk_usage,
            'timestamp': self.timestamp
        }


class WorkerConfiguration(object):
    """
    The class defines a data structure for a worker's configuration info.
    """
    def __init__(self, personality, hostname, coordinator_uri):

        self.personality = personality
        self.hostname = hostname
        self.coordinator_uri = coordinator_uri

    def format(self):
        """
        Formats an instance fo a WorkerConfiguration object as a dictionary.
        """
        return{
            'personality': self.personality,
            'hostname': self.hostname,
            'coordinator_uri': self.coordinator_uri
        }

########NEW FILE########
__FILENAME__ = worker_util
"""
The worker_util module provides an abstraction of database operations used
with instances fo the Worker class
"""

from meniscus.data.handlers import mongodb
from meniscus.data.model.worker import Worker

_db_handler = mongodb.get_handler()


def create_worker(worker):
    """
    add new worker to db
    """
    _db_handler.put('worker', worker.format())


def find_worker(hostname):
    """
    returns worker object based on hostname
    """
    worker_dict = _db_handler.find_one('worker', {'hostname': hostname})
    if worker_dict:
        return Worker(**worker_dict)
    return None


def save_worker(worker):
    """
    Updates an existing worker document
    """
    _db_handler.update('worker', worker.format_for_save())


def retrieve_all_workers():
    """
    Retrieve all worker documents from the db and
    return a list of Worker objects
    """
    return [
        Worker(**worker_dict) for worker_dict in _db_handler.find('worker')
    ]

########NEW FILE########
__FILENAME__ = env
from os import environ
from oslo.config import cfg
from meniscus.openstack.common import log
from meniscus.config import _DEFAULT_CONFIG_ARGS


CONF = cfg.CONF
CONF.import_opt('verbose', 'meniscus.openstack.common.log')
CONF.import_opt('debug', 'meniscus.openstack.common.log')
CONF.import_opt('log_file', 'meniscus.openstack.common.log')
CONF.import_opt('log_dir', 'meniscus.openstack.common.log')
CONF.import_opt('use_syslog', 'meniscus.openstack.common.log')
CONF.import_opt('syslog_log_facility', 'meniscus.openstack.common.log')
CONF.import_opt('log_config', 'meniscus.openstack.common.log')

try:
    cfg.CONF(args=_DEFAULT_CONFIG_ARGS)
except cfg.ConfigFilesNotFoundError as ex:
    pass


def get_logger(logger_name):
    return log.getLogger(logger_name)


def get(name, default=None):
    value = environ.get(name)
    return value if value else default

########NEW FILE########
__FILENAME__ = plugin
"""
This is a simple plugin layer that uses the sys.meta_path list along
with custom finder and loader definitions to hook into the Python
import process. For more information, please see:
http://www.python.org/dev/peps/pep-0302/
"""
import imp
import sys
import os.path
import importlib


# Constants; because they make the code look nice.
_MODULE_PATH_SEP = '.'
_NAME = '__name__'
_PATH = '__path__'


class PluginError(ImportError):

    def __init__(self, msg):
        self.msg = msg


class PluginFinder(object):

    def __init__(self, paths=None):
        if paths is None:
            paths = list()
        self.plugin_paths = paths

    def add_path(self, new_path):
        if new_path not in self.plugin_paths:
            self.plugin_paths.append(new_path)

    def find_module(self, fullname, path=None):
        pathname = os.path.join(*fullname.split(_MODULE_PATH_SEP))

        for path in self.plugin_paths:
            target = os.path.join(path, pathname)
            is_pkg = False

            # If the target references a directory, try to load it as
            # a module by referencing the __init__.py file, otherwise
            # append .py and attempt to resolve it.
            if os.path.isdir(target):
                target = os.path.join(target, '__init__.py')
                is_pkg = True
            else:
                target += '.py'

            if os.path.exists(target):
                return SecureLoader(fullname, target, is_pkg)

        return None


class SecureLoader(object):

    def __init__(self, module_name, target, is_pkg):
        self.module_name = module_name
        self.load_target = target
        self.is_pkg = is_pkg

    def _read_code(self):
        fin = open(self.load_target, 'r')
        code = fin.read()
        fin.close()
        return code

    def load_module(self, fullname):
        if fullname != self.module_name:
            raise PluginError('Requesting a module that the loader is '
                              'unaware of.')

        if fullname in sys.modules:
            return sys.modules[fullname]

        code = self._read_code()
        module = imp.new_module(fullname)
        module.__file__ = self.load_target
        module.__loader__ = self

        if self.is_pkg:
            module.__path__ = []
            module.__package__ = fullname
        else:
            module.__package__ = fullname.rpartition('.')[0]

        exec(code, module.__dict__)
        sys.modules[fullname] = module
        return module


# Plugin finder singleton
_PLUGIN_FINDER = PluginFinder()


def _inject():
    """
    Injects a custom finder object into the sys.meta_path list in order to
    allow for the loading of additional modules that may not be in the path
    given to the interpreter at boot.
    """
    if _PLUGIN_FINDER not in sys.meta_path:
        sys.meta_path.append(_PLUGIN_FINDER)


def import_module(module_name):
    """
    This function ensures that the directory hooks have been placed in the
    sys.meta_path list before passing the module name being required to
    the importlib call of the same name.
    """
    _inject()
    return importlib.import_module(module_name)


def plug_into(*args):
    """
    Adds all arguments passed as plugin directories to search when loading
    modules.
    """
    for path in args:
        _PLUGIN_FINDER.add_path(path)

########NEW FILE########
__FILENAME__ = lognorm
import os

from meniscus import config
from meniscus import env

from pylognorm import LogNormalizer
from oslo.config import cfg


_LOG = env.get_logger(__name__)

# Normalization configuration options
_NORMALIZATION_GROUP = cfg.OptGroup(
    name='liblognorm', title='Liblognorm options')
config.get_config().register_group(_NORMALIZATION_GROUP)

_NORMALIZATION = [
    cfg.StrOpt('rules_dir',
               default=None,
               help="""directory to load rules from"""
               )
]

config.get_config().register_opts(
    _NORMALIZATION, group=_NORMALIZATION_GROUP)

try:
    config.init_config()
except config.cfg.ConfigFilesNotFoundError as ex:
    _LOG.exception(ex.message)


def get_normalizer(conf=config.get_config()):
    """This returns both a normalizer as well as a list of loaded rules"""
    normalization_conf = conf.liblognorm
    normalizer = LogNormalizer()
    loaded_rules = list()
    if normalization_conf.rules_dir:
        loaded_rules = load_rules(normalizer, normalization_conf.rules_dir)
    return normalizer, loaded_rules


def load_rules(normalizer, path):
    loaded = list()
    if not os.path.isdir(path):
        raise IOError(
            'Unable to load rules. {} is not a directory'.format(path))
    for possible_rule in os.listdir(path):
        if possible_rule.endswith('.db'):
            normalizer.load_rules(os.path.join(path, possible_rule))
            loaded.append(possible_rule.rstrip('.db'))
    return loaded

########NEW FILE########
__FILENAME__ = normalizer
from meniscus import env
from meniscus.queue import celery
from meniscus.normalization.lognorm import get_normalizer
from meniscus import sinks
import json


_LOG = env.get_logger(__name__)
_normalizer, loaded_normalizer_rules = get_normalizer()


def should_normalize(message):
    """Returns true only if the pattern is in the loaded rules
    list and there is a string msg in the message dictionary"""
    should_normalize = (
        message['meniscus']['correlation']['pattern'] in
        loaded_normalizer_rules)
    can_normalize = ('msg' in message)
    return should_normalize and can_normalize


@celery.task(acks_late=True, max_retries=None, serializer="json")
def normalize_message(message):
    """
    This code takes a message and normalizes it into a dictionary. This
    normalized dictionary is assigned to a field matching the pattern name
    of the normalization. This dictionary is then assigned to the message
    under the normalized field.
    """
    pattern = message['meniscus']['correlation']['pattern']
    normalized_doc = json.loads(
        _normalizer.normalize(message['msg']).as_json())
    message['normalized'] = {
        pattern: normalized_doc
    }
    sinks.route_message(message)

########NEW FILE########
__FILENAME__ = excutils
# Copyright 2011 OpenStack Foundation.
# Copyright 2012, Red Hat, Inc.
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
Exception related utilities.
"""

import logging
import sys
import time
import traceback

import six

from meniscus.openstack.common.gettextutils import _  # noqa


class save_and_reraise_exception(object):
    """Save current exception, run some code and then re-raise.

    In some cases the exception context can be cleared, resulting in None
    being attempted to be re-raised after an exception handler is run. This
    can happen when eventlet switches greenthreads or when running an
    exception handler, code raises and catches an exception. In both
    cases the exception context will be cleared.

    To work around this, we save the exception state, run handler code, and
    then re-raise the original exception. If another exception occurs, the
    saved exception is logged and the new exception is re-raised.

    In some cases the caller may not want to re-raise the exception, and
    for those circumstances this context provides a reraise flag that
    can be used to suppress the exception.  For example:

    except Exception:
        with save_and_reraise_exception() as ctxt:
            decide_if_need_reraise()
            if not should_be_reraised:
                ctxt.reraise = False
    """
    def __init__(self):
        self.reraise = True

    def __enter__(self):
        self.type_, self.value, self.tb, = sys.exc_info()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logging.error(_('Original exception being dropped: %s'),
                          traceback.format_exception(self.type_,
                                                     self.value,
                                                     self.tb))
            return False
        if self.reraise:
            six.reraise(self.type_, self.value, self.tb)


def forever_retry_uncaught_exceptions(infunc):
    def inner_func(*args, **kwargs):
        last_log_time = 0
        last_exc_message = None
        exc_count = 0
        while True:
            try:
                return infunc(*args, **kwargs)
            except Exception as exc:
                this_exc_message = six.u(str(exc))
                if this_exc_message == last_exc_message:
                    exc_count += 1
                else:
                    exc_count = 1
                # Do not log any more frequently than once a minute unless
                # the exception message changes
                cur_time = int(time.time())
                if (cur_time - last_log_time > 60 or
                        this_exc_message != last_exc_message):
                    logging.exception(
                        _('Unexpected exception occurred %d time(s)... '
                          'retrying.') % exc_count)
                    last_log_time = cur_time
                    last_exc_message = this_exc_message
                    exc_count = 0
                # This should be a very rare event. In case it isn't, do
                # a sleep.
                time.sleep(1)
    return inner_func

########NEW FILE########
__FILENAME__ = fileutils
# Copyright 2011 OpenStack Foundation.
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


import contextlib
import errno
import os

from meniscus.openstack.common import excutils
from meniscus.openstack.common.gettextutils import _
from meniscus.openstack.common import log as logging

LOG = logging.getLogger(__name__)

_FILE_CACHE = {}


def ensure_tree(path):
    """Create a directory (and any ancestor directories required)

    :param path: Directory to create
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            if not os.path.isdir(path):
                raise
        else:
            raise


def read_cached_file(filename, force_reload=False):
    """Read from a file if it has been modified.

    :param force_reload: Whether to reload the file.
    :returns: A tuple with a boolean specifying if the data is fresh
              or not.
    """
    global _FILE_CACHE

    if force_reload and filename in _FILE_CACHE:
        del _FILE_CACHE[filename]

    reloaded = False
    mtime = os.path.getmtime(filename)
    cache_info = _FILE_CACHE.setdefault(filename, {})

    if not cache_info or mtime > cache_info.get('mtime', 0):
        LOG.debug(_("Reloading cached file %s") % filename)
        with open(filename) as fap:
            cache_info['data'] = fap.read()
        cache_info['mtime'] = mtime
        reloaded = True
    return (reloaded, cache_info['data'])


def delete_if_exists(path, remove=os.unlink):
    """Delete a file, but ignore file not found error.

    :param path: File to delete
    :param remove: Optional function to remove passed path
    """

    try:
        remove(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


@contextlib.contextmanager
def remove_path_on_error(path, remove=delete_if_exists):
    """Protect code that wants to operate on PATH atomically.
    Any exception will cause PATH to be removed.

    :param path: File to work with
    :param remove: Optional function to remove passed path
    """

    try:
        yield
    except Exception:
        with excutils.save_and_reraise_exception():
            remove(path)


def file_open(*args, **kwargs):
    """Open file

    see built-in file() documentation for more details

    Note: The reason this is kept in a separate module is to easily
    be able to provide a stub module that doesn't alter system
    state at all (for unit tests)
    """
    return file(*args, **kwargs)

########NEW FILE########
__FILENAME__ = gettextutils
# Copyright 2012 Red Hat, Inc.
# Copyright 2013 IBM Corp.
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
gettext for openstack-common modules.

Usual usage in an openstack.common module:

    from meniscus.openstack.common.gettextutils import _
"""

import copy
import gettext
import logging
import os
import re
try:
    import UserString as _userString
except ImportError:
    import collections as _userString

from babel import localedata
import six

_localedir = os.environ.get('meniscus'.upper() + '_LOCALEDIR')
_t = gettext.translation('meniscus', localedir=_localedir, fallback=True)

_AVAILABLE_LANGUAGES = {}
USE_LAZY = False


def enable_lazy():
    """Convenience function for configuring _() to use lazy gettext

    Call this at the start of execution to enable the gettextutils._
    function to use lazy gettext functionality. This is useful if
    your project is importing _ directly instead of using the
    gettextutils.install() way of importing the _ function.
    """
    global USE_LAZY
    USE_LAZY = True


def _(msg):
    if USE_LAZY:
        return Message(msg, 'meniscus')
    else:
        if six.PY3:
            return _t.gettext(msg)
        return _t.ugettext(msg)


def install(domain, lazy=False):
    """Install a _() function using the given translation domain.

    Given a translation domain, install a _() function using gettext's
    install() function.

    The main difference from gettext.install() is that we allow
    overriding the default localedir (e.g. /usr/share/locale) using
    a translation-domain-specific environment variable (e.g.
    NOVA_LOCALEDIR).

    :param domain: the translation domain
    :param lazy: indicates whether or not to install the lazy _() function.
                 The lazy _() introduces a way to do deferred translation
                 of messages by installing a _ that builds Message objects,
                 instead of strings, which can then be lazily translated into
                 any available locale.
    """
    if lazy:
        # NOTE(mrodden): Lazy gettext functionality.
        #
        # The following introduces a deferred way to do translations on
        # messages in OpenStack. We override the standard _() function
        # and % (format string) operation to build Message objects that can
        # later be translated when we have more information.
        #
        # Also included below is an example LocaleHandler that translates
        # Messages to an associated locale, effectively allowing many logs,
        # each with their own locale.

        def _lazy_gettext(msg):
            """Create and return a Message object.

            Lazy gettext function for a given domain, it is a factory method
            for a project/module to get a lazy gettext function for its own
            translation domain (i.e. nova, glance, cinder, etc.)

            Message encapsulates a string so that we can translate
            it later when needed.
            """
            return Message(msg, domain)

        from six import moves
        moves.builtins.__dict__['_'] = _lazy_gettext
    else:
        localedir = '%s_LOCALEDIR' % domain.upper()
        if six.PY3:
            gettext.install(domain,
                            localedir=os.environ.get(localedir))
        else:
            gettext.install(domain,
                            localedir=os.environ.get(localedir),
                            unicode=True)


class Message(_userString.UserString, object):
    """Class used to encapsulate translatable messages."""
    def __init__(self, msg, domain):
        # _msg is the gettext msgid and should never change
        self._msg = msg
        self._left_extra_msg = ''
        self._right_extra_msg = ''
        self._locale = None
        self.params = None
        self.domain = domain

    @property
    def data(self):
        # NOTE(mrodden): this should always resolve to a unicode string
        # that best represents the state of the message currently

        localedir = os.environ.get(self.domain.upper() + '_LOCALEDIR')
        if self.locale:
            lang = gettext.translation(self.domain,
                                       localedir=localedir,
                                       languages=[self.locale],
                                       fallback=True)
        else:
            # use system locale for translations
            lang = gettext.translation(self.domain,
                                       localedir=localedir,
                                       fallback=True)

        if six.PY3:
            ugettext = lang.gettext
        else:
            ugettext = lang.ugettext

        full_msg = (self._left_extra_msg +
                    ugettext(self._msg) +
                    self._right_extra_msg)

        if self.params is not None:
            full_msg = full_msg % self.params

        return six.text_type(full_msg)

    @property
    def locale(self):
        return self._locale

    @locale.setter
    def locale(self, value):
        self._locale = value
        if not self.params:
            return

        # This Message object may have been constructed with one or more
        # Message objects as substitution parameters, given as a single
        # Message, or a tuple or Map containing some, so when setting the
        # locale for this Message we need to set it for those Messages too.
        if isinstance(self.params, Message):
            self.params.locale = value
            return
        if isinstance(self.params, tuple):
            for param in self.params:
                if isinstance(param, Message):
                    param.locale = value
            return
        if isinstance(self.params, dict):
            for param in self.params.values():
                if isinstance(param, Message):
                    param.locale = value

    def _save_dictionary_parameter(self, dict_param):
        full_msg = self.data
        # look for %(blah) fields in string;
        # ignore %% and deal with the
        # case where % is first character on the line
        keys = re.findall('(?:[^%]|^)?%\((\w*)\)[a-z]', full_msg)

        # if we don't find any %(blah) blocks but have a %s
        if not keys and re.findall('(?:[^%]|^)%[a-z]', full_msg):
            # apparently the full dictionary is the parameter
            params = copy.deepcopy(dict_param)
        else:
            params = {}
            for key in keys:
                try:
                    params[key] = copy.deepcopy(dict_param[key])
                except TypeError:
                    # cast uncopyable thing to unicode string
                    params[key] = six.text_type(dict_param[key])

        return params

    def _save_parameters(self, other):
        # we check for None later to see if
        # we actually have parameters to inject,
        # so encapsulate if our parameter is actually None
        if other is None:
            self.params = (other, )
        elif isinstance(other, dict):
            self.params = self._save_dictionary_parameter(other)
        else:
            # fallback to casting to unicode,
            # this will handle the problematic python code-like
            # objects that cannot be deep-copied
            try:
                self.params = copy.deepcopy(other)
            except TypeError:
                self.params = six.text_type(other)

        return self

    # overrides to be more string-like
    def __unicode__(self):
        return self.data

    def __str__(self):
        if six.PY3:
            return self.__unicode__()
        return self.data.encode('utf-8')

    def __getstate__(self):
        to_copy = ['_msg', '_right_extra_msg', '_left_extra_msg',
                   'domain', 'params', '_locale']
        new_dict = self.__dict__.fromkeys(to_copy)
        for attr in to_copy:
            new_dict[attr] = copy.deepcopy(self.__dict__[attr])

        return new_dict

    def __setstate__(self, state):
        for (k, v) in state.items():
            setattr(self, k, v)

    # operator overloads
    def __add__(self, other):
        copied = copy.deepcopy(self)
        copied._right_extra_msg += other.__str__()
        return copied

    def __radd__(self, other):
        copied = copy.deepcopy(self)
        copied._left_extra_msg += other.__str__()
        return copied

    def __mod__(self, other):
        # do a format string to catch and raise
        # any possible KeyErrors from missing parameters
        self.data % other
        copied = copy.deepcopy(self)
        return copied._save_parameters(other)

    def __mul__(self, other):
        return self.data * other

    def __rmul__(self, other):
        return other * self.data

    def __getitem__(self, key):
        return self.data[key]

    def __getslice__(self, start, end):
        return self.data.__getslice__(start, end)

    def __getattribute__(self, name):
        # NOTE(mrodden): handle lossy operations that we can't deal with yet
        # These override the UserString implementation, since UserString
        # uses our __class__ attribute to try and build a new message
        # after running the inner data string through the operation.
        # At that point, we have lost the gettext message id and can just
        # safely resolve to a string instead.
        ops = ['capitalize', 'center', 'decode', 'encode',
               'expandtabs', 'ljust', 'lstrip', 'replace', 'rjust', 'rstrip',
               'strip', 'swapcase', 'title', 'translate', 'upper', 'zfill']
        if name in ops:
            return getattr(self.data, name)
        else:
            return _userString.UserString.__getattribute__(self, name)


def get_available_languages(domain):
    """Lists the available languages for the given translation domain.

    :param domain: the domain to get languages for
    """
    if domain in _AVAILABLE_LANGUAGES:
        return copy.copy(_AVAILABLE_LANGUAGES[domain])

    localedir = '%s_LOCALEDIR' % domain.upper()
    find = lambda x: gettext.find(domain,
                                  localedir=os.environ.get(localedir),
                                  languages=[x])

    # NOTE(mrodden): en_US should always be available (and first in case
    # order matters) since our in-line message strings are en_US
    language_list = ['en_US']
    # NOTE(luisg): Babel <1.0 used a function called list(), which was
    # renamed to locale_identifiers() in >=1.0, the requirements master list
    # requires >=0.9.6, uncapped, so defensively work with both. We can remove
    # this check when the master list updates to >=1.0, and all projects udpate
    list_identifiers = (getattr(localedata, 'list', None) or
                        getattr(localedata, 'locale_identifiers'))
    locale_identifiers = list_identifiers()
    for i in locale_identifiers:
        if find(i) is not None:
            language_list.append(i)
    _AVAILABLE_LANGUAGES[domain] = language_list
    return copy.copy(language_list)


def get_localized_message(message, user_locale):
    """Gets a localized version of the given message in the given locale."""
    if isinstance(message, Message):
        if user_locale:
            message.locale = user_locale
        return six.text_type(message)
    else:
        return message


class LocaleHandler(logging.Handler):
    """Handler that can have a locale associated to translate Messages.

    A quick example of how to utilize the Message class above.
    LocaleHandler takes a locale and a target logging.Handler object
    to forward LogRecord objects to after translating the internal Message.
    """

    def __init__(self, locale, target):
        """Initialize a LocaleHandler

        :param locale: locale to use for translating messages
        :param target: logging.Handler object to forward
                       LogRecord objects to after translation
        """
        logging.Handler.__init__(self)
        self.locale = locale
        self.target = target

    def emit(self, record):
        if isinstance(record.msg, Message):
            # set the locale and resolve to a string
            record.msg.locale = self.locale

        self.target.emit(record)

########NEW FILE########
__FILENAME__ = importutils
# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Import related utilities and helper functions.
"""

import sys
import traceback


def import_class(import_str):
    """Returns a class from a string including module and class."""
    mod_str, _sep, class_str = import_str.rpartition('.')
    try:
        __import__(mod_str)
        return getattr(sys.modules[mod_str], class_str)
    except (ValueError, AttributeError):
        raise ImportError('Class %s cannot be found (%s)' %
                          (class_str,
                           traceback.format_exception(*sys.exc_info())))


def import_object(import_str, *args, **kwargs):
    """Import a class and return an instance of it."""
    return import_class(import_str)(*args, **kwargs)


def import_object_ns(name_space, import_str, *args, **kwargs):
    """Tries to import object from default namespace.

Imports a class and return an instance of it, first by trying
to find the class in a default namespace, then failing back to
a full path if not found in the default namespace.
"""
    import_value = "%s.%s" % (name_space, import_str)
    try:
        return import_class(import_value)(*args, **kwargs)
    except ImportError:
        return import_class(import_str)(*args, **kwargs)


def import_module(import_str):
    """Import a module."""
    __import__(import_str)
    return sys.modules[import_str]


def try_import(import_str, default=None):
    """Try to import a module and if it fails return default."""
    try:
        return import_module(import_str)
    except ImportError:
        return default

########NEW FILE########
__FILENAME__ = jsonutils
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

'''
JSON related utilities.

This module provides a few things:

1) A handy function for getting an object down to something that can be
JSON serialized. See to_primitive().

2) Wrappers around loads() and dumps(). The dumps() wrapper will
automatically use to_primitive() for you if needed.

3) This sets up anyjson to use the loads() and dumps() wrappers if anyjson
is available.
'''


import datetime
import functools
import inspect
import itertools
import json
try:
    import xmlrpclib
except ImportError:
    # NOTE(jd): xmlrpclib is not shipped with Python 3
    xmlrpclib = None

import six

from meniscus.openstack.common import importutils
from meniscus.openstack.common import timeutils

netaddr = importutils.try_import("netaddr")

_nasty_type_tests = [inspect.ismodule, inspect.isclass, inspect.ismethod,
                     inspect.isfunction, inspect.isgeneratorfunction,
                     inspect.isgenerator, inspect.istraceback, inspect.isframe,
                     inspect.iscode, inspect.isbuiltin, inspect.isroutine,
                     inspect.isabstract]

_simple_types = (six.string_types + six.integer_types
                 + (type(None), bool, float))


def to_primitive(value, convert_instances=False, convert_datetime=True,
                 level=0, max_depth=3):
    """Convert a complex object into primitives.

Handy for JSON serialization. We can optionally handle instances,
but since this is a recursive function, we could have cyclical
data structures.

To handle cyclical data structures we could track the actual objects
visited in a set, but not all objects are hashable. Instead we just
track the depth of the object inspections and don't go too deep.

Therefore, convert_instances=True is lossy ... be aware.

"""
    # handle obvious types first - order of basic types determined by running
    # full tests on nova project, resulting in the following counts:
    # 572754 <type 'NoneType'>
    # 460353 <type 'int'>
    # 379632 <type 'unicode'>
    # 274610 <type 'str'>
    # 199918 <type 'dict'>
    # 114200 <type 'datetime.datetime'>
    # 51817 <type 'bool'>
    # 26164 <type 'list'>
    # 6491 <type 'float'>
    # 283 <type 'tuple'>
    # 19 <type 'long'>
    if isinstance(value, _simple_types):
        return value

    if isinstance(value, datetime.datetime):
        if convert_datetime:
            return timeutils.strtime(value)
        else:
            return value

    # value of itertools.count doesn't get caught by nasty_type_tests
    # and results in infinite loop when list(value) is called.
    if type(value) == itertools.count:
        return six.text_type(value)

    # FIXME(vish): Workaround for LP bug 852095. Without this workaround,
    # tests that raise an exception in a mocked method that
    # has a @wrap_exception with a notifier will fail. If
    # we up the dependency to 0.5.4 (when it is released) we
    # can remove this workaround.
    if getattr(value, '__module__', None) == 'mox':
        return 'mock'

    if level > max_depth:
        return '?'

    # The try block may not be necessary after the class check above,
    # but just in case ...
    try:
        recursive = functools.partial(to_primitive,
                                      convert_instances=convert_instances,
                                      convert_datetime=convert_datetime,
                                      level=level,
                                      max_depth=max_depth)
        if isinstance(value, dict):
            return dict((k, recursive(v)) for k, v in value.iteritems())
        elif isinstance(value, (list, tuple)):
            return [recursive(lv) for lv in value]

        # It's not clear why xmlrpclib created their own DateTime type, but
        # for our purposes, make it a datetime type which is explicitly
        # handled
        if xmlrpclib and isinstance(value, xmlrpclib.DateTime):
            value = datetime.datetime(*tuple(value.timetuple())[:6])

        if convert_datetime and isinstance(value, datetime.datetime):
            return timeutils.strtime(value)
        elif hasattr(value, 'iteritems'):
            return recursive(dict(value.iteritems()), level=level + 1)
        elif hasattr(value, '__iter__'):
            return recursive(list(value))
        elif convert_instances and hasattr(value, '__dict__'):
            # Likely an instance of something. Watch for cycles.
            # Ignore class member vars.
            return recursive(value.__dict__, level=level + 1)
        elif netaddr and isinstance(value, netaddr.IPAddress):
            return six.text_type(value)
        else:
            if any(test(value) for test in _nasty_type_tests):
                return six.text_type(value)
            return value
    except TypeError:
        # Class objects are tricky since they may define something like
        # __iter__ defined but it isn't callable as list().
        return six.text_type(value)


def dumps(value, default=to_primitive, **kwargs):
    return json.dumps(value, default=default, **kwargs)


def loads(s):
    return json.loads(s)


def load(s):
    return json.load(s)


try:
    import anyjson
except ImportError:
    pass
else:
    anyjson._modules.append((__name__, 'dumps', TypeError,
                                       'loads', ValueError, 'load'))
    anyjson.force_implementation(__name__)

########NEW FILE########
__FILENAME__ = local
# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Local storage of variables using weak references"""

import threading
import weakref


class WeakLocal(threading.local):
    def __getattribute__(self, attr):
        rval = super(WeakLocal, self).__getattribute__(attr)
        if rval:
            # NOTE(mikal): this bit is confusing. What is stored is a weak
            # reference, not the value itself. We therefore need to lookup
            # the weak reference and return the inner value here.
            rval = rval()
        return rval

    def __setattr__(self, attr, value):
        value = weakref.ref(value)
        return super(WeakLocal, self).__setattr__(attr, value)


# NOTE(mikal): the name "store" should be deprecated in the future
store = WeakLocal()

# A "weak" store uses weak references and allows an object to fall out of scope
# when it falls out of scope in the code that uses the thread local storage. A
# "strong" store will hold a reference to the object so that it never falls out
# of scope.
weak_store = WeakLocal()
strong_store = threading.local()

########NEW FILE########
__FILENAME__ = lockutils
# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import contextlib
import errno
import functools
import os
import threading
import time
import weakref

from oslo.config import cfg

from meniscus.openstack.common import fileutils
from meniscus.openstack.common.gettextutils import _  # noqa
from meniscus.openstack.common import local
from meniscus.openstack.common import log as logging


LOG = logging.getLogger(__name__)


util_opts = [
    cfg.BoolOpt('disable_process_locking', default=False,
                help='Whether to disable inter-process locks'),
    cfg.StrOpt('lock_path',
               help=('Directory to use for lock files.'))
]


CONF = cfg.CONF
CONF.register_opts(util_opts)


def set_defaults(lock_path):
    cfg.set_defaults(util_opts, lock_path=lock_path)


class _InterProcessLock(object):
    """Lock implementation which allows multiple locks, working around
issues like bugs.debian.org/cgi-bin/bugreport.cgi?bug=632857 and does
not require any cleanup. Since the lock is always held on a file
descriptor rather than outside of the process, the lock gets dropped
automatically if the process crashes, even if __exit__ is not executed.

There are no guarantees regarding usage by multiple green threads in a
single process here. This lock works only between processes. Exclusive
access between local threads should be achieved using the semaphores
in the @synchronized decorator.

Note these locks are released when the descriptor is closed, so it's not
safe to close the file descriptor while another green thread holds the
lock. Just opening and closing the lock file can break synchronisation,
so lock files must be accessed only using this abstraction.
"""

    def __init__(self, name):
        self.lockfile = None
        self.fname = name

    def __enter__(self):
        self.lockfile = open(self.fname, 'w')

        while True:
            try:
                # Using non-blocking locks since green threads are not
                # patched to deal with blocking locking calls.
                # Also upon reading the MSDN docs for locking(), it seems
                # to have a laughable 10 attempts "blocking" mechanism.
                self.trylock()
                return self
            except IOError as e:
                if e.errno in (errno.EACCES, errno.EAGAIN):
                    # external locks synchronise things like iptables
                    # updates - give it some time to prevent busy spinning
                    time.sleep(0.01)
                else:
                    raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.unlock()
            self.lockfile.close()
        except IOError:
            LOG.exception(_("Could not release the acquired lock `%s`"),
                          self.fname)

    def trylock(self):
        raise NotImplementedError()

    def unlock(self):
        raise NotImplementedError()


class _WindowsLock(_InterProcessLock):
    def trylock(self):
        msvcrt.locking(self.lockfile.fileno(), msvcrt.LK_NBLCK, 1)

    def unlock(self):
        msvcrt.locking(self.lockfile.fileno(), msvcrt.LK_UNLCK, 1)


class _PosixLock(_InterProcessLock):
    def trylock(self):
        fcntl.lockf(self.lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def unlock(self):
        fcntl.lockf(self.lockfile, fcntl.LOCK_UN)


if os.name == 'nt':
    import msvcrt
    InterProcessLock = _WindowsLock
else:
    import fcntl
    InterProcessLock = _PosixLock

_semaphores = weakref.WeakValueDictionary()


@contextlib.contextmanager
def lock(name, lock_file_prefix=None, external=False, lock_path=None):
    """Context based lock

This function yields a `threading.Semaphore` instance (if we don't use
eventlet.monkey_patch(), else `semaphore.Semaphore`) unless external is
True, in which case, it'll yield an InterProcessLock instance.

:param lock_file_prefix: The lock_file_prefix argument is used to provide
lock files on disk with a meaningful prefix.

:param external: The external keyword argument denotes whether this lock
should work across multiple processes. This means that if two different
workers both run a a method decorated with @synchronized('mylock',
external=True), only one of them will execute at a time.

:param lock_path: The lock_path keyword argument is used to specify a
special location for external lock files to live. If nothing is set, then
CONF.lock_path is used as a default.
"""
    # NOTE(soren): If we ever go natively threaded, this will be racy.
    # See http://stackoverflow.com/questions/5390569/dyn
    # amically-allocating-and-destroying-mutexes
    sem = _semaphores.get(name, threading.Semaphore())
    if name not in _semaphores:
        # this check is not racy - we're already holding ref locally
        # so GC won't remove the item and there was no IO switch
        # (only valid in greenthreads)
        _semaphores[name] = sem

    with sem:
        LOG.debug(_('Got semaphore "%(lock)s"'), {'lock': name})

        # NOTE(mikal): I know this looks odd
        if not hasattr(local.strong_store, 'locks_held'):
            local.strong_store.locks_held = []
        local.strong_store.locks_held.append(name)

        try:
            if external and not CONF.disable_process_locking:
                LOG.debug(_('Attempting to grab file lock "%(lock)s"'),
                          {'lock': name})

                # We need a copy of lock_path because it is non-local
                local_lock_path = lock_path or CONF.lock_path
                if not local_lock_path:
                    raise cfg.RequiredOptError('lock_path')

                if not os.path.exists(local_lock_path):
                    fileutils.ensure_tree(local_lock_path)
                    LOG.info(_('Created lock path: %s'), local_lock_path)

                def add_prefix(name, prefix):
                    if not prefix:
                        return name
                    sep = '' if prefix.endswith('-') else '-'
                    return '%s%s%s' % (prefix, sep, name)

                # NOTE(mikal): the lock name cannot contain directory
                # separators
                lock_file_name = add_prefix(name.replace(os.sep, '_'),
                                            lock_file_prefix)

                lock_file_path = os.path.join(local_lock_path, lock_file_name)

                try:
                    lock = InterProcessLock(lock_file_path)
                    with lock as lock:
                        LOG.debug(_('Got file lock "%(lock)s" at %(path)s'),
                                  {'lock': name, 'path': lock_file_path})
                        yield lock
                finally:
                    LOG.debug(_('Released file lock "%(lock)s" at %(path)s'),
                              {'lock': name, 'path': lock_file_path})
            else:
                yield sem

        finally:
            local.strong_store.locks_held.remove(name)


def synchronized(name, lock_file_prefix=None, external=False, lock_path=None):
    """Synchronization decorator.

Decorating a method like so::

@synchronized('mylock')
def foo(self, *args):
...

ensures that only one thread will execute the foo method at a time.

Different methods can share the same lock::

@synchronized('mylock')
def foo(self, *args):
...

@synchronized('mylock')
def bar(self, *args):
...

This way only one of either foo or bar can be executing at a time.
"""

    def wrap(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            with lock(name, lock_file_prefix, external, lock_path):
                LOG.debug(_('Got semaphore / lock "%(function)s"'),
                          {'function': f.__name__})
                return f(*args, **kwargs)

            LOG.debug(_('Semaphore / lock released "%(function)s"'),
                      {'function': f.__name__})
        return inner
    return wrap


def synchronized_with_prefix(lock_file_prefix):
    """Partial object generator for the synchronization decorator.

Redefine @synchronized in each project like so::

(in nova/utils.py)
from nova.openstack.common import lockutils

synchronized = lockutils.synchronized_with_prefix('nova-')


(in nova/foo.py)
from nova import utils

@utils.synchronized('mylock')
def bar(self, *args):
...

The lock_file_prefix argument is used to provide lock files on disk with a
meaningful prefix.
"""

    return functools.partial(synchronized, lock_file_prefix=lock_file_prefix)

########NEW FILE########
__FILENAME__ = log
# Copyright 2011 OpenStack Foundation.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Openstack logging handler.

This module adds to logging functionality by adding the option to specify
a context object when calling the various log methods. If the context object
is not specified, default formatting is used. Additionally, an instance uuid
may be passed as part of the log message, which is intended to make it easier
for admins to find messages related to a specific instance.

It also allows setting of formatting information through conf.

"""

import inspect
import itertools
import logging
import logging.config
import logging.handlers
import os
import sys
import traceback

from oslo.config import cfg
from six import moves

from meniscus.openstack.common.gettextutils import _  # noqa
from meniscus.openstack.common import importutils
from meniscus.openstack.common import jsonutils
from meniscus.openstack.common import local


_DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

common_cli_opts = [
    cfg.BoolOpt('debug',
                short='d',
                default=False,
                help='Print debugging output (set logging level to '
                     'DEBUG instead of default WARNING level).'),
    cfg.BoolOpt('verbose',
                short='v',
                default=False,
                help='Print more verbose output (set logging level to '
                     'INFO instead of default WARNING level).'),
]

logging_cli_opts = [
    cfg.StrOpt('log-config',
               metavar='PATH',
               help='If this option is specified, the logging configuration '
                    'file specified is used and overrides any other logging '
                    'options specified. Please see the Python logging module '
                    'documentation for details on logging configuration '
                    'files.'),
    cfg.StrOpt('log-format',
               default=None,
               metavar='FORMAT',
               help='DEPRECATED. '
                    'A logging.Formatter log message format string which may '
                    'use any of the available logging.LogRecord attributes. '
                    'This option is deprecated. Please use '
                    'logging_context_format_string and '
                    'logging_default_format_string instead.'),
    cfg.StrOpt('log-date-format',
               default=_DEFAULT_LOG_DATE_FORMAT,
               metavar='DATE_FORMAT',
               help='Format string for %%(asctime)s in log records. '
                    'Default: %(default)s'),
    cfg.StrOpt('log-file',
               metavar='PATH',
               deprecated_name='logfile',
               help='(Optional) Name of log file to output to. '
                    'If no default is set, logging will go to stdout.'),
    cfg.StrOpt('log-dir',
               deprecated_name='logdir',
               help='(Optional) The base directory used for relative '
                    '--log-file paths'),
    cfg.BoolOpt('use-syslog',
                default=False,
                help='Use syslog for logging.'),
    cfg.StrOpt('syslog-log-facility',
               default='LOG_USER',
               help='syslog facility to receive log lines')
]

generic_log_opts = [
    cfg.BoolOpt('use_stderr',
                default=True,
                help='Log output to standard error')
]

log_opts = [
    cfg.StrOpt('logging_context_format_string',
               default='%(asctime)s.%(msecs)03d %(process)d %(levelname)s '
                       '%(name)s [%(request_id)s %(user)s %(tenant)s] '
                       '%(instance)s%(message)s',
               help='format string to use for log messages with context'),
    cfg.StrOpt('logging_default_format_string',
               default='%(asctime)s.%(msecs)03d %(process)d %(levelname)s '
                       '%(name)s [-] %(instance)s%(message)s',
               help='format string to use for log messages without context'),
    cfg.StrOpt('logging_debug_format_suffix',
               default='%(funcName)s %(pathname)s:%(lineno)d',
               help='data to append to log format when level is DEBUG'),
    cfg.StrOpt('logging_exception_prefix',
               default='%(asctime)s.%(msecs)03d %(process)d TRACE %(name)s '
               '%(instance)s',
               help='prefix each line of exception output with this format'),
    cfg.ListOpt('default_log_levels',
                default=[
                    'amqplib=WARN',
                    'sqlalchemy=WARN',
                    'boto=WARN',
                    'suds=INFO',
                    'keystone=INFO',
                    'eventlet.wsgi.server=WARN'
                ],
                help='list of logger=LEVEL pairs'),
    cfg.BoolOpt('publish_errors',
                default=False,
                help='publish error events'),
    cfg.BoolOpt('fatal_deprecations',
                default=False,
                help='make deprecations fatal'),

    # NOTE(mikal): there are two options here because sometimes we are handed
    # a full instance (and could include more information), and other times we
    # are just handed a UUID for the instance.
    cfg.StrOpt('instance_format',
               default='[instance: %(uuid)s] ',
               help='If an instance is passed with the log message, format '
                    'it like this'),
    cfg.StrOpt('instance_uuid_format',
               default='[instance: %(uuid)s] ',
               help='If an instance UUID is passed with the log message, '
                    'format it like this'),
]

CONF = cfg.CONF
CONF.register_cli_opts(common_cli_opts)
CONF.register_cli_opts(logging_cli_opts)
CONF.register_opts(generic_log_opts)
CONF.register_opts(log_opts)

# our new audit level
# NOTE(jkoelker) Since we synthesized an audit level, make the logging
# module aware of it so it acts like other levels.
logging.AUDIT = logging.INFO + 1
logging.addLevelName(logging.AUDIT, 'AUDIT')


try:
    NullHandler = logging.NullHandler
except AttributeError:  # NOTE(jkoelker) NullHandler added in Python 2.7
    class NullHandler(logging.Handler):
        def handle(self, record):
            pass

        def emit(self, record):
            pass

        def createLock(self):
            self.lock = None


def _dictify_context(context):
    if context is None:
        return None
    if not isinstance(context, dict) and getattr(context, 'to_dict', None):
        context = context.to_dict()
    return context


def _get_binary_name():
    return os.path.basename(inspect.stack()[-1][1])


def _get_log_file_path(binary=None):
    logfile = CONF.log_file
    logdir = CONF.log_dir

    if logfile and not logdir:
        return logfile

    if logfile and logdir:
        return os.path.join(logdir, logfile)

    if logdir:
        binary = binary or _get_binary_name()
        return '%s.log' % (os.path.join(logdir, binary),)


class BaseLoggerAdapter(logging.LoggerAdapter):

    def audit(self, msg, *args, **kwargs):
        self.log(logging.AUDIT, msg, *args, **kwargs)


class LazyAdapter(BaseLoggerAdapter):
    def __init__(self, name='unknown', version='unknown'):
        self._logger = None
        self.extra = {}
        self.name = name
        self.version = version

    @property
    def logger(self):
        if not self._logger:
            self._logger = getLogger(self.name, self.version)
        return self._logger


class ContextAdapter(BaseLoggerAdapter):
    warn = logging.LoggerAdapter.warning

    def __init__(self, logger, project_name, version_string):
        self.logger = logger
        self.project = project_name
        self.version = version_string

    @property
    def handlers(self):
        return self.logger.handlers

    def deprecated(self, msg, *args, **kwargs):
        stdmsg = _("Deprecated: %s") % msg
        if CONF.fatal_deprecations:
            self.critical(stdmsg, *args, **kwargs)
            raise DeprecatedConfig(msg=stdmsg)
        else:
            self.warn(stdmsg, *args, **kwargs)

    def process(self, msg, kwargs):
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        extra = kwargs['extra']

        context = kwargs.pop('context', None)
        if not context:
            context = getattr(local.store, 'context', None)
        if context:
            extra.update(_dictify_context(context))

        instance = kwargs.pop('instance', None)
        instance_uuid = (extra.get('instance_uuid', None) or
                         kwargs.pop('instance_uuid', None))
        instance_extra = ''
        if instance:
            instance_extra = CONF.instance_format % instance
        elif instance_uuid:
            instance_extra = (CONF.instance_uuid_format
                              % {'uuid': instance_uuid})
        extra.update({'instance': instance_extra})

        extra.update({"project": self.project})
        extra.update({"version": self.version})
        extra['extra'] = extra.copy()
        return msg, kwargs


class JSONFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        # NOTE(jkoelker) we ignore the fmt argument, but its still there
        # since logging.config.fileConfig passes it.
        self.datefmt = datefmt

    def formatException(self, ei, strip_newlines=True):
        lines = traceback.format_exception(*ei)
        if strip_newlines:
            lines = [itertools.ifilter(
                lambda x: x,
                line.rstrip().splitlines()) for line in lines]
            lines = list(itertools.chain(*lines))
        return lines

    def format(self, record):
        message = {'message': record.getMessage(),
                   'asctime': self.formatTime(record, self.datefmt),
                   'name': record.name,
                   'msg': record.msg,
                   'args': record.args,
                   'levelname': record.levelname,
                   'levelno': record.levelno,
                   'pathname': record.pathname,
                   'filename': record.filename,
                   'module': record.module,
                   'lineno': record.lineno,
                   'funcname': record.funcName,
                   'created': record.created,
                   'msecs': record.msecs,
                   'relative_created': record.relativeCreated,
                   'thread': record.thread,
                   'thread_name': record.threadName,
                   'process_name': record.processName,
                   'process': record.process,
                   'traceback': None}

        if hasattr(record, 'extra'):
            message['extra'] = record.extra

        if record.exc_info:
            message['traceback'] = self.formatException(record.exc_info)

        return jsonutils.dumps(message)


def _create_logging_excepthook(product_name):
    def logging_excepthook(type, value, tb):
        extra = {}
        if CONF.verbose:
            extra['exc_info'] = (type, value, tb)
        getLogger(product_name).critical(str(value), **extra)
    return logging_excepthook


class LogConfigError(Exception):

    message = _('Error loading logging config %(log_config)s: %(err_msg)s')

    def __init__(self, log_config, err_msg):
        self.log_config = log_config
        self.err_msg = err_msg

    def __str__(self):
        return self.message % dict(log_config=self.log_config,
                                   err_msg=self.err_msg)


def _load_log_config(log_config):
    try:
        logging.config.fileConfig(log_config)
    except moves.configparser.Error as exc:
        raise LogConfigError(log_config, str(exc))


def setup(product_name):
    """Setup logging."""
    if CONF.log_config:
        _load_log_config(CONF.log_config)
    else:
        _setup_logging_from_conf()
    sys.excepthook = _create_logging_excepthook(product_name)


def set_defaults(logging_context_format_string):
    cfg.set_defaults(log_opts,
                     logging_context_format_string=
                     logging_context_format_string)


def _find_facility_from_conf():
    facility_names = logging.handlers.SysLogHandler.facility_names
    facility = getattr(logging.handlers.SysLogHandler,
                       CONF.syslog_log_facility,
                       None)

    if facility is None and CONF.syslog_log_facility in facility_names:
        facility = facility_names.get(CONF.syslog_log_facility)

    if facility is None:
        valid_facilities = facility_names.keys()
        consts = ['LOG_AUTH', 'LOG_AUTHPRIV', 'LOG_CRON', 'LOG_DAEMON',
                  'LOG_FTP', 'LOG_KERN', 'LOG_LPR', 'LOG_MAIL', 'LOG_NEWS',
                  'LOG_AUTH', 'LOG_SYSLOG', 'LOG_USER', 'LOG_UUCP',
                  'LOG_LOCAL0', 'LOG_LOCAL1', 'LOG_LOCAL2', 'LOG_LOCAL3',
                  'LOG_LOCAL4', 'LOG_LOCAL5', 'LOG_LOCAL6', 'LOG_LOCAL7']
        valid_facilities.extend(consts)
        raise TypeError(_('syslog facility must be one of: %s') %
                        ', '.join("'%s'" % fac
                                  for fac in valid_facilities))

    return facility


def _setup_logging_from_conf():
    log_root = getLogger(None).logger
    for handler in log_root.handlers:
        log_root.removeHandler(handler)

    if CONF.use_syslog:
        facility = _find_facility_from_conf()
        syslog = logging.handlers.SysLogHandler(address='/dev/log',
                                                facility=facility)
        log_root.addHandler(syslog)

    logpath = _get_log_file_path()
    if logpath:
        filelog = logging.handlers.WatchedFileHandler(logpath)
        log_root.addHandler(filelog)

    if CONF.use_stderr:
        streamlog = ColorHandler()
        log_root.addHandler(streamlog)

    elif not CONF.log_file:
        # pass sys.stdout as a positional argument
        # python2.6 calls the argument strm, in 2.7 it's stream
        streamlog = logging.StreamHandler(sys.stdout)
        log_root.addHandler(streamlog)

    if CONF.publish_errors:
        handler = importutils.import_object(
            "meniscus.openstack.common.log_handler.PublishErrorsHandler",
            logging.ERROR)
        log_root.addHandler(handler)

    datefmt = CONF.log_date_format
    for handler in log_root.handlers:
        # NOTE(alaski): CONF.log_format overrides everything currently. This
        # should be deprecated in favor of context aware formatting.
        if CONF.log_format:
            handler.setFormatter(logging.Formatter(fmt=CONF.log_format,
                                                   datefmt=datefmt))
            log_root.info('Deprecated: log_format is now deprecated and will '
                          'be removed in the next release')
        else:
            handler.setFormatter(ContextFormatter(datefmt=datefmt))

    if CONF.debug:
        log_root.setLevel(logging.DEBUG)
    elif CONF.verbose:
        log_root.setLevel(logging.INFO)
    else:
        log_root.setLevel(logging.WARNING)

    for pair in CONF.default_log_levels:
        mod, _sep, level_name = pair.partition('=')
        level = logging.getLevelName(level_name)
        logger = logging.getLogger(mod)
        logger.setLevel(level)

_loggers = {}


def getLogger(name='unknown', version='unknown'):
    if name not in _loggers:
        _loggers[name] = ContextAdapter(logging.getLogger(name),
                                        name,
                                        version)
    return _loggers[name]


def getLazyLogger(name='unknown', version='unknown'):
    """Returns lazy logger.

Creates a pass-through logger that does not create the real logger
until it is really needed and delegates all calls to the real logger
once it is created.
"""
    return LazyAdapter(name, version)


class WritableLogger(object):
    """A thin wrapper that responds to `write` and logs."""

    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level

    def write(self, msg):
        self.logger.log(self.level, msg)


class ContextFormatter(logging.Formatter):
    """A context.RequestContext aware formatter configured through flags.

The flags used to set format strings are: logging_context_format_string
and logging_default_format_string. You can also specify
logging_debug_format_suffix to append extra formatting if the log level is
debug.

For information about what variables are available for the formatter see:
http://docs.python.org/library/logging.html#formatter

"""

    def format(self, record):
        """Uses contextstring if request_id is set, otherwise default."""
        # NOTE(sdague): default the fancier formating params
        # to an empty string so we don't throw an exception if
        # they get used
        for key in ('instance', 'color'):
            if key not in record.__dict__:
                record.__dict__[key] = ''

        if record.__dict__.get('request_id', None):
            self._fmt = CONF.logging_context_format_string
        else:
            self._fmt = CONF.logging_default_format_string

        if (record.levelno == logging.DEBUG and
                CONF.logging_debug_format_suffix):
            self._fmt += " " + CONF.logging_debug_format_suffix

        # Cache this on the record, Logger will respect our formated copy
        if record.exc_info:
            record.exc_text = self.formatException(record.exc_info, record)
        return logging.Formatter.format(self, record)

    def formatException(self, exc_info, record=None):
        """Format exception output with CONF.logging_exception_prefix."""
        if not record:
            return logging.Formatter.formatException(self, exc_info)

        stringbuffer = moves.StringIO()
        traceback.print_exception(exc_info[0], exc_info[1], exc_info[2],
                                  None, stringbuffer)
        lines = stringbuffer.getvalue().split('\n')
        stringbuffer.close()

        if CONF.logging_exception_prefix.find('%(asctime)') != -1:
            record.asctime = self.formatTime(record, self.datefmt)

        formatted_lines = []
        for line in lines:
            pl = CONF.logging_exception_prefix % record.__dict__
            fl = '%s%s' % (pl, line)
            formatted_lines.append(fl)
        return '\n'.join(formatted_lines)


class ColorHandler(logging.StreamHandler):
    LEVEL_COLORS = {
        logging.DEBUG: '\033[00;32m',  # GREEN
        logging.INFO: '\033[00;36m',  # CYAN
        logging.AUDIT: '\033[01;36m',  # BOLD CYAN
        logging.WARN: '\033[01;33m',  # BOLD YELLOW
        logging.ERROR: '\033[01;31m',  # BOLD RED
        logging.CRITICAL: '\033[01;31m',  # BOLD RED
    }

    def format(self, record):
        record.color = self.LEVEL_COLORS[record.levelno]
        return logging.StreamHandler.format(self, record)


class DeprecatedConfig(Exception):
    message = _("Fatal call to deprecated config: %(msg)s")

    def __init__(self, msg):
        super(Exception, self).__init__(self.message % dict(msg=msg))

########NEW FILE########
__FILENAME__ = timeutils
# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Time related utilities and helper functions.
"""

import calendar
import datetime
import time

import iso8601
import six


# ISO 8601 extended time format with microseconds
_ISO8601_TIME_FORMAT_SUBSECOND = '%Y-%m-%dT%H:%M:%S.%f'
_ISO8601_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
PERFECT_TIME_FORMAT = _ISO8601_TIME_FORMAT_SUBSECOND


def isotime(at=None, subsecond=False):
    """Stringify time in ISO 8601 format."""
    if not at:
        at = utcnow()
    st = at.strftime(_ISO8601_TIME_FORMAT
                     if not subsecond
                     else _ISO8601_TIME_FORMAT_SUBSECOND)
    tz = at.tzinfo.tzname(None) if at.tzinfo else 'UTC'
    st += ('Z' if tz == 'UTC' else tz)
    return st


def parse_isotime(timestr):
    """Parse time from ISO 8601 format."""
    try:
        return iso8601.parse_date(timestr)
    except iso8601.ParseError as e:
        raise ValueError(unicode(e))
    except TypeError as e:
        raise ValueError(unicode(e))


def strtime(at=None, fmt=PERFECT_TIME_FORMAT):
    """Returns formatted utcnow."""
    if not at:
        at = utcnow()
    return at.strftime(fmt)


def parse_strtime(timestr, fmt=PERFECT_TIME_FORMAT):
    """Turn a formatted time back into a datetime."""
    return datetime.datetime.strptime(timestr, fmt)


def normalize_time(timestamp):
    """Normalize time in arbitrary timezone to UTC naive object."""
    offset = timestamp.utcoffset()
    if offset is None:
        return timestamp
    return timestamp.replace(tzinfo=None) - offset


def is_older_than(before, seconds):
    """Return True if before is older than seconds."""
    if isinstance(before, six.string_types):
        before = parse_strtime(before).replace(tzinfo=None)
    return utcnow() - before > datetime.timedelta(seconds=seconds)


def is_newer_than(after, seconds):
    """Return True if after is newer than seconds."""
    if isinstance(after, six.string_types):
        after = parse_strtime(after).replace(tzinfo=None)
    return after - utcnow() > datetime.timedelta(seconds=seconds)


def utcnow_ts():
    """Timestamp version of our utcnow function."""
    if utcnow.override_time is None:
        # NOTE(kgriffs): This is several times faster
        # than going through calendar.timegm(...)
        return int(time.time())

    return calendar.timegm(utcnow().timetuple())


def utcnow():
    """Overridable version of utils.utcnow."""
    if utcnow.override_time:
        try:
            return utcnow.override_time.pop(0)
        except AttributeError:
            return utcnow.override_time
    return datetime.datetime.utcnow()


def iso8601_from_timestamp(timestamp):
    """Returns a iso8601 formated date from timestamp."""
    return isotime(datetime.datetime.utcfromtimestamp(timestamp))


utcnow.override_time = None


def set_time_override(override_time=None):
    """Overrides utils.utcnow.

Make it return a constant time or a list thereof, one at a time.

:param override_time: datetime instance or list thereof. If not
given, defaults to the current UTC time.
"""
    utcnow.override_time = override_time or datetime.datetime.utcnow()


def advance_time_delta(timedelta):
    """Advance overridden time using a datetime.timedelta."""
    assert(not utcnow.override_time is None)
    try:
        for dt in utcnow.override_time:
            dt += timedelta
    except TypeError:
        utcnow.override_time += timedelta


def advance_time_seconds(seconds):
    """Advance overridden time by seconds."""
    advance_time_delta(datetime.timedelta(0, seconds))


def clear_time_override():
    """Remove the overridden time."""
    utcnow.override_time = None


def marshall_now(now=None):
    """Make an rpc-safe datetime with microseconds.

Note: tzinfo is stripped, but not required for relative times.
"""
    if not now:
        now = utcnow()
    return dict(day=now.day, month=now.month, year=now.year, hour=now.hour,
                minute=now.minute, second=now.second,
                microsecond=now.microsecond)


def unmarshall_time(tyme):
    """Unmarshall a datetime dict."""
    return datetime.datetime(day=tyme['day'],
                             month=tyme['month'],
                             year=tyme['year'],
                             hour=tyme['hour'],
                             minute=tyme['minute'],
                             second=tyme['second'],
                             microsecond=tyme['microsecond'])


def delta_seconds(before, after):
    """Return the difference between two timing objects.

Compute the difference in seconds between two date, time, or
datetime objects (as a float, to microsecond resolution).
"""
    delta = after - before
    try:
        return delta.total_seconds()
    except AttributeError:
        return ((delta.days * 24 * 3600) + delta.seconds +
                float(delta.microseconds) / (10 ** 6))


def is_soon(dt, window):
    """Determines if time is going to happen in the next window seconds.

:params dt: the time
:params window: minimum seconds to remain to consider the time not soon

:return: True if expiration is within the given duration
"""
    soon = (utcnow() + datetime.timedelta(seconds=window))
    return normalize_time(dt) <= soon

########NEW FILE########
__FILENAME__ = publish_stats
from oslo.config import cfg

from meniscus.api.utils.request import http_request
from meniscus.config import get_config
from meniscus.config import init_config
from meniscus.data.cache_handler import ConfigCache
from meniscus.data.model.worker import Worker
from meniscus.openstack.common import jsonutils
from meniscus.queue import celery
from meniscus import env


_LOG = env.get_logger(__name__)

# cache configuration options
_STATUS_UPDATE_GROUP = cfg.OptGroup(name='status_update',
                                    title='Status Update Settings')
get_config().register_group(_STATUS_UPDATE_GROUP)

_CACHE_OPTIONS = [
    cfg.IntOpt('worker_status_interval',
               default=60,
               help="""default time to update the worker status"""
               )
]

get_config().register_opts(_CACHE_OPTIONS, group=_STATUS_UPDATE_GROUP)
try:
    init_config()
    conf = get_config()
except cfg.ConfigFilesNotFoundError:
    conf = get_config()

WORKER_STATUS_INTERVAL = conf.status_update.worker_status_interval


@celery.task(name="stats.publish")
def publish_worker_stats():
    """
    Publishes worker stats to the Coordinator(s) at set times
    """
    try:
        cache = ConfigCache()
        config = cache.get_config()

        request_uri = "{0}/worker/{1}/status".format(
            config.coordinator_uri, config.hostname)

        req_body = {
            'worker_status': Worker(personality=config.personality).format()
        }

        http_request(url=request_uri, json_payload=jsonutils.dumps(req_body),
                     http_verb='PUT')
    except Exception as ex:
        _LOG.info(ex.message)

########NEW FILE########
__FILENAME__ = app
from multiprocessing import Process

import falcon

from meniscus.api.status.resources import (
    WorkerStatusResource, WorkersStatusResource)
from meniscus.api.tenant.resources import (
    EventProducerResource, EventProducersResource,
    UserResource, TenantResource, TokenResource)
from meniscus.api.version.resources import VersionResource
from meniscus import env
from meniscus.queue import celery


_LOG = env.get_logger(__name__)


def start_up():
    #Common Resource(s)
    versions = VersionResource()

    #Coordinator Resources
    workers_status = WorkersStatusResource()
    worker_status = WorkerStatusResource()

    #Tenant Resources
    tenant = TenantResource()
    user = UserResource()
    event_producers = EventProducersResource()
    event_producer = EventProducerResource()
    token = TokenResource()

    # Create API
    application = api = falcon.API()

    # Common Routing
    api.add_route('/', versions)

    api.add_route('/v1/worker/{hostname}/status', worker_status)
    api.add_route('/v1/status', workers_status)

    # Tenant Routing
    api.add_route('/v1/tenant', tenant)
    api.add_route('/v1/tenant/{tenant_id}', user)
    api.add_route('/v1/tenant/{tenant_id}/producers', event_producers)
    api.add_route('/v1/tenant/{tenant_id}/producers/{event_producer_id}',
                  event_producer)

    api.add_route('/v1/tenant/{tenant_id}/token', token)

    celery_proc = Process(target=celery.worker_main)
    celery_proc.start()
    _LOG.info(
        'Celery started as process: {}'.format(celery_proc.pid)
    )

    return application

########NEW FILE########
__FILENAME__ = app
from multiprocessing import Process
from datetime import timedelta

import falcon

from meniscus.api.tenant.resources import EventProducerResource
from meniscus.api.tenant.resources import EventProducersResource
from meniscus.api.tenant.resources import UserResource
from meniscus.api.tenant.resources import TenantResource
from meniscus.api.tenant.resources import TokenResource
from meniscus.api.version.resources import VersionResource
from meniscus.data.datastore import COORDINATOR_DB, get_data_handler
from meniscus import env
from meniscus.personas.common import publish_stats
from meniscus.queue import celery


_LOG = env.get_logger(__name__)


def start_up():
    #Common Resource(s)
    versions = VersionResource()

    #Tenant Resources
    tenant = TenantResource()
    user = UserResource()
    event_producers = EventProducersResource()
    event_producer = EventProducerResource()
    token = TokenResource()

    # Create API
    application = api = falcon.API()

    # Version Routing
    api.add_route('/', versions)

    # Tenant Routing
    api.add_route('/v1/tenant', tenant)
    api.add_route('/v1/tenant/{tenant_id}', user)
    api.add_route('/v1/tenant/{tenant_id}/producers', event_producers)
    api.add_route('/v1/tenant/{tenant_id}/producers/{event_producer_id}',
                  event_producer)
    api.add_route('/v1/tenant/{tenant_id}/token', token)

    celery.conf.CELERYBEAT_SCHEDULE = {
        'worker_stats': {
            'task': 'stats.publish',
            'schedule': timedelta(seconds=publish_stats.WORKER_STATUS_INTERVAL)
        },
    }

    #include blank argument to celery in order for beat to start correctly
    celery_proc = Process(target=celery.worker_main, args=[['', '--beat']])
    celery_proc.start()
    _LOG.info(
        'Celery started as process: {}'.format(celery_proc.pid)
    )

    return application

########NEW FILE########
__FILENAME__ = app
from multiprocessing import Process
from datetime import timedelta

import falcon

from meniscus.api.http_log.resources import PublishMessageResource
from meniscus.api.version.resources import VersionResource
from meniscus import config
from meniscus import env
from meniscus.correlation import receiver
from meniscus.personas.common import publish_stats
from meniscus.queue import celery
from meniscus.sinks.elasticsearch import ElasticSearchStreamBulker


_LOG = env.get_logger(__name__)


def start_up():
    try:
        config.init_config()
    except config.cfg.ConfigFilesNotFoundError as ex:
        _LOG.exception(ex.message)

    application = api = falcon.API()
    api.add_route('/', VersionResource())

    #http correlation endpoint
    api.add_route('/v1/tenant/{tenant_id}/publish', PublishMessageResource())

    #syslog correlation endpoint
    server = receiver.new_correlation_input_server()

    server_proc = Process(target=server.start)
    server_proc.start()

    _LOG.info(
        'ZeroMQ reception server started as process: {}'.format(
            server_proc.pid)
    )

    celery.conf.CELERYBEAT_SCHEDULE = {
        'worker_stats': {
            'task': 'stats.publish',
            'schedule': timedelta(seconds=publish_stats.WORKER_STATUS_INTERVAL)
        },
    }

    #include blank argument to celery in order for beat to start correctly
    celery_proc = Process(target=celery.worker_main, args=[['', '--beat']])
    celery_proc.start()
    _LOG.info(
        'Celery started as process: {}'.format(celery_proc.pid)
    )

    es_flusher = ElasticSearchStreamBulker()
    flush_proc = Process(target=es_flusher.start)
    flush_proc.start()
    _LOG.info(
        'ElasticSearchStreamBulker started as process: {}'.format(
            flush_proc.pid)
    )
    return application

########NEW FILE########
__FILENAME__ = proxy
try:
    import uwsgi
    UWSGI = True
except ImportError:
    uwsgi = None
    UWSGI = False


class NativeProxy(object):
    def __init__(self):
        self.server = uwsgi
        self.UWSGI = UWSGI
        # Default timeout = 15 minutes

    def cache_exists(self, key, cache_name):
        if self.UWSGI:
            return self.server.cache_exists(key, cache_name)
        else:
            return None

    def cache_get(self, key, cache_name):
        if self.UWSGI:
            return self.server.cache_get(key, cache_name)
        else:
            return None

    def cache_set(self, key, value, cache_expires, cache_name):
        if self.UWSGI:
            self.server.cache_set(
                key, value, cache_expires, cache_name)

    def cache_update(self, key, value, cache_expires, cache_name):
        if self.UWSGI:
            self.server.cache_update(
                key, value, cache_expires, cache_name)

    def cache_del(self, key, cache_name):
        if self.UWSGI:
            self.server.cache_del(key, cache_name)

    def cache_clear(self, cache_name):
        if self.UWSGI:
            self.server.cache_clear(cache_name)

    def restart(self):
        if self.UWSGI:
            self.server.reload()

########NEW FILE########
__FILENAME__ = dispatch
from oslo.config import cfg

import meniscus.config as config
from meniscus import env
from meniscus.sinks import elasticsearch

_LOG = env.get_logger(__name__)

_DATA_SINKS_GROUP = cfg.OptGroup(name='data_sinks', title='Data Sink List')
config.get_config().register_group(_DATA_SINKS_GROUP)

_SINK = [
    cfg.ListOpt('valid_sinks',
                default=['elasticsearch'],
                help="""valid data sinks list"""
                ),
    cfg.StrOpt('default_sink',
               default='elasticsearch',
               help="""default data sink"""
               )
]

config.get_config().register_opts(_SINK, group=_DATA_SINKS_GROUP)

try:
    config.init_config()
except config.cfg.ConfigFilesNotFoundError as ex:
    _LOG.exception(ex.message)

conf = config.get_config()

VALID_SINKS = conf.data_sinks.valid_sinks
DEFAULT_SINK = conf.data_sinks.default_sink


def route_message(message):
    message_sinks = message['meniscus']['correlation']['sinks']
    if 'elasticsearch' in message_sinks:
        elasticsearch.put_message.delay(message)

########NEW FILE########
__FILENAME__ = sink
"""
This module contains operations for implementing an elasticsearch data sink.
It exposes a task that allows messages to be queued for indexing.  It then
exposes the ElasticSearchBulkStreamer which creates a pool of processes for
pulling a stream off of the queue and performing bulk flushes to Elasticsearch.
"""
from multiprocessing import cpu_count, Process
import signal
import sys
import uuid

from kombu import Connection, Exchange, Queue
from kombu.pools import producers
from elasticsearch import helpers as es_helpers

import meniscus.config as config
from meniscus import env
from meniscus.data.handlers import elasticsearch
from meniscus.queue import celery


_LOG = env.get_logger(__name__)

conf = config.get_config()
broker_url = conf.celery.BROKER_URL

es_handler = elasticsearch.get_handler()

BULK_SIZE = es_handler.bulk_size
TTL = es_handler.ttl
ELASTICSEARCH_QUEUE = 'elasticsearch'

try:
    # The broker where our exchange is.
    connection = Connection(broker_url)

    # The exchange we send our index requests to.
    es_exchange = Exchange(
        ELASTICSEARCH_QUEUE, exchange_type='direct', exchange_durable=True)
    bound_exchange = es_exchange(connection)
    bound_exchange.declare()

    # Queue that exchange will route messages to
    es_queue = Queue(ELASTICSEARCH_QUEUE, exchange=bound_exchange,
                     routing_key=ELASTICSEARCH_QUEUE, queue_durable=True)
except Exception as ex:
    _LOG.exception(ex)


def _queue_index_request(index, doc_type, document, ttl=TTL):
    """
    places a message index request on the queue
    """

    #create the metadata for index operation
    action = {
        '_index': index,
        '_type': doc_type,
        '_id': str(uuid.uuid4()),
        '_ttl': ttl,
        '_source': document
    }

    #publish the message
    with producers[connection].acquire(block=True) as producer:
        producer.publish(action, routing_key=ELASTICSEARCH_QUEUE,
                         serializer='json', declare=[es_queue])


@celery.task
def put_message(message):
    """
    Builds an indexing requests for a message, then sends the request
    to be queued
    """
    try:
        _queue_index_request(
            index=message['meniscus']['tenant'],
            doc_type=message['meniscus']['correlation']['pattern'],
            document=message)
    except Exception as ex:
        _LOG.exception(ex.message)
        put_message.retry()


def get_queue_stream(ack_list, bulk_timeout=60):
    """
    A generator that pulls messages off a queue and yields the result.
    The generator can be used as an iterable to consume messages.
    Messages will be pulled continuously and will block while waiting for new
    messages until the timeout is reached.
    :param ack_list: list of data for messages that pending acknowledgement
    :param bulk_timeout:  length of time to wait for a message from queue
    """
    with Connection(broker_url) as connection:
        simple_queue = connection.SimpleQueue(ELASTICSEARCH_QUEUE)
        while True:
            msg = simple_queue.get(block=True, timeout=bulk_timeout)
            ack_list.append(msg)
            yield msg.payload


def flush_to_es():
    """
    Flushes a stream of messages to elasticsearch using bulk flushing.
    Uses a generator to pull messages off the queue and passes this as an
     iterable to the streaming_bulk method.  streaming_bulk is also a generator
     that yields message data used for acking from the queue after they
     are flushed.
    :param bulk_size: the number of messages to flush at once to elasticsearch
    :param bulk_timeout:
    :return: length of time to wait for a message from queue
    """

    while True:

        try:
            es_client = es_handler.connection
            ack_list = list()
            actions = get_queue_stream(ack_list)
            bulker = es_helpers.streaming_bulk(
                es_client, actions, chunk_size=BULK_SIZE)
            _LOG.error("Post flush")

            for response in bulker:
                msg = ack_list.pop(0)
                msg_ok = response[0]

                if msg_ok:
                    msg.ack()

        except Exception as ex:
            _LOG.exception(ex)


class ElasticSearchStreamBulker(object):
    """
    Controls a mutliprocess pool that pulls a message stream from a queue and
    bulk flushes to elasticsearch
    """
    def __init__(self, bulk_size=BULK_SIZE):
        self.bulk_size = bulk_size

    def start(self):
        """
        Start a process pool to handle streaming
        """
        concurrency = cpu_count()
        process_list = [
            Process(target=flush_to_es) for x in range(concurrency)]

        map(lambda x: x.start(), process_list)

########NEW FILE########
__FILENAME__ = resources_test
import unittest

from mock import MagicMock
from mock import patch
import falcon
import falcon.testing as testing
from meniscus.api.http_log.resources import PublishMessageResource
from meniscus.api.tenant.resources import MESSAGE_TOKEN
from meniscus.data.model import tenant
from meniscus.openstack.common import jsonutils


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingPublishMessage())
    return suite


class WhenTestingPublishMessage(testing.TestBase):
    def before(self):
        self.resource = PublishMessageResource()
        self.tenant_id = '1234'
        self.token = 'ffe7104e-8d93-47dc-a49a-8fb0d39e5192'
        self.host_name = 'tohru'
        self.producer_durable = 'durable'
        self.producer_non_durable = 'non_durable'
        self.pattern = "http://projectmeniscus.org/cee/profiles/base"
        self.producers = [
            tenant.EventProducer(1, self.producer_durable,
                                 self.pattern, durable=True),
            tenant.EventProducer(2, self.producer_non_durable, self.pattern)
        ]

        self.tenant = tenant.Tenant(
            self.tenant_id, self.token, event_producers=self.producers)
        self.message = {
            "log_message":  {
                "ver": "1",
                "msgid": "-",
                "pri": "46",
                "pid": "-",
                "host": self.host_name,
                "pname": "rsyslogd",
                "time": "2013-04-02T14:12:04.873490-05:00",
                "msg": "start",
                "native": {
                    "origin": {
                        "x-info": "http://www.rsyslog.com",
                        "swVersion": "7.2.5",
                        "x-pid": "12662",
                        "software": "rsyslogd"
                    }
                }
            }
        }

        self.req = MagicMock()
        self.req.get_header.return_value = \
            'ffe7104e-8d93-47dc-a49a-8fb0d39e5192'
        self.resp = MagicMock()

        self.test_route = '/v1/tenant/{tenant_id}/publish'
        self.api.add_route(self.test_route, self.resource)

    def test_returns_400_for_no_message_token_header(self):
        self.simulate_request(
            self.test_route,
            method='POST',
            headers={
                'content-type': 'application/json'
            },
            body=jsonutils.dumps(self.message))
        self.assertEquals(falcon.HTTP_400, self.srmock.status)

    def test_returns_202_for_non_durable_message(self):
        correlate_http_msg_func = MagicMock()
        with patch('meniscus.correlation.correlator.correlate_http_message',
                   correlate_http_msg_func):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={
                    'content-type': 'application/json',
                    MESSAGE_TOKEN: self.token
                },
                body=jsonutils.dumps(self.message))
            correlate_http_msg_func.assert_called_once()

        self.assertEquals(falcon.HTTP_202, self.srmock.status)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = resources_test
import unittest

import falcon
import falcon.testing as testing
from mock import MagicMock, patch


from meniscus.api.status.resources import WorkerStatusResource
from meniscus.api.status.resources import WorkersStatusResource
from meniscus.data.model.worker import Worker
from meniscus.data.model.worker import SystemInfo
from meniscus.openstack.common import jsonutils


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingWorkerOnPut())
    suite.addTest(WhenTestingWorkerStatus())

    return suite


class WhenTestingWorkerOnPut(testing.TestBase):
    def before(self):
        self.status = 'online'
        self.hostname = 'worker01'
        self.personality = 'worker'
        self.ip4 = "192.168.100.101",
        self.ip6 = "::1",
        self.system_info = SystemInfo().format()

        self.bad_status = 'bad_status'
        self.bad_system_info = SystemInfo()
        self.bad_worker_status = {
            'worker_status': {
                'hostname': self.hostname,
                'system_info': self.system_info,
                'status': self.bad_status,
                'personality': 'worker',
                'ip_address_v4': '192.168.100.101',
                'ip_address_v6': '::1'
            }
        }

        self.worker = {
            'worker_status': {
                'hostname': self.hostname,
                'system_info': self.system_info,
                'status': self.status,
                'personality': 'worker',
                'ip_address_v4': '192.168.100.101',
                'ip_address_v6': '::1'
            }
        }

        self.returned_worker = Worker(**{"hostname": "worker01",
                                         "ip_address_v4": "192.168.100.101",
                                         "ip_address_v6": "::1",
                                         "personality": "worker",
                                         "status": "online",
                                         "system_info": self.system_info})

        self.req = MagicMock()
        self.resp = MagicMock()
        self.resource = WorkerStatusResource()
        self.test_route = '/worker/{hostname}/status'
        self.api.add_route(self.test_route, self.resource)

    def test_returns_400_body_validation(self):
        with patch('meniscus.data.model.worker_util.save_worker', MagicMock()):
            self.simulate_request(
                self.test_route,
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(self.bad_worker_status))
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_202_for_new_worker_when_worker_not_found(self):
        create_worker = MagicMock()

        with patch('meniscus.data.model.worker_util.find_worker',
                   MagicMock(return_value=None)), \
                patch('meniscus.data.model.worker_util.create_worker',
                      create_worker):

            self.simulate_request(
                self.test_route,
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(self.worker))
            # self.assertEqual(falcon.HTTP_202, self.srmock.status)

    def test_return_200_for_new_worker_when_worker_found(self):
        save_worker = MagicMock()

        with patch('meniscus.data.model.worker_util.find_worker',
                   MagicMock(return_value=self.returned_worker)), \
                patch('meniscus.data.model.worker_util.save_worker',
                      save_worker):

            self.simulate_request(
                self.test_route,
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(self.worker))
            # self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_returns_400_bad_worker_status(self):
        with patch('meniscus.data.model.worker_util.find_worker',
                   MagicMock(return_value=self.worker)):
            self.simulate_request(
                self.test_route,
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(self.bad_worker_status))
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_when_load_average_is_negative_then_should_return_http_400(self):
        with patch('meniscus.data.model.worker_util.find_worker',
                   MagicMock(return_value=self.worker)):
            system_info = SystemInfo()
            system_info.load_average = {"1": -2, "15": -2, "5": -2}
            self.simulate_request(
                self.test_route,
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps({
                    'worker_status': {
                        'hostname': self.hostname,
                        'system_info': system_info.format(),
                        'status': self.status
                    }
                }))
            self.assertEqual(falcon.HTTP_400, self.srmock.status)


class WhenTestingWorkersStatus(unittest.TestCase):
    def setUp(self):
        self.req = MagicMock()
        self.resp = MagicMock()
        self.hostname = 'worker01'
        self.resource = WorkersStatusResource()
        self.worker = Worker(_id='010101',
                             hostname=self.hostname,
                             ip_address_v4='172.23.1.100',
                             ip_address_v6='::1',
                             personality='worker01',
                             status='online',
                             system_info={})

    def test_returns_200_on_get(self):
        with patch('meniscus.data.model.worker_util.retrieve_all_workers',
                   MagicMock(return_value=[self.worker])):
            self.resource.on_get(self.req, self.resp)
            self.assertEquals(self.resp.status, falcon.HTTP_200)
            resp = jsonutils.loads(self.resp.body)
            status = resp['status'][0]

        for key in resp.keys():
            self.assertTrue(key in self.worker.get_status().keys())


class WhenTestingWorkerStatus(unittest.TestCase):
    def setUp(self):
        self.req = MagicMock()
        self.resp = MagicMock()
        self.hostname = 'worker01'
        self.resource = WorkerStatusResource()
        self.worker = Worker(_id='010101',
                             hostname=self.hostname,
                             ip_address_v4='172.23.1.100',
                             ip_address_v6='::1',
                             personality='worker01',
                             status='online',
                             system_info={})
        self.hostname = 'worker01'
        self.worker_not_found = None

    def test_raises_worker_not_found(self):
        with patch('meniscus.data.model.worker_util.find_worker',
                   MagicMock(return_value=None)):
            with self.assertRaises(falcon.HTTPError):
                self.resource.on_get(self.req, self.resp, self.hostname)

    def test_returns_200_on_get(self):
        with patch('meniscus.data.model.worker_util.find_worker',
                   MagicMock(return_value=self.worker)):
            self.resource.on_get(self.req, self.resp, self.hostname)
            self.assertEquals(self.resp.status, falcon.HTTP_200)
            resp = jsonutils.loads(self.resp.body)
            status = resp['status']

            for key in resp.keys():
                self.assertTrue(key in self.worker.get_status().keys())


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = resources_test
import unittest

import falcon
import falcon.testing as testing
from mock import MagicMock
from mock import patch
with patch('meniscus.api.tenant.resources.tenant_util', MagicMock()):
    from meniscus.api.tenant.resources import EventProducerResource
    from meniscus.api.tenant.resources import EventProducersResource
    from meniscus.api.tenant.resources import MESSAGE_TOKEN
    from meniscus.api.tenant.resources import TenantResource
    from meniscus.api.tenant.resources import TokenResource
    from meniscus.api.tenant.resources import UserResource
from meniscus.data.model.tenant import EventProducer
from meniscus.data.model.tenant import Tenant
from meniscus.data.model.tenant import Token
from meniscus.openstack.common import jsonutils


def suite():

    test_suite = unittest.TestSuite()

    test_suite.addTest(TestingTenantResourceOnPost())

    test_suite.addTest(TestingUserResourceOnGet())
    test_suite.addTest(TestingUserResourceOnDelete())

    test_suite.addTest(TestingEventProducersResourceOnGet())
    test_suite.addTest(TestingEventProducersResourceOnPost())

    test_suite.addTest(TestingEventProducerResourceOnGet())
    test_suite.addTest(TestingEventProducerResourceOnPut())
    test_suite.addTest(TestingEventProducerResourceOnDelete())

    test_suite.addTest(TestingTokenResourceOnHead())
    test_suite.addTest(TestingTokenResourceOnGet())
    test_suite.addTest(TestingTokenResourceOnPost())

    return test_suite


class TenantApiTestBase(testing.TestBase):
    def before(self):
        self.db_handler = MagicMock()
        self.req = MagicMock()
        self.req.content_type = 'application/json'

        self.resp = MagicMock()
        self.producer_id = 432
        self.producer_name = 'producer1'
        self.producer_id_2 = 432
        self.producer_name_2 = 'producer2'
        self.not_valid_producer_id = 777
        self.producers = [
            EventProducer(self.producer_id, self.producer_name, 'syslog'),
            EventProducer(self.producer_id_2, self.producer_name_2, 'syslog')]
        self.token_original = 'ffe7104e-8d93-47dc-a49a-8fb0d39e5192'
        self.token_previous = 'bbd6302e-8d93-47dc-a49a-8fb0d39e5192'
        self.token_invalid = 'xxxyyy33-8d93-47dc-a49a-8fb0d39e5192'
        self.timestamp_original = "2013-03-19T18:16:48.411029Z"
        self.token = Token(self.token_original, self.token_previous,
                           self.timestamp_original)
        self.tenant_id = '1234'
        self.tenant_name = 'TenantName'
        self.tenant = Tenant(self.tenant_id, self.token,
                             event_producers=self.producers)
        self.tenant_not_found = MagicMock(return_value=None)
        self.tenant_found = MagicMock(return_value=self.tenant)

        self._set_resource()

    def _set_resource(self):
        pass


class TestingTenantResourceOnPost(TenantApiTestBase):
    def _set_resource(self):
        self.resource = TenantResource()
        self.test_route = '/v1/tenant'
        self.api.add_route(self.test_route, self.resource)

    def test_return_400_for_tenant_id_empty(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps({'tenant': {"tenant_id": ""}}))
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_tenant_name_empty(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps({'tenant': {"tenant_id": "123",
                                                 "tenant_name": ""}}))
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_tenant_not_provided(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps({'tenant': {"token": "1321316464646"}}))
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_tenant_exist(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps({'tenant': {"tenant_id": "1234"}}))
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_200_for_tenant_created(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found), patch(
                'meniscus.api.tenant.resources.tenant_util.create_tenant',
                MagicMock()):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps({'tenant': {"tenant_id": "1234"}}))
            self.assertEqual(falcon.HTTP_201, self.srmock.status)


class TestingUserResourceOnGet(TenantApiTestBase):
    def _set_resource(self):
        self.resource = UserResource()
        self.test_route = '/v1/tenant/{tenant_id}'
        self.api.add_route(self.test_route, self.resource)

    def test_return_404_for_tenant_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='GET')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_return_201_if_tenant_not_found_create_it(self):
        self.ds_handler_no_tenant = MagicMock()
        self.ds_handler_no_tenant.put = MagicMock()
        self.ds_handler_no_tenant.find_one.side_effect = [None, self.tenant]
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant'):
            self.simulate_request(
                self.test_route,
                method='GET')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_return_200_with_tenant_json(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='GET')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_should_return_tenant_json(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.resource.on_get(self.req, self.resp, self.tenant_id)

        parsed_body = jsonutils.loads(self.resp.body)

        self.assertTrue('tenant' in parsed_body)
        parsed_tenant = parsed_body['tenant']
        tenant_dict = self.tenant.format()
        for key in tenant_dict:
            self.assertTrue(key in parsed_tenant)
            self.assertEqual(tenant_dict[key], parsed_tenant[key])


class TestingEventProducersResourceOnGet(TenantApiTestBase):

    def _set_resource(self):
        self.resource = EventProducersResource()
        self.test_route = '/v1/tenant/{tenant_id}/producers'
        self.api.add_route(self.test_route, self.resource)

    def test_return_404_for_tenant_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='GET')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_should_return_200_on_get(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='GET')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_should_return_producer_json_on_get(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.resource.on_get(self.req, self.resp, self.tenant_id)

        parsed_body = jsonutils.loads(self.resp.body)

        self.assertTrue('event_producers'in parsed_body.keys())
        self.assertEqual(len(self.producers),
                         len(parsed_body['event_producers']))

        for producer in parsed_body['event_producers']:
            self.assertTrue(producer in [p.format() for p in self.producers])


class TestingEventProducersResourceOnPost(TenantApiTestBase):

    def _set_resource(self):
        self.resource = EventProducersResource()
        self.test_route = '/v1/tenant/{tenant_id}/producers'
        self.api.add_route(self.test_route, self.resource)

    def test_return_404_for_tenant_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': 'producer55',
                            'pattern': 'syslog'
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_return_400_for_name_empty(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': '',
                            'pattern': 'syslog'
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_name_not_provided(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'pattern': 'syslog'
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_pattern_empty(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': 'producer55',
                            'pattern': ''
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_pattern_not_provided(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': 'producer55'
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_pattern_not_provided(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': self.producer_name
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_bad_durable(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': self.producer_name,
                            'pattern': 'syslog',
                            'durable': "false"
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_bad_encrypted(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': self.producer_name,
                            'pattern': 'syslog',
                            'encrypted': "true"
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_bad_type_sink(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': 'producer55',
                            'pattern': 'syslog',
                            'sinks': 'true'
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_unsupported_and_supported_sink(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': 'producer55',
                            'pattern': 'syslog',
                            'sinks': ['mysql', 'elasticsearch']
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_duplicate_supported_sink(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': 'producer55',
                            'pattern': 'syslog',
                            'sinks': ['hdfs', 'hdfs']
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_201_for_one_supported_sink(self):
        save_tenant = MagicMock()
        create_event_producer = MagicMock()
        with patch(
                'meniscus.api.tenant.resources.tenant_util.find_tenant',
                self.tenant_found), \
            patch(
                'meniscus.api.tenant.resources.tenant_util.save_tenant',
                save_tenant), \
            patch(
                'meniscus.api.tenant.resources.'
                'tenant_util.create_event_producer',
                create_event_producer):

            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': 'producer55',
                            'pattern': 'syslog',
                            'sinks': ['elasticsearch']
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_return_201_for_multiple_supported_sink(self):
        save_tenant = MagicMock()
        create_event_producer = MagicMock()
        with patch(
                'meniscus.api.tenant.resources.tenant_util.find_tenant',
                self.tenant_found), \
            patch(
                'meniscus.api.tenant.resources.tenant_util.save_tenant',
                save_tenant), \
            patch(
                'meniscus.api.tenant.resources.'
                'tenant_util.create_event_producer',
                create_event_producer):

            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': 'producer55',
                            'pattern': 'syslog',
                            'sinks': ["elasticsearch", "hdfs"]
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_return_201_without_optional_fields(self):
        save_tenant = MagicMock()
        create_event_producer = MagicMock()
        with patch(
            'meniscus.api.tenant.resources.tenant_util.find_tenant',
            self.tenant_found), \
            patch(
                'meniscus.api.tenant.resources.tenant_util.save_tenant',
                save_tenant), \
            patch(
                'meniscus.api.tenant.resources.'
                'tenant_util.create_event_producer',
                create_event_producer):

            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': 'producer55',
                            'pattern': 'syslog'
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_return_201_with_optional_fields(self):
        save_tenant = MagicMock()
        create_event_producer = MagicMock()
        with patch(
                'meniscus.api.tenant.resources.tenant_util.find_tenant',
                self.tenant_found), \
            patch(
                'meniscus.api.tenant.resources.tenant_util.save_tenant',
                save_tenant), \
            patch(
                'meniscus.api.tenant.resources.'
                'tenant_util.create_event_producer',
                create_event_producer):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': 'producer55',
                            'pattern': 'syslog',
                            'durable': True,
                            'encrypted': False,
                            'sinks': ['elasticsearch']
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_201, self.srmock.status)


class TestingEventProducerResourceOnGet(TenantApiTestBase):

    def _set_resource(self):
        self.resource = EventProducerResource()
        self.test_route = '/v1/tenant/{tenant_id}' \
                          '/producers/{event_producer_id}'
        self.api.add_route(self.test_route, self.resource)

    def test_return_404_for_tenant_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='GET')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_return_404_for_producer_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.not_valid_producer_id
                ),
                method='GET')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_should_return_200_on_get(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.producer_id
                ),
                method='GET')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_should_return_producer_json(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.resource.on_get(self.req, self.resp, self.tenant_id,
                                 self.producer_id)

        parsed_body = jsonutils.loads(self.resp.body)
        parsed_producer = parsed_body['event_producer']
        producer_dict = [p.format() for p in self.producers
                         if p._id == self.producer_id][0]

        for key in producer_dict:
            self.assertEqual(producer_dict[key], parsed_producer[key])


class TestingEventProducerResourceOnPut(TenantApiTestBase):

    def _set_resource(self):
        self.resource = EventProducerResource()
        self.test_route = '/v1/tenant/{tenant_id}' \
                          '/producers/{event_producer_id}'
        self.api.add_route(self.test_route, self.resource)

    def test_return_404_for_tenant_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.producer_id
                ),
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': self.producer_name,
                            'pattern': 'syslog',
                            'encrypted': False,
                            'durable': False
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_return_400_for_name_not_provided(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.producer_id
                ),
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'pattern': 'syslog',
                            'encrypted': False,
                            'durable': False
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_name_empty(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.producer_id
                ),
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': '',
                            'pattern': 'syslog',
                            'encrypted': False,
                            'durable': False
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_pattern_not_provided(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.producer_id
                ),
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': self.producer_name,
                            'encrypted': False,
                            'durable': False
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_pattern_name_empty(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.producer_id
                ),
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': self.producer_name,
                            'pattern': '',
                            'encrypted': False,
                            'durable': False
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_404_producer_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.not_valid_producer_id
                ),
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': self.producer_name,
                            'pattern': 'syslog',
                            'encrypted': False,
                            'durable': False
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_return_400_producer_name_change_name_already_taken(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.producer_id
                ),
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': self.producer_name_2,
                            'pattern': 'syslog',
                            'encrypted': False,
                            'durable': False
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_200_producer_updated(self):
        save_tenant = MagicMock()
        with patch(
                'meniscus.api.tenant.resources.tenant_util.find_tenant',
                self.tenant_found), \
                patch(
                    'meniscus.api.tenant.resources.tenant_util.save_tenant',
                    save_tenant):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.producer_id
                ),
                method='PUT',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'event_producer': {
                            'name': self.producer_name,
                            'pattern': 'syslog',
                            'encrypted': False,
                            'durable': False
                        }
                    }
                )
            )
            self.assertEqual(falcon.HTTP_200, self.srmock.status)


class TestingEventProducerResourceOnDelete(TenantApiTestBase):

    def _set_resource(self):
        self.resource = EventProducerResource()
        self.test_route = '/v1/tenant/{tenant_id}' \
                          '/producers/{event_producer_id}'
        self.api.add_route(self.test_route, self.resource)

    def test_return_404_for_tenant_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='DELETE')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_return_404_for_producer_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.not_valid_producer_id
                ),
                method='DELETE')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_should_return_200_on_get(self):
        mock_tenant_util = MagicMock()
        mock_tenant_util.find_tenant.return_value = self.tenant_found

        with patch('meniscus.api.tenant.resources.tenant_util',
                   mock_tenant_util):
            self.simulate_request(
                '/v1/tenant/{tenant_id}/producers/{event_producer_id}'.format(
                    tenant_id=self.tenant_id,
                    event_producer_id=self.producer_id
                ),
                method='DELETE')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)


class TestingTokenResourceOnHead(TenantApiTestBase):

    def _set_resource(self):
        self.resource = TokenResource()
        self.test_route = '/v1/tenant/{tenant_id}/token'
        self.api.add_route(self.test_route, self.resource)

    def test_return_404_for_tenant_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='HEAD',
                headers={MESSAGE_TOKEN: self.token_original})
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_return_404_for_invalid_token(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='HEAD',
                headers={MESSAGE_TOKEN: self.token_invalid})
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_return_200_valid_token(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='HEAD',
                headers={MESSAGE_TOKEN: self.token_original})
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_should_return_200_previous_token(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='HEAD',
                headers={MESSAGE_TOKEN: self.token_previous})
            self.assertEqual(falcon.HTTP_200, self.srmock.status)


class TestingTokenResourceOnGet(TenantApiTestBase):

    def _set_resource(self):
        self.resource = TokenResource()
        self.test_route = '/v1/tenant/{tenant_id}/token'
        self.api.add_route(self.test_route, self.resource)

    def test_return_404_for_tenant_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='GET',
                headers={MESSAGE_TOKEN: self.token_original})
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_should_return_200_on_get(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route.format(
                    tenant_id=self.tenant_id
                ),
                method='GET')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_should_return_token_json(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.resource.on_get(self.req, self.resp, self.tenant_id)

        parsed_body = jsonutils.loads(self.resp.body)
        parsed_token = parsed_body['token']
        token_dict = self.token.format()
        for key in token_dict:
            self.assertEqual(parsed_token[key], token_dict[key])


class TestingTokenResourceOnPost(TenantApiTestBase):

    def _set_resource(self):
        self.resource = TokenResource()
        self.test_route = '/v1/tenant/{tenant_id}/token'
        self.api.add_route(self.test_route, self.resource)

    def test_return_404_for_tenant_not_found(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_not_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'token': {
                            'invalidate_now': False
                        }
                    }
                ))
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_return_400_for_invalidate_now_not_provided(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'token': {
                        }
                    }
                ))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_400_for_invalidate_now_not_boolean(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'token': {
                            'invalidate_now': "true"
                        }
                    }
                ))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_return_203_for_invalidate_now(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found), patch(
                'meniscus.api.tenant.resources.tenant_util.save_tenant',
                MagicMock()):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'token': {
                            'invalidate_now': True
                        }
                    }
                ))
        self.assertEqual(falcon.HTTP_203, self.srmock.status)
        self.assertNotEqual(self.tenant.token.valid, self.token_original)
        self.assertEqual(self.tenant.token.previous, None)
        self.assertGreater(self.tenant.token.last_changed,
                           self.timestamp_original)

    def test_return_203_for_invalidate_now_false(self):
        with patch('meniscus.api.tenant.resources.tenant_util.find_tenant',
                   self.tenant_found), patch(
                'meniscus.api.tenant.resources.tenant_util.save_tenant',
                MagicMock()):
            self.simulate_request(
                self.test_route,
                method='POST',
                headers={'content-type': 'application/json'},
                body=jsonutils.dumps(
                    {
                        'token': {
                            'invalidate_now': False
                        }
                    }
                ))
        self.assertEqual(falcon.HTTP_203, self.srmock.status)
        self.assertNotEqual(self.tenant.token.valid, self.token_original)
        self.assertEqual(self.tenant.token.previous, self.token_original)
        self.assertGreater(self.tenant.token.last_changed,
                           self.timestamp_original)


class TestingTokenResourceValidation(TenantApiTestBase):

    def _set_resource(self):
        self.resource = TokenResource()

    def test_iso_timestamp_format_should_throw_exception_for_time_limit(self):
        bad_time_format = "2013-03-19"
        new_token = Token('ffe7104e-8d93-47dc-a49a-8fb0d39e5192',
                          None, bad_time_format)
        self.assertRaises(
            ValueError,
            self.resource._validate_token_min_time_limit_reached,
            new_token)

    def test_should_throw_exception_for_time_limit_not_reached(self):
        new_token = Token()
        self.assertRaises(
            falcon.HTTPError,
            self.resource._validate_token_min_time_limit_reached,
            new_token)

    def test_should_not_throw_exception_for_time_limit(self):
        self.assertTrue(
            self.resource._validate_token_min_time_limit_reached(self.token))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = request_test
from meniscus.api.utils.request import http_request
from meniscus.api.utils.request import HTTP_VERBS

from mock import MagicMock
from mock import patch

from httpretty import HTTPretty
from httpretty import httprettified

import falcon
import requests
import unittest


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingUtilsRequest())
    return suite


class WhenTestingUtilsRequest(unittest.TestCase):

    def setUp(self):
        self.requests = MagicMock()
        self.url = 'http://localhost:8080/somewhere'
        self.json_payload = u'{}'

    @httprettified
    def test_should_raise_value_error(self):
        HTTPretty.register_uri(HTTPretty.PATCH, self.url,
                               body=self.json_payload,
                               content_type="application/json")

        with self.assertRaises(ValueError):
            http_request(self.url, json_payload=self.json_payload,
                         http_verb='PATCH')

    @httprettified
    def test_should_return_http_200_on_all_http_verbs(self):
        httpretty_verbs = {
            'POST': HTTPretty.POST,
            'GET': HTTPretty.GET,
            'DELETE': HTTPretty.DELETE,
            'PUT': HTTPretty.PUT,
            'HEAD': HTTPretty.HEAD,
        }

        for http_verb in HTTP_VERBS:
            HTTPretty.register_uri(httpretty_verbs[http_verb],
                                   self.url,
                                   body=self.json_payload,
                                   content_type="application/json",
                                   status=200)
            self.assertTrue(http_request(self.url,
                                         json_payload=self.json_payload,
                                         http_verb=http_verb),
                            falcon.HTTP_200)

    def test_should_cause_a_connection_exception(self):
        with patch.object(requests, 'get') as mock_method:
            with self.assertRaises(requests.ConnectionError):
                mock_method.side_effect = requests.ConnectionError
                http_request(self.url, json_payload=self.json_payload)

    def test_should_cause_a_http_exception(self):
        with patch.object(requests, 'get') as mock_method:
            with self.assertRaises(requests.HTTPError):
                mock_method.side_effect = requests.HTTPError
                http_request(self.url, json_payload=self.json_payload)

    def test_should_cause_a_request_exception(self):
        with patch.object(requests, 'get') as mock_method:
            with self.assertRaises(requests.RequestException):
                mock_method.side_effect = requests.RequestException
                http_request(self.url, json_payload=self.json_payload)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = sys_assist_test
import unittest
import meniscus.api.utils.sys_assist as sys_assist
from mock import MagicMock
from mock import patch
import __builtin__


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingSysAssist())
    return suite


class WhenTestingSysAssist(unittest.TestCase):
    def setUp(self):
        self.conf = MagicMock()
        self.conf.network_interface.default_ifname = 'eth1'
        self.get_config = MagicMock(return_value=self.conf)

        self.platform = 'linux'
        self.meminfo = ["MemTotal:        4196354 kB\n",
                        "MemFree:         1232352 kB\n",
                        "Buffers:          151176 kB\n"]
        self.statvfs = MagicMock()
        self.statvfs.f_blocks = 26214400
        self.statvfs.f_frsize = 4096

    def test_get_sys_mem_total_kB_should_return_4196354(self):
        with patch.object(sys_assist.sys, 'platform', self.platform), \
                patch.object(__builtin__, 'open', return_value=self.meminfo):
            mem_total = sys_assist.get_sys_mem_total_kB()
            self.assertEqual(mem_total, 4196354)

    def test_get_sys_mem_total_MB_should_return_4098(self):
        with patch.object(sys_assist.sys, 'platform', self.platform), \
                patch.object(__builtin__, 'open', return_value=self.meminfo):
            mem_total = sys_assist.get_sys_mem_total_MB()
            self.assertEqual(mem_total, 4098)

    def test_get_disk_size_GB_should_return_100(self):
        with patch.object(sys_assist.sys, 'platform', self.platform), \
                patch.object(sys_assist.os, 'statvfs',
                             return_value=self.statvfs):
            mem_total = sys_assist.get_disk_size_GB()
            self.assertEqual(mem_total, 100)

    def test_get_cpu_core_count_should_return_4(self):
        with patch.object(sys_assist.multiprocessing, 'cpu_count',
                          return_value=4):
            cpu_count = sys_assist.get_cpu_core_count()
            self.assertEqual(cpu_count, 4)

    def test_get_interface_ip(self):
        with patch.object(sys_assist.socket, 'socket',
                          MagicMock()), \
            patch.object(sys_assist.fcntl, 'ioctl',
                         MagicMock()), \
            patch.object(sys_assist.socket, 'inet_ntoa',
                         return_value='10.6.60.95'):
            ip = sys_assist.get_interface_ip('etho0')
            self.assertEqual(ip, '10.6.60.95')

    def test_get_interface_ip_should_return_external_ip(self):
        with patch.object(sys_assist, 'get_interface_ip',
                          return_value='10.6.60.99'), \
            patch.object(sys_assist.socket, 'gethostbyname',
                         return_value='127.0.0.1'):
            ip = sys_assist.get_interface_ip()
            self.assertEqual(ip, '10.6.60.99')

    def test_get_lan_ip_should_return_localhost(self):
        with patch.object(sys_assist.socket, 'gethostbyname',
                          return_value='127.0.0.1'):
            ip = sys_assist.get_interface_ip('ABC9')
            self.assertEqual(ip, '127.0.0.1')

    def test_get_load_avergae(self):
        ave = sys_assist.get_load_average()
        self.assertTrue('1'in ave)
        self.assertTrue('5'in ave)
        self.assertTrue('15'in ave)

    def test_get_disk_usage__(self):
        output = ('Filesystem      Size  Used Avail Use% Mounted on\n'
                  '/dev/sda5        24G  5.2G   18G  24% /\n'
                  'udev            7.8G  4.0K  7.8G   1% /dev\n'
                  'tmpfs           3.2G  892K  3.2G   1% /run\n'
                  'none            5.0M     0  5.0M   0% /run/lock\n'
                  '/dev/sda4       7.8G  164K  7.8G   1% /run/shm\n'
                  '/dev/sda6       255G  434M  209G  14% /home')
        df = MagicMock()
        df.communicate.return_value = [output]
        with patch.object(sys_assist.sys, 'platform', self.platform), \
                patch.object(sys_assist.subprocess, 'Popen', return_value=df):
            usage = sys_assist.get_disk_usage()

        sda4 = {
            'device': '/dev/sda4',
            'total': 7.8,
            'used': 0.000156402587890625
        }
        self.assertTrue(sda4 in usage)
        sda5 = {
            'device': '/dev/sda5',
            'total': 24.0,
            'used': 5.2
        }
        self.assertTrue(sda5 in usage)
        sda6 = {
            'device': '/dev/sda6',
            'total': 255.0,
            'used': 0.423828125
        }
        self.assertTrue(sda6 in usage)
        sda4 = {
            'device': '/dev/sda4',
            'total': 7.8,
            'used': 0.000156402587890625
        }
        self.assertTrue(sda4 in usage)
        sda4 = {
            'device': '/dev/sda4',
            'total': 7.8,
            'used': 0.000156402587890625
        }
        self.assertTrue(sda4 in usage)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = resources_test
import unittest
from mock import MagicMock

import falcon

from meniscus.api.version.resources import VersionResource
from meniscus.openstack.common import jsonutils


def suite():
    test_suite = unittest.TestSuite()
    suite.addTest(WhenTestingVersionResource())
    return test_suite


class WhenTestingVersionResource(unittest.TestCase):

    def setUp(self):
        self.req = MagicMock()
        self.resp = MagicMock()
        self.resource = VersionResource()

    def test_should_return_200_on_get(self):
        self.resource.on_get(self.req, self.resp)
        self.assertEqual(falcon.HTTP_200, self.resp.status)

    def test_should_return_version_json(self):
        self.resource.on_get(self.req, self.resp)
        parsed_body = jsonutils.loads(self.resp.body)
        self.assertTrue('v1' in parsed_body)
        self.assertEqual('current', parsed_body['v1'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = config_test
import os
import unittest

from oslo.config import cfg
from meniscus.config import init_config, get_config


# Configuration test configuration options
test_group = cfg.OptGroup(name='test', title='Configuration Test')

CFG_TEST_OPTIONS = [
    cfg.BoolOpt('should_pass',
                default=False,
                help="""Example option to make sure configuration
                        loading passes test.
                     """
                )
]


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenConfiguring())

    return suite


class WhenConfiguring(unittest.TestCase):

    def test_loading(self):
        try:
            init_config(['--config-file',
                         '../pkg/layout/etc/meniscus/meniscus.conf'])
        except:
            print('ass {}'.format(os.getcwd()))
            init_config(['--config-file',
                         './pkg/layout/etc/meniscus/meniscus.conf'])

        conf = get_config()
        conf.register_group(test_group)
        conf.register_opts(CFG_TEST_OPTIONS, group=test_group)

        self.assertTrue(conf.test.should_pass)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = correlator_test
import httplib
import unittest

from mock import MagicMock
from mock import patch
import requests
from meniscus.correlation import correlator

from meniscus.correlation import errors
from meniscus.data.model.tenant import EventProducer
from meniscus.data.model.tenant import Tenant
from meniscus.data.model.tenant import Token
from meniscus.data.model.worker import WorkerConfiguration


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingCorrelationPipeline())
    return suite


class WhenTestingCorrelationPipeline(unittest.TestCase):
    def setUp(self):
        self.tenant_id = '5164b8f4-16fb-4376-9d29-8a6cbaa02fa9'
        self.message_token = 'ffe7104e-8d93-47dc-a49a-8fb0d39e5192'
        self.producers = [
            EventProducer(432, 'producer1', 'syslog', durable=True),
            EventProducer(433, 'producer2', 'syslog', durable=False)
        ]
        self.invalid_message_token = 'yyy7104e-8d93-47dc-a49a-8fb0d39e5192'
        self.token = Token('ffe7104e-8d93-47dc-a49a-8fb0d39e5192',
                           'bbd6302e-8d93-47dc-a49a-8fb0d39e5192',
                           '2013-03-19T18:16:48.411029Z')
        self.tenant = Tenant(self.tenant_id, self.token,
                             event_producers=self.producers)
        self.get_token = MagicMock(return_value=self.token)
        self.get_tenant = MagicMock(return_value=self.tenant)
        self.get_none = MagicMock(return_value=None)
        self.src_msg = {
            'HOST': 'tohru',
            '_SDATA': {
                'meniscus': {
                    'token': self.message_token,
                    'tenant': self.tenant_id
                }
            },
            'PRIORITY': 'info',
            'MESSAGE': '127.0.0.1 - - [12/Jul/2013:19:40:58 +0000] '
                       '\'GET /test.html HTTP/1.1\' 404 466 \'-\' '
                       '\'curl/7.29.0\'',
            'FACILITY': 'local1',
            'MSGID': '345',
            'ISODATE': '2013-07-12T14:17:00+00:00',
            'PROGRAM': 'apache',
            'DATE': '2013-07-12T14:17:00.134+00:00',
            'PID': '234'
        }
        self.malformed_sys_msg = {
            'HOST': 'tohru',
            '_SDATA': {
                'meniscus': {
                    'token': '',
                    'tenant': ''
                }
            },
            'PRIORITY': 'info',
            'MESSAGE': '127.0.0.1 - - [12/Jul/2013:19:40:58 +0000] '
                       '\'GET /test.html HTTP/1.1\' 404 466 \'-\' '
                       '\'curl/7.29.0\'',
            'FACILITY': 'local1',
            'MSGID': '345',
            'ISODATE': '2013-07-12T14:17:00+00:00',
            'PROGRAM': 'apache',
            'DATE': '2013-07-12T14:17:00.134+00:00',
            'PID': '234'
        }
        self.cee_msg = {
            'host': 'tohru',
            'pri': 'info',
            'msg': '127.0.0.1 - - [12/Jul/2013:19:40:58 +0000] '
                   '\'GET /test.html HTTP/1.1\' 404 466 \'-\' '
                   '\'curl/7.29.0\'',
            'msgid': '345',
            'time': '2013-07-12T14:17:00+00:00',
            'pname': 'apache',
            'pid': '234',
            'ver': '1',
            'native': {'meniscus': {
                'token': 'ffe7104e-8d93-47dc-a49a-8fb0d39e5192',
                'tenant': '5164b8f4-16fb-4376-9d29-8a6cbaa02fa9'}}
        }
        self.config = WorkerConfiguration(
            personality='worker',
            hostname='worker01',
            coordinator_uri='http://192.168.1.2/v1')
        self.get_config = MagicMock(return_value=self.config)
        self.tenant_found = MagicMock(return_value=self.tenant)

    def test_correlate_syslog_message_exception(self):
        http_request = MagicMock(side_effect=requests.RequestException)

        with patch.object(correlator, '_get_config_from_cache',
                          self.get_config), \
            patch('meniscus.correlation.correlator.http_request',
                  http_request):

            with self.assertRaises(errors.CoordinatorCommunicationError):
                correlator.correlate_syslog_message(self.src_msg)

    def test_correlate_syslog_message_success(self):
        http_request = MagicMock(side_effect=requests.RequestException)

        with patch.object(correlator, '_get_config_from_cache',
                          self.get_config), \
                patch('meniscus.correlation.correlator.http_request',
                      http_request):

            with self.assertRaises(errors.CoordinatorCommunicationError):
                correlator.correlate_http_message(self.tenant_id,
                                                  self.message_token,
                                                  self.src_msg)

    def test_format_message_cee_message_failure_empty_string(self):
        with self.assertRaises(errors.MessageValidationError):
            correlator.correlate_syslog_message({})

    def test_format_message_cee_message(self):
        _validate_token_from_cache_func = MagicMock()
        with patch('meniscus.correlation.correlator.'
                   '_validate_token_from_cache',
                   _validate_token_from_cache_func):

            correlator._format_message_cee(self.src_msg)
            _validate_token_from_cache_func.assert_called_once_with(
                self.tenant_id, self.message_token, self.cee_msg)

    # Tests for _validate_token_from_cache
    def test_validate_token_from_cache_throws_auth_exception_from_cache(self):
        with patch.object(correlator.cache_handler.TokenCache, 'get_token',
                          self.get_token):
            with self.assertRaises(errors.MessageAuthenticationError):
                correlator._validate_token_from_cache(
                    self.tenant_id, self.invalid_message_token, self.src_msg)

    def test_validate_token_from_cache_calls_get_tenant_from_cache(self):
        get_tenant_from_cache_func = MagicMock()
        with patch.object(correlator.cache_handler.TokenCache, 'get_token',
                          self.get_token), \
            patch('meniscus.correlation.correlator._get_tenant_from_cache',
                  get_tenant_from_cache_func):

            correlator._validate_token_from_cache(
                self.tenant_id, self.message_token, self.src_msg)
            get_tenant_from_cache_func.assert_called_once_with(
                self.tenant_id, self.message_token, self.src_msg)

    def test_validate_token_from_cache_calls_validate_token_coordinator(self):
        validate_token_from_coordinator_func = MagicMock()
        with patch.object(correlator.cache_handler.TokenCache, 'get_token',
                          self.get_none), \
                patch('meniscus.correlation.correlator.'
                      '_validate_token_with_coordinator',
                      validate_token_from_coordinator_func):

            correlator._validate_token_from_cache(
                self.tenant_id, self.message_token, self.src_msg)
            validate_token_from_coordinator_func.assert_called_once_with(
                self.tenant_id, self.message_token, self.src_msg)

    # Tests for _get_tenant_from_cache
    def test_get_tenant_from_cache_calls_get_tenant_from_coordinator(self):
        get_tenant_from_coordinator_func = MagicMock()
        with patch.object(correlator.cache_handler.TenantCache, 'get_tenant',
                          self.get_none), \
                patch('meniscus.correlation.correlator.'
                      '_get_tenant_from_coordinator',
                      get_tenant_from_coordinator_func):

            correlator._get_tenant_from_cache(self.tenant_id,
                                              self.message_token,
                                              self.src_msg)
            get_tenant_from_coordinator_func.assert_called_once_with(
                self.tenant_id, self.message_token, self.src_msg)

    def test_get_tenant_from_cache_calls_add_correlation_info_to_message(self):
        add_correlation_info_to_message_func = MagicMock()
        with patch.object(correlator.cache_handler.TenantCache, 'get_tenant',
                          self.get_tenant), \
                patch('meniscus.correlation.correlator.'
                      '_add_correlation_info_to_message',
                      add_correlation_info_to_message_func):

            correlator._get_tenant_from_cache(self.tenant_id,
                                              self.message_token,
                                              self.src_msg)
            add_correlation_info_to_message_func.assert_called_once_with(
                self.tenant, self.src_msg)

    # Tests for _validate_token_with_coordinator
    def test_validate_token_with_coordinator_throws_communication_error(self):
        http_request = MagicMock(side_effect=requests.RequestException)

        with patch.object(correlator, '_get_config_from_cache',
                          self.get_config),\
            patch('meniscus.correlation.correlator.http_request',
                  http_request):

            with self.assertRaises(errors.CoordinatorCommunicationError):
                correlator._validate_token_with_coordinator(
                    self.tenant_id, self.message_token, self.src_msg)

    def test_validate_token_with_coordinator_throws_auth_error(self):
        response = MagicMock()
        response.status_code = httplib.NOT_FOUND
        http_request = MagicMock(return_value=response)

        with patch.object(correlator, '_get_config_from_cache',
                          self.get_config), \
                patch('meniscus.correlation.correlator.http_request',
                      http_request):

            with self.assertRaises(errors.MessageAuthenticationError):
                correlator._validate_token_with_coordinator(
                    self.tenant_id, self.invalid_message_token, self.src_msg)

    def test_validate_token_with_coordinator_calls_get_tenant(self):
        response = MagicMock()
        response.status_code = httplib.OK
        http_request = MagicMock(return_value=response)
        get_tenant_from_coordinator_func = MagicMock()
        with patch.object(correlator, '_get_config_from_cache',
                          self.get_config), \
            patch('meniscus.correlation.correlator.http_request',
                  http_request),\
            patch('meniscus.correlation.correlator.'
                  '_get_tenant_from_coordinator',
                  get_tenant_from_coordinator_func):
            correlator._validate_token_with_coordinator(self.tenant_id,
                                                        self.message_token,
                                                        self.src_msg)
        get_tenant_from_coordinator_func.assert_called_once_with(
            self.tenant_id, self.message_token, self.src_msg)

    # Tests for _get_tenant_from_coordinator
    def test_get_tenant_from_coordinator_throws_communication_error(self):
        http_request = MagicMock(
            side_effect=requests.RequestException)

        with patch.object(correlator, '_get_config_from_cache',
                          self.get_config), \
                patch('meniscus.correlation.correlator.http_request',
                      http_request):

            with self.assertRaises(errors.CoordinatorCommunicationError):
                correlator._get_tenant_from_coordinator(self.tenant_id,
                                                        self.message_token,
                                                        self.src_msg)

    def test_get_tenant_from_coordinator_throws_auth_error(self):
        response = MagicMock()
        response.status_code = httplib.NOT_FOUND
        http_request = MagicMock(return_value=response)

        with patch.object(correlator, '_get_config_from_cache',
                          self.get_config), \
                patch('meniscus.correlation.correlator.http_request',
                      http_request):

            with self.assertRaises(errors.ResourceNotFoundError):
                correlator._get_tenant_from_coordinator(
                    self.tenant_id, self.invalid_message_token, self.src_msg)

    def test_get_tenant_from_coordinator_throws_resource_not_found_error(self):
        response = MagicMock()
        response.status_code = httplib.BAD_REQUEST
        http_request = MagicMock(return_value=response)

        with patch.object(correlator, '_get_config_from_cache',
                          self.get_config), \
                patch('meniscus.correlation.correlator.http_request',
                      http_request):

            with self.assertRaises(errors.CoordinatorCommunicationError):
                correlator._get_tenant_from_coordinator(
                    self.tenant_id, self.invalid_message_token, self.src_msg)

    def test_get_tenant_from_coordinator_calls_get_tenant(self):
        response = MagicMock()
        response.status_code = httplib.OK
        http_request = MagicMock(return_value=response)
        add_correlation_info_to_message_func = MagicMock()
        with patch.object(correlator, '_get_config_from_cache',
                          self.get_config), \
                patch('meniscus.correlation.correlator.http_request',
                      http_request), \
                patch('meniscus.correlation.correlator.tenant_util.'
                      'load_tenant_from_dict',
                      self.tenant_found), \
                patch('meniscus.correlation.correlator.'
                      '_add_correlation_info_to_message',
                      add_correlation_info_to_message_func):
            correlator._get_tenant_from_coordinator(self.tenant_id,
                                                    self.message_token,
                                                    self.src_msg)
        add_correlation_info_to_message_func.assert_called_once_with(
            self.tenant, self.src_msg)

    #Tests for _add_correlation_info_to_message
    def test_add_correlation_info_to_message(self):
        route_message_func = MagicMock()
        with patch('meniscus.correlation.correlator.sinks.route_message',
                   route_message_func):
            correlator._add_correlation_info_to_message(
                self.tenant, self.cee_msg)
        route_message_func.assert_called_once_with(self.cee_msg)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = receiver_test
import unittest
import json

from mock import MagicMock
from mock import patch

from meniscus import env
from meniscus.correlation import receiver

_LOG = env.get_logger(__name__)


class WhenTestingCorrelationInputServer(unittest.TestCase):
    def setUp(self):
        self.conf = MagicMock()
        self.conf.worker_id = '12345'
        self.tenant_id = '5164b8f4-16fb-4376-9d29-8a6cbaa02fa9'
        self.token = '87324559-33aa-4534-bfd1-036472a32f2e'
        self.src_msg = {
            "profile": "http://projectmeniscus.org/cee/profiles/base",
            "version": "1",
            "messageid": "-",
            "priority": "46",
            "processid": "-",
            "hostname": "tohru",
            "appname": "rsyslogd",
            "timestamp": "2013-04-02T14:12:04.873490-05:00",
            "message": "start",
            "sd": {
                "meniscus": {
                    "tenant": "5164b8f4-16fb-4376-9d29-8a6cbaa02fa9",
                    "token": "87324559-33aa-4534-bfd1-036472a32f2e"
                }
            },
            "native": {
                "origin": {
                    "x-info": "http://www.rsyslog.com",
                    "swVersion": "7.2.5",
                    "x-pid": "12662",
                    "software": "rsyslogd"
                }
            }
        }
        self.correlated_message = {
            "profile": "http://projectmeniscus.org/cee/profiles/base",
            "ver": "1",
            "msgid": "-",
            "pri": "46",
            "pid": "-",
            "meniscus": {
                "tenant": "5164b8f4-16fb-4376-9d29-8a6cbaa02fa9",
                "correlation": {
                    "host_id": "1",
                    "durable": False,
                    "ep_id": None,
                    "pattern": None,
                    "encrypted": False
                }
            },
            "host": "tohru",
            "pname": "rsyslogd",
            "time": "2013-04-02T14:12:04.873490-05:00",
            "msg": "start",
            "native": {
                "origin": {
                    "x-info": "http://www.rsyslog.com",
                    "swVersion": "7.2.5",
                    "x-pid": "12662",
                    "software": "rsyslogd"
                }
            }
        }
        zmq_receiver = MagicMock()
        zmq_receiver.get.return_value = json.dumps(self.src_msg)
        self.server = receiver.CorrelationInputServer(zmq_receiver)

    def test_process_msg(self):
        correlate_func = MagicMock()
        with patch('meniscus.correlation.correlator.'
                   'correlate_syslog_message', correlate_func):
            self.server.process_msg()
            correlate_func.assert_called_once()

    def test_new_correlation_input_server(self):
        server = receiver.new_correlation_input_server()
        self.assertIsInstance(server, receiver.CorrelationInputServer)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = cache_handler_test
import unittest

from mock import MagicMock
from mock import patch

from meniscus.data.cache_handler import Cache
from meniscus.data.cache_handler import CACHE_CONFIG
from meniscus.data.cache_handler import CACHE_TENANT
from meniscus.data.cache_handler import CACHE_TOKEN
from meniscus.data.cache_handler import ConfigCache
from meniscus.data.cache_handler import CONFIG_EXPIRES
from meniscus.data.cache_handler import DEFAULT_EXPIRES
from meniscus.data.cache_handler import TenantCache
from meniscus.data.cache_handler import TokenCache
from meniscus.data.cache_handler import NativeProxy
from meniscus.data.model.tenant import Tenant
from meniscus.data.model.tenant import Token
from meniscus.data.model.worker import WorkerConfiguration
from meniscus.openstack.common import jsonutils


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingBaseCache())
    suite.addTest(WhenTestingConfigCache())
    suite.addTest(WhenTestingTenantCache())
    return suite


class WhenTestingBaseCache(unittest.TestCase):
    def test_cache_raises_not_implemented(self):
        cache = Cache()
        with self.assertRaises(NotImplementedError):
            cache.clear()


class WhenTestingConfigCache(unittest.TestCase):
    def setUp(self):
        self.cache_clear = MagicMock()
        self.cache_true = MagicMock(return_value=True)
        self.cache_false = MagicMock(return_value=False)
        self.cache_update = MagicMock()
        self.cache_set = MagicMock()
        self.cache_del = MagicMock()
        self.config = WorkerConfiguration(
            personality='worker',
            hostname='worker01',
            coordinator_uri='http://192.168.1.2/v1')
        self.config_json = jsonutils.dumps(self.config.format())
        self.cache_get_config = MagicMock(return_value=self.config_json)

    def test_clear_calls_cache_clear(self):
        with patch.object(NativeProxy, 'cache_clear', self.cache_clear):
            config_cache = ConfigCache()
            config_cache.clear()
        self.cache_clear.assert_called_once_with(CACHE_CONFIG)

    def test_set_config_calls_cache_update(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_true
        ), patch.object(NativeProxy, 'cache_update', self.cache_update):
            config_cache = ConfigCache()
            config_cache.set_config(self.config)

        self.cache_update.assert_called_once_with(
            'worker_configuration', jsonutils.dumps(self.config.format()),
            CONFIG_EXPIRES, CACHE_CONFIG)

    def test_set_config_calls_cache_set(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_false
        ), patch.object(NativeProxy, 'cache_set', self.cache_set):
            config_cache = ConfigCache()
            config_cache.set_config(self.config)

        self.cache_set.assert_called_once_with(
            'worker_configuration', jsonutils.dumps(self.config.format()),
            CONFIG_EXPIRES, CACHE_CONFIG)

    def test_get_config_calls_returns_config(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_true
        ), patch.object(NativeProxy, 'cache_get',  self.cache_get_config):
            config_cache = ConfigCache()
            config = config_cache.get_config()

        self.cache_get_config.assert_called_once_with(
            'worker_configuration', CACHE_CONFIG)
        self.assertIsInstance(config, WorkerConfiguration)

    def test_get_config_calls_returns_none(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_false):
            config_cache = ConfigCache()
            config = config_cache.get_config()

        self.assertIs(config, None)

    def test_delete_config_calls_cache_del(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_true
        ), patch.object(NativeProxy, 'cache_del', self.cache_del):
            config_cache = ConfigCache()
            config_cache.delete_config()

        self.cache_del.assert_called_once_with(
            'worker_configuration', CACHE_CONFIG)

    def test_delete_config_does_not_call_cache_del(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_false
        ), patch.object(NativeProxy, 'cache_del', self.cache_del):
            config_cache = ConfigCache()
            config_cache.delete_config()

        with self.assertRaises(AssertionError):
            self.cache_del.assert_called_once_with(
                'worker_configuration', CACHE_CONFIG)


class WhenTestingTenantCache(unittest.TestCase):
    def setUp(self):
        self.cache_clear = MagicMock()
        self.cache_true = MagicMock(return_value=True)
        self.cache_false = MagicMock(return_value=False)
        self.cache_update = MagicMock()
        self.cache_set = MagicMock()
        self.cache_del = MagicMock()
        self.tenant_id = '101'
        self.tenant = Tenant(
            tenant_id=self.tenant_id,
            token=Token()
        )
        self.tenant_json = jsonutils.dumps(self.tenant.format())
        self.cache_get_tenant = MagicMock(return_value=self.tenant_json)

    def test_clear_calls_cache_clear(self):
        with patch.object(NativeProxy, 'cache_clear', self.cache_clear):
            tenant_cache = TenantCache()
            tenant_cache.clear()
        self.cache_clear.assert_called_once_with(CACHE_TENANT)

    def test_set_tenant_calls_cache_update(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_true
        ), patch.object(NativeProxy, 'cache_update', self.cache_update):
            tenant_cache = TenantCache()
            tenant_cache.set_tenant(self.tenant)

        self.cache_update.assert_called_once_with(
            self.tenant_id, jsonutils.dumps(self.tenant.format()),
            DEFAULT_EXPIRES, CACHE_TENANT)

    def test_set_tenant_calls_cache_set(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_false
        ), patch.object(NativeProxy, 'cache_set', self.cache_set):
            tenant_cache = TenantCache()
            tenant_cache.set_tenant(self.tenant)

        self.cache_set.assert_called_once_with(
            self.tenant_id, jsonutils.dumps(self.tenant.format()),
            DEFAULT_EXPIRES, CACHE_TENANT)

    def test_get_tenant_calls_returns_tenant(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_true
        ), patch.object(NativeProxy, 'cache_get',  self.cache_get_tenant):
            tenant_cache = TenantCache()
            tenant = tenant_cache.get_tenant(self.tenant_id)

        self.cache_get_tenant.assert_called_once_with(
            self.tenant_id, CACHE_TENANT)
        self.assertIsInstance(tenant, Tenant)

    def test_get_tenant_calls_returns_none(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_false):
            tenant_cache = TenantCache()
            tenant = tenant_cache.get_tenant(self.tenant_id)

        self.assertIs(tenant, None)

    def test_delete_tenant_calls_cache_del(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_true
        ), patch.object(NativeProxy, 'cache_del', self.cache_del):
            tenant_cache = TenantCache()
            tenant_cache.delete_tenant(self.tenant_id)

        self.cache_del.assert_called_once_with(
            self.tenant_id, CACHE_TENANT)

    def test_delete_tenant_does_not_call_cache_del(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_false
        ), patch.object(NativeProxy, 'cache_del', self.cache_del):
            tenant_cache = TenantCache()
            tenant_cache.delete_tenant(self.tenant_id)

        with self.assertRaises(AssertionError):
            self.cache_del.assert_called_once_with(
                self.tenant_id, CACHE_TENANT)


class WhenTestingTokenCache(unittest.TestCase):
    def setUp(self):
        self.cache_clear = MagicMock()
        self.cache_true = MagicMock(return_value=True)
        self.cache_false = MagicMock(return_value=False)
        self.cache_update = MagicMock()
        self.cache_set = MagicMock()
        self.cache_del = MagicMock()
        self.tenant_id = '101'
        self.token = Token()
        self.token_json = jsonutils.dumps(self.token.format())
        self.cache_get_token = MagicMock(return_value=self.token_json)

    def test_clear_calls_cache_clear(self):
        with patch.object(NativeProxy, 'cache_clear', self.cache_clear):
            token_cache = TokenCache()
            token_cache.clear()
        self.cache_clear.assert_called_once_with(CACHE_TOKEN)

    def test_set_token_calls_cache_update(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_true
        ), patch.object(NativeProxy, 'cache_update', self.cache_update):
            token_cache = TokenCache()
            token_cache.set_token(self.tenant_id, self.token)

        self.cache_update.assert_called_once_with(
            self.tenant_id, jsonutils.dumps(self.token.format()),
            DEFAULT_EXPIRES, CACHE_TOKEN)

    def test_set_token_calls_cache_set(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_false
        ), patch.object(NativeProxy, 'cache_set', self.cache_set):
            token_cache = TokenCache()
            token_cache.set_token(self.tenant_id, self.token)

        self.cache_set.assert_called_once_with(
            self.tenant_id, jsonutils.dumps(self.token.format()),
            DEFAULT_EXPIRES, CACHE_TOKEN)

    def test_get_token_calls_returns_tenant(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_true
        ), patch.object(NativeProxy, 'cache_get',  self.cache_get_token):
            token_cache = TokenCache()
            token = token_cache.get_token(self.tenant_id)

        self.cache_get_token.assert_called_once_with(
            self.tenant_id, CACHE_TOKEN)
        self.assertIsInstance(token, Token)

    def test_get_token_calls_returns_none(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_false):
            token_cache = TokenCache()
            token = token_cache.get_token(self.tenant_id)

        self.assertIs(token, None)

    def test_delete_token_calls_cache_del(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_true
        ), patch.object(NativeProxy, 'cache_del', self.cache_del):
            token_cache = TokenCache()
            token_cache.delete_token(self.tenant_id)

        self.cache_del.assert_called_once_with(
            self.tenant_id, CACHE_TOKEN)

    def test_delete_token_does_not_call_cache_del(self):
        with patch.object(
                NativeProxy, 'cache_exists', self.cache_false
        ), patch.object(NativeProxy, 'cache_del', self.cache_del):
            token_cache = TokenCache()
            token_cache.delete_token(self.tenant_id)

        with self.assertRaises(AssertionError):
            self.cache_del.assert_called_once_with(
                self.tenant_id, CACHE_TOKEN)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = driver_test
import unittest
from mock import MagicMock, patch
from meniscus.data.handlers.elasticsearch import driver as es


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingEsDataSourceHandler)

    return suite


class WhenTestingEsDataSourceHandler(unittest.TestCase):
    def setUp(self):
        self.conf = MagicMock()
        self.conf = MagicMock()
        self.conf.servers = ['localhost:9200']
        self.conf.bulk_size = 100
        self.conf.ttl = 30
        self.es_handler = es.ElasticsearchHandler(self.conf)
        self.mock_index = "dc2bb3e0-3116-11e3-aa6e-0800200c9a66"
        self.mock_mapping = {
            "mapping": {
                "properties": {
                    "field": {
                        "type": "date",
                        "format": "dateOptionalTime"
                    }
                }
            }
        }

    def test_constructor(self):
        #test es_handler constructor with no bulk off
        self.assertEqual(
            self.es_handler.es_servers,
            [{'host': 'localhost', 'port': '9200'}]
        )
        self.assertEqual(self.es_handler.bulk_size, self.conf.bulk_size)
        self.assertEqual(self.es_handler.ttl, self.conf.ttl)
        self.assertEquals(self.es_handler.status, self.es_handler.STATUS_NEW)

    def test_check_connection(self):
        self.es_handler.status = self.es_handler.STATUS_NEW
        with self.assertRaises(es.ElasticsearchHandlerError):
            self.es_handler._check_connection()

        self.es_handler.status = self.es_handler.STATUS_CLOSED
        with self.assertRaises(es.ElasticsearchHandlerError):
            self.es_handler._check_connection()

        #test that a status of  STATUS_CONNECTED  does not raise an exception
        handler_error_raised = False
        try:
            self.es_handler.status = self.es_handler.STATUS_CONNECTED
            self.es_handler._check_connection()
        except es.ElasticsearchHandlerError:
            handler_error_raised = True
        self.assertFalse(handler_error_raised)

    def test_connection(self):
        connection = MagicMock(return_value=None)
        with patch.object(es.Elasticsearch, '__init__', connection):
            self.es_handler.connect()
        connection.assert_called_once_with(
            hosts=self.es_handler.es_servers
        )
        self.assertEquals(
            self.es_handler.status,
            self.es_handler.STATUS_CONNECTED)

    def test_close(self):
        self.es_handler.close()
        self.assertEqual(self.es_handler.connection, None)
        self.assertEqual(
            self.es_handler.status, self.es_handler.STATUS_CLOSED)

    def test_create_index(self):
        create_index_method = MagicMock()
        connection = MagicMock()
        connection.indices.create = create_index_method
        self.es_handler.connection = connection
        self.es_handler.status = self.es_handler.STATUS_CONNECTED
        self.es_handler.create_index(self.mock_index)
        create_index_method.assert_called_once_with(
            index=self.mock_index, body=None)

    def test_create_index_mapping(self):
        create_index_method = MagicMock()
        connection = MagicMock()
        connection.indices.create = create_index_method
        self.es_handler.connection = connection
        self.es_handler.status = self.es_handler.STATUS_CONNECTED
        self.es_handler.create_index(
            self.mock_index, mapping=self.mock_mapping)
        create_index_method.assert_called_once_with(
            index=self.mock_index, body=self.mock_mapping)

    def test_put_mapping(self):
        put_mapping_method = MagicMock()
        connection = MagicMock()
        connection.indices.put_mapping = put_mapping_method
        self.es_handler.connection = connection
        doc_type = "default"
        self.es_handler.status = self.es_handler.STATUS_CONNECTED
        self.es_handler.put_mapping(
            index=self.mock_index, doc_type=doc_type,
            mapping=self.mock_mapping)
        put_mapping_method.assert_called_once_with(
            index=self.mock_index,
            doc_type=doc_type,
            body=self.mock_mapping
        )


class WhenTestingGetHandler(unittest.TestCase):
    def setUp(self):
        self.connect_method = MagicMock()

    def test_get_handler(self):
        with patch.object(
                es.ElasticsearchHandler, 'connect', self.connect_method):
            handler = es.get_handler()
            self.connect_method.assert_called_once_with()
            self.assertIsInstance(handler, es.ElasticsearchHandler)

########NEW FILE########
__FILENAME__ = mapping_tasks_test
import unittest

from mock import MagicMock, patch

from meniscus.data.handlers.elasticsearch import mapping_tasks


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingTtlTasks())
    return suite


class WhenTestingTtlTasks(unittest.TestCase):

    def setUp(self):
        self.tenant_id = "dc2bb3e0-3116-11e3-aa6e-0800200c9a66"
        self.doc_type = "default"
        self.db_handler = MagicMock()
        self.create_index_method = MagicMock()
        self.db_handler.create_index = self.create_index_method
        self.put_mapping_method = MagicMock()
        self.db_handler.put_mapping = self.put_mapping_method

    def test_create_ttl_mapping(self):
        with patch(
            'meniscus.data.handlers.elasticsearch.'
                'mapping_tasks._es_handler', self.db_handler):
            mapping_tasks.create_ttl_mapping(self.tenant_id, self.doc_type)
            self.put_mapping_method.assert_called_once_with(
                index=self.tenant_id, doc_type=self.doc_type,
                mapping=mapping_tasks.TTL_MAPPING
            )

    def test_create_index(self):
        delay_call = MagicMock()

        with patch(
            'meniscus.data.handlers.elasticsearch.'
            'mapping_tasks._es_handler',
            self.db_handler), \
                patch(
                    'meniscus.data.handlers.elasticsearch.'
                    'mapping_tasks.create_ttl_mapping',
                    MagicMock()):
            mapping_tasks.create_index(self.tenant_id)
        self.create_index_method.assert_called_once_with(
            index=self.tenant_id, mapping=mapping_tasks.DEFAULT_MAPPING)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = driver_test
import unittest
from mock import MagicMock, patch
from meniscus.data.handlers.mongodb import driver as mongodb


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingMongoDataSourceHandler())
    return suite


class WhenTestingMongoDataSourceHandler(unittest.TestCase):
    def setUp(self):
        self.conf = MagicMock()

        self.conf.servers = ['localhost:9200']
        self.conf.username = 'mongodb'
        self.conf.password = 'pass'
        self.mongo_handler = mongodb.MongoDBHandler(self.conf)

    def test_constructor(self):
        self.assertEqual(self.mongo_handler.mongo_servers, self.conf.servers)
        self.assertEqual(self.mongo_handler.username, self.conf.username)
        self.assertEqual(self.mongo_handler.password, self.conf.password)

    def test_check_connection(self):
        self.mongo_handler.status = None
        with self.assertRaises(mongodb.MongoDBHandlerError):
            self.mongo_handler._check_connection()

        self.mongo_handler.status = self.mongo_handler.STATUS_CLOSED
        with self.assertRaises(mongodb.MongoDBHandlerError):
            self.mongo_handler._check_connection()

        #test that a status of  STATUS_CONNECTED  does not raise an exception
        handler_error_raised = False
        try:
            self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
            self.mongo_handler._check_connection()
        except mongodb.MongoDBHandlerError:
            handler_error_raised = True
        self.assertFalse(handler_error_raised)

    def test_connection(self):
        connection = MagicMock(return_value=MagicMock())
        with patch(
                'meniscus.data.handlers.mongodb.driver.MongoClient',
                connection):
            self.mongo_handler.connect()
        connection.assert_called_once_with(self.mongo_handler.mongo_servers,
                                           slave_okay=True)
        self.assertEquals(
            self.mongo_handler.status, self.mongo_handler.STATUS_CONNECTED)

    def test_close_connection(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CLOSED
        connection = MagicMock(return_value=MagicMock())
        with patch(
                'meniscus.data.handlers.mongodb.driver.MongoClient',
                connection):
            self.mongo_handler.connect()
        self.mongo_handler.close()
        self.assertEquals(
            self.mongo_handler.status, self.mongo_handler.STATUS_CLOSED)

    def test_create_sequence_existing_sequence(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        sequence = 'sequence01'
        create_sequence = MagicMock()
        self.mongo_handler.find_one = create_sequence
        self.mongo_handler.create_sequence(sequence)
        create_sequence.assert_called_once_with('counters', {'name': sequence})

    def test_create_sequence_new_sequence(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        sequence = 'sequence01'
        create_sequence = MagicMock()
        self.mongo_handler.find_one = MagicMock(return_value=None)
        self.mongo_handler.put = create_sequence
        self.mongo_handler.create_sequence(sequence)
        create_sequence.assert_called_once_with('counters', {'name': sequence,
                                                             'seq': 1})

    def test_delete_sequence(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        sequence = 'sequence01'
        delete_sequence = MagicMock()
        self.mongo_handler.delete = delete_sequence
        self.mongo_handler.delete_sequence(sequence)
        delete_sequence.assert_called_once_with('counters', {'name': sequence})

    def test_next_sequence_value(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        sequence_name = 'sequence01'
        next_sequence_value = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database['counters'].find_and_modify \
            = next_sequence_value
        self.mongo_handler.next_sequence_value(sequence_name)
        next_sequence_value.assert_called_once_with(
            {'name': sequence_name}, {'$inc': {'seq': 1}})

    def test_find_no_query_filter(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        find = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].find = find
        self.mongo_handler.find(object_name)
        find.assert_called_once_with({}, None)

    def test_find_with_query_filter(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        query_filter = {"filter": "test"}
        find = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].find = find
        self.mongo_handler.find(object_name, query_filter)
        find.assert_called_once_with(query_filter, None)

    def test_find_one_no_query_filter(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        find_one = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].find_one = find_one
        self.mongo_handler.find_one(object_name)
        find_one.assert_called_once_with({})

    def test_find_one_with_query_filter(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        query_filter = {"filter": "test"}
        find_one = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].find_one = find_one
        self.mongo_handler.find_one(object_name, query_filter)
        find_one.assert_called_once_with(query_filter)

    def test_put_no_document(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        insert = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].insert = insert
        self.mongo_handler.put(object_name)
        insert.assert_called_once_with({})

    def test_put_with_document(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        document = {"document": "test"}
        insert = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].insert = insert
        self.mongo_handler.put(object_name, document)
        insert.assert_called_once_with(document)

    def test_update_with_document(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        document = {"_id": "test"}
        save = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].save = save
        self.mongo_handler.update(object_name, document)
        save.assert_called_once_with(document)

    def test_set_field_no_query_filter(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        update_fields = {}
        set_field = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].update = set_field
        self.mongo_handler.set_field(object_name, update_fields)
        set_field.assert_called_once_with(
            {}, {"$set": update_fields}, multi=True)

    def test_set_field_query_filter(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        query_filter = {'filter01': 'test'}
        update_fields = {'field': 'test'}
        set_field = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].update = set_field
        self.mongo_handler.set_field(object_name, update_fields, query_filter)
        set_field.assert_called_once_with({'filter01': 'test'},
                                          {'$set': {'field': 'test'}},
                                          multi=True)

    def test_remove_field_no_query_filter(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        update_fields = {'field': 'test'}
        remove_field = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].update = remove_field
        self.mongo_handler.remove_field(object_name, update_fields)
        remove_field.assert_called_once_with(
            {}, {"$unset": update_fields}, multi=True)

    def test_remove_field_query_filter(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        query_filter = {'filter01': 'test'}
        update_fields = {'field': 'test'}
        remove_field = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].update = remove_field
        self.mongo_handler.remove_field(object_name, update_fields,
                                        query_filter)
        remove_field.assert_called_once_with({'filter01': 'test'},
                                             {'$unset': {'field': 'test'}},
                                             multi=True)

    def test_find_one_no_query_filter(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        remove = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].remove = remove
        self.mongo_handler.delete(object_name)
        remove.assert_called_once_with({}, True)

    def test_find_one_with_query_filter(self):
        self.mongo_handler.status = self.mongo_handler.STATUS_CONNECTED
        object_name = 'object01'
        query_filter = {"filter": "test"}
        remove = MagicMock()
        self.mongo_handler.database = MagicMock()
        self.mongo_handler.database[object_name].remove = remove
        self.mongo_handler.delete(object_name, query_filter)
        remove.assert_called_once_with({'filter': 'test'}, True)


class WhenTestingGetHandler(unittest.TestCase):
    def setUp(self):
        self.connect_method = MagicMock()

    def test_get_handler(self):
        with patch.object(
                mongodb.MongoDBHandler, 'connect', self.connect_method):
            handler = mongodb.get_handler()
            self.connect_method.assert_called_once_with()
            self.assertIsInstance(handler, mongodb.MongoDBHandler)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = tenant_test
import unittest

from mock import MagicMock, patch

from meniscus.data.model.tenant import EventProducer
from meniscus.data.model.tenant import Token
from meniscus.data.model.tenant import Tenant


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingEventProducerObject())
    suite.addTest(WhenTestingTokenObject())
    suite.addTest(WhenTestingTenantObject())


class WhenTestingEventProducerObject(unittest.TestCase):

    def setUp(self):
        with patch('meniscus.data.model.tenant.DEFAULT_SINK',
                   'elasticsearch'):
            self.event_producer = EventProducer('EVid',
                                                'mybillingsapp',
                                                'syslog',
                                                'true',
                                                'false')

    def test_event_producer_object_get_id(self):
        self.assertEqual(self.event_producer.get_id(), 'EVid')

    def test_event_producer_object_format(self):
        ep_dict = self.event_producer.format()
        self.assertEqual(ep_dict['id'], 'EVid')
        self.assertEqual(ep_dict['name'], 'mybillingsapp')
        self.assertEqual(ep_dict['pattern'], 'syslog')
        self.assertEqual(ep_dict['durable'], 'true')
        self.assertEqual(ep_dict['encrypted'], 'false')
        self.assertListEqual(ep_dict['sinks'], ['elasticsearch'])


class WhenTestingTokenObject(unittest.TestCase):

    def setUp(self):
        self.empty_token = Token()
        self.test_token = Token('89c38542-0c78-41f1-bcd2-5226189ccab9',
                                '89c38542-0c78-41f1-bcd2-5226189ddab1',
                                '2013-04-01T21:58:16.995031Z')
        self.true_token_string = '89c38542-0c78-41f1-bcd2-5226189ccab9'
        self.previous_token_string = '89c38542-0c78-41f1-bcd2-5226189ddab1'
        self.false_token_string = '89c38542-0c78-41f1-bcd2-5226189d453sh'
        self.empty_token_string = ''

    def test_token_new(self):
        self.assertIsNot(self.empty_token.valid,
                         '89c38542-0c78-41f1-bcd2-5226189ccab9')
        self.assertEqual(self.empty_token.previous, None)
        self.assertIsNot(self.empty_token.last_changed,
                         '2013-04-01T21:58:16.995031Z')

    def test_token_reset(self):
        self.test_token.reset_token()

        self.assertIsNot(self.test_token.valid,
                         '89c38542-0c78-41f1-bcd2-5226189ccab9')
        self.assertEqual(self.test_token.previous,
                         '89c38542-0c78-41f1-bcd2-5226189ccab9')
        self.assertIsNot(self.test_token.last_changed,
                         '2013-04-01T21:58:16.995031Z')

    def test_token_reset_token_now(self):
        self.test_token.reset_token_now()
        self.assertIsNot(self.test_token.valid,
                         '89c38542-0c78-41f1-bcd2-5226189ccab9')
        self.assertEqual(self.test_token.previous, None)
        self.assertIsNot(self.test_token.last_changed,
                         '2013-04-01T21:58:16.995031Z')

    def test_token_format(self):
        token_dict = self.test_token.format()
        self.assertEqual(token_dict['valid'],
                         '89c38542-0c78-41f1-bcd2-5226189ccab9')
        self.assertEqual(token_dict['previous'],
                         '89c38542-0c78-41f1-bcd2-5226189ddab1')
        self.assertEqual(token_dict['last_changed'],
                         '2013-04-01T21:58:16.995031Z')

    def test_token_validate(self):
        self.assertFalse(
            self.test_token.validate_token(self.empty_token_string))
        self.assertTrue(self.test_token.validate_token(self.true_token_string))
        self.assertTrue(
            self.test_token.validate_token(self.previous_token_string))
        self.assertFalse(
            self.test_token.validate_token(self.false_token_string))


class WhenTestingTenantObject(unittest.TestCase):
    def setUp(self):
        self.test_token = Token('89c38542-0c78-41f1-bcd2-5226189ccab9',
                                '89c38542-0c78-41f1-bcd2-5226189ddab1',
                                '2013-04-01T21:58:16.995031Z')
        self.test_tenant_bare = Tenant('1022', self.test_token)
        self.test_tenant = Tenant('1022', self.test_token, [], 'MDBid',
                                  'TenantName')

    def test_tenant_get_id(self):
        self.assertEqual(self.test_tenant.get_id(), 'MDBid')

    def test_tenant_format(self):
        tenant_dict = self.test_tenant_bare.format()
        self.assertEqual(tenant_dict['tenant_id'], '1022')
        self.assertEqual(tenant_dict['event_producers'], [])
        self.assertTrue('token' in tenant_dict)

    def test_tenant_format_for_save(self):
        tenant_dict = self.test_tenant.format_for_save()
        self.assertEqual(tenant_dict['tenant_id'], '1022')
        self.assertEqual(tenant_dict['tenant_name'], 'TenantName')
        self.assertEqual(tenant_dict['event_producers'], [])
        self.assertEqual(tenant_dict['_id'], 'MDBid')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = tenant_util_test
import unittest
from mock import MagicMock, patch
from meniscus.data.model.tenant import EventProducer, Tenant
from meniscus.data.model import tenant_util
from meniscus.openstack.common import jsonutils


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingFindMethods())


class WhenTestingFindMethods(unittest.TestCase):

    def setUp(self):
        self.tenant_id = "12673247623548752387452378"
        self.tenant_dict = {
            "tenant_id": self.tenant_id,
            "tenant_name": "TenantName",
            "_id": "507f1f77bcf86cd799439011",
            "event_producers": [
                {
                    "id": 123,
                    "name": "apache",
                    "pattern": "apache2.cee",
                    "durable": False,
                    "encrypted": False,
                    "sinks": ["elasticsearch"]
                },
                {
                    "id": 124,
                    "name": "system.auth",
                    "pattern": "auth_log.cee",
                    "durable": False,
                    "encrypted": False,
                    "sinks": ["elasticsearch", "hdfs"]
                }
            ],
            "token": {
                "valid": "c8a4db32-635a-46b6-94ed-04b1bd533f41",
                "previous": None,
                "last_changed": "2013-03-19T18:16:48.411029Z"
            }
        }
        self.producer_id = "234"
        self.event_producer = EventProducer(
            _id=self.producer_id, name="nginx", pattern="nginx")
        self.ds_handler = MagicMock()
        self.ds_handler.find_one.return_value = self.tenant_dict
        self.tenant_obj = tenant_util.load_tenant_from_dict(self.tenant_dict)
        self.tenant_cache = MagicMock()
        self.tenant_cache.cache_get.return_value = jsonutils.dumps(
            self.tenant_dict)
        self.tenant_cache.cache_exists.return_value = True
        self.tenant_cache.cache_update = MagicMock()
        self.token_cache = MagicMock()
        self.token_cache.cache_get.return_value = jsonutils.dumps(
            self.tenant_dict['token'])
        self.token_cache.cache_exists.return_value = True
        self.cache_empty = MagicMock()
        self.cache_empty.cache_exists.return_value = False
        self.cache_empty.cache_set = MagicMock()

    def test_find_tenant_returns_instance(self):
        retrieve_tenant_call = MagicMock(return_value=self.tenant_obj)
        with patch('meniscus.data.model.tenant_util.retrieve_tenant',
                   retrieve_tenant_call):
            tenant = tenant_util.find_tenant('12345')
            self.assertIsInstance(tenant, Tenant)

    def test_find_tenant_returns_none(self):
        retrieve_tenant_call = MagicMock(return_value=None)
        with patch('meniscus.data.model.tenant_util.retrieve_tenant',
                   retrieve_tenant_call):
            tenant = tenant_util.find_tenant('12345')
            self.assertIsNone(tenant)

    def test_find_tenant_creates_new_tenant_on_no_tenant_found(self):
        retrieve_tenant_call = MagicMock(side_effect=[None, self.tenant_obj])
        create_tenant_call = MagicMock()
        with patch('meniscus.data.model.tenant_util.retrieve_tenant',
                   retrieve_tenant_call), patch(
                'meniscus.data.model.tenant_util.create_tenant',
                create_tenant_call):
            tenant = tenant_util.find_tenant(
                'unknown_tenant_id', create_on_missing=True)
            self.assertIsInstance(tenant, Tenant)
            create_tenant_call.assert_called_once_with('unknown_tenant_id')

    def test_create_tenant(self):
        ttl_create_index_call = MagicMock()
        with patch('meniscus.data.model.tenant_util._db_handler',
                   self.ds_handler), patch(
                'meniscus.data.model.tenant_util.'
                'mapping_tasks.create_index.delay',
                ttl_create_index_call):
            tenant_util.create_tenant(self.tenant_id)
            self.ds_handler.put.assert_called_once()
            self.ds_handler.create_sequence.assert_called_once_with(
                self.tenant_id)
            ttl_create_index_call.assert_called_once_with(self.tenant_id)

    def test_retrieve_tenant_returns_tenant_obj(self):
        self.ds_handler.find_one = MagicMock(return_value=self.tenant_dict)
        with patch('meniscus.data.model.tenant_util._db_handler',
                   self.ds_handler):
            tenant = tenant_util.retrieve_tenant(self.tenant_id)
            self.ds_handler.find_one.assert_called_once_with(
                'tenant', {'tenant_id': self.tenant_id})
            self.assertIsInstance(tenant, Tenant)

    def test_retrieve_tenant_returns_none_when_no_tenant_found(self):
        self.ds_handler.find_one = MagicMock(return_value=None)
        with patch('meniscus.data.model.tenant_util._db_handler',
                   self.ds_handler):
            tenant = tenant_util.retrieve_tenant(self.tenant_id)
            self.ds_handler.find_one.assert_called_once_with(
                'tenant', {'tenant_id': self.tenant_id})
            self.assertIsNone(tenant)

    def test_save_tenant(self):
        self.ds_handler.update = MagicMock()
        with patch('meniscus.data.model.tenant_util._db_handler',
                   self.ds_handler):
            tenant_util.save_tenant(self.tenant_obj)
            self.ds_handler.update.assert_called_once_with(
                'tenant', self.tenant_obj.format_for_save())

    def test_load_tenant_from_dict(self):
        tenant = tenant_util.load_tenant_from_dict(
            self.tenant_obj.format_for_save())
        self.assertIsInstance(tenant, Tenant)
        self.assertEqual(tenant.format_for_save(),
                         self.tenant_obj.format_for_save())

    def test_create_event_producer(self):
        self.ds_handler.next_sequence_value = MagicMock(
            return_value=self.producer_id)
        ttl_create_mapping_call = MagicMock()
        save_tenant_call = MagicMock()
        with patch(
                'meniscus.data.model.tenant_util._db_handler',
                self.ds_handler), \
            patch(
                'meniscus.data.model.tenant_util.'
                'mapping_tasks.create_ttl_mapping.delay',
                ttl_create_mapping_call), \
            patch(
                'meniscus.data.model.tenant_util.save_tenant',
                save_tenant_call):
            new_producer_id = tenant_util.create_event_producer(
                self.tenant_obj,
                self.event_producer.name,
                self.event_producer.pattern,
                self.event_producer.durable,
                self.event_producer.encrypted,
                self.event_producer.sinks
            )
            save_tenant_call.assert_called_once_with(self.tenant_obj)
            ttl_create_mapping_call.assert_called_once_with(
                tenant_id=self.tenant_obj.tenant_id,
                producer_pattern=self.event_producer.pattern)
            self.assertEqual(new_producer_id, self.producer_id)

    def test_delete_event_producer(self):
        save_tenant_call = MagicMock()
        with patch('meniscus.data.model.tenant_util.save_tenant',
                   save_tenant_call):
            producer_to_delete = self.tenant_obj.event_producers[0]
            tenant_util.delete_event_producer(
                self.tenant_obj, producer_to_delete)
            self.assertFalse(
                producer_to_delete in self.tenant_obj.event_producers)
            save_tenant_call.assert_called_once_with(self.tenant_obj)

    def test_find_event_producer_by_id_returns_instance(self):
        with patch('meniscus.data.model.tenant_util._db_handler',
                   self.ds_handler):
            tenant = tenant_util.find_tenant('12345')
            producer = tenant_util.find_event_producer(tenant, producer_id=123)
            self.assertIsInstance(producer, EventProducer)

    def test_find_event_producer_by_id_returns_none(self):
        with patch('meniscus.data.model.tenant_util._db_handler',
                   self.ds_handler):
            tenant = tenant_util.find_tenant('12345')
            producer = tenant_util.find_event_producer(tenant, producer_id=130)
            self.assertEquals(producer, None)

    def test_find_event_producer_by_name_returns_instance(self):
        with patch('meniscus.data.model.tenant_util._db_handler',
                   self.ds_handler):
            tenant = tenant_util.find_tenant('12345')
            producer = tenant_util.find_event_producer(
                tenant, producer_name='system.auth')
            self.assertIsInstance(producer, EventProducer)

    def test_find_event_producer_by_name_returns_none(self):
        with patch('meniscus.data.model.tenant_util._db_handler',
                   self.ds_handler):
            tenant = tenant_util.find_tenant('12345')
            producer = tenant_util.find_event_producer(
                tenant, producer_name='not_name')
            self.assertEquals(producer, None)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = worker_test
import unittest

from meniscus.data.model.worker import SystemInfo
from meniscus.data.model.worker import Worker
from meniscus.data.model.worker import WorkerConfiguration


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingWorkerObject())
    suite.addTest(WhenTestingSystemInfoObject())
    suite.addTest(WhenTestingWorkerConfigurationObject())


class WhenTestingWorkerObject(unittest.TestCase):

    def setUp(self):
        self.system_info = SystemInfo()

        self.test_worker = Worker(_id='010101',
                                  worker_token='9876543210',
                                  hostname='worker01',
                                  callback='172.22.15.25:8080/v1/config/',
                                  ip_address_v4='172.23.1.100',
                                  ip_address_v6='::1',
                                  personality='worker',
                                  status='new',
                                  system_info=self.system_info.format())
        self.test_worker_lite = Worker(hostname='worker01',
                                       callback='172.22.15.25:8080/v1/config/',
                                       ip_address_v4='172.23.1.100',
                                       ip_address_v6='::1',
                                       personality='worker',
                                       status='new',
                                       system_info=self.system_info.format())
        self.worker_status = self.test_worker.get_status()

    def test_new_worker_format_for_save(self):
        self.assertTrue('_id' in self.test_worker.format_for_save())

    def test_get_status(self):
        self.assertEqual(self.worker_status['hostname'], 'worker01')
        self.assertEqual(self.worker_status['personality'], 'worker')
        self.assertEqual(self.worker_status['status'], 'new')
        self.assertEqual(self.worker_status['system_info'],
                         self.system_info.format())


class WhenTestingSystemInfoObject(unittest.TestCase):
    def setUp(self):
        self.system_info = SystemInfo(
            cpu_cores='4',
            os_type='Darwin-11.4.2-x86-64bit',
            memory_mb='1024',
            timestamp='2013-07-15 19:26:53.076426',
            architecture='x86_64',
            load_average={
                "1": 0.24755859375,
                "5": 1.0751953125,
                "15": 0.9365234375
            },
            disk_usage={
                "/dev/sda1": {
                    "total": 313764528,
                    "used": 112512436
                }
            }
        )

    def test_new_system_info_obj(self):
        self.assertEqual(self.system_info.cpu_cores, '4')
        self.assertEqual(self.system_info.os_type, 'Darwin-11.4.2-x86-64bit')
        self.assertEqual(self.system_info.memory_mb, '1024')
        self.assertEqual(self.system_info.architecture, 'x86_64')
        self.assertEqual(self.system_info.timestamp,
                         '2013-07-15 19:26:53.076426')
        self.assertEqual(
            self.system_info.disk_usage["/dev/sda1"],
            {
                "total": 313764528,
                "used": 112512436
            }
        )
        self.assertEqual(self.system_info.load_average["1"], 0.24755859375)
        self.assertEqual(self.system_info.load_average["5"], 1.0751953125)
        self.assertEqual(self.system_info.load_average["15"], 0.9365234375)

    def test_new_system_info_empty_obj(self):
        system_info = SystemInfo()
        system_dict = system_info.format()
        self.assertTrue('cpu_cores' in system_dict)
        self.assertTrue('os_type' in system_dict)
        self.assertTrue('memory_mb' in system_dict)
        self.assertTrue('architecture' in system_dict)
        self.assertTrue('load_average' in system_dict)
        self.assertTrue('disk_usage' in system_dict)
        self.assertTrue('timestamp' in system_dict)


class WhenTestingWorkerConfigurationObject(unittest.TestCase):

    def setUp(self):
        self.worker_config = WorkerConfiguration(
            "worker",
            "worker01",
            "http://172.22.15.25:8080/v1")

    def test_worker_configuration(self):
        self.assertEqual(self.worker_config.personality, 'worker')
        self.assertEqual(self.worker_config.hostname, 'worker01')
        self.assertEqual(self.worker_config.coordinator_uri,
                         'http://172.22.15.25:8080/v1')

    def test_worker_configuration_format(self):
        worker_dict = self.worker_config.format()
        self.assertEqual(worker_dict['personality'], 'worker')
        self.assertEqual(worker_dict['hostname'], 'worker01')
        self.assertEqual(worker_dict['coordinator_uri'],
                         'http://172.22.15.25:8080/v1')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = worker_util_test
import unittest

from mock import MagicMock, patch

from meniscus.data.model.worker import Worker, SystemInfo

_db_handler = MagicMock()

from meniscus.data.model import worker_util


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenTestingWorkerUtil())


class WhenTestingWorkerUtil(unittest.TestCase):

    def setUp(self):
        self.system_info = SystemInfo().format()
        self.worker = Worker(**{"hostname": "worker-01",
                                "ip_address_v4": "192.168.100.101",
                                "ip_address_v6": "::1",
                                "personality": "worker",
                                "status": "online",
                                "system_info": self.system_info})

    def test_create_worker_calls_db_put(self):
        put_method = MagicMock()
        with patch('meniscus.data.model.worker_util._db_handler.put',
                   put_method):
            worker_util.create_worker(self.worker)
            put_method.assert_called_once_with('worker', self.worker.format())

    def test_find_worker_returns_worker(self):
        find_one_method = MagicMock(return_value=self.worker.format())
        with patch('meniscus.data.model.worker_util._db_handler.find_one',
                   find_one_method):
            worker = worker_util.find_worker(self.worker.hostname)
            find_one_method.assert_called_once_with(
                'worker', {'hostname': self.worker.hostname})
            self.assertIsInstance(worker, Worker)

    def test_find_worker_returns_none(self):
        find_one_method = MagicMock(return_value=None)
        with patch('meniscus.data.model.worker_util._db_handler.find_one',
                   find_one_method):
            worker = worker_util.find_worker(self.worker.hostname)
            find_one_method.assert_called_once_with(
                'worker', {'hostname': self.worker.hostname})
            self.assertIsNone(worker)

    def test_save_worker(self):
        update_method = MagicMock(return_value=None)
        with patch('meniscus.data.model.worker_util._db_handler.update',
                   update_method):
            worker_util.save_worker(self.worker)
            update_method.assert_called_once_with(
                'worker', self.worker.format_for_save())

    def test_retrieve_all_workers(self):
        find_method = MagicMock(return_value=[self.worker.format_for_save()])
        with patch('meniscus.data.model.worker_util._db_handler.find',
                   find_method):
            workers = worker_util.retrieve_all_workers()
            find_method.assert_called_once_with('worker')
            for worker in workers:
                self.assertIsInstance(worker, Worker)

########NEW FILE########
__FILENAME__ = env_test
import unittest
import meniscus.env as env


class WhenGettingLoggers(unittest.TestCase):

    def test_should_get_logger(self):
        logger = env.get_logger('meniscus.env_test')
        self.assertIsNotNone(logger)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = plugin_test
import os
import unittest
import tempfile
import shutil

from meniscus.ext.plugin import plug_into, import_module


def suite():
    suite = unittest.TestSuite()
    suite.addTest(WhenLoading())

    return suite


INIT_PY = """
def perform_init():
    return True

"""


PLUGIN_PY = """
def perform_operation(msg):
    return True, msg

"""


class WhenLoading(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp('testing_lib')

        self.tmp_lib = os.path.join(self.tmp_dir, 'test')
        os.mkdir(self.tmp_lib)

        self.init_file = os.path.join(self.tmp_lib, '__init__.py')
        self.plugin_file = os.path.join(self.tmp_lib, 'plugin.py')

        output = open(self.init_file, 'w')
        output.write(INIT_PY)
        output.close()

        output = open(self.plugin_file, 'w')
        output.write(PLUGIN_PY)
        output.close()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)
        pass

    def test_loading_module(self):
        plug_into(self.tmp_dir)

        plugin_mod = import_module('test')
        must_be_true = plugin_mod.perform_init()

        self.assertTrue(must_be_true)

    def test_loading_file(self):
        plug_into(self.tmp_dir)

        plugin_mod = import_module('test.plugin')
        must_be_true, msg = plugin_mod.perform_operation('test')

        self.assertTrue(must_be_true)
        self.assertEqual('test', msg)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = lognorm_test
import unittest

from mock import MagicMock
from meniscus.normalization.lognorm import get_normalizer


class WhenTestingMessageNormalization(unittest.TestCase):

    def setUp(self):
        self.conf = MagicMock()
        self.conf.liblognorm = MagicMock()
        self.conf.liblognorm.rules_dir = '../etc/meniscus/normalizer_rules'

        self.normalizer, self.loaded_rules = get_normalizer(self.conf)

    def test_loading_rules(self):
        self.assertTrue('apache' in self.loaded_rules)

########NEW FILE########
__FILENAME__ = normalizer_test
import unittest

from mock import MagicMock, patch
from meniscus.normalization.normalizer import should_normalize


class WhenNormalizingMessages(unittest.TestCase):

    def setUp(self):
        self.bad_message = dict()
        self.good_message = {
            "processid": "3071",
            "appname": "dhcpcd",
            "timestamp": "2013-04-05T15:51:18.607457-05:00",
            "hostname": "tohru",
            "priority": "30",
            "version": "1",
            "messageid": "-",
            "msg": "wlan0: leased 10.6.173.172 for 3600 seconds\n",
            "sd": {
                "origin": {
                    "software": "rsyslogd",
                    "swVersion": "7.2.5",
                    "x-pid": "24592",
                    "x-info": "http://www.rsyslog.com"
                }
            },
            "meniscus": {
                "correlation": {
                    'ep_id': 1,
                    'pattern': "wpa_supplicant",
                    'durable': False,
                    'encrypted': False,
                    'sinks': ["elasticsearch"],
                }
            }
        }
        self.loaded_rules = ['wpa_supplicant']

    def test_normalize_message(self):
        target = 'meniscus.normalization.normalizer.loaded_normalizer_rules'
        with patch(target, self.loaded_rules):
            self.assertTrue(should_normalize(self.good_message))

########NEW FILE########
__FILENAME__ = publish_stats_test
import unittest

import requests
from mock import MagicMock
from mock import patch

from meniscus.openstack.common import jsonutils
from meniscus.personas.common.publish_stats import ConfigCache
from meniscus.personas.common.publish_stats import publish_worker_stats
from meniscus.data.model.worker import SystemInfo
from meniscus.data.model.worker import Worker
from meniscus.data.model.worker import WorkerConfiguration


def suite():

    suite = unittest.TestSuite()
    suite.addTest(WhenTestingPublishStats())
    return suite


class WhenTestingPublishStats(unittest.TestCase):
    def setUp(self):
        self.conf = MagicMock()
        self.conf.status_update.worker_status_interval = 60
        self.get_config = MagicMock(return_value=self.conf)
        self.config = WorkerConfiguration(
            personality='worker',
            hostname='worker01',
            coordinator_uri='http://192.168.1.2/v1')
        self.system_info = SystemInfo().format()
        self.request_uri = "{0}/worker/{1}/status".format(
            self.config.coordinator_uri, self.config.hostname)

        self.worker_status = {
            'worker_status': Worker(personality='worker').format()
        }
        self.worker_status['worker_status']['system_info'] = self.system_info
        self.req_body = jsonutils.dumps(self.worker_status)

        self.get_config = MagicMock(return_value=self.config)
        self.resp = requests.Response()
        self.http_request = MagicMock(return_value=self.resp)

    def test_http_request_called(self):
        with patch.object(
                ConfigCache, 'get_config', self.get_config), patch(
                'meniscus.personas.common.publish_stats.http_request',
                self.http_request), patch(
                'meniscus.personas.common.publish_stats.get_config',
                self.get_config), patch.object(
                SystemInfo, 'format',
                MagicMock(return_value=self.system_info)):

            publish_worker_stats()

            self.http_request.assert_called_once_with(
                url=self.request_uri,
                json_payload=self.req_body,
                http_verb='PUT'
            )


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = transport_test
import unittest

from mock import MagicMock, patch
import simplejson as json

from meniscus import transport


class WhenTestingZeroMqReceiver(unittest.TestCase):

    def setUp(self):
        self.host = '127.0.0.1'
        self.port = '5000'
        self.connect_host_tuple = (self.host, self.port)
        self.connect_host_tuples = [self.connect_host_tuple]
        self.validate_hosts = [
            "tcp://{}:{}".format(*host_tuple)
            for host_tuple in self.connect_host_tuples]
        self.zmq_mock = MagicMock()
        self.zmq_mock.PULL = transport.zmq.PULL

        #set up the mock of the socket object
        self.socket_mock = MagicMock()
        #create a mock for the zmq context object
        self.context_mock = MagicMock()
        #have the mock context object return the mock socket
        # when the context.socket() method is called
        self.context_mock.socket.return_value = self.socket_mock
        #have the mock zmq module return the mocked context object
        # when the Context() constructor is called
        self.zmq_mock.Context.return_value = self.context_mock

        self.receiver = transport.ZeroMQReceiver(self.connect_host_tuples)

    def test_constructor(self):
        self.assertEqual(
            self.receiver.upstream_hosts,
            self.validate_hosts)
        self.assertEqual(self.receiver.socket_type, transport.zmq.PULL)
        self.assertIsNone(self.receiver.context)
        self.assertIsNone(self.receiver.socket)
        self.assertFalse(self.receiver.connected)

    def test_connect(self):
        with patch('meniscus.transport.zmq', self.zmq_mock):
            self.receiver.connect()
        self.context_mock.socket.assert_called_once_with(transport.zmq.PULL)
        self.socket_mock.connect.assert_called_once_with(
            'tcp://{0}:{1}'.format(self.host, self.port))
        self.assertTrue(self.receiver.connected)

    def test_get(self):
        with patch('meniscus.transport.zmq', self.zmq_mock):
            self.receiver.connect()
        self.receiver.get()
        self.socket_mock.recv.assert_called_once()

        self.receiver.close()
        with self.assertRaises(transport.zmq.error.ZMQError):
            self.receiver.get()

    def test_close(self):
        with patch('meniscus.transport.zmq', self.zmq_mock):
            self.receiver.connect()
        self.receiver.close()
        self.socket_mock.close.assert_called_once_with()
        self.context_mock.destroy.assert_called_once_with()
        self.assertIsNone(self.receiver.context)
        self.assertIsNone(self.receiver.socket)
        self.assertFalse(self.receiver.connected)


class WhenTestingReceiverFactory(unittest.TestCase):

    def setUp(self):
        self.conf_mock = MagicMock()
        self.conf_mock.zmq_in.zmq_upstream_hosts = [
            '127.0.0.1:5000', '127.0.0.1:5003']
        self.upstream_host_tuples = [
            (host_port_str.split(':'))
            for host_port_str in self.conf_mock.zmq_in.zmq_upstream_hosts
        ]
        self.validate_hosts = [
            "tcp://{}:{}".format(*host_tuple)
            for host_tuple in self.upstream_host_tuples]
        self.zmq_mock = MagicMock()

    def test_new_zmq_receiver(self):
        with patch('meniscus.transport._CONF', self.conf_mock):
            zmq_receiver = transport.new_zmq_receiver()
        self.assertIsInstance(zmq_receiver, transport.ZeroMQReceiver)
        self.assertEqual(zmq_receiver.upstream_hosts, self.validate_hosts)


class WhenTestingZeroMQInputServer(unittest.TestCase):
    def setUp(self):
        self.receiver_mock = MagicMock()

        #create a test class from the base class and override process_msg
        class TestInputServer(transport.ZeroMQInputServer):
            def process_msg(self):
                self.test_stop = self._stop
                self.process_msg_called = True
                self.stop()

        self.server = TestInputServer(self.receiver_mock)
        self.msg = {"key": "value"}
        self.valid_json_msg = json.dumps(self.msg)
        self.bad_msg = "gigdiu"

    def test_constructor(self):
        self.assertEqual(self.server.zmq_receiver, self.receiver_mock)
        self.assertTrue(self.server._stop)

    def test_start_stop(self):
        self.assertTrue(self.server._stop)
        self.server.start()
        self.receiver_mock.connect.assert_called_once_with()
        self.assertFalse(self.server.test_stop)
        self.assertTrue(self.server._stop)
        self.assertTrue(self.server.process_msg_called)

    def test_get_msg_returns_dict(self):
        self.receiver_mock.get.return_value = self.valid_json_msg
        msg = self.server._get_msg()
        self.receiver_mock.get.assert_called_once_with()
        self.assertEquals(msg, self.msg)


class WhenTestingZeroMqCaster(unittest.TestCase):

    def setUp(self):
        self.host = '127.0.0.1'
        self.port = '5000'
        self.bind_host_tuple = (self.host, self.port)
        self.msg = '{"key": "value"}'
        self.zmq_mock = MagicMock()
        self.zmq_mock.PUSH = transport.zmq.PUSH

        #set up the mock of the socket object
        self.socket_mock = MagicMock()
        #create a mock for the zmq context object
        self.context_mock = MagicMock()
        #have the mock context object return the mock socket
        # when the context.socket() method is called
        self.context_mock.socket.return_value = self.socket_mock
        #have the mock zmq module return the mocked context object
        # when the Context() constructor is called
        self.zmq_mock.Context.return_value = self.context_mock

        self.caster = transport.ZeroMQCaster(self.bind_host_tuple)

    def test_constructor(self):
        self.assertEqual(self.caster.socket_type, transport.zmq.PUSH)
        self.assertEqual(
            self.caster.bind_host,
            'tcp://{0}:{1}'.format(self.host, self.port))
        self.assertIsNone(self.caster.context)
        self.assertIsNone(self.caster.socket)
        self.assertFalse(self.caster.bound)

    def test_bind(self):
        with patch('meniscus.transport.zmq', self.zmq_mock):
            self.caster.bind()
        self.context_mock.socket.assert_called_once_with(transport.zmq.PUSH)
        self.socket_mock.bind.assert_called_once_with(
            'tcp://{0}:{1}'.format(self.host, self.port))
        self.assertTrue(self.caster.bound)

    def test_cast(self):
        with patch('meniscus.transport.zmq', self.zmq_mock):
            self.caster.bind()
        self.caster.cast(self.msg)
        self.socket_mock.send.assert_called_once_with(self.msg)

        self.caster.close()
        with self.assertRaises(transport.zmq.error.ZMQError):
            self.caster.cast(self.msg)

    def test_close(self):
        with patch('meniscus.transport.zmq', self.zmq_mock):
            self.caster.bind()
        self.caster.close()
        self.socket_mock.close.assert_called_once_with()
        self.context_mock.destroy.assert_called_once_with()
        self.assertIsNone(self.caster.context)
        self.assertIsNone(self.caster.socket)
        self.assertFalse(self.caster.bound)


class WhenIntegrationTestingTransport(unittest.TestCase):

    def setUp(self):
        self.host = '127.0.0.1'
        self.port = '5000'
        self.host_tuple = (self.host, self.port)
        self.connect_host_tuples = [self.host_tuple]

        self.msg = {"key": "value"}
        self.msg_json = json.dumps(self.msg)

    def test_message_transport_over_zmq(self):
        self.caster = transport.ZeroMQCaster(self.host_tuple)
        self.caster.bind()
        self.receiver = transport.ZeroMQReceiver(self.connect_host_tuples)

        class TestInputServer(transport.ZeroMQInputServer):
            def process_msg(self):
                self.test_stop = self._stop
                self.process_msg_called = True
                msg = self._get_msg()
                self.stop()

        self.server = TestInputServer(self.receiver)
        from multiprocessing import Process
        self.server_proc = Process(target=self.server.start)
        self.server_proc.start()
        import time
        time.sleep(1)
        self.caster.cast(self.msg_json)
        time.sleep(2)
        self.server_proc.terminate()

    def tearDown(self):
        self.server_proc.terminate()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = falcon_hooks_test
try:
    import testtools as unittest
except ImportError:
    import unittest

import io
import json
import falcon
import falcon.testing as testing

from meniscus.validation import SchemaLoader
from meniscus.validation.jsonv import JsonSchemaValidatorFactory
from meniscus.validation.integration.falcon_hooks import validation_hook


class SchemaMock(SchemaLoader):

    _SCHEMA = {
        'id': 'http://projectmeniscus.org/json/worker_configuration#',
        'type': 'object',
        'additionalProperties': False,

        'properties': {
            'animal':  {
                'enum': ['falcon', 'dog']
            }
        }
    }

    def load_schema(self, schema_ref):
        return self._SCHEMA

_validation_factory = JsonSchemaValidatorFactory(SchemaMock())


@falcon.before(validation_hook(_validation_factory.get_validator('mock')))
class ValidatedResource(object):

    def on_post(self, req, resp, validated_body):
        self.req = req
        self.resp = resp
        self.validated_body = validated_body


class TestValidationHook(testing.TestBase):

    def before(self):
        self.resource = ValidatedResource()
        self.api.add_route(self.test_route, self.resource)

    def test_unhandled_media_type(self):
        self.simulate_request(self.test_route,
                              method='POST',
                              headers={'content-type': 'application/xml'},
                              body=unicode('<animal type="falcon">'))

        self.assertEqual(falcon.HTTP_415, self.srmock.status)

    def test_valid_payload(self):
        self.simulate_request(self.test_route,
                              method='POST',
                              headers={'content-type': 'application/json'},
                              body=json.dumps({'animal': 'falcon'}))

        self.assertEqual(self.resource.validated_body, {'animal': 'falcon'})

    def test_invalid_payload(self):
        self.simulate_request(self.test_route,
                              method='POST',
                              headers={'content-type': 'application/json'},
                              body=json.dumps({'animal': 'cat'}))

        self.assertEqual(falcon.HTTP_400, self.srmock.status)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = jsonv_test
import unittest

from mock import MagicMock

from meniscus.validation.jsonv import (JsonSchemaValidatorFactory,
                                       DirectorySchemaLoader)


class WhenLoading(unittest.TestCase):

    def setUp(self):
        schema_loader = DirectorySchemaLoader('../etc/meniscus/schemas')
        validator_factory = JsonSchemaValidatorFactory(schema_loader)
        self.validator = validator_factory.get_validator('tenant')

    def tearDown(self):
        pass

    def test_should_validate_simple_tenant_object(self):
        tenant_obj = {
            'tenant': {
                'tenant_id': '12345'
            }
        }
        result = self.validator.validate(tenant_obj)
        self.assertTrue(result.valid)

    def test_should_reject_bad_tenant_id(self):
        tenant_obj = {
            'tenant': {
                'tenant_id': 12345
            }
        }

        result = self.validator.validate(tenant_obj)
        self.assertFalse(result.valid)

    def test_should_reject_additional_properties(self):
        tenant_obj = {
            'tenant': {
                'tenant_id': '12345',
                'cool': 'should fail'
            }
        }

        result = self.validator.validate(tenant_obj)
        self.assertFalse(result.valid)

    def test_should_reject_mutex_objects(self):
        tenant_obj = {
            'tenant': {
                'tenant_id': '12345'
            },
            'host': {
                'id': 12345
            }
        }

        result = self.validator.validate(tenant_obj)
        self.assertFalse(result.valid)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = transport
"""
The transport module defines the classes that serve as the transport layer for
Meniscus when passing log messages between nodes.  ZeroMQ is used as the
transport mechanism.
"""

from oslo.config import cfg
import simplejson as json
import zmq

import meniscus.config as config
from meniscus import env


_LOG = env.get_logger(__name__)


# ZMQ configuration options
_ZMQ_GROUP = cfg.OptGroup(
    name='zmq_in', title='ZeroMQ Input Options')

config.get_config().register_group(_ZMQ_GROUP)

_ZMQ_OPTS = [
    cfg.ListOpt('zmq_upstream_hosts',
                default=['127.0.0.1:5000'],
                help='list of upstream host:port pairs to poll for '
                     'zmq messages')
]

config.get_config().register_opts(_ZMQ_OPTS, group=_ZMQ_GROUP)

try:
    config.init_config()
except config.cfg.ConfigFilesNotFoundError as ex:
    _LOG.exception(ex.message)

_CONF = config.get_config()


class ZeroMQReceiver(object):
    """
    ZeroMQReceiver allows for messages to be received by pulling
    messages over a zmq socket from an upstream host.  This client may
    connect to multiple upstream hosts.
    """

    def __init__(self, connect_host_tuples):
        """
        Creates an instance of the ZeroMQReceiver.

        :param connect_host_tuples: [(host, port), (host, port)],
        for example [('127.0.0.1', '5000'), ('127.0.0.1', '5001')]
        """
        self.upstream_hosts = [
            "tcp://{}:{}".format(*host_tuple)
            for host_tuple in connect_host_tuples]
        self.socket_type = zmq.PULL
        self.context = None
        self.socket = None
        self.connected = False

    def connect(self):
        """
        Connect the receiver to upstream hosts.  Create a zmq.Context
        and a zmq.PULL socket, and is connect the socket to all
        specified host:port tuples.
        """
        self.context = zmq.Context()
        self.socket = self.context.socket(self.socket_type)

        for host in self.upstream_hosts:
            self.socket.connect(host)

        self.connected = True

    def get(self):
        """
        Read a message form the zmq socket and return
        """
        if not self.connected:
            raise zmq.error.ZMQError(
                "ZeroMQReceiver is not connected to a socket")
        return self.socket.recv()

    def close(self):
        """
        Close the zmq socket
        """
        if self.connected:
            self.socket.close()
            self.context.destroy()
            self.socket = None
            self.context = None
            self.connected = False


def new_zmq_receiver():
    """
    Factory method creates a new instance of ZeroMQReceiver to connect to all
    host:ports listed in zmq_upstream_hosts from meniscus config.
    """

    #build a list of (host, port) tuples from config
    upstream_hosts = [
        (host_port_str.split(':'))
        for host_port_str in _CONF.zmq_in.zmq_upstream_hosts
    ]

    return ZeroMQReceiver(upstream_hosts)


class ZeroMQInputServer(object):
    """
    ZeroMQInputServer is a base class creates an IO Loop that continues
    to pull messages through a ZeroMQReceiver for processing.
    This class should be inherited and the process_msg() method overridden in
    order to implement the desired behavior.
    """

    def __init__(self, zmq_receiver):
        """
        Creates a new instance of ZeroMQInputServer by setting the receiver to
        be used to pull messages.

        :param zmq_receiver: an instance of ZeroMQReceiver
        """
        self.zmq_receiver = zmq_receiver
        self._stop = True

    def start(self):
        """
        Connect the ZeroMQReceiver and start the server IO loop to
        process messages. The receiver is connected here so that this method
        can easily be passed as a runnable to a child process, as zmq should
        not share context and sockets between a parent and child process.
        """
        self.zmq_receiver.connect()
        self._stop = False

        while not self._stop:
            self.process_msg()

    def stop(self):
        """
        set the server control variable that will break the IO Loop
        """
        self._stop = True

    def process_msg(self):
        """
        This method should be overridden to implement the desired message
        processing.  To retrieve the message for processing you can call:
        >>>  msg = self._get_msg()
        """
        pass

    def _get_msg(self):
        """
        Pulls a JSON message received over the ZeroMQ socket.  This call will
        block until a message is received.
        """
        try:
            msg = self.zmq_receiver.get()
            return json.loads(msg)
        except Exception as ex:
            _LOG.exception(ex)


class ZeroMQCaster(object):
    """
    ZeroMQCaster allows for messages to be sent downstream by pushing
    messages over a zmq socket to downstream clients.  If multiple clients
    connect to this PUSH socket the messages will be load balanced evenly
    across the clients.
    """

    def __init__(self, bind_host_tuple):
        """
        Creates an instance of the ZeroMQCaster.  A zmq PUSH socket is
        created and is bound to the specified host:port.

        :param bind_host_tuple: (host, port), for example ('127.0.0.1', '5000')
        """

        self.socket_type = zmq.PUSH
        self.bind_host = 'tcp://{0}:{1}'.format(*bind_host_tuple)
        self.context = None
        self.socket = None
        self.bound = False

    def bind(self):
        """
        Bind the ZeroMQCaster to a host:port to push out messages.
        Create a zmq.Context and a zmq.PUSH socket, and bind the
        socket to the specified host:port
        """
        self.context = zmq.Context()
        self.socket = self.context.socket(self.socket_type)
        self.socket.bind(self.bind_host)
        self.bound = True

    def cast(self, msg):
        """
        Sends a message over the zmq PUSH socket
        """
        if not self.bound:
            raise zmq.error.ZMQError(
                "ZeroMQCaster is not bound to a socket")
        try:
            self.socket.send(msg)
        except Exception as ex:
            _LOG.exception(ex)

    def close(self):
        """
        Close the zmq socket
        """
        if self.bound:
            self.socket.close()
            self.context.destroy()
            self.socket = None
            self.context = None
            self.bound = False

########NEW FILE########
__FILENAME__ = falcon_hooks
import json
import falcon

from meniscus import env


_LOG = env.get_logger(__name__)


def _load_json_body(stream):
    try:
        raw_json = stream.read()
    except Exception as ex:
        raise falcon.HTTPError(falcon.HTTP_500, 'Streaming body I/O error')

    try:
        return json.loads(raw_json)
    except ValueError as ve:
        raise falcon.HTTPError(falcon.HTTP_400, 'Malformed JSON body')


def validation_hook(validator):
    """
    This function creates a validator before hook for a falcon resource. Upon
    validation, the hook passes parameters to the request handler. Upon success
    the hook sets the 'validated' parameter to True and the 'doc' parameter
    equal to the parsed request body as a python array or dictionary.

    If the media type of the content is not JSON, this hook sets the
    'validated' parameter to False and the 'doc' parameter to None.

    If validation fails, this hook responds to the requester with a 400 and a
    detail message.
    """
    def validate(req, resp, params):
        params['validated_body'] = None

        # We only care about JSON content types
        if not (req.content_type
                and req.content_type.lower() == 'application/json'):

            _LOG.debug(
                'Failed validation: {0}'.format('Unsupported Media Type'))

            raise falcon.HTTPError(falcon.HTTP_415, 'Unsupported Media Type')

        json_body = _load_json_body(req.stream)
        result = validator.validate(json_body)

        if not result.valid:
            _LOG.debug(
                'Failed validation: {0}'.format(result.error.message))
            raise falcon.HTTPError(falcon.HTTP_400, result.error.message)

        # Set a custom parameters on the request
        params['validated_body'] = json_body
    return validate

########NEW FILE########
__FILENAME__ = jsonv
import os
import json

from meniscus.validation import *
from jsonschema import validate, ValidationError


class DirectorySchemaLoader(SchemaLoader):

    def __init__(self, *directories):
        self.directories = [
            d[0:len(d)-1] if d.endswith(os.sep) else d for d in directories]

    def load_schema(self, schema_ref):
        for directory in self.directories:
            formatted_path = '{}{}{}'.format(directory, os.sep, schema_ref)
            if os.path.isfile(formatted_path):
                return self._read_json(formatted_path)
        raise SchemaNotFoundError(schema_ref)

    def _read_json(self, schema_file):
        try:
            return json.loads(open(schema_file, 'r').read())
        except Exception as ex:
            raise MalformedSchemaError(schema_file, ex)


class JsonSchemaValidatorFactory(ValidatorFactory):

    def __init__(self, schema_loader):
        self.schema_loader = schema_loader

    def get_validator(self, schema_name):
        if not schema_name.endswith('.json'):
            schema_ref = '{}.json'.format(schema_name)
        else:
            schema_ref = schema_name
        return JsonSchemaValidator(self.schema_loader.load_schema(schema_ref))


class JsonSchemaValidator(ObjectValidator):

    def __init__(self, schema):
        self.schema = schema

    def validate(self, obj_graph):
        try:
            validate(obj_graph, self.schema)
            return ValidationResult(True)
        except ValidationError as ve:
            return ValidationResult(False, ve)

########NEW FILE########
