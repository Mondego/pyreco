__FILENAME__ = api
from awsfabrictasks.ec2.api import Ec2InstanceWrapper
from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.rds.api import RdsInstanceWrapper



class AwsEnvironment(object):
    """
    .. warning::
        This class is experimental, so we may make backwards-incompatible
        changes to it in the future.
    """
    #: The tag used to mark EC2 instances with their environment
    ec2_environment_tag = 'environment'

    def __init__(self, environment, region=None):
        """
        :param environment:
            The name of the environment. See: :meth:`.get_rds_instances`,
            :meth:`.get_ec2_instancewrappers`.
        :param region:
            The region where this environment belongs. Defaults to
            ``awsfab_settings.DEFAULT_REGION``.
        """
        self.environment = environment
        self.region = region or awsfab_settings.DEFAULT_REGION

    def get_rds_instancewrappers(self):
        """
        Get all RDS instances where the ID is prefixed with :obj:`.environment`.
        """
        dbinstancewrappers = RdsInstanceWrapper.get_all_dbinstancewrappers(region=self.region)
        return filter(lambda w: w.get_id().startswith(self.environment), dbinstancewrappers)

    def get_ec2_instancewrappers(self, tags={}):
        alltags = {}
        alltags.update(tags)
        alltags[self.ec2_environment_tag] = self.environment
        instancewrappers = Ec2InstanceWrapper.get_by_tagvalue(tags=alltags, region=self.region)
        return instancewrappers


def create_hostslist_from_environment(environment):
    awsenvironment = AwsEnvironment(environment)
    instancewrappers = awsenvironment.get_ec2_instancewrappers()

########NEW FILE########
__FILENAME__ = tasks
"""
Tasks for managing groups of AWS servers.
"""
from fabric.api import task

#from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.ec2.api import print_ec2_instance
from awsfabrictasks.rds.api import print_rds_instance
from .api import AwsEnvironment



__all__ = [
        'awsenv_print',
        ]


@task
def awsenv_print(environment):
    """
    Print information about all EC2 and RDS instances in the given AWS-environment.

    :param environment:
        The name of the environment.
    """
    awsenvironment = AwsEnvironment(environment)
    print '-' * 80
    print 'EC2 instances:'
    print '-' * 80
    try:
        instancewrappers = awsenvironment.get_ec2_instancewrappers()
    except LookupError, e:
        print str(e)
    else:
        for instancewrapper in instancewrappers:
            print
            print '{0}:'.format(instancewrapper.prettyname())
            print_ec2_instance(instancewrapper.instance)

    print
    print '-' * 80
    print 'RDS instances:'
    print '-' * 80
    dbinstancewrappers = awsenvironment.get_rds_instancewrappers()
    for dbinstancewrapper in dbinstancewrappers:
        print
        print_rds_instance(dbinstancewrapper.dbinstance)

########NEW FILE########
__FILENAME__ = conf
import sys
from os.path import expanduser, join, exists, dirname
from pprint import pprint
from fabric.api import task, env
from warnings import warn

import default_settings

__all__ = ['Settings', 'print_settings', 'default_settings']



def import_module(name, package=None):
    __import__(name)
    return sys.modules[name]

class Settings(object):
    """
    Settings object inspired by django.conf.settings.
    """
    def __init__(self):
        self._apply_settings_from_module(default_settings)
        self._is_loaded = False

    def __getattribute__(self, attr):
        """
        Load settings automatically the first time an uppercase attribute
        (setting) is requested.
        """
        if attr.upper() == attr:
            if not self._is_loaded:
                if hasattr(env, 'awsfab_settings_module'):
                    self.load(env.awsfab_settings_module)
                else:
                    warn('Could not find the env.awsfab_settings_module. Make sure you run run awsfab tasks using the ``awsfab`` command (not fab)?')
        return super(Settings, self).__getattribute__(attr)

    def load(self, settings_module):
        if self._is_loaded:
            raise Exception('Can only load settings once.')
        custom_settings = import_module(settings_module)
        self._apply_settings_from_module(custom_settings)

        try:
            local_settings = import_module(settings_module + '_local')
        except ImportError:
            pass
        else:
            self._apply_settings_from_module(local_settings)
        self._is_loaded = True

    def set_settings(self, **settings):
        """
        Set all all the given settings as attributes of this object.

        :raise ValueError: If any of the keys in ``settings`` is not uppercase.
        """
        for key, value in settings.iteritems():
            if not self._is_setting(key):
                raise ValueError('Settings must be all uppercase, and they can not begin with userscore (``_``).')
            setattr(self, key, value)

    def _is_setting(self, attrname):
        return attrname == attrname.upper() and not attrname.startswith('_')

    def _apply_settings_from_module(self, settings_module):
        for setting in dir(settings_module):
            if self._is_setting(setting):
                setattr(self, setting, getattr(settings_module, setting))

    def as_dict(self):
        """
        Get all settings (uppercase attributes on this object) as a dict.
        """
        dct = {}
        for attrname, value in self.__dict__.iteritems():
            if attrname.upper() == attrname:
                dct[attrname] = value
        return dct

    def pprint(self):
        """
        Prettyprint the settings.
        """
        pprint(self.as_dict())

    def clear_settings(self):
        """
        Clear all settings (intended for testing). Deletes all uppercase attributes.
        """
        for setting in dir(self):
            if self._is_setting(setting):
                delattr(self, setting)

    def reset_settings(self, **settings):
        """
        Reset settings (intended for testing). Shortcut for::

            clear_settings()
            set_settings(**settings)
        """
        self.clear_settings()
        self.set_settings(**settings)

awsfab_settings = Settings()



@task
def print_settings():
    """
    Pretty-print the settings as they are seen by the system.
    """
    awsfab_settings.pprint()



@task
def print_default_settings():
    """
    Print ``default_settings.py``.
    """
    path = join(dirname(default_settings.__file__), 'default_settings.py')
    print open(path).read()

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps
from fabric.decorators import _wrap_as_new
from .ec2.api import Ec2InstanceWrapper


def _list_annotating_decorator(attribute, *values):
    def attach_list(func):
        @wraps(func)
        def inner_decorator(*args, **kwargs):
            return func(*args, **kwargs)
        _values = values
        # Allow for single iterable argument as well as *args
        if len(_values) == 1 and not isinstance(_values[0], basestring):
            _values = _values[0]
        setattr(inner_decorator, attribute, list(_values))
        # Don't replace @task new-style task objects with inner_decorator by
        # itself -- wrap in a new Task object first.
        inner_decorator = _wrap_as_new(func, inner_decorator)
        return inner_decorator
    return attach_list


def ec2instance(nametag=None, instanceid=None, tags=None, region=None):
    """
    Wraps the decorated function to execute as if it had been invoked with
    ``--ec2names`` or ``--ec2ids``.
    """
    if instanceid:
        instancewrappers = [Ec2InstanceWrapper.get_by_instanceid(instanceid)]
    elif nametag:
        instancewrappers = [Ec2InstanceWrapper.get_by_nametag(nametag)]
    elif tags:
        instancewrappers = Ec2InstanceWrapper.get_by_tagvalue(tags, region)
    else:
        raise ValueError('nametag, instanceid, or tags must be supplied.')

    return _list_annotating_decorator('hosts', [instancewrapper['public_dns_name']
        for instancewrapper in instancewrappers])

########NEW FILE########
__FILENAME__ = default_settings

#: The AWS access key. Should look something like this::
#:
#:    AUTH = {'aws_access_key_id': 'XXXXXXXXXXXXXXXXX',
#:            'aws_secret_access_key': 'aaaaaaaaaaaa\BBBBBBBBB\dsaddad'}
#:
AUTH = {}

#: The default AWS region to use with the commands where REGION is supported.
DEFAULT_REGION = 'eu-west-1'

#: Default ssh user if the ``awsfab-ssh-user`` tag is not set
EC2_INSTANCE_DEFAULT_SSHUSER = 'root'

#: Directories to search for "<key_name>.pem". These paths are filtered through
#: os.path.expanduser, so paths like ``~/.ssh/`` works.
KEYPAIR_PATH = ['.', '~/.ssh/']


#: Extra SSH arguments. Used with ``ssh`` and ``rsync``.
EXTRA_SSH_ARGS = '-o StrictHostKeyChecking=no'

#: Configuration for ec2_launch_instance (see the docs)
EC2_LAUNCH_CONFIGS = {}


#: S3 bucket suffix. This is used for all tasks taking bucketname as parameter.
#: The actual bucketname used become::
#:
#:      S3_BUCKET_PATTERN.format(bucketname=bucketname)
#:
#: This is typically used to add your domain name or company name to all bucket
#: names, but avoid having to type the entire name for each task. Examples::
#:
#:     S3_BUCKET_PATTERN = '{bucketname}.example.com'
#:     S3_BUCKET_PATTERN = 'example.com.{bucketname}'
#:
#: The default, ``"{bucketname}"``, uses the bucket name as provided by the
#: user without any changes.
#:
#: .. seealso::
#:      :meth:`awsfabrictasks.s3.api.S3ConnectionWrapper.get_bucket_using_pattern`,
#:      :func:`awsfabrictasks.s3.api.settingsformat_bucketname`
S3_BUCKET_PATTERN = '{bucketname}'

########NEW FILE########
__FILENAME__ = api
from os.path import exists, join, expanduser, abspath
from warnings import warn
from pprint import pformat
from boto.ec2 import connect_to_region
from fabric.api import local, env, abort

from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.utils import rsyncformat_path

def zipit(ss):
    """
    Returns a string containing a user_data compatible gzip-file
    of the zipped ss input.
    Note(using zlib alone is not sufficient - we need a zipfile structure)
    """
    import StringIO
    import gzip
    out = StringIO.StringIO()
    f = gzip.GzipFile(fileobj=out, mode='w')
    f.write(ss)
    f.close()
    return out.getvalue()

def ec2_rsync_upload_command(instancewrapper, local_dir, remote_dir,
                             rsync_args='-av', sync_content=False):
    """
    Returns the rsync command used by :func:`ec2_rsync_upload`. Takes the
    same parameters as :func:`ec2_rsync_upload`, except for the first
    parameter, ``instancewrapper``, which is a :class:`Ec2InstanceWrapper`
    object.
    """
    ssh_uri = instancewrapper.get_ssh_uri()
    key_filename = instancewrapper.get_ssh_key_filename()
    extra_ssh_args = awsfab_settings.EXTRA_SSH_ARGS
    local_dir = rsyncformat_path(local_dir, sync_content)
    rsync_cmd = ('rsync {rsync_args} -e "ssh -i {key_filename} {extra_ssh_args}" '
                 '{local_dir} {ssh_uri}:{remote_dir}').format(**vars())
    return rsync_cmd

def ec2_rsync_upload(local_dir, remote_dir, rsync_args='-av', sync_content=False):
    """
    rsync ``local_dir`` into ``remote_dir`` on the current EC2 instance (the
    one returned by :meth:`Ec2InstanceWrapper.get_from_host_string`).

    :param sync_content: Normally the function automatically makes sure
        ``local_dir`` is not suffixed with ``/``, which makes rsync copy
        ``local_dir`` into ``remote_dir``. With ``sync_content=True``,
        the content of ``local_dir`` is synced into ``remote_dir`` instead.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    rsync_cmd = ec2_rsync_upload_command(instancewrapper, local_dir, remote_dir,
                                         rsync_args, sync_content)
    local(rsync_cmd)

def ec2_rsync(*args, **kwargs):
    """
    .. deprecated:: 1.0.13
        Use :func:`ec2_rsync_upload` instead.
    """
    warn('Deprecated since 1.0.13. Use ec2_rsync_upload instead.', DeprecationWarning)
    return ec2_rsync_upload(*args, **kwargs)

def ec2_rsync_download_command(instancewrapper, remote_dir, local_dir,
                               rsync_args='-av', sync_content=False):
    """
    Returns the rsync command used by :func:`ec2_rsync_download`. Takes the
    same parameters as :func:`ec2_rsync_download`, except for the first
    parameter, ``instancewrapper``, which is a :class:`Ec2InstanceWrapper`
    object.
    """
    ssh_uri = instancewrapper.get_ssh_uri()
    key_filename = instancewrapper.get_ssh_key_filename()
    extra_ssh_args = awsfab_settings.EXTRA_SSH_ARGS
    remote_dir = rsyncformat_path(remote_dir, sync_content)
    rsync_cmd = ('rsync {rsync_args} -e "ssh -i {key_filename} {extra_ssh_args}" '
                 '{ssh_uri}:{remote_dir} {local_dir}').format(**vars())
    return rsync_cmd

def ec2_rsync_download(remote_dir, local_dir, rsync_args='-av', sync_content=False):
    """
    rsync ``remote_dir`` on the current EC2 instance (the
    one returned by :meth:`Ec2InstanceWrapper.get_from_host_string`) into
    ``local_dir``.

    :param sync_content: Normally the function automatically makes sure
        ``local_dir`` is not suffixed with ``/``, which makes rsync copy
        ``local_dir`` into ``remote_dir``. With ``sync_content=True``,
        the content of ``local_dir`` is synced into ``remote_dir`` instead.
    """
    instance = Ec2InstanceWrapper.get_from_host_string()
    rsync_cmd = ec2_rsync_download_command(instance, remote_dir, local_dir,
                                           rsync_args, sync_content)
    local(rsync_cmd)


def _parse_instanceident(instanceid_with_optional_region):
    if ':' in instanceid_with_optional_region:
        region, instanceid = instanceid_with_optional_region.split(':', 1)
    else:
        instanceid = instanceid_with_optional_region
        region = awsfab_settings.DEFAULT_REGION
    return region, instanceid


def parse_instanceid(instanceid_with_optional_region):
    """
    Parse instance id with an optional region-name prefixed. Region name
    is specified by prefixing the instanceid with ``<regionname>:``.

    :return: (region, instanceid) where region defaults to
        ``awsfab_settings.DEFAULT_REGION`` if not prefixed to the id.
    """
    return _parse_instanceident(instanceid_with_optional_region)

def parse_instancename(instancename_with_optional_region):
    """
    Just like :func:`parse_instanceid`, however this is for instance names.
    We keep them as separate functions in case they diverge in the future.

    :return: (region, instanceid) where region defaults to
        ``awsfab_settings.DEFAULT_REGION`` if not prefixed to the name.
    """
    return _parse_instanceident(instancename_with_optional_region)


class Ec2RegionConnectionError(Exception):
    """
    Raised when we fail to connect to a region.
    """
    def __init__(self, region):
        self.region = region
        msg = 'Could not connect to region: {region}'.format(**vars())
        super(Ec2RegionConnectionError, self).__init__(msg)


class InstanceLookupError(LookupError):
    """
    Base class for instance lookup errors.
    """

class MultipleInstancesWithSameNameError(InstanceLookupError):
    """
    Raised when multiple instances with the same nametag is discovered.
    (see: :meth:`Ec2InstanceWrapper.get_by_nametag`)
    """

class NoInstanceWithNameFound(InstanceLookupError):
    """
    Raised when no instace with the requested name is found in
    :meth:`Ec2InstanceWrapper.get_by_nametag`.
    """

class NotExactlyOneInstanceError(InstanceLookupError):
    """
    Raised when more than one instance is found when expecting exactly one instance.
    """

class Ec2InstanceWrapper(object):
    """
    Wraps a :class:`boto.ec2.instance.Instance` with convenience functions.

    :ivar instance: The :class:`boto.ec2.instance.Instance`.
    """
    def __init__(self, instance):
        """
        :param instance: A :class:`boto.ec2.instance.Instance` object.
        """
        self.instance = instance

    def __getitem__(self, key):
        """
        Provides easy access to attributes in ``self.instance``.
        """
        return getattr(self.instance, key)

    def __str__(self):
        return 'Ec2InstanceWrapper:{0}'.format(self.prettyname())

    def __repr__(self):
        return 'Ec2InstanceWrapper({0})'.format(self.prettyname())

    def is_running(self):
        """
        Return ``True`` if state=='running'.
        """
        return self.instance.state == 'running'

    def is_stopped(self):
        """
        Return ``True`` if state=='stopped'.
        """
        return self.instance.state == 'stopped'

    def prettyname(self):
        """
        Return a pretty-formatted name for this instance, using the Name-tag if
        the instance is tagged with it.
        """
        instanceid = self.instance.id
        name = self.instance.tags.get('Name')
        if name:
            return '{instanceid} (name={name})'.format(**vars())
        else:
            return instanceid

    def get_ssh_uri(self):
        """
        Get the SSH URI for the instance.

        :return: "<instance.tags['awsfab-ssh-user']>@<instance.public_dns_name>"
        """
        user = self['tags'].get('awsfab-ssh-user', awsfab_settings.EC2_INSTANCE_DEFAULT_SSHUSER)
        host = self['public_dns_name']
        return '{user}@{host}'.format(**vars())

    def get_ssh_key_filename(self):
        """
        Get the SSH indentify filename (.pem-file) for the instance. Searches
        ``awsfab_settings.KEYPAIR_PATH`` for ``"<instance.key_name>.pem"``.

        :raise LookupError: If the key is not found.
        """
        path = awsfab_settings.KEYPAIR_PATH
        key_name = self.instance.key_name + '.pem'
        for dirpath in path:
            filename = abspath(join(expanduser(dirpath), key_name))
            if exists(filename):
                return filename
        raise LookupError('Could not find {key_name} in awsfab_settings.KEYPAIR_PATH: {path!r}'.format(**vars()))

    def add_instance_to_env(self):
        """
        Add ``self`` to ``fabric.api.env.ec2instances[self.get_ssh_uri()]``,
        and register the key-pair for the instance in
        ``fabric.api.env.key_filename``.
        """
        if not 'ec2instances' in env:
            env['ec2instances'] = {}
        env['ec2instances'][self.get_ssh_uri()] = self
        if not env.key_filename:
            env.key_filename = []
        key_filename = self.get_ssh_key_filename()
        if not key_filename in env.key_filename:
            env.key_filename.append(key_filename)

    @classmethod
    def get_by_nametag(cls, instancename_with_optional_region):
        """
        Connect to AWS and get the EC2 instance with the given Name-tag.

        :param instancename_with_optional_region:
            Parsed with :func:`parse_instancename` to find the region and name.
        :raise Ec2RegionConnectionError: If connecting to the region fails.
        :raise InstanceLookupError:
            Or one of its subclasses if the requested instance was not found in
            the region.
        :return: A :class:`Ec2InstanceWrapper` contaning the requested instance.
        """
        region, name = parse_instancename(instancename_with_optional_region)
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise Ec2RegionConnectionError(region)
        reservations = connection.get_all_instances(filters={'tag:Name': name})
        if len(reservations) == 0:
            raise NoInstanceWithNameFound('No ec2 instances with tag:Name={0}'.format(name))
        if len(reservations) > 1:
            raise MultipleInstancesWithSameNameError('More than one ec2 reservations with tag:Name={0}'.format(name))
        reservation = reservations[0]
        if len(reservation.instances) != 1:
            raise NotExactlyOneInstanceError('Did not get exactly one instance with tag:Name={0}'.format(name))
        return cls(reservation.instances[0])

    @classmethod
    def get_by_tagvalue(cls, tags={}, region=None):
        """
        Connect to AWS and get the EC2 instance with the given tag:value pairs.

        :param tags
            A string like 'role=testing,fake=yes' to AND a set of ec2
            instance tags
        :param region:
            optional.
        :raise Ec2RegionConnectionError: If connecting to the region fails.
        :return: A list of :class:`Ec2InstanceWrapper`s containing the
            matching instances.
        """

        region = region is None and awsfab_settings.DEFAULT_REGION or region
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise Ec2RegionConnectionError(region)
        tags = dict((('tag:%s' % oldk, v) for (oldk, v) in tags.iteritems()))
        reservations = connection.get_all_instances(filters=tags)
        if len(reservations) == 0:
            return []

        insts = []
        for r in reservations:
            for instance in r.instances:
                insts.append(cls(instance))
        return insts


    @classmethod
    def get_exactly_one_by_tagvalue(cls, tags, region=None):
        """
        Use :meth:`.get_by_tagvalue` to find instances by ``tags``, but
        raise ``LookupError`` if not exactly one instance is found.
        """
        instances = cls.get_by_tagvalue(tags, region)
        if not len(instances) == 1:
            raise LookupError('Got more than one instance matching {0!r} in region={1!r}'.format(tags, region))
        return instances[0]


    @classmethod
    def get_by_instanceid(cls, instanceid):
        """
        Connect to AWS and get the EC2 instance with the given instance ID.

        :param instanceid_with_optional_region:
            Parsed with :func:`parse_instanceid` to find the region and name.
        :raise Ec2RegionConnectionError: If connecting to the region fails.
        :raise LookupError: If the requested instance was not found in the region.
        :return: A :class:`Ec2InstanceWrapper` contaning the requested instance.
        """
        region, instanceid = parse_instanceid(instanceid)
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise Ec2RegionConnectionError(region)
        reservations = connection.get_all_instances([instanceid])
        if len(reservations) == 0:
            raise LookupError('No ec2 instances with instanceid={0}'.format(instanceid))
        reservation = reservations[0]
        if len(reservation.instances) != 1:
            raise LookupError('Did not get exactly one instance with instanceid={0}'.format(instanceid))
        return cls(reservation.instances[0])

    @classmethod
    def get_from_host_string(cls):
        """
        If an instance has been registered in ``fabric.api.env`` using
        :meth:`add_instance_to_env`, this method can be used to get
        the instance identified by ``fabric.api.env.host_string``.
        """
        return env.ec2instances[env.host_string]



class WaitForStateError(Exception):
    """
    Raises when :func:`wait_for_state` times out.
    """


def wait_for_state(instanceid, state_name, sleep_intervals=[15, 5], last_sleep_repeat=40):
    """
    Poll the instance with ``instanceid`` until its ``state_name`` matches the
    desired ``state_name``.

    The first poll is performed without any delay, and the rest of the polls are
    performed according to ``sleep_intervals``.

    :param instanceid: ID of an instance.
    :param state_name: The state_name to wait for.
    :param sleep_intervals: List of seconds to wait between each poll for state. The first poll
        is made immediately, then we wait for sleep_intervals[0] seconds before the next poll,
        and repeat for each item in sleep_intervals. Then we repeat for ``last_sleep_repeat``
        using the last item in ``sleep_intervals`` as the timout for each wait.
    :param last_sleep_repeat:
        Number of times to repeat the last item in ``sleep_intervals``. If this
        is 20, we will wait for a maximum of ``sum(sleep_intervals) + sleep_intervals[-1]*20``.
    """
    from time import sleep
    region, instanceid = parse_instanceid(instanceid)
    sleep_intervals.extend([sleep_intervals[-1] for x in xrange(last_sleep_repeat)])
    max_wait_sec = sum(sleep_intervals)
    print 'Waiting for {instanceid} to change state to: "{state_name}". Will try for {max_wait_sec}s.'.format(**vars())

    sleep_intervals_len = len(sleep_intervals)
    for index, sleep_sec in enumerate(sleep_intervals):
        instancewrapper = Ec2InstanceWrapper.get_by_instanceid(instanceid)
        current_state_name = instancewrapper['state']
        if current_state_name == state_name:
            print '.. OK'
            return
        index_n1 = index + 1
        print '.. Current state: "{current_state_name}". Next poll ({index_n1}/{sleep_intervals_len}) for "{state_name}"-state in {sleep_sec}s.'.format(**vars())
        sleep(sleep_sec)
    raise WaitForStateError('Desired state, "{state_name}", not achieved in {max_wait_sec}s.'.format(**vars()))


def wait_for_stopped_state(instanceid, **kwargs):
    """
    Shortcut for ``wait_for_state(instanceid, 'stopped', **kwargs)``.
    """
    wait_for_state(instanceid, 'stopped', **kwargs)

def wait_for_running_state(instanceid, **kwargs):
    """
    Shortcut for ``wait_for_state(instanceid, 'running', **kwargs)``.
    """
    wait_for_state(instanceid, 'running', **kwargs)


def print_ec2_instance(instance, full=False, indentspaces=3):
    """
    Print attributes of an ec2 instance.

    :param instance: A :class:`boto.ec2.instance.Instance` object.
    :param full: Print all attributes? If not, a subset of the attributes are printed.
    :param indentspaces: Number of spaces to indent each line in the output.
    """
    indent = ' ' * indentspaces
    if full:
        attrnames = sorted(instance.__dict__.keys())
    else:
        attrnames = ['state', 'instance_type', 'ip_address', 'public_dns_name',
                     'private_dns_name', 'private_ip_address',
                     'key_name', 'tags', 'placement']
    for attrname in attrnames:
        if attrname.startswith('_'):
            continue
        try:
            value = instance.__dict__[attrname]
        except KeyError:
            try:
                # Simple backward compatible workaround to boto 2.6.0 attr
                # changes with _state and _placement
                value = instance.__dict__['_' + attrname]
            except KeyError:
                value = '**key "{k}" and "_{k}" missing**'.format(k=attrname)
        if not isinstance(value, (str, unicode, bool, int)):
            value = pformat(value, indent=indentspaces+3)
        print '{indent}{attrname}: {value}'.format(**vars())



class Ec2LaunchInstance(object):
    """
    Launch instances configured in ``awsfab_settings.EC2_LAUNCH_CONFIGS``.

    Example::

        launcher = Ec2LaunchInstance(extra_tags={'Name': 'mytest'})
        launcher.confirm()
        instance = launcher.run_instance()

    Note that this class is optimized for the following use case:

        - Create one or more instances (initialize one or more Ec2LaunchInstance).
        - Confirm using :meth:`.confirm` or :meth:`.confirm_many`.
        - Launch each instance using meth:`Ec2LaunchInstance.run_instance` or :meth:`Ec2LaunchInstance.run_many_instances`.
        - Use :meth:`Ec2LaunchInstance.wait_for_running_state_many` to wait for all instances to launch.
        - Do something with the running instances.

    Example of launching many instances::

        a = Ec2LaunchInstance(extra_tags={'Name': 'a'})
        b = Ec2LaunchInstance(extra_tags={'Name': 'b'})
        Ec2LaunchInstance.confirm_many([a, b])
        Ec2LaunchInstance.run_many_instances([a, b])
        # Note: that we can start doing stuff with ``a`` and ``b`` that does not
        # require the instances to be running, such as setting tags.
        Ec2LaunchInstance.wait_for_running_state_many([a, b])
    """

    #: Number of seconds to sleep before retrying when adding tags gets EC2ResponseError.
    tag_retry_sleep = 2

    #: Number of times to retry when adding tags gets EC2ResponseError.
    tag_retry_count = 4

    @classmethod
    def wait_for_running_state_many(cls, launchers, **kwargs):
        """
        Loop through ``launchers`` and run :func:`wait_for_running_state`.

        :param launchers:
            List of Ec2LaunchInstance objects that have been lauched with
            :meth:`Ec2LaunchInstance.run_instance`.
        :param kwargs:
            Forwarded to :func:`wait_for_running_state`.
        """
        for launcher in launchers:
            wait_for_running_state(launcher.instance.id, **kwargs)

    @classmethod
    def run_many_instances(cls, launchers):
        """
        Loop through ``launchers`` and run :func:`run_instance`.

        :param launchers:
            List of Ec2LaunchInstance objects.
        :param kwargs:
            Forwarded to :func:`wait_for_running_state`.
        """
        for launcher in launchers:
            launcher.run_instance()

    @classmethod
    def confirm_many(cls, launchers):
        """
        Loop through
        Use :meth:`prettyprint` to show the user their choices, and ask
        for confirmation. Runs ``fabric.api.abort()`` if the user does
        not confirm the choices.
        """
        from textwrap import fill
        print fill('Are you sure you want to launch (create) the following new instances '
                   'with the following settings and tags?', 80)
        print '-' * 80
        for launcher in launchers:
            print
            print launcher.prettyformat()
        print '-' * 80
        Ec2LaunchInstance._confirm('Create instances')

    @staticmethod
    def _confirm(question):
        if raw_input(question + ' [y/N]? ').lower() != 'y':
            abort('Aborted')

    def __init__(self, extra_tags={}, configname=None,
                 configname_help='Please select one of the following configurations:',
                 duplicate_name_protection=True):
        """
        Initialize the launcher. Runs :meth:`create_config_ask_if_none`.

        :param configname:
            Name of a configuration in
            ``awsfab_settings.EC2_LAUNCH_CONFIGS``.
            If it is ``None``, we ask the user for the configfile.
        :param configname_help:
            The help to show above the prompt for configname input (only used
            if ``configname`` is ``None``.
        """
        if not awsfab_settings.EC2_LAUNCH_CONFIGS:
            abort('You have no awsfab_settings.EC2_LAUNCH_CONFIGS.')
        self.extra_tags = extra_tags

        #: A config dict from awsfab_settings.EC2_LAUNCH_CONFIGS.
        self.conf = {}

        #: Keyword arguments for ``run_instances()``.
        self.kw = {}

        #: See the docs for the __init__ parameter.
        self.configname = configname

        #: See the docs for the __init__ parameter.
        self.configname_help = configname_help

        #: The instance launced by :meth:`.run_instance`. None when
        #: run_instance() has not been invoked.
        self.instance = None

        self.create_config_ask_if_none()
        if duplicate_name_protection:
            self.check_if_name_exists()

    def _ask_for_configname(self):
        """
        Ask the user for a configname.

        :return: The user-provided configname.
        """
        print self.configname_help
        print '-' * 80
        fmt = '{0:>30} | {1}'
        print fmt.format('NAME', 'DESCRIPTION')
        for configname, config in awsfab_settings.EC2_LAUNCH_CONFIGS.iteritems():
            description = config.get('description', '')
            print fmt.format(configname, description)
        print '-' * 80
        configname = raw_input('Type name of config: ').strip()
        return configname

    def _configure(self, configname):
        if not configname in awsfab_settings.EC2_LAUNCH_CONFIGS:
            abort('"{configname}" is not in awsfab_settings.EC2_LAUNCH_CONFIGS'.format(**vars()))
        conf = awsfab_settings.EC2_LAUNCH_CONFIGS[configname]
        kw = dict(key_name = conf['key_name'],
                  instance_type = conf['instance_type'],
                  security_groups = conf['security_groups'])
        try:
            user_data = zipit(conf['user_data'])
            kw['user_data'] = user_data
        except KeyError:
            pass
        if 'availability_zone' in conf:
            kw['placement'] = conf['region'] + conf['availability_zone']
        self.conf = conf
        self.kw = kw

    def check_if_name_exists(self):
        import sys
        name = self.get_all_tags().get('Name')
        if name:
            print
            sys.stdout.write('Making sure no EC2 instance with Name={0} exists...'.format(name))
            sys.stdout.flush()
            try:
                wrapper = Ec2InstanceWrapper.get_by_nametag(name)
            except NoInstanceWithNameFound:
                pass
            else:
                abort('An instance named {name} already exists.'.format(name=name))
            print 'OK'
            print

    def create_config_ask_if_none(self):
        """
        Set :obj:`.kw` and :obj:`.conf` using :obj:`configname`.
        Prompt the user for a configname if bool(:obj:`.configname`) is
        ``False``.
        """
        if not self.configname:
            self.configname = self._ask_for_configname()
        self._configure(self.configname)

    def get_all_tags(self):
        """
        Merge tags from the awsfab_settings.EC2_LAUNCH_CONFIGS config, and the
        ``extra_tags`` parameter for __init__, and return the resulting dict.
        """
        tags = {}
        if 'tags' in self.conf:
            tags.update(self.conf['tags'])
        if self.extra_tags:
            tags.update(self.extra_tags)
        return tags

    def prettyformat(self):
        """
        Prettyformat the configuration.
        """
        from os import linesep
        tags = self.get_all_tags()
        stripped = self.kw.copy()
        try:
            del stripped['user_data']
            stripped['user_data'] = "YES!"
        except KeyError:
            pass
        info = '{kw}{linesep}Tags: {tags}'.format(kw=pformat(stripped),
                                                  linesep=linesep,
                                                  tags=pformat(tags))
        if 'Name' in tags:
            name = tags['Name']
            info = 'Name={name}:{linesep}{info}'.format(**vars())
            info = '\n   '.join(info.splitlines())
        return info

    def confirm(self):
        """
        Use :meth:`prettyprint` to show the user their choices, and ask
        for confirmation. Runs ``fabric.api.abort()`` if the user does
        not confirm the choices.
        """
        from textwrap import fill
        print fill('Are you sure you want to launch (create) a new instance '
                   'with the following settings and tags?', 80)
        print '-' * 80
        print self.prettyformat()
        print '-' * 80
        Ec2LaunchInstance._confirm('Create instance')

    def run_instance(self):
        """
        Run/launch the configured instance, and add the tags to the instance
        (:meth:`.get_all_tags`).

        :return: The launched instance.
        """
        connection = connect_to_region(region_name=self.conf['region'], **awsfab_settings.AUTH)
        reservation = connection.run_instances(self.conf['ami'], **self.kw)
        instance = reservation.instances[0]
        self._add_tags(instance)
        self.instance = instance
        return instance

    def _add_tag(self, instance, tagname, value, retries=0):
        import time
        from boto.exception import EC2ResponseError
        try:
            instance.add_tag(tagname, value)
        except EC2ResponseError:
            if retries > self.tag_retry_count:
                raise
            print ('Got EC2ResponseError while adding tag to {id}. Retrying in '
                   '{sec} seconds...').format(id=instance.id, sec=self.tag_retry_sleep)
            time.sleep(self.tag_retry_sleep)
            self._add_tag(instance, tagname, value, retries=retries+1)

    def _add_tags(self, instance):
        for tagname, value in self.get_all_tags().iteritems():
            self._add_tag(instance, tagname, value)

########NEW FILE########
__FILENAME__ = tasks
"""
General tasks for AWS management.
"""
from pprint import pformat, pprint
from boto.ec2 import connect_to_region
from fabric.api import task, abort, local, env
from fabric.contrib.console import confirm
from textwrap import fill

from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.utils import force_slashend
from awsfabrictasks.utils import parse_bool
from api import Ec2InstanceWrapper
from api import wait_for_stopped_state
from api import wait_for_running_state
from api import print_ec2_instance
from api import Ec2LaunchInstance
from api import ec2_rsync_upload
from api import ec2_rsync_upload_command
from api import ec2_rsync_download
from api import ec2_rsync_download_command



__all__ = [
        'ec2_add_tag', 'ec2_set_tag', 'ec2_remove_tag',
        'ec2_launch_instance', 'ec2_start_instance', 'ec2_stop_instance',
        'ec2_list_instances', 'ec2_print_instance', 'ec2_login',
        'ec2_rsync_download_dir', 'ec2_rsync_upload_dir'
        ]



@task
def ec2_rsync_download_dir(remote_dir, local_dir, rsync_args='-av', noconfirm=False):
    """
    Sync the contents of ``remote_dir`` into ``local_dir``. E.g.: if ``remote_dir`` is
    ``/etc``, and ``local_dir`` is ``/tmp``, the ``/tmp/etc`` will be created on the local
    host, and filled with all files in ``/etc`` on the EC2 instance.

    :param remote_dir: The remote directory to download into local_dir.
    :param local_dir: The local directory.
    :param rsync_args: Arguments for ``rsync``. Defaults to ``-av``.
    :param noconfirm:
        If this is ``True``, we will not ask for confirmation before
        proceeding with the operation. Defaults to ``False``.
    """
    kwargs = dict(remote_dir=remote_dir,
                  local_dir=local_dir,
                  rsync_args=rsync_args)
    if not parse_bool(noconfirm):
        instancewrapper = Ec2InstanceWrapper.get_from_host_string()
        print 'Are you sure you want to run:'
        print '   ', ec2_rsync_download_command(instancewrapper, **kwargs)
        if not confirm('Proceed?'):
            abort('Aborted')
    ec2_rsync_download(**kwargs)

@task
def ec2_rsync_upload_dir(local_dir, remote_dir, rsync_args='-av', noconfirm=False):
    """
    Sync the contents of ``local_dir`` into ``remote_dir`` on the EC2
    instance. E.g.: if ``local_dir`` is ``/etc``, and ``remote_dir`` is
    ``/tmp``, the ``/tmp/etc`` will be created on the EC2 instance, and filled
    with all files in ``/etc`` on the local host.

    :param local_dir: The local directory to upload to the EC2 instance.
    :param remote_dir: The remote directory to upload local_dir into.
    :param rsync_args: Arguments for ``rsync``. Defaults to ``-av``.
    :param noconfirm:
        If this is ``True``, we will not ask for confirmation before
        proceeding with the operation. Defaults to ``False``.
    """
    kwargs = dict(local_dir=local_dir,
                  remote_dir=remote_dir,
                  rsync_args=rsync_args)
    if not parse_bool(noconfirm):
        instancewrapper = Ec2InstanceWrapper.get_from_host_string()
        print 'Are you sure you want to run:'
        print '   ', ec2_rsync_upload_command(instancewrapper, **kwargs)
        if not confirm('Proceed?'):
            abort('Aborted')
    ec2_rsync_upload(**kwargs)

@task
def ec2_add_tag(tagname, value=''):
    """
    Add tag to EC2 instance. Fails if tag already exists.

    :param tagname: Name of the tag to set (required).
    :param value: Value to set the tag to. Default to empty string.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    if tagname in instancewrapper.instance.tags:
        prettyname = instancewrapper.prettyname()
        abort('{prettyname}: duplicate tag: {tagname}'.format(**vars()))
    instancewrapper.instance.add_tag(tagname, value)

@task
def ec2_set_tag(tagname, value=''):
    """
    Set tag on EC2 instance. Overwrites value if tag exists.

    :param tagname: Name of the tag to set (required).
    :param value: Value to set the tag to. Default to empty string.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    instancewrapper.instance.add_tag(tagname, value)

@task
def ec2_remove_tag(tagname):
    """
    Remove tag from EC2 instance. Fails if tag does not exist.

    :param tagname: Name of the tag to remove (required).
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    if not tagname in instancewrapper.instance.tags:
        prettyname = instancewrapper.prettyname()
        abort('{prettyname} has no "{tagname}"-tag'.format(**vars()))
    instancewrapper.instance.remove_tag(tagname)



@task
def ec2_launch_instance(name, configname=None):
    """
    Launch new EC2 instance.

    :param name: The name to tag the EC2 instance with (required)
    :param configname: Name of the configuration in
        ``awsfab_settings.EC2_LAUNCH_CONFIGS``. Prompts for input if not
        provided as an argument.
    """
    launcher = Ec2LaunchInstance(extra_tags={'Name': name}, configname=configname)
    launcher.confirm()
    instance = launcher.run_instance()
    wait_for_running_state(instance.id)


@task
def ec2_start_instance(nowait=False):
    """
    Start EC2 instance.

    :param nowait: Set to ``True`` to let the EC2 instance start in the
        background instead of waiting for it to start. Defaults to ``False``.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    instancewrapper.instance.start()
    if nowait:
        print ('Starting: {id}. This is an asynchronous operation. Use '
                '``ec2_list_instances`` or the aws dashboard to check the status of '
                'the operation.').format(id=instancewrapper['id'])
    else:
        wait_for_running_state(instancewrapper['id'])

@task
def ec2_stop_instance(nowait=False):
    """
    Stop EC2 instance.

    :param nowait: Set to ``True`` to let the EC2 instance stop in the
        background instead of waiting for it to start. Defaults to ``False``.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    instancewrapper.instance.stop()
    if nowait:
        print ('Stopping: {id}. This is an asynchronous operation. Use '
                '``ec2_list_instances`` or the aws dashboard to check the status of '
                'the operation.').format(id=instancewrapper['id'])
    else:
        wait_for_stopped_state(instancewrapper['id'])

def _get_instanceident(instance):
    return 'id: {id}   (Name: {name})'.format(id=instance.id,
                                          name=instance.tags.get('Name', ''))

@task
def ec2_print_instance(full=False):
    """
    Print EC2 instance info.

    :param full: Print all attributes, or just the most useful ones? Defaults
        to ``False``.
    """
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    print 'Instance:', _get_instanceident(instancewrapper.instance)
    print_ec2_instance(instancewrapper.instance, full=full)

@task
def ec2_list_instances(region=awsfab_settings.DEFAULT_REGION, full=False):
    """
    List EC2 instances in a region (defaults to awsfab_settings.DEFAULT_REGION).

    :param region: The region to list instances in. Defaults to
        ``awsfab_settings.DEFAULT_REGION.
    :param full: Print all attributes, or just the most useful ones? Defaults
        to ``False``.
    """
    conn = connect_to_region(region_name=region, **awsfab_settings.AUTH)

    for reservation in conn.get_all_instances():
        print
        print 'id:', reservation.id
        print '   owner_id:', reservation.owner_id
        print '   groups:'
        for group in reservation.groups:
            print '      - {name} (id:{id})'.format(**group.__dict__)
        print '   instances:'
        for instance in reservation.instances:
            attrnames = None
            print '      -', _get_instanceident(instance)
            print_ec2_instance(instance, full=full, indentspaces=11)


@task
def ec2_login():
    """
    Log into the host specified by --hosts, --ec2names or --ec2ids.

    Aborts if more than one host is specified.
    """
    if len(env.all_hosts) != 1:
        abort('ec2_login only works with exactly one host. Given hosts: {0}'.format(repr(env.all_hosts)))
    instancewrapper = Ec2InstanceWrapper.get_from_host_string()
    host = instancewrapper.get_ssh_uri()
    key_filename = instancewrapper.get_ssh_key_filename()
    extra_ssh_args = awsfab_settings.EXTRA_SSH_ARGS
    cmd = 'ssh -i {key_filename} {extra_ssh_args} {host}'.format(**vars())
    local(cmd)

########NEW FILE########
__FILENAME__ = hostslist
from awsfabrictasks.utils import sudo_upload_string_to_file

hostsfile_template = """
127.0.0.1 localhost

# The following lines are desirable for IPv6 capable hosts
::1 ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
ff02::3 ip6-allhosts

{custom_hosts}
"""

class Host(object):
    def __init__(self, hostname, ip, suffix=''):
        self.hostname = hostname
        self.ip = ip
        self.suffix = suffix

    def __str__(self):
        return '{ip} {hostname}{suffix}'.format(**self.__dict__)

class HostsList(list):
    def __str__(self):
        return '\n'.join(str(host) for host in self)

def create_hostslist_from_ec2instancewrappers(instancewrappers):
    hostslist = HostsList()
    for instancewrapper in instancewrappers:
        if not instancewrapper.is_running():
            raise ValueError('EC2 instance "{0}" is not RUNNING.'.format(instancewrapper))
        ip = instancewrapper.instance.private_ip_address
        role = instancewrapper.instance.tags['hostname']
        hostslist.append(Host(hostname=role, ip=ip, suffix='.ec2'))
    return hostslist

def create_hostsfile_from_ec2instancewrappers(instancewrappers):
    hostslist = create_hostslist_from_ec2instancewrappers(instancewrappers)
    return hostsfile_template.format(custom_hosts=hostslist)

def upload_hostsfile(hostsfile_string):
    sudo_upload_string_to_file(hostsfile_string, '/etc/hosts')

########NEW FILE########
__FILENAME__ = main
from os.path import join
from fabric import tasks

from .ec2.api import Ec2InstanceWrapper


def _splitnames(names):
    if names:
        return names.split(',')
    else:
        return []

def get_hosts_supporting_aws(self, arg_hosts, arg_roles, arg_exclude_hosts, env=None):
    hosts = tasks.Task.get_hosts(self, arg_hosts, arg_roles, arg_exclude_hosts, env)

    ids = _splitnames(env.ec2ids)
    for instanceid in ids:
        instance = Ec2InstanceWrapper.get_by_instanceid(instanceid)
        instance.add_instance_to_env()
        hosts.append(instance.get_ssh_uri())

    names = _splitnames(env.ec2names)
    for name in names:
        instance = Ec2InstanceWrapper.get_by_nametag(name)
        instance.add_instance_to_env()
        hosts.append(instance.get_ssh_uri())

    tvps = env.ec2tags
    tvps = tvps and tvps.split(',') or []
    if tvps:
        tvps = dict((tvp.split('=') for tvp in tvps))
        instances = Ec2InstanceWrapper.get_by_tagvalue(tvps)
        for instance in instances:
            instance.add_instance_to_env()
            hosts.append(instance.get_ssh_uri())

    return hosts


def monkey_patch_get_hosts():
    tasks.WrappedCallableTask.get_hosts = get_hosts_supporting_aws

def awsfab():
    monkey_patch_get_hosts()
    from optparse import make_option
    from fabric.main import main
    from fabric import state

    state.env_options.append(
            make_option('-E', '--ec2names',
                default=None,
                help=('Comma-separated list of AWS hosts identified by their '
                    '``Name`` tag. You can specify region by prefixing the name '
                    'with ``region:`` (e.g.: eu-west-1:ec2test). Default region '
                    'is awsfab_settings.DEFAULT_REGION.')
                )
            )
    state.env_options.append(
            make_option('-G', '--ec2tags',
                default='',
                help=('Comma-separated list of tag=value pairs.')
                )
            )
    state.env_options.append(
            make_option('--ec2ids',
                default=None,
                help=('Comma-separated list of AWS hosts identified by instance ID. '
                    'You can specify region by prefixing the instanceid '
                    'with ``region:`` (e.g.: eu-west-1:x-abcdefg). Default region '
                    'is awsfab_settings.DEFAULT_REGION.')
                )
            )
    state.env_options.append(
            make_option('--awsfab-settings',
                dest='awsfab_settings_module',
                default='awsfab_settings',
                help=('Awsfabrictask settings module. Defaults to '
                    '``awsfab_settings``. Can NOT be a dotted path (e.g.: '
                    'my.settings). If this module is found, it will be merged '
                    'with the default settings. Furthermore, this module suffixed with '
                    '``_local`` will also be merged into the awsfab settings if it exists.')
                )
            )

    main()

########NEW FILE########
__FILENAME__ = api
from pprint import pformat
from boto.rds import connect_to_region

from awsfabrictasks.conf import awsfab_settings


class RdsRegionConnectionError(Exception):
    """
    Raised when we fail to connect to a region.
    """
    def __init__(self, region):
        self.region = region
        msg = 'Could not connect to region: {region}'.format(**vars())
        super(RdsRegionConnectionError, self).__init__(msg)


class RdsInstanceWrapper(object):
    """
    .. warning::
        This class is experimental, so we may make backwards-incompatible
        changes to it in the future.
    """
    def __init__(self, dbinstance):
        """
        :param dbinstance: A :class:`boto.rds.dbinstance.DBInstance` object.
        """
        self.dbinstance = dbinstance

    def __str__(self):
        return 'RdsInstanceWrapper:{0}'.format(self.get_id())

    def __repr__(self):
        return 'RdsInstanceWrapper({0})'.format(self.get_id())

    def get_id(self):
        return self.dbinstance.id

    @classmethod
    def get_connection(cls, region=None):
        """
        Connect to the given region, and return the connection.

        :param region:
            Defaults to ``awsfab_settings.DEFAULT_REGION`` if ``None``.
        """
        region = region is None and awsfab_settings.DEFAULT_REGION or region
        connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
        if not connection:
            raise RdsRegionConnectionError(region)
        return connection

    @classmethod
    def get_all_dbinstancewrappers(cls, region=None):
        """
        Get :class:`RdsInstanceWrapper` wrappers for all RDS dbinstances in the
        given region.

        Uses :meth:`.get_connection` to connect to the region.
        """
        connection = cls.get_connection(region)
        dbinstances = connection.get_all_dbinstances()
        dbinstancewrappers = [cls(dbinstance) for dbinstance in dbinstances]
        return dbinstancewrappers

    @classmethod
    def get_dbinstancewrapper(cls, instanceid, region=None):
        """
        Get an :class:`RdsInstanceWrapper` for the db instance with the given
        ``instanceid``.

        :raise LookupError:
            If the instance is not found.
        """
        for dbinstancewrapper in cls.get_all_dbinstancewrappers(region=region):
            if dbinstancewrapper.get_id() == instanceid:
                return dbinstancewrapper
        raise LookupError('Could not find any RDS dbinstance with id={0}'.format(instanceid))


def print_rds_instance(dbinstance, full=False, indentspaces=0):
    """
    Print attributes of an RDS instance.

    :param dbinstance: A :class:`boto.rds.dbinstance.DBInstance` object.
    :param full: Print all attributes? If not, a subset of the attributes are printed.
    :param indentspaces: Number of spaces to indent each line in the output.
    """
    indent = ' ' * indentspaces
    print '{indent}id={id}:'.format(indent=indent, id=dbinstance.id)
    indent = ' ' * (indentspaces + 3)
    if full:
        attrnames = sorted(dbinstance.__dict__.keys())
    else:
        attrnames = ['status', 'endpoint', 'DBName', 'master_username',
                     'instance_class', 'availability_zone']
    for attrname in attrnames:
        if attrname.startswith('_'):
            continue
        value = dbinstance.__dict__[attrname]
        if not isinstance(value, (str, unicode, bool, int)):
            value = pformat(value)
        print '{indent}{attrname}: {value}'.format(**vars())

########NEW FILE########
__FILENAME__ = tasks
"""
Tasks for RDS instances.
"""
from fabric.api import task

#from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.rds.api import print_rds_instance
from .api import RdsInstanceWrapper



__all__ = [
        'rds_print_instance',
        ]


@task
def rds_print_instance(dbinstanceid, full=False):
    """
    Print RDS instance info.

    :param dbinstanceid:
        The id/name of the RDS instance.
    :param full:
        Print all attributes, or just the most useful ones? Defaults to
        ``False``.
    """
    dbinstancewrapper = RdsInstanceWrapper.get_dbinstancewrapper(dbinstanceid)
    print_rds_instance(dbinstancewrapper.dbinstance, full=bool(full), indentspaces=0)

########NEW FILE########
__FILENAME__ = regions
from fabric.api import task
from boto.ec2 import regions, connect_to_region

from conf import awsfab_settings



@task
def list_regions():
    """
    List all regions.
    """
    for region in regions(**awsfab_settings.AUTH):
        print '- {name} (endpoint: {endpoint})'.format(**region.__dict__)


@task
def list_zones(region=awsfab_settings.DEFAULT_REGION):
    """
    List zones in the given region.

    :param region: Defaults to ``awsfab_settings.DEFAULT_REGION``.
    """
    connection = connect_to_region(region_name=region, **awsfab_settings.AUTH)
    print 'Zones in {region}:'.format(region=region)
    for zone in connection.get_all_zones():
        print '- {name} (state:{state})'.format(**zone.__dict__)

########NEW FILE########
__FILENAME__ = api
#from pprint import pformat
from fnmatch import fnmatchcase
from os import walk, makedirs
from os.path import join, abspath, exists, dirname
from boto.s3.connection import S3Connection
from boto.s3.prefix import Prefix
from boto.s3.key import Key

from awsfabrictasks.utils import force_slashend
from awsfabrictasks.utils import localpath_to_slashpath
from awsfabrictasks.utils import slashpath_to_localpath
from awsfabrictasks.conf import awsfab_settings
from awsfabrictasks.utils import compute_localfile_md5sum


class S3ConnectionError(Exception):
    """
    Raised when we fail to connect to S3.
    """
    def __init__(self, msg='Could not connect S3'):
        super(S3ConnectionError, self).__init__(msg)


def settingsformat_bucketname(bucketname):
    """
    Returns ``awsfab_settings.S3_BUCKET_PATTERN.format(bucketname=bucketname)``.

    .. seealso:: :obj:`awsfabrictasks.default_settings.S3_BUCKET_PATTERN`.
    """
    return awsfab_settings.S3_BUCKET_PATTERN.format(bucketname=bucketname)


class S3ConnectionWrapper(object):
    """
    S3 connection wrapper.
    """
    def __init__(self, connection):
        """
        :param bucket: A :class:`boto.rds.bucket.DBInstance` object.
        """
        self.connection = connection

    def __str__(self):
        return 'S3ConnectionWrapper:{0}'.format(self.connection)

    @classmethod
    def get_connection(cls):
        """
        Connect to S3 using ``awsfab_settings.AUTH``.

        :return: S3ConnectionWrapper object.
        """
        connection = S3Connection(**awsfab_settings.AUTH)
        return cls(connection)

    @classmethod
    def get_bucket_using_pattern(cls, bucketname):
        """
        Same as :meth:`.get_bucket`, however the ``bucketname`` is filtered
        through :func:`.settingsformat_bucketname`.
        """
        return cls.get_bucket(settingsformat_bucketname(bucketname))

    @classmethod
    def get_bucket(cls, bucketname):
        """
        Get the requested bucket.

        Shortcut for::

            S3ConnectionWrapper.get_connection().connection.get_bucket(bucketname)

        :param bucketname: Name of an S3 bucket.
        """
        connectionwrapper = S3ConnectionWrapper.get_connection()
        return connectionwrapper.connection.get_bucket(bucketname)



def iter_bucketcontents(bucket, prefix, match, delimiter, formatter=lambda key: key.name):
    """
    Iterate over items given bucket, yielding items formatted for output.

    :param bucket: A class:`boto.s3.bucket.Bucket` object.
    :param prefix:
        The prefix to list. Defaults to empty string, which lists
        all items in the root directory.
    :param match:
        A Unix shell style pattern to match. Matches against the entire key
        name (in filesystem terms: the absolute path).

        Uses the ``fnmatch`` python module. The match is case-sensitive.

        Examples::

            *.jpg
            *2012*example*.log
            icon-*.png

    :param delimiter:
        The delimiter to use. Defaults to ``/``.

    :param formatter:
        Formatter callback to use to format each key. Not used on Prefix-keys
        (directories).  The callback should take a key as input, and return a
        string.

    .. seealso:: http://docs.amazonwebservices.com/AmazonS3/latest/dev/ListingKeysHierarchy.html
    """
    for key in bucket.list(prefix=prefix, delimiter=delimiter):
        if match and not fnmatchcase(key.name, match):
            continue
        if isinstance(key, Prefix):
            yield key.name
        else:
            yield formatter(key)


def dirlist_absfilenames(dirpath):
    """
    Get all the files within the given ``dirpath`` as a set of absolute
    filenames.
    """
    allfiles = set()
    for root, dirs, files in walk(dirpath):
        abspaths = map(lambda filename: join(root, filename), files)
        allfiles.update(abspaths)
    return allfiles

def s3list_s3filedict(bucket, prefix):
    """
    Get all the keys with the given ``prefix`` as a dict with key-name as key
    and the key-object wrappen in a :class:`S3File` as value.
    """
    result = {}
    for key in bucket.list(prefix=prefix):
        result[key.name] = S3File(bucket, key)
    return result

def localpath_to_s3path(localdir, localpath, s3prefix):
    """
    Convert a local filepath into a S3 path within the given ``s3prefix``.

    :param localdir: The local directory that corresponds to ``s3prefix``.
    :param localpath: Path to a file within ``localdir``.
    :param s3prefix: Prefix to use for the file on S3.

    Example::
    >>> localpath_to_s3path('/mydir', '/mydir/hello/world.txt', 'my/test')
    'my/test/hello/world.txt'
    """
    localdir = force_slashend(localpath_to_slashpath(abspath(localdir)))
    localpath = localpath_to_slashpath(abspath(localpath))
    s3prefix = force_slashend(s3prefix)
    relpath = localpath[len(localdir):]
    return s3prefix + relpath

def s3path_to_localpath(s3prefix, s3path, localdir):
    """
    Convert a s3 filepath into a local filepath within the given ``localdir``.

    :param s3prefix: Prefix used for the file on S3.
    :param s3path: Path to a file within ``s3prefix``.
    :param localdir: The local directory that corresponds to ``s3prefix``.

    Example::
    >>> s3path_to_localpath('mydir/', 'mydir/hello/world.txt', '/my/test')
    '/my/test/hello/world.txt'
    """
    s3prefix = force_slashend(s3prefix)
    localpath = slashpath_to_localpath(s3path[len(s3prefix):])
    return join(localdir, localpath)

class S3ErrorBase(Exception):
    """
    Base class for all S3 errors. Never raised directly.
    """

class S3FileErrorBase(S3ErrorBase):
    """
    Base class for all :class:`S3File` errors. Never raised directly.
    """
    def __init__(self, s3file):
        """
        :param s3file: A :class:`S3File` object.
        """
        self.s3file = s3file

    def __str__(self):
        return '{classname}: {s3file}'.format(classname=self.__class__.__name__,
                                              s3file=self.s3file)

class S3FileExistsError(S3FileErrorBase):
    """
    Raised when trying to overwrite an existing :class:`S3File`, unless
    overwriting is requested.
    """

class S3FileDoesNotExist(S3FileErrorBase):
    """
    Raised when an :class:`S3File` does not exist.
    """

class S3FileNoInfo(S3FileErrorBase):
    """
    Raised when trying to use :class:`S3File` metadata before performing a HEAD
    request.
    """
    def __str__(self):
        return ('{0}: No info about the key. Use S3File.perform_headrequest(), '
                'or initialize with head=True.').format(super(S3FileNoInfo, self).__str__())


class S3File(object):
    """
    Simplifies working with keys in S3 buckets.
    """

    @classmethod
    def raw(cls, bucket, name):
        key = Key(bucket)
        key.name = name
        return cls(bucket, key)

    @classmethod
    def from_head(cls, bucket, name):
        return cls(bucket, bucket.get_key(name))

    def __init__(self, bucket, key):
        self.bucket = bucket
        self.key = key

    def _overwrite_check(self, overwrite):
        if not overwrite and self.key.exists():
            raise S3FileExistsError(self)

    def _has_info_check(self):
        if self.key.etag == None or self.key.is_latest == None:
            raise S3FileNoInfo(self)

    def get_metadata(self, metadata_name):
        self._has_info_check()
        return self.key.get_metadata(metadata_name)

    def get_checksum(self):
        return self.get_metadata('awsfabchecksum')

    def exists(self):
        """
        Return ``True`` if the key/file exists in the S3 bucket.
        """
        return self.key.exists()

    def get_etag(self):
        """
        Return the etag (the md5sum)
        """
        self._has_info_check()
        return self.key.etag.strip('"')

    def etag_matches_localfile(self, localfile):
        """
        Return ``True`` if the file at the path given in ``localfile`` has an
        md5 hex-digested checksum matching the etag of this S3 key.
        """
        return self.get_etag() == compute_localfile_md5sum(localfile)

    def delete(self):
        """
        Delete the key/file from the bucket.

        :raise S3FileDoesNotExist:
            If the key does not exist in the bucket.
        """
        if not self.exists():
            raise S3FileDoesNotExist(self)
        self.key.delete()

    def set_contents_from_string(self, data, overwrite=False):
        """
        Write ``data`` to the S3 file.

        :param overwrite:
            If ``True``, overwrite if the key/file exists.
        :raise S3FileExistsError:
            If ``overwrite==True`` and the key exists in the bucket.
        """
        self._overwrite_check(overwrite)
        self.key.set_contents_from_string(data)

    def set_contents_from_filename(self, localfile, overwrite=False):
        """
        Upload ``localfile``.

        :param overwrite:
            If ``True``, overwrite if the key/file exists.
        :raise S3FileExistsError:
            If ``overwrite==True`` and the key exists in the bucket.
        """
        self._overwrite_check(overwrite)
        self.key.set_contents_from_filename(localfile)

    def get_contents_as_string(self):
        """
        Download the file and return it as a string.
        """
        return self.key.get_contents_as_string()

    def get_contents_to_filename(self, localfile):
        """
        Download the file to the given ``localfile``.
        """
        self.key.get_contents_to_filename(localfile)

    def __str__(self):
        return '{classname}({bucket}, {name})'.format(classname=self.__class__.__name__,
                                                      bucket=self.bucket,
                                                      name=self.key.name)


class S3SyncIterFile(object):
    """
    Objects of this class is yielded by :meth:`S3Sync.iterfiles`.
    Contains info about where the file exists, its local and S3 path (even if
    it does not exist).
    """
    def __init__(self):
        #: The local path. Always set.
        #: Use :obj:`.localexists` if you want to know if the local file exists.
        self.localpath = None

        #: Local file exists?
        self.localexists = False

        #: The S3 path. Always set.
        #: Use :obj:`.s3exists` if you want to know if the S3 file exists.
        self.s3path = None

        #: A :class:`S3File` object.
        #: Use :obj:`.s3exists` if you want to know if the S3 file exists.
        self.s3file = None

        #: S3 file exists?
        self.s3exists = False

    def __str__(self):
        return ('S3SyncIterFile(localpath={localpath}, '
                'localexists={localexists}, s3path={s3path}, s3file={s3file}, '
                's3exists={s3exists})').format(**self.__dict__)

    def both_exists(self):
        """
        Returns ``True`` if :obj:`.localexists` and :obj:`.s3exists`.
        """
        return self.localexists and self.s3exists

    def etag_matches_localfile(self):
        """
        Shortcut for::

            self.s3file.etag_matches_localfile(self.localpath)
        """
        return self.s3file.etag_matches_localfile(self.localpath)

    def create_localdir(self):
        """
        Create the directory containing :obj:`.localpath` if it does not exist.
        """
        dname = dirname(self.localpath)
        if not exists(dname):
            makedirs(dname)

    def download_s3file_to_localfile(self):
        """
        :meth:`.create_localdir` and download the file at :obj:`.s3path` to
        :obj:`.localpath`.
        """
        self.create_localdir()
        self.s3file.get_contents_to_filename(self.localpath)

class S3Sync(object):
    """
    Makes it easy to sync files to and from S3. This class does not make any
    changes to the local filesyste, or S3, it only makes it easy to write
    function that works with hierarkies of files synced locally and on S3.

    A good example is the sourcecode for :func:`awsfabrictasks.s3.tasks.s3_syncupload_dir`.
    """
    def __init__(self, bucket, local_dir, s3prefix):
        """
        :param bucket: A :class:`boto.rds.bucket.DBInstance` object.
        :param local_dir: The local directory.
        :param local_dir: The S3 key prefix that corresponds to ``local_dir``.
        """
        self.bucket = bucket
        self.local_dir = local_dir
        self.s3prefix = force_slashend(s3prefix)

    def _get_localfiles_set(self):
        return dirlist_absfilenames(self.local_dir)

    def _get_s3filedict(self):
        return s3list_s3filedict(self.bucket, self.s3prefix)

    def iterfiles(self):
        """
        Iterate over all files both local and within the S3 prefix.
        Yields :class:`S3SyncIterFile` objects.

        How it works:

            - Uses :func:`dirlist_absfilenames` to get all local files in the ``local_dir``.
            - Uses :func:`s3list_s3filedict` to get all S3 files in the ``s3prefix``.
            - Uses these two sets of information to create :class:`S3SyncIterFile` objects.
        """
        s3filedict = self._get_s3filedict()
        localfiles_set = self._get_localfiles_set()
        synced_s3paths = set()

        # Handle files that are locally, and possibly also on S3
        for localpath in localfiles_set:
            syncfile = S3SyncIterFile()
            syncfile.localpath = localpath
            syncfile.localexists = True
            syncfile.s3path = localpath_to_s3path(self.local_dir, localpath, self.s3prefix)
            synced_s3paths.add(syncfile.s3path)
            syncfile.s3exists = syncfile.s3path in s3filedict
            if syncfile.s3exists:
                syncfile.s3file = s3filedict[syncfile.s3path]
            else:
                syncfile.s3file = S3File.raw(self.bucket, syncfile.s3path)
            yield syncfile

        # Handle files that are only on S3
        only_remote_keys = set(s3filedict.keys()).difference(synced_s3paths)
        for s3path in only_remote_keys:
            s3file = S3File.raw(self.bucket, s3path)
            syncfile = S3SyncIterFile()
            syncfile.s3path = s3path
            syncfile.s3file = s3filedict[syncfile.s3path]
            syncfile.s3exists = True
            syncfile.localexists = False
            syncfile.localpath = s3path_to_localpath(self.s3prefix, s3path, self.local_dir)
            yield syncfile

########NEW FILE########
__FILENAME__ = tasks
from fabric.api import task, abort
from fabric.contrib.console import confirm
from os import linesep, remove
from os.path import exists, expanduser, abspath

from awsfabrictasks.utils import parse_bool
from awsfabrictasks.utils import configureStreamLoggerForTask
from awsfabrictasks.utils import getLoglevelFromString
from .api import S3ConnectionWrapper
from .api import iter_bucketcontents
from .api import S3File
from .api import S3FileExistsError
from .api import S3Sync


__all__ = ['s3_ls', 's3_listbuckets', 's3_createfile', 's3_uploadfile',
           's3_printfile', 's3_downloadfile', 's3_delete', 's3_is_same_file',
           's3_syncupload_dir', 's3_syncdownload_dir']

@task
def s3_ls(bucketname, prefix='', search=None, match=None, style='compact',
          delimiter='/'):
    """
    List all items with the given prefix within the given bucket.

    :param bucketname: Name of an S3 bucket.
    :param prefix:
        The prefix to list. Defaults to empty string, which lists
        all items in the root directory.
    :param search:
        Search for keys whose name contains this string.
        Shortcut for ``match="*<search>*"``.
    :param match:
        A Unix shell style pattern to match. Matches against the entire key
        name (in filesystem terms: the absolute path).

        Ignored if ``search`` is provided.  Uses the ``fnmatch`` python module.
        The match is case-sensitive.

        Examples::

            *.jpg
            *2012*example*.log
            icon-*.png

    :param style:
        The style of the output. One of:

            - compact
            - verbose
            - nameonly

    :param delimiter:
        The delimiter to use. Defaults to ``"/"``.
    """
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)

    styles = ('compact', 'verbose', 'nameonly')
    if not style in styles:
        abort('Invalid style: {0}. Use one of {1}'.format(style, ','.join(styles)))
    if style == 'compact':
        formatstring = '{name:<70} {size:<10} {last_modified:<25} {mode}'
        print formatstring.format(name='NAME', size='SIZE', last_modified='LAST MODIFIED',
                                  mode='MODE')
    elif style == 'verbose':
        formatstring = '{linesep}'.join(('name: {name}',
                                         '    size: {size}',
                                         '    last_modified: {last_modified}',
                                         '    mode: {mode}'))
    elif style == 'nameonly':
        formatstring = '{name}'

    if search:
        match = '*{0}*'.format(search)

    formatter = lambda key: formatstring.format(linesep=linesep, **key.__dict__)
    for line in iter_bucketcontents(bucket, prefix=prefix, match=match,
                                    delimiter=delimiter, formatter=formatter):
        print line

@task
def s3_listbuckets():
    """
    List all S3 buckets.
    """
    connectionwrapper = S3ConnectionWrapper.get_connection()
    for bucket in connectionwrapper.connection.get_all_buckets():
        loggingstatus = bucket.get_logging_status()
        print '{0}:'.format(bucket.name)
        print '   location:', bucket.get_location()
        print '   loggingstatus:'
        print '      enabled:', loggingstatus.target != None
        print '      prefix:', loggingstatus.prefix
        print '      grants:', loggingstatus.grants


@task
def s3_createfile(bucketname, keyname, contents, overwrite=False):
    """
    Create a file with the given keyname and contents.

    :param bucketname: Name of an S3 bucket.
    :param keyname: The key to create/overwrite (In filesystem terms: absolute file path).
    :param contents: The data to put in the bucket.
    :param overwrite: Overwrite if exists? Defaults to ``False``.
    """
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.raw(bucket, keyname)
    try:
        s3file.set_contents_from_string(contents, overwrite)
    except S3FileExistsError, e:
        abort(str(e))


@task
def s3_uploadfile(bucketname, keyname, localfile, overwrite=False):
    """
    Upload a local file.

    :param bucketname: Name of an S3 bucket.
    :param keyname: The key to create/overwrite (In filesystem terms: absolute file path).
    :param localfile: The local file to upload.
    :param overwrite: Overwrite if exists? Defaults to ``False``.
    """
    localfile = expanduser(localfile)
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.raw(bucket, keyname)
    try:
        s3file.set_contents_from_filename(localfile, overwrite)
    except S3FileExistsError, e:
        abort(str(e))

@task
def s3_printfile(bucketname, keyname):
    """
    Print the contents of the given key/file to stdout.

    :param bucketname: Name of an S3 bucket.
    :param keyname: The key to print (In filesystem terms: absolute file path).
    """
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.raw(bucket, keyname)
    print s3file.get_contents_as_string()

@task
def s3_downloadfile(bucketname, keyname, localfile, overwrite=False):
    """
    Print the contents of the given key/file to stdout.

    :param bucketname: Name of an S3 bucket.
    :param keyname: The key to download (In filesystem terms: absolute file path).
    :param localfile: The local file to write the data to.
    :param overwrite: Overwrite local file if exists? Defaults to ``False``.
    """
    localfile = expanduser(localfile)
    if exists(localfile) and not overwrite:
        abort('Local file exists: {0}'.format(localfile))
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.raw(bucket, keyname)
    print s3file.get_contents_to_filename()

@task
def s3_delete(bucketname, keyname, noconfirm=False):
    """
    Remove a "file" from the given bucket.

    :param bucketname: Name of an S3 bucket.
    :param keyname: The key to remove (In filesystem terms: absolute file path).
    :param noconfirm:
        If this is ``True``, we will not ask for confirmation before
        removing the key. Defaults to ``False``.
    """
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.raw(bucket, keyname)
    if not parse_bool(noconfirm):
        if not confirm('Remove {0}?'.format(keyname)):
            abort('Aborted')
    s3file.delete()


@task
def s3_is_same_file(bucketname, keyname, localfile):
    """
    Check if the ``keyname`` in the given ``bucketname`` has the same etag as
    the md5 checksum of the given ``localfile``. Files with the same md5sum are
    extremely likely to have the same contents. Prints ``True`` or ``False``.

    Files matching as the same file by this task is considered the same file by
    :func:`s3_upload_dir`.
    """
    localfile = expanduser(localfile)
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    s3file = S3File.from_head(bucket, keyname)
    print s3file.etag_matches_localfile(localfile)


@task
def s3_syncupload_dir(bucketname, local_dir, s3prefix, loglevel='INFO', delete=False,
                      pretend=False):
    """
    Sync a local directory into a S3 bucket. Uses the same method as the
    :func:`s3_is_same_file` task to determine if a local file differs from a
    file on S3.

    :param bucketname: Name of an S3 bucket.
    :param local_dir: The local directory to sync to S3.
    :param s3prefix: The S3 prefix to use for the uploaded files.
    :param loglevel:
        Controls the amount of output:

            QUIET --- No output.
            INFO --- Only produce output for changes.
            DEBUG --- One line of output for each file.

        Defaults to "INFO".
    :param delete:
        Delete remote files that are not present in ``local_dir``.
    :param pretend:
        Do not change anything. With ``verbosity=2``, this gives a good
        overview of the changes applied by running the task.
    """
    log = configureStreamLoggerForTask(__name__, 's3_syncupload_dir',
                                       getLoglevelFromString(loglevel))
    local_dir = abspath(expanduser(local_dir))
    delete = parse_bool(delete)
    pretend = parse_bool(pretend)
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    if pretend:
        log.info('Running in pretend mode. No changes are made.')
    for syncfile in S3Sync(bucket, local_dir, s3prefix).iterfiles():
        logname = '{0}:{1}'.format(bucket.name, syncfile.s3path)
        if syncfile.both_exists():
            if syncfile.etag_matches_localfile():
                log.debug('UNCHANGED %s', logname)
            else:
                if not pretend:
                    log.debug('Uploading %s', logname)
                    syncfile.s3file.set_contents_from_filename(syncfile.localpath, overwrite=True)
                log.info('UPDATED %s', logname)
        elif syncfile.localexists:
            if not pretend:
                log.debug('Uploading %s', logname)
                syncfile.s3file.set_contents_from_filename(syncfile.localpath)
            log.info('CREATED %s', logname)
        else:
            if delete:
                if not pretend:
                    syncfile.s3file.delete()
                log.info('DELETED %s', logname)
            else:
                log.debug('NOT DELETED %s (it does not exist locally)', logname)


@task
def s3_syncdownload_dir(bucketname, s3prefix, local_dir, loglevel='INFO', delete=False,
                        pretend=False):
    """
    Sync a S3 prefix from a S3 bucket into a local directory. Uses the same
    method as the :func:`s3_is_same_file` task to determine if a local file
    differs from a file on S3.

    :param bucketname: Name of an S3 bucket.
    :param s3prefix: The S3 prefix to use for the uploaded files.
    :param local_dir: The local directory to sync to S3.
    :param loglevel:
        Controls the amount of output:

            QUIET --- No output.
            INFO --- Only produce output for changes.
            DEBUG --- One line of output for each file.

        Defaults to "INFO".
    :param delete:
        Delete local files that are not present in ``s3prefix``.
    :param pretend:
        Do not change anything. With ``verbosity=2``, this gives a good
        overview of the changes applied by running the task.
    """
    log = configureStreamLoggerForTask(__name__, 's3_syncupload_dir',
                                       getLoglevelFromString(loglevel))
    local_dir = abspath(expanduser(local_dir))
    delete = parse_bool(delete)
    pretend = parse_bool(pretend)
    bucket = S3ConnectionWrapper.get_bucket_using_pattern(bucketname)
    if pretend:
        log.info('Running in pretend mode. No changes are made.')
    for syncfile in S3Sync(bucket, local_dir, s3prefix).iterfiles():
        logname = 'LocalFS:{0}'.format(syncfile.localpath)
        if syncfile.both_exists():
            if syncfile.etag_matches_localfile():
                log.debug('UNCHANGED %s', logname)
            else:
                if not pretend:
                    log.debug('Downloading %s', logname)
                    syncfile.download_s3file_to_localfile()
                log.info('UPDATED %s', logname)
        elif syncfile.s3exists:
            if not pretend:
                log.debug('Downloading %s', logname)
                syncfile.download_s3file_to_localfile()
            log.info('CREATED %s', logname)
        else:
            if delete:
                if not pretend:
                    remove(syncfile.localpath)
                log.info('DELETED %s', logname)
            else:
                log.debug('NOT DELETED %s (it does not exist on S3)', syncfile.localpath)

########NEW FILE########
__FILENAME__ = test_api
from unittest import TestCase

from awsfabrictasks.ec2.api import ec2_rsync_download_command
from awsfabrictasks.ec2.api import ec2_rsync_upload_command
from awsfabrictasks.ec2.api import Ec2LaunchInstance
from awsfabrictasks.ec2.api import zipit
from awsfabrictasks.conf import awsfab_settings


class TestRsync(TestCase):
    class MockEc2InstanceWrapper(object):
        def get_ssh_uri(self):
            return 'test@example.com'
        def get_ssh_key_filename(self):
            return '/path/to/key.pem'

    def setUp(self):
        self.instancewrapper = TestRsync.MockEc2InstanceWrapper()
        awsfab_settings.EXTRA_SSH_ARGS = ''

    def test_ec2_rsync_download_command(self):
        self.assertEquals(ec2_rsync_download_command(self.instancewrapper, '/etc', '/tmp/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem " test@example.com:/etc /tmp/etc')
        self.assertEquals(ec2_rsync_download_command(self.instancewrapper, '/etc/', '/tmp/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem " test@example.com:/etc /tmp/etc')
        self.assertEquals(ec2_rsync_download_command(self.instancewrapper, '/etc/', '/tmp/etc', sync_content=True),
                          'rsync -av -e "ssh -i /path/to/key.pem " test@example.com:/etc/ /tmp/etc')
        self.assertEquals(ec2_rsync_download_command(self.instancewrapper, '/etc/', '/tmp/etc', sync_content=False),
                          ec2_rsync_download_command(self.instancewrapper, '/etc/', '/tmp/etc'))

    def test_ec2_rsync_download_command_extra_ssh_args(self):
        awsfab_settings.EXTRA_SSH_ARGS = 'TEST'
        self.assertEquals(ec2_rsync_download_command(self.instancewrapper, '/etc/', '/tmp/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem TEST" test@example.com:/etc /tmp/etc')

    def test_ec2_rsync_upload_command(self):
        self.assertEquals(ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc', '/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem " /tmp/etc test@example.com:/etc')
        self.assertEquals(ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc/', '/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem " /tmp/etc test@example.com:/etc')
        self.assertEquals(ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc/', '/etc', sync_content=True),
                          'rsync -av -e "ssh -i /path/to/key.pem " /tmp/etc/ test@example.com:/etc')
        self.assertEquals(ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc/', '/etc', sync_content=False),
                          ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc/', '/etc'))

    def test_ec2_rsync_upload_command_extra_ssh_args(self):
        awsfab_settings.EXTRA_SSH_ARGS = 'TEST'
        self.assertEquals(ec2_rsync_upload_command(self.instancewrapper, '/tmp/etc', '/etc'),
                          'rsync -av -e "ssh -i /path/to/key.pem TEST" /tmp/etc test@example.com:/etc')





class TestEc2LaunchInstance(TestCase):
    class Ec2LaunchInstanceMock(Ec2LaunchInstance):
        def _ask_for_configname(self):
            return 'ASKED'
        def check_if_name_exists(self):
            self.NAME_EXISTS_CHECKED = True


    def setUp(self):
        self.conf = {'instance_type': 't1.micro',
                     'key_name': 'awstestkey',
                     'security_groups': ['testgroup'],
                     'extrastuff': 'test'}


    def _create_launcher(self, settings={}, launcher_kw={}):
        awsfab_settings.reset_settings(**settings)
        launcher = self.Ec2LaunchInstanceMock(**launcher_kw)
        return launcher

    def test_init(self):
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'ASKED': self.conf}})
        self.assertEquals(launcher.extra_tags, {})
        self.assertEquals(launcher.configname, 'ASKED')
        self.assertEquals(launcher.configname_help, 'Please select one of the following configurations:')
        self.assertEquals(launcher.conf, self.conf)
        self.assertEquals(launcher.kw, {'instance_type': 't1.micro',
                                        'key_name': 'awstestkey',
                                        'security_groups': ['testgroup']})
        self.assertEquals(launcher.instance, None)
        self.assertEquals(launcher.NAME_EXISTS_CHECKED, True)

    def test_userdata(self):
        self.conf['user_data'] = 'testing'
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'ASKED': self.conf}})
        self.assertEquals(launcher.kw['user_data'], zipit('testing'))

    def test_specify_configname(self):
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'myconf': self.conf}},
                                         launcher_kw={'configname': 'myconf'})
        self.assertEquals(launcher.configname, 'myconf')
        self.assertEquals(launcher.conf, self.conf)

    def test_get_all_tags_empty(self):
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'ASKED': self.conf}})
        self.assertEquals(launcher.get_all_tags(), {})

    def test_get_all_tags_from_conf(self):
        self.conf['tags'] = {'sshuser': 'test'}
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'ASKED': self.conf}})
        self.assertEquals(launcher.get_all_tags(), {'sshuser': 'test'})

    def test_get_all_tags_from_conf_and_extra(self):
        self.conf['tags'] = {'sshuser': 'test'}
        launcher = self._create_launcher(settings={'EC2_LAUNCH_CONFIGS': {'ASKED': self.conf}},
                                         launcher_kw={'extra_tags': {'port': '15010'}})
        self.assertEquals(launcher.get_all_tags(), {'sshuser': 'test', 'port': '15010'})

########NEW FILE########
__FILENAME__ = test_api
from unittest import TestCase
from shutil import rmtree
from tempfile import mkdtemp
from os import makedirs
from os.path import join, exists, dirname

from awsfabrictasks.s3.api import dirlist_absfilenames
from awsfabrictasks.s3.api import localpath_to_s3path
from awsfabrictasks.s3.api import s3path_to_localpath

def makefile(tempdir, path, contents):
    path = join(tempdir, *path.split('/'))
    if not exists(dirname(path)):
        makedirs(dirname(path))
    open(path, 'wb').write(contents)
    return path


class TestDirlistAbsfilenames(TestCase):
    def setUp(self):
        self.tempdir = mkdtemp()
        files = (('hello/world.txt', 'Hello world'),
                 ('test.py', 'print "test"'),
                 ('hello/cruel/world.txt', 'Cruel?'))
        self.paths = set()
        for path, contents in files:
            realpath = makefile(self.tempdir, path, contents)
            self.paths.add(realpath)

    def tearDown(self):
        rmtree(self.tempdir)

    def test_dirlist_absfilenames(self):
        result = dirlist_absfilenames(self.tempdir)
        self.assertEquals(result, self.paths)


class TestLocalpathToS3path(TestCase):
    def setUp(self):
        self.tempdir = mkdtemp()
        makefile(self.tempdir, 'hello/world.txt', '')

    def tearDown(self):
        rmtree(self.tempdir)

    def test_localpath_to_s3path(self):
        s3path = localpath_to_s3path(self.tempdir, join(self.tempdir, 'hello/world.txt'), 'my/test')
        self.assertEquals(s3path, 'my/test/hello/world.txt')

    def test_s3path_to_localpath(self):
        localpath = s3path_to_localpath('mydir/', 'mydir/hello/world.txt', join(self.tempdir, 'my', 'test'))
        self.assertEquals(localpath, join(self.tempdir, 'my', 'test', 'hello', 'world.txt'))

########NEW FILE########
__FILENAME__ = test_utils
from unittest import TestCase

from awsfabrictasks.utils import force_slashend
from awsfabrictasks.utils import force_noslashend
from awsfabrictasks.utils import rsyncformat_path
from awsfabrictasks.utils import guess_contenttype


class TestUtils(TestCase):
    def test_force_slashend(self):
        self.assertEquals(force_slashend('/path/to/'), '/path/to/')
        self.assertEquals(force_slashend('/path/to'), '/path/to/')

    def test_force_noslashend(self):
        self.assertEquals(force_noslashend('/path/to'), '/path/to')
        self.assertEquals(force_noslashend('/path/to/'), '/path/to')
        self.assertEquals(force_noslashend('/path/to////'), '/path/to')

    def test_rsyncformat_path(self):
        self.assertEquals(rsyncformat_path('/path/to'), '/path/to')
        self.assertEquals(rsyncformat_path('/path/to', sync_content=True), '/path/to/')
        self.assertEquals(rsyncformat_path('/path/to'), rsyncformat_path('/path/to', sync_content=False))

    def test_guess_contenttype(self):
        self.assertEquals(guess_contenttype('hello.py'), 'text/x-python')
        self.assertEquals(guess_contenttype('hello.txt'), 'text/plain')
        self.assertEquals(guess_contenttype('hello.json'), 'application/json')

########NEW FILE########
__FILENAME__ = ubuntu
"""
Ubuntu utilities.
"""
from fabric.api import sudo

def set_locale(locale='en_US'):
    """
    Set locale to avoid the warnings from perl and others about locale
    failures.
    """
    sudo('locale-gen {locale}.UTF-8'.format(**vars()))
    sudo('update-locale LANG={locale}.UTF-8 LC_ALL={locale}.UTF-8 LC_MESSAGES=POSIX'.format(**vars()))

########NEW FILE########
__FILENAME__ = utils
from fabric.api import put, sudo
from os import walk, remove
from os.path import relpath, join
from mimetypes import guess_type
from tempfile import NamedTemporaryFile
from boto.utils import compute_md5
import logging


#: Map of strings to loglevels (for the logging module)
loglevel_stringmap = {'DEBUG': logging.DEBUG,
                      'INFO': logging.INFO,
                      'WARN': logging.WARN,
                      'ERROR': logging.ERROR,
                      'CRITICAL': logging.CRITICAL,
                      'QUIET': logging.CRITICAL}

class InvalidLogLevel(KeyError):
    """
    Raised when :func:`getLoglevelFromString` gets an invalid ``loglevelstring``.
    """

def getLoglevelFromString(loglevelstring):
    """
    Lookup ``loglevelstring`` in :obj:`loglevel_stringmap`.

    :raise InvalidLogLevel: If loglevelstring is not in :obj:`loglevel_stringmap`.
    :return: The loglevel.
    :rtype: int
    """
    try:
        return loglevel_stringmap[loglevelstring]
    except KeyError, e:
        raise InvalidLogLevel('Invalid loglevel: {0}'.format(loglevelstring))

def configureStreamLogger(loggername, level):
    """
    Configure a stdout/stderr logger (logging.StreamHandler) with the given
    ``loggername`` and ``level``. If you are configuring logging for a
    task, use :func:`configureStreamLoggerForTask`.

    This is suitable for log-configuration for a single task, where the user
    specifies a loglevel.

    .. seealso:
        :func:`configureStreamLoggerForTask`,
        :func:`getLoglevelFromString`.

    :return: The configured logger.
    """
    logger = logging.getLogger(loggername)
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

def configureStreamLoggerForTask(modulename, taskname, loglevel):
    """
    Configure logging for a task.

    Shortcut for::

        configureStreamLogger(modulename + '.' + taskname, loglevel)

    Example (note that what you put in the loglevel docs for your task depends
    on how you use the logger)::

        @task
        mytask(loglevel='INFO'):
            \"\"\"
            Does some task.

            :param loglevel:
                Controls the amount of output:

                    QUIET --- No output.
                    INFO --- Only produce output for changes.
                    DEBUG --- One line of output for each file.

            Defaults to "INFO".
            \"\"\"
            log = configureStreamLoggerForTask(__name__, 's3_syncupload_dir',
                                               getLoglevelFromString(loglevel))
            log.info('Hello world')
    """
    return configureStreamLogger(modulename + '.' + taskname, loglevel)


def sudo_chown(remote_path, owner):
    """
    Run ``sudo chown <owner> remote_path``.
    """
    sudo('chown {owner} {remote_path}'.format(**vars()))

def sudo_chmod(remote_path, mode):
    """
    Run ``sudo chmod <mode> remote_path``.
    """
    sudo('chmod {mode} {remote_path}'.format(**vars()))

def sudo_chattr(remote_path, owner=None, mode=None):
    """
    Run :func:`sudo_chown` and :func:`sudo_chmod` on ``remote_path``.
    If owner or mode is None, their corresponding function is not called.
    """
    if owner:
        sudo_chown(remote_path, owner)
    if mode:
        sudo_chmod(remote_path, mode)

def sudo_upload_file(local_path, remote_path, **chattr_kw):
    """
    Use sudo to upload a file from ``local_path`` to ``remote_path`` and run
    :func:`sudo_chattr` with the given ``chattr_kw`` as arguments.
    """
    put(local_path, remote_path, use_sudo=True)
    sudo_chattr(remote_path, **chattr_kw)

def sudo_upload_string_to_file(string_to_upload, remote_path, **chattr_kw):
    """
    Create a tempfile containing ``string_to_upload``, and use
    :func:`sudo_upload_file` to upload the tempfile. Removes the tempfile
    when the upload is complete or if it fails.

    :param string_to_upload: The string to write to the tempfile.
    :param remote_path: See :func:`sudo_upload_file`.
    :param chattr_kw: See :func:`sudo_upload_file`.
    """
    tmpfile = NamedTemporaryFile(delete=False)
    try:
        tmpfile.write(string_to_upload)
        tmpfile.close()
        sudo_upload_file(tmpfile.name, remote_path, **chattr_kw)
    finally:
        remove(tmpfile.name)


def sudo_mkdir_p(remote_path, **chattr_kw):
    """
    ``sudo mkdir -p <remote_path>`` followed by :func:`sudo_chattr`(remote_path, **chattr_kw).
    """
    sudo('mkdir -p {remote_path}'.format(**vars()))
    sudo_chattr(remote_path, **chattr_kw)


def sudo_upload_dir(local_dir, remote_dir, **chattr_kw):
    """
    Upload all files and directories in ``local_dir`` to ``remote_dir``.
    Directories are created with :func:`sudo_mkdir_p` and files are uploaded
    with :func:`sudo_upload_file`. ``chattr_kw`` is forwarded in both cases.
    """
    for local_dirpath, dirnames, filenames in walk(local_dir):
        remote_dirpath = remote_dir
        rel = relpath(local_dirpath, local_dir)
        if rel != '.':
            remote_dirpath = join(remote_dir, rel)
        #print local_dirpath, '-->', remote_dirpath
        sudo_mkdir_p(remote_dirpath, **chattr_kw)
        for filename in filenames:
            local_filepath = join(local_dirpath, filename)
            remote_filepath = join(remote_dirpath, filename)
            #print local_filepath, '-->', remote_filepath
            sudo_upload_file(local_filepath, remote_filepath, **chattr_kw)


def parse_bool(data):
    """
    Return ``True`` if data is one of:: ``'true', 'True', True``. Otherwise,
    return ``False``.
    """
    return data in ('true', 'True', True)

def force_slashend(path):
    """
    Return ``path`` suffixed with ``/`` (path is unchanged if it is already
    suffixed with ``/``).
    """
    if not path.endswith('/'):
        path = path + '/'
    return path

def force_noslashend(path):
    """
    Return ``path`` with any trailing ``/`` removed.
    """
    if path.endswith('/'):
        path = path.rstrip('/')
    return path

def localpath_to_slashpath(path):
    """
    Replace ``os.sep`` in ``path`` with ``/``.
    """
    from os import sep
    return path.replace(sep, '/')

def slashpath_to_localpath(path):
    """
    Replace ``/`` in ``path`` with ``os.sep`` .
    """
    from os import sep
    return path.replace('/', sep)

def rsyncformat_path(source_dir, sync_content=False):
    """
    rsync uses ``/`` in the source directory to determine if we should
    sync a directory or the contents of a directory. How rsync works:

    Sync contents:
        Source path ending with ``/`` means sync the contents (just as if we
        used ``/*`` except that ``*`` does not include hidden files).
    Sync the directory:
        Source path NOT ending with ``/`` means sync the directory. I.e.: If
        the source is ``/etc/init.d``,  and the destination is ``/tmp``, the contents
        of ``/etc/init.d`` is copied into ``/tmp/init.d/``.

    This is error-prone, and the consequences can be severe if combined with
    ``--delete``. Therefore, we use a boolean to distinguish between these two
    methods of specifying source directory, and reformat the path using
    :func:`force_slashend` and :func:`force_noslashend`.

    :param source_dir:
        The source directory. May be a remote directory (i.e.:
        [USER@]HOSTNAME:PATH), or a local directory.
    :param sync_content: Normally the function automatically makes sure
        ``local_dir`` is not suffixed with ``/``, which makes rsync copy
        ``local_dir`` into ``remote_dir``. With ``sync_content=True``,
        the content of ``local_dir`` is synced into ``remote_dir`` instead.
    """
    if sync_content:
        return force_slashend(source_dir)
    else:
        return force_noslashend(source_dir)

def compute_localfile_md5sum(localfile):
    """
    Compute the hex-digested md5 checksum of the given ``localfile``.

    :param localfile: Path to a file on the local filesystem.
    """
    fp = open(localfile, 'rb')
    md5sum = compute_md5(fp)[0]
    fp.close()
    return md5sum

def guess_contenttype(filename):
    """
    Return the content-type for the given ``filename``. Uses
    :func:`mimetypes.guess_type`.
    """
    return guess_type(filename)[0]

########NEW FILE########
__FILENAME__ = awsfab_settings_example
# Config file for awsfabrictasks.
#
# This is a Python module, and it is imported just as a regular Python module.
# Every variable with an uppercase-only name is a setting.

AUTH = {'aws_access_key_id': 'XXXXXXXXXXXXXXXXXXXXXX',
        'aws_secret_access_key': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}

DEFAULT_REGION = 'eu-west-1'


##################################################################
# Self documenting map of AMIs
# - You are not required to use this, but it makes it easier to read
#   EC2_LAUNCH_CONFIGS.
##################################################################
ami = {
    'ubuntu-10.04-lts': 'ami-fb665f8f'
}

##################################################################
# Example user_data
# This script will be passed to the new instance at boot
# time and run late in the boot sequence.
# It can be used to do arbitrarily complex setup tasks.
# info: http://ubuntu-smoser.blogspot.co.uk/2010/03/introducing-cloud-inits-cloud-config.html
##################################################################
user_data_example = """#!/bin/sh
echo ========== Hello World: $(date) ==========
echo "I have been up for $(cut -d\  -f 1 < /proc/uptime) sec"
"""


###########################################################
# Configuration for ec2_launch_instance
###########################################################
EC2_LAUNCH_CONFIGS = {
    'ubuntu-10.04-lts-micro': {
        'description': 'Ubuntu 10.04 on the least expensive instance type.',

        # Ami ID (E.g.: ami-fb665f8f)
        'ami': ami['ubuntu-10.04-lts'],

        # One of: m1.small, m1.large, m1.xlarge, c1.medium, c1.xlarge, m2.xlarge, m2.2xlarge, m2.4xlarge, cc1.4xlarge, t1.micro
        'instance_type': 't1.micro',

        # List of security groups
        'security_groups': ['allowssh'],

        # Use the ``list_regions`` task to see all available regions
        'region': DEFAULT_REGION,

        # The name of the key pair to use for instances (See http://console.aws.amazon.com -> EC2 -> Key Pairs)
        'key_name': 'awstestkey',

        # The availability zone in which to launch the instances. This is
        # automatically prefixed by ``region``.
        'availability_zone': 'b',

        # Tags to add to the instances. You can use the ``ec2_*_tag`` tasks or
        # the management interface to manage tags. Special tags:
        #   - Name: Should not be in this dict. It is specified when launching
        #           an instance (needs to be unique for each instance).
        #   - awsfab-ssh-user: The ``awsfab`` tasks use this user to log into your instance.
        'tags': {
            'awsfab-ssh-user': 'ubuntu'
        },
        'user_data': user_data_example
    }
}



######################################################
# Add your own settings here
######################################################

MYCOOLSTUFF_REMOTE_DIR = '/var/www/stuff'

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# restfulgrok documentation build configuration file, created by
# sphinx-quickstart on Tue May  8 12:48:01 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'awsfabrictasks'
copyright = u'2012, Espen Angell Kristiansen'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
from awsfabrictasks import version
# The full version, including alpha/beta/rc tags.
release = version

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#html_theme = 'default'

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if not on_rtd:  # only import and set the theme if we're building docs locally
    try:
        import sphinx_rtd_theme
    except ImportError:
        pass
    else:
        html_theme = 'sphinx_rtd_theme'
        html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

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
htmlhelp_basename = 'restfulgrokdoc'


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
  ('index', 'restfulgrok.tex', u'restfulgrok Documentation',
   u'Espen Angell Kristiansen', 'manual'),
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
    ('index', 'restfulgrok', u'restfulgrok Documentation',
     [u'Espen Angell Kristiansen'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'restfulgrok', u'restfulgrok Documentation',
   u'Espen Angell Kristiansen', 'restfulgrok', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

autodoc_default_flags = ['members', 'show-inheritance']
autoclass_content = 'both'
autodoc_member_order = 'groupwise'

########NEW FILE########
__FILENAME__ = example_fabfile
from fabric.api import task, run
from awsfabrictasks.decorators import ec2instance


###########################
# Add some of our own tasks
###########################

@task
def uname():
    """
    Run ``uname -a``
    """
    run('uname -a')


@task
@ec2instance(nametag='tst')
def example_nametag_specific_task():
    """
    Example of using ``@ec2instance``.
    Enables us to run::

        awsfab example_nametag_specific_task``

    and have it automatically use the EC2 instance tagged with ``Name="tst"``.
    """
    run('uname -a')


#####################
# Import awsfab tasks
#####################
from awsfabrictasks.ec2.tasks import *
from awsfabrictasks.regions import *
from awsfabrictasks.conf import *

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import local, task


@task
def docs():
    """
    Build the Trafo docs.
    """
    local('sphinx-build -b html docs/ build/docs')

########NEW FILE########
